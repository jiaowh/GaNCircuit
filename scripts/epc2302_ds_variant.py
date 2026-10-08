#!/usr/bin/env python3
"""EPC2302DS: a datasheet-calibrated revision of the EPC2302 model that must pass the whole datasheet check set.

Owner request (8 October 2026): match Figs. 5 and 7 together, and then the whole datasheet, not those two
figures only. The vendor model passes every checked curve except Fig. 7; EPC2302QG (scripts/epc2302_qg_variant.py)
passes Fig. 7 by scaling existing terms and moves CRSS 23 % outside Fig. 5. This is a different representation,
declared below before any LTspice run of it. It is a calibration to EPC's published typical curves: not a tuned
model under the project's tuning rule, not identified physics, not validated against hardware. The vendor model
stays the baseline; EPC2302QG and its results keep their identity.

Representation (declared 8 October 2026). The vendor subcircuit is kept line for line; two charge-defined
capacitors are added, each a smooth step of charge in one branch voltage (charge-conserving by construction,
because each charge is a function of its own branch voltage only):

  C_XGS gate source Q = xqs/2 * (1 + tanh((V(gate,source) - xvs) / (2 xws)))
  C_XGD gate drain  Q = xqd/2 * (1 + tanh((V(gate,drain)  - xvd) / (2 xwd)))

Why there. Every datasheet capacitance (Fig. 5, Fig. 6 and the CISS/CRSS/COSS/QOSS rows) is taken at VGS = 0 and
VDS >= 0, i.e. VGS = 0 and VGD <= 0; Figs. 1-4 and 8-10 are DC. Fig. 7 also passes through VGS between 0 and the
plateau (about 2.4 V) and, at the end of the plateau, VGD between 0 and about +2.4 V. A charge step placed inside
those two windows changes Fig. 7 and, to within its exponential tail, nothing else the datasheet shows. The vendor
gap supports this placement: charge missing below the plateau grows from about 0.26 nC at 1.2 V to 0.73 nC at
2.3 V, and a further 0.5-0.7 nC is missing where VDS falls below about 1.5 V (replica, below).

Parameter design (exploratory, done BEFORE this declaration and before any LTspice run of the candidate). A
quasi-static replica of the Fig. 7 bench (design(): the vendor charge and channel equations, 50 V, 50 A ideal
clamp, 40 mA through RG) reproduces the stored LTspice vendor curve within about 0.01 nC at the horizontal rows
and gives the same worst vertical vertex (2.851 V model against 2.580 V drawn). A Nelder-Mead fit on the replica
minimized squared and worst vertical error at the Fig. 7 vertices, with a penalty when CISS or CRSS at VGS = 0
(0-100 V) moves by more than 1 %. One earlier replica fit placed the gate-drain step at VGD = -3.1 V (inside the
Fig. 5 domain) because the penalty then omitted the gate-drain term; it was corrected before freezing. Frozen
values (PARAMS): replica worst vertical error 0.052 V, all horizontal rows pass, CISS/CRSS change at most 0.8 %.

Checks, declared before the first LTspice run of the candidate. Existing evaluators run unchanged, against a copy
of EPCGaNLibrary.lib whose EPC2302 subcircuit is the candidate (git-ignored, vendor/epc/derived/EPC2302DS/):

* D0 machinery: the candidate with xqs = xqd = 0 through the full table bench reproduces every stored vendor
  table value (results/gan/epc2302-baseline.json) within 0.1 %.
* D1 Fig. 7: compare_epc2302_gate_charge's declared vertical (0.10 V) and horizontal (5 % + 0.25 nC) checks pass on
  the stored pipeline's curve (index-thinned, as for the vendor model) AND on a curve resampled every 0.01 nC from
  the same transient (sampling sensitivity, scripts/epc2302_qg_variant.py revision 2). Both must pass.
* D2 curves: compare_epc2302_curves passes all 24 curves of Figs. 1-6 and 8-10, tolerances unchanged.
* D3 table and bench self-checks: the table run completes; every row with datasheet limits stays inside them; no
  row unflagged for the vendor model becomes flagged; AC-vs-transient output charge, the charge-equation check
  (extended with the two added terms), reltol 1e-6 -> 1e-7 convergence and the drive-current check all pass.
  QGD and QG(TH) are flagged for the vendor model and EPC's own Fig. 7 does not reproduce those table values under
  the bench definitions (docs/build.md); they are reported, not required to clear.
* D4 charge conservation: gate driven 0 -> 5 -> 0 V (1 us ramps, 1 ohm) with the Fig. 7 drain circuit; net gate
  charge over the closed cycle equals the model's leakage charge within 1 % of QG. Vendor model run as control.
* D5 domain: the added terms' own contribution to CISS and CRSS at VGS = 0, VDS 0-100 V, at most 1 % (analytic).

Budget and stop rule: one frozen candidate, D0 plus one full suite, LTspice benches with the baseline settings
(trapezoidal, reltol 1e-6). Expected well under 10 minutes. Any non-completed bench is a numerical failure of the
candidate. No refit in this run: a failure is recorded as the result; a revision needs a new declaration.

Not covered by any datasheet figure, so untested: the added gate-drain charge (0.34 nC at VGD about +0.6 V) is
also crossed in reverse conduction (VGS = 0, VDS about -0.6 V) and near the end of every hard turn-on; Fig. 11
(SOA) and Fig. 12 (thermal) are not modelled. Passing published typical curves is not a hardware validation.

Outputs: results/gan/epc2302ds-{baseline,model-curves,model-curves-extra,curve-comparison,fig7-comparison}.json and
results/gan/epc2302-ds-variant.json; standalone vendor/epc/derived/EPC2302DS.lib (subckt EPC2302DS) only on pass.
Exit 0 when D0-D5 pass, 2 otherwise.

Run 1 (8 October 2026) CRASHED in post-processing (log kept: runs/epc2302-ds-variant-run1.log): D0 passed, every
bench completed, all 24 curves and the stored-pipeline Fig. 7 checks printed 'pass', then the D1 resampling read
the operating-point file bench.op.raw instead of the transient bench.raw (KeyError 'time'). Fixed that file name
only (no parameter, check or tolerance changed) and reran the whole declared suite as run 2. `--design` reruns the replica fit and prints its parameters (no LTspice).
"""
import argparse
import hashlib
import json
import math
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
import numpy as np

