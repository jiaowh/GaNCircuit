"""Test 9 assessment: apply the declared rules to the saved reports (no simulation).

Declared in scripts/epc90133_switching.py (test 9): baseline reruns reproduce test 7 within 0.1 % on every
switching metric; each full-R case is judged with the existing materiality rule against its baseline case;
G-m1-mid-fullR-ms50 is the 2 % step check; Q2's internal VGS and channel current during Q1's turn-on are
reported, not judged.

Reading of the internal quantities, defined here after run 1 and before this script's first run: the
switching report's diagnostics window (-5 to +60 ns from Q1's turn-on command) starts during Q2's own
turn-off tail (Q2's gate discharging, Q2 still in reverse conduction after the dead time began), so its
internal-VGS maximum is not a disturbance during the rise. This script takes the rise window instead: from
1 ns before the switch node first passes 10 % of the bus after the command, to +60 ns, on the saved traces
(25 ps grid). Internal quantities are the vendor model's channel-control nodes behind rg and rs; they are
model diagnostics, not physically measurable voltages.

    python scripts/assess_epc90133_test9.py
"""
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "results/gan/epc90133-switching-fullr.json"
TEST7 = ROOT / "results/gan/epc90133-switching-gateloop.json"
OUTPUT = ROOT / "results/gan/epc90133-test9-assessment.json"
KEYS = ("sw_fall_time_90_10_s", "sw_rise_time_10_90_s", "sw_overshoot_above_bus_V", "ringing_frequency_Hz",
        "ringing_damping_ratio")
VIN = 48.0


def flat(m):
    return {**m["event_a_turn_off_at_peak"], **m["event_b_turn_on_at_valley"]}


def rise_window(case):
    tr = case["traces"]
    dv = tr["device"]
    t = tr["start_s"] + tr["step_s"] * np.arange(len(tr["rising_V"]))
    v = np.array(tr["rising_V"])
    t10 = t[np.argmax((t > 0) & (v > 0.1 * VIN))]
    idx = np.where((t >= t10 - 1e-9) & (t < 60e-9))[0]
    out = {"rise_start_after_command_s": float(t10)}
    for q in ("1", "2"):
        vi, ich, vt = (np.array(dv[f"rising_q{q}_{k}"]) for k in ("vgs_internal_V", "channel_current_A", "vgs_V"))
        out[f"q{q}"] = {"terminal_vgs_max_V": float(vt[idx].max()), "terminal_vgs_min_V": float(vt[idx].min()),
                        "internal_vgs_max_V": float(vi[idx].max()), "internal_vgs_min_V": float(vi[idx].min()),
                        "channel_current_max_A": float(ich[idx].max()), "channel_current_min_A": float(ich[idx].min())}
    return out


def main():
    run, t7 = (json.loads(p.read_text(encoding="utf-8")) for p in (RUN, TEST7))
    cases = run["cases"]
    repro = {}
    for name in ("B-m1-mid-ms100", "G-m1-mid", "G-m1-mid-Ls50"):
        a, b = flat(t7["cases"][name]["metrics"]), flat(cases[name]["metrics"])
        rel = {k: b[k] / a[k] - 1 for k in KEYS}
        repro[name] = {"max_abs_rel_change": max(abs(x) for x in rel.values()), "pass": all(abs(x) <= 1e-3 for x in rel.values())}
    status = {n: {"usable": c.get("usable") is True, "failure": None if c.get("metrics") else run["runs"].get(n, {}).get("message")}
              for n, c in cases.items()}
    mat = {n: c for n, c in run["comparison_to_reference"].items() if n.endswith("fullR") or "fullR" in n}
    internal = {n: rise_window(c) for n, c in cases.items() if c.get("traces") and c["traces"].get("device")
                and "rising_q2_vgs_internal_V" in c["traces"]["device"]}
    report = {"schema": "epc90133-test9-assessment/1",
              "inputs": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in (RUN, TEST7)},
              "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "reproduction_of_test7": repro, "case_status": status, "full_R_materiality": mat,
              "step_check_G_fullR": "not evaluated: G-m1-mid-fullR and -ms50 timed out (3600 s)",
              "q2_q1_during_rise": internal,
              "reading": ("The sampled vendor-model traces show no appreciable positive Q2 channel current indicating "
                          "false turn-on during Q1's turn-on (positive maxima 0 to 70 uA at the traces' 10 uA resolution; "
                          "negative values to about -3 A are Q2's reverse conduction at the window start). Its internal "
                          "VGS stays below about 1 V while the terminal VGS reaches up to 2 V. Wording corrected after an "
                          "external audit (2 October 2026). A model diagnostic; it says nothing about the physical "
                          "device's internal gate network.")}
    OUTPUT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print("reproduction", {k: (round(v["max_abs_rel_change"], 6), v["pass"]) for k, v in repro.items()})
    print("status", {k: v["failure"] or "ok" for k, v in status.items()})
    for n, r in internal.items():
        print(n, {q: {k: round(v, 3) for k, v in r[q].items()} for q in ("q2",)})


if __name__ == "__main__":
    main()
