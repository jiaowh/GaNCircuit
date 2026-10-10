#!/usr/bin/env python3
"""Steady-state board thermal model of the EPC90133 (declared in plans/goal-targets-2026-10-08.md, 10 October 2026).

Cell grid of FACTOR x 1 mil over the board. One node per cell on each of the eight copper planes. In-plane
conductance between neighbouring cells: k_cu t_cu (mean copper fraction of the two cells, all nets) plus the
laminate's in-plane share k_lam t (half of each adjacent dielectric). Between planes: the laminate k_lam A / d, plus
every plated hole's copper barrel (wall 0.787 mil, EPC fab note) k_cu A_barrel / (d + t_cu) at its cell, whatever
its net (filled-via fill ignored). Top and bottom planes lose heat to ambient through h A. Each FET has a junction
node tied to the cells under its pads with 1 / R_thJB (1.5 K/W, EPC2302 datasheet), spread evenly over those cells,
and a case-top node through R_thJC 0.2 K/W; the case top loses heat through h A_top (bare board) or, in the
'spreader' case, through an assumed 5 K/W per FET (EPC's optional heat-spreader, QSG section 7).

Heat: Q1 and Q2 from the switching run's FET loss (split as declared: Q2 = R_ds (1 - D) I_rms^2 + dead-time loss from
the dead-time sweep slope, Q1 the remainder; conduction parts scaled by the digitized datasheet Fig. 9 R_ds(T_J)),
plus the board copper loss map from scripts/epc90133_copper_loss.py --map (scaled by 1 + 0.00393 (T - 20) at its
heat-weighted mean temperature). Iterated until no temperature moves by more than 0.05 K. Board solves use
conjugate gradient (solve_cg); the self-tests use a direct LU.

--selftest runs the declared checks T2 (1D slab) and T3 (via barrel) on synthetic grids. Output for a board:
results/gan/epc90133-thermal-<tag>.json.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import LinearOperator, cg, splu

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

K_CU, K_LAM, T_CU_M = 385.0, 0.4, 2.8 * 25.4e-6
DIEL_MIL = [5.0, 5.0, 7.2, 5.0, 7.2, 5.0, 5.0]  # EPC B5253 stackup, top to bottom
W_PLATE = 0.787 * 25.4e-6
R_JB, R_JC, A_CASE = 1.5, 0.2, 15e-6  # K/W, K/W, m^2 (3 x 5 mm package top)
T_AMB = 25.0
RDS_T = ([0, 25, 50, 75, 100, 125, 150], [0.852, 1.000, 1.162, 1.341, 1.537, 1.771, 2.039])  # Fig. 9, digitized
ALPHA_CU = 0.00393


def build(cf, holes, pitch_m, h, diel_mil, k_lam=K_LAM):
    """Conductance matrix (nodes: plane cells, then extra nodes added by the caller) and the ambient conductances.

    cf: list of 8 arrays (copper area fraction per cell); holes: list of (i, j, drill_m)."""
    nl = len(cf)
    H, W = cf[0].shape
    nc = H * W
    d = [m * 25.4e-6 for m in diel_mil]
    rows, cols, vals = [], [], []

    def add(p, q, g):
        rows.extend([p, q, p, q]); cols.extend([p, q, q, p]); vals.extend([g, g, -g, -g])
    for k in range(nl):
        t_lam = (d[k - 1] / 2 if k > 0 else 0) + (d[k] / 2 if k < nl - 1 else 0)
        base = k * nc
        idx = np.arange(nc).reshape(H, W) + base
        for ax in (0, 1):
            a_ = idx[:-1, :] if ax == 0 else idx[:, :-1]
            b_ = idx[1:, :] if ax == 0 else idx[:, 1:]
            fa = cf[k][:-1, :] if ax == 0 else cf[k][:, :-1]
            fb = cf[k][1:, :] if ax == 0 else cf[k][:, 1:]
            g = K_CU * T_CU_M * (fa + fb) / 2 + k_lam * t_lam
            p, q, g = a_.ravel(), b_.ravel(), g.ravel()
            rows.extend(np.concatenate([p, q, p, q])); cols.extend(np.concatenate([p, q, q, p]))
            vals.extend(np.concatenate([g, g, -g, -g]))
        if k < nl - 1:
            g = k_lam * pitch_m ** 2 / d[k]
            p = np.arange(nc) + base
            q = p + nc
            gv = np.full(nc, g)
            for i, j, dr in holes:
                r = dr / 2
                gv[i * W + j] += K_CU * np.pi * (r ** 2 - max(r - W_PLATE, 0) ** 2) / (d[k] + T_CU_M)
            rows.extend(np.concatenate([p, q, p, q])); cols.extend(np.concatenate([p, q, q, p]))
            vals.extend(np.concatenate([gv, gv, -gv, -gv]))
    amb = np.zeros(nl * nc)
    amb[:nc] += h * pitch_m ** 2
    amb[(nl - 1) * nc:] += h * pitch_m ** 2
    return rows, cols, vals, amb, nc, add


def solve_system(rows, cols, vals, amb, n, power):
    G = sparse.csr_matrix((vals, (rows, cols)), shape=(n, n)) + sparse.diags(np.pad(amb, (0, n - len(amb))))
    lu = splu(G.tocsc())
    return lu, lu.solve(power)


def solve_cg(G, power, x0=None):
    """Board solve: conjugate gradient with a diagonal preconditioner (the direct LU's fill on the 500k-node board
    takes GBs and tens of minutes; on the 0.4 mm grid both agree to 1e-11). Relative residual 1e-10, checked."""
    d = 1 / G.diagonal()
    x, info = cg(G, power, x0=x0, rtol=1e-10, maxiter=100000, M=LinearOperator(G.shape, matvec=lambda v: d * v))
    res = float(np.linalg.norm(G @ x - power) / np.linalg.norm(power))
    if info != 0 or res > 1e-9:
        raise SystemExit(f"CG did not converge (info {info}, residual {res:.1e})")
    return x


def selftest():
    out = {}
    # T2: uniform flux into the top plane of bare laminate, top adiabatic, bottom to ambient through h.
    H = W = 6
    pitch, h, q = 1e-3, 10.0, 500.0
    cf = [np.zeros((H, W)) for _ in range(8)]
    rows, cols, vals, amb, nc, _ = build(cf, [], pitch, h, DIEL_MIL)
    amb[:nc] = 0
    n = 8 * nc
    pw = np.zeros(n)
    pw[:nc] = q * pitch ** 2
    _, T = solve_system(rows, cols, vals, amb, n, pw)
    analytic = q * (sum(m * 25.4e-6 for m in DIEL_MIL) / K_LAM + 1 / h)
    out["T2_slab"] = {"model_K": float(T[:nc].mean()), "analytic_K": analytic,
                      "error": float(T[:nc].mean() / analytic - 1)}
    out["T2_slab"]["pass"] = abs(out["T2_slab"]["error"]) <= 0.01
    # T3: a single cell column, laminate removed (k_lam -> tiny), one via; heat into the top, bottom fixed by large h.
    cf = [np.zeros((1, 1)) for _ in range(8)]
    dr = 0.1981e-3
    rows, cols, vals, amb, nc, _ = build(cf, [(0, 0, dr)], 1e-4, 0.0, DIEL_MIL, k_lam=1e-12)
    amb[-1] = 1e12
    pw = np.zeros(8)
    pw[0] = 1.0
    _, T = solve_system(rows, cols, vals, amb, 8, pw)
    a_b = np.pi * ((dr / 2) ** 2 - (dr / 2 - W_PLATE) ** 2)
    r_an = sum((m * 25.4e-6 + T_CU_M) / (K_CU * a_b) for m in DIEL_MIL)
    out["T3_via"] = {"model_K_per_W": float(T[0]), "analytic_K_per_W": r_an, "error": float(T[0] / r_an - 1)}
    out["T3_via"]["pass"] = abs(out["T3_via"]["error"]) <= 0.01
    return out


def board_inputs(factor, diel_mil):
    import read_epc90133_geometry as rg
    b = rg.load_board()
    cf = []
    for e in rg.LAYERS:
        m = b.grids[e].grid
        Hh, Ww = (m.shape[0] // factor) * factor, (m.shape[1] // factor) * factor
        cf.append(m[:Hh, :Ww].reshape(Hh // factor, factor, Ww // factor, factor).mean(axis=(1, 3)))
    pitch = rg.PITCH * factor
    H, W = cf[0].shape
    holes = []
    for h_ in b.holes:
        if h_.plated:
            i, j = int((h_.y - rg.BOARD[1]) / pitch), int((h_.x - rg.BOARD[0]) / pitch)
            if 0 <= i < H and 0 <= j < W:
                holes.append((i, j, h_.diameter * 1e-3))
    return rg, cf, holes, pitch, rg.geometry_source()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--tag")
    ap.add_argument("--goals", type=Path, help="goals report holding <design>@ramp-Ls50-gear and its dead-time sweep")
    ap.add_argument("--design", default="stock")
    ap.add_argument("--dt-report", type=Path, default=ROOT / "results/gan/epc90133-goals-G.json",
                    help="report with stock's dead-time sweep (slope of FET loss per ns)")
    ap.add_argument("--copper-map", type=Path)
    ap.add_argument("--factor", type=int, default=8)
    ap.add_argument("--h", type=float, nargs="*", default=[10.0])
    ap.add_argument("--k-lam", type=float, nargs="*", default=[K_LAM])
    ap.add_argument("--top-dielectric-mm", type=float, help="V8 + 0.075 mm: first dielectric thickness")
    ap.add_argument("--spreader", action="store_true", help="also run EPC's optional heat-spreader case (5 K/W/FET)")
    ap.add_argument("--single-fet-check", action="store_true", help="T5: Q2 at 1 W alone, nothing else")
    a = ap.parse_args()
    if a.selftest:
        r = selftest()
        print(json.dumps(r, indent=1))
        (ROOT / "results/gan/epc90133-thermal-selftest.json").write_text(json.dumps(r, indent=1) + "\n")
        return 0 if all(v["pass"] for v in r.values()) else 2
    sys.path.insert(0, str(ROOT / "scripts"))
    from assess_epc90133_goals import metrics
    diel = list(DIEL_MIL)
    if a.top_dielectric_mm:
        diel[0] = a.top_dielectric_mm / 0.0254
    rg, cf, holes, pitch, geom = board_inputs(a.factor, diel)
    pm = pitch * 1e-3
    H, W = cf[0].shape
    nc = H * W
    gate = json.loads((ROOT / "results/gan/epc90133-gate-loop.json").read_text(encoding="utf-8"))["terminals"]
    pads = {q: [t["bbox_mm"] for k in (f"{q}.D", f"{q}.S2", f"{q}.S46", f"{q}.G") for t in gate[k]] for q in ("Q1", "Q2")}

    def pad_cells(q):
        cells = set()
        for x0, y0, x1, y1 in pads[q]:
            for i in range(int((y0 - rg.BOARD[1]) / pitch), int(np.ceil((y1 - rg.BOARD[1]) / pitch))):
                for j in range(int((x0 - rg.BOARD[0]) / pitch), int(np.ceil((x1 - rg.BOARD[0]) / pitch))):
                    cells.add(i * W + j)
        return sorted(cells)
    # Loss split (declared): from the design's nominal ramp-Ls50 case.
    rep = json.loads(a.goals.read_text(encoding="utf-8")) if a.goals else None
    if a.single_fet_check:
        split = None
    else:
        c = rep["cases"][f"{a.design}@ramp-Ls50-gear"]
        pl = c["metrics"]["period_loss"]
        dtr = json.loads(a.dt_report.read_text(encoding="utf-8"))["cases"]
        l25 = metrics(dtr["stock@ramp-Ls50-gear-dt2.5"], 48)["fet_loss_W"]
        l10 = metrics(dtr["stock@ramp-Ls50-gear"], 48)["fet_loss_W"]
        dead = (l10 - l25) / 7.5 * 10.0  # W at 10 ns, linear through zero dead time (declared)
        iv, ip = 11.8, 28.2
        msq = (iv ** 2 + iv * ip + ip ** 2) / 3
        q2_cond = pl["q1_rds_on_ohm"] * (1 - 0.25) * msq
        q1_cond = pl["on_time_conduction_W"]
        total = pl["fet_loss_W"]
        split = {"total_W": total, "Q2_conduction_W": q2_cond, "Q2_dead_time_W": dead, "Q1_conduction_W": q1_cond,
                 "Q1_switching_W": total - q2_cond - dead - q1_cond}
    cu = np.load(a.copper_map) if a.copper_map else None
    if cu is not None and int(cu["factor"]) != a.factor:
        raise SystemExit("copper map factor differs")
    rdsf = lambda T: float(np.interp(T, *RDS_T))
    out = {"schema": "epc90133-thermal/1", "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "geometry": geom, "tag": a.tag, "cell_mm": pitch, "dielectric_mil": diel, "loss_split_25C": split,
           "copper_map": str(a.copper_map) if a.copper_map else None, "cases": {}}
    for k_lam in a.k_lam:
        for h in a.h:
            for spreader in ([False, True] if a.spreader else [False]):
                rows, cols, vals, amb, _, add = build(cf, holes, pm, h, diel, k_lam)
                n = 8 * nc + 4  # + junction and case nodes of Q1, Q2
                jn = {"Q1": 8 * nc, "Q2": 8 * nc + 1}
                cn = {"Q1": 8 * nc + 2, "Q2": 8 * nc + 3}
                amb = np.pad(amb, (0, 4))
                for q in ("Q1", "Q2"):
                    cells = pad_cells(q)
                    for c_ in cells:
                        add(jn[q], c_, 1 / R_JB / len(cells))
                    add(jn[q], cn[q], 1 / R_JC)
                    amb[cn[q]] += 1 / 5.0 if spreader else h * A_CASE
                G = sparse.csr_matrix((vals, (rows, cols)), shape=(n, n)) + sparse.diags(amb)
                G = G.tocsr()
                x = None
                cu_vec = np.zeros(n)
                if cu is not None:
                    for k_, e in enumerate(rg.LAYERS):
                        cu_vec[k_ * nc:(k_ + 1) * nc] = cu[e][:H, :W].ravel()
                tj = {"Q1": 25.0, "Q2": 25.0}
                tcu = 25.0
                for it in range(50):
                    pw = np.zeros(n)
                    if split is None:
                        p1, p2 = 0.0, 1.0
                    else:
                        p1 = split["Q1_switching_W"] + split["Q1_conduction_W"] * rdsf(tj["Q1"])
                        p2 = split["Q2_dead_time_W"] + split["Q2_conduction_W"] * rdsf(tj["Q2"])
                    pw[jn["Q1"]], pw[jn["Q2"]] = p1, p2
                    cuf = 1 + ALPHA_CU * (tcu - 20)
                    pw += cu_vec * cuf
                    x = solve_cg(G, pw, x)
                    T = T_AMB + x
                    new = {"Q1": float(T[jn["Q1"]]), "Q2": float(T[jn["Q2"]])}
                    tcu_new = float((T * cu_vec).sum() / cu_vec.sum()) if cu_vec.sum() else 25.0
                    done = max(abs(new[q] - tj[q]) for q in tj) < 0.05 and abs(tcu_new - tcu) < 0.05
                    tj, tcu = new, tcu_new
                    if done:
                        break
                p_in = float(pw.sum())
                p_out = float((amb * (T - T_AMB)).sum())
                key = f"h{h:g}-k{k_lam:g}" + ("-spreader" if spreader else "")
                case = {"h_W_m2K": h, "k_lam": k_lam, "spreader": spreader, "iterations": it + 1,
                        "T_J_C": tj, "T_case_C": {q: float(T[cn[q]]) for q in cn},
                        "board_max_C": float(T[:8 * nc].max()), "copper_mean_C": tcu,
                        "fet_loss_W": {"Q1": p1, "Q2": p2, "total": p1 + p2},
                        "copper_loss_W": float((cu_vec * (1 + ALPHA_CU * (tcu - 20))).sum()),
                        "T1_energy_balance": {"in_W": p_in, "out_W": p_out, "error": p_out / p_in - 1}}
                if split is not None:
                    case["efficiency_fet_plus_copper"] = 240.0 / (240.0 + p1 + p2 + case["copper_loss_W"])
                else:
                    case["theta_JA_Q2_K_per_W"] = tj["Q2"] - T_AMB
                out["cases"][key] = case
                print(a.tag, key, "TJ", {q: round(v, 2) for q, v in tj.items()}, "FET", round(p1 + p2, 4), "Cu",
                      round(case["copper_loss_W"], 4), "balance", f"{case['T1_energy_balance']['error']:.1e}",
                      flush=True)
    if a.tag:
        (ROOT / f"results/gan/epc90133-thermal-{a.tag}.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
