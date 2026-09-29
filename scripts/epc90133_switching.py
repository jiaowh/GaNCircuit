#!/usr/bin/env python3
"""Switching sensitivity of the stock EPC90133 to the exploratory power-loop extraction (G3, step 3).

Owner review, 29 September 2026: find which layout assumptions change the circuit predictions,
then spend qualification effort where a change would alter a decision. Hold driver, dead-time,
temperature and measurement assumptions fixed while comparing extraction variants. G3 remains
open, and gate-charge-dependent timing and losses are not validated (EPC2302 Fig. 7 exception).

Specification (29 September 2026, before the first run):

Conditions: QSG Fig. 9, continuous buck operation: 48 V in, 13.8 V out, 20 A, 250 kHz, 2.2 uH.
Bench: a converter-equivalent double pulse, not the continuous converter. The lossless operating
point gives D = 0.2875 and 17.9 A peak-to-peak ripple, so Q1 turns off at the peak (28.9 A, event A,
switch-node fall) and turns on again at the valley (11.1 A, event B, switch-node rise) after the
converter's off time. Each edge's inductor current is reported and checked. A direct comparison
with Fig. 9 needs a periodic buck bench or a demonstration that these edges are equivalent; the
periodic case below is that demonstration for the reference variant.

Circuit, fixed for every extraction variant:
* two unmodified EPC2302 models (EPCGaNLibrary.lib), 25 C, reltol 1e-6;
* the extracted branch network (scripts/epc90133_extract.py): each branch an inductor with its
  100 MHz diagonal resistance, every branch pair coupled by K = M/sqrt(L1 L2). Off-diagonal
  resistance is dropped;
* capacitors at their terminals (assumed, not manufacturer models): Ci 220 nF nominal, 110 nF
  effective at 48 V, ESL 0.25 nH, ESR 10 mohm; Cm 1 uF nominal, 0.5 uF effective, ESL 0.35 nH,
  ESR 10 mohm. ESL here is the capacitor body only; pads and copper are in the extraction;
* variants without Cm branches (A, I) carry the ten Cm lumped behind 1 nH and 2 mohm at Ci4's
  terminals; with Cm extracted (B) the supply attaches at Cm10's terminals through the same 1 nH
  and 2 mohm. The supply is 48 V behind 20 mohm and 20 nH;
* uP1966E behavioural output stages of scripts/epc9097_switching.py, recalibrated here against
  the uP1966E datasheet edge times; 1/0 ohm gate resistors (R80-R83); ideal 5 V driver and
  high-side supplies; drivers return at the FET source terminals (gate loops not extracted, so no
  common-source inductance); 10 ns dead time at the driver inputs (R620/R625 = 120 ohm, QSG Fig. 4),
  driver delay mismatch omitted;
* output: 2.2 uH ideal inductor from the Q2 drain terminal to an ideal 13.8 V source;
* measurement: V(SW) is Q2's drain terminal against its source terminal, an ideal probe at the pads.

Sensitivity cases: every extraction result found (variants A/I/B, meshes, via representations),
an ideal-copper case (branches of 1 pH, 0.1 mohm, uncoupled), and capacitor-model cases on the
reference B-m1-mid (body ESL 0 and 2x). Reference for differences: B-m1-mid.
Materiality (fixed before running; judgement thresholds, not tolerances): a metric change is
material if the switch-node rise or fall time changes by more than 10%, the rise-edge peak
overshoot above the bus by more than 10% or 1 V, the ringing frequency by more than 5%, or the
damping ratio by more than 20%.
Checks per case: the transient completes; the edge currents are within 2% (event A) and 5%
(event B) of the lossless peak and valley. Numerical check on the reference: maxstep/2 and
reltol/10 change no reported metric by more than 2%.
"""
import argparse
import glob
import hashlib
import json
import math
from pathlib import Path
import sys
import uuid

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from circuit_tools.ltspice import parse_raw, run_ltspice
import epc2302_baseline as bl
from epc9097_switching import (DRIVER_FALL, DRIVER_RISE, EDGE_GRID, R_SNK, R_SRC, SWITCH_MODELS, cross,
                               drive_stage, driver_bench, edge_times, integral, interp, solve_edge, window)

