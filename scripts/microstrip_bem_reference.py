#!/usr/bin/env python3
"""Independent 2D reference for case H's cross-section: a symmetric microstrip on a finite slab, boundary elements.

Declared 3 October 2026, before it is run and before FasterCap user-mesh run 4 (scripts/fastercap_manual_mesh_check.py)
has produced any dielectric value at its finer meshes. Check D4 of that script compares its 3D C' with a FasterCap 2D
value at -a0.001 (123.23 pF/m, case H). FasterCap's automatic 2D refinement has since been shown to stall: case H's own
2D check H3 moved 15.8 % between settings, and in the via-array benchmark single-via references sat 1.3-2.1 % off at
some settings. This script provides an independent value from circuit_tools.bem2d (constant-charge boundary elements
with dielectric interfaces; tests/test_bem2d.py checks it against the exact dielectric-coated coax).

Geometry (case H, SI): h = 0.1 mm, w = 2h, t = h/100, eps_r 4.3; slab |x| <= S, |y| <= h; strips on both faces
(y = h ... h + t and -h - t ... -h), driven at +-0.5 V; C_ms = 2 C_pair. Each straight segment (strip faces, slab faces
split at the strip edges, slab sides) gets n cosine-clustered panels. The strip faces on the slab carry eps_r 4.3, the
others air.
Checks, fixed here:
    B1 accuracy: at S = 40h (case G's span) the Richardson value of n = 256 and 512 is within 0.3 % of
       Hammerstad-Jensen (case G(ii) put FasterCap 2D within 0.004 % of it at that span);
    B2 convergence: at S = 10h (case H's span) the Richardson values of (n = 128, 256) and (256, 512) agree within 0.1 %.
The S = 10h Richardson value of (256, 512) is the reference. Reported, not judged: its difference from case H's
FasterCap 2D value at -a0.001 and -a0.005. Declared use: once run 4 finishes, its dielectric C' at M3 is also reported
against this reference beside the declared D4 (which stays as declared).

    python scripts/microstrip_bem_reference.py   # results/gan/microstrip-bem-reference.json
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

from circuit_tools.bem2d import segment_panels, solve_dielectric  # noqa: E402
from fastercap_known_answer import hammerstad_jensen  # noqa: E402

H = 0.1e-3
W, T, ER = 2 * H, H / 100, 4.3
OUTPUT = ROOT / "results/gan/microstrip-bem-reference.json"
LEVELS = (128, 256, 512)


def c_ms(S, n):
    x0, x1 = -W / 2, W / 2
    strips = []
    for sgn in (1, -1):
        yb, yt = (H, H + T) if sgn > 0 else (-H - T, -H)
        on_slab = H if sgn > 0 else -H
        far = yt if sgn > 0 else yb
        diel = segment_panels(x0, on_slab, x1, on_slab, n)
        air = np.vstack([segment_panels(x0, far, x1, far, n), segment_panels(x0, yb, x0, yt, max(2, n // 16)),
                         segment_panels(x1, yb, x1, yt, max(2, n // 16))])
        strips.append([(diel, ER), (air, 1.0)])
    faces = []  # (panels, nx, ny): normals out of the slab
    for y, ny in ((H, 1.0), (-H, -1.0)):
        for a, b in ((-S, x0), (x1, S)):
            p = segment_panels(a, y, b, y, n)
            faces.append((p, np.zeros(len(p)), np.full(len(p), ny)))
    for x, nx in ((S, 1.0), (-S, -1.0)):
        p = segment_panels(x, -H, x, H, n)
        faces.append((p, np.full(len(p), nx), np.zeros(len(p))))
    interfaces = [(p, nx, ny, 1.0, ER) for p, nx, ny in faces]
    q = solve_dielectric(strips, interfaces, [0.5, -0.5])
    return 2 * q[0]  # C_pair = q_top / 1 V; C_ms = 2 C_pair


def richardson(a, b):
    """First-order extrapolation from n and 2n."""
    return 2 * b - a


def main():
    h_rep = json.loads((ROOT / "results/gan/fastercap-board3d-check.json").read_text(encoding="utf-8"))
    out = {"schema": "microstrip-bem-reference/1", "declared": "2026-10-03, before it was run (docstring)",
           "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "dependencies_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                                   for p in ("src/circuit_tools/bem2d.py", "scripts/fastercap_known_answer.py")},
           "values_F_per_m": {}}
    for S in (40 * H, 10 * H):
        row = {str(n): c_ms(S, n) for n in LEVELS}
        out["values_F_per_m"][f"S={S / H:g}h"] = row
        print(S / H, row, flush=True)
    v40, v10 = out["values_F_per_m"]["S=40h"], out["values_F_per_m"]["S=10h"]
    r40 = richardson(v40["256"], v40["512"])
    hj = hammerstad_jensen(W / H, T / H, ER)
    r10a, r10b = richardson(v10["128"], v10["256"]), richardson(v10["256"], v10["512"])
    out["checks"] = {"B1": {"richardson_S40h": r40, "hammerstad_jensen": hj, "relative_error": r40 / hj - 1,
                            "pass": abs(r40 / hj - 1) <= 0.003},
                     "B2": {"richardson_128_256": r10a, "richardson_256_512": r10b, "change": abs(r10b / r10a - 1),
                            "pass": abs(r10b / r10a - 1) <= 0.001}}
    out["reference_S10h_F_per_m"] = r10b
    out["fastercap_2d_case_h"] = {a: {"value": v["value_F_per_m"], "vs_bem": v["value_F_per_m"] / r10b - 1}
                                  for a, v in h_rep["two_d"].items() if v.get("value_F_per_m")}
    out["all_pass"] = all(c["pass"] for c in out["checks"].values())
    OUTPUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("checks", "reference_S10h_F_per_m", "fastercap_2d_case_h")}, indent=1))


if __name__ == "__main__":
    main()
