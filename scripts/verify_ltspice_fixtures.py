#!/usr/bin/env python3
"""Run known-answer LTspice fixtures through the adapter and retain the evidence.

Each fixture has an analytical answer and a tolerance fixed here before the
run. Together they cover every analysis the EPC benches use: operating point,
transient with .meas, complex AC output, nested DC sweeps, a nonlinear diode,
and binary/ASCII raw agreement.
"""
import argparse
import bisect
from dataclasses import asdict
import cmath
import hashlib
import json
import math
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from circuit_tools.ltspice import ltspice_capability, parse_raw, run_ltspice

FIXTURES = ROOT / "examples" / "ltspice"
K_OVER_Q = 1.380649e-23 / 1.602176634e-19  # exact SI values


def interp(xs, ys, x):
    i = min(max(bisect.bisect_left(xs, x), 1), len(xs) - 1)
    x0, x1, y0, y1 = xs[i - 1], xs[i], ys[i - 1], ys[i]
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def check(name, observed, expected, tolerance, definition, unit):
    error = abs(observed - expected) if observed is not None else math.inf
    return {"check": name, "definition": definition, "unit": unit, "observed": observed,
            "expected": expected, "absolute_error": error, "tolerance": tolerance,
            "outcome": "pass" if error <= tolerance else "fail"}


def evaluate(name, result):
    m = result.measurements
    if name == "divider_op":
        return [check("v_out", (m.get("v(out)") or [None])[0], 1.0, 1e-6, "v(out) at .op", "V")]
    if name == "rc_tran":
        rows = [check("meas_vtau", (m.get("vtau") or [None])[0], 1 - math.exp(-1), 1e-3,
                      ".meas FIND V(out) AT 1 ms", "V")]
        t, v = m.get("time", []), m.get("v(out)", [])
        worst = max((abs(interp(t, v, x) - (1 - math.exp(-x / 1e-3)))
                     for x in [k * 1e-4 for k in range(1, 50)]), default=math.inf) if t else math.inf
        rows.append({"check": "trace", "definition": "max |v(out) - (1-exp(-t/RC))| at 0.1..4.9 ms",
                     "unit": "V", "absolute_error": worst, "tolerance": 2e-3,
                     "outcome": "pass" if worst <= 2e-3 else "fail"})
        return rows
    if name == "rc_ac":
        # LTspice sorts .ac list frequencies, so select the point by frequency, not position.
        f0 = 1 / (2 * math.pi * 1e3 * 1e-6)
        freqs = [abs(f) for f in m.get("frequency", [])]
        k = min(range(len(freqs)), key=lambda j: abs(freqs[j] - f0)) if freqs else None
        v = m["v(out)"][k] if k is not None and abs(freqs[k] - f0) <= 1e-9 * f0 else None
        mag = abs(v) if v is not None else None
        phase = math.degrees(cmath.phase(v)) if v is not None else None
        return [check("magnitude", mag, 1 / math.sqrt(2), 1e-6, "|v(out)| at f = 1/(2 pi RC)", "V/V"),
                check("phase", phase, -45.0, 1e-4, "phase of v(out) at f = 1/(2 pi RC)", "deg")]
    if name == "nested_dc":
        raw = parse_raw(result.result_path)
        va, vb, i = m.get("v(a)", []), m.get("v(b)", []), m.get("i(r1)", [])
        worst = max((abs(x - (a - b) / 2000) for a, b, x in zip(va, vb, i)), default=math.inf)
        shape_ok = raw.n_steps == 2 and all(len(raw.step(s)["v(a)"]) == 3 for s in range(2))
        return [{"check": "current", "definition": "max |I(R1) - (V(a)-V(b))/2k| over 6 points",
                 "unit": "A", "absolute_error": worst, "tolerance": 1e-12,
                 "outcome": "pass" if worst <= 1e-12 and len(i) == 6 else "fail"},
                {"check": "step_split", "definition": "2 outer steps of 3 inner points each",
                 "observed": [len(raw.step(s)["v(a)"]) for s in range(raw.n_steps)],
                 "outcome": "pass" if shape_ok else "fail"}]
    if name == "diode_dc":
        vt = K_OVER_Q * 300.0
        v, i = m.get("v(anode)", []), m.get("i(d1)", [])
        errors = [abs(x - 1e-12 * math.expm1(u / vt)) / max(1e-12 * math.expm1(u / vt), 1e-12)
                  for u, x in zip(v, i)]
        worst = max(errors, default=math.inf)
        return [{"check": "shockley", "definition": "max |I(D1) - IS*(exp(V/Vt)-1)| / max(|ref|, 1e-12 A), T = 300 K",
                 "unit": "1", "absolute_error": worst, "tolerance": 1e-4, "points": len(i),
                 "outcome": "pass" if worst <= 1e-4 and len(i) == 11 else "fail"}]
    raise KeyError(name)


