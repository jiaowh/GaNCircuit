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
Cross-method fallback (committed at 1b24989, 5 October 2026 19:58; a retrospective amendment: it was committed after
stock@ramp-Ls50-gear stalled at 4.98 us, and after R80-2.2-dt7.5@ramp-Ls50-gear, one result it affects, had finished
at 19:28): if no same-method pair is usable, the usable trapezoidal case of one side is compared with the Gear case
of the other, only if the Gear check passes with every per-case difference within 0.1 % (4 pairs: at most 0.05 %
found). Such a comparison decides a constraint only if its margin exceeds 0.1 % of the stock value; otherwise
'undetermined'. Revision 4 reports verdicts under the amended rule and, separately, under the original rule
without this fallback ('original_rule').

Revision 4 (6 October 2026, audit at 5d72e4e, docs/project-audit-5d72e4e.md; no simulation rerun):
- the four declared alternatives are required independently of the inputs; a missing one is undetermined, never
  dropped from the rule;
- every case is checked structurally before use: its name (<design>@<alternative>[-ms50|-gear|-repro]) must agree
  with its parameters (design, alternative, driver form, package L, gate resistor, dead time, extraction G-m1-mid,
  step, integration method, base case); unknown alternatives, suffixes or designs reject the input;
- the merged reports must share operating conditions, fixed assumptions, extraction and vendor-library hashes;
- a FET loss counts (T3, C1, Gear check) only with loss-estimator revision 2 and a settled window;
- the Gear check requires its whole declared case set and every metric: stock and R80-2.2 at step-Ls0, R80-2.2 at
  step-Ls50 when that trapezoidal case is usable, and stock at ramp-Ls0 for the 0.1 % (cross-method) level;
- round 3's declared controls gate the selection: the reproduction control stock@ramp-Ls0-repro (netlist hash
  identical, every metric within 1e-6 relative) and the top candidate's half-step check <d>@step-Ls0-ms50 against
  <d>@step-Ls0 (overshoot, FET loss and Q2 gate peak within 2 %). Without both, nothing is selected;
- every design/alternative comparison is emitted as a resolved pair (both case names, kind, step, method, metrics,
  relative changes), and verdicts and relative changes derive from it.
Revision 5 (6 October 2026, audit at 0f07a6a, docs/project-audit-0f07a6a.md finding 1; no simulation rerun):
- types are checked before use: report, case table, each case, its parameters and metrics must be objects, the
  input manifest and run table objects, 'usable' a literal boolean (absent or null only for a case with no
  metrics, i.e. a run that produced no result: unusable), and every metric value read here null or a
  finite number (not a string or boolean); anything else rejects the input (exit 2) with reasons;
- a null metric is missing evidence: a design whose overshoot is missing under any alternative has objective
  'undetermined' and is never ranked or selected (revision 4 ranked it with a null objective); round 1's targets
  are undetermined, not an error, when a needed value is missing.
Exit status: 0 selected (round 3) or assessed (round 1), 1 round 3 without a selection, 2 input rejected (the
output then records the reasons and no verdicts).
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DECLARED_ALTERNATIVES = ("ramp-Ls0", "ramp-Ls50", "step-Ls0", "step-Ls50")
ALTERNATIVE_PARAMETERS = {"ramp-Ls0": ("ramp", None), "ramp-Ls50": ("ramp", 50e-12),
                          "step-Ls0": ("step", None), "step-Ls50": ("step", 50e-12)}  # driver form, package Ls
SUFFIXES = {"": (100e-12, None), "-ms50": (50e-12, None), "-gear": (100e-12, "gear"), "-repro": (100e-12, None)}
DESIGN_EXTRACTION = "G-m1-mid"
LOSS_ESTIMATOR_REVISION = 2
DESIGN_NAME = re.compile(r"^R80-(\d+(?:\.\d+)?)(?:-dt(\d+(?:\.\d+)?))?$")
GEAR_CHECK_KEYS = ("overshoot_V", "fet_loss_W", "q2_gate_peak_V")
REPRO_REL = 1e-6
HALF_STEP_REL = 0.02


class InputRejected(Exception):
    pass


