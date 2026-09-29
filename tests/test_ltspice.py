import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from circuit_tools.ltspice import parse_log, parse_raw, read_text_auto, run_ltspice


def _raw(variables, rows, *, flags="real forward", binary=True, fmt=None, encoding="utf-16-le"):
    lines = ["Title: * fixture", "Plotname: Fixture", f"Flags: {flags}",
             f"No. Variables: {len(variables)}", f"No. Points: {len(rows)}", "Variables:"]
    lines += [f"\t{i}\t{name}\t{kind}" for i, (name, kind) in enumerate(variables)]
    if binary:
        header = ("\n".join(lines) + "\nBinary:\n").encode(encoding)
        body = b"".join(struct.pack(fmt, *row) for row in rows)
        return header + body
    text = "\n".join(lines) + "\nValues:\n"
    for i, row in enumerate(rows):
        text += f"{i}\t" + "\n\t".join(str(x) for x in row) + "\n"
    return text.encode(encoding)


class RawParserTests(unittest.TestCase):
    def parse(self, data):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.raw"
            p.write_bytes(data)
            return parse_raw(p)

    def test_binary_double_axis_float_traces(self):
        raw = self.parse(_raw([("time", "time"), ("V(out)", "voltage")],
                              [(0.0, 0.0), (1e-3, 0.5), (-2e-3, 0.75)], fmt="<df"))
        self.assertEqual(raw.values["time"], [0.0, 1e-3, 2e-3])  # sign flag removed
        self.assertEqual(raw.values["v(out)"], [0.0, 0.5, 0.75])

    def test_binary_all_double_and_complex(self):
        raw = self.parse(_raw([("V(a)", "voltage"), ("I(R1)", "current")], [(1.0, 2e-3)], fmt="<dd"))
        self.assertEqual(raw.values["i(r1)"], [2e-3])
        raw = self.parse(_raw([("frequency", "frequency"), ("V(out)", "voltage")],
                              [(10.0, 0.0, 0.5, -0.5)], flags="complex forward", fmt="<dddd"))
        self.assertEqual(raw.values["v(out)"], [complex(0.5, -0.5)])

    def test_ascii_matches_binary(self):
        rows = [(0.0, 1.0), (1.0, 2.0)]
        a = self.parse(_raw([("V(a)", "voltage"), ("V(b)", "voltage")], rows, binary=False))
        b = self.parse(_raw([("V(a)", "voltage"), ("V(b)", "voltage")], rows, fmt="<dd"))
        self.assertEqual(a.values, b.values)

    def test_size_mismatch_and_nonfinite_rejected(self):
        good = _raw([("time", "time"), ("V(out)", "voltage")], [(0.0, 1.0)], fmt="<df")
        with self.assertRaises(ValueError):
            self.parse(good[:-1])
        with self.assertRaises(ValueError):
            self.parse(_raw([("time", "time"), ("V(out)", "voltage")], [(0.0, float("nan"))], fmt="<df"))

    def test_nested_sweep_and_single_point_steps(self):
        rows = [(v, 0.0) for v in (0.0, 0.5, 1.0)] * 2
        raw = self.parse(_raw([("va", "voltage"), ("I(R1)", "current")], rows, fmt="<df"))
        self.assertEqual((raw.n_steps, raw.step(1)["va"]), (2, [0.0, 0.5, 1.0]))
        raw = self.parse(_raw([("frequency", "frequency"), ("I(Vd)", "current")],
                              [(1e6, 0, 0, k) for k in range(4)], flags="complex forward stepped", fmt="<dddd"))
        self.assertEqual(raw.n_steps, 4)
        raw = self.parse(_raw([("time", "time"), ("V(out)", "voltage")],
                              [(0.0, 0.0), (1.0, 1.0), (0.0, 0.0), (1.0, 2.0)], fmt="<df"))
        self.assertEqual(raw.step_starts, [0, 2])


GOOD_RAW = None  # built lazily from _raw()
BENCH = "* bench\nV1 a 0 1\nR1 a 0 1k\n.op\n.meas op va FIND V(a)\n.end\n"