import epc2302_baseline as bl
import epc2302_curve_benches as cb
import compare_epc2302_curves as cc
import compare_epc2302_gate_charge as cg
from epc2204_baseline import cumtrapz, equation_gate_charge, leakage_charge, subckt_params
from epc2302_qg_variant import resampled
from circuit_tools.ltspice import parse_raw, run_ltspice

NAME = "EPC2302DS"
PARAMS = {"xqs": 1.087e-9, "xvs": 1.843, "xws": 0.3767, "xqd": 3.435e-10, "xvd": 0.6203, "xwd": 0.07692}
DERIVED = ROOT / "vendor/epc/derived"
SUITE_DIR = DERIVED / NAME  # full library copy with the candidate as EPC2302, for the unchanged benches
STANDALONE = DERIVED / f"{NAME}.lib"
OUT = ROOT / "results/gan"
REPORT = OUT / "epc2302-ds-variant.json"
VENDOR_BASELINE = OUT / "epc2302-baseline.json"
D0_TOL, D4_TOL, D5_TOL = 0.001, 0.01, 0.01


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sigmoid_q(q, v0, w, v):
    return 0.5 * q * (1 + math.tanh((v - v0) / (2 * w)))


def subckt_text(vendor_text, name, p):
    """Vendor EPC2302 subcircuit, renamed, with the two declared charge steps added before .ends."""
    start = vendor_text.index(".subckt EPC2302 ")
    end = vendor_text.index(".ends", start)
    body = vendor_text[start:end].replace(".subckt EPC2302 ", f".subckt {name} ", 1)
    lines = body.rstrip("\n").splitlines()
    lines.insert(1, ".param " + " ".join(f"{k}={v:.9g}" for k, v in p.items()))
    lines += ["* EPC2302DS additions (scripts/epc2302_ds_variant.py): gate-source and gate-drain charge steps",
              "C_XGS gate source Q=(0.5*xqs*(1+tanh((v(gate,source)-xvs)/(2*xws))))",
              "C_XGD gate drain Q=(0.5*xqd*(1+tanh((v(gate,drain)-xvd)/(2*xwd))))", ".ends"]
    return "\n".join(lines) + "\n"


