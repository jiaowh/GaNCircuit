#!/usr/bin/env python3
"""Probe connection points on the published EPC90133 layout (B5253 Rev 2.0), for the hardware probe plan.

Measurement readiness (external review, 1 October 2026): the probe-and-channel plan needs actual connection
points for the switch node, Q2's gate-source voltage and the driver's PHASE-to-GND voltage. This script finds
them in the Gerbers; it measures nothing and extracts nothing. It is a reading of EPC's published files, not
of our board: the purchased board's revision and population must be checked against it (silkscreen, fitted
parts) before any connection is planned on it.

Sources: the schematic PDF names the probe footprints (read 1 October 2026): J1 "Upper Gate" SMD MMCX on VGu
through R11 (0 ohm, EMPTY) with VSW as its return; J2 "Lower Gate" SMD MMCX on VGl through R22 (0 ohm, EMPTY)
with GND as its return; J32 switch-node MMCX and J33 switch-node 2-pin 100 mil header; TP1-TP4 Keystone 5015
hook-up points on the input and output. The BOM lists J1, J2, J32 as optional (Molex 734152063), R11/R22 as
optional, and does not list J33. The QSG says J33 and J32 are "provided for switch-node measurement".
Designators below are assigned by net, as for R80-R83 in scripts/epc90133_gate_loop.py: the layout print's
component tokens are not at component positions. Contacts are mask openings on copper, on both sides.

Declared checks (1 October 2026, after an exploratory survey of the contacts and before this script's first run):
P1 J2: exactly one top pad of 1.0-1.3 mm on a net (not VIN/SW/GND) that also holds the far pad of an 0402-like
   pad pair (centres 0.8-1.1 mm apart, aligned within 0.1 mm) whose near pad is on Q2's gate net (R22); the
   large pad has four GND pads at the corners of a square of side 2.6 +- 0.1 mm centred on it within 0.1 mm;
P2 J1: the same with Q1's gate net (R11) and four SW pads;
P3 J33: two plated 1.016 mm holes 2.54 +- 0.05 mm apart, one on SW and one on GND, within 12 mm of Q2's drain;
P4 C81 and C80 by net: exactly one 0402-like pair BOOT-SW and exactly one VCC-GND within 3 mm of U80's centre;
P5 J32: no MMCX pattern (as P1) with an SW centre and four GND corners exists on either side (consistent with
   the board audit, which found J32 absent from the layout). Reported, not a failure of this script.
Reported, not checked: other plated through-hole pins on the J2 and J1 nets, the distances from each connection
point to the device or ball it stands in for, and the parts in between.

    PYTHONPATH=src python scripts/epc90133_probe_points.py
"""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from circuit_tools.gerber import load_layer, rasterize  # noqa: E402
from read_epc90133_geometry import BOARD, GERBERS, PITCH, PREFIX, load_board  # noqa: E402

GATE_LOOP = ROOT / "results/gan/epc90133-gate-loop.json"
SIDES = (("top", "GTL", "GTS", "GTP"), ("bottom", "GBL", "GBS", "GBP"))
MMCX_SIDE, MMCX_TOL, MMCX_CENTRE = 2.6, 0.1, (1.0, 1.3)
PAIR = (0.8, 1.1)
HEADER_D, HEADER_PITCH = 1.016, 2.54
RENDER_WINDOW = (7.0, 19.0, 30.0, 38.0)


