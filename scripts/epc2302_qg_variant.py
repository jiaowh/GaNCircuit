#!/usr/bin/env python3
"""EPC2302 gate-charge sensitivity variant: a separate model revision that follows datasheet Fig. 7.

Purpose (owner request, 7 October 2026). The unmodified EPC2302 model fails its declared Fig. 7
checks: its Miller plateau is 2.19 nC wide against 2.87 nC on EPC's curve, and it is 0.23-0.53 nC low
below the plateau (results/gan/epc2302-fig7-comparison.json). R80 1.5 ohm, the provisional design
candidate, acts by slowing that plateau, so its predicted benefit and loss cost may depend on which
curve describes the real device. This script builds a variant that follows the drawn curve, so the
design comparison can be repeated with it (scripts/epc90133_switching.py --study qgfit).

This is NOT a tuned model under the project's tuning rule: nothing isolates the Fig. 7 discrepancy to
the device (EPC's drawing, EPC's model or both may be wrong), and no hardware data exist. It is a
sensitivity case, "what if EPC's drawn curve is the device", stored as a separate revision. The
vendor model stays the baseline. The derived library is written to the git-ignored
vendor/epc/derived/ (it is EPC's model text with changed parameters); the committed report records
the factors, the vendor library hash and the derived library hash.

Representation (declared 7 October 2026 before any variant run). The vendor subcircuit's charge
terms are scaled by factors, with every other line unchanged and the subcircuit renamed EPC2302QG:

* kgs multiplies ags1 (the linear gate-source capacitance, about 3.2 nF; it carries almost all of
  the charge below the plateau, which is 5-7 % low);
* kgd multiplies agd1, agd2 and agd5 (the gate-drain capacitance terms active between VGD = -48 V
  and the plateau end, which set the plateau width);
* fallback only (below): kon multiplies ags2 in both places it appears (the on-state gate-channel
  term above about 1.9 V, which sets the slope after the plateau).

Fit. Targets are the digitized curve's features from the existing comparator
(compare_epc2302_gate_charge.features): plateau start 8.434 nC and plateau width 2.867 nC. Each
iteration runs the declared Fig. 7 bench (scripts/epc2302_baseline.py, 40 mA gate current, 50 V,
50 A, reltol 1e-6) on the variant and updates kgs <- kgs x target/model plateau start and
kgd <- kgd x target/model plateau width. Stop when both features are within 0.5 %; at most 8
iterations, otherwise the fit fails and is reported as failed.

Checks (declared before any variant run):

* V0 reproduction: the renamed subcircuit with all factors 1 reproduces the stored vendor features
  (plateau start, width, charge at 4.98 V) within 0.1 %. Otherwise stop: the variant machinery is
  wrong.
* V1 Fig. 7: the fitted variant passes the comparator's own declared checks (vertical 0.10 V at
  every vertex; horizontal 5 % + 0.25 nC at 1.0-4.5 V), the same evaluate() used for the vendor
  model. If V1 fails with kgs/kgd, the fallback adds kon fitted to the curve's charge at 4.98 V
  (23.570 nC, same update rule, 0.5 %, at most 8 further iterations) and V1 is applied again. A
  variant that still fails V1 is reported as failed and must not be used by the switching study.
* V2 bench self-checks: the baseline gate-charge self-checks (current balance, starting bias, VDS
  at 5 V) are reported for the final variant, and the charge-equation check (transient QG against
  the variant's charge equations within 1 %) must pass.
* C5 consequence (reported, no pass/fail for the variant): scaling the gate-drain terms also
  changes the small-signal capacitances in datasheet Fig. 5, which the vendor model matches within
  its declared tolerance. CISS, CRSS and COSS from 0 to 100 V are computed for both models; the
  report gives the variant/vendor ratio and where it exceeds the Fig. 5b log tolerance (0.05 decade,
  a factor 1.122). Any exceedance means the variant cannot match Figs. 5 and 7 at once within this
  model structure: a measurement (E7, gate charge and C-V on the B1506A) has to decide.

Output: results/gan/epc2302-qg-variant.json; exit 0 when V0, V1 and V2 pass, 2 otherwise.
"""
import argparse
import hashlib
import json
import math
import re
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
import epc2302_baseline as bl
from compare_epc2302_gate_charge import evaluate
from epc2204_baseline import equation_gate_charge, subckt_params
from circuit_tools.ltspice import parse_raw, run_ltspice

