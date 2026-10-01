#!/usr/bin/env python3
"""Audit EPC's published EPC9165 files and screen them for probe access (deferred second-board candidate).

Owner, 1 October 2026 (plan section 9, item 10): EPC9165 is recorded as a candidate for a comparative
measurement; before any purchase, retrieve and audit its files and locate gate and switch-node probe access.
This script reads EPC's published files only. It identifies no physical board, measures nothing and extracts
no parasitics. Written and declared 1 October 2026, before its first run.

Document checks (as for EPC90133, scripts/audit_epc90133_board_files.py):
* checksums against devices/epc/epc9165-sources.json;
* PCB numbers named by the schematic, the Gerber files and the quick-start guide;
* copper layers in the Gerber extension report against the stackup;
* BOM reference designators against the layout print's Altium component tokens ("CO<ref>", with Altium's
  "_" -> "0" encoding applied to the BOM names).

Geometry screen (board millimetres, from the Gerbers, drill file and the layout print's assembly page):
G1 the assembly page (page 17) is placed in board coordinates by a scale and offset fitted to the six 6.2 mm
   plated holes; every hole maps within 0.15 mm.
G2 that page shows exactly four 3.0 x 5.0 mm outlines (EPC2302 bodies) and two 3.1 x 3.1 mm outlines (driver
   bodies); reported: whether each lies inside the heatsink footprint, taken as the mechanical-13 rectangle that
   contains the four 3.0 mm heatsink-mounting holes.
G3 exactly two pairs of 1.016 mm plated holes 2.54 +- 0.05 mm apart exist (the two unfitted 100 mil headers
   J1_F1/J1_F2 of the filter sheet; the guide calls J1_F1 a voltage-loop-gain injection/measurement point).
G4 nets by copper connectivity (all eight copper layers rasterized at 0.05 mm, joined through plated holes at
   their centres): for each phase (the two FET outlines nearest each other), exactly one net touches both of its
   FET outlines and no other FET outline (that phase's switch node).
Reported, not checked: the nets of each header pin; for each phase's switch-node net and for every net that
touches exactly one FET outline (gate candidates), every exposed contact (solder-mask opening on outer copper),
whether it lies inside the heatsink footprint, and its distance to the nearest FET outline of that net. A contact
outside the heatsink is where a probe could reach with the heatsink fitted; whether it is usable for a
high-bandwidth measurement (distance, return path, loading) is a separate engineering judgement.

Run 1 (1 October 2026) passed G1-G4 but is a failed run by design error, kept as
results/gan/epc9165-board-audit-run1-failed.json: it took each FET's nets from TOP copper inside its outline, but the
EPC2302s are on the BOTTOM side (the bottom paste has their stripe and gate pads inside the outlines; the top has
none), so it never saw the gate pads and its "inside the heatsink" ignored the side. Run 2, the one fix run,
changes only this: the FET side is the side whose paste has at least six pads inside every FET outline, and that
side's copper gives the FET nets; the heatsink side is the side whose solder mask is open around all four 3.0 mm
mounting holes; a contact counts as covered by the heatsink only if it is on the heatsink side and inside its
footprint. Its G4 switch-node nets agree with run 1's (checked by hand from the bottom pads before run 2). Run 2 crashed writing its report (a NumPy integer in the paste counts); fixed by a cast,
nothing else changed.

    PYTHONPATH=src python scripts/audit_epc9165_board_files.py   # results/gan/epc9165-board-audit.json
"""
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import sys
import zipfile

import numpy as np
import openpyxl
import pymupdf
from scipy import ndimage
import xlrd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from circuit_tools.gerber import load_layer, parse_excellon, rasterize  # noqa: E402

SOURCES = ROOT / "devices/epc/epc9165-sources.json"
GERBERS = ROOT / "vendor/epc/epc9165/gerbers"
PREFIX = "EPC9165B_B5309_Rev1_0_"
OUTPUT = ROOT / "results/gan/epc9165-board-audit.json"
COPPER = ("GTL", "G1", "G2", "G3", "G4", "G5", "G6", "GBL")
PITCH = 0.05
ASSEMBLY_PAGE = 16  # page 17
SCALE0, X_PT0, Y_PT0, Y_MM0 = 9.43, 85.0, 58.1, 111.98  # initial placement, refined by G1
SWITCHING_PARTS = ("Q1_P1", "Q2_P1", "Q1_P2", "Q2_P2", "U80_G1", "U80_G2", "R80_P1", "R81_P1", "R82_P1", "R83_P1",
                   "R70_G1", "R75_G1", "C81_G1", "C80_G1")


