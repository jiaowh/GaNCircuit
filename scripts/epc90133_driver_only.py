"""Driver-only bench: uP1966E with its supply and bootstrap capacitors, power stage unpowered (E1 preparation).

One bounded preparation task for hardware-plan E1 (project audit at 8284dbd, 1 October 2026, work-order item 4).
Declared here, 1 October 2026, before any run. It answers three setup questions for E1; it does not fit anything to
QSG Fig. 9, changes no vendor model, and its results do not enter switching predictions without a separate, declared
revision.

Questions (each a declared output):

Q1  E1's discriminating power. At VIN = 0 the gate load is the fitted EPC2302s at zero drain bias (no Miller plateau).
    Do test 11's two driver representations (ramp: typical resistances behind a source ramp calibrated to 8/4 ns;
    step: a near-step source behind resistances calibrated to the same edge times; both from the stored
    results/gan/epc90133-switching-driver.json calibration) still differ at the accessible gate points (Q2's gate net
    at R22/J2; Q1's at R11/J1) under these conditions? Outputs: 10-90 % rise and 90-10 % fall at each gate pad, peak
    above the settled high level, and the largest difference between the two forms' gate-pad voltages within
    +/-20 ns of each edge (time axes aligned on the command). Gate-loop inductance is not extracted for this bench:
    0 and an assumed 1 nH (inside test 6's 0.5-2 nH range) in series between the driver output and the gate pad.
    Declared reading: E1 at VIN = 0 can distinguish the forms if, at the Q2 gate pad, the rise times differ by at
    least 0.3 ns or the voltages by at least 0.5 V, for both inductance values. These two figures are provisional
    resolution placeholders, replaced by the measurement chain's characterized resolution (E0) when it exists.
    Also reported: the switch-node excursion during the sequence (at VIN = 0 it should stay near 0 V; if it does,
    Q1's gate can be observed with a ground-referenced probe at J1 during E1, to be confirmed on the bench).

Q2  Bootstrap state before the first high-side pulse, and its droop per pulse. The driver's internal bootstrap switch
    charges C81 (100 nF, 25 V X7R 0402) from VCC while PHASE is low; at VIN = 0, PHASE stays near ground, so C81
    charges after power-up without a low-side pulse. Outputs: BOOT-PHASE 200 us after VCC starts (vs the datasheet
    BOOT POR rising threshold 2.5/3.2/3.94 V min/typ/max, and vs the 5.0 V ideal high-side supply of the switching
    bench), for an assumed BOOT quiescent load of 0, 20 and 100 uA (the datasheet gives none); the droop of
    BOOT-PHASE across each high-side turn-on; the VCC minimum at C80.

Q3  Bootstrap overcharge in the dead time, for the energized procedure. When the switch node goes negative during a
    dead time (Q2 reverse conduction; Fig. 9 suggests about -2.5 V, a model-dependent reading), the bootstrap switch
    charges C81 above VCC. Imposed PHASE excursions of -2.5 V for 5 and 10 ns, high side off. Output: the
    BOOT-PHASE rise per excursion, compared with the EPC2302 gate maximum (6 V) and the driver's BOOT-PHASE
    absolute maximum (7 V). The datasheet's BOOT voltage clamp is drawn but not specified, so it is not modelled:
    the result bounds the unclamped case only.

Circuit (assumed where marked):
* uP1966E output stages: drive_stage of scripts/epc9097_switching.py, made supply-referenced: its normalized pull-up
  and pull-down ramps scale the actual BOOT-PHASE or VCC-GND voltage, and the pull-up current is drawn from that
  supply node by a current mirror (check C1). Typical/step resistances as in test 11; R80/R82 1 ohm, R81/R83 0 ohm.
  Not modelled: propagation delays (20 ns typical), delay matching, UVLO/POR logic (commands start after both
  supplies are above their thresholds), the board's dead-time and buffer logic (commands are given at the driver).
* Bootstrap switch: a diode fitted to the datasheet's two forward voltages, 0.2 V at 100 uA and 0.9 V at 100 mA
  (N = 1 at 25 C, series resistance from the second point); reverse leakage ignored. Sensitivity: an assumed extra
  2.2 ohm in the charging path (R70/R75, 2.2 ohm, appear on the gate-driver schematic page but their connections
  are not transcribed).
* VCC: MCP1703 5.0 V LDO (schematic Fig. 17) as an ideal 5.0 V source behind an assumed 0.1 ohm, ramped 0 -> 5 V
  over an assumed 50 us; C80 4.7 uF at the driver (DC-bias derating not applied); the other VCC bypass capacitors
  omitted.
* C81 100 nF nominal; sensitivity at an assumed 50 nF (DC bias and tolerance).
* Power stage unpowered: VIN tied to ground (supply off, input capacitors discharged), no inductor, two unmodified
  EPC2302 models, 25 C, reltol 1e-6, 10 ps maximum step during the edge runs.
* Sequence (edge runs, starting from the start-up run's BOOT-PHASE with the 20 uA load): low side on 0.5 us, 10 ns
  dead time, high side on 0.5 us, 10 ns, low side 0.5 us, 10 ns, high side 0.5 us.

Cases: start-up runs (3 BOOT loads); edge runs ramp/step x 0/1 nH with C81 100 nF, plus ramp 0 nH with C81 50 nF and
ramp 0 nH with the extra 2.2 ohm (6); dead-time runs 5/10 ns (2); stage checks into 3000 pF (2). 13 runs in all.

Checks (declared):
C1  charge balance: across the first high-side turn-on (command to command + 100 ns), C81 x (BOOT-PHASE drop)
    equals the charge drawn by the pull-up mirror within 2 %.
C2  the supply-referenced stages with an ideal 5 V supply into 3000 pF give 8.0 ns rise and 4.0 ns fall within 2 %
    for both forms (the calibration carries over).
C3  every run completes under the LTspice adapter without fallbacks.

Stop rules: one run of the declared case set. A run that fails is kept with its reason; at most one fix run follows,
recorded as such. No parameters are fitted, no case is added after results are seen without a new declaration, and
no comparison with Fig. 9 is made.

    PYTHONPATH=src python scripts/epc90133_driver_only.py   # results/gan/epc90133-driver-only.json
"""
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
from epc9097_switching import R_SNK, R_SRC, SWITCH_MODELS, cross, drive_stage

