"""Fault tests for the E2E-0 independent checker (scripts/e2e_check.py), from the project audit at f4767b1.

Each audit counterexample is a copy of a saved clean C1 record changed in memory; the checker must reject it.
Malformed records must produce structured problems, never an exception. The workspace tests need the git-ignored
pilot workspace (runs/e2e-pilot/C1) and are skipped without it; the validator tests need nothing.
"""
import copy
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from circuit_tools.handoff import validate  # noqa: E402

WS = ROOT / "runs/e2e-pilot/C1/workspace"


def load_checker():
    spec = importlib.util.spec_from_file_location("e2e_check", ROOT / "scripts/e2e_check.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MalformedValidatorTest(unittest.TestCase):
    def test_nested_types_give_problems_not_exceptions(self):
        rec = {"schema": "handoff-i1/1", "produced_by": "agent", "status": "provisional", "stop_reason": None,
               "inputs": [], "artifacts": [],
               "checks": [{"id": "C1", "description": "d", "outcome": "pass", "evidence": [{}]}],
               "exceptions": [{"id": [], "description": "d", "consequence": "c"}],
               "claims": [], "assumptions": []}
        problems = validate(rec)
        self.assertTrue(any("evidence" in p for p in problems))
        self.assertTrue(any("exceptions[0]" in p for p in problems))
        self.assertEqual(validate([]), ["record is not a JSON object"])
        self.assertTrue(validate({"schema": []}))


@unittest.skipUnless((WS / "handoffs/I-2.json").is_file(), "pilot workspace runs/e2e-pilot/C1 not present")
class CheckerCounterexampleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ec = load_checker()
        cls.original = staticmethod(cls.ec.load)

    def mutated(self, rel, change):
        rec = copy.deepcopy(self.original(WS, rel))
        change(rec)

        def load(w, p):
            return rec if Path(w) == WS and p == rel else self.original(w, p)

        with patch.object(self.ec, "load", side_effect=load):
            return self.ec.check(WS, rel)

    def test_clean_records_still_pass(self):
        for rel in ("handoffs/I-1.json", "handoffs/I-2.json", "handoffs/assessment.json"):
            self.assertEqual(self.ec.check(WS, rel), [], rel)

    def test_wrong_device_identity(self):
        p = self.mutated("handoffs/I-1.json", lambda r: r["model"].update(library="nonexistent.lib", subckt="EPC2204"))
        self.assertTrue(any("model.library" in x for x in p))
        self.assertTrue(any("model.subckt" in x for x in p))

    def test_wrong_network(self):
        p = self.mutated("handoffs/I-2.json", lambda r: r["network"].update(
            variant="G", mesh="m2", junction="pad", extraction="nonexistent.json"))
        self.assertTrue(any("network.extraction" in x for x in p))
        p = self.mutated("handoffs/I-2.json", lambda r: r["network"].update(variant="G", mesh="m2", junction="pad"))
        self.assertEqual(sum("identity: network." in x for x in p), 3)

    def test_extra_and_duplicate_predictions(self):
        p = self.mutated("handoffs/I-2.json", lambda r: r["predictions"].append(
            {"case": "invented", "metric": "efficiency", "value": 0.9999, "units": "1", "usable": True}))
        self.assertTrue(any("invented/efficiency" in x for x in p))
        p = self.mutated("handoffs/I-2.json", lambda r: r["predictions"].append(copy.deepcopy(r["predictions"][0])))
        self.assertTrue(any("duplicate" in x for x in p))

    def test_wrong_reference_data(self):
        p = self.mutated("handoffs/assessment.json",
                         lambda r: r["reference_data"].update(path="nonexistent.json", sha256="0" * 64))
        self.assertTrue(any("reference_data.path" in x for x in p))
        p = self.mutated("handoffs/assessment.json", lambda r: r["reference_data"].update(sha256="0" * 64))
        self.assertTrue(any("reference_data: cited hash" in x for x in p))

    def test_malformed_records_are_rejected_not_raised(self):
        p = self.mutated("handoffs/I-1.json", lambda r: r["checks"][0].update(evidence=[{}]))
        self.assertTrue(p)
        p = self.mutated("handoffs/I-1.json", lambda r: r["exceptions"][0].update(id=[]))
        self.assertTrue(p)
        with patch.object(self.ec, "load", return_value=[]):
            self.assertEqual(self.ec.check(WS, "handoffs/I-1.json"), ["schema: record is not a JSON object"])


if __name__ == "__main__":
    unittest.main()
