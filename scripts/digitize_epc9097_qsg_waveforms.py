#!/usr/bin/env python3
"""Digitize the switch-node oscilloscope screenshots in the EPC9097 quick-start guide.

QSG v3.0 Figs. 12-14 show the switch node at 48 V -> 12 V, 1 MHz, with 0, 10
and 15 A load. Each figure has two zoomed panels (10 V/div, 10 ns/div): the
rising and the falling edge. They are embedded raster screenshots, not vector
drawings, so this script works from pixels:

* the graticule is found from the grey dotted grid: rows and columns with
  many grey pixels, required to be uniformly spaced; the brightest row and
  column are the centre crosshair;
* volts per pixel come from the stated 10 V/div and the detected grid pitch;
  the zero-volt row is the centroid of the channel-1 ground marker at the
  left edge;
* the trace is the blue pixels; each column contributes the midpoint of its
  longest vertical run.

Independent check: the difference between the settled high and low levels
must be close to the stated 48 V bus. Resolution is about 0.3 V and 0.2 ns
per pixel. These are vendor-described measurements with unknown probe,
bandwidth and probing point; see docs/build.md.
"""
import argparse
import hashlib
import json
from pathlib import Path

import fitz  # PyMuPDF
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
QSG = ROOT / "vendor" / "epc" / "epc9097" / "EPC9097_qsg.pdf"
QSG_SHA256 = "4daa152684358d138102c3e6d8809ec41204a5c298eff96d96a59490e9f0c1d2"
V_PER_DIV, S_PER_DIV = 10.0, 10e-9
VIN = 48.0
LEVEL_CHECK_TOLERANCE_V = 2.0
M = 14  # px; frame border excluded from grid detection
LATE_WINDOW = (12e-9, 44e-9)  # s after the 50 % crossing, for the persistent ringing
# (figure, load current, page index, panel image xrefs as (rising, falling)), checked against bbox order below
PANELS = (("fig12", 0.0, 8), ("fig13", 10.0, 9), ("fig14", 15.0, 9))


def load(doc, xref):
    pix = fitz.Pixmap(doc, xref)
    if pix.n - pix.alpha < 3:
        pix = fitz.Pixmap(fitz.csRGB, pix)
    return np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3].astype(int)


def grid_lines(counts):
    """Uniformly spaced grid lines from per-row (or column) grey-pixel counts.

    The centre crosshair is the strongest line. The pitch is the spacing whose
    predicted lines (each located within +/-1 px) have the highest mean grey
    count; a half pitch lands on empty rows and scores lower. Each line is
    then placed at its local maximum and the pitch refined by least squares.
    """
    counts = np.asarray(counts, float)
    n = len(counts)
    centre = int(np.argmax(counts))

    def located(pitch):
        out = []
        for k in range(-int(centre / pitch), int((n - 1 - centre) / pitch) + 1):
            if k == 0:
                continue
            p = centre + k * pitch
            lo, hi = int(round(p)) - 1, int(round(p)) + 2
            if lo < 0 or hi > n:
                continue
            j = lo + int(np.argmax(counts[lo:hi]))
            out.append((k, j))
        return out

    best = None
    for pitch in np.arange(15.0, n / 4, 0.1):
        lines = located(pitch)
        if len(lines) < 6:
            continue
        score = float(np.mean([counts[j] for _, j in lines]))
        if best is None or score > best[0] + 1e-9:
            best = (score, pitch, lines)
    _, pitch, lines = best
    k = np.array([0] + [k for k, _ in lines], float)
    p = np.array([centre] + [j for _, j in lines], float)
    slope, intercept = np.polyfit(k, p, 1)
    residual = float(np.max(np.abs(p - (slope * k + intercept))))
    background = float(np.median(counts))
    return {"centre_px": centre, "pitch_px": float(slope), "lines_px": sorted(int(x) for x in p),
            "max_offset_px": residual, "mean_line_count": best[0], "median_count": background}


