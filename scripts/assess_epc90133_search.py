#!/usr/bin/env python3
"""Assess the layout search's switching runs (epc90133_switching.py --study search) by the owner's rule.

Rules fixed on 7 October 2026 with plans/layout-search-2026-10-07.md, before any search switching run. Every case is
compared with 'stock' (stock through the same KiCad route, same extraction variant) under the same alternative:

* C0 overshoot: not higher than stock's under any of the four alternatives, and the worst case over the four lower
  than stock's worst case (overshoot is the single objective);
* C1 FET loss (estimator revision 2, settled) at most 5 % above stock's under every alternative;
* C2 Q2 gate peak during the rise not above stock's under every alternative;
* N numerical check: the candidate's worst-case alternative rerun at 50 ps (case <NAME>@<alt>-gear-ms50, added on
  request) within 2 % of 100 ps on overshoot, FET loss and Q2 gate peak; without it the verdict is 'provisional'.
A missing or unusable case makes the candidate 'undetermined'. Verdict 'found' = C0, C1, C2 and N pass; the loop
inductance rule (more than 4 % lower than stock in the same variant) is checked in the export report, not here.
Output: results/gan/epc90133-search-assessment.json.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from assess_epc90133_design import metrics

ALTS = ("ramp-Ls0", "step-Ls0", "ramp-Ls50", "step-Ls50")
KEYS = ("overshoot_V", "fet_loss_W", "q2_gate_peak_V")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reports", nargs="+", type=Path)
    ap.add_argument("--suffix", default="-gear", help="case suffix; '-gear-qg' for the gate-charge check (7 October 2026)")
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-search-assessment.json")
    args = ap.parse_args()
    cases = {}
    for r in args.reports:
        rep = json.loads(r.read_text(encoding="utf-8"))
        if rep.get("study") != "search":
            raise SystemExit(f"{r} is not a search report")
        cases.update(rep["cases"])
    m = {k: metrics(c) for k, c in cases.items()}
    names = sorted({k.split("@")[0] for k in cases} - {"stock"})
    out = {}
    for n in names:
        rows, ok = {}, True
        for a in ALTS:
            s, c = m.get(f"stock@{a}{args.suffix}"), m.get(f"{n}@{a}{args.suffix}")
            if not s or not c or any(s[k] is None or c[k] is None for k in KEYS):
                rows[a] = None
                ok = None if ok is not False else False
                continue
            rows[a] = {"stock": {k: s[k] for k in KEYS}, "candidate": {k: c[k] for k in KEYS},
                       "overshoot_change_pct": 100 * (c["overshoot_V"] / s["overshoot_V"] - 1),
                       "loss_change_pct": 100 * (c["fet_loss_W"] / s["fet_loss_W"] - 1),
                       "q2_change_V": c["q2_gate_peak_V"] - s["q2_gate_peak_V"],
                       "C0_not_higher": c["overshoot_V"] <= s["overshoot_V"],
                       "C1": c["fet_loss_W"] <= 1.05 * s["fet_loss_W"],
                       "C2": c["q2_gate_peak_V"] <= s["q2_gate_peak_V"]}
        full = all(rows[a] for a in ALTS)
        res = {"alternatives": rows}
        if full:
            ws = max(rows[a]["stock"]["overshoot_V"] for a in ALTS)
            wa = max(ALTS, key=lambda a: rows[a]["candidate"]["overshoot_V"])
            wc = rows[wa]["candidate"]["overshoot_V"]
            res.update({"worst_case_stock_V": ws, "worst_case_candidate_V": wc, "worst_alternative": wa,
                        "C0": wc < ws and all(rows[a]["C0_not_higher"] for a in ALTS),
                        "C1": all(rows[a]["C1"] for a in ALTS), "C2": all(rows[a]["C2"] for a in ALTS)})
            h, f = m.get(f"{n}@{wa}{args.suffix}"), m.get(f"{n}@{wa}{args.suffix}-ms50")
            res["N"] = None if not f else all(abs(f[k] / h[k] - 1) <= 0.02 for k in KEYS)
            rule = res["C0"] and res["C1"] and res["C2"]
            res["verdict"] = ("not met" if not rule else "found" if res["N"] else
                              "provisional (numerical check missing)" if res["N"] is None else "not met (numerical)")
        else:
            res["verdict"] = "undetermined"
        out[n] = res
        print(n, res["verdict"], {a: None if not rows[a] else (round(rows[a]["overshoot_change_pct"], 1),
                                                              round(rows[a]["loss_change_pct"], 2),
                                                              round(rows[a]["q2_change_V"], 3)) for a in ALTS})
    args.output.write_text(json.dumps({"schema": "epc90133-search-assessment/1",
                                       "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                       "inputs": {str(r): hashlib.sha256(r.read_bytes()).hexdigest() for r in args.reports},
                                       "candidates": out}, indent=1) + "\n")


if __name__ == "__main__":
    main()
