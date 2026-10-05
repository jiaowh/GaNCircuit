import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from via_array_benchmark import v1_check  # noqa: E402


class V1Check(unittest.TestCase):
    def test_complete_and_within_tolerance_passes(self):
        res = {"row6-0.6|c=1|r1": {"ratio_errors": [0.01, -0.02, 0.0, 0.029]},
               "row6-0.6|c=2|r1": {"ratio_errors": [0.0, 0.0, 0.01, 0.02]}}
        self.assertTrue(v1_check(res)["pass"])

    def test_missing_cavity_fails(self):
        res = {"row6-0.6|c=2|r1": {"ratio_errors": [0.0, 0.0, 0.01, 0.02]}}
        out = v1_check(res)
        self.assertFalse(out["complete"])
        self.assertFalse(out["pass"])

    def test_short_ratio_list_fails(self):
        res = {"row6-0.6|c=1|r1": {"ratio_errors": [0.0, 0.0]}, "row6-0.6|c=2|r1": {"ratio_errors": [0.0] * 4}}
        self.assertFalse(v1_check(res)["pass"])

    def test_large_error_fails(self):
        res = {"row6-0.6|c=1|r1": {"ratio_errors": [0.0, 0.0, 0.0, 0.072]}, "row6-0.6|c=2|r1": {"ratio_errors": [0.0] * 4}}
        self.assertFalse(v1_check(res)["pass"])


if __name__ == "__main__":
    unittest.main()