def suite_library(vendor_text, p, tag):
    """EPCGaNLibrary.lib copy whose EPC2302 is the candidate (same name, so the unchanged benches load it)."""
    start = vendor_text.index(".subckt EPC2302 ")
    end = vendor_text.index(".ends", start) + len(".ends")
    text = vendor_text[:start] + subckt_text(vendor_text, "EPC2302", p).rstrip("\n") + vendor_text[end:]
    d = SUITE_DIR / tag
    d.mkdir(parents=True, exist_ok=True)
    lib = d / "EPCGaNLibrary.lib"
    lib.write_text(text, encoding="utf-8")
    return lib


def extended_equation(P, start, end):
    """Vendor charge equations plus the two added steps, at the same internal voltages."""
    rs = P["rpara_s_factor"] * P["rpara"]
    rd = (1 - P["rpara_s_factor"]) * P["rpara"]

    def added(vgs_t, vds_t, i_d, i_g):
        vgs = vgs_t - i_g * P["rg_value"] - i_d * rs
        vgd = vgs - (vds_t - i_d * (rs + rd))
        if "xqs" not in P:
            return 0.0
        return sigmoid_q(P["xqs"], P["xvs"], P["xws"], vgs) + sigmoid_q(P["xqd"], P["xvd"], P["xwd"], vgd)

    return equation_gate_charge(P, start, end) + added(*end) - added(*start)


def patch(lib, vendor_lib, archive_sha):
    """Point the unchanged evaluators at the candidate library (vendor sources still verified)."""
    real_verify = bl.verify_target_sources

    def verify(_):
        _, datasheet = real_verify(vendor_lib)
        return sha256(lib), datasheet

    bl.library_path = lambda: (lib, archive_sha)
    bl.verify_target_sources = verify
    bl.equation_gate_charge = extended_equation
    cg.equation_gate_charge = extended_equation


def run_main(module, argv):
    old = sys.argv
    sys.argv = [module.__file__] + argv
    try:
        return module.main()
    finally:
        sys.argv = old


def d5_domain(P):
    """Added terms' contribution to CISS and CRSS at VGS = 0 over VDS 0..100 V, relative to the vendor values."""
    v = np.linspace(0, 100, 401)
    ds = lambda q, v0, w, x: q / (4 * w) / np.cosh((x - v0) / (2 * w)) ** 2
    add_gs = ds(PARAMS["xqs"], PARAMS["xvs"], PARAMS["xws"], 0.0)
    add_gd = ds(PARAMS["xqd"], PARAMS["xvd"], PARAMS["xwd"], -v)
    stored = json.loads((OUT / "epc2302-model-curves-extra.json").read_text())["curves"]["ciss_crss_25C"]
    ciss = np.interp(v, stored["vds_V"], stored["ciss_pF"]) * 1e-12
    crss = np.interp(v, stored["vds_V"], stored["crss_pF"]) * 1e-12
    r_ciss, r_crss = float(np.max((add_gs + add_gd) / ciss)), float(np.max(add_gd / crss))
    return {"max_relative_ciss_change": r_ciss, "max_relative_crss_change": r_crss, "tolerance": D5_TOL,
            "outcome": "pass" if max(r_ciss, r_crss) <= D5_TOL else "fail"}