def close(a, b):
    return a is not None and b is not None and math.isclose(a, b, rel_tol=1e-9, abs_tol=0.0)


def parse_name(name):
    """(design, alternative, suffix) of a case name, or None if it does not follow the declared pattern."""
    if "@" not in name:
        return None
    design, rest = name.split("@", 1)
    for a in DECLARED_ALTERNATIVES:
        if rest.startswith(a) and rest[len(a):] in SUFFIXES:
            return design, a, rest[len(a):]
    return None


METRIC_FIELDS = {"event_a_turn_off_at_peak": ("q1_eoff_J", "sw_min_V", "sw_fall_time_90_10_s"),
                 "event_b_turn_on_at_valley": ("q1_eon_J", "sw_overshoot_above_bus_V", "q2_gate_peak_during_rise_V",
                                               "sw_rise_time_10_90_s"),
                 "period_loss": ("fet_loss_W", "estimated_efficiency")}


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def type_problems(name, case):
    """Revision 5: structural types of one case (before any other check reads it)."""
    if not isinstance(case, dict):
        return [f"{name}: case is not an object"]
    out = []
    if not isinstance(case.get("parameters"), dict):
        out.append(f"{name}: parameters is not an object")
    if case.get("usable") is None:  # a run that produced no result (stored reports omit the key): unusable
        if case.get("metrics") is not None:
            out.append(f"{name}: metrics present but usable is missing")
    elif not isinstance(case["usable"], bool):
        out.append(f"{name}: usable {case['usable']!r} is not a boolean")
    elif case["usable"]:
        m = case.get("metrics")
        if not isinstance(m, dict):
            return out + [f"{name}: usable case without a metrics object"]
        for group, fields in METRIC_FIELDS.items():
            g = m.get(group)
            if g is None:
                continue
            if not isinstance(g, dict):
                out.append(f"{name}: metrics.{group} is not an object")
                continue
            out += [f"{name}: metrics.{group}.{f} = {g[f]!r} is not a finite number or null"
                    for f in fields if g.get(f) is not None and not is_number(g[f])]
            if group == "period_loss":
                if g.get("settled_within_2pct") is not None and not isinstance(g["settled_within_2pct"], bool):
                    out.append(f"{name}: settled_within_2pct {g['settled_within_2pct']!r} is not a boolean")
                rev = g.get("estimator_revision")
                if rev is not None and (not isinstance(rev, int) or isinstance(rev, bool)):
                    out.append(f"{name}: estimator_revision {rev!r} is not an integer")
    return out


def case_problems(name, case):
    bad = type_problems(name, case)
    if bad:
        return bad
    parsed = parse_name(name)
    if parsed is None:
        return [f"{name}: name is not <design>@<declared alternative>[-ms50|-gear|-repro]"]
    design, alt, suffix = parsed
    p = case.get("parameters") or {}
    out = []
    want = {"design": design, "alternative": alt, "ext": DESIGN_EXTRACTION}
    out += [f"{name}: parameter {k} = {p.get(k)!r}, expected {v!r}" for k, v in want.items() if p.get(k) != v]
    driver, l_s = ALTERNATIVE_PARAMETERS[alt]
    if p.get("driver", "ramp") != driver:
        out.append(f"{name}: driver {p.get('driver', 'ramp')!r}, expected {driver!r}")
    if not (p.get("l_s") is None and l_s is None or close(p.get("l_s"), l_s)):
        out.append(f"{name}: l_s {p.get('l_s')!r}, expected {l_s!r}")
    maxstep, method = SUFFIXES[suffix]
    if not close(p.get("maxstep"), maxstep):
        out.append(f"{name}: maxstep {p.get('maxstep')!r}, expected {maxstep!r}")
    if p.get("method") != method:
        out.append(f"{name}: method {p.get('method')!r}, expected {method!r}")
    if suffix and p.get("base") != f"{design}@{alt}":
        out.append(f"{name}: base {p.get('base')!r}, expected {design}@{alt}")
    if not suffix and p.get("base") is not None:
        out.append(f"{name}: unexpected base {p.get('base')!r}")
    if design == "stock":
        if p.get("gate_r") or p.get("dead") is not None:
            out.append(f"{name}: stock design with gate_r {p.get('gate_r')!r} / dead {p.get('dead')!r}")
    else:
        m = DESIGN_NAME.match(design)
        if not m:
            out.append(f"{name}: unknown design {design!r}")
        else:
            if p.get("gate_r") != {"R80": float(m.group(1))}:
                out.append(f"{name}: gate_r {p.get('gate_r')!r}, expected {{'R80': {float(m.group(1))}}}")
            dead = None if m.group(2) is None else float(m.group(2)) * 1e-9
            if not (p.get("dead") is None and dead is None or close(p.get("dead"), dead)):
                out.append(f"{name}: dead {p.get('dead')!r}, expected {dead!r}")
    return out


