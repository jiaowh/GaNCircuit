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

Test 6, separated gate and source paths (--study paths; specification of 30 September 2026, after an
external review, before the first run). The bench so far returns both drivers at the FET source pads and
has no gate-loop inductance, and test 5's package cases put the same inductance on drain and source
together, so they cannot say which path matters. Each case below adds one inductance, per FET, to the
reference B at the 100 ps step (compared with B-m1-mid-ms100); values are an assumed bracket, not
extracted, and every inductor carries the 10 GHz damping resistor:
* drain only, 50 pH (power loop only);
* source only, 25 and 50 pH, driver returning at the source pad: common-source inductance;
* source only, 50 pH, driver returning at the die side of it (Kelvin): the same power-loop inductance
  without the common-source coupling. Csi50 against Kelvin50 isolates the common-source effect;
* gate only, 0.5 and 2 nH (board and package gate loop lumped in series with the gate).
Direct numerical checks on a B package case (test 5 checked only related configurations): B-pkg50pH at
100 ps against the same case at 50 ps and against the 20 GHz damping-resistor corner.
The periodic study now takes --periodic-ext and --periodic-maxstep, so the continuous-operation check can
run on B (at the 100 ps step, compared with the double pulse at the same step).
Added before the rerun of test 6 (its first run was interrupted with the session, and its report was lost
because reports were written only at the end; they are now saved after every case). In the first run the
0.5 nH gate case stalled (time step 1e-19 s; Gear integration stalled too) at Q1's second turn-off, 150 ns
after the valley turn-on. No metric uses that edge: the event B window ends 60 ns and the saved trace 70 ns
after the turn-on. Every test 6 case therefore ends its transient 80 ns after the valley turn-on (edges
later than that are dropped). The stall itself is recorded as a caveat for the gate-inductance cases, which
also get a direct 50 ps step check.
Result status: a comparison is formed only between two cases whose checks all pass; otherwise it is
recorded as excluded.

Second external review (30 September 2026), before test 7's first run:
* device metrics now use die terminals: with package or gate-loop inductors the pad nodes are not the
  die's. Each bench records its die nodes; Q1's gate-source voltage (switching-energy windows), Vds for the
  energies and Q2's gate peak are die quantities; Q2's pad-level gate peak is kept under its own name. The
  energies exclude energy stored in the package inductors. Switch-node metrics are unchanged (pads);
* the leading common-source case gets its own numerical checks: B-Ls50-csi at 50 ps, and with the
  damping-resistor corner at 20 GHz and at 5 GHz (20 GHz exceeded 600 s on the package case);
* reports are written to a temporary file and atomically replaced, and the input manifest is taken once,
  when the inputs are loaded.

Test 7, extracted gate-drive loops (--study gateloop; specification of 30 September 2026, before the first
run). The network is extraction G (scripts/epc90133_extract.py): B's copper plus the gate nets, the driver
balls, the gate-resistor pads and each FET's source split into pin 2 and pins 4+6. In the bench:
* each die source joins its pins 2 and 4+6 through 0 V sources (the package interior is ideal; their
  currents give the pin split); the gate pin is the die gate; Q2's pins 4+6 are the circuit ground;
* the upper driver stage is referenced to the PHASE balls (U80.PH), the lower to the GND ball (U80.GND);
  pull-up outputs drive the UGH/LGH balls and pull-down outputs the UGL/LGL balls; R80/R82 (1 ohm) and
  R81/R83 (0 ohm, 1 mohm here) sit between their pad terminals. Driver supplies stay ideal at the balls
  (the C80/C81 loops are not extracted). Everything else as test 6's reference (100 ps step, 80 ns end);
