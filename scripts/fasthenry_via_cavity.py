#!/usr/bin/env python3
"""Known-answer check for a via and its plane-pair return in FastHenry (G3, EPC90133).

Specification, fixed on 28 September 2026 before the first run (owner brief:
narrow scope, explicit geometry, ports, reference, assumptions, uncertainty,
tolerance and mesh criterion).

Purpose. The EPC90133 power loop returns on mid-layer 1 directly beneath the
top layer, and the gate return uses a Kelvin via (EPC2302 datasheet p. 6). Board
extraction will represent copper as explicit FastHenry segment grids and each via
as one vertical segment attached to ideal pads. This check uses exactly that
representation.

Geometry (mm). Board stack top layer to mid-layer 1 (B5253 Rev 2.0 stackup):
copper t = 0.0711 (2.8 mil) per plate, dielectric gap h = 0.127 (5 mil), so the
plate mid-planes are at z = 0 and z = h + t.
* Two square plates, node grid from -D/2 to D/2 at pitch s. Each grid edge is one
  segment of width s and thickness t: the representation the board reader emits.
* Return wall: one vertical segment (width s along the edge, thickness t) at every
  perimeter node, joining the two plates. It closes the cavity, so no field
  leaves it and no fringing correction is needed.
* Via: one vertical segment of square section w = 0.25 mm at the centre, from a
  separate node Nvb (z = 0) to a node Nvt (z = h + t). Nvt is shorted (.equiv) to all
  top-plate nodes with |x|, |y| <= w/2, an ideal pad.
* Port: between Nvb and a node Nqb shorted to all bottom-plate nodes with |x|, |y| <= w/2.
  It measures the whole loop: via, top-plate spreading, wall, bottom-plate spreading.
Frequency 100 MHz. Copper 5.8e7 S/m, skin depth delta = 6.61 um: much smaller than t,
and 5.2% of h. Cavity sizes D1 = 1.5 mm and D2 = 3.0 mm (D/w = 6 and 12).

References. For perfect conductors, the field between the plates is the 2D field
of a square coaxial line with the via as inner conductor. L = mu0 h / (2 pi) *
ln(1.0787 D_in / d_eq), where D_in = D - t is the wall's inner side and d_eq =
1.1804 w is the equivalent diameter of a square conductor under surface current
(equivalent radius 0.5902 w). With finite conductivity, each plate adds delta/2 to
the gap (case D of scripts/fasthenry_known_answer.py). The via and wall surfaces add
under 0.2 pH, which is neglected.

E1 (plane spreading and return; the declared known answer):
    L(D2) - L(D1) = mu0 (h + delta) / (2 pi) * ln(D2_in / D1_in).
    The via, its junctions, the pads and the square-coax constant cancel. The reference uncertainty
    is about 1%: higher-order terms of the square boundary for small d_eq/D, and
    the delta/2 surface-impedance approximation. Tolerance 3%.
E2 (explicit vertical conductor and junctions; a bracket, not a known answer):
    FastHenry places the via segment between plate mid-planes, so t of its length
    lies inside plate copper. The physical answer lies between
    L_low  = mu0 (h + delta)     / (2 pi) * ln(1.0787 D_in / d_eq)  (only the gap is inductive), and
    L_high = mu0 (h + t + delta) / (2 pi) * ln(1.0787 D_in / d_eq)  (the whole segment is).
    Check: the finest-mesh L(D1) and L(D2) lie inside [L_low, L_high]. The position
    f = (L - L_low) / (L_high - L_low) is reported. The bracket width is the per-via
    representation uncertainty that board extractions must carry, unless a later check narrows it.

Mesh criterion. Three meshes (s, filaments through t): (w/2, 3), (w/4, 5), (w/6, 7),
with thickness ratio rh = 2 (filaments thinner at the surfaces). The via uses
nwinc = nhinc = 3, 5, 7 with rw = rh = 2. E1 and E2 use the finest mesh, which must
agree with the middle mesh within 1% for each L and for E1's difference.

Scope. Passing qualifies: (a) current spreading and return in a closed plane
pair at this stack, 100 MHz, for the segment-grid representation; (b) the size of
the uncertainty from the mid-plane via-junction representation. It does NOT qualify
antipads or plane holes, via arrays and their coupling, Kelvin vias, vias through
several layers, open plane edges, plated barrels thinner than a few skin depths,
or frequencies where delta is not much smaller than t (below about 10 MHz).

Fourth mesh (revision declared 1 October 2026, before its run; the owner deferred it on 29 September and asked
on 1 October to advance tool qualification). The three-mesh result stays recorded as failed in
results/gan/fasthenry-via-cavity.json. With --fourth-mesh the meshes are those three plus (w/8, 9), the evaluation
is unchanged except that the finest mesh is (w/8, 9) and it is compared with (w/6, 7) under the same 1 % criterion,
E1 and E2 use (w/8, 9), and the report goes to results/gan/fasthenry-via-cavity-mesh4.json. The earlier meshes are
reused from the original run directory. Expected: about 340k filaments for D = 3 mm, run one case at a time
(-p diag). A pass would converge this single-via benchmark only; the scope above is unchanged, and it would
not qualify board via arrays or plane holes.
Launch 1 of the fourth mesh ran only the three old meshes (--meshes still defaulted to 3) and wrote no evaluation;
its log and report are kept under runs/ as via-mesh4-run1-failed.*. Fixed: --meshes defaults to all meshes.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from fasthenry_known_answer import FH_BIN, MU0, SIGMA_CU_PER_MM, parse_zc, run_fasthenry, skin_depth

T = 0.0711  # mm, 2.8 mil copper (B5253 stackup)
H = 0.127  # mm, 5 mil dielectric, top layer to mid-layer 1
W = 0.25  # mm, via section
FREQ = 1e8
SIZES = (1.5, 3.0)
MESHES = ((2, 3), (4, 5), (6, 7))  # (w / s, filaments through t and across the via)
MESH4 = (8, 9)  # fourth mesh, --fourth-mesh only
TOL_E1 = 0.03
MESH_TOL = 0.01


def deck(D, div, n):
    s = W / div
    k = round(D / 2 / s)
    if abs(k * s - D / 2) > 1e-9 or abs(round(W / 2 / s) * s - W / 2) > 1e-9:
        raise ValueError("grid must place nodes on the cavity edge and the via pad edge")
    zt = H + T
    lines = [f"* Via in a closed plane-pair cavity, D = {D} mm, pitch {s:.6g} mm; "
             "generated by scripts/fasthenry_via_cavity.py", ".units mm", f".default sigma={SIGMA_CU_PER_MM:g}"]
    name = lambda p, i, j: f"N{p}_{i + k}_{j + k}"
    for p, z in (("b", 0.0), ("t", zt)):
        for i in range(-k, k + 1):
            for j in range(-k, k + 1):
                lines.append(f"{name(p, i, j)} x={i * s:.9g} y={j * s:.9g} z={z:.9g}")
    seg = 0
    for p in ("b", "t"):
        for i in range(-k, k + 1):
            for j in range(-k, k + 1):
                if i < k:
                    seg += 1
                    lines.append(f"E{seg} {name(p, i, j)} {name(p, i + 1, j)} w={s:.9g} h={T} nwinc=1 nhinc={n} rh=2")
                if j < k:
                    seg += 1
                    lines.append(f"E{seg} {name(p, i, j)} {name(p, i, j + 1)} w={s:.9g} h={T} nwinc=1 nhinc={n} rh=2")
    for i in range(-k, k + 1):
        for j in range(-k, k + 1):
            if max(abs(i), abs(j)) == k:
                along_x = abs(j) == k  # wall faces +-y: width along x
                seg += 1
                lines.append(f"E{seg} {name('b', i, j)} {name('t', i, j)} w={s:.9g} h={T} "
                             f"wx={1 if along_x else 0} wy={0 if along_x else 1} wz=0 nwinc=1 nhinc=1")
    lines += ["Nvb x=0 y=0 z=0", f"Nvt x=0 y=0 z={zt:.9g}",
              f"Evia Nvb Nvt w={W} h={W} wx=1 wy=0 wz=0 nwinc={n} nhinc={n} rw=2 rh=2"]
    r = round(W / 2 / s)
    pad = lambda p: [name(p, i, j) for i in range(-r, r + 1) for j in range(-r, r + 1)]
    lines.append(".equiv Nvt " + " ".join(pad("t")))
    lines.append(".equiv Nqb " + " ".join(pad("b")))
    lines += [".external Nvb Nqb", f".freq fmin={FREQ:g} fmax={FREQ:g} ndec=1", ".end", ""]
    return "\n".join(lines)


def references(delta):
    d_eq = 1.1804 * W
    out = {}
    for D in SIZES:
        lnf = math.log(1.0787 * (D - T) / d_eq)
        out[D] = {"low_H": MU0 / (2 * math.pi) * (H + delta) * 1e-3 * lnf,
                  "high_H": MU0 / (2 * math.pi) * (H + T + delta) * 1e-3 * lnf}
    out["E1_H"] = MU0 / (2 * math.pi) * (H + delta) * 1e-3 * math.log((SIZES[1] - T) / (SIZES[0] - T))
    return out


def running_dirs():
    """Working directories (as WSL paths) of FastHenry processes now running."""
    cmd = "for p in $(pgrep -f bin/fasthenry); do readlink /proc/$p/cwd; done"
    out = subprocess.run(["wsl", "-e", "bash", "-c", cmd], capture_output=True, text=True).stdout
    return {line.strip() for line in out.splitlines() if line.strip()}


def run_case(inp_text, workdir, precond):
    """Run FastHenry without a time limit (fine meshes take longer than run_fasthenry's 30 min)."""
    from fasthenry_known_answer import wsl_path
    workdir.mkdir(parents=True, exist_ok=False)
    (workdir / "case.inp").write_text(inp_text, encoding="ascii")
    opt = f" -p {precond}" if precond else ""
    cmd = ["wsl", "-e", "bash", "-lc", f"cd '{wsl_path(workdir)}' && '{wsl_path(FH_BIN)}' case.inp{opt}"]
    p = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, check=False)
    (workdir / "stdout.log").write_text(p.stdout or "", encoding="utf-8")
    (workdir / "stderr.log").write_text(p.stderr or "", encoding="utf-8")
    zc = workdir / "Zc.mat"
    if p.returncode != 0 or not zc.is_file():
        raise RuntimeError(f"FastHenry failed in {workdir} (status {p.returncode}): {(p.stderr or p.stdout)[-500:]}")
    return parse_zc(zc.read_text(encoding="ascii", errors="replace"))


