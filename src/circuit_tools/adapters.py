"""Small, dependency-free execution adapters for circuit tools.

The adapter deliberately treats a simulator process as an untrusted external
program.  A zero exit status is not evidence that measurements were produced;
the returned result records whether the requested output was actually parsed.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import importlib.util
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence


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
    return next((line for line in lines if re.search(r"(?:ngspice|devsim).*\d+", line, re.I)), lines[0] if lines else None)


def discover_capabilities() -> dict[str, ToolCapability]:
    """Discover optional DEVSIM and ngspice executables without importing them."""
    found: dict[str, ToolCapability] = {}
    for name, features in (
        ("ngspice", ("batch", "wrdata", "dc", "ac", "tran")),
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


def capabilities() -> dict[str, ToolCapability]:
    """Compatibility alias used by command-line and agent clients."""
    return discover_capabilities()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


_FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"


def parse_wrdata(source: str | os.PathLike[str]) -> dict[str, list[float]]:
    """Parse ngspice ``wrdata`` output, including its ASCII headers.

    Both ordinary whitespace-separated output and the ``Values:`` format are
    accepted.  Columns are named from ``Variables:`` when available; otherwise
    they are ``column0``, ``column1``, ... .  The first integer index emitted by
    some ngspice versions is discarded when it is clearly an index column.
    """
    text = Path(source).read_text(encoding="utf-8") if isinstance(source, os.PathLike) else source
    names: list[str] = []
    rows: list[list[float]] = []
    in_values = False
    saw_values = False
    for line in text.splitlines():
        s = line.strip()
        if any(token.lower() in {"inf", "+inf", "-inf", "infinity", "nan", "+nan", "-nan"} for token in s.split()):
            raise ValueError("non-finite wrdata value")
        m = re.match(r"\s*\d+\s+([^\s]+)\s+([^\s]+)\s*$", line)
        if m and not in_values and not all(re.fullmatch(_FLOAT, x) for x in s.split()):
            # Header entries are commonly: index name type.
            if s.split()[0].isdigit() and len(s.split()) >= 2:
                names.append(s.split()[1])
                continue
        if s.lower().startswith("values:"):
            in_values = True
            saw_values = True
            continue
        if not s or s.startswith("#") or (":" in s and not in_values):
            continue
        tokens = s.split()
        if not in_values and tokens and not all(re.fullmatch(_FLOAT, v) for v in tokens):
            if not names:
                names = tokens
                continue
            raise ValueError(f"unsupported wrdata header: {line!r}")
        if not all(re.fullmatch(_FLOAT, v) for v in tokens):
            if saw_values:
                raise ValueError(f"unsupported wrdata row: {line!r}")
            continue
        values = [float(v) for v in tokens]
        if not all(math.isfinite(v) for v in values):
            raise ValueError("non-finite wrdata value")
        rows.append(values)
    if not rows:
        return {}
    if names and len(names) != len(set(names)):
        raise ValueError("duplicate wrdata column names")
    width = len(rows[0])
    if any(len(r) != width for r in rows):
        raise ValueError("ragged wrdata columns")
    if names and len(names) == width - 1:
        rows = [r[1:] for r in rows]
    elif names and len(names) != width:
        raise ValueError("wrdata header/data column mismatch")
    if not names:
        names = [f"column{i}" for i in range(width)]
    return {name: [row[i] for row in rows] for i, name in enumerate(names)}


def run_ngspice(netlist: str | os.PathLike[str], artifact_dir: str | os.PathLike[str],
                *, timeout_s: float = 30.0, executable: str = "ngspice",
                result_file: str | os.PathLike[str] | None = None,
                options: Sequence[str] = ()) -> SimulationResult:
    """Run ngspice in batch mode and persist inputs, logs, output, and hashes."""
    if not isinstance(timeout_s, (int, float)) or not math.isfinite(timeout_s) or not 0 < timeout_s <= 300:
        raise ValueError("timeout_s must be finite and in (0, 300]")
    out = Path(artifact_dir)
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty artifact directory: {out}")
    out.mkdir(parents=True, exist_ok=True)
    netlist_path = out / "netlist.cir"
    is_file = False
    if isinstance(netlist, os.PathLike):
        try: is_file = Path(netlist).is_file()
        except (OSError, ValueError): pass
    if is_file:
        netlist_path.write_bytes(Path(netlist).read_bytes())
    else:
        netlist_path.write_text(str(netlist), encoding="utf-8")
    log_path, parsed_path, prov_path = out / "ngspice.log", out / "result.json", out / "provenance.json"
    for stale in (log_path, parsed_path, out / "result.raw", out / "stdout.log", out / "stderr.log"):
        try: stale.unlink()
        except FileNotFoundError: pass
    try:
        explicit = Path(executable)
        exe = str(explicit.resolve()) if explicit.is_file() else shutil.which(executable)
    except (OSError, ValueError):
        exe = shutil.which(executable)
    tool_version = _version(exe) if exe else None
    if result_file is not None:
        candidate = Path(result_file)
        if candidate.is_absolute() or candidate.parent != Path("."):
            raise ValueError("result_file must be a basename in artifact_dir")
    base = {"simulator": "ngspice", "executable": exe, "tool_version": tool_version,
            "tool_version_sha256": hashlib.sha256(tool_version.encode()).hexdigest() if tool_version else None,
            "executable_sha256": _sha256(Path(exe)) if exe and Path(exe).is_file() else None,
            "netlist_sha256": _sha256(netlist_path), "netlist": netlist_path.name,
            "timeout_s": timeout_s, "options": list(options),
            "command": [exe or executable, "-n", "-b", "-o", log_path.name, *options, netlist_path.name]}
    start = time.monotonic()
    if re.search(r"^\s*\.(?:include|lib)\b", netlist_path.read_text(encoding="utf-8"), re.I | re.M):
        base.update(status="failed", reason="external .include/.lib netlists are unsupported")
        prov_path.write_text(json.dumps(base, indent=2, sort_keys=True), encoding="utf-8")
        return SimulationResult("failed", "unresolved", None, 0.0, artifact_dir=str(out), netlist_path=str(netlist_path), provenance_path=str(prov_path), provenance=base, message=base["reason"])
    if exe is None:
        base["status"] = "failed"
        base["reason"] = "ngspice executable not found"
        prov_path.write_text(json.dumps(base, indent=2, sort_keys=True), encoding="utf-8")
        return SimulationResult("failed", "not-supported", None, 0.0,
                                artifact_dir=str(out), netlist_path=str(netlist_path),
                                log_path=str(log_path), provenance_path=str(prov_path),
                                provenance=base, message=base["reason"])
    try:
        p = subprocess.run(base["command"], cwd=out, capture_output=True, text=True,
                           timeout=timeout_s, check=False)
        (out / "stdout.log").write_text(p.stdout or "", encoding="utf-8")
        (out / "stderr.log").write_text(p.stderr or "", encoding="utf-8")
        if not log_path.exists(): log_path.write_text(p.stdout or "", encoding="utf-8")
        status = "completed" if p.returncode == 0 else "failed"
        measurements: dict[str, list[float]] = {}
        raw_result_path: Path | None = None
        if result_file:
            rp = Path(result_file)
            if rp.is_absolute() or rp.parent != Path("."):
                raise ValueError("result_file must be a basename in artifact_dir")
            rp = out / rp
            if rp.exists():
                raw_result_path = out / "result.raw"
                raw_result_path.write_bytes(rp.read_bytes())
                measurements = parse_wrdata(raw_result_path)
                parsed_path.write_text(json.dumps(measurements, indent=2), encoding="utf-8")
        outcome = "unresolved"
        base.update(status=status, returncode=p.returncode, measurements=bool(measurements), log_sha256=_sha256(log_path))
        if raw_result_path is not None: base["result_raw_sha256"] = _sha256(raw_result_path)
        if parsed_path.exists(): base["result_sha256"] = _sha256(parsed_path)
        prov_path.write_text(json.dumps(base, indent=2, sort_keys=True), encoding="utf-8")
        return SimulationResult(status, outcome, p.returncode, time.monotonic()-start, measurements,
                                str(out), str(netlist_path), str(log_path), str(raw_result_path or parsed_path) if (raw_result_path or parsed_path).exists() else None,
                                str(prov_path), base)
    except subprocess.TimeoutExpired as exc:
        def _text(value: Any) -> str:
            return value.decode(errors="replace") if isinstance(value, bytes) else (value or "")
        (out / "stdout.log").write_text(_text(exc.stdout), encoding="utf-8")
        (out / "stderr.log").write_text(_text(exc.stderr), encoding="utf-8")
        if not log_path.exists(): log_path.write_text(_text(exc.stdout), encoding="utf-8")
        base.update(status="failed", reason="timeout", timeout_s=timeout_s, log_sha256=_sha256(log_path))
        prov_path.write_text(json.dumps(base, indent=2, sort_keys=True), encoding="utf-8")
        return SimulationResult("failed", "unresolved", None, time.monotonic()-start, artifact_dir=str(out),
                                netlist_path=str(netlist_path), log_path=str(log_path), provenance_path=str(prov_path), provenance=base)
    except (ValueError, OSError) as exc:
        (out / "stderr.log").write_text(str(exc), encoding="utf-8")
        if not log_path.exists(): log_path.write_text(str(exc), encoding="utf-8")
        base.update(status="failed", reason=str(exc), log_sha256=_sha256(log_path))
        prov_path.write_text(json.dumps(base, indent=2, sort_keys=True), encoding="utf-8")
        return SimulationResult("failed", "unresolved", None, time.monotonic()-start, artifact_dir=str(out),
                                netlist_path=str(netlist_path), log_path=str(log_path), provenance_path=str(prov_path), provenance=base, message=str(exc))


class NgspiceAdapter:
    """Object form of :func:`run_ngspice` for callers that inject an executable."""

    def __init__(self, executable: str = "ngspice") -> None:
        self.executable = executable

    def run(self, netlist: str | os.PathLike[str], artifact_dir: str | os.PathLike[str],
            *, timeout_s: float = 30.0, result_file: str | os.PathLike[str] | None = None,
            options: Sequence[str] = ()) -> SimulationResult:
        return run_ngspice(netlist, artifact_dir, timeout_s=timeout_s,
                           executable=self.executable, result_file=result_file, options=options)
