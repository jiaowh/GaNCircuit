#!/usr/bin/env python3
"""Qualify a bounded KiCad geometry-edit workflow on the reconstructed EPC90133 board (track R, before G5).

Declared 7 October 2026 before the first run of this script (audit at 0f07a6a, finding 2; plan section 10 item 4).

Problem. The reconstruction (scripts/epc90133_reconstruct_final.py) writes each EPC copper island as a KiCad zone
whose outline is the island's exterior, with EPC's fill frozen. A KiCad refill regenerates the fill from KiCad's
single clearance rule, so it fills EPC's holes (the audit: 1-2 % area change in the power/gate window, isolated
copper 13 -> 43, two solder-mask bridges). A labelled feasibility probe (7 October, scratch only, not a result)
reproduced the audit's numbers exactly with a plain refill, and showed that adding a copper-fill keep-out for each
stock hole makes the refill reproduce EPC's copper: with drills excluded every difference vanished at a 10 um
tolerance on all eight layers, isolated copper 13, no mask bridges. The residue is KiCad's arc approximation
(maximum error 5 um by default).

Workflow (this script defines it):
* Editable base: the saved reconstruction (board SHA-256 checked against results/gan/epc90133-reconstruct-verify.json)
  plus one KiCad rule area per stock-hole piece: copper pour not allowed, tracks/vias/pads/footprints allowed. A
  piece is an interior ring of an EPC copper island, minus the islands lying inside it, split into hole-free
  polygons. Written to git-ignored vendor/epc/epc90133/reconstruction/edit/.
* An edit is an ordered list of primitives applied to the base TEXT (KiCad-saved boards are outputs, never edited):
  move_footprint(ref, dx, dy); move_via(x, y, dx, dy), which also translates every zone and keep-out lying inside the
  via's clearance holes (the holes, on each layer, of a large island that contain the via centre), so EPC's hole
  shape moves with the via and the old hole fills. Coordinates are EPC board millimetres (y up).
* Each board is refilled by kicad-cli (circuit_tools.kicad.run_drc with --refill-zones --save-board, then a fresh
  DRC of the saved board), and Gerbers (8 copper, F/B mask, F/B paste) and IPC-D-356 are exported. A copy with every
  zone and keep-out removed gives pad-and-via-only copper for the expected-geometry checks.

Comparisons: drilled areas excluded (EPC's drills plus, for edits, old and new positions of moved drills), 1 mm
board-edge margin excluded, geometry matched within TOL = 0.010 mm both ways: area(A - dilate(B, TOL)) and
area(B - dilate(A, TOL)) each <= 1e-4 mm^2.

Cases and checks:
* W0 no edit. W0a copper equals EPC's Gerbers on all eight layers. W0b mask and paste equal EPC's. W0c DRC: 0
  unconnected items, no shorting_items, no solder_mask_bridge, isolated_copper count 13 (the stock netless islands),
  no clearance item below 0.150114 - 0.001 mm. W0d IPC-D-356 pad nets equal those of the saved board's export.
* W1 move_footprint Ci7 by dx = -0.30 mm (the audit's "move one component": pads stay on their own VIN/GND copper,
  mask and paste move). W2 move_via (24.16, 36.40) GND by dx = +0.20 mm (clearance holes on In5/In6 move; the old
  holes fill). For each:
  - Wa outside the edit window (old and new object extent buffered by 1.0 mm) copper equals W0's refilled copper on
    every layer within 0.001 mm;
  - Wb inside the window copper equals the expected geometry within TOL: W1, W0 copper plus the edited board's pad
    and via copper; W2, per layer ((W0 + H) - T(H)) + T(W0 * H) + pad/via copper, H the old clearance holes, T the
    translation (on layers without holes this is W0 plus pad/via copper);
  - Wc DRC as W0c, and no DRC type absent from W0's report;
  - Wd IPC-D-356 pad nets equal W0's (by pad name); W2 also: a GND via at the new position, none at the old;
  - We mask and paste: W1 equal EPC's except Ci7's openings, which equal EPC's translated by T within TOL; W2 equal
    EPC's;
  - Wf reversibility: the edit list [edit, inverse edit] gives copper equal to W0's within 0.001 mm.
Qualification passes only if every check passes. Failed or incomplete runs are kept. Time limit 1800 s per kicad-cli
call (probe: refill with keep-outs 170 s, plain 90 s). A pass qualifies this workflow for these two primitives on
this board; it is not fabrication approval, and edits that need new copper shapes (moving a part across a net
boundary, L3) need a further primitive and check.

Output: results/gan/epc90133-edit-workflow.json; exit 0 if qualified, 2 otherwise.
"""
import argparse
import collections
import hashlib
import json
import re
import shutil
import sys
import uuid
from pathlib import Path

