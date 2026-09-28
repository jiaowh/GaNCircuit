#!/usr/bin/env python3
"""Double-pulse simulation of the stock EPC9097 half bridge (G3, ideal-layout step).

Two unmodified EPC2204 models, the board's gate resistors and loop capacitors,
and a behavioural uP1966E driver run in LTspice at the conditions of EPC's
published waveforms (QSG v3.0 Figs. 12-14: 48 V in, 12 V out, 1 MHz, 2.2 uH,
10 ns dead time, 10 and 15 A load). The upper FET (Q1) is the hard-switched
device of a buck. The double pulse is converter-equivalent: the first pulse
builds the inductor current to the converter's peak (load + half the 4.1 A
ripple), the off time is the converter's 750 ns, so Q1 turns off and on again
at the converter's valley and peak currents.

Layout parasitics are not extracted yet. The power-loop inductance is swept
instead, so the report shows how strongly each prediction depends on it and
therefore how accurately the extraction must resolve it. All assumptions are
listed in the report; the principal ones:

* Driver: EPC publishes no uP1966E SPICE model. Each output pin is a ramped
  voltage source behind the datasheet's typical output resistance (0.7 ohm
  source, 0.4 ohm sink), connected only while the pin is active. The ramp
  times are calibrated in a separate bench so that 3000 pF rises in 8 ns and
  falls in 4 ns (datasheet typicals). A first version that ramped switch
  resistance instead could not slow the edge below the RC limit (4.6 ns). Propagation delay (20 ns, matched to 1.5 ns typ) is a common
  shift and omitted; delay mismatch is covered by the dead-time sweep.
* High-side supply: an ideal 4.8 V floating source (5 V VCC less the 0.2 V
  low-current bootstrap-switch drop). Bootstrap ripple is ignored
  (5.7 nC on 0.1 uF, about 60 mV).
* Capacitors: 7 x 220 nF loop capacitors lumped as one ideal 1.54 uF with
  1 mohm ESR; DC-bias derating ignored. The bus behind them is a damped
  network (see BUS below) standing in for the 10 x 1 uF intermediate
  capacitors and the lab supply.
* All loop inductance is lumped in series with Q1's drain; gate-loop and
  common-source inductances are zero in this step.
"""
import argparse
import bisect
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from circuit_tools.ltspice import ltspice_capability, parse_raw, run_ltspice
import epc2204_baseline as bl

VIN, VOUT, L_OUT = 48.0, 12.0, 2.2e-6
F_SW = 1e6                 # Hz, QSG Table 2
DUTY = VOUT / VIN
T_OFF = (1 - DUTY) / F_SW  # s between Q1 turn-off and the next turn-on command
RIPPLE = (VIN - VOUT) * DUTY / (F_SW * L_OUT)  # A peak-to-peak, lossless estimate
LOADS = (10.0, 15.0)       # A, QSG Figs. 13 and 14 (Fig. 12, 0 A, needs negative valley current)
T_ON2 = 150e-9             # s length of the second pulse
VCC, VBOOT = 5.0, 4.8      # V
R_SRC, R_SNK = 0.7, 0.4    # ohm, uP1966E typical output resistance
R_SRC_MAX, R_SNK_MAX = 1.4, 0.8
R_GON, R_GOFF = 1.0, 0.0   # ohm, R80/R82 and R81/R83
C_LOOP = 7 * 220e-9
DRIVER_LOAD = 3000e-12
DRIVER_RISE, DRIVER_FALL = 8e-9, 4e-9  # datasheet typical, 10-90 %
EDGE_GRID = (0.1e-9, 0.5e-9, 1e-9, 2e-9, 3e-9, 4e-9, 6e-9, 8e-9, 10e-9, 12e-9)
L_LOOP_SWEEP = (0.01e-9, 0.2e-9, 0.4e-9, 0.8e-9)
L_LOOP_REF = 0.4e-9        # sweep reference point for the other sensitivities (not an estimate of the board)
DEAD_TIMES = (4e-9, 10e-9, 16e-9)  # 10 ns default; 10 +/- 6 ns covers the driver's maximum delay mismatch
MAXSTEP = 20e-12
RELTOL = 1e-6
CONVERGENCE_TOLERANCE = 0.02
BUS = """* Bus behind the loop capacitors: lab supply and leads, intermediate capacitors (assumed values)
Vin vin 0 {vin}
Rsup vin vm1 20m
Lsup vm1 vm 20n
Cm vm vmc 10u
Rcm vmc 0 10m
Rbus vm vcr 2m
Lbus vcr vc 1n
"""
SWITCH_MODELS = """.model SWON SW(Ron=1m Roff=100Meg Vt=0.5 Vh=-0.05)
.model SWOFF SW(Ron=1m Roff=100Meg Vt=-0.5 Vh=-0.05)
"""
SWITCH_EDGE = 10e-12  # s, the output switches only select the active pin (high impedance otherwise)
RESET = 20e-12        # s, an idle pin's source is reset this long after its switch opens


