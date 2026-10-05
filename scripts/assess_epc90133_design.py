#!/usr/bin/env python3
"""Apply design round 1's declared robust rule (scripts/epc90133_switching.py, --study design) to its report.

For each design and target, under every alternative (driver form x package source inductance), compare with the
stock design under the same alternative:
  T1 overshoot: candidate <= stock - max(1 V, 10 % of stock);
  T2 Q1 Eon + Eoff: candidate <= stock x 1.02;
  T3 FET loss: candidate <= stock x 1.02 (efficiency not lower beyond the numerical tolerance).
A target is met only if it holds under all four alternatives, and only usable cases (checks passed) count: a
missing or unusable case makes the target 'undetermined' for that design, never met. Also reported (not targets):
Q2 die gate peak during the rise and the falling-edge minimum, each against stock.

Revision 3 (5 October 2026, loss-estimator revision 2): a case whose loss window did not settle has no T3
value (undetermined for that alternative); T1 and T2 are unaffected.

Revision 2 (5 October 2026, after round 1's results): verdict precedence corrected. Revision 1 reported
'undetermined' whenever an alternative was missing, even when another alternative already failed; since a target is
met only if it holds under every alternative, one failure means 'not met' (kept:
results/gan/epc90133-design-round1-assessment-v1-precedence-defect.json). Also, declared before the fix runs: an
alternative whose 100 ps stock or candidate case is unusable (round 1: solver stalls in three timing runs) is
compared using the pair run at 50 ps (stock and candidate both at 50 ps, never mixed steps), when both exist.

Rule 'round3' (--rule round3; owner decision 5 October 2026, plans/layout-round-2-plan.md): overshoot is the single
objective; constraints under all four alternatives: C1 FET loss (settled) at most 5 % above stock's, C2 Q2 die gate
peak during the rise not above stock's. A candidate meeting C1 and C2 under every alternative is ranked by its
worst-case overshoot over the four; 'not met' if any alternative fails, 'undetermined' if one is missing. The
50 ps pair rule above applies unchanged. (C3, admissible changes, holds by construction for part swaps.)
Gear fallback (declared 5 October 2026 before any Gear run; scripts/epc90133_switching.py): where neither the
100 ps pair nor a 50 ps pair is usable, the Gear pair <d>@<a>-gear is used, only if the declared Gear check passes.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def metrics(case):
    if not case or not case.get("usable"):
        return None
    m = case["metrics"]
    a, b, pl = m["event_a_turn_off_at_peak"], m["event_b_turn_on_at_valley"], m.get("period_loss")
    if a.get("q1_eoff_J") is None or b.get("q1_eon_J") is None or not pl:
        return None
    return {"overshoot_V": b["sw_overshoot_above_bus_V"], "eon_eoff_J": a["q1_eoff_J"] + b["q1_eon_J"],
            "eon_J": b["q1_eon_J"], "eoff_J": a["q1_eoff_J"], "fet_loss_W": pl["fet_loss_W"],
            "efficiency": pl["estimated_efficiency"], "q2_gate_peak_V": b["q2_gate_peak_during_rise_V"],
            "sw_min_V": a["sw_min_V"], "rise_s": b["sw_rise_time_10_90_s"], "fall_s": a["sw_fall_time_90_10_s"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report", type=Path, nargs="?", default=ROOT / "results/gan/epc90133-design-round1.json")
    ap.add_argument("--extra", type=Path, nargs="*", default=[], help="further reports (fix runs) merged by case name")
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-design-round1-assessment.json")
    ap.add_argument("--rule", choices=("round1", "round3"), default="round1")
    args = ap.parse_args()
    rep = json.loads(args.report.read_text(encoding="utf-8"))
    cases = dict(rep["cases"])
    extra_reports = []
    args.report = args.report.resolve()
    for x in args.extra:
        x = x.resolve()
        xr = json.loads(x.read_text(encoding="utf-8"))
        clash = set(xr["cases"]) & set(cases)
        if clash:
            raise SystemExit(f"{x}: cases already present: {sorted(clash)}")
        cases.update(xr["cases"])
        extra_reports.append({"path": x.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(x.read_bytes()).hexdigest(),
                              "complete": xr.get("complete")})
    main_cases = {k: c for k, c in cases.items() if not k.endswith(("-ms50", "-gear"))}
    designs = sorted({c["parameters"]["design"] for c in main_cases.values()}, key=lambda d: (d != "stock", d))
    alts = sorted({c["parameters"]["alternative"] for c in main_cases.values()})
    table, verdicts = {}, {}
    for d in designs:
        table[d] = {a: metrics(cases.get(f"{d}@{a}")) for a in alts}
    pair_step, pair_gear = {}, set()
    # Gear check (declared in scripts/epc90133_switching.py, rev-2 Gear fallback): Gear vs trapezoidal, same step.
    gear_check = []
    for base in ("stock@step-Ls0", "R80-2.2@step-Ls0", "R80-2.2@step-Ls50"):
        t, g = metrics(cases.get(base)), metrics(cases.get(base + "-gear"))
        if t and g:
            gear_check.append({"case": base, **{k: g[k] / t[k] - 1 for k in ("overshoot_V", "fet_loss_W", "q2_gate_peak_V")
                                               if t[k] and g[k] is not None}})
    gear_diff = []
    st, sg_ = metrics(cases.get("stock@step-Ls0")), metrics(cases.get("stock@step-Ls0-gear"))
    ct, cg_ = metrics(cases.get("R80-2.2@step-Ls0")), metrics(cases.get("R80-2.2@step-Ls0-gear"))
    if st and sg_ and ct and cg_:
        for k in ("overshoot_V", "fet_loss_W"):
            dt_, dg_ = ct[k] - st[k], cg_[k] - sg_[k]
            gear_diff.append({"metric": k, "trap_difference": dt_, "gear_difference": dg_, "rel": dg_ / dt_ - 1})
    gear_ok = bool(gear_check) and bool(gear_diff) and all(abs(v) <= 0.02 for r in gear_check for k, v in r.items() if k != "case")         and all(abs(r["rel"]) <= 0.10 for r in gear_diff)
    for a in alts:
        for d in designs:
            if d == "stock":
                continue
            if table["stock"][a] is None or table[d][a] is None:
                s50, c50 = metrics(cases.get(f"stock@{a}-ms50")), metrics(cases.get(f"{d}@{a}-ms50"))
                sg, cg = metrics(cases.get(f"stock@{a}-gear")), metrics(cases.get(f"{d}@{a}-gear"))
                if s50 and c50:
                    pair_step[(d, a)] = (s50, c50)
                elif sg and cg and gear_ok:
                    pair_step[(d, a)] = (sg, cg)
                    pair_gear.add((d, a))
    for d in designs:
        if d == "stock":
            continue
        if args.rule == "round3":
            per = {"C1_fet_loss_within_5pct": [], "C2_q2_gate_peak_not_above": []}
            over = []
            for a in alts:
                s, c = pair_step.get((d, a), (table["stock"][a], table[d][a]))
                if s is None or c is None:
                    for k in per:
                        per[k].append(None)
                    over.append(None)
                    continue
                per["C1_fet_loss_within_5pct"].append(None if c["fet_loss_W"] is None or s["fet_loss_W"] is None
                                                      else c["fet_loss_W"] <= s["fet_loss_W"] * 1.05)
                per["C2_q2_gate_peak_not_above"].append(c["q2_gate_peak_V"] <= s["q2_gate_peak_V"])
                over.append(c["overshoot_V"])
            v = {k: ("not met" if False in x else "undetermined" if None in x else "met") for k, x in per.items()}
            v["constraints"] = ("not met" if "not met" in v.values() else
                                "undetermined" if "undetermined" in v.values() else "met")
            verdicts[d] = {"per_alternative": per, "verdict": v, "overshoot_V": dict(zip(alts, over)),
                           "worst_case_overshoot_V": None if None in over else max(over),
                           "compared_at_50ps": sorted(a for (dd, a) in pair_step if dd == d and (dd, a) not in pair_gear),
                           "compared_with_gear": sorted(a for (dd, a) in pair_gear if dd == d)}
            continue
        per = {"T1_overshoot_lower": [], "T2_switching_energy_not_higher": [], "T3_efficiency_not_lower": []}
        for a in alts:
            s, c = pair_step.get((d, a), (table["stock"][a], table[d][a]))
            if s is None or c is None:
                for k in per:
                    per[k].append(None)
                continue
            per["T1_overshoot_lower"].append(c["overshoot_V"] <= s["overshoot_V"] - max(1.0, 0.10 * s["overshoot_V"]))
            per["T2_switching_energy_not_higher"].append(c["eon_eoff_J"] <= s["eon_eoff_J"] * 1.02)
            per["T3_efficiency_not_lower"].append(None if c["fet_loss_W"] is None or s["fet_loss_W"] is None
                                                  else c["fet_loss_W"] <= s["fet_loss_W"] * 1.02)
        v = {k: ("not met" if False in x else "undetermined" if None in x else "met") for k, x in per.items()}
        v["all_three"] = ("not met" if "not met" in v.values() else
                          "undetermined" if "undetermined" in v.values() else "met")
        verdicts[d] = {"per_alternative": per, "verdict": v,
                       "compared_at_50ps": sorted(a for (dd, a) in pair_step if dd == d)}
    rel = {d: {a: ({k: (table[d][a][k] / table["stock"][a][k] - 1) for k in table[d][a]
                    if table[d][a][k] is not None and table["stock"][a][k]}
                   if table[d][a] and table["stock"][a] else None) for a in alts} for d in designs if d != "stock"}
    out = {"schema": "epc90133-design-assessment/1",
           "report": {"path": args.report.relative_to(ROOT).as_posix(),
                      "sha256": hashlib.sha256(args.report.read_bytes()).hexdigest(), "complete": rep.get("complete")},
           "extra_reports": extra_reports,
           "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "rule": ("declared in scripts/epc90133_switching.py (design round 1); every alternative must hold"
                    if args.rule == "round1" else "round3: overshoot objective, C1 loss <= stock x 1.05, C2 Q2 gate peak <= stock, every alternative"),
           "ranking": (sorted(([d, v["worst_case_overshoot_V"]] for d, v in verdicts.items()
                               if v["verdict"]["constraints"] == "met"), key=lambda x: x[1])
                       if args.rule == "round3" else None),
           "scope": "ranking within the unvalidated model (EPC2302 Fig. 7 exception, behavioural driver, exploratory G extraction); frozen predictions for the board, not validated values",
           "gear_check": {"per_case": gear_check, "stock_to_candidate_difference": gear_diff, "passes": gear_ok,
                          "rule": "overshoot, FET loss, Q2 gate peak within 2 %; difference R80-2.2 minus stock within 10 %"},
           "metrics": table, "relative_to_stock": rel, "verdicts": verdicts}
    args.output.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    for d in designs:
        for a in alts:
            m = table[d][a]
            if m:
                loss = f"{m['fet_loss_W']:6.3f} W eta {m['efficiency'] * 100:6.3f} %" if m["fet_loss_W"] is not None                     else "loss not settled"
                print(f"{d:15s} {a:10s} over {m['overshoot_V']:6.2f} V  Eon+Eoff {m['eon_eoff_J'] * 1e6:6.2f} uJ "
                      f"(on {m['eon_J'] * 1e6:5.2f}, off {m['eoff_J'] * 1e6:5.2f})  loss {loss}  "
                      f"Q2g {m['q2_gate_peak_V']:5.2f} V  tr {m['rise_s'] * 1e9:5.2f} ns")
            else:
                print(f"{d:15s} {a:10s} missing or unusable")
    for d, v in verdicts.items():
        print(d, v["verdict"])


if __name__ == "__main__":
    main()
