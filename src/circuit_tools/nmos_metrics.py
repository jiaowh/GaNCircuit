"""Finite-span DC diagnostics; these are not certified local derivatives."""
from __future__ import annotations

import math

from .nmos_data import NMOSDataError, NMOSDataset


def dc_secants(dataset: NMOSDataset) -> dict:
    """Return six centred drain-current secants on a symmetric 3x3 grid.

    Values use S/cm, matching the input A/cm convention. A valid result only
    establishes that the calculation is defined; mesh and step-size accuracy
    need separate evidence.
    """
    rows = {(r["vgs_v"], r["vds_v"]): r for r in dataset.records}
    gates = sorted({g for g, _ in rows})
    drains = sorted({d for _, d in rows})
    if len(rows) != 9 or len(gates) != 3 or len(drains) != 3:
        raise NMOSDataError("secants require a complete 3x3 grid")
    for axis in (gates, drains):
        span = axis[2] - axis[0]
        left, right = axis[1] - axis[0], axis[2] - axis[1]
        if not all(math.isfinite(v) and v > 0 for v in (span, left, right)):
            raise NMOSDataError("secant bias spans must be positive and finite")
        if not math.isclose(left, right, rel_tol=1e-12, abs_tol=0):
            raise NMOSDataError("centred secants require symmetric bias spacing")

    def metric(low, high, varying_axis):
        x, y = rows[low], rows[high]
        low_current = x["currents_a_per_cm"]["drain"]
        high_current = y["currents_a_per_cm"]["drain"]
        span = high[varying_axis] - low[varying_axis]
        numerator = high_current - low_current
        value = numerator / span
        if not math.isfinite(numerator) or not math.isfinite(value):
            raise NMOSDataError("secant arithmetic produced a nonfinite value")
        return {
            "value": value,
            "units": "S/cm",
            "low_id": x["id"], "high_id": y["id"],
            "low_bias": low[varying_axis], "high_bias": high[varying_axis],
            "low_current_A_per_cm": low_current,
            "high_current_A_per_cm": high_current,
            "span_v": span, "numerator_A_per_cm": numerator,
        }

    result = {}
    for drain in drains:
        result[f"gm_vds_{drain:g}"] = metric((gates[0], drain), (gates[2], drain), 0)
    for gate in gates:
        result[f"gds_vgs_{gate:g}"] = metric((gate, drains[0]), (gate, drains[2]), 1)
    return result