def summary(result):
    """Run record without bulky traces; the full data stay in the run directory."""
    d = asdict(result)
    d["measurements"] = sorted(d["measurements"])
    return d


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", default=None)
    parser.add_argument("--output", type=Path, default=ROOT / "results/toolset/ltspice-fixtures.json")
    args = parser.parse_args()
    run_root = ROOT / "runs" / ("ltspice-fixtures-" + uuid.uuid4().hex)
    checks, results = [], {}
    for name in ("divider_op", "rc_tran", "rc_ac", "nested_dc", "diode_dc"):
        result = run_ltspice(FIXTURES / (name + ".cir"), run_root / name, executable=args.executable)
        results[name] = result
        row = {"fixture": name, "run": summary(result), "checks": [], "outcome": "unresolved"}
        if result.status == "completed":
            row["checks"] = evaluate(name, result)
            row["outcome"] = "pass" if all(c["outcome"] == "pass" for c in row["checks"]) else "fail"
        checks.append(row)
    # Binary and ASCII raw output of the same bench must agree to float32 precision.
    binary = results["rc_tran"]
    ascii_run = run_ltspice(FIXTURES / "rc_tran.cir", run_root / "rc_tran_ascii", executable=args.executable,
                            ascii_raw=True)
    row = {"fixture": "rc_tran_ascii", "run": summary(ascii_run), "checks": [], "outcome": "unresolved"}
    if ascii_run.status == "completed" and binary.status == "completed":
        b, a = binary.measurements, ascii_run.measurements
        same_len = len(a.get("v(out)", [])) == len(b.get("v(out)", []))
        worst = max((abs(x - y) for x, y in zip(a["v(out)"], b["v(out)"])), default=math.inf) if same_len else math.inf
        row["checks"] = [{"check": "binary_vs_ascii", "definition": "max |v(out)| difference, same bench",
                          "unit": "V", "absolute_error": worst, "tolerance": 1e-6,
                          "outcome": "pass" if worst <= 1e-6 else "fail"}]
        row["outcome"] = row["checks"][0]["outcome"]
    checks.append(row)
    outcome = ("pass" if all(c["outcome"] == "pass" for c in checks)
               else "fail" if any(c["outcome"] == "fail" for c in checks) else "unresolved")
    report = {"schema": "ltspice-fixtures/1",
              "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "tool": asdict(ltspice_capability(args.executable)),
              "scope": "Known-answer circuits for the LTspice batch adapter; no vendor-model or device claim",
              "outcome": outcome, "evidence_directory": str(run_root.relative_to(ROOT)), "checks": checks}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False, default=str) + "\n")
    print(json.dumps({"outcome": outcome, "report": str(args.output),
                      "fixtures": [{"fixture": c["fixture"], "outcome": c["outcome"],
                                    "message": c["run"].get("message")} for c in checks]}, indent=2))
    return 0 if outcome == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
