#!/usr/bin/env python3
"""Score a layout candidate against the owner's "outperforms stock" rule (plans/goal-targets-2026-10-08.md).

Written 10 October 2026 before any K1 switching result existed. Vendor model, assumed 50 pH, G network, nominal 48 V,
both drivers (ramp-Ls50, step-Ls50). Metrics are the goals assessor's. For each driver, the relative change against
stock of: S1 peak voltage, S2 overshoot, S3 settling, S6 Q1 peak current and di/dt, S10 Eon + Eoff, S12 FET loss
(efficiency follows it), S4 rise/fall time, and the S8 quantity (Q2 gate peak during the rise).
* rule as declared: every no-worse quantity <= +0.5 %, rise/fall <= +10 %, Q2 gate peak <= -10 % (verdict kept);
* amended rule (owner, post-result): the same with settling allowed up to +5 %.
Both drivers must pass. A missing or unusable case makes the verdict undetermined. The verdict is provisional until
the declared 50 ps check of the deciding cases agrees. Output: --output JSON and a printed table.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from assess_epc90133_goals import metrics  # noqa: E402

DRIVERS = ("ramp-Ls50", "step-Ls50")
NO_WORSE = ("vpk_V", "overshoot_V", "settling_s", "id_peak_A", "didt_A_per_ns", "eon_eoff_J", "fet_loss_W")
EDGES = ("tr_s", "tf_s")
GAIN = "q2_gate_peak_V"
RULES = {"declared": {"default": 0.5, "settling_s": 0.5}, "amended": {"default": 0.5, "settling_s": 5.0}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("candidate", help="design name in the candidate report, e.g. K1")
    ap.add_argument("report", type=Path)
    ap.add_argument("--stock", type=Path, default=ROOT / "results/gan/epc90133-goals-G.json")
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    cr, sr = (json.loads(p.read_text(encoding="utf-8")) for p in (a.report, a.stock))
    vin = cr["conditions"]["VIN"]
    if sr["conditions"]["VIN"] != vin:
        raise SystemExit("reports differ in VIN")
    rel, ok = {}, True
    for d in DRIVERS:
        c, s = metrics(cr["cases"].get(f"{a.candidate}@{d}-gear"), vin), metrics(sr["cases"].get(f"stock@{d}-gear"), vin)
        if c is None or s is None:
            ok = False
            continue
        rel[d] = {k: 100 * (c[k] / s[k] - 1) for k in NO_WORSE + EDGES + (GAIN,)}
        rel[d]["values"] = {"candidate": c, "stock": s}
    verdicts = {}
    for name, lim in RULES.items():
        if not ok:
            verdicts[name] = {"pass": None, "reason": "missing or unusable case"}
            continue
        fails = [f"{d}:{k} {rel[d][k]:+.2f} %" for d in DRIVERS for k in NO_WORSE if rel[d][k] > lim.get(k, lim["default"])]
        fails += [f"{d}:{k} {rel[d][k]:+.2f} %" for d in DRIVERS for k in EDGES if rel[d][k] > 10.0]
        fails += [f"{d}:{GAIN} {rel[d][GAIN]:+.2f} % (needs <= -10 %)" for d in DRIVERS if rel[d][GAIN] > -10.0]
        verdicts[name] = {"pass": not fails, "failures": fails}
    out = {"schema": "epc90133-outperform/1", "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "inputs": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (a.report, a.stock)},
           "candidate": a.candidate, "relative_change_pct": rel, "verdicts": verdicts,
           "note": "provisional until the declared 50 ps check of the deciding cases agrees"}
    a.output.write_text(json.dumps(out, indent=1, default=float) + "\n", encoding="utf-8")
    for d in rel:
        print(d, {k: round(v, 2) for k, v in rel[d].items() if k != "values"})
    for n, v in verdicts.items():
        print(n, v)


if __name__ == "__main__":
    main()
