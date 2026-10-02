"""Assessment of the driver-only bench (scripts/epc90133_driver_only.py, run 2); no new simulation.

Reads the stored report and its raw files and records, per declared question, what the run answers. Written after
the run, so its diagnostics are labelled post hoc; they do not change a declared check's verdict.

* C1 as declared compares C81's charge loss with the pull-up mirror's charge only. At VIN = 0 the bootstrap switch
  recharges C81 during the high-side turn-on (PHASE stays near ground), which the check omitted: a check-design
  error. C1 stays failed. Post-hoc diagnostic: mirror charge minus bootstrap-diode charge against C81's loss.
* The VCC minimum in the report includes the t = 0 sample of the uic start (0 V); the diagnostic excludes the
  first nanosecond.
* Q2 start-up and Q3 depend on initial states that the run shows were not what the declaration assumed (see
  "answered" fields), so those questions are recorded as not answered.

    PYTHONPATH=src python scripts/assess_epc90133_driver_only.py   # results/gan/epc90133-driver-only-assessment.json
"""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from circuit_tools.ltspice import parse_raw

REPORT = ROOT / "results/gan/epc90133-driver-only.json"
OUTPUT = ROOT / "results/gan/epc90133-driver-only-assessment.json"
C81 = {"ramp-L0-C81low": 50e-9}
T_HI1 = 0.1e-6 + 0.5e-6 + 10e-9  # first high-side command (the bench's sequence)


def main():
    rep = json.loads(REPORT.read_text(encoding="utf-8"))
    root = ROOT / rep["run_directory"]
    diag = {}
    for name, m in rep["edges"].items():
        s = {k: np.asarray(v) for k, v in parse_raw(root / f"edges-{name}" / "bench.raw").step(0).items()}
        t, vbp = s["time"], s["v(boot)"] - s["v(sw)"]
        w = (t >= T_HI1 - 1e-9) & (t <= T_HI1 + 100e-9)
        q_m, q_d = np.trapezoid(s["i(vusns)"][w], t[w]), np.trapezoid(s["i(dbst)"][w], t[w])
        dq = C81.get(name, 100e-9) * (np.interp(T_HI1 - 1e-9, t, vbp) - np.interp(T_HI1 + 100e-9, t, vbp))
        diag[name] = {"mirror_charge_C": float(q_m), "bootstrap_diode_charge_C": float(q_d), "c81_charge_loss_C": float(dq),
                      "balance_ratio": float((q_m - q_d) / dq), "vcc_min_after_1ns_V": float(s["v(vcc)"][t > 1e-9].min())}
    e = rep["edges"]
    q1 = rep["Q1_reading"]["per_inductance"]
    out = {
        "schema": "epc90133-driver-only-assessment/1",
        "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "inputs": {REPORT.relative_to(ROOT).as_posix(): hashlib.sha256(REPORT.read_bytes()).hexdigest()},
        "checks": {
            "C1": {"declared_verdict": "fail", "reason": "check omitted the simultaneous bootstrap recharge at VIN = 0 "
                   "(check-design error); kept failed",
                   "post_hoc_mirror_minus_diode_balance": {k: v["balance_ratio"] for k, v in diag.items()},
                   "post_hoc_pass_within_0.1pct": all(abs(v["balance_ratio"] - 1) <= 1e-3 for v in diag.values())},
            "C2": rep["C2"]["pass"], "C3": rep["C3"]["pass"]},
        "Q1_E1_discrimination": {
            "answered": True,
            "q2_gate_pad_rise_s": {k: e[k]["q2_gate_pad"][0]["rise_10_90_s"] for k in ("ramp-L0", "step-L0", "ramp-L1n", "step-L1n")},
            "q2_gate_pad_fall_s": {k: e[k]["q2_gate_pad"][0]["fall_90_10_s"] for k in ("ramp-L0", "step-L0", "ramp-L1n", "step-L1n")},
            "differences": q1,
            "reading": "distinguishable under the provisional placeholders for both gate-loop inductances (within this "
                       "model): the step form is slower into the real gate load because of its larger resistance; the "
                       "edges are about 20-25 ns, not the 8 ns datasheet figure into 3000 pF"},
        "Q2_bootstrap": {
            "startup_answered": False,
            "startup_reason": "with both FETs off at VIN = 0 the switch node was held only by the bench's assumed 1 Mohm, "
                              "rose to about 1.05-1.10 V and left BOOT-PHASE at 3.69-3.75 V after 200 us (below the "
                              "3.94 V maximum BOOT POR threshold); the declared premise that PHASE stays near ground "
                              "was an assumption the bench does not support",
            "startup_report": rep["startup"],
            "droop_answered": True,
            "first_high_side_pulse": {k: {"boot_phase_before_V": e[k]["boot_phase"][0]["before_V"],
                                          "net_drop_100ns_V": e[k]["boot_phase"][0]["drop_V"],
                                          "q1_gate_pad_high_V": e[k]["q1_gate_pad"][0]["high_level_V"],
                                          "q1_gate_pad_high_second_pulse_V": e[k]["q1_gate_pad"][1]["high_level_V"]}
                                      for k in ("ramp-L0", "ramp-L0-C81low", "ramp-L0-Rboot2.2")},
            "gate_charge_drawn_C": diag["ramp-L0"]["mirror_charge_C"],
            "vcc_min_after_1ns_V": min(v["vcc_min_after_1ns_V"] for v in diag.values())},
        "Q3_dead_time_overcharge": {
            "answered": False,
            "reason": "both excursion runs started at BOOT-PHASE 3.82 V, below VCC minus the switch drop, so the "
                      "0.17-0.19 V rise is ordinary recharge, not charging above VCC; a run from the settled state "
                      "needs a new declaration (the stop rules' fix run was used by run 2)",
            "report": rep["dead_time_excursions"]},
        "post_hoc_diagnostics": diag}
    OUTPUT.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out["checks"], indent=1))


if __name__ == "__main__":
    main()
