import json
import tempfile
import unittest
import sys
from unittest.mock import patch
from pathlib import Path

from circuit_tools.adapters import discover_capabilities, parse_wrdata, run_ngspice


class AdapterTests(unittest.TestCase):
  def test_parse_wrdata_values_and_headers(self):
    fixture = """Title: fixture
Variables: 2
0 time time
1 v(out) voltage
Values:
0 0.0 1.25
1 1.0 1.50
"""
    self.assertEqual(parse_wrdata(fixture), {"time": [0.0, 1.0], "v(out)": [1.25, 1.5]})


  def test_missing_ngspice_is_explicit_not_supported(self):
    with tempfile.TemporaryDirectory() as d:
      result = run_ngspice("* fixture\n.end\n", d, executable="definitely-no-ngspice")
      self.assertEqual((result.status, result.outcome), ("failed", "not-supported"))
      self.assertEqual(result.measurements, {})
      provenance = json.loads(Path(result.provenance_path).read_text())
      self.assertTrue(provenance["netlist_sha256"])
      self.assertTrue(provenance["reason"])


  def test_capability_discovery_reports_both_backends(self):
    found = discover_capabilities()
    self.assertTrue({"ngspice", "devsim"}.issubset(found))

  def test_parser_rejects_ragged_and_nonfinite(self):
    with self.assertRaises(ValueError): parse_wrdata("0 1\n1 2 3\n")
    with self.assertRaises(ValueError): parse_wrdata("0 Inf\n")

  def test_invalid_timeout_and_result_traversal(self):
    with tempfile.TemporaryDirectory() as d:
      with self.assertRaises(ValueError): run_ngspice(".end\n", d, timeout_s=0)
      Path(d).rmdir()
    with tempfile.TemporaryDirectory() as d:
      with self.assertRaises(ValueError): run_ngspice(".end\n", d, result_file="../x")

  def test_stale_directory_and_include_refused(self):
    with tempfile.TemporaryDirectory() as d:
      p = Path(d) / "artifact"; p.mkdir(); (p / "old").write_text("evidence")
      with self.assertRaises(FileExistsError): run_ngspice(".end\n", p)
    with tempfile.TemporaryDirectory() as d:
      r = run_ngspice(".include other.lib\n.end\n", d, executable="missing")
      self.assertEqual((r.status, r.outcome), ("failed", "unresolved"))

  @patch("circuit_tools.adapters.subprocess.run")
  def test_nonzero_exit_and_timeout_bytes_are_unresolved(self, run):
    class P:
      returncode = 2; stdout = ""; stderr = "bad"
    run.side_effect = [P(), P()]
    with tempfile.TemporaryDirectory() as d:
      r = run_ngspice(".end\n", d, executable=sys.executable)
      self.assertEqual((r.status, r.outcome), ("failed", "unresolved"))
    import subprocess
    run.side_effect = subprocess.TimeoutExpired("ngspice", 1, output=b"x", stderr=b"y")
    with tempfile.TemporaryDirectory() as d:
      r = run_ngspice(".end\n", d, executable=sys.executable)
      self.assertEqual((r.status, r.outcome), ("failed", "unresolved"))
