import unittest
from copy import deepcopy

from scripts.qualify_device_references import parse_contacts, qualification_outcome


class DeviceQualificationTests(unittest.TestCase):
    def test_parse_contacts_uses_total_current_column(self):
        text = """
        noise
        top\t0.5\t1.0\t2.0\t3.0
        bot\t0.0\t-1.0\t-2.0\t-3.0
        """
        contacts = parse_contacts(text)
        self.assertEqual(contacts["top"][0], 0.5)
        self.assertEqual(contacts["top"][3], 3.0)
        self.assertEqual(contacts["bot"][3], -3.0)

    def test_parse_contacts_ignores_malformed_rows(self):
        contacts = parse_contacts("top 0.5 not-a-number 0 0\nbot 0 1 2 3\n")
        self.assertNotIn("top", contacts)
        self.assertIn("bot", contacts)

    def test_acceptance_requires_complete_converged_finite_cases_and_comparisons(self):
        case = {"status": "completed", "solver_converged": True, "final_bias_V": 0.5, "node_count": 10,
                "relative_current_imbalance": 1e-6,
                "contacts": {"top": [0.5, 1.0, 2.0, 3.0], "bot": [0.0, -1.0, -2.0, -3.0]}}
        comparisons = [{"pass": True}, {"pass": True}]
        cases = [case, dict(case, node_count=20), dict(case, node_count=30)]
        self.assertEqual(qualification_outcome(cases, comparisons), "pass")
        self.assertEqual(qualification_outcome(cases[:2], comparisons), "unresolved")
        for field, value in (("solver_converged", False), ("final_bias_V", .4),
                             ("relative_current_imbalance", float("nan")), ("node_count", None)):
            with self.subTest(field=field):
                bad = deepcopy(cases)
                bad[0][field] = value
                self.assertEqual(qualification_outcome(bad, comparisons), "unresolved")
        self.assertEqual(qualification_outcome(cases, []), "unresolved")
        for row in ([], [0, 1, 2], [.1, -1, -2, -3], [0, float("nan"), -2, -3]):
            with self.subTest(contact=row):
                bad = deepcopy(cases)
                bad[0]["contacts"]["bot"] = row
                self.assertEqual(qualification_outcome(bad, comparisons), "unresolved")


if __name__ == "__main__":
    unittest.main()