VIN, VOUT, IOUT, F_SW, L_OUT = 48.0, 13.8, 20.0, 250e3, 2.2e-6
DUTY = VOUT / VIN
T_OFF = (1 - DUTY) / F_SW
RIPPLE = (VIN - VOUT) * DUTY / (F_SW * L_OUT)
I_PEAK, I_VALLEY = IOUT + RIPPLE / 2, IOUT - RIPPLE / 2
DEAD = 10e-9
VCC = VBOOT = 5.0
R_GON, R_GOFF = 1.0, 0.0
T_ON2 = 150e-9
MAXSTEP, RELTOL = 20e-12, 1e-6
CAP_MODEL = {"Ci": {"C": 110e-9, "ESL": 0.25e-9, "ESR": 10e-3}, "Cm": {"C": 0.5e-6, "ESL": 0.35e-9, "ESR": 10e-3}}
N_CM = 10
BUS = {"R_sup": 20e-3, "L_sup": 20e-9, "R_bus": 2e-3, "L_bus": 1e-9}
REFERENCE = "B-m1-mid"
NUMERICAL_REF = "A-m1-mid"
MATERIAL = {"sw_fall_time_90_10_s": ("rel", 0.10), "sw_rise_time_10_90_s": ("rel", 0.10),
            "sw_overshoot_above_bus_V": ("rel_or_abs", 0.10, 1.0), "ringing_frequency_Hz": ("rel", 0.05),
            "ringing_damping_ratio": ("rel", 0.20)}
EXTRACTIONS = ROOT / "results/gan/epc90133-extraction"
# Added 29 September 2026 after the literature review (docs/gan-layout-literature-notes.md), before
# their first run. Package inductance: the vendor model has none (EPC AN005 structure) and the QFN
# value is not published, so an assumed bracket in series with each FET drain and source terminal;
# the drivers stay at the pads, so the source term acts as common-source inductance. Switch-node
# capacitance: parallel-plate overlap of SW copper with adjacent-layer copper over the whole board
# (Gerber raster, er 4.8, no fringing): 135 pF to GND and 2 pF to VIN, placed at the FET terminals.
L_PKG_CASES = (50e-12, 150e-12)
C_SW = {"GND": 135e-12, "VIN": 2e-12}


def node(t):
    return {"Q2.S": "0"}.get(t, t.replace(".", "_").lower())


def network(ext, ideal=False):
    """Branch inductors, resistances and couplings from an extraction report."""
    L = np.array(ext["L_H"])
    R = np.array(ext["R_ohm"])
    lines = [f"* extracted branch network: {ext['case']}"]
    names = []
    for k, p in enumerate(ext["ports"]):
        lk, rk = (1e-12, 1e-4) if ideal else (L[k, k], R[k, k])
        lines.append(f"Lb{k} {node(p['terminal'])} xb{k} {lk:.6g}")
        lines.append(f"Rb{k} xb{k} {node(p['reference'])} {rk:.6g}")
        names.append(f"Lb{k}")
    if not ideal:
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                kij = L[i, j] / math.sqrt(L[i, i] * L[j, j])
                lines.append(f"K{i}_{j} Lb{i} Lb{j} {kij:.6g}")
    return "\n".join(lines), [p["terminal"] for p in ext["ports"]]


def capacitor(tag, p, n, model, scale=1.0):
    return (f"C{tag} {p} x{tag}a {model['C']:.6g}\nR{tag} x{tag}a x{tag}b {model['ESR']:.6g}\n"
            f"L{tag} x{tag}b {n} {max(model['ESL'] * scale, 1e-15):.6g}")