def pwl(points, t_end):
    pts = sorted(points)
    pts.append((t_end, pts[-1][1]))
    return "PWL(" + " ".join(f"{t:.12g} {v:.6g}" for t, v in pts) + ")"


def drive_stage(tag, ref, vdd, edges, te_rise, te_fall, gate, r_src, r_snk, r_on, r_off, t_end):
    """One uP1966E output channel (split pull-up and pull-down pins) with the board's gate resistors.

    Each pin is a voltage source behind the output resistance, connected by a
    switch only while that pin is active. The pull-up source ramps 0 -> VDD
    over te_rise when the channel turns on; the pull-down source ramps VDD -> 0
    over te_fall when it turns off. The ramps stand for the driver's internal
    pre-driver slew and are calibrated against the datasheet edge times.
    """
    ctrl, up, down = [(0.0, 0)], [(0.0, 0.0)], [(0.0, 0.0)]
    for t, level in edges:
        ctrl += [(t, 1 - level), (t + SWITCH_EDGE, level)]
        if level:
            up += [(t, 0.0), (t + te_rise, vdd)]
            down += [(t + RESET, 0.0), (t + 2 * RESET, vdd)]
        else:
            down += [(t, vdd), (t + te_fall, 0.0)]
            up += [(t + RESET, vdd), (t + 2 * RESET, 0.0)]
    return f"""V{tag}c c{tag} 0 {pwl(ctrl, t_end)}
V{tag}pu pus{tag} {ref} {pwl(up, t_end)}
S{tag}u pus{tag} pu{tag} c{tag} 0 SWON
R{tag}u pu{tag} {gate} {r_src + r_on:g}
V{tag}pd pds{tag} {ref} {pwl(down, t_end)}
S{tag}d pds{tag} pd{tag} 0 c{tag} SWOFF
R{tag}d {gate} pd{tag} {r_snk + r_off:g}
"""


def driver_bench():
    """3000 pF load on each edge-time grid point; rise uses the pull-up ramp, fall the pull-down ramp."""
    runs = {}
    for k, te in enumerate(EDGE_GRID):
        runs[f"driver_edge_{k}"] = f"""* uP1966E behavioural output stage into {DRIVER_LOAD*1e12:g} pF; source ramp {te*1e9:g} ns
{drive_stage("1", "0", VCC, [(20e-9, 1), (70e-9, 0)], te, te, "g", R_SRC, R_SNK, 0, 0, 150e-9)}Cl g 0 {DRIVER_LOAD:g}
{SWITCH_MODELS}.options plotwinsize=0 reltol={RELTOL:g}
.tran 0 150n 0 10p
.end
"""
    return runs


def double_pulse(l_loop, dead, t_edge_rise, t_edge_fall, load=LOADS[0], r_src=R_SRC, r_snk=R_SNK,
                 maxstep=MAXSTEP, reltol=RELTOL):
    """Converter-equivalent buck double pulse: Q1 turns off at load + ripple/2 and on at load - ripple/2."""
    slope_on = (VIN - VOUT) / L_OUT
    t1 = (load + RIPPLE / 2) / slope_on
    t_on1 = 20e-9
    t_off1 = t_on1 + t1                  # Q1 command low (event A: hard turn-off)
    t_lo1 = t_off1 + dead                # Q2 command high
    t_lo0 = t_off1 + T_OFF - dead        # Q2 command low
    t_on2 = t_off1 + T_OFF               # Q1 command high (event B: hard turn-on)
    t_off2 = t_on2 + T_ON2
    t_end = t_off2 + 100e-9
    hi = [(t_on1, 1), (t_off1, 0), (t_on2, 1), (t_off2, 0)]
    lo = [(t_lo1, 1), (t_lo0, 0), (t_off2 + dead, 1)]
    text = f"""* EPC9097 double pulse: 2 x unmodified EPC2204, behavioural uP1966E; generated by scripts/epc9097_switching.py
.lib EPCGaNLibrary.lib
{BUS.format(vin=VIN)}Cloop vc vcx {C_LOOP:g}
Rcloop vcx 0 1m
Lloop vc d1 {l_loop:g}
X1 gu d1 sw EPC2204
X2 gl sw 0 EPC2204
L1 sw out {L_OUT:g}
Vout out 0 {VOUT}
* Upper driver: floating bootstrap supply ({VBOOT} V) referenced to the switch node
{drive_stage("u", "sw", VBOOT, hi, t_edge_rise, t_edge_fall, "gu", r_src, r_snk, R_GON, R_GOFF, t_end)}* Lower driver ({VCC} V)
{drive_stage("l", "0", VCC, lo, t_edge_rise, t_edge_fall, "gl", r_src, r_snk, R_GON, R_GOFF, t_end)}{SWITCH_MODELS}* Save only the traces the metrics use; all nodes would be about 70 traces x 1e5 points
.save V(sw) V(d1) V(gu) V(gl) V(vc) I(L1) I(Lloop)
.temp 25
.options plotwinsize=0 reltol={reltol:g}
.tran 0 {t_end:.9g} 0 {maxstep:g}
.end
"""
    return text, {"t_off1": t_off1, "t_on2": t_on2, "t_off2": t_off2, "t_end": t_end}