NAME = "EPC2302QG"
DERIVED_DIR = ROOT / "vendor/epc/derived"
DERIVED_LIB = DERIVED_DIR / f"{NAME}.lib"
STORED_FIG7 = ROOT / "results/gan/epc2302-fig7-comparison.json"
BASELINE = ROOT / "results/gan/epc2302-baseline.json"
OUTPUT = ROOT / "results/gan/epc2302-qg-variant.json"
FIT_TOL = 0.005
REPRO_TOL = 0.001
MAX_ITER = 8
FIG5_LOG_TOL = 0.05  # decades, compare_epc2302_curves.TOL["5b"]
SCALED = {"kgs": ("ags1",), "kgd": ("agd1", "agd2", "agd5"), "kon": ("ags2",)}


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def variant_text(vendor_text, k):
    """Vendor EPC2302 subcircuit renamed, with each scaled parameter multiplied by its factor."""
    start = vendor_text.index(".subckt EPC2302 ")
    body = vendor_text[start:vendor_text.index(".ends", start) + len(".ends")]
    body = body.replace(".subckt EPC2302 ", f".subckt {NAME} ", 1)
    for factor, params in SCALED.items():
        for p in params:
            body, n = re.subn(rf"(?<![\w]){p}=\{{([^}}]*)\}}", lambda m: f"{p}={{({m.group(1)})*{factor}}}", body)
            if n != 1:
                raise SystemExit(f"expected one definition of {p}, found {n}")
    lines = body.splitlines()
    lines.insert(1, ".param " + " ".join(f"{f}={k[f]:.9g}" for f in SCALED))
    return (f"* {NAME}: EPC2302 vendor model with scaled charge terms (sensitivity variant, not EPC's model);\n"
            f"* generated by scripts/epc2302_qg_variant.py; factors {k}\n" + "\n".join(lines) + "\n")


def gate_charge_run(k, vendor_text, run_root, tag, vth_model):
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    lib = run_root / f"{tag}-{NAME}.lib"
    lib.parent.mkdir(parents=True, exist_ok=True)
    lib.write_text(variant_text(vendor_text, k), encoding="utf-8")
    text = bl.benches()["gate_charge_tran"]
    text = text.replace(".lib EPCGaNLibrary.lib", f".lib {lib.name}").replace(" EPC2302\n", f" {NAME}\n")
    text = text.replace("\n.end\n", f"\n.options reltol={bl.RELTOL:g}\n.end\n")
    r = run_ltspice(text, run_root / tag, libraries=[lib], timeout_s=600)
    if r.status != "completed":
        raise SystemExit(f"{tag}: gate-charge run {r.status}: {r.message}")
    values, checks, curve, states = bl.gate_charge(r.measurements, vth_model)
    P = subckt_params(lib.read_text(encoding="utf-8"), NAME)
    start = checks["starting_bias"]
    offset = 1e9 * equation_gate_charge(P, (0.0, start["vds_V"], 0.0, 0.0),
                                        (start["vgs_V"], start["vds_V"], start["fet_drain_current_A"], 0.0))
    qm = [x * 1e9 + offset for x in curve["qg_C"]]
    vertical, horizontal, fm, fd, _ = evaluate(qm, curve["vgs_V"], vth_model)
    q_eq = equation_gate_charge(P, states["start"], states["vgs_5V"])
    eq = {"qg_from_variant_equations_C": q_eq, "qg_transient_C": values["qg"],
          "relative_difference": abs(values["qg"] - q_eq) / q_eq, "tolerance": bl.EQUATION_TOLERANCE}
    eq["outcome"] = "pass" if eq["relative_difference"] <= bl.EQUATION_TOLERANCE else "fail"
    return {"factors": dict(k), "library": lib, "netlist_sha256": r.provenance.get("netlist_sha256"),
            "values": values, "bench_checks": checks, "equation_check": eq, "offset_nC": offset,
            "vertical": vertical, "horizontal": horizontal, "features": fm, "datasheet_features": fd,
            "curve": {"q_nC": qm, "vgs_V": curve["vgs_V"]}}


