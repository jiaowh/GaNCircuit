#!/usr/bin/env python3
"""Extract every vector curve from the EPC2204 datasheet figures.

EPC datasheet figures are vector drawings, so the plotted paths can be read
exactly rather than traced from an image. Axis calibration uses the plot's
own geometry, not text positions:

* the plot frame is the dark stroked rectangle around each figure;
* grid lines are found in a 600 dpi render of the frame (PyMuPDF does not
  return them as drawings);
* each tick label is paired with the nearest grid line or frame edge. Label
  positions only choose the line, because text boxes are offset from their
  ticks by a figure-dependent amount (2.3 pt in Fig. 6);
* the axis is fitted to the paired line positions (log10 for decade labels).

Points outside the plot frame are dropped. Bezier segments are sampled.
Legend swatches are also not returned as drawings, so each swatch colour is
sampled from the render left of its legend text and matched to the nearest
curve colour. Fig. 6 uses arrows instead; their direction gives each curve's
axis.

Revision 2, 28 September 2026. Revision 1 fitted axes to text-box centres and
clipped to the label range. That shifted Fig. 6 by about 2.3 pt and dropped
valid low-energy points; review found it.

Requires PyMuPDF (runs under WSL on the project host):

    python3 scripts/digitize_datasheet_figures.py
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = ROOT / "vendor" / "epc" / "EPC2204_datasheet.pdf"
DEFAULT_OUT = ROOT / "results" / "gan" / "epc2204-datasheet-figures.json"
NUM = re.compile(r"-?\d+(?:\.\d+)?")
BEZIER_SAMPLES = 24
DPI = 600
SCALE = DPI / 72


def fit(pairs, log=False):
    pairs = [(p, math.log10(v) if log else v) for p, v in pairs]
    n = len(pairs)
    mx = sum(p for p, _ in pairs) / n
    my = sum(v for _, v in pairs) / n
    slope = sum((p - mx) * (v - my) for p, v in pairs) / sum((p - mx) ** 2 for p, _ in pairs)
    icpt = my - slope * mx
    resid = max(abs(v - (icpt + slope * p)) for p, v in pairs)
    return {"slope": slope, "offset": icpt, "log10": log, "max_fit_residual": resid}


def apply(cal, coord):
    v = cal["offset"] + cal["slope"] * coord
    return 10 ** v if cal["log10"] else v


def is_log(values):
    pos = sorted(v for v in values if v > 0)
    return len(pos) >= 3 and len(pos) == len(values) and all(
        abs(math.log10(b / a) - 1) < 1e-9 for a, b in zip(pos, pos[1:]))


def path_points(items):
    pts = []

    def add(p):
        if not pts or abs(pts[-1][0] - p[0]) > 1e-6 or abs(pts[-1][1] - p[1]) > 1e-6:
            pts.append(p)
    for it in items:
        if it[0] == "l":
            add((it[1].x, it[1].y)); add((it[2].x, it[2].y))
        elif it[0] == "c":
            p0, p1, p2, p3 = it[1], it[2], it[3], it[4]
            for k in range(BEZIER_SAMPLES + 1):
                t = k / BEZIER_SAMPLES
                a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2, t ** 3
                add((a * p0.x + b * p1.x + c * p2.x + d * p3.x, a * p0.y + b * p1.y + c * p2.y + d * p3.y))
        else:
            raise ValueError(f"unsupported path item {it[0]!r}")
    return pts


class Raster:
    """RGB render of a page region with coordinates in PDF points."""

    def __init__(self, page, rect):
        self.rect = rect
        self.pix = page.get_pixmap(dpi=DPI, clip=rect, alpha=False)
        self.s = self.pix.samples
        self.w, self.h, self.n = self.pix.width, self.pix.height, self.pix.n

    def px(self, x, y):
        i = (y * self.w + x) * self.n
        return self.s[i], self.s[i + 1], self.s[i + 2]

    def to_pt(self, x=None, y=None):
        return (self.rect.x0 + (x + 0.5) / SCALE) if x is not None else (self.rect.y0 + (y + 0.5) / SCALE)


def grid_lines(page, frame):
    """Positions (pt) of light-grey grid lines inside the frame, from the render."""
    r = Raster(page, frame)
    grey = lambda p: max(p) - min(p) < 25 and 150 <= sum(p) / 3 <= 240
    margin = 6

    def runs(flags, to_pt):
        out, start = [], None
        for i, f in enumerate(flags + [False]):
            if f and start is None:
                start = i
            elif not f and start is not None:
                out.append(to_pt((start + i - 1) / 2))
                start = None
        return out
    rows = [margin <= y < r.h - margin and
            sum(grey(r.px(x, y)) for x in range(margin, r.w - margin, 2)) > 0.3 * (r.w - 2 * margin) / 2
            for y in range(r.h)]
    cols = [margin <= x < r.w - margin and
            sum(grey(r.px(x, y)) for y in range(margin, r.h - margin, 2)) > 0.3 * (r.h - 2 * margin) / 2
            for x in range(r.w)]
    return runs(cols, lambda x: r.to_pt(x=x)), runs(rows, lambda y: r.to_pt(y=y))


def calibrate(labels, candidates, horizontal):
    """Pair tick labels with grid lines or frame edges and fit the axis."""
    centre = (lambda w: (w[0] + w[2]) / 2) if horizontal else (lambda w: (w[1] + w[3]) / 2)
    pos = sorted(centre(w) for w in labels)
    spacing = min(b - a for a, b in zip(pos, pos[1:]))
    pairs, unpaired, offsets = [], [], []
    for w in labels:
        c = centre(w)
        best = min(candidates, key=lambda p: abs(p - c))
        if abs(best - c) <= 0.35 * spacing:
            pairs.append((best, float(w[4])))
            offsets.append(c - best)
        else:
            unpaired.append(w[4])
    values = [v for _, v in pairs]
    cal = fit(pairs, is_log(values)) if len(pairs) >= 2 else None
    if cal:
        cal.update(labels=[w[4] for w in labels], paired=len(pairs), unpaired=unpaired,
                   label_to_line_offset_pt=[round(o, 2) for o in offsets],
                   range=[min(values), max(values)])
    return cal


def legend(page, frame, inside_words, curves):
    """Map legend text to curve colours by sampling the swatch left of each legend line."""
    lines = {}
    for w in inside_words:
        lines.setdefault(round((w[1] + w[3]) / 2), []).append(w)
    out = {}
    for _, ws in sorted(lines.items()):
        ws = sorted(ws, key=lambda w: w[0])
        text = " ".join(w[4] for w in ws)
        x0, yc = ws[0][0], (ws[0][1] + ws[0][3]) / 2
        region = pymupdf.Rect(x0 - 26, yc - 2, x0 - 1, yc + 2)
        if not frame.contains(region):
            continue
        r = Raster(page, region)
        sat = [r.px(x, y) for y in range(r.h) for x in range(r.w)]
        sat = [p for p in sat if max(p) - min(p) > 60]
        if len(sat) < 20:
            continue
        mean = tuple(sum(p[i] for p in sat) / len(sat) / 255 for i in range(3))
        best = min(curves, key=lambda c: sum((a - b) ** 2 for a, b in zip(c["color"], mean)))
        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(best["color"], mean)))
        out[text] = {"swatch_rgb": [round(v, 3) for v in mean], "curve_color": best["color"],
                     "colour_distance": round(dist, 3)}
    return out


def arrow_directions(draws, region):
    """Fig. 6 style: short filled arrows in a curve colour point to that curve's axis."""
    out = {}
    for d in draws:
        if d.get("fill") and region.intersects(d["rect"]) and d["rect"].width < 40 and d["rect"].height < 6 \
                and max(d["fill"]) - min(d["fill"]) > 0.3 and len(d["items"]) >= 5:
            xs = [p.x for it in d["items"] for p in it[1:] if hasattr(p, "x")]
            lo, hi = min(xs), max(xs)
            n_lo = sum(abs(x - lo) < 0.3 for x in xs)
            n_hi = sum(abs(x - hi) < 0.3 for x in xs)
            out[tuple(round(c, 3) for c in d["fill"])] = "left" if n_lo < n_hi else "right"
    return out


