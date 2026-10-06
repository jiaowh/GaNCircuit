"""Rasterize RS-274X Gerber copper layers and read Excellon drill files.

A deliberately small reader for the EPC90133 (B5253 Rev 2.0) package, which Altium
exported with: inch or mm units, FSLA coordinate format, linear and
multi-quadrant circular interpolation (G01/G02/G03 with G75), circle and rectangle
apertures, aperture macros built from primitives 1 (circle), 4 (outline), 20
(vector line) and 21 (centre line), filled regions (G36/G37) and dark/clear
polarity. Anything outside that subset (single-quadrant arcs, step-repeat, block apertures,
other primitives) raises GerberUnsupported rather than being skipped, so a
later board cannot silently lose copper.

The raster is a boolean grid (row 0 at the lowest y) at a chosen pitch. Board
extraction meshes it onto FastHenry segment grids; rendering it lets a person
inspect the geometry.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

MM_PER_INCH = 25.4


class GerberUnsupported(ValueError):
    pass


@dataclass
class Aperture:
    kind: str  # "C", "R", "O" or a macro name
    params: list[float]


@dataclass
class Primitive:
    """One drawing operation in mm: ('poly', points) or ('line', p0, p1, width)."""
    polarity: bool
    kind: str
    data: tuple


@dataclass
class GerberLayer:
    name: str
    primitives: list[Primitive] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)

    def bounds(self):
        xs, ys = [], []
        for p in self.primitives:
            pts = p.data[0] if p.kind == "poly" else p.data[:2]
            pad = p.data[2] / 2 if p.kind == "line" else 0.0
            for x, y in pts:
                xs += [x - pad, x + pad]
                ys += [y - pad, y + pad]
        return min(xs), min(ys), max(xs), max(ys)


def _circle(cx, cy, d, n=32):
    r = d / 2
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def _rotate(points, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [(x * c - y * s, x * s + y * c) for x, y in points]


def _eval(expr, variables):
    expr = expr.strip()
    for k in sorted(variables, key=lambda v: len(str(v)), reverse=True):  # $10 before $1; keys are ints
        expr = expr.replace(f"${k}", repr(variables[k]))
    if not re.fullmatch(r"[0-9eE.+\-*/xX() ]*", expr):
        raise GerberUnsupported(f"macro expression {expr!r}")
    return float(eval(expr.replace("x", "*").replace("X", "*"), {"__builtins__": {}}))


def _macro_shapes(body, params, scale):
    """Primitives of an aperture macro as (exposure, polygon) in mm, relative to the flash point."""
    variables = {i + 1: v for i, v in enumerate(params)}
    shapes = []
    for stmt in body:
        stmt = stmt.strip()
        if not stmt or stmt.startswith("0 ") or stmt == "0":
            continue
        if stmt.startswith("$"):
            k, expr = stmt[1:].split("=", 1)
            variables[int(k)] = _eval(expr, variables)
            continue
        f = [_eval(x, variables) for x in stmt.split(",")]
        code = int(f[0])
        if code == 1:  # circle: exposure, diameter, x, y[, rotation]
            rot = f[5] if len(f) > 5 else 0.0
            cx, cy = _rotate([(f[3] * scale, f[4] * scale)], rot)[0]
            shapes.append((f[1] != 0, _circle(cx, cy, f[2] * scale)))
        elif code == 21:  # centre line: exposure, width, height, cx, cy, rotation
            w, h, cx, cy = (v * scale for v in f[2:6])
            pts = [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)]
            shapes.append((f[1] != 0, _rotate(pts, f[6])))
        elif code == 20:  # vector line: exposure, width, x0, y0, x1, y1, rotation
            w, x0, y0, x1, y1 = (v * scale for v in f[2:7])
            L = math.hypot(x1 - x0, y1 - y0)
            ux, uy = ((x1 - x0) / L, (y1 - y0) / L) if L else (1.0, 0.0)
            nx, ny = -uy * w / 2, ux * w / 2
            pts = [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)]
            shapes.append((f[1] != 0, _rotate(pts, f[7])))
        elif code == 4:  # outline: exposure, n, x0, y0, ..., xn, yn, rotation
            n = int(f[2])
            pts = [(f[3 + 2 * i] * scale, f[4 + 2 * i] * scale) for i in range(n + 1)]
            shapes.append((f[1] != 0, _rotate(pts, f[5 + 2 * n])))
        else:
            raise GerberUnsupported(f"aperture macro primitive {code}")
    return shapes


def parse_gerber(text: str, name: str = "") -> GerberLayer:
    layer = GerberLayer(name)
    scale = None
    fmt = None
    apertures: dict[int, Aperture] = {}
    macros: dict[str, list[str]] = {}
    polarity = True
    current = None
    x = y = 0.0
    region = None  # list of contours while in G36
    interp = "G01"
    quadrant = None
    # Split into extended (%...%) blocks and word commands terminated by '*'.
    tokens = re.findall(r"%[^%]*%|[^%*]+\*", text.replace("\r", "").replace("\n", ""))
    for tok in tokens:
        if tok.startswith("%"):
            body = tok[1:-1]
            if body.startswith("FS"):
                m = re.fullmatch(r"FSLAX(\d)(\d)Y(\d)(\d)\*", body)
                if not m:
                    raise GerberUnsupported(f"format {body!r}")
                fmt = int(m.group(2))
            elif body.startswith("MO"):
                scale = MM_PER_INCH if body.startswith("MOIN") else 1.0 if body.startswith("MOMM") else None
            elif body.startswith("AD"):
                m = re.fullmatch(r"ADD(\d+)([A-Za-z_][\w.$]*),?([^*]*)\*", body)
                if not m:
                    raise GerberUnsupported(f"aperture {body!r}")
                params = [float(v) for v in m.group(3).split("X") if v] if m.group(3) else []
                apertures[int(m.group(1))] = Aperture(m.group(2), params)
            elif body.startswith("AM"):
                parts = body.split("*")
                macros[parts[0][2:]] = [p for p in parts[1:] if p]
            elif body.startswith("LP"):
                polarity = body.startswith("LPD")
            elif body.startswith(("SR", "AB", "LM", "LR", "LS")):
                if body.startswith("SR") and body.strip("*") in ("SR", "SRX1Y1I0J0"):
                    continue
                raise GerberUnsupported(f"extended command {body!r}")
            elif body.startswith(("TF", "TA", "TO", "TD", "IP", "IN", "OF")):
                continue
            continue
        cmd = tok[:-1]
        if cmd.startswith("G04"):
            layer.comments.append(cmd[3:].strip())
            continue
        if cmd in ("M02", "M00", "M01"):
            break
        for g in re.findall(r"G(\d+)", cmd):
            g = int(g)
            if g in (1, 2, 3):
                interp = f"G0{g}"
            elif g == 36:
                region = []
            elif g == 37:
                for c in region:
                    if len(c) >= 3:
                        layer.primitives.append(Primitive(polarity, "poly", (c,)))
                region = None
            elif g in (70, 71, 74, 75, 90, 91):
                if g == 74:
                    quadrant = "single"
                if g == 75:
                    quadrant = "multi"
                if g == 91:
                    raise GerberUnsupported("incremental coordinates")
                if g == 70:
                    scale = MM_PER_INCH
                if g == 71:
                    scale = 1.0
        m = re.search(r"D(\d+)$", cmd)
        dcode = int(m.group(1)) if m else None
        if dcode is not None and dcode >= 10:
            current = apertures[dcode]
            continue
        coords = dict(re.findall(r"([XYIJ])([+-]?\d+)", cmd))
        if not coords and dcode is None:
            continue
        if scale is None or fmt is None:
            raise GerberUnsupported("coordinates before units and format")
        nx = int(coords["X"]) / 10 ** fmt * scale if "X" in coords else x
        ny = int(coords["Y"]) / 10 ** fmt * scale if "Y" in coords else y
        if dcode is None:
            dcode = 1 if region is not None or coords else None
        if dcode == 2:
            if region is not None:
                region.append([(nx, ny)])
        elif dcode == 1:
            if interp == "G01":
                path = [(nx, ny)]
            else:
                if quadrant != "multi":
                    raise GerberUnsupported("circular interpolation outside multi-quadrant mode (G75)")
                ci = int(coords.get("I", 0)) / 10 ** fmt * scale
                cj = int(coords.get("J", 0)) / 10 ** fmt * scale
                path = _arc((x, y), (nx, ny), (x + ci, y + cj), clockwise=interp == "G02")
            if region is not None:
                if not region:
                    region.append([(x, y)])
                region[-1].extend(path)
            else:
                if current is None:
                    raise GerberUnsupported("draw without aperture")
                if current.kind != "C":
                    raise GerberUnsupported(f"draw with {current.kind} aperture")
                for a, b in zip([(x, y)] + path[:-1], path):
                    layer.primitives.append(Primitive(polarity, "line", (a, b, current.params[0] * scale)))
        elif dcode == 3:
            layer.primitives += [Primitive(polarity if e else not polarity, "poly", ([(nx + px, ny + py) for px, py in pts],))
                                 for e, pts in _flash(current, scale, macros)]
        x, y = nx, ny
    return layer


def _arc(start, end, centre, clockwise, max_step_deg=5.0):
    """Points along a G75 arc from start to end (start excluded); equal points mean a full circle."""
    a0 = math.atan2(start[1] - centre[1], start[0] - centre[0])
    a1 = math.atan2(end[1] - centre[1], end[0] - centre[0])
    r0 = math.hypot(start[0] - centre[0], start[1] - centre[1])
    r1 = math.hypot(end[0] - centre[0], end[1] - centre[1])
    if abs(r0 - r1) > max(1e-3, 0.01 * r0):
        raise GerberUnsupported("arc end point is not on the arc")
    sweep = a1 - a0
    if clockwise:
        sweep = sweep - 2 * math.pi if sweep >= 0 else sweep
        if abs(end[0] - start[0]) < 1e-9 and abs(end[1] - start[1]) < 1e-9:
            sweep = -2 * math.pi
    else:
        sweep = sweep + 2 * math.pi if sweep <= 0 else sweep
        if abs(end[0] - start[0]) < 1e-9 and abs(end[1] - start[1]) < 1e-9:
            sweep = 2 * math.pi
    n = max(1, int(math.ceil(abs(math.degrees(sweep)) / max_step_deg)))
    pts = [(centre[0] + r0 * math.cos(a0 + sweep * k / n), centre[1] + r0 * math.sin(a0 + sweep * k / n))
           for k in range(1, n)]
    return pts + [end]


def _flash(ap, scale, macros):
    if ap is None:
        raise GerberUnsupported("flash without aperture")
    p = [v * scale for v in ap.params]
    if ap.kind == "C":
        if len(p) > 1:
            raise GerberUnsupported("circle aperture with hole")
        return [(True, _circle(0, 0, p[0]))]
    if ap.kind == "R":
        w, h = p[:2]
        return [(True, [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)])]
    if ap.kind == "O":
        w, h = p[:2]
        r = min(w, h) / 2
        body = [(-w / 2 + r, -h / 2), (w / 2 - r, -h / 2), (w / 2 - r, h / 2), (-w / 2 + r, h / 2)] if w >= h else \
               [(-w / 2, -h / 2 + r), (w / 2, -h / 2 + r), (w / 2, h / 2 - r), (-w / 2, h / 2 - r)]
        ends = ([(-w / 2 + r, 0), (w / 2 - r, 0)] if w >= h else [(0, -h / 2 + r), (0, h / 2 - r)])
        return [(True, body)] + [(True, _circle(cx, cy, 2 * r)) for cx, cy in ends]
    if ap.kind in macros:
        return _macro_shapes(macros[ap.kind], ap.params, scale)
    raise GerberUnsupported(f"aperture type {ap.kind}")


@dataclass
class Raster:
    origin: tuple[float, float]  # mm, centre of pixel (0, 0)
    pitch: float  # mm
    grid: np.ndarray  # bool, [row = y index, col = x index]

    def area_mm2(self):
        return float(self.grid.sum()) * self.pitch ** 2

    def at(self, x, y):
        i = round((y - self.origin[1]) / self.pitch)
        j = round((x - self.origin[0]) / self.pitch)
        return bool(self.grid[i, j]) if 0 <= i < self.grid.shape[0] and 0 <= j < self.grid.shape[1] else False


def rasterize(layer: GerberLayer, bounds, pitch: float) -> Raster:
    """Draw the layer's primitives in order (dark adds, clear removes) on a grid of the given pitch (mm)."""
    x0, y0, x1, y1 = bounds
    nx, ny = int(math.ceil((x1 - x0) / pitch)) + 1, int(math.ceil((y1 - y0) / pitch)) + 1
    img = Image.new("1", (nx, ny), 0)
    d = ImageDraw.Draw(img)
    to_px = lambda p: ((p[0] - x0) / pitch, (p[1] - y0) / pitch)
    for prim in layer.primitives:
        fill = 1 if prim.polarity else 0
        if prim.kind == "poly":
            d.polygon([to_px(p) for p in prim.data[0]], fill=fill)
        else:
            p0, p1, w = prim.data
            a, b = to_px(p0), to_px(p1)
            wp = w / pitch
            if a != b:
                ux, uy = b[0] - a[0], b[1] - a[1]
                L = math.hypot(ux, uy)
                nxp, nyp = -uy / L * wp / 2, ux / L * wp / 2
                d.polygon([(a[0] + nxp, a[1] + nyp), (b[0] + nxp, b[1] + nyp), (b[0] - nxp, b[1] - nyp),
                           (a[0] - nxp, a[1] - nyp)], fill=fill)
            for c in (a, b):
                d.ellipse([c[0] - wp / 2, c[1] - wp / 2, c[0] + wp / 2, c[1] + wp / 2], fill=fill)
    return Raster((x0, y0), pitch, np.array(img, dtype=bool))