def _log(run_dir, body, files=True):
    loaded = f"Files loaded:\n{Path(run_dir).resolve() / 'bench.cir'}\n" if files else ""
    return ("LTspice 26.1.1 for Windows\nCircuit: bench.cir\nsolver = Normal\ntnom = 27\ntemp = 27\n"
            f"method = trap\n{body}\nTotal elapsed time: 0.01 seconds.\n\n{loaded}\n")


class FakeLTspice:
    """Stands in for subprocess.run: writes the given log/raw into the run directory."""

    def __init__(self, body="Direct Newton iteration succeeded in finding operating point.\nva: V(a)=1",
                 raw=True, returncode=0, files=True, extra_files=(), nonfinite=False):
        self.body, self.raw, self.returncode = body, raw, returncode
        self.files, self.extra_files, self.nonfinite = files, extra_files, nonfinite

    def __call__(self, command, cwd, **kwargs):
        out = Path(cwd)
        log = _log(out, self.body, self.files)
        for extra in self.extra_files:
            log = log.replace("Files loaded:\n", f"Files loaded:\n{extra}\n")
        (out / "bench.log").write_bytes(log.encode("utf-16-le"))
        if self.raw:
            value = float("nan") if self.nonfinite else 1.0
            (out / "bench.raw").write_bytes(_raw([("V(a)", "voltage"), ("I(R1)", "current")],
                                                 [(value, 1e-3)], fmt="<dd"))

        class P:
            returncode = self.returncode
            stdout = ""
            stderr = ""
        return P()


