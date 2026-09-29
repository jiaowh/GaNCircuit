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

Test 5, candidate causes of the gap to QSG Fig. 9 (--study causes; specification of 30 September 2026,
written after digitizing Fig. 9 with scripts/digitize_epc90133_qsg_fig9.py and before the first run).
The digitized measurement (vendor-described, probe unknown): rise 1.68 ns, overshoot 5.7 V above the
settled level, ringing 264 MHz with a 7.8 ns decay time (damping ratio about 0.077), fall 3.63 ns,
4.6 V undershoot, and a dead-time plateau of about 7 ns at about -2.5 V. The unmodified reference B gives
0.83 ns, 36 V, 282 MHz and a damping ratio of 0.010. Each case changes one thing from its base, with every
other assumption held at the test 1-4 values:
* package inductance, 50 and 150 pH per drain and source terminal (assumed; the EPC2302 value is not
  published), with the 10 GHz damping resistors; the gate drivers stay at the pads, so the source terms act
  as common-source inductance;
* frequency-dependent copper resistance: every branch resistance x sqrt(282 MHz / 100 MHz) = 1.68, the
  skin-effect scaling from the 100 MHz extraction to the reference's ringing frequency (literature notes:
  AC resistance about x3 per decade);
* driver at the uP1966E datasheet maximum output resistance (1.4 ohm pull-up, 0.8 ohm pull-down);
* damping requirement, not a physical model: every capacitor ESR raised from 10 mohm to 0.3 and 1 ohm.
  Capacitor ESR carries no DC current, so these cases add loop resistance without changing conduction.
  They show how much series resistance the measured decay implies and whether damping alone changes the
  first overshoot; they do not identify its source (Coss loss, dielectric loss, probe);
* checks on A: the package case, and its damping-resistor corner at 20 GHz (material change = the
  corner matters);
* one combination of the physically motivated changes (package 50 pH, copper x1.68, driver maximum),
  exploratory.
