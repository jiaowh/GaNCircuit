"""Flip unconstrained interior edges to restore local Delaunay geometry.

Physical line elements and region boundaries are constraints. This changes
triangle connectivity only; coordinates and physical tags are retained.
"""
from collections import defaultdict, deque


def orient(nodes, a, b, c):
    x, y, z = nodes[a], nodes[b], nodes[c]
    return (y[0]-x[0])*(z[1]-x[1])-(y[1]-x[1])*(z[0]-x[0])


def opposite_cotangent(nodes, a, b, c):
    x, y, z = nodes[a], nodes[b], nodes[c]
    denominator = abs(orient(nodes, a,b,c))
    if denominator == 0:
        raise ValueError("degenerate triangle")
    return ((x[0]-z[0])*(y[0]-z[0])+(x[1]-z[1])*(y[1]-z[1]))/denominator


def restore_delaunay(nodes, elements):
    constraints = {tuple(sorted(vertices)) for kind,_,vertices in elements if kind == 1}
    triangles = {i:(tags,vertices) for i,(kind,tags,vertices) in enumerate(elements) if kind == 2}
    adjacency = defaultdict(set)

    def edges(vertices):
        a,b,c = vertices
        return [tuple(sorted(e)) for e in ((a,b),(b,c),(c,a))]

    for index, (_,vertices) in triangles.items():
        for edge in edges(vertices):
            adjacency[edge].add(index)
    queue = deque(sorted(adjacency))
    flips = 0
    while queue:
        edge = queue.popleft()
        owners = adjacency.get(edge, set())
        if edge in constraints or len(owners) != 2:
            continue
        first, second = sorted(owners)
        tags, left = triangles[first]
        other_tags, right = triangles[second]
        if tags != other_tags:
            continue
        a,b = edge
        c = next(v for v in left if v not in edge)
        d = next(v for v in right if v not in edge)
        if c == d or orient(nodes,a,b,c)*orient(nodes,a,b,d) >= 0:
            continue
        if orient(nodes,c,d,a)*orient(nodes,c,d,b) >= 0:
            continue
        if opposite_cotangent(nodes,a,b,c)+opposite_cotangent(nodes,a,b,d) >= -1e-12:
            continue
        new_edge = tuple(sorted((c,d)))
        if adjacency.get(new_edge):
            continue
        sign = orient(nodes,*left)
        replacements = [(c,d,a),(d,c,b)]
        replacements = [v if orient(nodes,*v)*sign > 0 else (v[0],v[2],v[1]) for v in replacements]
        for index, old in ((first,left),(second,right)):
            for key in edges(old):
                adjacency[key].discard(index)
        for index, new in zip((first,second),replacements):
            triangles[index] = (tags,new)
            for key in edges(new):
                adjacency[key].add(index)
                queue.append(key)
        flips += 1
        if flips > 20*len(triangles):
            raise ValueError("Delaunay edge-flip limit reached")
    result = [(kind,*triangles[i]) if kind == 2 else (kind,tags,vertices)
              for i,(kind,tags,vertices) in enumerate(elements)]
    return result, flips