from shapely.affinity import affine_transform, translate
from shapely.geometry import Point, Polygon, box as sbox
from shapely.ops import unary_union
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from circuit_tools.gerber import load_layer, parse_excellon
from circuit_tools.kicad import KiCadError, run_drc, sha256_file
from read_epc90133_geometry import BOARD, GERBERS, LAYERS, PREFIX
from epc90133_reconstruct import KICAD_CLI, KICAD_LAYER, OUT, box, layer_geometry, polygons, split_holes, to_kicad
from epc90133_reconstruct_nets import xy
from verify_epc90133_reconstruction import read_ipcd356

import subprocess

TOL, TIGHT, AREA_EPS = 0.010, 0.001, 1e-4
EDGE = 1.0
WINDOW_PAD = 1.0
TIMEOUT = 1800
RULE_MIN = 0.150114 - 0.001
STOCK_ISOLATED = 13
VERIFY = ROOT / "results/gan/epc90133-reconstruct-verify.json"
WORK = OUT / "edit"
MASKS = {"F.Mask": "GTS", "B.Mask": "GBS", "F.Paste": "GTP", "B.Paste": "GBP"}
EDITS = {
    "W0": [],
    "W1": [("move_footprint", "Ci7", -0.30, 0.0)],
    "W2": [("move_via", 24.16, 36.40, 0.20, 0.0)],
}
INVERSE = {"W1": [("move_footprint", "Ci7", 0.30, 0.0)], "W2": [("move_via", 24.36, 36.40, -0.20, 0.0)]}
HELPERS = ("src/circuit_tools/gerber.py", "src/circuit_tools/kicad.py", "scripts/read_epc90133_geometry.py",
           "scripts/epc90133_reconstruct.py", "scripts/epc90133_reconstruct_nets.py",
           "scripts/verify_epc90133_reconstruction.py")


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def epc_layers():
    return {e: polygons(layer_geometry(load_layer(GERBERS / f"{PREFIX}Gerbers.{e}")).intersection(box(*BOARD).buffer(1.0)))
            for e in LAYERS}


def keepouts(geo):
    """Rule-area lines: every interior ring of an island, minus islands inside it, split into hole-free pieces."""
    lines = []
    for e in LAYERS:
        isl, tree = geo[e], STRtree(geo[e])
        for p in isl:
            for ring in p.interiors:
                h = Polygon(ring)
                inner = [isl[int(j)] for j in tree.query(h) if h.contains(isl[int(j)].representative_point())]
                k = h.difference(unary_union(inner)) if inner else h
                for piece in polygons(k):
                    for q in split_holes(piece):
                        if q.area >= 1e-6:
                            lines.append(f'\t(zone (net 0) (net_name "") (layer "{KICAD_LAYER[e]}") (uuid "{uuid.uuid4()}") '
                                         f'(name "stock-hole") (hatch edge 0.5) (connect_pads (clearance 0)) '
                                         f'(min_thickness 0.01) (filled_areas_thickness no) (keepout (tracks allowed) '
                                         f'(vias allowed) (pads allowed) (copperpour not_allowed) (footprints allowed)) '
                                         f'(fill (thermal_gap 0.5) (thermal_bridge_width 0.5)) '
                                         f'(polygon (pts {xy(list(q.exterior.coords)[:-1])})))\n')
    return lines


def via_holes(geo, x, y, moved=None):
    """Per layer, the clearance hole (interior ring of an island larger than 1 mm^2, under 2 mm^2) containing (x, y).

    moved: {(layer, index): current polygon} for holes already translated by earlier edits in the same list; they
    are looked up at their current position and no longer at their stock one."""
    p, out = Point(x, y), {}
    moved = moved or {}
    for e in LAYERS:
        k = 0
        for q in geo[e]:
            if q.area > 1.0:
                for r in q.interiors:
                    h = moved.get((e, k), Polygon(r))
                    if h.area < 2.0 and h.contains(p):
                        out[e] = (k, h)
                    k += 1
    return out


