import json
import unittest
import importlib.util
from pathlib import Path


REPORT = Path(__file__).parents[1] / "results" / "device-reference" / "current-normalization.json"
SCRIPT = Path(__file__).parents[1] / "scripts" / "qualify_current_normalization.py"
spec = importlib.util.spec_from_file_location("qualify_current_normalization", SCRIPT)
qualify = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(qualify)


class CurrentNormalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not REPORT.is_file():
            raise unittest.SkipTest("qualification report has not been generated")
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_report_declares_units_and_tolerances(self):
        self.assertEqual(self.report["schema"], "current-normalization/1")
        self.assertEqual(self.report["units"]["contact_current"], "A/cm")
        self.assertGreater(self.report["tolerances"]["relative"], 0)
        self.assertGreater(self.report["tolerances"]["absolute_a_per_cm"], 0)

    def test_two_width_cases_pass_and_scale_linearly(self):
        self.assertEqual(self.report["result"]["outcome"], "pass")
        cases = self.report["result"]["cases"]
        self.assertEqual(len(cases), 2)
        for case in cases:
            self.assertEqual(case["outcome"], "pass")
            self.assertTrue(case["solver"]["initial_converged"])
            self.assertTrue(case["solver"]["carrier_converged"])
            self.assertLessEqual(case["observed"]["contact_balance_a_per_cm"], 1e-12)
        ratio = cases[1]["observed"]["left_electron_current_a_per_cm"] / cases[0]["observed"]["left_electron_current_a_per_cm"]
        width_ratio = cases[1]["geometry"]["contact_width_cm"] / cases[0]["geometry"]["contact_width_cm"]
        self.assertAlmostEqual(ratio, width_ratio, places=10)
        self.assertAlmostEqual(self.report["result"]["width_scaling"]["observed_current_ratio"], ratio, places=10)
        self.assertAlmostEqual(self.report["result"]["width_scaling"]["geometry_width_ratio"], width_ratio, places=10)

    def test_injected_nonconvergence_is_unresolved(self):
        case = {"solver": {"initial_converged": False, "carrier_converged": True}}
        self.assertEqual(qualify.classify_case(case), "unresolved")

    def test_injected_nan_or_missing_measurement_fails(self):
        case = {"solver": {"initial_converged": True, "carrier_converged": True}, "analytic": {"contact_current_a_per_cm": 1.0}, "observed": {"left_electron_current_a_per_cm": float("nan"), "right_electron_current_a_per_cm": -1.0, "absolute_error_a_per_cm": 0.0, "contact_balance_a_per_cm": 0.0}}
        self.assertEqual(qualify.classify_case(case), "fail")
        del case["observed"]["right_electron_current_a_per_cm"]
        self.assertEqual(qualify.classify_case(case), "fail")

    def test_injected_converged_mismatch_fails(self):
        case = {"solver": {"initial_converged": True, "carrier_converged": True}, "analytic": {"contact_current_a_per_cm": 1.0}, "observed": {"left_electron_current_a_per_cm": 2.0, "right_electron_current_a_per_cm": -2.0, "absolute_error_a_per_cm": 1.0, "contact_balance_a_per_cm": 0.0}}
        self.assertEqual(qualify.classify_case(case), "fail")


if __name__ == "__main__":
    unittest.main()
