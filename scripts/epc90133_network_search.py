#!/usr/bin/env python3
"""Direct network search (exhaustive improvement search, stage 3; declared in plans/goal-targets-2026-10-08.md).

Composite networks on stock's G network (scripts/epc90133_direction_screen.py compose) with log-uniform factors per
direction; each network simulated directly (ramp/step-Ls50, vendor model, 50 pH) through the unchanged switching bench,
stock rerun in every round. Score: goals met among S1, S2, S3, S4, S6, S7, S8, S10 under both drivers (definitions
below), tiebreak the summed normalised shortfall of failed goals. Round 1: Latin hypercube; later rounds: samples
around the three best so far with the spread halved each round.

    python scripts/epc90133_network_search.py --rounds 4 [--seed 1]
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import epc90133_direction_screen as ds  # noqa: E402
from assess_epc90133_goals import metrics  # noqa: E402

BASE = ROOT / "vendor/epc/epc90133/reconstruction/export/stock/extraction/G-m1-mid-stock.json"
OUTDIR = ROOT / "results/gan/network-search"
ds.OUT = OUTDIR / "networks"  # composite network files of this search
DRIVERS = ("ramp-Ls50", "step-Ls50")
# name: (kind, members, low, high)
PARAMS = {
    "CM": ("L", ds.GROUPS["CM"], 0.6, 1.5), "VIN": ("L", ds.GROUPS["VIN"], 0.6, 1.5),
    "GND": ("L", ds.GROUPS["GND"], 0.6, 1.5), "SW": ("L", ds.GROUPS["SW"], 0.6, 1.5),
    "DRV2": ("L", ds.GROUPS["DRV2"], 0.6, 1.5), "G1P": ("L", ds.GROUPS_1B["G1P"], 0.6, 1.5),
    "PH": ("L", ds.GROUPS_1B["PH"], 0.6, 1.5),
    "CSQ2": ("K", ds.COUPLINGS_1B["CSQ2"], 0.5, 1.5), "CSQ1": ("K", ds.COUPLINGS_1B["CSQ1"], 0.5, 1.25)}
NAMES = list(PARAMS)


def goals(m, s):
    """Per-driver verdicts (m: network metrics, s: stock metrics at the same driver)."""
    return {"S1": m["vpk_V"] <= 80.0,
            "S2": m["overshoot_V"] <= min(0.9 * s["overshoot_V"], 9.6),
            "S3": m["settling_s"] <= s["settling_s"],
            "S4": m["tr_s"] <= 1.1 * s["tr_s"] and m["tf_s"] <= 1.1 * s["tf_s"],
            "S6": m["id_peak_A"] <= s["id_peak_A"] and m["didt_A_per_ns"] <= s["didt_A_per_ns"],
            "S7": m["vgs_max_V"] <= 5.5 and m["vgs_min_V"] >= -3.0,
            "S8": m["q2_gate_peak_V"] < 0.5,
            "S10": m["eon_eoff_J"] <= 0.9 * s["eon_eoff_J"]}


def shortfall(m, s):
    """Normalised shortfall of each goal (0 when met)."""
    sh = lambda v, lim: max(0.0, v / lim - 1)
    return {"S2": sh(m["overshoot_V"], min(0.9 * s["overshoot_V"], 9.6)), "S3": sh(m["settling_s"], s["settling_s"]),
            "S4": max(sh(m["tr_s"], 1.1 * s["tr_s"]), sh(m["tf_s"], 1.1 * s["tf_s"])),
            "S6": max(sh(m["id_peak_A"], s["id_peak_A"]), sh(m["didt_A_per_ns"], s["didt_A_per_ns"])),
            "S8": sh(m["q2_gate_peak_V"], 0.5), "S10": sh(m["eon_eoff_J"], 0.9 * s["eon_eoff_J"])}


def score(cases, name):
    st = {a: cases.get(f"stock@{a}-gear") for a in DRIVERS}
    out = {"verdict": {}, "count": 0, "shortfall": None, "usable": True, "values": {}}
    per = {}
    short = {}
    for a in DRIVERS:
        c = cases.get(f"{name}@{a}-gear")
        if not c or not c.get("usable") or not st[a] or not st[a].get("usable"):
            out["usable"] = False
            return out
        m, s = metrics(c, 48), metrics(st[a], 48)
        out["values"][a] = {k: m[k] for k in ("vpk_V", "overshoot_V", "settling_s", "tr_s", "tf_s", "id_peak_A",
                                              "didt_A_per_ns", "vgs_max_V", "vgs_min_V", "q2_gate_peak_V",
                                              "eon_eoff_J", "fet_loss_W")}
        per[a] = goals(m, s)
        for g, v in shortfall(m, s).items():
            short[g] = max(short.get(g, 0.0), v)
    out["verdict"] = {g: all(per[a][g] for a in DRIVERS) for g in per[DRIVERS[0]]}
    out["count"] = sum(out["verdict"].values())
    out["shortfall"] = sum(v for g, v in short.items() if not out["verdict"].get(g, True))
    return out


def make(name, factors):
    steps = [(PARAMS[p][0], PARAMS[p][1], f) for p, f in factors.items()]
    return ds.compose(BASE, steps, name, "stage 3 network search: " + json.dumps(factors))


def sample_lhs(n, rng):
    u = (np.argsort(rng.random((len(NAMES), n)), axis=1) + rng.random((len(NAMES), n))) / n
    out = []
    for j in range(n):
        out.append({p: float(np.exp(np.log(PARAMS[p][2]) + u[i, j] * (np.log(PARAMS[p][3]) - np.log(PARAMS[p][2]))))
                    for i, p in enumerate(NAMES)})
    return out


def sample_near(centres, n, spread, rng):
    out = []
    for j in range(n):
        c = centres[j % len(centres)]
        f = {}
        for p in NAMES:
            lo, hi = np.log(PARAMS[p][2]), np.log(PARAMS[p][3])
            v = np.log(c[p]) + rng.normal(0, spread * (hi - lo))
            f[p] = float(np.exp(np.clip(v, lo, hi)))
        out.append(f)
    return out


def simulate(ext, only, report, log_path):
    cmd = [sys.executable, str(ROOT / "scripts/epc90133_switching.py"), "--study", "goals", "--jobs", "4",
           "--timeout", "3600", "--ext-file", *ext, "--only", *only, "--output", str(report)]
    with open(log_path, "w") as log:
        subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=dict(os.environ, PYTHONPATH="src"), check=False)


def load_cases(r):
    """Round r's cases, with the retry report (if any) replacing failed cases."""
    cases = {}
    for f in (OUTDIR / f"round{r}.json", OUTDIR / f"round{r}-retry.json"):
        if f.exists():
            cases.update({k: c for k, c in json.loads(f.read_text(encoding="utf-8"))["cases"].items() if c.get("usable")
                          or k not in cases})
    return cases


