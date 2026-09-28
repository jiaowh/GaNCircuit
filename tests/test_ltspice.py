import json
import struct
import tempfile
import unittest
from pathlib import Path

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


class LogAndRunnerTests(unittest.TestCase):
    def test_log_measurements_errors_and_failed_measurements(self):
        log = parse_log("vtau: v(out)=0.632 at 0.001\nqoss=2.5e-08\nMeasurement \"x\" FAIL'ed\n"
                        "Error: unknown subcircuit called in: x1 g d 0 foo\nWARNING: Less than two connections\n")
        self.assertEqual(log["measurements"], {"vtau": [0.632], "qoss": [2.5e-08]})
        self.assertEqual(len(log["failed_measurements"]), 1)
        self.assertEqual(len(log["errors"]), 1)
        self.assertEqual(len(log["warnings"]), 1)

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
            r = run_ltspice(".lib models.lib\n.end\n", Path(d) / "a")
            self.assertEqual((r.status, r.outcome), ("failed", "unresolved"))
            lib = Path(d) / "models.lib"
            lib.write_text("* empty\n")
            r = run_ltspice(".lib ../models.lib\n.end\n", Path(d) / "b", libraries=[lib])
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