OUTPUT = ROOT / "results/gan/epc90133-driver-only.json"
DRIVER_REPORT = ROOT / "results/gan/epc90133-switching-driver.json"
VCC, R_VCC, T_VCC_RAMP = 5.0, 0.1, 50e-6
C80, C81, C81_LOW = 4.7e-6, 100e-9, 50e-9
R_GON, R_GOFF = 1.0, 1e-3          # R80/R82 and R81/R83 (0 ohm as 1 mohm)
L_GATE = (0.0, 1e-9)
BOOT_LOADS = (0.0, 20e-6, 100e-6)
T_WAIT = 200e-6
PULSE, DEAD = 0.5e-6, 10e-9
DEAD_EXCURSIONS = (5e-9, 10e-9)
V_EXCURSION = -2.5
TEMP_C = 25.0
LOAD_3000P = 3000e-12
RISE_TARGET, FALL_TARGET = 8e-9, 4e-9
RES_RISE_S, RES_V = 0.3e-9, 0.5      # provisional resolution placeholders (Q1 reading)
EDGE_WIN = 20e-9


def boot_diode():
    """Diode through (100 uA, 0.2 V) and (100 mA, 0.9 V) with N = 1 at 25 C."""
    vt = 1.380649e-23 * (273.15 + TEMP_C) / 1.602176634e-19
    i_s = 100e-6 / math.expm1(0.2 / vt)
    rs = (0.9 - vt * math.log1p(0.1 / i_s)) / 0.1
    return {"Is_A": i_s, "N": 1.0, "Rs_ohm": rs,
            "model": f".model DBST D(Is={i_s:.6g} N=1 Rs={rs:.6g} Cjo=0 Tnom={TEMP_C:g})"}


