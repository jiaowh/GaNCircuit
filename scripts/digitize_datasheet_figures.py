#!/usr/bin/env python3
"""Extract every vector curve from the EPC2204 datasheet figures.

EPC datasheet figures are vector drawings, so the plotted paths can be read
exactly rather than traced from an image. For each "Figure N" caption the
script finds the coloured curves in that figure's region and calibrates the
axes by fitting tick-label positions (log10 fit when the labels are powers of
ten). It then maps each curve colour to its legend text by the short
same-coloured legend swatch next to the label, or by coloured label text.
Points outside the axis range (curves clipped at the plot frame) are dropped.
Bezier segments are sampled.

This records what the vendor drew; the traces are typical, vendor-described
curves. Requires PyMuPDF (runs under WSL on the project host):

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


def fit(pairs, log=False):
    pairs = [(p, math.log10(v) if log else v) for p, v in pairs]
    n = len(pairs)
    mx = sum(p for p, _ in pairs) / n
    my = sum(v for _, v in pairs) / n
    slope = sum((p - mx) * (v - my) for p, v in pairs) / sum((p - mx) ** 2 for p, _ in pairs)
    icpt = my - slope * mx
    resid = max(abs(v - (icpt + slope * p)) for p, v in pairs)
    return {"slope": slope, "offset": icpt, "log10": log, "max_label_residual": resid}


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


def span_colors(page, region):
    """Text lines in the region with their (r, g, b) colour."""
    out = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                if region.intersects(pymupdf.Rect(span["bbox"])) and span["text"].strip():
                    c = span["color"]
                    out.append((span["text"].strip(), ((c >> 16) / 255, ((c >> 8) & 255) / 255, (c & 255) / 255),
                                pymupdf.Rect(span["bbox"])))
    return out


def same(c1, c2, tol=0.02):
    return c1 is not None and c2 is not None and all(abs(a - b) < tol for a, b in zip(c1, c2))


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
        curves = [d for d in draws if d.get("color") and region.intersects(d["rect"]) and (d.get("width") or 0) > 1.2
                  and len(d["items"]) >= 2 and d["color"] != (0.0, 0.0, 0.0)]
        if not curves:
            continue
        cx0 = min(d["rect"].x0 for d in curves)
        cx1 = max(d["rect"].x1 for d in curves)
        cy1 = max(d["rect"].y1 for d in curves)
        inside = [w for w in words if region.contains(pymupdf.Rect(w[:4]))]
        numeric = [w for w in inside if NUM.fullmatch(w[4])]
        # Axis labels: a right-aligned column left of the curves (left axis), a
        # left-aligned column right of them (right axis), a row below them (x axis).
        cols = {}
        for w in numeric:
            if w[2] <= cx0 + 2:
                cols.setdefault(("left", round(w[2])), []).append(w)
            elif w[0] >= cx1 - 2:
                cols.setdefault(("right", round(w[0])), []).append(w)
        rows = {}
        for w in numeric:
            if w[1] >= cy1 - 2:
                rows.setdefault(round(w[1]), []).append(w)
        axes = {}
        for (side, _), ws in cols.items():
            if len(ws) >= 3:
                vals = [float(w[4]) for w in ws]
                axes["y_" + side] = dict(fit([((w[1] + w[3]) / 2, float(w[4])) for w in ws], is_log(vals)),
                                         labels=[w[4] for w in ws], range=[min(vals), max(vals)])
        xrow = max((ws for ws in rows.values() if len(ws) >= 3), key=len, default=None)
        if xrow is None or not any(k.startswith("y_") for k in axes):
            figures.append({"page": pno, "caption": caption, "error": "axes not found"})
            continue
        xv = [float(w[4]) for w in xrow]
        axes["x"] = dict(fit([((w[0] + w[2]) / 2, float(w[4])) for w in xrow], is_log(xv)),
                         labels=[w[4] for w in xrow], range=[min(xv), max(xv)])
        texts = span_colors(page, region)
        out_curves = []
        for d in curves:
            col = tuple(round(c, 3) for c in d["color"])
            # Legend: a short same-coloured swatch with text to its right, or coloured text.
            swatches = [s for s in draws if same(s.get("color"), d["color"]) and s is not d
                        and region.intersects(s["rect"]) and s["rect"].width < 30 and s["rect"].height < 4]
            label = None
            for s in swatches:
                near = [w for w in inside if abs((w[1] + w[3]) / 2 - (s["rect"].y0 + s["rect"].y1) / 2) < 4
                        and 0 <= w[0] - s["rect"].x1 < 60]
                if near:
                    label = " ".join(w[4] for w in sorted(near, key=lambda w: w[0]))
            coloured = [t for t, c, _ in texts if same(c, d["color"], 0.03)]
            pts = path_points(d["items"])
            entries = {}
            for yaxis in [k for k in axes if k.startswith("y_")]:
                ya, xa = axes[yaxis], axes["x"]
                data = []
                for x, y in pts:
                    xv_, yv_ = apply(xa, x), apply(ya, y)
                    lo, hi = ya["range"]
                    xlo, xhi = xa["range"]
                    if lo - 1e-9 * abs(hi) <= yv_ <= hi * (1 + 1e-6) + 1e-12 and xlo - 1e-9 <= xv_ <= xhi * (1 + 1e-6) + 1e-12:
                        data.append([xv_, yv_])
                entries[yaxis] = data
            out_curves.append({"color": col, "legend_swatch_label": label, "coloured_text": coloured,
                               "segments": len(d["items"]), "kinds": sorted({i[0] for i in d["items"]}),
                               "line_width_pt": d.get("width"), "points_by_axis": entries})
        figures.append({"page": pno, "caption": caption,
                        "axes": axes, "other_text": " ".join(w[4] for w in inside if not NUM.fullmatch(w[4])),
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
    report = {"schema": "datasheet-figures/1",
              "source": {"pdf": args.pdf.name, "sha256": hashlib.sha256(args.pdf.read_bytes()).hexdigest()},
              "method": ("vector paths read from the PDF; axes from a least-squares fit of tick-label centres "
                         "(log10 when labels are decades); points outside the labelled axis range dropped"),
              "figures": figures}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    for f in figures:
        if "error" in f:
            print(f["caption"], "ERROR", f["error"])
            continue
        ax = {k: (v["labels"], round(v["max_label_residual"], 4), v["log10"]) for k, v in f["axes"].items()}
        print(f"\n{f['caption']}\n  axes {ax}")
        for c in f["curves"]:
            n = {k: len(v) for k, v in c["points_by_axis"].items()}
            print(f"  curve {c['color']} swatch={c['legend_swatch_label']!r} text={c['coloured_text']} points={n}")


if __name__ == "__main__":
    main()
