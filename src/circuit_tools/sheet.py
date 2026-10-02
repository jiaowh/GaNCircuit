"""Two-dimensional sheet-current solver: resistance of a conducting sheet in squares.

A uniform sheet occupies the True cells of a boolean mask (rows = y, columns = x, square cells). The left column of
copper is held at potential 1, the right column at 0; every other boundary (outer edges, holes, slots) is insulating.
The solver uses cell-centred finite volumes with unit sheet conductance and returns the resistance in squares,
N = 1 / I. For a plane pair carrying a TEM-like current, the inductance is mu0 * (h + delta) * N, so a change of N from a
hole gives the hole's added inductance in the perfect-conductor sheet picture (scripts/plane_hole_benchmark.py).

Exact checks (tests/test_sheet.py): a rectangle of L x W cells has N = L / W exactly in this discretisation; a small
circular insulating hole of radius a, far from the edges of a strip of width W, adds 2 pi a^2 / W^2 squares
(dilute limit of the 2D effective conductivity sigma (1 - f) / (1 + f)).
"""
import numpy as np
from scipy import ndimage
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve


def squares(mask):
    """Resistance in squares of the copper cells of `mask`, driven from its first to its last column."""
    mask = np.asarray(mask, dtype=bool)
    ny, nx = mask.shape
    # keep only copper connected (4-neighbour) to both electrodes; other islands carry no current
    lab, _ = ndimage.label(mask)
    both = set(np.unique(lab[:, 0][mask[:, 0]])) & set(np.unique(lab[:, -1][mask[:, -1]]))
    if not both:
        raise ValueError("no copper path between the driven columns")
    mask = np.isin(lab, list(both))
    idx = -np.ones(mask.shape, dtype=np.int64)
    idx[mask] = np.arange(int(mask.sum()))
    n = int(mask.sum())
    rows, cols, vals = [], [], []
    diag = np.zeros(n)
    rhs = np.zeros(n)
    # interior links between neighbouring copper cells, conductance 1 each
    for (a, b) in ((idx[:, :-1], idx[:, 1:]), (idx[:-1, :], idx[1:, :])):
        ok = (a >= 0) & (b >= 0)
        i, j = a[ok], b[ok]
        rows += [i, j]
        cols += [j, i]
        vals += [-np.ones(i.size), -np.ones(i.size)]
        np.add.at(diag, i, 1.0)
        np.add.at(diag, j, 1.0)
    # driven faces: half-cell links of conductance 2 to the electrode at the left (V = 1) and right (V = 0) faces
    left = idx[:, 0][mask[:, 0]]
    right = idx[:, -1][mask[:, -1]]
    np.add.at(diag, left, 2.0)
    np.add.at(diag, right, 2.0)
    rhs[left] += 2.0
    rows.append(np.arange(n))
    cols.append(np.arange(n))
    vals.append(diag)
    A = coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()
    v = spsolve(A, rhs)
    current = float(np.sum(2.0 * (1.0 - v[left])))
    if current <= 0:
        raise ValueError("no current path between the driven columns")
    return 1.0 / current


def disk_mask(nx, ny, cell, holes=(), slots=()):
    """Strip of nx x ny cells of size `cell` with circular holes (xc, yc, r) and rectangular slots (x0, y0, x1, y1)
    removed; coordinates in the same unit as `cell`, origin at the strip's lower-left corner. A cell is copper when its
    centre is outside every hole."""
    x = (np.arange(nx) + 0.5) * cell
    y = (np.arange(ny) + 0.5) * cell
    X, Y = np.meshgrid(x, y)
    m = np.ones((ny, nx), dtype=bool)
    for xc, yc, r in holes:
        m &= (X - xc) ** 2 + (Y - yc) ** 2 > r ** 2
    for x0, y0, x1, y1 in slots:
        m &= ~((X > x0) & (X < x1) & (Y > y0) & (Y < y1))
    return m