def stage(tag, ref, sup, edges, te_rise, te_fall, out, r_src, r_snk, r_on, r_off, t_end):
    """drive_stage with its ramps scaled by the actual supply voltage and the pull-up current drawn from the supply."""
    text = drive_stage(tag, ref, 1.0, edges, te_rise, te_fall, out, r_src, r_snk, r_on, r_off, t_end)
    lines = text.rstrip().splitlines()
    pu = next(i for i, l in enumerate(lines) if l.startswith(f"V{tag}pu pus{tag} {ref} "))
    pd = next(i for i, l in enumerate(lines) if l.startswith(f"V{tag}pd pds{tag} {ref} "))
    pwl_u = lines[pu].split(f"V{tag}pu pus{tag} {ref} ", 1)[1]
    pwl_d = lines[pd].split(f"V{tag}pd pds{tag} {ref} ", 1)[1]
    lines[pu] = "\n".join([f"V{tag}fu fu{tag} 0 {pwl_u}",
                           f"B{tag}pu pux{tag} {ref} V=V(fu{tag})*V({sup},{ref})",
                           f"V{tag}sns pux{tag} pus{tag} 0",
                           f"F{tag}sup {sup} {ref} V{tag}sns 1"])
    lines[pd] = "\n".join([f"V{tag}fd fd{tag} 0 {pwl_d}",
                           f"B{tag}pd pds{tag} {ref} V=V(fd{tag})*V({sup},{ref})"])
    return "\n".join(lines)


def forms():
    rep = json.loads(DRIVER_REPORT.read_text(encoding="utf-8"))
    cal, st = rep["driver_calibration"], rep["driver_step_calibration"]
    return {"ramp": {"te_rise": cal["pull_up_edge_s"], "te_fall": cal["pull_down_edge_s"], "r_src": R_SRC, "r_snk": R_SNK},
            "step": {"te_rise": st["source_ramp_s"], "te_fall": st["source_ramp_s"], "r_src": st["r_src_ohm"],
                     "r_snk": st["r_snk_ohm"]}}


def header(title):
    return [f"* {title}", "* generated by scripts/epc90133_driver_only.py", ".lib EPCGaNLibrary.lib", boot_diode()["model"],
            SWITCH_MODELS.rstrip(), f".temp {TEMP_C:g}"]


def supplies(c81, r_boot_extra, boot_load, vcc_ramp=True):
    vsrc = f"PWL(0 0 {T_VCC_RAMP:g} {VCC:g})" if vcc_ramp else f"{VCC:g}"
    out = [f"Vvcc vccs 0 {vsrc}", f"Rvcc vccs vcc {R_VCC:g}", f"C80 vcc 0 {C80:g}",
           f"Dbst vcc bd DBST", f"Rbx bd boot {max(r_boot_extra, 1e-3):g}", f"C81 boot sw {c81:g}"]
    if boot_load:
        out.append(f"Iboot boot sw {boot_load:g}")
    return out


def power_stage():
    return ["Vvin vin 0 0", "X1 gu vin sw EPC2302", "X2 gl sw 0 EPC2302", "Rswleak sw 0 1Meg"]


def gate_paths(l_g):
    out = []
    for tag, pad in (("u", "gu"), ("l", "gl")):
        out.append(f"Lg{tag} gd{tag} {pad} {l_g:g}" if l_g else f"Rg{tag}0 gd{tag} {pad} 1e-6")
    return out


def sequence():
    t0 = 0.1e-6
    lo = [(t0, 1), (t0 + PULSE, 0)]
    hi = [(t0 + PULSE + DEAD, 1), (t0 + 2 * PULSE + DEAD, 0)]
    lo += [(t0 + 2 * PULSE + 2 * DEAD, 1), (t0 + 3 * PULSE + 2 * DEAD, 0)]
    hi += [(t0 + 3 * PULSE + 3 * DEAD, 1), (t0 + 4 * PULSE + 3 * DEAD, 0)]
    return hi, lo, t0 + 4 * PULSE + 3 * DEAD + 0.2e-6


