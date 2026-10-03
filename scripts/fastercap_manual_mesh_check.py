#!/usr/bin/env python3
"""FasterCap with user-controlled meshes: case H diagnosis (part D) and a partly filled plate capacitor (part K1).

Declared 2 October 2026, before the first run of either part (plan section 10 item 9; docs/build.md "Via-array,
plane-hole and FasterCap qualification"). Case H (scripts/fastercap_board3d_check.py) returned unphysical 3D matrices.
Its stored logs and FasterCap's source (Solver/SolveCapacitance.cpp, auto loop) show the automatic mode accepting
an iteration whose mesh had grown under 10 % (3,576 -> 4,132 panels). The two coarse matrices were identical, so the
change test passed at once. Whether the dielectric description is also at fault is not known. This script removes
the automatic refinement: every input face is split into a graded tensor mesh written by this script, and FasterCap
runs with -m1e9 (no refinement; on a probe cube the panel count stayed at its input value, runs/fastercap-probe-nomesh).

Part D: case H's geometry exactly (h = 0.1 mm, w = 2h, t = h/100, half-span S = 10h, end extension E = 10h,
lengths L1 = 20h and L2 = 40h, eps_r 4.3, symmetric strip pair, the same .lst structure and the slab reference point at
its centre with "-"), in two forms:
    diel  as case H;
    air   the strips alone (no slab; every strip face in air).
Meshes: graded lines on every face, size p at every geometric break (strip edges and ends, slab edges), growing by
ratio 1.2 up to 16p: M1 p = w/10, M2 p = w/20, M3 p = w/40. The 1 um strip side faces are one panel thick.
Per-unit-length value C' = 2 [C_pair(L2) - C_pair(L1)] / (L2 - L1), as in case H.
Checks:
    D0 no refinement: in every run FasterCap's panel count after refinement equals its input panel count;
    D1 validity: every matrix passes case H's physical-validity gate (matrix_validity, rel. tol 1e-3);
    D2 mesh: C' changes by <= 1 % from M2 to M3, for each form;
    D3 air accuracy: air C' at M3 within 1 % of Hammerstad-Jensen in air (case G(i) put FasterCap 2D within 0.13 % of it);
    D4 dielectric accuracy: diel C' at M3 within 2 % of case H's stored 2D value at -a0.001 (123.23 pF/m, slab truncated
       at S; valid matrix; case H's 2D refinement check H3 failed, so this reference carries that caveat, and
       Hammerstad-Jensen for an infinite slab, 123.04 pF/m, is reported beside it).
Readings fixed now: all of D0-D4 pass -> with resolved user meshes this dielectric description gives physical,
mesh-stable and accurate results, and case H's failure is attributed to the automatic refinement on that geometry;
air passes but diel fails D1 -> the fault persists with resolved meshes (next: lifted strips, the drafted D2);
air fails -> the user meshing is at fault and nothing follows about the dielectric.
Reported only: one -a0.01 run of diel L1 started from the M1 input, to show whether automatic refinement behaves when
it starts from a resolved mesh.

Part K1 (runs only if D0, D1 and D2 pass for both forms): a parallel-plate capacitor, square plates of side a,
thickness 35 um, gap d = 0.127 mm (the board's top layer to mid-layer 1 dielectric), a dielectric layer eps_r 4.3 of
thickness d/2 on the lower plate with the plate's footprint, air above it; and the same plates in air.
Reference: the uniform interior field gives C(a) = alpha a^2 + beta a + gamma + O((d/a)^3 alpha a^2), with
alpha = eps0 / (d1/eps_r + d2) (diel) or eps0/d (air) exactly; beta collects the edge fringing and the outer
surfaces, gamma the corners. Sizes a/d = 12, 18, 24 fix alpha, beta, gamma; a/d = 30 is held out.
Meshes: p = d/8 and d/16 at every break, ratio 1.2, up to 16p.
    K1a air: alpha within 0.5 % of eps0/d;
    K1b diel: alpha within 1 % of eps0/(d1/eps_r + d2);
    K1c expansion: the held-out C(30d) within 0.2 % of the fitted prediction, each form, finer mesh;
    K1d mesh: alpha changes by <= 0.5 % between the meshes, each form;
    every matrix passes the validity gate (a failure there fails K1).
Time limit 1 h per FasterCap call; a timeout fails the check that needs the value. A pass of part D qualifies nothing
for the board: it diagnoses case H. A pass of K1 supports user-meshed 3D planar dielectric layers touching a conductor,
at these sizes; not holes, vias, solder mask or the board.

Revision 2 (2 October 2026, declared after run 1 and before run 2). Run 1 used -m1e9 alone and failed: every L2 matrix,
air included, was unphysical, and the L1 values did not converge (air 62.0, 65.7, 54.4 fF). FasterCap sets its
interaction threshold to -d x -m (Solver/SolveCapacitance.cpp; Autorefine.cpp, RefineCriteria), so -m1e9 with the
default -d1 let panels interact through coarse super-panels. That is also why every automatic iteration 0 (-m 1e32) is
unphysical. On the probe cube (1 m, 96 panels) the capacitance was 69.0 pF at threshold 1e9, 72.66 pF at 0.01 and
72.67 pF with all links (reference 73.51 pF; the rest is the 4 x 4 face mesh). Run 1's report is kept as
results/gan/fastercap-manual-mesh-check-run1-failed.json. Changes, nothing else altered: every FasterCap call uses
-m1e9 -d1e-11 (threshold 0.01), and a check is added:
    D5 interaction threshold: at M2, both lengths and both forms, rerun with -d1e-12 (threshold 0.001); C' changes by
       <= 0.2 % for each form.
The part-D readings and the K1 gate add D5 to D0-D2.

Audit at 9ca735d (3 October 2026): run() now applies run_problem (memory termination; unconverged automatic stop), as
the shared runner does since 3 October. No case or criterion changed; stored reports are not re-evaluated (none of
their logs reports a memory termination).

    python scripts/fastercap_manual_mesh_check.py   # results/gan/fastercap-manual-mesh-check.json
"""
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import uuid

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEPENDENCIES = ("scripts/fastercap_known_answer.py", "scripts/fastercap_board3d_check.py",
                "results/gan/fastercap-board3d-check.json")
