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

Validity gate (added 2 October 2026 after the audit at 75d6f35, which reproduced all_pass on synthetic negative-
diagonal matrices; the stored run predates it and its verdict, failed, is unchanged): every returned matrix must be
square, finite and physical before any derived value is formed: diagonal > 0, off-diagonal <= REL_TOL x the largest
diagonal (Maxwell matrices have non-positive off-diagonals), each row sum >= -REL_TOL x the largest diagonal,
|C_ij - C_ji| <= REL_TOL x the largest diagonal, and the symmetric part positive definite. REL_TOL = 1e-3 (FasterCap's
stored matrices are reciprocal to about 1e-4). An invalid matrix is kept raw with its reasons; it gives no pair
capacitance, no C' and no check pass. The post-hoc invalidity of the stored run is recorded separately by
scripts/assess_fastercap_board3d.py, bound to the report's hash. Reports from now on also bind the imported helpers
(scripts/fastercap_known_answer.py: geometry builders, solver runner, pair capacitance) by sha256 under
"dependencies_sha256".

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
DEPENDENCIES = ("scripts/fastercap_known_answer.py",)  # imported code that shapes the result, bound by hash
sys.path.insert(0, str(ROOT / "scripts"))
from fastercap_known_answer import (ER, FC_BIN, case_g, hammerstad_jensen, pair, quad_box,  # noqa: E402
                                    run_fastercap)

H = 0.1e-3
W, T, S, E = 2 * H, H / 100, 10 * H, 10 * H
L1, L2 = 20 * H, 40 * H
AUTO_3D = ("0.01", "0.005", "0.002")
AUTO_2D = ("0.005", "0.001")
TOL_H1, TOL_H2, TOL_H3 = 0.02, 0.01, 0.005
REL_TOL = 1e-3
TIMEOUT = 3 * 3600
OUTPUT = ROOT / "results/gan/fastercap-board3d-check.json"


def q(name, *pts):
    return f"Q {name} " + "  ".join(" ".join(f"{v:.9g}" for v in p) for p in pts) + "\n"


def rect_z(name, x0, x1, y0, y1, z):
    return q(name, (x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z))


def dependency_hashes(paths=DEPENDENCIES):
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}


def matrix_validity(m, rel_tol=REL_TOL):
    """List of reasons why m is not a physical Maxwell capacitance matrix (empty if it is valid)."""
    try:
        n = len(m)
        rows = [[float(v) for v in r] for r in m]
    except (TypeError, ValueError):
        return ["not a numeric matrix"]
    if n == 0 or any(len(r) != n for r in rows):
        return ["not square"]
    if not all(math.isfinite(v) for r in rows for v in r):
        return ["non-finite entry"]
    reasons = []
    scale = max(abs(rows[i][i]) for i in range(n)) or 1.0
    if any(rows[i][i] <= 0 for i in range(n)):
        reasons.append("non-positive diagonal")
    if any(rows[i][j] > rel_tol * scale for i in range(n) for j in range(n) if i != j):
        reasons.append("positive off-diagonal")
    if any(sum(r) < -rel_tol * scale for r in rows):
        reasons.append("negative row sum")
    if any(abs(rows[i][j] - rows[j][i]) > rel_tol * scale for i in range(n) for j in range(i)):
        reasons.append("not reciprocal")
    sym = [[(rows[i][j] + rows[j][i]) / 2 for j in range(n)] for i in range(n)]
    # positive definite: every leading principal minor positive (Sylvester), by Gaussian elimination
    a = [r[:] for r in sym]
    for k in range(n):
        if a[k][k] <= 0:
            reasons.append("not positive definite")
            break
        for i in range(k + 1, n):
            f = a[i][k] / a[k][k]
            for j in range(k, n):
                a[i][j] -= f * a[k][j]
    return reasons


def evaluate(rep):
    """Validity per matrix, C' only from valid pairs, and the H checks; fills rep in place."""
    for auto, row in rep["two_d"].items():
        row["validity"] = matrix_validity(row["matrix"])
        if row["validity"]:
            row["value_F_per_m"] = None
    for auto, row in rep["three_d"].items():
        for key, v in row.items():
            if isinstance(v, dict) and "matrix" in v:
                v["validity"] = matrix_validity(v["matrix"])
                if v["validity"]:
                    v["C_pair_F"] = None
        a, b = row.get(f"{L1:g}", {}), row.get(f"{L2:g}", {})
        ok = a.get("C_pair_F") is not None and b.get("C_pair_F") is not None and b["C_pair_F"] > a["C_pair_F"] > 0
        row["C_per_m"] = 2 * (b["C_pair_F"] - a["C_pair_F"]) / (L2 - L1) if ok else None
    ref = rep["two_d"].get(AUTO_2D[-1], {}).get("value_F_per_m")
    first = rep["two_d"].get(AUTO_2D[0], {}).get("value_F_per_m")
    c3 = [rep["three_d"].get(a, {}).get("C_per_m") for a in AUTO_3D]
    h3 = abs(first / ref - 1) if ref and first else None
    h2 = abs(c3[-1] / c3[-2] - 1) if c3[-1] and c3[-2] else None
    h1 = c3[-1] / ref - 1 if c3[-1] and ref else None
    rep["checks"] = {"H1": {"relative_error": h1, "tolerance": TOL_H1, "pass": h1 is not None and abs(h1) <= TOL_H1},
                     "H2": {"change": h2, "tolerance": TOL_H2, "pass": h2 is not None and h2 <= TOL_H2},
                     "H3": {"change": h3, "tolerance": TOL_H3, "pass": h3 is not None and h3 <= TOL_H3}}
    rep["invalid_matrices"] = [f"2D -a{a}" for a, r in rep["two_d"].items() if r["validity"]] + \
        [f"3D L={k} -a{a}" for a, r in rep["three_d"].items() for k, v in r.items()
         if isinstance(v, dict) and v.get("validity")]
    rep["all_pass"] = all(v["pass"] for v in rep["checks"].values()) and not rep["invalid_matrices"]
    return rep


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
    rep = {"schema": "fastercap-board3d-check/2", "declared": "2026-10-01, before the first run (docstring)",
           "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "dependencies_sha256": dependency_hashes(),
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
                row[f"{L:g}"] = {"matrix": m, "C_pair_F": pair(m) if not matrix_validity(m) else None}
            except RuntimeError as exc:
                rep["errors"].append(f"3D L={L:g} -a{auto}: {exc}")
        rep["three_d"][auto] = row
        evaluate(rep)
        save()
        print("3D", auto, row.get("C_per_m"), flush=True)

    evaluate(rep)
    save()
    print(json.dumps(rep["checks"], indent=1))


if __name__ == "__main__":
    main()
