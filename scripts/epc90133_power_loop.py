#!/usr/bin/env python3
"""Power-loop geometry of the stock EPC90133 (B5253 Rev 2.0): contacts, footprints, via groups, ports (G3).

Step 1 of the exploratory extraction (owner review, 29 September 2026). It locates the
component contacts of the power loop, checks the two EPC2302 footprints, groups the loop's
vias with the layers they connect, fixes the extraction ports and renders an annotated
overlay for inspection. It extracts nothing.

Contacts. Paste openings locate the parts, but they are stencil apertures, not pads. A
contact is the solder-mask opening over copper: the EPC2302 land is solder-mask defined
(datasheet p. 11), and fab note 7 makes the mask 1:1 with the Gerber (mask-to-copper
registration +-0.003 in). Component windows are rasterized at 5 um, the board at 1 mil.

Declared checks (29 September 2026, before the first run):
C1 every paste opening in the component windows lies on mask-open copper (>= 95% of its pixels);
C2 each EPC2302 footprint has seven contacts, and one of the land pattern's eight orientations
   fits their centres with RMS <= 0.05 mm while the next best is >= 0.2 mm;
C3 pin centres lie within 0.03 mm of the land pattern after that fit;
C4 pin function by net: Q1 drain pins 3/5/7 on VIN and source pins 2/4/6 on SW; Q2 drain pins
   on SW and source pins on GND; each gate pin on a net that is none of VIN/SW/GND, and the two
   gates on different nets;
C5 Ci1-Ci7 are seven pad pairs on the top and Cm1-Cm10 ten pairs on the bottom, each pair with
   one VIN and one GND contact.
Reported, not pass/fail: contact dimensions against the land pattern. The Gerber aperture
definitions (0.370 and 0.470 mm mask widths for the long pins, against 0.30 and 0.40 mm in the
land pattern) were seen before this script was written, so the width comparison is a finding,
not a blind test. Via groups and their connected layers are reported, not checked.

Via layers. A via's barrel bonds to every layer whose copper surrounds its rim. That copper is
"functional" when it belongs to net copper beyond the via's own pad, and "pad only" when the
island lies within 0.25 mm of the rims of the vias it joins (non-functional inner pads and the
slot pads that join one row of vias). Implemented as the distance from the hull of the joined
vias' centres, at most the largest via radius plus 0.25 mm.

Run history. Run 1 (report kept: results/gan/epc90133-power-loop-run1-failed.json) failed C2 and
C5 because my component windows also held contacts of neighbouring parts (driver-side pads, D1/D2);
contacts cut by a window edge are now dropped, with the windows unchanged. Run 2's checks matched
run 3, but its via labels were wrong: per-via disks left slot pads' edges between vias uncovered,
so slot pads counted as functional, and keying groups on the contact split via pairs. Run 3 uses
the hull rule above. C1 fails in every run, for a board reason: on the outer pins (1, 2, 7) the
stencil opening is a full rounded rectangle, while the mask stays closed between the side-flank
notches, so 16-20% of those openings prints on mask-covered copper. Contacts are defined by the
mask opening on copper, so this does not change them.
"""
import argparse
import collections
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.optimize import linear_sum_assignment
from scipy.spatial import ConvexHull

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from circuit_tools.gerber import load_layer, rasterize
from read_epc90133_geometry import GERBERS, LAYERS, PITCH, PREFIX, geometry_source, load_board

FINE = 0.005  # mm, component windows
LOOP_WINDOW = (14.0, 22.0, 34.0, 38.0)  # mm; holds Q1, Q2, Ci1-Ci7, Cm1-Cm10 and their vias
# Component windows (mm), read from the paste layers; the script finds the contacts inside them.
FETS = {"Q1": (17.2, 28.7, 23.8, 33.3), "Q2": (17.2, 23.7, 23.8, 28.3)}
CAPS = {"Ci": ("top", (15.0, 33.0, 28.0, 36.2), 7), "Cm": ("bottom", (15.0, 32.9, 33.0, 36.5), 10)}
SIDE = {"top": ("GTL", "GTS", "GTP"), "bottom": ("GBL", "GBS", "GBP")}
# EPC2302 recommended land pattern, datasheet p. 11 (mask openings, part-centred, top view,
# long side along x, gate at -x/+y): pin -> (function, x, y, width, length).
LAND = {1: ("G", -2.338, 1.207, 0.40, 0.985), 2: ("S", -2.338, -0.650, 0.40, 2.10),
        3: ("D", -1.275, 0.0, 0.30, 3.40), 4: ("S", -0.425, 0.0, 0.30, 3.40),
        5: ("D", 0.425, 0.0, 0.30, 3.40), 6: ("S", 1.275, 0.0, 0.30, 3.40),
        7: ("D", 2.338, 0.0, 0.40, 3.40)}
EXPECTED_NETS = {"Q1": {"D": "VIN", "S": "SW"}, "Q2": {"D": "SW", "S": "GND"}}
PAD_MARGIN = 0.25  # mm beyond a via's rim within which copper counts as its own pad
LINK = 0.75  # mm, single-linkage distance for via groups
# B5253 stackup (board audit): copper 2.8 mil; dielectrics top to bottom, mil.
T_CU = 2.8 * 0.0254
DIELECTRICS = [5.0, 5.0, 7.2, 5.0, 7.2, 5.0, 5.0]
ORIENTATIONS = {"R0": lambda x, y: (x, y), "R90": lambda x, y: (-y, x), "R180": lambda x, y: (-x, -y),
                "R270": lambda x, y: (y, -x), "M0": lambda x, y: (-x, y), "M90": lambda x, y: (y, x),
                "M180": lambda x, y: (x, -y), "M270": lambda x, y: (-y, -x)}
