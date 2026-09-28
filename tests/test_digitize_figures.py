"""Regression tests for datasheet axis calibration (scripts/digitize_datasheet_figures.py).

Revision 1 of the digitizer fitted axes to tick-label text centres. EPC's
labels sit up to ~3 pt off their grid lines, which shifted Fig. 6 and turned a
correct energy curve into an apparent failure. These tests pin the fix: label
positions only choose a line; the fit uses the line positions. They need
PyMuPDF and are skipped where it is unavailable (it runs under WSL here).
"""
import importlib.util
import math
import unittest
from pathlib import Path

HAVE_PYMUPDF = importlib.util.find_spec("pymupdf") is not None


def load():
    path = Path(__file__).resolve().parents[1] / "scripts" / "digitize_datasheet_figures.py"
    spec = importlib.util.spec_from_file_location("digitize_datasheet_figures", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ylabel(text, centre_y, x=50.0):
    return (x, centre_y - 4.75, x + 6, centre_y + 4.75, text)


@unittest.skipUnless(HAVE_PYMUPDF, "PyMuPDF not installed")
class AxisCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.d = load()

    def test_offset_labels_calibrate_to_grid_lines(self):
        # Fig. 6-like axis: 0..40 over lines at 470.0 .. 304.0 pt; labels drawn 2.3 pt above their lines.
        lines = [470.0 - k * 33.2 for k in range(6)]
        labels = [ylabel(str(8 * k), y - 2.3) for k, y in enumerate(lines)]
        cal = self.d.calibrate(labels, lines, horizontal=False)
        self.assertEqual(cal["paired"], 6)
        self.assertAlmostEqual(self.d.apply(cal, 470.0), 0.0, places=9)
        self.assertAlmostEqual(self.d.apply(cal, 304.0), 40.0, places=9)

    def test_text_centre_fit_would_have_been_biased(self):
        # The revision-1 approach (fit to label centres) misplaces zero by the text offset.
        lines = [470.0 - k * 33.2 for k in range(6)]
        pairs = [(y - 2.3, 8 * k) for k, y in enumerate(lines)]
        biased = self.d.fit(pairs)
        self.assertGreater(abs(self.d.apply(biased, 470.0)), 0.5)

    def test_log_axis_and_unpaired_label(self):
        lines = [239.0 - k * 55.2 for k in range(4)]
        labels = [ylabel(str(10 ** k), y - 0.4) for k, y in enumerate(lines)]
        cal = self.d.calibrate(labels, lines, horizontal=False)
        self.assertTrue(cal["log10"])
        self.assertAlmostEqual(math.log10(self.d.apply(cal, lines[2])), 2.0, places=9)
        # A label far from every line is reported, not silently paired.
        far = labels + [ylabel("5000", lines[3] - 30.0)]
        cal = self.d.calibrate(far, lines, horizontal=False)
        self.assertEqual(cal["unpaired"], ["5000"])


if __name__ == "__main__":
    unittest.main()