sys.path.insert(0, str(ROOT / "scripts"))
from fastercap_board3d_check import matrix_validity  # noqa: E402
from fastercap_known_answer import ER, FC_BIN, hammerstad_jensen, pair, parse_last_matrix, run_problem, wsl_path  # noqa: E402

EPS0 = 8.8541878128e-12
OUTPUT = ROOT / "results/gan/fastercap-manual-mesh-check.json"
TIMEOUT = 3600
RATIO, MAXF = 1.2, 16
# Part D: case H geometry
H = 0.1e-3
W, T, S, E = 2 * H, H / 100, 10 * H, 10 * H
L1, L2 = 20 * H, 40 * H
D_MESHES = {"M1": W / 10, "M2": W / 20, "M3": W / 40}
# Part K1
D_GAP, T_PLATE = 0.127e-3, 35e-6
K_SIZES, K_HOLDOUT = (12, 18, 24), 30
K_MESHES = {"K1": D_GAP / 8, "K2": D_GAP / 16}


def graded(breaks, p):
    """Lines through every break, spacing p at each break, growing by RATIO up to MAXF p towards each interval's middle
    (the left half is built and mirrored; a last left line closer to the middle than half its step is dropped)."""
    out = [breaks[0]]
    for u, v in zip(breaks, breaks[1:]):
        m = (u + v) / 2
        left, step, x = [], p, u
        while x + step < m:
            x += step
            left.append((x, step))
            step = min(step * RATIO, MAXF * p)
        if left and m - left[-1][0] < 0.5 * left[-1][1]:
            left.pop()
        xs = [x for x, _ in left]
        out += xs + ([m] if v - u > 1.5 * p else []) + [u + v - x for x in xs[::-1]] + [v]
    return out


