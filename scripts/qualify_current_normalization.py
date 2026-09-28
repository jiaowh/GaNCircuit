#!/usr/bin/env python3
"""Qualify the 2-D contact-current convention with a uniform resistor.

The fixture uses the pinned DEVSIM resistor equations.  Coordinates are cm,
the simulated depth is the DEVSIM 2-D convention of one cm, and the contact
current is therefore expected to be J [A/cm^2] times the contact width [cm].
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
import argparse
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEVSIM_ROOT = ROOT / "devices" / "devsim-upstream"
OUT = ROOT / "results" / "device-reference" / "current-normalization.json"
PIN = "43b41ca845184c47e22b72d144db7e7db8509377"

LENGTH_CM = 1.0e-3
WIDTHS_CM = (1.0e-4, 2.0e-4)
BIAS_V = 0.1
NET_DOPING_CM3 = 1.0e16
ELECTRON_MOBILITY_CM2_VS = 400.0
Q_C = 1.6e-19
REL_TOL = 2.0e-3
ABS_TOL_A_PER_CM = 1.0e-12


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify_case(case: dict) -> str:
    """Classify measured mismatch separately from solver uncertainty."""
    solver = case.get("solver", {})
    if not solver.get("initial_converged") or not solver.get("carrier_converged"):
        return "unresolved"
    observed = case.get("observed", {})
    values = (observed.get("left_electron_current_a_per_cm"), observed.get("right_electron_current_a_per_cm"), observed.get("absolute_error_a_per_cm"), observed.get("contact_balance_a_per_cm"))
    if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in values):
        return "fail"
    expected = case.get("analytic", {}).get("contact_current_a_per_cm")
    if not isinstance(expected, (int, float)) or not math.isfinite(expected):
        return "fail"
    left, right = values[:2]
    if abs(left-expected) > ABS_TOL_A_PER_CM + REL_TOL * abs(expected) or abs(left+right) > ABS_TOL_A_PER_CM + REL_TOL * abs(expected):
        return "fail"
    return "pass"


def run_case(devsim, test_common, width_cm: float, suffix: str) -> dict:
    device, region = f"normalization_device_{suffix}", f"uniform_silicon_{suffix}"
    mesh = f"normalization_mesh_{suffix}"
    devsim.create_2d_mesh(mesh=mesh)
    boundary_bloat = 1.0e-7 * LENGTH_CM
    for pos, spacing in ((-boundary_bloat, boundary_bloat), (0.0, LENGTH_CM / 10.0), (LENGTH_CM, LENGTH_CM / 10.0), (LENGTH_CM + boundary_bloat, boundary_bloat)):
        devsim.add_2d_mesh_line(mesh=mesh, dir="x", pos=pos, ps=spacing)
    devsim.add_2d_mesh_line(mesh=mesh, dir="y", pos=0.0, ps=width_cm / 2.0)
    devsim.add_2d_mesh_line(mesh=mesh, dir="y", pos=width_cm, ps=width_cm / 2.0)
    devsim.add_2d_region(mesh=mesh, material="Si", region=region, xl=0.0, xh=LENGTH_CM)
    devsim.add_2d_region(mesh=mesh, material="Si", region=f"left_air_{suffix}", xl=-boundary_bloat, xh=0.0)
    devsim.add_2d_region(mesh=mesh, material="Si", region=f"right_air_{suffix}", xl=LENGTH_CM, xh=LENGTH_CM + boundary_bloat)
    devsim.add_2d_contact(mesh=mesh, name="left", material="metal", region=region, xl=0.0, xh=0.0, yl=0.0, yh=width_cm, bloat=1e-10)
    devsim.add_2d_contact(mesh=mesh, name="right", material="metal", region=region, xl=LENGTH_CM, xh=LENGTH_CM, yl=0.0, yh=width_cm, bloat=1e-10)
    devsim.finalize_mesh(mesh=mesh)
    devsim.create_device(mesh=mesh, device=device)
    test_common.SetupResistorConstants(device, region)
    test_common.SetupInitialResistorSystem(device, region, NET_DOPING_CM3)
    for contact, bias in (("left", BIAS_V), ("right", 0.0)):
        test_common.SetupInitialResistorContact(device, contact)
        devsim.set_parameter(device=device, name=contact + "bias", value=bias)
    initial = devsim.solve(type="dc", absolute_error=1.0, relative_error=1e-10, maximum_iterations=30, info=True)
    test_common.SetupCarrierResistorSystem(device, region)
    for contact in ("left", "right"):
        test_common.SetupCarrierResistorContact(device, contact)
    solved = devsim.solve(type="dc", absolute_error=1.0, relative_error=1e-10, maximum_iterations=30, info=True)
    left_current = float(devsim.get_contact_current(device=device, contact="left", equation="ElectronContinuityEquation"))
    right_current = float(devsim.get_contact_current(device=device, contact="right", equation="ElectronContinuityEquation"))
    expected_density = Q_C * NET_DOPING_CM3 * ELECTRON_MOBILITY_CM2_VS * BIAS_V / LENGTH_CM
    expected_current = expected_density * width_cm
    error = abs(left_current - expected_current)
    balance_error = abs(left_current + right_current)
    relative_error = error / max(abs(expected_current), ABS_TOL_A_PER_CM)
    return {
        "solver": {"initial_converged": bool(initial.get("converged")), "carrier_converged": bool(solved.get("converged")), "initial_iterations": len(initial.get("iterations", [])), "carrier_iterations": len(solved.get("iterations", []))},
        "geometry": {"length_cm": LENGTH_CM, "contact_width_cm": width_cm, "out_of_plane_depth_cm": 1.0, "side_regions": "mesh-only silicon scaffolding outside the resistor; no equations or contact currents are assigned"},
        "inputs": {"bias_v": BIAS_V, "net_doping_cm3": NET_DOPING_CM3, "electron_mobility_cm2_v_s": ELECTRON_MOBILITY_CM2_VS, "electron_charge_c": Q_C},
        "analytic": {"current_density_a_per_cm2": expected_density, "contact_current_a_per_cm": expected_current, "formula": "q_C * n_cm^-3 * mu_cm2_per_V_s * (bias_V / length_cm) * contact_width_cm"},
        "observed": {"left_electron_current_a_per_cm": left_current, "right_electron_current_a_per_cm": right_current, "absolute_error_a_per_cm": error, "relative_error": relative_error, "contact_balance_a_per_cm": balance_error},
        "outcome": "unresolved" if not initial.get("converged") or not solved.get("converged") else ("pass" if error <= ABS_TOL_A_PER_CM + REL_TOL * abs(expected_current) and balance_error <= ABS_TOL_A_PER_CM + REL_TOL * abs(expected_current) else "fail"),
    }


def run_fixture() -> dict:
    sys.path.insert(0, str(DEVSIM_ROOT / "testing"))
    import devsim  # type: ignore
    import test_common  # type: ignore
    cases = [run_case(devsim, test_common, width, str(index)) for index, width in enumerate(WIDTHS_CM)]
    for case in cases:
        case["outcome"] = classify_case(case)
    observed_ratio = cases[1]["observed"]["left_electron_current_a_per_cm"] / cases[0]["observed"]["left_electron_current_a_per_cm"]
    width_ratio = cases[1]["geometry"]["contact_width_cm"] / cases[0]["geometry"]["contact_width_cm"]
    return {"cases": cases, "width_scaling": {"observed_current_ratio": observed_ratio, "geometry_width_ratio": width_ratio, "relative_ratio_error": abs(observed_ratio - width_ratio) / width_ratio}}


def _worker() -> int:
    result = run_fixture()
    outcomes = [case["outcome"] for case in result["cases"]]
    scaling_ok = result["width_scaling"]["relative_ratio_error"] <= REL_TOL
    result["width_scaling"]["pass"] = scaling_ok
    result["outcome"] = ("unresolved" if "unresolved" in outcomes else
                         "pass" if len(outcomes) == 2 and all(outcome == "pass" for outcome in outcomes) and scaling_ok else "fail")
    print("__NORMALIZATION_RESULT__" + json.dumps(result, allow_nan=False))
    return 0 if result["outcome"] == "pass" else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        return _worker()
    report = {"schema": "current-normalization/1", "fixture": "uniform_2d_ohmic_resistor", "units": {"length": "cm", "current_density": "A/cm^2", "contact_current": "A/cm", "depth": "cm"}, "tolerances": {"relative": REL_TOL, "absolute_a_per_cm": ABS_TOL_A_PER_CM}, "provenance": {"devsim_source": str(DEVSIM_ROOT.relative_to(ROOT)), "devsim_expected_commit": PIN, "fixture_script_sha256": sha256(Path(__file__)), "test_common_sha256": sha256(DEVSIM_ROOT / "testing" / "test_common.py"), "devsim_runtime_version": "unknown"}}
    try:
        observed = subprocess.check_output(["git", "-C", str(DEVSIM_ROOT), "rev-parse", "HEAD"], text=True).strip()
        dirty = subprocess.run(["git", "-C", str(DEVSIM_ROOT), "diff", "--quiet", "HEAD"], check=False).returncode != 0
        report["provenance"].update({"devsim_observed_commit": observed, "devsim_source_dirty": dirty})
        if observed != PIN or dirty:
            raise RuntimeError("DEVSIM source is not the pinned clean checkout")
        import importlib.metadata
        report["provenance"]["devsim_runtime_version"] = importlib.metadata.version("devsim")
        work = OUT.with_name("current-normalization-work") / uuid.uuid4().hex
        work.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        try:
            completed = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker"], cwd=str(work), capture_output=True, text=True, timeout=120, check=False)
            worker_stdout, worker_stderr, returncode = completed.stdout, completed.stderr, completed.returncode
        except subprocess.TimeoutExpired as exc:
            worker_stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            worker_stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            returncode = None
        (work / "stdout.log").write_text(worker_stdout, encoding="utf-8")
        (work / "stderr.log").write_text(worker_stderr, encoding="utf-8")
        report["execution"] = {"timeout_s": 120, "elapsed_s": round(time.monotonic() - started, 6), "returncode": returncode, "stdout_log": str((work / "stdout.log").relative_to(ROOT)), "stderr_log": str((work / "stderr.log").relative_to(ROOT)), "stdout_sha256": sha256(work / "stdout.log"), "stderr_sha256": sha256(work / "stderr.log")}
        marker = "__NORMALIZATION_RESULT__"
        payload = next((line[len(marker):] for line in worker_stdout.splitlines() if line.startswith(marker)), None)
        if returncode not in (0, 2) or payload is None:
            raise RuntimeError("worker failed without a result marker")
        report["result"] = json.loads(payload)
    except Exception as exc:  # retain an honest machine-readable unresolved result
        report["result"] = {"outcome": "unresolved", "error": repr(exc)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"outcome": report["result"]["outcome"], "report": str(OUT)}))
    return 0 if report["result"]["outcome"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
