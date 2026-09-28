import tempfile
import unittest
from collections import Counter
from pathlib import Path

from scripts.mesh_invariants import compare_invariants, read_mesh
from scripts.refine_planar_mesh import refine


class LocalRefinementTests(unittest.TestCase):
    def test_preserves_geometry_and_has_no_hanging_edges(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory)/"source.msh", Path(directory)/"refined.msh"
            coords = [(x*1e-5, y) for y in (0, 3e-5, 6e-5, 1e-4) for x in range(4)]
            elements = []
            for j in range(3):
                for i in range(3):
                    a = 1+4*j+i
                    elements.extend([(2,2,(a,a+1,a+5)), (2,2,(a,a+5,a+4))])
            for i in range(3):
                elements.extend([(1,1,(i+1,i+2)), (1,1,(13+i,14+i)),
                                 (1,1,(1+4*i,5+4*i)), (1,1,(4+4*i,8+4*i))])
            lines = ['$MeshFormat','2.1 0 8','$EndMeshFormat','$PhysicalNames','2',
                     '1 1 "boundary"','2 2 "bulk"','$EndPhysicalNames','$Nodes','16']
            lines += [f'{n} {x:.17g} {y:.17g} 0' for n,(x,y) in enumerate(coords,1)]
            lines += ['$EndNodes','$Elements',str(len(elements))]
            lines += [' '.join(map(str,(n,kind,1,tag,*vertices)))
                      for n,(kind,tag,vertices) in enumerate(elements,1)]
            source.write_text('\n'.join(lines+['$EndElements'])+'\n')
            refine(source, output)
            self.assertTrue(compare_invariants(source, output)['pass'])
            mesh = read_mesh(output)
            incidence, boundary = Counter(), set()
            for _, kind, _, vertices in mesh['elements']:
                if kind == 1:
                    boundary.add(tuple(sorted(vertices)))
                else:
                    a,b,c = vertices
                    incidence.update(tuple(sorted(e)) for e in ((a,b),(b,c),(c,a)))
            self.assertEqual({e for e,count in incidence.items() if count == 1}, boundary)
            self.assertTrue(all(count == (1 if e in boundary else 2) for e,count in incidence.items()))
            self.assertGreater(len(mesh['nodes']), len(coords))
            second = Path(directory)/'second.msh'
            refine(source, second)
            self.assertEqual(output.read_bytes(), second.read_bytes())
