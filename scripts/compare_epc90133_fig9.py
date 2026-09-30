#!/usr/bin/env python3
"""Compare simulated EPC90133 switch-node edges with the digitized QSG Fig. 9 (G3 diagnosis).

Inputs: results/gan/epc90133-qsg-fig9.json (scripts/digitize_epc90133_qsg_fig9.py) and a switching
report with saved traces (scripts/epc90133_switching.py --study causes).

Specification (30 September 2026, written before the first comparison):

* Measurement response. EPC does not state the probe or oscilloscope behind Fig. 9. The simulated
  V(SW) (ideal probe at the Q2 pads) is passed through a zero-phase Gaussian response with -3 dB
  bandwidth B: |H(f)| = exp(-(ln 2 / 2) (f / B)^2), i.e. a Gaussian impulse response with
  sigma = sqrt(ln 2) / (2 pi B) and a 10-90 % rise time of about 0.34 / B. B = none, 2 GHz, 1 GHz,
  500 MHz and 350 MHz. A Gaussian is the textbook approximation of a multi-stage scope front end;
  a probe's ground-lead resonance is not a Gaussian and is not represented.
* Metrics use the digitizer's definitions: settled levels 25-45 ns either side of the 50 % crossing
  (or the available part of that window, at least 2 ns), 10-90 % edge times between them, the rising
  edge's peak above its settled high level, the damped-cosine fit of its ringing from the first crest
  to 25 ns, the dead-time plateau (more than 1 V below the settled low level, 20-1 ns before the rise),
  and the falling edge's undershoot below its settled low level.
* Fig. 9's volt scale fails its 48 V check (swing 45.8 V and 44.5 V), so voltages are also compared
  as a fraction of each edge's swing.
* "Resembles the measurement" (judgement criteria, fixed now): rise and fall time within 25 %,
  rising overshoot within 3 V and within 0.05 of swing, ringing frequency within 10 %, damping ratio
  within a factor 1.5. These are not validation tolerances. The probe is unknown, so a case that
  resembles the measurement under some bandwidth is consistent with it, not identified by it.

Added 30 September 2026 after an external review (no criterion above changed):
* a case whose switching checks failed ("usable" false) keeps its metrics for inspection but is
  structurally excluded: it receives no "resembles" or consistency verdict;
* each usable case also gets, per metric, "consistent with the declared extraction range" (second review:
  this is a sensitivity range over the digitizer's processing choices, not a complete uncertainty interval;
  it excludes the unknown probe response, the failed volt-scale check and other raster or fit errors): the rule in
  scripts/digitize_epc90133_qsg_fig9.py (the measured range over its extraction choices, widened by one
  pixel for time and voltage metrics);
* the report binds its inputs by hash (the digitized figure, every switching report, and the imported
  digitizer module), and writes results/gan/epc90133-fig9-summary.md, the single source for headline
  tables in the documentation.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from digitize_epc90133_qsg_fig9 import crossing, extrema, fit_ring  # noqa: E402

BANDWIDTHS = (None, 2e9, 1e9, 500e6, 350e6)
SETTLE = (25e-9, 45e-9)
CRITERIA = {"edge_rel": 0.25, "overshoot_V": 3.0, "overshoot_frac": 0.05, "freq_rel": 0.10, "damping_factor": 1.5}


def gaussian(v, dt, bw):
    if bw is None:
        return np.asarray(v, float)
    sigma = math.sqrt(math.log(2)) / (2 * math.pi * bw)
    n = int(math.ceil(5 * sigma / dt))
    k = np.arange(-n, n + 1) * dt
    h = np.exp(-0.5 * (k / sigma) ** 2)
    h /= h.sum()
    padded = np.concatenate([np.full(n, v[0]), v, np.full(n, v[-1])])
    return np.convolve(padded, h, mode="valid")


def settled(t, v, lo, hi):
    sel = (t >= lo) & (t <= hi)
    if np.sum(sel) == 0 or t[sel][-1] - t[sel][0] < 2e-9:
        return None
    return float(np.mean(v[sel]))


def edge(t, v, rising):
    """Digitizer-equivalent metrics on a volt trace; the settled low level is the zero."""
    first, last = float(np.median(v[:20])), float(np.median(v[-20:]))
    t50 = crossing(list(zip(t, v)), 0.5 * (first + last), rising)
    rel = t - t50
    before = settled(rel, v, -SETTLE[1], -SETTLE[0])
    after = settled(rel, v, SETTLE[0], SETTLE[1])
    if before is None or after is None:
        return None
    low, high = (before, after) if rising else (after, before)
    vv = v - low
    hi = high - low
    tr = list(zip(rel, vv))
    t50 = crossing(tr, 0.5 * hi, rising)
    tr = [(a - t50, b) for a, b in tr]
    t10, t90 = crossing(tr, 0.1 * hi, rising), crossing(tr, 0.9 * hi, rising)
    out = {"swing_V": hi, "edge_10_90_s": abs(t90 - t10) if t10 is not None and t90 is not None else None}
    ring = [(a, b) for a, b in tr if 0 <= a <= 30e-9]
    if rising:
        pk_t, pk_v = max(ring, key=lambda p: p[1])
        out.update(overshoot_above_settled_V=pk_v - hi, overshoot_fraction=(pk_v - hi) / hi)
        ext = extrema(ring, hi, True)
        fit = fit_ring(tr, hi, ext[0][0] if ext else pk_t)
        if fit and fit.get("frequency_Hz"):
            out["ring_frequency_Hz"] = fit["frequency_Hz"]
            out["ring_decay_time_s"] = fit["decay_time_s"]
            out["ring_damping_ratio"] = 1 / (2 * math.pi * fit["frequency_Hz"] * fit["decay_time_s"])
            out["ring_fit_rms_V"] = fit["fit_rms_V"]
        dip = [(a, b) for a, b in tr if -20e-9 <= a <= -1e-9 and b < -1.0]
        if dip:
            out["plateau_duration_s"] = dip[-1][0] - dip[0][0]
            out["plateau_mean_V"] = float(np.mean([b for _, b in dip]))
    else:
        pk_t, pk_v = min(ring, key=lambda p: p[1])
        out.update(undershoot_below_settled_V=-pk_v, undershoot_fraction=-pk_v / hi)
    return out


def measured(fig9):
    r, f = fig9["panels"]["rising"]["metrics"], fig9["panels"]["falling"]["metrics"]
    fit = r["ring_fit"]
    return {
        "rising": {"swing_V": r["swing_V"], "edge_10_90_s": r["edge_10_90_s"],
                   "overshoot_above_settled_V": r["overshoot_above_settled_V"],
                   "overshoot_fraction": r["overshoot_above_settled_V"] / r["swing_V"],
                   "ring_frequency_Hz": fit["frequency_Hz"], "ring_decay_time_s": fit["decay_time_s"],
                   "ring_damping_ratio": 1 / (2 * math.pi * fit["frequency_Hz"] * fit["decay_time_s"]),
                   "plateau_duration_s": r["reverse_conduction_plateau"]["duration_s"],
                   "plateau_mean_V": r["reverse_conduction_plateau"]["mean_V"]},
        "falling": {"swing_V": f["swing_V"], "edge_10_90_s": f["edge_10_90_s"],
                    "undershoot_below_settled_V": f["undershoot_below_settled_V"],
                    "undershoot_fraction": f["undershoot_below_settled_V"] / f["swing_V"]}}


PIXEL_METRICS = {"edge_10_90_s": "s_per_px", "overshoot_above_settled_V": "V_per_px",
                 "undershoot_below_settled_V": "V_per_px", "plateau_duration_s": "s_per_px", "plateau_mean_V": "V_per_px"}
FIT_METRICS = ("ring_frequency_Hz", "ring_damping_ratio", "overshoot_fraction")


def consistency(sim, fig9):
    """Per metric: is the simulated value inside the declared extraction range (see the digitizer's rule)?"""
    out = {}
    for kind in ("rising", "falling"):
        u = fig9["panels"][kind]["uncertainty"]
        for k in list(PIXEL_METRICS) + list(FIT_METRICS):
            if k not in u["ranges"] or sim[kind].get(k) is None:
                continue
            lo, hi = u["ranges"][k]["min"], u["ranges"][k]["max"]
            pad = u["resolution"][PIXEL_METRICS[k]] if k in PIXEL_METRICS else 0.0
            v = sim[kind][k]
            out[f"{kind}.{k}"] = {"value": v, "range": [lo - pad, hi + pad], "consistent": bool(lo - pad <= v <= hi + pad)}
    return out


def resembles(sim, meas):
    r, f, mr, mf = sim["rising"], sim["falling"], meas["rising"], meas["falling"]
    c = {}
    c["rise_time"] = r.get("edge_10_90_s") is not None and abs(r["edge_10_90_s"] / mr["edge_10_90_s"] - 1) <= CRITERIA["edge_rel"]
    c["fall_time"] = f.get("edge_10_90_s") is not None and abs(f["edge_10_90_s"] / mf["edge_10_90_s"] - 1) <= CRITERIA["edge_rel"]
    c["overshoot"] = (abs(r["overshoot_above_settled_V"] - mr["overshoot_above_settled_V"]) <= CRITERIA["overshoot_V"]
                      and abs(r["overshoot_fraction"] - mr["overshoot_fraction"]) <= CRITERIA["overshoot_frac"])
    c["ring_frequency"] = r.get("ring_frequency_Hz") is not None and abs(r["ring_frequency_Hz"] / mr["ring_frequency_Hz"] - 1) <= CRITERIA["freq_rel"]
    c["damping"] = r.get("ring_damping_ratio") is not None and \
        1 / CRITERIA["damping_factor"] <= r["ring_damping_ratio"] / mr["ring_damping_ratio"] <= CRITERIA["damping_factor"]
    c = {k: bool(v) for k, v in c.items()}
    c["all"] = all(c.values())
    return c


def evaluate_case(case, fig9, meas):
    """Metrics per bandwidth; verdicts only for a case whose switching checks all passed (usable is True)."""
    tr = case.get("traces")
    if not tr:
        return {"usable": False, "reason": case.get("error") or "no traces"}
    usable = case.get("usable") is True
    t = tr["start_s"] + tr["step_s"] * np.arange(len(tr["rising_V"]))
    per_bw = {}
    for bw in BANDWIDTHS:
        key = "none" if bw is None else f"{bw / 1e6:g}MHz"
        m = {k: edge(t, gaussian(np.array(tr[f"{k}_V"]), tr["step_s"], bw), k == "rising") for k in ("rising", "falling")}
        if m["rising"] is None or m["falling"] is None:
            per_bw[key] = {"metrics": m, "resembles": None, "consistency": None, "excluded": "metrics unavailable"}
        elif not usable:
            per_bw[key] = {"metrics": m, "resembles": None, "consistency": None,
                           "excluded": "switching checks failed; kept for inspection only"}
        else:
            per_bw[key] = {"metrics": m, "resembles": resembles(m, meas), "consistency": consistency(m, fig9)}
    return {"usable": usable, "checks": case.get("checks"), "parameters": case.get("parameters"), "bandwidths": per_bw}


def summary_md(report, fig9):
    """Headline table (ideal probe) and criterion outcomes over all bandwidths, generated from this report."""
    def f(v, sc, d):
        return "–" if v is None else f"{v * sc:.{d}f}"

    def row(label, r, fl, note=""):
        return (f"| {label} | {f(r.get('edge_10_90_s'), 1e9, 2)} | {f(r.get('overshoot_above_settled_V'), 1, 1)} | "
                f"{f(r.get('ring_frequency_Hz'), 1e-6, 0)} | {f(r.get('ring_damping_ratio'), 1, 3)} | "
                f"{f(fl.get('edge_10_90_s'), 1e9, 2)} | {f(r.get('plateau_duration_s'), 1e9, 1)} ns, "
                f"{f(r.get('plateau_mean_V'), 1, 1)} V | {note} |")

    u = {k: fig9["panels"][k]["uncertainty"]["ranges"] for k in ("rising", "falling")}

    def rng(kind, k, sc, d):
        return f"{u[kind][k]['min'] * sc:.{d}f}–{u[kind][k]['max'] * sc:.{d}f}"
    meas = report["measured"]
    lines = ["<!-- generated by scripts/compare_epc90133_fig9.py; do not edit -->",
             f"Inputs: {', '.join(report['inputs']['sim'])}; digitized figure sha256 {report['inputs']['fig9_sha256'][:12]}.",
             "",
             "| Case | tr (ns) | overshoot (V) | f (MHz) | ζ | tf (ns) | plateau | criteria passed at any probe bandwidth |",
             "|---|---|---|---|---|---|---|---|",
             row("**QSG Fig. 9**", meas["rising"], meas["falling"], "measured"),
             f"| declared extraction range | {rng('rising', 'edge_10_90_s', 1e9, 2)} | {rng('rising', 'overshoot_above_settled_V', 1, 2)} | "
             f"{rng('rising', 'ring_frequency_Hz', 1e-6, 0)} | {rng('rising', 'ring_damping_ratio', 1, 3)} | "
             f"{rng('falling', 'edge_10_90_s', 1e9, 2)} | {rng('rising', 'plateau_duration_s', 1e9, 2)} ns | "
             f"one pixel: {fig9['panels']['rising']['uncertainty']['resolution']['s_per_px'] * 1e9:.2f} ns, "
             f"{fig9['panels']['rising']['uncertainty']['resolution']['V_per_px']:.2f} V |"]
    for name, r in report["cases"].items():
        if "bandwidths" not in r:
            lines.append(f"| {name} | not run to completion: {r['reason']} | | | | | | excluded |")
            continue
        e = r["bandwidths"]["none"]
        if not r["usable"]:
            lines.append(row(name, e["metrics"]["rising"], e["metrics"]["falling"], "excluded: checks failed"))
            continue
        passed = sorted({k for b in r["bandwidths"].values() if b["resembles"] for k, v in b["resembles"].items()
                         if v and k != "all"})
        allbw = [b for b, v in r["bandwidths"].items() if v["resembles"] and v["resembles"]["all"]]
        note = ", ".join(passed) or "none"
        if allbw:
            note += f"; ALL criteria at {', '.join(allbw)}"
        lines.append(row(name, e["metrics"]["rising"], e["metrics"]["falling"], note))
    lines += ["", "Ideal probe values; ζ from the damped-cosine fit. Criteria and the digitization rule: see "
              "scripts/compare_epc90133_fig9.py and scripts/digitize_epc90133_qsg_fig9.py.", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fig9", type=Path, default=ROOT / "results/gan/epc90133-qsg-fig9.json")
    ap.add_argument("--sim", type=Path, nargs="+", default=[ROOT / "results/gan/epc90133-switching-causes.json"],
                    help="switching reports; a later file's case replaces an earlier case of the same name")
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-fig9-comparison.json")
    ap.add_argument("--summary", type=Path, default=ROOT / "results/gan/epc90133-fig9-summary.md")
    args = ap.parse_args()
    fig9 = json.loads(args.fig9.read_text(encoding="utf-8"))
    sim = {"cases": {}}
    for f in args.sim:
        sim["cases"].update(json.loads(f.read_text(encoding="utf-8"))["cases"])
    meas = measured(fig9)
    rows = {name: evaluate_case(case, fig9, meas) for name, case in sim["cases"].items()}
    report = {
        "schema": "epc90133-fig9-comparison/1",
        "inputs": {"fig9": args.fig9.resolve().relative_to(ROOT).as_posix(), "fig9_sha256": hashlib.sha256(args.fig9.read_bytes()).hexdigest(),
                   "sim": {f.resolve().relative_to(ROOT).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest() for f in args.sim},
                   "modules": {m: hashlib.sha256((ROOT / m).read_bytes()).hexdigest()
                               for m in ("scripts/digitize_epc90133_qsg_fig9.py",)}},
        "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "criteria": CRITERIA, "measured": meas,
        "note": ("Diagnostic comparison, not an acceptance test: Fig. 9's probe and probing point are unknown and its "
                 "volt scale fails the 48 V check. See the module docstring."),
        "cases": rows,
    }
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    args.summary.write_text(summary_md(report, fig9), encoding="utf-8")

    def fmt(m):
        r, f = m["rising"], m["falling"]
        return (f"tr {r['edge_10_90_s'] * 1e9:5.2f} tf {f['edge_10_90_s'] * 1e9:5.2f} ns  os {r['overshoot_above_settled_V']:5.1f} V "
                f"({r['overshoot_fraction']:.3f})  f {r.get('ring_frequency_Hz', float('nan')) / 1e6:5.0f} MHz  "
                f"zeta {r.get('ring_damping_ratio', float('nan')):.3f}  us {f['undershoot_below_settled_V']:4.1f} V  "
                f"plateau {r.get('plateau_duration_s', float('nan')) * 1e9:4.1f} ns {r.get('plateau_mean_V', float('nan')):5.2f} V")
    print(f"{'Fig. 9':34s} {fmt(meas)}")
    for name, row in rows.items():
        if "bandwidths" not in row:
            print(f"{name:34s} not usable: {row['reason']}")
            continue
        for bw, e in row["bandwidths"].items():
            if e["resembles"] is None:
                print(f"{name + ' ' + bw:34s} metrics unavailable")
                continue
            flags = "".join(k[0].upper() if v else "." for k, v in e["resembles"].items() if k != "all")
            print(f"{name + ' ' + bw:34s} {fmt(e['metrics'])}  [{flags}]{' usable' if row['usable'] else ' UNUSABLE'}")


if __name__ == "__main__":
    main()
