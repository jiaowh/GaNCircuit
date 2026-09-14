import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from circuit_tools.cli import main


class CliTests(unittest.TestCase):
    def test_circuit_revision_round_trip_and_stale_patch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "circuit.json"
            source.write_text(json.dumps({"elements": [{"name": "R1", "kind": "R", "terminals": {"p": "out", "n": "0"}, "value": 1000}]}))
            common = ["--store", str(root / "store")]
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(common + ["circuit-create", str(source)]), 0)
            result = json.loads(output.getvalue())
            patch = root / "patch.json"
            patch.write_text(json.dumps({"expected_revision": result["revision"], "connect": {"R1": {"p": "supply"}}}))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(common + ["circuit-patch", result["artifact"], str(patch)]), 0)
            updated = json.loads(output.getvalue())
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(common + ["circuit-patch", updated["artifact"], str(patch)]), 2)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(common + ["netlist", updated["artifact"]]), 0)
            self.assertEqual(output.getvalue(), "R1 supply 0 1000\n")