def load_reports(paths):
    """Merge reports by case name after the compatibility and structural checks; raises InputRejected."""
    cases, runs, records, problems = {}, {}, [], []
    shared = None
    for path in paths:
        path = Path(path).resolve()
        try:
            rep = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise InputRejected([f"{path}: unreadable report ({exc})"])
        if not isinstance(rep, dict) or not isinstance(rep.get("cases"), dict):
            raise InputRejected([f"{path}: no case table"])
        manifest = rep.get("input_manifest")
        if not isinstance(manifest, dict) or not isinstance(rep.get("runs", {}), dict)                 or not all(isinstance(v, dict) for v in (rep.get("runs") or {}).values()):
            raise InputRejected([f"{path}: input_manifest or runs is not an object (of objects)"])
        ident = {"conditions": rep.get("conditions"), "fixed_assumptions": rep.get("fixed_assumptions"),
                 "extractions": manifest.get("extractions"), "vendor_library": manifest.get("vendor_library")}
        if any(v is None for v in ident.values()):
            problems.append(f"{path.name}: missing {[k for k, v in ident.items() if v is None]}")
        elif shared is None:
            shared = ident
        else:
            problems += [f"{path.name}: {k} differs from the first report" for k in ident if ident[k] != shared[k]]
        clash = set(rep["cases"]) & set(cases)
        if clash:
            problems.append(f"{path.name}: cases already present: {sorted(clash)}")
        for name, case in rep["cases"].items():
            problems += case_problems(name, case)
        cases.update(rep["cases"])
        runs.update({k: v for k, v in (rep.get("runs") or {}).items() if k in rep["cases"]})
        try:
            rel = path.relative_to(ROOT).as_posix()
        except ValueError:
            rel = str(path)
        records.append({"path": rel, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "complete": rep.get("complete")})
    if problems:
        raise InputRejected(problems)
    return cases, runs, records


def metrics(case):
    if not case or not case.get("usable"):
        return None
    m = case.get("metrics") or {}
    a, b, pl = m.get("event_a_turn_off_at_peak") or {}, m.get("event_b_turn_on_at_valley") or {}, m.get("period_loss")
    if a.get("q1_eoff_J") is None or b.get("q1_eon_J") is None or not pl:
        return None
    loss_valid = (pl.get("estimator_revision") == LOSS_ESTIMATOR_REVISION and pl.get("settled_within_2pct") is True
                  and pl.get("fet_loss_W") is not None)
    return {"overshoot_V": b.get("sw_overshoot_above_bus_V"), "eon_eoff_J": a["q1_eoff_J"] + b["q1_eon_J"],
            "eon_J": b["q1_eon_J"], "eoff_J": a["q1_eoff_J"],
            "fet_loss_W": pl["fet_loss_W"] if loss_valid else None,
            "efficiency": pl.get("estimated_efficiency") if loss_valid else None,
            "q2_gate_peak_V": b.get("q2_gate_peak_during_rise_V"),
            "sw_min_V": a.get("sw_min_V"), "rise_s": b.get("sw_rise_time_10_90_s"),
            "fall_s": a.get("sw_fall_time_90_10_s")}


def relative(s, c):
    return {k: c[k] / s[k] - 1 for k in c if c[k] is not None and s.get(k)}


