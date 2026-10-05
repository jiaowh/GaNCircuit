#!/usr/bin/env python3
"""Topology audit of the EPC90133 extraction mesh: plane holes, slots and via attachments (no solver run).

Declared 2 October 2026, before its first run, as the first bounded step after the external review of the
via-array / plane-hole / FasterCap plans (docs/build.md "Mesh topology audit"). Purpose: before any benchmark
of via arrays or plane holes is designed, record how the PRODUCTION extraction rules (scripts/epc90133_extract.py,
unchanged and bound by hash) represent the board's holes, slots and via groups, so the benchmarks test the
representation that the board decks actually use. It measures representation, not accuracy: it computes no
inductance and its findings are not error bars.

Decks. build() of the production extractor, junction "mid" unless stated, parsed from the FastHenry deck text it
returns (so the audit sees exactly what FastHenry sees, after unconnected nodes are dropped):
    production meshes  A:m1, A:m2, B:m1, B:m2, G:m1 (m2 of A and B was never solved; it is audited as declared);
    junction pad       B:m1:pad (attachment statistics only);
    grid offsets       B:m1 and B:m2 with the grid origin shifted by (s/2, 0), (0, s/2), (s/2, s/2) (the
                       production grid is aligned to the FET pin rows; offsets show how much the findings depend on
                       that alignment). A shifted build that fails is recorded with its error.

Quantities (all per layer of the deck; raster = the 1-mil Gerber raster used by the extractor):
T1 width overreach. A plane segment carries width w about its centre line, but the extractor checks copper only on
   the centre line. For every plane segment: the fraction of its w-wide rectangle that is not copper of the
   segment's own island. Reported: number of segments, number with overreach > 0 and > 50 %, total overreach area,
   and the overreach area falling inside enclosed holes (T2).
T2 enclosed holes. Holes = pixels inside an island's filled outline but not copper of it (clearances, antipads,
   slots), within the deck window, for each island that has deck nodes. Per hole: area, equivalent diameter
   2 sqrt(A/pi), bounding box, the plated drills inside it with their nets, and "crossed": whether any grid line of
   the deck's grid passes through it. An uncrossed hole is invisible to the mesh: the segment widths cover it with
   copper. A row of antipads that join into one hole is reported as one hole with several drills (a slot).
   Notches open to an island's edge are not enclosed holes and are not covered.
T3 mesh splitting. Per (layer, island), the number of connected components of its plane-segment graph in the deck.
   More than one means the grid splits copper that the raster joins (or the window cuts it); vias may still join the
   parts, which is why they survived the drop of unconnected nodes.
T4 via attachments. Per via end (from the .equiv lines): the attached grid nodes and the distance from the via
   centre to the nearest one; per layer, how many vias attach to the same grid node (vias keep separate vertical
   segments, but their attachment points coincide). Summarised by via group (results/gan/epc90133-power-loop.json
   via_groups, matched by drill position).

Flags, fixed here (findings for benchmark design, not pass/fail of the extraction):
F1 an uncrossed enclosed hole with equivalent diameter >= s/2 in a deck with pitch s;
F2 any plane segment with overreach > 50 %;
F3 any via end whose nearest attached node lies farther than s from the via centre;
F4 any grid node shared by >= 2 vias on one layer (count of such nodes and of vias involved, per group);
F5 any island whose plane-segment graph has more than one component.
Outcome is "audit complete" when every declared production deck built and was measured; flags are listed, not
judged. A shifted-grid build failure is recorded and does not change the outcome.

    python scripts/audit_epc90133_mesh_topology.py   # results/gan/epc90133-mesh-topology-audit.json
"""
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import sys

import numpy as np
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import epc90133_extract as ex  # noqa: E402
from epc90133_power_loop import via_layers  # noqa: E402
from read_epc90133_geometry import PITCH, load_board  # noqa: E402

