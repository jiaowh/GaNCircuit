#!/usr/bin/env python3
"""Common-source screen (declared in plans/goal-targets-2026-10-08.md, 10 October 2026).

Takes a finished or prepared variant-G FastHenry deck (case.inp), keeps its geometry and terminal ties, and replaces
its 47 ports by the shorts g_summary applies afterwards plus three ports: loop (Q1.D-Q1.S46), cs_q2 (U80.GND-Q2.S46)
and cs_q1 (U80.PH-Q1.S46). L_loop = Im Z11 / w; L_cs = Im Z21, Z31 / w (open-terminal voltage per ampere of loop
current). Output: results/gan/epc90133-cs-screen-<tag>.json, compared with the G report when one is given.

    python scripts/epc90133_cs_screen.py --deck runs/<G dir>/case.inp --tag stock [--g-report <G json>]
"""
import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from epc90133_extract import parse_matrix_file  # noqa: E402
from fasthenry_known_answer import FH_BIN, wsl_path  # noqa: E402

CAPS = [f"ci{k}" for k in range(1, 8)] + [f"cm{k}" for k in range(1, 11)]


def reduce_deck(text):
    lines = text.splitlines()
    ext = {}
    body = []
    for ln in lines:
        if ln.startswith(".external"):
            _, a, b, name = ln.split()
            ext[name] = (a, b)
        elif ln.strip() not in (".end",) and not ln.startswith(".freq"):
            body.append(ln)
        elif ln.startswith(".freq"):
            freq = ln
    q1d = ext["ci1_vin"][1]            # VIN reference: Q1.D
    q2d = ext["q1_s2"][1]              # SW reference: Q2.D
    q2s46 = ext["q2_s2"][1]            # GND reference: Q2.S46
    q1s46, q1s2, q2s2 = ext["q1_s46"][0], ext["q1_s2"][0], ext["q2_s2"][0]
    shorts = [(q2d, q2s46), (q1s2, q1s46), (q2s2, q2s46)] + [(ext[f"{c}_vin"][0], ext[f"{c}_gnd"][0]) for c in CAPS]
    ports = [(q1d, q1s46, "loop"), (ext["u80_gnd"][0], q2s46, "cs_q2"), (ext["u80_ph"][0], q1s46, "cs_q1")]
    out = body + ["* common-source screen: g_summary shorts and three ports"]
    out += [f".equiv {a} {b}" for a, b in shorts]
    out += [f".external {a} {b} {n}" for a, b, n in ports]
    out += [freq, ".end"]
    return "\n".join(out) + "\n", float(freq.split("fmin=")[1].split()[0]), {"shorts": shorts, "ports": ports}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", type=Path, required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--g-report", type=Path)
    a = ap.parse_args()
    src = a.deck.read_text(encoding="ascii")
    deck, freq, meta = reduce_deck(src)
    work = ROOT / f"runs/cs-screen-{a.tag}"
    work.mkdir(parents=True, exist_ok=False)
    (work / "case.inp").write_text(deck, encoding="ascii")
    cmd = ["wsl", "-e", "bash", "-lc", f"cd '{wsl_path(work)}' && '{wsl_path(FH_BIN)}' case.inp -p diag"]
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, check=False)
    wall = time.time() - t0
    (work / "stdout.log").write_text(p.stdout or "", encoding="utf-8")
    (work / "stderr.log").write_text(p.stderr or "", encoding="utf-8")
    f = work / "Zc.mat"
    if p.returncode != 0 or not f.is_file():
        raise SystemExit(f"FastHenry failed ({p.returncode}): {(p.stderr or p.stdout)[-800:]}")
    rows, _, kind, Z = parse_matrix_file(f.read_text(errors="replace"))
    if kind != "Impedance":
        raise SystemExit(f"unexpected matrix kind {kind}")
    w = 2 * math.pi * freq
    i = {n: k for k, n in enumerate(rows)}
    res = {"L_loop_nH": Z[i["loop"], i["loop"]].imag / w * 1e9, "R_loop_mohm": Z[i["loop"], i["loop"]].real * 1e3,
           "L_cs_Q2_pH": Z[i["cs_q2"], i["loop"]].imag / w * 1e12,
           "L_cs_Q1_pH": Z[i["cs_q1"], i["loop"]].imag / w * 1e12,
           "reciprocity_cs_q2": abs(Z[i["cs_q2"], i["loop"]] - Z[i["loop"], i["cs_q2"]]) / abs(Z[i["cs_q2"], i["loop"]])}
    out = {"schema": "epc90133-cs-screen/1", "tag": a.tag,
           "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "source_deck": str(a.deck), "source_deck_sha256": hashlib.sha256(src.encode("ascii")).hexdigest(),
           "frequency_Hz": freq, "wall_time_s": wall, "ports": meta["ports"], "n_shorts": len(meta["shorts"]),
           "result": res}
    if a.g_report:
        g = json.loads(a.g_report.read_text(encoding="utf-8"))["summary"]
        out["g_report"] = str(a.g_report)
        out["against_g"] = {k: {"screen": res[k], "G": g[k], "rel": res[k] / g[k] - 1}
                            for k in ("L_loop_nH", "L_cs_Q2_pH", "L_cs_Q1_pH")}
    path = ROOT / f"results/gan/epc90133-cs-screen-{a.tag}.json"
    path.write_text(json.dumps(out, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"wall_s": round(wall), **{k: round(v, 5) for k, v in res.items()}}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
