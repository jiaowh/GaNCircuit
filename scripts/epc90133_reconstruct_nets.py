#!/usr/bin/env python3
"""Track R steps 3-4: nets on the EPC90133 copper, vias, stackup; full Gerber + drill round trip and KiCad DRC.

Plan: plans/layout-round-2-plan.md, "Parallel track R", steps 3-5. Input: step 2b's board
(vendor/epc/epc90133/reconstruction/epc90133-footprints.kicad_pcb: copper as unnetted graphic polygons, 106
footprints whose pads carry EPC's netlist nets). Output: epc90133-nets.kicad_pcb in the same git-ignored folder.

Construction (declared 6 October 2026 before the first run):
  - copper islands: each polygon of step 1's copper geometry on each layer; islands are joined across layers by
    every plated drill whose centre lies inside the island on each layer it touches (union-find);
  - nets: each joined group takes the net of the named pads whose copper lies in it (pad copper representative
    point); a group touched by pads of two different nets is a short and fails N2; a group with no named pad gets
    no net (reported);
  - each island becomes a zone on its layer with that net: outline = the island's exterior, fill = the island
    itself written as one fractured polygon (each hole joined to the outline by a zero-width slit, as KiCad stores
    fills), so the fill is EPC's copper exactly; KiCad's refill would regenerate it by KiCad rules (zones are not
    refilled here);
  - vias: every plated drill not at a footprint's through-hole pad becomes a through via, size = drill (adds no
    copper), remove_unused_layers with keep_end_layers, with its group's net;
  - stackup from EPC90133_B5253_Rev2_0_Stackup.xls: 8 copper layers of 2.8 mil, dielectrics 5/5/7.2/5/7.2/5/5 mil
    (FR370-HR, er 4.8), solder resist 0.7 mil (er 3.5); total 63.2 mil. Core/prepreg is not stated in the file;
    all dielectrics are written as prepreg (assumption; no effect on Gerbers).
Checks:
  N1 copper, mask and paste Gerbers round-trip exactly (as step 2b F1-F3: difference <= 0.01 %, largest piece
     <= 0.001 mm^2 per layer);
  N2 no copper group carries pads of two different nets;
  N3 drill round trip: KiCad's PTH and NPTH Excellon files hold exactly EPC's holes (each matched within 0.001 mm
     in position and diameter, same plating, equal counts);
  N4 KiCad DRC on the saved fills (no refill): zero shorting_items and zero unconnected_items; other violations
     (clearance, annular width from drill-size vias, ...) are reported, not checked, because KiCad's default rules
     are not EPC's;
  N5 the stackup's total thickness equals the file's 63.2 mil within 0.1 mil.

Run 1 FAILED N3 only (kept: results/gan/epc90133-reconstruct-nets-run1-failed.json). N1, N2, N4 and N5 passed:
KiCad's own DRC found zero shorts and zero unconnected items with the saved fills, and the Gerbers round-trip
exactly. N3 failed in the comparison, not the board: our Excellon reader ignored the decimal point in KiCad's
"decimal" coordinates (X105.25 read as 10.5). Fixed in src/circuit_tools/gerber.py with a regression test; EPC's
drill file has no decimal points, so its reading is unchanged. Run 2 uses the same construction and checks.

Audit at 0f07a6a (6 October 2026; no rerun, run 2's stored report stands): the N4 DRC now runs through
circuit_tools.kicad.run_drc, so a failed command or a stale report can no longer pass N4.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid

from shapely.geometry import Point
from shapely.geometry.polygon import orient
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from circuit_tools.gerber import load_layer, parse_excellon
from circuit_tools.kicad import KiCadError, run_drc
from read_epc90133_geometry import BOARD, GERBERS, LAYERS, PREFIX
from epc90133_reconstruct import KICAD_CLI, KICAD_LAYER, OUT, box, layer_geometry, mapped_layer, polygons, to_kicad

MIL = 0.0254
STACK = [("F.Mask", "Top Solder Mask", 0.7, 3.5)] + [x for i in range(8) for x in (
    [(["F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "In5.Cu", "In6.Cu", "B.Cu"][i], "copper", 2.8, None)]
    + ([(f"dielectric {i + 1}", "prepreg", [5.0, 5.0, 7.2, 5.0, 7.2, 5.0, 5.0][i], 4.8)] if i < 7 else []))] + \
    [("B.Mask", "Bottom Solder Mask", 0.7, 3.5)]
TOTAL_MIL = 63.2
TOL_FRACTION, TOL_PIECE_MM2, DRILL_TOL = 1e-4, 0.001, 0.001


def uid():
    return str(uuid.uuid4())


def fracture(poly):
    """One ring covering poly: exterior CCW, each hole (CW) joined by a zero-width slit from its rightmost vertex
    to the nearest outline edge to its right (holes merged in order of decreasing max x)."""
    poly = orient(poly, 1.0)
    out = list(poly.exterior.coords)[:-1]
    holes = sorted((list(h.coords)[:-1] for h in poly.interiors), key=lambda h: -max(p[0] for p in h))
    for h in holes:
        k = max(range(len(h)), key=lambda i: (h[i][0], -h[i][1]))
        px, py = h[k]
        best = None
        for i in range(len(out)):
            (ax, ay), (bx, by) = out[i], out[(i + 1) % len(out)]
            if (ay > py) != (by > py):
                x = ax + (py - ay) * (bx - ax) / (by - ay)
                if x >= px and (best is None or x < best[0]):
                    best = (x, i)
        if best is None:
            raise ValueError("fracture: no outline edge to the right of a hole")
        x, i = best
        ring = h[k:] + h[:k] + [h[k]]
        out = out[:i + 1] + [(x, py)] + ring + [(x, py)] + out[i + 1:]
    return out


def xy(points):
    return " ".join(f"(xy {x:.6f} {y:.6f})" for x, y in (to_kicad(*p) for p in points))


def stackup_sexpr():
    rows = []
    for name, typ, mil, er in STACK:
        if typ == "copper":
            rows.append(f'\t\t\t(layer "{name}" (type "copper") (thickness {mil * MIL:.6f}))')
        elif name.endswith("Mask"):
            rows.append(f'\t\t\t(layer "{name}" (type "{typ}") (thickness {mil * MIL:.6f}) (epsilon_r {er}))')
        else:
            rows.append(f'\t\t\t(layer "{name}" (type "{typ}") (thickness {mil * MIL:.6f}) (material "FR370-HR") '
                        f'(epsilon_r {er}) (loss_tangent 0))')
    return ("\t(setup\n\t\t(stackup\n" + "\n".join(rows) +
            '\n\t\t\t(copper_finish "None") (dielectric_constraints no)\n\t\t)\n\t\t(pad_to_mask_clearance 0)\n\t)\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-reconstruct-nets.json")
    args = ap.parse_args()
    src = (OUT / "epc90133-footprints.kicad_pcb").read_text(encoding="utf-8")
    copper_layers = set(KICAD_LAYER.values())
    lines = src.splitlines(keepends=True)
    keep = [ln for ln in lines if not (ln.startswith("\t(gr_poly") and
                                       re.search(r'\(layer "([^"]+)"\)', ln).group(1) in copper_layers)]
    text = "".join(keep).replace("\t(setup (pad_to_mask_clearance 0))\n", stackup_sexpr())
    netid = {m.group(2): int(m.group(1)) for m in re.finditer(r'^\t\(net (\d+) "([^"]*)"\)$', text, re.M)}

    geo = {e: polygons(layer_geometry(load_layer(GERBERS / f"{PREFIX}Gerbers.{e}")).intersection(box(*BOARD).buffer(1.0)))
           for e in LAYERS}
    trees = {e: STRtree(geo[e]) for e in LAYERS}
    parent = {}

    def find(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        parent[find(a)] = find(b)

    def island_at(e, x, y):
        p = Point(x, y)
        return next(((e, int(i)) for i in trees[e].query(p) if geo[e][int(i)].contains(p)), None)

    holes = parse_excellon((GERBERS / f"{PREFIX}NC Drill.TXT").read_text(encoding="latin-1"))
    for h in holes:
        if not h.plated:
            continue
        hit = [i for i in (island_at(e, h.x, h.y) for e in LAYERS) if i]
        for a in hit[1:]:
            union(hit[0], a)

    # named pads: footprint position + pad position + net, from the step-2b board text
    pad_net_points = []
    for fp in re.finditer(r'\t\(footprint "EPC90133:([^"]+)" \(layer "([FB])\.Cu"\) \(uuid "[^"]+"\) \(at ([-\d.]+) ([-\d.]+)\)'
                          r'(.*?)\n\t\)\n', text, re.S):
        fx, fy = float(fp.group(3)), float(fp.group(4))
        e = "GTL" if fp.group(2) == "F" else "GBL"
        for pad in re.finditer(r'\(pad "([^"]*)" (smd|thru_hole) \w+ \(at ([-\d.]+) ([-\d.]+)\).*?\(net (\d+) "([^"]*)"\)',
                               fp.group(5)):
            x, y = fx + float(pad.group(3)), fy + float(pad.group(4))
            pad_net_points.append((fp.group(1), pad.group(1), e, x - 100.0, 150.0 - y, pad.group(6)))
    group_net, shorts, off_copper = collections.defaultdict(set), [], []
    for ref, pin, e, x, y, net in pad_net_points:
        i = island_at(e, x, y)
        if i is None:
            off_copper.append(f"{ref}-{pin}")
            continue
        group_net[find(i)].add(net)
    shorts = {str(g): sorted(n) for g, n in group_net.items() if len(n) > 1}
    n2 = not shorts

    zones, unnamed = [], 0
    for e in LAYERS:
        L = KICAD_LAYER[e]
        for i, poly in enumerate(geo[e]):
            names = group_net.get(find((e, i)), set())
            net = next(iter(names)) if len(names) == 1 else ""
            unnamed += not net
            nid = netid.get(net, 0)
            zones.append(f'\t(zone (net {nid}) (net_name "{net}") (layer "{L}") (uuid "{uid()}") (hatch edge 0.5) '
                         f'(connect_pads yes (clearance 0)) (min_thickness 0.01) (filled_areas_thickness no) '
                         f'(fill yes (thermal_gap 0.01) (thermal_bridge_width 0.01) (island_removal_mode 1)) '
                         f'(polygon (pts {xy(list(orient(poly, 1.0).exterior.coords)[:-1])})) '
                         f'(filled_polygon (layer "{L}") (pts {xy(fracture(poly))})))\n')
    th_positions = []  # through-hole and non-plated footprint pads (absolute board mm)
    for fp in re.finditer(r'\(at ([-\d.]+) ([-\d.]+)\)\n(.*?)\n\t\)\n', text, re.S):
        fx, fy = float(fp.group(1)), float(fp.group(2))
        for pad in re.finditer(r'\(pad "[^"]*" (?:thru_hole|np_thru_hole) circle \(at ([-\d.]+) ([-\d.]+)\)', fp.group(3)):
            th_positions.append((fx + float(pad.group(1)) - 100.0, 150.0 - (fy + float(pad.group(2)))))
    th_tree = STRtree([Point(p) for p in th_positions]) if th_positions else None
    vias = []
    for h in holes:
        if not h.plated:
            continue
        p = Point(h.x, h.y)
        if th_tree is not None and any(p.distance(Point(th_positions[int(j)])) < DRILL_TOL for j in th_tree.query(p.buffer(0.01))):
            continue
        hit = next((i for i in (island_at(e, h.x, h.y) for e in LAYERS) if i), None)
        names = group_net.get(find(hit), set()) if hit else set()
        net = next(iter(names)) if len(names) == 1 else ""
        x, y = to_kicad(h.x, h.y)
        vias.append(f'\t(via (at {x:.6f} {y:.6f}) (size {h.diameter:.4f}) (drill {h.diameter:.4f}) '
                    f'(layers "F.Cu" "B.Cu") (remove_unused_layers yes) (keep_end_layers yes) (net {netid.get(net, 0)}) '
                    f'(uuid "{uid()}"))\n')
    body = text.rstrip()
    assert body.endswith(")")
    board = OUT / "epc90133-nets.kicad_pcb"
    board.write_text(body[:-1] + "".join(zones) + "".join(vias) + ")\n", encoding="utf-8")

    # N1 Gerber round trip
    gdir = OUT / "nets-gerbers"
    gdir.mkdir(exist_ok=True)
    layers = list(KICAD_LAYER.values()) + ["F.Mask", "B.Mask", "F.Paste", "B.Paste"]
    proc = subprocess.run([str(KICAD_CLI), "pcb", "export", "gerbers", "--layers", ",".join(layers), "--no-protel-ext",
                           "-o", str(gdir), str(board)], capture_output=True, text=True)
    if proc.returncode:
        raise SystemExit(f"kicad-cli gerbers failed ({proc.returncode}): {proc.stderr[-1500:]}")
    exported = {p.stem.split("-")[-1].replace("_", "."): p for p in gdir.glob("*.gbr")}
    orig_ext = {**{KICAD_LAYER[e]: e for e in LAYERS}, "F.Mask": "GTS", "B.Mask": "GBS", "F.Paste": "GTP", "B.Paste": "GBP"}
    rt = {}
    for name in layers:
        o = layer_geometry(load_layer(GERBERS / f"{PREFIX}Gerbers.{orig_ext[name]}")).intersection(box(*BOARD).buffer(1.0))
        r = layer_geometry(mapped_layer(exported[name]))
        diff = o.symmetric_difference(r)
        largest = max((q.area for q in polygons(diff)), default=0.0)
        rt[name] = {"difference_fraction": diff.area / o.area if o.area else 0.0, "largest_piece_mm2": largest}
        rt[name]["pass"] = rt[name]["difference_fraction"] <= TOL_FRACTION and largest <= TOL_PIECE_MM2
    n1 = all(v["pass"] for v in rt.values())

    # N3 drill round trip
    ddir = OUT / "nets-drill"
    ddir.mkdir(exist_ok=True)
    proc = subprocess.run([str(KICAD_CLI), "pcb", "export", "drill", "--excellon-separate-th", "-u", "mm",
                           "-o", str(ddir) + "/", str(board)], capture_output=True, text=True)
    if proc.returncode:
        raise SystemExit(f"kicad-cli drill failed ({proc.returncode}): {proc.stderr[-1500:]}")
    exp_holes = []
    for f in ddir.glob("*.drl"):
        plated = "NPTH" not in f.name
        for h in parse_excellon(f.read_text(encoding="latin-1")):
            exp_holes.append((h.x - 100.0, h.y + 150.0, h.diameter, plated))
    unmatched = []
    pool = list(exp_holes)
    for h in holes:
        j = next((k for k, q in enumerate(pool) if abs(q[0] - h.x) <= DRILL_TOL and abs(q[1] - h.y) <= DRILL_TOL
                  and abs(q[2] - h.diameter) <= DRILL_TOL and q[3] == h.plated), None)
        if j is None:
            unmatched.append((round(h.x, 3), round(h.y, 3), h.diameter, h.plated))
        else:
            pool.pop(j)
    n3 = not unmatched and not pool

    # N4 DRC without refill
    try:  # audit at 0f07a6a: fresh report path, exit status, schema and board identity checked
        d = run_drc(KICAD_CLI, board, OUT / "drc-runs", "nets")["report"]
    except KiCadError as exc:
        raise SystemExit(f"DRC failed: {exc}")
    viol = collections.Counter(v.get("type") for v in d.get("violations", []))
    unconnected = d.get("unconnected_items", [])
    n4 = bool(d) and viol.get("shorting_items", 0) == 0 and len(unconnected) == 0
    total = sum(m for _, _, m, _ in STACK)
    n5 = abs(total - TOTAL_MIL) <= 0.1
    passed = n1 and n2 and n3 and n4 and n5
    out = {"schema": "epc90133-reconstruct-nets/1", "step": "track R steps 3-4: nets, vias, stackup, round trip, DRC",
           "passed": passed, "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "checks": {"N1_gerber_round_trip": n1, "N2_no_shorts": n2, "N3_drills": n3, "N4_drc_shorts_unconnected": n4,
                      "N5_stackup_total": n5},
           "zones": len(zones), "zones_without_net": unnamed, "vias": len(vias), "pads_off_copper": off_copper,
           "shorts": shorts, "drill": {"original": len(holes), "exported": len(exp_holes), "unmatched_original": unmatched[:20],
                                       "unmatched_exported": [tuple(round(v, 3) if isinstance(v, float) else v for v in q)
                                                              for q in pool[:20]]},
           "stackup_total_mil": total, "layers": rt,
           "drc": {"violations": dict(viol), "unconnected_items": len(unconnected),
                   "unconnected_examples": [[i.get("description") for i in u.get("items", [])] for u in unconnected[:10]]},
           "board_file": "vendor/epc/epc90133/reconstruction/epc90133-nets.kicad_pcb (git-ignored; EPC derivative)"}
    args.output.write_text(json.dumps(out, indent=1, default=float) + "\n", encoding="utf-8")
    for name, v in rt.items():
        print(f"{name:8s} diff {v['difference_fraction'] * 100:.6f} %  largest {v['largest_piece_mm2']:.2e}  pass {v['pass']}")
    print(json.dumps({k: out[k] for k in ("passed", "checks", "zones", "zones_without_net", "vias", "pads_off_copper",
                                          "shorts", "drill", "stackup_total_mil", "drc")}, indent=1, default=str))
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
