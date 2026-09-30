"""Result-status rules of the EPC90133 Fig. 9 comparison (external review, 30 September 2026).

A switching case whose checks failed must stay inspectable but must never receive a verdict:
scripts/compare_epc90133_fig9.py gives it no "resembles" or consistency result, and
scripts/epc90133_switching.py forms no materiality comparison with it. The comparison module
imports the digitizer, which needs PyMuPDF; those tests are skipped where it is unavailable.
"""
import importlib.util
import math
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HAVE_PYMUPDF = importlib.util.find_spec("fitz") is not None


def load(name):
    for p in (ROOT / "scripts", ROOT / "src"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ringing_edge(rising, step=25e-12, f=270e6, amp=6.0, tau=8e-9, tr=1.7e-9):
    """A 0-45 V edge with a damped ring after it, on the switching script's trace grid."""
    t = -30e-9 + step * np.arange(4001)
    ramp = np.clip(t / tr + 0.5, 0, 1) * 45.0
    ring = np.where(t > tr, amp * np.exp(-(t - tr) / tau) * np.cos(2 * math.pi * f * (t - tr)), 0.0)
    v = ramp + ring if rising else 45.0 - ramp
    return [float(x) for x in v]


def case(usable):
    return {"usable": usable, "checks": {"no_spikes": usable}, "parameters": {"ext": "B-m1-mid"},
            "traces": {"step_s": 25e-12, "start_s": -30e-9, "rising_V": ringing_edge(True),
                       "falling_V": ringing_edge(False)}}


@unittest.skipUnless(HAVE_PYMUPDF, "PyMuPDF not installed")
class ComparisonStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cmp = load("compare_epc90133_fig9")
        import json
        cls.fig9 = json.loads((ROOT / "results/gan/epc90133-qsg-fig9.json").read_text(encoding="utf-8"))
        cls.meas = cls.cmp.measured(cls.fig9)

    def test_unusable_case_gets_no_verdict(self):
        row = self.cmp.evaluate_case(case(False), self.fig9, self.meas)
        self.assertFalse(row["usable"])
        for b in row["bandwidths"].values():
            self.assertIsNone(b["resembles"])
            self.assertIsNone(b["consistency"])
            self.assertIn("excluded", b)
            self.assertIsNotNone(b["metrics"]["rising"])  # still inspectable

    def test_usable_case_gets_verdicts(self):
        row = self.cmp.evaluate_case(case(True), self.fig9, self.meas)
        self.assertTrue(row["usable"])
        self.assertIsInstance(row["bandwidths"]["none"]["resembles"]["all"], bool)
        self.assertTrue(row["bandwidths"]["none"]["consistency"])

    def test_missing_usable_flag_is_not_usable(self):
        c = case(True)
        del c["usable"]
        row = self.cmp.evaluate_case(c, self.fig9, self.meas)
        self.assertFalse(row["usable"])
        self.assertIsNone(row["bandwidths"]["none"]["resembles"])

    def test_gaussian_rise_time_known_answer(self):
        dt = 5e-12
        t = np.arange(-5e-9, 5e-9, dt)
        for bw in (2e9, 1e9, 500e6):
            y = self.cmp.gaussian((t >= 0).astype(float), dt, bw)
            rise = t[np.argmax(y >= 0.9)] - t[np.argmax(y >= 0.1)]
            self.assertAlmostEqual(rise * bw, 0.34, delta=0.01)


class SwitchingComparisonStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sw = load("epc90133_switching")

    def metrics(self, tr):
        a = {"inductor_current_A": 28.9, "sw_fall_time_90_10_s": 4e-9}
        b = {"inductor_current_A": 11.1, "sw_rise_time_10_90_s": tr, "sw_overshoot_above_bus_V": 35.0,
             "ringing_frequency_Hz": 2.8e8, "ringing_damping_ratio": 0.01}
        return {"event_a_turn_off_at_peak": a, "event_b_turn_on_at_valley": b}

    def test_comparison_requires_both_usable(self):
        results = {"ref": {"parameters": {"ext": "B"}, "metrics": self.metrics(0.8e-9), "usable": True},
                   "good": {"parameters": {"ext": "B", "base": "ref"}, "metrics": self.metrics(1.6e-9), "usable": True},
                   "bad": {"parameters": {"ext": "B", "base": "ref"}, "metrics": self.metrics(1.6e-9), "usable": False}}
        out = self.sw.comparisons(results, exts={}, reference="ref")
        self.assertTrue(out["good"]["sw_rise_time_10_90_s"]["material"])
        self.assertIn("excluded", out["bad"])
        self.assertNotIn("sw_rise_time_10_90_s", out["bad"])

    def test_unusable_base_excludes_case(self):
        results = {"ref": {"parameters": {"ext": "B"}, "metrics": self.metrics(0.8e-9), "usable": False},
                   "good": {"parameters": {"ext": "B", "base": "ref"}, "metrics": self.metrics(1.6e-9), "usable": True}}
        out = self.sw.comparisons(results, exts={}, reference="ref")
        self.assertIn("excluded", out["good"])
        self.assertFalse(out["good"]["base_usable"])


if __name__ == "__main__":
    unittest.main()
