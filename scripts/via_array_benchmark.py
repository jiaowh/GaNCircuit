#!/usr/bin/env python3
"""Via arrays in a closed plane-pair cavity: FastHenry under the production via rule against a 2D reference (V1-V3).

Declared 2 October 2026, before its first run (plan section 10 item 9; docs/build.md "Via-array, plane-hole and
FasterCap qualification", draft design). The single-via cavity (scripts/fasthenry_via_cavity.py) passes its mesh
criterion but says nothing about arrays: board vias come in rows of six at 0.6 mm under each transistor pin and one
35-via cluster under Q2's source, and a single-via value must not be divided by the via count. This benchmark
measures how FastHenry with the production via rule represents arrays, through quantities in which the via's length
inside the plate copper (the single-via E2 bracket) cancels. It reports errors of these benchmark geometries; it does
not give board error bars.

Geometry (mm), as the single-via cavity: plates of thickness T = 0.0711 at mid-planes z = 0 (bottom) and h + T (top),
gap h = 0.127, square cavity of half-side a closed by a wall of vertical segments at every perimeter node (width s,
thickness T). Vias: square section, side w = 0.847 x 0.198 (the extractor's rule for the board's 0.198 mm drills),
one vertical segment each between the plate mid-planes (nwinc = nhinc = 3, rw = rh = 2). Arrangements, centred:
    single     one via;
    row6-0.6   six vias at x = 0, y = -1.5 ... 1.5 (pitch 0.6, as under each pin);
    row6-1.2   six vias at x = 0, pitch 1.2;
    grid3-0.6  3 x 3 at pitch 0.6.
Clearances c = 1.0 and 2.0 mm from the outermost via centres to the wall: a = k s with k = round((half-span + c) / s),
so a depends slightly on the mesh; each reference uses the same a. The 35-via cluster is deferred to a later case.
Representations:
    production  plates at the board pitches m1 (s = 0.425, plate nhinc 3) and m2 (0.2125, 5), grid lines through x = 0
                and y = 0 (the production grid runs through the via rows); each via's top end tied to the nearest top
                node, its bottom end is the port's + node and the nearest bottom node the port's - node;
    resolved    s = 0.085 (about w/2), plate nhinc 3; top end tied to every top node within the via footprint grown to
                s/2 (Chebyshev), port - node tied to the same bottom nodes. Single mesh: a consistency check of
                FastHenry against the reference, not a converged value (the single-via cavity at w/2 was 5 % high in
                absolute L but within 0.6 % in its cavity difference).
Each via is its own port; FastHenry gives the full N x N impedance matrix at 100 MHz (-p diag, admittance columns,
inverted); L = Im(Z) / omega, symmetrised.

Reference. Between perfectly conducting plates the field of vertical currents is two-dimensional, so
L_ref = mu0 eps0 (h + delta) C2D^-1, with C2D the 2D Maxwell matrix of the via cross-sections inside the wall's inner
face (a square of side 2a - T, the wall conductor as reference), every conductor equipotential. C2D from FasterCap 2D
(qualified on its 2D coax to 0.01 %), at -a0.001 and -a0.0005, every matrix through the physical-validity gate.
The reference cannot fix the via length inside the copper, so comparisons use:
    mutual ratios       r_j = M_1j / M_12 for rows (via 1 at one end), and M_centre,corner / M_centre,edge for the grid;
                        the factor h + delta cancels;
    cavity differences  dX = X(c = 2) - X(c = 1) for X = the parallel-array inductance
                        L_par = 1 / (1^T L^-1 1) and the self inductance of via 1 (the E1 construction);
    absolute L_par      reported against the reference at h + delta and h + T + delta (the bracket), not judged.
Checks, fixed here:
V0  reference (revisions 1-4): every C2D valid; -a0.001 to -a0.0005 changes every entry of L_ref by <= 0.2 %; see revision 5 below.
V1  resolved, mutual ratios: every r_j of row6-0.6 within 3 % of the reference (a single via has no ratio).
V2  resolved, cavity differences: dL_par and dL_self within 3 % of the reference, for single and row6-0.6.
V3  resolved, absolute: L_par inside the reference bracket for single and row6-0.6.
Reported, not judged: the same ratios, differences and absolute values for the production representation at m1 and
m2, as relative errors against the reference; the reference's L_par of each array against L_single / N for one via in
the same cavity (to show why a single-via value must not be divided by the count).
Run order: references, then production (cheap), then resolved. One FastHenry job at a time, 3 h limit per job, report
checkpointed after each job; --resume continues a report written by the same evaluator.

Run 1 (2 October 2026) failed in post-processing, kept as results/gan/via-array-benchmark-run1-failed.json: with every
port requested FastHenry writes the full impedance matrix, and the reused extractor runner accepts only admittance
columns, so every FastHenry case was solved but not read (12 cases). Fixed: this script runs FastHenry itself (-p diag,
all ports) and reads the impedance matrix by port name. A case whose run-1 directory holds a byte-identical case.inp and
a complete Zc.mat is read from there instead of being solved again (recorded per case as "reused"). Nothing else changed.

Run 2 (3 October 2026) is kept as results/gan/via-array-benchmark-run2-failed.json: with three jobs on the host, WSL's
free memory fell to tens of MB, FasterCap stopped some reference runs with "Cannot go out-of-core" and still exited 0,
and the shared runner read the last, unconverged matrix as the result (fixed in scripts/fastercap_known_answer.py,
run_problem). Revision 3: references come only from the fixed runner; a reference call rejected for lack of memory is
retried up to three times, 120 s apart, each attempt in its own directory and recorded; FastHenry cases are read from
the run-1 or run-2 directory when their case.inp is byte-identical. Nothing else changed.

Run 3 (revision 3, 3 October 2026) is kept as results/gan/via-array-benchmark-run3-failed.json: some reference calls
still failed for lack of memory. They exited with status 97 and the memory message sat in FasterCap's own log, not in
the error text the retry tested, so no retry ran. FasterCap goes out of core when its links exceed a fifth of
wxGetFreeMemory(), which counts only unused pages (about 80 MB on this host while about 5 GB of page cache was
reclaimable). Revision 4: reference calls pass -f0 (Solver/Autorefine.cpp: the out-of-core test becomes links x 0 <
free memory, so they stay in core; these 2D references need tens of MB), and a failed attempt is retried when its own
FasterCap log reports the memory termination. Nothing else changed; FastHenry outputs are read from runs 1-3 for
byte-identical decks.

Run 4 (revision 4) completed and is kept as results/gan/via-array-benchmark-run4-failed.json: V0 failed because
FasterCap's automatic 2D refinement sometimes stalls (single-via references 1.3-2.1 % above the closed form at one or
both settings, while converged ones agree with it to 0.02 %), so two -a settings cannot certify a reference; V1 and V2
failed and V3 passed against those references. Revision 5 (3 October 2026, declared before its run) replaces the
reference solver, as the draft design allowed: circuit_tools.bem2d, a 2D boundary-element solver with explicit
corner-graded panels (tests/test_bem2d.py: coax to 4e-7, the square via to 0.004 % of the closed form). V0 becomes:
    V0  every reference matrix physical; 16 to 32 panels per via side (wall panels scaled with length) changes every
        entry of L_ref by <= 0.05 %; and each single-via reference within 0.1 % of the closed form
        mu0/(2 pi) ln(1.0787 (2a - T) / (1.1804 w)).
V1-V3, the representations and the FastHenry cases are unchanged (FastHenry read from runs 1-3). Run 4's FasterCap
references at -a0.0005 are reported beside the new ones as a cross-check.

Audit at 9ca735d (3 October 2026), no rerun: FastHenry runs through circuit_tools.wslrun (stops the Linux solver
itself on timeout; before, a 3 h timeout was not even caught); the reference implementation src/circuit_tools/bem2d.py
(and wslrun.py) is now bound in DEPENDENCIES and --resume refuses a report whose dependencies changed; V1 now fails if
any expected ratio is missing. The stored revision-5 report predates these changes (its V1 failure and V0/V2/V3
verdicts stand; it binds bem2d.py only indirectly, through the git commit that declared revision 5).

    python scripts/via_array_benchmark.py            # results/gan/via-array-benchmark.json
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import uuid

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from epc90133_extract import parse_matrix_file  # noqa: E402
from fastercap_board3d_check import matrix_validity  # noqa: E402
from fastercap_known_answer import FC_BIN, run_fastercap, seg  # noqa: E402
from circuit_tools.bem2d import maxwell_matrix, panels, square  # noqa: E402
from circuit_tools.wslrun import run_solver  # noqa: E402
from fasthenry_known_answer import FH_BIN, SIGMA_CU_PER_MM, skin_depth  # noqa: E402
import time  # noqa: E402

def solve(text, workdir, reuse_dirs=()):
    """FastHenry with every port: (port names, complex Z, seconds, reused). A saved case is read only when its case.inp
    is byte-identical to `text` and its matrix file is complete."""
    for reuse_dir in reuse_dirs:
        if not ((reuse_dir / "case.inp").is_file() and (reuse_dir / "case.inp").read_text(encoding="ascii") == text):
            continue
        for f in (reuse_dir / "Zc_j0.mat", reuse_dir / "Zc.mat"):
            if f.is_file() and "matrix for frequency" in f.read_text(errors="replace"):
                rows, _, kind, mat = parse_matrix_file(f.read_text(errors="replace"))
                if kind == "Impedance":
                    return rows, mat, None, str(reuse_dir.relative_to(ROOT))
    workdir.mkdir(parents=True, exist_ok=False)
    (workdir / "case.inp").write_text(text, encoding="ascii")
    t0 = time.time()
    try:  # audit at 9ca735d: on timeout the Linux FastHenry process itself is stopped (circuit_tools.wslrun)
        p = run_solver(FH_BIN, "case.inp -p diag", workdir, 3 * 3600, "fasthenry")
    except TimeoutError as exc:
        raise RuntimeError(str(exc))
    (workdir / "stdout.log").write_text(p.stdout or "", encoding="utf-8")
    f = workdir / "Zc.mat"
    if p.returncode != 0 or not f.is_file() or "matrix for frequency" not in f.read_text(errors="replace"):
        raise RuntimeError(f"FastHenry failed (status {p.returncode}): {(p.stderr or p.stdout)[-400:]}")
    rows, _, kind, mat = parse_matrix_file(f.read_text(errors="replace"))
    if kind != "Impedance":
        raise RuntimeError(f"expected an impedance matrix, got {kind}")
    return rows, mat, time.time() - t0, None

OUTPUT = ROOT / "results/gan/via-array-benchmark.json"
T, H = 0.0711, 0.127
W = 0.847 * 0.198
FREQ = 1e8
MU0, EPS0 = 4e-7 * math.pi, 8.8541878128e-12
CLEAR = (1.0, 2.0)
ARRANGEMENTS = {
    "single": [(0.0, 0.0)],
    "row6-0.6": [(0.0, -1.5 + 0.6 * k) for k in range(6)],
    "row6-1.2": [(0.0, -3.0 + 1.2 * k) for k in range(6)],
    "grid3-0.6": [(x, y) for y in (-0.6, 0.0, 0.6) for x in (-0.6, 0.0, 0.6)],
}
REPS = {"m1": (0.425, 3, "production"), "m2": (0.2125, 5, "production"), "r1": (0.085, 3, "resolved")}
RESOLVED_CASES = ("single", "row6-0.6")
AUTO_2D = ("bem16", "bem32")  # revision 5: boundary-element refinements (panels per via side)
DEPENDENCIES = ("src/circuit_tools/bem2d.py", "src/circuit_tools/wslrun.py",
                "scripts/epc90133_extract.py", "scripts/fastercap_board3d_check.py", "scripts/fastercap_known_answer.py",
                "scripts/fasthenry_known_answer.py")


def half_side(arr, c, s):
    span = max(max(abs(x), abs(y)) for x, y in ARRANGEMENTS[arr])
    return round((span + c) / s) * s


def deck(arr, c, rep):
    s, n, kind = REPS[rep]
    a = half_side(arr, c, s)
    k = round(a / s)
    zt = H + T
    name = lambda p, i, j: f"n{p}_{i + k}_{j + k}"  # noqa: E731
    lines = [f"* via array {arr}, clearance {c}, {rep}; generated by scripts/via_array_benchmark.py", ".units mm",
             f".default sigma={SIGMA_CU_PER_MM:g}"]
    for p, z in (("b", 0.0), ("t", zt)):
        for i in range(-k, k + 1):
            for j in range(-k, k + 1):
                lines.append(f"{name(p, i, j)} x={i * s:.9g} y={j * s:.9g} z={z:.9g}")
    e = 0
    for p in ("b", "t"):
        for i in range(-k, k + 1):
            for j in range(-k, k + 1):
                if i < k:
                    e += 1
                    lines.append(f"E{e} {name(p, i, j)} {name(p, i + 1, j)} w={s:.9g} h={T} nwinc=1 nhinc={n} rh=2")
                if j < k:
                    e += 1
                    lines.append(f"E{e} {name(p, i, j)} {name(p, i, j + 1)} w={s:.9g} h={T} nwinc=1 nhinc={n} rh=2")
    for i in range(-k, k + 1):
        for j in range(-k, k + 1):
            if max(abs(i), abs(j)) == k:
                along_x = abs(j) == k
                e += 1
                lines.append(f"E{e} {name('b', i, j)} {name('t', i, j)} w={s:.9g} h={T} "
                             f"wx={1 if along_x else 0} wy={0 if along_x else 1} wz=0 nwinc=1 nhinc=1")
    ports = []
    used = {}
    for v, (x, y) in enumerate(ARRANGEMENTS[arr]):
        if kind == "production":
            pads = [(round(x / s), round(y / s))]
        else:
            g = max(W / 2, s / 2) + 1e-9
            pads = [(i, j) for i in range(-k, k + 1) for j in range(-k, k + 1) if abs(i * s - x) <= g and abs(j * s - y) <= g]
        for ij in pads:
            if ij in used:
                raise RuntimeError(f"vias {used[ij]} and {v} share an attachment node")
            used[ij] = v
        lines += [f"nv{v}b x={x:.9g} y={y:.9g} z=0", f"nv{v}t x={x:.9g} y={y:.9g} z={zt:.9g}",
                  f"Ev{v} nv{v}b nv{v}t w={W:.9g} h={W:.9g} wx=1 wy=0 wz=0 nwinc=3 nhinc=3 rw=2 rh=2",
                  ".equiv " + " ".join([f"nv{v}t"] + [name("t", i, j) for i, j in pads])]
        if len(pads) > 1:
            lines.append(".equiv " + " ".join(name("b", i, j) for i, j in pads))
        i0, j0 = pads[0]
        lines.append(f".external nv{v}b {name('b', i0, j0)} v{v}")
        ports.append((f"v{v}", None, None))
    lines += [f".freq fmin={FREQ:g} fmax={FREQ:g} ndec=1", ".end", ""]
    return "\n".join(lines), ports, a


def reference(arr, a, auto, workdir):
    """L_ref per unit (h + delta) [H/m]: mu0 eps0 C2D^-1 for the via squares inside the wall's inner face."""
    m = 1e-3
    files = {"va.lst": f"2D via array {arr}, half-side {a}\n"}
    for v, (x, y) in enumerate(ARRANGEMENTS[arr]):
        h = W / 2
        pts = [(x - h, y - h), (x + h, y - h), (x + h, y + h), (x - h, y + h), (x - h, y - h)]
        files[f"v{v}.txt"] = f"* via {v}\n" + "".join(seg(f"v{v}", p[0] * m, p[1] * m, q[0] * m, q[1] * m) for p, q in zip(pts, pts[1:]))
        files["va.lst"] += f"C v{v}.txt 1.0 0 0\n"
    b = a - T / 2
    pts = [(-b, -b), (b, -b), (b, b), (-b, b), (-b, -b)]
    files["wall.txt"] = "* wall inner face\n" + "".join(seg("wall", p[0] * m, p[1] * m, q[0] * m, q[1] * m) for p, q in zip(pts, pts[1:]))
    files["va.lst"] += "C wall.txt 1.0 0 0\n"
    mat, names, _ = run_fastercap(files, workdir, auto, 3600, extra="-f0")
    return mat