OUTPUT = ROOT / "results/gan/epc90133-mesh-topology-audit.json"
PRODUCTION = ("A:m1:mid", "A:m2:mid", "B:m1:mid", "B:m2:mid", "G:m1:mid")
PAD_CASE = "B:m1:pad"
OFFSET_CASES = ("B:m1:mid", "B:m2:mid")
OFFSETS = ((0.5, 0.0), (0.0, 0.5), (0.5, 0.5))  # in units of the pitch s
DEPENDENCIES = ("scripts/epc90133_extract.py", "scripts/epc90133_power_loop.py", "scripts/read_epc90133_geometry.py",
                "results/gan/epc90133-power-loop.json", "results/gan/epc90133-gate-loop.json")


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def parse_deck(deck):
    nodes, segs, equivs = {}, [], []
    for line in deck.splitlines():
        if line.startswith("n"):
            m = re.match(r"(\S+) x=(\S+) y=(\S+) z=(\S+)", line)
            nodes[m.group(1)] = (float(m.group(2)), float(m.group(3)))
        elif line.startswith("E"):
            parts = line.split()
            w = float(re.search(r" w=(\S+)", line).group(1))
            segs.append((parts[1], parts[2], w))
        elif line.startswith(".equiv"):
            equivs.append(line.split()[1:])
    return nodes, segs, equivs


def grid_layer(name):
    """Layer of a grid node name n{layer}_{i}_{j}, or None for via and other nodes."""
    m = re.match(r"n(gtl|gbl|g\d)_\d+_\d+$", name)
    return m.group(1).upper() if m else None


def rect_pixels(b, x0, x1, y0, y1):
    r0, c0 = b.pixel(x0, y0)
    r1, c1 = b.pixel(x1, y1)
    return slice(max(r0, 0), r1 + 1), slice(max(c0, 0), c1 + 1)


