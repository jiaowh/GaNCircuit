import copy
import json
import tempfile
import unittest
from pathlib import Path

from circuit_tools.nmos_data import NMOSDataset
from scripts.characterize_planar_mos import experiment
from scripts.compare_nmos_characterization import compare_reports, comparison
from scripts.nmos_evidence import ROOT, REQUIRED_FILES, canonical_hash, digest


class CharacterizationCompareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.work = [self.base / "coarse", self.base / "fine"]
        for work in self.work:
            work.mkdir()
            (work / "gmsh_mos2d.msh").write_text(work.name)
        backend = {"version": "fixture", "imported_physics_sha256": "physics",
                   "math_libraries": [{"path": "fixture-library", "sha256": "library"}]}
        qualification = {
            "outcome": "pass", "provenance": {"source_unchanged": True,
                "source_mesh_sha256": "base-mesh", "construction_sha256": "construction"},
            "backend": backend, "mesh_comparisons": [{"outcome": "pass", "levels": [2, 3]}],
            "cases": [{}, {}] + [{"status": "completed", "solver_converged": True,
                                  "mesh_sha256": digest(w / "gmsh_mos2d.msh")} for w in self.work],
        }
        self.qualification = self.base / "qualification.json"
        self.qualification.write_text(json.dumps(qualification))
        self.reports = []
        for level, work in zip((2, 3), self.work):
            manifest = experiment()
            (work / "runner-source.py").write_text("runner fixture")
            provenance = {
                "device_revision": canonical_hash({"base_mesh": "base-mesh", "construction": "construction"}),
                "mesh_sha256": digest(work / "gmsh_mos2d.msh"), "physics_sha256": "physics",
                "qualification_sha256": digest(self.qualification), "runtime": backend,
                "experiment_sha256": canonical_hash(manifest), "runner_sha256": digest(work / "runner-source.py"),
            }
            records = []
            for point in manifest["points"]:
                current = 100 + 2 * point["vgs_v"] + 3 * point["vds_v"]
                records.append({**point, "currents_a_per_cm": {
                    "gate": 0., "drain": current, "source": -current, "body": 0.}, "solver_converged": True})
            dataset = NMOSDataset.from_records(records, provenance, manifest["train_ids"], manifest["holdout_ids"])
            self.write_json(work / "dataset.json", dataset.to_dict())
            self.write_json(work / "points.json", dataset.to_dict()["records"])
            self.write_json(work / "experiment.json", manifest)
            self.write_json(work / "solve-info.json", [{"converged": True}] * 18)
            for name in ("stdout.log", "stderr.log", "worker.py"):
                (work / name).write_text(name)
            report = {"schema": "nmos-characterization-run/1", "outcome": "pass", "mesh_level": level,
                "experiment": manifest, "provenance": provenance, "execution": {"status": "completed", "returncode": 0},
                "observed_points": 9, "missing_point_ids": [], "dataset_path": str((work / "dataset.json").relative_to(ROOT)),
                "dataset_sha256": digest(work / "dataset.json"), "dataset_fingerprint": dataset.fingerprint}
            self.reports.append(report)
            self.refresh_receipts(len(self.reports)-1)

    @staticmethod
    def write_json(path, value):
        path.write_text(json.dumps(value))

    def refresh_receipts(self, index):
        self.reports[index]["artifacts"] = {str(p.relative_to(ROOT)): digest(p) for p in self.work[index].iterdir()}

    def edit_dataset(self, index, edit):
        work = self.work[index]
        payload = json.loads((work / "dataset.json").read_text())
        edit(payload)
        dataset = NMOSDataset.from_dict(payload)
        self.write_json(work / "dataset.json", dataset.to_dict())
        self.write_json(work / "points.json", dataset.to_dict()["records"])
        self.reports[index].update(dataset_sha256=digest(work / "dataset.json"), dataset_fingerprint=dataset.fingerprint)
        self.refresh_receipts(index)

    def compare(self):
        return compare_reports(*self.reports, qualification_path=self.qualification)

    def test_analytical_pass_and_endpoint_metadata(self):
        result = self.compare()
        self.assertEqual(result["outcome"], "pass", result)
        self.assertEqual(len(result["currents"]), 36)
        self.assertEqual(len(result["slopes"]), 6)
        for slope in result["slopes"]:
            self.assertAlmostEqual(slope["first"], 2. if slope["name"].startswith("gm") else 3.)
            self.assertIn("low_current_A_per_cm", slope["first_endpoints"])

    def test_comparison_rejects_overflow_and_uses_exact_absolute_floor(self):
        with self.assertRaises(ValueError):
            comparison(1e308, -1e308, .01, 1e-10)
        result = comparison(0., 1e-10, .01, 1e-10)
        self.assertTrue(result["pass"])
        self.assertTrue(result["absolute_floor_dominated"])
        self.assertAlmostEqual(result["allowed_delta"], 1.01e-10, delta=1e-24)

    def test_balanced_current_failure_is_resolved_fail(self):
        def edit(payload):
            currents = payload["records"][4]["currents_a_per_cm"]
            currents["drain"] *= 2
            currents["source"] *= 2
        self.edit_dataset(1, edit)
        result = self.compare()
        self.assertEqual(result["outcome"], "fail", result)
        self.assertTrue(all(row["pass"] for row in result["slopes"]))

    def test_slope_failure_with_all_currents_within_tolerance(self):
        def edit(payload):
            currents = payload["records"][7]["currents_a_per_cm"]
            currents["drain"] += .003
            currents["source"] -= .003
        self.edit_dataset(1, edit)
        result = self.compare()
        self.assertEqual(result["outcome"], "fail", result)
        self.assertTrue(all(row["pass"] for row in result["currents"]))
        self.assertTrue(any(not row["pass"] for row in result["slopes"]))

    def test_every_required_receipt_is_required_and_hash_checked(self):
        original = copy.deepcopy(self.reports[1])
        for name in REQUIRED_FILES:
            with self.subTest(name=name):
                self.reports[1] = copy.deepcopy(original)
                path = self.work[1] / name
                del self.reports[1]["artifacts"][str(path.relative_to(ROOT))]
                self.assertEqual(self.compare()["outcome"], "unresolved")
                self.reports[1] = copy.deepcopy(original)
                contents = path.read_bytes()
                path.write_bytes(contents + b"tampered")
                self.assertEqual(self.compare()["outcome"], "unresolved")
                path.write_bytes(contents)

    def test_false_or_missing_solver_receipts_are_unresolved(self):
        for solves in ([], [{"converged": True}] * 17 + [{"converged": False}]):
            self.write_json(self.work[1] / "solve-info.json", solves)
            self.refresh_receipts(1)
            self.assertEqual(self.compare()["outcome"], "unresolved")

    def test_second_dataset_split_must_match_manifest(self):
        def edit(payload):
            payload["train_ids"], payload["holdout_ids"] = payload["holdout_ids"], payload["train_ids"]
        self.edit_dataset(1, edit)
        self.assertEqual(self.compare()["outcome"], "unresolved")

    def test_dataset_bias_must_match_manifest(self):
        self.edit_dataset(1, lambda payload: payload["records"][0].update(vgs_v=.4))
        self.assertEqual(self.compare()["outcome"], "unresolved")

    def test_wrong_level_qualification_and_execution_are_unresolved(self):
        original = copy.deepcopy(self.reports[1])
        for mutate in (lambda r: r.update(mesh_level=2), lambda r: r["execution"].update(returncode=1),
                       lambda r: r["provenance"].pop("qualification_sha256")):
            self.reports[1] = copy.deepcopy(original)
            mutate(self.reports[1])
            self.assertEqual(self.compare()["outcome"], "unresolved")
        self.reports[1] = original
        self.qualification.write_text("{}")
        self.assertEqual(self.compare()["outcome"], "unresolved")


if __name__ == "__main__":
    unittest.main()
