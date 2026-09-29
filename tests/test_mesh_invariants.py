import tempfile
import unittest
from pathlib import Path
from scripts.mesh_invariants import MeshInvariantError, compare_invariants, invariants, read_mesh
from scripts.qualify_planar_mos import subdivide

BASE = """$MeshFormat
2.1 0 8
$EndMeshFormat
$PhysicalNames
2
1 1 "edge"
2 2 "region"
$EndPhysicalNames
$Nodes
4
1 0 0 0
2 1 0 0
3 1 1 0
4 0 1 0
$EndNodes
$Elements
5
1 1 1 1 1 2
2 1 1 1 2 3
3 1 1 1 3 4
4 1 1 1 4 1
5 2 1 2 1 2 3
$EndElements
"""

SUB = BASE.replace("""$Nodes
4
1 0 0 0
2 1 0 0
3 1 1 0
4 0 1 0
$EndNodes
$Elements
5
1 1 2 1 1 2
2 1 2 1 2 3
3 1 2 1 3 4
4 1 2 1 4 1
5 2 2 2 1 2 3
$EndElements""", """$Nodes
7
1 0 0 0
2 1 0 0
3 1 1 0
4 0 1 0
5 .5 0 0
6 1 .5 0
7 .5 .5 0
$EndNodes
$Elements
8
1 1 1 1 1 5
2 1 1 1 5 2
3 1 1 1 2 6
4 1 1 1 6 3
5 1 1 1 3 4
6 1 1 1 4 1
7 2 1 2 1 5 7
8 2 1 2 5 2 7
$EndElements""")

class MeshInvariantTests(unittest.TestCase):
    def paths(self, text=BASE):
        d=tempfile.TemporaryDirectory(); p=Path(d.name)/"m.msh"; p.write_text(text); self.addCleanup(d.cleanup); return p
    def test_analytical_metrics_and_subdivision(self):
        source = self.paths()
        a = invariants(source)
        self.assertEqual(a["node_count"], 4)
        self.assertAlmostEqual(a["line_lengths"]["1:1"], 4)
        self.assertAlmostEqual(a["triangle_areas"]["2:2"], .5)
        refined = source.with_name("refined.msh")
        subdivide(source, refined)
        self.assertTrue(compare_invariants(source, refined)["pass"])
        self.assertGreater(invariants(refined)["node_count"], a["node_count"])
        self.assertEqual(invariants(refined)["triangle_counts"]["2:2"], 4)
    def test_tag_mismatch_and_malformed_geometry(self):
        altered=BASE.replace('"edge"','"other"')
        self.assertFalse(compare_invariants(self.paths(),self.paths(altered))["pass"])
        bad=BASE.replace("5 2 1 2 1 2 3","5 2 1 2 1 1 1")
        with self.assertRaises(MeshInvariantError): invariants(self.paths(bad))
    def test_unknown_element_and_missing_node(self):
        unknown=BASE.replace("5 2 1 2 1 2 3","5 15 1 2 1 2 3")
        with self.assertRaises(MeshInvariantError): read_mesh(self.paths(unknown))
        missing=BASE.replace("5 2 1 2 1 2 3","5 2 1 2 1 2 9")
        with self.assertRaises(MeshInvariantError): read_mesh(self.paths(missing))
if __name__=="__main__": unittest.main()
