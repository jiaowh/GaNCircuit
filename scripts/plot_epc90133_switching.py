#!/usr/bin/env python3
"""Plot simulated EPC90133 switch-node edges for the extraction variants (README/doc figure).

Reads the LTspice waveforms kept in the sweep's evidence directory (git-ignored runs/) named by
results/gan/epc90133-switching-sensitivity.json and draws V(SW) about each edge, aligned at the 50%
crossing. The dashed line marks the peak of EPC's measured Fig. 9 read by eye (about 7 V above the
bus); it is not a digitized measurement. Colours: the dataviz reference palette's first four
categorical slots in fixed order.
"""
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from circuit_tools.ltspice import parse_raw
from epc9097_switching import cross

REPORT = ROOT / "results/gan/epc90133-switching-sensitivity.json"
OUT = ROOT / "results/gan/epc90133-switching-waveforms.png"
CASES = [("ideal-copper", "ideal copper (no board inductance)", "#2a78d6"),
         ("A-m1-mid", "A: top layer + mid-layer 1, Ci", "#eb6834"),
         ("I-m1-mid", "I: all 8 layers, Ci", "#1baf7a"),
         ("B-m1-mid", "B: all 8 layers, Ci + Cm", "#eda100")]
VIN = 48.0
INK, MUTED, GRID = "#1f1f1e", "#6b6a63", "#e4e3dc"


def main():
    rep = json.loads(REPORT.read_text(encoding="utf-8"))
    ev = ROOT / rep["evidence_directory"]
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), dpi=150, sharey=True)
    for key, label, col in CASES:
        s = parse_raw(ev / key / "bench.raw").step(0)
        t, sw = s["time"], s["v(q2_d)"]
        times = rep["cases"][key]["times_s"]
        for ax, t0, rising in ((axs[0], times["t_on2"], True), (axs[1], times["t_off1"], False)):
            t50 = cross(t, sw, VIN / 2, t0, rising)
            pts = [((tt - t50) * 1e9, v) for tt, v in zip(t, sw) if -10e-9 <= tt - t50 <= 30e-9]
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=col, lw=2, label=label)
    for ax, title in zip(axs, ("Q1 turn-on (switch node rises, 11 A)", "Q1 turn-off (switch node falls, 29 A)")):
        ax.axhline(VIN, color=MUTED, lw=1)
        ax.set_title(title, fontsize=10, color=INK)
        ax.set_xlabel("time from 50% crossing (ns)", color=MUTED)
        ax.grid(color=GRID, lw=0.8)
        ax.tick_params(colors=MUTED)
        for sp in ax.spines.values():
            sp.set_color(GRID)
    axs[0].axhline(VIN + 7, color=INK, lw=1, ls="--")
    axs[0].text(-9.5, VIN + 10, "EPC Fig. 9 peak,\nread by eye (~55 V)", ha="left", fontsize=8, color=INK)
    axs[0].text(-9.5, VIN - 5, "48 V bus", ha="left", fontsize=8, color=MUTED)
    axs[0].set_ylabel("switch-node voltage (V)", color=MUTED)
    axs[1].legend(fontsize=8, frameon=False, loc="upper right")
    fig.suptitle("Simulated EPC90133 switching edges for each extraction variant (exploratory, not validated)",
                 fontsize=10, color=INK)
    fig.tight_layout()
    fig.savefig(OUT)
    print(OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
