#!/usr/bin/env python3
"""DC copper (conduction) loss of the EPC90133 board in the template's buck operating point.

Written 10 October 2026 after the owner asked why board copper loss was missing: the goals study's loss and
efficiency (S12) are FET-only, so no copper loss had been computed for any board. This adds it. No field solver.

Geometry: the board's rasterized copper (scripts/read_epc90133_geometry.py; an edited board through
EPC90133_GERBER_EXPORT), coarsened to cells of FACTOR x 1 mil (a cell is copper if at least half its pixels are);
nets VIN, SW, GND (probe-named) and VOUT (copper under L1's output pad). Each layer is a sheet of 2.8 mil copper
(EPC's B5253 stackup, every layer 2.80 mil) with sheet resistance rho/t; adjacent cells of the same net and layer
are joined by 1/R_sheet. Plated holes join the layers whose copper touches their rim (the reader's ring test) through
a barrel of wall W_PLATE (EPC fab note 5: at least 0.787 mil; filled vias conduct through the barrel only) over the
copper mid-plane distance. Connector pins (J3, J9; drills >= 0.9 mm) are soldered pins: every layer's net copper
within the pad radius is tied to the pin. Surface-mount pads (FETs, capacitors, L1) tie the net copper under the
pad's contact box. rho = 1.724e-8 ohm m (IACS, 20 C); copper is hotter in operation (+0.393 %/K), reported.

Operating point (plans/goal-targets-2026-10-08.md; QSG buck use: J3 VIN/GND, L1 on board, output at J9): VIN 48 V,
VOUT 12 V, IOUT 20 A, D = 0.25, ripple neglected (DC steps). Two conduction states, each solved as a DC network per
net with terminal currents:
  Q1 on (D): J3 VIN +5 A in, capacitor VIN pads +15 A in, Q1 drain -20 A; Q1 source +20 A to SW, L1 SW pad -20 A;
             L1 VOUT pad +20 A, J9 VOUT -20 A; J9 GND +20 A, J3 GND -5 A, capacitor GND pads -15 A.
  Q2 on (1-D): J3 VIN +5 A, capacitor VIN pads -5 A; Q2 drain +20 A, L1 SW pad -20 A; VOUT as above;
             J9 GND +20 A, J3 GND -5 A, capacitor GND pads +5 A, Q2 source -20 A.
The capacitor pads of each net form one terminal (pads equipotential: an assumption that favours the copper). Loss
= D P(Q1 on) + (1-D) P(Q2 on), per net. Two cell sizes are run for sensitivity (not convergence).
Output: results/gan/epc90133-copper-loss-<tag>.json.
"""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import read_epc90133_geometry as rg  # noqa: E402
from epc90133_power_loop import T_CU, z_mid  # noqa: E402

