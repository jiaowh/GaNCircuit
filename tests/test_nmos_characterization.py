import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.characterize_planar_mos import ROOT, experiment, select_mesh

class NMOSCharacterizationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT)
        self.root = Path(self.tmp.name)
        self.mesh = self.root / "gmsh_mos2d.msh"
        self.mesh.write_text("mesh-fixture")
        self.stdout = self.root / "stdout.log"
        self.stdout.write_text("")
        self.case = {"status":"completed","solver_converged":True,
                     "stdout_log":str(self.stdout.relative_to(ROOT)),
                     "mesh_sha256":hashlib.sha256(self.mesh.read_bytes()).hexdigest()}
        self.report = {"outcome":"pass","provenance":{"source_unchanged":True},
                       "mesh_comparisons":[{"outcome":"pass","levels":[2,3]}],
                       "cases":[self.case,self.case,self.case,self.case]}
    def tearDown(self):
        self.tmp.cleanup()
    def test_experiment_has_complete_disjoint_central_slice_holdout(self):
        e=experiment(); self.assertEqual(e["schema"],"nmos-dc-experiment/1")
        ids={p["id"] for p in e["points"]}
        self.assertEqual(len(ids),9)
        self.assertEqual(set(e["train_ids"]) | set(e["holdout_ids"]),ids)
        self.assertFalse(set(e["train_ids"]) & set(e["holdout_ids"]))
        self.assertEqual(len(e["holdout_ids"]),3)
        self.assertTrue(all(p["vgs_v"]==.5 for p in e["points"] if p["id"] in e["holdout_ids"]))
        self.assertEqual(e["body_source_bias_v"],0.0)
    def test_select_mesh_accepts_qualified_level_and_retains_hash(self):
        path=select_mesh(self.report,2)
        self.assertEqual(path,self.mesh.resolve())
    def test_smaller_span_changes_biases_and_preserves_split(self):
        e = experiment(.025)
        self.assertEqual({p["vgs_v"] for p in e["points"]}, {.475, .5, .525})
        self.assertEqual({p["vds_v"] for p in e["points"]}, {.475, .5, .525})
        self.assertEqual(e["train_ids"], experiment()["train_ids"])
        self.assertEqual(e["holdout_ids"], experiment()["holdout_ids"])
        for value in (0, -1, .051, float("inf"), float("nan"), True, 1e-30):
            with self.subTest(value=value), self.assertRaises(ValueError):
                experiment(value)
    def test_select_mesh_rejects_each_guard(self):
        failed_cases = list(self.report["cases"]); failed_cases[2] = dict(self.case, status="failed")
        hash_cases = list(self.report["cases"]); hash_cases[2] = dict(self.case, mesh_sha256="0"*64)
        for bad in (
            dict(self.report,outcome="unresolved"),
            dict(self.report,provenance={"source_unchanged":False}),
            dict(self.report,mesh_comparisons=[{"outcome":"fail","levels":[2,3]}]),
            dict(self.report,mesh_comparisons=[{"outcome":"pass","levels":[3]}]),
            dict(self.report,cases=failed_cases),
            dict(self.report,cases=hash_cases),
        ):
            with self.assertRaises(ValueError):
                select_mesh(bad,2)
if __name__=="__main__":
    unittest.main()
