#!/usr/bin/env python3
"""Screening upper bounds for layout ideas (plans/layout-search-2026-10-07.md, method step 1).

Declared 7 October 2026 before any screening run. Each screen edits the rasterized EPC geometry of mid-layer 1
(G1, the power loop's return plane) before variant A's mesh is built, then runs the normal extraction
(scripts/epc90133_extract.py, A:m1:mid) and compares the loop inductance with stock A. Screens are idealized: they
ignore manufacturing minimum widths and are NOT designs; they only decide which ideas are worth a legal build.

Screens (G1 only; "hole" = an interior ring of a G1 copper island larger than 1 mm^2, i.e. a clearance cut in the
GND plane; "per-via antipad" = a disk of radius drill/2 + 0.150114 mm, EPC's clearance, no non-functional pad):
* S0 control: no edit; must reproduce results/gan/epc90133-extraction/A-m1-mid.json (loop L within 1e-6 relative).
* S1 holes whose centroid lies in Q1's window (17.2, 28.7)-(23.8, 33.3) become per-via antipads.
* S2 the same in Q2's window (17.2, 23.7)-(23.8, 28.3).
* S3 the same in the input-capacitor strip (15.5, 33.0)-(31.6, 34.7) (the VIN pair slots).
* S4 S1 + S2 + S3.
* S5 ceiling: every hole in the loop window (14, 22)-(34, 38) becomes bare drill disks (radius drill/2, no clearance).
Run 1 (7 October 2026): S0 reproduces stock exactly; S1 -19.0 %, S2 -9.2 %, S3 -0.7 %, S4 -54 %. S5 is INVALID
(recorded retrospectively): with holes shrunk to the bare drill, the plane reaches the VIN/SW via barrels, the
extraction's rim sampling bonds those vias to GND, and the loop is shorted (-88 %); it is not a ceiling.
Realistic screens (declared after run 1, before their runs; EPC's single-via inner-layer antipad has area 0.337 mm^2,
radius 0.3275 mm, so per-via antipads at the 0.6 mm row pitch merge into the existing slots, which is why EPC slots):
* S6 under Q1: in the slotted non-GND columns (x = 18.0 SW, 20.1 SW, 21.9 SW, 23.0 VIN) every other via is removed
  (kept: the 1st, 3rd, 5th from the lowest y), and each Q1-window hole becomes EPC-size per-via antipads (r = 0.3275)
  around the remaining drills;
* S7 the same under Q2 (columns x = 19.2, 20.9, 22.7, all SW); Q2's GND columns are the return path and stay;
* S8 S6 + S7.
These are legal-like (EPC's own antipad size, webs of 0.54 mm) but variant A omits the bottom loop that the removed
vias also feed, so a passing screen needs confirmation on B.
Drop rule: an idea whose screen does not lower loop L by more than 4 % is not built. Output:
results/gan/epc90133-layout-screen.json (and the extraction reports under results/gan/epc90133-layout-screen/).
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import Polygon, box

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import read_epc90133_geometry as g
from circuit_tools.gerber import load_layer, parse_excellon, rasterize
from epc90133_reconstruct import layer_geometry, polygons

CLEAR = 0.150114
WINDOWS = {"Q1": (17.2, 28.7, 23.8, 33.3), "Q2": (17.2, 23.7, 23.8, 28.3), "Ci": (15.5, 33.0, 31.6, 34.7)}
LOOP = (14.0, 22.0, 34.0, 38.0)
SCREENS = {"S0": [], "S1": ["Q1"], "S2": ["Q2"], "S3": ["Ci"], "S4": ["Q1", "Q2", "Ci"], "S5": ["ceiling"],
           "S6": ["thin:Q1"], "S7": ["thin:Q2"], "S8": ["thin:Q1", "thin:Q2"]}
THIN = {"Q1": (18.0, 20.1, 21.9, 23.0), "Q2": (19.2, 20.9, 22.7)}
EPC_ANTIPAD_R = 0.3275  # mm, from the 0.337 mm^2 single-via antipads on mid-layers 1-4
OUTDIR = ROOT / "results/gan/epc90133-layout-screen"
STOCK = ROOT / "results/gan/epc90133-extraction/A-m1-mid.json"


def g1_holes():
    geo = polygons(layer_geometry(load_layer(g.GERBERS / f"{g.PREFIX}Gerbers.G1")))
    return [Polygon(r) for p in geo if p.area > 1.0 for r in p.interiors]


def edit_grid(grid, holes, drills, regions, ceiling):
    ys = g.BOARD[1] + np.arange(grid.shape[0]) * g.PITCH
    xs = g.BOARD[0] + np.arange(grid.shape[1]) * g.PITCH
    changed = 0
    for h in holes:
        c = h.centroid
        if ceiling:
            if not box(*LOOP).contains(c):
                continue
        elif not any(box(*WINDOWS[r]).contains(c) for r in regions):
            continue
        i0, i1 = np.searchsorted(ys, [h.bounds[1] - g.PITCH, h.bounds[3] + g.PITCH])
        j0, j1 = np.searchsorted(xs, [h.bounds[0] - g.PITCH, h.bounds[2] + g.PITCH])
        X, Y = np.meshgrid(xs[j0:j1], ys[i0:i1])
        inside = shapely.contains_xy(h, X, Y)
        fill = inside.copy()
        for d in drills:
            if h.contains(shapely.Point(d.x, d.y)):
                r = d.diameter / 2 + (0 if ceiling else CLEAR)
                fill &= (X - d.x) ** 2 + (Y - d.y) ** 2 > r * r
        sub = grid[i0:i1, j0:j1]
        changed += int((fill & ~sub).sum())
        sub[fill] = True
    return changed


def thinned(drills, regions):
    """Drills kept after removing every other via in the declared columns (S6-S8), and the removed ones."""
    gone = set()
    for r in regions:
        w = WINDOWS[r]
        for cx in THIN[r]:
            col = sorted((d for d in drills if abs(d.x - cx) < 0.06 and w[0] < d.x < w[2] and w[1] < d.y < w[3]),
                         key=lambda d: d.y)
            gone |= {id(d) for d in col[1::2]}
    return [d for d in drills if id(d) not in gone], len(gone)


def edit_thin(grid, holes, drills, regions):
    ys = g.BOARD[1] + np.arange(grid.shape[0]) * g.PITCH
    xs = g.BOARD[0] + np.arange(grid.shape[1]) * g.PITCH
    changed = 0
    for h in holes:
        if not any(box(*WINDOWS[r]).contains(h.centroid) for r in regions):
            continue
        i0, i1 = np.searchsorted(ys, [h.bounds[1] - g.PITCH, h.bounds[3] + g.PITCH])
        j0, j1 = np.searchsorted(xs, [h.bounds[0] - g.PITCH, h.bounds[2] + g.PITCH])
        X, Y = np.meshgrid(xs[j0:j1], ys[i0:i1])
        fill = shapely.contains_xy(h, X, Y)
        for d in drills:
            if h.contains(shapely.Point(d.x, d.y)):
                fill &= (X - d.x) ** 2 + (Y - d.y) ** 2 > EPC_ANTIPAD_R ** 2
        sub = grid[i0:i1, j0:j1]
        changed += int((fill & ~sub).sum())
        sub[fill] = True
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("screens", nargs="*", default=list(SCREENS))
    args = ap.parse_args()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    holes = g1_holes()
    drills = parse_excellon((g.GERBERS / f"{g.PREFIX}NC Drill.TXT").read_text(encoding="latin-1"))
    stock = json.loads(STOCK.read_text(encoding="utf-8"))["summary"]["L_loop_nH"]
    out = OUTDIR.parent / "epc90133-layout-screen.json"
    report = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {
        "schema": "epc90133-layout-screen/1", "stock_A_L_loop_nH": stock, "screens": {}}
    report["evaluator_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    import epc90133_extract as x
    for s in args.screens:
        info = {}

        def patched():
            grids = {e: rasterize(load_layer(g.GERBERS / f"{g.PREFIX}Gerbers.{e}"), g.BOARD, g.PITCH)
                     for e in g.LAYERS + ("GTO",)}
            hs = parse_excellon((g.GERBERS / f"{g.PREFIX}NC Drill.TXT").read_text(encoding="latin-1"))
            regs = SCREENS[s]
            if regs and regs[0].startswith("thin:"):
                tr = [r.split(":")[1] for r in regs]
                hs, info["vias_removed"] = thinned(hs, tr)
                info["pixels_added"] = edit_thin(grids["G1"].grid, holes, hs, tr)
            elif regs:
                info["pixels_added"] = edit_grid(grids["G1"].grid, holes, hs, [r for r in regs if r != "ceiling"],
                                                 "ceiling" in regs)
            return g.derive(grids, hs)

        x.load_board = patched
        sys.argv = ["epc90133_extract.py", "A:m1:mid", "--outdir", str(OUTDIR), "--tag", s]
        try:
            x.main()
            r = json.loads((OUTDIR / f"A-m1-mid-{s}.json").read_text(encoding="utf-8"))
            L = r["summary"]["L_loop_nH"]
            info.update({"L_loop_nH": L, "relative_change": L / stock - 1, "outcome": r.get("outcome"),
                         "worth_building": L / stock - 1 < -0.04})
        except (SystemExit, Exception) as exc:  # record and continue with the next screen
            info.update({"error": repr(exc)})
        report["screens"][s] = {"regions": SCREENS[s], **info}
        out.write_text(json.dumps(report, indent=1) + "\n")
        print(s, json.dumps(report["screens"][s]), flush=True)
    s0 = report["screens"].get("S0", {})
    report["S0_control_pass"] = bool(s0.get("L_loop_nH") and abs(s0["L_loop_nH"] / stock - 1) <= 1e-6)
    out.write_text(json.dumps(report, indent=1) + "\n")
    print("S0 control", report["S0_control_pass"])


if __name__ == "__main__":
    main()