def gear_check(cases):
    """Declared Gear check (scripts/epc90133_switching.py, rev-2 Gear fallback), with its full case set required."""
    m = lambda k: metrics(cases.get(k))
    required = ["stock@step-Ls0", "R80-2.2@step-Ls0"] + (["R80-2.2@step-Ls50"] if m("R80-2.2@step-Ls50") else [])
    per_case, missing = [], []
    for base in required + ["stock@ramp-Ls0"]:
        t, g = m(base), m(base + "-gear")
        if not (t and g) or any(t[k] is None or g[k] is None or not t[k] for k in GEAR_CHECK_KEYS):
            missing.append(base)
            continue
        per_case.append({"case": base, **{k: g[k] / t[k] - 1 for k in GEAR_CHECK_KEYS}})
    diff = []
    st, sg, ct, cg = (m("stock@step-Ls0"), m("stock@step-Ls0-gear"), m("R80-2.2@step-Ls0"), m("R80-2.2@step-Ls0-gear"))
    if "stock@step-Ls0" not in missing and "R80-2.2@step-Ls0" not in missing:
        for k in ("overshoot_V", "fet_loss_W"):
            dt_, dg_ = ct[k] - st[k], cg[k] - sg[k]
            diff.append({"metric": k, "trap_difference": dt_, "gear_difference": dg_,
                         "rel": dg_ / dt_ - 1 if dt_ else None})
    within = lambda lim, rows: all(abs(v) <= lim for r in rows for k, v in r.items() if k != "case")
    passes = (not [b for b in missing if b in required] and len(diff) == 2
              and all(r["rel"] is not None and abs(r["rel"]) <= 0.10 for r in diff)
              and within(0.02, [r for r in per_case if r["case"] in required]))
    tight = passes and not missing and within(0.001, per_case)
    return {"per_case": per_case, "stock_to_candidate_difference": diff, "required": required,
            "required_for_0.1pct": required + ["stock@ramp-Ls0"], "missing": missing, "passes": passes,
            "rule": "overshoot, FET loss, Q2 gate peak within 2 %; difference R80-2.2 minus stock within 10 %",
            "tight_within_0.1pct": tight}


def resolve_pair(cases, d, a, gear_ok, gear_tight, allow_cross):
    m = lambda k: metrics(cases.get(k))
    options = [("main", f"stock@{a}", f"{d}@{a}"), ("ms50", f"stock@{a}-ms50", f"{d}@{a}-ms50")]
    if gear_ok:
        options.append(("gear", f"stock@{a}-gear", f"{d}@{a}-gear"))
    if allow_cross and gear_tight:
        options += [("cross_method", f"stock@{a}", f"{d}@{a}-gear"), ("cross_method", f"stock@{a}-gear", f"{d}@{a}")]
    for kind, sk, ck in options:
        s, c = m(sk), m(ck)
        if s and c:
            ps, pc = cases[sk]["parameters"], cases[ck]["parameters"]
            return {"kind": kind, "stock_case": sk, "candidate_case": ck,
                    "maxstep_s": [ps["maxstep"], pc["maxstep"]],
                    "method": [ps.get("method") or "trap", pc.get("method") or "trap"],
                    "stock": s, "candidate": c, "relative_to_stock": relative(s, c)}
    return {"kind": "none", "stock_case": None, "candidate_case": None}


def verdict_of(x):
    return "not met" if False in x else "undetermined" if None in x else "met"