def startup_netlist(boot_load):
    lines = header(f"start-up, BOOT load {boot_load * 1e6:g} uA") + supplies(C81, 0.0, boot_load) + power_stage()
    lines += ["Rgu gu sw 10k", "Rgl gl 0 10k", ".options plotwinsize=0 reltol=1e-6",
              f".tran 0 {T_WAIT:g} 0 50n", ".end"]
    return "\n".join(lines) + "\n"


def edge_netlist(form, l_g, c81, r_boot_extra, v_boot0):
    f = forms()[form]
    hi, lo, t_end = sequence()
    lines = header(f"edges: {form}, gate-loop L {l_g * 1e9:g} nH, C81 {c81 * 1e9:g} nF, extra {r_boot_extra:g} ohm")
    lines += supplies(c81, r_boot_extra, 0.0, vcc_ramp=False) + power_stage() + gate_paths(l_g)
    lines.append(stage("u", "sw", "boot", hi, f["te_rise"], f["te_fall"], "gdu", f["r_src"], f["r_snk"], R_GON, R_GOFF, t_end))
    lines.append(stage("l", "0", "vcc", lo, f["te_rise"], f["te_fall"], "gdl", f["r_src"], f["r_snk"], R_GON, R_GOFF, t_end))
    lines += [f".ic V(boot)={v_boot0:.6g} V(sw)=0 V(vcc)={VCC:g}", ".options plotwinsize=0 reltol=1e-6",
              f".tran 0 {t_end:.9g} 0 10p uic", ".end"]
    return "\n".join(lines) + "\n", hi, lo


def dead_netlist(width, v_boot0):
    t0 = 50e-9
    phase = f"PWL(0 0 {t0:g} 0 {t0 + 0.5e-9:g} {V_EXCURSION:g} {t0 + 0.5e-9 + width:g} {V_EXCURSION:g} {t0 + 1e-9 + width:g} 0)"
    lines = header(f"dead-time excursion {width * 1e9:g} ns at {V_EXCURSION:g} V")
    lines += supplies(C81, 0.0, 0.0, vcc_ramp=False)
    lines += [f"Vph sw 0 {phase}", ".options plotwinsize=0 reltol=1e-6",
              f".ic V(boot)={v_boot0:.6g} V(vcc)={VCC:g}", f".tran 0 {t0 + width + 100e-9:g} 0 10p uic", ".end"]
    return "\n".join(lines) + "\n", t0


def check_netlist(form):
    f = forms()[form]
    lines = header(f"stage check into 3000 pF, {form}")
    lines += [f"Vsup sup 0 {VCC:g}",
              stage("1", "0", "sup", [(20e-9, 1), (70e-9, 0)], f["te_rise"], f["te_fall"], "g", f["r_src"], f["r_snk"],
                    0, 0, 150e-9),
              f"Cl g 0 {LOAD_3000P:g}", ".options plotwinsize=0 reltol=1e-6", ".tran 0 150n 0 10p", ".end"]
    return "\n".join(lines) + "\n"


def edge_metrics(t, v, t_cmd_on, t_cmd_off):
    """10-90 rise after the on command, 90-10 fall after the off command, peak above the settled high level."""
    k = (t > t_cmd_off - 50e-9) & (t < t_cmd_off - 5e-9)
    high = float(np.mean(v[k]))
    r10, r90 = cross(t, v, 0.1 * high, t_cmd_on, True), cross(t, v, 0.9 * high, t_cmd_on, True)
    f90, f10 = cross(t, v, 0.9 * high, t_cmd_off, False), cross(t, v, 0.1 * high, t_cmd_off, False)
    w = (t > t_cmd_on) & (t < t_cmd_off)
    return {"high_level_V": high, "rise_10_90_s": (r90 - r10) if (r10 and r90) else None,
            "fall_90_10_s": (f10 - f90) if (f10 and f90) else None, "peak_above_high_V": float(np.max(v[w]) - high)}


def window_diff(ta, va, tb, vb, t_edges):
    out = 0.0
    for te in t_edges:
        tt = np.linspace(te - EDGE_WIN, te + EDGE_WIN, 4001)
        out = max(out, float(np.max(np.abs(np.interp(tt, ta, va) - np.interp(tt, tb, vb)))))
    return out


