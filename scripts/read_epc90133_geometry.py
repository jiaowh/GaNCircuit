#!/usr/bin/env python3
"""Read the EPC90133 (B5253 Rev 2.0) Gerbers into inspectable geometry and copper nets.

Uses circuit_tools.gerber to rasterize the eight copper layers (and the top
silkscreen for rendering) at a fixed pitch, reads the drill file, and builds
copper connectivity: connected copper on each layer, joined through every
plated hole at the layers where copper surrounds the hole's rim. Named probe points,
read from the rendered board, identify nets.

Consistency checks fixed before the first run:
* VIN, GND and SW must be three distinct nets (a merge means a reader or via error);
* each probe must land on copper;
* both FET footprints must connect to VIN/SW (Q1) and SW/GND (Q2) through their pads.
  This third check was declared but missing from the first run's report; it is
  implemented, with the footprint dimensions, in scripts/epc90133_power_loop.py
  (29 September 2026).

Outputs: results/gan/epc90133-geometry.json (layer areas, drills, nets touched
by the power stage) and PNG renders in results/gan/epc90133-geometry/ for
inspection. The Gerbers themselves stay in the git-ignored vendor directory.
"""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from circuit_tools.gerber import load_layer, parse_excellon, rasterize

PREFIX = "EPC90133_B5253_Rev2_0_"
ZIP_SHA = "76189d4293607795fc195f6766171b588e269a4ecb1c5d3e3da2be4c8525acd1"
# Edited boards (7 October 2026; scripts/epc90133_board_export.py): when EXPORT_ENV names a directory, every
# script that imports GERBERS reads that KiCad export instead, in EPC's frame and with EPC's file names. Set it only
# in the child processes the export driver starts. load_board then checks the export's manifest, not EPC's zip.
EXPORT_ENV = "EPC90133_GERBER_EXPORT"
EXPORT_DIR = os.environ.get(EXPORT_ENV)
GERBERS = Path(EXPORT_DIR) if EXPORT_DIR else ROOT / "vendor/epc/epc90133/gerbers/Gerbers"


def geometry_source():
    """Identity of the geometry being read: EPC's Gerber zip, or a KiCad export with its manifest hash."""
    if not EXPORT_DIR:
        return {"kind": "epc_gerbers", "zip_sha256": ZIP_SHA}
    man = Path(EXPORT_DIR) / "export.json"
    m = json.loads(man.read_text(encoding="utf-8"))
    bad = [f for f, h in m["files"].items() if hashlib.sha256((Path(EXPORT_DIR) / f).read_bytes()).hexdigest() != h]
    if bad:
        raise SystemExit(f"export files differ from their manifest: {bad}")
    return {"kind": "kicad_export", "dir": str(Path(EXPORT_DIR)), "manifest_sha256": hashlib.sha256(man.read_bytes()).hexdigest(),
            "case": m.get("case"), "board_sha256": m.get("board_sha256")}
LAYERS = ("GTL", "G1", "G2", "G3", "G4", "G5", "G6", "GBL")  # physical order, top to bottom
BOARD = (0.0, 0.0, 50.8, 50.8)  # mm, from the GM1 outline
PITCH = 0.0254  # mm (1 mil)
# Probe points (mm) read from the top-layer render: labelled test points and pour regions.
PROBES = {
    "VIN (TP2 pad)": ("GTL", 18.3, 41.7),
    "GND (TP1 pad)": ("GTL", 26.4, 41.7),
    "SW (pour right of L1 label)": ("GTL", 43.0, 27.9),
}
POWER_STAGE = (14.0, 20.0, 34.0, 40.0)  # mm window holding Q1, Q2, Ci1-Ci7 and U80


def load_board():
    """Rasterized layers, drills and copper connectivity, with VIN/GND/SW named from the probes."""
    if EXPORT_DIR:
        geometry_source()  # manifest check of the KiCad export
    else:
        zip_path = ROOT / "vendor/epc/epc90133/EPC90133 Development Board Gerbers.zip"
        if hashlib.sha256(zip_path.read_bytes()).hexdigest() != ZIP_SHA:
            raise SystemExit("Gerber zip checksum differs from devices/epc/epc90133-sources.json")
    grids = {e: rasterize(load_layer(GERBERS / f"{PREFIX}Gerbers.{e}"), BOARD, PITCH) for e in LAYERS + ("GTO",)}
    holes = parse_excellon((GERBERS / f"{PREFIX}NC Drill.TXT").read_text(encoding="latin-1"))
    return derive(grids, holes)


