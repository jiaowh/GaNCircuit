import hashlib
import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "audit_device_references.py"
spec = importlib.util.spec_from_file_location("audit_device_references", SCRIPT)
audit = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(audit)


def _report(tmp_path, diode_log="top .5 1 2 3\nbot 0 -1 -2 -3\n", mos_log="gate .5 0 0 0\ndrain .5 1 0 1\nsource 0 -1 0 -1\nbody 0 0 0 0\n"):
    diode = tmp_path / "diode.log"
    mos = tmp_path / "mos.log"
    diode.write_text(diode_log)
    mos.write_text(mos_log)
    return {
        "schema": "device-reference/1",
        "references": [
            {"name": "official_diode_1d", "status": "completed", "returncode": 0,
             "stdout_log": "diode.log", "artifacts": {"stdout.log": hashlib.sha256(diode.read_bytes()).hexdigest()}},
            {"name": "official_planar_mos_2d", "status": "completed", "returncode": 0,
             "stdout_log": "mos.log", "artifacts": {"stdout.log": hashlib.sha256(mos.read_bytes()).hexdigest()}},
        ],
    }


class DeviceReferenceAuditTests(unittest.TestCase):
    def test_valid_report_passes(self):
        with self.subTest("valid"):
            from tempfile import TemporaryDirectory
            with TemporaryDirectory() as directory:
                root = Path(directory)
                result = audit.audit_report(_report(root), root)
                self.assertEqual(result["outcome"], "pass")
                self.assertTrue(all(check["outcome"] == "pass" for check in result["checks"]))


    def test_missing_and_duplicate_references_fail(self):
        with self.subTest("structure"):
            from tempfile import TemporaryDirectory
            with TemporaryDirectory() as directory:
                root = Path(directory)
                report = _report(root)
                report["references"] = [report["references"][0], report["references"][0]]
                result = audit.audit_report(report, root)
                self.assertEqual(result["outcome"], "fail")
                self.assertTrue(any("duplicated" in check["reason"] for check in result["checks"]))
                self.assertTrue(any("missing" in check["reason"] for check in result["checks"]))


    def test_noncompleted_reference_is_unresolved(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            root = Path(directory)
            report = _report(root)
            report["references"][0] = {"name": "official_diode_1d", "status": "missing_backend"}
            result = audit.audit_report(report, root)
            self.assertEqual(result["outcome"], "unresolved")
            self.assertEqual(result["checks"][0]["reason"], "reference status is missing_backend")


    def test_bad_status_and_tampered_log_fail(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            root = Path(directory)
            report = _report(root)
            report["references"][0]["status"] = "completed-ish"
            result = audit.audit_report(report, root)
            self.assertEqual(result["outcome"], "fail")
            self.assertTrue(any(check.get("reason") == "invalid reference status" for check in result["checks"]))

            report = _report(root)
            (root / "diode.log").write_text("top .5 1 2 999\nbot 0 -1 -2 -3\n")
            result = audit.audit_report(report, root)
            self.assertEqual(result["outcome"], "fail")
            self.assertTrue(any(check.get("reason") == "stdout log hash mismatch" for check in result["checks"]))


    def test_malformed_nonfinite_and_incomplete_contacts_fail(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            root = Path(directory)
            report = _report(root, diode_log="top .5 nan 2 3\n")
            result = audit.audit_report(report, root)
            self.assertEqual(result["outcome"], "fail")
            self.assertEqual(result["checks"][0]["reason"], "malformed contact data")

            report = _report(root, diode_log="top .5 1 2 3\n")
            result = audit.audit_report(report, root)
            self.assertEqual(result["outcome"], "fail")
            self.assertEqual(result["checks"][0]["reason"], "incomplete contact data")

    def test_truncated_contact_after_valid_row_fails(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            root = Path(directory)
            report = _report(root, diode_log="top .5 1 2 3\ntop .5 1 2\nbot 0 -1 -2 -3\n")
            result = audit.audit_report(report, root)
            self.assertEqual(result["outcome"], "fail")
            self.assertEqual(result["checks"][0]["reason"], "malformed contact data")
