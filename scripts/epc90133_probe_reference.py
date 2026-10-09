#!/usr/bin/env python3
"""Probe-reference bracket for the Fig. 9 overshoot gap (epc90133_switching.py --study probe; declared there).

For each probe case, every pair V(tip) - V(ground) is scored with compare_epc90133_fig9.evaluate_case (unchanged
Fig. 9 metric definitions and bandwidths). Tips: Q2.D (the present observable's tip), Q1.S2, Q1.S46. Grounds: Q2.S46
(circuit ground, the present observable), Q2.S2, Ci1-7.GND, Cm1-10.GND, U80.GND, and the means over Ci and over Cm.
The extraction has no J33 terminals, so these pairs bracket, not reproduce, EPC's probe connection.
Output: results/gan/epc90133-probe-reference.json.

Shape metrics (added 8 October 2026 after an external review, before the J33 run; applied identically to Fig. 9's
digitized traces and to every simulated pair, ideal observation, no bandwidth filter), times from the 50 % crossing
of each edge, levels relative to that edge's settled low level (the Fig. 9 metric definitions):
* pre_edge_V: rising-edge level 1.0 ns before the 50 % crossing minus the reverse-conduction plateau (median over
  -8 to -4 ns); a shelf before the edge shows as a large value;
* falling plateau_V: median level 5.0-7.0 ns after the falling 50 % crossing (dead-time reverse conduction);
* falling dip_below_plateau_V: plateau_V minus the minimum over 0-5 ns, i.e. the oscillatory dip separated from
  the dead-time plateau (the Fig. 9 undershoot metric mixes the two).
The ring damping ratio is reported per pair from the Fig. 9 fit; it is not assumed independent of location.
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

TIPS = ("q2_d", "q1_s2", "q1_s46", "j33_sw")


def _cross(t, v, lev, rising):
    s_ = np.sign(v - lev)
    for i in np.where(np.diff(s_) != 0)[0]:
        if (v[i + 1] > v[i]) == rising:
            return t[i] + (lev - v[i]) * (t[i + 1] - t[i]) / (v[i + 1] - v[i])
    return None


def _settled(t, v, tc, rising):
    pre = v[(t > tc - 45e-9) & (t < tc - 25e-9)]
    post = v[(t > tc + 25e-9) & (t < tc + 45e-9)]
    lo, hi = (np.median(pre), np.median(post)) if rising else (np.median(post), np.median(pre))
    return lo, hi


def shape(t, v, rising):
    """Shape metrics of the module docstring; None when a window is not covered."""
    tc = _cross(t, v, 0.5 * (v.min() + v.max()), rising)
    if tc is None:
        return None
    lo, hi = _settled(t, v, tc, rising)
    tc = _cross(t, v, 0.5 * (lo + hi), rising)
    if tc is None:
        return None
    w = lambda a, b: v[(t >= tc + a) & (t <= tc + b)] - lo
    if rising:
        plat = w(-8e-9, -4e-9)
        if not len(plat):
            return None
        return {"pre_edge_V": float(np.interp(tc - 1e-9, t, v) - lo - np.median(plat))}
    plat, early = w(5e-9, 7e-9), w(0.0, 5e-9)
    if not len(plat) or not len(early):
        return None
    return {"plateau_V": float(np.median(plat)), "dip_below_plateau_V": float(np.median(plat) - early.min())}


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
        grounds = (["0", "q2_s2", "u80_gnd"] + (["j33_gnd"] if "j33_gnd" in sig else [])
                   + sorted(k for k in sig if k.endswith("_gnd") and k[:2] in ("ci", "cm")))
        for grp in ("ci", "cm"):
            ks = [k for k in sig if k.startswith(grp) and k.endswith("_gnd")]
            sig[f"mean_{grp}_gnd"] = {ev: np.mean([sig[k][ev] for k in ks], axis=0) for ev in ("rising", "falling")}
            grounds.append(f"mean_{grp}_gnd")
        rows = {}
        for tip in [t_ for t_ in TIPS if t_ in sig]:
            for g in grounds:
                pseudo = {"traces": {"step_s": tr["step_s"], "start_s": tr["start_s"],
                                     **{f"{ev}_V": list(sig[tip][ev] - sig[g][ev]) for ev in ("rising", "falling")}},
                          "usable": case.get("usable"), "checks": case.get("checks"),
                          "interpretation_invalid": case.get("interpretation_invalid")}
                ev = cmp.evaluate_case(pseudo, fig9, meas)
                bw = ev.get("bandwidths", {})
                pick = {}
                for key in ("none", "1000MHz"):
                    m = (bw.get(key) or {}).get("metrics") or {}
                    r_, f_ = m.get("rising") or {}, m.get("falling") or {}
                    pick[key] = {"rise_s": r_.get("edge_10_90_s"), "overshoot_V": r_.get("overshoot_above_settled_V"),
                                 "ring_Hz": r_.get("ring_frequency_Hz"), "zeta": r_.get("ring_damping_ratio"),
                                 "fall_s": f_.get("edge_10_90_s"), "undershoot_V": f_.get("undershoot_below_settled_V")}
                tt = tr["start_s"] + tr["step_s"] * np.arange(n)
                for ev in ("rising", "falling"):
                    pick["none"][f"{ev}_shape"] = shape(tt, sig[tip][ev] - sig[g][ev], ev == "rising")
                rows[f"{tip}-{g}"] = pick
                p = pick["none"]
                if all(p[k] is not None for k in ("overshoot_V", "undershoot_V", "rise_s")):
                    print(f"{name:22s} {tip:7s} - {g:13s} os {p['overshoot_V']:5.1f} V  us {p['undershoot_V']:4.1f} V  "
                          f"tr {p['rise_s'] * 1e9:4.2f} ns  f {(p['ring_Hz'] or 0) / 1e6:4.0f} MHz  zeta {(p['zeta'] or 0):.3f}")
        out[name] = {"usable": case.get("usable"), "pairs": rows}
    meas_row = {"overshoot_V": meas["rising"]["overshoot_above_settled_V"],
                "undershoot_V": meas["falling"]["undershoot_below_settled_V"]}
    for ev in ("rising", "falling"):
        d = np.array(fig9["panels"][ev]["metrics"]["trace_rel_s_V"])
        meas_row[f"{ev}_shape"] = shape(d[:, 0], d[:, 1], ev == "rising")
    print("Fig. 9 shape", meas_row["rising_shape"], meas_row["falling_shape"])
    args.output.write_text(json.dumps({
        "schema": "epc90133-probe-reference/1", "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "inputs": {str(args.report): hashlib.sha256(args.report.read_bytes()).hexdigest(),
                   str(args.fig9): hashlib.sha256(args.fig9.read_bytes()).hexdigest()},
        # Imported comparison/digitizer code bound 9 October 2026 (audit); the J33 report of 8 October omits it.
        "modules": {m: hashlib.sha256((ROOT / m).read_bytes()).hexdigest()
                    for m in ("scripts/compare_epc90133_fig9.py", "scripts/digitize_epc90133_qsg_fig9.py")},
        "measured": meas_row, "cases": out}, indent=1) + "\n")


if __name__ == "__main__":
    main()
