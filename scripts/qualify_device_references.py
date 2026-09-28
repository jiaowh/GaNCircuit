#!/usr/bin/env python3
"""Qualify the diode reference on refined meshes and report current semantics.

This is deliberately a small, direct DEVSIM experiment.  It does not claim
physical validation: it checks solver convergence, terminal-current balance,
and mesh stability for the pinned upstream diode fixture.  The generated
runner uses the same silicon physics as ``diode_1d.py`` while making the
interface mesh spacing explicit.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEVSIM = ROOT / "devices" / "devsim-upstream"
PIN = "43b41ca845184c47e22b72d144db7e7db8509377"
REFERENCE = DEVSIM / "examples" / "diode" / "diode_1d.py"

RUNNER = r'''from devsim import get_node_model_values, set_parameter, solve
from devsim.python_packages.simple_physics import GetContactBiasName, PrintCurrents
import diode_common

device = "MyDevice"
region = "MyRegion"
mid_ps = float(__import__("os").environ["QUALIFY_MID_PS"])
diode_common.create_1d_mesh(mesh="dio")
diode_common.add_1d_mesh_line(mesh="dio", pos=0, ps=1e-7, tag="top")
diode_common.add_1d_mesh_line(mesh="dio", pos=0.5e-5, ps=mid_ps, tag="mid")
diode_common.add_1d_mesh_line(mesh="dio", pos=1e-5, ps=1e-7, tag="bot")
diode_common.add_1d_contact(mesh="dio", name="top", tag="top", material="metal")
diode_common.add_1d_contact(mesh="dio", name="bot", tag="bot", material="metal")
diode_common.add_1d_region(mesh="dio", material="Si", region=region, tag1="top", tag2="bot")
diode_common.finalize_mesh(mesh="dio")
diode_common.create_device(mesh="dio", device=device)
print("QUALIFY_NODE_COUNT", len(get_node_model_values(device=device, region=region, name="x")))
diode_common.SetParameters(device=device, region=region)
diode_common.set_parameter(device=device, region=region, name="taun", value=1e-8)
diode_common.set_parameter(device=device, region=region, name="taup", value=1e-8)
diode_common.SetNetDoping(device=device, region=region)
diode_common.InitialSolution(device, region)
records = []
records.append(solve(type="dc", absolute_error=1.0, relative_error=1e-10,
                     maximum_iterations=30, info=True))
diode_common.DriftDiffusionInitialSolution(device, region)
records.append(solve(type="dc", absolute_error=1e10, relative_error=1e-10,
                     maximum_iterations=30, info=True))
v = 0.0
while v < 0.51:
    set_parameter(device=device, name=GetContactBiasName("top"), value=v)
    records.append(solve(type="dc", absolute_error=1e10, relative_error=1e-10,
                         maximum_iterations=30, info=True))
    if abs(v - 0.5) < 1e-12:
        print("QUALIFY_FINAL_BIAS 0.5")
        PrintCurrents(device, "top")
        PrintCurrents(device, "bot")
    v += 0.1
print("QUALIFY_CONVERGED", int(all(bool(r.get("converged", False)) for r in records)))
print("QUALIFY_SOLVES", len(records))
'''


def sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def git_head(repo: Path) -> str | None:
    try:
        return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def probe_backend() -> dict:
    try:
        import devsim  # noqa: F401
        imported = Path(devsim.__file__).resolve().parent / "python_packages" / "simple_physics.py"
        return {"available": True, "python": sys.executable,
                "devsim_version": importlib.metadata.version("devsim"),
                "python_version": sys.version,
                "imported_package": str(Path(devsim.__file__).resolve()),
                "imported_physics_source": str(imported),
                "imported_physics_sha256": sha256(imported)}
    except (ImportError, RuntimeError, OSError) as exc:
        return {"available": False, "reason": f"devsim import failed: {exc}"}


def parse_contacts(stdout: str) -> dict[str, list[float]]:
    contacts: dict[str, list[float]] = {}
    for line in stdout.splitlines():
        fields = line.split()
        if len(fields) == 5 and fields[0] in {"top", "bot"}:
            try:
                contacts[fields[0]] = [float(v) for v in fields[1:]]
            except ValueError:
                pass
    return contacts


def run_case(ps: float, work: Path, timeout: int) -> dict:
    work.mkdir(parents=True, exist_ok=False)
    source = work / "qualify_diode.py"
    source.write_text(RUNNER, encoding="utf-8")
    env = os.environ.copy()
    env["QUALIFY_MID_PS"] = f"{ps:.17g}"
    env["PYTHONPATH"] = os.pathsep.join([str(REFERENCE.parent), str(DEVSIM), env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
    started = time.monotonic()
    try:
        proc = subprocess.run([sys.executable, str(source)], cwd=work, env=env,
                              capture_output=True, text=True, timeout=timeout, check=False)
        (work / "stdout.log").write_text(proc.stdout, encoding="utf-8")
        (work / "stderr.log").write_text(proc.stderr, encoding="utf-8")
        contacts = parse_contacts(proc.stdout)
        converged = "QUALIFY_CONVERGED 1" in proc.stdout
        solve_match = re.search(r"QUALIFY_SOLVES (\d+)", proc.stdout)
        nodes_match = re.search(r"QUALIFY_NODE_COUNT (\d+)", proc.stdout)
        total = {name: rows[3] for name, rows in contacts.items()}
        imbalance = None
        if set(total) == {"top", "bot"}:
            imbalance = abs(total["top"] + total["bot"]) / max(abs(total["top"]) + abs(total["bot"]), 1e-30)
        return {"mesh_mid_spacing_cm": ps, "status": "completed" if proc.returncode == 0 else "failed",
                "returncode": proc.returncode, "elapsed_s": round(time.monotonic() - started, 6),
                "solver_converged": converged, "solve_count": int(solve_match.group(1)) if solve_match else None,
                "node_count": int(nodes_match.group(1)) if nodes_match else None,
                "final_bias_V": contacts.get("top", [None])[0] if contacts.get("top") else None,
                "contacts": contacts, "relative_current_imbalance": imbalance,
                "runner_sha256": sha256(source),
                "stdout_log": str((work / "stdout.log").relative_to(ROOT)),
                "stderr_log": str((work / "stderr.log").relative_to(ROOT)),
                "stdout_sha256": sha256(work / "stdout.log"), "stderr_sha256": sha256(work / "stderr.log")}
    except subprocess.TimeoutExpired as exc:
        partial = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        (work / "stdout.log").write_text(partial, encoding="utf-8")
        (work / "stderr.log").write_text(exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or ""), encoding="utf-8")
        return {"mesh_mid_spacing_cm": ps, "status": "timeout", "elapsed_s": round(time.monotonic() - started, 6),
                "reason": f"timeout after {timeout}s", "stdout_log": str((work / "stdout.log").relative_to(ROOT)),
                "stderr_log": str((work / "stderr.log").relative_to(ROOT)), "stdout_partial": bool(exc.stdout)}


def qualification_outcome(cases: list[dict], comparisons: list[dict]) -> str:
    """Apply the acceptance gate; incomplete or malformed evidence is unresolved."""
    completed = [c for c in cases if c.get("status") == "completed"]
    valid = all(c.get("solver_converged") and c.get("final_bias_V") == 0.5 and
                c.get("relative_current_imbalance") is not None and
                math.isfinite(c["relative_current_imbalance"]) and c["relative_current_imbalance"] <= 1e-4 and
                set(c.get("contacts", {})) == {"top", "bot"} and
                all(len(row) == 4 and all(math.isfinite(v) for v in row) for row in c["contacts"].values()) and
                c["contacts"]["top"][0] == 0.5 and c["contacts"]["bot"][0] == 0.0
                for c in completed)
    node_counts = [c.get("node_count") for c in completed]
    refined = all(isinstance(n, int) and n > 0 for n in node_counts) and node_counts == sorted(node_counts) and len(set(node_counts)) == 3
    return "pass" if len(completed) == 3 and valid and refined and len(comparisons) == 2 and all(c.get("pass") is True for c in comparisons) else "unresolved"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", help="execute the real DEVSIM qualification")
    ap.add_argument("--out", type=Path, default=ROOT / "results/device-reference/qualification.json")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--relative-tolerance", type=float, default=1e-3)
    ap.add_argument("--absolute-tolerance", type=float, default=1e-12)
    args = ap.parse_args()
    args.out = args.out.resolve()
    if not (math.isfinite(args.relative_tolerance) and math.isfinite(args.absolute_tolerance) and
            args.relative_tolerance > 0 and args.absolute_tolerance > 0 and args.timeout > 0):
        ap.error("tolerances must be finite and positive; timeout must be positive")
    observed = git_head(DEVSIM)
    backend = probe_backend()
    if observed != PIN:
        backend = {"available": False, "reason": f"DEVSIM source pin mismatch: observed {observed}, expected {PIN}"}
    elif subprocess.run(["git", "-C", str(DEVSIM), "diff", "--quiet", "HEAD"], check=False).returncode != 0:
        backend = {"available": False, "reason": "DEVSIM tracked sources differ from pinned commit"}
    cases = []
    if args.run and backend["available"]:
        root = args.out.parent / "qualification-work" / uuid.uuid4().hex
        for ps in (2e-9, 1e-9, 5e-10):
            cases.append(run_case(ps, root / f"mid-{ps:.0e}", args.timeout))
    elif not backend["available"]:
        cases = [{"status": "missing_backend", "reason": backend["reason"]}]
    else:
        cases = [{"status": "available_not_run", "reason": "pass --run to execute"}]
    completed = [c for c in cases if c.get("status") == "completed"]
    comparisons = []
    for prev, cur in zip(completed, completed[1:]):
        a = prev.get("contacts", {}).get("top", [None] * 4)[3]
        b = cur.get("contacts", {}).get("top", [None] * 4)[3]
        if a is None or b is None:
            continue
        if not all(math.isfinite(v) for v in (a, b)):
            continue
        err = abs(b - a)
        scale = max(abs(a), abs(b), args.absolute_tolerance)
        comparisons.append({"coarse_spacing_cm": prev["mesh_mid_spacing_cm"], "fine_spacing_cm": cur["mesh_mid_spacing_cm"],
                            "absolute_delta_A_per_cm2": err, "relative_delta": err / scale,
                            "pass": err <= args.absolute_tolerance + args.relative_tolerance * scale})
    outcome = qualification_outcome(cases, comparisons)
    result = {"schema": "device-reference-qualification/1", "generated_by": str(Path(__file__).relative_to(ROOT)),
              "outcome": outcome, "backend": backend,
              "provenance": {"repository": "https://github.com/devsim/devsim", "commit": observed, "expected_commit": PIN,
                             "reference_script": str(REFERENCE.relative_to(ROOT)), "reference_sha256": sha256(REFERENCE),
                             "physics_source": str((DEVSIM / "python_packages/simple_physics.py").relative_to(ROOT)),
                             "physics_source_sha256": sha256(DEVSIM / "python_packages/simple_physics.py"),
                             "imported_physics_source": backend.get("imported_physics_source"),
                             "imported_physics_sha256": backend.get("imported_physics_sha256")},
              "current_definition": {"unit": "A/cm^2", "basis": "DEVSIM simple_physics contact current using cm-based silicon parameters; 1D unit out-of-plane area",
                                      "columns": ["bias_V", "electron_current_A_per_cm2", "hole_current_A_per_cm2", "total_current_A_per_cm2"],
                                      "normalization_status": "explicit model-unit convention; not measured-current validation"},
              "mesh_policy": {"midpoint": "0.5e-5 cm", "mid_spacings_cm": [2e-9, 1e-9, 5e-10], "endpoint_spacing_cm": 1e-7},
              "tolerances": {"mesh_relative_current": args.relative_tolerance, "mesh_absolute_current_A_per_cm2": args.absolute_tolerance,
                             "conservation_relative_current": 1e-4}, "cases": cases, "mesh_comparisons": comparisons,
              "claim_boundary": "Numerical midpoint-local mesh/current qualification for the 1D diode at final 0.5 V only; 2D planar MOS and independent physical validation remain unresolved."}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if outcome == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
