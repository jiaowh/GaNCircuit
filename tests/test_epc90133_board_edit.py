"""Rule checks of scripts/epc90133_board_edit.py (layout round 2). Needs the git-ignored EPC90133 Gerbers."""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIP = ROOT / "vendor/epc/epc90133/EPC90133 Development Board Gerbers.zip"
HAVE = ZIP.is_file() and importlib.util.find_spec("scipy") is not None


@unittest.skipUnless(HAVE, "EPC90133 Gerbers (vendor/) not present")
class AddViaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
        import epc90133_board_edit as be
        from read_epc90133_geometry import load_board
        cls.be, cls.b = be, load_board()
        cls.paste = be.paste_layers()

    def test_accepted_via_bonds_only_to_its_net(self):
        nb, rec = self.be.add_via(self.b, 17.0, 23.0, "GND", paste=self.paste)
        self.assertEqual(len(nb.holes), len(self.b.holes) + 1)
        self.assertGreaterEqual(len(rec["bonded_layers"]), 2)
        self.assertTrue(nb.distinct)
        self.assertEqual(nb.net_of("GTL", 17.0, 23.0), "GND")

    def test_original_board_is_not_modified(self):
        before = self.b.grids["GTL"].grid.sum()
        self.be.add_via(self.b, 17.0, 23.0, "GND", paste=self.paste)
        self.assertEqual(self.b.grids["GTL"].grid.sum(), before)

    def test_spacing_rule(self):
        h = next(h for h in self.b.holes if h.plated and 18 < h.x < 23 and 24 < h.y < 33)
        with self.assertRaisesRegex(self.be.EditRefused, "R2"):
            self.be.add_via(self.b, h.x + 0.2, h.y, "GND", paste=self.paste)

    def test_drill_rule(self):
        with self.assertRaisesRegex(self.be.EditRefused, "R1"):
            self.be.add_via(self.b, 17.0, 23.0, "GND", drill=0.1, paste=self.paste)

    def test_no_via_under_a_component_pad(self):
        refused = 0
        for x, y in ((20.5, 31.0), (20.5, 26.0)):  # the FET centres
            try:
                self.be.add_via(self.b, x, y, "GND", paste=self.paste)
            except self.be.EditRefused as e:
                refused += str(e).startswith(("R2", "R3"))
        self.assertEqual(refused, 2)


if __name__ == "__main__":
    unittest.main()