* cases: G-m1-mid, compared with B-m1-mid-ms100 (B also has no gate or source paths, so the difference is
  what the board's gate-drive copper adds); G-m1-mid-ms50, the direct step check; and G with the assumed
  package common-source inductance of test 6 (25 and 50 pH on each die source, drivers at the pins), to see
  what package inductance would still be needed on top of the board's;
* added after an external audit, before the first run: every test 7 case (B included) has a 0 V source in
  Q2's drain, and reports both die VGS extrema and both drain currents around each event, with traces
  (gate_and_current_diagnostics; reported, not judged), and on G the driver's PHASE-to-GND ball voltage
  extremes against its -5/+85 V absolute maximum (uP1966E datasheet p. 7);
* matched control G-m1-mid-ctl, declared before G's first result and run only on request (--only), when the
  G-B difference is material: G's network with B's gate drive (ideal stages at the gate pads returning at
  the source junction, the driver-ball and gate-resistor copper left open). G-ctl against B isolates the
  extraction window, local mesh and source-terminal representation; G against G-ctl isolates what the
  board's gate-drive and shared source paths add. Its PHASE-ball values are not meaningful (open copper);
* split controls, declared on 1 October 2026 after G-ctl showed that the gate-drive copper accounts for about
  two thirds of the G-B overshoot change together with a Q2 gate peak of 2.0 V (1.07 V in G-ctl), before
  their runs: G-m1-mid-ctl-hs (high-side stage ideal, low-side through the extracted copper) and
  G-m1-mid-ctl-ls (the reverse), both against G. They separate the high-side gate loop (Q1's turn-on) from
  the low-side loop (Q2's gate disturbance and possible conduction). The two parts need not add up exactly;
  their sum against G-ctl is reported, not assumed. G differs from B in extraction window, local mesh
  and source-terminal representation as well as in the gate paths, so a material G-B difference is not
  attributed to common-source inductance without a matched control. Every report carries an input manifest (extraction files, vendor library and
imported modules by sha256).
"""
import argparse
import glob
import hashlib
import json
import math
import os
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
    # Q2.S (power-loop variants) or Q2.S46 (variant G) is the circuit ground; the gate pins are gu/gl.
    return {"Q2.S": "0", "Q2.S46": "0", "Q1.G": "gu", "Q2.G": "gl"}.get(t, t.replace(".", "_").lower())


def is_gate_extraction(ext):
    return any(p["terminal"] == "U80.PH" for p in ext["ports"])


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


def fet(n, gate, dpad, spad, l_d, l_s, l_g, r_corner):
    """One EPC2302 with optional drain, source and gate inductance; returns lines and the die source node."""
    dd, ss, gg = (f"p{n}d" if l_d else dpad), (f"p{n}s" if l_s else spad), (f"p{n}g" if l_g else gate)
    lines = []
    for tag, a, b, lv in (("d", dpad, dd, l_d), ("s", ss, spad, l_s), ("g", gate, gg, l_g)):
        if lv:
            lines += [f"Lp{n}{tag} {a} {b} {lv:g}", f"Rp{n}{tag} {a} {b} {2 * math.pi * r_corner * lv:.6g}"]
    lines.append(f"X{n} {gg} {dd} {ss} EPC2302")
    return lines, ss


# Board elements of each driver stage (test 7 split controls).
STAGE_OF = {"R80": "u", "R81": "u", "U80.UGH": "u", "U80.UGL": "u", "U80.PH": "u",
            "R82": "l", "R83": "l", "U80.LGH": "l", "U80.LGL": "l", "U80.GND": "l"}


def gate_drive(hi, lo, te_rise, te_fall, r_src, r_snk, t_end, stages=("u", "l")):
    """Test 7: uP1966E stages at the extracted ball terminals, gate resistors between their pad terminals.

    drive_stage ties its pull-up and pull-down resistors to one gate node; here the pull-down resistor is
    moved to the turn-off ball, and the board resistors R80-R83 are separate elements.
    """
    out = []
    for tag, ref, vdd, edges, up, dn in (("u", "u80_ph", VBOOT, hi, "u80_ugh", "u80_ugl"),
                                          ("l", "u80_gnd", VCC, lo, "u80_lgh", "u80_lgl")):
        if tag not in stages:
            continue
        text = drive_stage(tag, ref, vdd, edges, te_rise, te_fall, up, r_src, r_snk, 0.0, 0.0, t_end).rstrip()
        old = f"R{tag}d {up} pd{tag}"
        if text.count(old) != 1:
            raise RuntimeError("drive_stage output changed; cannot split its outputs")
        out.append(text.replace(old, f"R{tag}d {dn} pd{tag}"))
    for ref, ohm in (("R80", R_GON), ("R81", R_GOFF), ("R82", R_GON), ("R83", R_GOFF)):
        if STAGE_OF[ref] not in stages:
            continue
        out.append(f"{ref} {ref.lower()}_d {ref.lower()}_g {max(ohm, 1e-3):g}")
    return out


def ideal_stage(tag, hi, lo, te_rise, te_fall, r_src, r_snk, t_end):
    """B's ideal stage for one FET of the G network, at its gate pad, returning at its source junction."""
    if tag == "u":
        return drive_stage("u", "q1_s", VBOOT, hi, te_rise, te_fall, "gu", r_src, r_snk, R_GON, R_GOFF, t_end).rstrip()
    return drive_stage("l", "q2_s", VCC, lo, te_rise, te_fall, "gl", r_src, r_snk, R_GON, R_GOFF, t_end).rstrip()


def bench(ext, te_rise, te_fall, esl_scale=1.0, ideal=False, maxstep=MAXSTEP, reltol=RELTOL, periods=None, timing=None,
          l_pkg=0.0, c_sw=False, r_pkg_corner=R_PKG_CORNER_HZ, r_scale=1.0, esr=None, r_src=R_SRC, r_snk=R_SNK,
          c_gd=0.0, l_d=None, l_s=None, l_g=0.0, kelvin=False, t_after_b=None, sense_q2=False, gate_ctl=False):
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
        if t_after_b is not None:  # test 6: stop after the measured window; drop later edges
            t_end = t_on2 + t_after_b
            hi = [e for e in hi if e[0] <= t_end - 20e-9]
            lo = [e for e in lo if e[0] <= t_end - 20e-9]
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
    # l_pkg (tests 4-5) is the same inductance on drain and source; l_d / l_s / l_g (test 6) set them apart.
    ld = l_pkg if l_d is None else l_d
    ls = l_pkg if l_s is None else l_s
    g_ext = is_gate_extraction(ext)
    # Test 7 (audit, 30 September 2026): a 0 V source in Q2's drain gives its terminal current.
    q2dd = "q2dd" if sense_q2 else "q2_d"
    die = {"g1": "gu", "d1": "q1dd", "s1": "q1_s", "g2": "gl", "d2": q2dd, "s2": "0"}
    if g_ext:
        # Test 7: die source q1_s / q2_s joins the split pins; optional package source inductance l_s.
        if ld or l_g or c_gd or c_sw:
            raise ValueError("variant G bench supports only l_s (package common-source) among the options")
        fet1, fet2 = [], []
        for n_, pins, gate_node, d_node in ((1, ("q1_s2", "q1_s46"), "gu", "q1dd"), (2, ("q2_s2", "0"), "gl", q2dd)):
            junction = f"q{n_}_s"
            src = f"p{n_}s" if ls else junction
            lst = fet1 if n_ == 1 else fet2
            if ls:
                lst += [f"Lp{n_}s {src} {junction} {ls:g}", f"Rp{n_}s {src} {junction} {2 * math.pi * r_pkg_corner * ls:.6g}"]
            lst += [f"Vs{n_}2 {junction} {pins[0]} 0", f"Vs{n_}46 {junction} {pins[1]} 0",
                    f"X{n_} {gate_node} {d_node} {src} EPC2302"]
        s1_die, s2_die = "q1_s", "q2_s"
        die.update(s1="p1s" if ls else "q1_s", s2="p2s" if ls else "q2_s")
        if gate_ctl:
            # Matched control: G's network, B's gate drive (ideal stages at the gate pads, returning at the
            # source junction, as B returns at its single source terminal). The driver-ball and gate-resistor
            # copper is left open; 1 Gohm bleeders keep those nodes defined.
            if ls:
                raise ValueError("the gate control case takes no package inductance")
            # gate_ctl True: both stages ideal; "u" or "l": only that stage (split control, test 7 follow-up).
            ideal_st = ("u", "l") if gate_ctl is True else (gate_ctl,)
            owner = lambda t: STAGE_OF.get(t, STAGE_OF.get(t.split(".")[0]))
            gate_nodes = sorted({node(t) for p_ in ext["ports"] for t in (p_["terminal"], p_["reference"])
                                 if owner(t) in ideal_st})
            fet2 += [f"Rbleed_{nd} {nd} 0 1e9" for nd in gate_nodes]
            s2_die = "q2_s"
    else:
        fet1, s1_die = fet(1, "gu", "q1dd", "q1_s", ld, ls, l_g, r_pkg_corner)
        fet2, s2_die = fet(2, "gl", q2dd, "0", ld, ls, l_g, r_pkg_corner)
        die.update(g1="p1g" if l_g else "gu", d1="p1d" if ld else "q1dd", s1=s1_die,
                   g2="p2g" if l_g else "gl", d2="p2d" if ld else q2dd, s2=s2_die)
    times["die_nodes"] = die
    lines += [
        "Vq1d q1_d q1dd 0",
        *(["Vq2d q2_d q2dd 0"] if sense_q2 else []),
        *fet1, *fet2,
        *([f"Csw_gnd q2_d 0 {C_SW['GND']:g}", f"Csw_vin q2_d q1_d {C_SW['VIN']:g}"] if c_sw else []),
        *([f"Cgdx1 gu q1dd {c_gd:g}", f"Cgdx2 gl q2_d {c_gd:g}"] if c_gd else []),
        f"L1 q2_d out {L_OUT:g}{l_ic}",
        f"Vout out 0 {VOUT:g}",
        *(gate_drive(hi, lo, te_rise, te_fall, r_src, r_snk, t_end) if g_ext and not gate_ctl else
          gate_drive(hi, lo, te_rise, te_fall, r_src, r_snk, t_end, stages=[x for x in ("u", "l") if x != gate_ctl])
          + [ideal_stage(gate_ctl, hi, lo, te_rise, te_fall, r_src, r_snk, t_end)]
          if g_ext and gate_ctl in ("u", "l") else [
            # Drivers return at the source pads (common-source coupling through l_s) or, with kelvin, at the die source.
            drive_stage("u", s1_die if kelvin else "q1_s", VBOOT, hi, te_rise, te_fall, "gu", r_src, r_snk, R_GON, R_GOFF,
                        t_end).rstrip(),
            drive_stage("l", s2_die if (kelvin or gate_ctl) else "0", VCC, lo, te_rise, te_fall, "gl", r_src, r_snk, R_GON, R_GOFF,
                        t_end).rstrip()]),
        SWITCH_MODELS.rstrip(),
        ".save V(q2_d) V(q1_d) V(q1_s) V(gu) V(gl) I(Vq1d) I(L1)" + (" I(Vq2d)" if sense_q2 else "") + (f" V({node(at + '.VIN')}) V({node(at + '.GND')})")
        + (" V(q2_s) V(u80_ph) V(u80_gnd) I(Vs12) I(Vs146) I(Vs22) I(Vs246)" if g_ext else "")
        + "".join(f" V({v})" for v in sorted(set(die.values()) - {"0", "gu", "gl", "q1_s", "q2_d", "q2_s", "q2dd", "q1dd"})),
        ".temp 25",
        f".options plotwinsize=0 reltol={reltol:g}",
        f".tran 0 {t_end:.9g} 0 {maxstep:g}",
        ".end", ""]
    head = (f"* EPC90133 switching sensitivity, extraction {ext['case']}{' (ideal copper)' if ideal else ''}; "
            "generated by scripts/epc90133_switching.py\n.lib EPCGaNLibrary.lib\n")
    return head + "\n".join(lines), times, at


def metrics(s, times, at):
    t = s["time"]
    die = times.get("die_nodes") or {"g1": "gu", "d1": "q1_d", "s1": "q1_s", "g2": "gl", "s2": "0"}
    zero = [0.0] * len(t)
    v = lambda nd: zero if nd == "0" else s[f"v({nd})"]
    sw, gl = s["v(q2_d)"], s["v(gl)"]
    # Second review: device quantities at the die terminals (q1dd is not saved; Vq1d is a 0 V source, so
    # the die drain equals q1_d unless a drain inductor is present).
    d1 = v("q1_d" if die["d1"] == "q1dd" else die["d1"])
    s1, g1 = v(die["s1"]), v(die["g1"])
    vds1 = [a - b for a, b in zip(d1, s1)]
    vgs1 = [a - b for a, b in zip(g1, s1)]
    vgs2 = [a - b for a, b in zip(v(die["g2"]), v(die["s2"]))]
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
               "q2_gate_peak_during_rise_V": max(x for _, x in window(t, vgs2, tb, tb + 60e-9)),
               "q2_gate_pad_peak_during_rise_V": max(x for _, x in window(t, gl, tb, tb + 60e-9))}
    return {"event_a_turn_off_at_peak": event_a, "event_b_turn_on_at_valley": event_b,
            "gate_and_current_diagnostics": diagnostics(s, t, vgs1, vgs2, id1, ta, tb),
            "terminals": {"device_metrics": "die (q1 vgs and vds for the energies, q2 gate-source peak)",
                          "switch_node_metrics": "Q2 drain pad to circuit ground (Q2 source pad)",
                          "die_nodes": die, "energies_exclude": "energy stored in package or gate-loop inductors"},
            "not_validated": "q1_eoff_J, q1_eon_J and the edge times depend on gate charge (EPC2302 Fig. 7 exception)"}


def diagnostics(s, t, vgs1, vgs2, id1, ta, tb):
    """Test 7 (audit, 30 September 2026): die gate-source extremes of both FETs and both drain currents
    around each event, so gate disturbance and possible false turn-on are read before any conclusion.

    Terminal currents include capacitive (Coss, Cgd) charging current, so a positive Q2 drain current
    during the rising edge does not by itself show channel conduction; it is read together with Q2's VGS.
    Reported, not judged: no pass/fail threshold was declared before the first run."""
    id2 = s.get("i(vq2d)")
    out = {"window_s": [-5e-9, 60e-9], "vgs_ratings_V": {"max": 6.0, "min": -4.0, "source": "EPC2302 datasheet"},
           "q2_drain_current": "I(Vq2d), drain terminal into Q2" if id2 else "not saved (no Q2 sense source)"}
    for tag, te in (("event_a", ta), ("event_b", tb)):
        w = lambda y: [x for _, x in window(t, y, te - 5e-9, te + 60e-9)]
        d = {"q1_vgs_max_V": max(w(vgs1)), "q1_vgs_min_V": min(w(vgs1)),
             "q2_vgs_max_V": max(w(vgs2)), "q2_vgs_min_V": min(w(vgs2)),
             "q1_id_max_A": max(w(id1)), "q1_id_min_A": min(w(id1))}
        if id2:
            d.update(q2_id_max_A=max(w(id2)), q2_id_min_A=min(w(id2)))
        if "v(u80_ph)" in s:
            # Variant G only: the driver's PHASE ball against its GND ball (uP1966E absolute maximum
            # -5 V to +85 V, datasheet p. 7). A simulated sensitivity result, not a safe limit.
            ph = [a - b for a, b in zip(s["v(u80_ph)"], s["v(u80_gnd)"])]
            d.update(driver_phase_to_gnd_max_V=max(w(ph)), driver_phase_to_gnd_min_V=min(w(ph)))
        out[tag] = d
    return out


def spikes(s):
    """Single-sample V(SW) spikes (the test 4 artefact): count, and the smallest time step."""
    t, v = np.array(s["time"]), np.array(s["v(q2_d)"])
    d = v[1:-1] - 0.5 * (v[:-2] + v[2:])
    return {"count": int(np.sum(np.abs(d) > SPIKE_V)), "threshold_V": SPIKE_V, "min_step_s": float(np.min(np.diff(t)))}


def edge_traces(s, times):
    """V(SW) (Q2 drain pad to Q2 source pad, ideal probe) resampled around both events; with a Q2 sense
    source (test 7) also both die VGS and both drain currents."""
    t, v = np.array(s["time"]), np.array(s["v(q2_d)"])
    rel = np.arange(TRACE_WINDOW[0], TRACE_WINDOW[1] + TRACE_STEP / 2, TRACE_STEP)
    out = {"step_s": TRACE_STEP, "start_s": TRACE_WINDOW[0],
           "event_times_s": {"falling": times["t_off1"], "rising": times["t_on2"]},
           "falling_V": [round(float(x), 4) for x in np.interp(times["t_off1"] + rel, t, v)],
           "rising_V": [round(float(x), 4) for x in np.interp(times["t_on2"] + rel, t, v)]}
    if "i(vq2d)" in s:
        die = times["die_nodes"]
        zero = np.zeros(len(t))
        nv = lambda nd: zero if nd == "0" else np.array(s[f"v({'q1_d' if nd == 'q1dd' else nd})"])
        sig = {"q1_vgs_V": nv(die["g1"]) - nv(die["s1"]), "q2_vgs_V": nv(die["g2"]) - nv(die["s2"]),
               "q1_id_A": np.array(s["i(vq1d)"]), "q2_id_A": np.array(s["i(vq2d)"])}
        out["device"] = {f"{ev}_{k}": [round(float(x), 5) for x in np.interp(times[tk] + rel, t, y)]
                         for ev, tk in (("falling", "t_off1"), ("rising", "t_on2")) for k, y in sig.items()}
    return out


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


L_PATH_CASES = {"B-Ld50": {"l_d": 50e-12, "l_s": 0.0},
                "B-Ls25-csi": {"l_d": 0.0, "l_s": 25e-12},
                "B-Ls50-csi": {"l_d": 0.0, "l_s": 50e-12},
                "B-Ls50-kelvin": {"l_d": 0.0, "l_s": 50e-12, "kelvin": True},
                "B-Lg0.5n": {"l_g": 0.5e-9},
                "B-Lg2n": {"l_g": 2e-9}}


T_AFTER_B = 80e-9


def path_cases(exts):
    """Test 6 cases (see the module docstring)."""
    b, ref = "B-m1-mid", "B-m1-mid-ms100"
    common = {"ext": b, "maxstep": MAXSTEP_PKG, "t_after_b": T_AFTER_B}
    cases = {ref: dict(common)}
    for name, kw in L_PATH_CASES.items():
        cases[name] = {**common, "base": ref, **kw}
    cases["B-Lg0.5n-ms50"] = {**common, **L_PATH_CASES["B-Lg0.5n"], "maxstep": MAXSTEP_PKG / 2, "base": "B-Lg0.5n"}
    cases["B-pkg50pH"] = {**common, "l_pkg": 50e-12, "base": ref}
    cases["B-pkg50pH-ms50"] = {**common, "l_pkg": 50e-12, "maxstep": MAXSTEP_PKG / 2, "base": "B-pkg50pH"}
    cases["B-pkg50pH-r20GHz"] = {**common, "l_pkg": 50e-12, "r_pkg_corner": 20e9, "base": "B-pkg50pH"}
    # Second review: direct checks of the leading common-source case.
    csi = {**common, **L_PATH_CASES["B-Ls50-csi"], "base": "B-Ls50-csi"}
    cases["B-Ls50-csi-ms50"] = {**csi, "maxstep": MAXSTEP_PKG / 2}
    cases["B-Ls50-csi-r20GHz"] = {**csi, "r_pkg_corner": 20e9}
    cases["B-Ls50-csi-r5GHz"] = {**csi, "r_pkg_corner": 5e9}
    if b not in exts:
        raise SystemExit(f"path study needs extraction {b}")
    return cases


def comparisons(results, exts, reference):
    """Materiality of each case against its base; formed only when both passed every check (test 6)."""
    out = {}
    for name, r in results.items():
        base = r["parameters"].get("base") or (reference if (name in exts or name == "ideal-copper") else r["parameters"]["ext"])
        if name == base or base not in results:
            continue
        if r.get("usable") is True and results[base].get("usable") is True:
            out[name] = {"compared_with": base, **material(flat(results[base]["metrics"]), flat(r["metrics"]))}
        else:
            out[name] = {"compared_with": base, "excluded": "case or base failed its checks",
                         "case_usable": r.get("usable") is True, "base_usable": results[base].get("usable") is True}
    return out


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def gateloop_cases(exts):
    """Test 7 cases (see the module docstring)."""
    g, ref = "G-m1-mid", "B-m1-mid-ms100"
    if g not in exts or "B-m1-mid" not in exts:
        raise SystemExit("test 7 needs extractions G-m1-mid and B-m1-mid")
    common = {"maxstep": MAXSTEP_PKG, "t_after_b": T_AFTER_B, "sense_q2": True}
    return {ref: {"ext": "B-m1-mid", **common},
            g: {"ext": g, "base": ref, **common},
            f"{g}-ms50": {"ext": g, "base": g, **common, "maxstep": MAXSTEP_PKG / 2},
            f"{g}-Ls25": {"ext": g, "base": g, **common, "l_s": 25e-12},
            f"{g}-Ls50": {"ext": g, "base": g, **common, "l_s": 50e-12},
            # Matched control (declared before G's first result; run with --only when G-B is material).
            f"{g}-ctl": {"ext": g, "base": ref, **common, "gate_ctl": True, "on_request": True},
            # Split controls (declared 1 October 2026 after G-ctl, before their runs): one stage ideal.
            f"{g}-ctl-hs": {"ext": g, "base": g, **common, "gate_ctl": "u", "on_request": True},
            f"{g}-ctl-ls": {"ext": g, "base": g, **common, "gate_ctl": "l", "on_request": True}}


def main():
    global REFERENCE
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-switching-sensitivity.json")
    ap.add_argument("--cases", nargs="*", default=None, help="extraction names (e.g. A-m1-mid); default: all found")
    ap.add_argument("--no-extra", action="store_true", help="skip ideal, capacitor, numerical and periodic cases")
    ap.add_argument("--reference", default=REFERENCE, help="reference extraction for differences and extra cases")
    ap.add_argument("--periodic-ext", default=NUMERICAL_REF, help="periodic study: extraction (default A-m1-mid)")
    ap.add_argument("--periodic-maxstep", type=float, default=MAXSTEP, help="periodic study: maximum step (s)")
    ap.add_argument("--study", choices=("sensitivity", "causes", "periodic", "paths", "gateloop"), default="sensitivity",
                    help="sensitivity: extraction variants (tests 1-4); causes: candidate causes of the Fig. 9 gap (test 5); periodic: 3-period buck check on A")
    ap.add_argument("--jobs", type=int, default=1, help="cases run in parallel")
    ap.add_argument("--timeout", type=float, default=600.0,
                    help="s per LTspice run (default 600, the limit of all runs before test 7; G needs more)")
    ap.add_argument("--only", nargs="*", default=None, help="causes study: run only these case names")
    args = ap.parse_args()
    REFERENCE = args.reference
    lib, _ = bl.library_path()
    bl.verify_target_sources(lib)
    run_root = ROOT / "runs" / ("epc90133-switching-" + uuid.uuid4().hex[:12])
    runs = {}

    def run(name, text):  # limit per LTspice run: --timeout (the adapter allows up to MAX_TIMEOUT_S)
        r = run_ltspice(text, run_root / name, libraries=[lib], timeout_s=args.timeout)
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
    ext_files = {Path(f).stem: Path(f) for f in files}
    exts = {Path(f).stem: json.loads(Path(f).read_text(encoding="utf-8")) for f in files}
    exts = {k: v for k, v in exts.items() if v.get("outcome") == "complete" and (args.cases is None or k in args.cases)}
    if args.study == "periodic":
        pe, pm = args.periodic_ext, args.periodic_maxstep
        tag = pe + ("" if pm == MAXSTEP else f"-ms{pm * 1e12:.0f}")
        cases = {tag: {"ext": pe, "maxstep": pm}, f"{tag}-periodic3": {"ext": pe, "periods": 3, "maxstep": pm, "base": tag}}
    elif args.study == "gateloop":
        cases = gateloop_cases(exts)
        if args.only:
            cases = {k: c for k, c in cases.items() if k in args.only}
        else:
            cases = {k: c for k, c in cases.items() if not c.get("on_request")}
    elif args.study == "paths":
        cases = path_cases(exts)
        if args.only:
            cases = {k: c for k, c in cases.items() if k in args.only}
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
    # Second review: identities of the inputs as loaded, not as found at the end of a long run.
    manifest = {
        "taken_at": "start of run, when the inputs were loaded",
        "evaluator_sha256": sha256(Path(__file__)),
        "extractions": {ext_files[e].relative_to(ROOT).as_posix(): sha256(ext_files[e])
                        for e in sorted({c["ext"] for c in cases.values()})},
        "vendor_library": {"file": Path(lib).name, "sha256": sha256(lib)},
        "modules": {m: sha256(ROOT / m) for m in ("scripts/epc9097_switching.py", "scripts/epc2302_baseline.py",
                                                  "src/circuit_tools/ltspice.py")}}
    results, slopes = {}, {}
    import threading
    save_lock = threading.Lock()

    def run_case(name, c):
        ext = exts[c["ext"]]
        kw = dict(esl_scale=c.get("esl_scale", 1.0), ideal=c.get("ideal", False),
                  maxstep=c.get("maxstep", MAXSTEP), reltol=c.get("reltol", RELTOL),
                  l_pkg=c.get("l_pkg", 0.0), c_sw=c.get("c_sw", False),
                  r_pkg_corner=c.get("r_pkg_corner", R_PKG_CORNER_HZ), r_scale=c.get("r_scale", 1.0),
                  esr=c.get("esr"), r_src=c.get("r_src", R_SRC), r_snk=c.get("r_snk", R_SNK), c_gd=c.get("c_gd", 0.0),
                  l_d=c.get("l_d"), l_s=c.get("l_s"), l_g=c.get("l_g", 0.0), kelvin=c.get("kelvin", False),
                  t_after_b=c.get("t_after_b"), sense_q2=c.get("sense_q2", False), gate_ctl=c.get("gate_ctl", False))
        first = None
        if c.get("periods"):
            # Loss-corrected duty cycle and first-pulse length from the double pulse's measured slopes.
            s_on, s_off = slopes[c.get("base", c["ext"])]
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

    def save(final=False):
        """Write the report; called after every case (test 6), so an interrupted run keeps its results."""
        with save_lock:
            done = {k: results[k] for k in cases if k in results}
            # Extraction variants are compared with the reference B; a modified case (ideal copper, ESL, package,
            # switch-node capacitance, fine, periodic) is compared with the unmodified case of its own extraction.
            comparison = comparisons(done, exts, REFERENCE)
            numerical = None
            fine = done.get(f"{NUMERICAL_REF}-fine")
            if fine and fine.get("usable") and NUMERICAL_REF in done and done[NUMERICAL_REF].get("usable"):
                a, b_ = flat(done[NUMERICAL_REF]["metrics"]), flat(fine["metrics"])
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
                "evaluator_sha256": manifest["evaluator_sha256"],
                "input_manifest": manifest,
                "conditions": {"VIN": VIN, "VOUT": VOUT, "IOUT": IOUT, "f_sw_Hz": F_SW, "L_out_H": L_OUT, "duty": DUTY,
                               "ripple_A": RIPPLE, "I_peak_A": I_PEAK, "I_valley_A": I_VALLEY, "dead_time_s": DEAD,
                               "source": "EPC90133 QSG Fig. 9 (continuous buck; measured tf 3.7 ns, tr 1.7 ns)"},
                "fixed_assumptions": {"capacitors": CAP_MODEL, "bus": BUS, "N_cm_lumped": N_CM, "gate_resistors_ohm": [R_GON, R_GOFF],
                                      "driver_supplies_V": [VCC, VBOOT], "temperature_C": 25, "maxstep_s": MAXSTEP, "reltol": RELTOL,
                                      "measurement": "ideal probe, Q2 drain terminal to Q2 source terminal"},
                "driver_calibration": {"pull_up_edge_s": te_rise, "pull_down_edge_s": te_fall, "targets_s": [DRIVER_RISE, DRIVER_FALL]},
                "reference": REFERENCE, "materiality": MATERIAL, "cases": done, "comparison_to_reference": comparison,
                "runs": runs, "evidence_directory": str(run_root.relative_to(ROOT)),
            }
            report["complete"] = final
            tmp = args.output.with_name(args.output.name + ".tmp")
            tmp.write_text(json.dumps(report, indent=1) + "\n")
            os.replace(tmp, args.output)  # atomic: an interruption leaves the previous checkpoint intact

    def guarded(name, c):
        try:
            run_case(name, c)
        except Exception as exc:  # record the failure; the other cases continue
            results[name] = {"parameters": c, "metrics": None, "checks": None, "error": repr(exc)}
            print(name, "error:", repr(exc), flush=True)
        save()

    # Cases are independent except that a periodic case needs its extraction's slopes: run it afterwards.
    plain = {k: c for k, c in cases.items() if not c.get("periods")}
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        list(pool.map(lambda kv: guarded(*kv), plain.items()))
    for name, c in cases.items():
        if c.get("periods"):
            guarded(name, c)
    save(final=True)


if __name__ == "__main__":
    main()
