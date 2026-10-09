"""Acceptance-gate rules of scripts/assess_epc90133_goals.py (audit docs/project-audit-274cd46.md, 9 October 2026).

An interpretation-invalid case is never scored, an unset required goal (S5) keeps 'all_met' from passing, an empty
goal set is undetermined, and duplicate or model-incompatible inputs stop the scoring. Synthetic reports only.
"""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HAVE_NUMPY = importlib.util.find_spec("numpy") is not None


def load():
    spec = importlib.util.spec_from_file_location("assess_epc90133_goals", ROOT / "scripts" / "assess_epc90133_goals.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def report(cases, lib="a" * 64):
    return {"study": "goals", "conditions": {"VIN": 48.0}, "input_manifest": {"vendor_library": {"sha256": lib}},
            "cases": cases}


@unittest.skipUnless(HAVE_NUMPY, "needs numpy")
class GoalsAssessmentGate(unittest.TestCase):
    def setUp(self):
        self.g = load()
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, *reports):
        paths = []
        for i, r in enumerate(reports):
            p = self.dir / f"r{i}.json"
            p.write_text(json.dumps(r), encoding="utf-8")
            paths.append(str(p))
        out = self.dir / "out.json"
        argv = sys.argv
        sys.argv = ["assess", *paths, "--model-suffix", "", "--output", str(out)]
        try:
            self.g.main()
        finally:
            sys.argv = argv
        return json.loads(out.read_text(encoding="utf-8"))

    def test_interpretation_invalid_case_is_not_scored(self):
        self.assertIsNone(self.g.metrics({"usable": True, "interpretation_invalid": "declared"}, 48.0))

    def test_empty_and_partial_sets_are_undetermined(self):
        self.assertIsNone(self.g.combine([]))
        self.assertIsNone(self.g.combine([True, None]))
        self.assertIs(self.g.combine([True, None, False]), False)

    def test_unset_s5_blocks_all_met(self):
        out = self.run_main(report({"stock@ramp-Ls50-gear": {"usable": False}}))
        verdict = out["designs"]["stock"]["verdict"]
        self.assertEqual(tuple(verdict), self.g.GOALS)
        self.assertIsNone(verdict["S5"])
        self.assertIsNone(out["designs"]["stock"]["all_met"])
        self.assertIsNone(self.g.combine(dict(verdict, **{k: True for k in verdict if k != "S5"}).values()))

    def test_duplicate_case_stops(self):
        r = report({"stock@ramp-Ls50-gear": {"usable": False}})
        with self.assertRaises(SystemExit):
            self.run_main(r, r)

    def test_model_library_mismatch_stops(self):
        with self.assertRaises(SystemExit):
            self.run_main(report({"stock@ramp-Ls50-gear": {"usable": False}}),
                          report({"V8@ramp-Ls50-gear": {"usable": False}}, lib="b" * 64))


if __name__ == "__main__":
    unittest.main()