def cross(t, y, level, start_t, rising):
    """First interpolated time after start_t where y crosses level in the given direction."""
    for i in range(1, len(t)):
        if t[i] <= start_t:
            continue
        a, b = y[i - 1], y[i]
        if (rising and a < level <= b) or (not rising and a > level >= b):
            return t[i - 1] + (t[i] - t[i - 1]) * (level - a) / (b - a)
    return None


def window(t, y, t0, t1):
    return [(tt, v) for tt, v in zip(t, y) if t0 <= tt <= t1]


def integral(t, y, t0, t1):
    pts = window(t, y, t0, t1)
    return sum(0.5 * (pts[k][1] + pts[k - 1][1]) * (pts[k][0] - pts[k - 1][0]) for k in range(1, len(pts)))


def interp(t, y, x):
    """Linear interpolation on an increasing time axis (binary search)."""
    i = bisect.bisect_left(t, x)
    if i == 0 or i >= len(t):
        return None
    return y[i - 1] + (y[i] - y[i - 1]) * (x - t[i - 1]) / (t[i] - t[i - 1])


def edge_times(raw):
    """10-90 % rise and 90-10 % fall of the driver-bench gate voltage for every step."""
    out = []
    for k in range(raw.n_steps):
        s = raw.step(k)
        t, v = s["time"], s["v(g)"]
        r10, r90 = cross(t, v, 0.1 * VCC, 0, True), cross(t, v, 0.9 * VCC, 0, True)
        f90, f10 = cross(t, v, 0.9 * VCC, 60e-9, False), cross(t, v, 0.1 * VCC, 60e-9, False)
        out.append((r90 - r10 if r10 and r90 else None, f10 - f90 if f10 and f90 else None))
    return out


def solve_edge(grid, times, target):
    """Control-edge time giving the target 10-90 % time, by linear interpolation on the grid."""
    pairs = [(g, x) for g, x in zip(grid, times) if x is not None]
    for (g0, x0), (g1, x1) in zip(pairs, pairs[1:]):
        if (x0 - target) * (x1 - target) <= 0 and x1 != x0:
            return g0 + (g1 - g0) * (target - x0) / (x1 - x0)
    return None


