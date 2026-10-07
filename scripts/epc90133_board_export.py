#!/usr/bin/env python3
"""Export an edited EPC90133 board as an EPC-style Gerber package and run power-loop + extraction on it.

Declared 7 October 2026 before its first run (owner: layout improvements need the edit -> extraction route).

Route. The board text is the editable base of scripts/epc90133_edit_workflow.py (saved reconstruction plus stock-hole
keep-outs) with a case's edit list applied and the auxiliary (drill/plot) origin set to EPC's origin, KiCad (100, 150).
KiCad refills it (circuit_tools.kicad.run_drc, --refill-zones --save-board), a fresh DRC is taken, and kicad-cli
exports Gerbers with --use-drill-file-origin and drills with --drill-origin plot, so coordinates are EPC's
(x right, y up, board 0-50.8 mm). Files are renamed to EPC's names (PREFIX + "Gerbers." + GTL, G1-G6, GBL, GTS, GBS,
GTP, GBP, GTO, GBO, GM1); plated and non-plated drills are exported separately and written into one Excellon file
("NC Drill.TXT") with ;TYPE=PLATED / ;TYPE=NON_PLATED sections, because the project's parser reads plating from
those lines (a trial export showed KiCad's merged file marks plating only in comments). export.json lists every
file's SHA-256, the board's, the edit list and the DRC summary. Then, with read_epc90133_geometry.EXPORT_ENV set in
the child processes only: scripts/epc90133_power_loop.py writes the package's own contact/port record, and
scripts/epc90133_extract.py runs the requested cases with --loop pointing to it.

X0 qualification of the route (case 'stock', no edits), against EPC's own files and stored results:
* X0a drills: the same 445 holes as EPC's drill file (positions and diameters within 0.001 mm, same plating);
* X0b power loop: every FET pin centre, capacitor pad centre and port contact box within 0.010 mm of the stored
  record (results/gan/epc90133-power-loop.json), capacitor pad areas within 2 %, and the record's check outcomes
  (C1-C5, including C1's known board-reason failure) identical;
* X0c extraction A:m1:mid against results/gan/epc90133-extraction/A-m1-mid.json: loop inductance within 0.5 %,
  loop resistance within 2 %, every capacitor current share within 0.01 (absolute), every diagonal of the port
  inductance matrix within 1 %. Mesh statistics are reported.
The route is qualified for variant-A extractions of edited boards only if X0a-X0c pass. The tolerances are about
the route (rasterization of 10 um-level geometry differences at the 1 mil pitch), not the extraction's accuracy,
which stays exploratory (unqualified vias and plane holes, one mesh).

X0 run 1 (7 October 2026): NOT QUALIFIED as declared (results/gan/epc90133-board-export-x0.json). X0a drills and
X0b power-loop contacts/checks pass; X0c fails: A:m1:mid loop L 0.4925 against 0.5017 nH (-1.8 %), R -1.4 %, one
capacitor share 0.013, one port self-inductance 8.8 %; mesh 2,805 against 2,756 nodes. Rasters differ in 12,000-27,000
pixels per layer outside holes (micrometre edge differences flip 1 mil pixels; the mesh is pin-aligned, so pad edges sit
on grid lines) and, on the top layer only, 14 mm^2 of copper EPC draws over drill holes that KiCad leaves empty. A
labelled diagnostic (stock EPC Gerbers with the top layer's hole disks cleared) crashed: Ci1's GND terminal lost every
mesh node, so terminal contacts depend on copper drawn over via-in-pad holes. Reading: the export reproduces the
geometry, not EPC's absolute extracted inductance; the extraction is sensitive at about 2 % to sub-10 um
representation and the hole-copper convention (inside the 2-4 % via/mesh sensitivity already recorded).
RETROSPECTIVE AMENDMENT (after X0 run 1): edited boards are compared only with 'stock' exported through this same
route (matched control; the route offset cancels), and a change counts only beyond 4 % in loop inductance (the upper
end of the recorded via/mesh representation sensitivity). Absolute values through this route are not compared with
the stored EPC-Gerber extractions.

Output: <outdir>/export.json, <outdir>/power-loop.json, <outdir>/extraction/A-m1-mid-<case>.json and, for 'stock',
results/gan/epc90133-board-export-x0.json. Packages live in git-ignored vendor/epc/epc90133/reconstruction/export/
(EPC-derived geometry). Time limit 3600 s per child process (power loop and A extraction each took minutes).
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from circuit_tools.gerber import parse_excellon
from circuit_tools.kicad import KiCadError, run_drc, sha256_file
from read_epc90133_geometry import EXPORT_ENV, GERBERS, PREFIX
import epc90133_edit_workflow as ew
from epc90133_reconstruct import KICAD_CLI, OUT

EXPORT_ROOT = OUT / "export"
EPC_NAME = {"F.Cu": "GTL", "In1.Cu": "G1", "In2.Cu": "G2", "In3.Cu": "G3", "In4.Cu": "G4", "In5.Cu": "G5",
            "In6.Cu": "G6", "B.Cu": "GBL", "F.Mask": "GTS", "B.Mask": "GBS", "F.Paste": "GTP", "B.Paste": "GBP",
            "F.SilkS": "GTO", "B.SilkS": "GBO", "Edge.Cuts": "GM1"}
TIMEOUT = 3600
STORED_LOOP = ROOT / "results/gan/epc90133-power-loop.json"
STORED_A = ROOT / "results/gan/epc90133-extraction/A-m1-mid.json"
CASES = {"stock": []}


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def with_aux_origin(text):
    if "(aux_axis_origin" in text:
        raise SystemExit("board already has an aux origin")
    new, n = re.subn(r"^\t\(setup\b", "\t(setup\n\t\t(aux_axis_origin 100 150)", text, count=1, flags=re.M)
    if n != 1:
        raise SystemExit("no (setup ...) block found")
    return new


def write_excellon(pth, npth, path):
    rows = ["M48", "METRIC"]
    tools, k = {}, 0
    for plated, holes in ((True, pth), (False, npth)):
        rows.append(";TYPE=PLATED" if plated else ";TYPE=NON_PLATED")
        for d in sorted({round(h.diameter, 4) for h in holes}):
            k += 1
            tools[(plated, d)] = k
            rows.append(f"T{k}C{d:.4f}")
    rows.append("%")
    for plated, holes in ((True, pth), (False, npth)):
        for d in sorted({round(h.diameter, 4) for h in holes}):
            rows.append(f"T{tools[(plated, d)]}")
            rows += [f"X{h.x:.4f}Y{h.y:.4f}" for h in holes if round(h.diameter, 4) == d]
    rows.append("M30")
    path.write_text("\n".join(rows) + "\n", encoding="latin-1")


def export_package(case, edits, outdir):
    geo = ew.epc_layers()
    base = (OUT / "epc90133.kicad_pcb").read_text(encoding="utf-8").rstrip()
    ident = json.loads(ew.VERIFY.read_text(encoding="utf-8"))["identity"]
    if sha256_file(OUT / "epc90133.kicad_pcb") != ident["board"]["sha256"]:
        raise SystemExit("saved board is not the verified reconstruction")
    base = base[:-1] + "".join(ew.keepouts(geo)) + ")\n"
    text, log = ew.apply_edits(base, edits, geo)
    text = with_aux_origin(text)
    bdir = outdir / "board"
    bdir.mkdir(parents=True, exist_ok=True)
    board = bdir / "epc90133.kicad_pcb"
    board.write_text(text, encoding="utf-8")
    (bdir / "epc90133.kicad_pro").write_bytes((OUT / "epc90133.kicad_pro").read_bytes())
    run_drc(KICAD_CLI, board, bdir, "refill", extra=("--refill-zones", "--save-board"), timeout=TIMEOUT)
    drc = run_drc(KICAD_CLI, board, bdir, "drc", timeout=TIMEOUT)
    gdir, ddir = bdir / "gerbers", bdir / "drill"
    r = subprocess.run([str(KICAD_CLI), "pcb", "export", "gerbers", "--use-drill-file-origin", "--no-protel-ext",
                        "--layers", ",".join(EPC_NAME), "-o", str(gdir) + os.sep, str(board)],
                       capture_output=True, text=True, timeout=TIMEOUT)
    if r.returncode:
        raise KiCadError(f"gerber export failed: {r.stderr[-800:]}")
    r = subprocess.run([str(KICAD_CLI), "pcb", "export", "drill", "--drill-origin", "plot", "--excellon-separate-th",
                        "-o", str(ddir) + os.sep, str(board)], capture_output=True, text=True, timeout=TIMEOUT)
    if r.returncode:
        raise KiCadError(f"drill export failed: {r.stderr[-800:]}")
    files = {}
    for layer, ext in EPC_NAME.items():
        suffix = {"F.SilkS": "F_Silkscreen", "B.SilkS": "B_Silkscreen"}.get(layer, layer.replace(".", "_"))
        src = next(p for p in gdir.iterdir() if p.name.endswith("-" + suffix + ".gbr"))
        dst = outdir / f"{PREFIX}Gerbers.{ext}"
        dst.write_bytes(src.read_bytes())
        files[dst.name] = sha256(dst)
    pth = parse_excellon(next(ddir.glob("*-PTH.drl")).read_text(encoding="latin-1"))
    npth_file = next(ddir.glob("*-NPTH.drl"), None)
    npth = parse_excellon(npth_file.read_text(encoding="latin-1")) if npth_file else []
    drill = outdir / f"{PREFIX}NC Drill.TXT"
    write_excellon(pth, npth, drill)
    files[drill.name] = sha256(drill)
    manifest = {"schema": "epc90133-board-export/1", "case": case, "edits": [list(e) for e in edits], "edit_log": log,
                "board_sha256": sha256_file(board), "drc_summary": ew.drc_summary(drc["report"]),
                "kicad_version": drc["kicad_version"], "files": files,
                "frame": "EPC Gerber frame (aux origin at KiCad (100, 150); x right, y up, mm)"}
    (outdir / "export.json").write_text(json.dumps(manifest, indent=1, default=str) + "\n", encoding="utf-8")
    return manifest


def child(args, outdir, log_name):
    env = dict(os.environ, **{EXPORT_ENV: str(outdir), "PYTHONPATH": str(ROOT / "src")})
    r = subprocess.run([sys.executable, *args], capture_output=True, text=True, timeout=TIMEOUT, env=env, cwd=ROOT)
    (outdir / f"{log_name}.log").write_text(r.stdout + "\n--- stderr ---\n" + r.stderr, encoding="utf-8")
    return r.returncode


def near(a, b, tol):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def x0_checks(outdir, cases_out):
    epc = sorted((round(h.x, 3), round(h.y, 3), round(h.diameter, 3), h.plated)
                 for h in parse_excellon((GERBERS / f"{PREFIX}NC Drill.TXT").read_text(encoding="latin-1")))
    exp = sorted((round(h.x, 3), round(h.y, 3), round(h.diameter, 3), h.plated)
                 for h in parse_excellon((outdir / f"{PREFIX}NC Drill.TXT").read_text(encoding="latin-1")))
    x0a = {"epc_holes": len(epc), "export_holes": len(exp),
           "pass": len(epc) == len(exp) and all(a[3] == b[3] and near(a[:3], b[:3], 0.001 + 1e-9) for a, b in zip(epc, exp))}
    s, n = json.loads(STORED_LOOP.read_text(encoding="utf-8")), json.loads((outdir / "power-loop.json").read_text(encoding="utf-8"))
    bad = []
    for q in ("Q1", "Q2"):
        for p, pin in s["fets"][q]["pins"].items():
            if not near(pin["centre_mm"], n["fets"][q]["pins"][p]["centre_mm"], 0.010):
                bad.append(f"{q}.{p} centre")
    for k in ("Ci", "Cm"):
        for cs, cn in zip(s["capacitors"][k]["caps"], n["capacitors"][k]["caps"]):
            for ps, pn in zip(cs["pads"], cn["pads"]):
                if not near(ps["centre_mm"], pn["centre_mm"], 0.010):
                    bad.append(f"{cs['ref']} {ps['net']} centre")
                if abs(pn["area_mm2"] / ps["area_mm2"] - 1) > 0.02:
                    bad.append(f"{cs['ref']} {ps['net']} area")
    for t, v in s["ports"]["terminals"].items():
        nb = n["ports"]["terminals"].get(t, {}).get("contact_bboxes_mm", [])
        if len(nb) != len(v["contact_bboxes_mm"]) or not all(near(a, b, 0.010) for a, b in zip(v["contact_bboxes_mm"], nb)):
            bad.append(f"port {t}")
    x0b = {"differences": bad, "checks_stored": s["checks"], "checks_export": n["checks"],
           "pass": not bad and s["checks"] == n["checks"]}
    sa = json.loads(STORED_A.read_text(encoding="utf-8"))
    na = json.loads(cases_out["A:m1:mid"].read_text(encoding="utf-8"))
    ss, ns = sa["summary"], na["summary"]
    rel = lambda a, b: abs(b / a - 1)
    import numpy as np
    dl = (np.abs(np.diag(np.array(na["L_H"])) / np.diag(np.array(sa["L_H"])) - 1)).max() \
        if sa["port_order"] == na["port_order"] else None
    shares = {c: abs(ns["capacitor_current_share"][c] - v) for c, v in ss["capacitor_current_share"].items()}
    x0c = {"L_loop_nH": [ss["L_loop_nH"], ns["L_loop_nH"]], "L_rel": rel(ss["L_loop_nH"], ns["L_loop_nH"]),
           "R_loop_mohm": [ss["R_loop_mohm"], ns["R_loop_mohm"]], "R_rel": rel(ss["R_loop_mohm"], ns["R_loop_mohm"]),
           "max_share_diff": max(shares.values()), "max_diag_L_rel": dl, "same_port_order": sa["port_order"] == na["port_order"],
           "mesh_stats": {"stored": {k: sa["mesh_stats"][k] for k in ("grid", "nodes", "segments", "filaments_before_refine")},
                          "export": {k: na["mesh_stats"][k] for k in ("grid", "nodes", "segments", "filaments_before_refine")}}}
    x0c["pass"] = (x0c["L_rel"] <= 0.005 and x0c["R_rel"] <= 0.02 and x0c["max_share_diff"] <= 0.01
                   and dl is not None and dl <= 0.01 and na.get("outcome") == "complete")
    return {"X0a_drills": x0a, "X0b_power_loop": x0b, "X0c_extraction_A": x0c,
            "pass": x0a["pass"] and x0b["pass"] and x0c["pass"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case", choices=sorted(CASES))
    ap.add_argument("--extract", nargs="*", default=["A:m1:mid"])
    args = ap.parse_args()
    outdir = EXPORT_ROOT / args.case
    if outdir.exists() and any(outdir.iterdir()):
        raise SystemExit(f"{outdir} exists; packages are never overwritten (remove it deliberately)")
    outdir.mkdir(parents=True, exist_ok=True)
    manifest = export_package(args.case, CASES[args.case], outdir)
    print("exported", args.case, manifest["drc_summary"], flush=True)
    rc = child(["scripts/epc90133_power_loop.py", "--output", str(outdir / "power-loop.json"),
                "--renders", str(outdir / "power-loop")], outdir, "power-loop")
    print("power loop exit", rc, flush=True)
    cases_out = {}
    if (outdir / "power-loop.json").exists():
        for c in args.extract:
            rc = child(["scripts/epc90133_extract.py", c, "--loop", str(outdir / "power-loop.json"),
                        "--outdir", str(outdir / "extraction"), "--tag", args.case], outdir, "extract-" + c.replace(":", "_"))
            out = outdir / "extraction" / ("-".join(c.split(":")[:3]) + f"-{args.case}.json")
            print("extract", c, "exit", rc, out.exists(), flush=True)
            if out.exists():
                cases_out[c] = out
    if args.case == "stock":
        res = {"schema": "epc90133-board-export-x0/1", "evaluator_sha256": sha256(__file__),
               "manifest_sha256": sha256(outdir / "export.json"), "export_dir": str(outdir.relative_to(ROOT)),
               "inputs": {"stored_power_loop": sha256(STORED_LOOP), "stored_A": sha256(STORED_A)}}
        try:
            res.update(x0_checks(outdir, cases_out))
        except (KeyError, FileNotFoundError, StopIteration) as exc:
            res.update({"error": repr(exc), "pass": False})
        res["outcome"] = "qualified" if res.get("pass") else "not qualified"
        (ROOT / "results/gan/epc90133-board-export-x0.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
        print("X0", res["outcome"], json.dumps({k: res.get(k, {}).get("pass") if isinstance(res.get(k), dict) else res.get(k)
                                                 for k in ("X0a_drills", "X0b_power_loop", "X0c_extraction_A", "error")}), flush=True)
        return 0 if res.get("pass") else 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
