"""Two-dimensional electrostatic boundary-element solver for conductor cross-sections (capacitance per unit length).

Conductors are closed polygons in a uniform medium. Each side is split into panels clustered towards its corners
(cosine spacing, where the charge density is singular); each panel carries a constant line-charge density and the
potential is collocated at panel midpoints, using the exact integral of ln r over a straight segment. Solving for every
conductor at unit potential (others at zero) gives the Maxwell capacitance matrix. When one conductor encloses all
others (a wall), the block of the others is their capacitance matrix with the wall as reference, independent of what
lies outside the wall.

Use in this project: the via-array benchmark's reference, L' = mu0 eps0 C'^-1 for vertical currents between perfectly
conducting plates (scripts/via_array_benchmark.py). Checks in tests/test_bem2d.py: a coaxial pair against
2 pi eps0 / ln(b/a), and a square via in a square wall against the closed form used by the single-via cavity check.
"""
import math

import numpy as np

EPS0 = 8.8541878128e-12


def _ln_integral(px, py, ax, ay, bx, by):
    """Integral of ln|r - r'| over the segment a-b (r' on it), for points r = (px, py); arrays allowed."""
    L = math.hypot(bx - ax, by - ay)
    tx, ty = (bx - ax) / L, (by - ay) / L
    u = (px - ax) * tx + (py - ay) * ty
    v = -(px - ax) * ty + (py - ay) * tx

    def F(x):
        r2 = x * x + v * v
        with np.errstate(divide="ignore", invalid="ignore"):
            lg = np.where(r2 > 0, 0.5 * x * np.log(np.where(r2 > 0, r2, 1.0)), 0.0)
            at = np.where(np.abs(v) > 0, v * np.arctan2(x, np.abs(v)) * np.sign(v), 0.0)
        return lg - x + at

    return F(L - u) - F(-u)


def panels(polygon, n_per_side):
    """Split a closed polygon (list of vertices, not repeated) into panels; n_per_side is an int or a function of the
    side length. Returns an array of (ax, ay, bx, by)."""
    out = []
    m = len(polygon)
    for k in range(m):
        (x0, y0), (x1, y1) = polygon[k], polygon[(k + 1) % m]
        side = math.hypot(x1 - x0, y1 - y0)
        n = n_per_side(side) if callable(n_per_side) else n_per_side
        s = 0.5 * (1 - np.cos(np.pi * np.arange(n + 1) / n))
        for a, b in zip(s[:-1], s[1:]):
            out.append((x0 + a * (x1 - x0), y0 + a * (y1 - y0), x0 + b * (x1 - x0), y0 + b * (y1 - y0)))
    return np.array(out)


def maxwell_matrix(conductors, eps=EPS0):
    """Maxwell capacitance matrix (F/m) of conductors, each given as an array of panels (ax, ay, bx, by)."""
    allp = np.vstack(conductors)
    owner = np.concatenate([np.full(len(c), k) for k, c in enumerate(conductors)])
    mx = 0.5 * (allp[:, 0] + allp[:, 2])
    my = 0.5 * (allp[:, 1] + allp[:, 3])
    n = len(allp)
    P = np.empty((n, n))
    for j in range(n):
        ax, ay, bx, by = allp[j]
        L = math.hypot(bx - ax, by - ay)
        P[:, j] = -_ln_integral(mx, my, ax, ay, bx, by) / (2 * math.pi * eps * L)  # potential per unit charge q_j
    k = len(conductors)
    rhs = np.zeros((n, k))
    for c in range(k):
        rhs[owner == c, c] = 1.0
    q = np.linalg.solve(P, rhs)
    return np.array([[q[owner == m, c].sum() for c in range(k)] for m in range(k)])


def square(x, y, side):
    h = side / 2
    return [(x - h, y - h), (x + h, y - h), (x + h, y + h), (x - h, y + h)]
