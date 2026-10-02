#!/usr/bin/env python3
"""Post-hoc diagnostic of the slot benchmark: is the production-mesh error explained by the mesh's topology alone?

Declared 3 October 2026 before it is run, after the board-pitch (m1, m2) cases of scripts/plane_hole_benchmark.py had
finished and before its fine meshes had. Not part of that benchmark's declared checks. Reading of those cases: at the
board pitches FastHenry's added inductance for a slot through both plates (P1) falls well below the 2D sheet
reference, and the unslotted strip comes out near mu0 (h + delta) L / (W + s) instead of L / W, as if every copper edge
were widened by s/2 (the segment-width overreach that the mesh topology audit measured on the board).

Hypothesis. In the plane-pair (TEM) limit the production mesh acts as a resistor network on its grid: one unit
conductance per segment the centre-line rule keeps (width s over length s), the x = 0 column at one potential and the
x = L column (the wall) at the other. Its resistance in squares N_net gives L_net = mu0 (h + delta) N_net. If FastHenry's
board-pitch dL for each P1 case is close to the network's dL_net, the production error is a property of the mesh
topology, computable without FastHenry for any slot shape (including the board's own slots), and FastHenry itself is
not the source of the error.

Quantities, for every P1 case at m1 and m2, aligned and shifted, and for the unslotted strip:
    dL_net = mu0 (h + delta) [N_net(slot) - N_net(none)], with the same grid, slot position and centre-line rule as the
             benchmark deck (the network is built from the deck's own segment list);
    ratio  = dL_FastHenry / dL_net.
Reading fixed here: every ratio within 0.90-1.10 -> supported (topology explains the production error to within 10 %);
otherwise not supported for the cases outside. The unslotted L_FastHenry / L_net is reported (side fringing, port and
wall representation). P2 (one plate slotted) has no single-sheet network and is not assessed.

    python scripts/assess_plane_hole_network.py   # results/gan/plane-hole-network-assessment.json
"""
import hashlib
import json
import math
from pathlib import Path
import re
import sys

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import plane_hole_benchmark as b  # noqa: E402
from fasthenry_known_answer import skin_depth  # noqa: E402

REPORT = ROOT / "results/gan/plane-hole-benchmark.json"
OUTPUT = ROOT / "results/gan/plane-hole-network-assessment.json"


def network_squares(deck_text, plate="b"):
    """Resistance in squares of one plate's segment network between its x = 0 and x = L node columns."""
    pos = {}
    for m in re.finditer(r"^(n[bt]_\d+_\d+) x=(\S+) y=(\S+)", deck_text, re.M):
        pos[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    edges = [(m.group(1), m.group(2)) for m in re.finditer(r"^E\d+ (n[bt]_\d+_\d+) (n[bt]_\d+_\d+) w=", deck_text, re.M)
             if m.group(1)[1] == plate and m.group(2)[1] == plate]
    names = sorted({n for e in edges for n in e})
    xs = [pos[n][0] for n in names]
    x0, x1 = min(xs), max(xs)
    fixed = {n: (1.0 if abs(pos[n][0] - x0) < 1e-9 else 0.0) for n in names
             if abs(pos[n][0] - x0) < 1e-9 or abs(pos[n][0] - x1) < 1e-9}
    free = [n for n in names if n not in fixed]
    idx = {n: k for k, n in enumerate(free)}
    rows, cols, vals = [], [], []
    rhs = np.zeros(len(free))
    diag = np.zeros(len(free))
    for a, c in edges:
        for p, q in ((a, c), (c, a)):
            if p in idx:
                diag[idx[p]] += 1
                if q in idx:
                    rows.append(idx[p])
                    cols.append(idx[q])
                    vals.append(-1.0)
                else:
                    rhs[idx[p]] += fixed[q]
    rows += list(range(len(free)))
    cols += list(range(len(free)))
    vals += list(diag)
    v = spsolve(coo_matrix((vals, (rows, cols)), shape=(len(free),) * 2).tocsr(), rhs)
    volt = {n: fixed.get(n, v[idx[n]] if n in idx else None) for n in names}
    current = sum((volt[a] - volt[c]) if a in fixed and fixed[a] == 1.0 else (volt[c] - volt[a]) if c in fixed and fixed[c] == 1.0 else 0
                  for a, c in edges)
    return 1.0 / current


def main():
    rep = json.loads(REPORT.read_text(encoding="utf-8"))
    w = 2 * math.pi * b.FREQ
    per_sq = b.MU0 * (b.H + skin_depth(b.FREQ) * 1e3) * 1e-3
    out = {"schema": "plane-hole-network-assessment/1", "declared": "2026-10-03, before it was run (docstring)",
           "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "benchmark_report_sha256": hashlib.sha256(REPORT.read_bytes()).hexdigest(), "cases": {}}
    base = {}
    for mesh in ("m1", "m2"):
        text, _ = b.deck(None, None, mesh, "aligned", b.H)
        base[mesh] = network_squares(text)
        r = rep["runs"][b.run_id("none", mesh, "aligned", b.H)]
        out["cases"][f"none {mesh}"] = {"N_net": base[mesh], "N_ideal": b.LEN / b.WID,
                                        "L_fasthenry_over_L_net": r["Z_imag"] / w / (per_sq * base[mesh])}
    ratios = []
    for slot in ("perp", "par", "small"):
        for mesh in ("m1", "m2"):
            for al in ("aligned", "shifted"):
                rid = b.run_id(f"P1-{slot}", mesh, al, b.H)
                if rid not in rep["runs"] or "Z_imag" not in rep["runs"][rid]:
                    continue
                text, _ = b.deck("P1", slot, mesh, al, b.H)
                dn = network_squares(text) - base[mesh]
                dl_fh = (rep["runs"][rid]["Z_imag"] - rep["runs"][b.run_id("none", mesh, "aligned", b.H)]["Z_imag"]) / w
                ratio = dl_fh / (per_sq * dn)
                ratios.append(ratio)
                out["cases"][f"P1-{slot} {mesh} {al}"] = {"dN_net": dn, "dL_net_pH": per_sq * dn * 1e12,
                                                          "dL_fasthenry_pH": dl_fh * 1e12, "ratio": ratio,
                                                          "dN_sheet_reference": rep["reference"][slot]["dN"]}
                print(f"P1-{slot} {mesh} {al}: FastHenry {dl_fh * 1e12:.1f} pH, network {per_sq * dn * 1e12:.1f} pH, "
                      f"ratio {ratio:.3f}; sheet reference {per_sq * rep['reference'][slot]['dN'] * 1e12:.1f} pH")
    out["supported"] = bool(ratios) and all(0.90 <= r <= 1.10 for r in ratios)
    out["outside_0.9_1.1"] = [k for k, v in out["cases"].items() if "ratio" in v and not 0.90 <= v["ratio"] <= 1.10]
    OUTPUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("supported", "outside_0.9_1.1")}, indent=1),
          {k: v for k, v in out["cases"].items() if k.startswith("none")})


if __name__ == "__main__":
    main()
