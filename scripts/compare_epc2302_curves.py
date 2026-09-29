#!/usr/bin/env python3
"""Compare the unmodified EPC2302 model with digitized datasheet Figs. 1-6 and 8-10.

Fig. 7 (gate charge) is compared by scripts/compare_epc2302_gate_charge.py.
Figs. 11 (safe operating area) and 12 (transient thermal response) are ratings
and thermal data, not outputs of the electrical model, and are not compared.

Inputs:
* results/gan/epc2302-datasheet-figures.json (digitize_datasheet_figures.py, revision 3)
* results/gan/epc2302-model-curves.json (epc2302_baseline.py)
* results/gan/epc2302-model-curves-extra.json (epc2302_curve_benches.py)

Tolerances fixed on 28 September 2026, after the figures were digitized and
before any model curve was compared. They reuse the EPC2204 rule, scaled to
EPC2302's axes: |model - datasheet| <= 5% of |datasheet| + 1% of the axis full
scale, at every datasheet point inside the model's simulated range. Log-scale
capacitance: |log10(model/datasheet)| <= 0.05. Normalized Fig. 9 keeps EPC2204's
0.03. Fig. 10 uses 0.01, 1% of its 0.5-1.5 axis: the whole curve varies by
about 0.025, so 0.03 would not test it.

Curve labels come from physical ordering rules that do not use the values
under test, cross-checked with the legend swatch colours. Fig. 6 has no legend
or arrows; its assignment is checked by integrating the digitized charge curve
(E = integral of V dQ) and comparing with the other curve on the energy axis.
A figure whose two assignments disagree is marked unresolved.
"""
import hashlib
import json
import math
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from compare_epc2204_curves import check_legend, compare, figure, interp, ordered, pts, value_at

FIGS = ROOT / "results/gan/epc2302-datasheet-figures.json"
BASE = ROOT / "results/gan/epc2302-model-curves.json"
EXTRA = ROOT / "results/gan/epc2302-model-curves-extra.json"
OUTPUT = ROOT / "results/gan/epc2302-curve-comparison.json"
DIGITIZER_REVISION = 3

TOL = {  # figure -> (relative, absolute, unit); absolute = 1% of the axis full scale
    "1": (0.05, 4.0, "A"), "2": (0.05, 4.0, "A"), "8": (0.05, 4.0, "A"),
    "3": (0.05, 0.06, "mOhm"), "4": (0.05, 0.06, "mOhm"),
    "5a": (0.05, 40.0, "pF"), "5b": ("log", 0.05, "decades"),
    "6q": (0.05, 1.44, "nC"), "6e": (0.05, 0.06, "uJ"),
    "9": (0.0, 0.03, "normalized"), "10": (0.0, 0.01, "normalized"),
}
FIG6_ASSIGNMENT_TOLERANCE = 0.10  # relative, integrated-charge energy vs the energy curve at the largest common VDS
DRAIN_CURRENTS_FIG3 = (25, 50, 75, 100)

PARSERS = {
    "1": lambda t: (lambda m: f"VGS={m.group(1)}V" if m else None)(re.search(r"(\d)\s*V\b", t)),
    "2": lambda t: (lambda m: f"{m.group(1)}C" if m else None)(re.search(r"(\d+)\s*˚C", t)),
    # EPC2302 Fig. 3 sets "ID" on its own line; the legend lines read "= 25 A".
    "3": lambda t: (lambda m: f"ID={m.group(1)}A" if m else None)(re.search(r"=\s*(\d+)\s*A", t)),
    "5": lambda t: next((k for k in ("COSS", "CISS", "CRSS") if k in t.split()), None),
}
PARSERS["4"] = PARSERS["8"] = PARSERS["2"]


