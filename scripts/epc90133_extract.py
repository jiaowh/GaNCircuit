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

Variant G (30 September 2026, specification before its first run; after test 6 in docs/build.md). B's
copper and capacitors plus the gate-drive loop, with the terminals and port scheme of
results/gan/epc90133-gate-loop.json (scripts/epc90133_gate_loop.py): each FET's source split into pin 2
and pins 4+6, the gate pins, the four gate-resistor pad pairs and the driver balls (UGH, UGL, LGH, LGL,
PHASE C1+D4 tied, GND). Added nets: the gate nets VGu and VGl and the driver output nets VGuH, VGuL,
VGlH, VGlL (identified by the islands under those terminals). Window x 14.0-33.0 mm (U80 lies at
x 14.9-16.1). The gate traces are about 0.15 mm wide and the balls 0.4 mm apart, so the top layer uses a
fine grid of s/4 inside the box G_FINE (x 14.4-18.8, y 24.2-32.8 mm, snapped outwards to coarse lines):
nodes every s/4, segments of width s/4 between neighbours inside the closed box; coarse segments that
lie entirely inside the closed box are dropped, and coarse segments reaching its edge end on the shared
edge nodes. Other layers stay coarse. The mesh check is the existing one (every port connected) plus
every G terminal having nodes. Not modelled: the resistor bodies and the driver (lumped in LTspice),
the driver supply loops (C80, C81), the FET package interior (the die source joins pins 2, 4 and 6
ideally in the bench). Diagnostic added for G: with 1 A round the power loop (as for the loop inductance,
Q2 and capacitors shorted), the voltage induced between each driver return (U80.PH, U80.GND) and its FET's
source pins tied (Q1.S2+S46, Q2.S2+S46) gives the board's common-source inductance of each FET.

Variant G run 1 (30 September 2026) stopped at FastHenry's input stage: it truncates lines of roughly
1000 characters, and the fine-meshed terminals' .equiv lines were longer. Such lines are now split into
several .equiv lines sharing their first node (electrically identical; shorter lines, and so the A/B/I
decks, are unchanged).

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
            "B": {"layers": LAYERS, "caps": ("Ci", "Cm")},
            "G": {"layers": LAYERS, "caps": ("Ci", "Cm"), "gate": True}}
GATE_LOOP = ROOT / "results/gan/epc90133-gate-loop.json"
G_WINDOW = (14.0, 22.0, 33.0, 37.5)
G_FINE = (14.4, 24.2, 18.8, 32.8)
FINE_DIV = 4
GATE_NETS = ("VGu", "VGl", "VGuH", "VGuL", "VGlH", "VGlL")
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


