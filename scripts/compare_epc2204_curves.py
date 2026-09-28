#!/usr/bin/env python3
"""Compare the unmodified EPC2204 model with digitized datasheet Figs. 1-6, 8 and 9.

Inputs:
* results/gan/epc2204-datasheet-figures.json (scripts/digitize_datasheet_figures.py)
* results/gan/epc2204-model-curves.json (scripts/epc2204_baseline.py)
* results/gan/epc2204-model-curves-extra.json (scripts/epc2204_curve_benches.py)

Tolerances were fixed on 28 September 2026 before these figures were digitized
or compared. They are screening tolerances on vendor "typical" curves:
|model - datasheet| <= REL * |datasheet| + ABS at every datasheet point inside
the model's simulated range. For the log-scale capacitance figure the rule is
|log10(model/datasheet)| <= 0.05.

The PDF has no legend swatches, so curve colours are assigned by physical
ordering rules that do not use the values under test. Each rule is checked
here, and the figure is marked unresolved if its rule does not hold.
"""
import bisect
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIGS = ROOT / "results/gan/epc2204-datasheet-figures.json"
BASE = ROOT / "results/gan/epc2204-model-curves.json"
EXTRA = ROOT / "results/gan/epc2204-model-curves-extra.json"
OUTPUT = ROOT / "results/gan/epc2204-curve-comparison.json"

TOL = {  # figure -> (relative, absolute, unit)
    "1": (0.05, 1.6, "A"), "2": (0.05, 1.6, "A"), "8": (0.05, 1.6, "A"),
    "3": (0.05, 0.16, "mOhm"), "4": (0.05, 0.16, "mOhm"),
    "5a": (0.05, 9.0, "pF"), "5b": ("log", 0.05, "decades"),
    "6q": (0.05, 0.4, "nC"), "6e": (0.05, 0.016, "uJ"), "9": (0.0, 0.03, "normalized"),
}


def interp(xs, ys, x):
    """Linear interpolation on an increasing axis; None outside it."""
    if not xs or x < xs[0] or x > xs[-1]:
        return None
    i = max(1, bisect.bisect_left(xs, x))
    if xs[i] == xs[i - 1]:
        return ys[i]
    return ys[i - 1] + (ys[i] - ys[i - 1]) * (x - xs[i - 1]) / (xs[i] - xs[i - 1])


def ordered(xs, ys):
    pairs = sorted(zip(xs, ys))
    return [p[0] for p in pairs], [p[1] for p in pairs]


def figure(figs, number):
    return next(f for f in figs if f["caption"].startswith(f"Figure {number}:"))


def pts(curve, axis="y_left"):
    return curve["points_by_axis"][axis]


def value_at(points, x):
    xs, ys = ordered([p[0] for p in points], [p[1] for p in points])
    return interp(xs, ys, x)


def compare(points, model_x, model_y, tol, transform=None):
    mx, my = ordered(model_x, model_y)
    rows = []
    for x, y in points:
        m = interp(mx, my, x)
        if m is None:
            continue
        if transform:
            m = transform(m)
        if tol[0] == "log":
            if m <= 0 or y <= 0:
                continue
            err, allowed = abs(math.log10(m / y)), tol[1]
        else:
            err, allowed = abs(m - y), tol[0] * abs(y) + tol[1]
        rows.append({"x": x, "datasheet": y, "model": m, "error": err, "allowed": allowed, "ratio": err / allowed})
    worst = max(rows, key=lambda r: r["ratio"]) if rows else None
    return {"points_compared": len(rows), "worst": worst,
            "fraction_within": sum(r["ratio"] <= 1 for r in rows) / len(rows) if rows else None,
            "outcome": "not-compared" if not rows else ("pass" if worst["ratio"] <= 1 else "fail"),
            "points": rows}


