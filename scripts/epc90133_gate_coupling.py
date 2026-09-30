"""Full gate-loop coupling to the power loop, from an extraction G report (test 7 follow-up).

g_summary in epc90133_extract.py reports each FET's board common-source inductance as the voltage between the
driver return ball and the FET's source per ampere of commutation-loop current (1 A from Q1.D to Q1.S46, Q2
shorted, all capacitors shorted; 100 MHz). That covers the return side of the gate loop only. The forward path
(driver output ball, gate-resistor pads, gate) also has mutual inductance with the power branches.

This script repeats the same solve (by calling g_summary and capturing its solution) and adds the voltages the
loop current induces in the forward branches, which carry no current. With the driver output held at its return
potential and no gate current, the induced die gate-source voltage per ampere is

    (V(return ball) - V(source)) - (V_b(driver ball -> resistor pad) + V_b(resistor pad -> gate)),

reported as an inductance (imaginary part over omega), for the turn-on path (UGH/R80, LGH/R82) and the turn-off
path (UGL/R81, LGL/R83). The sign is that of g_summary's L_cs. One frequency and one mesh: an estimate.

Why this and not a netlist check: removing the gate-to-power coupling terms from the branch network
(test 7 case G-m1-mid-nogpk) is not a valid test. The branches share reference nodes, so their mutual terms also
represent shared copper, and removing them adds spurious common-source inductance instead of removing coupling.

    python scripts/epc90133_gate_coupling.py
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import epc90133_extract as ex  # noqa: E402

PATHS = {"Q1": ("U80.PH", {"turn_on": [("U80.UGH", "R80.D"), ("R80.G", "Q1.G")],
                           "turn_off": [("U80.UGL", "R81.D"), ("R81.G", "Q1.G")]}),
         "Q2": ("U80.GND", {"turn_on": [("U80.LGH", "R82.D"), ("R82.G", "Q2.G")],
                            "turn_off": [("U80.LGL", "R83.D"), ("R83.G", "Q2.G")]})}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extraction", type=Path, default=ROOT / "results/gan/epc90133-extraction/G-m1-mid.json")
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-gate-coupling.json")
    args = ap.parse_args()
    g = json.loads(args.extraction.read_text(encoding="utf-8"))
    order = g["port_order"]
    Z = np.array(g["Z_raw_real"]) + 1j * np.array(g["Z_raw_imag"])
    Z = (Z + Z.T) / 2  # as the extractor passes it to g_summary
    ports = [(p["name"], p["terminal"], p["reference"]) for p in g["ports"]]
    captured = {}
    solve = np.linalg.solve

    def spy(A, b):
        captured["x"] = solve(A, b)
        return captured["x"]

    ex.np.linalg.solve = spy
    try:
        summary = ex.g_summary(order, Z, ports)
    finally:
        ex.np.linalg.solve = solve
    for k in ("L_cs_Q1_pH", "L_cs_Q2_pH", "L_loop_nH"):  # the repeated solve must match the recorded one
        if not math.isclose(summary[k], g["summary"][k], rel_tol=1e-9):
            raise SystemExit(f"repeated solve differs from the report on {k}")
    # Reconstruct g_summary's indexing (power branches, node order, ground Q2.S46).
    br = {n: (t, r) for n, t, r in ports}
    power = [k for k, n in enumerate(order) if not br[n][0].startswith(("R8", "U80.U", "U80.L"))
             and not br[n][1].startswith(("Q1.G", "Q2.G", "R8"))]
    names = [order[k] for k in power]
    nodes = sorted({x for n in names for x in br[n]} | {"Q1.D", "Q1.S46", "Q2.D", "Q2.S46"})
    nidx = {n: k for k, n in enumerate(x for x in nodes if x != "Q2.S46")}
    x = captured["x"]
    current = x[len(nidx):len(nidx) + len(names)]
    v = lambda n: 0 if n == "Q2.S46" else x[nidx[n]]
    w = 2 * math.pi * g["frequency_Hz"]
    ph = lambda z: float(z.imag / w * 1e12)

    def branch_v(t, r):
        k = next(k for k, n in enumerate(order) if br[n] == (t, r))
        return Z[k, power] @ current

    out = {}
    for q, (ret, paths) in PATHS.items():
        ret_v = v(ret) - v(f"{q}.S46")
        res = {"return_side_pH": ph(ret_v)}
        for name, path in paths.items():
            fwd = sum(branch_v(*b) for b in path)
            res[f"forward_{name}_pH"] = ph(-fwd)
            res[f"total_{name}_pH"] = ph(ret_v - fwd)
        out[q] = res
        print(q, {k: round(val, 2) for k, val in res.items()})
    report = {"schema": "epc90133-gate-coupling/1",
              "extraction": args.extraction.relative_to(ROOT).as_posix(),
              "extraction_sha256": hashlib.sha256(args.extraction.read_bytes()).hexdigest(),
              "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "frequency_Hz": g["frequency_Hz"], "definition": __doc__.strip().split("\n\n")[1].replace("\n", " "),
              "scope": "one frequency, one mesh, unqualified vias: an estimate", "fets": out}
    args.output.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
