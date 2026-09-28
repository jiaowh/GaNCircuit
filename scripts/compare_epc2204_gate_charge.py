#!/usr/bin/env python3
"""Compare the model's VGS-QG curve with digitized datasheet Figure 7.

Inputs: results/gan/epc2204-model-curves.json (from epc2204_baseline.py) and
results/gan/epc2204-fig7-digitized.json (from digitize_datasheet_figure.py).

Primary check, fixed here before the comparison was run: at every datasheet
vertex, |VGS_model(Q) - VGS_datasheet(Q)| <= VGS_TOLERANCE. The tolerance was
chosen after the datasheet coordinates had been extracted, but before any
model comparison. Features (plateau voltage and extent, charge at 5 V and at
the threshold voltage) are extracted from both curves with one algorithm and
reported without pass/fail. They make the datasheet table's QGS/QGD/QG(TH)
boundaries comparable with the curve EPC drew.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "results/gan/epc2204-model-curves.json"
DIGITIZED = ROOT / "results/gan/epc2204-fig7-digitized.json"
BASELINE = ROOT / "results/gan/epc2204-baseline.json"
OUTPUT = ROOT / "results/gan/epc2204-fig7-comparison.json"
VGS_TOLERANCE = 0.10  # V; about 3 half-line-widths of the datasheet trace
PLATEAU_BAND = 0.05  # V around the plateau voltage
TABLE = {"qg_nC": 5.7, "qgs_nC": 1.8, "qgd_nC": 0.8, "qg_th_nC": 1.0, "vgs_th_V": 1.1}


def interp(xs, ys, x):
    if x < xs[0] or x > xs[-1]:
        return None
    for i in range(1, len(xs)):
        if xs[i] >= x:
            if xs[i] == xs[i - 1]:
                return ys[i]
            return ys[i - 1] + (ys[i] - ys[i - 1]) * (x - xs[i - 1]) / (xs[i] - xs[i - 1])
    return None


def first_q_at(q, v, level):
    for i in range(1, len(v)):
        if v[i - 1] < level <= v[i]:
            return q[i - 1] + (q[i] - q[i - 1]) * (level - v[i - 1]) / (v[i] - v[i - 1])
    return None


def features(q, v, vth):
    # Plateau voltage: VGS at the flattest stretch of at least 0.2 nC.
    best = None
    for i in range(len(q)):
        j = next((k for k in range(i, len(q)) if q[k] - q[i] >= 0.2), None)
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
            "q_at_vgs_th_nC": first_q_at(q, v, vth),
            "definitions": {"plateau": f"VGS within {PLATEAU_BAND} V of the flattest 0.2 nC stretch",
                            "q_at_vgs_5V": "first charge where VGS reaches 4.98 V (the datasheet trace ends at 4.99 V)",
                            "q_at_vgs_th": f"first charge where VGS reaches {vth:.3f} V"}}


def main():
    model = json.loads(MODEL.read_text())["curves"]["gate_charge_25C_vds50V_16A"]
    dig = json.loads(DIGITIZED.read_text())
    base = json.loads(BASELINE.read_text())
    vth_model = base["datasheet_table"]["vgs_th"]["model"]
    qm = [x * 1e9 for x in model["qg_C"]]
    vm = model["vgs_V"]
    # The bench starts at VGS = v0 (gate hold-down), the datasheet at VGS = 0. Shift the model
    # charge by the charge between 0 and v0, estimated from the initial slope.
    k = next(i for i in range(len(qm)) if vm[i] - vm[0] > 0.05)
    offset = vm[0] * (qm[k] - qm[0]) / (vm[k] - vm[0])
    qm = [x + offset for x in qm]
    qd = [p["qg_nC"] for p in dig["points"]]
    vd = [p["vgs_V"] for p in dig["points"]]
    rows = []
    for q, v in zip(qd, vd):
        vmod = interp(qm, vm, q)
        rows.append({"q_nC": q, "vgs_datasheet_V": v, "vgs_model_V": vmod,
                     "difference_V": None if vmod is None else vmod - v})
    compared = [r for r in rows if r["difference_V"] is not None]
    worst = max(compared, key=lambda r: abs(r["difference_V"]))
    outcome = "pass" if abs(worst["difference_V"]) <= VGS_TOLERANCE else "fail"
    fm = features(qm, vm, vth_model)
    fd = features(qd, vd, TABLE["vgs_th_V"])
    fd_model_vth = features(qd, vd, vth_model)["q_at_vgs_th_nC"]
    report = {
        "schema": "epc2204-fig7-comparison/1",
        "scope": ("Unmodified EPC2204 model (LTspice, reltol 1e-6) against the vendor-drawn typical gate-charge "
                  "curve. Model-to-datasheet consistency only; not a hardware measurement."),
        "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "inputs": {"model_curves_sha256": hashlib.sha256(MODEL.read_bytes()).hexdigest(),
                   "digitized_sha256": hashlib.sha256(DIGITIZED.read_bytes()).hexdigest()},
        "model_charge_offset_nC": offset,
        "primary_check": {"definition": "|VGS_model(Q) - VGS_datasheet(Q)| at every datasheet vertex",
                          "tolerance_V": VGS_TOLERANCE, "vertices_compared": len(compared),
                          "worst": worst, "outcome": outcome,
                          "tolerance_timing": "chosen after extracting datasheet coordinates, before comparing the model"},
        "features": {"model": fm, "datasheet_curve": fd,
                     "datasheet_curve_q_at_model_vgs_th_nC": fd_model_vth},
        "datasheet_table_nC": TABLE,
        "table_vs_curve_observation": {
            "curve_plateau_start_nC": fd["plateau_start_nC"], "table_qgs_nC": TABLE["qgs_nC"],
            "curve_plateau_width_nC": fd["plateau_width_nC"], "table_qgd_nC": TABLE["qgd_nC"],
            "curve_q_at_1p1V_nC": fd["q_at_vgs_th_nC"], "table_qg_th_nC": TABLE["qg_th_nC"],
            "note": ("If the vendor's own curve does not reproduce its table values under these boundary "
                     "definitions, the table uses different (unstated) definitions or different data.")},
        "vertices": rows,
    }
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"outcome": outcome, "worst": worst, "model": {k: v for k, v in fm.items() if k != "definitions"},
                      "datasheet_curve": {k: v for k, v in fd.items() if k != "definitions"},
                      "datasheet_curve_q_at_model_vth": fd_model_vth, "offset_nC": offset}, indent=2))
    return 0 if outcome == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
