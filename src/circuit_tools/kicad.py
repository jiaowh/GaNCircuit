"""kicad-cli runs whose failures cannot pass as clean reports (audit at 0f07a6a, docs/project-audit-0f07a6a.md).

The track R scripts ignored the DRC command's exit status and read a fixed report path, so a failed command plus a
stale or empty report gave passing short/unconnected checks. run_drc writes each report to a fresh path, requires
exit status 0, validates the report's structure and source board, checks that the board did not change during the
run, and returns the hashes that bind the report to the board checked. Any failure raises KiCadError.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import uuid


class KiCadError(Exception):
    pass


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _command(cli):
    return [str(c) for c in cli] if isinstance(cli, (list, tuple)) else [str(cli)]


def validate_drc_report(d, board):
    """Problems with a kicad-cli DRC JSON report (schema drc.v1) for the given board; empty if none."""
    if not isinstance(d, dict):
        return ["report is not a JSON object"]
    out = []
    if not str(d.get("$schema", "")).endswith("drc.v1.json"):
        out.append(f"unexpected schema {d.get('$schema')!r}")
    if not isinstance(d.get("kicad_version"), str) or not d.get("kicad_version"):
        out.append("missing kicad_version")
    if d.get("source") != Path(board).name:
        out.append(f"source {d.get('source')!r} is not {Path(board).name!r}")
    for key in ("violations", "unconnected_items"):
        v = d.get(key)
        if not isinstance(v, list):
            out.append(f"{key} is not a list")
            continue
        for i, item in enumerate(v):
            if not isinstance(item, dict) or not isinstance(item.get("type"), str) \
                    or not isinstance(item.get("items"), list):
                out.append(f"{key}[{i}] lacks a type string or an items list")
                break
    return out


def run_drc(cli, board, report_dir, tag, extra=(), timeout=3600):
    """Run kicad-cli DRC on board (saved fills unless extra asks otherwise) into a fresh report path.

    Returns {"report", "report_path", "report_sha256", "board_sha256", "kicad_version", "command"}."""
    board = Path(board).resolve()
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    report = report_dir / f"{tag}-{uuid.uuid4().hex[:12]}.json"
    if report.exists():
        raise KiCadError(f"{report} already exists")
    before = sha256_file(board)
    cmd = _command(cli) + ["pcb", "drc", "--format", "json", "--severity-all", *extra, "-o", str(report), str(board)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise KiCadError(f"DRC timed out after {timeout} s") from exc
    if proc.returncode != 0:
        raise KiCadError(f"DRC exited {proc.returncode}: {(proc.stderr or proc.stdout)[-1500:]}")
    if not report.exists():
        raise KiCadError("DRC exited 0 but wrote no report")
    try:
        d = json.loads(report.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise KiCadError(f"DRC report is not JSON: {exc}") from exc
    problems = validate_drc_report(d, board)
    if problems:
        raise KiCadError("invalid DRC report: " + "; ".join(problems))
    if "--save-board" not in extra and sha256_file(board) != before:
        raise KiCadError("board changed during DRC")
    return {"report": d, "report_path": report, "report_sha256": sha256_file(report), "board_sha256": before,
            "kicad_version": d["kicad_version"], "command": cmd[len(_command(cli)):]}
