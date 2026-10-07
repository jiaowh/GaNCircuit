#!/usr/bin/env python3
"""Compare the unmodified EPC2302 model's VGS-QG curve with digitized datasheet Fig. 7.

Inputs: results/gan/epc2302-model-curves.json and results/gan/epc2302-baseline.json
(scripts/epc2302_baseline.py), and results/gan/epc2302-datasheet-figures.json
(scripts/digitize_datasheet_figures.py, revision 3). Fig. 7 conditions, read from
the plot: ID = 50 A, VDS = 50 V; the model bench uses the same.

Checks fixed on 28 September 2026 after the datasheet curve was digitized and
before any model comparison:

* vertical: |VGS_model(Q) - VGS_datasheet(Q)| <= 0.10 V at every datasheet vertex
  (2% of the 5 V axis, the EPC2204 tolerance);
* horizontal, off the plateau: at VGS = 1.0, 1.5, 2.0, 3.0, 3.5, 4.0, 4.5 V,
  |Q_model(V) - Q_datasheet(V)| <= 5% of Q_datasheet + 0.25 nC (1% of the 25 nC axis).
  The vertical check alone is blind to charge shifts along the flat plateau.

Features (plateau voltage and extent, charge at 5 V, charge at the datasheet
threshold 1.3 V and at the model threshold) are extracted from both curves with
one algorithm and reported without pass/fail. They put the table's QGS/QGD/QG(TH)
next to what EPC's own curve shows; they do not establish why the table differs.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from compare_epc2204_gate_charge import first_q_at, interp
from epc2204_baseline import equation_gate_charge, subckt_params

MODEL = ROOT / "results/gan/epc2302-model-curves.json"
DIGITIZED = ROOT / "results/gan/epc2302-datasheet-figures.json"
BASELINE = ROOT / "results/gan/epc2302-baseline.json"
OUTPUT = ROOT / "results/gan/epc2302-fig7-comparison.json"
LIBRARY = ROOT / "vendor/epc/ltspice/EPCGaNLibrary.lib"
CURVE_KEY = "gate_charge_25C_vds50V_50A"
VGS_TOLERANCE = 0.10  # V
Q_REL, Q_ABS = 0.05, 0.25  # relative, nC
Q_LEVELS = (1.0, 1.5, 2.0, 3.0, 3.5, 4.0, 4.5)  # V, away from the ~2.4 V plateau
PLATEAU_STRETCH = 0.8  # nC; EPC2204's 0.2 nC scaled by QG (23 / 5.7)
PLATEAU_BAND = 0.05  # V around the plateau voltage
TABLE = {"qg_nC": 23.0, "qgs_nC": 8.9, "qgd_nC": 2.3, "qg_th_nC": 6.3, "vgs_th_V": 1.3}


def features(q, v, vth_levels):
    best = None
    for i in range(len(q)):
        j = next((k for k in range(i, len(q)) if q[k] - q[i] >= PLATEAU_STRETCH), None)
        if j is None:
            break
        slope = (v[j] - v[i]) / (q[j] - q[i])
        if best is None or slope < best[0]:
            best = (slope, (v[i] + v[j]) / 2)
    vp = best[1]
    inside = [i for i in range(len(q)) if abs(v[i] - vp) <= PLATEAU_BAND]
    return {"plateau_vgs_V": vp,
            "plateau_start_nC": q[inside[0]], "plateau_end_nC": q[inside[-1]],
            "plateau_width_nC": q[inside[-1]] - q[inside[0]],
            "q_at_vgs_5V_nC": first_q_at(q, v, 4.98),
            "q_at_vgs_th_nC": {f"{name} ({level:.3f} V)": first_q_at(q, v, level) for name, level in vth_levels.items()},
            "definitions": {"plateau": f"VGS within {PLATEAU_BAND} V of the flattest {PLATEAU_STRETCH} nC stretch",
                            "q_at_vgs_5V": "first charge where VGS reaches 4.98 V",
                            "q_at_vgs_th": "first charge where VGS reaches the stated threshold"}}


def datasheet_curve():
    """Digitized Fig. 7 trace (charge nC, VGS V)."""
    fig7 = next(f for f in json.loads(DIGITIZED.read_text(encoding="utf-8"))["figures"]
                if f["caption"].startswith("Figure 7:"))
    if len(fig7["curves"]) != 1:
        raise SystemExit(f"expected one Fig. 7 curve, found {len(fig7['curves'])}")
    trace = fig7["curves"][0]["points_by_axis"]["y_left"]
    return [p[0] for p in trace], [p[1] for p in trace]


def evaluate(qm, vm, vth_model):
    """The declared vertical and horizontal checks and the features, for a model curve already offset to VGS = 0.

    Also used by scripts/epc2302_qg_variant.py, so a model revision is judged by the same checks."""
    qd, vd = datasheet_curve()

    rows = []
    for q, v in zip(qd, vd):
        vmod = interp(qm, vm, q)
        rows.append({"q_nC": q, "vgs_datasheet_V": v, "vgs_model_V": vmod,
                     "difference_V": None if vmod is None else vmod - v})
    compared = [r for r in rows if r["difference_V"] is not None]
    worst = max(compared, key=lambda r: abs(r["difference_V"]))
    vertical = {"definition": "|VGS_model(Q) - VGS_datasheet(Q)| at every datasheet vertex",
                "tolerance_V": VGS_TOLERANCE, "vertices_compared": len(compared), "vertices_total": len(rows),
                "fraction_within": sum(abs(r["difference_V"]) <= VGS_TOLERANCE for r in compared) / len(compared),
                "worst": worst, "outcome": "pass" if abs(worst["difference_V"]) <= VGS_TOLERANCE else "fail"}

    hrows = []
    for level in Q_LEVELS:
        q_ds, q_mod = first_q_at(qd, vd, level), first_q_at(qm, vm, level)
        if q_ds is None or q_mod is None:
            hrows.append({"vgs_V": level, "q_datasheet_nC": q_ds, "q_model_nC": q_mod, "outcome": "not-compared"})
            continue
        allowed = Q_REL * q_ds + Q_ABS
        hrows.append({"vgs_V": level, "q_datasheet_nC": q_ds, "q_model_nC": q_mod, "difference_nC": q_mod - q_ds,
                      "allowed_nC": allowed, "outcome": "pass" if abs(q_mod - q_ds) <= allowed else "fail"})
    done = [r for r in hrows if r["outcome"] != "not-compared"]
    horizontal = {"definition": "charge at which each curve first reaches VGS, off the plateau",
                  "tolerance": {"relative": Q_REL, "absolute_nC": Q_ABS}, "rows": hrows,
                  "outcome": ("not-compared" if not done else
                              "pass" if all(r["outcome"] == "pass" for r in done) else "fail")}

    levels = {"datasheet VGS(th)": TABLE["vgs_th_V"], "model VGS(th)": vth_model}
    fm, fd = features(qm, vm, levels), features(qd, vd, levels)
    return vertical, horizontal, fm, fd, rows


def main():
    model = json.loads(MODEL.read_text())["curves"][CURVE_KEY]
    base = json.loads(BASELINE.read_text())
    vth_model = base["datasheet_table"]["vgs_th"]["model"]
    qm = [x * 1e9 for x in model["qg_C"]]
    vm = model["vgs_V"]
    # The bench starts at VGS = v0 (gate hold-down), the datasheet at 0 V. Shift the model
    # charge by the model's own charge from VGS = 0 to the simulated start state. The first
    # run used EPC2204's initial-slope estimate; on the downsampled curve it gave 0.34 nC
    # against 0.47 nC from the equations, so it was replaced after the declared checks failed.
    k = next(i for i in range(len(qm)) if vm[i] - vm[0] > 0.05)
    slope_offset = vm[0] * (qm[k] - qm[0]) / (vm[k] - vm[0])
    start = base["checks_and_definitions"]["gate_charge_checks"]["starting_bias"]
    P = subckt_params(LIBRARY.read_text(encoding="utf-8", errors="replace"), "EPC2302")
    offset = 1e9 * equation_gate_charge(P, (0.0, start["vds_V"], 0.0, 0.0),
                                        (start["vgs_V"], start["vds_V"], start["fet_drain_current_A"], 0.0))
    qm = [x + offset for x in qm]
    vertical, horizontal, fm, fd, rows = evaluate(qm, vm, vth_model)
    report = {
        "schema": "epc2302-fig7-comparison/1",
        "scope": ("Unmodified EPC2302 model (LTspice, reltol 1e-6) against the vendor-drawn typical gate-charge "
                  "curve. Model-to-datasheet consistency only; not a hardware measurement."),
        "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "inputs": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (MODEL, DIGITIZED, BASELINE)},
        "figure_conditions": "ID = 50 A, VDS = 50 V (read from the plot)",
        "model_charge_offset_nC": {"used": offset, "method": "model charge equations, VGS 0 -> bench start state",
                                   "initial_slope_estimate_first_run": slope_offset,
                                   "change_timing": "replaced after the first run's declared checks failed; "
                                                    "both checks failed with either offset"},
        "tolerance_timing": "fixed after the datasheet curve was digitized, before any model comparison",
        "vertical_check": vertical,
        "horizontal_check": horizontal,
        "features": {"model": fm, "datasheet_curve": fd},
        "datasheet_table_nC": TABLE,
        "table_vs_curve_observation": {
            "table_qg_th_nC": TABLE["qg_th_nC"],
            "datasheet_curve_q_at_thresholds_nC": fd["q_at_vgs_th_nC"],
            "model_q_at_thresholds_nC": fm["q_at_vgs_th_nC"],
            "table_qgs_nC": TABLE["qgs_nC"], "datasheet_curve_plateau_start_nC": fd["plateau_start_nC"],
            "table_qgd_nC": TABLE["qgd_nC"], "datasheet_curve_plateau_width_nC": fd["plateau_width_nC"],
            "note": ("Observation only. Where EPC's curve and EPC's table disagree under these boundaries, the cause "
                     "(definitions, source data, or something else) is not established by this comparison.")},
        "vertices": rows,
    }
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"vertical": {k: vertical[k] for k in ("outcome", "fraction_within", "worst")},
                      "horizontal": [{k: r.get(k) for k in ("vgs_V", "q_datasheet_nC", "q_model_nC", "outcome")}
                                     for r in horizontal["rows"]],
                      "model": {k: v for k, v in fm.items() if k != "definitions"},
                      "datasheet_curve": {k: v for k, v in fd.items() if k != "definitions"},
                      "offset_nC": offset}, indent=2))
    return 0 if vertical["outcome"] == "pass" and horizontal["outcome"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
