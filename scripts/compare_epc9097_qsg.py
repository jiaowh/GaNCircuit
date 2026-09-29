#!/usr/bin/env python3
"""Compare the EPC9097 double-pulse simulation with EPC's published switch-node waveforms.

Inputs: results/gan/epc9097-switching-ideal-layout.json and
results/gan/epc9097-switching-traces.json (scripts/epc9097_switching.py),
results/gan/epc9097-qsg-waveforms.json (scripts/digitize_epc9097_qsg_waveforms.py)
and the model COSS curve in results/gan/epc2204-model-curves.json.

This is a diagnostic comparison, not an acceptance test. The measured values
were digitized before any comparison categories were chosen, the loop
inductance is swept rather than extracted, and EPC does not state the probe,
bandwidth or probing point. No pass/fail tolerance is therefore declared.
Each quantity is labelled with what it can test:

* turn-off fall time: set mainly by the inductor current charging the output
  capacitances (Qoss/I); insensitive to the swept loop inductance, so it
  tests the device model, subject to measurement bandwidth;
* reverse-conduction plateau before the rising edge: dead time and the
  lower FET's third-quadrant voltage; tests driver timing and the device;
* rise time, overshoot, ringing: depend on loop inductance and measurement
  bandwidth, so they are reported with the loop inductance they would imply,
  not as agreement.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIN = 48.0
PLATEAU_WINDOW = (-20e-9, -1e-9)  # s before the rising 50 % crossing
PLATEAU_THRESHOLD = 1.0           # V below the settled low level, as in the digitizer


def interp(xs, ys, x):
    for i in range(1, len(xs)):
        if xs[i] >= x:
            return ys[i - 1] + (ys[i] - ys[i - 1]) * (x - xs[i - 1]) / (xs[i] - xs[i - 1])
    return None


def sim_plateau(trace, step, t0):
    """Plateau metrics of a simulated rising-edge trace, with the digitizer's definition."""
    t = [t0 + k * step for k in range(len(trace))]
    low = [v for tt, v in zip(t, trace) if -45e-9 <= tt <= -25e-9]
    settled = sum(low) / len(low)
    dip = [(tt, v) for tt, v in zip(t, trace)
           if PLATEAU_WINDOW[0] <= tt <= PLATEAU_WINDOW[1] and v < settled - PLATEAU_THRESHOLD]
    if not dip:
        return {"settled_low_V": settled, "duration_s": 0.0, "depth_below_settled_V": 0.0}
    return {"settled_low_V": settled, "duration_s": dip[-1][0] - dip[0][0],
            "depth_below_settled_V": settled - min(v for _, v in dip)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sim", type=Path, default=ROOT / "results/gan/epc9097-switching-ideal-layout.json")
    parser.add_argument("--traces", type=Path, default=ROOT / "results/gan/epc9097-switching-traces.json")
    parser.add_argument("--qsg", type=Path, default=ROOT / "results/gan/epc9097-qsg-waveforms.json")
    parser.add_argument("--curves", type=Path, default=ROOT / "results/gan/epc2204-model-curves.json")
    parser.add_argument("--output", type=Path, default=ROOT / "results/gan/epc9097-switching-vs-qsg.json")
    args = parser.parse_args()
    sim = json.loads(args.sim.read_text())
    traces = json.loads(args.traces.read_text())
    qsg = json.loads(args.qsg.read_text())
    coss = json.loads(args.curves.read_text())["curves"]["coss_25C"]
    coss_48 = interp(coss["vds_V"], coss["coss_F"], VIN)
    step = traces["sample_step_s"]
    t0 = -50e-9

    rows = {}
    for load, fig, case in ((10.0, "fig13", "lloop_400pH_dt10ns"), (15.0, "fig14", "lloop_400pH_dt10ns_15A")):
        meas = qsg["figures"][fig]
        mr, mf = meas["rising"]["metrics"], meas["falling"]["metrics"]
        sweep = {name: c["metrics"] for name, c in sim["cases"].items()
                 if c["metrics"] and c["parameters"].get("load", 10.0) == load
                 and c["parameters"].get("dead") == 10e-9 and "rmax" not in name and "fine" not in name}
        ref = sim["cases"][case]["metrics"]
        a, b = ref["event_a_turn_off"], ref["event_b_turn_on"]
        f_meas = (mr.get("late_ring") or {}).get("frequency_Hz")
        l_implied = 1 / ((2 * math.pi * f_meas) ** 2 * coss_48) if f_meas else None
        sp = sim_plateau(traces["traces"][case]["rising"]["v_sw_V"], step, t0)
        mp = mr.get("reverse_conduction_plateau") or {}
        rows[f"{load:g}A"] = {
            "measured_figure": fig,
            "simulated_reference_case": case,
            "simulated_currents_A": {"turn_off": a["inductor_current_A"], "turn_on": b["inductor_current_A"]},
            "turn_off_fall_time_10_90_s": {
                "tests": "device output charge (Qoss/I); weakly dependent on loop inductance",
                "measured": mf["edge_10_90_s"], "simulated": a["sw_fall_time_90_10_s"],
                "simulated_range_over_loop_sweep": [min(m["event_a_turn_off"]["sw_fall_time_90_10_s"] for m in sweep.values()),
                                                    max(m["event_a_turn_off"]["sw_fall_time_90_10_s"] for m in sweep.values())]},
            "reverse_conduction_plateau_before_rise": {
                "tests": "dead time at the driver input and the lower FET's third-quadrant voltage",
                "measured": {"duration_s": mp.get("duration_s"),
                             "depth_below_settled_V": (mr["level_before_V"] - mp["min_V"]) if mp else None},
                "simulated": {"duration_s": sp["duration_s"], "depth_below_settled_V": sp["depth_below_settled_V"]}},
            "rise_time_10_90_s": {
                "tests": "loop inductance, driver strength and measurement bandwidth together",
                "measured": mr["edge_10_90_s"], "simulated": b["sw_rise_time_10_90_s"],
                "measurement_system_rise_time_if_simulation_were_exact_s":
                    math.sqrt(max(mr["edge_10_90_s"] ** 2 - b["sw_rise_time_10_90_s"] ** 2, 0.0)),
                "note": "root-sum-square convention for cascaded Gaussian-like responses; a hypothesis, not a measured bandwidth"},
            "overshoot_above_settled_V": {
                "tests": "loop inductance and damping, measurement bandwidth",
                "measured": mr["overshoot_above_settled_V"],
                "simulated_by_loop_inductance": {n: m["event_b_turn_on"]["sw_overshoot_above_bus_V"] for n, m in sweep.items()}},
            "ringing": {
                "tests": "an LC resonance somewhere in the power loop, bus or measurement path",
                "measured_persistent_frequency_Hz": f_meas,
                "measured_decay_time_s": (mr.get("late_ring") or {}).get("decay_time_s"),
                "measured_early_crest_spacing_s": mr.get("early_crest_spacing_s"),
                "simulated_frequency_by_loop_inductance_Hz": {n: m["event_b_turn_on"]["ringing_frequency_Hz"]
                                                              for n, m in sweep.items()},
                "inductance_implied_if_it_rings_with_one_coss_H": l_implied,
                "coss_used_F": coss_48,
                "coss_source": "model COSS at 48 V from epc2204-model-curves.json"},
        }
    load_independence = {
        "persistent_ring_frequencies_Hz": {f"{fig}_{k}": (qsg["figures"][fig][k]["metrics"].get("late_ring") or {}).get("frequency_Hz")
                                           for fig in ("fig12", "fig13", "fig14") for k in ("rising", "falling")},
        "observation": ("the persistent ring has the same frequency at 0, 10 and 15 A and on both edges, "
                        "so it comes from a fixed L and C; the digitized images cannot say whether that LC is "
                        "the power loop, the bus network or the probe connection"),
    }
    report = {
        "schema": "epc9097-switching-vs-qsg/1",
        "kind": "diagnostic comparison; no acceptance tolerance (see script docstring)",
        "evidence_classes": {"simulated": "unmodified EPC2204 model, behavioural driver, swept loop inductance",
                             "measured": "vendor-described waveforms digitized from raster screenshots"},
        "inputs": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.sim, args.traces, args.qsg, args.curves)},
        "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "by_load": rows,
        "persistent_ringing": load_independence,
    }
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    short = {}
    for k, r in rows.items():
        short[k] = {
            "fall_ns meas/sim": [round(r["turn_off_fall_time_10_90_s"]["measured"] * 1e9, 2),
                                 round(r["turn_off_fall_time_10_90_s"]["simulated"] * 1e9, 2)],
            "plateau_ns meas/sim": [r["reverse_conduction_plateau_before_rise"]["measured"]["duration_s"] and
                                    round(r["reverse_conduction_plateau_before_rise"]["measured"]["duration_s"] * 1e9, 2),
                                    round(r["reverse_conduction_plateau_before_rise"]["simulated"]["duration_s"] * 1e9, 2)],
            "plateau_depth_V meas/sim": [r["reverse_conduction_plateau_before_rise"]["measured"]["depth_below_settled_V"] and
                                         round(r["reverse_conduction_plateau_before_rise"]["measured"]["depth_below_settled_V"], 2),
                                         round(r["reverse_conduction_plateau_before_rise"]["simulated"]["depth_below_settled_V"], 2)],
            "rise_ns meas/sim": [round(r["rise_time_10_90_s"]["measured"] * 1e9, 2),
                                 round(r["rise_time_10_90_s"]["simulated"] * 1e9, 2)],
            "implied_L_nH": r["ringing"]["inductance_implied_if_it_rings_with_one_coss_H"] and
                            round(r["ringing"]["inductance_implied_if_it_rings_with_one_coss_H"] * 1e9, 2),
        }
    print(json.dumps(short, indent=1))


if __name__ == "__main__":
    main()
