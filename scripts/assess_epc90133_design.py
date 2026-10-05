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
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-design-round1-assessment.json")
    args = ap.parse_args()
    rep = json.loads(args.report.read_text(encoding="utf-8"))
    cases = rep["cases"]
    main_cases = {k: c for k, c in cases.items() if not k.endswith("-ms50")}
    designs = sorted({c["parameters"]["design"] for c in main_cases.values()}, key=lambda d: (d != "stock", d))
    alts = sorted({c["parameters"]["alternative"] for c in main_cases.values()})
    table, verdicts = {}, {}
    for d in designs:
        table[d] = {a: metrics(cases.get(f"{d}@{a}")) for a in alts}
    for d in designs:
        if d == "stock":
            continue
        per = {"T1_overshoot_lower": [], "T2_switching_energy_not_higher": [], "T3_efficiency_not_lower": []}
        for a in alts:
            s, c = table["stock"][a], table[d][a]
            if s is None or c is None:
                for k in per:
                    per[k].append(None)
                continue
            per["T1_overshoot_lower"].append(c["overshoot_V"] <= s["overshoot_V"] - max(1.0, 0.10 * s["overshoot_V"]))
            per["T2_switching_energy_not_higher"].append(c["eon_eoff_J"] <= s["eon_eoff_J"] * 1.02)
            per["T3_efficiency_not_lower"].append(c["fet_loss_W"] <= s["fet_loss_W"] * 1.02)
        v = {k: ("undetermined" if None in x else "met" if all(x) else "not met") for k, x in per.items()}
        v["all_three"] = ("met" if all(x == "met" for x in v.values()) else
                          "undetermined" if "undetermined" in v.values() else "not met")
        verdicts[d] = {"per_alternative": per, "verdict": v}
    rel = {d: {a: ({k: (table[d][a][k] / table["stock"][a][k] - 1) for k in table[d][a]}
                   if table[d][a] and table["stock"][a] else None) for a in alts} for d in designs if d != "stock"}
    out = {"schema": "epc90133-design-assessment/1",
           "report": {"path": args.report.relative_to(ROOT).as_posix(),
                      "sha256": hashlib.sha256(args.report.read_bytes()).hexdigest(), "complete": rep.get("complete")},
           "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "rule": "declared in scripts/epc90133_switching.py (design round 1); every alternative must hold",
           "scope": "ranking within the unvalidated model (EPC2302 Fig. 7 exception, behavioural driver, exploratory G extraction); frozen predictions for the board, not validated values",
           "metrics": table, "relative_to_stock": rel, "verdicts": verdicts}
    args.output.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    for d in designs:
        for a in alts:
            m = table[d][a]
            if m:
                print(f"{d:15s} {a:10s} over {m['overshoot_V']:6.2f} V  Eon+Eoff {m['eon_eoff_J'] * 1e6:6.2f} uJ "
                      f"(on {m['eon_J'] * 1e6:5.2f}, off {m['eoff_J'] * 1e6:5.2f})  loss {m['fet_loss_W']:6.3f} W "
                      f"eta {m['efficiency'] * 100:6.3f} %  Q2g {m['q2_gate_peak_V']:5.2f} V  tr {m['rise_s'] * 1e9:5.2f} ns")
            else:
                print(f"{d:15s} {a:10s} missing or unusable")
    for d, v in verdicts.items():
        print(d, v["verdict"])


if __name__ == "__main__":
    main()