NET_COLOURS = {"VIN": (0.80, 0.24, 0.24), "GND": (0.24, 0.43, 0.78), "SW": (0.24, 0.63, 0.24),
               "other": (0.75, 0.63, 0.43), "none": (1.0, 1.0, 1.0)}


@lru_cache(maxsize=None)
def layer(ext):
    return load_layer(GERBERS / f"{PREFIX}Gerbers.{ext}")


def fine(ext, bounds):
    return rasterize(layer(ext), bounds, FINE).grid


def regions(grid, bounds, pitch, min_area=0.01):
    """Connected regions of a boolean grid, with board-coordinate bounding boxes."""
    lab, _ = ndimage.label(grid)
    out = []
    for k, sl in enumerate(ndimage.find_objects(lab), 1):
        m = lab[sl] == k
        if m.sum() * pitch ** 2 < min_area:
            continue
        ys, xs = np.nonzero(m)
        x = bounds[0] + (xs + sl[1].start) * pitch
        y = bounds[1] + (ys + sl[0].start) * pitch
        out.append({"k": k, "sl": sl, "m": m, "area": float(m.sum() * pitch ** 2),
                    "x0": float(x.min()), "x1": float(x.max()), "y0": float(y.min()), "y1": float(y.max()),
                    "cx": float((x.min() + x.max()) / 2), "cy": float((y.min() + y.max()) / 2)})
    return out, lab


def core(region, pitch):
    """Width and length of a pin running along y; the 25th-percentile row width excludes side notches."""
    widths = np.array([r[-1] - r[0] + 1 for r in (np.nonzero(row)[0] for row in region["m"] if row.any())])
    return float(np.percentile(widths, 25) * pitch), float(region["y1"] - region["y0"] + pitch)


def ring_on_copper(region, lab, copper, width_px):
    """Fraction of a thin ring just outside a mask opening that is copper (1.0: mask-defined all round)."""
    m = lab == region["k"]
    ring = ndimage.binary_dilation(m, iterations=width_px) & ~m
    return float(copper[ring].mean())


def net_at(b, e, x, y):
    i, j = b.pixel(x, y)
    lab = int(b.labels[e][i, j])
    if not lab:
        return "none", None
    root = b.find((e, lab))
    return b.net_name.get(root, "other"), str(root)


def contacts_in(side, bounds):
    """Mask-open copper regions in a window, with the paste openings on them (C1 evidence)."""
    cu_e, mask_e, paste_e = SIDE[side]
    cu, mask, paste = fine(cu_e, bounds), fine(mask_e, bounds), fine(paste_e, bounds)
    contact_grid = cu & mask
    cons, lab = regions(contact_grid, bounds, FINE)
    pastes, plab = regions(paste, bounds, FINE)
    for p in pastes:
        pm = plab == p["k"]
        p["on_contact"] = float(contact_grid[pm].mean())
        p["contact_k"] = collections.Counter(lab[pm][lab[pm] > 0].tolist()).most_common(1)[0][0] if (lab[pm] > 0).any() else None
    used = {p["contact_k"] for p in pastes}
    # A contact cut by the window edge belongs to a neighbouring part (run 1 counted such contacts).
    edge = lambda c: (c["sl"][0].start == 0 or c["sl"][1].start == 0 or c["sl"][0].stop == lab.shape[0]
                      or c["sl"][1].stop == lab.shape[1])
    clipped = [c for c in cons if c["k"] in used and edge(c)]
    cons = [c for c in cons if c["k"] in used and not edge(c)]
    kept = {c["k"] for c in cons}
    pastes = [p for p in pastes if p["contact_k"] in kept]
    for c in cons:
        c["pastes"] = [p for p in pastes if p["contact_k"] == c["k"]]
    contacts_in.clipped[(side, bounds)] = len(clipped)
    return cons, lab, cu, pastes


contacts_in.clipped = {}


def fit_footprint(cons):
    """Best of the land pattern's eight orientations for the measured contact centres."""
    meas = np.array([[c["cx"], c["cy"]] for c in cons])
    fits = {}
    for name, T in ORIENTATIONS.items():
        pins = sorted(LAND)
        P = np.array([T(LAND[p][1], LAND[p][2]) for p in pins])
        if len(meas) != len(P):
            continue
        t = meas.mean(0) - P.mean(0)
        cost = ((meas[:, None, :] - (P[None] + t)) ** 2).sum(-1)
        r, c = linear_sum_assignment(cost)
        t = (meas[r] - P[c]).mean(0)
        res = meas[r] - (P[c] + t)
        fits[name] = {"rms_mm": float(np.sqrt((res ** 2).sum(1).mean())), "centre": t.tolist(),
                      "pin_of": {int(i): pins[j] for i, j in zip(r, c)},
                      "residual": {pins[j]: res[k].tolist() for k, j in enumerate(c)}}
    return fits


