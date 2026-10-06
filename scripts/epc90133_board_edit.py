#!/usr/bin/env python3
"""Checked geometry edits on the rasterized EPC90133 layers (layout round 2, plans/layout-round-2-plan.md).

Edits change the in-memory rasters and drill list that scripts/read_epc90133_geometry.py derives connectivity
from; the Gerber files are never touched. After every edit the board is derived again by the same code
(read_epc90133_geometry.derive), and the edit is refused unless its checks pass.

add_via(board, x, y, net, drill): a plated through via, as a real layout would place it:
  * on every copper layer where the via centre is on copper of `net`: a pad of diameter drill + 2 x RING joined
    to that copper (the via bonds there);
  * on every layer where copper of another net lies within the antipad radius: a clearance hole of diameter
    drill + 2 x CLEARANCE is cut (an antipad); the cut must not split that copper island;
  * elsewhere nothing (no unused pads).
Rules, refused otherwise (values follow the existing layout where it shows them, else stated assumptions):
  R1 drill not smaller than the smallest plated drill on the board (0.198 mm);
  R2 centre spacing to every existing hole at least MIN_PITCH (0.52 mm, the smallest via spacing in the power
     area);
  R3 not under a component pad: no paste (GTP/GBP) within the pad radius plus CLEARANCE;
  R4 bonds to `net` on at least two layers (else it carries no current);
  R5 after derivation: the probe nets VIN/SW/GND stay distinct, every layer the new via bonds belongs to `net`, and
     no other net's island count changes except where an antipad was cut without splitting it (checked).
  R6 (added 5 October 2026 after the first candidate cut Q1's source path in the extraction mesh): no antipad in
     VIN or SW copper; holes are not cut into the power current path.
Assumptions (no fab rule given; open question in the plan): RING = 0.125 mm annular ring, CLEARANCE = 0.2 mm.
"""
import copy
import dataclasses
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from circuit_tools.gerber import load_layer, rasterize
from read_epc90133_geometry import BOARD, GERBERS, LAYERS, PITCH, PREFIX, derive

MIN_DRILL, MIN_PITCH = 0.198, 0.52
RING, CLEARANCE = 0.125, 0.2


class EditRefused(ValueError):
    pass


def paste_layers():
    return {e: rasterize(load_layer(GERBERS / f"{PREFIX}Gerbers.{e}"), BOARD, PITCH) for e in ("GTP", "GBP")}


def disk(shape, i, j, r_px):
    yy, xx = np.ogrid[:shape[0], :shape[1]]
    return (yy - i) ** 2 + (xx - j) ** 2 <= r_px ** 2


def net_at(b, e, i, j):
    lab = int(b.labels[e][i, j])
    return b.net_name.get(b.find((e, lab)), "other") if lab else None


def add_via(b, x, y, net, drill=MIN_DRILL, paste=None):
    """New board namespace with the via added, and an edit record; raises EditRefused when a rule fails."""
    if drill < MIN_DRILL - 1e-6:
        raise EditRefused(f"R1: drill {drill} mm below {MIN_DRILL} mm")
    near = min(np.hypot(h.x - x, h.y - y) for h in b.holes)
    if near < MIN_PITCH:
        raise EditRefused(f"R2: {near:.3f} mm to the nearest hole, below {MIN_PITCH} mm")
    pad_r, anti_r = drill / 2 + RING, drill / 2 + CLEARANCE
    i, j = b.pixel(x, y)
    paste = paste or paste_layers()
    for e, ras in paste.items():
        if ras.grid[disk(ras.grid.shape, i, j, (pad_r + CLEARANCE) / PITCH)].any():
            raise EditRefused(f"R3: component pad (paste on {e}) within {pad_r + CLEARANCE:.3f} mm")
    grids = {e: dataclasses.replace(r, grid=r.grid.copy()) for e, r in b.grids.items()}
    bonded, cut = [], []
    for e in LAYERS:
        g = grids[e].grid
        lab = b.labels[e]
        around = disk(g.shape, i, j, anti_r / PITCH)
        ids = {int(v) for v in np.unique(lab[around]) if v}
        nets = {net_at(b, e, *np.argwhere(lab == k)[0]): k for k in ids}
        here = net_at(b, e, i, j)
        if here == net:
            others = [k for n_, k in nets.items() if n_ != net]
            if others:
                raise EditRefused(f"R5: on {e} another net's copper is within the clearance of a {net} pad")
            g[disk(g.shape, i, j, pad_r / PITCH)] = True
            bonded.append(e)
        elif ids:
            power = sorted({n_ for n_ in nets if n_ in ("VIN", "SW")})
            if power:
                raise EditRefused(f"R6: an antipad on {e} would cut {power} copper")
            for k in ids:
                region = (lab == k)
                before = ndimage.label(region)[1]
                after = ndimage.label(region & ~around)[1]
                if after > before:
                    raise EditRefused(f"R5: the antipad on {e} would split a copper island")
            g[around] = False
            cut.append(e)
    if len(bonded) < 2:
        raise EditRefused(f"R4: the via bonds to {net} on {len(bonded)} layer(s)")
    hole = dataclasses.replace(next(h for h in b.holes if h.plated), x=x, y=y, diameter=drill)
    new = derive(grids, list(b.holes) + [hole])
    if not new.distinct:
        raise EditRefused("R5: probe nets VIN/SW/GND merged")
    row = next(v for v in new.via_rows if abs(v["x"] - x) < 1e-9 and abs(v["y"] - y) < 1e-9)
    wrong = [e for e, lab in row["islands"] if new.net_name.get(new.find((e, lab)), "other") != net]
    if wrong:
        raise EditRefused(f"R5: the new via bonds to another net on {wrong}")
    return new, {"edit": "add_via", "x_mm": x, "y_mm": y, "net": net, "drill_mm": drill,
                 "pad_mm": 2 * pad_r, "antipad_mm": 2 * anti_r, "bonded_layers": row["layers"], "antipad_layers": cut}


def apply(b, edits, paste=None):
    """Apply a list of edits ({"edit": "add_via", "x_mm", "y_mm", "net", "drill_mm"?}) in order."""
    paste = paste or paste_layers()
    records = []
    for ed in edits:
        if ed["edit"] != "add_via":
            raise EditRefused(f"unknown edit {ed['edit']!r}")
        b, rec = add_via(b, ed["x_mm"], ed["y_mm"], ed["net"], ed.get("drill_mm", MIN_DRILL), paste)
        records.append(rec)
    return b, records
