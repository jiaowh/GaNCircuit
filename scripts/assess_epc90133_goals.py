#!/usr/bin/env python3
"""Score goals-study runs (epc90133_switching.py --study goals) against the owner's template goals S1-S13.

Definitions fixed on 8 October 2026 with plans/goal-targets-2026-10-08.md, before any goals run. Each design is
compared with 'stock' (same KiCad route, same extraction variant) under the same condition. The primary conditions
are ramp-Ls50 and step-Ls50 (assumed 50 pH package source inductance, the owner's default); a goal is met only if it
holds under both. The 0 pH alternatives are reported, not judged. Ideal probe at Q2's pads; FET-only losses.

* S1 Vpk: max(switch-node peak at the valley turn-on, Q1 VDS peak at the peak turn-off) <= 80 V (and < 100 V).
* S2 overshoot above the bus at the valley turn-on <= 20 % of VIN and <= 0.9 x stock's.
* S3 ring frequency reported; settling = last time after the valley turn-on command at which the switch node is
  more than 2 % of VIN from its final value (median of 490-500 ns; the goals study stores 500 ns); <= stock's.
* S4 tr (10-90 %), tf (90-10 %) <= 1.10 x stock's.
* S5 dv/dt = 0.8 VIN / tr, reported (template limit unfilled).
* S6 Q1 peak drain current at the valley turn-on <= stock's; di/dt = maximum slope of Q1's drain current over the
  rising-edge trace (0.25 ns centred differences) <= stock's.
* S7 every FET terminal gate-source extreme over both events within +5.5 / -3 V.
* S8 Q2 terminal gate-source peak during the rise < 0.5 V.
* S9 shoot-through: the model's channel current is not separated from capacitive current in these runs; 'none' is
  claimed only if Q2's terminal gate peak stays below VGS(th) min 0.8 V, otherwise 'not shown'.
* S10 Q1 Eon + Eoff <= 0.9 x stock's.
* S11 the dead time with the lowest FET loss over the sweep (2.5-20 ns, ramp-Ls50) lies within 5-15 ns.
* S12 FET-only estimated efficiency at least 0.3 points above stock's.
* S13 S1, S2, S7 and S8 hold at VIN 40 and 60 V, 0 % load (or the declared 2 A fallback) and parasitics x0.9/x1.1,
  each against stock at the same corner.
Model (owner decision, 8 October 2026): EPC2302QG is primary, cases named <case>-qg (--model-suffix -qg, the
default); --model-suffix '' scores the vendor model's runs, which are reported alongside, not judged.
A missing or unusable case makes that goal 'undetermined'.
Model update (owner decision, 8 October 2026, after EPC2302DS passed its datasheet checks): EPC2302DS is primary,
cases <case>-ds (--model-suffix -ds, now the default); EPC2302QG and vendor scoring remain available for the earlier
runs. The 0 pH alternatives are not run for EPC2302DS; they appear as missing ("reported_0pH" empty).
Retrospective fix (8 October 2026, after the first scoring attempt crashed, no definition changed): at 0 % load the
valley turn-on is soft and the bench reports no 10-90 % rise time; dv/dt and S4 are then None (undetermined) for
that case. S13 uses only S1, S2, S7 and S8, so its corner verdicts are unaffected. Output: --output (JSON) and a printed table.
Acceptance-gate repair (9 October 2026, after the audit docs/project-audit-274cd46.md; no goal definition or limit
changed): a case carrying "interpretation_invalid" is unusable, as in the other evaluators; a case name supplied by two
reports stops the scoring; every report contributing cases must record the same model-library identity (vendor and,
for -ds/-qg, the variant), and a -ds run's recorded model report must still match its file and pass every D check;
S5 has no template limit, so it is reported as undetermined and keeps 'all_met' from passing; an empty goal set is
undetermined, not met. S13 covers the declared separate voltage/load/scale corners only, not combined corners.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PRIMARY = ("ramp-Ls50", "step-Ls50")
REPORTED = ("ramp-Ls0", "step-Ls0")
DEADS = (2.5, 5, 7.5, 10, 12.5, 15, 20)
CORNERS = ("-v40", "-v60", "-i0", "-l0.9", "-l1.1")
GOALS = ("S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10", "S11", "S12", "S13")
LIBRARIES = {"-ds": ("vendor_library", "ds_library"), "-qg": ("vendor_library", "variant_library"), "": ("vendor_library",)}


def metrics(c, vin):
    if not c or c.get("usable") is not True or c.get("interpretation_invalid"):
        return None
    m = c["metrics"]
    a, b = m["event_a_turn_off_at_peak"], m["event_b_turn_on_at_valley"]
    g = m["gate_and_current_diagnostics"]
    tr = c["traces"]
    lg = tr["rising_long"]
    t = lg["start_s"] + lg["step_s"] * np.arange(len(lg["V"]))
    v = np.array(lg["V"])
    final = np.median(v[t >= t[-1] - 10e-9])
    out = np.where((t > 0) & (np.abs(v - final) > 0.02 * vin))[0]
    settle = float(t[out[-1]]) if len(out) else 0.0
    i1 = np.array(tr["device"]["rising_q1_id_A"])
    k = max(1, int(round(0.125e-9 / tr["step_s"])))
    didt = float(np.max((i1[2 * k:] - i1[:-2 * k]) / (2 * k * tr["step_s"])))
    vg = [g[e][f"q{q}_vgs_{x}_V"] for e in ("event_a", "event_b") for q in (1, 2) for x in ("max", "min")]
    return {"vpk_V": max(b["sw_peak_V"], a["q1_vds_peak_V"]), "overshoot_V": b["sw_overshoot_above_bus_V"],
            "f_r_Hz": b["ringing_frequency_Hz"], "settling_s": settle, "settling_censored": settle >= t[-1] - 10e-9,
            "tr_s": b["sw_rise_time_10_90_s"], "tf_s": a["sw_fall_time_90_10_s"],
            "dvdt_V_per_ns": None if b["sw_rise_time_10_90_s"] is None else 0.8 * vin / (b["sw_rise_time_10_90_s"] * 1e9),
            "id_peak_A": b["q1_peak_drain_current_A"], "didt_A_per_ns": didt / 1e9,
            "vgs_max_V": max(vg[0::2]), "vgs_min_V": min(vg[1::2]), "q2_gate_peak_V": b["q2_gate_peak_during_rise_V"],
            "eon_eoff_J": a["q1_eoff_J"] + b["q1_eon_J"], "fet_loss_W": m["period_loss"]["fet_loss_W"],
            "efficiency": m["period_loss"]["estimated_efficiency"]}


def goals(c, s, vin):
    """Per-condition goal checks for candidate metrics c against stock metrics s."""
    return {"S1": c["vpk_V"] <= 80.0, "S2": c["overshoot_V"] <= 0.2 * vin and c["overshoot_V"] <= 0.9 * s["overshoot_V"],
            "S3": c["settling_s"] <= s["settling_s"] and not c["settling_censored"],
            "S4": (None if None in (c["tr_s"], s["tr_s"], c["tf_s"], s["tf_s"])
                   else c["tr_s"] <= 1.1 * s["tr_s"] and c["tf_s"] <= 1.1 * s["tf_s"]),
            "S6": c["id_peak_A"] <= s["id_peak_A"] and c["didt_A_per_ns"] <= s["didt_A_per_ns"],
            "S7": c["vgs_max_V"] <= 5.5 and c["vgs_min_V"] >= -3.0, "S8": c["q2_gate_peak_V"] < 0.5,
            "S9": True if c["q2_gate_peak_V"] < 0.8 else None,
            "S10": c["eon_eoff_J"] <= 0.9 * s["eon_eoff_J"], "S12": 100 * (c["efficiency"] - s["efficiency"]) >= 0.3}


def combine(vals):
    vals = list(vals)
    if not vals:
        return None
    if any(v is None for v in vals):
        return None if all(v is not False for v in vals) else False
    return all(vals)


def check_inputs(reps, suffix):
    """Identity checks on the reports that supplied cases; returns the shared model identity or stops."""
    ids = {}
    for r, rep in reps:
        m = rep.get("input_manifest") or {}
        key = tuple((lib, (m.get(lib) or {}).get("sha256")) for lib in LIBRARIES[suffix])
        if any(h is None for _, h in key):
            raise SystemExit(f"{r}: no recorded model-library identity for model suffix {suffix!r}")
        ids.setdefault(key, []).append(str(r))
    if len(ids) != 1:
        raise SystemExit(f"reports disagree on the model library: {list(ids.values())}")
    identity = dict(next(iter(ids)))
    if suffix == "-ds":
        lib = reps[0][1]["input_manifest"]["ds_library"]
        f = ROOT / lib["report"]
        if hashlib.sha256(f.read_bytes()).hexdigest() != lib["report_sha256"]:
            raise SystemExit(f"{lib['report']} changed since the runs recorded it")
        failed = [k for k, v in json.loads(f.read_text(encoding="utf-8")).items()
                  if k.startswith("D") and isinstance(v, dict) and v.get("outcome") != "pass"]
        if failed:
            raise SystemExit(f"model report checks not passed: {failed}")
        identity["model_report"] = {"file": lib["report"], "sha256": lib["report_sha256"], "D_checks": "pass"}
    return identity


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reports", nargs="+", type=Path)
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-goals-assessment.json")
    ap.add_argument("--model-suffix", default="-ds", choices=("-ds", "-qg", ""),
                    help="'-ds' (EPC2302DS, primary from 8 October 2026), '-qg' (EPC2302QG, earlier runs) or '' (vendor)")
    args = ap.parse_args()
    cases, vins, used = {}, {}, []
    for r in args.reports:
        rep = json.loads(r.read_text(encoding="utf-8"))
        if rep.get("study") != "goals":
            raise SystemExit(f"{r} is not a goals report")
        n0 = len(cases)
        for k, c in rep["cases"].items():
            suf = next((x for x in ("-qg", "-ds") if k.endswith(x)), "")  # model suffix of the case name
            if suf != args.model_suffix:
                continue
            k = k[:-len(suf)] if suf else k
            if k in cases:
                raise SystemExit(f"case {k} is supplied by more than one report")
            cases[k], vins[k] = c, rep["conditions"]["VIN"]
        if len(cases) > n0:
            used.append((r, rep))
    if not used:
        raise SystemExit(f"no cases for model suffix {args.model_suffix!r}")
    identity = check_inputs(used, args.model_suffix)
    M = {k: metrics(c, vins[k]) for k, c in cases.items()}
    names = sorted({k.split("@")[0] for k in cases})
    out = {}
    for n in names:
        res = {"conditions": {}, "reported_0pH": {}, "corners": {}}
        for a in PRIMARY + REPORTED:
            c, s = M.get(f"{n}@{a}-gear"), M.get(f"stock@{a}-gear")
            row = {"metrics": c, "goals": goals(c, s, vins[f"{n}@{a}-gear"]) if c and s else None}
            (res["conditions"] if a in PRIMARY else res["reported_0pH"])[a] = row
        prim = [res["conditions"][a]["goals"] for a in PRIMARY]
        verdict = {g: (None if any(p is None for p in prim) else combine(p[g] for p in prim))
                   for g in ("S1", "S2", "S3", "S4", "S6", "S7", "S8", "S9", "S10", "S12")}
        loss = {dt: (M.get(f"{n}@ramp-Ls50-gear" + ("" if dt == 10 else f"-dt{dt:g}")) or {}).get("fet_loss_W")
                for dt in DEADS}
        res["dead_time_loss_W"] = loss
        if all(v is not None for v in loss.values()):
            best = min(loss, key=loss.get)
            res["dead_time_optimum_ns"] = best
            verdict["S11"] = 5 <= best <= 15
        else:
            verdict["S11"] = None
        s13 = []
        for tag in CORNERS:
            row = {}
            for a in PRIMARY:
                k = f"{n}@{a}-gear{tag}"
                c, s = M.get(k), M.get(f"stock@{a}-gear{tag}")
                if tag == "-i0" and (c is None or s is None):  # declared fallback
                    k = f"{n}@{a}-gear-i2"
                    c, s = M.get(k), M.get(f"stock@{a}-gear-i2")
                gl = goals(c, s, vins.get(k, 48.0)) if c and s else None
                row[a] = {"case": k, "metrics": c, "S1_S2_S7_S8": None if gl is None else
                          {g: gl[g] for g in ("S1", "S2", "S7", "S8")}}
                s13.append(None if gl is None else combine(gl[g] for g in ("S1", "S2", "S7", "S8")))
            res["corners"][tag] = row
        verdict["S13"] = combine(s13)
        verdict["S5"] = None  # reported dv/dt; the template's limit is unfilled, so undetermined
        res["verdict"] = {g: verdict[g] for g in GOALS}
        res["all_met"] = combine(res["verdict"].values())
        out[n] = res
        print(n, " ".join(f"{g}:{'-' if v is None else 'Y' if v else 'n'}" for g, v in res["verdict"].items()),
              "all:" + ('-' if res["all_met"] is None else 'Y' if res["all_met"] else 'n'))
        for a in PRIMARY + REPORTED:
            r_ = (res["conditions"] if a in PRIMARY else res["reported_0pH"])[a]["metrics"]
            if r_:
                print(f"  {a:10s} Vpk {r_['vpk_V']:5.1f} os {r_['overshoot_V']:5.2f} settle {r_['settling_s'] * 1e9:5.1f} ns "
                      f"tr {r_['tr_s'] * 1e9:4.2f} tf {r_['tf_s'] * 1e9:4.2f} di/dt {r_['didt_A_per_ns']:5.1f} "
                      f"Q2g {r_['q2_gate_peak_V']:4.2f} E {r_['eon_eoff_J'] * 1e6:5.2f} uJ eff {100 * r_['efficiency']:6.3f}")
    args.output.write_text(json.dumps({
        "schema": "epc90133-goals-assessment/2", "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "inputs": {str(r): hashlib.sha256(r.read_bytes()).hexdigest() for r in args.reports},
        "model_identity": identity, "designs": out},
        indent=1, default=lambda o: bool(o) if isinstance(o, np.bool_) else float(o)) + "\n")


if __name__ == "__main__":
    main()