def d1_resampled(baseline_report, vth):
    """Fig. 7 checks on a 0.01 nC resampled curve from the table run's own gate-charge transient."""
    raw_dir = ROOT / baseline_report["evidence_directory"] / "gate_charge_tran"
    raw = parse_raw(raw_dir / "bench.raw")  # run 2 fix: run 1 globbed bench.op.raw (the operating point) and crashed
    g = {k: [x.real if isinstance(x, complex) else x for x in vals] for k, vals in raw.values.items()}
    _, checks, _, states = bl.gate_charge(g, vth)
    P = subckt_params(bl.library_path()[0].read_text(encoding="utf-8", errors="replace"), "EPC2302")
    s = checks["starting_bias"]
    offset = 1e9 * extended_equation(P, (0.0, s["vds_V"], 0.0, 0.0), (s["vgs_V"], s["vds_V"], s["fet_drain_current_A"], 0.0))
    qs, vs = resampled(g, states["t_g5"])
    vertical, horizontal, fm, fd, _ = cg.evaluate([x * 1e9 + offset for x in qs], vs, vth)
    return {"vertical": vertical, "horizontal": horizontal, "features": fm, "datasheet_features": fd,
            "offset_nC": offset, "time_points": len(g["time"]),
            "outcome": "pass" if vertical["outcome"] == "pass" and horizontal["outcome"] == "pass" else "fail"}


def d4_cycle(lib, run_root, label):
    text = f"""* Closed gate-charge cycle 0 -> 5 -> 0 V with the Fig. 7 drain circuit; scripts/epc2302_ds_variant.py
.lib EPCGaNLibrary.lib
Vdd vdd 0 50
Il vdd d {bl.LOAD_CURRENT:g}
Dc d vdd dclamp
.model dclamp D(Ron=1m Roff=1G Vfwd=0)
Vg gs 0 PWL(0 0 100n 0 1.1u 5 2u 5 3u 0 4u 0)
Rgs gs g 1
X1 g d 0 EPC2302
.temp 25
.options plotwinsize=0 reltol={bl.RELTOL:g}
.tran 0 4u 0 0.1n
.end
"""
    r = run_ltspice(text, run_root / f"cycle-{label}", libraries=[lib], timeout_s=600)
    if r.status != "completed":
        return {"status": r.status, "message": r.message, "outcome": "fail"}
    g = r.measurements
    P = subckt_params(lib.read_text(encoding="utf-8", errors="replace"), "EPC2302")
    t = g["time"]
    q = cumtrapz(t, g["ix(x1:gatein)"])
    q_peak = max(q)
    leak = leakage_charge(P, g, t[-1])
    diff = abs(q[-1] - leak)
    return {"net_cycle_charge_C": q[-1], "leakage_charge_C": leak, "peak_charge_C": q_peak,
            "relative_to_peak": diff / q_peak, "tolerance": D4_TOL, "time_points": len(t),
            "vgs_end_V": g["v(g)"][-1], "vds_end_V": g["v(d)"][-1],
            "outcome": "pass" if diff / q_peak <= D4_TOL else "fail"}


