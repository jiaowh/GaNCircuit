import math
import unittest

from scripts.analyze_planar_nmos import amplifier, central, crossing


class PlanarNMOSAnalysisTest(unittest.TestCase):
    def test_central_difference_is_exact_for_quadratic(self):
        xs = [0.0, 0.1, 0.2, 0.3]
        slopes = central(xs, [3 * x * x for x in xs])
        for x, slope in slopes:
            self.assertAlmostEqual(slope, 6 * x)

    def test_crossing_interpolates_in_log_current(self):
        xs = [0.0, 0.1, 0.2]
        ys = [1e-9 * 10 ** (x / 0.08) for x in xs]  # 80 mV/decade
        self.assertAlmostEqual(crossing(xs, ys, 1e-8), 0.08)
        self.assertIsNone(crossing(xs, ys, 1.0))

    def test_amplifier_gain_is_width_independent(self):
        op = {"spec": {"supply_v": 3.0}, "stencil": {"vg_v": 0.7, "vd_v": 1.5},
              "metadata": {"mesh_scale": 1.0, "nodes": {"bulk": 10}},
              "small_signal": {"id_a_per_cm": 0.05, "gm_s_per_cm": 0.4, "gds_s_per_cm": 0.002,
                               "gm_over_id_per_v": 8.0, "intrinsic_gain": 200.0}}
        a, b = amplifier([op], 1e-4), amplifier([op], 2e-4)
        self.assertAlmostEqual(a["device_width_um"], 20.0)
        self.assertAlmostEqual(a["rd_ohm"], 15000.0)
        self.assertAlmostEqual(a["gm_rd"], 8.0 * 1.5)
        expected = -12.0 / (1 + 12.0 / 200.0)
        self.assertAlmostEqual(a["small_signal_gain_v_per_v"], expected)
        self.assertAlmostEqual(b["small_signal_gain_v_per_v"], expected)
        self.assertTrue(math.isclose(b["device_width_um"], 2 * a["device_width_um"]))


if __name__ == "__main__":
    unittest.main()
