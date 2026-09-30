#!/usr/bin/env python3
"""Overlay the digitized QSG Fig. 9 edges on simulated switch-node traces (G3 diagnosis figure).

Each trace is aligned at its 50 % crossing and offset so that its settled low level is 0 V, as in
scripts/compare_epc90133_fig9.py. Usage:

    python scripts/plot_epc90133_fig9.py --cases B-m1-mid:none B-combined:1000MHz
"""
import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from compare_epc90133_fig9 import SETTLE, gaussian, settled  # noqa: E402
from digitize_epc90133_qsg_fig9 import crossing  # noqa: E402


def aligned(t, v, rising):
    first, last = float(np.median(v[:20])), float(np.median(v[-20:]))
    t50 = crossing(list(zip(t, v)), 0.5 * (first + last), rising)
    rel = t - t50
    low = settled(rel, v, -SETTLE[1], -SETTLE[0]) if rising else settled(rel, v, SETTLE[0], SETTLE[1])
    high = settled(rel, v, SETTLE[0], SETTLE[1]) if rising else settled(rel, v, -SETTLE[1], -SETTLE[0])
    vv = v - low
    t50 = crossing(list(zip(rel, vv)), 0.5 * (high - low), rising)
    return rel - t50, vv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fig9", type=Path, default=ROOT / "results/gan/epc90133-qsg-fig9.json")
    ap.add_argument("--sim", type=Path, nargs="+", default=[ROOT / "results/gan/epc90133-switching-causes.json"],
                    help="switching reports; a later file's case replaces an earlier case of the same name")
    ap.add_argument("--cases", nargs="+", default=["B-m1-mid:none"], help="case:bandwidth, bandwidth 'none' or e.g. 1000MHz")
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-fig9-overlay.png")
    args = ap.parse_args()
    fig9 = json.loads(args.fig9.read_text(encoding="utf-8"))
    sim = {"cases": {}}
    for f in args.sim:
        sim["cases"].update(json.loads(f.read_text(encoding="utf-8"))["cases"])
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
    for ax, kind in zip(axes, ("rising", "falling")):
        m = np.array(fig9["panels"][kind]["metrics"]["trace_rel_s_V"])
        ax.plot(m[:, 0] * 1e9, m[:, 1], color="black", lw=1.6, label="QSG Fig. 9 (digitized)")
        for spec in args.cases:
            name, bw = spec.split(":")
            tr = sim["cases"][name]["traces"]
            t = tr["start_s"] + tr["step_s"] * np.arange(len(tr[f"{kind}_V"]))
            v = gaussian(np.array(tr[f"{kind}_V"]), tr["step_s"], None if bw == "none" else float(bw[:-3]) * 1e6)
            tt, vv = aligned(t, v, kind == "rising")
            ax.plot(tt * 1e9, vv, lw=1.0, label=f"{name}, {'ideal probe' if bw == 'none' else bw[:-3] + ' MHz Gaussian'}")
        ax.set_xlim(-15, 30)
        ax.set_xlabel("time from 50 % crossing (ns)")
        ax.set_title(f"{kind} edge")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("V(SW) above settled low (V)")
    axes[1].legend(fontsize=7, loc="upper right")
    fig.suptitle("EPC90133 switch node: QSG Fig. 9 against simulation (exploratory extraction; probe unknown)", fontsize=10)
    fig.tight_layout()
    fig.savefig(args.output, dpi=120)
    print(args.output)


if __name__ == "__main__":
    main()
