#!/usr/bin/env python3
"""FasterCap case H: a 3D board-like check (strip over a finite dielectric slab) against the same cross-section in 2D.

Declared 1 October 2026, before its first run (owner, 1 October: advance tool qualification). The known-answer
qualification (scripts/fastercap_known_answer.py) passed only 2D microstrips (G) and a 3D sphere in air (B); its
documented requirement before board use is "a board-like 3D check with a declared refinement sequence". This is that
check, in its simplest form.

Geometry (SI units), the cross-section of case G with the slab truncated at +-S, extruded along y:
* symmetric form as in G: a slab of eps_r 4.3 from z = -h to h, a strip on each face (z = h..h+t and -h-t..-h),
  driven in opposite phase, so the mid-plane is the ground plane and C_ms = 2 x the pair capacitance;
* h = 0.1 mm, w = 2h, t = h/100, S = 10h; strip length L, slab extending E = 10h beyond each strip end;
* each strip's face towards the slab lies in the dielectric, its other faces in air; the slab surface outside the
  strip footprints is a dielectric interface.
Per-unit-length 3D value: C' = 2 [C_pair(L2) - C_pair(L1)] / (L2 - L1), L1 = 20h, L2 = 40h, so the end effects cancel
to the extent they are equal (strip ends at least 20h apart).
Reference: FasterCap 2D for the same cross-section (case G's builder with half-span S), at -a0.005 and -a0.001;
case G showed the 2D solver within 0.004 % of Hammerstad-Jensen for this cross-section with S = 40h. The
Hammerstad-Jensen value (infinite slab) is reported for context only.
H1 accuracy: the 3D C' at the finest setting within 2 % of the 2D reference (-a0.001).
H2 refinement: 3D settings -a0.01, -a0.005, -a0.002 (FasterCap's automatic refinement is a stopping rule, not an
   error bound, as cases A and C showed); C' from the two finest within 1 %.
H3 2D reference self-consistency: -a0.005 and -a0.001 within 0.5 %.
Time limit 3 h per FasterCap call; a timeout fails the check that needs that value. A pass qualifies thin 3D
strips over a planar dielectric interface with finite extent, against 2D, at this scale. It does not qualify plane
pairs, holes or vias, solder mask, thick copper, several dielectric layers or curved interfaces.

    python scripts/fastercap_board3d_check.py   # results/gan/fastercap-board3d-check.json
"""
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from fastercap_known_answer import (ER, FC_BIN, case_g, hammerstad_jensen, pair, quad_box,  # noqa: E402
                                    run_fastercap)

H = 0.1e-3
W, T, S, E = 2 * H, H / 100, 10 * H, 10 * H
L1, L2 = 20 * H, 40 * H
AUTO_3D = ("0.01", "0.005", "0.002")
AUTO_2D = ("0.005", "0.001")
TOL_H1, TOL_H2, TOL_H3 = 0.02, 0.01, 0.005
TIMEOUT = 3 * 3600
OUTPUT = ROOT / "results/gan/fastercap-board3d-check.json"


def q(name, *pts):
    return f"Q {name} " + "  ".join(" ".join(f"{v:.9g}" for v in p) for p in pts) + "\n"


def rect_z(name, x0, x1, y0, y1, z):
    return q(name, (x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z))


def case_3d(L):
    x0, x1, y0, y1 = -W / 2, W / 2, -L / 2, L / 2
    files = {"ms3d.lst": f"* 3D microstrip by symmetry, L = {L:g} m, eps_r {ER}\n"}
    for tag, zb, zt, inner in (("top", H, H + T, H), ("bot", -H - T, -H, -H)):
        box = quad_box(tag, x0, y0, zb, x1, y1, zt).splitlines()
        # quad_box face order: +x, -x, +y, -y, z = zb, z = zt; the face on the slab is z = H (top) or z = -H (bottom)
        slab_face = box[4] if tag == "top" else box[5]
        air = [f for f in box if f is not slab_face]
        files[f"{tag}_air.txt"] = f"* {tag} strip, air faces\n" + "\n".join(air) + "\n"
        files[f"{tag}_diel.txt"] = f"* {tag} strip, slab face\n" + slab_face + "\n"
        files["ms3d.lst"] += f"C {tag}_air.txt 1.0 0 0 0 +\nC {tag}_diel.txt {ER} 0 0 0\n"
    Y0, Y1 = y0 - E, y1 + E
    iface = ""
    for z in (H, -H):  # slab faces minus the strip footprint, as four rectangles
        iface += rect_z("slab", -S, x0, Y0, Y1, z) + rect_z("slab", x1, S, Y0, Y1, z)
        iface += rect_z("slab", x0, x1, Y0, y0, z) + rect_z("slab", x0, x1, y1, Y1, z)
    iface += q("slab", (-S, Y0, -H), (-S, Y1, -H), (-S, Y1, H), (-S, Y0, H))
    iface += q("slab", (S, Y0, -H), (S, Y0, H), (S, Y1, H), (S, Y1, -H))
    iface += q("slab", (-S, Y0, -H), (-S, Y0, H), (S, Y0, H), (S, Y0, -H))
    iface += q("slab", (-S, Y1, -H), (S, Y1, -H), (S, Y1, H), (-S, Y1, H))
    files["slab.txt"] = "* slab surface except under the strips\n" + iface
    files["ms3d.lst"] += f"D slab.txt 1.0 {ER} 0 0 0 0 0 0 -\n"
    return files


