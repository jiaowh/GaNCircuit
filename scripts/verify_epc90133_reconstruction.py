#!/usr/bin/env python3
"""Independent readback check of the saved EPC90133 KiCad reconstruction (track R step 5 output).

Audit at 0f07a6a (6 October 2026, docs/project-audit-0f07a6a.md, findings 3-5): step 5's R5 looked only at the
pads its own code had assigned, never reread the saved board, and its report did not identify the board checked;
its DRC calls ignored failures. This script checks the board as saved, without reusing step 5's construction.
Declared 6 October 2026 before its first run:
  V1 KiCad's own readback of the saved board (kicad-cli pcb export ipcd356) lists every pad of EPC's netlist,
     parsed here directly from the layout PDF bookmarks (scripts/epc90133_reconstruct_parts.read_pdf), with EPC's
     net (IPC-D-356 upper-cases names; EPC's 37 net names are distinct when upper-cased and at most 14 characters);
  V2 every other pad record is explained by an explicit rule: (a) a numbered pad absent from EPC's netlist is N/C or
     carries a KiCad 'unconnected-(<ref>-Pad<pin>)' net (IPC-D-356 keeps its last 14 characters); (b) an unnamed
     pad sits within 0.0001 in of a named pad of the same part and carries that pad's EPC net (Q1/Q2's auxiliary
     gate pads); (c) unnamed non-plated mounting holes are N/C. Anything else fails;
  V3 every via and every plated through-hole pad in the saved file has a copper size larger than its drill, or is
     listed as ringless in step 5's stored report (matched within 0.001 mm);
  V4 a fresh KiCad DRC of this exact board (circuit_tools.kicad.run_drc: exit status, schema, source and board
     hash checked) reports zero shorting_items and zero unconnected_items, and a second DRC with clearance reduced
     by 1 um reports zero clearance items (no gap below EPC's 5.91 mil rule within that geometric tolerance).
The report binds by SHA-256 the board, project, step 5's stored report, the layout PDF, the Gerber zip, the
IPC-D-356 file, both DRC reports, this script and its imported helpers, and records the KiCad version.
It does not check that KiCad's refill preserves the copper (it does not: audit finding 2).
"""
import argparse
import collections
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from circuit_tools.kicad import KiCadError, run_drc, sha256_file
import epc90133_reconstruct_parts as P
from epc90133_reconstruct import KICAD_CLI, OUT, to_kicad

BOARD, PROJECT = OUT / "epc90133.kicad_pcb", OUT / "epc90133.kicad_pro"
STEP5 = ROOT / "results/gan/epc90133-reconstruct-final.json"
PDF = P.GERBERS / f"{P.PREFIX}Layout.PDF"
ZIP = ROOT / "vendor/epc/epc90133/EPC90133 Development Board Gerbers.zip"
CLEARANCE, ARC_TOL = 5.91 * 0.0254, 0.001
HELPERS = ("src/circuit_tools/kicad.py", "scripts/epc90133_reconstruct_parts.py", "scripts/epc90133_reconstruct.py",
           "scripts/read_epc90133_geometry.py", "src/circuit_tools/gerber.py")


def read_ipcd356(path):
    """Pad records (not vias) of a KiCad IPC-D-356 file: [{key, ref, pin, net, x, y, plated}] (x, y in 0.0001 in)."""
    out = []
    for line in path.read_text(encoding="latin-1").splitlines():
        if line[:3] not in ("317", "327", "367") or line[20:26].strip() == "VIA":
            continue
        m = re.search(r"X([+-]\d+)Y([+-]\d+)", line[31:])
        ref, pin = line[20:26].strip(), line[27:31].strip() if line[26] == "-" else ""
        out.append({"key": f"{ref}-{pin}" if pin else ref, "ref": ref, "pin": pin, "net": line[3:17].strip(),
                    "x": int(m.group(1)), "y": int(m.group(2)), "plated": line[:3] != "367"})
    return out


