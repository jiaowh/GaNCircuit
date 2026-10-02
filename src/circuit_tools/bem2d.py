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


def _field(px, py, ax, ay, bx, by):
    """Field (Ex, Ey) at points p from the segment a-b carrying unit total charge, divided by 1/(2 pi eps); the
    principal value (zero normal component) on the segment itself."""
    L = math.hypot(bx - ax, by - ay)
    tx, ty = (bx - ax) / L, (by - ay) / L
    u = (px - ax) * tx + (py - ay) * ty
    v = -(px - ax) * ty + (py - ay) * tx
    x1, x2 = -u, L - u
    with np.errstate(divide="ignore", invalid="ignore"):
        eu = -0.5 * (np.log(x2 * x2 + v * v) - np.log(x1 * x1 + v * v))
        on = np.abs(v) < 1e-9 * L
        ev = np.where(on, 0.0, np.sign(v) * (np.arctan2(x2, np.abs(v)) - np.arctan2(x1, np.abs(v))))
        eu = np.where(on & (x1 < 0) & (x2 > 0), -0.5 * (np.log(x2 * x2) - np.log(x1 * x1)), eu)
    eu, ev = eu / L, ev / L
    return eu * tx - ev * ty, eu * ty + ev * tx


def outward_normals(p, polygon):
    """Unit normals of panels p (from the side of `polygon` they lie on), pointing out of the polygon."""
    area = 0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(polygon, polygon[1:] + polygon[:1]))
    tx, ty = p[:, 2] - p[:, 0], p[:, 3] - p[:, 1]
    L = np.hypot(tx, ty)
    s = 1.0 if area > 0 else -1.0  # counter-clockwise: outward normal is (ty, -tx)
    return s * ty / L, -s * tx / L


def solve_dielectric(conductors, interfaces, potentials, eps0=EPS0):
    """Free charge per unit length on each conductor for given conductor potentials, with dielectric interfaces.

    conductors: list of lists of (panels, eps_r of the medium touching those panels);
    interfaces: list of (panels, nx, ny, eps_out, eps_in), normals pointing into eps_out.
    Unknowns are total (free + bound) panel charges; conductor rows impose the potential, interface rows impose
    eps_out E_n(out) = eps_in E_n(in). Free charge on a conductor panel is eps_r of its medium times its total charge.
    """
    cpan = [(pp, er, k) for k, parts in enumerate(conductors) for pp, er in parts]
    allp = np.vstack([pp for pp, _, _ in cpan] + [i[0] for i in interfaces])
    nc = sum(len(pp) for pp, _, _ in cpan)
    n = len(allp)
    mx = 0.5 * (allp[:, 0] + allp[:, 2])
    my = 0.5 * (allp[:, 1] + allp[:, 3])
    A = np.empty((n, n))
    nx = np.concatenate([i[1] for i in interfaces]) if interfaces else np.zeros(0)
    ny = np.concatenate([i[2] for i in interfaces]) if interfaces else np.zeros(0)
    eo = np.concatenate([np.full(len(i[0]), i[3]) for i in interfaces]) if interfaces else np.zeros(0)
    ei = np.concatenate([np.full(len(i[0]), i[4]) for i in interfaces]) if interfaces else np.zeros(0)
    lens = np.hypot(allp[:, 2] - allp[:, 0], allp[:, 3] - allp[:, 1])
    for j in range(n):
        ax, ay, bx, by = allp[j]
        A[:nc, j] = -_ln_integral(mx[:nc], my[:nc], ax, ay, bx, by) / (2 * math.pi * eps0 * lens[j])
        if n > nc:
            ex, ey = _field(mx[nc:], my[nc:], ax, ay, bx, by)
            A[nc:, j] = (eo - ei) * (ex * nx + ey * ny) / (2 * math.pi * eps0)
    if n > nc:
        idx = np.arange(nc, n)
        A[idx, idx] = (eo + ei) / (2 * eps0 * lens[nc:])  # self term: principal value of E_n is zero on a straight panel
    rhs = np.zeros(n)
    owner = np.concatenate([np.full(len(pp), k) for pp, _, k in cpan])
    epsr = np.concatenate([np.full(len(pp), er) for pp, er, _ in cpan])
    for k, v in enumerate(potentials):
        rhs[:nc][owner == k] = v
    q = np.linalg.solve(A, rhs)
    return np.array([np.sum(epsr[owner == k] * q[:nc][owner == k]) for k in range(len(conductors))])


def segment_panels(x0, y0, x1, y1, n):
    """One straight segment split into n cosine-clustered panels."""
    s = 0.5 * (1 - np.cos(np.pi * np.arange(n + 1) / n))
    return np.array([(x0 + a * (x1 - x0), y0 + a * (y1 - y0), x0 + b * (x1 - x0), y0 + b * (y1 - y0))
                     for a, b in zip(s[:-1], s[1:])])
