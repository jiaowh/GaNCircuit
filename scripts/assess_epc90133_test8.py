"""Test 8 verdict: apply the PHASE-stress criteria declared in scripts/epc90133_switching.py to the saved reports.

No simulation. Reads run 1 (results/gan/epc90133-switching-phase.json), the substitute step check
(epc90133-switching-phase-2.json) and the supplementary timing-run reading (epc90133-test8-phase-partial.json),
and writes one structured assessment. The declared criteria, on RAW PHASE-to-GND extremes (no averaging):
  C1 rating: the regularized G+50 pH cases (pin10, pin100) and G-pin100 stay inside -5/+85 V at both events;
  C2 step: pin100 changes each raw extreme by less than 0.3 V or 10 % when the step is halved; after run 1 a
       substitute was declared before its run: pin10 against pin10-ms50, same criterion;
  C3 bracket: 10 and 100 pF give the same C1 verdict.
Partial timing-run values are listed as supplementary and never satisfy a criterion. PHASE-stress validity is
kept separate from switching-metric eligibility (the "usable" flag, numerical checks of the switching metrics).
Whatever the verdict, this concerns an assumed driver regularization (pin capacitance, clamps to ideal rails),
not a qualified driver model; it is not a hardware margin.

    python scripts/assess_epc90133_test8.py
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN1 = ROOT / "results/gan/epc90133-switching-phase.json"
RUN2 = ROOT / "results/gan/epc90133-switching-phase-2.json"
PARTIAL = ROOT / "results/gan/epc90133-test8-phase-partial.json"
OUTPUT = ROOT / "results/gan/epc90133-test8-assessment.json"
RATING_V = (-5.0, 85.0)
STEP_ABS_V, STEP_REL = 0.3, 0.10
EVENTS = ("event_a", "event_b")


def extremes(case):
    """Raw PHASE extremes per event, or None when the case has no metrics."""
    m = (case or {}).get("metrics")
    if not m:
        return None
    g = m["gate_and_current_diagnostics"]
    return {e: {"min_V": g[e]["driver_phase_to_gnd_min_V"], "max_V": g[e]["driver_phase_to_gnd_max_V"]} for e in EVENTS}


def inside(x):
    return all(RATING_V[0] <= x[e]["min_V"] and x[e]["max_V"] <= RATING_V[1] for e in EVENTS)


def step_check(a, b):
    out = {}
    for e in EVENTS:
        out[e] = {}
        for k in ("min_V", "max_V"):
            d = b[e][k] - a[e][k]
            out[e][k] = {"base": a[e][k], "half_step": b[e][k], "change_V": d,
                         "pass": abs(d) < STEP_ABS_V or abs(d) < STEP_REL * abs(a[e][k])}
        out[e]["pass"] = all(v["pass"] for v in out[e].values() if isinstance(v, dict))
    return out


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    r1, r2 = (json.loads(p.read_text(encoding="utf-8")) for p in (RUN1, RUN2))
    partial = json.loads(PARTIAL.read_text(encoding="utf-8"))
    cases = {**r1["cases"], **{f"{k} (step-check run)": v for k, v in r2["cases"].items()}}
    status = {n: {"completed": extremes(c) is not None, "switching_usable": c.get("usable") is True,
                  "phase_extremes": extremes(c)} for n, c in cases.items()}

    c1_cases = ("G-m1-mid-Ls50-pin10", "G-m1-mid-Ls50-pin100", "G-m1-mid-pin100")
    c1 = {n: (inside(status[n]["phase_extremes"]) if status[n]["completed"] else None) for n in c1_cases}
    c1_verdict = "incomplete" if None in c1.values() else ("pass" if all(c1.values()) else "fail")

    p100, p100h = (extremes(r1["cases"].get(n)) for n in ("G-m1-mid-Ls50-pin100", "G-m1-mid-Ls50-pin100-ms50"))
    c2_declared = {"verdict": "incomplete", "reason": "pin100 and pin100-ms50 timed out in their timing runs"} \
        if not (p100 and p100h) else {"detail": step_check(p100, p100h)}
    p10, p10h = extremes(r2["cases"]["G-m1-mid-Ls50-pin10"]), extremes(r2["cases"]["G-m1-mid-Ls50-pin10-ms50"])
    sub = step_check(p10, p10h)
    c2_sub = {"cases": "G-m1-mid-Ls50-pin10 vs -pin10-ms50 (declared after run 1, before its run)",
              "event_a": "pass" if sub["event_a"]["pass"] else "fail",
              "event_b": "pass" if sub["event_b"]["pass"] else "fail", "detail": sub,
              "note": "event B's half-step minimum is one sample at a step of about 1e-19 s (next lowest -2.32 V); "
                      "excluding it would be a judgement made after the run, so the failure stands"}
    c3 = {"verdict": "incomplete", "reason": "no completed 100 pF case"} if c1["G-m1-mid-Ls50-pin100"] is None else \
        {"verdict": "pass" if c1["G-m1-mid-Ls50-pin10"] == c1["G-m1-mid-Ls50-pin100"] else "fail"}

    unregularized = step_check(extremes(r1["cases"]["G-m1-mid-Ls50"]), extremes(r1["cases"]["G-m1-mid-Ls50-ms50"]))
    report = {
        "schema": "epc90133-test8-assessment/1",
        "inputs": {p.relative_to(ROOT).as_posix(): sha(p) for p in (RUN1, RUN2, PARTIAL)},
        "evaluator_sha256": sha(Path(__file__)),
        "criteria": {"rating_V": RATING_V, "step_abs_V": STEP_ABS_V, "step_rel": STEP_REL},
        "case_status": status,
        "C1_rating": {"verdict": c1_verdict, "per_case": c1},
        "C2_step_declared": c2_declared,
        "C2_step_substitute": c2_sub,
        "C3_bracket": c3,
        "supplementary_not_criteria": {
            "partial_timing_runs_event_a": {n: {k: v for k, v in c.items() if k in ("status", "raw_min_V", "raw_max_V",
                                                                                      "raw_min_half_width_s")}
                                            for n, c in partial["cases"].items()},
            "unregularized_step_change": unregularized},
        "phase_stress": "unresolved",
        "summary": ("Declared test incomplete (100 pF cases timed out); substitute step check passes at event A and "
                    "fails at event B. PHASE extremes are sensitive to driver-model assumptions (assumed pin "
                    "capacitance and clamps to ideal rails), and some unregularized extremes are numerically "
                    "unstable; the unregularized event-A minimum (-28 V) is step-stable. No hardware margin follows."),
        "switching_metrics": ("separate from PHASE stress: eligibility is each case's 'usable' flag; the regularization "
                              "is not a qualified driver model")}
    OUTPUT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print("C1", c1_verdict, c1, "| C2 declared", c2_declared.get("verdict"), "| C2 substitute A", c2_sub["event_a"],
          "B", c2_sub["event_b"], "| C3", c3["verdict"], "| PHASE stress unresolved")


if __name__ == "__main__":
    main()