@dataclass
class Drill:
    x: float  # mm
    y: float
    diameter: float
    plated: bool


def parse_excellon(text: str) -> list[Drill]:
    """Excellon with INCH or METRIC header; zero suppression per LZ/TZ and ;FILE_FORMAT=i:d."""
    scale, digits, keep = MM_PER_INCH, (2, 5), "LZ"
    tools, plated_section, holes = {}, True, []
    tool = None
    x = y = None
    header = True
    for line in text.replace("\r", "").split("\n"):
        line = line.strip()
        if m := re.match(r";FILE_FORMAT=(\d):(\d)", line):
            digits = (int(m.group(1)), int(m.group(2)))
        elif line.startswith(";TYPE="):
            plated_section = line == ";TYPE=PLATED"
        elif line.startswith(("INCH", "METRIC")):
            scale = MM_PER_INCH if line.startswith("INCH") else 1.0
            keep = "TZ" if "TZ" in line else "LZ"
        elif header and (m := re.match(r"T(\d+)(?:F\d+)?(?:S\d+)?C([\d.]+)", line)):
            tools[int(m.group(1))] = (float(m.group(2)) * scale, plated_section)
        elif line == "%":
            header = False
        elif not header and (m := re.fullmatch(r"T(\d+)", line)):
            tool = int(m.group(1))
        elif not header and line.startswith(("X", "Y")):
            for axis, raw in re.findall(r"([XY])([+-]?[\d.]+)", line):
                if "." in raw:  # explicit decimal point (KiCad's "decimal" format): no implied digits
                    v = float(raw) * scale
                    if axis == "X":
                        x = v
                    else:
                        y = v
                    continue
                sign = -1 if raw.startswith("-") else 1
                raw = raw.lstrip("+-")
                n = sum(digits)
                raw = raw.ljust(n, "0") if keep == "LZ" else raw.rjust(n, "0")
                v = sign * int(raw) / 10 ** digits[1] * scale
                if axis == "X":
                    x = v
                else:
                    y = v
            d, plated = tools[tool]
            holes.append(Drill(x, y, d, plated))
        elif line.startswith(("G85", "M15", "G00", "G01")):
            raise ValueError(f"unsupported Excellon routing command {line!r}")
    return holes


def load_layer(path: str | Path) -> GerberLayer:
    path = Path(path)
    return parse_gerber(path.read_text(encoding="latin-1"), path.suffix.lstrip("."))
