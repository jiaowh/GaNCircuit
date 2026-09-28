"""LTspice batch adapter: write the bench, run it, parse the waveforms and log.

As with the other adapters, the simulator is an untrusted external program.
LTspice can exit with status 0 after an error, so success requires a parsed
``.raw`` file and a log without errors.  Every model library the netlist
loads must be passed explicitly; it is copied into the run directory and
hashed, so a run never depends on files outside its own evidence.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import struct
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from .adapters import SimulationResult, ToolCapability

_STANDARD_PATHS = (
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "ADI" / "LTspice" / "LTspice.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "ADI" / "LTspice" / "LTspice.exe",
)
_INCLUDE = re.compile(r"^\s*\.(?:include|inc|lib)\s+(.+?)\s*$", re.I | re.M)
_ERROR = re.compile(r"(?:^|\b)(?:error|fatal|singular matrix|time step too small|"
                    r"convergence failed|analysis failed|unknown (?:subcircuit|parameter|device))",
                    re.I)
_FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"


def find_ltspice(executable: str | os.PathLike[str] | None = None) -> str | None:
    """Return an LTspice executable from an explicit path, LTSPICE_EXE, standard installs, or PATH.

    An explicit ``executable`` never falls back to another installation, so
    provenance always names the tool the caller asked for.
    """
    if executable is not None:
        if Path(executable).is_file():
            return str(Path(executable).resolve())
        return shutil.which(str(executable))
    for candidate in (os.environ.get("LTSPICE_EXE"), *_STANDARD_PATHS):
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    for name in ("LTspice", "LTspice.exe", "XVIIx64.exe"):
        found = shutil.which(name)
        if found:
            return found
    return None


def ltspice_version(executable: str) -> str | None:
    """Windows file version of the executable, or None when unavailable."""
    try:
        p = subprocess.run(["powershell", "-NoProfile", "-Command",
                            f"(Get-Item -LiteralPath '{executable}').VersionInfo.ProductVersion"],
                           capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (p.stdout or "").strip()
    return text or None


def ltspice_capability(executable: str | None = None) -> ToolCapability:
    features = ("batch", "raw-binary", "raw-ascii", "op", "dc", "ac", "tran", "meas", "step")
    exe = find_ltspice(executable)
    if exe is None:
        return ToolCapability("ltspice", False, capabilities=features, reason="LTspice executable not found")
    return ToolCapability("ltspice", True, exe, ltspice_version(exe), features)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_text_auto(path: str | os.PathLike[str]) -> str:
    """Decode LTspice text output, which may be UTF-16LE (with or without BOM) or UTF-8."""
    data = Path(path).read_bytes()
    if data.startswith(b"\xff\xfe"):
        return data[2:].decode("utf-16-le", errors="replace")
    if len(data) >= 4 and data[1] == 0 and data[3] == 0:
        return data.decode("utf-16-le", errors="replace")
    return data.decode("utf-8", errors="replace")


@dataclass
class RawData:
    """Parsed LTspice ``.raw`` output. Values are keyed by lower-case trace name."""
    title: str
    plotname: str
    flags: tuple[str, ...]
    variables: list[tuple[str, str]]
    values: dict[str, list[Any]]
    step_starts: list[int] = field(default_factory=lambda: [0])

    @property
    def axis(self) -> str:
        return self.variables[0][0]

    def step(self, index: int) -> dict[str, list[Any]]:
        """Values for one ``.step`` or nested-sweep run."""
        starts = self.step_starts + [len(self.values[self.axis])]
        lo, hi = starts[index], starts[index + 1]
        return {k: v[lo:hi] for k, v in self.values.items()}

    @property
    def n_steps(self) -> int:
        return len(self.step_starts)


def _header_encoding(data: bytes) -> str:
    return "utf-16-le" if len(data) > 1 and data[1] == 0 else "latin-1"


def parse_raw(path: str | os.PathLike[str]) -> RawData:
    """Parse an LTspice binary or ASCII ``.raw`` file.

    The binary row layout is inferred from the file size: LTspice stores real
    data either as a float64 axis plus float32 traces, or entirely as float64
    (``double`` flag); complex data are pairs of float64.  A size that fits
    neither layout is rejected rather than guessed.
    """
    data = Path(path).read_bytes()
    enc = _header_encoding(data)
    unit = 2 if enc == "utf-16-le" else 1
    markers = {m: m.encode(enc) for m in ("Binary:\n", "Values:\n", "Binary:\r\n", "Values:\r\n")}
    pos, marker = -1, ""
    for m, b in markers.items():
        i = data.find(b)
        if i >= 0 and (pos < 0 or i < pos):
            pos, marker = i, m
    if pos < 0:
        raise ValueError("raw file has no Binary:/Values: section")
    header = data[:pos].decode(enc)
    body = data[pos + len(markers[marker]):]
    fields: dict[str, str] = {}
    variables: list[tuple[str, str]] = []
    in_vars = False
    for line in header.splitlines():
        if in_vars and line[:1] in ("\t", " ") and line.strip():
            parts = line.split()
            variables.append((parts[1].lower(), parts[2] if len(parts) > 2 else ""))
            continue
        key, _, value = line.partition(":")
        in_vars = key.strip().lower() == "variables"
        fields[key.strip().lower()] = value.strip()
    flags = tuple(fields.get("flags", "").lower().split())
    n_vars, n_points = int(fields["no. variables"]), int(fields["no. points"])
    if len(variables) != n_vars or n_vars == 0:
        raise ValueError(f"raw header declares {n_vars} variables but lists {len(variables)}")
    names = [v[0] for v in variables]
    if len(set(names)) != len(names):
        raise ValueError("duplicate raw variable names")
    complex_data = "complex" in flags
    rows: list[list[Any]] = []
    if marker.startswith("Binary"):
        if complex_data:
            fmt = "<" + "d" * (2 * n_vars)
        elif len(body) == n_points * 8 * n_vars:
            fmt = "<" + "d" * n_vars
        elif len(body) == n_points * (8 + 4 * (n_vars - 1)):
            fmt = "<d" + "f" * (n_vars - 1)
        else:
            raise ValueError(f"raw binary size {len(body)} fits no known layout for "
                             f"{n_points} points x {n_vars} variables")
        size = struct.calcsize(fmt)
        if len(body) != size * n_points:
            raise ValueError("raw binary section is truncated or padded")
        for (row) in struct.iter_unpack(fmt, body):
            if complex_data:
                rows.append([complex(row[2 * i], row[2 * i + 1]) for i in range(n_vars)])
            else:
                rows.append(list(row))
    else:
        tokens = body.decode(enc).split()
        per_point = n_vars + 1
        if len(tokens) != n_points * per_point:
            raise ValueError("raw ASCII value count does not match header")
        for p in range(n_points):
            chunk = tokens[p * per_point + 1:(p + 1) * per_point]
            if complex_data:
                rows.append([complex(*map(float, t.split(","))) for t in chunk])
            else:
                rows.append([float(t) for t in chunk])
    for row in rows:
        for v in row:
            parts = (v.real, v.imag) if isinstance(v, complex) else (v,)
            if not all(math.isfinite(x) for x in parts):
                raise ValueError("non-finite raw value")
    values = {name: [r[i] for r in rows] for i, name in enumerate(names)}
    if names[0] == "time":
        # LTspice uses the sign bit of the time axis as an internal flag.
        values["time"] = [abs(t) for t in values["time"]]
    return RawData(fields.get("title", ""), fields.get("plotname", ""), flags, variables, values,
                   _step_starts(values[names[0]], names[0] == "time"))


def _step_starts(axis: list[Any], is_time: bool) -> list[int]:
    """Split concatenated ``.step``/nested-sweep runs.

    A transient run restarts when time decreases. Sweeps repeat the same axis
    values in every step, so the step length is the smallest period that
    reproduces the whole axis (length 1 for single-point AC or OP steps).
    """
    n = len(axis)
    if n < 2:
        return [0]
    if is_time:
        return [0] + [i for i in range(1, n) if axis[i] < axis[i - 1]]
    for period in range(1, n // 2 + 1):
        if n % period == 0 and all(axis[i] == axis[i % period] for i in range(n)):
            if period == 1 and n > 1:
                return list(range(n))
            return list(range(0, n, period))
    return [0]


def parse_log(text: str) -> dict[str, Any]:
    """Extract measurements, failed measurements, errors and warnings from an LTspice log."""
    measurements: dict[str, list[float]] = {}
    failed: list[str] = []
    errors: list[str] = []
    warnings: list[str] = []
    step = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        low = line.lower()
        m = re.match(r"^(\w+):\s*(?:.*?=\s*)?(" + _FLOAT + r")(?:\s|$)", line)
        m2 = re.match(r"^(\w+)\s*=\s*(" + _FLOAT + r")(?:\s|$)", line)
        if re.match(r"^measurement \S+ fail", low) or re.search(r"fail'?ed", low):
            failed.append(line)
        elif m and not low.startswith(("total elapsed", "solver", "tnom", "temp", "method",
                                       "matrix", "thread", "direct newton", "gmin", "source stepping")):
            measurements.setdefault(m.group(1).lower(), []).append(float(m.group(2)))
        elif m2:
            measurements.setdefault(m2.group(1).lower(), []).append(float(m2.group(2)))
        if low.startswith("warning"):
            warnings.append(line)
        elif _ERROR.search(low) and "fail" not in low.split(":")[0]:
            errors.append(line)
        if low.startswith(".step"):
            step += 1
    return {"measurements": measurements, "failed_measurements": failed,
            "errors": errors, "warnings": warnings, "steps": step}


def _referenced_libraries(netlist_text: str) -> list[str]:
    refs = []
    for m in _INCLUDE.finditer(netlist_text):
        refs.append(m.group(1).strip().strip('"').strip("'"))
    return refs


def run_ltspice(netlist: str | os.PathLike[str], artifact_dir: str | os.PathLike[str], *,
                libraries: Sequence[str | os.PathLike[str]] = (), timeout_s: float = 60.0,
                executable: str | os.PathLike[str] | None = None, ascii_raw: bool = False) -> SimulationResult:
    """Run one LTspice batch simulation and persist inputs, outputs and hashes.

    ``libraries`` lists every model file the netlist loads with ``.lib`` or
    ``.include``; references must be bare file names matching those files.
    Measurements combine ``.meas`` results from the log with the waveform
    traces of the first ``.raw`` output; ``result_path`` points at the raw file.
    """
    if not isinstance(timeout_s, (int, float)) or not math.isfinite(timeout_s) or not 0 < timeout_s <= 600:
        raise ValueError("timeout_s must be finite and in (0, 600]")
    out = Path(artifact_dir)
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty artifact directory: {out}")
    out.mkdir(parents=True, exist_ok=True)
    netlist_path = out / "bench.cir"
    source = Path(netlist) if isinstance(netlist, os.PathLike) else None
    text = source.read_text(encoding="utf-8") if source is not None else str(netlist)
    netlist_path.write_text(text, encoding="utf-8")
    log_path, raw_path, prov_path = out / "bench.log", out / "bench.raw", out / "provenance.json"
    exe = find_ltspice(executable)
    command = [exe or "LTspice", "-b", *(["-ascii"] if ascii_raw else []), str(netlist_path.resolve())]
    base: dict[str, Any] = {"simulator": "ltspice", "executable": exe,
                            "tool_version": ltspice_version(exe) if exe else None,
                            "executable_sha256": _sha256(Path(exe)) if exe else None,
                            "netlist": netlist_path.name, "netlist_sha256": _sha256(netlist_path),
                            "timeout_s": timeout_s, "ascii_raw": ascii_raw, "command": command,
                            "libraries": {}}

    def finish(status: str, outcome: str, returncode: int | None, started: float,
               measurements: dict[str, list[float]] | None = None, message: str | None = None) -> SimulationResult:
        if message:
            base["reason"] = message
        base["status"] = status
        prov_path.write_text(json.dumps(base, indent=2, sort_keys=True), encoding="utf-8")
        return SimulationResult(status, outcome, returncode, time.monotonic() - started, measurements or {},
                                str(out), str(netlist_path), str(log_path) if log_path.exists() else None,
                                str(raw_path) if raw_path.exists() else None, str(prov_path), base, message)

    started = time.monotonic()
    supplied: dict[str, Path] = {}
    for lib in libraries:
        p = Path(lib)
        if not p.is_file():
            return finish("failed", "unresolved", None, started, message=f"library not found: {p}")
        if p.name in supplied or p.name == netlist_path.name:
            return finish("failed", "unresolved", None, started, message=f"duplicate library name: {p.name}")
        supplied[p.name] = p
    for ref in _referenced_libraries(text):
        if Path(ref).name != ref or ref not in supplied:
            return finish("failed", "unresolved", None, started,
                          message=f"netlist loads {ref!r}, which is not a supplied library file name")
    for name, p in supplied.items():
        shutil.copyfile(p, out / name)
        base["libraries"][name] = {"source": str(p.resolve()), "sha256": _sha256(out / name)}
    if exe is None:
        return finish("failed", "not-supported", None, started, message="LTspice executable not found")
    try:
        p = subprocess.run(command, cwd=out, capture_output=True, text=True, timeout=timeout_s, check=False)
    except subprocess.TimeoutExpired:
        return finish("failed", "unresolved", None, started, message="timeout")
    except OSError as exc:
        return finish("failed", "unresolved", None, started, message=str(exc))
    (out / "stdout.log").write_text(p.stdout or "", encoding="utf-8")
    (out / "stderr.log").write_text(p.stderr or "", encoding="utf-8")
    base["returncode"] = p.returncode
    if not log_path.exists():
        return finish("failed", "unresolved", p.returncode, started, message="LTspice wrote no log")
    base["log_sha256"] = _sha256(log_path)
    log = parse_log(read_text_auto(log_path))
    base.update(log_errors=log["errors"], log_warnings=log["warnings"],
                failed_measurements=log["failed_measurements"])
    header = read_text_auto(log_path).splitlines()[:3]
    base["log_header"] = [h.strip() for h in header if h.strip()]
    measurements: dict[str, list[float]] = dict(log["measurements"])
    if raw_path.exists():
        base["raw_sha256"] = _sha256(raw_path)
        try:
            raw = parse_raw(raw_path)
        except (ValueError, KeyError, struct.error) as exc:
            return finish("failed", "unresolved", p.returncode, started, measurements,
                          message=f"unparseable raw output: {exc}")
        base.update(raw_plotname=raw.plotname, raw_flags=list(raw.flags), raw_points=len(raw.values[raw.axis]),
                    raw_steps=raw.n_steps)
        for name, trace in raw.values.items():
            if name in measurements:
                continue
            measurements[name] = trace
    if log["errors"]:
        return finish("failed", "unresolved", p.returncode, started, measurements,
                      message="LTspice log reports errors: " + "; ".join(log["errors"][:3]))
    if not measurements:
        return finish("failed", "unresolved", p.returncode, started, message="no raw traces or measurements parsed")
    (out / "result.json").write_text(json.dumps(
        {k: ([[c.real, c.imag] for c in v] if v and isinstance(v[0], complex) else v)
         for k, v in measurements.items()}, allow_nan=False), encoding="utf-8")
    base["result_sha256"] = _sha256(out / "result.json")
    return finish("completed", "unresolved", p.returncode, started, measurements)