class LogAndRunnerTests(unittest.TestCase):
    def run_fake(self, fake, netlist=BENCH, libraries=()):
        with patch("circuit_tools.ltspice.subprocess.run", fake), \
             patch("circuit_tools.ltspice.ltspice_version", lambda exe: "test"):
            d = Path(tempfile.mkdtemp())
            exe = d / "LTspice.exe"
            exe.write_bytes(b"stand-in executable")
            return run_ltspice(netlist, d / "run", executable=exe, libraries=libraries)

    def test_log_classification(self):
        log = parse_log("va: v(a)=0.632 at 0.001\nqoss=2.5e-08\ntemp = 27\ngmin = 1e-12\n"
                        "Measurement \"x\" FAIL'ed\n"
                        "C:\\run\\bench.cir(3): This sub-circuit name is not defined.\n"
                        "WARNING: Less than two connections\nChanging Tseed to 1e-15\n",
                        declared=["va", "qoss", "x", "absent"])
        self.assertEqual(log["measurements"], {"va": [0.632], "qoss": [2.5e-08]})
        self.assertEqual(log["missing_measurements"], ["absent"])
        self.assertEqual(len(log["failed_measurements"]), 1)
        self.assertEqual(len(log["errors"]), 1)
        self.assertEqual(len(log["warnings"]), 1)
        self.assertIn("Changing Tseed to 1e-15", log["notices"])
        # Undeclared name=value lines are metadata, never measurements.
        self.assertEqual(parse_log("temp=27\n")["measurements"], {})

    def test_operating_point_recovery_is_not_an_error(self):
        recovered = parse_log("Direct Newton iteration failed to find operating point.\nStarting Gmin stepping\n"
                              "Gmin stepping succeeded in finding the operating point.\n")
        self.assertEqual(recovered["errors"], [])
        stuck = parse_log("Direct Newton iteration failed to find operating point.\nStarting Gmin stepping\n"
                          "Gmin stepping failed to find operating point.\n")
        self.assertEqual(len(stuck["errors"]), 1)

    def test_good_run_completes(self):
        r = self.run_fake(FakeLTspice())
        self.assertEqual(r.status, "completed", r.message)
        self.assertEqual(r.measurements["va"], [1.0])

    # The three false-success cases found in review.
    def test_missing_waveform_with_metadata_only_log_fails(self):
        r = self.run_fake(FakeLTspice(body="temp=27", raw=False))
        self.assertEqual(r.status, "failed")
        self.assertIn("no waveform", r.message)

    def test_convergence_failure_with_partial_waveform_fails(self):
        r = self.run_fake(FakeLTspice(body="va: V(a)=1\nconvergence failed"))
        self.assertEqual(r.status, "failed")
        self.assertIn("convergence failed", r.message)

    def test_nonzero_exit_with_waveform_fails(self):
        r = self.run_fake(FakeLTspice(returncode=7))
        self.assertEqual(r.status, "failed")
        self.assertIn("status 7", r.message)

    def test_other_failure_paths(self):
        cases = {
            "declared measurements without values": FakeLTspice(body="Measurement \"va\" FAIL'ed"),
            "not defined": FakeLTspice(body="C:\\x\\bench.cir(3): This sub-circuit name is not defined."),
            "unrecovered operating-point": FakeLTspice(body="va: V(a)=1\nGmin stepping failed to find operating point."),
            "non-finite": FakeLTspice(nonfinite=True),
            "undeclared file loaded": FakeLTspice(extra_files=["C:\\LTspice\\lib\\sub\\standard.dio"]),
            "cannot be verified": FakeLTspice(files=False),
        }
        for expected, fake in cases.items():
            with self.subTest(expected):
                r = self.run_fake(fake)
                self.assertEqual(r.status, "failed")
                self.assertIn(expected, r.message)

    def test_terminal_solver_failures_beat_warning_phrases(self):
        # Regression: "too small" is also a warning phrase; the terminal failure must win.
        for phrase in ("Time step too small; initial breakpoint: 1e-9", "Timestep too small",
                       "Singular matrix: check node x", "Iteration limit reached"):
            with self.subTest(phrase):
                self.assertEqual(len(parse_log(phrase + "\n")["errors"]), 1)
                r = self.run_fake(FakeLTspice(body="va: V(a)=1\n" + phrase))
                self.assertEqual(r.status, "failed")
        # A genuine warning phrase alone is still a warning.
        log = parse_log("dd: Emission coefficient, N=0.01, too small, this might lead to numerical problems.\n")
        self.assertEqual((len(log["errors"]), len(log["warnings"])), (0, 1))

    def test_nested_library_dependency_rejected(self):
        d = Path(tempfile.mkdtemp())
        lib = d / "outer.lib"
        lib.write_text("* outer\n.include inner.lib\n")
        r = self.run_fake(FakeLTspice(), netlist=BENCH.replace(".op", ".lib outer.lib\n.op"), libraries=[lib])
        self.assertEqual(r.status, "failed")
        self.assertIn("nested dependencies are not supported", r.message)

    def test_utf16_log_decoding(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.log"
            p.write_bytes("Circuit: x\n".encode("utf-16-le"))
            self.assertEqual(read_text_auto(p), "Circuit: x\n")

    def test_missing_executable_is_not_supported_with_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            r = run_ltspice("* x\n.op\n.end\n", Path(d) / "run", executable=Path(d) / "none.exe")
            self.assertEqual((r.status, r.outcome), ("failed", "not-supported"))
            self.assertTrue(json.loads(Path(r.provenance_path).read_text())["netlist_sha256"])

    def test_unsupplied_or_pathed_library_refused(self):
        with tempfile.TemporaryDirectory() as d:
            r = run_ltspice(".lib models.lib\n.op\n.end\n", Path(d) / "a")
            self.assertEqual((r.status, r.outcome), ("failed", "unresolved"))
            lib = Path(d) / "models.lib"
            lib.write_text("* empty\n")
            r = run_ltspice(".lib ../models.lib\n.op\n.end\n", Path(d) / "b", libraries=[lib])
            self.assertIn("not a supplied library", r.message)

    def test_refuses_non_empty_run_directory_and_bad_timeout(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "old").write_text("evidence")
            with self.assertRaises(FileExistsError):
                run_ltspice(".end\n", d)
            with self.assertRaises(ValueError):
                run_ltspice(".end\n", Path(d) / "new", timeout_s=0)


if __name__ == "__main__":
    unittest.main()
