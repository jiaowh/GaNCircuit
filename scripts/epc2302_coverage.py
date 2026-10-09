#!/usr/bin/env python3
"""EPC2302 whole-datasheet coverage record, with the missing electrical rows checked (declared 9 October 2026).

Decision it serves: what the vendor model and EPC2302DS do and do not cover in the datasheet (revised April 29,
2026; plans/epc2302-full-datasheet-model-plan.md), so later board results state their device-model limits. It does
not tune either model; a failure is recorded, not refitted.

Model reading before any run (vendor subcircuit, identical in EPC2302DS apart from two charge-only capacitors):
off-state drain current flows only through two 1e11/aWg = 36.8 Mohm convergence resistors (drain-source and
drain-gate), the gate-drain diode and the subthreshold channel; gate leakage only through the two gate diodes and
the gate convergence resistors. None has a temperature coefficient. There is no avalanche or breakdown element and
no stored-charge (diode) element: reverse conduction is the channel. Expected, by hand: IDSS(80 V) about 4.5 uA,
IGSS(+5 V, VDS = 0) about 0.6 mA at both 25 and 125 C, IGSS(-4 V) about 0.3 uA, and no breakdown below kilovolts.
The datasheet does not print the drain condition for IGSS; VDS = 0 V (drain tied to source) is assumed and the
drain-open case is reported as a sensitivity.

New electrical checks, both models, LTspice 26.1.1 through the existing adapter, reltol 1e-6:

* E0 machinery: IDSS and the three IGSS operating points agree with the subcircuit equations evaluated by hand
  (model_leakage below) within 1 %. A failure means the model was misread: those rows become 'unresolved'.
* Rows IDSS, IGSS forward 25 C, IGSS forward 125 C, IGSS reverse: classified exactly as the existing table rows
  (epc2302_baseline.classify: limit compliance, and a 25 % typical-value screen that flags for review).
* BVDSS: VGS = 0, VDS swept 0-200 V; the voltage at which ID reaches 0.15 mA, or none within the sweep. With no
  breakdown element, meeting the 100 V minimum says nothing about breakdown: status 'unsupported' whatever the value.
* QRR: diode-commutation bench (50 V bus, DUT as freewheeling low side at VGS = 0, forward currents 10 and 50 A,
  1 A/ns current ramp in an ideal high-side source, ideal clamp). Recovered charge = integral of the DUT drain
  current from its zero crossing to the end of the run. R1: it equals the model's own capacitive drain charge
  between the two states (charge equations, as for the gate-charge equation check) within 2 % - the remainder is
  channel/leakage conduction, reported. R2: recovered charge at 50 A within 2 % of that at 10 A (stored charge would
  scale with forward current). Both pass -> QRR consistent with the datasheet's 0 for this model; it is 0 by
  construction (no stored-charge element), so this confirms the reading and integration, not device physics.
* Note check (page 4, Fig. 11 note: negative gate drive increases the reverse drain-source voltage): VSD at 0.5 A
  with VGS = -2 V exceeds VSD at VGS = 0. Qualitative only.

Reused evidence (no rerun): the 13 table rows, the 24 curves of Figs. 1-6 and 8-10 and Fig. 7, from the saved vendor
and EPC2302DS reports, after checking that the DS report still records the vendor baseline and libraries by hash and
that its D0-D5 outcomes pass. QGD and QG(TH) stay 'unresolved' (table definition and Fig. 7 disagree, docs/build.md).

Not electrical-subcircuit properties, given explicit dispositions (no invented passes): thermal resistances and Fig. 12
(no EPC2302 thermal network in hand; EPC's library archive has none; the subcircuit has no self-heating),
maximum ratings, Fig. 11 SOA and the page-5 repetitive-overvoltage illustration (application limits; no checker in
the evaluation layer), and package/pinout/marking/layout notes (structural, outside the model).

Budget: 10 benches x 2 models = 20 LTspice runs, 120 s timeout each, expected under 2 minutes in total; stop at
10 minutes of solver time. A bench that does not complete makes its item 'not-run' and is kept. One run of the
suite; any change after a result is a labelled revision.

Outputs: results/gan/epc2302-coverage.json and results/gan/epc2302-coverage.md (generated). Evidence in runs/.

Run 1 (9 October 2026, kept as results/gan/epc2302-coverage-run1.{json,md}): all 20 benches completed (23.6 s), E0
passed. RETROSPECTIVE correction after reading it, no check or tolerance changed: IGSS reverse was classified with
its signed value (current leaves the gate, -0.49 uA), so its limit check against +0.2 mA passed vacuously; the
datasheet quotes magnitudes, so the leakage rows now use |I|. Run 2 repeats the whole suite with that fix.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from circuit_tools.ltspice import run_ltspice
import epc2302_baseline as bl
from epc2204_baseline import cumtrapz, subckt_params

OUT = ROOT / "results/gan"
DS_REPORT = OUT / "epc2302-ds-variant.json"
VENDOR_BASELINE = OUT / "epc2302-baseline.json"
VENDOR_CURVES, DS_CURVES = OUT / "epc2302-curve-comparison.json", OUT / "epc2302ds-curve-comparison.json"
VENDOR_FIG7, DS_FIG7 = OUT / "epc2302-fig7-comparison.json", OUT / "epc2302ds-fig7-comparison.json"
DS_BASELINE = OUT / "epc2302ds-baseline.json"
MACHINERY_TOL, QRR_TOL = 0.01, 0.02
BV_CURRENT, BV_SWEEP = 0.15e-3, 200.0
QRR_CURRENTS, DIDT, EXCESS, VBUS = (10.0, 50.0), 1e9, 20.0, 50.0
TIMEOUT_S, BUDGET_S = 120, 600

# Datasheet page 2, column positions read from word x-coordinates (MIN 428, TYP 464, MAX 502).
NEW_ROWS = {
    "idss": {"unit": "A", "typ": 1e-6, "max": 100e-6, "conditions": "VDS = 80 V, VGS = 0 V"},
    "igss_fwd_25C": {"unit": "A", "typ": 0.01e-3, "max": 4e-3, "conditions": "VGS = 5 V (VDS = 0 V assumed)"},
    "igss_fwd_125C": {"unit": "A", "typ": 0.4e-3, "max": 9e-3, "conditions": "VGS = 5 V, TJ = 125 C (defined by design)"},
    "igss_rev": {"unit": "A", "typ": 0.01e-3, "max": 0.2e-3, "conditions": "VGS = -4 V (VDS = 0 V assumed)"},
}


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sp(x):
    return x + math.log1p(math.exp(-x)) if x > 30 else math.log1p(math.exp(x))


def model_leakage(P, vgs, vds, temp=25.0):
    """Terminal gate and drain DC currents of the subcircuit equations (internal drops neglected, < 0.1 %)."""
    k = 0.125 * P["aWg"] / 1077
    diode = lambda v: k * (P["dgs1"] * math.expm1(min(v, 10.0) / P["dgs3"]) + P["dgs2"] * math.expm1(min(v, 10.0) / P["dgs4"]))
    r = 100000e6 / P["aWg"]
    vgd = vgs - vds
    a1 = P["A1"] * (1 - P["aITc"] * (temp - 25))
    k2 = P["k2"] * (1 - P["k2Tc"] * (temp - 25))
    x0 = P["x0_0"] * (1 - P["x0_0_TC"] * (temp - 25)) + P["x0_1"] * (1 - P["x0_1_TC"] * (temp - 25)) * vgs
    ch = a1 * sp((vgs - k2) / P["k3"]) * vds / (1 + x0 * vds) if vds > 0 else 0.0
    i_g = diode(vgs) + diode(vgd) + vgs / r + vgd / r
    i_d = ch + vds / r - vgd / r - diode(vgd)
    return i_g, i_d


def drain_charge(P, vgs_t, vds_t, i_d, i_g):
    """Charge on the internal drain node from the gate-drain and source-drain charge equations (plus DS steps)."""
    rs = P["rpara_s_factor"] * P["rpara"]
    rd = (1 - P["rpara_s_factor"]) * P["rpara"]
    vgs = vgs_t - i_g * P["rg_value"] - i_d * rs
    vds = vds_t - i_d * (rs + rd)
    vsd, vgd = -vds, vgs - vds
    q_gd = (P["agd1"] * vgd + 0.5 * P["ags2"] * P["ags4"] * sp((vgd - P["ags3"]) / P["ags4"])
            + P["agd2"] * P["agd4"] * sp((vgd - P["agd3"]) / P["agd4"])
            + P["agd5"] * P["agd7"] * sp((vgd - P["agd6"]) / P["agd7"])
            + P["agd8"] * P["agd10"] * sp((vgd - P["agd9"]) / P["agd10"]))
    if "xqd" in P:
        q_gd += 0.5 * P["xqd"] * (1 + math.tanh((vgd - P["xvd"]) / (2 * P["xwd"])))
    q_sd = (P["asd1"] * vsd + P["asd2"] * P["asd4"] * sp((vsd - P["asd3"]) / P["asd4"])
            + P["asd5"] * P["asd7"] * sp((vsd - P["asd6"]) / P["asd7"])
            + P["asd8"] * P["asd10"] * sp((vsd - P["asd9"]) / P["asd10"]))
    return -(q_gd + q_sd)


def benches(lib_name, sub):
    head = f"* {sub}; bench generated by scripts/epc2302_coverage.py\n.lib {lib_name}\n"
    tail = ".options reltol=1e-6\n.end\n"
    b = {}
    b["idss"] = head + f"Vd d 0 80\nVg g 0 0\nX1 g d 0 {sub}\n.temp 25\n.op\n" + tail
    for name, vg, t, drain in (("igss_fwd_25C", 5, 25, "Vd d 0 0"), ("igss_fwd_125C", 5, 125, "Vd d 0 0"),
                               ("igss_rev", -4, 25, "Vd d 0 0"), ("igss_fwd_25C_drain_open", 5, 25, ""),
                               ("igss_rev_drain_open", -4, 25, "")):
        b[name] = head + f"Vg g 0 {vg}\n{drain}\nX1 g d 0 {sub}\n.temp {t}\n.op\n" + tail
    b["bvdss"] = head + f"Vd d 0 0\nVg g 0 0\nX1 g d 0 {sub}\n.temp 25\n.dc Vd 0 {BV_SWEEP:g} 0.5\n" + tail
    b["vsd_vgs_neg2"] = head + f"Vg g 0 -2\nIs d 0 0.5\nX1 g d 0 {sub}\n.temp 25\n.op\n" + tail
    for i_f in QRR_CURRENTS:
        t1 = 50e-9 + (i_f + EXCESS) / DIDT
        b[f"qrr_{i_f:g}A"] = head + f"""* Diode commutation: DUT low side at VGS = 0 carries {i_f:g} A in reverse, then the high-side current
