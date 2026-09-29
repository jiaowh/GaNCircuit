"""Conforming local refinement for the pinned planar MOS cross-section.

Mark all edges of triangles in a fixed surface/junction band and a body-contact
band. Neighbours sharing marked edges are split too, so no hanging nodes are
introduced. This changes the mesh only, not the geometry or doping equations.
"""
from pathlib import Path

try:
    from .mesh_invariants import read_mesh, compare_invariants
    from .mesh_delaunay import restore_delaunay
except ImportError:
    from mesh_invariants import read_mesh, compare_invariants
    from mesh_delaunay import restore_delaunay


POLICY = {
    "name": "interfaces-junctions-and-body-delaunay-v2",
    "band_half_width_cm": 5e-7,
    "horizontal_centres_cm": [-1e-5, 0.0, 1e-5, 1e-4],
    "vertical_junction_x_cm": [4.5e-5, 5.5e-5],
    "selection": "triangle bbox intersects an interface/junction/contact band; all three edges marked",
    "transition": "shared-edge midpoint splits with one/two/three marked-edge templates",
    "edge_cleanup": "Delaunay flips within regions; physical lines constrained",
}


def refine(source, destination):
    source, destination = Path(source), Path(destination)
    mesh = read_mesh(source)
    nodes = dict(mesh["nodes"])
    edges = set()
    for _, kind, _, vertices in mesh["elements"]:
        if kind != 2:
            continue
        xs, ys = [nodes[n][0] for n in vertices], [nodes[n][1] for n in vertices]
        half = POLICY["band_half_width_cm"]
        horizontal = any(min(ys) <= y+half and max(ys) >= y-half for y in POLICY["horizontal_centres_cm"])
        vertical = (min(ys) <= 1e-5+half and max(ys) >= -half and
                    any(min(xs) <= x+half and max(xs) >= x-half for x in POLICY["vertical_junction_x_cm"]))
        if horizontal or vertical:
            a, b, c = vertices
            edges.update(tuple(sorted(e)) for e in ((a, b), (b, c), (c, a)))
    next_id = max(nodes)+1
    midpoints = {}
    for offset, (a, b) in enumerate(sorted(edges)):
        midpoint = next_id+offset
        midpoints[(a, b)] = midpoint
        nodes[midpoint] = tuple((x+y)/2 for x, y in zip(nodes[a], nodes[b]))

    elements = []
    for _, kind, tags, vertices in mesh["elements"]:
        if kind == 1:
            a, b = vertices
            midpoint = midpoints.get(tuple(sorted(vertices)))
            children = [(a, midpoint), (midpoint, b)] if midpoint else [vertices]
        else:
            a, b, c = vertices
            mids = [midpoints.get(tuple(sorted(e))) for e in ((a,b), (b,c), (c,a))]
            count = sum(m is not None for m in mids)
            if count == 0:
                children = [vertices]
            elif count == 3:
                ab, bc, ca = mids
                children = [(a,ab,ca), (ab,b,bc), (ca,bc,c), (ab,bc,ca)]
            else:
                # Rotate the triangle so the single marked edge is AB, or
                # the two marked edges are AB and BC. Preserve orientation.
                pivot = next(i for i in range(3) if mids[i] is not None and
                             (count == 1 or mids[(i+1)%3] is not None))
                a, b, c = [vertices[(pivot+i)%3] for i in range(3)]
                ab = mids[pivot]
                if count == 1:
                    children = [(a,ab,c), (ab,b,c)]
                else:
                    bc = mids[(pivot+1)%3]
                    # Choose the shorter of the two quadrilateral diagonals.
                    distance2 = lambda u,v: sum((x-y)**2 for x,y in zip(nodes[u], nodes[v]))
                    if distance2(a,bc) <= distance2(ab,c):
                        children = [(ab,b,bc), (a,ab,bc), (a,bc,c)]
                    else:
                        children = [(ab,b,bc), (a,ab,c), (ab,bc,c)]
        elements.extend((kind, tags, child) for child in children)

    elements, flips = restore_delaunay(nodes, elements)
    lines = ["$MeshFormat", "2.1 0 8", "$EndMeshFormat", "$PhysicalNames", str(len(mesh["physical_names"]))]
    lines.extend(f'{dim} {tag} "{name}"' for (dim,tag),name in sorted(mesh["physical_names"].items()))
    lines.extend(["$EndPhysicalNames", "$Nodes", str(len(nodes))])
    lines.extend(f"{n} " + " ".join(f"{v:.17g}" for v in xyz) for n,xyz in sorted(nodes.items()))
    lines.extend(["$EndNodes", "$Elements", str(len(elements))])
    lines.extend(" ".join(map(str, (i,kind,len(tags),*tags,*vertices)))
                 for i,(kind,tags,vertices) in enumerate(elements,1))
    lines.append("$EndElements")
    destination.write_text("\n".join(lines)+"\n")
    check = compare_invariants(source, destination)
    if not check["pass"]:
        raise ValueError(f"refinement changed geometry: {check}")
    return {"policy": POLICY, "marked_edges": len(edges), "nodes": len(nodes), "elements": len(elements), "edge_flips": flips}
