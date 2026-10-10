#!/usr/bin/env python3
"""Trade-off screen of saved EPC90133 switching results against the owner's "outperforms stock" rule.

Declared 10 October 2026 before its runs (plans/goal-targets-2026-10-08.md, "Trade-off screen"). No solver: reads
saved goals reports (vendor model, assumed 50 pH, G network, 48 V nominal) and scores them with the goals
assessor's metric function. For each saved DIRECTION (a change applied to stock) it records the relative change of
every rule quantity against stock under both drivers, then solves linear programs over non-negative mixes of the
directions within their tested ranges:
  (a) feasibility of the rule: every no-worse quantity <= +0.5 %, rise/fall time <= +10 % (S4), Q2 gate peak <= -10 %;
  (b) the largest Q2 gate-peak reduction, and the largest improvement of each other quantity, with the rest no worse.
Linear superposition of separately simulated changes is a SCREENING assumption: an infeasible result means no mix of
these directions passes to first order, not that no layout can. Uniform board-inductance scaling is not a layout; it
brackets power-loop geometry. The ideal low-side gate stage brackets gate-return geometry. The +135 pF switch-node
capacitance direction is reported, not mixed (no removable copper is identified and it is a different bench
condition). Output: results/gan/epc90133-tradeoff-screen.json and a printed table.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from assess_epc90133_goals import metrics  # noqa: E402

RES = ROOT / "results/gan"
VIN = 48.0
DRIVERS = ("ramp-Ls50", "step-Ls50")
NO_WORSE = ("vpk_V", "overshoot_V", "settling_s", "id_peak_A", "didt_A_per_ns", "eon_eoff_J", "fet_loss_W")
EDGES = ("tr_s", "tf_s")
GAIN = "q2_gate_peak_V"
LIMIT, EDGE_LIMIT, GAIN_TARGET = 0.5, 10.0, -10.0
REPORTS = {"G": "epc90133-goals-G.json", "bound": "epc90133-goals-G-bound.json", "ctlls50": "epc90133-goals-G-ctlls50.json",
           "ds": "epc90133-goals-G-ds.json", "ds_ctlls": "epc90133-goals-G-ds-ctlls.json", "csw": "epc90133-goals-G-V8d075-csw.json"}
# name: (report, case pattern, reference report, reference pattern, mix range or None if reported only)
DIRECTIONS = {
    "L x0.9": ("G", "stock@{a}-gear-l0.9", "G", "stock@{a}-gear", (0, 2.5)),
    "L x1.1": ("G", "stock@{a}-gear-l1.1", "G", "stock@{a}-gear", (0, 2.5)),
    "V8": ("G", "V8@{a}-gear", "G", "stock@{a}-gear", (0, 1)),
    "ideal low-side gate (vendor)": ("ctlls50", "stock@{a}-gear-ctlls", "G", "stock@{a}-gear", (0, 1)),
    "L x0.75": ("bound", "stock@{a}-gear-l0.75", "G", "stock@{a}-gear", None),
    "L x1.25": ("bound", "stock@{a}-gear-l1.25", "G", "stock@{a}-gear", None),
    "ideal low-side gate (EPC2302DS)": ("ds_ctlls", "stock@{a}-gear-ctlls-ds", "ds", "stock@{a}-gear-ds", None),
    "+135 pF switch-node C": ("csw", "stock@{a}-gear-csw", "G", "stock@{a}-gear", None),
}


def main():
    cases = {k: json.loads((RES / f).read_text(encoding="utf-8"))["cases"] for k, f in REPORTS.items()}
    keys = NO_WORSE + EDGES + (GAIN,)
    rel = {}
    for name, (rep, pat, rrep, rpat, _) in DIRECTIONS.items():
        rel[name] = {}
        for a in DRIVERS:
            c, s = metrics(cases[rep][pat.format(a=a)], VIN), metrics(cases[rrep][rpat.format(a=a)], VIN)
            if c is None or s is None:
                raise SystemExit(f"{name} {a}: unusable case")
            rel[name][a] = {k: 100 * (c[k] / s[k] - 1) for k in keys}
    mix = [n for n, d in DIRECTIONS.items() if d[4]]
    bounds = [DIRECTIONS[n][4] for n in mix]

    def lp(target, bound):
        """Maximise the improvement t of `target` (both drivers) with every other quantity within the rule."""
        A, b = [], []
        for a in DRIVERS:
            for k in NO_WORSE + (GAIN,):
                if k != target:
                    A.append([rel[n][a][k] for n in mix] + [0]); b.append(LIMIT if k != GAIN else bound)
            for k in EDGES:
                A.append([rel[n][a][k] for n in mix] + [0]); b.append(EDGE_LIMIT)
            A.append([rel[n][a][target] for n in mix] + [1]); b.append(0)
        r = linprog([0] * len(mix) + [-1], A_ub=A, b_ub=b, bounds=bounds + [(None, None)])
        if r.status != 0:
            return None
        x = r.x[:-1]
        return {"improvement_pct": float(r.x[-1]), "mix": dict(zip(mix, map(float, x))),
                "changes_pct": {a: {k: float(sum(rel[n][a][k] * x[i] for i, n in enumerate(mix))) for k in keys}
                                for a in DRIVERS}}

    best = {k: lp(k, 1e9) for k in NO_WORSE + (GAIN,)}
    gain = best[GAIN]
    feasible = gain is not None and gain["improvement_pct"] >= -GAIN_TARGET
    out = {"schema": "epc90133-tradeoff-screen/1", "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "inputs": {f: hashlib.sha256((RES / f).read_bytes()).hexdigest() for f in REPORTS.values()},
           "rule": {"no_worse_pct": LIMIT, "edge_pct": EDGE_LIMIT, "q2_gate_peak_pct": GAIN_TARGET, "drivers": DRIVERS},
           "directions_pct": rel, "mixed": mix, "ranges": dict(zip(mix, bounds)),
           "rule_feasible_linear": feasible, "best_with_rest_no_worse": best,
           "assumption": "linear superposition of separately simulated changes (screen, not a design)"}
    (RES / "epc90133-tradeoff-screen.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    for a in DRIVERS:
        print(f"== {a} (% change against stock)\n{'':32s}" + "".join(f"{k[:9]:>10s}" for k in keys))
        for n in rel:
            print(f"{n:32s}" + "".join(f"{rel[n][a][k]:10.2f}" for k in keys))
    print("rule feasible (linear screen):", feasible)
    for k, v in best.items():
        print(f"best {k:16s} {v['improvement_pct']:5.1f} %  mix {({n: round(x, 2) for n, x in v['mix'].items() if x > 1e-3})}")


if __name__ == "__main__":
    main()