def bem_reference(arr, a, n):
    """2D Maxwell matrix (F/m) of the via squares with the wall's inner face as reference (boundary elements)."""
    m = 1e-3
    vias = [panels(square(x * m, y * m, W * m), n) for x, y in ARRANGEMENTS[arr]]
    wall = panels(square(0.0, 0.0, (2 * a - T) * m), lambda s: max(n, round(n * s / (W * m) / 4)))
    M = maxwell_matrix(vias + [wall])
    k = len(vias)
    return M[:k, :k]


def v1_check(res, tol=0.03):
    """V1 over the resolved row cases; every expected ratio must be present (audit at 9ca735d: a missing cavity used to
    drop out of the list silently)."""
    expected = {arr: len(ARRANGEMENTS[arr]) - 2 for arr in RESOLVED_CASES if len(ARRANGEMENTS[arr]) == 6}
    sets = {f"{arr}|c={c:g}": res.get(f"{arr}|c={c:g}|r1", {}).get("ratio_errors") for arr in expected for c in CLEAR}
    complete = all(v is not None and len(v) == expected[k.split("|")[0]] for k, v in sets.items())
    errs = [e for v in sets.values() if v for e in v]
    return {"max_abs_error": max((abs(e) for e in errs), default=None), "complete": complete,
            "pass": complete and all(abs(e) <= tol for e in errs)}


