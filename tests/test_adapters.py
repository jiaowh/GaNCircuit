import unittest

from circuit_tools.adapters import discover_capabilities


class AdapterTests(unittest.TestCase):
  def test_capability_discovery_reports_both_backends(self):
    found = discover_capabilities()
    self.assertTrue({"ltspice", "devsim"}.issubset(found))
    self.assertNotIn("ngspice", found)