def bench(ext, te_rise, te_fall, esl_scale=1.0, ideal=False, maxstep=MAXSTEP, reltol=RELTOL, periods=None, timing=None,
          l_pkg=0.0, c_sw=False):
    net, terms = network(ext, ideal)
    caps = sorted({t.rsplit(".", 1)[0] for t in terms if t.startswith("C")})
    lines = [net]
    for c in caps:
        lines.append(capacitor(c, node(f"{c}.VIN"), node(f"{c}.GND"), CAP_MODEL[c[:2]], esl_scale))
    m = CAP_MODEL["Cm"]
    if any(c.startswith("Cm") for c in caps):
        at = "Cm10"
        bus = f"""Vin bp bn {VIN:g}
Rsup bp bs {BUS['R_sup']:g}
Lsup bs bc {BUS['L_sup']:g}
Rbus bc bx {BUS['R_bus']:g}
Lbus bx {node(at + '.VIN')} {BUS['L_bus']:g}
Rbret bn {node(at + '.GND')} 1u"""
    else:
        at = "Ci4"
        bus = f"""Vin bp bn {VIN:g}
Rsup bp bs {BUS['R_sup']:g}
Lsup bs bc {BUS['L_sup']:g}
Ccm bc xcm1 {N_CM * m['C']:.6g}
Rcm xcm1 xcm2 {m['ESR'] / N_CM:.6g}
Lcm xcm2 bn {max(m['ESL'] * esl_scale / N_CM, 1e-15):.6g}
Rbus bc bx {BUS['R_bus']:g}
Lbus bx {node(at + '.VIN')} {BUS['L_bus']:g}
Rbret bn {node(at + '.GND')} 1u"""
    lines.append(bus)
    t_on1 = 20e-9
    timing = timing or {}
    if periods is None:
        # First pulse to the peak, then the off interval down to the valley; nominal values are lossless,
        # and main() corrects them once from each case's own first run.
        t_off1 = t_on1 + timing.get("t1", I_PEAK / ((VIN - VOUT) / L_OUT))
        t_on2 = t_off1 + timing.get("t_off", T_OFF)
        hi = [(t_on1, 1), (t_off1, 0), (t_on2, 1), (t_on2 + T_ON2, 0)]
        lo = [(t_off1 + DEAD, 1), (t_on2 - DEAD, 0), (t_on2 + T_ON2 + DEAD, 1)]
        t_end = t_on2 + T_ON2 + 100e-9
        times = {"t_off1": t_off1, "t_on2": t_on2, "t_end": t_end}
        l_ic = ""
    else:
        # Periodic buck at a loss-corrected duty cycle, starting at the valley current.
        T = 1 / F_SW
        duty = timing.get("duty", DUTY)
        hi, lo = [], []
        for k in range(periods):
            t0 = t_on1 + k * T
            hi += [(t0, 1), (t0 + duty * T, 0)]
            lo += [(t0 + duty * T + DEAD, 1), (t0 + T - DEAD, 0)]
        t_end = t_on1 + periods * T + 50e-9  # run 1 ended before the last low-side edge
        k = periods - 1
        times = {"t_off1": t_on1 + k * T + duty * T, "t_on2": t_on1 + k * T, "t_end": t_end, "duty": duty,
                 "period_starts_s": [t_on1 + j * T for j in range(periods)],
                 "note": "last period: event B at its start, event A at the end of its on-time"}
        # Run 1 used .ic I(L1) with an operating-point solve, which failed on B (Gmin and source stepping:
        # 11 A forced through the off FETs). The transient now skips the operating point (uic) and sets the
        # initial state explicitly: every VIN-side node at the bus voltage, all others at 0 V, and the valley
        # current in L1. The first periods absorb the start-up; only the last period is measured.
        vin_nodes = {"bp", "bs", "bc", "bx", "q1_d", "q1dd"} | ({"p1d"} if l_pkg else set())
        for k, p in enumerate(ext["ports"]):
            if p["reference"] == "Q1.D":
                vin_nodes |= {node(p["terminal"]), f"xb{k}"}
        l_ic = (f"\n.ic I(L1)={timing.get('i0', I_VALLEY):.6g} "
                + " ".join(f"V({n})={VIN:g}" for n in sorted(vin_nodes)))
    lines += [
        "Vq1d q1_d q1dd 0",
        *([f"Lp1d q1dd p1d {l_pkg:g}", f"Lp1s p1s q1_s {l_pkg:g}", f"Lp2d q2_d p2d {l_pkg:g}", f"Lp2s p2s 0 {l_pkg:g}",
           "X1 gu p1d p1s EPC2302", "X2 gl p2d p2s EPC2302"] if l_pkg else
          ["X1 gu q1dd q1_s EPC2302", "X2 gl q2_d 0 EPC2302"]),
        *([f"Csw_gnd q2_d 0 {C_SW['GND']:g}", f"Csw_vin q2_d q1_d {C_SW['VIN']:g}"] if c_sw else []),
        f"L1 q2_d out {L_OUT:g}{l_ic}",
        f"Vout out 0 {VOUT:g}",
        drive_stage("u", "q1_s", VBOOT, hi, te_rise, te_fall, "gu", R_SRC, R_SNK, R_GON, R_GOFF, t_end).rstrip(),
        drive_stage("l", "0", VCC, lo, te_rise, te_fall, "gl", R_SRC, R_SNK, R_GON, R_GOFF, t_end).rstrip(),
        SWITCH_MODELS.rstrip(),
        ".save V(q2_d) V(q1_d) V(q1_s) V(gu) V(gl) I(Vq1d) I(L1)" + (f" V({node(at + '.VIN')}) V({node(at + '.GND')})"),
        ".temp 25",
        f".options plotwinsize=0 reltol={reltol:g}",
        f".tran 0 {t_end:.9g} 0 {maxstep:g}" + (" uic" if periods else ""),
        ".end", ""]
    head = (f"* EPC90133 switching sensitivity, extraction {ext['case']}{' (ideal copper)' if ideal else ''}; "
            "generated by scripts/epc90133_switching.py\n.lib EPCGaNLibrary.lib\n")
    return head + "\n".join(lines), times, at


