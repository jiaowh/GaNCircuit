#!/usr/bin/env python3
"""Run the pinned DEVSIM references, or report an honest missing backend.

This script deliberately does not emulate TCAD.  A successful result requires
the real ``devsim`` Python module and the official upstream scripts.  Without
those prerequisites it writes a machine-readable ``missing_backend`` result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
import importlib.metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEVSIM = ROOT / "devices" / "devsim-upstream"
OUT = ROOT / "results" / "device-reference"
PIN = "43b41ca845184c47e22b72d144db7e7db8509377"


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head(repo: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def backend_probe() -> dict:
    try:
        import devsim  # type: ignore  # noqa: F401

        return {"available": True, "python": sys.executable,
                "devsim_version": importlib.metadata.version("devsim"),
                "python_version": sys.version}
    except (ImportError, RuntimeError, OSError) as exc:
        return {"available": False, "reason": f"devsim import failed: {exc}"}


def run_reference(name: str, script: Path, probe: dict, run: bool, out_root: Path) -> dict:
    row = {"name": name, "script": str(script.relative_to(ROOT)), "status": None}
    if not script.is_file():
        row.update(status="missing_source", reason="official script is absent")
        return row
    if not probe["available"]:
        row.update(status="missing_backend", reason=probe["reason"])
        return row
    if not run:
        row.update(status="available_not_run", reason="pass --run to execute")
        return row
    work = out_root / name
    work.mkdir(parents=True, exist_ok=False)
    # Official examples use filenames relative to their source directory for
    # input meshes. Copy only those immutable inputs into the isolated workdir;
    # generated outputs never touch the pinned checkout.
    for input_file in script.parent.glob("*.msh"):
        shutil.copy2(input_file, work / input_file.name)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(script.parent), str(DEVSIM), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    started = time.monotonic()
    try:
        p = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(work),
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        (work / "stdout.log").write_text(p.stdout, encoding="utf-8")
        (work / "stderr.log").write_text(p.stderr, encoding="utf-8")
        row.update(
            status="completed" if p.returncode == 0 else "failed",
            returncode=p.returncode,
            elapsed_s=round(time.monotonic() - started, 6),
            stdout_log=str((work / "stdout.log").relative_to(ROOT)),
            stderr_log=str((work / "stderr.log").relative_to(ROOT)),
            artifacts={str(path.relative_to(work)): sha256(path) for path in work.rglob("*") if path.is_file()},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        row.update(status="failed", reason=repr(exc), elapsed_s=round(time.monotonic() - started, 6))
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", help="execute official scripts when devsim is importable")
    ap.add_argument("--out", type=Path, default=OUT / "latest.json")
    args = ap.parse_args()
    args.out = args.out.resolve()
    probe = backend_probe()
    observed_commit = git_head(DEVSIM)
    if observed_commit != PIN:
        probe = {"available": False, "reason": f"DEVSIM source pin mismatch: observed {observed_commit}, expected {PIN}"}
    elif subprocess.run(["git", "-c", "core.autocrlf=true", "-C", str(DEVSIM), "diff", "--quiet", "HEAD"], check=False).returncode != 0:
        probe = {"available": False, "reason": "DEVSIM tracked sources differ from pinned commit"}
    work_root = args.out.parent / "work" / uuid.uuid4().hex
    result = {
        "schema": "device-reference/1",
        "generated_by": str(Path(__file__).relative_to(ROOT)),
        "backend": probe,
        "provenance": {
            "repository": "https://github.com/devsim/devsim",
            "commit": observed_commit,
            "expected_commit": PIN,
            "pin_match": observed_commit == PIN,
            "license": "Apache-2.0",
            "license_sha256": sha256(DEVSIM / "LICENSE"),
        },
        "references": [
            run_reference("official_diode_1d", DEVSIM / "examples" / "diode" / "diode_1d.py", probe, args.run, work_root),
            run_reference("official_planar_mos_2d", DEVSIM / "examples" / "mobility" / "gmsh_mos2d.py", probe, args.run, work_root),
        ],
        "tcad_claim": "script execution evidence only; no physical acceptance follows from process exit status",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    bad = [r for r in result["references"] if r["status"] != "completed"]
    return 2 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
