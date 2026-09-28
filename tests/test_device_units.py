import unittest

from circuit_tools.core import ValidationError
from circuit_tools.device_units import current_per_cm_to_amperes


class DeviceUnitsTests(unittest.TestCase):
    def test_one_micrometre_width_preserves_current_sign(self):
        # 3 A/cm * 1e-4 cm = 300 microamperes.
        self.assertAlmostEqual(current_per_cm_to_amperes(3.0, 1e-6), 300e-6)
        self.assertAlmostEqual(current_per_cm_to_amperes(-3.0, 1e-6), -300e-6)
        self.assertEqual(current_per_cm_to_amperes(0.0, 1e-6), 0.0)

    def test_rejects_invalid_units_inputs_and_overflow(self):
        for current, width in ((1, 0), (1, -1), (True, 1), (1, True),
                               ("3", 1), (1, None), (float("nan"), 1),
                               (1, float("inf")), (1e308, 1e308)):
            with self.subTest(current=current, width=width):
                with self.assertRaises(ValidationError):
                    current_per_cm_to_amperes(current, width)
