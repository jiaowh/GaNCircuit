#!/usr/bin/env python3
"""Independent finite/current-balance checks on official reference logs."""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / "results/device-reference/latest.json"
    report = json.loads(source.read_text())
    expected = {"official_diode_1d": {"top": .5, "bot": 0.0},
                "official_planar_mos_2d": {"gate": .5, "drain": .5, "source": 0.0, "body": 0.0}}
    checks = []
    for row in report["references"]:
        terminals = expected[row["name"]]
        values = {}
        check = {"reference": row["name"], "outcome": "unresolved"}
        if row["status"] == "completed":
            log = ROOT / row["stdout_log"]
            for line in log.read_text().splitlines():
                tokens = line.split()
                if len(tokens) == 5 and tokens[0] in terminals:
                    try:
                        parsed = [float(x) for x in tokens[1:]]
                    except ValueError:
                        continue
                    values[tokens[0]] = parsed
            finite = set(values) == set(terminals) and all(math.isfinite(v) for vals in values.values() for v in vals)
            if finite:
                balance = abs(sum(vals[-1] for vals in values.values())) / max(sum(abs(vals[-1]) for vals in values.values()), 1e-30)
                bias_ok = all(abs(values[name][0] - bias) < 1e-12 for name, bias in terminals.items())
                check.update(outcome="pass" if bias_ok and balance < 1e-4 else "fail",
                             final_contact_rows=values, relative_current_imbalance=balance,
                             imbalance_tolerance=1e-4, expected_bias_volts=terminals,
                             log_sha256=hashlib.sha256(log.read_bytes()).hexdigest())
        checks.append(check)
    result = {"schema": "reference-audit/1", "outcome": "pass" if all(c["outcome"] == "pass" for c in checks) else "unresolved",
              "scope": "Finite final contact data, expected final biases, and current conservation only; mesh convergence and 2D current normalization remain unqualified",
              "contact_columns": ["bias_V", "electron_current_native", "hole_current_native", "total_current_native"],
              "reference_report_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "checks": checks}
    destination = source.with_name("audit.json")
    destination.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"outcome": result["outcome"], "report": str(destination)}))
    return 0 if result["outcome"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
