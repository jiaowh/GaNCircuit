#!/usr/bin/env python3
"""FasterCap case H geometry with edge-refined user meshes, and the 2D emulation that predicts each mesh's error.

Declared 3 October 2026, before its first run. scripts/fastercap_manual_mesh_check.py (revision 2) showed with user meshes
and a tight interaction threshold that the air form is physical and accurate (run 2: within 0.53 % of
Hammerstad-Jensen) while the dielectric form converges slowly (run 4: C' = 116.8 and 118.3 pF/m on M1 and M2,
-5.1 % and -3.9 % against the independent 2D reference 123.10 pF/m of scripts/microstrip_bem_reference.py); M3 exceeded
its 1 h limit. A post-hoc 2D boundary-element emulation with the same panel layout (this script, emulate_2d) gives
air -0.48 % and dielectric -5.5 % / -4.0 % / -2.8 % on M1/M2/M3: the 3D values are what those meshes should give, and
the dielectric shortfall is discretisation at the strip edges. In 2D, refining only the panels at the strip's side
edges removes it (edge panel 1.25 um: -0.76 %; 0.625 um: -0.13 %).

Mesh E1 (fixed here): case H's geometry and .lst structure exactly as scripts/fastercap_manual_mesh_check.py case_d,
dielectric form, with x lines graded from 1.25 um at the strip's side edges (x = +-w/2) and 10 um (= w/20) at the slab
edges, ratio 1.2, up to 160 um; y lines as that script's M2 (10 um at every break). FasterCap -m1e9 -d1e-11 (no
refinement, interaction threshold 0.01), 3 h per call. C' from L1 = 2 mm and L2 = 4 mm as before.
Checks:
    D1 validity: both matrices pass the physical-validity gate;
    D4 accuracy: C'(E1) within 2 % of the 2D reference 123.10 pF/m;
    D6 emulation: C'(E1) within 0.5 % of the 2D emulation of E1's own panel layout (C'(2D, E1 layout)).
Reading fixed here: D1, D4 and D6 pass -> FasterCap's 3D dielectric solution reproduces what its mesh should give, and
an edge-refined mesh reaches the reference within the D4 tolerance. Convergence evidence then rests on the 2D emulation
series (E1 and finer edge panels), not on a 3D refinement series, which would take most of a day per mesh on this host.
A pass does not qualify FasterCap for board geometry; part K1 (partly filled plates) stays unrun.

    python scripts/fastercap_edge_mesh_check.py   # results/gan/fastercap-edge-mesh-check.json
"""
import hashlib
import json
from pathlib import Path
import sys
import uuid

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import fastercap_manual_mesh_check as fm  # noqa: E402
from circuit_tools.bem2d import solve_dielectric  # noqa: E402
from fastercap_board3d_check import matrix_validity  # noqa: E402
from fastercap_known_answer import FC_BIN, pair  # noqa: E402

OUTPUT = ROOT / "results/gan/fastercap-edge-mesh-check.json"
H, W, T, ER, S, E = fm.H, fm.W, fm.T, fm.ER, fm.S, fm.E
P, P_EDGE, RATIO, PMAX = W / 20, 1.25e-6, 1.2, 16 * W / 20
REF_2D = 1.23099722223097e-10  # results/gan/microstrip-bem-reference.json
TIMEOUT = 3 * 3600
DEPENDENCIES = ("scripts/fastercap_manual_mesh_check.py", "scripts/fastercap_board3d_check.py",
                "scripts/fastercap_known_answer.py", "src/circuit_tools/bem2d.py", "results/gan/microstrip-bem-reference.json")


def graded2(breaks, sizes, ratio=RATIO, pmax=PMAX):
    """Lines through every break with its own starting size, growing by ratio towards the interval middle."""
    out = [breaks[0]]
    for (u, pu), (v, pv) in zip(zip(breaks, sizes), zip(breaks[1:], sizes[1:])):
        left, right, x, y, s, t = [], [], u, v, pu, pv
        while True:
            if s <= t:
                if x + s >= y - 0.5 * s:
                    break
                x += s
                left.append(x)
                s = min(s * ratio, pmax)
            else:
                if y - t <= x + 0.5 * t:
                    break
                y -= t
                right.append(y)
                t = min(t * ratio, pmax)
        out += left + right[::-1] + [v]
    return out


def x_lines():
    return graded2([-S, -W / 2, W / 2, S], [P, P_EDGE, P_EDGE, P])


def case_e1(L):
    """case_d of the user-mesh check with E1's x lines (dielectric form)."""
    xs = x_lines()
    Y0, Y1 = -L / 2 - E, L / 2 + E
    ys = fm.graded([Y0, -L / 2, L / 2, Y1], P)
    sx = [x for x in xs if -W / 2 - 1e-15 <= x <= W / 2 + 1e-15]
    sy = [y for y in ys if -L / 2 - 1e-15 <= y <= L / 2 + 1e-15]
    files = {"ms3d.lst": f"* case H geometry, edge-refined user mesh E1, L = {L:g} m, diel\n"}
    for tag, zb, zt in (("top", H, H + T), ("bot", -H - T, -H)):
        f = fm.box_faces(tag, sx, sy, [zb, zt])
        on_slab = "z0" if tag == "top" else "z1"
        air = [ln for k, v in f.items() if k != on_slab for ln in v]
        files[f"{tag}_air.txt"] = f"* {tag} strip, air faces\n" + "\n".join(air) + "\n"
        files[f"{tag}_diel.txt"] = f"* {tag} strip, slab face\n" + "\n".join(f[on_slab]) + "\n"
        files["ms3d.lst"] += f"C {tag}_air.txt 1.0 0 0 0 +\nC {tag}_diel.txt {ER} 0 0 0\n"
    zs = fm.graded([-H, H], P)
    under = lambda u, v: abs(u) < W / 2 and abs(v) < L / 2  # noqa: E731
    slab = fm.quads("slab", 2, H, xs, ys, under) + fm.quads("slab", 2, -H, xs, ys, under)
    f = fm.box_faces("slab", xs, ys, zs)
    slab += f["x0"] + f["x1"] + f["y0"] + f["y1"]
    files["slab.txt"] = "* slab surface except under the strips\n" + "\n".join(slab) + "\n"
    files["ms3d.lst"] += f"D slab.txt 1.0 {ER} 0 0 0 0 0 0 -\n"
    return files