def measure(b, deck, s, window, groups, via_xy):
    nodes, segs, equivs = parse_deck(deck)
    layers = sorted({grid_layer(n) for n in nodes} - {None})
    out = {"layers": {}}
    # grid lines of this deck (coarse and fine) per layer: the x and y values at which nodes sit
    for e in layers:
        lab = b.labels[e]
        enodes = {n: xy for n, xy in nodes.items() if grid_layer(n) == e}
        island_of = {n: int(lab[b.pixel(*xy)]) for n, xy in enodes.items()}
        islands = sorted(set(island_of.values()) - {0})
        xs = sorted({round(xy[0], 6) for xy in enodes.values()})
        ys = sorted({round(xy[1], 6) for xy in enodes.values()})
        # T2 holes
        wr = rect_pixels(b, window[0], window[2], window[1], window[3])
        sub = lab[wr]
        holes_all = np.zeros(sub.shape, bool)
        holes = []
        for isl in islands:
            m = sub == isl
            filled = ndimage.binary_fill_holes(m)
            hm = filled & ~m
            hl, nh = ndimage.label(hm)
            holes_all |= hm
            for k, sl in enumerate(ndimage.find_objects(hl), 1):
                hk = hl[sl] == k
                area = float(hk.sum()) * PITCH ** 2
                rows0 = wr[0].start + sl[0].start
                cols0 = wr[1].start + sl[1].start
                bx = (cols0 * PITCH, rows0 * PITCH, (cols0 + hk.shape[1] - 1) * PITCH, (rows0 + hk.shape[0] - 1) * PITCH)
                crossed = any(bx[0] <= x <= bx[2] and hk[:, round(x / PITCH) - cols0].any() for x in xs
                              if 0 <= round(x / PITCH) - cols0 < hk.shape[1]) or \
                    any(bx[1] <= y <= bx[3] and hk[round(y / PITCH) - rows0, :].any() for y in ys
                        if 0 <= round(y / PITCH) - rows0 < hk.shape[0])
                drills = [{"x": vx, "y": vy, "net": net, "group": grp} for vx, vy, net, grp in via_xy
                          if bx[0] - PITCH <= vx <= bx[2] + PITCH and bx[1] - PITCH <= vy <= bx[3] + PITCH
                          and hk[min(max(round(vy / PITCH) - rows0, 0), hk.shape[0] - 1),
                                 min(max(round(vx / PITCH) - cols0, 0), hk.shape[1] - 1)]]
                holes.append({"island": isl, "area_mm2": area, "eq_diameter_mm": 2 * math.sqrt(area / math.pi),
                              "bbox_mm": [round(v, 4) for v in bx], "crossed_by_grid_line": bool(crossed),
                              "drills": drills})
        # T1 overreach and T3 components
        n_seg = n_any = n_half = 0
        over_area = over_in_holes = seg_area = 0.0
        worst = []
        adj = {}
        for a, c, w in segs:
            if grid_layer(a) != e or grid_layer(c) != e:
                continue
            n_seg += 1
            (xa, ya), (xc, yc) = nodes[a], nodes[c]
            isl = island_of[a]
            if abs(ya - yc) < 1e-9:
                sl = rect_pixels(b, min(xa, xc), max(xa, xc), ya - w / 2, ya + w / 2 - PITCH / 2)
            else:
                sl = rect_pixels(b, xa - w / 2, xa + w / 2 - PITCH / 2, min(ya, yc), max(ya, yc))
            patch = lab[sl]
            bad = patch != isl
            frac = float(bad.mean()) if patch.size else 0.0
            seg_area += patch.size * PITCH ** 2
            over_area += float(bad.sum()) * PITCH ** 2
            hsl = (slice(sl[0].start - wr[0].start, sl[0].stop - wr[0].start),
                   slice(sl[1].start - wr[1].start, sl[1].stop - wr[1].start))
            hp = holes_all[hsl]
            if hp.shape == bad.shape:
                over_in_holes += float((bad & hp).sum()) * PITCH ** 2
            n_any += frac > 0
            if frac > 0.5:
                n_half += 1
                worst.append({"from": [round(xa, 4), round(ya, 4)], "to": [round(xc, 4), round(yc, 4)],
                              "overreach": round(frac, 3)})
            adj.setdefault(a, []).append(c)
            adj.setdefault(c, []).append(a)
        comps = {}
        seen = set()
        for n0 in enodes:
            if n0 in seen:
                continue
            stack, size = [n0], 0
            seen.add(n0)
            while stack:
                n1 = stack.pop()
                size += 1
                for n2 in adj.get(n1, ()):
                    if n2 not in seen:
                        seen.add(n2)
                        stack.append(n2)
            comps.setdefault(island_of[n0], []).append(size)
        split = {str(k): sorted(v, reverse=True) for k, v in comps.items() if len(v) > 1}
        big = [h for h in holes if h["eq_diameter_mm"] >= s / 2]
        out["layers"][e] = {
            "T1": {"plane_segments": n_seg, "with_overreach": int(n_any), "over_half": n_half,
                   "segment_area_mm2": seg_area, "overreach_area_mm2": over_area, "overreach_in_holes_mm2": over_in_holes,
                   "over_half_segments": worst[:40]},
            "T2": {"holes": len(holes), "holes_eq_d_ge_half_pitch": len(big),
                   "uncrossed_eq_d_ge_half_pitch": [h for h in big if not h["crossed_by_grid_line"]],
                   "holes_with_several_drills": [h for h in holes if len(h["drills"]) > 1],
                   "all_holes": holes},
            "T3": {"islands_with_nodes": len(islands), "split_islands": split},
        }
    # T4 attachments
    ends, shared = [], {}
    for eq in equivs:
        v = eq[0]
        m = re.match(r"nv(\d+)_(\w+?)_([du])$", v)
        if not m:
            continue
        k, e = int(m.group(1)), m.group(2).upper()
        grid_nodes = [n for n in eq[1:] if grid_layer(n)]
        vx, vy = via_xy_by_index[k][:2]
        d = min(math.hypot(nodes[n][0] - vx, nodes[n][1] - vy) for n in grid_nodes) if grid_nodes else None
        ends.append({"via": k, "layer": e, "nearest_mm": d, "attached": len(grid_nodes),
                     "group": via_xy_by_index[k][3]})
        for n in grid_nodes:
            shared.setdefault((e, n), set()).add(k)
    multi = {key: vs for key, vs in shared.items() if len(vs) > 1}
    by_group = {}
    for (e, n), vs in multi.items():
        for k in vs:
            g = via_xy_by_index[k][3]
            by_group.setdefault(g, set()).add(k)
    far = [x for x in ends if x["nearest_mm"] is not None and x["nearest_mm"] > s]
    out["T4"] = {"via_ends": len(ends), "max_nearest_mm": max((x["nearest_mm"] for x in ends if x["nearest_mm"] is not None),
                                                                default=None),
                 "ends_farther_than_pitch": far,
                 "shared_attachment_nodes": len(multi),
                 "max_vias_per_node": max((len(v) for v in multi.values()), default=1),
                 "vias_sharing_by_group": {g: len(v) for g, v in sorted(by_group.items(), key=lambda t: str(t[0]))}}
    lay = out["layers"]
    out["flags"] = {
        "F1_uncrossed_holes_ge_half_pitch": sum(len(l["T2"]["uncrossed_eq_d_ge_half_pitch"]) for l in lay.values()),
        "F2_segments_over_half": sum(l["T1"]["over_half"] for l in lay.values()),
        "F3_ends_farther_than_pitch": len(far),
        "F4_shared_attachment_nodes": len(multi),
        "F5_split_islands": sum(len(l["T3"]["split_islands"]) for l in lay.values()),
    }
    return out


