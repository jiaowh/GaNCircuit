#!/usr/bin/env python3
"""Digitize the switch-node waveform in the EPC90133 quick-start guide (QSG v1.0, Fig. 9).

Fig. 9 (page 6) is printed as one wide oscilloscope picture, but the PDF holds
it as two raster screenshots placed side by side: xref 119 (left, the rising
edge) and xref 117 (right, the falling edge). The labels (10 V/div, 10 ns/div,
tr = 1.7 ns, tf = 3.7 ns, operating conditions) are PDF text drawn over them.
At 250 kHz and 13.8/48 duty the high time is about 1.15 us, which cannot fit on
a 10 ns/div screen, so the two panels are separate zoomed captures and the
horizontal distance between the edges in the printed figure is not time.
Each panel is digitized on its own time axis.

Method, fixed before the first run (written after viewing the images; the
level rule is carried over unchanged from scripts/digitize_epc9097_qsg_waveforms.py):

* graticule: grid pixels are non-white pixels more than 4 px (vertically) or
  1 px (horizontally) away from any trace pixel; the trace's flat parts
  otherwise add false grid rows. The centre crosshair is the strongest line.
  The pitch is the spacing whose predicted lines score highest in grid-pixel
  count minus the count half a pitch away (the contrast rejects multiples and
  fractions of the true pitch). Lines are then located within +/-1 px and the
  pitch refined by least squares. The pixels are not square: the pitch is
  detected separately on each axis.
* scale: 10 V/div and 10 ns/div as printed, divided by the detected pitch.
* zero volt: the settled low level of each panel is taken as 0 V. The lower
  FET conducts at most about 29 A with RDS(on) about 2 mOhm, so the true
  level is within 0.1 V of zero. Only the left panel carries the channel
  ground marker; its centroid is a cross-check, not the reference.
* trace: pixels with b - r > 60 and b - g > 40; each column contributes the
  midpoint of its longest vertical run. Rows within 8 px of the frame hold
  trigger markers and are ignored.
* time origin: each edge's 50 % crossing between its settled levels.

Checks (a failed check is recorded, not tuned away):

1. grid: detected lines within 1.5 px of uniform on each axis, and the two
   panels' pitches within 1 % of each other;
2. time scale: digitized 10-90 % rise and 90-10 % fall within 0.4 ns (about
   2 px) of EPC's printed tr = 1.7 ns and tf = 3.7 ns. EPC's printed values
   come from the same capture, presumably from the scope's own level
   estimates, so this is a consistency check;
3. volt scale: settled swing within 2 V of the 48 V bus;
4. zero: the left panel's ground-marker centroid within 1 V of its settled
   low level.

The falling edge's undershoot recovers without ringing above the pixel noise
(checked on an overlay after the first run), so only the rising edge reports
a ringing frequency; the falling edge's extrema are listed but not converted.

Digitization uncertainty (added 30 September 2026 after an external review, before
its first run; the baseline method and checks above are unchanged). Every metric is
recomputed over all combinations of these extraction choices:
* trace estimator: midpoint of the longest run (baseline), or the centroid of
  that run weighted by blueness (b - (r + g) / 2);
* settled-level windows: 20-40, 25-45 (baseline) and 30-45 ns from the 50 % crossing;
* ringing fit: start at the first crest (baseline) or at the highest sample;
  end at 20, 25 (baseline) or 30 ns;
* grid pitch: detected value and +/- two standard errors of its least-squares
  fit, on each axis.
Each metric is reported with the range over the combinations and with the pixel
resolution. The ranges are an extraction-choice sensitivity, not a complete uncertainty interval: they
exclude the unknown probe response, the failed volt-scale check and other raster or fit errors (second
review, 30 September 2026). Rule for "consistent with the declared extraction range" (used by
scripts/compare_epc90133_fig9.py): a simulated value lies inside the range widened
by one pixel (time and voltage metrics) or inside the range itself (frequency and
damping, which are fits over many pixels). Point estimates finer than this are
not claimed.

Resolution is about 0.32 V and 0.20 ns per pixel. Evidence class:
vendor-described measurement. Probe, bandwidth and probing point are not
stated for Fig. 9. The guide recommends the J32 MMCX or the J33 header and
an IsoVu or a TPP1000 passive probe, but J32 is absent from the published
layout (docs/build.md).
"""
import argparse
import hashlib
import json
from pathlib import Path

import fitz  # PyMuPDF
import numpy as np
from scipy.ndimage import binary_dilation
from scipy.optimize import curve_fit