def decide(pairs, designs, rule):
    verdicts = {}
    for d in designs:
        if rule == "round3":
            per = {"C1_fet_loss_within_5pct": [], "C2_q2_gate_peak_not_above": []}
            over = []
            for a in DECLARED_ALTERNATIVES:
                pr = pairs[d][a]
                if pr["kind"] == "none":
                    for k in per:
                        per[k].append(None)
                    over.append(None)
                    continue
                s, c = pr["stock"], pr["candidate"]
                tol = 0.001 if pr["kind"] == "cross_method" else 0.0  # cross-method: decide only outside the method error

                def cmp(cv, lim):
                    if cv is None or lim is None:
                        return None
                    return None if tol and abs(cv - lim) <= tol * abs(lim) else cv <= lim
                per["C1_fet_loss_within_5pct"].append(
                    cmp(c["fet_loss_W"], None if s["fet_loss_W"] is None else s["fet_loss_W"] * 1.05))
                per["C2_q2_gate_peak_not_above"].append(cmp(c["q2_gate_peak_V"], s["q2_gate_peak_V"]))
                over.append(c["overshoot_V"])
            v = {k: verdict_of(x) for k, x in per.items()}
            v["constraints"] = verdict_of([{"met": True, "not met": False}.get(x) for x in v.values()])
            v["objective"] = "undetermined" if None in over else "complete"  # revision 5
            verdicts[d] = {"per_alternative": per, "verdict": v, "overshoot_V": dict(zip(DECLARED_ALTERNATIVES, over)),
                           "worst_case_overshoot_V": None if None in over else max(over),
                           "pair_kinds": {a: pairs[d][a]["kind"] for a in DECLARED_ALTERNATIVES}}
            continue
        per = {"T1_overshoot_lower": [], "T2_switching_energy_not_higher": [], "T3_efficiency_not_lower": []}
        for a in DECLARED_ALTERNATIVES:
            pr = pairs[d][a]
            if pr["kind"] == "none":
                for k in per:
                    per[k].append(None)
                continue
            s, c = pr["stock"], pr["candidate"]
            per["T1_overshoot_lower"].append(
                None if c["overshoot_V"] is None or s["overshoot_V"] is None
                else c["overshoot_V"] <= s["overshoot_V"] - max(1.0, 0.10 * s["overshoot_V"]))
            per["T2_switching_energy_not_higher"].append(c["eon_eoff_J"] <= s["eon_eoff_J"] * 1.02)
            per["T3_efficiency_not_lower"].append(None if c["fet_loss_W"] is None or s["fet_loss_W"] is None
                                                  else c["fet_loss_W"] <= s["fet_loss_W"] * 1.02)
        v = {k: verdict_of(x) for k, x in per.items()}
        v["all_three"] = verdict_of([{"met": True, "not met": False}.get(x) for x in v.values()])
        verdicts[d] = {"per_alternative": per, "verdict": v,
                       "pair_kinds": {a: pairs[d][a]["kind"] for a in DECLARED_ALTERNATIVES}}
    return verdicts


def reproduction_control(cases, runs):
    base, ctl = "stock@ramp-Ls0", "stock@ramp-Ls0-repro"
    b, c = metrics(cases.get(base)), metrics(cases.get(ctl))
    hb, hc = (runs.get(base) or {}).get("netlist_sha256"), (runs.get(ctl) or {}).get("netlist_sha256")
    if not (b and c and hb and hc):
        return {"status": "missing", "cases": [base, ctl]}
    if any((b[k] is None) != (c[k] is None) for k in b):
        worst = math.inf
    else:
        worst = max((abs(c[k] - b[k]) / (abs(b[k]) or 1.0) for k in b if b[k] is not None), default=0.0)
    ok = hb == hc and worst <= REPRO_REL
    return {"status": "pass" if ok else "fail", "cases": [base, ctl], "netlist_identical": hb == hc,
            "max_relative_difference": worst, "limit": REPRO_REL}


def half_step_check(cases, d):
    base, chk = f"{d}@step-Ls0", f"{d}@step-Ls0-ms50"
    b, c = metrics(cases.get(base)), metrics(cases.get(chk))
    if not (b and c) or any(b[k] is None or c[k] is None or not b[k] for k in GEAR_CHECK_KEYS):
        return {"status": "missing", "cases": [base, chk]}
    rel = {k: c[k] / b[k] - 1 for k in GEAR_CHECK_KEYS}
    return {"status": "pass" if all(abs(v) <= HALF_STEP_REL for v in rel.values()) else "fail",
            "cases": [base, chk], "relative": rel, "limit": HALF_STEP_REL}