def metrics(s, times, at):
    t = s["time"]
    sw, d1, s1, gu, gl = s["v(q2_d)"], s["v(q1_d)"], s["v(q1_s)"], s["v(gu)"], s["v(gl)"]
    vds1 = [a - b for a, b in zip(d1, s1)]
    vgs1 = [a - b for a, b in zip(gu, s1)]
    id1, il = s["i(vq1d)"], s["i(l1)"]
    p1 = [a * b for a, b in zip(vds1, id1)]
    bus = [a - b for a, b in zip(s[f"v({node(at + '.VIN')})"], s[f"v({node(at + '.GND')})"])] \
        if node(at + ".GND") != "0" else s[f"v({node(at + '.VIN')})"]
    ta, tb = times["t_off1"], times["t_on2"]
    vb_b = interp(t, bus, tb)
    a90, a10 = cross(t, sw, 0.9 * VIN, ta, False), cross(t, sw, 0.1 * VIN, ta, False)
    ga = cross(t, vgs1, 0.9 * VBOOT, ta, False)
    a_end = cross(t, vds1, 0.9 * VIN, ta, True)
    wa = window(t, vds1, ta, ta + 60e-9)
    event_a = {"inductor_current_A": interp(t, il, ta),
               "sw_fall_time_90_10_s": (a10 - a90) if a90 and a10 else None,
               "q1_vds_peak_V": max(v for _, v in wa),
               "sw_min_V": min(v for _, v in window(t, sw, ta, ta + 60e-9)),
               "q1_eoff_J": integral(t, p1, ga, a_end + 2e-9) if ga and a_end else None}
    gb = cross(t, vgs1, 0.1 * VBOOT, tb, True)
    b10, b90 = cross(t, sw, 0.1 * VIN, tb, True), cross(t, sw, 0.9 * VIN, tb, True)
    b_end = cross(t, vds1, 0.1 * VIN, tb, False)
    ring = window(t, sw, tb, tb + 60e-9)
    peak_t, peak_v = max(ring, key=lambda p: p[1])
    freq, damping = ringing(ring, peak_t)
    event_b = {"inductor_current_A": interp(t, il, tb),
               "sw_rise_time_10_90_s": (b90 - b10) if b10 and b90 else None,
               "sw_peak_V": peak_v, "sw_overshoot_above_bus_V": peak_v - vb_b, "bus_at_event_V": vb_b,
               "ringing_frequency_Hz": freq, "ringing_damping_ratio": damping,
               "q1_peak_drain_current_A": max(v for _, v in window(t, id1, tb, tb + 60e-9)),
               "q1_eon_J": integral(t, p1, gb, b_end) if gb and b_end else None,
               "q2_gate_peak_during_rise_V": max(v for _, v in window(t, gl, tb, tb + 60e-9))}
    return {"event_a_turn_off_at_peak": event_a, "event_b_turn_on_at_valley": event_b,
            "not_validated": "q1_eoff_J, q1_eon_J and the edge times depend on gate charge (EPC2302 Fig. 7 exception)"}


