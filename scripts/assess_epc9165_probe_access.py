#!/usr/bin/env python3
"""Post-hoc reading of the EPC9165 audit (run 2): probe access with the heatsink on the bottom side.

Run 2 of scripts/audit_epc9165_board_files.py found the FETs on the bottom side and passed G1-G4, but its
heatsink-side rule sampled the solder mask 1.0 mm from each 3.0 mm mounting-hole centre, outside the bottom
openings (about 1.35 mm across), and returned no side; its "inside_heatsink" flags are therefore all false and not
usable. The stop rules allowed no further fix run. This assessment, written after run 2, records the mask evidence
at the hole centres and re-reads the same contact list (rebuilt deterministically with the audit's own functions,
and checked against run 2's per-net contact counts) with a contact counted as covered when it is on the bottom
side inside the mechanical-13 heatsink rectangle. It is a labelled post-hoc reading, not a declared check.

    PYTHONPATH=src python scripts/assess_epc9165_probe_access.py   # results/gan/epc9165-probe-access.json
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import audit_epc9165_board_files as au  # noqa: E402
from circuit_tools.gerber import load_layer, parse_excellon, rasterize  # noqa: E402

REPORT = ROOT / "results/gan/epc9165-board-audit.json"
OUTPUT = ROOT / "results/gan/epc9165-probe-access.json"


def main():
    rep = json.loads(REPORT.read_text(encoding="utf-8"))
    g = rep["geometry"]
    fets = [tuple(r) for r in g["G2_outlines"]["fet_outlines"]]
    hs = tuple(g["G2_outlines"]["heatsink_rect_mm"])
    drills = parse_excellon((au.GERBERS / f"{au.PREFIX}NC Drill.TXT").read_text(errors="replace"))
    bounds = tuple(g["board_bounds_mm"])
    nets = au.Nets(bounds, drills)
    holes = [d for d in drills if abs(d.diameter - 3.0) < 0.05]
    mask_at_holes = {}
    for side, mask in (("top", "GTS"), ("bottom", "GBS")):
        m = rasterize(load_layer(au.GERBERS / f"{au.PREFIX}Gerbers.{mask}"), bounds, au.PITCH).grid
        mask_at_holes[side] = [bool(m[nets.idx(h.x, h.y)]) for h in holes]
    hs_side = "bottom" if all(mask_at_holes["bottom"]) and not any(mask_at_holes["top"]) else None

    fet_nets = [nets.in_rect("GBL", r) for r in fets]
    phases = g["G4_switch_nodes"]["phases_fet_indices"]
    labels = {}
    for k, ph in enumerate(phases, 1):
        for n in fet_nets[ph[0]] & fet_nets[ph[1]]:
            if not any(n in fet_nets[j] for j in range(len(fets)) if j not in ph):
                labels[n] = f"SW_phase{k}"
    for i, ns in enumerate(fet_nets):
        for n in ns:
            if sum(n in o for o in fet_nets) == 1:
                labels.setdefault(n, f"one_fet_net_{i}")
    cs = au.contacts(nets, bounds)
    out, consistent = {}, True
    for n, lab in labels.items():
        touched = [i for i, ns in enumerate(fet_nets) if n in ns]
        rows = []
        for c in cs:
            if c["net"] != n:
                continue
            p = (c["cx"], c["cy"])
            rows.append({"side": c["side"], "xy_mm": [round(p[0], 2), round(p[1], 2)],
                         "size_mm": [round(c["w"], 2), round(c["h"], 2)],
                         "covered_by_heatsink": bool(c["side"] == hs_side and au.inside(p, hs)),
                         "distance_to_its_fet_mm": round(min(au.rect_dist(p, fets[i]) for i in touched), 2)})
        stored = g["probe_access"].get(lab, {}).get("contacts")
        consistent &= stored == len(rows)
        open_rows = sorted((r for r in rows if not r["covered_by_heatsink"]), key=lambda r: r["distance_to_its_fet_mm"])
        out[lab] = {"fets": touched, "contacts": len(rows), "uncovered": len(open_rows), "uncovered_contacts": open_rows}
    result = {"schema": "epc9165-probe-access/1", "post_hoc": True,
              "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "inputs": {REPORT.relative_to(ROOT).as_posix(): hashlib.sha256(REPORT.read_bytes()).hexdigest()},
              "mask_open_at_mounting_hole_centres": mask_at_holes, "heatsink_side": hs_side,
              "contact_counts_match_run2": bool(consistent), "nets": out}
    OUTPUT.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print("heatsink side", hs_side, mask_at_holes, "counts match run 2:", consistent)
    for lab, v in out.items():
        print(lab, "fets", v["fets"], "contacts", v["contacts"], "uncovered", v["uncovered"])
        for r in v["uncovered_contacts"][:6]:
            print("   ", r)


if __name__ == "__main__":
    main()
