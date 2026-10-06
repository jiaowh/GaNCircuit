#!/usr/bin/env python3
"""Track R step 5: finish the EPC90133 KiCad reconstruction (rings, silkscreen, EPC's rules) and explain its DRC.

Plan: plans/layout-round-2-plan.md, "Parallel track R", step 5 (acceptance: round trip and DRC with every exception
explained). Input: step 2b's board (footprints) rebuilt with step 3-4's construction (scripts/
epc90133_reconstruct_nets.py, run 2 passed). Output: vendor/epc/epc90133/reconstruction/epc90133.kicad_pcb and
epc90133.kicad_pro (git-ignored; EPC derivative).

Changes over steps 3-4 (declared 6 October 2026 before the first run), from step 3-4's DRC:
  - ring sizes: a via or plated pad becomes a circle of diameter min(cap, 2 r), where r is the largest radius about
    the hole centre that stays inside the copper island on every layer whose island contains the centre (so no
    copper is added); cap = for vias, the median equivalent diameter of isolated single-via islands of the same
    drill on the outer layers; for pads, the diameter of the largest circle about the hole inside the pad's mask
    opening(s). Rings that come out no larger than the drill are reported;
  - zone priorities: each zone's priority is its nesting depth (number of other islands on the layer whose exterior
    contains it), so zones lying in another island's hole are distinct;
  - netless pads: an unnamed or netless pad whose copper lies in a netted group takes that net (Q1/Q2's auxiliary
    gate pads); one lying in a netless group gives that group a KiCad-style 'unconnected-(REF-PIN)' net. Pads with
    an EPC net never change;
  - outline: GM1's lines are checked to lie on the board rectangle and written as one Edge.Cuts rectangle;
  - silkscreen: GTO/GBO as graphic polygons on F.SilkS/B.SilkS; back-side Fab references mirrored;
  - rules (EPC's .RUL in the Gerber package, units mil): clearance 5.91 mil (0.150114 mm, the smallest of its six
    clearance rules; the export lost the named rules' net scopes, so only the board-wide minimum is used), minimum
    width 5 mil, solder mask expansion 2 mil (metadata: mask openings are explicit). The file has no edge, hole,
    via or annular-ring rules; those KiCad constraints are set to 0 (not enforced) and the board's measured minima
    are reported.
Checks:
  R1 Gerber round trip of 8 copper, 2 mask, 2 paste and 2 silkscreen layers (difference <= 0.01 %, largest piece
     <= 0.001 mm^2 per layer) and outline bounds within 0.001 mm;
  R2 drill round trip as N3 (all EPC holes, position and diameter within 0.001 mm, same plating, equal counts);
  R3 KiCad DRC on the saved fills: zero shorting_items and zero unconnected_items;
  R4 every other DRC item is in a declared category: lib_footprint_issues (footprints built here, no library),
     isolated_copper (netless islands without pads; count must equal ours), clearance with actual >= 0.150114 -
     0.001 mm (arcs are 5-degree polygons, so EPC's exactly-at-rule gaps can read a fraction of a micron low), and
     silkscreen checks (silk_over_copper, silk_overlap, silk_edge_clearance, text_height, text_thickness: EPC's
     silkscreen as drawn). Anything else fails;
  R5 no pad with an EPC net changed net; every via and plated pad has a ring larger than its drill, or is listed.

Run 1 crashed in the comparison (no report): KiCad names the silkscreen Gerbers F_Silkscreen/B_Silkscreen, which
the file lookup did not map. Fixed for run 2; construction and checks unchanged.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys
import uuid

from shapely.geometry import Point
from shapely.geometry.polygon import Polygon, orient
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from circuit_tools.gerber import load_layer, parse_excellon
from read_epc90133_geometry import BOARD, GERBERS, LAYERS, PREFIX
from epc90133_reconstruct import KICAD_CLI, KICAD_LAYER, OUT, box, layer_geometry, mapped_layer, polygons, split_holes, to_kicad
from epc90133_reconstruct_nets import fracture, stackup_sexpr, xy

MIL = 0.0254
CLEARANCE = 5.91 * MIL
WIDTH = 5.0 * MIL
MASK_EXP = 2.0 * MIL
ARC_TOL = 0.001
TOL_FRACTION, TOL_PIECE_MM2, DRILL_TOL = 1e-4, 0.001, 0.001
SILK_TYPES = {"silk_over_copper", "silk_overlap", "silk_edge_clearance", "text_height", "text_thickness"}


def uid():
    return str(uuid.uuid4())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-reconstruct-final.json")
    args = ap.parse_args()
    src = (OUT / "epc90133-footprints.kicad_pcb").read_text(encoding="utf-8")
    copper_layers = set(KICAD_LAYER.values())
    keep = [ln for ln in src.splitlines(keepends=True)
            if not (ln.startswith("\t(gr_poly") and re.search(r'\(layer "([^"]+)"\)', ln).group(1) in copper_layers)
            and not (ln.startswith("\t(gr_line") and '"Edge.Cuts"' in ln)]
    text = "".join(keep).replace("\t(setup (pad_to_mask_clearance 0))\n", stackup_sexpr())

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

    def island_at(e, x, y):
        p = Point(x, y)
        return next(((e, int(i)) for i in trees[e].query(p) if geo[e][int(i)].contains(p)), None)

    holes = parse_excellon((GERBERS / f"{PREFIX}NC Drill.TXT").read_text(encoding="latin-1"))
    hole_layers = {}
    for k, h in enumerate(holes):
        if not h.plated:
            continue
        hit = [i for i in (island_at(e, h.x, h.y) for e in LAYERS) if i]
        hole_layers[k] = hit
        for a in hit[1:]:
            parent[find(a)] = find(hit[0])

    # --- footprints: pads, nets ---------------------------------------------------------------------------------
    fp_re = re.compile(r'\t\(footprint "EPC90133:([^"]+)" \(layer "([FB])\.Cu"\) \(uuid "[^"]+"\) \(at ([-\d.]+) ([-\d.]+)\)'
                       r'(.*?)\n\t\)\n', re.S)
    pad_re = re.compile(r'\(pad "([^"]*)" (smd|thru_hole) (\w+) \(at ([-\d.]+) ([-\d.]+)\)(.*?)\(uuid "[^"]+"\)\)')
    pads = []  # ref, pin, kind, side layer, board x, y, net
    for fp in fp_re.finditer(text):
        fx, fy = float(fp.group(3)), float(fp.group(4))
        e = "GTL" if fp.group(2) == "F" else "GBL"
        for p in pad_re.finditer(fp.group(5)):
            m = re.search(r'\(net \d+ "([^"]*)"\)', p.group(6))
            pads.append((fp.group(1), p.group(1), p.group(2), e, fx + float(p.group(4)) - 100.0,
                         150.0 - (fy + float(p.group(5))), m.group(1) if m else ""))
    group_net = collections.defaultdict(set)
    for ref, pin, kind, e, x, y, net in pads:
        i = island_at(e, x, y)
        if i and net:
            group_net[find(i)].add(net)
    if any(len(v) > 1 for v in group_net.values()):
        raise SystemExit("short: a copper group carries two EPC nets (steps 3-4 N2 should have caught this)")
    pad_net_change, new_nets = [], {}
    pad_final_net = {}
    for ref, pin, kind, e, x, y, net in pads:
        if net:
            pad_final_net[(ref, pin)] = net
            continue
        i = island_at(e, x, y)
        g = find(i) if i else None
        if g is not None and group_net.get(g):
            nn = next(iter(group_net[g]))
        else:
            nn = new_nets.setdefault(g, f"unconnected-({ref}-Pad{pin or '0'})")
            if g is not None:
                group_net[g] = {nn}
        pad_final_net[(ref, pin)] = nn
        pad_net_change.append({"pad": f"{ref}-{pin}", "net": nn})
    all_nets = sorted({n for s in group_net.values() for n in s} | set(pad_final_net.values()) - {""})
    netid = {n: i for i, n in enumerate(all_nets, start=1)}

    # --- ring sizes ---------------------------------------------------------------------------------------------
    def inscribed(k, h):
        """Largest radius about the hole centre inside the island on every layer whose island contains it."""
        p = Point(h.x, h.y)
        out = [geo[e][i].boundary.distance(p) for e, i in hole_layers.get(k, [])]
        return min(out) if out else 0.0

    th_holes = {}
    for ref, pin, kind, e, x, y, net in pads:
        if kind == "thru_hole":
            k = min(range(len(holes)), key=lambda j: (holes[j].x - x) ** 2 + (holes[j].y - y) ** 2)
            th_holes[k] = (ref, pin)
    masks = {s: polygons(layer_geometry(load_layer(GERBERS / f"{PREFIX}Gerbers.{s}"))) for s in ("GTS", "GBS")}
    mtree = {s: STRtree(masks[s]) for s in masks}

    def mask_cap(h):
        p = Point(h.x, h.y)
        rs = [masks[s][int(i)].exterior.distance(p) for s in masks for i in mtree[s].query(p)
              if masks[s][int(i)].contains(p)]
        return 2 * min(rs) if rs else None

    iso = collections.defaultdict(list)
    for k, h in enumerate(holes):
        if not h.plated or k in th_holes:
            continue
        for e in ("GTL", "GBL"):
            i = island_at(e, h.x, h.y)
            if i and geo[e][i[1]].area < 1.0 and sum(geo[e][i[1]].contains(Point(q.x, q.y)) for q in holes) == 1:
                iso[round(h.diameter, 4)].append(2 * (geo[e][i[1]].area / 3.141592653589793) ** 0.5)
    nominal = {d: statistics.median(v) for d, v in iso.items()}
    size, ringless = {}, []
    for k, h in enumerate(holes):
        if not h.plated:
            continue
        cap = mask_cap(h) if k in th_holes else nominal.get(round(h.diameter, 4))
        r2 = 2 * inscribed(k, h)
        s = min(r2, cap) if cap else r2
        if s <= h.diameter + 1e-4:
            ringless.append({"x": round(h.x, 3), "y": round(h.y, 3), "drill": h.diameter,
                             "kind": "pad " + "-".join(th_holes[k]) if k in th_holes else "via"})
            s = h.diameter
        size[k] = s

    # --- rewrite footprints: TH pad sizes, nets for netless pads, mirrored back references ----------------------
    def fix_fp(m):
        ref, side, fx, fy, body = m.group(1), m.group(2), float(m.group(3)), float(m.group(4)), m.group(5)

        def fix_pad(p):
            pin, kind = p.group(1), p.group(2)
            rest = p.group(0)
            x, y = fx + float(p.group(4)) - 100.0, 150.0 - (fy + float(p.group(5)))
            if kind == "thru_hole":
                k = min(range(len(holes)), key=lambda j: (holes[j].x - x) ** 2 + (holes[j].y - y) ** 2)
                d = size[k]
                rest = re.sub(r"\(size [\d.]+ [\d.]+\)", f"(size {d:.4f} {d:.4f})", rest, count=1)
            net = pad_final_net.get((ref, pin), "")
            rest = re.sub(r' \(net \d+ "[^"]*"\)', "", rest)
            if net:
                rest = rest.replace(" (uuid ", f' (net {netid[net]} "{net}") (uuid ', 1)
            return rest

        body = pad_re.sub(fix_pad, body)
        if side == "B":
            body = body.replace("(effects (font (size 0.5 0.5) (thickness 0.08)))",
                                "(effects (font (size 0.5 0.5) (thickness 0.08)) (justify mirror))")
        return m.group(0).replace(m.group(5), body)

    text = fp_re.sub(fix_fp, text)
    text = re.sub(r'^\t\(net [1-9]\d* "[^"]*"\)\n', "", text, flags=re.M)  # keep net 0
    text = text.replace('\t(net 0 "")\n', '\t(net 0 "")\n' + "".join(f'\t(net {i} "{n}")\n' for n, i in netid.items()), 1)

    # --- zones, vias, outline, silkscreen -----------------------------------------------------------------------
    zones, netless_islands = [], 0
    for e in LAYERS:
        L = KICAD_LAYER[e]
        ext = [Polygon(p.exterior) for p in geo[e]]
        et = STRtree(ext)
        for i, poly in enumerate(geo[e]):
            depth = sum(1 for j in et.query(poly) if int(j) != i and ext[int(j)].contains(poly.representative_point())
                        and ext[int(j)].area > ext[i].area)
            names = group_net.get(find((e, i)), set())
            net = next(iter(names)) if names else ""
            netless_islands += not net
            zones.append(f'\t(zone (net {netid.get(net, 0)}) (net_name "{net}") (layer "{L}") (uuid "{uid()}") '
                         f'(priority {depth}) (hatch edge 0.5) (connect_pads yes (clearance 0)) (min_thickness 0.01) '
                         f'(filled_areas_thickness no) (fill yes (thermal_gap 0.01) (thermal_bridge_width 0.01) '
                         f'(island_removal_mode 1)) (polygon (pts {xy(list(orient(poly, 1.0).exterior.coords)[:-1])})) '
                         f'(filled_polygon (layer "{L}") (pts {xy(fracture(poly))})))\n')
    vias = []
    for k, h in enumerate(holes):
        if not h.plated or k in th_holes:
            continue
        hit = hole_layers.get(k)
        names = group_net.get(find(hit[0]), set()) if hit else set()
        net = next(iter(names)) if names else ""
        x, y = to_kicad(h.x, h.y)
        vias.append(f'\t(via (at {x:.6f} {y:.6f}) (size {size[k]:.4f}) (drill {h.diameter:.4f}) (layers "F.Cu" "B.Cu") '
                    f'(remove_unused_layers yes) (keep_end_layers yes) (net {netid.get(net, 0)}) (uuid "{uid()}"))\n')
    gm1 = load_layer(GERBERS / f"{PREFIX}Gerbers.GM1")
    ends = [q for p in gm1.primitives if p.kind == "line" for q in p.data[:2]]
    x0, y0 = min(q[0] for q in ends), min(q[1] for q in ends)
    x1, y1 = max(q[0] for q in ends), max(q[1] for q in ends)
    if not all(min(abs(q[0] - x0), abs(q[0] - x1)) < 1e-6 or min(abs(q[1] - y0), abs(q[1] - y1)) < 1e-6 for q in ends):
        raise SystemExit("GM1 outline is not the board rectangle")
    (ax, ay), (bx, by) = to_kicad(x0, y1), to_kicad(x1, y0)
    outline = (f'\t(gr_rect (start {ax:.6f} {ay:.6f}) (end {bx:.6f} {by:.6f}) (stroke (width 0.05) (type solid)) '
               f'(fill no) (layer "Edge.Cuts") (uuid "{uid()}"))\n')
    silk = []
    for ext_, L in (("GTO", "F.SilkS"), ("GBO", "B.SilkS")):
        g = layer_geometry(load_layer(GERBERS / f"{PREFIX}Gerbers.{ext_}")).intersection(box(*BOARD).buffer(1.0))
        for p in polygons(g):
            silk += [f'\t(gr_poly (pts {xy(list(q.exterior.coords)[:-1])}) (stroke (width 0) (type solid)) (fill yes) '
                     f'(layer "{L}") (uuid "{uid()}"))\n' for q in split_holes(p)]
    body = text.rstrip()
    board = OUT / "epc90133.kicad_pcb"
    board.write_text(body[:-1] + "".join(zones) + "".join(vias) + outline + "".join(silk) + ")\n", encoding="utf-8")
    pro = {"meta": {"filename": "epc90133.kicad_pro", "version": 1},
           "board": {"design_settings": {"rules": {
               "min_clearance": CLEARANCE, "min_track_width": WIDTH, "solder_mask_to_copper_clearance": 0.0,
               "min_copper_edge_clearance": 0.0, "min_hole_clearance": 0.0, "min_hole_to_hole": 0.0,
               "min_through_hole_diameter": 0.0, "min_via_diameter": 0.0, "min_via_annular_width": 0.0,
               "min_microvia_diameter": 0.0, "min_microvia_drill": 0.0, "min_text_height": 0.0,
               "min_text_thickness": 0.0, "min_silk_clearance": 0.0}}},
           "net_settings": {"classes": [{"name": "Default", "clearance": CLEARANCE, "track_width": WIDTH,
                                         "via_diameter": 0.4, "via_drill": 0.2, "priority": 2147483647}],
                            "meta": {"version": 4}}}
    (OUT / "epc90133.kicad_pro").write_text(json.dumps(pro, indent=2) + "\n", encoding="utf-8")

    # --- R1 Gerber round trip ------------------------------------------------------------------------------------
    gdir = OUT / "final-gerbers"
    gdir.mkdir(exist_ok=True)
    for f in gdir.glob("*"):
        f.unlink()
    layers = list(KICAD_LAYER.values()) + ["F.Mask", "B.Mask", "F.Paste", "B.Paste", "F.SilkS", "B.SilkS", "Edge.Cuts"]
    proc = subprocess.run([str(KICAD_CLI), "pcb", "export", "gerbers", "--layers", ",".join(layers), "--no-protel-ext",
                           "-o", str(gdir), str(board)], capture_output=True, text=True)
    if proc.returncode:
        raise SystemExit(f"kicad-cli gerbers failed ({proc.returncode}): {proc.stderr[-1500:]}")
    exported = {p.stem.split("-")[-1].replace("_", ".").replace("Silkscreen", "SilkS"): p for p in gdir.glob("*.gbr")}
    orig_ext = {**{KICAD_LAYER[e]: e for e in LAYERS}, "F.Mask": "GTS", "B.Mask": "GBS", "F.Paste": "GTP",
                "B.Paste": "GBP", "F.SilkS": "GTO", "B.SilkS": "GBO"}
    rt = {}
    for name, ext_ in orig_ext.items():
        o = layer_geometry(load_layer(GERBERS / f"{PREFIX}Gerbers.{ext_}")).intersection(box(*BOARD).buffer(1.0))
        r = layer_geometry(mapped_layer(exported[name]))
        diff = o.symmetric_difference(r)
        largest = max((q.area for q in polygons(diff)), default=0.0)
        rt[name] = {"difference_fraction": diff.area / o.area if o.area else 0.0, "largest_piece_mm2": largest}
        rt[name]["pass"] = rt[name]["difference_fraction"] <= TOL_FRACTION and largest <= TOL_PIECE_MM2
    edge = mapped_layer(exported["Edge.Cuts"])
    pts = [q for p in edge.primitives for q in (p.data[:2] if p.kind == "line" else p.data[0])]
    eb = (min(q[0] for q in pts), min(q[1] for q in pts), max(q[0] for q in pts), max(q[1] for q in pts))
    outline_ok = max(abs(a - b) for a, b in zip(eb, (x0, y0, x1, y1))) <= 0.001  # centre-line bounds
    r1 = all(v["pass"] for v in rt.values()) and outline_ok

    # --- R2 drills -----------------------------------------------------------------------------------------------
    ddir = OUT / "final-drill"
    ddir.mkdir(exist_ok=True)
    for f in ddir.glob("*"):
        f.unlink()
    proc = subprocess.run([str(KICAD_CLI), "pcb", "export", "drill", "--excellon-separate-th", "-u", "mm",
                           "-o", str(ddir) + "/", str(board)], capture_output=True, text=True)
    if proc.returncode:
        raise SystemExit(f"kicad-cli drill failed ({proc.returncode}): {proc.stderr[-1500:]}")
    pool = [(h.x - 100.0, h.y + 150.0, h.diameter, "NPTH" not in f.name)
            for f in ddir.glob("*.drl") for h in parse_excellon(f.read_text(encoding="latin-1"))]
    n_exp = len(pool)
    unmatched = []
    for h in holes:
        j = next((k for k, q in enumerate(pool) if abs(q[0] - h.x) <= DRILL_TOL and abs(q[1] - h.y) <= DRILL_TOL
                  and abs(q[2] - h.diameter) <= DRILL_TOL and q[3] == h.plated), None)
        if j is None:
            unmatched.append((round(h.x, 3), round(h.y, 3), h.diameter, h.plated))
        else:
            pool.pop(j)
    r2 = not unmatched and not pool

    # --- R3/R4 DRC -----------------------------------------------------------------------------------------------
    drc_path = OUT / "final-drc.json"
    subprocess.run([str(KICAD_CLI), "pcb", "drc", "--format", "json", "--severity-all", "-o", str(drc_path), str(board)],
                   capture_output=True, text=True)
    d = json.loads(drc_path.read_text(encoding="utf-8"))
    viol = d.get("violations", [])
    counts = collections.Counter(v.get("type") for v in viol)
    r3 = counts.get("shorting_items", 0) == 0 and not d.get("unconnected_items")
    unexplained, below = [], []
    for v in viol:
        t = v.get("type")
        if t in ("lib_footprint_issues",) or t in SILK_TYPES:
            continue
        if t == "isolated_copper":
            continue
        if t == "clearance":
            m = re.search(r"actual ([\d.]+) mm", v.get("description", ""))
            if m and float(m.group(1)) >= CLEARANCE - ARC_TOL:
                continue
            below.append({"description": v.get("description"), "items": [i.get("description") for i in v.get("items", [])]})
            continue
        unexplained.append({"type": t, "description": v.get("description"),
                            "items": [i.get("description") for i in v.get("items", [])][:2]})
    iso_ok = counts.get("isolated_copper", 0) <= netless_islands
    r4 = not unexplained and not below and iso_ok
    epc_net_changed = [c for c in pad_net_change if any(p[0] + "-" + p[1] == c["pad"] and p[6] for p in pads)]
    r5 = not epc_net_changed
    passed = r1 and r2 and r3 and r4 and r5
    out = {"schema": "epc90133-reconstruct-final/1", "step": "track R step 5: rings, silkscreen, EPC rules, explained DRC",
           "passed": passed, "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "checks": {"R1_gerber_round_trip": r1, "R2_drills": r2, "R3_no_shorts_unconnected": r3,
                      "R4_drc_explained": r4, "R5_epc_nets_unchanged": r5},
           "rules_mm": {"clearance": CLEARANCE, "min_width": WIDTH, "mask_expansion": MASK_EXP},
           "via_nominal_diameter_mm": nominal, "ringless": ringless, "netless_pads_assigned": pad_net_change,
           "netless_islands": netless_islands, "drill": {"original": len(holes), "exported": n_exp,
                                                         "unmatched": unmatched[:20], "extra": pool[:20]},
           "layers": rt, "outline_bounds_roundtrip": eb,
           "drc": {"counts": dict(counts), "unconnected_items": len(d.get("unconnected_items", [])),
                   "unexplained": unexplained[:30], "clearance_below_rule": below[:30]},
           "board_file": "vendor/epc/epc90133/reconstruction/epc90133.kicad_pcb (git-ignored; EPC derivative)"}
    args.output.write_text(json.dumps(out, indent=1, default=float) + "\n", encoding="utf-8")
    for name, v in rt.items():
        print(f"{name:8s} diff {v['difference_fraction'] * 100:.6f} %  largest {v['largest_piece_mm2']:.2e}  pass {v['pass']}")
    print(json.dumps({k: out[k] for k in ("passed", "checks", "via_nominal_diameter_mm", "netless_islands")}, indent=1,
                     default=float))
    print("ringless", len(ringless), ringless[:5])
    print("netless pads assigned", pad_net_change)
    print("drc", out["drc"]["counts"], "unconnected", out["drc"]["unconnected_items"])
    print("unexplained", unexplained[:8])
    print("below rule", below[:8])
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
