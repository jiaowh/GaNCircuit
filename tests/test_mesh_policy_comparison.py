import unittest
from copy import deepcopy
from scripts.compare_planar_mesh_reports import compare


class MeshPolicyComparisonTests(unittest.TestCase):
    def report(self):
        return {"provenance": {key:"same" for key in ("commit","source_mesh_sha256","script_sha256","construction_sha256")},
                "backend": {"version":"same","imported_physics_sha256":"same"},
                "outcome":"unresolved", "cases":[{"status":"completed","solver_converged":True,
                    "contact_rows":{"gate":[.5,0,0,0],"drain":[.5,3,0,3],
                                    "source":[0,-3,0,-3],"body":[0,0,0,0]}}]}

    def test_agreement_is_separate_from_reference_qualification(self):
        result = compare(self.report(),self.report())
        self.assertEqual(result['outcome'],'pass')
        self.assertEqual(result['reference_mesh_outcome'],'unresolved')

    def test_rejects_physics_change_missing_data_and_current_disagreement(self):
        reference = self.report()
        for fault in ('physics','missing','current'):
            candidate = deepcopy(reference)
            if fault == 'physics':
                candidate['backend']['imported_physics_sha256'] = 'changed'
            elif fault == 'missing':
                candidate['cases'] = []
            else:
                candidate['cases'][0]['contact_rows']['drain'][-1] = 4
            self.assertNotEqual(compare(reference,candidate)['outcome'],'pass')
