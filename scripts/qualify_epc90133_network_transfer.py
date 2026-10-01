"""Qualify the SPICE representation of an extracted branch network against its matrices (LTspice AC, 100 MHz).

Method audit, 1 October 2026: the baseline network (scripts/epc90133_switching.py network(), full_r False) keeps
the full inductance and coupling but only the diagonal resistance. The separate network revision full_r replaces
each branch resistor by a behavioural source carrying the full resistance row. This script checks both
representations in LTspice before any switching comparison uses the revision. Nothing here simulates switching.

Q1 known answer: a synthetic three-branch network (branches to ground, positive-definite R with off-diagonal
   terms, coupled L) driven by 1 A AC into each branch in turn. The measured port impedance matrix must equal
   R + j omega L (full_r) or diag(R) + j omega L (baseline) within 1e-4 of max |Z|.
Q2 saved matrices: the B-m1-mid and G-m1-mid networks as the switching bench writes them, under the extractor's
   diagnostic loading (1 A from Q1's source into Q1.D; Q2 drain-source and every capacitor shorted; on G the
   source pins joined and the gate-drive branches left open). The loop R and L between Q1.D and Q1's source
   and, on G, the return-ball transfers must match scripts/audit_epc90133_network_transfer.py's independent
   solve of the same matrices: full_r against the full-matrix solve, the baseline against the diagonal-R solve.
   Tolerances: loop R within 1 %, loop L within 0.1 %, transfer resistance within 2 % or 0.005 mohm.
Criteria fixed 1 October 2026 before the first run. Open nodes get 1 Gohm to ground (stated, negligible here).
Run 1 (1 October 2026) stopped at B full_r: LTspice rejected loops of behavioural voltage sources, inductors and
the 0 V shorts. The revision now keeps R[k, k] as a resistor and puts only the off-diagonal terms in the source
(same matrix). Criteria unchanged.

    PYTHONPATH=src python scripts/qualify_epc90133_network_transfer.py
"""
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import uuid

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from circuit_tools.ltspice import parse_raw, run_ltspice  # noqa: E402
import audit_epc90133_network_transfer as audit  # noqa: E402
import epc90133_switching as sw  # noqa: E402

FREQ = 100e6
OUTPUT = ROOT / "results/gan/epc90133-network-transfer-qualification.json"


def ac_run(lines, run_dir, saves):
    text = "\n".join(["* network transfer qualification", *lines, f".save {' '.join(saves)}",
                      f".ac list {FREQ:g}", ".end", ""])
    r = run_ltspice(text, run_dir, timeout_s=600)
    if r.status != "completed":
        raise SystemExit(f"LTspice run failed in {run_dir}: {r.message}")
    return parse_raw(run_dir / "bench.raw").step(0)


def known_answer(run_root):
    R = np.array([[2.0e-3, 0.6e-3, -0.3e-3], [0.6e-3, 1.5e-3, 0.4e-3], [-0.3e-3, 0.4e-3, 1.2e-3]])
    L = np.array([[300e-12, 120e-12, 40e-12], [120e-12, 250e-12, -60e-12], [40e-12, -60e-12, 200e-12]])
    assert np.linalg.eigvalsh(R).min() > 0 and np.linalg.eigvalsh(L).min() > 0
    ext = {"case": "synthetic", "L_H": L.tolist(), "R_ohm": R.tolist(),
           "ports": [{"terminal": f"P{k}.T", "reference": "Q2.S"} for k in range(3)]}
    w = 2 * math.pi * FREQ
    out = {}
    for full in (True, False):
        net, _ = sw.network(ext, full_r=full)
        Z = np.zeros((3, 3), complex)
        for j in range(3):
            s = ac_run([net, f"I1 0 p{j}_t AC 1"], run_root / f"ka-{'full' if full else 'diag'}-{j}",
                       [f"V(p{k}_t)" for k in range(3)])
            for k in range(3):
                Z[k, j] = s[f"v(p{k}_t)"][0]
        ref = (R if full else np.diag(np.diag(R))) + 1j * w * L
        err = float(np.abs(Z - ref).max() / np.abs(ref).max())
        out["full_r" if full else "baseline"] = {"max_rel_error": err, "pass": err <= 1e-4,
                                                  "Z_real_mohm": (Z.real * 1e3).round(6).tolist()}
    return out


