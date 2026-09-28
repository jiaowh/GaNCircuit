import unittest
from scripts.mesh_delaunay import restore_delaunay, opposite_cotangent


class DelaunayTests(unittest.TestCase):
    def test_flips_bad_diagonal_and_preserves_constraints(self):
        nodes = {1:(0,0,0),2:(2,0,0),3:(2,1,0),4:(0,3,0)}
        elements = [(2,(1,),(1,2,4)),(2,(1,),(2,3,4))]
        self.assertLess(opposite_cotangent(nodes,2,4,1)+opposite_cotangent(nodes,2,4,3),0)
        result, count = restore_delaunay(nodes,elements)
        self.assertEqual(count,1)
        self.assertTrue(all(1 in row[2] and 3 in row[2] for row in result))
        self.assertEqual(restore_delaunay(nodes,result)[1],0)
        constrained = elements+[(1,(2,),(2,4))]
        self.assertEqual(restore_delaunay(nodes,constrained), (constrained,0))
        separated = [elements[0],(2,(2,),elements[1][2])]
        self.assertEqual(restore_delaunay(nodes,separated),(separated,0))
