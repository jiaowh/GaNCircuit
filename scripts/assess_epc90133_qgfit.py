#!/usr/bin/env python3
"""Assess the gate-charge sensitivity study (epc90133_switching.py --study qgfit).

Rules fixed on 7 October 2026 with the study's declaration, before any qgfit run.

For each model (vendor EPC2302, variant EPC2302QG) and each of the four alternatives, R80-1.5 is
compared with stock under the same model, method and run:

* overshoot change (V and %), FET loss change (%), Q2 gate peak change (V);
* C1: R80-1.5 FET loss at most 1.05 x stock's; C2: R80-1.5 Q2 gate peak not above stock's
  (the owner's rule of 5 October); a missing or unusable case makes that alternative undetermined;
* per model: 'meets' if C1 and C2 hold under all four alternatives, 'not met' if any fails,
  otherwise 'undetermined'.

Numerical check: R80-1.5@step-Ls50-gear-qg-ms50 against R80-1.5@step-Ls50-gear-qg, overshoot, FET
loss and Q2 gate peak within 2 %; if it fails, the variant's step-Ls50 alternative is undetermined.

Reported without pass/fail: the variant's effect on stock (overshoot, rise and fall time, Eon+Eoff,
FET loss, vendor -> variant), and the vendor Gear cases against the stored round-1/round-3 values of
the same design and alternative (a consistency control; differences above 2 % are flagged).

Reading, fixed now:
* both models 'meets': the R80 1.5 ohm decision does not depend on the Fig. 7 discrepancy within
  these models; an E4 prediction should carry both models' values as the range over the unresolved
  gate charge;
* variant 'not met' or 'undetermined': the decision depends on gate charge; measuring gate charge
  (hardware plan E7) should precede freezing the E4 prediction. No new resistor search follows
  automatically.
Neither reading says which gate-charge curve describes the real device.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from assess_epc90133_design import metrics

REPORT = ROOT / "results/gan/epc90133-qgfit.json"
OUTPUT = ROOT / "results/gan/epc90133-qgfit-assessment.json"
STORED = [ROOT / f"results/gan/{n}.json" for n in (
    "epc90133-design-round1-rev2", "epc90133-design-round1-rev2-cont", "epc90133-design-round1-rev2-gear",
    "epc90133-design-round1-rev2-gear2", "epc90133-design-round3", "epc90133-design-round3-gear-a",
    "epc90133-design-round3-gear-b")]
ALTS = ("ramp-Ls50", "step-Ls50", "ramp-Ls0", "step-Ls0")
MODELS = {"vendor": "", "variant": "-qg"}
CHECK_KEYS = ("overshoot_V", "fet_loss_W", "q2_gate_peak_V")


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(a, b):
    return None if a is None or b is None or not a else b / a - 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", type=Path, default=REPORT)
    ap.add_argument("--output", type=Path, default=OUTPUT)
    args = ap.parse_args()
    rep = json.loads(args.report.read_text(encoding="utf-8"))
    if rep.get("study") != "qgfit":
        raise SystemExit("not a qgfit report")
    cases = rep["cases"]
    m = {k: metrics(c) for k, c in cases.items()}

    check = None
    a_, b_ = m.get("R80-1.5@step-Ls50-gear-qg"), m.get("R80-1.5@step-Ls50-gear-qg-ms50")
    if a_ and b_:
        d = {k: rel(a_[k], b_[k]) for k in CHECK_KEYS}
        check = {"relative_change": d, "pass": all(v is not None and abs(v) <= 0.02 for v in d.values())}

    out = {"models": {}, "variant_effect_on_stock": {}, "vendor_consistency_with_stored": {}}
    for model, sfx in MODELS.items():
        rows, verdicts = {}, []
        for a in ALTS:
            s, c = m.get(f"stock@{a}-gear{sfx}"), m.get(f"R80-1.5@{a}-gear{sfx}")
            if model == "variant" and a == "step-Ls50" and not (check and check["pass"]):
                c = None
            if not s or not c:
                rows[a] = {"verdict": "undetermined", "reason": "case missing, unusable or numerical check failed"}
                verdicts.append(None)
                continue
            c1 = None if s["fet_loss_W"] is None or c["fet_loss_W"] is None else c["fet_loss_W"] <= 1.05 * s["fet_loss_W"]
            c2 = c["q2_gate_peak_V"] <= s["q2_gate_peak_V"]
            ok = None if c1 is None else (c1 and c2)
            verdicts.append(ok)
            rows[a] = {"stock": s, "R80-1.5": c,
                       "overshoot_change_V": c["overshoot_V"] - s["overshoot_V"],
                       "overshoot_change_pct": 100 * rel(s["overshoot_V"], c["overshoot_V"]),
                       "fet_loss_change_pct": None if c1 is None else 100 * rel(s["fet_loss_W"], c["fet_loss_W"]),
                       "q2_gate_peak_change_V": c["q2_gate_peak_V"] - s["q2_gate_peak_V"],
                       "C1_fet_loss_within_5pct": c1, "C2_q2_gate_peak_not_above": c2,
                       "verdict": {True: "meets", False: "not met", None: "undetermined"}[ok]}
        verdict = ("not met" if any(v is False for v in verdicts) else
                   "meets" if all(v is True for v in verdicts) else "undetermined")
        out["models"][model] = {"alternatives": rows, "verdict": verdict}

    for a in ALTS:
        v, q = m.get(f"stock@{a}-gear"), m.get(f"stock@{a}-gear-qg")
        out["variant_effect_on_stock"][a] = None if not v or not q else {
            k: {"vendor": v[k], "variant": q[k], "relative_change": rel(v[k], q[k])}
            for k in ("overshoot_V", "rise_s", "fall_s", "eon_eoff_J", "fet_loss_W", "q2_gate_peak_V")}

    stored = {}
    for p in STORED:
        if p.exists():
            for k, c in json.loads(p.read_text(encoding="utf-8"))["cases"].items():
                if metrics(c):
                    stored.setdefault(k, (p.name, metrics(c)))
    for a in ALTS:
        for d in ("stock", "R80-1.5"):
            new = m.get(f"{d}@{a}-gear")
            old = stored.get(f"{d}@{a}-gear") or stored.get(f"{d}@{a}")
            if new and old:
                diff = {k: rel(old[1][k], new[k]) for k in CHECK_KEYS}
                out["vendor_consistency_with_stored"][f"{d}@{a}"] = {
                    "stored_report": old[0], "relative_change": diff,
                    "flag_above_2pct": any(x is not None and abs(x) > 0.02 for x in diff.values())}

    vv, qv = out["models"]["vendor"]["verdict"], out["models"]["variant"]["verdict"]
    reading = ("decision does not depend on the Fig. 7 discrepancy within these models; carry both models' values "
               "as the range in the E4 prediction" if vv == qv == "meets" else
               "decision depends on gate charge (or is undetermined); measure gate charge (E7) before freezing the "
               "E4 prediction; no automatic resistor search")
    result = {"schema": "epc90133-qgfit-assessment/1", "evaluator_sha256": sha256(__file__),
              "inputs": {args.report.relative_to(ROOT).as_posix(): sha256(args.report)},
              "report_complete": rep.get("complete"), "numerical_check": check, **out,
              "decision_reading": reading,
              "scope": ("Sensitivity within the vendor model and a Fig. 7-following variant. Says nothing about which "
                        "gate-charge curve describes the real EPC2302.")}
    args.output.write_text(json.dumps(result, indent=1) + "\n")
    for model in MODELS:
        print(model, out["models"][model]["verdict"])
        for a, r in out["models"][model]["alternatives"].items():
            if "overshoot_change_pct" in r:
                print(f"  {a:10s} overshoot {r['stock']['overshoot_V']:5.1f} -> {r['R80-1.5']['overshoot_V']:5.1f} V "
                      f"({r['overshoot_change_pct']:+.0f} %), loss {r['fet_loss_change_pct'] if r['fet_loss_change_pct'] is None else round(r['fet_loss_change_pct'], 2)} %, "
                      f"Q2 gate {r['q2_gate_peak_change_V']:+.2f} V -> {r['verdict']}")
            else:
                print(f"  {a:10s} {r['verdict']}")
    print("numerical check", check)
    print(reading)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
