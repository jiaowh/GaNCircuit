import math
import unittest

import numpy as np

from circuit_tools.bem2d import EPS0, maxwell_matrix, panels, square


def polygon_circle(r, n):
    return [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n)) for k in range(n)]


class Bem2d(unittest.TestCase):
    def test_coax(self):
        # 256-gons approximate circles; the polygon's own geometric error is about (pi/n)^2 / 6 in radius
        a, b = 1e-3, 2e-3
        C = maxwell_matrix([panels(polygon_circle(a, 256), 2), panels(polygon_circle(b, 256), 2)])
        ref = 2 * math.pi * EPS0 / math.log(b / a)
        self.assertAlmostEqual(C[0, 0] / ref, 1.0, delta=2e-4)
        self.assertAlmostEqual(-C[0, 1] / ref, 1.0, delta=2e-4)

    def test_square_via_in_square_wall(self):
        # closed form of scripts/fasthenry_via_cavity.py: L' = mu0/(2 pi) ln(1.0787 D / (1.1804 w)), here w/D = 1/12;
        # FasterCap 2D at -a0.0005 agreed with it to about 0.02 % (via-array run 4)
        w, D = 0.25e-3, 3e-3
        vals = []
        for n in (8, 16):
            Cm = maxwell_matrix([panels(square(0, 0, w), n), panels(square(0, 0, D), lambda s: max(n, round(n * s / w / 4)))])
            vals.append(Cm[0, 0])
        Lp = 4e-7 * math.pi * EPS0 / vals[-1]
        ref = 4e-7 * math.pi / (2 * math.pi) * math.log(1.0787 * D / (1.1804 * w))
        self.assertAlmostEqual(Lp / ref, 1.0, delta=1e-3)
        self.assertLess(abs(vals[1] / vals[0] - 1), 5e-4)

    def test_maxwell_matrix_is_physical(self):
        C = maxwell_matrix([panels(square(-0.3e-3, 0, 0.17e-3), 8), panels(square(0.3e-3, 0, 0.17e-3), 8),
                            panels(square(0, 0, 3e-3), 32)])
        self.assertTrue(np.allclose(C, C.T, rtol=1e-6, atol=1e-6 * abs(C).max()))
        self.assertTrue(np.all(np.diag(C) > 0))
        self.assertTrue(np.all(C - np.diag(np.diag(C)) <= 1e-9 * abs(C).max()))


if __name__ == "__main__":
    unittest.main()