def footprint(b, name, bounds):
    cons, lab, cu, pastes = contacts_in("top", bounds)
    fits = fit_footprint(cons)
    ranked = sorted(fits.items(), key=lambda kv: kv[1]["rms_mm"])
    best_name, best = ranked[0] if ranked else (None, None)
    second = ranked[1][1]["rms_mm"] if len(ranked) > 1 else None
    pins = {}
    if best:
        cx, cy = best["centre"]
        for i, c in enumerate(cons):
            p = best["pin_of"][i]
            fn, lx, ly, lw, ll = LAND[p]
            w, length = core(c, FINE)
            if best_name not in ("R0", "R180", "M0", "M180"):
                w, length = None, None  # pins would run along x; not expected on this board
            net, root = net_at(b, "GTL", c["cx"], c["cy"])
            pins[p] = {"function": fn, "net": net, "net_root": root,
                       "centre_mm": [c["cx"], c["cy"]], "centre_residual_mm": best["residual"][p],
                       "mask_opening_on_copper": {"core_width_mm": w, "length_mm": length,
                                                  "land_pattern_width_mm": lw, "land_pattern_length_mm": ll,
                                                  "width_minus_land_mm": None if w is None else w - lw,
                                                  "length_minus_land_mm": None if length is None else length - ll},
                       "bbox_mm": [c["x0"], c["y0"], c["x1"], c["y1"]], "area_mm2": c["area"],
                       "ring_outside_mask_on_copper": ring_on_copper(c, lab, cu, 4),
                       "paste_openings": [{"bbox_mm": [p_["x0"], p_["y0"], p_["x1"], p_["y1"]], "area_mm2": p_["area"]}
                                          for p_ in c["pastes"]]}
    return {"contacts": len(cons), "orientation": best_name, "fit_rms_mm": best["rms_mm"] if best else None,
            "next_best_rms_mm": second, "centre_mm": best["centre"] if best else None,
            "orientations": {k: v["rms_mm"] for k, v in fits.items()}, "pins": dict(sorted(pins.items())),
            "paste": pastes, "cons": cons}


def capacitors(b, prefix, side, bounds, count):
    cons, _, _, pastes = contacts_in(side, bounds)
    cu_e = SIDE[side][0]
    xs = np.array([c["cx"] for c in cons])
    order = np.argsort(xs)
    pairs, cur = [], []
    for k in order:  # pads of one capacitor share a column
        if cur and abs(xs[k] - xs[cur[0]]) > 0.3:
            pairs.append(cur)
            cur = []
        cur.append(k)
    if cur:
        pairs.append(cur)
    caps = []
    for n, pair in enumerate(pairs, 1):
        pads = []
        for k in sorted(pair, key=lambda k: cons[k]["cy"]):
            c = cons[k]
            net, _ = net_at(b, cu_e, c["cx"], c["cy"])
            pads.append({"net": net, "centre_mm": [c["cx"], c["cy"]], "bbox_mm": [c["x0"], c["y0"], c["x1"], c["y1"]],
                         "size_mm": [c["x1"] - c["x0"] + FINE, c["y1"] - c["y0"] + FINE], "area_mm2": c["area"]})
        caps.append({"ref": f"{prefix}{n}", "side": side, "layer": cu_e, "pads": pads,
                     "pad_centre_spacing_mm": abs(pads[-1]["centre_mm"][1] - pads[0]["centre_mm"][1]) if len(pads) == 2 else None,
                     "one_vin_one_gnd": sorted(p["net"] for p in pads) == ["GND", "VIN"]})
    return {"caps": caps, "pairs": len(pairs), "expected": count, "paste": pastes, "cons": cons}


def via_layers(b):
    """Per via and layer: functional (net copper), pad only, or no copper at the rim."""
    touching = collections.defaultdict(list)
    for idx, v in enumerate(b.via_rows):
        for e, lab in v["islands"]:
            touching[(e, lab)].append(idx)
    objs = {e: ndimage.find_objects(b.labels[e]) for e in LAYERS}
    local = {}

    def is_pad_only(e, lab):
        if (e, lab) in local:
            return local[(e, lab)]
        sl = objs[e][lab - 1]
        vs = [b.via_rows[i] for i in touching[(e, lab)]]
        r_max = max(v["d"] / 2 for v in vs) + PAD_MARGIN
        span_x = max(v["x"] for v in vs) - min(v["x"] for v in vs) + 2 * r_max
        span_y = max(v["y"] for v in vs) - min(v["y"] for v in vs) + 2 * r_max
        if (sl[1].stop - sl[1].start) * PITCH > span_x + PITCH or (sl[0].stop - sl[0].start) * PITCH > span_y + PITCH:
            local[(e, lab)] = False
            return False
        # Distance from the hull of the joined vias' centres (a point, segment or polygon), so a slot
        # pad joining a row of vias counts as pad only. Run 2 used per-via disks, which left the slot's
        # edges between vias uncovered and labelled such pads functional.
        m = b.labels[e][sl] == lab
        pts = np.array([(v["x"] / PITCH - sl[1].start, v["y"] / PITCH - sl[0].start) for v in vs])
        if len(pts) > 2 and np.linalg.matrix_rank(pts - pts.mean(0), tol=1.0) == 2:
            pts = pts[ConvexHull(pts).vertices]
        hull = Image.new("1", (m.shape[1], m.shape[0]), 0)
        draw = ImageDraw.Draw(hull)
        if len(pts) > 2:
            draw.polygon([tuple(p) for p in pts], fill=1, outline=1)
        else:
            draw.line([tuple(p) for p in pts] * (2 if len(pts) == 1 else 1), fill=1, width=1)
        hull = np.array(hull, dtype=bool)
        for x, y in np.round(pts).astype(int):  # the centres themselves, whatever the drawing does
            if 0 <= y < hull.shape[0] and 0 <= x < hull.shape[1]:
                hull[y, x] = True
        dist = ndimage.distance_transform_edt(~hull) * PITCH
        local[(e, lab)] = bool(dist[m].max() <= r_max + PITCH)
        return local[(e, lab)]

    out = []
    for v in b.via_rows:
        lay = {e: "none" for e in LAYERS}
        for e, lab in v["islands"]:
            lay[e] = "pad only" if is_pad_only(e, lab) else "functional"
        out.append(lay)
    return out