def contacts(b):
    """Every mask opening on copper, both sides: centre, size, area, paste coverage and copper net root."""
    out = []
    for side, cu, mask, paste in SIDES:
        m = rasterize(load_layer(GERBERS / f"{PREFIX}Gerbers.{mask}"), BOARD, PITCH).grid
        p = rasterize(load_layer(GERBERS / f"{PREFIX}Gerbers.{paste}"), BOARD, PITCH).grid
        lab, _ = ndimage.label(b.grids[cu].grid & m)
        for k, sl in enumerate(ndimage.find_objects(lab), 1):
            reg = lab[sl] == k
            area = float(reg.sum() * PITCH ** 2)
            if area < 0.01:
                continue
            ys, xs = np.nonzero(reg)
            cl = int(b.labels[cu][ys[len(ys) // 2] + sl[0].start, xs[len(xs) // 2] + sl[1].start])
            x = BOARD[0] + (xs + sl[1].start) * PITCH
            y = BOARD[1] + (ys + sl[0].start) * PITCH
            out.append({"side": side, "root": b.find((cu, cl)) if cl else None,
                        "cx": float((x.min() + x.max()) / 2), "cy": float((y.min() + y.max()) / 2),
                        "w": float(x.max() - x.min()), "h": float(y.max() - y.min()), "area_mm2": area,
                        "paste": float(p[sl][reg].mean())})
    return out


def dist(a, b):
    return math.hypot(a["cx"] - b["cx"], a["cy"] - b["cy"])


def pairs(cons, side="top"):
    """0402-like pad pairs: centres PAIR apart, aligned on one axis, each pad under 0.6 mm2."""
    small = [c for c in cons if c["side"] == side and c["area_mm2"] < 0.6 and min(c["w"], c["h"]) > 0.3]
    return [(a, b) for a, b in itertools.combinations(small, 2)
            if PAIR[0] <= dist(a, b) <= PAIR[1] and min(abs(a["cx"] - b["cx"]), abs(a["cy"] - b["cy"])) < 0.1]


def mmcx_at(cons, centre, ground_net, net_of):
    corners = [c for c in cons if c["side"] == centre["side"] and net_of(c) == ground_net
               and abs(dist(c, centre) - MMCX_SIDE / math.sqrt(2)) <= MMCX_TOL * 1.5]
    if len(corners) != 4:
        return None
    cx, cy = np.mean([c["cx"] for c in corners]), np.mean([c["cy"] for c in corners])
    xs = sorted(c["cx"] for c in corners)
    ys = sorted(c["cy"] for c in corners)
    side_x, side_y = (xs[2] + xs[3] - xs[0] - xs[1]) / 2, (ys[2] + ys[3] - ys[0] - ys[1]) / 2
    ok = (math.hypot(cx - centre["cx"], cy - centre["cy"]) <= MMCX_TOL
          and abs(side_x - MMCX_SIDE) <= MMCX_TOL and abs(side_y - MMCX_SIDE) <= MMCX_TOL)
    return {"corners": corners, "side_mm": [side_x, side_y], "pass": bool(ok)} if ok else None


def summary(c, net_of):
    return {"side": c["side"], "net": net_of(c), "centre_mm": [round(c["cx"], 3), round(c["cy"], 3)],
            "size_mm": [round(c["w"], 3), round(c["h"], 3)], "pasted": c["paste"] > 0.3}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-probe-points.json")
    ap.add_argument("--render", type=Path, default=ROOT / "results/gan/epc90133-probe-points.png")
    args = ap.parse_args()
    b = load_board()
    gl = json.loads(GATE_LOOP.read_text(encoding="utf-8"))
    cons = contacts(b)
    term = {k: v[0]["centre_mm"] for k, v in gl["terminals"].items()}
    balls = {f"U80.{v['name']}.{k}": v["centre_mm"] for k, v in gl["ball_array"]["balls"].items()}

    def root_at(x, y, e="GTL"):
        lab = int(b.labels[e][b.pixel(x, y)])
        return b.find((e, lab)) if lab else None

    names = dict(b.net_name)  # VIN, GND, SW
    for t, n in (("Q2.G", "VGl"), ("Q1.G", "VGu")):
        names[root_at(*term[t])] = n
    for ball, n in (("D3", "BOOT"), ("A3", "VCC")):
        names[root_at(*gl["ball_array"]["balls"][ball]["centre_mm"])] = n
    net_of = lambda c: names.get(c["root"], "other")
    checks, points = {}, {}

    # P1/P2: gate probe MMCX footprints.
    for tag, gate, ground, ref, res in (("J2", "VGl", "GND", "Q2.G", "R22"), ("J1", "VGu", "SW", "Q1.G", "R11")):
        known = {tuple(term[k]) for k in term if k.startswith(("R8", "Q"))}
        found = []
        for a, c in pairs(cons):
            for near, far in ((a, c), (c, a)):
                if net_of(near) != gate or net_of(far) != "other" or (round(near["cx"], 2), round(near["cy"], 2)) in \
                        {(round(x, 2), round(y, 2)) for x, y in known}:
                    continue
                big = [d for d in cons if d["root"] == far["root"] and d["side"] == "top"
                       and MMCX_CENTRE[0] <= min(d["w"], d["h"]) and max(d["w"], d["h"]) <= MMCX_CENTRE[1]]
                for d in big:
                    m = mmcx_at(cons, d, ground, net_of)
                    if m:
                        found.append((near, far, d, m))
        ok = len(found) == 1
        checks[f"P{1 if tag == 'J2' else 2}_{tag}"] = {"candidates": len(found), "pass": ok}
        if ok:
            near, far, centre, m = found[0]
            th = [d for d in cons if d["root"] == far["root"] and d is not centre and d is not far and d["side"] == "top"]
            points[tag] = {
                "measures": f"{gate} (gate net, {'Q2' if tag == 'J2' else 'Q1'}) against {ground}",
                "status_on_published_board": f"{tag} (MMCX) and {res} (0 ohm) optional, not fitted",
                res: {"gate_pad": summary(near, net_of), "probe_pad": summary(far, net_of)},
                "mmcx_signal_pad": summary(centre, net_of),
                "mmcx_ground_pads": [summary(c, net_of) for c in m["corners"]],
                "other_contacts_on_probe_net": [summary(c, net_of) for c in th],
                "distance_mm": {f"{res} gate pad to {ref} pad": round(math.hypot(near["cx"] - term[ref][0], near["cy"] - term[ref][1]), 2),
                                f"{res} gate pad to MMCX signal pad": round(dist(near, centre), 2)}}

    # P3: J33 header.
    q2d = term["Q2.D"]
    holes = [h for h in b.holes if h.plated and abs(h.diameter - HEADER_D) < 0.01]
    hole_net = lambda h: next((names.get(root_at(h.x + (h.diameter / 2 + 3 * PITCH) * math.cos(a),
                                                 h.y + (h.diameter / 2 + 3 * PITCH) * math.sin(a), e), "other")
                               for e in ("GTL", "GBL") for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)
                               if root_at(h.x + (h.diameter / 2 + 3 * PITCH) * math.cos(a),
                                          h.y + (h.diameter / 2 + 3 * PITCH) * math.sin(a), e)), "none")
    hdr = [(h1, h2) for h1, h2 in itertools.combinations(holes, 2)
           if abs(math.hypot(h1.x - h2.x, h1.y - h2.y) - HEADER_PITCH) <= 0.05
           and {hole_net(h1), hole_net(h2)} == {"SW", "GND"}
           and min(math.hypot(h.x - q2d[0], h.y - q2d[1]) for h in (h1, h2)) <= 12]
    checks["P3_J33"] = {"candidates": len(hdr), "pass": len(hdr) == 1}
    if len(hdr) == 1:
        points["J33"] = {"measures": "SW against GND (switch node)", "status_on_published_board": "footprint only; not in the BOM",
                         "pins": [{"net": hole_net(h), "centre_mm": [round(h.x, 3), round(h.y, 3)]} for h in hdr[0]],
                         "distance_mm": {"SW pin to Q2 drain pad centre": round(min(math.hypot(h.x - q2d[0], h.y - q2d[1])
                                                                                 for h in hdr[0] if hole_net(h) == "SW"), 2)}}
    j2_net = None
    if "J2" in points:
        j2_net = next(c["root"] for c in cons if [round(c["cx"], 3), round(c["cy"], 3)] == points["J2"]["mmcx_signal_pad"]["centre_mm"])
    th_j2 = [h for h in holes if j2_net is not None and root_at(h.x + (h.diameter / 2 + 3 * PITCH), h.y, "GTL") == j2_net]
    if th_j2:
        mates = [g for g in holes if any(abs(math.hypot(g.x - h.x, g.y - h.y) - HEADER_PITCH) <= 0.05 for h in th_j2)
                 and hole_net(g) == "GND"]
        points["J2"]["unnamed_through_hole_pair"] = {
            "note": "100 mil pair on the J2 net with a GND mate; not named in the schematic or BOM",
            "pins": [{"net": "J2 net", "centre_mm": [round(h.x, 3), round(h.y, 3)]} for h in th_j2]
                    + [{"net": "GND", "centre_mm": [round(g.x, 3), round(g.y, 3)]} for g in mates]}

    # P4: C81 (BOOT-SW) and C80 (VCC-GND) near the driver.
    u80 = np.mean([v for v in balls.values()], axis=0)
    near_u80 = lambda c: math.hypot(c["cx"] - u80[0], c["cy"] - u80[1]) <= 3.0
    for tag, nets in (("C81", {"BOOT", "SW"}), ("C80", {"VCC", "GND"})):
        hits = [(a, c) for a, c in pairs(cons) if {net_of(a), net_of(c)} == nets and near_u80(a) and near_u80(c)]
        checks[f"P4_{tag}"] = {"candidates": len(hits), "pass": len(hits) == 1}
        if len(hits) == 1:
            a, c = hits[0]
            pad = a if net_of(a) in ("SW", "GND") else c
            ball = "U80.PHASE.D4" if tag == "C81" else "U80.GND.A2"
            points[tag] = {"role": "PHASE-side access (bootstrap capacitor)" if tag == "C81" else "GND-side access (VCC capacitor)",
                           "pads": [summary(a, net_of), summary(c, net_of)], "access_pad": summary(pad, net_of),
                           "distance_mm": {f"access pad to {ball} ball": round(math.hypot(pad["cx"] - balls[ball][0], pad["cy"] - balls[ball][1]), 2)}}
    if "C81" in points and "C80" in points:
        p, g = points["C81"]["access_pad"]["centre_mm"], points["C80"]["access_pad"]["centre_mm"]
        points["PHASE_to_GND"] = {"tip": "C81 PHASE-side pad", "ground": "C80 GND pad",
                                  "tip_to_ground_mm": round(math.hypot(p[0] - g[0], p[1] - g[1]), 2),
                                  "caveat": "both pads carry gate-drive current between them and the balls; the voltage measured "
                                            "there differs from the ball-to-ball voltage the rating applies to"}

    # P5: J32 (reported).
    sw_mmcx = [d for d in cons if net_of(d) == "SW" and MMCX_CENTRE[0] <= min(d["w"], d["h"]) and max(d["w"], d["h"]) <= MMCX_CENTRE[1]
               and mmcx_at(cons, d, "GND", net_of)]
    checks["P5_J32_absent"] = {"switch_node_mmcx_patterns": len(sw_mmcx), "consistent_with_audit": len(sw_mmcx) == 0}

    report = {"schema": "epc90133-probe-points/1",
              "scope": "connection points in EPC's published B5253 Rev 2.0 files; not our board; nothing measured or extracted",
              "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "gate_loop_sha256": hashlib.sha256(GATE_LOOP.read_bytes()).hexdigest(),
              "checks": checks, "points": points,
              "outcome": "pass" if all(v["pass"] for k, v in checks.items() if "pass" in v) else "fail"}
    args.output.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    for k, v in checks.items():
        print(k, v)
    render(b, names, report, term, args.render)


def render(b, names, report, term, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from epc90133_power_loop import NET_COLOURS
    x0, y0, x1, y1 = RENDER_WINDOW
    i0, j0 = b.pixel(x0, y0)
    i1, j1 = b.pixel(x1, y1)
    lut = np.ones((b.counts["GTL"] + 1, 3))
    for lab in range(1, b.counts["GTL"] + 1):
        lut[lab] = NET_COLOURS.get(names.get(b.find(("GTL", lab)), "other"), NET_COLOURS["other"])
    img = 1 - (1 - lut[b.labels["GTL"][i0:i1 + 1, j0:j1 + 1]]) * 0.5
    fig, ax = plt.subplots(figsize=(9, 8), dpi=150)
    ax.imshow(img, origin="lower", extent=(x0, x1, y0, y1), interpolation="nearest")
    marks = []
    for tag in ("J1", "J2"):
        p = report["points"].get(tag)
        if p:
            marks.append((p["mmcx_signal_pad"]["centre_mm"], f"{tag} MMCX ({'Q1' if tag == 'J1' else 'Q2'} gate)", "purple"))
            res = "R11" if tag == "J1" else "R22"
            marks.append((p[res]["probe_pad"]["centre_mm"], f"{res} (0 ohm, empty)", "purple"))
            for pin in p.get("unnamed_through_hole_pair", {}).get("pins", []):
                marks.append((pin["centre_mm"], f"TH {pin['net']}", "gray"))
    for pin in report["points"].get("J33", {}).get("pins", []):
        marks.append((pin["centre_mm"], f"J33 {pin['net']}", "darkgreen"))
    for tag in ("C81", "C80"):
        p = report["points"].get(tag)
        if p:
            marks.append((p["access_pad"]["centre_mm"], f"{tag} {p['access_pad']['net']} pad", "darkorange"))
    for t, lbl in (("Q1.G", "Q1 G"), ("Q2.G", "Q2 G"), ("U80.PH", "U80")):
        marks.append((term[t], lbl, "black"))
    for (x, y), lbl, col in marks:
        ax.plot(x, y, "o", ms=5, mfc="none", mec=col, mew=1.2)
        ax.annotate(lbl, (x, y), xytext=(4, 4), textcoords="offset points", fontsize=6, color=col,
                    bbox=dict(fc="white", ec="none", alpha=0.75, pad=0.2))
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_title("EPC90133 B5253 Rev 2.0, top copper: probe connection points (published files, not our board)", fontsize=8)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


if __name__ == "__main__":
    main()
