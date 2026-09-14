#!/usr/bin/env python3
"""Run fixed known-answer SPICE fixtures and retain their acceptance evidence."""
import argparse
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from circuit_tools.adapters import run_ngspice


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", default="ngspice")
    parser.add_argument("--output", type=Path, default=ROOT / "results/toolset/circuit-fixtures.json")
    args = parser.parse_args()
    run_root = ROOT / "runs" / ("fixtures-" + uuid.uuid4().hex)
    checks = []
    for name in ("divider", "custom_diode"):
        source = ROOT / "examples" / (name + ".cir")
        result = run_ngspice(source, run_root / name, executable=args.executable,
                             result_file="measurements.dat", timeout_s=30)
        row = {"fixture": name, "run": asdict(result), "outcome": "unresolved"}
        if result.status == "completed" and result.measurements:
            columns = list(result.measurements.values())
            if name == "divider":
                observed = columns[-1]
                error = abs(observed[0] - 1.0) if len(observed) == 1 else math.inf
                row.update(measurement={"value": observed[0], "unit": "V", "definition": "v(out) at OP"},
                           expected=1.0, absolute_error=error, tolerance=1e-9,
                           outcome="pass" if error <= 1e-9 else "fail")
            else:
                volts, source_current = columns[-2:]
                # ngspice-42/src/include/ngspice/const.h (pinned source).
                thermal_voltage = 1.38064852e-23 * 300 / 1.6021766208e-19
                expected = [1e-12 * math.expm1(v / thermal_voltage) for v in volts]
                errors = [abs(-i - ref) / max(abs(ref), 1e-12)
                          for i, ref in zip(source_current, expected)]
                error = max(errors)
                row.update(max_scaled_error=error, tolerance=1e-4,
                           expected_points=11, observed_points=len(volts),
                           definition="-i(V1) vs IS*(exp(V/(k*T/q))-1), IS=1e-12 A, T=300 K",
                           outcome="pass" if error <= 1e-4 and len(volts) == 11 else "fail")
        checks.append(row)
    report = {"schema": "circuit-fixtures/1", "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "scope": "Known-answer circuit and native custom diode model; no TCAD or NMOS co-design claim",
              "outcome": ("pass" if all(c["outcome"] == "pass" for c in checks)
                          else "fail" if any(c["outcome"] == "fail" for c in checks) else "unresolved"),
              "checks": checks}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"outcome": report["outcome"], "report": str(args.output), "checks": [{"fixture": c["fixture"], "outcome": c["outcome"]} for c in checks]}, indent=2))
    return 0 if report["outcome"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
