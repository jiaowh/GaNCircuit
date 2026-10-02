"""Status rules of the frozen handoff records (src/circuit_tools/handoff.py) and the E2E-0 fault injection."""
import importlib.util
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from circuit_tools.handoff import validate  # noqa: E402

H = "a" * 64


def base(schema="handoff-i1/1", status="provisional", **kw):
    rec = {"schema": schema, "produced_by": "agent", "status": status, "stop_reason": None,
           "inputs": [{"path": "in.json", "sha256": H, "role": "input"}],
           "artifacts": [{"path": "out.json", "sha256": H, "role": "result"}],
           "checks": [{"id": "C1", "description": "d", "outcome": "pass", "evidence": ["out.json"]},
                      {"id": "C2", "description": "d", "outcome": "fail", "evidence": ["out.json"]}],
           "exceptions": [{"id": "C2", "description": "d", "consequence": "c"}],
           "claims": [{"statement": "s", "scope": "x", "status": "supported", "evidence": ["out.json"]}],
           "assumptions": [{"name": "a.b", "value": 1.0, "units": "H", "source": "s"}]}
    if schema == "handoff-i1/1":
        rec.update(model={"library": "lib", "sha256": H, "subckt": "EPC2302", "modified": False},
                   simulator={"name": "LTspice", "settings": {}})
    else:
        rec["upstream"] = {"path": "in.json", "sha256": H}
    if schema == "handoff-i2/1":
        rec.update(network={"extraction": "e", "variant": "A", "mesh": "m1", "junction": "mid"},
                   predictions=[{"case": "A", "metric": "m", "value": 1.0, "units": "V", "usable": True}])
    if schema == "sim-assessment/1":
        rec.update(reference_data={"path": "out.json", "sha256": H, "description": "d"}, needed_measurements=[])
    rec.update(kw)
    return rec


class HandoffRules(unittest.TestCase):
    def test_valid_provisional_records(self):
        self.assertEqual(validate(base()), [])
        up = base()
        self.assertEqual(validate(base("handoff-i2/1"), up), [])
        self.assertEqual(validate(base("sim-assessment/1"), base("handoff-i2/1")), [])

    def test_complete_with_failed_check_is_invalid(self):
        self.assertTrue(validate(base(status="complete")))

    def test_provisional_failed_check_must_be_an_exception(self):
        self.assertTrue(validate(base(exceptions=[])))

    def test_stopped_needs_reason_and_no_predictions(self):
        self.assertTrue(validate(base("handoff-i2/1", status="rejected_input"), base()))
        rec = base("handoff-i2/1", status="rejected_input", stop_reason="upstream hash mismatch")
        self.assertIn("a rejected_input record carries no predictions", validate(rec, base()))
        rec["predictions"] = []
        self.assertEqual(validate(rec, base()), [])

    def test_upstream_exceptions_must_be_carried(self):
        up = base(exceptions=[{"id": "C2", "description": "d", "consequence": "c"},
                              {"id": "S1-FIG7", "description": "d", "consequence": "c"}])
        self.assertTrue(any("not carried" in p for p in validate(base("handoff-i2/1"), up)))

    def test_stopped_upstream_forces_rejection(self):
        up = base(status="failed", stop_reason="x")
        self.assertTrue(any("must be rejected_input" in p for p in validate(base("handoff-i2/1"), up)))

    def test_claims_need_scope_and_listed_evidence(self):
        self.assertTrue(validate(base(claims=[{"statement": "s", "scope": "", "status": "supported", "evidence": ["out.json"]}])))
        self.assertTrue(validate(base(claims=[{"statement": "s", "scope": "x", "status": "supported", "evidence": ["other"]}])))
        self.assertTrue(validate(base(claims=[{"statement": "s", "scope": "x", "status": "validated", "evidence": ["out.json"]}])))

    def test_malformed_inputs_never_raise(self):
        for rec in (None, [], {}, {"schema": "handoff-i2/1"}, base(inputs=[{}]), base(checks="x"), base(model=None)):
            self.assertIsInstance(validate(rec), list)
            self.assertTrue(validate(rec))


class FaultInjection(unittest.TestCase):
    def test_model_revision_change_keeps_records_consistent(self):
        spec = importlib.util.spec_from_file_location("e2e_pilot", ROOT / "scripts" / "e2e_pilot.py")
        ep = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ep)
        with tempfile.TemporaryDirectory() as d:
            ws = Path(d)
            lib = ws / "vendor/epc/ltspice/EPCGaNLibrary.lib"
            lib.parent.mkdir(parents=True)
            lib.write_text(".subckt EPC2204 a b c\n.param x=1.5\n.ends\n.subckt EPC2302 g d s\n.param  aWg={Wg*1E-3} "
                           "Wg=2720000 A1={1.698e-02*aWg} k2=2.138e+00\n.ends\n", encoding="latin-1")
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                z.writestr("EPCGaNLibrary.lib", lib.read_bytes())
                z.writestr("other.txt", "x")
            (ws / "vendor/epc/EPCGaNLibrary.zip").write_bytes(buf.getvalue())
            (ws / "devices/epc").mkdir(parents=True)
            (ws / "devices/epc/sources.json").write_text(json.dumps({"files": [{"name": "EPCGaNLibrary.zip", "sha256": "0"}]}))
            (ws / "devices/epc/epc90133-sources.json").write_text(json.dumps({"model": {"sha256": "0"}}))
            note = ep.inject_model_revision(ws)
            text = lib.read_text(encoding="latin-1")
            self.assertIn("k2=3.138e+00", text)          # first decimal parameter of EPC2302, not EPC2204's x
            self.assertIn("x=1.5", text)
            with zipfile.ZipFile(ws / "vendor/epc/EPCGaNLibrary.zip") as z:
                self.assertEqual(z.read("EPCGaNLibrary.lib"), lib.read_bytes())
            s1 = json.loads((ws / "devices/epc/sources.json").read_text())
            s2 = json.loads((ws / "devices/epc/epc90133-sources.json").read_text())
            self.assertEqual(s1["files"][0]["sha256"], ep.sha(ws / "vendor/epc/EPCGaNLibrary.zip"))
            self.assertEqual(s2["model"]["sha256"], ep.sha(lib))
            self.assertNotEqual(note["library_sha256_before"], note["library_sha256_after"])


if __name__ == "__main__":
    unittest.main()