def ringing(ring, peak_t, hyst=0.5):
    """Ringing frequency and damping from crossings of the settled level, with hysteresis.

    Run 1's local-maximum detector picked numerical wiggles on a finer time step (3.98 GHz with
    every waveform metric unchanged); crossings of the level settled 40-60 ns after the edge are
    insensitive to them. Damping uses the logarithmic decrement of successive same-sign extremes.
    """
    late = [v for tt, v in ring if tt >= ring[-1][0] - 20e-9]
    level = sum(late) / len(late)
    pts = [(tt, v - level) for tt, v in ring if tt >= peak_t]
    cross, state, ext, extremes = [], 1, 0.0, []
    for (t0, a), (t1, b_) in zip(pts, pts[1:]):
        ext = max(ext, abs(a))
        if state > 0 and b_ < -hyst or state < 0 and b_ > hyst:
            cross.append(t0)
            extremes.append(ext)
            ext, state = 0.0, -state
    if len(cross) < 4:
        return None, None
    half = [b_ - a for a, b_ in zip(cross, cross[1:])][:6]
    freq = 1 / (2 * sum(half) / len(half))
    damping = None
    if len(extremes) >= 3 and extremes[2] > 0:
        delta = math.log(extremes[0] / extremes[2])
        damping = delta / math.sqrt(4 * math.pi ** 2 + delta ** 2)
    return freq, damping


def flat(m):
    return {**{k: v for k, v in m["event_a_turn_off_at_peak"].items()}, **{k: v for k, v in m["event_b_turn_on_at_valley"].items()}}


def material(ref, other):
    out = {}
    for k, rule in MATERIAL.items():
        a, b = ref.get(k), other.get(k)
        if a is None or b is None:
            out[k] = {"reference": a, "case": b, "material": None}
            continue
        rel = (b - a) / abs(a) if a else float("inf")
        mat = abs(rel) > rule[1] or (rule[0] == "rel_or_abs" and abs(b - a) > rule[2])
        out[k] = {"reference": a, "case": b, "relative_change": rel, "material": bool(mat)}
    return out


