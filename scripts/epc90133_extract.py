#!/usr/bin/env python3
"""Exploratory FastHenry extraction of the EPC90133 power-loop network (G3, step 2).

Owner review, 29 September 2026: extract with explicit geometry assumptions, keep return paths
and mutual coupling in the network, and use the circuit's sensitivity to those assumptions to
decide where qualification is worthwhile. This is exploratory: the via/plane-pair check failed
its mesh criterion, and plane holes, via arrays and multi-layer vias are not qualified. Two
meshes are a sensitivity check, not proof of convergence.

Specification (29 September 2026, before the first board run):

Geometry. Copper of the nets VIN, SW and GND from the B5253 Gerbers (1-mil raster, nets and via
layers from scripts/epc90133_power_loop.py) inside one window for every variant, x 15.0-33.0 mm,
y 22.0-37.5 mm. Other nets are omitted (they carry no loop current; their eddy currents are
neglected). Islands that are only via pads are omitted. Copper 2.8 mil at the stackup's
mid-planes; conductivity 5.8e7 S/m; 100 MHz (skin depth 6.6 um).

Mesh. A uniform node grid aligned to the FET pin rows (x = FET centre + k s, y = Q2 centre + k s).
A node exists where the grid point is on meshed copper. Neighbouring nodes are joined by a
segment of width s when the raster along the whole segment is one copper island, so clearances
and slots stay open. Segments: thickness 2.8 mil, nwinc 1, nhinc n, rh 2.
    m1: s = 0.425 mm (half the pin pitch), n = 3;   m2: s = 0.2125 mm, n = 5.
Nodes not connected to any port terminal are dropped.

Vias. Each plated via of VIN/SW/GND in the window becomes vertical segments between consecutive
layers on which it is functional (within the variant's layers): square section of side 0.847 d
(the side whose equivalent radius, 0.5902 w, equals the drill radius; the plating is at least
20 um and its outer radius is not given), nwinc = nhinc = 3, rw = rh = 2. Explicit alternative
representations (not bounds):
    mid  (baseline) segment between copper mid-planes; each end tied to the nearest grid node
         of the same island on that layer;
    gap  segment only across the dielectric, ends at the copper surfaces, tied to the same nodes
         (the via inside the copper thickness is ideal);
    pad  as mid, but each end tied to every same-island grid node within 0.25 mm of the via centre.

Terminals and ports (epc90133-power-loop.json "ports"). A terminal's nodes are the grid nodes on
its contact's island inside the contact box grown by s/2, tied into one node (equipotential
contact; a FET terminal ties its pins). Branch ports run from each terminal to its net's
reference terminal (VIN: Q1.D, SW: Q2.D, GND: Q2.S). Not modelled: the EPC2302 package and
internal metallization, capacitor ESL/ESR, gate loops, the bus entry and the output inductor.

Variants.
    A  top layer and mid-layer 1 copper, vias only between them; Ci branches only
    I  all eight layers; Ci branches only (extra copper, same capacitors)
    B  all eight layers; Ci and Cm branches

Solution. FastHenry 3.0.1, -p diag (reproduced the default preconditioner on the via check).
Ports are split into parallel jobs with -x; each job returns admittance columns, which are
assembled and inverted to give the branch impedance matrix Z = R + jwL.

Reported checks (per case, fixed here): every port's terminals are connected through the mesh
before solving; the assembled L is symmetric within 1% of its largest entry and positive
definite. Diagnostic summary alongside the network (not a replacement for it): the loop
inductance and capacitor current shares with all capacitors as ideal shorts, Q2 shorted and
the port at Q1 (drain to source).

Run history (29 September 2026). First A-m1-mid attempt: FastHenry rejected the via node names
(they must start with "n"); no result. Second: capacitor terminal boxes grown by s/2 overlapped
between neighbouring Ci pads, so shared nodes tied the Ci1-Ci5 VIN terminals together and the
admittance matrix was singular; no result was used. A node now belongs to at most one terminal
(checked), and a box grows only when it holds no node. FastHenry lists -x columns last to first;
they are now sorted by column number. Neither change alters the geometry, meshes or ports above.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from epc90133_power_loop import T_CU, via_layers, z_mid
from fasthenry_known_answer import FH_BIN, SIGMA_CU_PER_MM, skin_depth, wsl_path
from read_epc90133_geometry import LAYERS, PITCH, load_board

LOOP = ROOT / "results/gan/epc90133-power-loop.json"
WINDOW = (15.0, 22.0, 33.0, 37.5)
FREQ = 1e8
MESHES = {"m1": (0.425, 3), "m2": (0.2125, 5)}
VIA_W = 0.847  # side of the square via section / drill diameter
PAD_R = 0.25  # mm, "pad" junction radius
VARIANTS = {"A": {"layers": ("GTL", "G1"), "caps": ("Ci",)},
            "I": {"layers": LAYERS, "caps": ("Ci",)},
            "B": {"layers": LAYERS, "caps": ("Ci", "Cm")}}
JUNCTIONS = ("mid", "gap", "pad")
POWER = ("VIN", "SW", "GND")


class UF:
    def __init__(self):
        self.p = {}

    def find(self, a):
        p = self.p
        while p.setdefault(a, a) != a:
            p[a] = p[p[a]]
            a = p[a]
        return a

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def build(b, loop, variant, mesh, junction, per_layer):
    s, n = MESHES[mesh]
    layers = VARIANTS[variant]["layers"]
    z = z_mid()
    xc = loop["fets"]["Q1"]["centre_mm"][0]
    yc = loop["fets"]["Q2"]["centre_mm"][1]
    xs = xc + s * np.arange(math.ceil((WINDOW[0] - xc) / s), math.floor((WINDOW[2] - xc) / s) + 1)
    ys = yc + s * np.arange(math.ceil((WINDOW[1] - yc) / s), math.floor((WINDOW[3] - yc) / s) + 1)
    rows = np.round(ys / PITCH).astype(int)
    cols = np.round(xs / PITCH).astype(int)
    pad_only = {(e, lab) for v, lay in zip(b.via_rows, per_layer) for e, lab in v["islands"] if lay[e] == "pad only"}

    nodes, segs, equivs = {}, [], []  # nodes: name -> (x, y, z, layer, island)
    grid = {}
    for e in layers:
        lab = b.labels[e]
        net_of_label = {}
        L = lab[np.ix_(rows, cols)]
        for i in range(len(ys)):
            for j in range(len(xs)):
                l = int(L[i, j])
                if not l or (e, l) in pad_only:
                    continue
                if l not in net_of_label:
                    net_of_label[l] = b.net_name.get(b.find((e, l)), "other")
                if net_of_label[l] not in POWER:
                    continue
                name = f"n{e}_{i}_{j}".lower()
                nodes[name] = (float(xs[j]), float(ys[i]), z[e], e, l)
                grid[(e, i, j)] = name
        for (ee, i, j), name in list(grid.items()):
            if ee != e:
                continue
            l = nodes[name][4]
            if (e, i, j + 1) in grid and nodes[grid[(e, i, j + 1)]][4] == l and \
                    np.all(lab[rows[i], cols[j]:cols[j + 1] + 1] == l):
                segs.append((name, grid[(e, i, j + 1)], f"w={s:.6g} h={T_CU:.6g} nhinc={n} rh=2"))
            if (e, i + 1, j) in grid and nodes[grid[(e, i + 1, j)]][4] == l and \
                    np.all(lab[rows[i]:rows[i + 1] + 1, cols[j]] == l):
                segs.append((name, grid[(e, i + 1, j)], f"w={s:.6g} h={T_CU:.6g} nhinc={n} rh=2"))

    def grid_nodes_near(e, x, y, island, radius):
        i0, j0 = int(round((y - ys[0]) / s)), int(round((x - xs[0]) / s))
        k = int(math.ceil(radius / s)) + 1
        out = []
        for i in range(i0 - k, i0 + k + 1):
            for j in range(j0 - k, j0 + k + 1):
                nm = grid.get((e, i, j))
                if nm and nodes[nm][4] == island:
                    out.append((math.hypot(nodes[nm][0] - x, nodes[nm][1] - y), nm))
        return sorted(out)

    # Vias
    via_rows = [(k, v) for k, v in enumerate(b.via_rows)
                if WINDOW[0] <= v["x"] <= WINDOW[2] and WINDOW[1] <= v["y"] <= WINDOW[3]]
    via_stats = {"vias": 0, "segments": 0, "unattached_ends": 0}
    for k, v in via_rows:
        net = b.net_of(v["layers"][0], v["x"], v["y"]) if v["layers"] else "none"
        if net not in POWER:
            continue
        island = dict(v["islands"])
        func = [e for e in layers if per_layer[k][e] == "functional"]
        if len(func) < 2:
            continue
        ends = {}
        for e in func:
            near = grid_nodes_near(e, v["x"], v["y"], island[e], max(PAD_R, 1.5 * s))
            if not near:
                via_stats["unattached_ends"] += 1
                continue
            ends[e] = [nm for d, nm in near if d <= PAD_R] or [near[0][1]] if junction == "pad" else [near[0][1]]
        func = [e for e in func if e in ends]
        if len(func) < 2:
            continue
        via_stats["vias"] += 1
        w = VIA_W * v["d"]
        for e1, e2 in zip(func, func[1:]):
            top, bot = f"nv{k}_{e1}_d".lower(), f"nv{k}_{e2}_u".lower()
            z1, z2 = z[e1], z[e2]
            if junction == "gap":
                z1, z2 = z1 - T_CU / 2, z2 + T_CU / 2
            nodes[top] = (v["x"], v["y"], z1, e1, island[e1])
            nodes[bot] = (v["x"], v["y"], z2, e2, island[e2])
            segs.append((top, bot, f"w={w:.6g} h={w:.6g} wx=1 wy=0 wz=0 nwinc=3 nhinc=3 rw=2 rh=2"))
            equivs.append([top] + ends[e1])
            equivs.append([bot] + ends[e2])
            via_stats["segments"] += 1

    # Terminals
    caps = [c for k in VARIANTS[variant]["caps"] for c in loop["capacitors"][k]["caps"]]
    terms = {}
    for q in ("Q1", "Q2"):
        for fn in ("D", "S"):
            pins = [p for p in loop["fets"][q]["pins"].values() if p["function"] == fn]
            terms[f"{q}.{fn}"] = [("GTL", p["bbox_mm"], p["centre_mm"]) for p in pins]
    for c in caps:
        for p in c["pads"]:
            terms[f"{c['ref']}.{p['net']}"] = [(c["layer"], p["bbox_mm"], p["centre_mm"])]
    # A terminal takes the grid nodes inside its contact box; only a contact with none inside takes
    # the nodes within s/2 of the box. No node may belong to two terminals (the first run's boxes grown
    # by s/2 overlapped between neighbouring capacitor pads and shorted their terminals together).
    term_nodes, term_missing = {}, []
    claimed = {}

    def inside(e, island, x0, y0, x1, y1, g):
        return [nm for (ee, gi, gj), nm in grid.items() if ee == e and nodes[nm][4] == island
                and x0 - g <= xs[gj] <= x1 + g and y0 - g <= ys[gi] <= y1 + g]

    for t, contacts in terms.items():
        members = []
        for e, (x0, y0, x1, y1), (cx, cy) in contacts:
            if e not in layers:
                continue
            i, j = b.pixel(cx, cy)
            island = int(b.labels[e][i, j])
            got = inside(e, island, x0, y0, x1, y1, 0.0) or inside(e, island, x0, y0, x1, y1, s / 2)
            if not got:
                term_missing.append(f"{t} contact at ({cx:.2f}, {cy:.2f})")
            members += got
        for nm in members:
            if nm in claimed and claimed[nm] != t:
                raise RuntimeError(f"grid node {nm} lies in the contacts of both {claimed[nm]} and {t}")
            claimed[nm] = t
        if members:
            term_nodes[t] = members
            equivs.append(list(members))

    scheme = loop["ports"]["scheme"]
    ports = []
    for net, sc in scheme.items():
        for br in sc["branches"]:
            if br in term_nodes and sc["reference"] in term_nodes:
                ports.append((br.replace(".", "_").lower(), br, sc["reference"]))

    # Connectivity: drop components without terminals; every port must be connected.
    uf = UF()
    for a, c, _ in segs:
        uf.union(a, c)
    for eq in equivs:
        for m in eq[1:]:
            uf.union(eq[0], m)
    term_roots = {uf.find(ns[0]) for ns in term_nodes.values()}
    keep = {nm for nm in nodes if uf.find(nm) in term_roots}
    dropped = len(nodes) - len(keep)
    nodes = {k: v for k, v in nodes.items() if k in keep}
    segs = [sg for sg in segs if sg[0] in keep]
    equivs = [[m for m in eq if m in keep] for eq in equivs]
    equivs = [eq for eq in equivs if len(eq) > 1]
    connected = {name: uf.find(term_nodes[br][0]) == uf.find(term_nodes[ref][0]) for name, br, ref in ports}

    lines = [f"* EPC90133 power loop, variant {variant}, mesh {mesh}, via junction {junction}; "
             "generated by scripts/epc90133_extract.py", ".units mm", f".default sigma={SIGMA_CU_PER_MM:g} nwinc=1"]
    lines += [f"{nm} x={x:.6f} y={y:.6f} z={zz:.6f}" for nm, (x, y, zz, _, _) in nodes.items()]
    lines += [f"E{k} {a} {c} {geo}" for k, (a, c, geo) in enumerate(segs, 1)]
    lines += [".equiv " + " ".join(eq) for eq in equivs]
    lines += [f".external {term_nodes[br][0]} {term_nodes[ref][0]} {name}" for name, br, ref in ports]
    lines += [f".freq fmin={FREQ:g} fmax={FREQ:g} ndec=1", ".end", ""]
    fil = sum(n if "nhinc=%d" % n in geo and "nwinc=3" not in geo else 9 for _, _, geo in segs)
    stats = {"pitch_mm": s, "nhinc": n, "grid": [len(xs), len(ys)], "nodes": len(nodes), "segments": len(segs),
             "filaments_before_refine": fil, "nodes_dropped_unconnected": dropped, "via": via_stats,
             "terminals": {t: len(v) for t, v in term_nodes.items()}, "terminal_contacts_without_nodes": term_missing,
             "ports": [p[0] for p in ports]}
    return "\n".join(lines), ports, connected, stats


def parse_matrix_file(text):
    """Rows (port names) and the matrix blocks of a Zc.mat file: impedance (n x n) or admittance columns."""
    rows = {int(m.group(1)): m.group(2) for m in re.finditer(r"Row (\d+):.*port name: (\S+)", text)}
    cols = {int(m.group(1)): m.group(2) for m in re.finditer(r"Col (\d+): port name: (\S+)", text)}
    cols = [cols[k] for k in sorted(cols)]  # FastHenry lists rows and columns last to first
    m = re.search(r"(Impedance|ADMITTANCE) matrix for frequency = (\S+) (\d+) x (\d+)\n", text)
    kind, nr, nc = m.group(1), int(m.group(3)), int(m.group(4))
    body = text[m.end():].split()
    vals = []
    k = 0
    while len(vals) < nr * nc:
        re_, im_ = float(body[k]), float(body[k + 1].rstrip("j"))
        vals.append(complex(re_, im_))
        k += 2
    return [rows[i] for i in sorted(rows)], cols, kind, np.array(vals).reshape(nr, nc)


def run_case(deck, ports, workdir, jobs):
    workdir.mkdir(parents=True, exist_ok=False)
    (workdir / "case.inp").write_text(deck, encoding="ascii")
    names = [p[0] for p in ports]
    chunks = [names[k::jobs] for k in range(jobs) if names[k::jobs]]

    def one(k, chunk):
        opts = " ".join(f"-x {c}" for c in chunk)
        cmd = ["wsl", "-e", "bash", "-lc", f"cd '{wsl_path(workdir)}' && '{wsl_path(FH_BIN)}' case.inp -p diag {opts} -S _j{k}"]
        t0 = time.time()
        p = subprocess.run(cmd, capture_output=True, text=True, check=False)
        (workdir / f"stdout_j{k}.log").write_text(p.stdout or "", encoding="utf-8")
        (workdir / f"stderr_j{k}.log").write_text(p.stderr or "", encoding="utf-8")
        f = workdir / f"Zc_j{k}.mat"
        if p.returncode != 0 or not f.is_file() or "matrix for frequency" not in f.read_text(errors="replace"):
            raise RuntimeError(f"FastHenry job {k} failed in {workdir}: {(p.stderr or p.stdout)[-800:]}")
        return time.time() - t0, parse_matrix_file(f.read_text(errors="replace"))

    with ThreadPoolExecutor(max_workers=len(chunks)) as pool:
        results = list(pool.map(lambda a: one(*a), enumerate(chunks)))
    order = results[0][1][0]
    Y = np.zeros((len(order), len(order)), complex)
    for _, (rows, cols, kind, mat) in results:
        if kind != "ADMITTANCE" or rows != order:
            raise RuntimeError("unexpected FastHenry output layout")
        for c, name in enumerate(cols):
            Y[:, order.index(name)] = mat[:, c]
    stdout = (workdir / "stdout_j0.log").read_text(encoding="utf-8")
    fil = re.search(r"filaments after multipole refine:\s*(\d+)", stdout)
    return order, Y, [r[0] for r in results], int(fil.group(1)) if fil else None


def loop_summary(order, Z, ports):
    """Loop impedance at Q1 with Q2 shorted and every capacitor an ideal short; capacitor current shares."""
    br = {name: (b_, ref) for name, b_, ref in ports}
    nodes = sorted({x for name in order for x in br[name]} | {"Q1.D", "Q1.S", "Q2.D", "Q2.S"})
    caps = sorted({t.rsplit(".", 1)[0] for t in nodes if t.startswith("C")})
    ground = "Q2.S"
    nidx = {n_: k for k, n_ in enumerate(x for x in nodes if x != ground)}
    nb, nn = len(order), len(nidx)
    shorts = [("Q2.D", "Q2.S")] + [(f"{c}.VIN", f"{c}.GND") for c in caps]
    N = nn + nb + len(shorts)
    A = np.zeros((N, N), complex)
    rhs = np.zeros(N, complex)

    def stamp_current(node, k, sign):  # branch/short current k leaves node (sign +1) or enters it
        if node != ground:
            A[nidx[node], k] += sign

    for k, name in enumerate(order):  # V(term) - V(ref) - sum Z I = 0; I flows term -> ref
        t, r = br[name]
        row = nn + k
        if t != ground:
            A[row, nidx[t]] += 1
        if r != ground:
            A[row, nidx[r]] -= 1
        A[row, nn:nn + nb] -= Z[k]
        stamp_current(t, nn + k, 1)
        stamp_current(r, nn + k, -1)
    for k, (a, c) in enumerate(shorts):
        row = nn + nb + k
        if a != ground:
            A[row, nidx[a]] += 1
        if c != ground:
            A[row, nidx[c]] -= 1
        stamp_current(a, row, 1)
        stamp_current(c, row, -1)
    # 1 A injected at Q1.D and taken out at Q1.S: it flows through the VIN branches, the capacitors
    # (VIN to GND), the GND branches, the Q2 short and the SW branch.
    rhs[nidx["Q1.D"]] += 1
    rhs[nidx["Q1.S"]] -= 1
    x = np.linalg.solve(A, rhs)
    v = lambda n_: 0 if n_ == ground else x[nidx[n_]]
    zl = v("Q1.D") - v("Q1.S")
    shares = {c: float(x[nn + nb + 1 + k].real) for k, c in enumerate(caps)}
    return {"L_loop_nH": float(zl.imag / (2 * math.pi * FREQ) * 1e9), "R_loop_mohm": float(zl.real * 1e3),
            "capacitor_current_share": shares}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cases", nargs="+", help="variant:mesh:junction, e.g. A:m1:mid")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--build-only", action="store_true", help="write decks and report mesh statistics only")
    ap.add_argument("--outdir", type=Path, default=ROOT / "results/gan/epc90133-extraction")
    args = ap.parse_args()
    loop = json.loads(LOOP.read_text(encoding="utf-8"))
    b = load_board()
    per_layer = via_layers(b)
    run_root = ROOT / "runs" / ("epc90133-extract-" + uuid.uuid4().hex[:12])
    args.outdir.mkdir(parents=True, exist_ok=True)
    for case in args.cases:
        variant, mesh, junction = case.split(":")
        deck, ports, connected, stats = build(b, loop, variant, mesh, junction, per_layer)
        print(case, json.dumps({k: stats[k] for k in ("grid", "nodes", "segments", "filaments_before_refine", "via",
                                                       "nodes_dropped_unconnected", "terminal_contacts_without_nodes")}))
        report = {"schema": "epc90133-extraction/1", "case": {"variant": variant, "mesh": mesh, "junction": junction},
                  "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  "power_loop_sha256": hashlib.sha256(LOOP.read_bytes()).hexdigest(),
                  "fasthenry_binary_sha256": hashlib.sha256(FH_BIN.read_bytes()).hexdigest(),
                  "window_mm": WINDOW, "frequency_Hz": FREQ, "skin_depth_um": skin_depth(FREQ) * 1e6,
                  "mesh_stats": stats, "ports": [{"name": p[0], "terminal": p[1], "reference": p[2]} for p in ports],
                  "checks": {"all_ports_connected": all(connected.values())}}
        if not all(connected.values()):
            report["unconnected_ports"] = [k for k, ok in connected.items() if not ok]
        wd = run_root / case.replace(":", "_")
        if args.build_only or not all(connected.values()):
            wd.mkdir(parents=True, exist_ok=True)
            (wd / "case.inp").write_text(deck, encoding="ascii")
            print("  deck:", wd.relative_to(ROOT), "connected:", all(connected.values()))
            continue
        # Memory guard: B-m1 used 1.59 GB per job for 62k filaments (about 26 kB each); allow 30 kB.
        need = 30e3 * stats["filaments_before_refine"]
        info = subprocess.run(["wsl", "-e", "bash", "-c", "grep MemAvailable /proc/meminfo"], capture_output=True, text=True).stdout
        avail = float(info.split()[1]) * 1024 if info.strip() else None
        jobs = args.jobs if avail is None else max(1, min(args.jobs, int(0.85 * avail // need)))
        report["parallel_jobs"] = {"requested": args.jobs, "used": jobs, "estimated_bytes_per_job": need, "available_bytes": avail}
        t0 = time.time()
        order, Y, job_s, filaments = run_case(deck, ports, wd, jobs)
        Z = np.linalg.inv(Y)
        w = 2 * math.pi * FREQ
        L = Z.imag / w
        asym = float(np.abs(L - L.T).max() / np.abs(L).max())
        Ls = (L + L.T) / 2
        eig = np.linalg.eigvalsh(Ls)
        report["checks"].update({"L_symmetric_within_1pct": asym <= 0.01, "L_positive_definite": bool(eig.min() > 0)})
        report.update({
            "evidence_directory": str(wd.relative_to(ROOT)), "wall_time_s": time.time() - t0, "job_times_s": job_s,
            "filaments_after_refine": filaments, "port_order": order,
            "L_H": Ls.tolist(), "R_ohm": ((Z.real + Z.real.T) / 2).tolist(),
            "Z_raw_real": Z.real.tolist(), "Z_raw_imag": Z.imag.tolist(),
            "L_asymmetry_rel": asym, "L_min_eigenvalue_H": float(eig.min()),
            "summary": loop_summary(order, (Z + Z.T) / 2, ports),
        })
        report["outcome"] = "complete" if all(report["checks"].values()) else "check failed"
        out = args.outdir / f"{variant}-{mesh}-{junction}.json"
        out.write_text(json.dumps(report, indent=1) + "\n")
        print(f"  {report['outcome']}; {report['wall_time_s']:.0f} s; filaments {filaments}; "
              f"L_loop {report['summary']['L_loop_nH']:.4f} nH; asym {asym:.2e}; -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
