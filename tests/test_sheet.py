import math
import unittest

from circuit_tools.sheet import disk_mask, squares


class SheetSquares(unittest.TestCase):
    def test_rectangle_is_exact(self):
        for nx, ny in ((10, 10), (40, 10), (7, 23)):
            self.assertAlmostEqual(squares(disk_mask(nx, ny, 1.0)), nx / ny, places=10)

    def test_series_rectangles(self):
        # a narrowing: a W-wide section then a W/2-wide section in series
        m = disk_mask(40, 20, 1.0, slots=[(20, 10, 41, 21)])
        self.assertGreater(squares(m), 20 / 20 + 20 / 10 - 0.5)  # spreading adds to the ideal series sum minus a bit
        self.assertLess(squares(m), 20 / 20 + 20 / 10 + 0.5)

    def test_small_hole_dilute_limit(self):
        # a = W/20 in a strip of width W, length 4W: added squares 2 pi a^2 / W^2. Staircased circles converge first
        # order in the cell size (10 and 20 cells per radius give +6.7 % and +4.1 %), so compare the Richardson value.
        W, a = 1.0, 1.0 / 20
        ref = 2 * math.pi * a ** 2 / W ** 2
        added = []
        for div in (200, 400):
            cell = W / div
            base = squares(disk_mask(4 * div, div, cell))
            added.append(squares(disk_mask(4 * div, div, cell, holes=[(2.0, 0.5, a)])) - base)
        self.assertAlmostEqual((2 * added[1] - added[0]) / ref, 1.0, delta=0.025)

    def test_aligned_rectangle_converges(self):
        # a slot whose edges lie on cell faces has no staircase error; halving the cell changes it little
        vals = []
        for cell in (0.05, 0.025):
            m = disk_mask(round(4 / cell), round(2 / cell), cell, slots=[(1.8, 0.5, 2.2, 1.5)])
            vals.append(squares(m) - 2.0)
        self.assertLess(abs(vals[1] / vals[0] - 1), 0.02)

    def test_disconnected_raises(self):
        m = disk_mask(20, 10, 1.0, slots=[(9, -1, 11, 11)])
        with self.assertRaises(ValueError):
            squares(m)


if __name__ == "__main__":
    unittest.main()