ROOT = Path(__file__).resolve().parents[1]
QSG = ROOT / "vendor" / "epc" / "epc90133" / "EPC90133_qsg.pdf"
QSG_SHA256 = "53e70a9c7f4583b079c8c2ce20117e3be3b6b0417146b56cdd09a32a71764886"  # devices/epc/epc90133-sources.json
PAGE = 5  # zero-based; printed page 6
PANELS = (("rising", 119, True), ("falling", 117, False))
V_PER_DIV, S_PER_DIV = 10.0, 10e-9
VIN = 48.0
PRINTED = {"rising": 1.7e-9, "falling": 3.7e-9}
EDGE_TOL_S = 0.4e-9
LEVEL_TOL_V = 2.0
ZERO_TOL_V = 1.0
GRID_UNIFORM_PX = 1.5
PITCH_AGREE = 0.01
M = 10       # px; frame border excluded from grid detection
FRAME = 8    # px; rows next to the frame hold markers, not the trace
SETTLE = (25e-9, 45e-9)  # s from the 50 % crossing, on each side, for the settled levels


def load(doc, xref):
    pix = fitz.Pixmap(doc, xref)
    if pix.n - pix.alpha < 3:
        pix = fitz.Pixmap(fitz.csRGB, pix)
    return np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3].astype(int)


def grid_lines(counts, lo=15.0, hi=90.0):
    counts = np.asarray(counts, float)
    n = len(counts)
    centre = int(np.argmax(counts))

    def near_max(p):
        a, b = max(0, int(round(p)) - 1), min(n, int(round(p)) + 2)
        return a + int(np.argmax(counts[a:b]))

    best = None
    for pitch in np.arange(lo, hi, 0.1):
        ks = [k for k in range(-int(centre / pitch), int((n - 1 - centre) / pitch) + 1) if k]
        on = [counts[near_max(centre + k * pitch)] for k in ks if 1 <= centre + k * pitch < n - 2]
        off = [counts[int(round(centre + (k + 0.5) * pitch))] for k in ks + [0]
               if 0 <= centre + (k + 0.5) * pitch < n - 1]
        if len(on) < 5:
            continue
        score = float(np.mean(on) - np.mean(off))
        if best is None or score > best[0] + 1e-9:
            best = (score, pitch, ks)
    score, pitch, ks = best
    pts = [(0, centre)] + [(k, near_max(centre + k * pitch)) for k in ks if 1 <= centre + k * pitch < n - 2]
    k = np.array([p[0] for p in pts], float)
    p = np.array([p[1] for p in pts], float)
    (slope, intercept), cov = np.polyfit(k, p, 1, cov=True)
    return {"centre_px": centre, "pitch_px": float(slope), "pitch_se_px": float(np.sqrt(cov[0, 0])),
            "lines_px": sorted(int(x) for x in p),
            "max_offset_px": float(np.max(np.abs(p - (slope * k + intercept)))), "contrast": score}


def digitize(a, estimator="mid", pitch_se=(0.0, 0.0)):
    """Calibrate the panel and extract the trace.

    estimator: "mid" (baseline) or "centroid" (blueness-weighted, longest run);
    pitch_se: multiples of the pitch standard error added to (rows, cols).
    """
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    h, w = r.shape
    blue = (b - r > 60) & (b - g > 40)
    near_trace = binary_dilation(blue, np.ones((9, 3), bool))
    grid = ((r + g + b) < 660) & ~near_trace
    inner = grid[M:h - M, M:w - M]
    rows, cols = grid_lines(inner.sum(1)), grid_lines(inner.sum(0))
    for d in (rows, cols):
        d["centre_px"] += M
        d["lines_px"] = [p + M for p in d["lines_px"]]
    v_per_px = V_PER_DIV / (rows["pitch_px"] + pitch_se[0] * rows["pitch_se_px"])
    s_per_px = S_PER_DIV / (cols["pitch_px"] + pitch_se[1] * cols["pitch_se_px"])
    weight = np.clip(b - 0.5 * (r + g), 0, None)
    trace = []
    for x in range(14, w - 14):
        yy = np.nonzero(blue[FRAME:h - FRAME, x])[0] + FRAME
        if len(yy) == 0:
            continue
        run = max(np.split(yy, np.nonzero(np.diff(yy) > 1)[0] + 1), key=len)
        if estimator == "mid":
            y = 0.5 * (run[0] + run[-1])
        else:
            wts = weight[run, x].astype(float)
            y = float(np.sum(run * wts) / np.sum(wts)) if np.sum(wts) > 0 else 0.5 * (run[0] + run[-1])
        trace.append(((x - cols["centre_px"]) * s_per_px, y))
    marker = [y for y in range(FRAME, h - FRAME) if blue[y, 0:12].sum() >= 4]
    blob = max(np.split(np.array(marker), np.nonzero(np.diff(marker) > 1)[0] + 1), key=len) if marker else None
    cal = {"image_px": [w, h], "grid_rows": rows, "grid_cols": cols, "v_per_px": v_per_px, "s_per_px": s_per_px,
           "ground_marker_row_px": 0.5 * (blob[0] + blob[-1]) if blob is not None and len(blob) >= 4 else None}
    return cal, trace


