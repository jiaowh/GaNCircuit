import importlib.util
import unittest

HAVE_DEPS = all(importlib.util.find_spec(m) for m in ("numpy", "PIL"))
if HAVE_DEPS:
  from circuit_tools.gerber import GerberUnsupported, parse_excellon, parse_gerber, rasterize

HEADER = "%FSLAX25Y25*%\n%MOIN*%\n%ADD10C,0.10000*%\n%ADD11R,0.20000X0.10000*%\n"


@unittest.skipUnless(HAVE_DEPS, "numpy and PIL are needed for the Gerber reader")
class GerberRasterTests(unittest.TestCase):
  """Known-answer areas for each construct the EPC90133 Gerbers use."""

  def raster_area(self, body, bounds, pitch=0.01):
    layer = parse_gerber(HEADER + body + "M02*\n")
    return rasterize(layer, bounds, pitch).area_mm2()

  def test_rectangle_flash(self):
    area = self.raster_area("D11*\nX100000Y100000D03*\n", (0, 0, 50, 50))
    self.assertAlmostEqual(area, 5.08 * 2.54, delta=0.02 * 5.08 * 2.54)

  def test_region_with_clear_polarity_hole(self):
    body = ("G36*\nX0Y0D02*\nX100000Y0D01*\nX100000Y100000D01*\nX0Y100000D01*\nX0Y0D01*\nG37*\n"
            "%LPC*%\nG36*\nX25000Y25000D02*\nX75000Y25000D01*\nX75000Y75000D01*\nX25000Y75000D01*\nX25000Y25000D01*\nG37*\n")
    area = self.raster_area(body, (-1, -1, 30, 30))
    self.assertAlmostEqual(area, 25.4 ** 2 * 0.75, delta=0.01 * 25.4 ** 2)

  def test_round_stroke_includes_end_caps(self):
    area = self.raster_area("D10*\nX0Y0D02*\nX100000Y0D01*\n", (-5, -5, 30, 5))
    w = 2.54
    self.assertAlmostEqual(area, 25.4 * w + 3.14159 * (w / 2) ** 2, delta=0.02 * 25.4 * w)

  def test_centre_line_macro_rotated(self):
    body = "%AMBOX*\n21,1,0.2,0.1,0,0,90.0*\n%\n%ADD12BOX*%\nD12*\nX0Y0D03*\n"
    layer = parse_gerber(HEADER + body + "M02*\n")
    r = rasterize(layer, (-5, -5, 5, 5), 0.01)
    self.assertTrue(r.at(0, 2.2))   # 5.08 x 2.54 mm rotated 90 degrees: 5.08 mm tall
    self.assertFalse(r.at(2.2, 0))  # and only 2.54 mm wide

  def test_parameterised_macro(self):
    # KiCad writes macros with $n parameters; integer variable keys once crashed the substitution (track R 2b run 1).
    body = "%AMPBOX*\n21,1,$1,$2,0,0,0*\n%\n%ADD12PBOX,0.20000X0.10000*%\nD12*\nX0Y0D03*\n"
    layer = parse_gerber(HEADER + body + "M02*\n")
    r = rasterize(layer, (-5, -5, 5, 5), 0.01)
    self.assertAlmostEqual(r.area_mm2(), 5.08 * 2.54, delta=0.02 * 5.08 * 2.54)

  def test_full_circle_region_by_multi_quadrant_arc(self):
    # G75 full circle of radius 0.5 in (12.7 mm), drawn as a region.
    body = "G75*\nG36*\nX50000Y0D02*\nG03*\nX50000Y0I-50000J0D01*\nG01*\nG37*\n"
    area = self.raster_area(body, (-15, -15, 15, 15), pitch=0.02)
    self.assertAlmostEqual(area, 3.14159 * 12.7 ** 2, delta=0.01 * 3.14159 * 12.7 ** 2)

  def test_single_quadrant_arcs_are_rejected(self):
    with self.assertRaises(GerberUnsupported):
      parse_gerber(HEADER + "G74*\nD10*\nX0Y0D02*\nG02*\nX100000Y0I50000J0D01*\nM02*\n")


@unittest.skipUnless(HAVE_DEPS, "numpy and PIL are needed for the Gerber reader")
class ExcellonTests(unittest.TestCase):
  def test_leading_zero_format_pads_on_the_right(self):
    text = "M48\n;FILE_FORMAT=2:5\nINCH,LZ\n;TYPE=PLATED\nT1F00S00C0.01000\n;TYPE=NON_PLATED\nT2F00S00C0.11811\n%\nT01\nX001938Y0042126\nT02\nX0010000Y001\nM30\n"
    holes = parse_excellon(text)
    self.assertAlmostEqual(holes[0].x, 0.1938 * 25.4)
    self.assertAlmostEqual(holes[0].y, 0.42126 * 25.4)
    self.assertTrue(holes[0].plated)
    self.assertAlmostEqual(holes[1].y, 0.1 * 25.4)
    self.assertFalse(holes[1].plated)
    self.assertAlmostEqual(holes[1].diameter, 0.11811 * 25.4)

  def test_metric_decimal_coordinates(self):
    # KiCad's default drill export (track R steps 3-4 run 1 misread X105.25 as 10.5)
    text = "M48\nFMAT,2\nMETRIC\nT1C3.000\n%\nG90\nG05\nT1\nX105.25Y-112.0\nX-0.5Y7\nM30\n"
    holes = parse_excellon(text)
    self.assertAlmostEqual(holes[0].x, 105.25)
    self.assertAlmostEqual(holes[0].y, -112.0)
    self.assertAlmostEqual(holes[1].x, -0.5)
    self.assertAlmostEqual(holes[0].diameter, 3.0)


if __name__ == "__main__":
  unittest.main()
