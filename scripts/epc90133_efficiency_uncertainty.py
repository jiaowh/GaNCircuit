#!/usr/bin/env python3
"""Meter accuracy needed for an EPC90133 efficiency measurement (hardware plan E9), before the inventory.

Loss is the difference of two large powers, Ploss = Vin Iin - Vout Iout, so its relative uncertainty is
much larger than that of either power. With independent relative errors eVi, eIi, eVo, eIo (one standard
uncertainty each) and DC readings,

    u(Ploss)^2 = Pin^2 (eVi^2 + eIi^2) + Pout^2 (eVo^2 + eIo^2),

and the efficiency eta = Pout / Pin has u(eta) / eta = sqrt(eVi^2 + eIi^2 + eVo^2 + eIo^2).
Correlated errors (one meter on both sides, one shunt type) partly cancel and are not credited here.

This script takes the operating points and the loss fraction as parameters. The loss fraction is a sweep, not a
prediction: no validated loss model exists (gate-charge dependent, G2 exception). For each point it reports
the equal per-reading relative uncertainty that keeps u(Ploss)/Ploss at the target, and the resulting u(eta).
It also bounds the error of multiplying averaged readings when ripple is correlated:
|mean(v i) - mean(v) mean(i)| <= sigma_v sigma_i (Cauchy-Schwarz), as a fraction of the power.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# (Vin, Vout, Iout): Fig. 9 conditions and lower-power points inside a stepped envelope (proposals)
POINTS = [(48.0, 13.8, 20.0), (48.0, 13.8, 10.0), (48.0, 13.8, 5.0), (24.0, 6.9, 10.0)]
LOSS_FRACTIONS = (0.01, 0.02, 0.03, 0.05)  # of Pin, swept
TARGET = 0.10  # u(Ploss)/Ploss
RIPPLE = (0.001, 0.01)  # sigma/mean of voltage and current at a meter, examples for the product bound


def per_reading(pin, pout, ploss, target):
    """Equal relative standard uncertainty e for all four readings giving u(Ploss) = target * Ploss."""
    return target * ploss / math.sqrt(2 * (pin ** 2 + pout ** 2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-efficiency-uncertainty.json")
    args = ap.parse_args()
    rows = []
    for vin, vout, iout in POINTS:
        pout = vout * iout
        for lf in LOSS_FRACTIONS:
            pin = pout / (1 - lf)
            ploss = pin - pout
            e = per_reading(pin, pout, ploss, TARGET)
            rows.append({"vin_V": vin, "vout_V": vout, "iout_A": iout, "pout_W": round(pout, 2),
                         "loss_fraction_assumed": lf, "ploss_W": round(ploss, 3),
                         "per_reading_rel_uncertainty_for_target": e,
                         "u_eta_abs_at_that_accuracy": (1 - lf) * 2 * e})
    product = [{"sigma_rel_v": a, "sigma_rel_i": b, "max_rel_power_error": a * b}
               for a in RIPPLE for b in RIPPLE]
    report = {"schema": "epc90133-efficiency-uncertainty/1",
              "scope": "Requirement arithmetic with swept loss fractions; no prediction of the board's loss; proposals, not lab-approved.",
              "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "target_u_ploss_rel": TARGET, "rows": rows, "ripple_product_bound": product}
    args.output.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    for r in rows:
        print(f"{r['vin_V']:>4} V -> {r['vout_V']:>4} V, {r['iout_A']:>4} A, loss {r['loss_fraction_assumed']:.0%}"
              f" ({r['ploss_W']:6.2f} W): each reading <= {r['per_reading_rel_uncertainty_for_target'] * 100:.3f} %,"
              f" u(eta) = {r['u_eta_abs_at_that_accuracy'] * 100:.3f} points")


if __name__ == "__main__":
    main()
