#!/usr/bin/env python3
"""Switch-node capacitance added by a thinner top dielectric (V8 + 0.075 mm confirmation, step 3; declared in
plans/goal-targets-2026-10-08.md before any of its runs).

Parallel-plate estimate, no fringing: switch-node (SW) copper on the top layer over GND copper on mid-layer 1, from the
board rasters (1 mil pixels), eps_r 4.8 (stackup FR370-HR), at the stock 0.127 mm and at 0.075 mm. Read the V8 KiCad
package by setting EPC90133_GERBER_EXPORT to its directory. Decision rule (declared): if the increase, scaled by the
+0.8 V of overshoot observed for the whole 135 pF C_SW on G, exceeds 0.1 V, a nominal sensitivity case is declared
separately; otherwise the estimate is reported and no case is run. Output: results/gan/epc90133-csw-dielectric.json.
"""
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
from read_epc90133_geometry import PITCH, geometry_source, load_board

EPS0, EPS_R = 8.854e-12, 4.8
C_SW_TOTAL, OVERSHOOT_PER_C_SW, MATERIAL_V = 135e-12, 0.8, 0.1


def net_mask(b, e, net):
    lab = b.labels[e]
    names = np.array(["none"] + [b.net_name.get(b.find((e, k)), "other") for k in range(1, b.counts[e] + 1)])
    return names[lab] == net


def main():
    b = load_board()
    overlap = net_mask(b, "GTL", "SW") & net_mask(b, "G1", "GND")
    area_m2 = overlap.sum() * (PITCH * 1e-3) ** 2
    c = {d: EPS0 * EPS_R * area_m2 / (d * 1e-3) for d in (0.127, 0.075)}
    dc = c[0.075] - c[0.127]
    effect = dc / C_SW_TOTAL * OVERSHOOT_PER_C_SW
    out = {"geometry_source": {k: v for k, v in geometry_source().items() if k != "dir"}, "overlap_area_mm2": area_m2 * 1e6,
           "C_top_to_G1_pF": {f"{d:g} mm": v * 1e12 for d, v in c.items()}, "increase_pF": dc * 1e12,
           "scaled_overshoot_effect_V": effect, "threshold_V": MATERIAL_V,
           "sensitivity_case_needed": bool(effect > MATERIAL_V), "scope": __doc__}
    (ROOT / "results/gan/epc90133-csw-dielectric.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "scope"}, indent=1))


if __name__ == "__main__":
    main()