def design():
    """Replica of the Fig. 7 bench and the exploratory fit that produced PARAMS (no LTspice)."""
    from scipy.optimize import minimize
    from compare_epc2204_gate_charge import interp
    P = subckt_params(bl.library_path()[0].read_text(encoding="utf-8", errors="replace"), "EPC2302")
    sp = lambda x: np.where(x > 30, x, np.log1p(np.exp(np.minimum(x, 30))))
    st = lambda q, v0, w, x: 0.5 * q * (1 + np.tanh((x - v0) / (2 * w)))
    rs = P["rpara_s_factor"] * P["rpara"]

    def qg(vgs, vgd, X):
        q = (P["ags1"] * vgs + 0.5 * P["ags2"] * P["ags4"] * sp((vgs - P["ags3"]) / P["ags4"])
             + P["agd1"] * vgd + 0.5 * P["ags2"] * P["ags4"] * sp((vgd - P["ags3"]) / P["ags4"])
             + P["agd2"] * P["agd4"] * sp((vgd - P["agd3"]) / P["agd4"])
             + P["agd5"] * P["agd7"] * sp((vgd - P["agd6"]) / P["agd7"]))
        return q + st(X["xqs"], X["xvs"], X["xws"], vgs) + st(X["xqd"], X["xvd"], X["xwd"], vgd)

    def curve(X):
        x0, load = P["x0_0"], bl.LOAD_CURRENT
        vg = np.linspace(0, 6, 60001)
        L = P["A1"] * sp((vg - P["k2"]) / P["k3"])
        vds = np.where(L > load * x0, load / np.maximum(L - load * x0, 1e-30), np.inf)
        vv = np.geomspace(50, 0.05, 20000)  # plateau, parametrized by VDS
        vgp = P["k2"] + P["k3"] * np.log(np.expm1(load * (1 + x0 * vv) / vv / P["A1"]))
        off = vds >= 50
        vi = np.concatenate([vg[off], vgp, vg[~off]])
        vdi = np.concatenate([np.full(off.sum(), 50.0), vv, vds[~off]])
        idd = np.concatenate([np.zeros(off.sum()), np.full(len(vv) + (~off).sum(), load)])
        q = (qg(vi, vi - vdi, X) - qg(0.0, -50.0, X)) * 1e9
        o = np.argsort(q)
        vt = (vi + bl.GATE_CURRENT * P["rg_value"] + idd * rs)[o]
        keep = vt <= 5.2
        return q[o][keep], vt[keep]

    qd, vd = cg.datasheet_curve()
    v = np.linspace(0, 100, 401)
    zero = dict.fromkeys(PARAMS, 0.0) | {"xws": 1.0, "xwd": 1.0}

    def caps(X, h=1e-4):
        ciss = (qg(h, h - v, X) - qg(-h, -h - v, X)) / (2 * h)
        crss = (qg(0.0, -v + h, X) - qg(0.0, -v - h, X)) / (2 * h)  # gate-drain part only: dQ/dVGD
        return np.concatenate([ciss, crss])

    c0 = caps(zero)
    names = list(PARAMS)

    def obj(x):
        X = dict(zip(names, x * scale))
        if min(X["xqs"], X["xqd"]) < 0 or min(X["xws"], X["xwd"]) < 0.05:
            return 1e3
        qm, vm = curve(X)
        dv = np.array([interp(list(qm), list(vm), q) - u for q, u in zip(qd[1:-1], vd[1:-1])])
        pen = max(0.0, float(np.max(np.abs(caps(X) / c0 - 1))) - 0.01) * 1e3
        return float(np.sum(dv ** 2) + 20 * np.max(np.abs(dv)) ** 2 + pen)

    scale = np.array([1e-9, 1, 1, 1e-9, 1, 1])
    x0 = np.array([0.63e-9, 1.43, 0.24, 0.6e-9, 1.2, 0.15]) / scale
    r = minimize(obj, x0, method="Nelder-Mead", options={"maxiter": 3000, "xatol": 1e-4, "fatol": 1e-8})
    X = dict(zip(names, r.x * scale))
    qm, vm = curve(X)
    vert, hor, fm, _, _ = cg.evaluate(list(qm), list(vm), json.loads(VENDOR_BASELINE.read_text())["datasheet_table"]["vgs_th"]["model"])
    print(json.dumps({"params": X, "vertical_worst": vert["worst"]["difference_V"], "horizontal": hor["outcome"],
                      "max_cap_change": float(np.max(np.abs(caps(X) / c0 - 1)))}, indent=1, default=float))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", action="store_true", help="rerun the replica fit only (no LTspice)")
    args = ap.parse_args()
    if args.design:
        design()
        return 0
    vendor_lib, archive_sha = bl.library_path()
    bl.verify_target_sources(vendor_lib)
    vendor_text = vendor_lib.read_text(encoding="utf-8", errors="replace")
    run_root = ROOT / "runs" / ("epc2302-ds-variant-" + uuid.uuid4().hex[:12])
    report = {"schema": "epc2302-ds-variant/1", "evaluator_sha256": sha256(__file__), "candidate": NAME,
              "params": PARAMS, "evidence_directory": str(run_root.relative_to(ROOT)),
              "scope": ("Datasheet-calibrated revision of the EPC2302 vendor model: vendor subcircuit unchanged plus two "
                        "declared charge steps. Calibration to EPC's typical curves; not physically identified, not "
                        "validated against hardware. The vendor model stays the baseline."),
              "input_manifest": {"vendor_library": sha256(vendor_lib), "vendor_baseline": sha256(VENDOR_BASELINE),
                                 "modules": {m: sha256(ROOT / m) for m in (
                                     "scripts/epc2302_baseline.py", "scripts/epc2302_curve_benches.py",
                                     "scripts/compare_epc2302_curves.py", "scripts/compare_epc2302_gate_charge.py",
                                     "scripts/epc2302_qg_variant.py", "scripts/epc2204_baseline.py",
                                     "scripts/compare_epc2204_curves.py", "scripts/compare_epc2204_gate_charge.py",
                                     "src/circuit_tools/ltspice.py")}}}

    def save(outcome):
        report["outcome"] = outcome
        REPORT.write_text(json.dumps(report, indent=1, default=float) + "\n")

    # D0: zeroed additions reproduce the stored vendor table values.
    zero = dict(PARAMS, xqs=0.0, xqd=0.0)
    lib0 = suite_library(vendor_text, zero, "d0")
    patch(lib0, vendor_lib, archive_sha)
    d0_out = run_root / "d0-baseline.json"
    run_root.mkdir(parents=True, exist_ok=True)
    run_main(bl, ["--output", str(d0_out), "--curves", str(run_root / "d0-curves.json")])
    stored = json.loads(VENDOR_BASELINE.read_text())["datasheet_table"]
    got = json.loads(d0_out.read_text())["datasheet_table"]
    rel = {k: abs(got[k]["model"] / stored[k]["model"] - 1) for k in stored if stored[k]["model"]}
    report["D0_machinery"] = {"max_relative_difference": max(rel.values()), "per_row": rel, "tolerance": D0_TOL,
                              "outcome": "pass" if max(rel.values()) <= D0_TOL else "fail"}
    print("D0", report["D0_machinery"]["outcome"], max(rel.values()), flush=True)
    if report["D0_machinery"]["outcome"] != "pass":
        save("failed (D0)")
        return 2

    # Candidate: full table run, extra curves, comparisons.
    lib = suite_library(vendor_text, PARAMS, "candidate")
    patch(lib, vendor_lib, archive_sha)
    report["candidate_suite_library_sha256"] = sha256(lib)
    base_out, curves_out = OUT / "epc2302ds-baseline.json", OUT / "epc2302ds-model-curves.json"
    extra_out = OUT / "epc2302ds-model-curves-extra.json"
    run_main(bl, ["--output", str(base_out), "--curves", str(curves_out)])
    cb.OUTPUT = extra_out
    run_main(cb, [])
    for p in (base_out, extra_out):  # the unchanged writers record "modified": false; correct the identity
        d = json.loads(p.read_text())
        d["model"].update(modified=True, candidate=NAME, params=PARAMS, generator="scripts/epc2302_ds_variant.py")
        p.write_text(json.dumps(d, indent=2, allow_nan=False) + "\n")
    cc.BASE, cc.EXTRA, cc.OUTPUT = curves_out, extra_out, OUT / "epc2302ds-curve-comparison.json"
    curves_rc = cc.main()
    cg.MODEL, cg.BASELINE, cg.OUTPUT, cg.LIBRARY = curves_out, base_out, OUT / "epc2302ds-fig7-comparison.json", lib
    fig7_rc = cg.main()

    base = json.loads(base_out.read_text())
    vth = base["datasheet_table"]["vgs_th"]["model"]
    fig7 = json.loads(cg.OUTPUT.read_text())
    res = d1_resampled(base, vth)
    report["D1_fig7"] = {"stored_pipeline": {"vertical": fig7["vertical_check"]["outcome"],
                                             "vertical_worst": fig7["vertical_check"]["worst"],
                                             "horizontal": fig7["horizontal_check"]["outcome"],
                                             "features": fig7["features"]["model"]},
                         "resampled": res,
                         "outcome": "pass" if fig7_rc == 0 and res["outcome"] == "pass" else "fail"}
    comp = json.loads(cc.OUTPUT.read_text())
    report["D2_curves"] = {"summary": comp["summary"],
                           "outcome": "pass" if curves_rc == 0 and len(comp["summary"]) == 24 else "fail"}
    vend = json.loads(VENDOR_BASELINE.read_text())["datasheet_table"]
    table = base["datasheet_table"]
    newly_flagged = [k for k in table if table[k]["review"] and not vend[k]["review"]]
    outside = [k for k in table if table[k]["limit_check"] == "outside-limits"]
    notes = base["checks_and_definitions"]
    self_checks = {k: notes.get(k, {}).get("outcome") for k in (
        "ac_vs_transient", "gate_charge_equation_check", "gate_charge_numerical_convergence",
        "gate_charge_drive_current_sensitivity")}
    report["D3_table"] = {"run_outcome": base["run_outcome"], "failed_benches": base["failed_benches"],
                          "rows": {k: {"model": r["model"], "typ": r.get("typ"), "limit_check": r["limit_check"],
                                       "deviation_from_typ": r.get("deviation_from_typ"), "review": r["review"],
                                       "vendor_model": vend[k]["model"], "vendor_review": vend[k]["review"]}
                                   for k, r in table.items()},
                          "outside_limits": outside, "newly_flagged": newly_flagged, "self_checks": self_checks,
                          "outcome": "pass" if (base["run_outcome"] == "completed" and not outside and not newly_flagged
                                                and all(v == "pass" for v in self_checks.values())) else "fail"}
    cyc = run_root / "cycle"
    report["D4_charge_cycle"] = {"candidate": d4_cycle(lib, cyc, "candidate"), "vendor_control": d4_cycle(vendor_lib, cyc, "vendor")}
    report["D4_charge_cycle"]["outcome"] = report["D4_charge_cycle"]["candidate"]["outcome"]
    report["D5_domain"] = d5_domain(subckt_params(lib.read_text(encoding="utf-8", errors="replace"), "EPC2302"))
    checks = ("D0_machinery", "D1_fig7", "D2_curves", "D3_table", "D4_charge_cycle", "D5_domain")
    ok = all(report[c]["outcome"] == "pass" for c in checks)
    if ok:
        STANDALONE.write_text(f"* {NAME}: EPC2302 vendor model plus two charge steps (datasheet-calibrated revision, "
                              f"not EPC's model);\n* generated by scripts/epc2302_ds_variant.py\n"
                              + subckt_text(vendor_text, NAME, PARAMS), encoding="utf-8")
        report["standalone_library"] = {"file": str(STANDALONE.relative_to(ROOT)), "sha256": sha256(STANDALONE),
                                        "subckt": NAME, "location_note": "git-ignored (EPC model text)"}
    save("pass" if ok else "failed (" + ", ".join(c for c in checks if report[c]["outcome"] != "pass") + ")")
    print(json.dumps({c: report[c]["outcome"] for c in checks} | {"outcome": report["outcome"]}, indent=1))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