def loading(ext):
    """Netlist lines for the extractor's diagnostic loading, and the nodes to read."""
    g = sw.is_gate_extraction(ext)
    src = "Q1.S46" if g else "Q1.S"
    nodes = sorted({sw.node(t) for p in ext["ports"] for t in (p["terminal"], p["reference"])} - {"0"})
    caps = sorted({p["terminal"].split(".")[0] for p in ext["ports"] if p["terminal"].startswith("C")})
    shorts = [("Q2.D", "Q2.S46" if g else "Q2.S")] + [(f"{c}.VIN", f"{c}.GND") for c in caps]
    if g:
        shorts += [("Q1.S2", src), ("Q2.S2", "Q2.S46")]
    lines = [f"Vsh{k} {sw.node(a)} {sw.node(b)} 0" for k, (a, b) in enumerate(shorts)]
    lines += [f"Rgmin_{n} {n} 0 1e9" for n in nodes]
    lines.append(f"I1 {sw.node(src)} {sw.node('Q1.D')} AC 1")
    reads = {"loop": (sw.node("Q1.D"), sw.node(src))}
    if g:
        reads.update(Q1=(sw.node("U80.PH"), sw.node(src)), Q2=(sw.node("U80.GND"), "0"))
    return lines, reads


def saved_matrices(run_root):
    out = {}
    w = 2 * math.pi * FREQ
    for name in ("B-m1-mid", "G-m1-mid"):
        path = ROOT / f"results/gan/epc90133-extraction/{name}.json"
        ext = json.loads(path.read_text(encoding="utf-8"))
        R, L = np.array(ext["R_ohm"]), np.array(ext["L_H"])
        refs = {"full_r": audit.solve_loop(ext, R, L), "baseline": audit.solve_loop(ext, np.diag(np.diag(R)), L)}
        load, reads = loading(ext)
        row = {"extraction_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        for rep, full in (("full_r", True), ("baseline", False)):
            net, _ = sw.network(ext, full_r=full)
            nodes = sorted({n for a, b in reads.values() for n in (a, b) if n != "0"})
            s = ac_run([net, *load], run_root / f"{name}-{rep}", [f"V({n})" for n in nodes])
            v = lambda n: 0 if n == "0" else s[f"v({n})"][0]
            z = v(reads["loop"][0]) - v(reads["loop"][1])
            got = {"R_loop_mohm": z.real * 1e3, "L_loop_nH": z.imag / w * 1e9}
            for q in ("Q1", "Q2"):
                if q in reads:
                    got[f"R_cs_{q}_mohm"] = (v(reads[q][0]) - v(reads[q][1])).real * 1e3
            ref = refs[rep]
            chk = {"R_loop": abs(got["R_loop_mohm"] / ref["R_loop_mohm"] - 1) <= 0.01,
                   "L_loop": abs(got["L_loop_nH"] / ref["L_loop_nH"] - 1) <= 0.001}
            for q in ("Q1", "Q2"):
                k = f"R_cs_{q}_mohm"
                if k in got:
                    d = abs(got[k] - ref[k])
                    chk[k] = d <= 0.005 or d <= 0.02 * abs(ref[k])
            row[rep] = {"ltspice": got, "reference": ref, "checks": chk, "pass": all(chk.values())}
        out[name] = row
    return out


def main():
    run_root = ROOT / "runs" / ("network-transfer-" + uuid.uuid4().hex[:12])
    ka = known_answer(run_root)
    sm = saved_matrices(run_root)
    ok = all(v["pass"] for v in ka.values()) and all(r[k]["pass"] for r in sm.values() for k in ("full_r", "baseline"))
    report = {"schema": "epc90133-network-transfer-qualification/1",
              "scope": "AC port impedance of the SPICE network against its extracted matrices at 100 MHz; "
                       "not frequency dependence, geometry accuracy or switching",
              "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "network_generator_sha256": hashlib.sha256((ROOT / "scripts/epc90133_switching.py").read_bytes()).hexdigest(),
              "audit_solver_sha256": hashlib.sha256((ROOT / "scripts/audit_epc90133_network_transfer.py").read_bytes()).hexdigest(),
              "run_directory": run_root.relative_to(ROOT).as_posix(),
              "Q1_known_answer": ka, "Q2_saved_matrices": sm, "outcome": "pass" if ok else "fail"}
    OUTPUT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print("Q1", {k: (v["max_rel_error"], v["pass"]) for k, v in ka.items()})
    for name, r in sm.items():
        for rep in ("full_r", "baseline"):
            print(name, rep, {k: round(v, 5) for k, v in r[rep]["ltspice"].items()},
                  "ref", {k: round(v, 5) for k, v in r[rep]["reference"].items()}, r[rep]["pass"])
    print("outcome", report["outcome"])


if __name__ == "__main__":
    main()