def main():
    lib, _ = bl.library_path()
    bl.verify_target_sources(lib)
    run_root = ROOT / "runs" / ("epc90133-driver-only-" + uuid.uuid4().hex[:12])
    runs, failures = {}, []

    def run(name, text, timeout=600):
        r = run_ltspice(text, run_root / name, libraries=[lib], timeout_s=timeout)
        runs[name] = {"status": r.status, "message": r.message, "elapsed_s": r.duration_s}
        if r.status != "completed":
            failures.append(name)
            print(name, r.status, r.message, flush=True)
            return None
        print(name, "completed", f"{r.duration_s:.0f} s", flush=True)
        return parse_raw(r.result_path).step(0)

    report = {"schema": "epc90133-driver-only/1", "declared": "2026-10-01, before any run (script docstring)",
              "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "input_manifest": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in (DRIVER_REPORT, ROOT / "scripts/epc9097_switching.py",
                                           ROOT / "scripts/epc2302_baseline.py", ROOT / "src/circuit_tools/ltspice.py", lib)},
              "boot_diode": {k: v for k, v in boot_diode().items() if k != "model"},
              "assumptions": {"VCC_V": VCC, "R_vcc_ohm": R_VCC, "vcc_ramp_s": T_VCC_RAMP, "C80_F": C80, "C81_F": C81,
                              "C81_low_F": C81_LOW, "R80_R82_ohm": R_GON, "gate_loop_L_H": list(L_GATE),
                              "boot_loads_A": list(BOOT_LOADS), "dead_excursion_V": V_EXCURSION,
                              "temperature_C": TEMP_C, "forms": forms()},
              "run_directory": run_root.relative_to(ROOT).as_posix()}

    # C2: stage checks
    c2 = {}
    for form in ("ramp", "step"):
        s = run(f"check-{form}", check_netlist(form))
        if s is None:
            c2[form] = None
            continue
        t, v = s["time"], s["v(g)"]
        r10, r90 = cross(t, v, 0.1 * VCC, 0, True), cross(t, v, 0.9 * VCC, 0, True)
        f90, f10 = cross(t, v, 0.9 * VCC, 60e-9, False), cross(t, v, 0.1 * VCC, 60e-9, False)
        c2[form] = {"rise_s": r90 - r10, "fall_s": f10 - f90}
    report["C2"] = {"forms": c2, "pass": all(x is not None and abs(x["rise_s"] / RISE_TARGET - 1) <= 0.02
                                             and abs(x["fall_s"] / FALL_TARGET - 1) <= 0.02 for x in c2.values())}

    # Q2a: start-up
    startup = {}
    for load in BOOT_LOADS:
        s = run(f"startup-{load * 1e6:g}uA", startup_netlist(load))
        if s is None:
            startup[f"{load * 1e6:g}"] = None
            continue
        t, vb = s["time"], s["v(boot)"] - s["v(sw)"]
        tp = cross(t, vb, 3.94, 0, True)
        startup[f"{load * 1e6:g}"] = {"boot_phase_at_wait_V": float(vb[-1]), "sw_at_wait_V": float(s["v(sw)"][-1]),
                                      "time_above_por_max_s": tp}
    report["startup"] = startup
    v_boot0 = (startup.get("20") or {}).get("boot_phase_at_wait_V", 4.8)

    # Q1/Q2b: edge runs
    hi, lo, _ = sequence()
    edge_cases = {"ramp-L0": ("ramp", 0.0, C81, 0.0), "step-L0": ("step", 0.0, C81, 0.0),
                  "ramp-L1n": ("ramp", 1e-9, C81, 0.0), "step-L1n": ("step", 1e-9, C81, 0.0),
                  "ramp-L0-C81low": ("ramp", 0.0, C81_LOW, 0.0), "ramp-L0-Rboot2.2": ("ramp", 0.0, C81, 2.2)}
    edges, traces = {}, {}
    for name, (form, l_g, c81, rbx) in edge_cases.items():
        text, _, _ = edge_netlist(form, l_g, c81, rbx, v_boot0)
        s = run(f"edges-{name}", text)
        if s is None:
            edges[name] = None
            continue
        t = s["time"]
        vgl, vgu, vsw = s["v(gl)"], s["v(gu)"] - s["v(sw)"], s["v(sw)"]
        vbp = s["v(boot)"] - s["v(sw)"]
        isns = s["i(vusns)"]
        m = {"q2_gate_pad": [edge_metrics(t, vgl, lo[2 * k][0], lo[2 * k + 1][0]) for k in range(2)],
             "q1_gate_pad": [edge_metrics(t, vgu, hi[2 * k][0], hi[2 * k + 1][0]) for k in range(2)],
             "sw_max_abs_V": float(np.max(np.abs(vsw))), "vcc_min_V": float(np.min(s["v(vcc)"]))}
        droops = []
        for k in range(2):
            ton = hi[2 * k][0]
            b0 = float(np.interp(ton - 1e-9, t, vbp))
            b1 = float(np.interp(ton + 100e-9, t, vbp))
            w = (t >= ton - 1e-9) & (t <= ton + 100e-9)
            q = float(np.trapezoid(isns[w], t[w]))
            droops.append({"before_V": b0, "after_100ns_V": b1, "drop_V": b0 - b1, "mirror_charge_C": q,
                           "c81_charge_C": c81 * (b0 - b1)})
        m["boot_phase"] = droops
        c1 = droops[0]
        m["C1_pass"] = bool(c1["mirror_charge_C"] > 0 and abs(c1["c81_charge_C"] / c1["mirror_charge_C"] - 1) <= 0.02)
        edges[name] = m
        traces[name] = (t, vgl, vgu)
    report["edges"] = edges

    # Q1 reading: ramp vs step
    q1 = {}
    for l_tag in ("L0", "L1n"):
        a, b = f"ramp-{l_tag}", f"step-{l_tag}"
        if edges.get(a) is None or edges.get(b) is None:
            q1[l_tag] = None
            continue
        ta, vla, vua = traces[a]
        tb, vlb, vub = traces[b]
        t_lo = [x[0] for x in lo]
        t_hi = [x[0] for x in hi]
        dr = abs(edges[a]["q2_gate_pad"][0]["rise_10_90_s"] - edges[b]["q2_gate_pad"][0]["rise_10_90_s"])
        dv = window_diff(ta, vla, tb, vlb, t_lo)
        q1[l_tag] = {"q2_rise_difference_s": dr, "q2_max_voltage_difference_V": dv,
                     "q1_max_voltage_difference_V": window_diff(ta, vua, tb, vub, t_hi),
                     "distinguishable": bool(dr >= RES_RISE_S or dv >= RES_V)}
    report["Q1_reading"] = {"per_inductance": q1, "resolution_placeholders": {"rise_s": RES_RISE_S, "voltage_V": RES_V},
                            "E1_can_distinguish_forms": (all(v is not None and v["distinguishable"] for v in q1.values())
                                                         if all(v is not None for v in q1.values()) else None)}

    # Q3: dead-time excursions
    dead = {}
    for width in DEAD_EXCURSIONS:
        text, t0 = dead_netlist(width, v_boot0)
        s = run(f"dead-{width * 1e9:g}ns", text)
        if s is None:
            dead[f"{width * 1e9:g}"] = None
            continue
        t, vbp = s["time"], s["v(boot)"] - s["v(sw)"]
        b0 = float(np.interp(t0 - 1e-9, t, vbp))
        b_end = float(vbp[-1])
        dead[f"{width * 1e9:g}"] = {"before_V": b0, "after_V": b_end, "rise_V": b_end - b0,
                                    "max_during_V": float(np.max(vbp)),
                                    "margin_to_gate_max_6V": 6.0 - b_end, "margin_to_boot_phase_abs_max_7V": 7.0 - b_end}
    report["dead_time_excursions"] = dead

    report["C1"] = {"pass": all(m is not None and m["C1_pass"] for m in edges.values())}
    report["C3"] = {"pass": not failures, "failed_runs": failures}
    report["runs"] = runs
    report["complete"] = not failures
    OUTPUT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("C1", "C2", "C3", "Q1_reading", "startup", "dead_time_excursions")}, indent=1))


if __name__ == "__main__":
    main()
