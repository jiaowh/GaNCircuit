"""Shared result types and tool discovery for the execution adapters.

Adapters treat a simulator process as an untrusted external program.  A zero
exit status is not evidence that measurements were produced; the returned
result records whether the requested output was actually parsed.  The circuit
simulator adapter is ``circuit_tools.ltspice``.
"""
from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolCapability:
    name: str
    available: bool
    executable: str | None = None
    version: str | None = None
    capabilities: tuple[str, ...] = ()
    reason: str | None = None


@dataclass
class SimulationResult:
    status: str
    outcome: str
    returncode: int | None
    duration_s: float
    measurements: dict[str, list[float]] = field(default_factory=dict)
    artifact_dir: str | None = None
    netlist_path: str | None = None
    log_path: str | None = None
    result_path: str | None = None
    provenance_path: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)
    message: str | None = None


def _version(executable: str) -> str | None:
    try:
        p = subprocess.run([executable, "--version"], capture_output=True,
                           text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (p.stdout or "") + "\n" + (p.stderr or "")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return next((line for line in lines if re.search(r"devsim.*\d+", line, re.I)), lines[0] if lines else None)


def discover_capabilities() -> dict[str, ToolCapability]:
    """Discover LTspice and DEVSIM without importing or running a simulation."""
    from .ltspice import ltspice_capability

    found: dict[str, ToolCapability] = {"ltspice": ltspice_capability()}
    for name, features in (
        ("devsim", ("device-pde", "python-script")),
    ):
        exe = shutil.which(name)
        if name == "devsim" and exe is None:
            spec = importlib.util.find_spec("devsim")
            if spec is not None:
                found[name] = ToolCapability(name, True, spec.origin, None, features)
                continue
        if exe is None:
            found[name] = ToolCapability(name, False, capabilities=features,
                                         reason="simulator executable not found")
        else:
            found[name] = ToolCapability(name, True, exe, _version(exe), features)
    return found

