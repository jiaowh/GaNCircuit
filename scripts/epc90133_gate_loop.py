#!/usr/bin/env python3
"""Gate-drive loop geometry of the stock EPC90133 (B5253 Rev 2.0): driver balls, gate resistors, split sources.

Step 1 of the gate-loop and common-source extraction (G3; after test 6, docs/build.md). Test 6 showed that
an assumed 25-50 pH of common-source inductance halves the simulated overshoot, and the power-loop
extraction cannot show whether the board has any: it ties each FET's three source pins into one
equipotential terminal and has no gate or driver terminals. This script locates the gate-drive contacts,
checks them, and writes the terminals and ports that scripts/epc90133_extract.py (variant G) uses. It
extracts nothing.

Sources: the Gerbers (as scripts/epc90133_power_loop.py), the schematic transcription
(devices/epc/epc90133-schematic.json: R80 1 ohm VGuH-VGu, R81 0 ohm VGuL-VGu, R82 1 ohm VGlH-VGl,
R83 0 ohm VGlL-VGl, U80 PHASE tied to SW, GND to GND) and the uP1966E datasheet ball map (WLCSP 1.6x1.6-12B,
0.4 mm pitch, top view): A1 LGL, A2 GND, A3 VCC, A4 LI, B1 LGH, B4 HI, C1 PHASE, C4 NC, D1 UGL, D2 UGH,
D3 BOOT, D4 PHASE; B2, B3, C2, C3 empty. Contacts are mask openings on copper, as in the power loop.
Observed before this script was written (probe on 30 September 2026): 12 contacts near (15.5, 29.7) mm,
two on SW and one on GND, and two resistor-sized pad pairs per gate net.

Declared checks (30 September 2026, before the first run):
K1 U80: exactly 12 top-side contacts in its window, on a 0.4 mm grid (every centre within 0.03 mm of a
   grid point after a least-squares fit of the grid origin), occupying the 12 perimeter positions of a
   4 x 4 array;
K2 orientation: of the ball map's eight orientations, exactly one puts both PHASE balls on SW copper and
   the GND ball on GND copper;
K3 each driver output ball (UGH, UGL, LGH, LGL) is on its own net (four distinct nets, none of them
   VIN/SW/GND), and that net holds exactly one other contact: a resistor pad;
K4 that resistor's other pad (the contact 0.8-1.1 mm from it) is on the gate net of the matching FET
   (UGH/UGL: Q1 pin 1; LGH/LGL: Q2 pin 1), and the two resistors of each gate are different parts;
K5 the FET source pins keep the power loop's assignment: pin 2 (next to the gate) and pins 4 and 6 are on
   SW (Q1) or GND (Q2).
Run history. Run 1 (report kept: results/gan/epc90133-gate-loop-run1-failed.json) passed K1, K2, K3 and K5
and failed K4 for UGL and LGL: besides the facing pad, a pad of the neighbouring resistor lay diagonally at
about 1.0 mm, inside the distance window. An 0402's pads face each other along one axis, so run 2 also
requires the two pad centres to be aligned (offset under 0.1 mm across the axis). K4's intent is unchanged.
Reported, not checked: other contacts on the gate nets (dead-end parts), and the driver's supply pins
(VCC, BOOT), whose decoupling loops are not extracted (supplies are ideal at the balls in the bench).

Resistor values follow the nets, not the silkscreen: the resistor fed by UGH is R80 (1 ohm), UGL R81 (0 ohm),
LGH R82 (1 ohm), LGL R83 (0 ohm). Terminals and the port scheme for variant G:
    VIN  reference Q1.D;   branches Ci1-7.VIN, Cm1-10.VIN
    SW   reference Q2.D;   branches Q1.S2 (pin 2), Q1.S46 (pins 4 and 6), U80.PH (C1 and D4 tied)
    GND  reference Q2.S46; branches Ci/Cm GND pads, Q2.S2, U80.GND (A2)
    VGu  reference Q1.G;   branches R80.G, R81.G (the resistors' gate-side pads)
    VGl  reference Q2.G;   branches R82.G, R83.G
    VGuH reference R80.D;  branch U80.UGH      VGuL reference R81.D; branch U80.UGL
    VGlH reference R82.D;  branch U80.LGH      VGlL reference R83.D; branch U80.LGL
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from epc90133_power_loop import NET_COLOURS, contacts_in, net_at
from read_epc90133_geometry import PITCH, load_board

LOOP = ROOT / "results/gan/epc90133-power-loop.json"
U80_WINDOW = (14.6, 28.9, 16.4, 30.7)
AREA = (13.0, 23.5, 19.0, 33.5)  # contacts searched for the gate nets (both sides)
BALL_PITCH = 0.4
GRID_TOL = 0.03
RES_SPAN = (0.8, 1.1)  # mm, centre distance between an 0402's two pads
RES_ALIGN = 0.1  # mm, run 2: the two pad centres are aligned along x or y
BALLS = {"A1": "LGL", "A2": "GND", "A3": "VCC", "A4": "LI", "B1": "LGH", "B4": "HI",
         "C1": "PHASE", "C4": "NC", "D1": "UGL", "D2": "UGH", "D3": "BOOT", "D4": "PHASE"}
OUTPUTS = {"UGH": ("Q1", "R80", 1.0), "UGL": ("Q1", "R81", 0.0), "LGH": ("Q2", "R82", 1.0), "LGL": ("Q2", "R83", 0.0)}
# Top view: row letter -> index along one axis, column number -> index along the other.
ORIENT = {f"{a}{s}": (a, s) for a in ("rc", "cr") for s in ((1, 1), (1, -1), (-1, 1), (-1, -1))}


def local(ball, orient):
    """Ball position relative to the array centre in board mm for one orientation."""
    r, c = "ABCD".index(ball[0]), int(ball[1]) - 1
    a, (sx, sy) = ORIENT[orient]
    u, v = (r, c) if a == "rc" else (c, r)
    return sx * (u - 1.5) * BALL_PITCH, sy * (v - 1.5) * BALL_PITCH


def as_contact(side, c):
    e = "GTL" if side == "top" else "GBL"
    return {"layer": e, "bbox_mm": [c["x0"], c["y0"], c["x1"], c["y1"]], "centre_mm": [c["cx"], c["cy"]]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-gate-loop.json")
    ap.add_argument("--render", type=Path, default=ROOT / "results/gan/epc90133-gate-loop.png")
    args = ap.parse_args()
    b = load_board()
    loop = json.loads(LOOP.read_text(encoding="utf-8"))
    checks, notes = {}, {}

    # K1: the ball array.
    cons, _, _, _ = contacts_in("top", U80_WINDOW)
    cxy = np.array([[c["cx"], c["cy"]] for c in cons])
    centre = cxy.mean(axis=0) if len(cons) else np.zeros(2)
    idx = np.round((cxy - centre) / BALL_PITCH + 1.5) if len(cons) else np.zeros((0, 2))
    origin = (cxy - (idx - 1.5) * BALL_PITCH).mean(axis=0) if len(cons) else centre
    resid = np.hypot(*(cxy - origin - (idx - 1.5) * BALL_PITCH).T) if len(cons) else np.array([])
    perimeter = {(i, j) for i in range(4) for j in range(4)} - {(1, 1), (1, 2), (2, 1), (2, 2)}
    occupied = {(int(i), int(j)) for i, j in idx}
    checks["K1_ball_array"] = {"contacts": len(cons), "max_grid_residual_mm": float(resid.max()) if len(resid) else None,
                               "perimeter_occupied": occupied == perimeter,
                               "pass": len(cons) == 12 and len(resid) and float(resid.max()) <= GRID_TOL
                               and occupied == perimeter}

    # K2: orientation from the nets.
    def assign(orient):
        out = {}
        for ball in BALLS:
            dx, dy = local(ball, orient)
            k = int(np.argmin(np.hypot(cxy[:, 0] - origin[0] - dx, cxy[:, 1] - origin[1] - dy)))
            out[ball] = cons[k]
        return out

    fits = {}
    for o in ORIENT:
        a = assign(o)
        nets = {ball: net_at(b, "GTL", c["cx"], c["cy"])[0] for ball, c in a.items()}
        fits[o] = nets["C1"] == "SW" and nets["D4"] == "SW" and nets["A2"] == "GND"
    good = [o for o, ok in fits.items() if ok]
    checks["K2_orientation"] = {"orientations_passing": good, "pass": len(good) == 1}
    balls = assign(good[0]) if len(good) == 1 else {}

    # Contacts of the area on both sides, keyed by net root.
    area = []
    for side, e in (("top", "GTL"), ("bottom", "GBL")):
        cs, _, _, _ = contacts_in(side, AREA)
        for c in cs:
            net, root = net_at(b, e, c["cx"], c["cy"])
            area.append({"side": side, "c": c, "net": net, "root": root})
    ball_ids = {id(c) for c in balls.values()}

    def same(c1, c2):
        return abs(c1["cx"] - c2["cx"]) < 1e-6 and abs(c1["cy"] - c2["cy"]) < 1e-6

    gate_root = {q: net_at(b, "GTL", *loop["fets"][q]["pins"]["1"]["centre_mm"])[1] for q in ("Q1", "Q2")}
    terminals, parts = {}, {}
    k3, k4 = {}, {}
    out_roots = []
    for pin, (q, ref, ohm) in OUTPUTS.items():
        ball = next(bl for bl, name in BALLS.items() if name == pin)
        bc = balls.get(ball)
        if bc is None:
            continue
        net, root = net_at(b, "GTL", bc["cx"], bc["cy"])
        out_roots.append(root)
        others = [a for a in area if a["root"] == root and not same(a["c"], bc)]
        k3[pin] = {"ball": ball, "net": net, "root": root, "other_contacts": len(others),
                   "pass": net == "other" and len(others) == 1}
        if len(others) != 1:
            continue
        drv = others[0]
        span = [a for a in area if a["side"] == drv["side"] and not same(a["c"], drv["c"])
                and RES_SPAN[0] <= float(np.hypot(a["c"]["cx"] - drv["c"]["cx"], a["c"]["cy"] - drv["c"]["cy"])) <= RES_SPAN[1]
                and a["root"] == gate_root[q]
                and min(abs(a["c"]["cx"] - drv["c"]["cx"]), abs(a["c"]["cy"] - drv["c"]["cy"])) < RES_ALIGN]
        k4[pin] = {"resistor": ref, "ohm": ohm, "gate_side_candidates": len(span), "pass": len(span) == 1}
        if len(span) != 1:
            continue
        g = span[0]
        parts[ref] = {"ohm": ohm, "driver_pin": pin, "ball": ball, "fet": q,
                      "driver_pad": as_contact(drv["side"], drv["c"]), "gate_pad": as_contact(g["side"], g["c"])}
        terminals[f"{ref}.D"] = [as_contact(drv["side"], drv["c"])]
        terminals[f"{ref}.G"] = [as_contact(g["side"], g["c"])]
        terminals[f"U80.{pin}"] = [as_contact("top", bc)]
    checks["K3_driver_outputs"] = {"per_output": k3, "distinct_nets": len(set(out_roots)) == 4,
                                   "pass": len(k3) == 4 and all(v["pass"] for v in k3.values()) and len(set(out_roots)) == 4}
    pads = {q: [tuple(parts[r]["gate_pad"]["centre_mm"]) for r in parts if parts[r]["fet"] == q] for q in ("Q1", "Q2")}
    checks["K4_resistors"] = {"per_output": k4, "two_parts_per_gate": {q: len(set(v)) == 2 for q, v in pads.items()},
                              "pass": len(k4) == 4 and all(v["pass"] for v in k4.values())
                              and all(len(set(v)) == 2 for v in pads.values())}

    # K5 and the split source terminals.
    k5 = {}
    for q, net in (("Q1", "SW"), ("Q2", "GND")):
        pins = loop["fets"][q]["pins"]
        k5[q] = {p: pins[p]["net"] for p in ("2", "4", "6")}
        terminals[f"{q}.G"] = [{"layer": "GTL", "bbox_mm": pins["1"]["bbox_mm"], "centre_mm": pins["1"]["centre_mm"]}]
        terminals[f"{q}.D"] = [{"layer": "GTL", "bbox_mm": pins[p]["bbox_mm"], "centre_mm": pins[p]["centre_mm"]}
                               for p in ("3", "5", "7")]
        terminals[f"{q}.S2"] = [{"layer": "GTL", "bbox_mm": pins["2"]["bbox_mm"], "centre_mm": pins["2"]["centre_mm"]}]
        terminals[f"{q}.S46"] = [{"layer": "GTL", "bbox_mm": pins[p]["bbox_mm"], "centre_mm": pins[p]["centre_mm"]}
                                 for p in ("4", "6")]
    checks["K5_source_pins"] = {"nets": k5, "pass": all(v == {"2": n, "4": n, "6": n}
                                                        for (q, v), n in zip(k5.items(), ("SW", "GND")))}
    if balls:
        terminals["U80.PH"] = [as_contact("top", balls["C1"]), as_contact("top", balls["D4"])]
        terminals["U80.GND"] = [as_contact("top", balls["A2"])]
    for kind in ("Ci", "Cm"):
        for cap in loop["capacitors"][kind]["caps"]:
            for p in cap["pads"]:
                terminals[f"{cap['ref']}.{p['net']}"] = [{"layer": cap["layer"], "bbox_mm": p["bbox_mm"],
                                                         "centre_mm": p["centre_mm"]}]

    old = loop["ports"]["scheme"]
    scheme = {
        "VIN": {"reference": "Q1.D", "branches": list(old["VIN"]["branches"])},
        "SW": {"reference": "Q2.D", "branches": ["Q1.S2", "Q1.S46", "U80.PH"]},
        "GND": {"reference": "Q2.S46", "branches": list(old["GND"]["branches"]) + ["Q2.S2", "U80.GND"]},
        "VGu": {"reference": "Q1.G", "branches": ["R80.G", "R81.G"]},
        "VGl": {"reference": "Q2.G", "branches": ["R82.G", "R83.G"]},
        "VGuH": {"reference": "R80.D", "branches": ["U80.UGH"]},
        "VGuL": {"reference": "R81.D", "branches": ["U80.UGL"]},
        "VGlH": {"reference": "R82.D", "branches": ["U80.LGH"]},
        "VGlL": {"reference": "R83.D", "branches": ["U80.LGL"]},
    }
    missing = sorted({t for s in scheme.values() for t in [s["reference"]] + s["branches"]} - set(terminals))
    checks["all_scheme_terminals_located"] = {"missing": missing, "pass": not missing}

    # Reported: other contacts on the gate nets, and the supply balls.
    used = {tuple(c["centre_mm"]) for v in terminals.values() for c in v}
    notes["other_gate_net_contacts"] = {q: [dict(as_contact(a["side"], a["c"]), side=a["side"]) for a in area
                                            if a["root"] == gate_root[q]
                                            and min(np.hypot(a["c"]["cx"] - ux, a["c"]["cy"] - uy) for ux, uy in used) > 0.05]
                                        for q in ("Q1", "Q2")}
    notes["supply_balls"] = {name: {"ball": ball, "centre_mm": [balls[ball]["cx"], balls[ball]["cy"]],
                                    "net": net_at(b, "GTL", balls[ball]["cx"], balls[ball]["cy"])}
                             for ball, name in BALLS.items() if name in ("VCC", "BOOT", "NC", "LI", "HI") and balls}

    report = {
        "schema": "epc90133-gate-loop/1",
        "scope": "Gate-drive loop contacts and ports for extraction variant G; geometry only, nothing extracted.",
        "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "power_loop_sha256": hashlib.sha256(LOOP.read_bytes()).hexdigest(),
        "sources": {"ball_map": "uP1966E datasheet (uP1966E_EPC-DS-F0000, Aug. 2021), pin description and package p. 12",
                    "resistors": "devices/epc/epc90133-schematic.json"},
        "ball_array": {"origin_mm": [float(origin[0]), float(origin[1])], "orientation": good[0] if len(good) == 1 else None,
                       "balls": {bl: {"name": BALLS[bl], "centre_mm": [balls[bl]["cx"], balls[bl]["cy"]],
                                      "net": net_at(b, "GTL", balls[bl]["cx"], balls[bl]["cy"])[0]} for bl in balls}},
        "gate_resistors": parts, "terminals": terminals, "scheme": scheme, "checks": checks, "notes": notes,
        "outcome": "pass" if all(c["pass"] for c in checks.values()) else "fail",
    }
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    render(b, report, args.render)
    print(json.dumps({k: v["pass"] for k, v in checks.items()}), report["outcome"])
    print("orientation", report["ball_array"]["orientation"])
    for r, p in parts.items():
        print(r, p["ohm"], p["driver_pin"], p["ball"], "drv", [round(x, 3) for x in p["driver_pad"]["centre_mm"]],
              "gate", [round(x, 3) for x in p["gate_pad"]["centre_mm"]])
    print("other gate-net contacts:", {q: [[round(x, 3) for x in c["centre_mm"]] + [c["side"]] for c in v]
                                       for q, v in notes["other_gate_net_contacts"].items()})
    return 0 if report["outcome"] == "pass" else 2


def render(b, report, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    x0, y0, x1, y1 = 13.5, 23.8, 19.0, 33.2
    i0, j0 = b.pixel(x0, y0)
    i1, j1 = b.pixel(x1, y1)
    lut = np.ones((b.counts["GTL"] + 1, 3))
    for lab in range(1, b.counts["GTL"] + 1):
        lut[lab] = NET_COLOURS[b.net_name.get(b.find(("GTL", lab)), "other")]
    img = 1 - (1 - lut[b.labels["GTL"][i0:i1 + 1, j0:j1 + 1]]) * 0.55
    fig, ax = plt.subplots(figsize=(7, 10), dpi=150)
    ax.imshow(img, origin="lower", extent=(x0, x1, y0, y1), interpolation="nearest")
    colours = {"U80": "black", "R8": "purple", "Q1": "darkred", "Q2": "navy"}
    for t, cs in report["terminals"].items():
        if t.startswith(("Ci", "Cm")):
            continue
        col = next((v for k, v in colours.items() if t.startswith(k)), "black")
        for c in cs:
            if c["layer"] != "GTL":
                continue
            bx = c["bbox_mm"]
            ax.add_patch(Rectangle((bx[0], bx[1]), bx[2] - bx[0], bx[3] - bx[1], fc="none", ec=col, lw=1.0, zorder=3))
            ax.text(c["centre_mm"][0], c["centre_mm"][1], t, fontsize=4.5, ha="center", va="center", color=col, zorder=4, clip_on=True,
                    bbox=dict(fc="white", ec="none", alpha=0.7, pad=0.1))
    for v in b.via_rows:
        if x0 <= v["x"] <= x1 and y0 <= v["y"] <= y1:
            ax.add_patch(plt.Circle((v["x"], v["y"]), v["d"] / 2, fc="none", ec="k", lw=0.4, zorder=2))
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_title("EPC90133 gate-drive terminals (top layer; colours: VIN red, SW green, GND blue, other tan)", fontsize=7)
    fig.tight_layout()
    fig.savefig(path)


if __name__ == "__main__":
    raise SystemExit(main())
