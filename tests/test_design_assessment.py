"""Design-assessment gate (audit at 5d72e4e, 6 October 2026; docs/project-audit-5d72e4e.md).

The audit's fault probes still produced a 1.5-ohm selection (or a ranking) with alternatives missing, controls
removed or failed, Gear checks missing, an unsettled revision-1 loss or another extraction. These tests feed the
assessor solver-free synthetic reports built to the switching report's structure; one test replays the stored
round-3 inputs.
"""
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("assess_design", ROOT / "scripts" / "assess_epc90133_design.py")
ad = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ad)

ALTS = ad.DECLARED_ALTERNATIVES
VALUES = {"stock": (20.0, 2.00, 2.00), "R80-1.5": (15.0, 2.06, 1.80), "R80-2.2": (10.0, 2.20, 1.50)}


def case(name, overshoot, loss, q2g, usable=True, revision=2, settled=True):
    design, alt, suffix = ad.parse_name(name)
    driver, l_s = ad.ALTERNATIVE_PARAMETERS[alt]
    maxstep, method = ad.SUFFIXES[suffix]
    p = {"ext": "G-m1-mid", "maxstep": maxstep, "design": design, "alternative": alt}
    if driver == "step":
        p["driver"] = "step"
    if l_s:
        p["l_s"] = l_s
    if method:
        p["method"] = method
    if suffix:
        p["base"] = f"{design}@{alt}"
    if design != "stock":
        p["gate_r"] = {"R80": float(design.split("-")[1])}
    metrics = {"event_a_turn_off_at_peak": {"q1_eoff_J": 2e-6, "sw_min_V": -2.0, "sw_fall_time_90_10_s": 3e-9},
               "event_b_turn_on_at_valley": {"q1_eon_J": 3e-6, "sw_overshoot_above_bus_V": overshoot,
                                             "q2_gate_peak_during_rise_V": q2g, "sw_rise_time_10_90_s": 1.7e-9},
               "period_loss": {"fet_loss_W": loss, "estimated_efficiency": 0.97, "estimator_revision": revision,
                               "settled_within_2pct": settled}}
    return {"parameters": p, "usable": usable, "metrics": metrics if usable else None}


def baseline():
    cases = {}
    for d, v in VALUES.items():
        for a in ALTS:
            cases[f"{d}@{a}"] = case(f"{d}@{a}", *v)
    for base in ("stock@step-Ls0", "R80-2.2@step-Ls0", "R80-2.2@step-Ls50", "stock@ramp-Ls0"):
        cases[base + "-gear"] = case(base + "-gear", *VALUES[base.split("@")[0]])
    cases["stock@ramp-Ls0-repro"] = case("stock@ramp-Ls0-repro", *VALUES["stock"])
    cases["R80-1.5@step-Ls0-ms50"] = case("R80-1.5@step-Ls0-ms50", *VALUES["R80-1.5"])
    return cases


def report(cases, **override):
    rep = {"conditions": {"VIN": 48.0}, "fixed_assumptions": {"x": 1},
           "input_manifest": {"extractions": {"G-m1-mid.json": "aa"}, "vendor_library": {"sha256": "bb"}},
           "cases": cases, "complete": True,
           "runs": {k: {"netlist_sha256": "h-" + k.replace("-repro", "")} for k in cases}}
    rep.update(override)
    return rep