def complete(workdir):
    zc = workdir / "Zc.mat"
    return zc.is_file() and "Impedance matrix" in zc.read_text(encoding="ascii", errors="replace")


def case_impedance(run_root, D, div, n, precond):
    """Run one case, or reuse it; returns (impedances, preconditioner used). Orchestration only.

    FastHenry creates Zc.mat when it starts, so a case counts as finished only when Zc.mat
    holds an impedance matrix. A finished default-preconditioner case is reused. Otherwise the
    case's directory for the requested preconditioner is waited on while a FastHenry process
    works in it; a stale one is renamed aside and rerun.
    """
    from fasthenry_known_answer import wsl_path
    default_dir = run_root / f"D{D}_s{div}"
    if complete(default_dir):
        return parse_zc((default_dir / "Zc.mat").read_text(encoding="ascii", errors="replace")), "default (cube)"
    workdir = default_dir if not precond else run_root / f"D{D}_s{div}_p{precond}"
    if workdir.exists() and not complete(workdir):
        if wsl_path(workdir) in running_dirs():
            while not complete(workdir):
                if wsl_path(workdir) not in running_dirs():
                    time.sleep(10)
                    if not complete(workdir):
                        raise RuntimeError(f"FastHenry in {workdir} stopped without a result")
                time.sleep(30)
        else:
            k = 1
            while (stale := workdir.with_name(f"{workdir.name}_stale{k}")).exists():
                k += 1
            workdir.rename(stale)
    if not workdir.exists():
        return run_case(deck(D, div, n), workdir, precond), precond or "default (cube)"
    return parse_zc((workdir / "Zc.mat").read_text(encoding="ascii", errors="replace")), precond or "default (cube)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/fasthenry-via-cavity.json")
    ap.add_argument("--meshes", type=int, default=None, help="run only the first N meshes (for timing)")
    ap.add_argument("--jobs", type=int, default=1, help="cases run in parallel (FastHenry is single-threaded)")
    ap.add_argument("--run-dir", type=Path, default=None, help="reuse finished or running cases in this directory")
    ap.add_argument("--precond", default=None, help="FastHenry -p option for new runs, e.g. diag (solver path only)")
    ap.add_argument("--fourth-mesh", action="store_true", help="add the declared (w/8, 9) mesh (see the docstring)")
    args = ap.parse_args()
    meshes = MESHES + ((MESH4,) if args.fourth_mesh else ())
    if args.meshes is None:
        args.meshes = len(meshes)
    if args.fourth_mesh and args.output == ap.get_default("output"):
        args.output = ROOT / "results/gan/fasthenry-via-cavity-mesh4.json"
    delta = skin_depth(FREQ) * 1e3  # mm
    run_root = args.run_dir.resolve() if args.run_dir else ROOT / "runs" / ("fasthenry-via-" + uuid.uuid4().hex)
    cases = [(div, n, D) for div, n in meshes[:args.meshes] for D in SIZES]
    values = {}

    def one(case):
        div, n, D = case
        z, used = case_impedance(run_root, D, div, n, args.precond)
        values[f"{div},{D}"] = {"L_H": z[FREQ].imag / (2 * math.pi * FREQ), "R_ohm": z[FREQ].real, "preconditioner": used}
        print(f"mesh w/{div}, n={n}, D={D}: L = {values[f'{div},{D}']['L_H'] * 1e12:.3f} pH", flush=True)

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for f in [pool.submit(one, c) for c in cases]:
            f.result()
    ref = references(delta)
    report = {"schema": "fasthenry-via-cavity/1",
              "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "fasthenry_binary_sha256": hashlib.sha256(FH_BIN.read_bytes()).hexdigest() if FH_BIN.is_file() else None,
              "geometry_mm": {"t": T, "h": H, "via_w": W, "sizes_D": SIZES}, "frequency_Hz": FREQ,
              "skin_depth_mm": delta, "meshes": meshes[:args.meshes], "values": values,
              "solver_note": ("-p diag was adopted after it reproduced the finished fine D = 1.5 mm case exactly "
                              "(Z = 0.00107254 + 0.0327315j ohm, 187 s against 759 s for the default); "
                              "each case records its preconditioner"),
              "references": {str(k): v for k, v in ref.items()}, "evidence_directory": str(run_root.relative_to(ROOT))}
    if args.meshes >= len(meshes):
        fine, mid = meshes[-1][0], meshes[-2][0]
        L = {D: values[f"{fine},{D}"]["L_H"] for D in SIZES}
        Lm = {D: values[f"{mid},{D}"]["L_H"] for D in SIZES}
        dl, dlm = L[SIZES[1]] - L[SIZES[0]], Lm[SIZES[1]] - Lm[SIZES[0]]
        mesh = {"per_L": {str(D): abs(L[D] / Lm[D] - 1) for D in SIZES}, "difference": abs(dl / dlm - 1)}
        mesh["outcome"] = "pass" if max(list(mesh["per_L"].values()) + [mesh["difference"]]) <= MESH_TOL else "fail"
        e1_err = dl / ref["E1_H"] - 1
        e2 = {str(D): {"L_H": L[D], **ref[D], "position_f": (L[D] - ref[D]["low_H"]) / (ref[D]["high_H"] - ref[D]["low_H"]),
                       "inside": ref[D]["low_H"] <= L[D] <= ref[D]["high_H"]} for D in SIZES}
        report["mesh_check"] = mesh
        report["E1"] = {"fasthenry_H": dl, "reference_H": ref["E1_H"], "relative_error": e1_err, "tolerance": TOL_E1,
                        "outcome": "pass" if abs(e1_err) <= TOL_E1 else "fail"}
        report["E2"] = {"sizes": e2, "outcome": "pass" if all(v["inside"] for v in e2.values()) else "fail"}
        print(json.dumps({k: report[k] for k in ("mesh_check", "E1", "E2")}, indent=1))
    args.output.write_text(json.dumps(report, indent=1) + "\n")


if __name__ == "__main__":
    main()
