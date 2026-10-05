#!/usr/bin/env python3
"""Known-answer qualification of FasterCap before any board capacitance extraction (G3).

FasterCap 6.0.7 (FastFieldSolvers; ediloren/FasterCap with its LinAlgebra and Geometry packages, LGPL 2.1 or later)
is built headless under WSL from source in the git-ignored .tools/ by .tools/build-fastercap.sh (docs/build.md).
Units are SI: coordinates in metres, capacitance in F (3D) or F/m (2D).

Cases and tolerances, fixed before the first run on 30 September 2026. One smoke run came first, of case A
at -a0.001, to learn the output format; it gave -0.05 %.

A. Unit cube in air (3D, sharp edges and corners): against 0.6606785 x 4 pi eps0 a (Hwang and Mascagni 2004,
   random-walk value, uncertainty below 1e-6). Tolerance 0.5 %.
B. Sphere in air (3D), radius 1 mm, icosphere of 1280 flat triangles (the inscribed facets make the geometry
   about 0.1 % small): against 4 pi eps0 R. Tolerance 1 %.
C. The same sphere coated with a dielectric shell, eps_r 4.3 to radius 2 mm, air outside (3D, 'D' interface):
   against 4 pi eps0 / ((1/a - 1/b) / eps_r + 1/b). Tolerance 1 %.
D. Coaxial line in air (2D), radii 1 and 2 mm, 128-segment polygons: against 2 pi eps0 / ln(b/a). Tolerance 0.5 %.
E. Coaxial line with a dielectric layer (2D), eps_r 4.3 from 1 to 1.5 mm, air to 2 mm: against
   2 pi eps0 / (ln(b/a) / eps_r + ln(c/b)). Tolerance 0.5 %.
F. Coplanar strips in air (2D), zero thickness, width 1 mm, gap 0.2 mm: against eps0 K(k') / K(k),
   k = s / (s + 2 w) (conformal mapping, exact). Tolerance 1 % (field singularities at the strip edges).
G. Microstrip, strip width 2h, thickness h/100, h = 0.1 mm, by symmetry: a strip on each face of a slab of
   thickness 2h, driven in opposite phase, so the mid-plane is the ground plane (C_ms = 2 x the pair capacitance).
   The slab and the domain are truncated at +-40 h. Reference: Hammerstad and Jensen (1980) with their thickness
   correction. (i) Slab of eps_r 1 (air): tolerance 2 %. (ii) eps_r 4.3: tolerance 2 %. (ii) tests the dielectric
   interface at a conductor edge, which a board with FR-4 needs.
The two-conductor capacitance is taken from the 2 x 2 Maxwell matrix as (C11 C22 - C12 C21) / (C11 + C22 + C12 + C21).
Mesh check: every case runs with -a0.005 and with -a0.001 (FasterCap's automatic refinement, stopping when the
relative change is below that value); the two must agree within 0.5 %. The -a0.001 value is scored.

Run 1 (30 September 2026) stopped at case D on an evaluator error: the 2D output is a 1 x 1 matrix for two
conductors (the last conductor is the reference, see pair()), and the 2 x 2 reading failed. Its A-C values are
kept in its run directory. The fix changes only how the output is read, not a case or a tolerance.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess
import uuid

from scipy.special import ellipk

ROOT = Path(__file__).resolve().parents[1]
FC_BIN = ROOT / ".tools" / "FasterCap-bin" / "FasterCap"
FC_SRC = ROOT / ".tools" / "FasterCap"
EPS0 = 8.8541878128e-12
C0 = 299792458.0
ETA0 = 4e-7 * math.pi * C0
TOL = {"A": 0.005, "B": 0.01, "C": 0.01, "D": 0.005, "E": 0.005, "F": 0.01, "G_air": 0.02, "G_er4.3": 0.02}
MESH_TOL = 0.005
AUTO = ("0.005", "0.001")
ER = 4.3


def wsl_path(p):
    p = Path(p).resolve()
    return "/mnt/" + p.drive[0].lower() + p.as_posix()[2:]


def run_fastercap(files, workdir, auto, timeout, extra=""):
    """Write the input files (first is the root), run FasterCap, return (Maxwell matrix, names, stdout).
    `extra` adds FasterCap options (e.g. -f0, stay in core); the default leaves every earlier call unchanged."""
    workdir.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (workdir / name).write_text(text, encoding="ascii")
    root = next(iter(files))
    args = f"-b {root} -a{auto}" + (f" {extra}" if extra else "")
    pidfile = workdir / f"fastercap-a{auto}.pid"
    if platform.system() == "Windows":
        # exec keeps bash's PID, so the PID file names this run's FasterCap process and no other.
        cmd = ["wsl", "-e", "bash", "-c",
               f"cd '{wsl_path(workdir)}' && echo $$ > '{pidfile.name}' && exec '{wsl_path(FC_BIN)}' {args}"]
    else:
        cmd = [str(FC_BIN), *args.split()]
    try:
        p = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        if platform.system() == "Windows":  # the Linux process outlives wsl.exe
            # Audit, 30 September 2026: kill only this run's process (the host is shared; pkill -x would
            # also stop other FasterCap jobs). The PID is checked to still be FasterCap before the kill.
            pid = pidfile.read_text().strip() if pidfile.exists() else ""
            if pid.isdigit():
                subprocess.run(["wsl", "-e", "bash", "-c",
                                f'[ "$(cat /proc/{pid}/comm 2>/dev/null)" = FasterCap ] && kill {pid}'], check=False)
        raise RuntimeError(f"FasterCap did not finish within {timeout:g} s at -a{auto}")
    (workdir / f"stdout-a{auto}.log").write_text(p.stdout or "", encoding="utf-8")
    if p.returncode != 0:
        raise RuntimeError(f"FasterCap failed in {workdir} (status {p.returncode}): {(p.stderr or p.stdout)[-500:]}")
    problem = run_problem(p.stdout, float(auto))
    if problem:
        raise RuntimeError(f"FasterCap result rejected in {workdir}: {problem}")
    names, matrix = parse_last_matrix(p.stdout)
    return matrix, names, p.stdout


def run_problem(text, auto=None):
    """Why a FasterCap log must not be read as a result, or None.

    Added 3 October 2026: under memory pressure FasterCap printed "Cannot go out-of-core, terminating process" during
    an automatic iteration and still exited 0, so the last matrix printed (an earlier, unconverged iteration) was read
    as the result (via-array references, run 2). A log is rejected if it reports that termination, or, in automatic
    mode, if its last relative change exceeds the requested -a value (FasterCap stops either on convergence or on its
    iteration limit).
    """
    if "Cannot go out-of-core" in text or "Cannot go Out-of-Core" in text or "not enough to allocate" in text:
        return "FasterCap terminated for lack of memory"
    if auto is not None:
        diffs = re.findall(r"Weighted Frobenius norm of the difference between capacitance \(auto option\): (\S+)", text)
        if diffs and float(diffs[-1]) > auto:
            return f"automatic refinement ended without converging (last change {diffs[-1]} > {auto:g})"
    return None


def parse_last_matrix(text):
    blocks = text.split("Capacitance matrix is:")
    if len(blocks) < 2:
        raise RuntimeError("no capacitance matrix in FasterCap output")
    lines = blocks[-1].strip().splitlines()
    n = int(re.match(r"Dimension (\d+) x \d+", lines[0]).group(1))
    names, rows = [], []
    for line in lines[1:1 + n]:
        parts = line.split()
        names.append(parts[0])
        rows.append([float(x) for x in parts[1:1 + n]])
    return names, rows


def pair(m):
    if len(m) == 1:
        # 2D: FasterCap takes the last conductor as the reference and removes its row and column
        # (Solver/SolveCapacitance.cpp; charge balance after Djordjevic, Harrington and Sarkar 1994), so for two
        # conductors the one entry is already the capacitance between them.
        return m[0][0]
    (c11, c12), (c21, c22) = m
    return (c11 * c22 - c12 * c21) / (c11 + c22 + c12 + c21)


# ---------- geometry ----------

def quad_box(name, x0, y0, z0, x1, y1, z1):
    pts = lambda *c: " ".join(f"{v:.9g}" for v in c)
    faces = [(x1, y0, z0, x1, y1, z0, x1, y1, z1, x1, y0, z1), (x0, y0, z0, x0, y0, z1, x0, y1, z1, x0, y1, z0),
             (x0, y1, z0, x0, y1, z1, x1, y1, z1, x1, y1, z0), (x0, y0, z0, x1, y0, z0, x1, y0, z1, x0, y0, z1),
             (x0, y0, z0, x0, y1, z0, x1, y1, z0, x1, y0, z0), (x0, y0, z1, x1, y0, z1, x1, y1, z1, x0, y1, z1)]
    return "".join(f"Q {name} {pts(*f)}\n" for f in faces)


def icosphere(name, radius, level=3):
    t = (1 + 5 ** 0.5) / 2
    v = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
         (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    v = [tuple(c / math.sqrt(sum(x * x for x in p)) for c in p) for p in v]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
         (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10),
         (8, 6, 7), (9, 8, 1)]
    for _ in range(level):
        cache, nf = {}, []

        def mid(a, b):
            key = (min(a, b), max(a, b))
            if key not in cache:
                p = [(v[a][i] + v[b][i]) / 2 for i in range(3)]
                r = math.sqrt(sum(x * x for x in p))
                v.append(tuple(x / r for x in p))
                cache[key] = len(v) - 1
            return cache[key]
        for a, b, c in f:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        f = nf
    return "".join("T " + name + " " + "  ".join(" ".join(f"{radius * x:.9g}" for x in v[i]) for i in tri) + "\n"
                   for tri in f), len(f)


def circle(name, r, n=128):
    pts = [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n)) for k in range(n + 1)]
    return "".join(f"S {name} {x0:.9g} {y0:.9g}  {x1:.9g} {y1:.9g}\n" for (x0, y0), (x1, y1) in zip(pts, pts[1:]))


def seg(name, x0, y0, x1, y1):
    return f"S {name} {x0:.9g} {y0:.9g}  {x1:.9g} {y1:.9g}\n"


# ---------- cases ----------

def case_a():
    a = 1.0
    return {"cube.txt": "* unit cube in air\n" + quad_box("cube", 0, 0, 0, a, a, a)}, \
        0.6606785 * 4 * math.pi * EPS0 * a, lambda m: m[0][0], {"edge_m": a}


def case_b():
    r = 1e-3
    text, n = icosphere("sph", r)
    return {"sphere.txt": "* sphere in air\n" + text}, 4 * math.pi * EPS0 * r, lambda m: m[0][0], \
        {"radius_m": r, "triangles": n}


def case_c():
    a, b = 1e-3, 2e-3
    ta, n = icosphere("sph", a)
    tb, _ = icosphere("shell", b)
    root = f"* coated sphere\nC inner.txt {ER} 0 0 0\nD shell.txt 1.0 {ER} 0 0 0 0 0 0 -\n"
    ref = 4 * math.pi * EPS0 / ((1 / a - 1 / b) / ER + 1 / b)
    return {"coated.lst": root, "inner.txt": "* inner\n" + ta, "shell.txt": "* shell\n" + tb}, ref, \
        lambda m: m[0][0], {"a_m": a, "b_m": b, "eps_r": ER, "triangles_each": n}


def case_d():
    a, b = 1e-3, 2e-3
    root = "2D coax in air\nC inner.txt 1.0 0 0\nC outer.txt 1.0 0 0\n"
    return {"coax.lst": root, "inner.txt": "* inner\n" + circle("inner", a), "outer.txt": "* outer\n" + circle("outer", b)}, \
        2 * math.pi * EPS0 / math.log(b / a), pair, {"a_m": a, "b_m": b, "segments": 128}


def case_e():
    a, b, c = 1e-3, 1.5e-3, 2e-3
    root = (f"2D coated coax\nC inner.txt {ER} 0 0\nD mid.txt 1.0 {ER} 0 0 0 0 -\nC outer.txt 1.0 0 0\n")
    ref = 2 * math.pi * EPS0 / (math.log(b / a) / ER + math.log(c / b))
    return {"coax.lst": root, "inner.txt": "* inner\n" + circle("inner", a), "mid.txt": "* interface\n" + circle("mid", b),
            "outer.txt": "* outer\n" + circle("outer", c)}, ref, pair, {"a_m": a, "b_m": b, "c_m": c, "eps_r": ER}


def case_f():
    w, s = 1e-3, 0.2e-3
    k = s / (s + 2 * w)
    ref = float(EPS0 * ellipk(1 - k * k) / ellipk(k * k))
    root = "2D coplanar strips\nC left.txt 1.0 0 0\nC right.txt 1.0 0 0\n"
    return {"cps.lst": root, "left.txt": "* left\n" + seg("left", -s / 2 - w, 0, -s / 2, 0),
            "right.txt": "* right\n" + seg("right", s / 2, 0, s / 2 + w, 0)}, ref, pair, \
        {"width_m": w, "gap_m": s, "k": k}


def hammerstad_jensen(u, t, er):
    """Static microstrip C per metre, Hammerstad and Jensen (1980), with their thickness correction (t = T/h)."""
    def z01(x):
        f = 6 + (2 * math.pi - 6) * math.exp(-(30.666 / x) ** 0.7528)
        return ETA0 / (2 * math.pi) * math.log(f / x + math.sqrt(1 + (2 / x) ** 2))

    def eeff(x, e):
        a = 1 + math.log((x ** 4 + (x / 52) ** 2) / (x ** 4 + 0.432)) / 49 + math.log(1 + (x / 18.1) ** 3) / 18.7
        b = 0.564 * ((e - 0.9) / (e + 3)) ** 0.053
        return (e + 1) / 2 + (e - 1) / 2 * (1 + 10 / x) ** (-a * b)

    du1 = t / math.pi * math.log(1 + 4 * math.e / (t / math.tanh(math.sqrt(6.517 * u)) ** 2))
    dur = 0.5 * (1 + 1 / math.cosh(math.sqrt(er - 1))) * du1
    u1, ur = u + du1, u + dur
    z0 = z01(ur) / math.sqrt(eeff(ur, er))
    e_eff = eeff(ur, er) * (z01(u1) / z01(ur)) ** 2
    return math.sqrt(e_eff) / (C0 * z0)


def case_g(er):
    h = 0.1e-3
    w, t, span = 2 * h, h / 100, 40 * h
    x0, x1 = -w / 2, w / 2
    files = {"ms.lst": f"2D microstrip by symmetry, eps_r {er}\n"}
    for tag, yb, yt, inner in (("top", h, h + t, h), ("bot", -h - t, -h, -h)):
        # faces towards the slab sit in the dielectric; the rest in air
        outer_faces = (seg(tag, x1, yt, x0, yt) + seg(tag, x1, yb, x1, yt) + seg(tag, x0, yt, x0, yb)) if tag == "top" \
            else (seg(tag, x0, yb, x1, yb) + seg(tag, x1, yb, x1, yt) + seg(tag, x0, yt, x0, yb))
        inner_face = seg(tag, x0, inner, x1, inner)
        files[f"{tag}_air.txt"] = f"* {tag} strip, air faces\n" + outer_faces
        files[f"{tag}_diel.txt"] = f"* {tag} strip, slab face\n" + inner_face
        files["ms.lst"] += f"C {tag}_air.txt 1.0 0 0 +\nC {tag}_diel.txt {er} 0 0\n"
    if er != 1.0:
        iface = (seg("slab", -span, h, x0, h) + seg("slab", x1, h, span, h) + seg("slab", -span, -h, x0, -h)
                 + seg("slab", x1, -h, span, -h) + seg("slab", -span, -h, -span, h) + seg("slab", span, -h, span, h))
        files["slab.txt"] = "* slab surface except under the strips\n" + iface
        files["ms.lst"] += f"D slab.txt 1.0 {er} 0 0 0 0 -\n"
    ref = hammerstad_jensen(w / h, t / h, er)
    return files, ref, lambda m: 2 * pair(m), {"h_m": h, "w_m": w, "t_m": t, "half_span_m": span, "eps_r": er}


CASES = {"A": case_a, "B": case_b, "C": case_c, "D": case_d, "E": case_e, "F": case_f,
         "G_air": lambda: case_g(1.0), "G_er4.3": lambda: case_g(ER)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/fastercap-known-answer.json")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--timeout", type=float, default=1800, help="per FasterCap call, s; a timeout fails the case")
    args = ap.parse_args()
    # Audit, 30 September 2026: an unknown or empty --only selected nothing and all([]) reported all_pass.
    if args.only is not None:
        unknown = sorted(set(args.only) - set(CASES))
        if not args.only or unknown:
            raise SystemExit(f"--only needs known case names; unknown: {unknown}; known: {sorted(CASES)}")
    requested = [k for k in CASES if args.only is None or k in args.only]
    run_root = ROOT / "runs" / f"fastercap-known-answer-{uuid.uuid4().hex[:12]}"
    results = {}
    commit = lambda d: subprocess.run(["git", "-C", str(d), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    tool = {"name": "FasterCap", "version": "6.0.7", "licence": "LGPL 2.1 or later",
            "sources": {"FasterCap": commit(FC_SRC), "LinAlgebra": commit(ROOT / ".tools/LinAlgebra"),
                        "Geometry": commit(ROOT / ".tools/Geometry")},
            "build": ".tools/build-fastercap.sh (headless; wxWidgets 3.2 base, Ubuntu 24.04)",
            "binary_sha256": hashlib.sha256(FC_BIN.read_bytes()).hexdigest()}

    def write_report():
        """Checkpoint after every case (atomic replace); all_pass needs every requested case, all passing."""
        complete = [k for k in requested if k in results] == requested
        report = {"tool": tool, "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  "requested_cases": requested, "complete": complete,
                  "cases": results, "run_directory": run_root.relative_to(ROOT).as_posix(),
                  "time_limit_per_call_s": args.timeout,
                  "all_pass": complete and bool(results) and all(r["pass"] for r in results.values())}
        tmp = args.output.with_suffix(args.output.suffix + ".tmp")
        tmp.write_text(json.dumps(report, indent=1) + "\n")
        os.replace(tmp, args.output)
        return report

    for key in requested:
        build = CASES[key]
        files, ref, extract, geometry = build()
        values = {}
        try:
            for auto in AUTO:
                m, names, _ = run_fastercap(files, run_root / key, auto, args.timeout)
                values[auto] = {"matrix": m, "conductors": names, "value": extract(m)}
        except RuntimeError as exc:
            results[key] = {"reference": ref, "tolerance": TOL[key], "geometry": geometry, "runs": values,
                            "error": str(exc), "pass": False}
            print(f"{key}: ref {ref:.6g} FAIL: {exc}", flush=True)
            write_report()
            continue
        v, coarse = values[AUTO[-1]]["value"], values[AUTO[0]]["value"]
        err, mesh = v / ref - 1, abs(coarse / v - 1)
        results[key] = {"reference": ref, "value": v, "relative_error": err, "tolerance": TOL[key],
                        "mesh_change": mesh, "mesh_tolerance": MESH_TOL, "geometry": geometry, "runs": values,
                        "pass": abs(err) <= TOL[key] and mesh <= MESH_TOL}
        print(f"{key}: ref {ref:.6g} got {v:.6g} err {100 * err:+.3f}% mesh {100 * mesh:.3f}% "
              f"{'PASS' if results[key]['pass'] else 'FAIL'}", flush=True)
        write_report()
    report = write_report()
    print("all pass" if report["all_pass"] else "FAILURES recorded")


if __name__ == "__main__":
    main()