class AssessmentGateTests(unittest.TestCase):
    def run_assess(self, *reports, rule="round3"):
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for i, rep in enumerate(reports):
                p = Path(tmp) / f"r{i}.json"
                p.write_text(json.dumps(rep), encoding="utf-8")
                paths.append(p)
            cases, runs, _ = ad.load_reports(paths)
        return ad.assess(cases, runs, rule)

    def test_baseline_selects(self):
        res = self.run_assess(report(baseline()))
        for label in ("amended_rule", "original_rule"):
            self.assertEqual(res[label]["selection"], "R80-1.5")
            self.assertEqual(res[label]["verdicts"]["R80-2.2"]["verdict"]["constraints"], "not met")
        self.assertTrue(res["gear_check"]["tight_within_0.1pct"])

    def test_missing_alternatives_stay_undetermined(self):
        cases = {k: v for k, v in baseline().items() if v["parameters"]["alternative"] == "step-Ls0"}
        res = self.run_assess(report(cases))["amended_rule"]
        self.assertEqual(res["verdicts"]["R80-1.5"]["verdict"]["constraints"], "undetermined")
        self.assertEqual(res["ranking"], [])
        self.assertIsNone(res["selection"])

    def test_unknown_alternative_or_inconsistent_name_rejected(self):
        cases = baseline()
        cases["stock@ramp-Ls25"] = copy.deepcopy(cases["stock@ramp-Ls0"])
        with self.assertRaises(ad.InputRejected):
            self.run_assess(report(cases))
        cases = baseline()
        cases["R80-1.5@step-Ls0"]["parameters"].pop("driver")
        with self.assertRaises(ad.InputRejected):
            self.run_assess(report(cases))
        cases = baseline()
        cases["R80-1.5@step-Ls50-gear"] = copy.deepcopy(cases["R80-1.5@step-Ls50"])  # no method=gear
        with self.assertRaises(ad.InputRejected):
            self.run_assess(report(cases))

    def test_wrong_extraction_or_incompatible_reports_rejected(self):
        cases = baseline()
        cases["R80-1.5@ramp-Ls0"]["parameters"]["ext"] = "A-m1-mid"
        with self.assertRaises(ad.InputRejected):
            self.run_assess(report(cases))
        b = baseline()
        one = {k: v for k, v in b.items() if k.startswith("stock")}
        two = {k: v for k, v in b.items() if not k.startswith("stock")}
        other = report(two, input_manifest={"extractions": {"G-m1-mid.json": "cc"}, "vendor_library": {"sha256": "bb"}})
        with self.assertRaises(ad.InputRejected):
            self.run_assess(report(one), other)
        self.assertEqual(self.run_assess(report(one), report(two))["amended_rule"]["selection"], "R80-1.5")

    def test_reproduction_control_gates_selection(self):
        cases = baseline()
        del cases["stock@ramp-Ls0-repro"]
        res = self.run_assess(report(cases))["amended_rule"]
        self.assertEqual(res["reproduction_control"]["status"], "missing")
        self.assertIsNone(res["selection"])
        cases = baseline()
        cases["stock@ramp-Ls0-repro"]["metrics"]["period_loss"]["fet_loss_W"] *= 2
        res = self.run_assess(report(cases))["amended_rule"]
        self.assertEqual(res["reproduction_control"]["status"], "fail")
        self.assertIsNone(res["selection"])
        rep = report(baseline())
        rep["runs"]["stock@ramp-Ls0-repro"]["netlist_sha256"] = "different"
        self.assertIsNone(self.run_assess(rep)["amended_rule"]["selection"])

    def test_half_step_check_gates_selection(self):
        cases = baseline()
        del cases["R80-1.5@step-Ls0-ms50"]
        self.assertIsNone(self.run_assess(report(cases))["amended_rule"]["selection"])
        cases = baseline()
        cases["R80-1.5@step-Ls0-ms50"]["metrics"]["period_loss"]["fet_loss_W"] *= 2
        res = self.run_assess(report(cases))["amended_rule"]
        self.assertEqual(res["half_step_check"]["status"], "fail")
        self.assertIsNone(res["selection"])

    def test_gear_check_requires_its_case_set(self):
        cases = baseline()
        cases["R80-1.5@step-Ls50"] = case("R80-1.5@step-Ls50", 0, 0, 0, usable=False)
        cases["stock@step-Ls50-gear"] = case("stock@step-Ls50-gear", *VALUES["stock"])
        cases["R80-1.5@step-Ls50-gear"] = case("R80-1.5@step-Ls50-gear", *VALUES["R80-1.5"])
        res = self.run_assess(report(cases))
        self.assertEqual(res["amended_rule"]["pairs"]["R80-1.5"]["step-Ls50"]["kind"], "gear")
        self.assertEqual(res["amended_rule"]["selection"], "R80-1.5")
        del cases["R80-2.2@step-Ls50-gear"]  # trapezoidal R80-2.2@step-Ls50 is usable, so its check is required
        res = self.run_assess(report(cases))
        self.assertFalse(res["gear_check"]["passes"])
        self.assertEqual(res["amended_rule"]["verdicts"]["R80-1.5"]["verdict"]["constraints"], "undetermined")
        self.assertIsNone(res["amended_rule"]["selection"])

    def test_loss_needs_revision_2_and_settled_window(self):
        for field, value in (("estimator_revision", 1), ("settled_within_2pct", False)):
            cases = baseline()
            cases["R80-1.5@ramp-Ls0"]["metrics"]["period_loss"][field] = value
            res = self.run_assess(report(cases))["amended_rule"]
            self.assertEqual(res["verdicts"]["R80-1.5"]["verdict"]["C1_fet_loss_within_5pct"], "undetermined")
            self.assertIsNone(res["selection"])

    def test_cross_method_reported_separately_from_original_rule(self):
        cases = baseline()
        cases["R80-1.5@ramp-Ls50"] = case("R80-1.5@ramp-Ls50", 0, 0, 0, usable=False)
        cases["R80-1.5@ramp-Ls50-gear"] = case("R80-1.5@ramp-Ls50-gear", *VALUES["R80-1.5"])
        res = self.run_assess(report(cases))
        self.assertEqual(res["amended_rule"]["pairs"]["R80-1.5"]["ramp-Ls50"]["kind"], "cross_method")
        self.assertEqual(res["amended_rule"]["selection"], "R80-1.5")
        self.assertEqual(res["original_rule"]["pairs"]["R80-1.5"]["ramp-Ls50"]["kind"], "none")
        self.assertIsNone(res["original_rule"]["selection"])

    def test_missing_objective_prevents_selection(self):
        # audit at 0f07a6a: revision 4 selected R80-1.5 with ranking [["R80-1.5", null]]
        cases = baseline()
        cases["R80-1.5@ramp-Ls50"]["metrics"]["event_b_turn_on_at_valley"]["sw_overshoot_above_bus_V"] = None
        res = self.run_assess(report(cases))
        for label in ("amended_rule", "original_rule"):
            self.assertEqual(res[label]["verdicts"]["R80-1.5"]["verdict"]["objective"], "undetermined")
            self.assertEqual(res[label]["ranking"], [])
            self.assertIsNone(res[label]["selection"])
        res = self.run_assess(report(cases), rule="round1")  # round 1: undetermined, not a TypeError
        self.assertEqual(res["amended_rule"]["verdicts"]["R80-1.5"]["verdict"]["T1_overshoot_lower"], "undetermined")

    def test_malformed_types_rejected(self):
        # audit at 0f07a6a: usable "false" was treated as true; null cases and a list manifest raised AttributeError
        probes = []
        cases = baseline()
        cases["R80-1.5@ramp-Ls50"]["usable"] = "false"
        probes.append(report(cases))
        cases = baseline()
        cases["R80-1.5@ramp-Ls50"] = None
        probes.append(report(cases))
        probes.append(report(baseline(), input_manifest=["G-m1-mid.json"]))
        cases = baseline()
        cases["R80-1.5@ramp-Ls50"]["metrics"]["event_b_turn_on_at_valley"]["sw_overshoot_above_bus_V"] = "15"
        probes.append(report(cases))
        cases = baseline()
        cases["R80-1.5@ramp-Ls50"]["metrics"]["period_loss"]["fet_loss_W"] = float("nan")
        probes.append(report(cases))
        cases = baseline()
        cases["R80-1.5@ramp-Ls50"]["metrics"]["period_loss"]["settled_within_2pct"] = "yes"
        probes.append(report(cases))
        cases = baseline()
        cases["R80-1.5@ramp-Ls50"]["metrics"] = []
        probes.append(report(cases))
        rep = report(baseline())
        rep["runs"]["stock@ramp-Ls0"] = "h"
        probes.append(rep)
        for i, rep in enumerate(probes):
            with self.subTest(probe=i), self.assertRaises(ad.InputRejected):
                self.run_assess(rep)

    def test_malformed_input_exit_status(self):
        cases = baseline()
        cases["R80-1.5@ramp-Ls50"] = None
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp) / "r.json", Path(tmp) / "a.json"
            src.write_text(json.dumps(report(cases)), encoding="utf-8")
            proc = subprocess.run([sys.executable, str(ROOT / "scripts/assess_epc90133_design.py"), str(src),
                                   "--rule", "round3", "--output", str(out)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["status"], "rejected")

    def test_rejected_input_exit_status(self):
        cases = baseline()
        cases["stock@ramp-Ls25"] = copy.deepcopy(cases["stock@ramp-Ls0"])
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp) / "r.json", Path(tmp) / "a.json"
            src.write_text(json.dumps(report(cases)), encoding="utf-8")
            proc = subprocess.run([sys.executable, str(ROOT / "scripts/assess_epc90133_design.py"), str(src),
                                   "--rule", "round3", "--output", str(out)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2)
            res = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(res["status"], "rejected")
            self.assertNotIn("amended_rule", res)


STORED = ["epc90133-design-round1-rev2.json", "epc90133-design-round1-rev2-cont.json",
          "epc90133-design-round1-rev2-gear.json", "epc90133-design-round1-rev2-gear2.json",
          "epc90133-design-round3.json", "epc90133-design-round3-gear-a.json", "epc90133-design-round3-gear-b.json",
          "epc90133-design-round3-check.json", "epc90133-design-round3-ms50-a.json"]


@unittest.skipUnless(all((ROOT / "results/gan" / f).exists() for f in STORED), "stored round-3 reports absent")
class StoredRound3Tests(unittest.TestCase):
    def test_stored_inputs_select_r80_1_5_under_both_rules(self):
        cases, runs, _ = ad.load_reports([ROOT / "results/gan" / f for f in STORED])
        res = ad.assess(cases, runs, "round3")
        for label in ("amended_rule", "original_rule"):
            self.assertEqual(res[label]["selection"], "R80-1.5")
            self.assertEqual(res[label]["ranking"][0][0], "R80-1.5")
        kinds = res["amended_rule"]["verdicts"]["R80-1.5"]["pair_kinds"]
        self.assertNotIn("cross_method", kinds.values())


if __name__ == "__main__":
    unittest.main()
