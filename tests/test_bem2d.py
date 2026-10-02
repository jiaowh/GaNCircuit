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



class Bem2dDielectric(unittest.TestCase):
    def test_coated_coax(self):
        # inner conductor a in a dielectric shell (eps 4.3) to b, air to the outer conductor c: exact
        # C = 2 pi eps0 / (ln(b/a)/eps + ln(c/b)); constant interface panels converge first order, so compare the
        # Richardson value of n and 4n panels
        from circuit_tools.bem2d import outward_normals, solve_dielectric
        a, b, c, er = 1e-3, 1.5e-3, 2e-3, 4.3
        ref = 2 * math.pi * EPS0 / (math.log(b / a) / er + math.log(c / b))
        vals = []
        for n in (96, 384):
            mid = polygon_circle(b, n)
            pm = panels(mid, 1)
            nx, ny = outward_normals(pm, mid)
            q = solve_dielectric([[(panels(polygon_circle(a, n), 1), er)], [(panels(polygon_circle(c, n), 1), 1.0)]],
                                 [(pm, nx, ny, 1.0, er)], [1.0, 0.0])
            vals.append(q[0] / ref - 1)
        self.assertLess(abs(vals[1]), 0.005)
        self.assertLess(abs(vals[1] - (vals[0] - vals[1]) / 3), 5e-4)

    def test_equal_permittivity_interface_changes_nothing(self):
        from circuit_tools.bem2d import outward_normals, solve_dielectric
        mid = polygon_circle(1.5e-3, 128)
        pm = panels(mid, 1)
        nx, ny = outward_normals(pm, mid)
        q = solve_dielectric([[(panels(polygon_circle(1e-3, 128), 1), 1.0)], [(panels(polygon_circle(2e-3, 128), 1), 1.0)]],
                             [(pm, nx, ny, 1.0, 1.0)], [1.0, 0.0])
        self.assertAlmostEqual(q[0] / (2 * math.pi * EPS0 / math.log(2)), 1.0, delta=1e-5)


if __name__ == "__main__":
    unittest.main()
