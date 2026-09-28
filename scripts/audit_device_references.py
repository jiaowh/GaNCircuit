#!/usr/bin/env python3
"""Independent finite/current-balance checks on official reference logs."""
from __future__ import annotations
import hashlib, json, math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {"official_diode_1d": {"top": .5, "bot": 0.0}, "official_planar_mos_2d": {"gate": .5, "drain": .5, "source": 0.0, "body": 0.0}}
VALID_STATUSES = {"completed", "missing_source", "missing_backend", "available_not_run", "failed"}
CONTACT_COLUMNS = ["bias_V", "electron_current_native", "hole_current_native", "total_current_native"]

def _bad_check(name: str, reason: str, **extra: Any) -> dict[str, Any]:
    result = {"reference": name, "outcome": "fail", "reason": reason}
    result.update(extra)
    return result

def _audit_row(row: Any, root: Path) -> dict[str, Any]:
    if not isinstance(row, dict):
        return _bad_check("<invalid>", "reference row must be an object")
    name = row.get("name")
    if not isinstance(name, str) or name not in EXPECTED:
        return _bad_check(str(name), "unexpected reference name")
    status = row.get("status")
    if not isinstance(status, str) or status not in VALID_STATUSES:
        return _bad_check(name, "invalid reference status", status=status)
    check = {"reference": name, "outcome": "unresolved"}
    if status != "completed":
        check["reason"] = f"reference status is {status}"
        return check
    if row.get("returncode") != 0:
        return _bad_check(name, "completed reference has nonzero return code", returncode=row.get("returncode"))
    log_name = row.get("stdout_log")
    if not isinstance(log_name, str) or not log_name:
        return _bad_check(name, "completed reference has no stdout log")
    log = (root / log_name).resolve()
    try: log.relative_to(root.resolve())
    except ValueError:
        return _bad_check(name, "stdout log is outside project root")
    if not log.is_file():
        return _bad_check(name, "stdout log is missing", stdout_log=log_name)
    actual_hash = hashlib.sha256(log.read_bytes()).hexdigest()
    artifacts = row.get("artifacts")
    expected_hash = artifacts.get("stdout.log") if isinstance(artifacts, dict) else None
    if expected_hash is not None:
        if not isinstance(expected_hash, str) or len(expected_hash) != 64 or any(c not in "0123456789abcdefABCDEF" for c in expected_hash):
            return _bad_check(name, "stdout log hash is malformed", log_sha256=actual_hash)
        if actual_hash.lower() != expected_hash.lower():
            return _bad_check(name, "stdout log hash mismatch", expected_log_sha256=expected_hash, log_sha256=actual_hash)
    terminals, values, malformed = EXPECTED[name], {}, []
    for line_number, line in enumerate(log.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        tokens = line.split()
        if not tokens or tokens[0] not in terminals:
            continue
        if len(tokens) != 5:
            # Official scripts also print metadata such as ``gate gate`` and
            # ``drain last end``.  A numeric bias identifies a truncated
            # contact record; nonnumeric metadata is not a malformed row.
            if len(tokens) > 1:
                try:
                    float(tokens[1])
                except ValueError:
                    continue
                malformed.append(f"line {line_number}: expected 4 numeric values")
            continue
        try:
            parsed = [float(value) for value in tokens[1:]]
        except ValueError:
            # A five-field line whose bias field is not numeric is still
            # diagnostic output, rather than a contact record.
            try:
                float(tokens[1])
            except ValueError:
                continue
            malformed.append(f"line {line_number}: nonnumeric contact data")
            continue
        if not all(math.isfinite(value) for value in parsed):
            malformed.append(f"line {line_number}: nonfinite contact data")
            continue
        values[tokens[0]] = parsed
    if malformed:
        return _bad_check(name, "malformed contact data", malformed_rows=malformed, final_contact_rows=values)
    missing = sorted(set(terminals) - set(values))
    if missing:
        return _bad_check(name, "incomplete contact data", missing_terminals=missing, final_contact_rows=values)
    currents = [vals[-1] for vals in values.values()]
    scale = max((abs(value) for value in currents), default=0.0)
    balance = abs(sum(value / scale for value in currents)) / max(sum(abs(value / scale) for value in currents), 1e-30) if scale else 0.0
    bias_ok = all(abs(values[terminal][0] - bias) < 1e-12 for terminal, bias in terminals.items())
    check.update(outcome="pass" if bias_ok and balance < 1e-4 else "fail", final_contact_rows=values, relative_current_imbalance=balance, imbalance_tolerance=1e-4, expected_bias_volts=terminals, log_sha256=actual_hash)
    if not bias_ok:
        check["reason"] = "final contact bias does not match expected bias"
    elif balance >= 1e-4:
        check["reason"] = "current conservation tolerance exceeded"
    return check

def audit_report(report: Any, root: Path = ROOT, reference_report_sha256: str | None = None) -> dict[str, Any]:
    """Audit a device-reference report without writing files."""
    checks = []
    if not isinstance(report, dict):
        checks.append(_bad_check("<report>", "reference report must be an object"))
    elif report.get("schema") != "device-reference/1":
        checks.append(_bad_check("<report>", "unsupported or missing reference report schema"))
    elif not isinstance(report.get("references"), list):
        checks.append(_bad_check("<report>", "references must be a list"))
    else:
        rows = report["references"]
        names = [row.get("name") if isinstance(row, dict) else None for row in rows]
        for expected_name in EXPECTED:
            count = names.count(expected_name)
            if count == 0:
                checks.append(_bad_check(expected_name, "expected reference is missing"))
            elif count > 1:
                checks.append(_bad_check(expected_name, "expected reference is duplicated", count=count))
        checks.extend(_audit_row(row, root) for row in rows)
    outcomes = [check["outcome"] for check in checks]
    overall = "fail" if "fail" in outcomes else ("unresolved" if "unresolved" in outcomes else "pass")
    result = {"schema": "reference-audit/1", "outcome": overall, "scope": "Finite final contact data, expected final biases, and current conservation only; mesh convergence and 2D current normalization remain unqualified", "contact_columns": CONTACT_COLUMNS, "checks": checks}
    if reference_report_sha256 is not None:
        result["reference_report_sha256"] = reference_report_sha256
    return result

def main() -> int:
    source, destination = ROOT / "results/device-reference/latest.json", ROOT / "results/device-reference/audit.json"
    try:
        raw = source.read_bytes()
        result = audit_report(json.loads(raw), ROOT, hashlib.sha256(raw).hexdigest())
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        result = {"schema": "reference-audit/1", "outcome": "fail", "scope": "Finite final contact data, expected final biases, and current conservation only; mesh convergence and 2D current normalization remain unqualified", "contact_columns": CONTACT_COLUMNS, "checks": [_bad_check("<report>", "reference report could not be read", error=str(exc))]}
    destination.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"outcome": result["outcome"], "report": str(destination)}))
    return 0 if result["outcome"] == "pass" else 2

if __name__ == "__main__": raise SystemExit(main())