def shift_pts(line, dx, dy):
    """Translate every (xy ...) in a zone line by an EPC-frame offset (KiCad y is down)."""
    return re.sub(r"\(xy ([-\d.]+) ([-\d.]+)\)",
                  lambda m: f"(xy {float(m.group(1)) + dx:.6f} {float(m.group(2)) - dy:.6f})", line)


def zone_layer_and_poly(line):
    lay = re.search(r'\(layer "([^"]+)"\)', line).group(1)
    pts = re.search(r"\(polygon \(pts (.*?)\)\)", line).group(1)
    xs = [(float(a) - 100.0, 150.0 - float(b)) for a, b in re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", pts)]
    return lay, Polygon(xs)


def apply_edits(text, edits, geo):
    lines = text.splitlines(keepends=True)
    log, moved_holes = [], {}
    for op in edits:
        if op[0] == "move_footprint":
            _, ref, dx, dy = op
            pat = re.compile(rf'^(\t\(footprint "EPC90133:{re.escape(ref)}" \(layer "[FB]\.Cu"\) \(uuid "[^"]+"\) \(at )'
                             r'([-\d.]+) ([-\d.]+)')
            hits = [i for i, ln in enumerate(lines) if pat.match(ln)]
            if len(hits) != 1:
                raise SystemExit(f"move_footprint {ref}: {len(hits)} matches")
            i = hits[0]
            lines[i] = pat.sub(lambda m: f"{m.group(1)}{float(m.group(2)) + dx:.6f} {float(m.group(3)) - dy:.6f}", lines[i], 1)
            log.append({"op": op, "footprint_line": i})
        elif op[0] == "move_via":
            _, x, y, dx, dy = op
            kx, ky = to_kicad(x, y)
            vi = [i for i, ln in enumerate(lines) if ln.startswith("\t(via (at ")
                  and (lambda m: abs(float(m.group(1)) - kx) < 0.02 and abs(float(m.group(2)) - ky) < 0.02)(
                      re.match(r"\t\(via \(at ([-\d.]+) ([-\d.]+)\)", ln))]
            if len(vi) != 1:
                raise SystemExit(f"move_via ({x}, {y}): {len(vi)} matches")
            m = re.match(r"\t\(via \(at ([-\d.]+) ([-\d.]+)\)", lines[vi[0]])
            vx, vy = float(m.group(1)) - 100.0, 150.0 - float(m.group(2))
            lines[vi[0]] = lines[vi[0]].replace(m.group(0), f"\t(via (at {float(m.group(1)) + dx:.6f} {float(m.group(2)) - dy:.6f})", 1)
            holes = via_holes(geo, vx, vy, moved_holes)
            moved = collections.Counter()
            for i, ln in enumerate(lines):
                if ln.startswith("\t(zone "):
                    lay, poly = zone_layer_and_poly(ln)
                    e = next(k for k, v in KICAD_LAYER.items() if v == lay)
                    if e in holes and holes[e][1].buffer(1e-4).contains(poly):
                        lines[i] = shift_pts(ln, dx, dy)
                        moved[lay] += 1
            for e, (k, h) in holes.items():
                moved_holes[(e, k)] = translate(h, dx, dy)
            log.append({"op": op, "via_epc_xy": [vx, vy], "hole_layers": sorted(KICAD_LAYER[e] for e in holes),
                        "zones_and_keepouts_translated": dict(moved)})
        else:
            raise SystemExit(f"unknown edit {op}")
    return "".join(lines), log


def strip_zones(text):
    return "".join(ln for ln in text.splitlines(keepends=True) if not ln.lstrip().startswith("(zone "))


def export(board, out, layers):
    out.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([str(KICAD_CLI), "pcb", "export", "gerbers", "--layers", ",".join(layers), "--no-protel-ext",
                        "-o", str(out) + "\\", str(board)], capture_output=True, text=True, timeout=TIMEOUT)
    if r.returncode != 0:
        raise KiCadError(f"gerber export failed {r.returncode}: {r.stderr[-800:]}")
    return {L: next(p for p in out.iterdir() if p.name.endswith(L.replace(".", "_") + ".gbr")) for L in layers}


def gerber_geom(path):
    return affine_transform(layer_geometry(load_layer(path)), [1, 0, 0, 1, -100.0, 150.0])


def match(a, b, tol):
    ab, ba = a.difference(b.buffer(tol, 8)).area, b.difference(a.buffer(tol, 8)).area
    return {"a_not_in_b_mm2": ab, "b_not_in_a_mm2": ba, "pass": ab <= AREA_EPS and ba <= AREA_EPS}


def build(name, text, run_dir):
    """Write, refill, DRC, export a board; returns geometry and records."""
    d = run_dir / name
    d.mkdir(parents=True, exist_ok=True)
    board = d / "epc90133.kicad_pcb"
    board.write_text(text, encoding="utf-8")
    shutil.copy(OUT / "epc90133.kicad_pro", d / "epc90133.kicad_pro")
    refill = run_drc(KICAD_CLI, board, d, "refill", extra=("--refill-zones", "--save-board"), timeout=TIMEOUT)
    drc = run_drc(KICAD_CLI, board, d, "drc", timeout=TIMEOUT)
    files = export(board, d / "gerbers", list(KICAD_LAYER.values()) + list(MASKS))
    ipc = d / "board.d356"
    r = subprocess.run([str(KICAD_CLI), "pcb", "export", "ipcd356", "-o", str(ipc), str(board)],
                       capture_output=True, text=True, timeout=TIMEOUT)
    if r.returncode != 0:
        raise KiCadError(f"ipcd356 export failed {r.returncode}")
    bare = d / "bare"
    bare.mkdir(exist_ok=True)
    (bare / "epc90133.kicad_pcb").write_text(strip_zones(text), encoding="utf-8")
    shutil.copy(OUT / "epc90133.kicad_pro", bare / "epc90133.kicad_pro")
    bfiles = export(bare / "epc90133.kicad_pcb", bare / "gerbers", list(KICAD_LAYER.values()))
    vias = [(float(a) - 100.0, 150.0 - float(b)) for a, b in
            re.findall(r"\(via\s+\(at ([-\d.]+) ([-\d.]+)\)", board.read_text(encoding="utf-8"))]
    return {"dir": d, "board_sha256": sha256_file(board), "refill_report_sha256": refill["report_sha256"],
            "drc": drc["report"], "drc_report_sha256": drc["report_sha256"], "kicad_version": drc["kicad_version"],
            "copper": {L: gerber_geom(files[L]) for L in KICAD_LAYER.values()},
            "masks": {L: gerber_geom(files[L]) for L in MASKS},
            "pads": {L: gerber_geom(bfiles[L]) for L in KICAD_LAYER.values()},
            "nets": {r_["key"]: r_["net"] for r_ in read_ipcd356(ipc)}, "vias": vias}


def drc_summary(d):
    types = collections.Counter(v["type"] for v in d.get("violations", []))
    low = [v for v in d.get("violations", []) if v["type"] == "clearance"
           and (m := re.search(r"actual ([\d.]+) mm", v.get("description", ""))) and float(m.group(1)) < RULE_MIN]
    ok = (not d.get("unconnected_items") and not types.get("shorting_items") and not types.get("solder_mask_bridge")
          and types.get("isolated_copper", 0) == STOCK_ISOLATED and not low)
    return {"types": dict(types), "unconnected": len(d.get("unconnected_items", [])), "clearance_below_rule": len(low),
            "pass": ok}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-edit-workflow.json")
    args = ap.parse_args()
    saved = OUT / "epc90133.kicad_pcb"
    ident = json.loads(VERIFY.read_text(encoding="utf-8"))["identity"]
    if sha256_file(saved) != ident["board"]["sha256"]:
        raise SystemExit("saved board is not the board the readback verifier checked")
    ipc_ref = ROOT / ident["ipcd356"]["path"]
    if sha256_file(ipc_ref) != ident["ipcd356"]["sha256"]:
        raise SystemExit("the verifier's IPC-D-356 export changed")
    run_dir = WORK / ("run-" + uuid.uuid4().hex[:10])
    run_dir.mkdir(parents=True)
    report = {"schema": "epc90133-edit-workflow/1", "evaluator_sha256": sha256(__file__),
              "input_manifest": {"saved_board": sha256_file(saved), "project": sha256_file(OUT / "epc90133.kicad_pro"),
                                 "verify_report": sha256(VERIFY),
                                 "helpers": {h: sha256(ROOT / h) for h in HELPERS}},
              "tolerances_mm": {"geometry": TOL, "outside_window": TIGHT, "area_eps_mm2": AREA_EPS},
              "edits": {k: [list(o) for o in v] for k, v in EDITS.items()},
              "evidence_directory": str(run_dir.relative_to(ROOT)), "checks": {}}

    def save(outcome):
        report["outcome"] = outcome
        args.output.write_text(json.dumps(report, indent=1, default=str) + "\n")

    geo = epc_layers()
    holes = parse_excellon((GERBERS / f"{PREFIX}NC Drill.TXT").read_text(encoding="latin-1"))
    drill_disks = [Point(h.x, h.y).buffer(h.diameter / 2, 64) for h in holes]
    drills = unary_union(drill_disks)
    interior = sbox(BOARD[0] + EDGE, BOARD[1] + EDGE, BOARD[2] - EDGE, BOARD[3] - EDGE)
    base_text = saved.read_text(encoding="utf-8").rstrip()
    ko = keepouts(geo)
    base_text = base_text[:-1] + "".join(ko) + ")\n"
    report["keepout_pieces"] = len(ko)
    epc = {KICAD_LAYER[e]: unary_union(geo[e]) for e in LAYERS}
    epc_masks = {L: layer_geometry(load_layer(GERBERS / f"{PREFIX}Gerbers.{s}")) for L, s in MASKS.items()}
    ref_nets = {r_["key"]: r_["net"] for r_ in read_ipcd356(ipc_ref)}

    try:
        b0 = build("W0", base_text, run_dir)
    except KiCadError as exc:
        report["checks"]["W0"] = {"error": str(exc)}
        save("failed (W0 build)")
        return 2
    reg = interior.difference(drills)
    w0 = {"W0a_copper": {L: match(epc[L].intersection(reg), b0["copper"][L].intersection(reg), TOL) for L in epc},
          "W0b_mask_paste": {L: match(epc_masks[L].intersection(interior), b0["masks"][L].intersection(interior), TOL)
                             for L in MASKS},
          "W0c_drc": drc_summary(b0["drc"]),
          "W0d_nets": {"reference": "saved board's IPC-D-356 (verify report)" if ref_nets else "missing",
                       "pass": ref_nets is not None and ref_nets == b0["nets"],
                       "differences": None if ref_nets is None else
                       sorted(k for k in set(ref_nets) | set(b0["nets"]) if ref_nets.get(k) != b0["nets"].get(k))[:20]},
          "board_sha256": b0["board_sha256"], "drc_report_sha256": b0["drc_report_sha256"],
          "kicad_version": b0["kicad_version"]}
    w0["pass"] = (all(v["pass"] for v in w0["W0a_copper"].values()) and all(v["pass"] for v in w0["W0b_mask_paste"].values())
                  and w0["W0c_drc"]["pass"] and w0["W0d_nets"]["pass"])
    report["checks"]["W0"] = w0
    save("running")
    print("W0", w0["pass"], {L: (round(v["a_not_in_b_mm2"], 6), round(v["b_not_in_a_mm2"], 6)) for L, v in w0["W0a_copper"].items()},
          w0["W0c_drc"], flush=True)

    all_pass = w0["pass"]
    for case, edits in EDITS.items():
        if case == "W0":
            continue
        rec = {}
        try:
            text, log = apply_edits(base_text, edits, geo)
            b1 = build(case, text, run_dir)
            rtext, rlog = apply_edits(base_text, edits + INVERSE[case], geo)
            br = build(case + "-reverse", rtext, run_dir)
        except (KiCadError, SystemExit) as exc:
            report["checks"][case] = {"error": str(exc)}
            all_pass = False
            save("running")
            continue
        op = edits[0]
        dx, dy = op[-2], op[-1]
        if op[0] == "move_footprint":
            ref = op[1]
            centres = {"Ci7": [(26.85, 33.83), (26.85, 35.28)]}[ref]
            opens = [p for p in polygons(epc_masks["F.Mask"]) if any(p.contains(Point(c)) for c in centres)]
            if len(opens) != 2:
                raise SystemExit(f"{ref}: expected two mask openings, found {len(opens)}")
            extent = unary_union(opens)
            moved_drills = []
            hole_by_layer = {}
        else:
            x, y = op[1], op[2]
            hole_by_layer = {KICAD_LAYER[e]: h for e, (_, h) in via_holes(geo, x, y).items()}
            extent = unary_union([Point(x, y).buffer(0.2)] + list(hole_by_layer.values()))
            moved_drills = [k for k, h in enumerate(holes) if abs(h.x - x) < 0.02 and abs(h.y - y) < 0.02]
        window = unary_union([extent, translate(extent, dx, dy)]).buffer(WINDOW_PAD)
        new_drills = [translate(drill_disks[k], dx, dy) for k in moved_drills]
        reg_e = interior.difference(unary_union([drills] + new_drills))
        outside, inside = reg_e.difference(window), reg_e.intersection(window)
        wa = {L: match(b0["copper"][L].intersection(outside), b1["copper"][L].intersection(outside), TIGHT)
              for L in KICAD_LAYER.values()}
        wb = {}
        for L in KICAD_LAYER.values():
            w0c = b0["copper"][L]
            if L in hole_by_layer:
                H = hole_by_layer[L]
                expect = w0c.union(H).difference(translate(H, dx, dy)).union(translate(w0c.intersection(H), dx, dy))
            else:
                expect = w0c
            expect = expect.union(b1["pads"][L])
            wb[L] = match(expect.intersection(inside), b1["copper"][L].intersection(inside), TOL)
        dsum = drc_summary(b1["drc"])
        dsum["new_types"] = sorted(set(dsum["types"]) - set(w0["W0c_drc"]["types"]))
        dsum["pass"] = dsum["pass"] and not dsum["new_types"]
        nets_ok = b1["nets"] == b0["nets"]
        wd = {"pad_nets_equal_W0": nets_ok}
        if op[0] == "move_via":
            nx, ny = op[1] + dx, op[2] + dy
            wd["via_at_new"] = any(abs(a - nx) < 0.01 and abs(b - ny) < 0.01 for a, b in b1["vias"])
            wd["via_at_old_absent"] = not any(abs(a - op[1]) < 0.01 and abs(b - op[2]) < 0.01 for a, b in b1["vias"])
            ipc_vias = [ln for ln in (b1["dir"] / "board.d356").read_text(encoding="latin-1").splitlines()
                        if ln[:3] == "317" and ln[20:26].strip() == "VIA"]
            wd["new_via_net"] = next((ln[3:17].strip() for ln in ipc_vias
                                      if (m := re.search(r"X([+-]\d+)Y([+-]\d+)", ln[31:]))
                                      and abs(int(m.group(1)) / 10000 * 25.4 - (nx + 100.0)) < 0.02
                                      and abs(-int(m.group(2)) / 10000 * 25.4 - (150.0 - ny)) < 0.02), None)
            wd["pass"] = nets_ok and wd["via_at_new"] and wd["via_at_old_absent"] and wd["new_via_net"] == "GND"
        else:
            wd["pass"] = nets_ok
        we = {}
        for L in MASKS:
            ref_m = epc_masks[L]
            if op[0] == "move_footprint" and L in ("F.Mask", "F.Paste"):
                own = [p for p in polygons(ref_m) if p.intersects(extent)]
                own_u = unary_union(own)
                ref_m = ref_m.difference(own_u).union(translate(own_u, dx, dy))
            we[L] = match(ref_m.intersection(interior), b1["masks"][L].intersection(interior), TOL)
        wf = {L: match(b0["copper"][L].intersection(reg), br["copper"][L].intersection(reg), TIGHT)
              for L in KICAD_LAYER.values()}
        rec = {"edit_log": log, "reverse_log": rlog, "window_bounds": list(window.bounds),
               "Wa_outside_window": wa, "Wb_inside_window": wb, "Wc_drc": dsum, "Wd_connectivity": wd,
               "We_mask_paste": we, "Wf_reversibility": wf,
               "board_sha256": b1["board_sha256"], "reverse_board_sha256": br["board_sha256"],
               "inside_window_change_mm2": {L: b0["copper"][L].symmetric_difference(b1["copper"][L]).intersection(inside).area
                                            for L in KICAD_LAYER.values()}}
        rec["pass"] = (all(v["pass"] for v in wa.values()) and all(v["pass"] for v in wb.values()) and dsum["pass"]
                       and wd["pass"] and all(v["pass"] for v in we.values()) and all(v["pass"] for v in wf.values()))
        all_pass = all_pass and rec["pass"]
        report["checks"][case] = rec
        save("running")
        print(case, rec["pass"], "Wa", all(v["pass"] for v in wa.values()), "Wb", {L: v["pass"] for L, v in wb.items()},
              "Wc", dsum, "Wd", wd, "We", {L: v["pass"] for L, v in we.items()}, "Wf", all(v["pass"] for v in wf.values()),
              flush=True)
    save("qualified" if all_pass else "not qualified")
    print("outcome", report["outcome"])
    return 0 if all_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
