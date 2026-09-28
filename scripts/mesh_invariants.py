"""Geometry and physical-tag invariants for Gmsh v2.1 meshes."""
from __future__ import annotations
import math
from pathlib import Path

class MeshInvariantError(ValueError):
    pass

def _section(lines, name):
    start = f"${name}"
    end = f"$End{name}"
    try:
        a, b = lines.index(start), lines.index(end)
    except ValueError as exc:
        raise MeshInvariantError(f"missing {name} section") from exc
    return lines[a + 1:b]

def read_mesh(path):
    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "$MeshFormat":
        raise MeshInvariantError("not a Gmsh ASCII mesh")
    fmt = _section(lines, "MeshFormat")
    if fmt != ["2.1 0 8"]:
        raise MeshInvariantError("only Gmsh v2.1 ASCII meshes are supported")
    names = {}
    rows = _section(lines, "PhysicalNames")
    if not rows or len(rows)-1 != int(rows[0]):
        raise MeshInvariantError("missing physical names")
    for row in rows[1:]:
        f = row.split(maxsplit=2)
        if len(f) != 3:
            raise MeshInvariantError("malformed physical name")
        dim, tag = int(f[0]), int(f[1])
        if (dim, tag) in names or dim not in (1, 2):
            raise MeshInvariantError("duplicate or unsupported physical name")
        quoted = f[2]
        if len(quoted) < 2 or quoted[0] != '"' or quoted[-1] != '"':
            raise MeshInvariantError("malformed physical name quote")
        names[(dim, tag)] = quoted[1:-1]
    nr = _section(lines, "Nodes")
    if not nr:
        raise MeshInvariantError("missing nodes")
    n = int(nr[0])
    if n <= 0 or len(nr[1:]) != n:
        raise MeshInvariantError("node count mismatch")
    nodes = {}
    for row in nr[1:]:
        f = row.split()
        if len(f) != 4:
            raise MeshInvariantError("malformed node")
        idx = int(f[0]); xyz = tuple(float(x) for x in f[1:])
        if idx in nodes or not all(math.isfinite(x) for x in xyz):
            raise MeshInvariantError("duplicate or nonfinite node")
        nodes[idx] = xyz
    er = _section(lines, "Elements")
    if not er:
        raise MeshInvariantError("missing elements")
    m = int(er[0])
    if m <= 0 or len(er[1:]) != m:
        raise MeshInvariantError("element count mismatch")
    elems = []
    element_ids = set()
    for row in er[1:]:
        f = row.split()
        if len(f) < 4:
            raise MeshInvariantError("malformed element")
        eid, typ, nt = map(int, f[:3])
        if eid in element_ids or nt < 1:
            raise MeshInvariantError("duplicate element or missing physical tag")
        element_ids.add(eid)
        tags = tuple(map(int, f[3:3 + nt])); verts = tuple(map(int, f[3 + nt:]))
        if typ not in (1, 2):
            raise MeshInvariantError(f"unsupported element type {typ}")
        need = 2 if typ == 1 else 3
        if len(verts) != need or any(v not in nodes for v in verts):
            raise MeshInvariantError("element references missing node")
        if not tags or (typ == 1 and (1, tags[0]) not in names) or (typ == 2 and (2, tags[0]) not in names):
            raise MeshInvariantError("element has unknown physical tag")
        elems.append((eid, typ, tags, verts))
    return {"path": str(path), "physical_names": names, "nodes": nodes, "elements": elems}

def invariants(mesh_or_path):
    mesh = read_mesh(mesh_or_path) if isinstance(mesh_or_path, (str, Path)) else mesh_or_path
    names = mesh["physical_names"]; nodes = mesh["nodes"]
    line_lengths = {}; triangle_areas = {}; line_counts = {}; triangle_counts = {}
    for _, typ, tags, verts in mesh["elements"]:
        tag = (1 if typ == 1 else 2, tags[0])
        if typ == 1:
            a, b = nodes[verts[0]], nodes[verts[1]]
            value = math.dist(a, b)
            if not math.isfinite(value) or value <= 0: raise MeshInvariantError("degenerate line")
            line_lengths[tag] = line_lengths.get(tag, 0.0) + value
            line_counts[tag] = line_counts.get(tag, 0) + 1
        else:
            a, b, c = (nodes[v] for v in verts)
            area = abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])) / 2
            if not math.isfinite(area) or area <= 0: raise MeshInvariantError("degenerate triangle")
            triangle_areas[tag] = triangle_areas.get(tag, 0.0) + area
            triangle_counts[tag] = triangle_counts.get(tag, 0) + 1
    xyz = list(nodes.values())
    bbox = [[min(p[i] for p in xyz), max(p[i] for p in xyz)] for i in range(3)]
    return {"physical_names": {f"{d}:{t}": n for (d,t), n in sorted(names.items())},
            "bbox": bbox, "node_count": len(nodes), "element_count": len(mesh["elements"]),
            "line_counts": {f"{d}:{t}": n for (d,t), n in sorted(line_counts.items())},
            "triangle_counts": {f"{d}:{t}": n for (d,t), n in sorted(triangle_counts.items())},
            "line_lengths": {f"{d}:{t}": v for (d,t), v in sorted(line_lengths.items())},
            "triangle_areas": {f"{d}:{t}": v for (d,t), v in sorted(triangle_areas.items())}}

def compare_invariants(baseline, refined, rel_tol=1e-10, abs_tol=1e-20):
    if not (math.isfinite(rel_tol) and math.isfinite(abs_tol) and rel_tol > 0 and abs_tol > 0):
        raise ValueError("tolerances must be positive finite")
    a = invariants(baseline) if isinstance(baseline, (str, Path)) else baseline
    b = invariants(refined) if isinstance(refined, (str, Path)) else refined
    if a["physical_names"] != b["physical_names"]:
        return {"pass": False, "reason": "physical names differ"}
    checks = []
    for key in ("bbox", "line_lengths", "triangle_areas"):
        if key == "bbox":
            pairs = [(x, y) for xa, xb in zip(a[key], b[key]) for x, y in zip(xa, xb)]
        else:
            if set(a[key]) != set(b[key]):
                return {"pass": False, "reason": f"{key} tags differ"}
            pairs = [(a[key][k], b[key][k]) for k in a[key]]
        checks.extend(abs(y-x) <= abs_tol + rel_tol * max(abs(x), abs(y), abs_tol) for x, y in pairs)
    return {"pass": all(checks), "checks": len(checks), "failed_checks": checks.count(False),
            "relative_tolerance": rel_tol, "absolute_tolerance": abs_tol}
