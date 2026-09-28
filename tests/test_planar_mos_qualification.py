import unittest
from copy import deepcopy
from scripts.qualify_planar_mos import qualify

class PlanarMosQualificationTests(unittest.TestCase):
    def base(self, n):
        return {"status":"completed","solver_converged":True,"contacts":{"gate":.5,"drain":.5,"source":0.,"body":0.},
                "contact_rows":{k:[v,1.,2.,1.] for k,v in {"gate":.5,"drain":.5,"source":0.,"body":0.}.items()},
                "nodes":{"gate":n,"bulk":n,"oxide":n},"relative_current_imbalance":1e-6}
    def test_valid_two_mesh_cases_pass(self):
        self.assertEqual(qualify([self.base(10),self.base(20)],1e-4),"pass")
    def test_each_gate_failure_is_unresolved(self):
        valid=[self.base(10),self.base(20)]
        self.assertEqual(qualify(valid[:1],1e-4),"unresolved")
        bad=dict(self.base(20),solver_converged=False)
        self.assertEqual(qualify([valid[0],bad],1e-4),"unresolved")
    def test_mesh_delta_and_all_contact_columns_are_checked(self):
        valid = [self.base(10), self.base(20)]
        for row in ([.5, 1., 2., 1.03], [.5, float("nan"), 2., 1.],
                    [.4, 1., 2., 1.], []):
            with self.subTest(row=row):
                bad = deepcopy(valid)
                bad[1]["contact_rows"]["drain"] = row
                self.assertEqual(qualify(bad, 1e-4), "unresolved")
        bad=dict(self.base(20),contacts={"gate":.4,"drain":.5,"source":0.,"body":0.})
        self.assertEqual(qualify([valid[0],bad],1e-4),"unresolved")
        bad=dict(self.base(20),relative_current_imbalance=float("nan"))
        self.assertEqual(qualify([valid[0],bad],1e-4),"unresolved")
        bad=dict(self.base(10),nodes={"gate":10,"bulk":10,"oxide":10})
        self.assertEqual(qualify([valid[0],bad],1e-4),"unresolved")
if __name__=="__main__":
    unittest.main()