def check_nets(epc, records):
    """V1 and V2: returns (v1_problems, v2_problems, explained_extras)."""
    by_key = collections.defaultdict(list)
    for r in records:
        by_key[r["key"]].append(r)
    v1 = [f"{p}: missing from the readback" for p in epc if p not in by_key]
    v1 += [f"{p}: readback net {r['net']!r}, EPC {n!r}" for p, n in epc.items() for r in by_key.get(p, [])
           if r["net"] != n.upper()]
    v2, extras = [], []
    for r in records:
        if r["key"] in epc:
            continue
        if r["pin"]:
            tail = f"unconnected-({r['ref']}-Pad{r['pin']})".upper()[-14:]
            ok, rule = r["net"] in ("N/C", tail), "a"
        elif not r["plated"]:
            ok, rule = r["net"] == "N/C", "c"
        else:
            twins = [q for q in records if q["ref"] == r["ref"] and q["pin"] and q["key"] in epc
                     and abs(q["x"] - r["x"]) <= 1 and abs(q["y"] - r["y"]) <= 1]
            ok, rule = bool(twins) and all(epc[q["key"]].upper() == r["net"] for q in twins), "b"
        (extras if ok else v2).append({"pad": r["key"], "net": r["net"], "rule": rule})
    return v1, v2, extras