def metrics(s, times):
    """Switching metrics from one double-pulse transient."""
    t = s["time"]
    sw, d1, gu, gl = s["v(sw)"], s["v(d1)"], s["v(gu)"], s["v(gl)"]
    vds1 = [a - b for a, b in zip(d1, sw)]
    vgs1 = [a - b for a, b in zip(gu, sw)]
    id1 = s["i(lloop)"]  # Q1 drain current: Lloop is in series with the drain
    il = s["i(l1)"]
    p1 = [a * b for a, b in zip(vds1, id1)]
    ta, tb = times["t_off1"], times["t_on2"]
    vbus_b = interp(t, s["v(vc)"], tb)
    # Event A: Q1 hard turn-off, switch node falls.
    a90 = cross(t, sw, 0.9 * VIN, ta, False)
    a10 = cross(t, sw, 0.1 * VIN, ta, False)
    ga = cross(t, vgs1, 0.9 * VBOOT, ta, False)
    a_end = cross(t, vds1, 0.9 * VIN, ta, True)
    event_a = {
        "inductor_current_A": interp(t, il, ta),
        "sw_fall_time_90_10_s": (a10 - a90) if a90 and a10 else None,
        "sw_dv_dt_V_per_s": (0.8 * VIN / (a10 - a90)) if a90 and a10 else None,
        "q1_eoff_J": integral(t, p1, ga, a_end + 2e-9) if ga and a_end else None,
        "q1_eoff_definition": "terminal VDS*ID of Q1 from VGS1 = 90 % until VDS1 = 90 % of VIN + 2 ns",
        "q2_third_quadrant_min_sw_V": min(v for _, v in window(t, sw, ta, ta + times["t_on2"] - ta - 10e-9)),
    }
    # Event B: Q1 hard turn-on, switch node rises.
    gb = cross(t, vgs1, 0.1 * VBOOT, tb, True)
    b10 = cross(t, sw, 0.1 * VIN, tb, True)
    b90 = cross(t, sw, 0.9 * VIN, tb, True)
    b_end = cross(t, vds1, 0.1 * VIN, tb, False)
    ring = window(t, sw, tb, tb + 60e-9)
    peak_t, peak_v = max(ring, key=lambda p: p[1])
    maxima = [ring[k] for k in range(1, len(ring) - 1)
              if ring[k][1] > ring[k - 1][1] and ring[k][1] >= ring[k + 1][1] and ring[k][0] >= peak_t
              and ring[k][1] > VIN + 0.05]
    freq = damping = None
    if len(maxima) >= 3:
        periods = [maxima[k][0] - maxima[k - 1][0] for k in range(1, len(maxima))]
        freq = 1 / (sum(periods[:3]) / len(periods[:3]))
        a0, a1 = maxima[0][1] - VIN, maxima[1][1] - VIN
        if a1 > 0:
            delta = math.log(a0 / a1)
            damping = delta / math.sqrt(4 * math.pi ** 2 + delta ** 2)
    event_b = {
        "inductor_current_A": interp(t, il, tb),
        "sw_rise_time_10_90_s": (b90 - b10) if b10 and b90 else None,
        "sw_dv_dt_V_per_s": (0.8 * VIN / (b90 - b10)) if b10 and b90 else None,
        "sw_peak_V": peak_v,
        "sw_overshoot_above_bus_V": peak_v - vbus_b,
        "ringing_frequency_Hz": freq,
        "ringing_damping_ratio": damping,
        "q1_peak_drain_current_A": max(v for _, v in window(t, id1, tb, tb + 60e-9)),
        "q1_eon_J": integral(t, p1, gb, b_end) if gb and b_end else None,
        "q1_eon_definition": "terminal VDS*ID of Q1 from VGS1 = 10 % until VDS1 = 10 % of VIN",
        "q1_eon_30ns_window_J": integral(t, p1, gb, gb + 30e-9) if gb else None,
        "q2_gate_peak_during_rise_V": max(v for _, v in window(t, gl, tb, tb + 60e-9)),
    }
    limits = {
        "q1_vds_max_V": max(vds1),
        "q2_vds_max_V": max(sw),
        "q1_vgs_max_V": max(vgs1),
        "q2_vgs_max_V": max(gl),
        "q2_vgs_min_V": min(gl),
        "bus_voltage_at_event_b_V": vbus_b,
    }
    return {"event_a_turn_off": event_a, "event_b_turn_on": event_b, "limits": limits}


TRACE_STEP = 0.1e-9
TRACE_WINDOW = (-50e-9, 50e-9)  # s about each edge, the QSG panels' 10 ns/div span