def emulate_2d(xs, zs, er):
    """C_ms per metre of the 2D cross-section with the given x lines (strip and slab faces) and z lines (slab sides)."""
    seg = lambda lines, fixed, axis: np.array([(a, fixed, b, fixed) if axis == "x" else (fixed, a, fixed, b)  # noqa: E731
                                               for a, b in zip(lines, lines[1:])])
    sx = [x for x in xs if -W / 2 - 1e-15 <= x <= W / 2 + 1e-15]
    strips = []
    for sg in (1, -1):
        yb, yt = (H, H + T) if sg > 0 else (-H - T, -H)
        on, far = (H, yt) if sg > 0 else (-H, yb)
        strips.append([(seg(sx, on, "x"), er),
                       (np.vstack([seg(sx, far, "x"), seg([yb, yt], -W / 2, "y"), seg([yb, yt], W / 2, "y")]), 1.0)])
    inter = []
    if er != 1.0:
        for y, ny in ((H, 1.0), (-H, -1.0)):
            for part in ([x for x in xs if x <= -W / 2 + 1e-15], [x for x in xs if x >= W / 2 - 1e-15]):
                pp = seg(part, y, "x")
                inter.append((pp, np.zeros(len(pp)), np.full(len(pp), ny), 1.0, er))
        for x, nx in ((S, 1.0), (-S, -1.0)):
            pp = seg(zs, x, "y")
            inter.append((pp, np.full(len(pp), nx), np.zeros(len(pp)), 1.0, er))
    return float(2 * solve_dielectric(strips, inter, [0.5, -0.5])[0])


def main():
    run_root = ROOT / "runs" / f"fastercap-edge-mesh-{uuid.uuid4().hex[:12]}"
    rep = {"schema": "fastercap-edge-mesh-check/1", "declared": "2026-10-03, before the first run (docstring)",
           "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "dependencies_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in DEPENDENCIES},
           "binary_sha256": hashlib.sha256(FC_BIN.read_bytes()).hexdigest(),
           "run_directory": run_root.relative_to(ROOT).as_posix(), "reference_2d_F_per_m": REF_2D, "errors": []}
    zs = fm.graded([-H, H], P)
    rep["emulation_2d"] = {
        "declared_meshes": {m: {"air": emulate_2d(fm.graded([-S, -W / 2, W / 2, S], p), fm.graded([-H, H], p), 1.0),
                                "diel": emulate_2d(fm.graded([-S, -W / 2, W / 2, S], p), fm.graded([-H, H], p), ER)}
                            for m, p in fm.D_MESHES.items()},
        "E1": emulate_2d(x_lines(), zs, ER)}
    print("2D emulation", rep["emulation_2d"], flush=True)
    OUTPUT.write_text(json.dumps(rep, indent=1) + "\n")
    runs = {}
    for L in (fm.L1, fm.L2):
        try:
            m, n_in, n_ref, secs = fm.run(case_e1(L), run_root / f"e1-L{L * 1e3:g}mm", "-m1e9 -d1e-11", TIMEOUT)
            val = matrix_validity(m)
            runs[f"{L:g}"] = {"matrix": m, "validity": val, "input_panels": n_in, "panels_after_refinement": n_ref,
                              "seconds": secs, "C_pair_F": pair(m) if not val else None}
        except RuntimeError as exc:
            runs[f"{L:g}"] = {"error": str(exc)}
            rep["errors"].append(f"L={L:g}: {exc}")
        print(L, {k: v for k, v in runs[f"{L:g}"].items() if k != "matrix"}, flush=True)
        rep["runs"] = runs
        OUTPUT.write_text(json.dumps(rep, indent=1) + "\n")
    a, b = runs[f"{fm.L1:g}"].get("C_pair_F"), runs[f"{fm.L2:g}"].get("C_pair_F")
    cp = 2 * (b - a) / (fm.L2 - fm.L1) if a and b and b > a > 0 else None
    e1 = rep["emulation_2d"]["E1"]
    rep["C_per_m"] = cp
    rep["checks"] = {
        "D1_valid": all("matrix" in r and not r["validity"] for r in runs.values()),
        "D4_vs_reference": {"relative_error": cp / REF_2D - 1 if cp else None, "pass": bool(cp and abs(cp / REF_2D - 1) <= 0.02)},
        "D6_vs_emulation": {"emulation_F_per_m": e1, "relative_error": cp / e1 - 1 if cp else None,
                            "pass": bool(cp and abs(cp / e1 - 1) <= 0.005)}}
    rep["all_pass"] = bool(rep["checks"]["D1_valid"] and rep["checks"]["D4_vs_reference"]["pass"]
                           and rep["checks"]["D6_vs_emulation"]["pass"])
    rep["outcome"] = "complete"
    OUTPUT.write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep["checks"], indent=1))


if __name__ == "__main__":
    main()
