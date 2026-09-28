import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from circuit_tools.cli import main


class CliTests(unittest.TestCase):
    def test_nmos_import_preserves_dataset_and_rejects_wrong_schema(self):
        from circuit_tools.nmos_data import NMOSDataset
        records = [{"id": f"g{i}_d{j}", "vgs_v": gate, "vds_v": drain,
                    "currents_a_per_cm": {"gate": 0., "drain": 2*gate+3*drain, "source": -(2*gate+3*drain), "body": 0.},
                    "solver_converged": True} for i, gate in enumerate((.45, .5, .55))
                   for j, drain in enumerate((.45, .5, .55))]
        dataset = NMOSDataset.from_records(records,
            {"device_revision": "device", "mesh_sha256": "mesh", "physics_sha256": "physics"},
            [r["id"] for r in records if r["vgs_v"] != .5],
            [r["id"] for r in records if r["vgs_v"] == .5])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "dataset.json"
            source.write_text(json.dumps(dataset.to_dict()))
            common = ["--store", str(root / "store")]
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(common + ["nmos-import", str(source)]), 0)
            imported = json.loads(output.getvalue())
            self.assertEqual(imported["fingerprint"], dataset.fingerprint)
            self.assertEqual(imported["current_units"], "A/cm")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(common + ["inspect", imported["artifact"]]), 0)
            artifact = json.loads(output.getvalue())
            self.assertEqual(artifact["kind"], "NMOSDCDataset")
            self.assertEqual(artifact["payload"], dataset.to_dict())
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(common + ["nmos-secants", imported["artifact"]]), 0)
            metrics = json.loads(output.getvalue())
            self.assertEqual(metrics["dataset_fingerprint"], dataset.fingerprint)
            self.assertAlmostEqual(metrics["secants"]["gm_vds_0.5"]["value"], 2.)
            self.assertAlmostEqual(metrics["secants"]["gds_vgs_0.5"]["value"], 3.)
            invalid = dataset.to_dict()
            invalid["schema"] = "unknown/1"
            source.write_text(json.dumps(invalid))
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(common + ["nmos-import", str(source)]), 2)

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
