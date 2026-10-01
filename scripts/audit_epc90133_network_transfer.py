"""Small, simulator-free audit of the saved extraction-to-SPICE network transfer.

Uses an independent incidence-matrix solve with the extractor's diagnostic loading:
1 A into Q1.D and out of its source, Q2 and capacitors shorted; G source pins joined,
gate branches open. This is NOT a switching-waveform or frequency-convergence test.
Compares full R with the diagonal R emitted by epc90133_switching.network, and
checks the six-significant-digit inductance/coupling serialization.
Requires numpy only. Does not import geometry modules or launch external tools.
"""
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def solve_loop(report, resistance, inductance):
    ports = report["ports"]
    assert report["port_order"] == [p["name"] for p in ports]
    gate = any(p["terminal"] == "U80.PH" for p in ports)
    selected = [i for i, p in enumerate(ports) if not gate or (
        not p["terminal"].startswith(("R8", "U80.U", "U80.L"))
        and not p["reference"].startswith(("Q1.G", "Q2.G", "R8")))]
    branches = [(ports[i]["terminal"], ports[i]["reference"]) for i in selected]
    source = "Q1.S46" if gate else "Q1.S"
    ground = "Q2.S46" if gate else "Q2.S"
    nodes = sorted({n for b in branches for n in b} - {ground})
    index = {n: i for i, n in enumerate(nodes)}
    caps = sorted({n.split(".")[0] for n in nodes if n.startswith("C")})
    shorts = [("Q2.D", ground)] + [(c + ".VIN", c + ".GND") for c in caps]
    if gate:
        shorts += [("Q1.S2", source), ("Q2.S2", ground)]

    def incidence(edges):
        a = np.zeros((len(nodes), len(edges)))
        for j, (start, end) in enumerate(edges):
            for n, sign in ((start, 1), (end, -1)):
                if n != ground:
                    a[index[n], j] += sign
        return a

    b, s = incidence(branches), incidence(shorts)
    omega = 2 * math.pi * report["frequency_Hz"]
    z = (resistance + 1j * omega * inductance)[np.ix_(selected, selected)]
    nn, nb, ns = len(nodes), len(branches), len(shorts)
    a = np.block([[np.zeros((nn, nn)), b, s],
                  [b.T, -z, np.zeros((nb, ns))],
                  [s.T, np.zeros((ns, nb)), np.zeros((ns, ns))]])
    rhs = np.zeros(nn + nb + ns)
    rhs[index["Q1.D"]], rhs[index[source]] = 1, -1
    x = np.linalg.solve(a, rhs)
    assert np.max(np.abs(a @ x - rhs)) < 1e-9
    loop = x[index["Q1.D"]] - x[index[source]]
    out = {"R_loop_mohm": float(loop.real * 1e3), "L_loop_nH": float(loop.imag / omega * 1e9)}
    if gate:
        for q, ret, src in (("Q1", "U80.PH", source), ("Q2", "U80.GND", ground)):
            transfer = x[index[ret]] - (0 if src == ground else x[index[src]])
            out[f"R_cs_{q}_mohm"] = float(transfer.real * 1e3)
    return out


def main():
    rows = {}
    for name in ("B-m1-mid", "G-m1-mid"):
        path = ROOT / f"results/gan/epc90133-extraction/{name}.json"
        r = json.loads(path.read_text())
        resistance, inductance = np.array(r["R_ohm"]), np.array(r["L_H"])
        full = solve_loop(r, resistance, inductance)
        for k in ("R_loop_mohm", "L_loop_nH"):
            assert math.isclose(full[k], r["summary"][k], rel_tol=1e-9)
        diagonal = solve_loop(r, np.diag(np.diag(resistance)), inductance)
        rounded = np.diag([float(f"{v:.6g}") for v in np.diag(inductance)])
        for i in range(len(rounded)):
            for j in range(i):
                coupling = float(f"{inductance[i,j] / math.sqrt(inductance[i,i] * inductance[j,j]):.6g}")
                rounded[i,j] = rounded[j,i] = coupling * math.sqrt(rounded[i,i] * rounded[j,j])
        rows[name] = {
            "extraction_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "frequency_Hz": r["frequency_Hz"], "full_R": full, "diagonal_R": diagonal,
            "loop_resistance_change_fraction": diagonal["R_loop_mohm"] / full["R_loop_mohm"] - 1,
            "R_min_eigenvalue_ohm": float(np.linalg.eigvalsh(resistance).min()),
            "L_min_eigenvalue_pH": float(np.linalg.eigvalsh(inductance).min() * 1e12),
            "serialized_L_min_eigenvalue_pH": float(np.linalg.eigvalsh(rounded).min() * 1e12),
            "serialized_diagonal_R": solve_loop(r, np.diag(np.diag(resistance)), rounded),
        }
    report = {"schema": "epc90133-network-transfer-audit/1",
              "scope": __doc__.strip(),
              "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "network_generator_sha256": hashlib.sha256((ROOT / "scripts/epc90133_switching.py").read_bytes()).hexdigest(),
              "cases": rows}
    output = ROOT / "results/gan/epc90133-network-transfer-audit.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for name, row in rows.items():
        print(name, row["full_R"], row["diagonal_R"])


if __name__ == "__main__":
    main()
