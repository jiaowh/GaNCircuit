"""Generate a planar NMOS from one parameter specification and sweep it in DEVSIM.

The spec (devices/planar-nmos-*.json) controls geometry, doping, contacts and
mesh spacing. Structure and doping are built with DEVSIM's internal 2D mesher,
so a changed parameter always changes the simulated device. Physics is the
upstream simple_physics package (see the spec's "physics" note).

Subcommands, run in the DEVSIM environment described in docs/build.md:
  inspect SPEC          structure/doping report
  sweep SPEC            transfer and output curves
  op SPEC --vg --vd     local 5-point stencil for gm and gds at one bias

Currents are native 2D values in A/cm of out-of-plane width. A point is
recorded only after DEVSIM's Newton solve converges (it raises otherwise).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import time
from pathlib import Path

import devsim as ds
from devsim.python_packages import simple_physics as sp
from devsim.python_packages.model_create import CreateSolution

ROOT = Path(__file__).resolve().parents[1]
DEVICE = "nmos"
UM = 1e-4  # cm per micrometre
CONTACTS = ("gate", "drain", "source", "body")
AIR = 1e-7
# Tighter targets stall in roundoff noise (1e-8..1e-7) from near-zero electron
# densities in the depleted drain junction when the device is off at high Vd.
# Terminal-current conservation is checked independently for every point.
REL_ERROR, ABS_ERROR, MAX_ITER = 1e-6, 1e30, 50
# Observed terminal-current residual is an absolute floor of ~1e-11..2e-10 A/cm,
# independent of current level; currents near KCL_ABS_A_PER_CM are unresolved.
KCL_REL, KCL_ABS_A_PER_CM = 1e-6, 1e-9
MIN_STEP = 1e-4


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_spec(path: Path, mesh_scale: float | None = None) -> dict:
    spec = json.loads(path.read_text(encoding="utf-8"))
    if spec.get("schema") != "planar-nmos-spec/1":
        raise ValueError("unsupported spec schema")
    if spec["temperature_k"] != 300.0:
        raise ValueError("simple_physics constants are 300 K only")
    for group in ("geometry_um", "doping_cm3", "junction_grading_um", "mesh_um"):
        for key, value in spec[group].items():
            if not (isinstance(value, (int, float)) and math.isfinite(value) and value > 0):
                raise ValueError(f"{group}.{key} must be positive and finite")
    if mesh_scale is not None:
        spec["mesh_um"]["scale"] = mesh_scale
    return spec


def layout(spec: dict) -> dict:
    """Derived coordinates in cm; x lateral, y positive into the silicon."""
    g = spec["geometry_um"]
    lsd, L = g["source_drain_length"] * UM, g["gate_length"] * UM
    tox, tpoly = g["oxide_thickness"] * UM, g["poly_thickness"] * UM
    return {"x_left": 0.0, "x_gate_left": lsd, "x_gate_right": lsd + L, "x_right": 2 * lsd + L,
            "x_mid": lsd + L / 2, "y_surface": 0.0, "y_oxide_top": -tox, "y_gate_top": -tox - tpoly,
            "y_junction": g["junction_depth"] * UM, "y_bottom": g["body_depth"] * UM}


def build(spec: dict) -> dict:
    p = layout(spec)
    m = {k: v * UM * spec["mesh_um"]["scale"] for k, v in spec["mesh_um"].items() if k != "scale"}
    mesh = "nmos_mesh"
    ds.create_2d_mesh(mesh=mesh)
    line = lambda d, pos, ps, ns=None: ds.add_2d_mesh_line(mesh=mesh, dir=d, pos=pos, ps=ps, ns=ps if ns is None else ns)
    line("y", p["y_gate_top"] - AIR, m["poly_top"])
    line("y", p["y_gate_top"], m["poly_top"])
    line("y", p["y_oxide_top"], m["oxide"])
    line("y", p["y_surface"], m["surface"], m["oxide"])
    line("y", p["y_junction"], m["junction_bottom"])
    line("y", p["y_bottom"], m["body_bottom"])
    line("y", p["y_bottom"] + AIR, m["body_bottom"])
    line("x", p["x_left"] - AIR, m["outer_edge"])
    line("x", p["x_left"], m["outer_edge"])
    line("x", p["x_gate_left"], m["junction_edge"])
    line("x", p["x_mid"], m["channel_centre"])
    line("x", p["x_gate_right"], m["junction_edge"])
    line("x", p["x_right"], m["outer_edge"])
    line("x", p["x_right"] + AIR, m["outer_edge"])

    ds.add_2d_region(mesh=mesh, material="Air", region="air")
    ds.add_2d_region(mesh=mesh, material="Silicon", region="bulk", xl=p["x_left"], xh=p["x_right"], yl=p["y_bottom"], yh=p["y_surface"])
    ds.add_2d_region(mesh=mesh, material="Oxide", region="oxide", xl=p["x_gate_left"], xh=p["x_gate_right"], yl=p["y_surface"], yh=p["y_oxide_top"])
    ds.add_2d_region(mesh=mesh, material="Silicon", region="gate", xl=p["x_gate_left"], xh=p["x_gate_right"], yl=p["y_oxide_top"], yh=p["y_gate_top"])
    ds.add_2d_contact(mesh=mesh, name="gate", region="gate", yl=p["y_gate_top"], yh=p["y_gate_top"], material="metal")
    ds.add_2d_contact(mesh=mesh, name="body", region="bulk", yl=p["y_bottom"], yh=p["y_bottom"], material="metal")
    ds.add_2d_contact(mesh=mesh, name="source", region="bulk", yl=0.0, yh=0.0, xl=p["x_left"] - AIR, xh=p["x_gate_left"], material="metal")
    ds.add_2d_contact(mesh=mesh, name="drain", region="bulk", yl=0.0, yh=0.0, xl=p["x_gate_right"], xh=p["x_right"] + AIR, material="metal")
    ds.add_2d_interface(mesh=mesh, name="gate_oxide", region0="gate", region1="oxide")
    ds.add_2d_interface(mesh=mesh, name="bulk_oxide", region0="bulk", region1="oxide")
    ds.finalize_mesh(mesh=mesh)
    ds.create_device(mesh=mesh, device=DEVICE)

    d, j = spec["doping_cm3"], spec["junction_grading_um"]
    sx, sy = j["lateral"] * UM, j["vertical"] * UM
    ds.node_model(device=DEVICE, region="gate", name="NetDoping", equation=f"{d['gate_poly_donors']:.17g}")
    ds.node_model(device=DEVICE, region="bulk", name="SourceDonors",
                  equation=f"0.25*{d['source_drain_donors']:.17g}*erfc((x-{p['x_gate_left']:.17g})/{sx:.17g})*erfc((y-{p['y_junction']:.17g})/{sy:.17g})")
    ds.node_model(device=DEVICE, region="bulk", name="DrainDonors",
                  equation=f"0.25*{d['source_drain_donors']:.17g}*erfc(-(x-{p['x_gate_right']:.17g})/{sx:.17g})*erfc((y-{p['y_junction']:.17g})/{sy:.17g})")
    ds.node_model(device=DEVICE, region="bulk", name="NetDoping",
                  equation=f"SourceDonors + DrainDonors - {d['body_acceptors']:.17g}")
    return p


def setup_physics() -> None:
    """Upstream testing/mos_2d.py physics sequence, then equilibrium drift-diffusion."""
    for r in ("gate", "bulk", "oxide"):
        CreateSolution(DEVICE, r, "Potential")
    for r in ("gate", "bulk"):
        sp.SetSiliconParameters(DEVICE, r, 300)
        sp.CreateSiliconPotentialOnly(DEVICE, r)
    sp.SetOxideParameters(DEVICE, "oxide", 300)
    sp.CreateOxidePotentialOnly(DEVICE, "oxide", "log_damp")
    for c in CONTACTS:
        region = ds.get_region_list(device=DEVICE, contact=c)[0]
        sp.CreateSiliconPotentialOnlyContact(DEVICE, region, c)
        ds.set_parameter(device=DEVICE, name=sp.GetContactBiasName(c), value=0.0)
    for i in ("bulk_oxide", "gate_oxide"):
        sp.CreateSiliconOxideInterface(DEVICE, i)
    ds.solve(type="dc", absolute_error=1e-13, relative_error=1e-12, maximum_iterations=50)
    for r in ("gate", "bulk"):
        CreateSolution(DEVICE, r, "Electrons")
        CreateSolution(DEVICE, r, "Holes")
        ds.set_node_values(device=DEVICE, region=r, name="Electrons", init_from="IntrinsicElectrons")
        ds.set_node_values(device=DEVICE, region=r, name="Holes", init_from="IntrinsicHoles")
        sp.CreateSiliconDriftDiffusion(DEVICE, r, "mu_n", "mu_p")
    for c in CONTACTS:
        region = ds.get_region_list(device=DEVICE, contact=c)[0]
        sp.CreateSiliconDriftDiffusionAtContact(DEVICE, region, c)
    ds.solve(type="dc", absolute_error=ABS_ERROR, relative_error=1e-5, maximum_iterations=MAX_ITER)
    ds.solve(type="dc", absolute_error=ABS_ERROR, relative_error=REL_ERROR, maximum_iterations=MAX_ITER)


class Ramp:
    """Move one contact bias with step halving; DEVSIM restores the prior solution on failure."""

    def __init__(self):
        self.halvings = 0

    def to(self, contact: str, target: float, step: float) -> None:
        name = sp.GetContactBiasName(contact)
        current = ds.get_parameter(device=DEVICE, name=name)
        while abs(target - current) > 1e-12:
            nxt = target if abs(target - current) <= step else current + math.copysign(step, target - current)
            ds.set_parameter(device=DEVICE, name=name, value=nxt)
            try:
                ds.solve(type="dc", absolute_error=ABS_ERROR, relative_error=REL_ERROR, maximum_iterations=MAX_ITER)
            except ds.error as exc:
                if "Convergence failure" not in str(exc):
                    raise
                ds.set_parameter(device=DEVICE, name=name, value=current)
                step /= 2
                self.halvings += 1
                if step < MIN_STEP:
                    raise RuntimeError(f"{contact} ramp to {target} V failed below {MIN_STEP} V step") from exc
                continue
            current = nxt


def terminal_currents() -> dict:
    currents = {c: sum(ds.get_contact_current(device=DEVICE, contact=c, equation=e)
                       for e in ("ElectronContinuityEquation", "HoleContinuityEquation")) for c in CONTACTS}
    residual = abs(sum(currents.values()))
    return {"currents_a_per_cm": currents, "kcl_residual_a_per_cm": residual,
            "kcl_pass": residual <= KCL_ABS_A_PER_CM + KCL_REL * max(abs(v) for v in currents.values())}


def record(vg: float, vd: float) -> dict:
    bias = {c: ds.get_parameter(device=DEVICE, name=sp.GetContactBiasName(c)) for c in CONTACTS}
    if abs(bias["gate"] - vg) > 1e-12 or abs(bias["drain"] - vd) > 1e-12 or bias["source"] or bias["body"]:
        raise RuntimeError(f"applied bias {bias} differs from requested ({vg}, {vd})")
    point = {"vg_v": vg, "vd_v": vd, **terminal_currents()}
    # Off-state points at the noise floor are kept but marked unresolved; a
    # conducting point that fails conservation invalidates the run.
    point["resolved"] = point["kcl_pass"]
    if not point["kcl_pass"] and max(abs(v) for v in point["currents_a_per_cm"].values()) > 100 * KCL_ABS_A_PER_CM:
        raise RuntimeError(f"terminal currents not conserved at ({vg}, {vd}): {point['kcl_residual_a_per_cm']:.3g} A/cm")
    return point


def grid(start: float, stop: float, step: float) -> list[float]:
    n = int(round((stop - start) / step))
    return [round(start + i * step, 10) for i in range(n + 1)]


def metadata(spec_path: Path, spec: dict, started: float) -> dict:
    nodes = {r: len(ds.get_node_model_values(device=DEVICE, region=r, name="x")) for r in ("gate", "oxide", "bulk")}
    return {"spec_path": str(spec_path.resolve().relative_to(ROOT)), "spec_sha256": sha256(spec_path),
            "mesh_scale": spec["mesh_um"]["scale"], "runner_sha256": sha256(Path(__file__)),
            "devsim_version": importlib.metadata.version("devsim"),
            "openblas_num_threads": os.environ.get("OPENBLAS_NUM_THREADS"), "nodes": nodes,
            "solver": {"relative_error": REL_ERROR, "absolute_error": ABS_ERROR, "maximum_iterations": MAX_ITER,
                       "convergence": "every recorded point follows a DEVSIM solve that did not raise",
                       "kcl_relative": KCL_REL, "kcl_absolute_a_per_cm": KCL_ABS_A_PER_CM},
            "current_units": "A/cm (2D, per cm of out-of-plane width)", "elapsed_s": time.monotonic() - started}


def region_nodes(region: str, *names: str) -> list[tuple]:
    return list(zip(*(ds.get_node_model_values(device=DEVICE, region=region, name=n) for n in names)))


def sign_changes(points: list[tuple[float, float]]) -> list[float]:
    """Positions where a (position, value) profile changes sign, by linear interpolation."""
    out = []
    for (a, fa), (b, fb) in zip(points, points[1:]):
        if fa == 0 or (fa > 0) != (fb > 0):
            out.append(a if fa == 0 else a + (b - a) * fa / (fa - fb))
    return out


def inspect(spec: dict, p: dict) -> dict:
    bulk = region_nodes("bulk", "x", "y", "NetDoping")
    surface = sorted((x, n) for x, y, n in bulk if abs(y) < 1e-12)
    def column(x0):
        xs = min({x for x, _, _ in bulk}, key=lambda x: abs(x - x0))
        return xs, sorted((y, n) for x, y, n in bulk if x == xs)
    regions = {}
    for r in ("gate", "oxide", "bulk"):
        xy = region_nodes(r, "x", "y")
        regions[r] = {"x_um": [min(x for x, _ in xy) / UM, max(x for x, _ in xy) / UM],
                      "y_um": [min(y for _, y in xy) / UM, max(y for _, y in xy) / UM], "nodes": len(xy)}
    contacts = {}
    for c in CONTACTS:
        region = ds.get_region_list(device=DEVICE, contact=c)[0]
        x = ds.get_node_model_values(device=DEVICE, region=region, name="x")
        y = ds.get_node_model_values(device=DEVICE, region=region, name="y")
        idx = {i for element in ds.get_element_node_list(device=DEVICE, region=region, contact=c) for i in element}
        contacts[c] = {"region": region, "x_um": [min(x[i] for i in idx) / UM, max(x[i] for i in idx) / UM],
                       "y_um": [min(y[i] for i in idx) / UM, max(y[i] for i in idx) / UM], "nodes": len(idx)}
        contacts[c]["net_doping_cm3_range"] = [min(ds.get_node_model_values(device=DEVICE, region=region, name="NetDoping")[i] for i in idx),
                                               max(ds.get_node_model_values(device=DEVICE, region=region, name="NetDoping")[i] for i in idx)]
    sd_x, sd_col = column(p["x_gate_left"] / 2)
    ch_x, ch_col = column(p["x_mid"])
    lateral = [x / UM for x in sign_changes(surface)]
    return {
        "layout_um": {k: v / UM for k, v in p.items()},
        "regions": regions, "contacts": contacts,
        "surface_junctions_x_um": lateral,
        "metallurgical_channel_length_um": lateral[1] - lateral[0] if len(lateral) == 2 else None,
        "gate_overlap_each_side_um": [lateral[0] - p["x_gate_left"] / UM,
                                      p["x_gate_right"] / UM - lateral[1]] if len(lateral) == 2 else None,
        "source_column": {"x_um": sd_x / UM, "junction_depth_um": [y / UM for y in sign_changes(sd_col)],
                          "surface_net_doping_cm3": sd_col[0][1]},
        "channel_column": {"x_um": ch_x / UM, "sign_changes_um": [y / UM for y in sign_changes(ch_col)],
                           "surface_net_doping_cm3": ch_col[0][1]},
        "net_doping_extremes_cm3": {r: [min(v for (v,) in region_nodes(r, "NetDoping")), max(v for (v,) in region_nodes(r, "NetDoping"))]
                                    for r in ("gate", "bulk")},
        "doping_map": {"x_um": [x / UM for x, _, _ in bulk], "y_um": [y / UM for _, y, _ in bulk], "net_doping_cm3": [n for _, _, n in bulk]},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("command", choices=("inspect", "sweep", "op"))
    ap.add_argument("spec", type=Path)
    ap.add_argument("--mesh-scale", type=float, help="Override the spec's mesh scale (recorded)")
    ap.add_argument("--out", type=Path, help="Output JSON (default results/nmos-design/<name>/<command>.json)")
    ap.add_argument("--transfer-vd", type=float, nargs="+", default=[0.05, 1.65, 3.3])
    ap.add_argument("--output-vg", type=float, nargs="+", default=[0.5, 0.75, 1.0, 1.5, 2.0, 3.0])
    ap.add_argument("--step", type=float, default=0.1, help="Sweep step in V")
    ap.add_argument("--vg-min", type=float, default=-0.5)
    ap.add_argument("--vg", type=float)
    ap.add_argument("--vd", type=float)
    ap.add_argument("--delta", type=float, default=0.01)
    args = ap.parse_args()
    started = time.monotonic()
    spec = load_spec(args.spec, args.mesh_scale)
    suffix = "" if spec["mesh_um"]["scale"] == 1.0 else f"-mesh{spec['mesh_um']['scale']:g}"
    out = args.out or ROOT / "results/nmos-design" / spec["name"] / f"{args.command}{suffix}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    report = {"schema": f"planar-nmos-{args.command}/1", "spec": spec, "status": "failed"}
    ramp = Ramp()

    def save():
        report["metadata"] = {**metadata(args.spec, spec, started), "step_halvings": ramp.halvings}
        out.write_text(json.dumps(report, indent=1, allow_nan=False) + "\n", encoding="utf-8")

    p = build(spec)
    if args.command == "inspect":
        report["structure"] = inspect(spec, p)
    setup_physics()
    report["equilibrium"] = terminal_currents()
    vdd = spec["supply_v"]
    try:
        if args.command == "sweep":
            report["transfer"], report["output"] = [], []
            for vd in args.transfer_vd:
                ramp.to("gate", args.vg_min, 0.25)
                ramp.to("drain", vd, 0.25)
                curve = {"vd_v": vd, "points": []}
                report["transfer"].append(curve)
                for vg in grid(args.vg_min, vdd, args.step):
                    ramp.to("gate", vg, args.step)
                    curve["points"].append(record(vg, vd))
                save()
                ramp.to("drain", 0.0, 0.5)
            for vg in args.output_vg:
                ramp.to("gate", vg, 0.25)
                curve = {"vg_v": vg, "points": []}
                report["output"].append(curve)
                for vd in grid(0.0, vdd, args.step):
                    ramp.to("drain", vd, args.step)
                    curve["points"].append(record(vg, vd))
                save()
                ramp.to("drain", 0.0, 0.5)
        elif args.command == "op":
            if args.vg is None or args.vd is None:
                ap.error("op requires --vg and --vd")
            stencil = [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]
            report["stencil"] = {"vg_v": args.vg, "vd_v": args.vd, "delta_v": args.delta, "points": []}
            for i, j in stencil:
                vg, vd = args.vg + i * args.delta, args.vd + j * args.delta
                ramp.to("gate", vg, 0.25)
                ramp.to("drain", vd, 0.25)
                report["stencil"]["points"].append(record(vg, vd))
            pts = report["stencil"]["points"]
            idrain = [pt["currents_a_per_cm"]["drain"] for pt in pts]
            gm = (idrain[2] - idrain[1]) / (2 * args.delta)
            gds = (idrain[4] - idrain[3]) / (2 * args.delta)
            report["small_signal"] = {"id_a_per_cm": idrain[0], "gm_s_per_cm": gm, "gds_s_per_cm": gds,
                                      "intrinsic_gain": gm / gds, "gm_over_id_per_v": gm / idrain[0]}
        report["status"] = "completed"
    except RuntimeError as exc:
        report["reason"] = str(exc)
    save()
    print(json.dumps({"status": report["status"], "out": str(out), "halvings": ramp.halvings,
                      "elapsed_s": report["metadata"]["elapsed_s"], "nodes": report["metadata"]["nodes"],
                      "reason": report.get("reason")}))
    return 0 if report["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
