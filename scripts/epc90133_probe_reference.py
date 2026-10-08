#!/usr/bin/env python3
"""Probe-reference bracket for the Fig. 9 overshoot gap (epc90133_switching.py --study probe; declared there).

For each probe case, every pair V(tip) - V(ground) is scored with compare_epc90133_fig9.evaluate_case (unchanged
Fig. 9 metric definitions and bandwidths). Tips: Q2.D (the present observable's tip), Q1.S2, Q1.S46. Grounds: Q2.S46
(circuit ground, the present observable), Q2.S2, Ci1-7.GND, Cm1-10.GND, U80.GND, and the means over Ci and over Cm.
The extraction has no J33 terminals, so these pairs bracket, not reproduce, EPC's probe connection.
Output: results/gan/epc90133-probe-reference.json.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import compare_epc90133_fig9 as cmp

TIPS = ("q2_d", "q1_s2", "q1_s46")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report", type=Path)
    ap.add_argument("--fig9", type=Path, default=ROOT / "results/gan/epc90133-qsg-fig9.json")
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-probe-reference.json")
    args = ap.parse_args()
    rep = json.loads(args.report.read_text(encoding="utf-8"))
    fig9 = json.loads(args.fig9.read_text(encoding="utf-8"))
    meas = cmp.measured(fig9)
    out = {}
    for name, case in rep["cases"].items():
        tr = case.get("traces") or {}
        term = tr.get("terminals")
        if not term:
            out[name] = {"usable": False, "reason": case.get("error") or "no terminal traces"}
            continue
        n = len(tr["rising_V"])
        sig = {nd: {ev: np.array(v[ev]) for ev in ("rising", "falling")} for nd, v in term.items()}
        sig["q2_d"] = {ev: np.array(tr[f"{ev}_V"]) for ev in ("rising", "falling")}
        sig["0"] = {ev: np.zeros(n) for ev in ("rising", "falling")}
        grounds = ["0", "q2_s2", "u80_gnd"] + sorted(k for k in sig if k.endswith("_gnd") and k[:2] in ("ci", "cm"))
        for grp in ("ci", "cm"):
            ks = [k for k in sig if k.startswith(grp) and k.endswith("_gnd")]
            sig[f"mean_{grp}_gnd"] = {ev: np.mean([sig[k][ev] for k in ks], axis=0) for ev in ("rising", "falling")}
            grounds.append(f"mean_{grp}_gnd")
        rows = {}
        for tip in TIPS:
            for g in grounds:
                pseudo = {"traces": {"step_s": tr["step_s"], "start_s": tr["start_s"],
                                     **{f"{ev}_V": list(sig[tip][ev] - sig[g][ev]) for ev in ("rising", "falling")}},
                          "usable": case.get("usable"), "checks": case.get("checks")}
                ev = cmp.evaluate_case(pseudo, fig9, meas)
                bw = ev.get("bandwidths", {})
                pick = {}
                for key in ("none", "1000MHz"):
                    m = (bw.get(key) or {}).get("metrics") or {}
                    r_, f_ = m.get("rising") or {}, m.get("falling") or {}
                    pick[key] = {"rise_s": r_.get("edge_10_90_s"), "overshoot_V": r_.get("overshoot_above_settled_V"),
                                 "ring_Hz": r_.get("ring_frequency_Hz"), "zeta": r_.get("ring_damping_ratio"),
                                 "fall_s": f_.get("edge_10_90_s"), "undershoot_V": f_.get("undershoot_below_settled_V")}
                rows[f"{tip}-{g}"] = pick
                p = pick["none"]
                if all(p[k] is not None for k in ("overshoot_V", "undershoot_V", "rise_s")):
                    print(f"{name:22s} {tip:7s} - {g:13s} os {p['overshoot_V']:5.1f} V  us {p['undershoot_V']:4.1f} V  "
                          f"tr {p['rise_s'] * 1e9:4.2f} ns  f {(p['ring_Hz'] or 0) / 1e6:4.0f} MHz  zeta {(p['zeta'] or 0):.3f}")
        out[name] = {"usable": case.get("usable"), "pairs": rows}
    meas_row = {"overshoot_V": meas["rising"]["overshoot_above_settled_V"],
                "undershoot_V": meas["falling"]["undershoot_below_settled_V"]}
    args.output.write_text(json.dumps({
        "schema": "epc90133-probe-reference/1", "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "inputs": {str(args.report): hashlib.sha256(args.report.read_bytes()).hexdigest(),
                   str(args.fig9): hashlib.sha256(args.fig9.read_bytes()).hexdigest()},
        "measured": meas_row, "cases": out}, indent=1) + "\n")


if __name__ == "__main__":
    main()
