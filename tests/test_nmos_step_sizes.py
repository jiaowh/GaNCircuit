import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from circuit_tools.nmos_data import NMOSDataset
from scripts.characterize_planar_mos import experiment
from scripts.compare_nmos_step_sizes import compare_steps
from scripts.nmos_evidence import ROOT


class StepSizeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def fixtures(self, current):
        loaded = []
        for i, span in enumerate((.05, .025, .0125)):
            work = self.root / str(i)
            work.mkdir(exist_ok=True)
            (work / "worker.py").write_text("same worker")
            manifest = experiment(span)
            records = []
            for p in manifest["points"]:
                value = current(p["vgs_v"], p["vds_v"])
                records.append({**p, "currents_a_per_cm": {
                    "gate": 0., "drain": value, "source": -value, "body": 0.}, "solver_converged": True})
            provenance = {"device_revision": "device", "mesh_sha256": "mesh", "physics_sha256": "physics",
                          "runtime": {"version": "fixture"}, "qualification_sha256": "qualification"}
            data = NMOSDataset.from_records(records, provenance, manifest["train_ids"], manifest["holdout_ids"])
            report = {"experiment": manifest, "mesh_level": 2, "provenance": provenance,
                      "dataset_path": str((work / "dataset.json").relative_to(ROOT))}
            loaded.append((report, data))
        return loaded

    def compare(self, loaded):
        # Receipt validation is exercised independently by the comparator tests.
        # Isolate this test to the step schedule, identities and numerical rule.
        with patch("scripts.compare_nmos_step_sizes.load_evidence", side_effect=loaded):
            return compare_steps(["wide", "half", "quarter"])

    def test_quadratic_derivative_is_step_independent(self):
        result = self.compare(self.fixtures(lambda g, d: g*g + 3*d*d))
        self.assertEqual(result["outcome"], "pass")
        self.assertEqual(len(result["comparisons"]), 4)
        for row in result["metrics"]:
            self.assertAlmostEqual(row["gm"]["value"], 1.)
            self.assertAlmostEqual(row["gds"]["value"], 3.)
            self.assertAlmostEqual(row["gm_over_gds"], 1/3)

    def test_resolved_step_error_is_fail(self):
        result = self.compare(self.fixtures(lambda g, d: 10 + (g-.5)**3 + d))
        self.assertEqual(result["outcome"], "fail")
        gm = [r for r in result["comparisons"] if r["metric"] == "gm"]
        self.assertTrue(all(not row["pass"] for row in gm))
        self.assertAlmostEqual(gm[0]["relative_delta"], .75)

    def test_zero_slopes_have_no_gain_ratio(self):
        result = self.compare(self.fixtures(lambda g, d: 10.))
        self.assertEqual(result["outcome"], "pass")
        self.assertTrue(all(row["gm_over_gds"] is None for row in result["metrics"]))

    def test_changed_mesh_or_step_schedule_is_unresolved(self):
        loaded = self.fixtures(lambda g, d: g+d)
        loaded[1][0]["provenance"]["mesh_sha256"] = "different"
        self.assertEqual(self.compare(loaded)["outcome"], "unresolved")
        loaded = self.fixtures(lambda g, d: g+d)
        loaded[1][0]["experiment"]["points"][0]["vgs_v"] = .46
        self.assertEqual(self.compare(loaded)["outcome"], "unresolved")