def crossing(tr, level, rising):
    for (t0, v0), (t1, v1) in zip(tr, tr[1:]):
        if (rising and v0 < level <= v1) or (not rising and v0 > level >= v1):
            return t0 + (t1 - t0) * (level - v0) / (v1 - v0)
    return None


def extrema(ring, settled, rising, min_dev=1.0):
    """Crests (rising edge) or troughs (falling edge) deviating by min_dev V, merged within 1.5 ns."""
    sgn = 1 if rising else -1
    ext = [ring[k] for k in range(2, len(ring) - 2)
           if sgn * ring[k][1] == max(sgn * p[1] for p in ring[k - 2:k + 3]) and sgn * (ring[k][1] - settled) > min_dev]
    merged = []
    for p in ext:
        if merged and p[0] - merged[-1][0] < 1.5e-9:
            if sgn * p[1] > sgn * merged[-1][1]:
                merged[-1] = p
            continue
        merged.append(p)
    return merged


def fit_ring(tr, settled, t_start, t_stop=25e-9):
    """Damped-cosine fit of the ringing about the settled level from the first crest to t_stop."""
    pts = [(t, v - settled) for t, v in tr if t_start <= t <= t_stop]
    if len(pts) < 20:
        return None
    t = np.array([p[0] for p in pts]) - t_start
    y = np.array([p[1] for p in pts])
    dt = float(np.median(np.diff(t)))
    grid = np.arange(0, t[-1], dt)
    yu = np.interp(grid, t, y) - np.mean(y)
    spec = np.abs(np.fft.rfft(yu * np.hanning(len(yu)), 8192))
    freqs = np.fft.rfftfreq(8192, dt)
    band = (freqs >= 50e6) & (freqs <= 1.5e9)
    f0 = float(freqs[band][np.argmax(spec[band])])

    def model(tt, a, tau, f, phi, c):
        return c + a * np.exp(-tt / tau) * np.cos(2 * np.pi * f * tt + phi)

    best = None
    for phi0 in np.linspace(0, 2 * np.pi, 8, endpoint=False):
        try:
            a0 = float(np.max(np.abs(y)))  # simulated rings reach 55 V; Fig. 9 about 6 V
            p, _ = curve_fit(model, t, y, p0=[a0, 5e-9, f0, phi0, 0.0],
                             bounds=([0, 0.2e-9, 0.4 * f0, -10, -3], [max(40.0, 2 * a0), 1e-6, 2.5 * f0, 10, 3]), maxfev=20000)
        except RuntimeError:
            continue
        rms = float(np.sqrt(np.mean((model(t, *p) - y) ** 2)))
        if best is None or rms < best[1]:
            best = (p, rms)
    if best is None:
        return {"spectral_peak_Hz": f0, "fit": None}
    p, rms = best
    return {"window_s": [t_start, t_stop], "spectral_peak_Hz": f0, "frequency_Hz": float(p[2]),
            "decay_time_s": float(p[1]), "amplitude_at_window_start_V": float(p[0]), "fit_rms_V": rms,
            "data_rms_V": float(np.sqrt(np.mean((y - np.mean(y)) ** 2)))}


