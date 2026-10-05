"""Static evaluation rules of scripts/epc90133_input_logic.py.

The transcription in devices/epc/epc90133-input-logic.json is evaluated as recorded; these
tests pin the gate function and the classifications that the hardware plan relies on
(the documented settings, and the jumper errors that command both gates on).
"""
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HAVE_OPENPYXL = importlib.util.find_spec("openpyxl") is not None


def load():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("epc90133_input_logic", ROOT / "scripts/epc90133_input_logic.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(HAVE_OPENPYXL, "openpyxl needed by the BOM helper import")
class InputLogicTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()
        cls.logic = json.loads((ROOT / "devices/epc/epc90133-input-logic.json").read_text(encoding="utf-8"))

    def test_gate_is_mux_xor_with_active_low_enable(self):
        g = self.m.gate
        for a in (0, 1):
            for b in (0, 1):
                for c in (0, 1):
                    for d in (0, 1):
                        self.assertEqual(g(0, a, b, c, d), (b if c else a) ^ d)
                        self.assertIsNone(g(1, a, b, c, d))

    def test_documented_settings(self):
        self.assertTrue(all(self.m.qsg_checks(self.logic).values()))

    def test_buck_no_bypass_is_complementary_with_rc_delay(self):
        c = self.m.classify(self.logic, ("1-2",), ("5-6",))
        self.assertEqual(c["kind"], "complementary from PWM1, RC delay on each turn-on")
        self.assertEqual(c["both_on_states"], [])

    def test_missing_bypass_jumper_removes_dead_time(self):
        c = self.m.classify(self.logic, ("1-2",), ())
        self.assertEqual(c["kind"], "complementary from PWM1, no added dead time")

    def test_missing_mode_jumper_drives_both_from_pwm1(self):
        c = self.m.classify(self.logic, (), ("5-6",))
        self.assertTrue(c["kind"].startswith("both follow PWM1"))
        self.assertIn("PWM1=1,PWM2=0", c["both_on_states"])

    def test_two_polarity_jumpers_turn_both_on_at_idle(self):
        c = self.m.classify(self.logic, ("1-2", "3-4"), ("5-6",))
        self.assertTrue(c["kind"].startswith("both on at idle"))
        self.assertEqual(c["idle_gate_commands"], {"HIN": 1, "LIN": 1})

    def test_inverted_dual_reports_actual_both_on_state(self):
        c = self.m.classify(self.logic, ("3-4", "5-6"), ("5-6",))
        self.assertEqual(c["both_on_states"], ["PWM1=0,PWM2=1"])

    def test_full_bypass_passes_inputs_through(self):
        c = self.m.classify(self.logic, ("1-2", "3-4"), ("1-2",))
        self.assertEqual(c["both_on_states"], ["PWM1=1,PWM2=1"])
        self.assertFalse(c["contention"])


if __name__ == "__main__":
    unittest.main()