Added during test 5, before any B package result existed: the B package and combined cases use a 100 ps
maximum step (20 ps exceeded the 600 s limit even with B run alone), checked on B without package and on A
with package against 20 ps.
Probe and oscilloscope bandwidth are applied afterwards to the saved traces by
scripts/compare_epc90133_fig9.py. The gate-charge exception (EPC2302 Fig. 7: the model's Miller plateau is
24% narrow) is not tested: the model stays unmodified.
"""
import argparse
import glob
import hashlib
import json
import math
from pathlib import Path
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from circuit_tools.ltspice import parse_raw, run_ltspice
import epc2302_baseline as bl
from epc9097_switching import (DRIVER_FALL, DRIVER_RISE, EDGE_GRID, R_SNK, R_SNK_MAX, R_SRC, R_SRC_MAX, SWITCH_MODELS,
                               cross, drive_stage, driver_bench, edge_times, integral, interp, solve_edge, window)

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
# Test 5 (30 September 2026). Test 4's package cases showed single-sample V(SW) spikes with the time step
# collapsing to 2e-20 s. A resistor across each package inductor, R = 2 pi f_c L with f_c = 10 GHz, removed
# every spike on A-pkg50pH with trapezoidal or Gear integration, and the two methods then agreed within 0.1%
# on every metric; Gear alone left 625 spikes. At the 0.2-0.3 GHz ringing the resistor carries about 3% of
# the inductor current. The corner is checked by a 20 GHz case. Every case now runs a spike check.
R_PKG_CORNER_HZ = 10e9
SPIKE_V = 5.0  # V: a sample more than this from the mean of its two neighbours is a spike
TRACE_WINDOW = (-30e-9, 70e-9)  # s around each event, saved for the Fig. 9 comparison
TRACE_STEP = 25e-12


def node(t):
    return {"Q2.S": "0"}.get(t, t.replace(".", "_").lower())


def network(ext, ideal=False, r_scale=1.0):
    """Branch inductors, resistances and couplings from an extraction report."""
    L = np.array(ext["L_H"])
    R = np.array(ext["R_ohm"])
    lines = [f"* extracted branch network: {ext['case']}"]
    names = []
    for k, p in enumerate(ext["ports"]):
        lk, rk = (1e-12, 1e-4) if ideal else (L[k, k], R[k, k] * r_scale)
        lines.append(f"Lb{k} {node(p['terminal'])} xb{k} {lk:.6g}")
        lines.append(f"Rb{k} xb{k} {node(p['reference'])} {rk:.6g}")
        names.append(f"Lb{k}")
    if not ideal:
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                kij = L[i, j] / math.sqrt(L[i, i] * L[j, j])
                lines.append(f"K{i}_{j} Lb{i} Lb{j} {kij:.6g}")
    return "\n".join(lines), [p["terminal"] for p in ext["ports"]]


def capacitor(tag, p, n, model, scale=1.0, esr=None):
    return (f"C{tag} {p} x{tag}a {model['C']:.6g}\nR{tag} x{tag}a x{tag}b {esr if esr is not None else model['ESR']:.6g}\n"
            f"L{tag} x{tag}b {n} {max(model['ESL'] * scale, 1e-15):.6g}")


def bench(ext, te_rise, te_fall, esl_scale=1.0, ideal=False, maxstep=MAXSTEP, reltol=RELTOL, periods=None, timing=None,
          l_pkg=0.0, c_sw=False, r_pkg_corner=R_PKG_CORNER_HZ, r_scale=1.0, esr=None, r_src=R_SRC, r_snk=R_SNK,
          c_gd=0.0):
    net, terms = network(ext, ideal, r_scale)
    caps = sorted({t.rsplit(".", 1)[0] for t in terms if t.startswith("C")})
    lines = [net]
    for c in caps:
        lines.append(capacitor(c, node(f"{c}.VIN"), node(f"{c}.GND"), CAP_MODEL[c[:2]], esl_scale, esr))
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
Rcm xcm1 xcm2 {(esr if esr is not None else m['ESR']) / N_CM:.6g}
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
        # Periodic buck at a loss-corrected duty cycle.
        # History: run 1 used .ic I(L1) with an operating-point solve, which failed on B (Gmin and source
        # stepping: 11 A forced through the off FETs). Test 4 skipped the operating point (uic) with every
        # VIN-side node at the bus voltage and the valley current in L1; on A it stalled at 0.77 ps with
        # 1e-19 s steps (the model-internal nodes started at 0 V). In test 5 an operating point with the
        # low-side FET on and .ic I(L1) was found only by LTspice's pseudo-transient fallback, after Newton,
        # Gmin and source stepping failed (a .nodeset guess did not help), which the adapter reports as a
        # failed run. The bench therefore starts like the double pulse, from the all-off, zero-current
        # operating point: a first pulse ramps L1 to the peak current, then the converter runs `periods`
        # full periods (off interval to the valley, then on). The last period is measured, and the valley
        # currents of successive periods are reported as the periodicity check.
        T = 1 / F_SW
        duty = timing.get("duty", DUTY)
        t1 = timing["t1"]
        hi, lo = [(t_on1, 1), (t_on1 + t1, 0)], [(t_on1 + t1 + DEAD, 1)]
        starts = [t_on1 + t1 + (1 - duty) * T + k * T for k in range(periods)]
        for t0 in starts:
            lo.append((t0 - DEAD, 0))
            hi += [(t0, 1), (t0 + duty * T, 0)]
            lo.append((t0 + duty * T + DEAD, 1))
        t_end = starts[-1] + duty * T + 100e-9
        times = {"t_off1": starts[-1] + duty * T, "t_on2": starts[-1], "t_end": t_end, "duty": duty,
                 "period_starts_s": starts,
                 "note": "last period: event B (valley turn-on) at its start, event A (peak turn-off) at the end of its on-time"}
        l_ic = ""
    lines += [
        "Vq1d q1_d q1dd 0",
        *([f"Lp1d q1dd p1d {l_pkg:g}", f"Lp1s p1s q1_s {l_pkg:g}", f"Lp2d q2_d p2d {l_pkg:g}", f"Lp2s p2s 0 {l_pkg:g}",
           *(f"Rp{n} {a} {b} {2 * math.pi * r_pkg_corner * l_pkg:.6g}"
             for n, a, b in (("1d", "q1dd", "p1d"), ("1s", "p1s", "q1_s"), ("2d", "q2_d", "p2d"), ("2s", "p2s", "0"))),
           "X1 gu p1d p1s EPC2302", "X2 gl p2d p2s EPC2302"] if l_pkg else
          ["X1 gu q1dd q1_s EPC2302", "X2 gl q2_d 0 EPC2302"]),
        *([f"Csw_gnd q2_d 0 {C_SW['GND']:g}", f"Csw_vin q2_d q1_d {C_SW['VIN']:g}"] if c_sw else []),
        *([f"Cgdx1 gu q1dd {c_gd:g}", f"Cgdx2 gl q2_d {c_gd:g}"] if c_gd else []),
        f"L1 q2_d out {L_OUT:g}{l_ic}",
        f"Vout out 0 {VOUT:g}",
        drive_stage("u", "q1_s", VBOOT, hi, te_rise, te_fall, "gu", r_src, r_snk, R_GON, R_GOFF, t_end).rstrip(),
        drive_stage("l", "0", VCC, lo, te_rise, te_fall, "gl", r_src, r_snk, R_GON, R_GOFF, t_end).rstrip(),
        SWITCH_MODELS.rstrip(),
        ".save V(q2_d) V(q1_d) V(q1_s) V(gu) V(gl) I(Vq1d) I(L1)" + (f" V({node(at + '.VIN')}) V({node(at + '.GND')})"),
        ".temp 25",
        f".options plotwinsize=0 reltol={reltol:g}",
        f".tran 0 {t_end:.9g} 0 {maxstep:g}",
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


def spikes(s):
    """Single-sample V(SW) spikes (the test 4 artefact): count, and the smallest time step."""
    t, v = np.array(s["time"]), np.array(s["v(q2_d)"])
    d = v[1:-1] - 0.5 * (v[:-2] + v[2:])
    return {"count": int(np.sum(np.abs(d) > SPIKE_V)), "threshold_V": SPIKE_V, "min_step_s": float(np.min(np.diff(t)))}


def edge_traces(s, times):
    """V(SW) (Q2 drain pad to Q2 source pad, ideal probe) resampled around both events."""
    t, v = np.array(s["time"]), np.array(s["v(q2_d)"])
    rel = np.arange(TRACE_WINDOW[0], TRACE_WINDOW[1] + TRACE_STEP / 2, TRACE_STEP)
    return {"step_s": TRACE_STEP, "start_s": TRACE_WINDOW[0],
            "event_times_s": {"falling": times["t_off1"], "rising": times["t_on2"]},
            "falling_V": [round(float(x), 4) for x in np.interp(times["t_off1"] + rel, t, v)],
            "rising_V": [round(float(x), 4) for x in np.interp(times["t_on2"] + rel, t, v)]}


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


R_SKIN = math.sqrt(282e6 / 100e6)
MAXSTEP_PKG = 100e-12
C_GD_DEFICIT = (2.867 - 2.187) * 1e-9 / 50.0  # F; results/gan/epc2302-fig7-comparison.json plateau widths


def cause_cases(exts):
    """Test 5 cases (see the module docstring); each names the case it is compared with."""
    b, a = "B-m1-mid", "A-m1-mid"
    cases = {b: {"ext": b}}
    # Test 5: B with package inductors exceeded the 600 s limit at the 20 ps maximum step, even run alone.
    # On A-pkg50pH a 100 ps maximum step changed every metric by at most 1.4% (damping ratio; the others
    # under 0.1%) at a quarter of the run time. The package and combined cases on B use it; the check is
    # repeated in the report on B without package (B-m1-mid-ms100) and on A with it (A-pkg50pH-ms100).
    cases["B-m1-mid-ms100"] = {"ext": b, "maxstep": MAXSTEP_PKG, "base": b}
    for lp in L_PKG_CASES:
        cases[f"B-pkg{lp * 1e12:.0f}pH"] = {"ext": b, "l_pkg": lp, "maxstep": MAXSTEP_PKG, "base": b}
    cases["B-rskin"] = {"ext": b, "r_scale": R_SKIN, "base": b}
    cases["B-drvmax"] = {"ext": b, "r_src": R_SRC_MAX, "r_snk": R_SNK_MAX, "base": b}
    for esr in (0.3, 1.0):
        cases[f"B-esr{esr:g}"] = {"ext": b, "esr": esr, "base": b}
    cases["B-combined"] = {"ext": b, "l_pkg": 50e-12, "r_scale": R_SKIN, "r_src": R_SRC_MAX, "r_snk": R_SNK_MAX,
                           "maxstep": MAXSTEP_PKG, "base": b}
    cases[a] = {"ext": a}
    cases["A-pkg50pH"] = {"ext": a, "l_pkg": 50e-12, "base": a}
    cases["A-pkg50pH-r20GHz"] = {"ext": a, "l_pkg": 50e-12, "r_pkg_corner": 20e9, "base": "A-pkg50pH"}
    cases["A-pkg50pH-ms100"] = {"ext": a, "l_pkg": 50e-12, "maxstep": MAXSTEP_PKG, "base": "A-pkg50pH"}
    # Added after test 5 run 4 (declared here before their runs). B-esr1 exceeded 600 s at 20 ps; it reruns at
    # the checked 100 ps step. B-cgd tests the gate-charge candidate without modifying the model: an external
    # linear gate-drain capacitance on each FET restoring the Miller-charge deficit of EPC2302 Fig. 7
    # (datasheet plateau 2.87 nC wide, model 2.19 nC, at VDS 50 V: 0.68 nC / 50 V = 13.6 pF). The real
    # deficit is voltage dependent, so this is a sensitivity, not a correction.
    cases["B-esr1-ms100"] = {"ext": b, "esr": 1.0, "maxstep": MAXSTEP_PKG, "base": "B-m1-mid-ms100"}
    cases["B-cgd"] = {"ext": b, "c_gd": C_GD_DEFICIT, "maxstep": MAXSTEP_PKG, "base": "B-m1-mid-ms100"}
    missing = {c["ext"] for c in cases.values()} - set(exts)
    if missing:
        raise SystemExit(f"cause study needs extractions {sorted(missing)}")
    return cases


def main():
    global REFERENCE
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-switching-sensitivity.json")
    ap.add_argument("--cases", nargs="*", default=None, help="extraction names (e.g. A-m1-mid); default: all found")
    ap.add_argument("--no-extra", action="store_true", help="skip ideal, capacitor, numerical and periodic cases")
    ap.add_argument("--reference", default=REFERENCE, help="reference extraction for differences and extra cases")
    ap.add_argument("--study", choices=("sensitivity", "causes", "periodic"), default="sensitivity",
                    help="sensitivity: extraction variants (tests 1-4); causes: candidate causes of the Fig. 9 gap (test 5); periodic: 3-period buck check on A")
    ap.add_argument("--jobs", type=int, default=1, help="cases run in parallel")
    ap.add_argument("--only", nargs="*", default=None, help="causes study: run only these case names")
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
    if args.study == "periodic":
        cases = {NUMERICAL_REF: {"ext": NUMERICAL_REF}, f"{NUMERICAL_REF}-periodic3": {"ext": NUMERICAL_REF, "periods": 3}}
    elif args.study == "causes":
        cases = cause_cases(exts)
        if args.only:
            cases = {k: c for k, c in cases.items() if k in args.only}
    else:
        cases = {k: {"ext": k} for k in exts}
    if args.study == "sensitivity" and not args.no_extra and REFERENCE in exts:
        cases["ideal-copper"] = {"ext": REFERENCE, "ideal": True}
        cases[f"{REFERENCE}-esl0.5x"] = {"ext": REFERENCE, "esl_scale": 0.5}  # esl 0 (1 fF) stalled the solver
        cases[f"{REFERENCE}-esl2x"] = {"ext": REFERENCE, "esl_scale": 2.0}
        cases[f"{REFERENCE}-csw"] = {"ext": REFERENCE, "c_sw": True}
        # On B the fine run exceeded the adapter's 600 s limit (sweep 1); the numerical check runs on A.
        if NUMERICAL_REF in exts:
            cases[f"{NUMERICAL_REF}-fine"] = {"ext": NUMERICAL_REF, "maxstep": MAXSTEP / 2, "reltol": RELTOL / 10}
            # Test 3: on B the package cases and the periodic case exceeded the adapter's 600 s limit, so they
            # run on the smaller A network: the package cases as a screen, the periodic case as the check that
            # the double pulse reproduces continuous-operation edges (it depends on the timing, not the network).
            for lp in L_PKG_CASES:
                cases[f"{NUMERICAL_REF}-pkg{lp * 1e12:.0f}pH"] = {"ext": NUMERICAL_REF, "l_pkg": lp}
            cases[f"{NUMERICAL_REF}-periodic3"] = {"ext": NUMERICAL_REF, "periods": 3}
    results, slopes = {}, {}

    def run_case(name, c):
        ext = exts[c["ext"]]
        kw = dict(esl_scale=c.get("esl_scale", 1.0), ideal=c.get("ideal", False),
                  maxstep=c.get("maxstep", MAXSTEP), reltol=c.get("reltol", RELTOL),
                  l_pkg=c.get("l_pkg", 0.0), c_sw=c.get("c_sw", False),
                  r_pkg_corner=c.get("r_pkg_corner", R_PKG_CORNER_HZ), r_scale=c.get("r_scale", 1.0),
                  esr=c.get("esr"), r_src=c.get("r_src", R_SRC), r_snk=c.get("r_snk", R_SNK), c_gd=c.get("c_gd", 0.0))
        first = None
        if c.get("periods"):
            # Loss-corrected duty cycle and first-pulse length from the double pulse's measured slopes.
            s_on, s_off = slopes[c["ext"]]
            duty = s_off / (s_on + s_off)
            timing = {"duty": duty, "t1": I_PEAK / s_on}
            text, times, at = bench(ext, te_rise, te_fall, periods=c["periods"], timing=timing, **kw)
            # Test 5 run 1 (duty from the double pulse's average slopes) drifted by about -0.3 A per period
            # (valleys 11.27, 10.95, 10.66 A): the edges and dead times lose volt-seconds that the average
            # slopes miss. One correction from the measured drift, then the measured run.
            raw0 = run(name + "-duty", text)
            if raw0:
                s0 = raw0.step(0)
                v0 = [interp(s0["time"], s0["i(l1)"], t) for t in times["period_starts_s"]]
                drift = (v0[-1] - v0[0]) / (len(v0) - 1)
                timing = {**timing, "duty": duty - drift / ((s_on + s_off) / F_SW),
                          "duty_run_valleys_A": v0, "duty_run_drift_A_per_period": drift}
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
                return
            ia = m0["event_a_turn_off_at_peak"]["inductor_current_A"]
            ib = m0["event_b_turn_on_at_valley"]["inductor_current_A"]
            s_on, s_off = ia / (times["t_off1"] - 20e-9), (ia - ib) / (times["t_on2"] - times["t_off1"])
            slopes[name] = (s_on, s_off)
            timing = {"t1": I_PEAK / s_on, "t_off": (I_PEAK - I_VALLEY) / s_off}
            first = {"edge_currents_A": [ia, ib], "slopes_A_per_s": [s_on, s_off], "corrected_timing_s": timing}
            text, times, at = bench(ext, te_rise, te_fall, timing=timing, **kw)
        raw = run(name, text)
        s = raw.step(0) if raw else None
        m = metrics(s, times, at) if raw else None
        if m and c.get("periods"):
            valleys = [interp(s["time"], s["i(l1)"], t) for t in times["period_starts_s"]]
            m["periodicity"] = {"inductor_current_at_period_starts_A": valleys, "timing": timing,
                                "valley_spread_rel": (max(valleys) - min(valleys)) / (sum(valleys) / len(valleys)),
                                "check": "valley currents of successive periods within 2%"}
        ok = None
        spk = spikes(s) if s else None
        if m:
            ia, ib = m["event_a_turn_off_at_peak"]["inductor_current_A"], m["event_b_turn_on_at_valley"]["inductor_current_A"]
            ok = {"edge_current_A_within_2pct": abs(ia / I_PEAK - 1) <= 0.02, "edge_current_B_within_5pct": abs(ib / I_VALLEY - 1) <= 0.05,
                  "no_spikes": spk["count"] == 0}
            if c.get("periods"):
                ok["periodic_within_2pct"] = m["periodicity"]["valley_spread_rel"] <= 0.02
        results[name] = {"parameters": {k: v for k, v in c.items()}, "extraction_case": ext["case"], "timing_run": first,
                         "extraction_summary": ext.get("summary"), "times_s": times, "bus_attachment": at,
                         "metrics": m, "checks": ok, "spikes": spk,
                         "usable": bool(ok and all(ok.values())),
                         "traces": edge_traces(s, times) if m else None}
        if m:
            f = flat(m)
            print(f"{name:22s} Ia {m['event_a_turn_off_at_peak']['inductor_current_A']:.2f} "
                  f"tf {f['sw_fall_time_90_10_s'] * 1e9 if f['sw_fall_time_90_10_s'] else float('nan'):.3f} ns | "
                  f"Ib {m['event_b_turn_on_at_valley']['inductor_current_A']:.2f} tr {f['sw_rise_time_10_90_s'] * 1e9 if f['sw_rise_time_10_90_s'] else float('nan'):.3f} ns "
                  f"peak {f['sw_peak_V']:.2f} V over {f['sw_overshoot_above_bus_V']:.2f} V "
                  f"f {(f['ringing_frequency_Hz'] or float('nan')) / 1e6:.1f} MHz zeta {f['ringing_damping_ratio'] or float('nan'):.3f} "
                  f"Q1 Vds pk {f['q1_vds_peak_V']:.2f} V spikes {spk['count']}", flush=True)
        else:
            print(name, "failed:", runs[name]["message"], flush=True)

    def guarded(name, c):
        try:
            run_case(name, c)
        except Exception as exc:  # record the failure; the other cases continue
            results[name] = {"parameters": c, "metrics": None, "checks": None, "error": repr(exc)}
            print(name, "error:", repr(exc), flush=True)

    # Cases are independent except that a periodic case needs its extraction's slopes: run it afterwards.
    plain = {k: c for k, c in cases.items() if not c.get("periods")}
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        list(pool.map(lambda kv: guarded(*kv), plain.items()))
    for name, c in cases.items():
        if c.get("periods"):
            guarded(name, c)
    results = {k: results[k] for k in cases if k in results}
    # Extraction variants are compared with the reference B; a modified case (ideal copper, ESL, package,
    # switch-node capacitance, fine, periodic) is compared with the unmodified case of its own extraction.
    comparison = {}
    for name, r in results.items():
        base = r["parameters"].get("base") or (REFERENCE if (name in exts or name == "ideal-copper") else r["parameters"]["ext"])
        if name != base and r["metrics"] and base in results and results[base]["metrics"]:
            comparison[name] = {"compared_with": base, **material(flat(results[base]["metrics"]), flat(r["metrics"]))}
    numerical = None
    fine = results.get(f"{NUMERICAL_REF}-fine")
    if fine and fine["metrics"] and NUMERICAL_REF in results and results[NUMERICAL_REF]["metrics"]:
        a, b_ = flat(results[NUMERICAL_REF]["metrics"]), flat(fine["metrics"])
        keys = list(MATERIAL) + ["sw_peak_V", "q1_vds_peak_V", "q1_peak_drain_current_A"]
        rel = {k: (b_[k] - a[k]) / abs(a[k]) for k in keys if a.get(k) and b_.get(k) is not None}
        numerical = {"relative_change": rel, "pass": all(abs(v) <= 0.02 for v in rel.values()) and len(rel) == len(keys)}
    report = {
        "schema": "epc90133-switching-sensitivity/1",
        "study": args.study,
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
