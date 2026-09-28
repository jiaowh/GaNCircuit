#!/usr/bin/env python3
"""Extract a vector curve from a datasheet figure, with axis calibration from its tick labels.

EPC datasheet figures are vector drawings, so the plotted polyline can be read
exactly instead of traced from an image. This records what the vendor drew; it
does not add information the vendor's rendering lacks (the polyline has a
finite number of vertices, and its line width is reported as an uncertainty).

Requires PyMuPDF (available under WSL on the project host). Example:

    python3 scripts/digitize_datasheet_figure.py --page 3 --region 330 295 600 500 \\
        --curve-color 0 0.47 0.29 --x-name qg_nC --y-name vgs_V \\
        --figure "Figure 7: Gate Charge" --output results/gan/epc2204-fig7-digitized.json
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = ROOT / "vendor" / "epc" / "EPC2204_datasheet.pdf"


def linear_fit(pairs):
    n = len(pairs)
    mx = sum(p for p, _ in pairs) / n
    my = sum(v for _, v in pairs) / n
    sxx = sum((p - mx) ** 2 for p, _ in pairs)
    slope = sum((p - mx) * (v - my) for p, v in pairs) / sxx
    icpt = my - slope * mx
    resid = [v - (icpt + slope * p) for p, v in pairs]
    return slope, icpt, max(abs(r) for r in resid)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    ap.add_argument("--page", type=int, required=True, help="1-based page number")
    ap.add_argument("--region", type=float, nargs=4, required=True, metavar=("X0", "Y0", "X1", "Y1"))
    ap.add_argument("--curve-color", type=float, nargs=3, required=True)
    ap.add_argument("--x-name", required=True)
    ap.add_argument("--y-name", required=True)
    ap.add_argument("--figure", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    doc = pymupdf.open(str(args.pdf))
    page = doc[args.page - 1]
    region = pymupdf.Rect(*args.region)
    words = [w for w in page.get_text("words") if region.contains(pymupdf.Rect(w[:4]))]
    numeric = [w for w in words if re.fullmatch(r"-?\d+(?:\.\d+)?", w[4])]
    frame = next(d["rect"] for d in page.get_drawings()
                 if region.intersects(d["rect"]) and d.get("color") == (0.0, 0.0, 0.0)
                 and (d.get("width") or 0) >= 0.9 and d["rect"].width > 100)
    # Y tick labels sit left of the frame; X tick labels sit below it.
    ylab = [w for w in numeric if w[2] <= frame.x0 + 1]
    xlab = [w for w in numeric if w[1] >= frame.y1 - 1 and w[2] > frame.x0 + 1]
    ys, yi, yres = linear_fit([((w[1] + w[3]) / 2, float(w[4])) for w in ylab])
    xs, xi, xres = linear_fit([((w[0] + w[2]) / 2, float(w[4])) for w in xlab])
    target = tuple(args.curve_color)
    curves = [d for d in page.get_drawings() if region.intersects(d["rect"]) and d.get("color")
              and all(abs(a - b) < 0.01 for a, b in zip(d["color"], target))]
    if len(curves) != 1:
        raise SystemExit(f"expected one curve of colour {target}, found {len(curves)}")
    curve = curves[0]
    pts = []
    for it in curve["items"]:
        if it[0] != "l":
            raise SystemExit(f"unsupported path item {it[0]!r}; only straight segments are handled")
        for p in (it[1], it[2]):
            if not pts or (abs(pts[-1][0] - p.x) > 1e-6 or abs(pts[-1][1] - p.y) > 1e-6):
                pts.append((p.x, p.y))
    data = [{args.x_name: xi + xs * x, args.y_name: yi + ys * y} for x, y in pts]
    width = curve.get("width") or 0
    report = {
        "schema": "datasheet-figure-digitization/1",
        "source": {"pdf": args.pdf.name, "sha256": hashlib.sha256(args.pdf.read_bytes()).hexdigest(),
                   "page": args.page, "figure": args.figure},
        "method": ("vector polyline read from the PDF; axes calibrated by a least-squares fit of tick-label "
                   "centres (label value against page coordinate)"),
        "calibration": {
            "x": {"units_per_pt": xs, "offset": xi, "max_label_residual": xres, "labels": [w[4] for w in xlab]},
            "y": {"units_per_pt": ys, "offset": yi, "max_label_residual": yres, "labels": [w[4] for w in ylab]},
            "frame_pt": [frame.x0, frame.y0, frame.x1, frame.y1],
            "frame_corners": {"x0": xi + xs * frame.x0, "x1": xi + xs * frame.x1,
                              "y_bottom": yi + ys * frame.y1, "y_top": yi + ys * frame.y0}},
        "uncertainty": {
            "line_width_pt": width,
            "half_line_width": {args.x_name: abs(xs) * width / 2, args.y_name: abs(ys) * width / 2},
            "note": ("Between vertices the vendor's line is straight; the underlying measurement or model "
                     "curve between vertices is unknown. Datasheet curves are typical, vendor-described data.")},
        "vertices": len(data),
        "points": data,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"vertices": len(data), "calibration": report["calibration"],
                      "first": data[0], "last": data[-1]}, indent=2))


if __name__ == "__main__":
    main()
