#!/usr/bin/env python3
"""Track R step 1: EPC90133 (B5253 Rev 2.0) copper reconstructed as a KiCad 10 board, checked by a round trip.

Plan: plans/layout-round-2-plan.md, "Parallel track R". This step writes copper only (no parts, nets, vias or
zones; those are steps 2-4). Each copper layer's Gerber primitives are applied in drawing order (dark adds, clear
removes) with shapely, giving hole-free filled polygons (a polygon with holes is split along vertical lines through
its holes, because KiCad graphic polygons have no holes). They are written as filled graphic polygons (stroke 0) on
F.Cu, In1.Cu-In6.Cu and B.Cu, with the GM1 outline on Edge.Cuts. Board coordinates map as
x_kicad = x + 100, y_kicad = 150 - y (mm), which keeps the board on the page.

Round trip (declared 6 October 2026 before the first run): kicad-cli exports Gerbers of the eight copper layers and
Edge.Cuts; our reader (circuit_tools.gerber) maps them back and rasterizes them at 0.0254 mm over the board window,
as it rasterizes EPC's originals. Per copper layer:
  R1 XOR area (original vs round trip) <= 0.1 % of the original copper area;
  R2 largest connected (8-neighbour) mismatch region <= 0.005 mm^2 (about 8 pixels);
and R3 the exported outline's bounds equal GM1's within 0.001 mm. Arcs are already polygons (5 degree steps) in our
reader, so the reconstruction inherits that approximation; the round trip tests the conversion, not the reader.

Terms: the board file is a derivative of EPC's layout. The repository is public, so the board file and exported
Gerbers stay in the git-ignored vendor/epc/epc90133/reconstruction/; only this script and the summary report
(areas and mismatch numbers, no geometry) are committed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid

import numpy as np
from scipy import ndimage
from shapely import ops
from shapely.geometry import LineString, MultiLineString, Polygon, box
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from circuit_tools.gerber import load_layer, rasterize
from read_epc90133_geometry import BOARD, GERBERS, LAYERS, PITCH, PREFIX, ZIP_SHA

OUT = ROOT / "vendor/epc/epc90133/reconstruction"
KICAD_CLI = Path.home() / "AppData/Local/Programs/KiCad/10.0/bin/kicad-cli.exe"
KICAD_LAYER = dict(zip(LAYERS, ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "In5.Cu", "In6.Cu", "B.Cu")))
DX, DY = 100.0, 150.0
R1_XOR_FRACTION, R2_BLOB_MM2, R3_OUTLINE_MM = 0.001, 0.005, 0.001


def to_kicad(x, y):
    return x + DX, DY - y


def from_kicad_gerber(x, y):
    # KiCad writes Gerber Y = -y_kicad (absolute coordinates, no origin offset)
    return x - DX, y + DY


def layer_geometry(layer):
    """Shapely geometry of a Gerber layer, primitives applied in order; consecutive same-polarity runs are merged."""
    geom, run, run_pol = Polygon(), [], None

    def flush():
        nonlocal geom
        if run:
            u = ops.unary_union(run)
            geom = geom.union(u) if run_pol else geom.difference(u)

    for p in layer.primitives:
        if p.kind == "poly":
            shape = make_valid(Polygon(p.data[0])) if len(p.data[0]) >= 3 else Polygon()
        else:
            p0, p1, w = p.data
            shape = (LineString([p0, p1]) if p0 != p1 else LineString([p0, (p0[0] + 1e-9, p0[1])])).buffer(w / 2)
        if p.polarity != run_pol:
            flush()
            run, run_pol = [], p.polarity
        run.append(shape)
    flush()
    return geom


def polygons(geom):
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    return [g for part in getattr(geom, "geoms", []) for g in polygons(part)]


def split_holes(poly):
    """Hole-free polygons covering poly: split along vertical lines through every hole at once, repeated (bounded)
    for any piece that still has a hole. Run 1 split one hole per recursion level and exceeded Python's recursion
    limit on the inner planes (hundreds of holes); kept as a failed run, no report written."""
    todo, done = [poly], []
    for _ in range(20):
        nxt = []
        for p in todo:
            if not p.interiors:
                done.append(p)
                continue
            x0, y0, x1, y1 = p.bounds
            xs = sorted({round(Polygon(h).representative_point().x, 9) for h in p.interiors})
            cutter = MultiLineString([[(x, y0 - 1), (x, y1 + 1)] for x in xs])
            nxt += [q for g in ops.split(p, cutter).geoms for q in polygons(g)]
        todo = nxt
        if not todo:
            return done
    raise RuntimeError(f"holes remain after 20 splitting passes ({len(todo)} pieces)")


def poly_sexpr(points, layer):
    pts = " ".join(f"(xy {x:.6f} {y:.6f})" for x, y in (to_kicad(*p) for p in points))
    return (f'\t(gr_poly\n\t\t(pts {pts})\n\t\t(stroke (width 0) (type solid))\n\t\t(fill yes)\n'
            f'\t\t(layer "{layer}")\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n')


def line_sexpr(p0, p1, layer, width=0.05):
    (x0, y0), (x1, y1) = to_kicad(*p0), to_kicad(*p1)
    return (f'\t(gr_line (start {x0:.6f} {y0:.6f}) (end {x1:.6f} {y1:.6f}) (stroke (width {width}) (type solid))'
            f' (layer "Edge.Cuts") (uuid "{uuid.uuid4()}"))\n')


HEADER = """(kicad_pcb
\t(version 20241229)
\t(generator "epc90133_reconstruct")
\t(generator_version "9.0")
\t(general (thickness 1.6) (legacy_teardrops no))
\t(paper "A4")
\t(layers
\t\t(0 "F.Cu" signal) (4 "In1.Cu" signal) (6 "In2.Cu" signal) (8 "In3.Cu" signal) (10 "In4.Cu" signal)
\t\t(12 "In5.Cu" signal) (14 "In6.Cu" signal) (2 "B.Cu" signal)
\t\t(13 "F.Paste" user) (15 "B.Paste" user) (5 "F.SilkS" user "F.Silkscreen") (7 "B.SilkS" user "B.Silkscreen")
\t\t(1 "F.Mask" user) (3 "B.Mask" user) (25 "Edge.Cuts" user) (31 "F.CrtYd" user "F.Courtyard")
\t\t(29 "B.CrtYd" user "B.Courtyard") (35 "F.Fab" user) (33 "B.Fab" user)
\t)
\t(setup (pad_to_mask_clearance 0))
\t(net 0 "")
"""


def build(board_path):
    report = {}
    body = []
    for e in LAYERS:
        geom = layer_geometry(load_layer(GERBERS / f"{PREFIX}Gerbers.{e}")).intersection(box(*BOARD).buffer(1.0))
        pieces = [q for p in polygons(geom) for q in split_holes(p)]
        report[e] = {"kicad_layer": KICAD_LAYER[e], "area_mm2": geom.area, "polygons": len(polygons(geom)),
                     "hole_free_pieces": len(pieces), "piece_area_mm2": sum(q.area for q in pieces)}
        body += [poly_sexpr(list(q.exterior.coords)[:-1], KICAD_LAYER[e]) for q in pieces]
    outline = load_layer(GERBERS / f"{PREFIX}Gerbers.GM1")
    body += [line_sexpr(p.data[0], p.data[1], "Edge.Cuts") for p in outline.primitives if p.kind == "line"]
    board_path.write_text(HEADER + "".join(body) + ")\n", encoding="utf-8")
    return report


def round_trip(board_path, report):
    gdir = board_path.parent / "roundtrip-gerbers"
    gdir.mkdir(exist_ok=True)
    layers = ",".join(list(KICAD_LAYER.values()) + ["Edge.Cuts"])
    proc = subprocess.run([str(KICAD_CLI), "pcb", "export", "gerbers", "--layers", layers, "--no-protel-ext",
                           "-o", str(gdir), str(board_path)], capture_output=True, text=True)
    if proc.returncode:
        raise SystemExit(f"kicad-cli failed ({proc.returncode}): {proc.stderr[-800:]}")
    exported = {p.stem.split("-")[-1].replace("_", "."): p for p in gdir.glob("*.gbr")}
    checks = {}
    for e in LAYERS:
        name = KICAD_LAYER[e]
        orig = rasterize(load_layer(GERBERS / f"{PREFIX}Gerbers.{e}"), BOARD, PITCH).grid
        rt_layer = load_layer(exported[name])
        for p in rt_layer.primitives:
            if p.kind == "poly":
                p.data = ([from_kicad_gerber(*q) for q in p.data[0]],) + tuple(p.data[1:])
            else:
                p.data = (from_kicad_gerber(*p.data[0]), from_kicad_gerber(*p.data[1]), p.data[2])
        rt = rasterize(rt_layer, BOARD, PITCH).grid
        xor = orig ^ rt
        lab, n = ndimage.label(xor, structure=np.ones((3, 3)))
        blob = (np.bincount(lab.ravel())[1:].max() if n else 0) * PITCH ** 2
        area = orig.sum() * PITCH ** 2
        checks[e] = {"original_area_mm2": area, "roundtrip_area_mm2": rt.sum() * PITCH ** 2,
                     "xor_area_mm2": xor.sum() * PITCH ** 2, "xor_fraction": xor.sum() / max(orig.sum(), 1),
                     "largest_mismatch_mm2": blob, "mismatch_regions": int(n)}
        checks[e]["R1"] = checks[e]["xor_fraction"] <= R1_XOR_FRACTION
        checks[e]["R2"] = blob <= R2_BLOB_MM2
    edge = load_layer(exported["Edge.Cuts"])
    pts = [from_kicad_gerber(*q) for p in edge.primitives for q in (p.data[:2] if p.kind == "line" else p.data[0])]
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    gm1 = load_layer(GERBERS / f"{PREFIX}Gerbers.GM1")
    g = [q for p in gm1.primitives if p.kind == "line" for q in p.data[:2]]
    ob = (min(q[0] for q in g), min(q[1] for q in g), max(q[0] for q in g), max(q[1] for q in g))
    rb = (min(xs), min(ys), max(xs), max(ys))
    r3 = max(abs(a - b) for a, b in zip(ob, rb)) <= R3_OUTLINE_MM
    return checks, {"original_bounds": ob, "roundtrip_bounds": rb, "R3": r3}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-reconstruct-copper.json")
    args = ap.parse_args()
    zip_path = ROOT / "vendor/epc/epc90133/EPC90133 Development Board Gerbers.zip"
    if hashlib.sha256(zip_path.read_bytes()).hexdigest() != ZIP_SHA:
        raise SystemExit("Gerber zip checksum differs from devices/epc/epc90133-sources.json")
    OUT.mkdir(parents=True, exist_ok=True)
    board = OUT / "epc90133-copper.kicad_pcb"
    report = build(board)
    checks, outline = round_trip(board, report)
    passed = all(c["R1"] and c["R2"] for c in checks.values()) and outline["R3"]
    out = {"schema": "epc90133-reconstruct/1", "step": "track R step 1: copper only", "passed": passed,
           "criteria": {"R1_xor_fraction_max": R1_XOR_FRACTION, "R2_largest_mismatch_mm2_max": R2_BLOB_MM2,
                        "R3_outline_mm_max": R3_OUTLINE_MM, "raster_pitch_mm": PITCH},
           "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "gerber_zip_sha256": ZIP_SHA,
           "kicad_cli": subprocess.run([str(KICAD_CLI), "version"], capture_output=True, text=True).stdout.strip(),
           "board_file": "vendor/epc/epc90133/reconstruction/epc90133-copper.kicad_pcb (git-ignored; EPC derivative)",
           "layers": {e: {**report[e], **checks[e]} for e in LAYERS}, "outline": outline}
    args.output.write_text(json.dumps(out, indent=1, default=float) + "\n", encoding="utf-8")
    for e in LAYERS:
        c = out["layers"][e]
        print(f"{e:4s} {c['kicad_layer']:7s} pieces {c['hole_free_pieces']:5d}  area {c['original_area_mm2']:8.2f} mm2  "
              f"xor {c['xor_fraction'] * 100:7.4f} %  blob {c['largest_mismatch_mm2']:.4f} mm2  R1 {c['R1']} R2 {c['R2']}")
    print("outline", outline, "PASSED" if passed else "FAILED")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
