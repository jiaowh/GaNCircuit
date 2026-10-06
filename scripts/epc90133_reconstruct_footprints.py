#!/usr/bin/env python3
"""Track R step 2b: EPC90133 footprints built from the board's own pads, placed in the KiCad board.

Plan: plans/layout-round-2-plan.md, "Parallel track R", step 2 (footprints) with step 3's pad nets. Inputs: step 1's
copper conversion (scripts/epc90133_reconstruct.py), step 2a's sides and pad-to-opening matches
(scripts/epc90133_reconstruct_parts.py, run 3), EPC's netlist from the layout PDF bookmarks, and the drill file.
Deviation from the plan, recorded: footprints come from the board's own mask, paste and copper rather than from
KiCad/EPC library footprints, because several parts have no library footprint and EPC's land patterns may differ;
library footprints remain a cross-check for later edits.

Construction (declared 6 October 2026 before the first run). For each part on its side s (F or B):
  - footprint origin at the mean of its pads' mask-opening centroids, rotation 0, layer F.Cu or B.Cu;
  - each pad: copper = its mask opening intersected with step 1's copper on s's outer layer (so pads add no
    copper), written as a custom pad (anchor circle 0.05 mm at a point inside the shape), net from EPC's netlist;
    the pad does not open mask or paste itself;
  - the pad's mask opening is a footprint polygon on F.Mask/B.Mask; paste openings on s that intersect one of the
    part's pad openings are footprint polygons on F.Paste/B.Paste;
  - a pad whose opening contains a plated drill becomes a through-hole pad (see revision 2 below); a part on
    'mechanical' holes
    (step 2a) gets a non-plated hole of the drill's diameter;
  - mask and paste openings not used by any footprint stay as board-level graphic polygons on their layer.
Copper stays step 1's graphic polygons; zones, tracks and vias are steps 3-4.

Round trip (kicad-cli Gerber export, read back, compared exactly as in step 1, revision 2):
  F1 F.Mask and B.Mask: symmetric difference <= 0.01 % of the original opening area, largest piece <= 0.001 mm^2;
  F2 F.Paste and B.Paste: the same criteria;
  F3 the eight copper layers: the same criteria (pads must add no copper);
  F4 every named pad has non-empty copper, and its net equals EPC's netlist net (unnamed or netless pads: no net);
  F5 every through-hole or mechanical pad of step 2a's rule-4 parts contains exactly one drill.
Reported, not checked: KiCad DRC counts (graphic copper carries no connectivity until step 3, so unconnected-item
counts are expected), and the openings left at board level.

Run 1 (the declared version) crashed after writing the board: our Gerber reader could not parse KiCad's
parameterised aperture macros (the $n substitution sorted integer keys by len()). Fixed in
src/circuit_tools/gerber.py with a regression test; EPC's files never pass macro parameters, so their reading is
unchanged. No report was written.

Revision 2 (declared 6 October 2026 after run 1, before run 2), two corrections intended before run 1 but lost to a
failed patch: a through-hole pad is a circle exactly the drill's size (KiCad would copy a custom shape to both
outer layers and could add copper; EPC's copper already covers every plated hole position), flashed only on the
outer layers (remove_unused_layers with keep_end_layers), with the pad's net; and the mechanical footprints use a
valid attribute (through_hole exclude_from_pos_files exclude_from_bom). Checks F1-F5 are unchanged.

Terms: the board file is an EPC derivative and stays in the git-ignored vendor/epc/epc90133/reconstruction/.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid

import shapely
from shapely.geometry import Point
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from circuit_tools.gerber import load_layer, parse_excellon
from read_epc90133_geometry import BOARD, GERBERS, LAYERS, PREFIX, ZIP_SHA
from epc90133_reconstruct import (HEADER, KICAD_CLI, KICAD_LAYER, OUT, box, layer_geometry, line_sexpr, mapped_layer,
                                  polygons, split_holes, to_kicad)
import epc90133_reconstruct_parts as P

TOL_FRACTION, TOL_PIECE_MM2 = 1e-4, 0.001
SIDE = {"top": ("F", "GTL", "GTS", "GTP"), "bot": ("B", "GBL", "GBS", "GBP")}


def uid():
    return str(uuid.uuid4())


def pts(points, origin):
    ox, oy = to_kicad(*origin)
    return " ".join(f"(xy {x - ox:.6f} {y - oy:.6f})" for x, y in (to_kicad(*q) for q in points))


def board_poly(poly, layer):
    return "".join(f'\t(gr_poly (pts {pts(list(q.exterior.coords)[:-1], (0.0, 0.0))}) (stroke (width 0) (type solid))'
                   f' (fill yes) (layer "{layer}") (uuid "{uid()}"))\n' for q in split_holes(poly))


def fp_poly(poly, layer, origin):
    return "".join(f'\t\t(fp_poly (pts {pts(list(q.exterior.coords)[:-1], origin)}) (stroke (width 0) (type solid))'
                   f' (fill yes) (layer "{layer}") (uuid "{uid()}"))\n' for q in split_holes(poly))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-reconstruct-footprints.json")
    args = ap.parse_args()
    if hashlib.sha256((ROOT / "vendor/epc/epc90133/EPC90133 Development Board Gerbers.zip").read_bytes()).hexdigest() \
            != ZIP_SHA:
        raise SystemExit("Gerber zip checksum differs")
    sides = json.loads((OUT / "parts-sides.json").read_text(encoding="utf-8"))
    nets = sides["nets"]
    padnet = {p: n for n, pl in nets.items() for p in pl}
    netid = {n: i for i, n in enumerate(sorted(nets), start=1)}
    pins, _, pads, _ = P.read_pdf()
    copper = {e: layer_geometry(load_layer(GERBERS / f"{PREFIX}Gerbers.{e}")).intersection(box(*BOARD).buffer(1.0))
              for e in LAYERS}
    mask = {s: P.Openings(SIDE[s][2]) for s in SIDE}
    paste = {s: P.Openings(SIDE[s][3]) for s in SIDE}
    holes = parse_excellon((GERBERS / f"{PREFIX}NC Drill.TXT").read_text(encoding="latin-1"))
    hole_tree = STRtree([Point(h.x, h.y) for h in holes])
    used_mask = {s: set() for s in SIDE}
    used_paste = {s: set() for s in SIDE}
    fps, f4_fail, f5_fail, pad_count = [], [], [], 0
    mechanical = set(json.loads((ROOT / "results/gan/epc90133-reconstruct-sides.json").read_text())["mechanical"])
    for ref, info in sorted(sides["parts"].items()):
        s = info["side"]
        L, cu = SIDE[s][0], SIDE[s][1]
        if ref in mechanical:
            pp = pads[ref]
            body = []
            for pin, tag in pp.items():
                inside = [holes[int(i)] for i in hole_tree.query(tag) if tag.contains(Point(holes[int(i)].x, holes[int(i)].y))
                          and holes[int(i)].diameter >= 1.5]
                if len(inside) != 1:
                    f5_fail.append(f"{ref}-{pin}")
                    continue
                h = inside[0]
                origin = (h.x, h.y)
                body.append(f'\t\t(pad "" np_thru_hole circle (at 0 0) (size {h.diameter:.4f} {h.diameter:.4f}) '
                            f'(drill {h.diameter:.4f}) (layers "*.Cu" "*.Mask") (uuid "{uid()}"))\n')
            if body:
                x, y = to_kicad(*origin)
                fps.append(f'\t(footprint "EPC90133:{ref}" (layer "{L}.Cu") (uuid "{uid()}") (at {x:.6f} {y:.6f})\n'
                           f'\t\t(property "Reference" "{ref}" (at 0 0) (layer "{L}.Fab") (uuid "{uid()}") '
                           f'(effects (font (size 0.5 0.5) (thickness 0.08))))\n\t\t(attr through_hole exclude_from_pos_files exclude_from_bom)\n'
                           + "".join(body) + "\t)\n")
            continue
        assign = mask[s].assign(pads[ref])
        openings = {pin: mask[s].g[i] for pin, (_, i) in assign.items()}
        cents = [g.centroid for g in openings.values()]
        origin = (sum(c.x for c in cents) / len(cents), sum(c.y for c in cents) / len(cents))
        body, th = [], False
        for pin, (_, i) in assign.items():
            used_mask[s].add(i)
        for g in {i: mask[s].g[i] for _, i in assign.values()}.values():
            body.append(fp_poly(g, f"{L}.Mask", origin))
        part_area = shapely.union_all(list(openings.values()))
        for k in paste[s].tree.query(part_area):
            k = int(k)
            if paste[s].g[k].intersects(part_area) and k not in used_paste[s]:
                used_paste[s].add(k)
                body.append(fp_poly(paste[s].g[k], f"{L}.Paste", origin))
        for pin, g in openings.items():
            pad_count += 1
            cu_shape = g.intersection(copper[cu])
            net = padnet.get(f"{ref}-{pin}")
            if cu_shape.is_empty:
                if pin:
                    f4_fail.append(f"{ref}-{pin}: no copper")
                continue
            parts = [q for q in polygons(cu_shape) if q.area > 1e-6]
            anchor = max(parts, key=lambda q: q.area).representative_point()
            drill = [holes[int(j)] for j in hole_tree.query(g) if g.contains(Point(holes[int(j)].x, holes[int(j)].y))
                     and holes[int(j)].plated and holes[int(j)].diameter > 0.3]
            prims = "".join(f'(gr_poly (pts {pts(list(q.exterior.coords)[:-1], (anchor.x, anchor.y))}) (width 0) (fill yes))'
                            for p_ in parts for q in split_holes(p_))
            ax, ay = to_kicad(anchor.x, anchor.y)
            ox, oy = to_kicad(*origin)
            nets_s = f' (net {netid[net]} "{net}")' if net else ""
            if len(drill) == 1:
                th = True
                d = drill[0]
                dx, dy = to_kicad(d.x, d.y)
                body.append(f'\t\t(pad "{pin}" thru_hole circle (at {dx - ox:.6f} {dy - oy:.6f}) '
                            f'(size {d.diameter:.4f} {d.diameter:.4f}) (drill {d.diameter:.4f}) (layers "*.Cu") '
                            f'(remove_unused_layers yes) (keep_end_layers yes){nets_s} (uuid "{uid()}"))\n')
            else:
                if len(drill) > 1:
                    f5_fail.append(f"{ref}-{pin}: {len(drill)} drills")
                body.append(f'\t\t(pad "{pin}" smd custom (at {ax - ox:.6f} {ay - oy:.6f}) (size 0.05 0.05) '
                            f'(layers "{L}.Cu"){nets_s} (options (clearance outline) (anchor circle)) '
                            f'(primitives {prims}) (uuid "{uid()}"))\n')
        x, y = to_kicad(*origin)
        fps.append(f'\t(footprint "EPC90133:{ref}" (layer "{L}.Cu") (uuid "{uid()}") (at {x:.6f} {y:.6f})\n'
                   f'\t\t(property "Reference" "{ref}" (at 0 0) (layer "{L}.Fab") (uuid "{uid()}") '
                   f'(effects (font (size 0.5 0.5) (thickness 0.08))))\n'
                   f'\t\t(attr {"through_hole" if th else "smd"})\n' + "".join(body) + "\t)\n")
    # board-level leftovers
    extra = []
    for s, (L, _, _, _) in SIDE.items():
        extra += [board_poly(g, f"{L}.Mask") for i, g in enumerate(mask[s].g) if i not in used_mask[s]]
        extra += [board_poly(g, f"{L}.Paste") for i, g in enumerate(paste[s].g) if i not in used_paste[s]]
    leftovers = {s: {"mask": len(mask[s].g) - len(used_mask[s]), "paste": len(paste[s].g) - len(used_paste[s])}
                 for s in SIDE}
    cu_body = []
    for e in LAYERS:
        cu_body += [board_poly(q, KICAD_LAYER[e]) for q in polygons(copper[e])]
    outline = load_layer(GERBERS / f"{PREFIX}Gerbers.GM1")
    edge = [line_sexpr(p.data[0], p.data[1], "Edge.Cuts") for p in outline.primitives if p.kind == "line"]
    header = HEADER.replace('\t(net 0 "")\n', '\t(net 0 "")\n' + "".join(f'\t(net {i} "{n}")\n'
                                                                       for n, i in sorted(netid.items(), key=lambda x: x[1])))
    board = OUT / "epc90133-footprints.kicad_pcb"
    board.write_text(header + "".join(cu_body) + "".join(extra) + "".join(fps) + "".join(edge) + ")\n",
                     encoding="utf-8")

    # round trip
    gdir = OUT / "footprints-gerbers"
    gdir.mkdir(exist_ok=True)
    layers = list(KICAD_LAYER.values()) + ["F.Mask", "B.Mask", "F.Paste", "B.Paste"]
    proc = subprocess.run([str(KICAD_CLI), "pcb", "export", "gerbers", "--layers", ",".join(layers),
                           "--no-protel-ext", "-o", str(gdir), str(board)], capture_output=True, text=True)
    if proc.returncode:
        raise SystemExit(f"kicad-cli failed ({proc.returncode}): {proc.stderr[-1500:]}")
    exported = {p.stem.split("-")[-1].replace("_", "."): p for p in gdir.glob("*.gbr")}
    orig_ext = {**{KICAD_LAYER[e]: e for e in LAYERS}, "F.Mask": "GTS", "B.Mask": "GBS", "F.Paste": "GTP", "B.Paste": "GBP"}
    rt = {}
    for name in layers:
        o = layer_geometry(load_layer(GERBERS / f"{PREFIX}Gerbers.{orig_ext[name]}")).intersection(box(*BOARD).buffer(1.0))
        r = layer_geometry(mapped_layer(exported[name]))
        diff = o.symmetric_difference(r)
        largest = max((q.area for q in polygons(diff)), default=0.0)
        rt[name] = {"original_mm2": o.area, "roundtrip_mm2": r.area, "difference_mm2": diff.area,
                    "fraction": diff.area / o.area if o.area else 0.0, "largest_piece_mm2": largest}
        rt[name]["pass"] = rt[name]["fraction"] <= TOL_FRACTION and largest <= TOL_PIECE_MM2
    f1 = rt["F.Mask"]["pass"] and rt["B.Mask"]["pass"]
    f2 = rt["F.Paste"]["pass"] and rt["B.Paste"]["pass"]
    f3 = all(rt[KICAD_LAYER[e]]["pass"] for e in LAYERS)
    f4, f5 = not f4_fail, not f5_fail
    drc_path = OUT / "footprints-drc.json"
    drc = subprocess.run([str(KICAD_CLI), "pcb", "drc", "--format", "json", "-o", str(drc_path), str(board)],
                         capture_output=True, text=True)
    drc_counts = {}
    if drc_path.exists():
        d = json.loads(drc_path.read_text(encoding="utf-8"))
        drc_counts = {"violations": collections.Counter(v.get("type") for v in d.get("violations", [])),
                      "unconnected_items": len(d.get("unconnected_items", [])),
                      "schematic_parity": len(d.get("schematic_parity", []))}
    passed = f1 and f2 and f3 and f4 and f5
    out = {"schema": "epc90133-reconstruct-footprints/2", "step": "track R step 2b: footprints from the board's pads",
           "passed": passed, "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "checks": {"F1_mask": f1, "F2_paste": f2, "F3_copper_unchanged": f3, "F4_pad_copper_and_nets": f4,
                      "F5_drills": f5},
           "footprints": len(fps), "pads": pad_count, "nets": len(netid), "f4_failures": f4_fail,
           "f5_failures": f5_fail, "board_level_leftovers": leftovers, "layers": rt,
           "drc_reported_not_checked": {k: (dict(v) if isinstance(v, collections.Counter) else v)
                                         for k, v in drc_counts.items()},
           "board_file": "vendor/epc/epc90133/reconstruction/epc90133-footprints.kicad_pcb (git-ignored)"}
    args.output.write_text(json.dumps(out, indent=1, default=float) + "\n", encoding="utf-8")
    for name, v in rt.items():
        print(f"{name:8s} diff {v['fraction'] * 100:.6f} %  largest {v['largest_piece_mm2']:.2e} mm2  pass {v['pass']}")
    print(json.dumps({k: out[k] for k in ("passed", "checks", "footprints", "pads", "f4_failures", "f5_failures",
                                          "board_level_leftovers", "drc_reported_not_checked")}, indent=1, default=str))
    raise SystemExit(0 if passed else 1)


def pts_shift(parts, centre):
    return "".join(f'(gr_poly (pts {pts(list(q.exterior.coords)[:-1], centre)}) (width 0) (fill yes))'
                   for p_ in parts for q in split_holes(p_))


if __name__ == "__main__":
    main()