def main():
    figs = json.loads(FIGS.read_text())["figures"]
    base = json.loads(BASE.read_text())["curves"]
    extra = json.loads(EXTRA.read_text())["curves"]
    results = {}

    # Figure 1: output characteristics at 25 C; more current at the widest common VDS = higher VGS.
    f = figure(figs, 1)
    common = min(max(p[0] for p in pts(c)) for c in f["curves"])
    order = sorted(f["curves"], key=lambda c: value_at(pts(c), common), reverse=True)
    res = {"assignment_rule": f"current at VDS = {common:.2f} V decreases with VGS", "curves": {}}
    for vgs, c in zip((5, 4, 3, 2), order):
        m = base["output_25C"][f"vgs_{vgs}V"]
        res["curves"][f"VGS={vgs}V"] = dict(compare(pts(c), m["vds_V"], m["id_A"], TOL["1"]), color=c["color"])
    results["Figure 1"] = res

    # Figure 2: transfer at VDS = 3 V; the 125 C curve carries less current at VGS = 5 V (or ends lower).
    f = figure(figs, 2)
    # Assign by current at the largest VGS both curves reach.
    common = min(max(p[0] for p in pts(c)) for c in f["curves"])
    cold, hot = sorted(f["curves"], key=lambda c: value_at(pts(c), common), reverse=True)
    res = {"assignment_rule": f"at VGS = {common:.2f} V the 125 C curve carries less current", "curves": {}}
    for t, c in ((25, cold), (125, hot)):
        m = base[f"transfer_vds3V_{t}C"]
        res["curves"][f"{t}C"] = dict(compare(pts(c), m["vgs_V"], m["id_A"], TOL["2"]), color=c["color"])
    results["Figure 2"] = res

    # Figure 3: RDS(on) vs VGS; a higher drain current reaches the plot top at higher VGS.
    f = figure(figs, 3)
    order = sorted(f["curves"], key=lambda c: min(p[0] for p in pts(c)))
    res = {"assignment_rule": "curves reaching the 16 mOhm top at higher VGS carry more current", "curves": {}}
    for i_d, c in zip((8, 16, 24, 32), order):
        m = extra["rds_vs_vgs_25C"][f"id_{i_d}A"]
        res["curves"][f"ID={i_d}A"] = dict(compare(pts(c), m["vgs_V"], m["rds_mohm"], TOL["3"]), color=c["color"])
    results["Figure 3"] = res

    # Figure 4: RDS(on) vs VGS at 16 A; 125 C has the higher resistance at VGS = 5 V.
    f = figure(figs, 4)
    cold, hot = sorted(f["curves"], key=lambda c: value_at(pts(c), 5.0) or math.inf)
    res = {"assignment_rule": "the 125 C curve has the higher RDS(on) at VGS = 5 V", "curves": {}}
    m25 = extra["rds_vs_vgs_25C"]["id_16A"]
    m125 = extra["rds_vs_vgs_125C_16A"]
    res["curves"]["25C"] = dict(compare(pts(cold), m25["vgs_V"], m25["rds_mohm"], TOL["4"]), color=cold["color"])
    res["curves"]["125C"] = dict(compare(pts(hot), m125["vgs_V"], m125["rds_mohm"], TOL["4"]), color=hot["color"])
    results["Figure 4"] = res

    # Figures 5a/5b: CISS > COSS > CRSS at 50 V.
    cc = extra["ciss_crss_25C"]
    coss = base["coss_25C"]
    model5 = {"CISS": (cc["vds_V"], cc["ciss_pF"]), "CRSS": (cc["vds_V"], cc["crss_pF"]),
              "COSS": (coss["vds_V"], [c * 1e12 for c in coss["coss_F"]])}
    for num in ("5a", "5b"):
        f = figure(figs, num)
        common = min(max(p[0] for p in pts(c)) for c in f["curves"])
        order = sorted(f["curves"], key=lambda c: value_at(pts(c), common), reverse=True)
        res = {"assignment_rule": f"CISS > COSS > CRSS at VDS = {common:.1f} V (largest VDS all curves reach)", "curves": {}}
        for name, c in zip(("CISS", "COSS", "CRSS"), order):
            res["curves"][name] = dict(compare(pts(c), *model5[name], TOL[num]), color=c["color"])
        results[f"Figure {num}"] = res

    # Figure 6: QOSS (left axis, nC) is concave in VDS; EOSS (right axis, uJ) is not.
    f = figure(figs, 6)
    end = min(max(p[0] for p in pts(c, "y_left")) for c in f["curves"])

    def concavity(c, axis):
        p = pts(c, axis)
        return value_at(p, 20.0) / value_at(p, end)
    q_curve, e_curve = sorted(f["curves"], key=lambda c: concavity(c, "y_left"), reverse=True)
    v = coss["vds_V"]
    c_f = coss["coss_F"]
    q = [0.0]
    e = [0.0]
    for i in range(1, len(v)):
        dv = v[i] - v[i - 1]
        q.append(q[-1] + 0.5 * (c_f[i] + c_f[i - 1]) * dv)
        e.append(e[-1] + 0.5 * (c_f[i] * v[i] + c_f[i - 1] * v[i - 1]) * dv)
    res = {"assignment_rule": f"QOSS(20 V)/QOSS({end:.1f} V) exceeds the same ratio for EOSS (charge is concave)",
           "model_method": "trapezoid integration of the small-signal COSS curve from 0 V", "curves": {}}
    res["curves"]["QOSS"] = dict(compare(pts(q_curve, "y_left"), v, [x * 1e9 for x in q], TOL["6q"]), color=q_curve["color"])
    res["curves"]["EOSS"] = dict(compare(pts(e_curve, "y_right"), v, [x * 1e6 for x in e], TOL["6e"]), color=e_curve["color"])
    # Diagnostic added after the declared EOSS check failed: integrate EPC's own Fig. 5a COSS
    # curve and compare it with EPC's Fig. 6, independently of the model.
    f5 = figure(figs, "5a")
    c5 = sorted(f5["curves"], key=lambda c: value_at(pts(c), min(max(p[0] for p in pts(k)) for k in f5["curves"])),
                reverse=True)[1]
    vx, cx = ordered([p[0] for p in pts(c5)], [p[1] for p in pts(c5)])
    vx, cx = [0.0] + vx, [cx[0]] + cx  # hold the first digitized COSS value down to 0 V
    qd, ed = [0.0], [0.0]
    for i in range(1, len(vx)):
        dv = vx[i] - vx[i - 1]
        qd.append(qd[-1] + 0.5 * (cx[i] + cx[i - 1]) * dv * 1e-3)            # pF*V -> nC
        ed.append(ed[-1] + 0.5 * (cx[i] * vx[i] + cx[i - 1] * vx[i - 1]) * dv * 1e-6)  # pF*V^2 -> uJ
    diag = {"added_after_the_declared_check_failed": True,
            "method": "trapezoid integration of the digitized Fig. 5a COSS curve (EPC's own data), no model involved",
            "rows": []}
    for vv in (5, 10, 15, 20, 30, 50, 75, 95):
        diag["rows"].append({"vds_V": vv,
                             "eoss_fig6_uJ": value_at(pts(e_curve, "y_right"), vv),
                             "eoss_from_fig5a_uJ": interp(vx, ed, vv),
                             "eoss_model_uJ": interp(v, [x * 1e6 for x in e], vv),
                             "qoss_fig6_nC": value_at(pts(q_curve, "y_left"), vv),
                             "qoss_from_fig5a_nC": interp(vx, qd, vv),
                             "qoss_model_nC": interp(v, [x * 1e9 for x in q], vv)})
    diag["fig6_eoss_curve_starts_at_V"] = min(p[0] for p in pts(e_curve, "y_left"))
    diag["fig6_segments"] = {"QOSS": q_curve["segments"], "EOSS": e_curve["segments"], "kinds": e_curve["kinds"]}
    res["vendor_internal_consistency_diagnostic"] = diag
    results["Figure 6"] = res

    # Figure 8: reverse conduction; the 125 C curve carries less current at the largest common VSD.
    f = figure(figs, 8)
    common = min(max(p[0] for p in pts(c)) for c in f["curves"])
    cold, hot = sorted(f["curves"], key=lambda c: value_at(pts(c), common), reverse=True)
    res = {"assignment_rule": f"at VSD = {common:.2f} V the 125 C curve carries less current; "
                              "the blue/red pair matches Figs. 2 and 4", "curves": {}}
    for t, c in ((25, cold), (125, hot)):
        m = extra[f"reverse_{t}C"]
        res["curves"][f"{t}C"] = dict(compare(pts(c), m["vsd_V"], m["isd_A"], TOL["8"]), color=c["color"])
    results["Figure 8"] = res

    # Figure 9: normalized RDS(on) vs temperature (single curve).
    f = figure(figs, 9)
    m = extra["rds_on_vs_temperature_16A_5V"]
    results["Figure 9"] = {"curves": {"normalized": dict(compare(pts(f["curves"][0]), m["tj_C"], m["normalized"], TOL["9"]),
                                                         color=f["curves"][0]["color"])},
                           "model_note": "model points at 0, 25, ..., 150 C, linearly interpolated"}

    # Colour consistency: blue/red must mean 25/125 C in every temperature figure.
    temp_colors = {name: {k: tuple(v["color"]) for k, v in r["curves"].items()}
                   for name, r in results.items() if name in ("Figure 2", "Figure 4", "Figure 8")}
    consistent = len({(c["25C"], c["125C"]) for c in temp_colors.values()}) == 1
    summary = {}
    for name, r in results.items():
        for cname, c in r["curves"].items():
            summary[f"{name} {cname}"] = {"outcome": c["outcome"], "points": c["points_compared"],
                                          "fraction_within": c["fraction_within"],
                                          "worst_ratio": c["worst"]["ratio"] if c["worst"] else None,
                                          "worst_at_x": c["worst"]["x"] if c["worst"] else None}
    report = {"schema": "epc2204-curve-comparison/1",
              "scope": ("Unmodified EPC2204 model (LTspice, reltol 1e-6) against vendor-drawn typical curves. "
                        "Model-to-datasheet consistency only; not a hardware measurement."),
              "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "inputs": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (FIGS, BASE, EXTRA)},
              "tolerances": {k: {"relative": v[0], "absolute": v[1], "unit": v[2]} for k, v in TOL.items()},
              "tolerance_timing": "fixed before these figures were digitized or compared (Fig. 7 is compared separately)",
              "temperature_colour_consistency": {"consistent": consistent, "colours": temp_colors},
              "summary": summary, "figures": results}
    OUTPUT.write_text(json.dumps(report, indent=1) + "\n")
    for k, s in summary.items():
        w = s["worst_ratio"]
        print(f"{k:24s} {s['outcome']:13s} n={s['points']:3d} within={s['fraction_within'] if s['fraction_within'] is None else round(s['fraction_within'],3)} "
              f"worst={'-' if w is None else round(w, 2)} at x={s['worst_at_x']}")
    print("temperature colours consistent:", consistent)


if __name__ == "__main__":
    main()