def edge_traces(s, times):
    """V(sw) on a uniform grid about the 50 % crossing of each edge, for comparison with the QSG panels."""
    t, sw = s["time"], s["v(sw)"]
    out = {}
    for kind, t0, rising in (("rising", times["t_on2"], True), ("falling", times["t_off1"], False)):
        t50 = cross(t, sw, VIN / 2, t0, rising)
        n = int(round((TRACE_WINDOW[1] - TRACE_WINDOW[0]) / TRACE_STEP)) + 1
        grid = [TRACE_WINDOW[0] + k * TRACE_STEP for k in range(n)]
        out[kind] = {"t50_s": t50, "v_sw_V": [round(interp(t, sw, t50 + g), 4) for g in grid]}
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", default=None)
    parser.add_argument("--output", type=Path, default=ROOT / "results/gan/epc9097-switching-ideal-layout.json")
    parser.add_argument("--traces", type=Path, default=ROOT / "results/gan/epc9097-switching-traces.json")
    args = parser.parse_args()
    lib, archive_sha = bl.library_path()
    run_root = ROOT / "runs" / ("epc9097-switching-" + uuid.uuid4().hex)
    runs = {}

    def run(name, text):
        r = run_ltspice(text, run_root / name, libraries=[lib], executable=args.executable, timeout_s=600)
        # Keep only the status summary: the result's measurement lists hold every waveform
        # (hundreds of MB per double-pulse case) and would accumulate across cases.
        runs[name] = {"status": r.status, "message": r.message, "duration_s": r.duration_s,
                      "warnings": r.provenance.get("log_warnings"), "netlist_sha256": r.provenance.get("netlist_sha256")}
        return parse_raw(r.result_path) if r.status == "completed" and r.result_path else None

    # 1. Driver calibration against the datasheet edge times.
    rises, falls = [], []
    for name, text in driver_bench().items():
        raw = run(name, text)
        rf = edge_times(raw)[0] if raw else (None, None)
        rises.append(rf[0])
        falls.append(rf[1])
    te_rise = solve_edge(EDGE_GRID, rises, DRIVER_RISE)
    te_fall = solve_edge(EDGE_GRID, falls, DRIVER_FALL)
    driver = {"load_F": DRIVER_LOAD, "r_source_ohm": R_SRC, "r_sink_ohm": R_SNK,
              "grid_control_edge_s": list(EDGE_GRID), "rise_10_90_s": rises, "fall_90_10_s": falls,
              "target_rise_s": DRIVER_RISE, "target_fall_s": DRIVER_FALL,
              "calibrated_pull_up_edge_s": te_rise, "calibrated_pull_down_edge_s": te_fall}
    if te_rise is None or te_fall is None:
        raise SystemExit(f"driver calibration did not bracket the datasheet edge times: {json.dumps(driver)}")

    # 2. Double-pulse cases.
    cases = {}
    for l in L_LOOP_SWEEP:
        cases[f"lloop_{l*1e12:.0f}pH_dt10ns"] = dict(l_loop=l, dead=10e-9)
    cases[f"lloop_{L_LOOP_REF*1e12:.0f}pH_dt10ns_15A"] = dict(l_loop=L_LOOP_REF, dead=10e-9, load=LOADS[1])
    for d in DEAD_TIMES:
        if d != 10e-9:
            cases[f"lloop_{L_LOOP_REF*1e12:.0f}pH_dt{d*1e9:.0f}ns"] = dict(l_loop=L_LOOP_REF, dead=d)
    cases[f"lloop_{L_LOOP_REF*1e12:.0f}pH_dt10ns_driver_rmax"] = dict(l_loop=L_LOOP_REF, dead=10e-9,
                                                                       r_src=R_SRC_MAX, r_snk=R_SNK_MAX)
    ref = f"lloop_{L_LOOP_REF*1e12:.0f}pH_dt10ns"
    cases[ref + "_fine"] = dict(l_loop=L_LOOP_REF, dead=10e-9, maxstep=MAXSTEP / 2, reltol=RELTOL / 10)
    results, traces = {}, {}
    for name, kw in cases.items():
        text, times = double_pulse(t_edge_rise=te_rise, t_edge_fall=te_fall, **kw)
        raw = run(name, text)
        results[name] = {"parameters": {k: v for k, v in kw.items()}, "times_s": times,
                         "metrics": metrics(raw.step(0), times) if raw else None}
        if raw:
            traces[name] = edge_traces(raw.step(0), times)

    # 3. Numerical convergence of the reference case.
    def flat(d, prefix=""):
        out = {}
        for k, v in d.items():
            if isinstance(v, dict):
                out.update(flat(v, prefix + k + "."))
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                out[prefix + k] = v
        return out
    conv = None
    if results[ref]["metrics"] and results[ref + "_fine"]["metrics"]:
        a, b = flat(results[ref]["metrics"]), flat(results[ref + "_fine"]["metrics"])
        checked = ["event_b_turn_on.sw_rise_time_10_90_s", "event_b_turn_on.sw_overshoot_above_bus_V",
                   "event_b_turn_on.q1_eon_J", "event_b_turn_on.ringing_frequency_Hz",
                   "event_a_turn_off.sw_fall_time_90_10_s", "event_a_turn_off.q1_eoff_J"]
        rel = {k: (abs(b[k] / a[k] - 1) if a.get(k) and b.get(k) else None) for k in checked}
        conv = {"reference": ref, "fine": ref + "_fine", "change": "max step halved, reltol 1e-7",
                "relative_change": rel, "tolerance": CONVERGENCE_TOLERANCE,
                "outcome": "pass" if all(v is not None and v <= CONVERGENCE_TOLERANCE for v in rel.values()) else "fail"}

    failed = {n: r["message"] for n, r in runs.items() if r["status"] != "completed"}
    report = {
        "schema": "epc9097-switching-ideal-layout/1",
        "gate": "G3 (stock-board simulation), step: switching bench before layout extraction",
        "scope": ("Simulated predictions from the unmodified EPC2204 model with a behavioural driver and "
                  "swept, not extracted, loop inductance. Not a board prediction until the loop inductance "
                  "is extracted from the matching layout revision; not validated against measurement."),
        "run_outcome": "completed" if not failed else "incomplete",
        "failed_runs": failed,
        "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "model": {"library": bl.LIB_NAME, "library_sha256": hashlib.sha256(lib.read_bytes()).hexdigest(),
                  "archive_sha256": archive_sha, "subcircuit": "EPC2204", "modified": False},
        "tool": asdict(ltspice_capability(args.executable)),
        "conditions": {"vin_V": VIN, "vout_V": VOUT, "inductor_H": L_OUT, "switching_frequency_Hz": F_SW,
                       "off_time_s": T_OFF, "ripple_A_pp": RIPPLE, "loads_A": list(LOADS),
                       "double_pulse": "converter-equivalent: turn-off at load + ripple/2, turn-on at load - ripple/2",
                       "temperature_C": 25, "source": "EPC9097 QSG v3.0 Table 2 and Figs. 12-14"},
        "assumptions": {
            "driver": ("behavioural uP1966E: ramped pull-up/pull-down sources behind typical 0.7/0.4 ohm, each "
                       "connected only while active; ramps calibrated to the datasheet's 8 ns rise / 4 ns fall "
                       "into 3000 pF; propagation delay omitted"),
            "gate_resistors": {"turn_on_ohm": R_GON, "turn_off_ohm": R_GOFF, "source": "schematic R80-R83, BOM"},
            "high_side_supply_V": VBOOT,
            "low_side_supply_V": VCC,
            "loop_capacitors": "7 x 220 nF (BOM Ci1-Ci7) as one ideal 1.54 uF, 1 mohm ESR; no DC-bias derating",
            "bus_network": BUS.strip().splitlines()[1:],
            "loop_inductance": "lumped in series with Q1 drain; swept, not extracted",
            "gate_and_common_source_inductance_H": 0,
            "dead_time": "applied at the driver inputs, as the QSG defines it",
        },
        "driver_calibration": driver,
        "loop_inductance_sweep_H": list(L_LOOP_SWEEP),
        "cases": results,
        "numerical_convergence": conv,
        "evidence_directory": str(run_root.relative_to(ROOT)),
        "runs": runs,
    }
    report["traces_file"] = str(args.traces.relative_to(ROOT))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    args.traces.write_text(json.dumps({"schema": "epc9097-switching-traces/1",
                                       "time_origin": "50 % crossing of V(sw) at each edge",
                                       "sample_step_s": TRACE_STEP, "traces": traces}, allow_nan=False) + "\n")
    summary = {}
    for n, c in results.items():
        m = c["metrics"]
        if m:
            b, a = m["event_b_turn_on"], m["event_a_turn_off"]
            summary[n] = {"I_on_A": round(b["inductor_current_A"], 2),
                          "rise_ns": b["sw_rise_time_10_90_s"] and round(b["sw_rise_time_10_90_s"] * 1e9, 3),
                          "overshoot_V": round(b["sw_overshoot_above_bus_V"], 2),
                          "ring_MHz": b["ringing_frequency_Hz"] and round(b["ringing_frequency_Hz"] / 1e6, 1),
                          "Eon_nJ": b["q1_eon_J"] and round(b["q1_eon_J"] * 1e9, 1),
                          "fall_ns": a["sw_fall_time_90_10_s"] and round(a["sw_fall_time_90_10_s"] * 1e9, 3),
                          "Eoff_nJ": a["q1_eoff_J"] and round(a["q1_eoff_J"] * 1e9, 1),
                          "Vgs2_peak_V": round(b["q2_gate_peak_during_rise_V"], 3)}
    print(json.dumps({"run_outcome": report["run_outcome"], "failed": failed,
                      "driver_edges_s": [te_rise, te_fall], "summary": summary,
                      "convergence": conv and conv["outcome"], "report": str(args.output)}, indent=2))
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
