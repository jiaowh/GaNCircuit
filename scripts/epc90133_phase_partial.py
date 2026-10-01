"""Test 8 supplement: PHASE-ball extremes at event A from the timing runs, including runs stopped by the timeout.

In test 8 run 1 the three 100 pF cases timed out in their timing runs, so they have no report metrics. Their raw
files were written up to the stop (2.07-3.09 us), past event A (Q1's turn-off command, about 1.88 us) for two of
them. This script reads each timing run's raw file directly (LTspice binary, header up to "Binary:"; a record
cut by the stop is dropped), takes event A's time from the high-side control source Vuc in its netlist, and
reports the raw PHASE-to-GND minimum and maximum in the same window as the test 7 reports (-5 ns to +60 ns), with
the minimum's half-width (below half the minimum). A run whose data end before the window ends is reported as
incomplete. These timing runs differ from the case runs only in their edge timing, so this is supplementary
evidence outside test 8's declared criteria. Simulated sensitivity results, not a safe limit.

    PYTHONPATH=src python scripts/epc90133_phase_partial.py
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CASES = ("G-m1-mid-Ls50", "G-m1-mid-Ls50-pin10", "G-m1-mid-Ls50-pin100", "G-m1-mid-Ls50-pin100-ms50",
         "G-m1-mid-pin100")
WINDOW_S = (-5e-9, 60e-9)


def read_raw(path):
    """Time and named real traces of an LTspice binary raw file, possibly truncated."""
    b = path.read_bytes()
    key = "Binary:\n".encode("utf-16-le")
    i = b.find(key)
    hdr = b[:i].decode("utf-16-le").splitlines()
    nv = int(next(l for l in hdr if l.startswith("No. Variables")).split()[-1])
    k = hdr.index("Variables:")
    names = [l.split("\t")[2].lower() for l in hdr[k + 1:k + 1 + nv]]
    data = b[i + len(key):]
    rec = 8 + 4 * (nv - 1)
    n = len(data) // rec
    arr = np.frombuffer(data[:n * rec], dtype=np.uint8).reshape(n, rec)
    t = np.abs(arr[:, :8].copy().view("<f8")[:, 0])
    v = arr[:, 8:].copy().view("<f4")
    return t, {nm: v[:, j - 1] for j, nm in enumerate(names) if j}


def event_a(cir):
    pw = re.search(r"^Vuc cu 0 PWL\((.*)\)", cir, re.M).group(1).split()
    pts = list(zip(map(float, pw[::2]), map(float, pw[1::2])))
    return next(pts[j][0] for j in range(1, len(pts)) if pts[j - 1][1] == 1 and pts[j][1] == 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", type=Path, default=ROOT / "runs/epc90133-switching-77ac08acba88")
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-test8-phase-partial.json")
    args = ap.parse_args()
    out = {}
    for case in CASES:
        d = args.run_dir / f"{case}-timing"
        raw = d / "bench.raw"
        if not raw.exists():
            out[case] = {"status": "no raw file"}
            continue
        te = event_a((d / "bench.cir").read_text(encoding="utf-8", errors="replace"))
        t, v = read_raw(raw)
        res = {"raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(), "data_end_s": float(t[-1]),
               "event_a_s": te}
        if t[-1] < te + WINDOW_S[1]:
            out[case] = {**res, "status": "incomplete: data end before the event A window ends"}
            continue
        ph = v["v(u80_ph)"] - v["v(u80_gnd)"]
        w = np.where((t > te + WINDOW_S[0]) & (t < te + WINDOW_S[1]))[0]
        i = w[np.argmin(ph[w])]
        j0 = j1 = i
        while j0 > 0 and ph[j0] < ph[i] / 2:
            j0 -= 1
        while j1 < len(ph) - 1 and ph[j1] < ph[i] / 2:
            j1 += 1
        out[case] = {**res, "status": "event A complete", "raw_min_V": float(ph[i]),
                     "raw_min_time_after_event_s": float(t[i] - te), "raw_min_half_width_s": float(t[j1] - t[j0]),
                     "raw_max_V": float(ph[w].max())}
        print(f"{case:28s} min {ph[i]:7.2f} V, half-width {(t[j1] - t[j0]) * 1e12:8.2f} ps, max {ph[w].max():6.2f} V")
    report = {"schema": "epc90133-test8-phase-partial/1", "run_directory": args.run_dir.relative_to(ROOT).as_posix(),
              "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "window_s": WINDOW_S, "rating_V": (-5.0, 85.0),
              "scope": "timing runs of test 8 run 1, event A only; supplementary to the declared criteria; "
                       "simulated PHASE-to-GND ball voltage of the unvalidated bench, not a safe limit",
              "cases": out}
    args.output.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
