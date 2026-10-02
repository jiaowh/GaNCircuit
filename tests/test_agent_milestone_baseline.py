"""Result-status rules of the agent-milestone plain baseline (audit at 75d6f35, 2 October 2026).

The baseline must never report completion after a failed comparison, must turn missing or malformed inputs into
structured stops instead of crashing, and must not pass K3 on a figure record that names no panel. The comparison
subprocess is mocked; no simulator or agent runs.
"""
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location("agent_milestone", ROOT / "scripts" / "agent_milestone.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AM = load()
FIG = {"checks": {"rising": {"time_scale": "pass", "volt_scale": "fail"},
                  "falling": {"time_scale": "pass", "volt_scale": "fail"}, "pitch_agreement": {}}}
SIM = {"complete": True, "cases": {"B": {"usable": True}}}


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


class Sandbox:
    """A sandbox with one figure and one switching report; contents may be overridden per test."""

    def __init__(self, base, fig=FIG, sim=SIM, write_fig=True, sim_text=None):
        self.sb = base / "run"
        (self.sb / "inputs").mkdir(parents=True)
        (self.sb / "outputs").mkdir()
        fig_b = json.dumps(fig).encode()
        sim_b = (sim_text if sim_text is not None else json.dumps(sim)).encode()
        if write_fig:
            (self.sb / "inputs/fig.json").write_bytes(fig_b)
        (self.sb / "inputs/sim.json").write_bytes(sim_b)
        m = {"evaluator_sha256": AM.sha(AM.COMPARE),
             "files": [{"path": "fig.json", "sha256": sha_bytes(fig_b), "kind": "digitized_figure"},
                       {"path": "sim.json", "sha256": sha_bytes(sim_b), "kind": "switching_report"}]}
        (self.sb / "manifest.json").write_text(json.dumps(m), encoding="utf-8")


def fake_run(returncode, write_outputs, comparison=None):
    def run(cmd, **kw):
        if write_outputs:
            out = Path(cmd[cmd.index("--output") + 1])
            out.write_text(json.dumps(comparison if comparison is not None else {"measured": {}, "cases": {}}))
            Path(cmd[cmd.index("--summary") + 1]).write_text("summary")
        return subprocess.CompletedProcess(cmd, returncode, stdout="out", stderr="Traceback: boom")
    return run


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.saved = AM.BASE
        AM.BASE = self.base

    def tearDown(self):
        AM.BASE = self.saved
        self.tmp.cleanup()

    def report(self):
        return json.loads((self.base / "run/outputs/agent-report.json").read_text(encoding="utf-8"))

    def test_clean_inputs_and_successful_comparison_complete(self):
        Sandbox(self.base)
        out = AM.baseline("run", run=fake_run(0, True))
        self.assertEqual(out["status"], "completed")
        self.assertEqual(out["caveats"], ["rising volt scale fail", "falling volt scale fail"])

    def test_nonzero_exit_is_failed_not_completed(self):
        Sandbox(self.base)
        out = AM.baseline("run", run=fake_run(1, False))
        self.assertEqual(out["status"], "failed")
        self.assertEqual(out["returncode"], 1)
        self.assertIn("Traceback", out["failure"]["stderr_tail"])
        self.assertEqual(self.report()["status"], "failed")

    def test_zero_exit_without_outputs_is_failed(self):
        Sandbox(self.base)
        self.assertEqual(AM.baseline("run", run=fake_run(0, False))["status"], "failed")

    def test_comparison_without_result_keys_is_failed(self):
        Sandbox(self.base)
        self.assertEqual(AM.baseline("run", run=fake_run(0, True, comparison={"x": 1}))["status"], "failed")

    def test_missing_figure_is_a_structured_stop(self):
        Sandbox(self.base, write_fig=False)
        out = AM.baseline("run", run=fake_run(0, True))
        self.assertEqual(out["status"], "stopped")
        self.assertIn("K1", out["stop_reason"])
        self.assertIn("fig.json", out["checks"]["K1"]["detail"])
        self.assertFalse(out["checks"]["K3"]["pass"])
        self.assertTrue(self.report())

    def test_malformed_switching_report_is_a_structured_k4_stop(self):
        Sandbox(self.base, sim_text='{"complete": tru')  # manifest hash matches the malformed file
        out = AM.baseline("run", run=fake_run(0, True))
        self.assertEqual(out["status"], "stopped")
        self.assertEqual(out["stop_reason"], ["K4"])
        self.assertIn("unreadable", out["checks"]["K4"]["detail"]["sim.json"])

    def test_empty_checks_object_does_not_pass_k3(self):
        Sandbox(self.base, fig={"checks": {}})
        out = AM.baseline("run", run=fake_run(0, True))
        self.assertEqual(out["stop_reason"], ["K3"])
        self.assertEqual(out["checks"]["K3"]["detail"]["missing_panels"], ["rising", "falling"])

    def test_one_missing_panel_fails_k3(self):
        Sandbox(self.base, fig={"checks": {"rising": {"time_scale": "pass", "volt_scale": "pass"}}})
        self.assertEqual(AM.baseline("run", run=fake_run(0, True))["stop_reason"], ["K3"])

    def test_malformed_manifests_are_structured_k1_stops(self):
        Sandbox(self.base)
        good = json.loads((self.base / "run/manifest.json").read_text(encoding="utf-8"))
        bad_entries = [{}, {"path": "fig.json"}, {"path": "../fig.json", "sha256": "0" * 64, "kind": "digitized_figure"},
                       {"path": "sub/fig.json", "sha256": "0" * 64, "kind": "digitized_figure"},
                       {"path": "fig.json", "sha256": "xyz", "kind": "digitized_figure"},
                       {"path": "fig.json", "sha256": "0" * 64, "kind": "other"}, "fig.json", None]
        manifests = [[], {}, {"evaluator_sha256": good["evaluator_sha256"]},
                     {**good, "files": "fig.json"}, {**good, "files": []},
                     {**good, "evaluator_sha256": 5},
                     {**good, "files": good["files"] + good["files"][:1]},           # duplicate path
                     {**good, "files": good["files"][1:]}]                            # no figure
        manifests += [{**good, "files": [e] + good["files"][1:]} for e in bad_entries]
        calls = []
        for m in manifests:
            with self.subTest(manifest=m):
                (self.base / "run/manifest.json").write_text(json.dumps(m), encoding="utf-8")
                out = AM.baseline("run", run=lambda *a, **k: calls.append(a))
                self.assertEqual(out["status"], "stopped")
                self.assertEqual(out["stop_reason"], ["K1"])
                self.assertTrue(self.report()["checks"]["K1"]["detail"])
        self.assertEqual(calls, [])

    def test_well_formed_manifest_has_no_problems(self):
        Sandbox(self.base)
        m = json.loads((self.base / "run/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(AM.manifest_problems(m), [])

    def test_no_comparison_runs_after_a_failed_check(self):
        Sandbox(self.base, sim={"complete": False, "cases": {}})
        calls = []
        out = AM.baseline("run", run=lambda *a, **k: calls.append(a))
        self.assertEqual(out["stop_reason"], ["K4"])
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