def short(run):
    f = run["features"]
    return {"factors": run["factors"], "plateau_start_nC": f["plateau_start_nC"],
            "plateau_width_nC": f["plateau_width_nC"], "q_at_vgs_5V_nC": f["q_at_vgs_5V_nC"],
            "vertical": run["vertical"]["outcome"], "horizontal": run["horizontal"]["outcome"]}


def fit(k, keys, vendor_text, run_root, vth, targets, log, label):
    """Proportional update of the factors in keys toward their feature targets."""
    for i in range(MAX_ITER):
        run = gate_charge_run(k, vendor_text, run_root, f"{label}-{i}", vth)
        log.append(short(run))
        print(label, i, json.dumps(log[-1]), flush=True)
        err = {f: run["features"][feat] / tgt for f, (feat, tgt) in targets.items() if f in keys}
        if all(abs(e - 1) <= FIT_TOL for e in err.values()):
            return run, True
        for f, e in err.items():
            k[f] /= e
    return run, False


def caps_runs(lib_text_vendor, variant_lib, run_root):
    """CISS, CRSS and COSS against VDS, 0-100 V, for the vendor model and the variant (AC, 1 MHz)."""
    out = {}
    for model, lib in (("EPC2302", bl.library_path()[0]), (NAME, variant_lib)):
        text = f"""* CISS/CRSS (gate AC) and COSS (drain AC) against VDS; generated by scripts/epc2302_qg_variant.py
.lib {Path(lib).name}
.param vds=50
Vg g 0 0 AC 1
Vd d 0 {{vds}}
X1 g d 0 {model}
Vg2 g2 0 0
Vd2 d2 0 {{vds}} AC 1
X2 g2 d2 0 {model}
.temp 25
.step param vds 0 100 1
.ac list {bl.AC_FREQ:g}
.options reltol={bl.RELTOL:g}
.end
"""
        r = run_ltspice(text, run_root / f"caps-{model}", libraries=[lib], timeout_s=600)
        if r.status != "completed":
            raise SystemExit(f"capacitance run {model} {r.status}: {r.message}")
        raw = parse_raw(r.result_path)
        w = 2 * math.pi * bl.AC_FREQ
        vds = [x.real for x in raw.values["vds"]]
        out[model] = {"vds_V": vds,
                      "ciss_F": [-i.imag / w for i in raw.values["i(vg)"]],
                      "crss_F": [i.imag / w for i in raw.values["i(vd)"]],
                      "coss_F": [-i.imag / w for i in raw.values["i(vd2)"]]}
    v, q = out["EPC2302"], out[NAME]
    summary = {}
    for c in ("ciss_F", "crss_F", "coss_F"):
        ratios = [b / a for a, b in zip(v[c], q[c])]
        outside = [x for x, r in zip(v["vds_V"], ratios) if abs(math.log10(r)) > FIG5_LOG_TOL]
        summary[c[:-2]] = {"ratio_at_vds_V": {str(x): ratios[v["vds_V"].index(x)] for x in (0.0, 1.0, 10.0, 25.0, 50.0, 100.0)},
                           "max_ratio": max(ratios), "min_ratio": min(ratios),
                           "vds_outside_fig5b_tolerance_V": [min(outside), max(outside)] if outside else None,
                           "points_outside": len(outside), "points": len(ratios)}
    return out, summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=OUTPUT)
    args = ap.parse_args()
    vendor_lib, _ = bl.library_path()
    bl.verify_target_sources(vendor_lib)
    vendor_text = vendor_lib.read_text(encoding="utf-8", errors="replace")
    stored = json.loads(STORED_FIG7.read_text())
    vth = json.loads(BASELINE.read_text())["datasheet_table"]["vgs_th"]["model"]
    run_root = ROOT / "runs" / ("epc2302-qg-variant-" + uuid.uuid4().hex[:12])
    report = {"schema": "epc2302-qg-variant/1", "evaluator_sha256": sha256(__file__),
              "scope": ("Sensitivity variant of the EPC2302 vendor model that follows the drawn datasheet Fig. 7 "
                        "curve. Not EPC's model, not a tuned model under the project's tuning rule, not validated "
                        "against hardware. The vendor model stays the baseline."),
              "input_manifest": {"vendor_library": {"file": vendor_lib.name, "sha256": sha256(vendor_lib)},
                                 "stored_fig7_comparison": sha256(STORED_FIG7), "baseline": sha256(BASELINE),
                                 "modules": {m: sha256(ROOT / m) for m in (
                                     "scripts/compare_epc2302_gate_charge.py", "scripts/epc2302_baseline.py",
                                     "scripts/epc2204_baseline.py", "src/circuit_tools/ltspice.py")}},
              "evidence_directory": str(run_root.relative_to(ROOT))}

    # V0: all factors 1 must reproduce the stored vendor features.
    k = {"kgs": 1.0, "kgd": 1.0, "kon": 1.0}
    r0 = gate_charge_run(k, vendor_text, run_root, "v0", vth)
    ref = stored["features"]["model"]
    rel = {f: abs(r0["features"][f] / ref[f] - 1) for f in ("plateau_start_nC", "plateau_width_nC", "q_at_vgs_5V_nC")}
    report["V0_reproduction"] = {"relative_difference": rel, "tolerance": REPRO_TOL,
                                 "outcome": "pass" if max(rel.values()) <= REPRO_TOL else "fail"}
    print("V0", report["V0_reproduction"], flush=True)
    if report["V0_reproduction"]["outcome"] != "pass":
        report["outcome"] = "failed (V0)"
        args.output.write_text(json.dumps(report, indent=1) + "\n")
        return 2

    dsf = stored["features"]["datasheet_curve"]
    targets = {"kgs": ("plateau_start_nC", dsf["plateau_start_nC"]), "kgd": ("plateau_width_nC", dsf["plateau_width_nC"]),
               "kon": ("q_at_vgs_5V_nC", dsf["q_at_vgs_5V_nC"])}
    report["targets"] = {f: {"feature": a, "value": b} for f, (a, b) in targets.items()}
    log = []
    run, converged = fit(k, ("kgs", "kgd"), vendor_text, run_root, vth, targets, log, "fit")
    used_fallback = False
    v1 = converged and run["vertical"]["outcome"] == "pass" and run["horizontal"]["outcome"] == "pass"
    if converged and not v1:
        used_fallback = True
        run, converged = fit(k, ("kgs", "kgd", "kon"), vendor_text, run_root, vth, targets, log, "fallback")
        v1 = converged and run["vertical"]["outcome"] == "pass" and run["horizontal"]["outcome"] == "pass"
    report["fit"] = {"iterations": log, "converged": converged, "fallback_kon_used": used_fallback,
                     "tolerance": FIT_TOL, "max_iterations_per_stage": MAX_ITER}
    report["V1_fig7"] = {"vertical": run["vertical"], "horizontal": run["horizontal"],
                         "outcome": "pass" if v1 else "fail"}
    report["V2_bench"] = {"bench_checks": run["bench_checks"], "equation_check": run["equation_check"],
                          "outcome": run["equation_check"]["outcome"]}
    report["features"] = {"variant": run["features"], "vendor_model": ref, "datasheet_curve": dsf}
    report["values"] = run["values"]
    report["factors"] = run["factors"]
    ok = v1 and report["V2_bench"]["outcome"] == "pass"
    if ok:
        DERIVED_DIR.mkdir(parents=True, exist_ok=True)
        DERIVED_LIB.write_text(run["library"].read_text(encoding="utf-8"), encoding="utf-8")
        report["derived_library"] = {"file": str(DERIVED_LIB.relative_to(ROOT)), "sha256": sha256(DERIVED_LIB),
                                     "subckt": NAME, "location_note": "git-ignored (EPC model text)"}
        curves, summary = caps_runs(vendor_text, DERIVED_LIB, run_root)
        report["C5_fig5_consequence"] = {
            "summary": summary, "fig5b_log_tolerance_decades": FIG5_LOG_TOL,
            "reading": ("ratios are variant/vendor; the vendor model matches Fig. 5 within its tolerance, so a ratio "
                        "outside 10^+-0.05 means the variant would fail Fig. 5 there"),
            "curves": curves}
    report["curve"] = run["curve"]
    report["outcome"] = "pass" if ok else "failed (V1/V2)"
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"outcome": report["outcome"], "factors": report["factors"],
                      "features": {k_: short(run)[k_] for k_ in ("plateau_start_nC", "plateau_width_nC", "q_at_vgs_5V_nC")},
                      "C5": report.get("C5_fig5_consequence", {}).get("summary")}, indent=1))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