def metrics(L):
    """Parallel-array inductance, self of via 0, and mutual ratios, from a symmetric N x N matrix (henry)."""
    L = np.asarray(L)
    n = len(L)
    out = {"L_par": float(1 / np.sum(np.linalg.inv(L))), "L_self0": float(L[0, 0])}
    if n == 6:
        out["ratios"] = [float(L[0, j] / L[0, 1]) for j in range(2, 6)]
    elif n == 9:  # centre is via 4; edge neighbour via 1, corner via 0
        out["ratios"] = [float(L[4, 0] / L[4, 1])]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    ev = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if args.resume and OUTPUT.is_file():
        rep = json.loads(OUTPUT.read_text(encoding="utf-8"))
        if rep["evaluator_sha256"] != ev:
            raise SystemExit("report was written by a different evaluator")
        now = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in DEPENDENCIES}
        if rep.get("dependencies_sha256") != now:
            raise SystemExit("a dependency changed since the report was written; start a new report")
    else:
        rep = {"schema": "via-array-benchmark/5", "declared": "2026-10-02, before the first run (docstring)",
               "evaluator_sha256": ev,
               "dependencies_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in DEPENDENCIES},
               "fasthenry_binary_sha256": hashlib.sha256(FH_BIN.read_bytes()).hexdigest(),
               "fastercap_binary_sha256": hashlib.sha256(FC_BIN.read_bytes()).hexdigest(),
               "run_directory": f"runs/via-array-{uuid.uuid4().hex[:12]}", "references": {}, "runs": {}, "errors": []}
    root = ROOT / rep["run_directory"]
    earlier = [ROOT / f"results/gan/via-array-benchmark-run{k}-failed.json" for k in (1, 2, 3)]  # run 4 solved nothing new
    PREV = [ROOT / json.loads(f.read_text(encoding="utf-8"))["run_directory"] for f in earlier if f.is_file()]
    rep["earlier_directories_reused"] = [str(d.relative_to(ROOT)) for d in PREV]
    delta = skin_depth(FREQ) * 1e3

    def save():
        tmp = OUTPUT.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(rep, indent=1) + "\n")
        os.replace(tmp, OUTPUT)

    plan = [(arr, c, r) for r in ("m1", "m2") for arr in ARRANGEMENTS for c in CLEAR] + \
           [(arr, c, "r1") for arr in RESOLVED_CASES for c in CLEAR]
    # references for every cavity size used
    wanted = []
    for arr, c, r in plan:
        a = half_side(arr, c, REPS[r][0])
        wanted += [(arr, a), ("single", a)]  # one via in the same cavity, for the division-by-count comparison
    for arr, a in wanted:
        key = f"{arr}|a={a:.6g}"
        if key in rep["references"]:
            continue
        row = {}
        for level in AUTO_2D:
            C = bem_reference(arr, a, int(level[3:])).tolist()
            val = matrix_validity(C)
            row[level] = {"C2D": C, "validity": val,
                          "L_per_heff_H_per_m": (MU0 * EPS0 * np.linalg.inv(np.array(C))).tolist() if not val else None}
        rep["references"][key] = row
        print("reference", key, {k: v.get("validity", v.get("error")) for k, v in row.items()}, flush=True)
        save()
    for arr, c, r in plan:
        rid = f"{arr}|c={c:g}|{r}"
        if rid in rep["runs"]:
            continue
        text, ports, a = deck(arr, c, r)
        sub_ = rid.replace("|", "_").replace("=", "")
        try:
            order, Z, secs, reused = solve(text, root / sub_, [d / sub_ for d in PREV])
            idx = [order.index(f"v{v}") for v in range(len(ports))]
            Z = Z[np.ix_(idx, idx)]
            L = (Z.imag + Z.imag.T) / 2 / (2 * math.pi * FREQ)
            rep["runs"][rid] = {"a_mm": a, "L_H": L.tolist(), "R_ohm": ((Z.real + Z.real.T) / 2).tolist(),
                                "seconds": secs, "reused_from": reused}
        except Exception as exc:  # recorded per run
            rep["runs"][rid] = {"a_mm": a, "error": f"{type(exc).__name__}: {exc}"}
            rep["errors"].append(f"{rid}: {exc}")
        print(rid, {k: v for k, v in rep["runs"][rid].items() if k not in ("L_H", "R_ohm")}, flush=True)
        save()

    # evaluation
    def ref_L(arr, a, gap):
        row = rep["references"].get(f"{arr}|a={a:.6g}", {}).get(AUTO_2D[-1], {})
        Lp = row.get("L_per_heff_H_per_m")
        return np.array(Lp) * gap * 1e-3 if Lp is not None else None

    res = {}
    v0_changes = []
    for key, row in rep["references"].items():
        x, y = row.get(AUTO_2D[0], {}).get("L_per_heff_H_per_m"), row.get(AUTO_2D[1], {}).get("L_per_heff_H_per_m")
        v0_changes.append(float(np.max(np.abs(np.array(y) / np.array(x) - 1))) if x and y else None)
    closed = {}
    for key, row in rep["references"].items():
        if key.startswith("single|") and row.get(AUTO_2D[-1], {}).get("L_per_heff_H_per_m"):
            a = float(key.split("=")[1])
            ref = MU0 / (2 * math.pi) * math.log(1.0787 * (2 * a - T) / (1.1804 * W))
            closed[key] = row[AUTO_2D[-1]]["L_per_heff_H_per_m"][0][0] / ref - 1
    valid = all(not row.get(lv, {}).get("validity", ["missing"]) for row in rep["references"].values() for lv in AUTO_2D)
    checks = {"V0": {"max_change": max((v for v in v0_changes if v is not None), default=None),
                     "single_vs_closed_form": closed, "all_valid": valid,
                     "pass": valid and all(v is not None and v <= 0.0005 for v in v0_changes)
                     and bool(closed) and all(abs(e) <= 0.001 for e in closed.values())}}
    run4 = ROOT / "results/gan/via-array-benchmark-run4-failed.json"
    if run4.is_file():
        old = json.loads(run4.read_text(encoding="utf-8"))["references"]
        xc = {}
        for key, row in rep["references"].items():
            a_ = old.get(key, {}).get("0.0005", {}).get("L_per_heff_H_per_m")
            b_ = row.get(AUTO_2D[-1], {}).get("L_per_heff_H_per_m")
            if a_ and b_:
                xc[key] = float(np.max(np.abs(np.array(a_) / np.array(b_) - 1)))
        rep["fastercap_run4_vs_bem_max_entry_difference"] = xc
    for arr, c, r in plan:
        run = rep["runs"].get(f"{arr}|c={c:g}|{r}", {})
        if "L_H" not in run:
            continue
        Lr = ref_L(arr, run["a_mm"], H + delta)
        Lr_hi = ref_L(arr, run["a_mm"], H + T + delta)
        if Lr is None:
            continue
        mf, mr, mh = metrics(run["L_H"]), metrics(Lr), metrics(Lr_hi)
        res[f"{arr}|c={c:g}|{r}"] = {"fasthenry": mf, "reference": mr, "reference_upper": mh,
                                     "ratio_errors": [a / b - 1 for a, b in zip(mf.get("ratios", []), mr.get("ratios", []))],
                                     "L_par_bracket_position": (mf["L_par"] - mr["L_par"]) / (mh["L_par"] - mr["L_par"])}
    for arr in ARRANGEMENTS:
        for r in REPS:
            a1, a2 = res.get(f"{arr}|c=1|{r}"), res.get(f"{arr}|c=2|{r}")
            if a1 and a2:
                res[f"{arr}|diff|{r}"] = {
                    q: {"fasthenry": a2["fasthenry"][q] - a1["fasthenry"][q], "reference": a2["reference"][q] - a1["reference"][q],
                        "relative_error": (a2["fasthenry"][q] - a1["fasthenry"][q]) / (a2["reference"][q] - a1["reference"][q]) - 1}
                    for q in ("L_par", "L_self0")}
    checks["V1"] = v1_check(res)
    v2 = [res.get(f"{arr}|diff|r1", {}).get(q, {}).get("relative_error") for arr in RESOLVED_CASES for q in ("L_par", "L_self0")]
    checks["V2"] = {"errors": v2, "pass": all(e is not None and abs(e) <= 0.03 for e in v2)}
    v3 = [res.get(f"{arr}|c={c:g}|r1", {}).get("L_par_bracket_position") for arr in RESOLVED_CASES for c in CLEAR]
    checks["V3"] = {"bracket_positions": v3, "pass": all(p is not None and 0 <= p <= 1 for p in v3)}
    div = {}
    for arr in ARRANGEMENTS:
        a = half_side(arr, 1.0, REPS["m2"][0])
        La, L1 = ref_L(arr, a, H + delta), ref_L("single", a, H + delta)
        if La is not None and L1 is not None:
            lp, l1 = metrics(La)["L_par"], float(L1[0, 0])
            div[arr] = {"half_side_mm": a, "reference_L_par_H": lp, "single_over_N_H": l1 / len(ARRANGEMENTS[arr]),
                        "ratio": lp / (l1 / len(ARRANGEMENTS[arr]))}
    rep["division_by_count"] = div
    rep["results"] = res
    rep["checks"] = checks
    rep["all_pass"] = all(v["pass"] for v in checks.values())
    rep["outcome"] = "complete"
    save()
    print(json.dumps(checks, indent=1, default=str))


if __name__ == "__main__":
    main()