def via_groups(b, per_layer, contact_of):
    x0, y0, x1, y1 = LOOP_WINDOW
    idx = [i for i, v in enumerate(b.via_rows) if x0 <= v["x"] <= x1 and y0 <= v["y"] <= y1]
    keyed = collections.defaultdict(list)
    for i in idx:
        v = b.via_rows[i]
        net = b.net_of(v["layers"][0], v["x"], v["y"]) if v["layers"] else "unconnected"
        func = tuple(e for e in LAYERS if per_layer[i][e] == "functional")
        keyed[(net, func)].append(i)  # run 2 also keyed on the contact, which split via pairs
    groups = []
    for (net, func), members in keyed.items():
        pts = np.array([[b.via_rows[i]["x"], b.via_rows[i]["y"]] for i in members])
        labels = fcluster(linkage(pts, "single"), LINK, "distance") if len(pts) > 1 else np.array([1])
        for c in sorted(set(labels)):
            sel = [m for m, l in zip(members, labels) if l == c]
            p = np.array([[b.via_rows[i]["x"], b.via_rows[i]["y"]] for i in sel])
            nn = [float(np.sort(np.hypot(*(p - q).T))[1]) for q in p] if len(p) > 1 else []
            contact = sorted({c for c in (contact_of(b.via_rows[i]["x"], b.via_rows[i]["y"]) for i in sel) if c})
            groups.append({"net": net, "count": len(sel), "contact": contact or None,
                           "vias_in_contacts": sum(1 for i in sel if contact_of(b.via_rows[i]["x"], b.via_rows[i]["y"])),
                           "drills_mm": dict(collections.Counter(f"{b.via_rows[i]['d']:.3f}" for i in sel)),
                           "centroid_mm": p.mean(0).round(3).tolist(), "bbox_mm": [*p.min(0).round(3), *p.max(0).round(3)],
                           "median_nn_spacing_mm": float(np.median(nn)) if nn else None,
                           "functional_layers": list(func),
                           "pad_only_layers": [e for e in LAYERS if all(per_layer[i][e] == "pad only" for i in sel)],
                           "members": sel})
    groups.sort(key=lambda g: (g["net"], -g["centroid_mm"][1], g["centroid_mm"][0]))
    counter = collections.Counter()
    for g in groups:
        counter[g["net"]] += 1
        g["id"] = f"{g['net']}-{counter[g['net']]:02d}"
    return groups, idx


def z_mid():
    """Copper mid-plane heights (mm), top layer at 0."""
    z, out = 0.0, {}
    for k, e in enumerate(LAYERS):
        out[e] = z
        if k < len(DIELECTRICS):
            z -= T_CU + DIELECTRICS[k] * 0.0254
    return out