def retry_failed(r, ext):
    """Round 1 (11 October 2026): the first batch (both stock cases, one network case) hung until the 3,600 s
    timeout while the other 63 ran in about 2 min each. RETROSPECTIVE robustness change: failed cases are rerun once
    (round<r>-retry.json) and replace the failed ones; nothing else is rerun."""
    rep_ = json.loads((OUTDIR / f"round{r}.json").read_text(encoding="utf-8"))
    failed = [k for k, v in rep_.get("runs", {}).items() if v.get("status") != "completed" and "@" in k]
    if not failed:
        return
    names = {k.split("@")[0] for k in failed}
    ext_ = [e for e in ext if e.split("=")[0] in names | {"stock"}]
    print(f"round {r}: retrying {failed}", flush=True)
    simulate(ext_, failed, OUTDIR / f"round{r}-retry.json", ROOT / f"runs/network-search-round{r}-retry.log")


def ext_for(nets):
    ext = [f"stock={BASE}"]
    for name, f in nets.items():
        path = ds.OUT / f"{name}.json"
        try:
            ext.append(f"{name}={path if path.exists() else make(name, f)}")
        except SystemExit as e:
            print("skip", name, e, flush=True)
    return ext


def run_round(r, nets):
    ext = ext_for(nets)
    only = [f"{e.split('=')[0]}@{a}-gear" for e in ext for a in DRIVERS]
    if not (OUTDIR / f"round{r}.json").exists():
        simulate(ext, only, OUTDIR / f"round{r}.json", ROOT / f"runs/network-search-round{r}.log")
    retry_failed(r, ext)
    return load_cases(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--n1", type=int, default=32)
    ap.add_argument("--n", type=int, default=16)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    state_path = OUTDIR / "search.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {"networks": {}, "rounds": []}
    spread = 0.25 / 2 ** max(0, len(state["rounds"]) - 1)
    # Rescore rounds whose stock reference was unusable (round 1, 11 October 2026): retry failed cases, then rescore.
    for rd in state["rounds"]:
        if not rd["stock"]["usable"]:
            nets = {k: v["factors"] for k, v in state["networks"].items() if v["round"] == rd["round"]}
            cases = run_round(rd["round"], nets)
            rd["stock"] = score(cases, "stock")
            for name in nets:
                state["networks"][name]["score"] = score(cases, name)
            rd["rescored"] = True
            state_path.write_text(json.dumps(state, indent=1) + "\n", encoding="utf-8")
            print(f"round {rd['round']} rescored: stock {rd['stock']['count']}", flush=True)
            if not rd["stock"]["usable"]:
                raise SystemExit(f"round {rd['round']}: stock still unusable")
    for r in range(len(state["rounds"]) + 1, a.rounds + 1):
        if r == 1:
            fs = sample_lhs(a.n1, rng)
        else:
            ranked = sorted((v for v in state["networks"].values() if v["score"]["usable"]),
                            key=lambda v: (-v["score"]["count"], v["score"]["shortfall"]))
            if not ranked:
                raise SystemExit(f"round {r}: no usable network to search around")
            fs = sample_near([v["factors"] for v in ranked[:3]], a.n, spread, rng)
            spread /= 2
        nets = {f"N{r}_{k:02d}": f for k, f in enumerate(fs)}
        cases = run_round(r, nets)
        stock = score(cases, "stock")
        for name, f in nets.items():
            state["networks"][name] = {"round": r, "factors": f, "score": score(cases, name)}
        state["rounds"].append({"round": r, "stock": stock, "n": len(nets)})
        state_path.write_text(json.dumps(state, indent=1) + "\n", encoding="utf-8")
        best = sorted((v for v in state["networks"].values() if v["score"]["usable"]),
                      key=lambda v: (-v["score"]["count"], v["score"]["shortfall"]))[:3]
        print(f"round {r}: stock {stock['count']} {stock['verdict']}", flush=True)
        for b in best:
            print("  best", b["score"]["count"], round(b["score"]["shortfall"], 3),
                  {g for g, v in b["score"]["verdict"].items() if v}, {k: round(v, 2) for k, v in b["factors"].items()},
                  flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
