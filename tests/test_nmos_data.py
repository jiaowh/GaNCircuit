import math
import unittest
from circuit_tools.nmos_data import NMOSDataError, NMOSDataset

PROV={"device_revision":"dev-1","mesh_sha256":"a"*64,"physics_sha256":"b"*64}
def rec(i,vgs=.5,vds=.5,imbalance=0.0,converged=True):
    return {"id":i,"vgs_v":vgs,"vds_v":vds,
            "currents_a_per_cm":{"gate":0.0,"drain":1.0+imbalance,"source":-1.0,"body":0.0},
            "solver_converged":converged}

class NMOSDatasetTests(unittest.TestCase):
    def dataset(self):
        rows=[rec("r0",.4,.2),rec("r1",.5,.5),rec("r2",.6,.8)]
        return NMOSDataset.from_records(rows,PROV,["r0","r1"],["r2"])
    def test_valid_immutable_roundtrip_and_fingerprint(self):
        d=self.dataset(); self.assertEqual(d.temperature_k,300.0); self.assertEqual(len(d.fingerprint),64)
        self.assertEqual(NMOSDataset.from_dict(d.to_dict()).fingerprint,d.fingerprint)
        with self.assertRaises(TypeError): d.records[0]["id"]="changed"
        with self.assertRaises(TypeError): d.provenance["x"]="y"
        bad = d.to_dict(); bad["schema"] = "other/1"
        with self.assertRaises(NMOSDataError): NMOSDataset.from_dict(bad)
    def test_required_provenance_and_complete_disjoint_split(self):
        for key in PROV:
            bad=dict(PROV); del bad[key]
            with self.assertRaises(NMOSDataError): NMOSDataset.from_records([rec("a"),rec("b",.6)],bad,["a"],["b"])
        with self.assertRaises(NMOSDataError): NMOSDataset.from_records([rec("a"),rec("b",.6)],PROV,["a","b"],["b"])
        with self.assertRaises(NMOSDataError): NMOSDataset.from_records([rec("a"),rec("b",.6)],PROV,["a"],[])
        with self.assertRaises(NMOSDataError): NMOSDataset.from_records([rec("a"),rec("b",.6)],PROV,["a"],["unknown"])
    def test_reject_duplicate_ids_bias_bad_current_and_solver(self):
        with self.assertRaises(NMOSDataError): NMOSDataset.from_records([rec("a"),rec("a",.6)],PROV,["a"],["a"])
        with self.assertRaises(NMOSDataError): NMOSDataset.from_records([rec("a"),rec("b")],PROV,["a"],["b"])
        with self.assertRaises(NMOSDataError): NMOSDataset.from_records([rec("a",imbalance=1e-2),rec("b",.5,.6)],PROV,["a"],["b"])
        with self.assertRaises(NMOSDataError): NMOSDataset.from_records([rec("a",converged=False),rec("b",.5,.6)],PROV,["a"],["b"])
    def test_reject_wrong_temperature_nonfinite_and_missing_terminal(self):
        with self.assertRaises(NMOSDataError): NMOSDataset.from_records([rec("a"),rec("b",.5,.6)],PROV,["a"],["b"],temperature_k=298.0)
        row=rec("a"); row["vgs_v"]=math.nan
        with self.assertRaises(NMOSDataError): NMOSDataset.from_records([row,rec("b",.5,.6)],PROV,["a"],["b"])
        row=rec("a"); del row["currents_a_per_cm"]["body"]
        with self.assertRaises(NMOSDataError): NMOSDataset.from_records([row,rec("b",.5,.6)],PROV,["a"],["b"])

    def test_overflow_balance_and_finite_provenance(self):
        huge=rec("a"); huge["currents_a_per_cm"]={"gate":1e308,"drain":1e308,"source":-1e308,"body":-1e308}
        d=NMOSDataset.from_records([huge,rec("b",.5,.6)],PROV,["a"],["b"])
        self.assertEqual(len(d.fingerprint),64)
        bad=dict(PROV); bad["nested"]={"x":float("nan")}
        with self.assertRaises(NMOSDataError): NMOSDataset.from_records([rec("a"),rec("b",.5,.6)],bad,["a"],["b"])
    def test_fingerprint_binds_data_and_provenance(self):
        a=self.dataset(); changed=[dict(r) for r in a.to_dict()["records"]]; changed[0]["vgs_v"]+=.01
        b=NMOSDataset.from_records(changed,PROV,["r0","r1"],["r2"])
        self.assertNotEqual(a.fingerprint,b.fingerprint)
        altered=dict(PROV); altered["device_revision"]="dev-2"
        c=NMOSDataset.from_records(a.to_dict()["records"],altered,["r0","r1"],["r2"])
        self.assertNotEqual(a.fingerprint,c.fingerprint)
        with self.assertRaises(TypeError): a.records[0]["currents_a_per_cm"]["gate"]=1.0
if __name__=="__main__": unittest.main()
