#!/usr/bin/env python3
"""Linear mixes of screen directions (exhaustive improvement search, stage 1; plans/goal-targets-2026-10-08.md).

Directions: the per-group congruence directions of the direction screen (each factor a separate direction, weight
0-1 = fraction of that change), plus the measured K2 and V8 changes and the uniform board-L scales x0.9 / x1.1.
Linear superposition is a screening assumption (as in the 10 October trade-off screen): an infeasible result means
no mix of these directions passes to first order, not that no layout can.

Questions, all under both drivers: (a) amended outperform rule (no-worse quantities <= +0.5 %, settling <= +5 %,
rise/fall <= +10 %, Q2 gate peak <= -10 %); (b) overshoot -10 % with the rest of (a) except the gate peak; (c) Eon+Eoff
-10 % likewise; (d) the best Q2 gate peak with (a)'s other limits; (e) the best of each quantity with (a)'s other
limits, gate-peak rule dropped.

    python scripts/epc90133_direction_mix.py --score results/gan/epc90133-direction-screen-score.json --output <json>
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from assess_epc90133_goals import metrics  # noqa: E402

DRIVERS = ("ramp-Ls50", "step-Ls50")
KEYS = ("vpk_V", "overshoot_V", "settling_s", "id_peak_A", "didt_A_per_ns", "eon_eoff_J", "fet_loss_W", "tr_s", "tf_s",
        "q2_gate_peak_V")
LIMIT = {k: 0.005 for k in KEYS}
LIMIT.update({"settling_s": 0.05, "tr_s": 0.10, "tf_s": 0.10})


def rel(c, r):
    m, mr = metrics(c, 48), metrics(r, 48)
    return {k: m[k] / mr[k] - 1 for k in KEYS}


def measured():
    """K2, V8 and uniform L scales against stock from saved reports."""
    G = json.loads((ROOT / "results/gan/epc90133-goals-G.json").read_text(encoding="utf-8"))["cases"]
    K2 = json.loads((ROOT / "results/gan/epc90133-goals-G-K2.json").read_text(encoding="utf-8"))["cases"]
    out = {}
    for name, src, fmt in (("K2", K2, "K2@{a}-gear"), ("V8", G, "V8@{a}-gear"), ("Lx0p9", G, "stock@{a}-gear-l0.9"),
                           ("Lx1p1", G, "stock@{a}-gear-l1.1")):
        out[name] = {a: rel(src[fmt.format(a=a)], G[f"stock@{a}-gear"]) for a in DRIVERS}
    return out


def group(n):
    """Directions of one group share a budget: at most one full change, in one direction."""
    if n.startswith("D") and "x" in n:
        return n[1:].split("x")[0]
    if n.startswith("Lx"):
        return "L"
    return n


def solve(dirs, objective, extra, drop=()):
    names = list(dirs)
    A, b = [], []
    for g in sorted({group(n) for n in names}):
        A.append([1.0 if group(n) == g else 0.0 for n in names])
        b.append(1.0)
    for a in DRIVERS:
        for k in KEYS:
            if k in drop:
                continue
            lim = extra.get(k, LIMIT[k])
            A.append([dirs[n][a][k] for n in names])
            b.append(lim)
    c = np.zeros(len(names))
    if objective:
        key, drv = objective
        for a in (DRIVERS if drv == "max" else (drv,)):
            c += np.array([dirs[n][a][key] for n in names])
    r = linprog(c, A_ub=np.array(A), b_ub=np.array(b), bounds=[(0, 1)] * len(names), method="highs")
    if r.status != 0:
        return {"feasible": False}
    w = {n: float(x) for n, x in zip(names, r.x) if x > 1e-6}
    res = {a: {k: float(sum(r.x[i] * dirs[n][a][k] for i, n in enumerate(names))) for k in KEYS} for a in DRIVERS}
    return {"feasible": True, "weights": w, "result": res}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--score", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    sc = json.loads(a.score.read_text(encoding="utf-8"))["relative"]
    dirs = {d: v for d, v in sc.items() if d != "stock" and all(v.get(x) for x in DRIVERS)}
    dirs.update(measured())
    out = {"schema": "epc90133-direction-mix/2", "directions": dirs, "questions": {}, "questions_with_rpow": {}}
    for label, use in (("questions", {k: v for k, v in dirs.items() if not k.startswith("DRPOW")}),
                       ("questions_with_rpow", dirs)):
        print("==", label)
        ask(use, out[label])
    a.output.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    return 0


def ask(dirs, q):
    q["a_amended_rule"] = solve(dirs, None, {"q2_gate_peak_V": -0.10})
    q["b_overshoot_-10"] = solve(dirs, None, {"overshoot_V": -0.10}, drop=())
    q["c_eon_eoff_-10"] = solve(dirs, None, {"eon_eoff_J": -0.10})
    q["d_best_gate_peak"] = solve(dirs, ("q2_gate_peak_V", "max"), {})
    for k in KEYS:
        q[f"e_best_{k}"] = solve(dirs, (k, "max"), {}, drop=(k,))
    for name, r in q.items():
        if not r["feasible"]:
            print(f"{name:26s} infeasible")
            continue
        best = {d: {k: f"{v * 100:+.1f}" for k, v in r["result"][d].items()} for d in DRIVERS}
        tag = name.split("best_")[-1] if "best_" in name else None
        summary = {d: best[d][tag] for d in DRIVERS} if tag in KEYS else ""
        print(f"{name:26s} feasible {summary} weights { {k: round(v, 2) for k, v in r['weights'].items()} }")


if __name__ == "__main__":
    raise SystemExit(main())
