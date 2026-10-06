"""kicad-cli DRC runner (audit at 0f07a6a: failed DRC commands with stale empty reports passed R3/R4).

A fake kicad-cli (this interpreter running a small script) exits with a chosen status and writes a chosen report,
so the runner is tested without KiCad.
"""
import json
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from circuit_tools.kicad import KiCadError, run_drc, validate_drc_report

FAKE = textwrap.dedent("""
    import json, os, sys
    out = sys.argv[sys.argv.index("-o") + 1]
    board = sys.argv[-1]
    mode = os.environ["FAKE_DRC_MODE"]
    good = {"$schema": "https://schemas.kicad.org/drc.v1.json", "kicad_version": "10.0.6",
            "source": os.path.basename(board), "violations": [], "unconnected_items": []}
    if mode == "fail":
        sys.exit(1)
    if mode == "noreport":
        sys.exit(0)
    if mode == "empty":
        good = {}
    if mode == "wrongsource":
        good["source"] = "other.kicad_pcb"
    if mode == "badlist":
        good["violations"] = {"type": "x"}
    if mode == "touch":
        open(board, "a").write("x")
    open(out, "w").write(json.dumps(good))
""")


class RunDrcTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "fake.py").write_text(FAKE, encoding="utf-8")
        self.board = self.dir / "b.kicad_pcb"
        self.board.write_text("(kicad_pcb)", encoding="utf-8")
        self.cli = [sys.executable, str(self.dir / "fake.py")]
        (self.dir / "reports").mkdir()
        (self.dir / "reports" / "stale.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        os.environ.pop("FAKE_DRC_MODE", None)
        self.tmp.cleanup()

    def run_mode(self, mode):
        os.environ["FAKE_DRC_MODE"] = mode
        return run_drc(self.cli, self.board, self.dir / "reports", "t")

    def test_clean_run_binds_hashes(self):
        r = self.run_mode("ok")
        self.assertEqual(r["report"]["violations"], [])
        self.assertEqual(len(r["board_sha256"]), 64)
        self.assertNotEqual(r["report_path"].name, "stale.json")

    def test_failures_raise(self):
        for mode in ("fail", "noreport", "empty", "wrongsource", "badlist", "touch"):
            with self.subTest(mode=mode), self.assertRaises(KiCadError):
                self.run_mode(mode)

    def test_validator(self):
        self.assertTrue(validate_drc_report({}, "b.kicad_pcb"))
        self.assertTrue(validate_drc_report([], "b.kicad_pcb"))


if __name__ == "__main__":
    unittest.main()