def main():
    global REFERENCE
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-switching-sensitivity.json")
    ap.add_argument("--cases", nargs="*", default=None, help="extraction names (e.g. A-m1-mid); default: all found")
    ap.add_argument("--no-extra", action="store_true", help="skip ideal, capacitor, numerical and periodic cases")
    ap.add_argument("--reference", default=REFERENCE, help="reference extraction for differences and extra cases")
    args = ap.parse_args()
    REFERENCE = args.reference
    lib, _ = bl.library_path()
    bl.verify_target_sources(lib)
    run_root = ROOT / "runs" / ("epc90133-switching-" + uuid.uuid4().hex[:12])
    runs = {}

    def run(name, text, timeout=600):  # the adapter allows at most 600 s
        r = run_ltspice(text, run_root / name, libraries=[lib], timeout_s=timeout)
        runs[name] = {"status": r.status, "message": r.message, "duration_s": r.duration_s,
                      "warnings": r.provenance.get("log_warnings"), "netlist_sha256": r.provenance.get("netlist_sha256")}
        return parse_raw(r.result_path) if r.status == "completed" and r.result_path else None

    rises, falls = [], []
    for name, text in driver_bench().items():
        raw = run(name, text)
        rf = edge_times(raw)[0] if raw else (None, None)
        rises.append(rf[0])
        falls.append(rf[1])
    te_rise, te_fall = solve_edge(EDGE_GRID, rises, DRIVER_RISE), solve_edge(EDGE_GRID, falls, DRIVER_FALL)
    if te_rise is None or te_fall is None:
        raise SystemExit("driver calibration did not bracket the datasheet edge times")

    files = sorted(glob.glob(str(EXTRACTIONS / "*.json")))
    exts = {Path(f).stem: json.loads(Path(f).read_text(encoding="utf-8")) for f in files}
    exts = {k: v for k, v in exts.items() if v.get("outcome") == "complete" and (args.cases is None or k in args.cases)}
    cases = {k: {"ext": k} for k in exts}
    if not args.no_extra and REFERENCE in exts:
        cases["ideal-copper"] = {"ext": REFERENCE, "ideal": True}
        cases[f"{REFERENCE}-esl0.5x"] = {"ext": REFERENCE, "esl_scale": 0.5}  # esl 0 (1 fF) stalled the solver
        cases[f"{REFERENCE}-esl2x"] = {"ext": REFERENCE, "esl_scale": 2.0}
        for lp in L_PKG_CASES:
            cases[f"{REFERENCE}-pkg{lp * 1e12:.0f}pH"] = {"ext": REFERENCE, "l_pkg": lp}
        cases[f"{REFERENCE}-csw"] = {"ext": REFERENCE, "c_sw": True}
        # On B the fine run exceeded the adapter's 600 s limit (sweep 1); the numerical check runs on A.
        if NUMERICAL_REF in exts:
            cases[f"{NUMERICAL_REF}-fine"] = {"ext": NUMERICAL_REF, "maxstep": MAXSTEP / 2, "reltol": RELTOL / 10}
        cases[f"{REFERENCE}-periodic3"] = {"ext": REFERENCE, "periods": 3}
    results, slopes = {}, {}
    for name, c in cases.items():
        ext = exts[c["ext"]]
        kw = dict(esl_scale=c.get("esl_scale", 1.0), ideal=c.get("ideal", False),
                  maxstep=c.get("maxstep", MAXSTEP), reltol=c.get("reltol", RELTOL),
                  l_pkg=c.get("l_pkg", 0.0), c_sw=c.get("c_sw", False))
        first = None
        if c.get("periods"):
            # Loss-corrected duty cycle from the reference's measured slopes, started at the matching valley.
            s_on, s_off = slopes[REFERENCE]
            duty = s_off / (s_on + s_off)
            timing = {"duty": duty, "i0": IOUT - s_on * duty / F_SW / 2}
            text, times, at = bench(ext, te_rise, te_fall, periods=c["periods"], timing=timing, **kw)
        else:
            # Run 1 of the first bench run missed the edge currents (-2.6% and -5.8%): losses reduce the
            # slopes. Each case therefore runs once at the lossless timing and once corrected from its slopes.
            text, times, at = bench(ext, te_rise, te_fall, **kw)
            raw0 = run(name + "-timing", text)
            m0 = metrics(raw0.step(0), times, at) if raw0 else None
            if m0 is None:
                results[name] = {"parameters": c, "metrics": None, "checks": None}
                print(name, "timing run failed:", runs[name + "-timing"]["message"], flush=True)
                continue
            ia = m0["event_a_turn_off_at_peak"]["inductor_current_A"]
            ib = m0["event_b_turn_on_at_valley"]["inductor_current_A"]
            s_on, s_off = ia / (times["t_off1"] - 20e-9), (ia - ib) / (times["t_on2"] - times["t_off1"])
            slopes[name] = (s_on, s_off)
            timing = {"t1": I_PEAK / s_on, "t_off": (I_PEAK - I_VALLEY) / s_off}
            first = {"edge_currents_A": [ia, ib], "slopes_A_per_s": [s_on, s_off], "corrected_timing_s": timing}
            text, times, at = bench(ext, te_rise, te_fall, timing=timing, **kw)
        raw = run(name, text)
        m = metrics(raw.step(0), times, at) if raw else None
        if m and c.get("periods"):
            s = raw.step(0)
            m["periodicity"] = {"inductor_current_at_period_starts_A": [interp(s["time"], s["i(l1)"], t) for t in times["period_starts_s"]],
                                "timing": timing}
        ok = None
        if m:
            ia, ib = m["event_a_turn_off_at_peak"]["inductor_current_A"], m["event_b_turn_on_at_valley"]["inductor_current_A"]
            ok = {"edge_current_A_within_2pct": abs(ia / I_PEAK - 1) <= 0.02, "edge_current_B_within_5pct": abs(ib / I_VALLEY - 1) <= 0.05}
        results[name] = {"parameters": {k: v for k, v in c.items()}, "extraction_case": ext["case"], "timing_run": first,
                         "extraction_summary": ext.get("summary"), "times_s": times, "bus_attachment": at,
                         "metrics": m, "checks": ok}
        if m:
            f = flat(m)
            print(f"{name:22s} Ia {m['event_a_turn_off_at_peak']['inductor_current_A']:.2f} "
                  f"tf {f['sw_fall_time_90_10_s'] * 1e9 if f['sw_fall_time_90_10_s'] else float('nan'):.3f} ns | "
                  f"Ib {m['event_b_turn_on_at_valley']['inductor_current_A']:.2f} tr {f['sw_rise_time_10_90_s'] * 1e9 if f['sw_rise_time_10_90_s'] else float('nan'):.3f} ns "
                  f"peak {f['sw_peak_V']:.2f} V over {f['sw_overshoot_above_bus_V']:.2f} V "
                  f"f {(f['ringing_frequency_Hz'] or float('nan')) / 1e6:.1f} MHz zeta {f['ringing_damping_ratio'] or float('nan'):.3f} "
                  f"Q1 Vds pk {f['q1_vds_peak_V']:.2f} V", flush=True)
        else:
            print(name, "failed:", runs[name]["message"], flush=True)
    comparison = {}
    if REFERENCE in results and results[REFERENCE]["metrics"]:
        ref = flat(results[REFERENCE]["metrics"])
        for name, r in results.items():
            if name != REFERENCE and r["metrics"]:
                comparison[name] = material(ref, flat(r["metrics"]))
    numerical = None
    fine = results.get(f"{NUMERICAL_REF}-fine")
    if fine and fine["metrics"] and NUMERICAL_REF in results and results[NUMERICAL_REF]["metrics"]:
        a, b_ = flat(results[NUMERICAL_REF]["metrics"]), flat(fine["metrics"])
        keys = list(MATERIAL) + ["sw_peak_V", "q1_vds_peak_V", "q1_peak_drain_current_A"]
        rel = {k: (b_[k] - a[k]) / abs(a[k]) for k in keys if a.get(k) and b_.get(k) is not None}
        numerical = {"relative_change": rel, "pass": all(abs(v) <= 0.02 for v in rel.values()) and len(rel) == len(keys)}
    report = {
        "schema": "epc90133-switching-sensitivity/1",
        "numerical_check": numerical,
        "scope": ("Sensitivity of simulated switching to exploratory extraction assumptions. Not a validated prediction: "
                  "the extraction is unqualified for plane holes and via arrays, the driver is behavioural, capacitor "
                  "models are assumed, and gate-charge-dependent quantities carry the EPC2302 Fig. 7 exception."),
        "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "conditions": {"VIN": VIN, "VOUT": VOUT, "IOUT": IOUT, "f_sw_Hz": F_SW, "L_out_H": L_OUT, "duty": DUTY,
                       "ripple_A": RIPPLE, "I_peak_A": I_PEAK, "I_valley_A": I_VALLEY, "dead_time_s": DEAD,
                       "source": "EPC90133 QSG Fig. 9 (continuous buck; measured tf 3.7 ns, tr 1.7 ns)"},
        "fixed_assumptions": {"capacitors": CAP_MODEL, "bus": BUS, "N_cm_lumped": N_CM, "gate_resistors_ohm": [R_GON, R_GOFF],
                              "driver_supplies_V": [VCC, VBOOT], "temperature_C": 25, "maxstep_s": MAXSTEP, "reltol": RELTOL,
                              "measurement": "ideal probe, Q2 drain terminal to Q2 source terminal"},
        "driver_calibration": {"pull_up_edge_s": te_rise, "pull_down_edge_s": te_fall, "targets_s": [DRIVER_RISE, DRIVER_FALL]},
        "reference": REFERENCE, "materiality": MATERIAL, "cases": results, "comparison_to_reference": comparison,
        "runs": runs, "evidence_directory": str(run_root.relative_to(ROOT)),
    }
    args.output.write_text(json.dumps(report, indent=1) + "\n")


if __name__ == "__main__":
    main()
