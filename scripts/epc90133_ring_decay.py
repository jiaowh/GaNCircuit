"""Cycle-by-cycle decay and frequency of the simulated turn-on ring, against amplitude (existing traces only).

External audit, 2 October 2026: test 10's single local linearization does not account for the B/G transient
decay; before attributing that to amplitude dependence, read the existing transient traces cycle by cycle and
see whether later, smaller oscillations approach the local AC result. No simulation. Method declared here,
2 October 2026, before this script was first run on any trace:

Input: the saved rising-edge switch-node trace (V(q2_d), 25 ps grid, 0.1 mV resolution, -30 to +70 ns around
Q1's turn-on command) of the completed cases B-m1-mid-ms100, G-m1-mid and G-m1-mid-Ls50 in
results/gan/epc90133-switching-fullr.json, compared with the active-form local mode of test 10
(results/gan/epc90133-ringdown.json, networks B-m1-mid, G-m1-mid, G-m1-mid-Ls50).
Extrema: from the first maximum after the trace passes 50 % of the bus, every local extremum of the trace
(three-point test on the grid, refined by a parabola through it and its neighbours), keeping only alternating
max/min (a run of same-type extrema keeps the most extreme).
Moving baseline: each extremum's amplitude is a_k = |e_k - (e_{k-1} + e_{k+1}) / 2|, half the excursion from
the mean of its two neighbours, which removes a baseline that varies linearly over one cycle.
Per-cycle quantities, for k with k+2 available: f_k = 1 / (t_{k+2} - t_k); delta_k = ln(a_k / a_{k+2});
zeta_k = delta_k / sqrt(4 pi^2 + delta_k^2) (the transient bench's definition). Extrema with a_k below 0.05 V
(500 times the storage resolution) end the sequence.
Reported: the sequences; the Spearman rank correlation between a_k and zeta_k (positive: more damping at larger
amplitude); and the mean zeta and f over the last three cycles, compared with the local AC mode. Declared reading:
the late cycles "approach" the local mode if their mean zeta is within 25 % of it and their mean f within 3 %.
Approaching would support amplitude (or state) dependence of the decay within the model; not approaching would
point to a different mode or state rather than amplitude alone. Neither identifies a mechanism, and the voltage-
envelope decay read here is not the energy loss (that is the energy budget's question).

Correction after run 1 (2 October 2026; no number changes): a_k as defined above is the excursion of extremum
k from the mean of its neighbours, about the peak-to-peak amplitude, not half of it as first written. zeta_k and
f_k use ratios and times only and are unaffected; the reported amplitudes are about peak-to-peak.

    python scripts/epc90133_ring_decay.py
"""
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TRANSIENT = ROOT / "results/gan/epc90133-switching-fullr.json"
RINGDOWN = ROOT / "results/gan/epc90133-ringdown.json"
OUTPUT = ROOT / "results/gan/epc90133-ring-decay.json"
CASES = {"B-m1-mid-ms100": "B-m1-mid", "G-m1-mid": "G-m1-mid", "G-m1-mid-Ls50": "G-m1-mid-Ls50"}
VIN, A_MIN, LATE = 48.0, 0.05, 3


def extrema(t, v):
    start = int(np.argmax(v > 0.5 * VIN))
    out = []
    for i in range(max(start, 1), len(v) - 1):
        if (v[i] >= v[i - 1] and v[i] > v[i + 1]) or (v[i] <= v[i - 1] and v[i] < v[i + 1]):
            y0, y1, y2 = v[i - 1], v[i], v[i + 1]
            den = y0 - 2 * y1 + y2
            dx = 0.5 * (y0 - y2) / den if den != 0 else 0.0
            dt = t[1] - t[0]
            out.append((t[i] + dx * dt, y1 - 0.25 * (y0 - y2) * dx, "max" if y1 > y0 else "min"))
    # first maximum, then strictly alternating
    while out and out[0][2] != "max":
        out.pop(0)
    alt = []
    for e in out:
        if alt and alt[-1][2] == e[2]:
            if (e[2] == "max" and e[1] > alt[-1][1]) or (e[2] == "min" and e[1] < alt[-1][1]):
                alt[-1] = e
        else:
            alt.append(e)
    return alt


def spearman(x, y):
    rx, ry = np.argsort(np.argsort(x)), np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1]) if len(x) > 2 else None


def main():
    tr_rep = json.loads(TRANSIENT.read_text(encoding="utf-8"))
    rd_rep = json.loads(RINGDOWN.read_text(encoding="utf-8"))
    out = {}
    for case, net in CASES.items():
        tr = tr_rep["cases"][case]["traces"]
        t = tr["start_s"] + tr["step_s"] * np.arange(len(tr["rising_V"]))
        v = np.array(tr["rising_V"])
        ex = extrema(t, v)
        amps = [abs(ex[k][1] - 0.5 * (ex[k - 1][1] + ex[k + 1][1])) for k in range(1, len(ex) - 1)]
        pts = [(ex[k][0], a) for k, a in zip(range(1, len(ex) - 1), amps)]
        cut = next((i for i, (_, a) in enumerate(pts) if a < A_MIN), len(pts))
        pts = pts[:cut]
        cyc = []
        for k in range(len(pts) - 2):
            (t0, a0), (t2, a2) = pts[k], pts[k + 2]
            d = math.log(a0 / a2)
            cyc.append({"t_s": t0, "amplitude_V": a0, "f_Hz": 1 / (t2 - t0), "zeta": d / math.sqrt(4 * math.pi ** 2 + d ** 2)})
        ac = rd_rep["cases"][net]["active"]
        late = cyc[-LATE:] if len(cyc) >= LATE else cyc
        lz = float(np.mean([c["zeta"] for c in late])) if late else None
        lf = float(np.mean([c["f_Hz"] for c in late])) if late else None
        out[case] = {"cycles": cyc, "n_cycles": len(cyc),
                     "spearman_amplitude_zeta": spearman([c["amplitude_V"] for c in cyc], [c["zeta"] for c in cyc]),
                     "first_cycle": cyc[0] if cyc else None, "late_mean_zeta": lz, "late_mean_f_Hz": lf,
                     "late_amplitude_range_V": [late[-1]["amplitude_V"], late[0]["amplitude_V"]] if late else None,
                     "local_ac": {"network": net, "zeta": ac["fit"]["zeta"], "f_Hz": ac["peak_frequency_Hz"]},
                     "approaches_local_mode": (lz is not None and abs(lz / ac["fit"]["zeta"] - 1) <= 0.25
                                               and abs(lf / ac["peak_frequency_Hz"] - 1) <= 0.03)}
        r = out[case]
        print(f"{case:16s} cycles {r['n_cycles']:2d} rho {r['spearman_amplitude_zeta']} | first a {cyc[0]['amplitude_V']:.2f} V "
              f"zeta {cyc[0]['zeta']:.4f} f {cyc[0]['f_Hz'] / 1e6:.1f} | late a {r['late_amplitude_range_V']} zeta {lz:.4f} "
              f"f {lf / 1e6:.1f} | AC zeta {ac['fit']['zeta']:.4f} f {ac['peak_frequency_Hz'] / 1e6:.1f} -> {r['approaches_local_mode']}")
    report = {"schema": "epc90133-ring-decay/1",
              "scope": "cycle-by-cycle envelope decay of saved simulated traces against test 10's local mode; no simulation; "
                       "voltage-envelope decay, not energy loss",
              "inputs": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in (TRANSIENT, RINGDOWN)},
              "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "cases": out}
    OUTPUT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
