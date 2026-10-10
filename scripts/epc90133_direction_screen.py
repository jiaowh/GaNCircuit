#!/usr/bin/env python3
"""Direction screen (exhaustive improvement search, stage 1; declared in plans/goal-targets-2026-10-08.md).

make: write synthetic network reports from a G extraction, one per direction. A direction scales one branch group by
congruence, L' = D L D with D = sqrt(s) on the group's rows and columns: the group's self inductances scale by s,
every coupling coefficient is unchanged and positive definiteness is kept. RPOW directions scale the diagonal
resistance of the power branches instead. Files go to results/gan/direction-screen/<name>.json (numbers only).

    python scripts/epc90133_direction_screen.py make [--base <G json>] [--prefix D]
    python scripts/epc90133_direction_screen.py score <goals report> [...] --reference stock --output <json>
"""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
OUT = ROOT / "results/gan/direction-screen"
BASE = ROOT / "vendor/epc/epc90133/reconstruction/export/stock/extraction/G-m1-mid-stock.json"
CAPS = [f"ci{k}" for k in range(1, 8)] + [f"cm{k}" for k in range(1, 11)]
GROUPS = {
    "VIN": [f"{c}_vin" for c in CAPS],
    "GND": [f"{c}_gnd" for c in CAPS] + ["q2_s2"],
    "SW": ["q1_s2", "q1_s46"],
    "CM": [f"cm{k}_{n}" for k in range(1, 11) for n in ("vin", "gnd")],
    "DRV1": ["r80_g", "r81_g", "u80_ugh", "u80_ugl", "u80_ph"],
    "DRV2": ["r82_g", "r83_g", "u80_lgh", "u80_lgl", "u80_gnd"],
}
POWER = GROUPS["VIN"] + GROUPS["GND"] + GROUPS["SW"]
FACTORS = (0.6, 1.5)
R_FACTORS = (2.0, 4.0)


def directions():
    out = {}
    for g in GROUPS:
        for s in FACTORS:
            out[f"{g}x{s:g}".replace(".", "p")] = ("L", GROUPS[g], s)
    for s in R_FACTORS:
        out[f"RPOWx{s:g}".replace(".", "p")] = ("R", POWER, s)
    return out


def make(base_path, prefix):
    base = json.loads(base_path.read_text(encoding="utf-8"))
    names = [p["name"] for p in base["ports"]]
    L0, R0 = np.array(base["L_H"]), np.array(base["R_ohm"])
    sha = hashlib.sha256(base_path.read_bytes()).hexdigest()
    OUT.mkdir(parents=True, exist_ok=True)
    made = {}
    for d, (kind, group, s) in directions().items():
        idx = [names.index(n) for n in group]
        rep = copy.deepcopy(base)
        if kind == "L":
            dv = np.ones(len(names))
            dv[idx] = np.sqrt(s)
            L = dv[:, None] * L0 * dv[None, :]
            if np.linalg.eigvalsh((L + L.T) / 2).min() <= 0:
                raise SystemExit(f"{d}: not positive definite")
            rep["L_H"] = L.tolist()
        else:
            R = R0.copy()
            R[idx, idx] *= s
            rep["R_ohm"] = R.tolist()
        rep["case"] = f"{prefix}{d}"
        rep["direction_screen"] = {"base": str(base_path.relative_to(ROOT)), "base_sha256": sha, "kind": kind,
                                   "group": group, "factor": s,
                                   "note": "synthetic sensitivity network, not a geometry or extraction"}
        for k in ("evidence_directory",):
            rep.pop(k, None)
        path = OUT / f"{prefix}{d}.json"
        path.write_text(json.dumps(rep) + "\n", encoding="utf-8")
        made[f"{prefix}{d}"] = str(path.relative_to(ROOT))
    print(" ".join(f"{k}={v}" for k, v in made.items()))
    return made


def score(reports, reference, output):
    from assess_epc90133_outperform import DRIVERS, NO_WORSE, EDGES
    from assess_epc90133_goals import metrics
    cases = {}
    for r in reports:
        cases.update(json.loads(Path(r).read_text(encoding="utf-8"))["cases"])
    keys = NO_WORSE + EDGES + ("q2_gate_peak_V",)
    designs = sorted({k.split("@")[0] for k in cases})
    out = {"schema": "epc90133-direction-screen-score/1", "reference": reference,
           "reports": {r: hashlib.sha256(Path(r).read_bytes()).hexdigest() for r in reports}, "relative": {}}
    for d in designs:
        row = {}
        for a in DRIVERS:
            c, ref = cases.get(f"{d}@{a}-gear"), cases.get(f"{reference}@{a}-gear")
            if not c or not ref or not c.get("usable") or not ref.get("usable"):
                row[a] = None
                continue
            m, mr = metrics(c, 48), metrics(ref, 48)
            row[a] = {k: (m[k] / mr[k] - 1) if m.get(k) is not None and mr.get(k) else None for k in keys}
        out["relative"][d] = row
        print(d, {a: ({k: f"{v * 100:+.2f}" for k, v in r_.items() if v is not None} if r_ else None)
                  for a, r_ in row.items()})
    Path(output).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("make", "score"))
    ap.add_argument("reports", nargs="*")
    ap.add_argument("--base", type=Path, default=BASE)
    ap.add_argument("--prefix", default="D")
    ap.add_argument("--reference", default="stock")
    ap.add_argument("--output", type=Path)
    a = ap.parse_args()
    if a.action == "make":
        make(a.base, a.prefix)
    else:
        score(a.reports, a.reference, a.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