def render(b, fets, caps, groups, per_layer, outdir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    outdir.mkdir(parents=True, exist_ok=True)
    x0, y0, x1, y1 = LOOP_WINDOW
    i0, j0 = b.pixel(x0, y0)
    i1, j1 = b.pixel(x1, y1)
    ext = (x0 - PITCH / 2, x1 + PITCH / 2, y0 - PITCH / 2, y1 + PITCH / 2)

    def net_image(e, light=0.55):
        lut = np.ones((b.counts[e] + 1, 3))
        for lab in range(1, b.counts[e] + 1):
            lut[lab] = NET_COLOURS[b.net_name.get(b.find((e, lab)), "other")]
        img = lut[b.labels[e][i0:i1 + 1, j0:j1 + 1]]
        return 1 - (1 - img) * light

    def draw_vias(ax, ids=True, only=None):
        for g in groups:
            if only and not only(g):
                continue
            col = NET_COLOURS.get(g["net"], (0.5, 0.5, 0.5))
            for i in g["members"]:
                v = b.via_rows[i]
                ax.add_patch(plt.Circle((v["x"], v["y"]), v["d"] / 2, fc=col, ec="k", lw=0.4, zorder=4))
            if ids and g["count"] >= 2:
                cx, cy = g["centroid_mm"]
                ax.text(g["bbox_mm"][2] + 0.12, cy, g["id"], fontsize=5.5, va="center", zorder=6,
                        bbox=dict(fc="white", ec="none", alpha=0.75, pad=0.3))

    def contacts(ax, cons, bounds, lab_face=(0, 0, 0, 0.35)):
        for c in cons:
            ax.add_patch(Rectangle((c["x0"], c["y0"]), c["x1"] - c["x0"], c["y1"] - c["y0"], fc=lab_face, ec="k", lw=0.5, zorder=3))

    def finish(ax, title):
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect("equal")
        ax.set_xlabel("x (mm)")
        ax.set_ylabel("y (mm)")
        ax.set_title(title, fontsize=9)
        handles = [Rectangle((0, 0), 1, 1, fc=NET_COLOURS[n]) for n in ("VIN", "SW", "GND", "other")]
        ax.legend(handles, ["VIN", "SW", "GND", "other net"], loc="lower right", fontsize=6, framealpha=0.9)
        ax.plot([x0 + 0.5, x0 + 2.5], [y0 + 0.5] * 2, "k-", lw=2)
        ax.text(x0 + 1.5, y0 + 0.7, "2 mm", ha="center", fontsize=6)

    # Top layer
    fig, ax = plt.subplots(figsize=(9, 7.4), dpi=150)
    ax.imshow(net_image("GTL"), origin="lower", extent=ext, interpolation="nearest")
    for q, f in fets.items():
        contacts(ax, f["cons"], FETS[q])
        for p, pin in f["pins"].items():
            cx, cy = pin["centre_mm"]
            ax.text(cx, cy, f"{p}\n{pin['function']}", ha="center", va="center", fontsize=5.5, zorder=7,
                    bbox=dict(fc="white", ec="none", alpha=0.8, pad=0.2))
        bx = [p["bbox_mm"] for p in f["pins"].values()]
        ax.text(min(r[0] for r in bx) - 0.2, max(r[3] for r in bx), q, ha="right", va="top", fontsize=8, weight="bold")
    contacts(ax, caps["Ci"]["cons"], CAPS["Ci"][1])
    for c in caps["Ci"]["caps"]:
        top = max(p["bbox_mm"][3] for p in c["pads"])
        ax.text(c["pads"][0]["centre_mm"][0], top + 0.15, c["ref"], ha="center", va="bottom", fontsize=6, weight="bold")
        for p in c["pads"]:
            ax.text(*p["centre_mm"], "+" if p["net"] == "VIN" else "−", ha="center", va="center", fontsize=7, zorder=7)
    draw_vias(ax)
    q1, q2 = fets["Q1"]["centre_mm"], fets["Q2"]["centre_mm"]
    ci_vin = np.mean([p["centre_mm"] for c in caps["Ci"]["caps"] for p in c["pads"] if p["net"] == "VIN"], 0)
    kw = dict(arrowstyle="-|>", color="k", lw=1.4, mutation_scale=10)
    ax.annotate("", xy=(q1[0] + 1.0, q1[1] + 1.8), xytext=(q1[0] + 1.0, ci_vin[1] - 0.25), arrowprops=kw, zorder=8)
    ax.annotate("", xy=(q2[0] + 1.0, q2[1] + 1.9), xytext=(q1[0] + 1.0, q1[1] - 1.8), arrowprops=kw, zorder=8)
    ax.text(q1[0] + 3.0, ci_vin[1] - 1.0, "top-layer loop current:\nCi+ → Q1 drain → SW → Q2 drain\n→ Q2 source → GND vias down",
            fontsize=6.5, va="top", bbox=dict(fc="white", ec="k", lw=0.5, pad=2), zorder=8)
    finish(ax, "EPC90133 B5253 Rev 2.0, top layer: nets, contacts (mask opening on copper), via groups")
    fig.tight_layout()
    fig.savefig(outdir / "top.png")
    plt.close(fig)

    # Mid-layer 1 (first return plane)
    fig, ax = plt.subplots(figsize=(9, 7.4), dpi=150)
    ax.imshow(net_image("G1"), origin="lower", extent=ext, interpolation="nearest")
    for q, f in fets.items():
        for c in f["cons"]:
            ax.add_patch(Rectangle((c["x0"], c["y0"]), c["x1"] - c["x0"], c["y1"] - c["y0"], fc="none", ec="k", lw=0.4, ls=":", zorder=3))
    for c in caps["Ci"]["cons"]:
        ax.add_patch(Rectangle((c["x0"], c["y0"]), c["x1"] - c["x0"], c["y1"] - c["y0"], fc="none", ec="k", lw=0.4, ls=":", zorder=3))
    draw_vias(ax)
    ci_gnd = np.mean([p["centre_mm"] for c in caps["Ci"]["caps"] for p in c["pads"] if p["net"] == "GND"], 0)
    ax.annotate("", xy=(q1[0] - 1.2, ci_gnd[1] - 0.6), xytext=(q2[0] - 1.2, q2[1]), arrowprops=kw, zorder=8)
    ax.text(q1[0] - 1.4, q1[1], "return on\nmid-layer 1", ha="right", fontsize=6.5, bbox=dict(fc="white", ec="k", lw=0.5, pad=2), zorder=8)
    finish(ax, "Mid-layer 1 (0.127 mm below top): nets and via groups; dotted: top-layer contacts above")
    fig.tight_layout()
    fig.savefig(outdir / "mid1.png")
    plt.close(fig)

    # Bottom layer
    fig, ax = plt.subplots(figsize=(9, 7.4), dpi=150)
    ax.imshow(net_image("GBL"), origin="lower", extent=ext, interpolation="nearest")
    contacts(ax, caps["Cm"]["cons"], CAPS["Cm"][1])
    for c in caps["Cm"]["caps"]:
        top = max(p["bbox_mm"][3] for p in c["pads"])
        ax.text(c["pads"][0]["centre_mm"][0], top + 0.15, c["ref"], ha="center", va="bottom", fontsize=6, weight="bold")
        for p in c["pads"]:
            ax.text(*p["centre_mm"], "+" if p["net"] == "VIN" else "−", ha="center", va="center", fontsize=7, zorder=7)
    for q, f in fets.items():
        for c in f["cons"]:
            ax.add_patch(Rectangle((c["x0"], c["y0"]), c["x1"] - c["x0"], c["y1"] - c["y0"], fc="none", ec="k", lw=0.4, ls=":", zorder=3))
    draw_vias(ax)
    finish(ax, "Bottom layer, viewed from the top: nets, Cm contacts, via groups; dotted: Q1/Q2 contacts on top")
    fig.tight_layout()
    fig.savefig(outdir / "bottom.png")
    plt.close(fig)

    # All eight layers
    fig, axs = plt.subplots(2, 4, figsize=(13, 6.6), dpi=130)
    for ax, e in zip(axs.flat, LAYERS):
        ax.imshow(net_image(e, 0.7), origin="lower", extent=ext, interpolation="nearest")
        draw_vias(ax, ids=False, only=lambda g, e=e: e in g["functional_layers"])
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect("equal")
        ax.set_title(f"{e}: vias drawn where functional", fontsize=7)
        ax.tick_params(labelsize=5)
    fig.suptitle("Loop window, all copper layers top to bottom (net colours as before)", fontsize=9)
    fig.tight_layout()
    fig.savefig(outdir / "layers.png")
    plt.close(fig)

    # Cross-sections along y through Q2 pin 4 (source) and pin 5 (drain) columns
    z = z_mid()
    fig, axs = plt.subplots(2, 1, figsize=(10, 6.4), dpi=150)
    for ax, pin in zip(axs, (4, 5)):
        xs = fets["Q2"]["pins"][pin]["centre_mm"][0]
        _, j = b.pixel(xs, y0)
        for e in LAYERS:
            col = b.labels[e][i0:i1 + 1, j]
            ys = y0 + np.arange(len(col)) * PITCH
            names = [b.net_name.get(b.find((e, int(l))), "other") if l else "none" for l in col]
            start = 0
            for k in range(1, len(names) + 1):
                if k == len(names) or names[k] != names[start]:
                    if names[start] != "none":
                        ax.add_patch(Rectangle((ys[start], z[e] - T_CU / 2), ys[k - 1] - ys[start] + PITCH, T_CU,
                                               fc=NET_COLOURS[names[start]], ec="none"))
                    start = k
            ax.text(y0 - 0.1, z[e], e, ha="right", va="center", fontsize=6)
        for g in groups:
            for i in g["members"]:
                v = b.via_rows[i]
                if abs(v["x"] - xs) <= 0.3:
                    func = [z[e] for e in LAYERS if per_layer[i][e] == "functional"]
                    zs = [z[e] for e in LAYERS if per_layer[i][e] != "none"]
                    ax.add_patch(Rectangle((v["y"] - v["d"] / 2, min(zs) - T_CU / 2), v["d"], max(zs) - min(zs) + T_CU,
                                           fc=NET_COLOURS.get(g["net"], (0.5, 0.5, 0.5)), ec="k", lw=0.3, alpha=0.9))
                    for zz in func:
                        ax.plot([v["y"] - v["d"] / 2, v["y"] + v["d"] / 2], [zz, zz], "k-", lw=0.6)
        for q in ("Q1", "Q2"):
            bx = fets[q]["pins"][pin]["bbox_mm"]
            ax.add_patch(Rectangle((bx[1], 0.05), bx[3] - bx[1], 0.12, fc="0.2", ec="none"))
            ax.text((bx[1] + bx[3]) / 2, 0.2, f"{q} pin {pin} ({fets[q]['pins'][pin]['function']})", ha="center", fontsize=6)
        zb = min(z.values())
        for k, zz, dz in (("Ci", 0.05, 0.12), ("Cm", zb - 0.17, -0.12)):
            cap = min(caps[k]["caps"], key=lambda c: abs(c["pads"][0]["centre_mm"][0] - xs))
            for p in cap["pads"]:
                ax.add_patch(Rectangle((p["bbox_mm"][1], min(zz, zz + dz)), p["bbox_mm"][3] - p["bbox_mm"][1], abs(dz),
                                       fc="0.5", ec="none"))
            ax.text(np.mean([p["centre_mm"][1] for p in cap["pads"]]), zz + dz + (0.03 if dz > 0 else -0.09),
                    f"{cap['ref']} pads (x = {cap['pads'][0]['centre_mm'][0]:.1f})", ha="center", fontsize=6)
        ax.set_xlim(y0, y1)
        ax.set_ylim(min(z.values()) - 0.4, 0.35)
        ax.set_xlabel("y (mm)")
        ax.set_ylabel("z (mm), top copper at 0")
        ax.set_title(f"Section at x = {xs:.2f} mm (Q2 pin {pin} column); vias within 0.3 mm; black ticks: functional layers "
                     "(z exaggerated)", fontsize=7.5)
    fig.tight_layout()
    fig.savefig(outdir / "sections.png")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-power-loop.json")
    ap.add_argument("--renders", type=Path, default=ROOT / "results/gan/epc90133-power-loop")
    args = ap.parse_args()
    b = load_board()
    fets = {q: footprint(b, q, w) for q, w in FETS.items()}
    caps = {k: capacitors(b, k, side, w, n) for k, (side, w, n) in CAPS.items()}

    def contact_of(x, y):
        for q, f in fets.items():
            for p, pin in f["pins"].items():
                x0_, y0_, x1_, y1_ = pin["bbox_mm"]
                if x0_ <= x <= x1_ and y0_ <= y <= y1_:
                    return f"{q} pin {p} ({pin['function']})"
        for k, c in caps.items():
            for cap in c["caps"]:
                for p in cap["pads"]:
                    x0_, y0_, x1_, y1_ = p["bbox_mm"]
                    if x0_ <= x <= x1_ and y0_ <= y <= y1_:
                        return f"{cap['ref']} {p['net']} pad ({cap['side']})"
        return None

    per_layer = via_layers(b)
    groups, window_vias = via_groups(b, per_layer, contact_of)
    assert sum(g["count"] for g in groups) == len(window_vias)

    # Kelvin candidates: vias within 0.8 mm of pin 2's gate-side end (datasheet p. 6).
    kelvin = {}
    for q, f in fets.items():
        p2 = f["pins"].get(2)
        if not p2:
            continue
        ex, ey = p2["centre_mm"][0], p2["bbox_mm"][3]
        near = []
        for g in groups:
            for i in g["members"]:
                v = b.via_rows[i]
                d = float(np.hypot(v["x"] - ex, v["y"] - ey))
                if d <= 0.8:
                    near.append({"group": g["id"], "net": g["net"], "xy_mm": [v["x"], v["y"]], "distance_mm": d,
                                 "functional_layers": [e for e in LAYERS if per_layer[i][e] == "functional"]})
        kelvin[q] = sorted(near, key=lambda r: r["distance_mm"])

    # Checks
    pastes = [p for f in fets.values() for p in f["paste"]] + [p for c in caps.values() for p in c["paste"]]
    c1 = min(p["on_contact"] for p in pastes)
    checks = {"C1_paste_on_mask_open_copper": c1 >= 0.95}
    for q, f in fets.items():
        checks[f"C2_{q}_seven_contacts_unique_orientation"] = (
            f["contacts"] == 7 and f["fit_rms_mm"] is not None and f["fit_rms_mm"] <= 0.05
            and f["next_best_rms_mm"] is not None and f["next_best_rms_mm"] >= 0.2)
        checks[f"C3_{q}_pin_centres_within_0.03mm"] = bool(f["pins"]) and all(
            float(np.hypot(*p["centre_residual_mm"])) <= 0.03 for p in f["pins"].values())
        exp = EXPECTED_NETS[q]
        checks[f"C4_{q}_pin_nets"] = bool(f["pins"]) and all(
            (p["net"] == exp[p["function"]]) if p["function"] in exp else (p["net"] not in ("VIN", "SW", "GND", "none"))
            for p in f["pins"].values())
    g1, g2 = fets["Q1"]["pins"].get(1), fets["Q2"]["pins"].get(1)
    checks["C4_gates_on_different_nets"] = bool(g1 and g2 and g1["net_root"] != g2["net_root"])
    for k, c in caps.items():
        checks[f"C5_{k}_pairs_one_vin_one_gnd"] = (c["pairs"] == c["expected"] and len(c["caps"]) == c["expected"]
                                                   and all(len(x["pads"]) == 2 and x["one_vin_one_gnd"] for x in c["caps"]))

    # Ports for the extraction: per net conductor, branches from each terminal to one reference terminal.
    def pin_rects(q, fn):
        return [p["bbox_mm"] for p in fets[q]["pins"].values() if p["function"] == fn]
    terminals = {f"{q}.{fn}": {"net": EXPECTED_NETS[q].get(fn, "gate"), "layer": "GTL", "contact_bboxes_mm": pin_rects(q, fn),
                               "pins": [n for n, p in fets[q]["pins"].items() if p["function"] == fn]}
                 for q in fets for fn in ("D", "S", "G")}
    for c in caps.values():
        for cap in c["caps"]:
            for p in cap["pads"]:
                terminals[f"{cap['ref']}.{p['net']}"] = {"net": p["net"], "layer": cap["layer"], "contact_bboxes_mm": [p["bbox_mm"]]}
    caps_all = [cap["ref"] for c in caps.values() for cap in c["caps"]]
    ports = {
        "terminals": terminals,
        "scheme": {
            "VIN": {"reference": "Q1.D", "branches": [f"{r}.VIN" for r in caps_all]},
            "SW": {"reference": "Q2.D", "branches": ["Q1.S"]},
            "GND": {"reference": "Q2.S", "branches": [f"{r}.GND" for r in caps_all]},
        },
        "meaning": ("Each branch is a FastHenry port from a terminal to its net's reference terminal. One run gives the "
                    "coupled impedance matrix of all branches, including mutual terms between nets, so return paths "
                    "and coupling stay in the network; the circuit bench joins branches at shared terminals. Variants "
                    "without Cm drop those branches."),
        "junction_assumptions": {
            "baseline": "all mesh nodes inside a terminal's contact regions form one equipotential node",
            "alternative": "each contact joined at its centroid node only, with the pins of a FET terminal tied at those nodes",
            "not_modelled": ("EPC2302 package and internal metallization (the vendor model's terminals are its pads and it "
                             "has no package inductance); capacitor body ESL and ESR, which the bench must state separately"),
        },
        "later": ["gate loops (U80 outputs through R80-R83 to pins 1, return through the Kelvin candidates)",
                  "SW to the L1 pads and the bus entry, which matter for the buck bench but not the loop's high-frequency path"],
    }

    x_ci = [p["centre_mm"] for cap in caps["Ci"]["caps"] for p in cap["pads"]]
    q2_src = [g for g in groups if g["net"] == "GND" and any(c.startswith("Q2 pin") for c in g["contact"] or [])]
    dims = {
        "Q1_centre_mm": fets["Q1"]["centre_mm"], "Q2_centre_mm": fets["Q2"]["centre_mm"],
        "Ci_row_y_mm": [min(p[1] for p in x_ci), max(p[1] for p in x_ci)],
        "Ci_row_x_mm": [min(p[0] for p in x_ci), max(p[0] for p in x_ci)],
        "Q2_source_via_groups": [g["id"] for g in q2_src],
        "top_to_mid1_dielectric_mm": DIELECTRICS[0] * 0.0254, "copper_mm": T_CU,
        "layer_mid_planes_mm": z_mid(),
    }
    strip = lambda d: {k: v for k, v in d.items() if k not in ("cons", "paste")}
    report = {
        "schema": "epc90133-power-loop/1",
        "scope": "Geometry identification for exploratory extraction; no inductance is extracted here.",
        "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "geometry_source": geometry_source(),
        "sources": {"gerbers": "EPC90133 B5253 Rev 2.0 (zip checked by load_board)", "land_pattern": "EPC2302 datasheet p. 11",
                    "layout_description": "EPC2302 datasheet p. 6", "fab_notes": "EPC90133_B5253_Rev2_0_Fab Notes.PDF"},
        "fabrication_facts": {
            "vias": "0.010 in and smaller: tented both sides, IPC-4761 type VII (non-conductive fill, plated over) (fab note 6)",
            "barrel_plating": "at least 0.000787 in (20 um); the actual thickness is not given (fab note 5)",
            "solder_mask": "1:1 with the Gerber; mask-to-copper registration within 0.003 in (fab note 7)",
            "layer_registration": "within 0.003 in (fab note 4)",
            "all_drills_through": "all plated holes run top to bottom (drill layer-pair file; epc90133-geometry.json)",
        },
        "method": {"component_pitch_mm": FINE, "board_pitch_mm": PITCH, "pad_margin_mm": PAD_MARGIN, "via_link_mm": LINK,
                   "loop_window_mm": LOOP_WINDOW, "fet_windows_mm": FETS, "cap_windows_mm": {k: v[1] for k, v in CAPS.items()}},
        "land_pattern_mm": {p: dict(zip(("function", "x", "y", "width", "length"), v)) for p, v in LAND.items()},
        "fets": {q: strip(f) for q, f in fets.items()},
        "capacitors": {k: strip(c) for k, c in caps.items()},
        "paste_min_fraction_on_contact": c1,
        "neighbour_contacts_dropped_at_window_edges": {f"{s} {w}": n for (s, w), n in contacts_in.clipped.items()},
        "via_groups": [{k: v for k, v in g.items() if k != "members"} for g in groups],
        "window_via_count": len(window_vias),
        "kelvin_candidates": kelvin,
        "ports": ports,
        "dimensions": dims,
        "checks": checks,
        "outcome": "pass" if all(checks.values()) else "fail",
        "renders": str(args.renders.relative_to(ROOT)),
    }
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    render(b, fets, caps, groups, per_layer, args.renders)
    print(json.dumps({"checks": checks, "outcome": report["outcome"], "paste_min": c1}, indent=1))
    for q, f in fets.items():
        print(q, f["orientation"], f"rms {f['fit_rms_mm']:.4f}", "next", f["next_best_rms_mm"], "centre", np.round(f["centre_mm"], 3))
        for p, pin in f["pins"].items():
            m = pin["mask_opening_on_copper"]
            print(f"  pin {p} {pin['function']} {pin['net']:5s} res {np.round(pin['centre_residual_mm'], 3)} "
                  f"w {m['core_width_mm']:.3f} (land {m['land_pattern_width_mm']}) L {m['length_mm']:.3f} "
                  f"(land {m['land_pattern_length_mm']}) ring-on-Cu {pin['ring_outside_mask_on_copper']:.2f} paste {len(pin['paste_openings'])}")
    for k, c in caps.items():
        for cap in c["caps"]:
            print(cap["ref"], [(p["net"], np.round(p["size_mm"], 2).tolist()) for p in cap["pads"]], round(cap["pad_centre_spacing_mm"] or 0, 3))
    for g in report["via_groups"]:
        print(g["id"], g["count"], g["drills_mm"], g["centroid_mm"], g["contact"], "func", g["functional_layers"],
              "pad-only", g["pad_only_layers"], "nn", g["median_nn_spacing_mm"])
    print("kelvin", json.dumps(kelvin, indent=0)[:1500])


if __name__ == "__main__":
    main()