RHO = 1.724e-8  # ohm m
W_PLATE = 0.787 * 25.4e-6  # m, EPC fab note minimum barrel plating
PIN_MIN_D = 0.9  # mm: holes this large are connector pins
VIN, VOUT, IOUT, L_IND, FSW = 48.0, 12.0, 20.0, 2.2e-6, 250e3
# Inductor ripple (added the same day, before any candidate was run): within each state the inductor current ramps
# between I -/+ dI/2; its mean square is I^2 + dI^2/12. Reported as an upper factor on every term (the J3 input
# current is in fact smooth), beside the DC result.
D_I = (VIN - VOUT) * (VOUT / VIN) / (L_IND * FSW)
RIPPLE = 1 + D_I ** 2 / (12 * IOUT ** 2)
D = VOUT / VIN
I_IN = IOUT * D
G_TIE = 1e8  # S, pad/pin ties (far above the 4 kS sheet conductance)
GATE = ROOT / "results/gan/epc90133-gate-loop.json"
LOOP = ROOT / "results/gan/epc90133-power-loop.json"
# Footprint pads read from the reconstructed board (EPC millimetres): L1 pads and connector pins.
L1_VOUT = (35.99, 15.28)
# L1 lands (10.2 x 6.1 mm), measured as the mask-open copper at each pad (EPC Gerbers): the solder joint is the contact.
L1_SW_BOX, L1_VOUT_BOX = [30.885, 20.275, 41.09, 26.375], [30.885, 12.17, 41.09, 18.375]
J3_VIN = [(x, y) for x in (46.48, 49.02) for y in (39.5, 36.96, 34.42, 31.88)]
J3_GND = [(x, y) for x in (46.48, 49.02) for y in (19.18, 16.64, 14.1, 11.56)]
J3_R = 0.85
J9_VOUT, J9_GND, J9_R = [(31.59, 5.3)], [(39.21, 5.3)], 1.3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="stock")
    ap.add_argument("--factors", nargs="*", type=int, default=[8, 4])
    ap.add_argument("--map", type=Path, help="save the per-cell dissipation (W, state- and ripple-weighted) of the "
                    "last factor as an .npz (thermal model input)")
    a = ap.parse_args()
    t0 = time.time()
    b = rg.load_board()
    roots = {n: r for r, n in b.net_name.items()}
    i, j = b.pixel(*L1_VOUT)
    roots["VOUT"] = b.find(("GTL", int(b.labels["GTL"][i, j])))
    gate = json.loads(GATE.read_text(encoding="utf-8"))["terminals"]
    loop = json.loads(LOOP.read_text(encoding="utf-8"))
    boxes = lambda keys: [("GTL", t["bbox_mm"]) for k in keys for t in gate[k]]
    caps = {n: [("GTL" if c["layer"] == "GTL" else "GBL", p["bbox_mm"]) for g in loop["capacitors"].values()
                for c in g["caps"] for p in c["pads"] if p["net"] == n] for n in ("VIN", "GND")}
    terms = {"VIN": {"J3": ("pins", J3_VIN, J3_R), "CAP": ("pads", caps["VIN"]), "Q1D": ("pads", boxes(["Q1.D"]))},
             "SW": {"Q1S": ("pads", boxes(["Q1.S2", "Q1.S46"])), "Q2D": ("pads", boxes(["Q2.D"])),
                    "L1": ("pads", [("GTL", L1_SW_BOX)])},
             "VOUT": {"L1": ("pads", [("GTL", L1_VOUT_BOX)]), "J9": ("pins", J9_VOUT, J9_R)},
             "GND": {"J9": ("pins", J9_GND, J9_R), "J3": ("pins", J3_GND, J3_R), "CAP": ("pads", caps["GND"]),
                     "Q2S": ("pads", boxes(["Q2.S2", "Q2.S46"]))}}
    states = {"Q1": {"VIN": {"J3": I_IN, "CAP": IOUT - I_IN, "Q1D": -IOUT}, "SW": {"Q1S": IOUT, "L1": -IOUT},
                     "VOUT": {"L1": IOUT, "J9": -IOUT}, "GND": {"J9": IOUT, "J3": -I_IN, "CAP": -(IOUT - I_IN)}},
              "Q2": {"VIN": {"J3": I_IN, "CAP": -I_IN}, "SW": {"Q2D": IOUT, "L1": -IOUT},
                     "VOUT": {"L1": IOUT, "J9": -IOUT}, "GND": {"J9": IOUT, "J3": -I_IN, "CAP": I_IN, "Q2S": -IOUT}}}
    zm = z_mid()
    g_sheet = T_CU * 1e-3 / RHO  # S per square
    out = {"schema": "epc90133-copper-loss/1", "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "geometry": rg.geometry_source(), "tag": a.tag,
           "assumptions": {"rho_ohm_m": RHO, "t_cu_mm": T_CU, "barrel_wall_m": W_PLATE, "VIN": VIN, "VOUT": VOUT,
                           "IOUT": IOUT, "D": D, "ripple_pp_A": D_I, "ripple_factor": RIPPLE,
                           "temperature_C": 20},
           "results": {}}
    for f in a.factors:
        pitch = rg.PITCH * f
        res = {"cell_mm": pitch, "nets": {}}
        heat = {}
        for net, tdef in terms.items():
            root = roots[net]
            cells, index = {}, {}
            n = 0
            for e in rg.LAYERS:
                lab = b.labels[e]
                labs = [int(k) for k in np.unique(lab) if k and b.find((e, int(k))) == root]
                m = np.isin(lab, labs)
                H, W = (m.shape[0] // f) * f, (m.shape[1] // f) * f
                c = m[:H, :W].reshape(H // f, f, W // f, f).mean(axis=(1, 3)) >= 0.5
                idx = -np.ones(c.shape, np.int64)
                k = int(c.sum())
                idx[c] = np.arange(n, n + k)
                cells[e], index[e] = c, idx
                n += k
            rows, cols, vals = [], [], []

            def link(p, q, g):
                rows.extend([p, q, p, q]); cols.extend([p, q, q, p]); vals.extend([g, g, -g, -g])
            for e in rg.LAYERS:
                idx = index[e]
                for sl_a, sl_b in (((slice(None), slice(None, -1)), (slice(None), slice(1, None))),
                                   ((slice(None, -1), slice(None)), (slice(1, None), slice(None)))):
                    pa, pb = idx[sl_a], idx[sl_b]
                    ok = (pa >= 0) & (pb >= 0)
                    p, q = pa[ok], pb[ok]
                    rows.extend(np.concatenate([p, q, p, q])); cols.extend(np.concatenate([p, q, q, p]))
                    vals.extend(np.concatenate([np.full(len(p), g_sheet)] * 2 + [np.full(len(p), -g_sheet)] * 2))

            def cell_at(e, x, y):
                ci, cj = int((y - rg.BOARD[1]) / pitch), int((x - rg.BOARD[0]) / pitch)
                idx = index[e]
                for r in range(0, 4):
                    sub = idx[max(ci - r, 0):ci + r + 1, max(cj - r, 0):cj + r + 1]
                    if (sub >= 0).any():
                        return int(sub[sub >= 0][0])
                return None
            nvia = 0
            for v in b.via_rows:
                if v["d"] >= PIN_MIN_D:
                    continue
                lays = [e for e, lab_ in v["islands"] if b.find((e, lab_)) == root]
                nodes = [(e, cell_at(e, v["x"], v["y"])) for e in lays]
                nodes = [(e, c) for e, c in nodes if c is not None]
                if len(nodes) < 2:
                    continue
                r_out = v["d"] / 2 * 1e-3
                area = np.pi * (r_out ** 2 - max(r_out - W_PLATE, 0) ** 2)
                for (e1, c1), (e2, c2) in zip(nodes, nodes[1:]):
                    dz = abs(zm[e1] - zm[e2]) * 1e-3
                    link(c1, c2, area / (RHO * dz))
                nvia += 1
            tnode = {}
            for tname, spec in tdef.items():
                tn = n + len(tnode)
                tnode[tname] = tn
                ties = set()
                if spec[0] == "pads":
                    for e, (x0, y0, x1, y1) in spec[1]:
                        c = cells[e]
                        i0, i1 = int((y0 - rg.BOARD[1]) / pitch), int(np.ceil((y1 - rg.BOARD[1]) / pitch))
                        j0, j1 = int((x0 - rg.BOARD[0]) / pitch), int(np.ceil((x1 - rg.BOARD[0]) / pitch))
                        sub = index[e][i0:i1, j0:j1]
                        ties |= set(sub[sub >= 0].tolist())
                else:
                    for x, y in spec[1]:
                        for e in rg.LAYERS:
                            ci, cj = int((y - rg.BOARD[1]) / pitch), int((x - rg.BOARD[0]) / pitch)
                            rr = int(np.ceil(spec[2] / pitch))
                            sub = index[e][max(ci - rr, 0):ci + rr + 1, max(cj - rr, 0):cj + rr + 1]
                            ties |= set(sub[sub >= 0].tolist())
                if not ties:
                    raise SystemExit(f"{net}.{tname}: no copper under the terminal at cell {pitch} mm")
                for c in ties:
                    link(c, tn, G_TIE)
            N = n + len(tnode)
            G = sparse.csr_matrix((vals, (rows, cols)), shape=(N, N))
            off = G.tocoo()
            sel = (off.row < off.col) & (off.data < 0)
            er, ec, eg = off.row[sel], off.col[sel], -off.data[sel]
            # Floating islands of the net (not reachable from a terminal) are pinned by a tiny leak to ground.
            G = G + sparse.identity(N, format="csr") * 1e-9
            ref = tnode[next(iter(tdef))]
            keep = np.array([k for k in range(N) if k != ref])
            Gr = G[keep][:, keep].tocsc()
            net_res = {"cells": n, "vias_used": nvia, "terminal_ties": {}, "loss_W": {}}
            for st, cur in states.items():
                rhs = np.zeros(N)
                for tname, ival in cur[net].items():
                    rhs[tnode[tname]] += ival
                v_ = np.zeros(N)
                v_[keep] = spsolve(Gr, rhs[keep])
                p = float(sum(ival * v_[tnode[t]] for t, ival in cur[net].items()))
                net_res["loss_W"][st] = p
                if a.map:
                    pe = eg * (v_[er] - v_[ec]) ** 2 * (D if st == "Q1" else 1 - D) * RIPPLE / 2
                    node_p = np.bincount(er, pe, N) + np.bincount(ec, pe, N)
                    for e in rg.LAYERS:
                        idx = index[e]
                        hm = heat.setdefault(e, np.zeros(idx.shape))
                        hm[idx >= 0] += node_p[idx[idx >= 0]]
            net_res["loss_W"]["average"] = D * net_res["loss_W"]["Q1"] + (1 - D) * net_res["loss_W"]["Q2"]
            res["nets"][net] = net_res
            print(f"cell {pitch:.4f} mm {net:4s} cells {n:7d} vias {nvia:4d} loss Q1 {net_res['loss_W']['Q1']:.4f} "
                  f"Q2 {net_res['loss_W']['Q2']:.4f} avg {net_res['loss_W']['average']:.4f} W  ({time.time() - t0:.0f} s)",
                  flush=True)
        res["total_W"] = sum(v["loss_W"]["average"] for v in res["nets"].values())
        res["total_with_ripple_W"] = res["total_W"] * RIPPLE
        out["results"][str(f)] = res
        if a.map:
            a.map.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(a.map, factor=f, pitch_mm=pitch, **heat)
            print(f"map {a.map}: {sum(h.sum() for h in heat.values()):.4f} W", flush=True)
        print(f"cell {pitch:.4f} mm total {res['total_W']:.4f} W, with ripple {res['total_with_ripple_W']:.4f} W", flush=True)
    path = ROOT / f"results/gan/epc90133-copper-loss-{a.tag}.json"
    path.write_text(json.dumps(out, indent=1, default=str) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