def edge_metrics(cal, raw, rising, settle=None, fit_start="crest", fit_stop=25e-9):
    """Convert pixel rows to volts (settled low = 0 V) and measure the edge."""
    settle = settle or SETTLE
    ys = np.array([y for _, y in raw])
    ts = np.array([t for t, _ in raw])
    # First pass: settled rows from the panel ends, then the 50 % crossing in pixel rows.
    first, last = float(np.median(ys[:40])), float(np.median(ys[-40:]))
    t50 = crossing([(t, -y) for t, y in raw], -0.5 * (first + last), rising)
    rel = ts - t50
    before = ys[(rel >= -settle[1]) & (rel <= -settle[0])]
    after = ys[(rel >= settle[0]) & (rel <= settle[1])]
    low_row = float(np.mean(before if rising else after))
    high_row = float(np.mean(after if rising else before))
    vp = cal["v_per_px"]
    tr = [(float(t), float((low_row - y) * vp)) for t, y in zip(rel, ys)]
    hi = (low_row - high_row) * vp
    t50 = crossing(tr, 0.5 * hi, rising)
    tr = [(t - t50, v) for t, v in tr]
    t10, t90 = crossing(tr, 0.1 * hi, rising), crossing(tr, 0.9 * hi, rising)
    out = {"settled_low_V": 0.0, "settled_high_V": hi, "swing_V": hi,
           "edge_10_90_s": abs(t90 - t10) if t10 is not None and t90 is not None else None}
    if cal["ground_marker_row_px"] is not None:
        out["ground_marker_V"] = (low_row - cal["ground_marker_row_px"]) * vp
    ring = [(t, v) for t, v in tr if 0 <= t <= 30e-9]
    if rising:
        pk_t, pk_v = max(ring, key=lambda p: p[1])
        out.update(peak_V=pk_v, overshoot_above_settled_V=pk_v - hi, peak_time_s=pk_t)
        ext = extrema(ring, hi, True)
        # Dead-time plateau before the rise: switch node more than 1 V below its settled low level.
        dip = [(t, v) for t, v in tr if -20e-9 <= t <= -1e-9 and v < -1.0]
        if dip:
            out["reverse_conduction_plateau"] = {
                "start_s": dip[0][0], "end_s": dip[-1][0], "duration_s": dip[-1][0] - dip[0][0],
                "min_V": min(v for _, v in dip), "mean_V": float(np.mean([v for _, v in dip])),
                "definition": "switch node more than 1 V below its settled low level, 20 ns to 1 ns before the rise"}
        out["ring_fit"] = fit_ring(tr, hi, ext[0][0] if ext and fit_start == "crest" else pk_t, fit_stop)
    else:
        pk_t, pk_v = min(ring, key=lambda p: p[1])
        out.update(trough_V=pk_v, undershoot_below_settled_V=-pk_v, trough_time_s=pk_t)
        ext = extrema(ring, 0.0, False)
    out["extrema_s_V"] = [[t, v] for t, v in ext]
    if rising and len(ext) >= 2:
        sp = [b[0] - a[0] for a, b in zip(ext, ext[1:])]
        out["extrema_spacing_s"] = sp
        out["frequency_from_first_two_extrema_Hz"] = 1.0 / sp[0]
        out["frequency_from_mean_spacing_Hz"] = 1.0 / float(np.mean(sp))
    out["trace_rel_s_V"] = [[t, v] for t, v in tr]
    return out


UNCERTAINTY = {"estimator": ("mid", "centroid"), "settle_s": ((20e-9, 40e-9), (25e-9, 45e-9), (30e-9, 45e-9)),
               "fit_start": ("crest", "peak"), "fit_stop_s": (20e-9, 25e-9, 30e-9), "pitch_se": (-2.0, 0.0, 2.0)}


def headline(m, rising):
    """The metrics compared with simulation (scripts/compare_epc90133_fig9.py)."""
    if not rising:
        return {"edge_10_90_s": m["edge_10_90_s"], "undershoot_below_settled_V": m["undershoot_below_settled_V"],
                "swing_V": m["swing_V"]}
    out = {"edge_10_90_s": m["edge_10_90_s"], "overshoot_above_settled_V": m["overshoot_above_settled_V"],
           "overshoot_fraction": m["overshoot_above_settled_V"] / m["swing_V"], "swing_V": m["swing_V"]}
    fit = m.get("ring_fit") or {}
    if fit.get("frequency_Hz"):
        out["ring_frequency_Hz"] = fit["frequency_Hz"]
        out["ring_damping_ratio"] = 1 / (2 * np.pi * fit["frequency_Hz"] * fit["decay_time_s"])
    if m.get("frequency_from_mean_spacing_Hz"):
        out["ring_frequency_crest_spacing_Hz"] = m["frequency_from_mean_spacing_Hz"]
    plat = m.get("reverse_conduction_plateau")
    if plat:
        out["plateau_duration_s"] = plat["duration_s"]
        out["plateau_mean_V"] = plat["mean_V"]
    return out


