"""Test 7 follow-up: are the driver PHASE-ball extremes waveforms or sub-picosecond artefacts?

Test 7's report gives the raw extremes of V(U80.PH) - V(U80.GND) around each event. In the first run the minima
(-8 V on G, -24 and -28 V with package inductance) sat 10.005 ns after Q1's turn-off command, when the ideal
low-side driver stage switches, and lasted well under a picosecond. This script reads the saved raw files and
reports, per case and event, the raw minimum and maximum, the half-width of the minimum (against 0 V), and the
extremes after a 10 ps moving average on a 1 ps grid. The 10 ps window is declared here, before its use in any
conclusion: it is ten times shorter than the fastest physical edge in the bench (the 10 GHz damping corner
gives about 16 ps) and far longer than the artefacts. The uP1966E absolute maximum PHASE-to-GND is -5 V to
+85 V (datasheet p. 7). Simulated sensitivity results, not a safe limit.

    PYTHONPATH=src python scripts/epc90133_phase_check.py
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from circuit_tools.ltspice import parse_raw

ROOT = Path(__file__).resolve().parents[1]
AVERAGE_S = 10e-12
RATING_V = (-5.0, 85.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", type=Path, default=ROOT / "results/gan/epc90133-switching-gateloop.json")
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-test7-phase-check.json")
    args = ap.parse_args()
    rep = json.loads(args.report.read_text(encoding="utf-8"))
    ev_dir = ROOT / rep["evidence_directory"]
    out = {}
    for case, r in rep["cases"].items():
        raw = ev_dir / case / "bench.raw"
        if not r.get("usable") or not raw.exists():
            continue
        s = parse_raw(raw).step(0)
        if "v(u80_ph)" not in s:
            continue
        t = np.array(s["time"])
        ph = np.array(s["v(u80_ph)"]) - np.array(s["v(u80_gnd)"])
        res = {"raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest()}
        for tag, key in (("event_a", "t_off1"), ("event_b", "t_on2")):
            te = r["times_s"][key]
            w = np.where((t > te - 5e-9) & (t < te + 60e-9))[0]
            i = w[np.argmin(ph[w])]
            j0 = j1 = i
            if ph[i] < 0:
                while j0 > 0 and ph[j0] < ph[i] / 2:
                    j0 -= 1
                while j1 < len(ph) - 1 and ph[j1] < ph[i] / 2:
                    j1 += 1
            g = np.arange(te - 5e-9, te + 60e-9, 1e-12)
            k = int(round(AVERAGE_S / 1e-12))
            ys = np.convolve(np.interp(g, t, ph), np.ones(k) / k, mode="valid")
            res[tag] = {"raw_min_V": float(ph[i]), "raw_min_time_after_event_s": float(t[i] - te),
                        "raw_min_half_width_s": float(t[j1] - t[j0]), "raw_max_V": float(ph[w].max()),
                        "averaged_min_V": float(ys.min()), "averaged_max_V": float(ys.max()),
                        "averaged_within_rating": bool(RATING_V[0] <= ys.min() and ys.max() <= RATING_V[1])}
        out[case] = res
        print(case, {e: (round(res[e]["raw_min_V"], 2), round(res[e]["averaged_min_V"], 2),
                         round(res[e]["averaged_max_V"], 1)) for e in ("event_a", "event_b")})
    report = {"schema": "epc90133-phase-check/1", "source_report": args.report.relative_to(ROOT).as_posix(),
              "source_report_sha256": hashlib.sha256(args.report.read_bytes()).hexdigest(),
              "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "average_window_s": AVERAGE_S, "rating_V": RATING_V,
              "scope": "simulated PHASE-to-GND ball voltage of the unvalidated bench; not a safe limit", "cases": out}
    args.output.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