def digitize_page(page, pno):
    words = page.get_text("words")
    draws = page.get_drawings()
    figures = []
    for cap in [w for w in words if w[4] == "Figure"]:
        left = cap[0] < 306
        x0, x1 = (20, 306) if left else (306, 600)
        below = [w[1] for w in words if w[4] == "Figure" and (w[0] < 306) == left and w[1] > cap[1] + 5]
        region = pymupdf.Rect(x0, cap[3], x1, min(below) if below else 760)
        caption = " ".join(w[4] for w in words if abs(w[1] - cap[1]) < 2 and cap[0] - 1 <= w[0] < cap[0] + 260)
        frames = [d["rect"] for d in draws if d.get("color") and all(c < 0.2 for c in d["color"])
                  and (d.get("width") or 0) >= 0.9 and len(d["items"]) == 1 and d["items"][0][0] == "re"
                  and region.contains(d["rect"]) and d["rect"].width > 100 and d["rect"].height > 80]
        if len(frames) != 1:
            figures.append({"page": pno, "caption": caption, "error": f"{len(frames)} plot frames found"})
            continue
        frame = frames[0]
        curves = [d for d in draws if d.get("color") and frame.intersects(d["rect"]) and (d.get("width") or 0) > 1.2
                  and len(d["items"]) >= 2 and max(d["color"]) - min(d["color"]) > 0.2]
        vgrid, hgrid = grid_lines(page, frame)
        near = pymupdf.Rect(frame.x0 - 40, frame.y0 - 8, frame.x1 + 40, frame.y1 + 16)
        numeric = [w for w in words if near.contains(pymupdf.Rect(w[:4])) and NUM.fullmatch(w[4])]
        ylab_l = [w for w in numeric if w[2] <= frame.x0 + 1 and frame.y0 - 8 <= w[1] <= frame.y1]
        ylab_r = [w for w in numeric if w[0] >= frame.x1 - 1 and frame.y0 - 8 <= w[1] <= frame.y1]
        xlab = [w for w in numeric if w[1] >= frame.y1 - 1]
        axes = {"x": calibrate(xlab, vgrid + [frame.x0, frame.x1], True)}
        if len(ylab_l) >= 3:
            axes["y_left"] = calibrate(ylab_l, hgrid + [frame.y0, frame.y1], False)
        if len(ylab_r) >= 3:
            axes["y_right"] = calibrate(ylab_r, hgrid + [frame.y0, frame.y1], False)
        inside = [w for w in words if frame.contains(pymupdf.Rect(w[:4]))]
        out_curves = []
        for d in curves:
            pts = [(x, y) for x, y in path_points(d["items"])
                   if frame.x0 - 0.5 <= x <= frame.x1 + 0.5 and frame.y0 - 0.5 <= y <= frame.y1 + 0.5]
            entries = {k: [[apply(axes["x"], x), apply(a, y)] for x, y in pts]
                       for k, a in axes.items() if k.startswith("y_") and a}
            out_curves.append({"color": [round(c, 3) for c in d["color"]], "segments": len(d["items"]),
                               "kinds": sorted({i[0] for i in d["items"]}), "line_width_pt": d.get("width"),
                               "points_by_axis": entries})
        figures.append({
            "page": pno, "caption": caption, "frame_pt": [frame.x0, frame.y0, frame.x1, frame.y1],
            "grid_lines_pt": {"vertical": [round(v, 2) for v in vgrid], "horizontal": [round(v, 2) for v in hgrid]},
            "axes": axes, "frame_values": {k: [apply(a, frame.x0 if k == "x" else frame.y1),
                                              apply(a, frame.x1 if k == "x" else frame.y0)]
                                          for k, a in axes.items() if a},
            "legend": legend(page, frame, inside, out_curves),
            "arrows": {str(list(k)): v for k, v in arrow_directions(draws, frame).items()},
            "other_text": " ".join(w[4] for w in inside if not NUM.fullmatch(w[4])),
            "curves": out_curves})
    return figures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--pages", type=int, nargs="+", default=[2, 3])
    args = ap.parse_args()
    doc = pymupdf.open(str(args.pdf))
    figures = []
    for p in args.pages:
        figures += digitize_page(doc[p - 1], p)
    report = {"schema": "datasheet-figures/2",
              "source": {"pdf": args.pdf.name, "sha256": hashlib.sha256(args.pdf.read_bytes()).hexdigest()},
              "method": ("vector paths read from the PDF; axes fitted to grid-line and frame positions found in a "
                         f"{DPI} dpi render, each paired with its tick label; points clipped to the plot frame; "
                         "legend swatch colours sampled from the render"),
              "figures": figures}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    for f in figures:
        if "error" in f:
            print(f["caption"], "ERROR", f["error"])
            continue
        print(f"\n{f['caption']}")
        for k, a in f["axes"].items():
            if a is None:
                print(f"  {k}: CALIBRATION FAILED")
                continue
            print(f"  {k}: paired {a['paired']}/{len(a['labels'])} unpaired={a['unpaired']} log={a['log10']} "
                  f"fit_residual={a['max_fit_residual']:.2e} label_offsets={a['label_to_line_offset_pt']} "
                  f"frame={[round(v, 4) for v in f['frame_values'][k]]}")
        print(f"  grid: {len(f['grid_lines_pt']['vertical'])} vertical, {len(f['grid_lines_pt']['horizontal'])} horizontal")
        for t, m in f["legend"].items():
            print(f"  legend {t!r} -> {m['curve_color']} (distance {m['colour_distance']})")
        for c, dirn in f["arrows"].items():
            print(f"  arrow {c} points {dirn}")
        for c in f["curves"]:
            print(f"  curve {c['color']} points={ {k: len(v) for k, v in c['points_by_axis'].items()} }")


if __name__ == "__main__":
    main()