def uncertainty(img, rising):
    """Range of each headline metric over every combination of UNCERTAINTY's extraction choices."""
    import itertools
    values, n = {}, 0
    for est, pr, pc in itertools.product(UNCERTAINTY["estimator"], UNCERTAINTY["pitch_se"], UNCERTAINTY["pitch_se"]):
        cal, raw = digitize(img, est, (pr, pc))
        for settle, start, stop in itertools.product(UNCERTAINTY["settle_s"], UNCERTAINTY["fit_start"],
                                                     UNCERTAINTY["fit_stop_s"] if rising else (25e-9,)):
            if not rising and start != "crest":
                continue
            h = headline(edge_metrics(cal, raw, rising, settle, start, stop), rising)
            n += 1
            for k, v in h.items():
                if v is not None:
                    values.setdefault(k, []).append(float(v))
    return {"combinations": n,
            "ranges": {k: {"min": min(v), "max": max(v), "n": len(v)} for k, v in values.items()}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-qsg-fig9.json")
    args = parser.parse_args()
    digest = hashlib.sha256(QSG.read_bytes()).hexdigest()
    if digest != QSG_SHA256:
        raise SystemExit(f"{QSG} sha256 {digest} does not match devices/epc/epc90133-sources.json")
    doc = fitz.open(QSG)
    infos = {i["xref"]: i for i in doc[PAGE].get_image_info(xrefs=True) if i["xref"]}
    left, right = infos[119]["bbox"], infos[117]["bbox"]
    if not (left[2] <= right[0] + 1 and abs(left[1] - right[1]) < 1):
        raise SystemExit("Fig. 9 panels are not side by side as expected (xref 119 left of xref 117)")
    panels, checks = {}, {}
    for kind, xref, rising in PANELS:
        img = load(doc, xref)
        cal, raw = digitize(img)
        m = edge_metrics(cal, raw, rising)
        panels[kind] = {"xref": xref, "bbox_pt": [round(x, 1) for x in infos[xref]["bbox"]],
                        "calibration": cal, "metrics": m, "headline": headline(m, rising),
                        "uncertainty": {**uncertainty(img, rising), "choices": {k: list(v) for k, v in UNCERTAINTY.items()},
                                        "resolution": {"s_per_px": cal["s_per_px"], "V_per_px": cal["v_per_px"]}}}
        edge_err = m["edge_10_90_s"] - PRINTED[kind]
        c = {"grid_rows_offset_px": cal["grid_rows"]["max_offset_px"],
             "grid_cols_offset_px": cal["grid_cols"]["max_offset_px"],
             "edge_10_90_s": m["edge_10_90_s"], "edge_minus_printed_s": edge_err,
             "swing_V": m["swing_V"], "swing_minus_bus_V": m["swing_V"] - VIN}
        c["grid"] = "pass" if max(c["grid_rows_offset_px"], c["grid_cols_offset_px"]) <= GRID_UNIFORM_PX else "fail"
        c["time_scale"] = "pass" if abs(edge_err) <= EDGE_TOL_S else "fail"
        c["volt_scale"] = "pass" if abs(c["swing_minus_bus_V"]) <= LEVEL_TOL_V else "fail"
        if "ground_marker_V" in m:
            c["ground_marker_V"] = m["ground_marker_V"]
            c["zero"] = "pass" if abs(m["ground_marker_V"]) <= ZERO_TOL_V else "fail"
        checks[kind] = c
    pr = [panels[k]["calibration"]["grid_rows"]["pitch_px"] for k in ("rising", "falling")]
    pc = [panels[k]["calibration"]["grid_cols"]["pitch_px"] for k in ("rising", "falling")]
    checks["pitch_agreement"] = {"rows_px": pr, "cols_px": pc,
                                 "outcome": "pass" if abs(pr[0] / pr[1] - 1) <= PITCH_AGREE
                                 and abs(pc[0] / pc[1] - 1) <= PITCH_AGREE else "fail"}
    report = {
        "schema": "epc90133-qsg-fig9/1",
        "source": {"file": "EPC90133_qsg.pdf", "sha256": digest, "revision": "Version 1.0, September 6, 2022",
                   "figure": "Fig. 9, page 6", "conditions": "buck, VIN 48 V, VOUT 13.8 V, IOUT 20 A, 250 kHz, 2.2 uH",
                   "printed": {"tr_10_90_s": 1.7e-9, "tf_90_10_s": 3.7e-9}},
        "evidence_class": ("vendor-described measurement, digitized from two embedded raster screenshots; probe, "
                           "bandwidth and probing point are not stated"),
        "method": "see the module docstring of scripts/digitize_epc90133_qsg_fig9.py",
        "checks": checks,
        "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "panels": panels,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    summary = {}
    for kind in ("rising", "falling"):
        m = panels[kind]["metrics"]
        summary[kind] = {k: v for k, v in m.items() if k not in ("trace_rel_s_V", "extrema_s_V")}
        summary[kind + "_uncertainty"] = panels[kind]["uncertainty"]["ranges"]
    print(json.dumps({"checks": checks, "summary": summary}, indent=1, default=str))
    failed = [k for k, c in checks.items() for f in ("grid", "time_scale", "volt_scale", "zero", "outcome")
              if c.get(f) == "fail"]
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