def build(b, loop, variant, mesh, junction, per_layer, gate=None):
    """FastHenry deck for one case. Grid nodes are keyed by fine indices (I, J) = FINE_DIV x coarse index;
    without a fine box only coarse points exist, which reproduces the uniform grid of tests 1-4."""
    s, n = MESHES[mesh]
    spec = VARIANTS[variant]
    layers = spec["layers"]
    is_g = bool(spec.get("gate"))
    window = G_WINDOW if is_g else WINDOW
    z = z_mid()
    f = s / FINE_DIV
    xc = loop["fets"]["Q1"]["centre_mm"][0]
    yc = loop["fets"]["Q2"]["centre_mm"][1]
    I0, I1 = FINE_DIV * math.ceil((window[0] - xc) / s), FINE_DIV * math.floor((window[2] - xc) / s)
    J0, J1 = FINE_DIV * math.ceil((window[1] - yc) / s), FINE_DIV * math.floor((window[3] - yc) / s)
    X = lambda I: xc + I * f
    Y = lambda J: yc + J * f
    if is_g:
        box = (FINE_DIV * math.floor((G_FINE[0] - xc) / s), FINE_DIV * math.floor((G_FINE[1] - yc) / s),
               FINE_DIV * math.ceil((G_FINE[2] - xc) / s), FINE_DIV * math.ceil((G_FINE[3] - yc) / s))
    else:
        box = None
    fine_layers = ("GTL",) if is_g else ()

    def in_box(I, J):
        return box is not None and box[0] <= I <= box[2] and box[1] <= J <= box[3]

    pad_only = {(e, lab) for v, lay in zip(b.via_rows, per_layer) for e, lab in v["islands"] if lay[e] == "pad only"}
    allowed_roots = set()
    if is_g:
        for t, cs in gate["terminals"].items():
            for c in cs:
                if c["layer"] in layers:
                    i, j = b.pixel(*c["centre_mm"])
                    lab = int(b.labels[c["layer"]][i, j])
                    if lab and b.net_name.get(b.find((c["layer"], lab)), "other") not in POWER:
                        allowed_roots.add(b.find((c["layer"], lab)))

    nodes, segs, equivs = {}, [], []  # nodes: name -> (x, y, z, layer, island)
    grid = {}
    for e in layers:
        lab = b.labels[e]
        keep_label = {}
        pts = [(I, J) for J in range(J0, J1 + 1, FINE_DIV) for I in range(I0, I1 + 1, FINE_DIV)]
        if e in fine_layers:
            pts += [(I, J) for J in range(max(J0, box[1]), min(J1, box[3]) + 1) for I in range(max(I0, box[0]), min(I1, box[2]) + 1)
                    if I % FINE_DIV or J % FINE_DIV]
        for I, J in pts:
            r, c = b.pixel(X(I), Y(J))
            l = int(lab[r, c])
            if not l or (e, l) in pad_only:
                continue
            if l not in keep_label:
                root = b.find((e, l))
                keep_label[l] = b.net_name.get(root, "other") in POWER or root in allowed_roots
            if not keep_label[l]:
                continue
            name = f"n{e}_{I - I0}_{J - J0}".lower()
            nodes[name] = (float(X(I)), float(Y(J)), z[e], e, l)
            grid[(e, I, J)] = name

        def connect(k1, k2, width, hinc):
            if k2 not in grid:
                return
            a_, b_ = grid[k1], grid[k2]
            l = nodes[a_][4]
            if nodes[b_][4] != l:
                return
            r1, c1 = b.pixel(nodes[a_][0], nodes[a_][1])
            r2, c2 = b.pixel(nodes[b_][0], nodes[b_][1])
            if np.all(lab[min(r1, r2):max(r1, r2) + 1, min(c1, c2):max(c1, c2) + 1] == l):
                segs.append((a_, b_, f"w={width:.6g} h={T_CU:.6g} nhinc={hinc} rh=2"))

        for (ee, I, J) in list(grid):
            if ee != e:
                continue
            fine_here = e in fine_layers
            if I % FINE_DIV == 0 and J % FINE_DIV == 0:
                for dI, dJ in ((FINE_DIV, 0), (0, FINE_DIV)):
                    if fine_here and in_box(I, J) and in_box(I + dI, J + dJ):
                        continue  # inside the closed fine box the fine segments replace it
                    connect((e, I, J), (e, I + dI, J + dJ), s, n)
            if fine_here and in_box(I, J):
                for dI, dJ in ((1, 0), (0, 1)):
                    if in_box(I + dI, J + dJ):
                        connect((e, I, J), (e, I + dI, J + dJ), f, n)

    from scipy.spatial import cKDTree
    layer_nodes = {e: [(nm, v) for nm, v in nodes.items() if v[3] == e] for e in layers}
    trees = {e: cKDTree(np.array([[v[0], v[1]] for _, v in ln])) if ln else None for e, ln in layer_nodes.items()}

    def grid_nodes_near(e, x, y, island, radius):
        if trees[e] is None:
            return []
        out = []
        for k in trees[e].query_ball_point([x, y], radius + 1e-9):
            nm, v = layer_nodes[e][k]
            if v[4] == island:
                out.append((math.hypot(v[0] - x, v[1] - y), nm))
        return sorted(out)

    # Vias
    via_rows = [(k, v) for k, v in enumerate(b.via_rows)
                if window[0] <= v["x"] <= window[2] and window[1] <= v["y"] <= window[3]]
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
    if is_g:
        terms = {t: [(c["layer"], c["bbox_mm"], c["centre_mm"]) for c in cs] for t, cs in gate["terminals"].items()}
        scheme = gate["scheme"]
    else:
        caps = [c for k in spec["caps"] for c in loop["capacitors"][k]["caps"]]
        terms = {}
        for q in ("Q1", "Q2"):
            for fn in ("D", "S"):
                pins = [p for p in loop["fets"][q]["pins"].values() if p["function"] == fn]
                terms[f"{q}.{fn}"] = [("GTL", p["bbox_mm"], p["centre_mm"]) for p in pins]
        for c in caps:
            for p in c["pads"]:
                terms[f"{c['ref']}.{p['net']}"] = [(c["layer"], p["bbox_mm"], p["centre_mm"])]
        scheme = loop["ports"]["scheme"]
    # A terminal takes the grid nodes inside its contact box; only a contact with none inside takes
    # the nodes within half a local pitch of the box. No node may belong to two terminals (the first run's
    # boxes grown by s/2 overlapped between neighbouring capacitor pads and shorted their terminals together).
    term_nodes, term_missing = {}, []
    claimed = {}

    def inside(e, island, x0, y0, x1, y1, g):
        return [nm for (ee, gI, gJ), nm in grid.items() if ee == e and nodes[nm][4] == island
                and x0 - g <= X(gI) <= x1 + g and y0 - g <= Y(gJ) <= y1 + g]

    for t, contacts in terms.items():
        members = []
        for e, (x0, y0, x1, y1), (cx, cy) in contacts:
            if e not in layers:
                continue
            i, j = b.pixel(cx, cy)
            island = int(b.labels[e][i, j])
            half = (f if (e in fine_layers and in_box(round((cx - xc) / f), round((cy - yc) / f))) else s) / 2
            got = inside(e, island, x0, y0, x1, y1, 0.0) or inside(e, island, x0, y0, x1, y1, half)
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

    ports = []
    for net, sc in scheme.items():
        for br in sc["branches"]:
            if br in term_nodes and sc["reference"] in term_nodes:
                ports.append((br.replace(".", "_").lower(), br, sc["reference"]))

    # Connectivity: drop components without terminals; every port must be connected.
    uf = UF()
    for a_, c_, _ in segs:
        uf.union(a_, c_)
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
    expected = {br for sc in scheme.values() for br in sc["branches"]}
    missing_ports = sorted(expected - {p[1] for p in ports}) if is_g else []

    lines = [f"* EPC90133 {'power and gate-drive loops' if is_g else 'power loop'}, variant {variant}, mesh {mesh}, "
             f"via junction {junction}; generated by scripts/epc90133_extract.py", ".units mm",
             f".default sigma={SIGMA_CU_PER_MM:g} nwinc=1"]
    lines += [f"{nm} x={x:.6f} y={y:.6f} z={zz:.6f}" for nm, (x, y, zz, _, _) in nodes.items()]
    lines += [f"E{k} {a_} {c_} {geo}" for k, (a_, c_, geo) in enumerate(segs, 1)]
    for eq in equivs:  # FastHenry truncates long lines (G run 1): split, every chunk sharing the first node
        if len(".equiv " + " ".join(eq)) <= 900:
            lines.append(".equiv " + " ".join(eq))
        else:
            lines += [".equiv " + " ".join([eq[0]] + eq[k:k + 40]) for k in range(1, len(eq), 40)]
    lines += [f".external {term_nodes[br][0]} {term_nodes[ref][0]} {name}" for name, br, ref in ports]
    lines += [f".freq fmin={FREQ:g} fmax={FREQ:g} ndec=1", ".end", ""]
    fil = sum(n if "nhinc=%d" % n in geo and "nwinc=3" not in geo else 9 for _, _, geo in segs)
    stats = {"pitch_mm": s, "fine_pitch_mm": f if is_g else None, "fine_box_index": box, "nhinc": n,
             "grid": [(I1 - I0) // FINE_DIV + 1, (J1 - J0) // FINE_DIV + 1], "nodes": len(nodes), "segments": len(segs),
             "filaments_before_refine": fil, "nodes_dropped_unconnected": dropped, "via": via_stats,
             "terminals": {t: len(v) for t, v in term_nodes.items()}, "terminal_contacts_without_nodes": term_missing,
             "ports": [p[0] for p in ports], "scheme_branches_without_port": missing_ports}
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


def g_summary(order, Z, ports):
    """Variant G diagnostics: power-loop inductance at Q1 and the board common-source inductance of each FET.

    Only the VIN/SW/GND branches carry the power-loop current; gate-net branches are left out (they carry
    none). Q2's drain-source, every capacitor, Q1's source pins (S2 to S46) and Q2's source pins are shorted
    (the die joins them); 1 A enters at Q1.D and leaves at Q1.S46. The common-source inductance of a FET
    is the imaginary part of the voltage between its driver return and its source, over omega, per ampere
    of loop current: L_cs(Q1) from U80.PH to Q1.S46, L_cs(Q2) from U80.GND to Q2.S46.
    """
    br = {name: (b_, ref) for name, b_, ref in ports}
    power = [k for k, name in enumerate(order) if not br[name][0].startswith(("R8", "U80.U", "U80.L"))
             and not br[name][1].startswith(("Q1.G", "Q2.G", "R8"))]
    names = [order[k] for k in power]
    Zp = Z[np.ix_(power, power)]
    nodes = sorted({x for name in names for x in br[name]} | {"Q1.D", "Q1.S46", "Q2.D", "Q2.S46"})
    caps = sorted({t.rsplit(".", 1)[0] for t in nodes if t.startswith("C")})
    ground = "Q2.S46"
    nidx = {n_: k for k, n_ in enumerate(x for x in nodes if x != ground)}
    nb, nn = len(names), len(nidx)
    shorts = [("Q2.D", "Q2.S46"), ("Q1.S2", "Q1.S46"), ("Q2.S2", "Q2.S46")] + [(f"{c}.VIN", f"{c}.GND") for c in caps]
    N = nn + nb + len(shorts)
    A = np.zeros((N, N), complex)
    rhs = np.zeros(N, complex)

    def stamp(node, k, sign):
        if node != ground:
            A[nidx[node], k] += sign

    for k, name in enumerate(names):
        t, r = br[name]
        row = nn + k
        if t != ground:
            A[row, nidx[t]] += 1
        if r != ground:
            A[row, nidx[r]] -= 1
        A[row, nn:nn + nb] -= Zp[k]
        stamp(t, nn + k, 1)
        stamp(r, nn + k, -1)
    for k, (a, c) in enumerate(shorts):
        row = nn + nb + k
        if a != ground:
            A[row, nidx[a]] += 1
        if c != ground:
            A[row, nidx[c]] -= 1
        stamp(a, row, 1)
        stamp(c, row, -1)
    rhs[nidx["Q1.D"]] += 1
    rhs[nidx["Q1.S46"]] -= 1
    x = np.linalg.solve(A, rhs)
    v = lambda n_: 0 if n_ == ground else x[nidx[n_]]
    w = 2 * math.pi * FREQ
    zl = v("Q1.D") - v("Q1.S46")
    out = {"L_loop_nH": float(zl.imag / w * 1e9), "R_loop_mohm": float(zl.real * 1e3),
           "source_pin_current_share": {
               "Q1.S2": float(x[nn + nb + 1].real), "Q2.S2": float(x[nn + nb + 2].real)}}
    for q, drv in (("Q1", "U80.PH"), ("Q2", "U80.GND")):
        if drv in nidx or drv == ground:
            zc = v(drv) - v(f"{q}.S46")
            out[f"L_cs_{q}_pH"] = float(zc.imag / w * 1e12)
            out[f"R_cs_{q}_mohm"] = float(zc.real * 1e3)
    out["definition"] = g_summary.__doc__.strip().splitlines()[0]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cases", nargs="+", help="variant:mesh:junction, e.g. A:m1:mid")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--build-only", action="store_true", help="write decks and report mesh statistics only")
    ap.add_argument("--outdir", type=Path, default=ROOT / "results/gan/epc90133-extraction")
    args = ap.parse_args()
    loop = json.loads(LOOP.read_text(encoding="utf-8"))
    gate = json.loads(GATE_LOOP.read_text(encoding="utf-8")) if GATE_LOOP.is_file() else None
    b = load_board()
    per_layer = via_layers(b)
    run_root = ROOT / "runs" / ("epc90133-extract-" + uuid.uuid4().hex[:12])
    args.outdir.mkdir(parents=True, exist_ok=True)
    for case in args.cases:
        variant, mesh, junction = case.split(":")
        is_g = bool(VARIANTS[variant].get("gate"))
        if is_g and (gate is None or gate.get("outcome") != "pass"):
            raise SystemExit("variant G needs a passing results/gan/epc90133-gate-loop.json")
        deck, ports, connected, stats = build(b, loop, variant, mesh, junction, per_layer, gate)
        print(case, json.dumps({k: stats[k] for k in ("grid", "nodes", "segments", "filaments_before_refine", "via",
                                                       "nodes_dropped_unconnected", "terminal_contacts_without_nodes")}))
        report = {"schema": "epc90133-extraction/1", "case": {"variant": variant, "mesh": mesh, "junction": junction},
                  "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  "power_loop_sha256": hashlib.sha256(LOOP.read_bytes()).hexdigest(),
                  **({"gate_loop_sha256": hashlib.sha256(GATE_LOOP.read_bytes()).hexdigest()} if is_g else {}),
                  "fasthenry_binary_sha256": hashlib.sha256(FH_BIN.read_bytes()).hexdigest(),
                  "window_mm": G_WINDOW if is_g else WINDOW, "frequency_Hz": FREQ, "skin_depth_um": skin_depth(FREQ) * 1e6,
                  "mesh_stats": stats, "ports": [{"name": p[0], "terminal": p[1], "reference": p[2]} for p in ports],
                  "checks": {"all_ports_connected": all(connected.values())}}
        if is_g:
            report["checks"]["every_g_terminal_has_nodes"] = not stats["terminal_contacts_without_nodes"] \
                and not stats["scheme_branches_without_port"]
        if not all(connected.values()):
            report["unconnected_ports"] = [k for k, ok in connected.items() if not ok]
        wd = run_root / case.replace(":", "_")
        if args.build_only or not all(report["checks"].values()):
            wd.mkdir(parents=True, exist_ok=True)
            (wd / "case.inp").write_text(deck, encoding="ascii")
            print("  deck:", wd.relative_to(ROOT), "checks:", report["checks"])
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
            "summary": (g_summary if is_g else loop_summary)(order, (Z + Z.T) / 2, ports),
        })
        report["outcome"] = "complete" if all(report["checks"].values()) else "check failed"
        out = args.outdir / f"{variant}-{mesh}-{junction}.json"
        out.write_text(json.dumps(report, indent=1) + "\n")
        print(f"  {report['outcome']}; {report['wall_time_s']:.0f} s; filaments {filaments}; "
              f"L_loop {report['summary']['L_loop_nH']:.4f} nH; asym {asym:.2e}; -> {out.relative_to(ROOT)}")
        if is_g:
            print("  common-source:", {k: round(v_, 2) for k, v_ in report["summary"].items() if k.startswith(("L_cs", "R_cs"))})


if __name__ == "__main__":
    main()
