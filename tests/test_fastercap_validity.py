"""Matrix-validity gate of FasterCap case H (audit at 75d6f35, 2 October 2026).

The audit reproduced all_pass on synthetic negative-diagonal matrices whose pair-capacitance difference matched the
2D reference. These tests feed evaluate() solver-free reports; no FasterCap run is made. The module imports the
known-answer helpers, which need scipy; the tests are skipped where it is unavailable.
"""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HAVE_SCIPY = importlib.util.find_spec("scipy") is not None


def load(name):
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(HAVE_SCIPY, "scipy unavailable")
class ValidityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fc = load("fastercap_board3d_check")

    def pair_matrix(self, c_pair, c_self=1e-13):
        """A physical 2 x 2 Maxwell matrix whose two-conductor capacitance is c_pair."""
        # C11 = C22 = a + b, C12 = -b  ->  pair = (a/2 + b)
        a = c_self
        b = c_pair - a / 2
        return [[a + b, -b], [-b, a + b]]

    def report(self, m_short, m_long, ref):
        rep = {"two_d": {a: {"matrix": [[ref]], "value_F_per_m": ref} for a in self.fc.AUTO_2D}, "three_d": {}}
        for a in self.fc.AUTO_3D:
            rep["three_d"][a] = {f"{self.fc.L1:g}": {"matrix": m_short, "C_pair_F": self.fc.pair(m_short)},
                                 f"{self.fc.L2:g}": {"matrix": m_long, "C_pair_F": self.fc.pair(m_long)}}
        return rep

    def test_physical_matrices_pass(self):
        ref = 1.0e-10
        dl = self.fc.L2 - self.fc.L1
        ms, ml = self.pair_matrix(2e-13), self.pair_matrix(2e-13 + ref * dl / 2)
        self.assertEqual(self.fc.matrix_validity(ms), [])
        rep = self.fc.evaluate(self.report(ms, ml, ref))
        self.assertTrue(rep["all_pass"], rep["checks"])

    def test_negative_diagonal_matrices_cannot_pass(self):
        # the audit's reproduction: unphysical matrices whose pair difference matches the 2D reference
        ref = 1.0e-10
        dl = self.fc.L2 - self.fc.L1
        ms = [[-3.3e-13, 3.7e-13], [3.7e-13, -3.3e-13]]
        target = self.fc.pair(ms) + ref * dl / 2
        # for [[c, d], [d, c]] the pair capacitance is (c - d) / 2
        c = -1.0e-13
        ml = [[c, c - 2 * target], [c - 2 * target, c]]
        self.assertAlmostEqual(self.fc.pair(ml) / target, 1.0, places=9)
        self.assertIn("non-positive diagonal", self.fc.matrix_validity(ms))
        rep = self.fc.evaluate(self.report(ms, ml, ref))
        self.assertFalse(rep["all_pass"])
        self.assertFalse(any(v["pass"] for k, v in rep["checks"].items() if k in ("H1", "H2")))
        self.assertTrue(all(r["C_per_m"] is None for r in rep["three_d"].values()))
        self.assertEqual(len(rep["invalid_matrices"]), 2 * len(self.fc.AUTO_3D))
        self.assertEqual(rep["three_d"][self.fc.AUTO_3D[0]][f"{self.fc.L1:g}"]["matrix"], ms)  # raw matrix kept

    def test_each_rule(self):
        v = self.fc.matrix_validity
        self.assertIn("not square", v([[1.0, 0.0]]))
        self.assertIn("non-finite entry", v([[float("nan")]]))
        self.assertIn("positive off-diagonal", v([[2.0, 0.5], [0.5, 2.0]]))
        self.assertIn("negative row sum", v([[1.0, -1.5], [-1.5, 3.0]]))
        self.assertIn("not reciprocal", v([[2.0, -0.5], [-0.6, 2.0]]))
        self.assertIn("not positive definite", v([[1.0, -1.0], [-1.0, 1.0 - 1e-6]]))
        self.assertEqual(v([[2.0, -0.5], [-0.5, 2.0]]), [])

    def test_stored_report_is_assessed_invalid(self):
        report = ROOT / "results/gan/fastercap-board3d-check.json"
        if not report.is_file():
            self.skipTest("stored report absent")
        import json
        out = load("assess_fastercap_board3d").assess(json.loads(report.read_text(encoding="utf-8")))
        self.assertEqual(out["disposition"]["three_d"], "invalid")
        self.assertEqual(out["disposition"]["two_d"], "valid")
        self.assertFalse(out["disposition"]["derived_C_per_m_usable"])


    def test_stored_assessment_binds_current_dependencies(self):
        out = ROOT / "results/gan/fastercap-board3d-assessment.json"
        if not out.is_file():
            self.skipTest("stored assessment absent")
        import hashlib
        import json
        deps = json.loads(out.read_text(encoding="utf-8"))["dependencies_sha256"]
        self.assertEqual(set(deps), {"scripts/fastercap_board3d_check.py", *self.fc.DEPENDENCIES})
        for p, h in deps.items():
            self.assertEqual(hashlib.sha256((ROOT / p).read_bytes()).hexdigest(), h, p)


if __name__ == "__main__":
    unittest.main()