def main():
    figs = json.loads(FIGS.read_text(encoding="utf-8"))["figures"]
    base = json.loads(BASE.read_text())["curves"]
    extra = json.loads(EXTRA.read_text())["curves"]
    results = {}

    f = figure(figs, 1)
    common = min(max(p[0] for p in pts(c)) for c in f["curves"])
    order = sorted(f["curves"], key=lambda c: value_at(pts(c), common), reverse=True)
    res = {"assignment_rule": f"current at VDS = {common:.2f} V decreases with VGS", "curves": {}}
    for vgs, c in zip((5, 4, 3, 2), order):
        m = base["output_25C"][f"vgs_{vgs}V"]
        res["curves"][f"VGS={vgs}V"] = dict(compare(pts(c), m["vds_V"], m["id_A"], TOL["1"]), color=c["color"])
    check_legend(res, f, PARSERS["1"])
    results["Figure 1"] = res

    f = figure(figs, 2)
    if len(f["curves"]) != 2:
        raise SystemExit(f"expected two Fig. 2 curves, found {len(f['curves'])}")
    common = min(max(p[0] for p in pts(c)) for c in f["curves"])
    cold, hot = sorted(f["curves"], key=lambda c: value_at(pts(c), common), reverse=True)
    res = {"assignment_rule": f"at VGS = {common:.2f} V the 125 C curve carries less current", "curves": {}}
    for t, c in ((25, cold), (125, hot)):
        m = base[f"transfer_vds3V_{t}C"]
        res["curves"][f"{t}C"] = dict(compare(pts(c), m["vgs_V"], m["id_A"], TOL["2"]), color=c["color"])
    check_legend(res, f, PARSERS["2"])
    results["Figure 2"] = res

    f = figure(figs, 3)
    common = max(min(p[0] for p in pts(c)) for c in f["curves"])
    order = sorted(f["curves"], key=lambda c: value_at(pts(c), common))
    res = {"assignment_rule": f"at VGS = {common:.2f} V (lowest VGS all curves reach) RDS(on) rises with drain current",
           "curves": {}}
    for i_d, c in zip(DRAIN_CURRENTS_FIG3, order):
        m = extra["rds_vs_vgs_25C"][f"id_{i_d}A"]
        res["curves"][f"ID={i_d}A"] = dict(compare(pts(c), m["vgs_V"], m["rds_mohm"], TOL["3"]), color=c["color"])
    check_legend(res, f, PARSERS["3"])
    results["Figure 3"] = res

    f = figure(figs, 4)
    cold, hot = sorted(f["curves"], key=lambda c: value_at(pts(c), 5.0) or math.inf)
    res = {"assignment_rule": "the 125 C curve has the higher RDS(on) at VGS = 5 V", "curves": {}}
    m25, m125 = extra["rds_vs_vgs_25C"]["id_50A"], extra["rds_vs_vgs_125C_50A"]
    res["curves"]["25C"] = dict(compare(pts(cold), m25["vgs_V"], m25["rds_mohm"], TOL["4"]), color=cold["color"])
    res["curves"]["125C"] = dict(compare(pts(hot), m125["vgs_V"], m125["rds_mohm"], TOL["4"]), color=hot["color"])
    check_legend(res, f, PARSERS["4"])
    results["Figure 4"] = res

    cc, coss = extra["ciss_crss_25C"], base["coss_25C"]
    model5 = {"CISS": (cc["vds_V"], cc["ciss_pF"]), "CRSS": (cc["vds_V"], cc["crss_pF"]),
              "COSS": (coss["vds_V"], [c * 1e12 for c in coss["coss_F"]])}
    for num in ("5a", "5b"):
        f = figure(figs, num)
        common = min(max(p[0] for p in pts(c)) for c in f["curves"])
        order = sorted(f["curves"], key=lambda c: value_at(pts(c), common), reverse=True)
        res = {"assignment_rule": f"CISS > COSS > CRSS at VDS = {common:.1f} V (largest VDS all curves reach)",
               "curves": {}}
        for name, c in zip(("CISS", "COSS", "CRSS"), order):
            res["curves"][name] = dict(compare(pts(c), *model5[name], TOL[num]), color=c["color"])
        check_legend(res, f, PARSERS["5"])
        results[f"Figure {num}"] = res

    # Figure 6: QOSS (left axis, nC) is concave in VDS; EOSS (right axis, uJ) is not.
    f = figure(figs, 6)
    end = min(max(p[0] for p in pts(c, "y_left")) for c in f["curves"])
    concavity = lambda c: value_at(pts(c, "y_left"), 20.0) / value_at(pts(c, "y_left"), end)
    q_curve, e_curve = sorted(f["curves"], key=concavity, reverse=True)
    qx, qy = ordered([p[0] for p in pts(q_curve, "y_left")], [p[1] for p in pts(q_curve, "y_left")])
    e_from_q = [0.0]
    for i in range(1, len(qx)):
        e_from_q.append(e_from_q[-1] + 0.5 * (qx[i] + qx[i - 1]) * (qy[i] - qy[i - 1]) * 1e-3)  # V*nC -> uJ
    e_end = min(qx[-1], max(p[0] for p in pts(e_curve, "y_right")))
    e_int, e_drawn = interp(qx, e_from_q, e_end), value_at(pts(e_curve, "y_right"), e_end)
    assignment_ok = abs(e_int / e_drawn - 1) <= FIG6_ASSIGNMENT_TOLERANCE
    v, c_f = coss["vds_V"], coss["coss_F"]
    q, e = [0.0], [0.0]
    for i in range(1, len(v)):
        dv = v[i] - v[i - 1]
        q.append(q[-1] + 0.5 * (c_f[i] + c_f[i - 1]) * dv)
        e.append(e[-1] + 0.5 * (c_f[i] * v[i] + c_f[i - 1] * v[i - 1]) * dv)
    res = {"assignment_rule": f"QOSS(20 V)/QOSS({end:.1f} V) exceeds the same ratio for EOSS (charge is concave)",
           "legend_check": {"agree": assignment_ok,
                            "method": ("no legend or arrows in EPC2302 Fig. 6; integral of V dQ along the digitized "
                                       f"charge curve compared with the energy curve at {e_end:.1f} V"),
                            "energy_from_charge_curve_uJ": e_int, "energy_curve_uJ": e_drawn,
                            "tolerance_relative": FIG6_ASSIGNMENT_TOLERANCE},
           "model_method": "trapezoid integration of the small-signal COSS curve from 0 V", "curves": {}}
    res["curves"]["QOSS"] = dict(compare(pts(q_curve, "y_left"), v, [x * 1e9 for x in q], TOL["6q"]), color=q_curve["color"])
    res["curves"]["EOSS"] = dict(compare(pts(e_curve, "y_right"), v, [x * 1e6 for x in e], TOL["6e"]), color=e_curve["color"])
    if not assignment_ok:
        for c in res["curves"].values():
            c["outcome"] = "unresolved"
    results["Figure 6"] = res

    f = figure(figs, 8)
    common = min(max(p[0] for p in pts(c)) for c in f["curves"])
    cold, hot = sorted(f["curves"], key=lambda c: value_at(pts(c), common), reverse=True)
    res = {"assignment_rule": f"at VSD = {common:.2f} V the 125 C curve carries less current", "curves": {}}
    for t, c in ((25, cold), (125, hot)):
        m = extra[f"reverse_{t}C"]
        res["curves"][f"{t}C"] = dict(compare(pts(c), m["vsd_V"], m["isd_A"], TOL["8"]), color=c["color"])
    check_legend(res, f, PARSERS["8"])
    results["Figure 8"] = res

    for num, key, note in (("9", "rds_on_vs_temperature_50A_5V", "RDS(on) at 50 A, VGS = 5 V, normalized to 25 C"),
                           ("10", "vgs_th_vs_temperature_14mA", "VGS(th) at 14 mA, normalized to 25 C")):
        f = figure(figs, num)
        if len(f["curves"]) != 1:
            raise SystemExit(f"expected one Fig. {num} curve, found {len(f['curves'])}")
        m = extra[key]
        results[f"Figure {num}"] = {
            "curves": {"normalized": dict(compare(pts(f["curves"][0]), m["tj_C"], m["normalized"], TOL[num]),
                                          color=f["curves"][0]["color"])},
            "model_note": f"{note}; model points every 12.5 C from 0 to 150 C, linearly interpolated"}

    temp_colors = {name: {k: tuple(v["color"]) for k, v in r["curves"].items()}
                   for name, r in results.items() if name in ("Figure 2", "Figure 4", "Figure 8")}
    consistent = len({(c["25C"], c["125C"]) for c in temp_colors.values()}) == 1
    legend_agreement = {name: r.get("legend_check", {}).get("agree") for name, r in results.items()}
    summary = {}
    for name, r in results.items():
        for cname, c in r["curves"].items():
            summary[f"{name} {cname}"] = {"outcome": c["outcome"], "points": c["points_compared"],
                                          "fraction_within": c["fraction_within"],
                                          "worst_ratio": c["worst"]["ratio"] if c["worst"] else None,
                                          "worst_at_x": c["worst"]["x"] if c["worst"] else None}
    report = {"schema": "epc2302-curve-comparison/1",
              "scope": ("Unmodified EPC2302 model (LTspice, reltol 1e-6) against vendor-drawn typical curves. "
                        "Model-to-datasheet consistency only; not a hardware measurement."),
              "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "inputs": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (FIGS, BASE, EXTRA)},
              "tolerances": {k: {"relative": t[0], "absolute": t[1], "unit": t[2]} for k, t in TOL.items()},
              "tolerance_timing": "fixed after digitizing, before any model curve was compared (Fig. 7 separate)",
              "not_compared": {"Figure 11": "safe operating area (rating)", "Figure 12": "transient thermal response"},
              "temperature_colour_consistency": {"consistent": consistent, "colours": temp_colors},
              "legend_agreement": legend_agreement,
              "digitizer_revision": DIGITIZER_REVISION,
              "summary": summary, "figures": results}
    OUTPUT.write_text(json.dumps(report, indent=1) + "\n")
    for k, s in summary.items():
        w = s["worst_ratio"]
        fw = s["fraction_within"]
        print(f"{k:24s} {s['outcome']:11s} n={s['points']:3d} within={'-' if fw is None else round(fw, 3)} "
              f"worst={'-' if w is None else round(w, 2)} at x={'-' if s['worst_at_x'] is None else round(s['worst_at_x'], 3)}")
    print("temperature colours consistent:", consistent)
    print("legend agreement:", legend_agreement)
    return 0 if all(s["outcome"] == "pass" for s in summary.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