def verified(name):
    rec = json.loads(SOURCES.read_text(encoding="utf-8"))
    entry = next(f for f in rec["files"] if f["name"] == name)
    path = ROOT / entry["local_path"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != entry["sha256"]:
        raise SystemExit(f"{path} sha256 {digest} does not match the recorded {entry['sha256']}")
    return path


def read_bom(path):
    ws = openpyxl.load_workbook(path, data_only=True).active
    fitted, optional, section = {}, {}, None
    for row in ws.iter_rows(values_only=True):
        if row[0] == "Item":
            section = fitted if section is None else section
            continue
        if row[0] == "Optional Components":
            section = optional
            continue
        if row[0] == "Heatsink Kit":
            section = "kit"
            continue
        if isinstance(section, dict) and isinstance(row[0], int) and row[2]:
            for ref in str(row[2]).split(","):
                section[ref.strip()] = {"description": row[3], "manufacturer": row[4], "part_number": str(row[5])}
    return fitted, optional


def segments(prims, axis_tol=1e-3):
    out = []
    for p in prims:
        if p.kind == "line":
            (x0, y0), (x1, y1) = p.data[0], p.data[1]
            out.append((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
    return [s for s in out if abs(s[0] - s[2]) < axis_tol or abs(s[1] - s[3]) < axis_tol]


def rectangles(segs, w, h, tol=0.06):
    """Axis-aligned rectangles of size w x h (either orientation) whose four edges are all present."""
    found = set()
    for ww, hh in ((w, h), (h, w)):
        verts = [s for s in segs if abs(s[0] - s[2]) < 1e-3 and abs((s[3] - s[1]) - hh) < tol]
        horiz = [s for s in segs if abs(s[1] - s[3]) < 1e-3 and abs((s[2] - s[0]) - ww) < tol]
        for a, b in itertools.combinations(verts, 2):
            if abs(abs(a[0] - b[0]) - ww) < tol and abs(a[1] - b[1]) < tol:
                x0, x1, y0, y1 = min(a[0], b[0]), max(a[0], b[0]), a[1], a[3]
                if sum(1 for s in horiz if abs(s[0] - x0) < tol and abs(s[2] - x1) < tol
                       and (abs(s[1] - y0) < tol or abs(s[1] - y1) < tol)) >= 2:
                    found.add((round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)))
    return sorted(found)


def assembly_page(layout, holes62):
    """Assembly page lines in board mm, with the placement fitted to the 6.2 mm holes (G1)."""
    page = layout[ASSEMBLY_PAGE]
    draws = page.get_drawings()
    circles = [((d["rect"].x0 + d["rect"].x1) / 2, (d["rect"].y0 + d["rect"].y1) / 2) for d in draws
               if abs(d["rect"].width - d["rect"].height) < 0.5 and 5.5 * SCALE0 < d["rect"].width < 12 * SCALE0]
    to_mm = lambda x, y, s, xo, yo: (20.0 + (x - xo) / s, Y_MM0 - (y - yo) / s)
    pairs = []
    for h in holes62:
        c = min(circles, key=lambda c: math.dist(to_mm(*c, SCALE0, X_PT0, Y_PT0), (h.x, h.y)))
        pairs.append((c, (h.x, h.y)))
    # least squares: x_mm = ax + bx * x_pt, y_mm = ay - by * y_pt with one scale
    A, rhs = [], []
    for (xp, yp), (xm, ym) in pairs:
        A += [[xp, 1, 0], [-yp, 0, 1]]
        rhs += [xm, ym]
    (k, bx, by), *_ = np.linalg.lstsq(np.array(A), np.array(rhs), rcond=None)
    f = lambda x, y: (bx + k * x, by - k * y)
    resid = [math.dist(f(*c), m) for c, m in pairs]
    segs = []
    for d in draws:
        for it in d["items"]:
            if it[0] == "l":
                (x0, y0), (x1, y1) = f(it[1].x, it[1].y), f(it[2].x, it[2].y)
                segs.append((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
            elif it[0] == "re":
                r = it[1]
                (x0, y0), (x1, y1) = f(r.x0, r.y1), f(r.x1, r.y0)
                segs += [(x0, y0, x1, y0), (x0, y1, x1, y1), (x0, y0, x0, y1), (x1, y0, x1, y1)]
    segs = [s for s in segs if abs(s[0] - s[2]) < 1e-3 or abs(s[1] - s[3]) < 1e-3]
    return segs, {"mm_per_pt": float(k), "residuals_mm": resid, "pass": max(resid) <= 0.15}


class Nets:
    def __init__(self, bounds, drills):
        self.bounds, self.labels, self.parent = bounds, {}, {}
        for cu in COPPER:
            grid = rasterize(load_layer(GERBERS / f"{PREFIX}Gerbers.{cu}"), bounds, PITCH).grid
            self.labels[cu], _ = ndimage.label(grid)
        for d in drills:
            if not d.plated:
                continue
            keys = [(cu, int(self.labels[cu][self.idx(d.x, d.y)])) for cu in COPPER]
            keys = [k for k in keys if k[1]]
            for a, b in zip(keys, keys[1:]):
                self.union(a, b)

    def idx(self, x, y):
        return int(round((y - self.bounds[1]) / PITCH)), int(round((x - self.bounds[0]) / PITCH))

    def find(self, k):
        self.parent.setdefault(k, k)
        while self.parent[k] != k:
            self.parent[k] = self.parent[self.parent[k]]
            k = self.parent[k]
        return k

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra

    def at(self, cu, x, y):
        lab = int(self.labels[cu][self.idx(x, y)])
        return self.find((cu, lab)) if lab else None

    def in_rect(self, cu, r):
        i0, j0 = self.idx(r[0], r[1])
        i1, j1 = self.idx(r[2], r[3])
        labs = np.unique(self.labels[cu][i0:i1 + 1, j0:j1 + 1])
        return {self.find((cu, int(l))) for l in labs if l}


def contacts(nets, bounds):
    """Solder-mask openings on outer copper: centre, size and net."""
    out = []
    for side, cu, mask in (("top", "GTL", "GTS"), ("bottom", "GBL", "GBS")):
        m = rasterize(load_layer(GERBERS / f"{PREFIX}Gerbers.{mask}"), bounds, PITCH).grid
        lab, _ = ndimage.label((nets.labels[cu] > 0) & m)
        for k, sl in enumerate(ndimage.find_objects(lab), 1):
            reg = lab[sl] == k
            if reg.sum() * PITCH ** 2 < 0.01:
                continue
            ys, xs = np.nonzero(reg)
            r, c = ys[len(ys) // 2] + sl[0].start, xs[len(xs) // 2] + sl[1].start
            x = bounds[0] + (xs + sl[1].start) * PITCH
            y = bounds[1] + (ys + sl[0].start) * PITCH
            out.append({"side": side, "net": nets.find((cu, int(nets.labels[cu][r, c]))),
                        "cx": float((x.min() + x.max()) / 2), "cy": float((y.min() + y.max()) / 2),
                        "w": float(x.max() - x.min()), "h": float(y.max() - y.min())})
    return out


def inside(p, r):
    return r[0] <= p[0] <= r[2] and r[1] <= p[1] <= r[3]


def rect_dist(p, r):
    dx = max(r[0] - p[0], 0, p[0] - r[2])
    dy = max(r[1] - p[1], 0, p[1] - r[3])
    return math.hypot(dx, dy)


def main():
    bom_path = verified("EPC9165BOM.xlsx")
    gerber_zip = verified("EPC9165 Development Board Gerbers.zip")
    schematic = verified("EPC9165_Schematic.pdf")
    qsg = verified("EPC9165_qsg.pdf")
    fitted, optional = read_bom(bom_path)
    with zipfile.ZipFile(gerber_zip) as z:
        names = z.namelist()
        extrep = z.read(PREFIX + "Gerbers.EXTREP").decode("latin-1")
        layout = pymupdf.open(stream=z.read(PREFIX + "Layout.PDF"), filetype="pdf")
        stack = xlrd.open_workbook(file_contents=z.read(PREFIX + "Stackup.xls")).sheet_by_index(0)
    copper_files = re.findall(r"^\.(GTL|G\d+|GBL)\s+(.+?)\s*$", extrep, re.M)
    stack_rows = [[str(v).strip() for v in stack.row_values(r)] for r in range(stack.nrows)]
    stack_copper = [r for r in stack_rows if "Copper" in r]
    height = next((c for row in stack_rows for c in row if c.startswith("Height")), None)

    layout_refs = set(re.findall(r"\bCO([A-Za-z]+\w*)\b", layout[0].get_text()))
    encode = lambda ref: ref.replace("_", "0")
    bom_refs = set(fitted) | set(optional)
    sch_text = " ".join(p.get_text() for p in pymupdf.open(str(schematic)))
    qsg_text = " ".join(p.get_text() for p in pymupdf.open(str(qsg)))

    # geometry
    drills = parse_excellon((GERBERS / f"{PREFIX}NC Drill.TXT").read_text(errors="replace"))
    gtl = load_layer(GERBERS / f"{PREFIX}Gerbers.GTL")
    bounds = gtl.bounds()
    holes62 = [d for d in drills if abs(d.diameter - 6.2) < 0.05]
    hs_holes = [d for d in drills if abs(d.diameter - 3.0) < 0.05]
    segs, g1 = assembly_page(layout, holes62)
    fets = rectangles(segs, 3.0, 5.0)
    drivers = rectangles(segs, 3.1, 3.1)
    m13 = segments(load_layer(GERBERS / f"{PREFIX}Gerbers.GM13").primitives)
    hs_rects = []
    for a, b in itertools.combinations([s for s in m13 if abs(s[1] - s[3]) < 1e-3], 2):
        if abs(a[0] - b[0]) < 0.05 and abs(a[2] - b[2]) < 0.05 and abs(a[1] - b[1]) > 5:
            r = (a[0], min(a[1], b[1]), a[2], max(a[1], b[1]))
            if all(inside((h.x, h.y), r) for h in hs_holes):
                hs_rects.append(r)
    heatsink = min(hs_rects, key=lambda r: (r[2] - r[0]) * (r[3] - r[1])) if hs_rects else None
    g2 = {"fet_outlines": fets, "driver_outlines": drivers, "heatsink_rect_mm": heatsink,
          "pass": len(fets) == 4 and len(drivers) == 2 and heatsink is not None,
          "fets_inside_heatsink": [bool(heatsink and inside(((r[0] + r[2]) / 2, (r[1] + r[3]) / 2), heatsink)) for r in fets],
          "drivers_inside_heatsink": [bool(heatsink and inside(((r[0] + r[2]) / 2, (r[1] + r[3]) / 2), heatsink)) for r in drivers]}
    h1016 = [d for d in drills if abs(d.diameter - 1.016) < 0.01 and d.plated]
    headers = [(a, b) for a, b in itertools.combinations(h1016, 2) if abs(math.dist((a.x, a.y), (b.x, b.y)) - 2.54) <= 0.05]
    g3 = {"pairs": [[(a.x, a.y), (b.x, b.y)] for a, b in headers], "pass": len(headers) == 2}

    nets = Nets(bounds, drills)
    sides = {"top": ("GTL", "GTP", "GTS"), "bottom": ("GBL", "GBP", "GBS")}
    paste_pads = {}
    for side, (_, paste, _) in sides.items():
        lab, _ = ndimage.label(rasterize(load_layer(GERBERS / f"{PREFIX}Gerbers.{paste}"), bounds, PITCH).grid)
        cents = [((sl[1].start + sl[1].stop) / 2 * PITCH + bounds[0], (sl[0].start + sl[0].stop) / 2 * PITCH + bounds[1])
                 for sl in ndimage.find_objects(lab)]
        paste_pads[side] = [int(sum(bool(inside(c, r)) for c in cents)) for r in fets]
    fet_side = next((sd for sd, n in paste_pads.items() if n and min(n) >= 6), None)
    fet_cu = sides[fet_side][0] if fet_side else "GTL"
    hs_side = None
    for side, (_, _, mask) in sides.items():
        m = rasterize(load_layer(GERBERS / f"{PREFIX}Gerbers.{mask}"), bounds, PITCH).grid
        if hs_holes and all(m[nets.idx(h.x + 1.0, h.y)] or m[nets.idx(h.x - 1.0, h.y)] for h in hs_holes):
            hs_side = side if hs_side is None else "both"
    fet_nets = [nets.in_rect(fet_cu, r) for r in fets]
    # phases: pair each FET with its nearest neighbour
    order = sorted(range(len(fets)), key=lambda i: fets[i][0])
    phases = [order[:2], order[2:]] if len(fets) == 4 else []
    name = {}
    g4_ok = bool(phases)
    for k, ph in enumerate(phases, 1):
        cand = [n for n in fet_nets[ph[0]] & fet_nets[ph[1]]
                if not any(n in fet_nets[j] for j in range(len(fets)) if j not in ph)]
        g4_ok &= len(cand) == 1
        if len(cand) == 1:
            name[cand[0]] = f"SW_phase{k}"
    single = {}
    for i, ns in enumerate(fet_nets):
        for n in ns:
            if sum(n in o for o in fet_nets) == 1:
                single.setdefault(n, i)
    for n, i in single.items():
        name.setdefault(n, f"one_fet_net_{i}")
    shared_all = set.intersection(*fet_nets) if fet_nets else set()
    for n in shared_all:
        name.setdefault(n, "touches_all_four_FETs")

    header_nets = []
    for a, b in headers:
        pins = []
        for d in (a, b):
            roots = {nets.at(cu, d.x, d.y) for cu in COPPER} - {None}
            pins.append({"xy_mm": [d.x, d.y], "nets": sorted(name.get(r, "other") for r in roots),
                         "touches_fets": sorted({i for r in roots for i, ns in enumerate(fet_nets) if r in ns})})
        header_nets.append(pins)

    cs = contacts(nets, bounds)
    access = {}
    for n, label in name.items():
        if label.startswith("touches_all"):
            continue
        touched = [i for i, ns in enumerate(fet_nets) if n in ns]
        rows = []
        for c in cs:
            if c["net"] != n:
                continue
            p = (c["cx"], c["cy"])
            rows.append({"side": c["side"], "xy_mm": [round(p[0], 2), round(p[1], 2)], "size_mm": [round(c["w"], 2), round(c["h"], 2)],
                         "inside_heatsink": bool(heatsink and c["side"] == hs_side and inside(p, heatsink)),
                         "distance_to_its_fet_mm": round(min(rect_dist(p, fets[i]) for i in touched), 2)})
        outside = [r for r in rows if not r["inside_heatsink"]]
        access[label] = {"fets": touched, "contacts": len(rows), "contacts_outside_heatsink": len(outside),
                         "nearest_outside": sorted(outside, key=lambda r: r["distance_to_its_fet_mm"])[:5]}

    report = {
        "schema": "epc9165-board-audit/1",
        "scope": "EPC's published EPC9165 files; consistency and probe-access screen only. Not the identity of a physical board.",
        "declared": "2026-10-01, before the first run (script docstring)",
        "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "board_numbers": {"gerber_files": sorted({m for n in names for m in re.findall(r"B\d{4}_Rev\d+_\d+", n)}),
                          "schematic": sorted(set(re.findall(r"B\d{4} Rev\s?\d+\.\d+", sch_text))),
                          "quick_start_guide": sorted(set(re.findall(r"B\d{4}", qsg_text)))},
        "copper": {"gerber_copper_layers": [{"extension": e, "description": d} for e, d in copper_files],
                   "stackup_copper_layers": len(stack_copper), "stackup_height": height,
                   "consistent": len(copper_files) == len(stack_copper)},
        "reference_designators": {"bom_fitted": len(fitted), "bom_optional": len(optional), "layout_components": len(layout_refs),
                                  "bom_not_in_layout": sorted(r for r in bom_refs if encode(r) not in layout_refs),
                                  "layout_not_in_bom": sorted(r for r in layout_refs if r not in {encode(b) for b in bom_refs})},
        "switching_parts": {r: fitted.get(r) or optional.get(r) for r in SWITCHING_PARTS},
        "driver_labels": {"bom": sorted({v["part_number"] for k, v in fitted.items() if k.startswith("U80")}),
                          "schematic": sorted(set(re.findall(r"MPQ\d+\w*", sch_text))),
                          "quick_start_guide": sorted(set(re.findall(r"MPQ\d+\w*", qsg_text)))},
        "geometry": {"board_bounds_mm": bounds, "fet_side": fet_side, "paste_pads_in_fet_outlines": paste_pads,
                     "heatsink_side": hs_side, "G1_placement": g1, "G2_outlines": g2, "G3_headers": g3,
                     "G4_switch_nodes": {"pass": g4_ok, "phases_fet_indices": phases},
                     "header_pin_nets": header_nets, "probe_access": access},
    }
    OUTPUT.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    show = {k: report[k] for k in ("board_numbers", "copper", "reference_designators", "driver_labels")}
    show["copper"] = {k: v for k, v in show["copper"].items() if k != "gerber_copper_layers"}
    print(json.dumps(show, indent=1, ensure_ascii=False))
    g = report["geometry"]
    print("FET side", fet_side, paste_pads, "heatsink side", hs_side)
    print("G1", g1["pass"], [round(r, 3) for r in g1["residuals_mm"]], "G2", g2["pass"], "G3", g3["pass"], "G4", g4_ok)
    print(json.dumps({"outlines": g2, "headers": header_nets, "access": access}, indent=1))


if __name__ == "__main__":
    main()
