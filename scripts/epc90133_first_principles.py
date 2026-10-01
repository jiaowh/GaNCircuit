"""Analytical scale checks on frozen Fig. 9 metrics, not a fitted board model.

Maps the fitted damped sinusoid to a hypothetical single series RLC mode and
compares excitation/decay scales. The board is nonlinear and multiport; its
diagnostic loop L is not established as that mode's L. No simulator is invoked.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def mode(metrics, inductance):
    wd = 2 * math.pi * metrics["ring_frequency_Hz"]
    alpha = 1 / metrics["ring_decay_time_s"]
    wn = math.hypot(wd, alpha)
    r = alpha / wd
    # For a free series RLC with v_C(0)=0 and i_L(0)=I0:
    # v_C,peak = I0 sqrt(L/C) exp[-r atan(1/r)].
    return {"alpha_per_s": alpha, "damping_ratio_exact": alpha / wn,
            "amplitude_remaining_per_cycle": math.exp(-2 * math.pi * r),
            "modal_energy_remaining_per_cycle": math.exp(-4 * math.pi * r),
            "R_equivalent_ohm": 2 * alpha * inductance,
            "C_equivalent_F": 1 / (inductance * wn * wn),
            "first_peak_attenuation_for_initial_current": math.exp(-r * math.atan(1 / r))}


def main():
    sources = {
        "comparison": ROOT / "results/gan/epc90133-fig9-comparison.json",
        "extraction": ROOT / "results/gan/epc90133-extraction/G-m1-mid.json",
        "transfer_audit": ROOT / "results/gan/epc90133-network-transfer-audit.json",
    }
    data = {k: json.loads(p.read_text()) for k, p in sources.items()}
    meas = data["comparison"]["measured"]["rising"]
    sim = data["comparison"]["cases"]["G-m1-mid-Ls50"]["bandwidths"]["none"]["metrics"]["rising"]
    board_l = data["extraction"]["summary"]["L_loop_nH"] * 1e-9
    loss = data["transfer_audit"]["cases"]["G-m1-mid"]
    delta_r = (loss["full_R"]["R_loop_mohm"] - loss["diagonal_R"]["R_loop_mohm"]) * 1e-3
    rows = {}
    for name, inductance in (("board_diagnostic_L_only", board_l),
                             ("board_plus_two_assumed_50pH_sources", board_l + 100e-12)):
        m, s = mode(meas, inductance), mode(sim, inductance)
        gap = m["R_equivalent_ohm"] - s["R_equivalent_ohm"]
        rows[name] = {"assumed_modal_L_H": inductance, "measured_mode": m, "simulated_mode": s,
                      "equivalent_R_gap_ohm": gap,
                      "omitted_R_fraction_of_equivalent_gap": delta_r / gap}
    m = mode(meas, board_l)
    s = mode(sim, board_l)
    attenuation_ratio = m["first_peak_attenuation_for_initial_current"] / s["first_peak_attenuation_for_initial_current"]
    amplitude_ratio = meas["overshoot_above_settled_V"] / sim["overshoot_above_settled_V"]
    report = {
        "schema": "epc90133-first-principles/1", "scope": __doc__.strip(),
        "inputs": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources.values()},
        "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "single_mode_hypotheses_not_board_parameter_estimates": rows,
        "overshoot": {"measured_to_simulated_ratio": amplitude_ratio,
                      "same_initial_current_and_LC_damping_only_ratio": attenuation_ratio,
                      "residual_excitation_or_observation_factor_in_this_approximation": amplitude_ratio / attenuation_ratio,
                      "measured_if_voltage_scale_rescaled_to_48V": meas["overshoot_above_settled_V"] * 48 / meas["swing_V"]},
        "Gaussian_gain_at_measured_ring_frequency": {str(bw): math.exp(-math.log(2) / 2 * (meas["ring_frequency_Hz"] / bw)**2)
                                                       for bw in (350e6, 500e6, 1e9, 2e9)},
        "bootstrap_charge_scale": {"assumed_gate_charge_C": 23e-9, "nominal_C81_F": 100e-9,
                                   "Q_over_C_V": 23e-9 / 100e-9,
                                   "scope": "charge scale only; not a predicted droop; recharge, bias derating and driver current omitted"},
    }
    out = ROOT / "results/gan/epc90133-first-principles.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