def assess(cases, runs, rule):
    designs = sorted({c["parameters"]["design"] for c in cases.values()} - {"stock"})
    gc = gear_check(cases)
    out = {"gear_check": gc,
           "main_case_metrics": {d: {a: metrics(cases.get(f"{d}@{a}")) for a in DECLARED_ALTERNATIVES}
                                 for d in ["stock"] + designs}}
    for label, allow_cross in (("amended_rule", True), ("original_rule", False)):
        pairs = {d: {a: resolve_pair(cases, d, a, gc["passes"], gc["tight_within_0.1pct"], allow_cross)
                     for a in DECLARED_ALTERNATIVES} for d in designs}
        block = {"pairs": pairs, "verdicts": decide(pairs, designs, rule)}
        if rule == "round3":
            ranking = sorted(([d, v["worst_case_overshoot_V"]] for d, v in block["verdicts"].items()
                              if v["verdict"]["constraints"] == "met" and v["worst_case_overshoot_V"] is not None),
                             key=lambda x: x[1])
            repro = reproduction_control(cases, runs)
            half = half_step_check(cases, ranking[0][0]) if ranking else None
            selected = ranking[0][0] if ranking and repro["status"] == "pass" and half["status"] == "pass" else None
            block.update({"ranking": ranking, "reproduction_control": repro, "half_step_check": half,
                          "selection": selected,
                          "selection_rule": "top-ranked candidate (constraints met and overshoot known under every "
                                            "alternative), only if the reproduction control and its half-step check "
                                            "both pass"})
        out[label] = block
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report", type=Path, nargs="?", default=ROOT / "results/gan/epc90133-design-round1.json")
    ap.add_argument("--extra", type=Path, nargs="*", default=[], help="further reports (fix runs) merged by case name")
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-design-round1-assessment.json")
    ap.add_argument("--rule", choices=("round1", "round3"), default="round1")
    args = ap.parse_args()
    head = {"schema": "epc90133-design-assessment/2", "revision": 5,
            "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "rule": ("declared in scripts/epc90133_switching.py (design round 1); every alternative must hold"
                     if args.rule == "round1" else
                     "round3: overshoot objective, C1 loss <= stock x 1.05, C2 Q2 gate peak <= stock, every alternative; "
                     "selection gated on the reproduction control and the half-step check"),
            "declared_alternatives": list(DECLARED_ALTERNATIVES)}
    try:
        cases, runs, records = load_reports([args.report] + list(args.extra))
    except InputRejected as exc:
        out = {**head, "status": "rejected", "reasons": exc.args[0]}
        args.output.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
        print("input rejected:", *exc.args[0], sep="\n  ")
        raise SystemExit(2)
    res = assess(cases, runs, args.rule)
    amended = res["amended_rule"]
    status = "assessed" if args.rule == "round1" else "selected" if amended["selection"] else "no selection"
    out = {**head, "status": status, "report": records[0], "extra_reports": records[1:],
           "scope": "ranking within the unvalidated model (EPC2302 Fig. 7 exception, behavioural driver, exploratory "
                    "G extraction); provisional simulation predictions, not a frozen prediction record and not "
                    "validated values",
           "cross_method_note": "the cross-method fallback (1b24989) is a retrospective amendment; 'original_rule' "
                                "gives the verdicts without it",
           **res}
    args.output.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    for d, row in res["main_case_metrics"].items():
        for a, m in row.items():
            if m:
                loss = f"{m['fet_loss_W']:6.3f} W" if m["fet_loss_W"] is not None else "loss invalid/unsettled"
                over, q2g = (math.nan if m[k] is None else m[k] for k in ("overshoot_V", "q2_gate_peak_V"))
                print(f"{d:15s} {a:10s} over {over:6.2f} V  Eon+Eoff {m['eon_eoff_J'] * 1e6:6.2f} uJ  "
                      f"loss {loss}  Q2g {q2g:5.2f} V")
            else:
                print(f"{d:15s} {a:10s} main case missing or unusable")
    for label in ("amended_rule", "original_rule"):
        print(label)
        for d, v in res[label]["verdicts"].items():
            print(f"  {d:15s} {v['verdict']}  pairs {v['pair_kinds']}")
        if args.rule == "round3":
            b = res[label]
            print(f"  ranking {b['ranking']}  reproduction {b['reproduction_control']['status']}  "
                  f"half-step {b['half_step_check'] and b['half_step_check']['status']}  selection {b['selection']}")
    print("Gear check passes", res["gear_check"]["passes"], "0.1 %", res["gear_check"]["tight_within_0.1pct"],
          "missing", res["gear_check"]["missing"])
    raise SystemExit(0 if status in ("assessed", "selected") else 1)


if __name__ == "__main__":
    main()
