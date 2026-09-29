"""Extract transistor figures of merit from a planar_nmos.py sweep and plot the curves.

Pure Python for the metrics; plots are written only when matplotlib is
available. Currents stay in A/cm (2D) and are also reported in uA/um
(1 A/cm = 100 uA/um). Derivatives are finite differences on the sweep grid.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

UA_PER_UM = 100.0          # uA/um per A/cm
RESOLUTION_A_PER_CM = 1e-9  # below this, terminal currents are not resolved (see planar_nmos.py)


def interp(xs, ys, x):
    for (x0, y0), (x1, y1) in zip(zip(xs, ys), zip(xs[1:], ys[1:])):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    raise ValueError(f"{x} outside [{xs[0]}, {xs[-1]}]")


def central(xs, ys):
    """Central differences at interior points: (x_i, dy/dx)."""
    return [(xs[i], (ys[i + 1] - ys[i - 1]) / (xs[i + 1] - xs[i - 1])) for i in range(1, len(xs) - 1)]


def curve(points, x_key):
    pts = sorted(points, key=lambda p: p[x_key])
    return [p[x_key] for p in pts], [p["currents_a_per_cm"]["drain"] for p in pts]


def crossing(xs, ys, level):
    """First x where log10(y) crosses log10(level) (y increasing)."""
    for (x0, y0), (x1, y1) in zip(zip(xs, ys), zip(xs[1:], ys[1:])):
        if y0 > 0 and y1 > 0 and y0 < level <= y1:
            a, b = math.log10(y0), math.log10(y1)
            return x0 + (x1 - x0) * (math.log10(level) - a) / (b - a)
    return None


def analyze(sweep: dict) -> dict:
    vdd = sweep["spec"]["supply_v"]
    L_um = sweep["spec"]["geometry_um"]["gate_length"]
    icc = 1e-7 / L_um * 1e4  # constant-current criterion 100 nA * W/L, in A/cm
    transfer = {c["vd_v"]: curve(c["points"], "vg_v") for c in sweep["transfer"]}
    output = {c["vg_v"]: curve(c["points"], "vd_v") for c in sweep["output"]}

    per_vd = {}
    for vd, (vg, idr) in transfer.items():
        gm = central(vg, idr)
        vg_pk, gm_pk = max(gm, key=lambda t: t[1])
        # steepest subthreshold slope between the resolution floor and Icc/10
        ss = [(vg[i + 1] - vg[i]) / math.log10(idr[i + 1] / idr[i]) * 1e3
              for i in range(len(vg) - 1)
              if 10 * RESOLUTION_A_PER_CM < idr[i] < idr[i + 1] < icc / 10]
        per_vd[vd] = {"vt_constant_current_v": crossing(vg, idr, icc),
                      "subthreshold_slope_mv_per_dec": min(ss) if ss else None,
                      "gm_peak_s_per_cm": gm_pk, "vg_at_gm_peak_v": vg_pk,
                      "vt_linear_extrapolation_v": vg_pk - interp(vg, idr, vg_pk) / gm_pk - vd / 2}
    vd_lo, vd_hi = min(transfer), max(transfer)
    vg_hi, id_hi = transfer[vd_hi]
    ioff = interp(vg_hi, id_hi, 0.0)
    ion = interp(vg_hi, id_hi, vdd)
    vt_lo, vt_hi = per_vd[vd_lo]["vt_constant_current_v"], per_vd[vd_hi]["vt_constant_current_v"]

    vd_mid = vdd / 2
    mid = {}
    if vd_mid in transfer:
        vg_m, gm_m = zip(*central(*transfer[vd_mid]))
        for vg, (vds, idr) in output.items():
            gds = central(vds, idr)
            gds_mid = interp([v for v, _ in gds], [g for _, g in gds], vd_mid)
            id_mid = interp(vds, idr, vd_mid)
            gm_here = interp(vg_m, gm_m, vg)
            mid[vg] = {"vov_v": vg - per_vd[vd_lo]["vt_linear_extrapolation_v"], "id_a_per_cm": id_mid,
                       "gm_s_per_cm": gm_here, "gds_s_per_cm": gds_mid, "intrinsic_gain": gm_here / gds_mid,
                       "gm_over_id_per_v": gm_here / id_mid, "early_voltage_v": id_mid / gds_mid,
                       # max CS gain if the load drops (VDD - vd_mid) at this current: gm*RD = (gm/Id)*(VDD - Vout)
                       "gm_rd_at_mid_supply": gm_here / id_mid * (vdd - vd_mid)}
    return {
        "schema": "planar-nmos-analysis/1", "supply_v": vdd,
        "constant_current_criterion_a_per_cm": icc,
        "transfer": {str(k): v for k, v in per_vd.items()},
        "vt_linear_v": per_vd[vd_lo]["vt_linear_extrapolation_v"],
        "dibl_mv_per_v": (vt_lo - vt_hi) / (vd_hi - vd_lo) * 1e3 if vt_lo and vt_hi else None,
        "ion_a_per_cm": ion, "ion_ua_per_um": ion * UA_PER_UM,
        "ioff_a_per_cm": ioff, "ioff_resolved": ioff > RESOLUTION_A_PER_CM,
        "ion_over_ioff": ion / ioff,
        "mid_supply_small_signal": {str(k): v for k, v in mid.items()},
        "method": "finite differences on the sweep grid; gm from the Vd=VDD/2 transfer curve, gds from output curves interpolated to VDD/2",
    }


def plot(sweep: dict, analysis: dict, path: Path, structure: dict | None) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    panels = 5 if structure else 4
    fig, ax = plt.subplots(1, panels, figsize=(4.2 * panels, 3.8), constrained_layout=True)
    for c in sweep["transfer"]:
        vg, idr = curve(c["points"], "vg_v")
        ax[0].semilogy(vg, [max(i, 1e-13) * UA_PER_UM for i in idr], marker=".", label=f"Vd = {c['vd_v']:g} V")
        ax[1].plot(vg, [i * UA_PER_UM for i in idr], marker=".", label=f"Vd = {c['vd_v']:g} V")
    ax[0].axhline(RESOLUTION_A_PER_CM * UA_PER_UM, color="grey", ls=":", lw=1, label="resolution floor")
    ax[0].set(xlabel="Vg (V)", ylabel="Id (uA/um)", title="Transfer (log)")
    ax[1].set(xlabel="Vg (V)", ylabel="Id (uA/um)", title="Transfer (linear)")
    for c in sweep["output"]:
        vd, idr = curve(c["points"], "vd_v")
        ax[2].plot(vd, [i * UA_PER_UM for i in idr], label=f"Vg = {c['vg_v']:g} V")
    ax[2].set(xlabel="Vd (V)", ylabel="Id (uA/um)", title="Output")
    mid = analysis["mid_supply_small_signal"]
    vg = [float(k) for k in mid]
    ax[3].semilogy(vg, [m["intrinsic_gain"] for m in mid.values()], "o-", label="gm/gds")
    ax[3].semilogy(vg, [m["gm_rd_at_mid_supply"] for m in mid.values()], "s--", label="gm*RD (Vout = VDD/2)")
    ax[3].set(xlabel="Vg (V)", title=f"Gain terms at Vd = {analysis['supply_v'] / 2:g} V")
    for a in ax[:4]:
        a.grid(True, which="both", alpha=0.3)
        a.legend(fontsize=7)
    if structure:
        m = structure["doping_map"]
        signed = [math.copysign(math.log10(max(abs(n), 1.0)), n) for n in m["net_doping_cm3"]]
        sc = ax[4].tricontourf(m["x_um"], m["y_um"], signed, levels=30, cmap="coolwarm")
        ax[4].invert_yaxis()
        ax[4].set(xlabel="x (um)", ylabel="depth y (um)", title="Net doping, sign*log10|N| (cm^-3)")
        fig.colorbar(sc, ax=ax[4])
    fig.suptitle(f"{sweep['spec']['name']}: L = {sweep['spec']['geometry_um']['gate_length']} um, "
                 f"tox = {sweep['spec']['geometry_um']['oxide_thickness'] * 1e3:g} nm, "
                 f"NA = {sweep['spec']['doping_cm3']['body_acceptors']:.0e} cm^-3, mesh scale {sweep['metadata']['mesh_scale']:g}")
    fig.savefig(path, dpi=130)
    return True


def amplifier(ops: list[dict], target_id_a: float) -> dict:
    """Size a resistively loaded common-source stage from op stencils (finest mesh last).

    Vout is the stencil drain bias; width scales the 2D current to target_id_a and
    RD = (VDD - Vout) / Id. The gain is width-independent: gm*RD = (gm/Id)(VDD - Vout).
    """
    finest = ops[-1]
    vdd, s = finest["spec"]["supply_v"], finest["small_signal"]
    vg, vout = finest["stencil"]["vg_v"], finest["stencil"]["vd_v"]
    width_cm = target_id_a / s["id_a_per_cm"]
    gm, gds = s["gm_s_per_cm"] * width_cm, s["gds_s_per_cm"] * width_cm
    rd = (vdd - vout) / target_id_a
    history = [{"mesh_scale": o["metadata"]["mesh_scale"], "bulk_nodes": o["metadata"]["nodes"]["bulk"], **o["small_signal"]} for o in ops]
    change = lambda k: [abs(b[k] / a[k] - 1) for a, b in zip(history, history[1:])]
    return {
        "schema": "planar-nmos-amplifier-point/1", "topology": "common-source, resistive drain load RD to VDD, source and body grounded",
        "supply_v": vdd, "vgs_q_v": vg, "vout_q_v": vout, "target_id_a": target_id_a,
        "device_width_um": width_cm * 1e4, "rd_ohm": rd,
        "gm_s": gm, "gds_s": gds, "gm_rd": gm * rd, "intrinsic_gain": gm / gds,
        "small_signal_gain_v_per_v": -gm / (gds + 1 / rd), "supply_power_w": vdd * target_id_a,
        "mesh_history": history,
        "adjacent_mesh_relative_change": {k: change(k) for k in ("id_a_per_cm", "gm_over_id_per_v", "intrinsic_gain")},
        "scope": "DC small-signal estimate from device-simulator derivatives at one bias; no compact model, circuit simulation, or dynamic behavior yet",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("sweep", type=Path, nargs="?")
    ap.add_argument("--structure", type=Path, help="inspect JSON for the doping map panel")
    ap.add_argument("--op", type=Path, nargs="+", help="op stencil JSONs, coarse to fine: size an amplifier instead")
    ap.add_argument("--target-id", type=float, default=100e-6, help="quiescent drain current in A for --op")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    if args.op:
        result = amplifier([json.loads(p.read_text(encoding="utf-8")) for p in args.op], args.target_id)
        result["sources"] = [str(p) for p in args.op]
        (args.out or args.op[-1].with_name("amplifier-point.json")).write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=1))
        return 0
    sweep = json.loads(args.sweep.read_text(encoding="utf-8"))
    if sweep.get("status") != "completed":
        raise SystemExit(f"sweep status is {sweep.get('status')}: {sweep.get('reason')}")
    analysis = analyze(sweep)
    analysis["source"] = {"sweep": str(args.sweep), "spec_sha256": sweep["metadata"]["spec_sha256"],
                          "mesh_scale": sweep["metadata"]["mesh_scale"]}
    stem = args.sweep.with_name(args.sweep.stem.replace("sweep", "analysis"))
    structure = json.loads(args.structure.read_text(encoding="utf-8"))["structure"] if args.structure else None
    analysis["plot"] = str(stem.with_suffix(".png")) if plot(sweep, analysis, stem.with_suffix(".png"), structure) else None
    stem.with_suffix(".json").write_text(json.dumps(analysis, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in analysis.items() if k not in ("transfer",)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