* ramps at {DIDT / 1e9:g} A/ns to {i_f + EXCESS:g} A; the excess charges the DUT output and an ideal clamp takes it
Vbus bus 0 {VBUS:g}
Iload sw bus {i_f:g}
Ihs bus sw PWL(0 0 50n 0 {t1:.6g} {i_f + EXCESS:g})
Dc sw bus dclamp
.model dclamp D(Ron=1m Roff=1G Vfwd=0)
Vg g 0 0
X1 g sw 0 {sub}
.temp 25
.options plotwinsize=0 numdgt=15
.tran 0 {t1 + 100e-9:.6g} 0 10p
""" + tail
    return b


def qrr_metrics(m, P):
    t, vsw, i_d, i_g = m["time"], m["v(sw)"], m["ix(x1:drainin)"], m["ix(x1:gatein)"]
    k0 = next(k for k in range(1, len(t)) if i_d[k - 1] < 0 <= i_d[k])
    q = cumtrapz(t[k0:], i_d[k0:])[-1]
    start = (-0.0, vsw[k0], i_d[k0], i_g[k0])
    end = (-0.0, vsw[-1], i_d[-1], i_g[-1])
    q_cap = drain_charge(P, *end) - drain_charge(P, *start)
    return {"recovered_charge_C": q, "capacitive_charge_C": q_cap, "residual_C": q - q_cap,
            "residual_fraction": (q - q_cap) / q_cap, "zero_crossing_s": t[k0], "vds_at_zero_crossing_V": vsw[k0],
            "vds_end_V": vsw[-1], "drain_current_end_A": i_d[-1]}


def run_model(label, lib, sub, run_root, budget):
    P = subckt_params(lib.read_text(encoding="utf-8", errors="replace"), sub)
    res, failed = {}, {}
    for name, text in benches(lib.name, sub).items():
        if budget["used_s"] >= BUDGET_S:
            failed[name] = "budget exhausted before start"
            continue
        t0 = time.monotonic()
        r = run_ltspice(text, run_root / label / name, libraries=[lib], timeout_s=TIMEOUT_S)
        budget["used_s"] += time.monotonic() - t0
        if r.status != "completed":
            failed[name] = r.message
        else:
            res[name] = r.measurements
    one = lambda n, tr: res[n][tr][0] if n in res else None
    out = {"failed_benches": failed, "rows": {}, "machinery": {}, "sensitivity": {}}
    vals = {"idss": None if "idss" not in res else abs(one("idss", "i(vd)"))}
    for n in ("igss_fwd_25C", "igss_fwd_125C", "igss_rev"):
        vals[n] = None if n not in res else abs(one(n, "i(vg)"))  # datasheet leakage rows are magnitudes
    expected = {k: abs(v) for k, v in {"idss": model_leakage(P, 0, 80)[1], "igss_fwd_25C": model_leakage(P, 5, 0)[0],
                "igss_fwd_125C": model_leakage(P, 5, 0, 125)[0], "igss_rev": model_leakage(P, -4, 0)[0]}.items()}
    for n, row in NEW_ROWS.items():
        bl.DATASHEET[n] = row
        out["rows"][n] = bl.classify(n, vals[n])
        if vals[n] is not None:
            d = vals[n] / expected[n] - 1
            out["machinery"][n] = {"hand_evaluated_A": expected[n], "ltspice_A": vals[n], "relative_difference": d,
                                   "tolerance": MACHINERY_TOL, "outcome": "pass" if abs(d) <= MACHINERY_TOL else "fail"}
    for n in ("igss_fwd_25C_drain_open", "igss_rev_drain_open"):
        if n in res:
            out["sensitivity"][n] = {"igss_A": -one(n, "i(vg)"), "drain_V": one(n, "v(d)")}
    if "bvdss" in res:
        v, i = res["bvdss"]["v(d)"], [-x for x in res["bvdss"]["i(vd)"]]
        hit = next((a for a, b in zip(v, i) if b >= BV_CURRENT), None)
        out["bvdss"] = {"v_at_0.15mA_V": hit, "id_at_100V_A": bl.at(v, i, 100.0), "id_at_200V_A": i[-1],
                        "sweep_max_V": BV_SWEEP, "datasheet_min_V": 100.0,
                        "limit_check": "inside-limits" if hit is None or hit >= 100.0 else "outside-limits"}
    if "vsd_vgs_neg2" in res:
        out["vsd_note"] = {"vsd_vgs_neg2_V": -one("vsd_vgs_neg2", "v(d)")}
    q = {f: qrr_metrics(res[f"qrr_{f:g}A"], P) for f in QRR_CURRENTS if f"qrr_{f:g}A" in res}
    if len(q) == len(QRR_CURRENTS):
        lo, hi = (q[f]["recovered_charge_C"] for f in QRR_CURRENTS)
        r1 = all(abs(x["residual_fraction"]) <= QRR_TOL for x in q.values())
        r2 = abs(hi / lo - 1) <= QRR_TOL
        out["qrr"] = {"per_forward_current": {f"{f:g}A": x for f, x in q.items()}, "R1_capacitive": r1,
                      "R2_current_independent": r2, "current_ratio_change": hi / lo - 1, "tolerance": QRR_TOL}
    return out


def saved_evidence():
    """Reused reports, with identity and status checks; raises if the DS record no longer matches."""
    ds = json.loads(DS_REPORT.read_text(encoding="utf-8"))
    if ds["input_manifest"]["vendor_baseline"] != sha256(VENDOR_BASELINE):
        raise SystemExit("epc2302-baseline.json changed since EPC2302DS recorded it")
    if ds["outcome"] != "pass" or any(ds[k]["outcome"] != "pass" for k in ds if k.startswith("D") and isinstance(ds[k], dict) and "outcome" in ds[k]):
        raise SystemExit("EPC2302DS report outcomes are not all pass")
    files = [DS_REPORT, VENDOR_BASELINE, DS_BASELINE, VENDOR_CURVES, DS_CURVES, VENDOR_FIG7, DS_FIG7]
    return ds, {str(f.relative_to(ROOT).as_posix()): sha256(f) for f in files}


def inventory(ds, new):
    """One record per datasheet item: status per model and the evidence it rests on."""
    base = json.loads(VENDOR_BASELINE.read_text(encoding="utf-8"))["datasheet_table"]
    items = []

    def add(page, item, conditions, kind, vendor, dsm, evidence, note=""):
        items.append({"page": page, "item": item, "conditions": conditions, "kind": kind,
                      "status": {"vendor": vendor, "EPC2302DS": dsm}, "evidence": evidence, "note": note})

    def row_status(r):
        if r.get("model") is None:
            return "not-run"
        if r["limit_check"] == "outside-limits":
            return "fail"
        return "flagged" if r["review"] else "pass"

    for k, r in base.items():
        d = ds["D3_table"]["rows"][k]
        sv, sd = row_status(r), row_status(dict(d, limit_check=d["limit_check"]))
        if k in ("qgd", "qg_th"):
            sv = sd = "unresolved"
        add(2, k, r["conditions"], "table row", sv, sd, "results/gan/epc2302-baseline.json; epc2302-ds-variant.json D3",
            "table definition and Fig. 7 disagree (docs/build.md); flagged in both" if k in ("qgd", "qg_th") else "")
    for k in NEW_ROWS:
        sv, sd = (row_status(new[m]["rows"][k]) for m in ("vendor", "EPC2302DS"))
        mach = [new[m]["machinery"].get(k, {}).get("outcome") for m in ("vendor", "EPC2302DS")]
        if "fail" in mach:
            sv = sd = "unresolved"
        add(2, k, NEW_ROWS[k]["conditions"], "table row", sv, sd, "this report",
            "no temperature dependence in the model's leakage" if "125" in k else "")
    bv = [new[m].get("bvdss") for m in ("vendor", "EPC2302DS")]
    add(2, "bvdss", "VGS = 0 V, ID = 0.15 mA", "table row", "unsupported" if bv[0] else "not-run",
        "unsupported" if bv[1] else "not-run", "this report",
        "no breakdown element: the 100 V minimum is met only because nothing breaks down")
    qs = []
    for m in ("vendor", "EPC2302DS"):
        q = new[m].get("qrr")
        qs.append("not-run" if not q else "pass" if q["R1_capacitive"] and q["R2_current_independent"] else "unresolved")
    add(2, "qrr", "datasheet value 0", "table row", *qs, "this report",
        "0 by construction (no stored-charge element); recovered charge is output charge")
    for fig, (fv, fd) in (("Figure 7", ("fail", "pass")),):
        add(4, fig, "VDS = 50 V, ID = 50 A", "curve", fv, fd, "epc2302-fig7-comparison.json; epc2302ds-fig7-comparison.json")
    for path_v, path_d in ((VENDOR_CURVES, DS_CURVES),):
        cv = json.loads(path_v.read_text(encoding="utf-8"))["figures"]
        cd = json.loads(path_d.read_text(encoding="utf-8"))["figures"]
        for fig, curves in cv.items():
            for c, x in curves.get("curves", curves).items():
                if isinstance(x, dict):
                    y = cd[fig].get("curves", cd[fig])[c]
                    add(3 if fig in ("Figure 1", "Figure 2", "Figure 3", "Figure 4", "Figure 5a", "Figure 5b") else 4,
                        f"{fig} {c}", "", "curve", x.get("outcome"), y.get("outcome"), "curve comparisons")
    vv, vd = (new[m].get("vsd_note", {}).get("vsd_vgs_neg2_V") for m in ("vendor", "EPC2302DS"))
    v0 = base["vsd"]["model"]
    note = lambda v: "not-run" if v is None else "pass" if v > v0 else "fail"
    add(4, "Fig. 11 note: negative gate drive raises reverse VDS", "IS = 0.5 A, VGS = -2 vs 0 V", "qualitative note",
        note(vv), note(vd), "this report")
    for item, page in (("RthJC 0.2 C/W", 2), ("RthJB 1.5 C/W", 2), ("RthJA JEDEC 45 C/W", 2), ("RthJA EPC90142 EVB 21 C/W", 2),
                       ("Figure 12 transient thermal impedance", 5)):
        add(page, item, "", "thermal", "not-modelled", "not-modelled", "none",
            "no EPC2302 thermal network in hand (not in EPC's library archive); the subcircuit has no self-heating")
    for item in ("VDS 100 V continuous", "VDS(tr) 120 V repetitive, duty factor <= 1 %", "ID 133 A continuous (TJ < 125 C)",
                 "ID 408 A pulsed (300 us)", "VGS +6 V", "VGS -4 V", "TJ -40 to 150 C", "TSTG -55 to 175 C"):
        add(1, item, "", "maximum rating", "not-checked", "not-checked", "none",
            "application limit, not a model property; no ratings checker in the evaluation layer (goals S1/S7 are "
            "stricter template limits on board runs only)")
    add(4, "Figure 11 safe operating area", "", "rating", "not-checked", "not-checked", "none", "application limit")
    add(5, "Repetitive-overvoltage illustration (page 5)", "", "rating", "not-checked", "not-checked", "none",
        "duty-factor limit; no checker")
    for item, page in (("Package 3 x 5 mm QFN, pinout, top connected to source", 1), ("Layout recommendation (page 6)", 6),
                       ("Packaging, marking, MSL1", 1)):
        add(page, item, "", "structural", "not-an-electrical-target", "not-an-electrical-target", "none",
            "outside the subcircuit; the board reconstruction uses EPC's own pads")
    return items


def markdown(report):
    lines = ["<!-- generated by scripts/epc2302_coverage.py; do not edit -->",
             f"EPC2302 datasheet coverage, {report['date']}. Status per model; 'pass' means the declared check, not "
             "hardware validation.", "",
             "| Page | Item | Kind | Vendor | EPC2302DS | Note |", "|---|---|---|---|---|---|"]
    for it in report["inventory"]:
        lines.append(f"| {it['page']} | {it['item']} | {it['kind']} | {it['status']['vendor']} | "
                     f"{it['status']['EPC2302DS']} | {it['note']} |")
    lines += ["", "Counts: " + "; ".join(f"{m}: " + ", ".join(f"{k} {v}" for k, v in c.items())
                                         for m, c in report["counts"].items()),
              "", f"Whole datasheet satisfied: {report['whole_datasheet_satisfied']}."]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=OUT / "epc2302-coverage.json")
    args = ap.parse_args()
    lib, _ = bl.library_path()
    lib_sha, datasheet = bl.verify_target_sources(lib)
    ds, reused = saved_evidence()
    ds_lib = ROOT / Path(ds["standalone_library"]["file"].replace("\\", "/"))
    if sha256(ds_lib) != ds["standalone_library"]["sha256"]:
        raise SystemExit(f"{ds_lib} does not match the EPC2302DS report")
    run_root = ROOT / "runs" / ("epc2302-coverage-" + uuid.uuid4().hex)
    budget = {"used_s": 0.0}
    new = {"vendor": run_model("vendor", lib, "EPC2302", run_root, budget),
           "EPC2302DS": run_model("ds", ds_lib, "EPC2302DS", run_root, budget)}
    items = inventory(ds, new)
    counts = {m: {} for m in ("vendor", "EPC2302DS")}
    for it in items:
        for m in counts:
            counts[m][it["status"][m]] = counts[m].get(it["status"][m], 0) + 1
    report = {"schema": "epc2302-coverage/1", "date": "2026-10-09", "run": 2, "scope": __doc__,
              "evaluator_sha256": sha256(__file__),
              "modules": {m: sha256(ROOT / m) for m in ("scripts/epc2302_baseline.py", "scripts/epc2204_baseline.py",
                                                        "src/circuit_tools/ltspice.py", "src/circuit_tools/adapters.py")},
              "datasheet": datasheet, "vendor_library_sha256": lib_sha,
              "ds_library": ds["standalone_library"], "reused_reports": reused,
              "solver_time_s": budget["used_s"], "evidence_directory": run_root.relative_to(ROOT).as_posix(),
              "new_checks": new, "inventory": items, "counts": counts,
              "whole_datasheet_satisfied": False}
    args.output.write_text(json.dumps(report, indent=1, default=float) + "\n", encoding="utf-8")
    args.output.with_suffix(".md").write_text(markdown(report), encoding="utf-8")
    for m, r in new.items():
        print(m, "failed:", r["failed_benches"] or "none")
        for k, row in r["rows"].items():
            print(f"  {k:14s} {row['model']!s:24.24s} limit {row['limit_check']:14s} review {row['review']}  "
                  f"machinery {r['machinery'].get(k, {}).get('outcome')}")
        print("  bvdss", r.get("bvdss")); print("  sensitivity", r["sensitivity"]); print("  vsd", r.get("vsd_note"))
        q = r.get("qrr") or {}
        print("  qrr R1", q.get("R1_capacitive"), "R2", q.get("R2_current_independent"),
              {k: (round(v["recovered_charge_C"] * 1e9, 3), round(v["capacitive_charge_C"] * 1e9, 3), round(v["residual_fraction"], 4))
               for k, v in q.get("per_forward_current", {}).items()})
    print("counts", counts, "solver s", round(budget["used_s"], 1))


if __name__ == "__main__":
    main()