via_xy_by_index = {}


def main():
    loop = json.loads(ex.LOOP.read_text(encoding="utf-8"))
    gate = json.loads(ex.GATE_LOOP.read_text(encoding="utf-8"))
    b = load_board()
    per_layer = via_layers(b)
    groups = loop["via_groups"]

    def group_of(x, y):
        for g in groups:
            x0, y0, x1, y1 = g["bbox_mm"]
            if x0 - 1e-3 <= x <= x1 + 1e-3 and y0 - 1e-3 <= y <= y1 + 1e-3:
                return g["id"]
        return None

    via_xy = []
    for k, v in enumerate(b.via_rows):
        net = b.net_of(v["layers"][0], v["x"], v["y"]) if v["layers"] else "none"
        g = group_of(v["x"], v["y"])
        via_xy_by_index[k] = (v["x"], v["y"], net, g)
        via_xy.append((v["x"], v["y"], net, g))

    rep = {"schema": "epc90133-mesh-topology-audit/1", "declared": "2026-10-02, before the first run (docstring)",
           "evaluator_sha256": sha("scripts/audit_epc90133_mesh_topology.py"),
           "dependencies_sha256": {p: sha(p) for p in DEPENDENCIES}, "decks": {}, "errors": []}

    def run(case, shift=None):
        variant, mesh, junction = case.split(":")
        s = ex.MESHES[mesh][0]
        lp = copy.deepcopy(loop)
        if shift:
            lp["fets"]["Q1"]["centre_mm"][0] += shift[0] * s
            lp["fets"]["Q2"]["centre_mm"][1] += shift[1] * s
        deck, ports, connected, stats = ex.build(b, lp, variant, mesh, junction, per_layer, gate)
        window = ex.G_WINDOW if variant == "G" else ex.WINDOW
        res = measure(b, deck, s, window, groups, via_xy)
        res["pitch_mm"] = s
        res["build"] = {"nodes": stats["nodes"], "segments": stats["segments"], "via": stats["via"],
                        "nodes_dropped_unconnected": stats["nodes_dropped_unconnected"],
                        "all_ports_connected": all(connected.values()),
                        "terminal_contacts_without_nodes": stats["terminal_contacts_without_nodes"]}
        return res

    for case in PRODUCTION + (PAD_CASE,):
        print(case, flush=True)
        rep["decks"][case] = run(case)
        print("  flags", rep["decks"][case]["flags"], flush=True)
    for case in OFFSET_CASES:
        for sh in OFFSETS:
            key = f"{case}@+{sh[0]}s,+{sh[1]}s"
            print(key, flush=True)
            try:
                rep["decks"][key] = run(case, sh)
                print("  flags", rep["decks"][key]["flags"], flush=True)
            except Exception as exc:  # recorded, does not change the outcome
                rep["errors"].append(f"{key}: {type(exc).__name__}: {exc}")
    rep["outcome"] = "audit complete" if all(c in rep["decks"] for c in PRODUCTION) else "incomplete"
    rep["flags_by_deck"] = {k: v["flags"] for k, v in rep["decks"].items()}
    OUTPUT.write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep["flags_by_deck"], indent=1))


if __name__ == "__main__":
    main()
