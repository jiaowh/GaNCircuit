#!/usr/bin/env python3
"""Plane-pair slots in FastHenry under the production mesh rule, against a 2D sheet-current reference (P1, P2).

Declared 2 October 2026, before its first run (plan section 10 item 9; docs/build.md "Via-array, plane-hole and
FasterCap qualification"). The mesh topology audit (scripts/audit_epc90133_mesh_topology.py) found that under each
EPC90133 transistor the antipads of a six-via row merge into a slot of about 0.66 x 3.66 mm in the ground return planes,
and that at the coarse board mesh the segment widths cover 27 % of that hole area (production grid lines run down the
slot centres). This benchmark measures what the production representation does to the inductance of such a slot. It
reports errors of these benchmark geometries; it does not give board error bars.

Geometry (mm). A plane-pair strip at the board's top-layer/mid-layer-1 stack: plates of copper thickness T = 0.0711,
gap h = 0.127, plate mid-planes at z = 0 (bottom, the return plate) and h + T (top). Strip length L = 6.8 along x (the
current direction), width W = 5.1. Port at x = 0 between the two plates' edge nodes (each plate's x = 0 nodes tied);
the far end x = L is shorted by a wall of vertical segments (width s, thickness T), as in the single-via cavity.
Copper 5.8e7 S/m, 100 MHz (skin depth delta 6.61 um). Slots are rectangles centred on (3.4, 2.55):
    perp   0.65 (x) x 3.65 (y): long axis across the current (the most disruptive orientation);
    par    3.65 (x) x 0.65 (y): long axis along the current;
    small  0.35 (x) x 1.85 (y), across the current.
Forms: P1 the slot cut through both plates; P2 the slot in the return (bottom) plate only, as on the board.
On the board the slots run along y and the return current under the transistors flows mostly along y, which resembles
"par"; that resemblance is a geometric reading, not an extracted current distribution.

Mesh rule, as in scripts/epc90133_extract.py: a node at every grid point on copper (strictly outside every slot of its
plate), a segment of width s between neighbouring nodes when its centre line does not cross a slot, thickness T,
nwinc 1, nhinc n, rh 2. Meshes (s, n): m1 (0.425, 3) and m2 (0.2125, 5) are the board's; f3 (0.10625, 5) and
f4 (0.0708333, 5) are finer. Alignment: "aligned" puts a grid line through the slot centre in x and y (the production
grid is aligned to the pin rows, which are the slot centres); "shifted" moves the slot by (s/2, s/2).
Run matrix:
    none                m1, m2, f3, f4
    P1 perp, P2 perp    m1, m2 aligned and shifted; f3 aligned; f4 aligned
    P1 par,  P2 par     m1, m2 aligned and shifted; f3 aligned
    P1 small            m1, m2, f3 aligned
    gap h/2: none and P1 perp   f3, f4
Added inductance dL = Im(Z_slot - Z_none) / omega at the same mesh and gap.

Reference (P1 only). In the perfect-conductor sheet picture a plane pair carries the same current pattern in both
plates, with inductance mu0 (h + delta) per square; a slot through both plates is an insulating boundary. dL_ref =
mu0 (h + delta) dN, where dN is the slot's added squares from circuit_tools.sheet (exact for the unslotted strip; slot
edges lie on cell faces, so there is no staircase error; dilute-hole check in tests/test_sheet.py). The picture neglects
field fringing over a distance of order h at the slot edges and at the strip's open sides (the side fringing is common
to dL's two terms). No reference exists for P2.

Checks, fixed here:
R1  reference: dN at cells 0.025, 0.0125, 0.00625 mm for each P1 slot, aligned; the last two agree within 0.5 %;
    the unslotted strip gives L/W squares within 1e-9.
P1a FastHenry mesh: dL(P1 perp) changes by <= 3 % from f3 to f4.
P1b accuracy: dL(P1 perp, f4) within 5 % of dL_ref.
P1c gap trend: the relative error of dL(P1 perp) against its own dL_ref is smaller in magnitude at h/2 than at h, or
    both are within 2 % (consistent with edge fringing of order h being the residual).
P2a mesh: dL(P2 perp) changes by <= 3 %, or by <= 1 pH, from f3 to f4.
Fallback, fixed here: the first f4 run (none) is the profile. If it takes more than 75 min, every other f4 run is
dropped and P1a, P1b, P1c and P2a use f3 as the finest mesh with m2 as the comparison mesh; this is recorded.
Reported, not judged: for every slot case at m1 and m2, aligned and shifted, the production-mesh error
e = dL / dL(finest aligned) - 1 and its absolute value in pH; the reference's change between the aligned and shifted
slot positions (cell 0.00625 for m2 shifts, 0.0125 not usable for them); the unslotted L against mu0 (h + delta) L / W.
Applicability: these numbers belong to this strip, these slots and this current direction. Transfer to the board needs
a separate argument or a board-subgeometry check.

Runs one FastHenry job at a time (-p diag), 3 h limit per job, report checkpointed after each job; --resume continues a
report written by the same evaluator.

Audit at 9ca735d (3 October 2026): FastHenry now runs through circuit_tools.wslrun, which stops the Linux solver itself
on timeout (before, only wsl.exe was stopped, so a timed-out case could keep running beside the next one); --resume also
refuses a report whose dependencies changed. No case, mesh or criterion changed; the stored run-1 report stays as written.

    python scripts/plane_hole_benchmark.py            # results/gan/plane-hole-benchmark.json
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from circuit_tools.sheet import disk_mask, squares  # noqa: E402
from circuit_tools.wslrun import run_solver  # noqa: E402
from fasthenry_known_answer import FH_BIN, SIGMA_CU_PER_MM, parse_zc, skin_depth  # noqa: E402

OUTPUT = ROOT / "results/gan/plane-hole-benchmark.json"
T, H = 0.0711, 0.127
LEN, WID = 6.8, 5.1
XC, YC = 3.4, 2.55
FREQ = 1e8
MU0 = 4e-7 * math.pi
SLOTS = {"perp": (0.65, 3.65), "par": (3.65, 0.65), "small": (0.35, 1.85)}
MESHES = {"m1": (0.425, 3), "m2": (0.2125, 5), "f3": (0.10625, 5), "f4": (0.425 / 6, 5)}
REF_CELLS = (0.025, 0.0125, 0.00625)
TIMEOUT = 3 * 3600
PROFILE_LIMIT = 75 * 60
DEPENDENCIES = ("src/circuit_tools/sheet.py", "scripts/fasthenry_known_answer.py", "src/circuit_tools/wslrun.py")


def runs_matrix():
    """(case key, form, slot, mesh, alignment, gap) in run order: references aside, cheap meshes first."""
    out = []
    for mesh in ("m1", "m2"):
        out.append(("none", None, None, mesh, "aligned", H))
        for form in ("P1", "P2"):
            for slot in ("perp", "par"):
                for al in ("aligned", "shifted"):
                    out.append((f"{form}-{slot}", form, slot, mesh, al, H))
        out.append(("P1-small", "P1", "small", mesh, "aligned", H))
    out.append(("none", None, None, "f4", "aligned", H))  # the profile
    out.append(("none", None, None, "f3", "aligned", H))
    for key, form, slot in (("P1-perp", "P1", "perp"), ("P2-perp", "P2", "perp"), ("P1-par", "P1", "par"),
                            ("P2-par", "P2", "par"), ("P1-small", "P1", "small")):
        out.append((key, form, slot, "f3", "aligned", H))
    out += [("none", None, None, "f3", "aligned", H / 2), ("P1-perp", "P1", "perp", "f3", "aligned", H / 2)]
    out += [(k, f, sl, "f4", "aligned", H) for k, f, sl in (("P1-perp", "P1", "perp"), ("P2-perp", "P2", "perp"))]
    out += [("none", None, None, "f4", "aligned", H / 2), ("P1-perp", "P1", "perp", "f4", "aligned", H / 2)]
    return out


def run_id(key, mesh, al, gap):
    return f"{key}|{mesh}|{al}|h={gap:g}"


def slot_rect(slot, shift):
    dx, dy = SLOTS[slot]
    cx, cy = XC + shift, YC + shift
    return (cx - dx / 2, cy - dy / 2, cx + dx / 2, cy + dy / 2)


def deck(form, slot, mesh, al, gap):
    s, n = MESHES[mesh]
    nx, ny = round(LEN / s), round(WID / s)
    if abs(nx * s - LEN) > 1e-9 or abs(ny * s - WID) > 1e-9:
        raise ValueError("the strip must be a whole number of pitches")
    rect = slot_rect(slot, s / 2 if al == "shifted" else 0.0) if slot else None
    plates = {"b": rect, "t": rect if form == "P1" else None}
    zt = gap + T
    copper = lambda p, x, y: not (plates[p] and plates[p][0] < x < plates[p][2] and plates[p][1] < y < plates[p][3])  # noqa: E731

    def crosses(p, x0, y0, x1, y1):
        r = plates[p]
        if not r:
            return False
        if y0 == y1:
            return r[1] < y0 < r[3] and max(x0, r[0]) < min(x1, r[2])
        return r[0] < x0 < r[2] and max(y0, r[1]) < min(y1, r[3])

    lines = [f"* plane-pair strip {form or 'none'} {slot or ''} mesh {mesh} {al} gap {gap:g}; "
             "generated by scripts/plane_hole_benchmark.py", ".units mm", f".default sigma={SIGMA_CU_PER_MM:g}"]
    nodes = {}
    for p, z in (("b", 0.0), ("t", zt)):
        for i in range(nx + 1):
            for j in range(ny + 1):
                x, y = i * s, j * s
                if copper(p, x, y):
                    nodes[(p, i, j)] = f"n{p}_{i}_{j}"
                    lines.append(f"n{p}_{i}_{j} x={x:.9g} y={y:.9g} z={z:.9g}")
    k = 0
    for (p, i, j), nm in nodes.items():
        for di, dj in ((1, 0), (0, 1)):
            nb = nodes.get((p, i + di, j + dj))
            if nb and not crosses(p, i * s, j * s, (i + di) * s, (j + dj) * s):
                k += 1
                lines.append(f"E{k} {nm} {nb} w={s:.9g} h={T} nwinc=1 nhinc={n} rh=2")
    for j in range(ny + 1):
        if ("b", nx, j) in nodes and ("t", nx, j) in nodes:
            k += 1
            lines.append(f"E{k} {nodes[('b', nx, j)]} {nodes[('t', nx, j)]} w={s:.9g} h={T} wx=0 wy=1 wz=0 nwinc=1 nhinc=1")
    for p in ("b", "t"):
        edge = [nodes[(p, 0, j)] for j in range(ny + 1) if (p, 0, j) in nodes]
        for c in range(1, len(edge), 40):
            lines.append(".equiv " + " ".join([edge[0]] + edge[c:c + 40]))
    tb = [nodes[("t", 0, j)] for j in range(ny + 1) if ("t", 0, j) in nodes][0]
    bb = [nodes[("b", 0, j)] for j in range(ny + 1) if ("b", 0, j) in nodes][0]
    lines += [f".external {tb} {bb} port", f".freq fmin={FREQ:g} fmax={FREQ:g} ndec=1", ".end", ""]
    filaments = sum(n for _ in range(k))
    return "\n".join(lines), {"nodes": len(nodes), "segments": k, "filaments_estimate": filaments}


def solve(text, workdir):
    workdir.mkdir(parents=True, exist_ok=False)
    (workdir / "case.inp").write_text(text, encoding="ascii")
    t0 = time.time()
    try:  # audit at 9ca735d: on timeout the Linux FastHenry process itself is stopped (circuit_tools.wslrun)
        p = run_solver(FH_BIN, "case.inp -p diag", workdir, TIMEOUT, "fasthenry")
    except TimeoutError:
        raise RuntimeError(f"FastHenry did not finish within {TIMEOUT} s")
    (workdir / "stdout.log").write_text(p.stdout or "", encoding="utf-8")
    zc = workdir / "Zc.mat"
    if p.returncode != 0 or not zc.is_file() or "matrix for frequency" not in zc.read_text(errors="replace"):
        raise RuntimeError(f"FastHenry failed (status {p.returncode}): {(p.stderr or p.stdout)[-400:]}")
    z = parse_zc(zc.read_text(encoding="ascii", errors="replace"))[FREQ]
    return z, time.time() - t0


def reference(rep):
    """R1: added squares per slot (aligned) at three cells, and at the m2-shifted position on the finest cell."""
    out = {}
    for slot in SLOTS:
        vals = []
        for cell in REF_CELLS:
            nx, ny = round(LEN / cell), round(WID / cell)
            base = squares(disk_mask(nx, ny, cell))
            rect = slot_rect(slot, 0.0)
            vals.append(squares(disk_mask(nx, ny, cell, slots=[rect])) - base)
            if slot == "perp":
                out.setdefault("unslotted_minus_L_over_W", []).append(base - LEN / WID)
        cell = REF_CELLS[-1]
        nx, ny = round(LEN / cell), round(WID / cell)
        shifted = {}
        for mesh in ("m1", "m2"):
            sh = MESHES[mesh][0] / 2
            shifted[mesh] = squares(disk_mask(nx, ny, cell, slots=[slot_rect(slot, sh)])) - squares(disk_mask(nx, ny, cell))
        out[slot] = {"dN_by_cell": dict(zip([f"{c:g}" for c in REF_CELLS], vals)),
                     "last_change": abs(vals[-1] / vals[-2] - 1), "dN": vals[-1], "dN_shifted": shifted}
        print("reference", slot, out[slot], flush=True)
    return out


def evaluate(rep):
    runs = rep["runs"]
    w = 2 * math.pi * FREQ
    delta = skin_depth(FREQ) * 1e3  # mm

    def L(key, mesh, al="aligned", gap=H):
        r = runs.get(run_id(key, mesh, al, gap))
        return r["Z_imag"] / w if r and "Z_imag" in r else None

    def dL(key, mesh, al="aligned", gap=H):
        a, b = L(key, mesh, al, gap), L("none", mesh, "aligned", gap)
        return a - b if a is not None and b is not None else None

    prof = runs.get(run_id("none", "f4", "aligned", H), {})
    fallback = prof.get("seconds") is None or prof["seconds"] > PROFILE_LIMIT
    fine, comp = ("f3", "m2") if fallback else ("f4", "f3")
    ref = rep["reference"]
    dl_ref = lambda gap: MU0 * (gap + delta) * 1e-3 * ref["perp"]["dN"]  # noqa: E731  (H; mm -> m)
    c = {"fallback_to_f3": fallback, "finest": fine, "comparison": comp}
    c["R1"] = {"changes": {s: ref[s]["last_change"] for s in SLOTS},
               "unslotted_minus_L_over_W": ref["unslotted_minus_L_over_W"],
               "pass": all(ref[s]["last_change"] <= 0.005 for s in SLOTS)
               and all(abs(v) <= 1e-9 for v in ref["unslotted_minus_L_over_W"])}
    a, b = dL("P1-perp", fine), dL("P1-perp", comp)
    ch = abs(a / b - 1) if a and b else None
    c["P1a"] = {"change": ch, "pass": ch is not None and ch <= 0.03}
    e_h = a / dl_ref(H) - 1 if a else None
    c["P1b"] = {"dL_H": a, "dL_ref_H": dl_ref(H), "relative_error": e_h, "pass": e_h is not None and abs(e_h) <= 0.05}
    a2 = dL("P1-perp", fine, gap=H / 2)
    e_h2 = a2 / dl_ref(H / 2) - 1 if a2 else None
    c["P1c"] = {"relative_error_h": e_h, "relative_error_h2": e_h2,
                "pass": e_h is not None and e_h2 is not None and (abs(e_h2) < abs(e_h) or max(abs(e_h), abs(e_h2)) <= 0.02)}
    p2, p2c = dL("P2-perp", fine), dL("P2-perp", comp)
    ch2 = abs(p2 / p2c - 1) if p2 and p2c else None
    c["P2a"] = {"change": ch2, "abs_change_pH": abs(p2 - p2c) * 1e12 if p2 and p2c else None,
                "pass": ch2 is not None and (ch2 <= 0.03 or abs(p2 - p2c) <= 1e-12)}
    prod = {}
    for key in ("P1-perp", "P1-par", "P2-perp", "P2-par", "P1-small"):
        best = dL(key, fine) if dL(key, fine) is not None else dL(key, "f3")
        for mesh in ("m1", "m2"):
            for al in ("aligned", "shifted"):
                v = dL(key, mesh, al)
                if v is not None and best:
                    prod[f"{key} {mesh} {al}"] = {"dL_pH": v * 1e12, "finest_pH": best * 1e12,
                                                  "error": v / best - 1, "error_pH": (v - best) * 1e12}
    c["production_mesh_error"] = prod
    c["dL_pH"] = {k: {m: (dL(k, m) * 1e12 if dL(k, m) is not None else None) for m in MESHES}
                  for k in ("P1-perp", "P1-par", "P2-perp", "P2-par", "P1-small")}
    Ln = L("none", fine)
    c["unslotted_L_vs_sheet"] = Ln / (MU0 * (H + delta) * 1e-3 * LEN / WID) - 1 if Ln else None
    rep["checks"] = c
    rep["all_pass"] = all(c[k]["pass"] for k in ("R1", "P1a", "P1b", "P1c", "P2a"))


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
        rep = {"schema": "plane-hole-benchmark/1", "declared": "2026-10-02, before the first run (docstring)",
               "evaluator_sha256": ev,
               "dependencies_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in DEPENDENCIES},
               "fasthenry_binary_sha256": hashlib.sha256(FH_BIN.read_bytes()).hexdigest(),
               "run_directory": f"runs/plane-hole-{uuid.uuid4().hex[:12]}", "runs": {}, "errors": []}

    def save():
        tmp = OUTPUT.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(rep, indent=1) + "\n")
        os.replace(tmp, OUTPUT)

    if "reference" not in rep:
        rep["reference"] = reference(rep)
        save()
    for key, form, slot, mesh, al, gap in runs_matrix():
        rid = run_id(key, mesh, al, gap)
        if rid in rep["runs"]:
            continue
        if mesh == "f4" and rid != run_id("none", "f4", "aligned", H):
            prof = rep["runs"].get(run_id("none", "f4", "aligned", H), {})
            if prof.get("seconds") is None or prof["seconds"] > PROFILE_LIMIT:
                rep["runs"][rid] = {"skipped": "f4 dropped by the declared profile rule"}
                save()
                continue
        text, stats = deck(form, slot, mesh, al, gap)
        wd = ROOT / rep["run_directory"] / rid.replace("|", "_").replace("=", "")
        try:
            z, secs = solve(text, wd)
            rep["runs"][rid] = {"Z_real": z.real, "Z_imag": z.imag, "seconds": secs, **stats}
        except RuntimeError as exc:
            rep["runs"][rid] = {"error": str(exc), **stats}
            rep["errors"].append(f"{rid}: {exc}")
        print(rid, rep["runs"][rid], flush=True)
        evaluate(rep)
        save()
    evaluate(rep)
    rep["outcome"] = "complete"
    save()
    print(json.dumps({k: v for k, v in rep["checks"].items() if k != "production_mesh_error"}, indent=1, default=str))


if __name__ == "__main__":
    main()
