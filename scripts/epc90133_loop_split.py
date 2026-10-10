#!/usr/bin/env python3
"""Split a variant-G loop inductance by section, from an existing G report (no solver run).

Same reduced network and excitation as g_summary in scripts/epc90133_extract.py (capacitors, Q2 die and source pins
shorted; 1 A into Q1.D, out of Q1.S46; Q2.S46 is the reference). The loop voltage is split where it drops, with the
capacitor terminals weighted by their current shares: VIN copper (Q1.D to the capacitors), GND copper (capacitors to
Q2's source), SW copper (Q2's drain to Q1's source). Node potentials of the extracted network include every mutual
term; the split is a description of where the voltage drops, not a unique partial-inductance decomposition.

    python scripts/epc90133_loop_split.py <G report json> [...]
"""
import json
import math
import sys

import numpy as np


def split(path):
    d = json.loads(open(path, encoding="utf-8").read())
    order, w = d["port_order"], 2 * math.pi * d["frequency_Hz"]
    Z = np.array(d["R_ohm"]) + 1j * w * np.array(d["L_H"])
    br = {p["name"]: (p["terminal"], p["reference"]) for p in d["ports"]}
    power = [k for k, n in enumerate(order) if not br[n][0].startswith(("R8", "U80", "J33"))
             and not br[n][1].startswith(("Q1.G", "Q2.G", "R8"))]
    names = [order[k] for k in power]
    Zp = Z[np.ix_(power, power)]
    nodes = sorted({x for n in names for x in br[n]} | {"Q1.D", "Q1.S46", "Q2.D", "Q2.S46"})
    caps = sorted({t.rsplit(".", 1)[0] for t in nodes if t.startswith("C")})
    ground = "Q2.S46"
    nidx = {n: k for k, n in enumerate(x for x in nodes if x != ground)}
    nb, nn = len(names), len(nidx)
    shorts = [("Q2.D", "Q2.S46"), ("Q1.S2", "Q1.S46"), ("Q2.S2", "Q2.S46")] + [(f"{c}.VIN", f"{c}.GND") for c in caps]
    N = nn + nb + len(shorts)
    A = np.zeros((N, N), complex)
    rhs = np.zeros(N, complex)

    def stamp(node, k, s):
        if node != ground:
            A[nidx[node], k] += s
    for k, n in enumerate(names):
        t, r = br[n]
        if t != ground:
            A[nn + k, nidx[t]] += 1
        if r != ground:
            A[nn + k, nidx[r]] -= 1
        A[nn + k, nn:nn + nb] -= Zp[k]
        stamp(t, nn + k, 1)
        stamp(r, nn + k, -1)
    for k, (a, c) in enumerate(shorts):
        row = nn + nb + k
        if a != ground:
            A[row, nidx[a]] += 1
        if c != ground:
            A[row, nidx[c]] -= 1
        stamp(a, row, 1)
        stamp(c, row, -1)
    rhs[nidx["Q1.D"]] += 1
    rhs[nidx["Q1.S46"]] -= 1
    x = np.linalg.solve(A, rhs)
    v = lambda n: 0 if n == ground else x[nidx[n]]
    share = {c: x[nn + nb + 3 + k] for k, c in enumerate(caps)}
    tot = sum(share.values())
    s = {c: share[c] / tot for c in caps}
    seg = {"VIN": sum(s[c] * (v("Q1.D") - v(f"{c}.VIN")) for c in caps),
           "GND": sum(s[c] * (v(f"{c}.GND") - v(ground)) for c in caps),
           "SW": v("Q2.D") - v("Q1.S46")}
    loop = v("Q1.D") - v("Q1.S46")
    pH = lambda z: z.imag / w * 1e12
    return {"report": path, "L_loop_pH": pH(loop), "sections_pH": {k: pH(z) for k, z in seg.items()},
            "sum_check_pH": pH(sum(seg.values())), "cap_current_share": {c: abs(s[c]) for c in caps}}


if __name__ == "__main__":
    for p in sys.argv[1:]:
        r = split(p)
        print(json.dumps({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items() if k != "cap_current_share"}))
        print("  shares", {c: round(v, 3) for c, v in r["cap_current_share"].items()})