def derive(grids, holes):
    """Connectivity, via bonding and net names from rasterized layers and drills (split out of load_board on
    5 October 2026 so that edited geometry, scripts/epc90133_board_edit.py, is derived by the same code)."""
    labels, counts = {}, {}
    for e in LAYERS:
        labels[e], counts[e] = ndimage.label(grids[e].grid)
    parent = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        parent[find(a)] = find(b)

    def pixel(x, y):
        return round((y - BOARD[1]) / PITCH), round((x - BOARD[0]) / PITCH)

    via_rows = []
    for h in holes:
        if not h.plated:
            continue
        # Sample a ring just outside the drill: copper there means the barrel bonds to that layer.
        # (Pads cover the hole centre in Gerbers; clearances appear as a copper-free ring.)
        r = h.diameter / 2 + 2 * PITCH
        ring = [(h.x + r * np.cos(a), h.y + r * np.sin(a)) for a in np.linspace(0, 2 * np.pi, 16, endpoint=False)]
        touched = []
        for e in LAYERS:
            ids = {int(labels[e][pixel(x, y)]) for x, y in ring}
            ids.discard(0)
            if len(ids) > 1:
                raise SystemExit(f"hole at ({h.x:.3f}, {h.y:.3f}) touches {len(ids)} islands on {e}")
            if ids:
                touched.append((e, ids.pop()))
        for (e1, i1), (e2, i2) in zip(touched, touched[1:]):
            union((e1, i1), (e2, i2))
        via_rows.append({"x": h.x, "y": h.y, "d": h.diameter, "layers": [e for e, _ in touched], "islands": touched})

    probes = {}
    for name, (e, x, y) in PROBES.items():
        lab = int(labels[e][pixel(x, y)])
        probes[name] = {"layer": e, "x": x, "y": y, "on_copper": lab != 0, "net": find((e, lab)) if lab else None}
    nets = [p["net"] for p in probes.values()]
    distinct = len(set(nets)) == len(nets) and None not in nets
    net_name = {p["net"]: name.split()[0] for name, p in probes.items() if p["net"] is not None}

    def net_of(e, x, y):
        lab = int(labels[e][pixel(x, y)])
        return net_name.get(find((e, lab)), "other") if lab else "none"

    return SimpleNamespace(grids=grids, holes=holes, labels=labels, counts=counts, find=find, pixel=pixel,
                           via_rows=via_rows, probes=probes, distinct=distinct, net_name=net_name, net_of=net_of)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-geometry.json")
    ap.add_argument("--renders", type=Path, default=ROOT / "results/gan/epc90133-geometry")
    args = ap.parse_args()
    b = load_board()
    grids, holes, labels, counts, find, pixel = b.grids, b.holes, b.labels, b.counts, b.find, b.pixel
    via_rows, probes, distinct, net_name, net_of = b.via_rows, b.probes, b.distinct, b.net_name, b.net_of

    # Layer coverage of each named net inside the power-stage window.
    x0, y0, x1, y1 = POWER_STAGE
    i0, j0 = pixel(x0, y0)
    i1, j1 = pixel(x1, y1)
    coverage = {}
    for e in LAYERS:
        sub = labels[e][i0:i1, j0:j1]
        roots = collections.Counter()
        for lab, n in zip(*np.unique(sub[sub > 0], return_counts=True)):
            roots[net_name.get(find((e, int(lab))), "other")] += int(n)
        coverage[e] = {k: round(v * PITCH ** 2, 2) for k, v in roots.items()}
    stage_vias = [v for v in via_rows if x0 <= v["x"] <= x1 and y0 <= v["y"] <= y1]
    for v in stage_vias:
        v["net"] = net_of(v["layers"][0], v["x"], v["y"]) if v["layers"] else "unconnected"
    via_summary = collections.Counter((v["net"], round(v["d"], 3), tuple(v["layers"])) for v in stage_vias)

    args.renders.mkdir(parents=True, exist_ok=True)
    colours = {"VIN": (200, 60, 60), "GND": (60, 110, 200), "SW": (60, 160, 60), "other": (190, 160, 110)}
    for e in LAYERS[:3] + ("GBL",):
        img = np.full(labels[e].shape + (3,), 255, np.uint8)
        roots = {lab: net_name.get(find((e, lab)), "other") for lab in range(1, counts[e] + 1)}
        lut = np.zeros((counts[e] + 1, 3), np.uint8) + 255
        for lab, n in roots.items():
            lut[lab] = colours[n]
        img = lut[labels[e]]
        if e == "GTL":
            img[grids["GTO"].grid] = (0, 0, 0)
        for v in via_rows:
            i, j = pixel(v["x"], v["y"])
            rr = max(1, round(v["d"] / 2 / PITCH))
            img[i - rr:i + rr, j - rr:j + rr] = (0, 0, 0)
        Image.fromarray(img[::-1]).save(args.renders / f"{e}-nets.png")
        Image.fromarray(img[i0:i1, j0:j1][::-1]).resize((1000, 1000), Image.NEAREST).save(args.renders / f"{e}-power-stage.png")

    report = {
        "schema": "epc90133-geometry/1",
        "source": {"zip_sha256": ZIP_SHA, "board": "B5253 Rev 2.0", "pitch_mm": PITCH, "board_mm": BOARD},
        "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "layers": {e: {"copper_area_mm2": round(grids[e].area_mm2(), 1), "islands": counts[e]} for e in LAYERS},
        "drills": {"plated": sum(h.plated for h in holes), "non_plated": sum(not h.plated for h in holes),
                   "by_diameter_mm": {f"{d:.3f}": n for d, n in sorted(collections.Counter(round(h.diameter, 3) for h in holes).items())}},
        "probes": {k: {kk: vv for kk, vv in v.items() if kk != "net"} | {"net_id": str(v["net"])} for k, v in probes.items()},
        "checks": {"VIN_GND_SW_distinct": distinct, "all_probes_on_copper": all(p["on_copper"] for p in probes.values())},
        "power_stage_window_mm": POWER_STAGE,
        "power_stage_copper_mm2_by_net": coverage,
        "power_stage_vias": [{"net": n, "diameter_mm": d, "layers": list(l), "count": c}
                             for (n, d, l), c in sorted(via_summary.items(), key=lambda kv: -kv[1])],
        "renders": str(args.renders.relative_to(ROOT)),
    }
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: report[k] for k in ("layers", "checks", "power_stage_copper_mm2_by_net")}, indent=1))
    for row in report["power_stage_vias"][:12]:
        print(row)


if __name__ == "__main__":
    main()