def check_rings(text, ringless):
    """V3 on the saved s-expression: vias and plated through-hole pads with size <= drill must be listed."""
    listed = [to_kicad(r["x"], r["y"]) for r in ringless]
    near = lambda x, y: any(abs(x - a) <= 0.001 + 5e-4 and abs(y - b) <= 0.001 + 5e-4 for a, b in listed)
    bad, n = [], 0
    for m in re.finditer(r"\(via \(at ([-\d.]+) ([-\d.]+)\) \(size ([\d.]+)\) \(drill ([\d.]+)\)", text):
        x, y, s, d = map(float, m.groups())
        n += 1
        if s <= d + 1e-4 and not near(x, y):
            bad.append({"via": [x, y], "size": s, "drill": d})
    fp_re = re.compile(r'\t\(footprint "EPC90133:([^"]+)" \(layer "[FB]\.Cu"\) \(uuid "[^"]+"\) \(at ([-\d.]+) ([-\d.]+)\)'
                       r'(.*?)\n\t\)\n', re.S)
    for fp in fp_re.finditer(text):
        fx, fy = float(fp.group(2)), float(fp.group(3))
        for p in re.finditer(r'\(pad "([^"]*)" thru_hole \w+ \(at ([-\d.]+) ([-\d.]+)\) \(size ([\d.]+) [\d.]+\)'
                             r' \(drill ([\d.]+)', fp.group(4)):
            x, y, s, d = fx + float(p.group(2)), fy + float(p.group(3)), float(p.group(4)), float(p.group(5))
            n += 1
            if s <= d + 1e-4 and not near(x, y):
                bad.append({"pad": f"{fp.group(1)}-{p.group(1)}", "size": s, "drill": d})
    return n, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-reconstruct-verify.json")
    args = ap.parse_args()
    run_dir = OUT / "verify"
    run_dir.mkdir(exist_ok=True)
    board_sha = sha256_file(BOARD)
    step5 = json.loads(STEP5.read_text(encoding="utf-8"))

    _, nets, _, _ = P.read_pdf()
    epc = {p: n for n, pl in nets.items() for p in pl}
    if len({n.upper() for n in nets}) != len(nets) or max(map(len, nets)) > 14:
        raise SystemExit("EPC net names are not distinct when upper-cased or exceed 14 characters")
    d356 = run_dir / "epc90133.d356"
    d356.unlink(missing_ok=True)
    proc = subprocess.run([str(KICAD_CLI), "pcb", "export", "ipcd356", "-o", str(d356), str(BOARD)],
                          capture_output=True, text=True)
    if proc.returncode or not d356.exists():
        raise SystemExit(f"ipcd356 export failed ({proc.returncode}): {proc.stderr[-1500:]}")
    records = read_ipcd356(d356)
    v1_problems, v2_problems, extras = check_nets(epc, records)
    n_items, ring_bad = check_rings(BOARD.read_text(encoding="utf-8"), step5["ringless"])

    try:
        drc = run_drc(KICAD_CLI, BOARD, run_dir, "drc")
        tol_dir = run_dir / "tolerance"
        tol_dir.mkdir(exist_ok=True)
        shutil.copyfile(BOARD, tol_dir / BOARD.name)
        pro = json.loads(PROJECT.read_text(encoding="utf-8"))
        pro["board"]["design_settings"]["rules"]["min_clearance"] = CLEARANCE - ARC_TOL
        for c in pro["net_settings"]["classes"]:
            c["clearance"] = CLEARANCE - ARC_TOL
        (tol_dir / PROJECT.name).write_text(json.dumps(pro, indent=2) + "\n", encoding="utf-8")
        tol = run_drc(KICAD_CLI, tol_dir / BOARD.name, tol_dir, "drc")
    except KiCadError as exc:
        raise SystemExit(f"DRC failed: {exc}")
    if drc["board_sha256"] != board_sha or tol["board_sha256"] != board_sha or sha256_file(BOARD) != board_sha:
        raise SystemExit("the board changed during verification")
    counts = collections.Counter(v["type"] for v in drc["report"]["violations"])
    v4 = (counts.get("shorting_items", 0) == 0 and not drc["report"]["unconnected_items"]
          and not any(v["type"] == "clearance" for v in tol["report"]["violations"]))
    checks = {"V1_epc_pad_nets": not v1_problems, "V2_other_pads_explained": not v2_problems,
              "V3_rings": not ring_bad, "V4_drc_this_board": v4}
    rel = lambda p: Path(p).resolve().relative_to(ROOT).as_posix()
    out = {"schema": "epc90133-reconstruct-verify/1", "passed": all(checks.values()), "checks": checks,
           "epc_netlist": {"nets": len(nets), "pads": len(epc)}, "readback_pad_records": len(records),
           "v1_problems": v1_problems[:50], "v2_problems": v2_problems[:50], "v2_explained": extras,
           "rings_checked": n_items, "ring_problems": ring_bad[:50],
           "drc": {"counts": dict(counts), "unconnected_items": len(drc["report"]["unconnected_items"]),
                   "clearance_items_at_rule_minus_1um": sum(v["type"] == "clearance" for v in tol["report"]["violations"])},
           "identity": {"board": {"path": rel(BOARD), "sha256": board_sha},
                        "project": {"path": rel(PROJECT), "sha256": sha256_file(PROJECT)},
                        "step5_report": {"path": rel(STEP5), "sha256": sha256_file(STEP5),
                                         "script_sha256": step5.get("script_sha256")},
                        "layout_pdf": {"path": rel(PDF), "sha256": sha256_file(PDF)},
                        "gerber_zip": {"path": rel(ZIP), "sha256": sha256_file(ZIP)},
                        "ipcd356": {"path": rel(d356), "sha256": sha256_file(d356)},
                        "drc_reports": {k: {"path": rel(r["report_path"]), "sha256": r["report_sha256"]}
                                        for k, r in (("rule", drc), ("rule_minus_1um", tol))},
                        "kicad_version": drc["kicad_version"],
                        "script_sha256": sha256_file(Path(__file__)),
                        "helpers": {f: sha256_file(ROOT / f) for f in HELPERS}},
           "scope": "the saved board as stored (EPC's frozen fills); not a qualification of KiCad refill or editing"}
    args.output.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("passed", "checks", "epc_netlist", "readback_pad_records", "rings_checked",
                                          "drc")}, indent=1))
    print("V1", v1_problems[:5], "\nV2", v2_problems[:5], "\nrings", ring_bad[:5])
    print("explained extras", [(e["pad"], e["net"], e["rule"]) for e in extras])
    raise SystemExit(0 if out["passed"] else 1)


if __name__ == "__main__":
    main()