def quads(name, axis, c, us, vs, skip=None):
    """Quadrilaterals on the plane axis = c over the tensor grid us x vs (the other two axes in x, y, z order)."""
    lines = []
    for u0, u1 in zip(us, us[1:]):
        for v0, v1 in zip(vs, vs[1:]):
            if skip and skip((u0 + u1) / 2, (v0 + v1) / 2):
                continue
            pts = []
            for a, b in ((u0, v0), (u1, v0), (u1, v1), (u0, v1)):
                p = [a, b]
                p.insert(axis, c)
                pts.append(p)
            lines.append(f"Q {name} " + "  ".join(" ".join(f"{q:.9g}" for q in p) for p in pts))
    return lines


def box_faces(name, xs, ys, zs):
    """The six faces of an axis-aligned box meshed on its own lines: {face key: lines}."""
    return {"x0": quads(name, 0, xs[0], ys, zs), "x1": quads(name, 0, xs[-1], ys, zs),
            "y0": quads(name, 1, ys[0], xs, zs), "y1": quads(name, 1, ys[-1], xs, zs),
            "z0": quads(name, 2, zs[0], xs, ys), "z1": quads(name, 2, zs[-1], xs, ys)}


def case_d(L, p, form):
    xs = graded([-S, -W / 2, W / 2, S], p)
    Y0, Y1 = -L / 2 - E, L / 2 + E
    ys = graded([Y0, -L / 2, L / 2, Y1], p)
    sx = [x for x in xs if -W / 2 - 1e-15 <= x <= W / 2 + 1e-15]
    sy = [y for y in ys if -L / 2 - 1e-15 <= y <= L / 2 + 1e-15]
    er = ER if form == "diel" else 1.0
    files = {"ms3d.lst": f"* case H geometry, user mesh p = {p:g} m, L = {L:g} m, {form}\n"}
    for tag, zb, zt in (("top", H, H + T), ("bot", -H - T, -H)):
        f = box_faces(tag, sx, sy, [zb, zt])
        on_slab = "z0" if tag == "top" else "z1"
        air = [ln for k, v in f.items() if k != on_slab for ln in v]
        files[f"{tag}_air.txt"] = f"* {tag} strip, air faces\n" + "\n".join(air) + "\n"
        files[f"{tag}_diel.txt"] = f"* {tag} strip, slab face\n" + "\n".join(f[on_slab]) + "\n"
        files["ms3d.lst"] += f"C {tag}_air.txt 1.0 0 0 0 +\nC {tag}_diel.txt {er} 0 0 0\n"
    if form == "diel":
        zs = graded([-H, H], p)
        under = lambda u, v: abs(u) < W / 2 and abs(v) < L / 2  # noqa: E731
        slab = quads("slab", 2, H, xs, ys, under) + quads("slab", 2, -H, xs, ys, under)
        f = box_faces("slab", xs, ys, zs)
        slab += f["x0"] + f["x1"] + f["y0"] + f["y1"]
        files["slab.txt"] = "* slab surface except under the strips\n" + "\n".join(slab) + "\n"
        files["ms3d.lst"] += f"D slab.txt 1.0 {ER} 0 0 0 0 0 0 -\n"
    return files


def case_k(a, p, form):
    d1 = D_GAP / 2
    xs = graded([-a / 2, a / 2], p)
    files = {"pp.lst": f"* parallel plates a = {a:g} m, gap {D_GAP:g} m, user mesh p = {p:g} m, {form}\n"}
    zt = graded([-T_PLATE, 0.0], p)
    fb = box_faces("low", xs, xs, zt)
    fu = box_faces("up", xs, xs, graded([D_GAP, D_GAP + T_PLATE], p))
    er = ER if form == "diel" else 1.0
    files["low_air.txt"] = "* lower plate, air faces\n" + "\n".join(ln for k, v in fb.items() if k != "z1" for ln in v) + "\n"
    files["low_diel.txt"] = "* lower plate, face under the layer\n" + "\n".join(fb["z1"]) + "\n"
    files["up.txt"] = "* upper plate\n" + "\n".join(ln for v in fu.values() for ln in v) + "\n"
    files["pp.lst"] += f"C low_air.txt 1.0 0 0 0 +\nC low_diel.txt {er} 0 0 0\nC up.txt 1.0 0 0 0\n"
    if form == "diel":
        zs = graded([0.0, d1], p)
        f = box_faces("layer", xs, xs, zs)
        layer = f["x0"] + f["x1"] + f["y0"] + f["y1"] + f["z1"]
        files["layer.txt"] = "* dielectric layer, faces not on the lower plate\n" + "\n".join(layer) + "\n"
        files["pp.lst"] += f"D layer.txt 1.0 {ER} 0 0 0 0 0 {d1 / 2:.9g} -\n"
    return files