def main():
    run_root = ROOT / "runs" / f"fastercap-board3d-{uuid.uuid4().hex[:12]}"
    rep = {"schema": "fastercap-board3d-check/1", "declared": "2026-10-01, before the first run (docstring)",
           "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "binary_sha256": hashlib.sha256(FC_BIN.read_bytes()).hexdigest(),
           "geometry_m": {"h": H, "w": W, "t": T, "half_span": S, "end_extension": E, "L1": L1, "L2": L2, "eps_r": ER},
           "hammerstad_jensen_F_per_m": hammerstad_jensen(W / H, T / H, ER),
           "run_directory": run_root.relative_to(ROOT).as_posix(), "two_d": {}, "three_d": {}, "errors": []}

    def save():
        tmp = OUTPUT.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(rep, indent=1) + "\n")
        os.replace(tmp, OUTPUT)

    # 2D reference, same cross-section and truncation
    files2d, _, extract2d, _ = case_g(ER)
    files2d = {k: v.replace(f"{40 * H:.9g}", f"{S:.9g}") for k, v in files2d.items()}
    if f"{S:.9g}" not in files2d["slab.txt"]:
        raise SystemExit("2D slab truncation was not replaced")
    for auto in AUTO_2D:
        try:
            m, names, _ = run_fastercap(files2d, run_root / "2d", auto, TIMEOUT)
            rep["two_d"][auto] = {"matrix": m, "value_F_per_m": extract2d(m)}
        except RuntimeError as exc:
            rep["errors"].append(f"2D -a{auto}: {exc}")
        save()
        print("2D", auto, rep["two_d"].get(auto, {}).get("value_F_per_m"), flush=True)
    for auto in AUTO_3D:
        row = {}
        for L in (L1, L2):
            try:
                m, names, _ = run_fastercap(case_3d(L), run_root / f"3d-L{L * 1e3:g}mm", auto, TIMEOUT)
                row[f"{L:g}"] = {"matrix": m, "C_pair_F": pair(m)}
            except RuntimeError as exc:
                rep["errors"].append(f"3D L={L:g} -a{auto}: {exc}")
        if len(row) == 2:
            row["C_per_m"] = 2 * (row[f"{L2:g}"]["C_pair_F"] - row[f"{L1:g}"]["C_pair_F"]) / (L2 - L1)
        rep["three_d"][auto] = row
        save()
        print("3D", auto, row.get("C_per_m"), flush=True)

    ref = rep["two_d"].get(AUTO_2D[-1], {}).get("value_F_per_m")
    c3 = [rep["three_d"].get(a, {}).get("C_per_m") for a in AUTO_3D]
    h3 = (abs(rep["two_d"][AUTO_2D[0]]["value_F_per_m"] / ref - 1) if ref and AUTO_2D[0] in rep["two_d"] else None)
    h2 = abs(c3[-1] / c3[-2] - 1) if c3[-1] and c3[-2] else None
    h1 = c3[-1] / ref - 1 if c3[-1] and ref else None
    rep["checks"] = {"H1": {"relative_error": h1, "tolerance": TOL_H1, "pass": h1 is not None and abs(h1) <= TOL_H1},
                     "H2": {"change": h2, "tolerance": TOL_H2, "pass": h2 is not None and h2 <= TOL_H2},
                     "H3": {"change": h3, "tolerance": TOL_H3, "pass": h3 is not None and h3 <= TOL_H3}}
    rep["all_pass"] = all(v["pass"] for v in rep["checks"].values())
    save()
    print(json.dumps(rep["checks"], indent=1))


if __name__ == "__main__":
    main()
