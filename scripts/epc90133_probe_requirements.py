#!/usr/bin/env python3
"""Measurement-chain requirements for EPC90133 switching measurements, before the inventory.

Derives what each channel must meet from waveform features already on record, so the lab's
equipment can be checked against numbers when the inventory arrives. Inputs: the measured
QSG Fig. 9 features and the usable simulated cases in results/gan/epc90133-fig9-comparison.json
(cases with failed checks or interpretation_invalid are excluded). The board's waveform is
not known; the span from Fig. 9 to the fastest usable simulated case is the range a
discriminating measurement must resolve (hardware plan H4: Fig. 9 itself may be
bandwidth-limited). The simulated cases are not predictions of the board.

Declared allowances (proposals for the owner, 5 October 2026; not lab-approved):
  rise-time error   <= 5 %:  system rise time t_sys <= tr * sqrt(1.05^2 - 1), and
                              bandwidth >= 0.35 / t_sys (Gaussian-like response; the 0.35
                              factor is the usual approximation, not a property of a real probe)
  ring amplitude    <= 3 % at the ring frequency, for a Gaussian magnitude response
                              |H(f)| = exp(-(ln 2 / 2) (f / f3dB)^2)
  sample rate       >= max(2.5 x bandwidth, 10 samples per fastest 10-90 % edge)
  channel deskew    <= 10 % of the fastest edge
  capacitive load   ring-frequency shift <= 1 %: C_probe <= 2 x 0.01 x C_ring, with C_ring
                              the EPC2302 datasheet COSS at 50 V (1000 pF typical); this bounds
                              the tip capacitance only, not the ground-path inductance
  floating Q1 VGS   error <= 0.1 V under the switch-node common-mode step (swing plus overshoot):
                              CMRR >= 20 log10(step / 0.1 V) over the edge's frequency content;
                              edge dv/dt per case = 0.8 x swing / (10-90 % time)
Ranges and ratings: switch node and PHASE from the uP1966E PHASE rating (-5 to +85 V) and the
EPC2302 VDS rating (100 V); gate channels from the EPC2302 VGS rating (-4 to +6 V).
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPARISON = ROOT / "results/gan/epc90133-fig9-comparison.json"
RISE_ERR, RING_ERR, F_SHIFT, VGS_ERR = 0.05, 0.03, 0.01, 0.1
COSS_50V = 1000e-12  # F, EPC2302 datasheet typical, VDS = 50 V
BW_RT = 0.35


def bw_for_rise(tr):
    t_sys = tr * math.sqrt((1 + RISE_ERR) ** 2 - 1)
    return BW_RT / t_sys, t_sys


def bw_for_ring(f):
    return f / math.sqrt(-math.log(1 - RING_ERR) * 2 / math.log(2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-probe-requirements.json")
    args = ap.parse_args()
    comp = json.loads(COMPARISON.read_text(encoding="utf-8"))
    meas = comp["measured"]["rising"]
    rows = [{"case": "QSG Fig. 9", "tr_s": meas["edge_10_90_s"], "f_Hz": meas["ring_frequency_Hz"],
             "swing_V": meas["swing_V"], "overshoot_V": meas["overshoot_above_settled_V"]}]
    for name, c in comp["cases"].items():
        if not c.get("usable") or c.get("interpretation_invalid"):
            continue
        r = c["bandwidths"]["none"]["metrics"]["rising"]
        rows.append({"case": name, "tr_s": r["edge_10_90_s"], "f_Hz": r["ring_frequency_Hz"],
                     "swing_V": r["swing_V"], "overshoot_V": r["overshoot_above_settled_V"]})
    tr_min = min(r["tr_s"] for r in rows)
    f_max = max(r["f_Hz"] for r in rows)
    step_max = max(r["swing_V"] + r["overshoot_V"] for r in rows)
    fig9 = rows[0]

    def need(tr, f):
        bw_r, t_sys = bw_for_rise(tr)
        bw_f = bw_for_ring(f)
        bw = max(bw_r, bw_f)
        return {"bandwidth_for_rise_Hz": bw_r, "system_rise_time_max_s": t_sys, "bandwidth_for_ring_Hz": bw_f,
                "bandwidth_Hz": bw, "sample_rate_Sps": max(2.5 * bw, 10 / tr), "deskew_max_s": 0.1 * tr}

    req = {"at_fig9": need(fig9["tr_s"], fig9["f_Hz"]), "at_fastest_usable_case": need(tr_min, f_max)}
    loading = {"probe_capacitance_max_F": 2 * F_SHIFT * COSS_50V,
               "note": "tip capacitance only; the ground path's inductance and the probe's own resonance are set by the connection and are characterized in E0"}
    fig9_step = fig9["swing_V"] + fig9["overshoot_V"]
    q1 = {"common_mode_step_V": step_max, "cmrr_min_dB": 20 * math.log10(step_max / VGS_ERR),
          "fig9_common_mode_step_V": fig9_step, "cmrr_min_at_fig9_dB": 20 * math.log10(fig9_step / VGS_ERR),
          "edge_dv_dt_max_V_per_s": max(0.8 * r["swing_V"] / r["tr_s"] for r in rows),
          "edge_dv_dt_fig9_V_per_s": 0.8 * fig9["swing_V"] / fig9["tr_s"],
          "note": "applies to a floating high-side gate measurement; a ground-referenced probe on J1's switch-node return would tie the switch node to earth"}
    channels = [
        {"channel": "switch node (Q2 drain to GND)", "range_V": [-10, 100], "resolution_target_V": 0.3,
         "requirements": "bandwidth, sample rate and deskew as above; vertical resolution near the 0.31 V Fig. 9 pixel",
         "connection": "J33 footprint (8.6 mm from Q2 drain) or as approved; probe-points section"},
        {"channel": "Q2 VGS (low side, source = GND)", "range_V": [-4, 6], "resolution_target_V": 0.1,
         "requirements": "same bandwidth as the switch node (the predicted spike occurs during the switch-node edge); resolution against the 0.8 V minimum threshold",
         "connection": "J2/R22 or the 100 mil pair on that net (unfitted; fitting needs the lab's approval)"},
        {"channel": "PHASE to GND near U80", "range_V": [-10, 100], "resolution_target_V": 0.5,
         "requirements": "same bandwidth; undershoot against the -5 V rating is a stop criterion",
         "connection": "C81 PHASE pad to C80 GND pad (3.9 mm apart)"},
        {"channel": "Q1 VGS (high side, floating)", "range_V": [-4, 6], "resolution_target_V": VGS_ERR,
         "requirements": "CMRR as in q1_floating_gate; optional, only with a probe class that meets it",
         "connection": "J1/R11 (unfitted)"},
        {"channel": "inductor current", "range_A": [0, 35], "accuracy_target": "2 % at the 11.1 and 28.9 A edge currents",
         "requirements": "DC-coupled; bandwidth to resolve the double-pulse ramp, not the switching edge",
         "connection": "around the user-fitted inductor lead"},
    ]
    report = {
        "schema": "epc90133-probe-requirements/1",
        "scope": "Requirements derived from recorded waveform features and declared allowances; proposals, not lab-approved; no equipment assessed.",
        "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "inputs": {str(COMPARISON.relative_to(ROOT)): hashlib.sha256(COMPARISON.read_bytes()).hexdigest()},
        "allowances": {"rise_time_error": RISE_ERR, "ring_amplitude_error": RING_ERR, "ring_frequency_shift": F_SHIFT,
                       "floating_vgs_error_V": VGS_ERR, "bandwidth_rise_time_product": BW_RT},
        "features": rows, "fastest_edge_s": tr_min, "highest_ring_Hz": f_max,
        "requirements": req, "switch_node_loading": loading, "q1_floating_gate": q1, "channels": channels,
    }
    args.output.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    fmt = lambda d: {k: (f"{v / 1e9:.2f} G" if k.endswith(("Hz", "Sps")) else f"{v * 1e12:.0f} ps") for k, v in d.items()}
    print(json.dumps({"fastest_edge_ns": tr_min * 1e9, "highest_ring_MHz": f_max / 1e6,
                      "at_fig9": fmt(req["at_fig9"]), "at_fastest": fmt(req["at_fastest_usable_case"]),
                      "probe_C_max_pF": loading["probe_capacitance_max_F"] * 1e12,
                      "q1_cmrr_dB": [q1["cmrr_min_at_fig9_dB"], q1["cmrr_min_dB"]], "dv_dt_V_per_ns": q1["edge_dv_dt_max_V_per_s"] * 1e-9}, indent=1))


if __name__ == "__main__":
    main()