ARGS = "-m1e9 -d1e-11"
ARGS_FINE = "-m1e9 -d1e-12"


def run(files, workdir, args, timeout=TIMEOUT):
    """Write the inputs, run FasterCap with args, return (matrix, input panels, panels after refinement, seconds)."""
    workdir.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (workdir / name).write_text(text, encoding="ascii")
    root = next(iter(files))
    pidfile = workdir / "fastercap.pid"
    if platform.system() == "Windows":
        cmd = ["wsl", "-e", "bash", "-c",
               f"cd '{wsl_path(workdir)}' && echo $$ > '{pidfile.name}' && exec '{wsl_path(FC_BIN)}' -b {root} {args}"]
    else:
        cmd = [str(FC_BIN), "-b", root, *args.split()]
    try:
        p = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        if platform.system() == "Windows":  # stop only this run's process, checked to still be FasterCap
            pid = pidfile.read_text().strip() if pidfile.exists() else ""
            if pid.isdigit():
                subprocess.run(["wsl", "-e", "bash", "-c",
                                f'[ "$(cat /proc/{pid}/comm 2>/dev/null)" = FasterCap ] && kill {pid}'], check=False)
        raise RuntimeError(f"FasterCap did not finish within {timeout:g} s ({args})")
    (workdir / "stdout.log").write_text(p.stdout or "", encoding="utf-8")
    if p.returncode != 0:
        raise RuntimeError(f"FasterCap failed in {workdir} (status {p.returncode}): {(p.stderr or p.stdout)[-500:]}")
    auto = re.search(r"-a(\S+)", args)
    problem = run_problem(p.stdout, float(auto.group(1)) if auto else None)
    if problem:  # audit at 9ca735d: the false-success gate of the shared runner applies here too
        raise RuntimeError(f"FasterCap result rejected in {workdir}: {problem}")
    _, m = parse_last_matrix(p.stdout)
    n_in = [int(x) for x in re.findall(r"Number of input panels to solver engine: (\d+)", p.stdout)]
    n_ref = [int(x) for x in re.findall(r"Number of panels after refinement: (\d+)", p.stdout)]
    secs = re.findall(r"Total time: (\S+)s", p.stdout)
    return m, n_in[-1] if n_in else None, n_ref[-1] if n_ref else None, float(secs[-1]) if secs else None


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def main():
    run_root = ROOT / "runs" / f"fastercap-manual-mesh-{uuid.uuid4().hex[:12]}"
    h_rep = json.loads((ROOT / "results/gan/fastercap-board3d-check.json").read_text(encoding="utf-8"))
    ref_2d = h_rep["two_d"]["0.001"]["value_F_per_m"]
    rep = {"schema": "fastercap-manual-mesh-check/2", "declared": "2026-10-02, before the first run (docstring)",
           "evaluator_sha256": sha("scripts/fastercap_manual_mesh_check.py"),
           "dependencies_sha256": {p: sha(p) for p in DEPENDENCIES},
           "binary_sha256": hashlib.sha256(FC_BIN.read_bytes()).hexdigest(),
           "run_directory": run_root.relative_to(ROOT).as_posix(),
           "references": {"hj_air_F_per_m": hammerstad_jensen(W / H, T / H, 1.0),
                          "hj_diel_F_per_m": hammerstad_jensen(W / H, T / H, ER), "case_h_2d_a0.001_F_per_m": ref_2d},
           "part_d": {}, "part_k1": {}, "errors": [], "checks": {}}

    def save():
        tmp = OUTPUT.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(rep, indent=1) + "\n")
        os.replace(tmp, OUTPUT)

    def solve(key, files, wd, args=ARGS):
        try:
            m, n_in, n_ref, secs = run(files, wd, args)
            val = matrix_validity(m)
            rec = {"matrix": m, "validity": val, "input_panels": n_in, "panels_after_refinement": n_ref,
                   "seconds": secs, "C_pair_F": pair(m) if not val else None}
        except RuntimeError as exc:
            rep["errors"].append(f"{key}: {exc}")
            rec = {"error": str(exc)}
        print(key, {k: v for k, v in rec.items() if k != "matrix"}, flush=True)
        return rec

    # ---- part D
    for form in ("air", "diel"):
        for mesh, p in D_MESHES.items():
            row = {}
            for L in (L1, L2):
                row[f"{L:g}"] = solve(f"D {form} {mesh} L={L:g}", case_d(L, p, form), run_root / f"d-{form}-{mesh}-L{L * 1e3:g}mm")
            a, b = row[f"{L1:g}"].get("C_pair_F"), row[f"{L2:g}"].get("C_pair_F")
            row["C_per_m"] = 2 * (b - a) / (L2 - L1) if a and b and b > a > 0 else None
            rep["part_d"].setdefault(form, {})[mesh] = row
            save()
    for form in ("air", "diel"):
        row = {}
        for L in (L1, L2):
            row[f"{L:g}"] = solve(f"D5 {form} M2 L={L:g} threshold 0.001", case_d(L, D_MESHES["M2"], form),
                                  run_root / f"d5-{form}-M2-L{L * 1e3:g}mm", ARGS_FINE)
        a, b = row[f"{L1:g}"].get("C_pair_F"), row[f"{L2:g}"].get("C_pair_F")
        row["C_per_m"] = 2 * (b - a) / (L2 - L1) if a and b and b > a > 0 else None
        rep.setdefault("part_d5", {})[form] = row
        save()
    rep["part_d"]["auto_from_M1_diel_L1"] = solve("D diel M1 L1 -a0.01", case_d(L1, D_MESHES["M1"], "diel"),
                                                  run_root / "d-diel-M1-L2mm-auto", "-a0.01")
    runs = [r for form in ("air", "diel") for row in rep["part_d"][form].values() for k, r in row.items() if k != "C_per_m"]
    cp = {form: [rep["part_d"][form][m]["C_per_m"] for m in D_MESHES] for form in ("air", "diel")}
    chg = {f: abs(v[2] / v[1] - 1) if v[1] and v[2] else None for f, v in cp.items()}
    d3 = cp["air"][2] / rep["references"]["hj_air_F_per_m"] - 1 if cp["air"][2] else None
    d4 = cp["diel"][2] / ref_2d - 1 if cp["diel"][2] else None
    rep["checks"]["D0_no_refinement"] = all(r.get("input_panels") is not None and r.get("input_panels") == r.get("panels_after_refinement") for r in runs)
    rep["checks"]["D1_valid"] = {f: all("matrix" in r and not r["validity"] for row in rep["part_d"][f].values()
                                        for k, r in row.items() if k != "C_per_m") for f in ("air", "diel")}
    rep["checks"]["D2_mesh_change"] = {f: {"change": chg[f], "pass": chg[f] is not None and chg[f] <= 0.01} for f in chg}
    d5 = {}
    for f in ("air", "diel"):
        a5, a2 = rep["part_d5"][f]["C_per_m"], rep["part_d"][f]["M2"]["C_per_m"]
        ch = abs(a5 / a2 - 1) if a5 and a2 else None
        d5[f] = {"change": ch, "pass": ch is not None and ch <= 0.002}
    rep["checks"]["D5_interaction_threshold"] = d5
    rep["checks"]["D3_air_vs_hj"] = {"relative_error": d3, "pass": d3 is not None and abs(d3) <= 0.01}
    rep["checks"]["D4_diel_vs_2d"] = {"relative_error": d4, "pass": d4 is not None and abs(d4) <= 0.02,
                                      "vs_hj_infinite_slab": cp["diel"][2] / rep["references"]["hj_diel_F_per_m"] - 1 if cp["diel"][2] else None}
    c = rep["checks"]
    rep["part_d_all_pass"] = bool(c["D0_no_refinement"] and all(c["D1_valid"].values())
                                  and all(v["pass"] for v in c["D5_interaction_threshold"].values())
                                  and all(v["pass"] for v in c["D2_mesh_change"].values()) and c["D3_air_vs_hj"]["pass"]
                                  and c["D4_diel_vs_2d"]["pass"])
    save()

    # ---- part K1, gated
    gate = c["D0_no_refinement"] and all(c["D1_valid"].values()) and all(v["pass"] for v in c["D2_mesh_change"].values())         and all(v["pass"] for v in c["D5_interaction_threshold"].values())
    if not gate:
        rep["part_k1"] = {"run": False, "reason": "part D did not pass D0, D1, D2 and D5 for both forms"}
        rep["outcome"] = "part D failed its gate; K1 not run"
        save()
        print(json.dumps(rep["checks"], indent=1))
        return
    d1 = D_GAP / 2
    alpha_ref = {"air": EPS0 / D_GAP, "diel": EPS0 / (d1 / ER + (D_GAP - d1))}
    for form in ("air", "diel"):
        for mesh, p in K_MESHES.items():
            row = {}
            for n in K_SIZES + (K_HOLDOUT,):
                row[str(n)] = solve(f"K1 {form} {mesh} a={n}d", case_k(n * D_GAP, p, form), run_root / f"k-{form}-{mesh}-a{n}")
            cs = [row[str(n)].get("C_pair_F") for n in K_SIZES]
            if all(cs):
                A = np.array([[(n * D_GAP) ** 2, n * D_GAP, 1.0] for n in K_SIZES])
                al, be, ga = np.linalg.solve(A, np.array(cs))
                row["fit"] = {"alpha_F_per_m2": al, "beta_F_per_m": be, "gamma_F": ga,
                              "alpha_rel_error": al / alpha_ref[form] - 1}
                ho = row[str(K_HOLDOUT)].get("C_pair_F")
                a4 = K_HOLDOUT * D_GAP
                row["fit"]["holdout_rel_error"] = ho / (al * a4 ** 2 + be * a4 + ga) - 1 if ho else None
            rep["part_k1"].setdefault(form, {})[mesh] = row
            save()
    fine, coarse = list(K_MESHES)[-1], list(K_MESHES)[0]
    k = {}
    for form, tol in (("air", 0.005), ("diel", 0.01)):
        ff, fc = rep["part_k1"][form][fine].get("fit"), rep["part_k1"][form][coarse].get("fit")
        e = ff["alpha_rel_error"] if ff else None
        k["K1a_air" if form == "air" else "K1b_diel"] = {"alpha_rel_error": e, "pass": e is not None and abs(e) <= tol}
        h = ff["holdout_rel_error"] if ff else None
        k[f"K1c_holdout_{form}"] = {"relative_error": h, "pass": h is not None and abs(h) <= 0.002}
        mc = abs(ff["alpha_F_per_m2"] / fc["alpha_F_per_m2"] - 1) if ff and fc else None
        k[f"K1d_mesh_{form}"] = {"change": mc, "pass": mc is not None and mc <= 0.005}
    k["K1_valid"] = all("matrix" in r and not r["validity"] for f in ("air", "diel") for row in rep["part_k1"][f].values()
                        for kk, r in row.items() if kk != "fit")
    rep["checks"].update(k)
    rep["part_k1_all_pass"] = all(v["pass"] if isinstance(v, dict) else v for v in k.values())
    rep["outcome"] = "complete"
    save()
    print(json.dumps(rep["checks"], indent=1))


if __name__ == "__main__":
    main()