def digitize(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    h, w = r.shape
    grey = (abs(r - g) < 20) & (abs(g - b) < 25) & (r > 60) & (r < 200)
    blue = (b - r > 60) & (b - g > 40)
    inner = grey[M:h - M, M:w - M]
    rows = grid_lines(inner.sum(1))
    cols = grid_lines(inner.sum(0))
    rows = {**rows, "centre_px": rows["centre_px"] + M, "lines_px": [p + M for p in rows["lines_px"]]}
    cols = {**cols, "centre_px": cols["centre_px"] + M, "lines_px": [p + M for p in cols["lines_px"]]}
    # Ground marker: the largest cluster of rows with a filled blue blob in the first columns
    # (the trace can also enter those columns, but only as a thin line).
    marker = [y for y in range(3, h - 3) if blue[y, 0:12].sum() >= 4]
    clusters = np.split(np.array(marker), np.nonzero(np.diff(marker) > 1)[0] + 1) if marker else []
    blob = max(clusters, key=len)
    ground_row = 0.5 * (blob[0] + blob[-1])
    v_per_px = V_PER_DIV / rows["pitch_px"]
    t_per_px = S_PER_DIV / cols["pitch_px"]
    trace = []
    for x in range(14, w - 14):
        # Rows next to the frame hold the trigger-position marker, not the trace.
        yy = np.nonzero(blue[8:h - 8, x])[0] + 8
        if len(yy) == 0:
            continue
        runs = np.split(yy, np.nonzero(np.diff(yy) > 1)[0] + 1)
        run = max(runs, key=len)
        y = 0.5 * (run[0] + run[-1])
        trace.append(((x - cols["centre_px"]) * t_per_px, (ground_row - y) * v_per_px))
    return {"image_px": [w, h], "grid_rows": rows, "grid_cols": cols, "ground_row_px": ground_row,
            "ground_marker_rows_px": [int(blob[0]), int(blob[-1])],
            "v_per_px": v_per_px, "s_per_px": t_per_px}, trace


def crossing(trace, level, rising):
    for (t0, v0), (t1, v1) in zip(trace, trace[1:]):
        if (rising and v0 < level <= v1) or (not rising and v0 > level >= v1):
            return t0 + (t1 - t0) * (level - v0) / (v1 - v0)
    return None


def mean(vals):
    return float(np.mean(vals)) if vals else None


def fit_damped(tr, settled, window):
    """Damped-cosine fit of the ringing about the settled level inside window (s after the edge).

    The starting frequency is the peak of the zero-padded spectrum between
    30 and 600 MHz; scipy's least squares then fits amplitude, decay time,
    frequency, phase and offset.
    """
    from scipy.optimize import curve_fit
    pts = [(t, v - settled) for t, v in tr if window[0] <= t <= window[1]]
    if len(pts) < 20:
        return None
    t = np.array([p[0] for p in pts]) - window[0]
    y = np.array([p[1] for p in pts])
    dt = float(np.median(np.diff(t)))
    grid = np.arange(0, t[-1], dt)
    yu = np.interp(grid, t, y) - np.mean(y)
    spec = np.abs(np.fft.rfft(yu * np.hanning(len(yu)), 8192))
    freqs = np.fft.rfftfreq(8192, dt)
    band = (freqs >= 30e6) & (freqs <= 600e6)
    f0 = float(freqs[band][np.argmax(spec[band])])

    def model(tt, a, tau, f, phi, c):
        return c + a * np.exp(-tt / tau) * np.cos(2 * np.pi * f * tt + phi)

    a0 = float(np.max(np.abs(yu)))
    best = None
    for phi0 in np.linspace(0, 2 * np.pi, 8, endpoint=False):
        try:
            p, _ = curve_fit(model, t, y, p0=[a0, 20e-9, f0, phi0, 0.0],
                             bounds=([0, 1e-9, 0.5 * f0, -10, -5], [60, 1e-6, 2 * f0, 10, 5]), maxfev=20000)
        except RuntimeError:
            continue
        rms = float(np.sqrt(np.mean((model(t, *p) - y) ** 2)))
        if best is None or rms < best[1]:
            best = (p, rms)
    if best is None:
        return {"spectral_peak_Hz": f0, "fit": None}
    p, rms = best
    return {"window_s": list(window), "spectral_peak_Hz": f0, "frequency_Hz": float(p[2]),
            "decay_time_s": float(p[1]), "amplitude_at_window_start_V": float(p[0]),
            "fit_rms_V": rms, "data_rms_V": float(np.sqrt(np.mean((y - np.mean(y)) ** 2)))}


def edge_metrics(trace, rising):
    """Levels, 10-90 % edge time, overshoot/undershoot, ringing and dead-time plateau."""
    t50 = crossing(trace, VIN / 2, rising)
    tr = [(t - t50, v) for t, v in trace]
    before = [v for t, v in tr if -45e-9 <= t <= -25e-9]
    after = [v for t, v in tr if 25e-9 <= t <= 45e-9]
    pre, post = mean(before), mean(after)
    lo, hi = (pre, post) if rising else (post, pre)
    swing = hi - lo
    t10 = crossing(tr, lo + 0.1 * swing, rising)
    t90 = crossing(tr, lo + 0.9 * swing, rising)
    out = {"t50_in_panel_s": t50, "level_before_V": pre, "level_after_V": post, "swing_V": swing,
           "edge_10_90_s": abs(t90 - t10) if t10 is not None and t90 is not None else None}
    ring = [(t, v) for t, v in tr if 0 <= t <= 40e-9]
    if rising:
        pk_t, pk_v = max(ring, key=lambda p: p[1])
        out.update(peak_V=pk_v, overshoot_above_settled_V=pk_v - post, peak_time_s=pk_t)
        ext = [ring[k] for k in range(2, len(ring) - 2)
               if ring[k][1] == max(p[1] for p in ring[k - 2:k + 3]) and ring[k][1] > post + 1.0]
        # Plateau before the rise: switch node below its settled low level while Q2 conducts in reverse.
        dip = [(t, v) for t, v in tr if -20e-9 <= t <= -1e-9 and v < pre - 1.0]
    else:
        pk_t, pk_v = min(ring, key=lambda p: p[1])
        out.update(trough_V=pk_v, undershoot_below_settled_V=post - pk_v, trough_time_s=pk_t)
        ext = [ring[k] for k in range(2, len(ring) - 2)
               if ring[k][1] == min(p[1] for p in ring[k - 2:k + 3]) and ring[k][1] < post - 1.0]
        dip = [(t, v) for t, v in tr if 1e-9 <= t <= 20e-9 and v < post - 1.0]
    # Merge neighbouring extrema closer than 1.5 ns (pixel noise on one crest).
    merged = []
    for p in ext:
        if merged and p[0] - merged[-1][0] < 1.5e-9:
            continue
        merged.append(p)
    # The ringing has two parts: a fast one in the first few ns and a slower, persistent one.
    out["early_crest_times_s"] = [p[0] for p in merged[:3]]
    out["early_crest_spacing_s"] = merged[1][0] - merged[0][0] if len(merged) >= 2 else None
    out["late_ring"] = fit_damped(tr, post, LATE_WINDOW)
    if dip:
        out["reverse_conduction_plateau"] = {"start_s": dip[0][0], "end_s": dip[-1][0],
                                             "duration_s": dip[-1][0] - dip[0][0],
                                             "min_V": min(v for _, v in dip),
                                             "definition": "switch node more than 1 V below its settled low level"}
    out["trace_rel_s_V"] = [[t, v] for t, v in tr]
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "results/gan/epc9097-qsg-waveforms.json")
    args = parser.parse_args()
    digest = hashlib.sha256(QSG.read_bytes()).hexdigest()
    if digest != QSG_SHA256:
        raise SystemExit(f"{QSG} sha256 {digest} does not match devices/epc/sources.json")
    doc = fitz.open(QSG)
    figures, checks = {}, {}
    for fig, load_A, page in PANELS:
        # The two zoomed panels are the lower pair of images on the figure's page (sorted by position).
        infos = [i for i in doc[page].get_image_info(xrefs=True) if i["xref"]]
        overview_y = {"fig12": 330, "fig13": 70, "fig14": 420}[fig]
        overview = min(infos, key=lambda i: abs(i["bbox"][1] - overview_y))
        panels = sorted([i for i in infos if i is not overview and 0 < i["bbox"][1] - overview["bbox"][3] < 60],
                        key=lambda i: i["bbox"][0])
        if len(panels) != 2:
            raise SystemExit(f"{fig}: expected two zoomed panels below the overview, found {len(panels)}")
        entry = {"load_A": load_A, "page": page + 1}
        for kind, info, rising in (("rising", panels[0], True), ("falling", panels[1], False)):
            cal, trace = digitize(load(doc, info["xref"]))
            m = edge_metrics(trace, rising)
            entry[kind] = {"xref": info["xref"], "bbox_pt": [round(x, 1) for x in info["bbox"]],
                           "calibration": cal, "metrics": m}
            swing_err = m["swing_V"] - VIN
            checks[f"{fig}_{kind}"] = {
                "grid_rows_uniform_px": cal["grid_rows"]["max_offset_px"],
                "grid_cols_uniform_px": cal["grid_cols"]["max_offset_px"],
                "swing_V": m["swing_V"], "swing_minus_bus_V": swing_err,
                "outcome": "pass" if abs(swing_err) <= LEVEL_CHECK_TOLERANCE_V
                and cal["grid_rows"]["max_offset_px"] <= 1.5 and cal["grid_cols"]["max_offset_px"] <= 1.5 else "fail"}
        figures[fig] = entry
    report = {
        "schema": "epc9097-qsg-waveforms/1",
        "source": {"file": "EPC9097_qsg.pdf", "sha256": digest, "revision": "Version 3.0, revised October 3, 2024",
                   "figures": "12 (0 A), 13 (10 A), 14 (15 A); 48 V -> 12 V, 1 MHz, 2.2 uH, 10 ns dead time"},
        "evidence_class": ("vendor-described measurement, digitized from embedded raster screenshots; probe type, "
                           "bandwidth and probing point are not stated"),
        "method": {"scale": f"{V_PER_DIV} V/div, {S_PER_DIV*1e9:g} ns/div as printed; pitch from detected grid",
                   "zero_volt": "centroid of the channel ground marker",
                   "trace": "midpoint of the longest blue run in each pixel column",
                   "time_origin": "50 % (24 V) crossing of each edge"},
        "checks": checks,
        "check_rule": f"settled swing within {LEVEL_CHECK_TOLERANCE_V} V of the {VIN} V bus; grid lines within 1.5 px of uniform",
        "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "figures": figures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    summary = {}
    for fig, e in figures.items():
        for kind in ("rising", "falling"):
            m = {k: v for k, v in e[kind]["metrics"].items() if k not in ("trace_rel_s_V", "ringing_extrema_s")}
            summary[f"{fig}_{kind}"] = {k: (round(v * 1e9, 2) if k.endswith("_s") and isinstance(v, float) else
                                            round(v / 1e6, 1) if k.endswith("_Hz") and v else
                                            round(v, 2) if isinstance(v, float) else v) for k, v in m.items()}
    print(json.dumps({"checks": {k: v["outcome"] for k, v in checks.items()}, "summary": summary}, indent=1, default=str))
    return 0 if all(c["outcome"] == "pass" for c in checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
