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

Candidate L3a (declared 7 October 2026 before its build; layout plan option L3). The top input capacitors Ci1-Ci7
move 0.40 mm toward Q1 (VIN pad bottom 33.36 -> 32.96 mm; the Q1 switch-node bars end at about 32.70, so about 0.26 mm
remains); the 20 VIN stitching vias under their VIN pads (rows y = 33.63 and 34.30, x 16-31 mm, ten pairs sharing
inner-layer clearance slots) move with them through move_vias (new group primitive: each shared hole translated
once); the GND via row at y = 34.90 stays (it remains inside the moved GND pads) and the bottom capacitors stay (the
bottom VIN pads would otherwise meet the bottom switch-node fingers); top GND copper is widened by
reshape(F.Cu, GND, (15.4, 34.25)-(32.0, 34.70)), which cuts VIN back by the 0.150114 mm rule. Acceptance before any
comparison: L1 DRC as stock-through-route (0 unconnected, no shorts, isolated copper 13, no clearance below the rule,
no new DRC types); L2 IPC-D-356 pad nets equal stock's; L3 power-loop record checks C2-C5 pass (C1 as stock); L4
A:m1:mid extraction complete. Comparison: loop inductance, resistance and capacitor current shares against
'stock' through this route; the change counts only if |dL|/L > 4 %. Switching simulation follows only if it counts.
Output: results/gan/epc90133-board-export-L3a.json.
Candidates V6/V7/V8 (layout search F1, declared 7 October 2026 before their builds; screens S6-S8 gave A -13.9 /
-8.9 / -50.7 %): the S6/S7 via-thinning rule built legally with remove_vias. Same acceptance L1-L4 and A comparison
with stock through the route (4 % rule). Because the removed vias also feed the bottom loop that A omits, every
candidate that counts on A is then extracted on B (B:m1:mid, with stock through the route as control) and counts only
if it also beats B by more than 4 %.
V6/V7/V8 run 1 (7 October 2026; kept as export/<case>-run1-slit and results/gan/epc90133-board-export-<case>-run1-slit.json):
all legal (L1-L4 pass); A loop L -2.8 / -4.3 / -7.1 %. Defect: remove_vias kept one split keep-out piece per slot
whose straight edge cuts a chord 0.00008 mm^2 outside the curved slot outline, so a thin slit stayed in the plane
(seen on In1 under Q1 at x = 22.2). Revision 2 (RETROSPECTIVE, edit primitive only): containment by area (at most
0.1 % of the piece outside the hole). --reuse (new): an existing package gets further extractions (manifest checked)
and B/G comparisons with stock through the route.
L3a run 1 (7 October 2026) REJECTED (package kept as export/L3a-run1-rejected; no report, the driver crashed): DRC 14
isolated-copper items (a 0.011 mm^2 GND sliver on In1 at x 15.8-16.0, y 32.9, pinched off where the moved x = 16.05 VIN
pair approaches the plane edge) and 14 silk_over_copper (EPC's frozen silk ticks now on the moved GND pads); the
power-loop record lost every Ci VIN contact (its Ci window starts at y = 33.0, so the moved pads were dropped as cut by
the window edge: C5 fails, extraction KeyError 'Ci1.VIN'); and the driver expected a pad-net list the stock package
predates (KeyError). Revision 2 (RETROSPECTIVE): silk pieces wholly within a moved part's pad-centre box grown by
0.5 mm move with it; netted zones in edited builds drop isolated fill islands (KiCad's default; stock has no netted
isolated islands, so stock is unaffected); the power-loop Ci window follows the move (CAP_WINDOWS); the stock pad nets
are read from the stock board when missing. Acceptance and comparison rules are unchanged.
Candidate V9 (layout search F1, declared 7 October 2026 before its build, after the screens were found invalid and
V6-V8 became this family's evidence): the same columns as V8 with only every third via kept (the 1st and 4th from the
lowest y; 26 vias removed, 14 kept, against V8's 20 and 20), slots to EPC-size per-via antipads. Same acceptance
L1-L4, A comparison with stock through the route and the 4 % rule; it is extracted on A as soon as a solver slot is
free, and on B/G only if it beats V8 on A by more than 4 % of stock (otherwise V8 stays the family's candidate).
Practical limit, not modelled: fewer vias carry the switch-node current to the inner and bottom layers (heating).

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
# B run 1 (7 October 2026) was killed at TIMEOUT for stock and V8 (the stored B profile is 6,588 s); B now gets
# 14,400 s. Retrospective: the limit was set from the A profile and never derived for B.
B_TIMEOUT = 14400
STORED_LOOP = ROOT / "results/gan/epc90133-power-loop.json"
STORED_A = ROOT / "results/gan/epc90133-extraction/A-m1-mid.json"
L3A_VIAS = [(16.05, 33.5999), (16.05, 34.3004), (17.5293, 34.3004), (17.5387, 33.625), (19.21, 34.3004),
            (19.2192, 33.625), (20.8907, 34.3004), (20.9001, 33.625), (22.5715, 34.3004), (22.5806, 33.625),
            (24.2522, 34.3004), (24.2613, 33.625), (25.9326, 34.3004), (25.942, 33.625), (27.6228, 33.625),
            (27.6291, 34.3004), (29.3035, 33.625), (29.3098, 34.3004), (30.9999, 33.625), (30.9999, 34.275)]
CASES = {
    "stock": [],
    # L3a (declared 7 October 2026 before its build): input capacitors 0.40 mm toward Q1 with their VIN via pairs;
    # top GND copper widened 0.40 mm along the strip so the moved GND pads stay on ground (VIN cut back by the rule).
    "L3a": [*[("move_footprint", f"Ci{k}", 0.0, -0.40) for k in range(1, 8)],
            ("move_vias", L3A_VIAS, 0.0, -0.40),
            ("reshape", "F.Cu", "GND", (15.4, 34.25, 32.0, 34.70), None)],
}
# Revision 2 (retrospective after L3a run 1): capacitor windows of the power-loop record follow the moved parts.
CAP_WINDOWS = {"L3a": {"Ci": [15.0, 32.6, 28.0, 35.8]}}
NETTED_ISLAND = re.compile(r'^(\t\(zone \(net [1-9]\d*\) .*?)\(island_removal_mode 1\)', re.M)
LOOP_L_THRESHOLD = 0.04


def thin_list(regions, keep_every=2):
    """Vias removed by the layout-search screens S6/S7 (scripts/epc90133_layout_screen.py THIN rule); keep_every=3
    (V9) keeps only every third via of each column instead of every other."""
    import epc90133_layout_screen as ls
    drills = parse_excellon((GERBERS / f"{PREFIX}NC Drill.TXT").read_text(encoding="latin-1"))
    if keep_every == 2:
        kept, _ = ls.thinned(drills, regions)
        ids = {id(d) for d in kept}
        return [(round(d.x, 4), round(d.y, 4)) for d in drills if id(d) not in ids]
    gone = []
    for r in regions:
        w = ls.WINDOWS[r]
        for cx in ls.THIN[r]:
            col = sorted((d for d in drills if abs(d.x - cx) < 0.06 and w[0] < d.x < w[2] and w[1] < d.y < w[3]),
                         key=lambda d: d.y)
            gone += [d for k, d in enumerate(col) if k % keep_every]
    return [(round(d.x, 4), round(d.y, 4)) for d in gone]


EPC_ANTIPAD_R = 0.3275
CASES.update({
    # Layout search F1 (plans/layout-search-2026-10-07.md; declared 7 October 2026 before their builds): every other
    # via removed in the slotted non-GND columns under Q1 (V6), Q2 (V7) or both (V8); the slots on every layer become
    # EPC-size per-via antipads (remove_vias).
    "V6": [("remove_vias", thin_list(["Q1"]), EPC_ANTIPAD_R)],
    "V7": [("remove_vias", thin_list(["Q2"]), EPC_ANTIPAD_R)],
    "V8": [("remove_vias", thin_list(["Q1", "Q2"]), EPC_ANTIPAD_R)],
    "V9": [("remove_vias", thin_list(["Q1", "Q2"], keep_every=3), EPC_ANTIPAD_R)],
    # Candidate K1 (declared 10 October 2026 before its build; plans/goal-targets-2026-10-08.md): Q2 Kelvin-style
    # driver return on the top layer. The probe net NetJ2_1 (R22 pad 1 -> J22 pin 1) moves to B.Cu through one new
    # via beside R22 pad 1; the freed top-layer gap becomes GND joining the driver's GND copper to Q2's source copper.
    "K1": [("reshape", "F.Cu", "NetJ2_1", (15.85, 26.70, 16.30, 27.05), None),
           ("reshape", "F.Cu", "GND", (15.60, 25.80, 17.20, 26.44), None),
           ("reshape", "B.Cu", "NetJ2_1", (15.95, 25.40, 16.25, 27.06), None),
           ("add_via", 15.98, 26.88, 0.3488, 0.1981, "NetJ2_1",
            ("In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "In5.Cu", "In6.Cu"), EPC_ANTIPAD_R),
           # Run 3 (RETROSPECTIVE after run 2's DRC: the via came out on GND): tracks tie the via to R22.1 and J22.1.
           ("add_track", "F.Cu", "NetJ2_1", [(15.98, 26.88), (16.379, 26.90)], 0.25),
           ("add_track", "B.Cu", "NetJ2_1", [(15.98, 26.88), (16.10, 26.75), (16.10, 25.30)], 0.30)],
})
CASES.update({
    # Candidate K2 (declared 10 October 2026 before any K1 result; K1 decision tree step 2): K1 plus EPC-size antipads
    # on In1-In6 around the three driver GND vias, so the driver's ground reaches the planes only through Q2's source
    # copper (top) and the bottom layer.
    "K2": CASES["K1"] + [("antipad", x, y, EPC_ANTIPAD_R, ("In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "In5.Cu", "In6.Cu"))
                         for x, y in ((15.429, 27.201), (15.592, 26.200), (15.603, 28.549))],
})
INNER = ("In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "In5.Cu", "In6.Cu")
DRIVER_GND_VIAS = ((15.429, 27.201), (15.592, 26.200), (15.603, 28.549))
CASES.update({
    # Candidate C3 (search stage 2, declared 11 October 2026 before its build; plans/goal-targets-2026-10-08.md): K1
    # plus a dedicated driver-return island on In1 under Q2's gate drive. Driver GND vias isolated on In2-In6 only;
    # slits (0.18 mm copper-pour keep-outs; runs 1-3 cut the plane outline and were rejected) separate the island from the In1 plane; one new GND via on the top-layer source
    # copper joins the island to Q2's source near the gate end (top and In1 only).
    "C3": CASES["K1"] + [("antipad", x, y, EPC_ANTIPAD_R, INNER[1:]) for x, y in DRIVER_GND_VIAS] + [
        ("keepout", "In1.Cu", (15.00, 25.90, 17.45, 26.08)),   # bottom slit
        ("keepout", "In1.Cu", (15.00, 25.90, 15.18, 27.73)),   # left slit, lower
        ("keepout", "In1.Cu", (15.00, 27.55, 15.40, 27.73)),   # left step
        ("keepout", "In1.Cu", (15.22, 27.55, 15.40, 29.48)),   # left slit, upper
        ("keepout", "In1.Cu", (15.22, 29.30, 17.45, 29.48)),   # top slit
        ("keepout", "In1.Cu", (17.27, 25.90, 17.45, 29.48)),   # right slit
        ("add_via", 17.00, 26.25, 0.3488, 0.1981, "GND", INNER[1:], EPC_ANTIPAD_R)],
})
CASES.update({
    # P1 (free-placement study, declared 10 October 2026 before its build; owner: parts may move anywhere viable):
    # the outlying input capacitor Ci7 moved into the free Ci-row slot at x = 24.15 (row pitch 1.30 mm), whose vias
    # follow the same pattern as an occupied slot (filled, plated-over vias: via-in-pad allowed by EPC's fab note).
    "P1": [("move_footprint", "Ci7", -2.70, 0.0)],
})  # retrospective amendment after X0 run 1


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
    if edits:
        # Revision 2: netted zones drop isolated fill islands (KiCad's default). Stock has none (its 13 isolated
        # islands are all netless and keep mode 1), so only islands created by an edit are removed.
        text = NETTED_ISLAND.sub(lambda m: m.group(1) + "(island_removal_mode 0)", text)
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
    ipc = bdir / "board.d356"
    r = subprocess.run([str(KICAD_CLI), "pcb", "export", "ipcd356", "-o", str(ipc), str(board)],
                       capture_output=True, text=True, timeout=TIMEOUT)
    if r.returncode:
        raise KiCadError("ipcd356 export failed")
    manifest = {"schema": "epc90133-board-export/1", "case": case,
                "pad_nets": {x["key"]: x["net"] for x in ew.read_ipcd356(ipc)}, "edits": [list(e) for e in edits], "edit_log": log,
                "board_sha256": sha256_file(board), "drc_summary": ew.drc_summary(drc["report"]),
                "kicad_version": drc["kicad_version"], "files": files,
                "frame": "EPC Gerber frame (aux origin at KiCad (100, 150); x right, y up, mm)"}
    (outdir / "export.json").write_text(json.dumps(manifest, indent=1, default=str) + "\n", encoding="utf-8")
    return manifest


G_TIMEOUT = 21600  # s; stock G-m1-mid took 12,279 s (profile), x1.75 margin (added 7 October 2026 for the search)


def child(args, outdir, log_name):
    env = dict(os.environ, **{EXPORT_ENV: str(outdir), "PYTHONPATH": str(ROOT / "src")})
    limit = (G_TIMEOUT if any(str(a).startswith("G:") for a in args) else
             B_TIMEOUT if any(str(a).startswith("B:") for a in args) else TIMEOUT)
    r = subprocess.run([sys.executable, *args], capture_output=True, text=True, timeout=limit, env=env, cwd=ROOT)
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
    ap.add_argument("--reuse", action="store_true",
                    help="existing package: verify its manifest, keep its board and power-loop record, run only the "
                         "extractions not yet present (7 October 2026, layout search confirmation)")
    args = ap.parse_args()
    outdir = EXPORT_ROOT / args.case
    if args.reuse:
        if not (outdir / "export.json").exists() or not (outdir / "power-loop.json").exists():
            raise SystemExit(f"--reuse: {outdir} has no complete package")
        man = json.loads((outdir / "export.json").read_text(encoding="utf-8"))
        bad = [f for f, h in man["files"].items() if sha256(outdir / f) != h]
        if bad:
            raise SystemExit(f"--reuse: package files differ from the manifest: {bad}")
    else:
        if outdir.exists() and any(outdir.iterdir()):
            raise SystemExit(f"{outdir} exists; packages are never overwritten (remove it deliberately)")
        outdir.mkdir(parents=True, exist_ok=True)
        manifest = export_package(args.case, CASES[args.case], outdir)
        print("exported", args.case, manifest["drc_summary"], flush=True)
        rc = child(["scripts/epc90133_power_loop.py", "--output", str(outdir / "power-loop.json"),
                    "--renders", str(outdir / "power-loop"),
                    *(["--cap-windows", json.dumps(CAP_WINDOWS[args.case])] if args.case in CAP_WINDOWS else [])],
                   outdir, "power-loop")
        print("power loop exit", rc, flush=True)
    cases_out = {}
    for c in ("A:m1:mid", "B:m1:mid", "G:m1:mid"):
        prior = outdir / "extraction" / ("-".join(c.split(":")[:3]) + f"-{args.case}.json")
        if prior.exists():
            cases_out[c] = prior
    if (outdir / "power-loop.json").exists():
        for c in [c for c in args.extract if c not in cases_out]:
            rc = child(["scripts/epc90133_extract.py", c, "--loop", str(outdir / "power-loop.json"),
                        "--outdir", str(outdir / "extraction"), "--tag", args.case], outdir, "extract-" + c.replace(":", "_"))
            out = outdir / "extraction" / ("-".join(c.split(":")[:3]) + f"-{args.case}.json")
            print("extract", c, "exit", rc, out.exists(), flush=True)
            if out.exists():
                cases_out[c] = out
    if args.case != "stock":
        st = EXPORT_ROOT / "stock"
        sm = json.loads((st / "export.json").read_text(encoding="utf-8"))
        cm = json.loads((outdir / "export.json").read_text(encoding="utf-8"))
        res = {"schema": "epc90133-board-export-candidate/1", "case": args.case, "evaluator_sha256": sha256(__file__),
               "edits": cm["edits"], "edit_log": cm["edit_log"], "manifest_sha256": sha256(outdir / "export.json"),
               "stock_manifest_sha256": sha256(st / "export.json")}
        d = cm["drc_summary"]
        res["L1_drc"] = {**d, "new_types": sorted(set(d["types"]) - set(sm["drc_summary"]["types"]))}
        res["L1_drc"]["pass"] = d["pass"] and not res["L1_drc"]["new_types"]
        if "pad_nets" not in sm:  # revision 2: the stock package predates the pad-net list; read its board
            ipc = st / "board" / "board-pad-nets.d356"
            if not ipc.exists():
                subprocess.run([str(KICAD_CLI), "pcb", "export", "ipcd356", "-o", str(ipc), str(st / "board" / "epc90133.kicad_pcb")],
                               capture_output=True, text=True, timeout=TIMEOUT, check=True)
            sm["pad_nets"] = {x["key"]: x["net"] for x in ew.read_ipcd356(ipc)}
        diff = sorted(k for k in set(sm["pad_nets"]) | set(cm["pad_nets"]) if sm["pad_nets"].get(k) != cm["pad_nets"].get(k))
        res["L2_nets"] = {"differences": diff[:20], "pass": not diff}
        loop_ok = (outdir / "power-loop.json").exists()
        if loop_ok:
            pc = json.loads((outdir / "power-loop.json").read_text(encoding="utf-8"))["checks"]
            res["L3_power_loop"] = {"checks": pc, "pass": all(v for k, v in pc.items() if not k.startswith("C1"))}
        else:
            res["L3_power_loop"] = {"pass": False, "error": "no power-loop record"}
        a = cases_out.get("A:m1:mid")
        na = json.loads(a.read_text(encoding="utf-8")) if a else None
        res["L4_extraction"] = {"pass": bool(na and na.get("outcome") == "complete")}
        res["accepted"] = all(res[k]["pass"] for k in ("L1_drc", "L2_nets", "L3_power_loop", "L4_extraction"))
        if res["accepted"]:
            sa = json.loads((st / "extraction" / "A-m1-mid-stock.json").read_text(encoding="utf-8"))
            ss, ns = sa["summary"], na["summary"]
            dl = ns["L_loop_nH"] / ss["L_loop_nH"] - 1
            res["comparison_vs_stock_route"] = {
                "L_loop_nH": [ss["L_loop_nH"], ns["L_loop_nH"]], "relative_change": dl,
                "R_loop_mohm": [ss["R_loop_mohm"], ns["R_loop_mohm"]],
                "capacitor_current_share": {"stock": ss["capacitor_current_share"], "candidate": ns["capacitor_current_share"]},
                "threshold": LOOP_L_THRESHOLD, "counts": abs(dl) > LOOP_L_THRESHOLD}
            # Confirmation variants (B, G) against stock through the route, when both exist.
            for c in ("B:m1:mid", "G:m1:mid"):
                stem = "-".join(c.split(":")[:3])
                sp, cp = st / "extraction" / f"{stem}-stock.json", cases_out.get(c)
                if sp.exists() and cp:
                    sx, cx = json.loads(sp.read_text(encoding="utf-8")), json.loads(cp.read_text(encoding="utf-8"))
                    if sx.get("outcome") == "complete" and cx.get("outcome") == "complete":
                        a_, b_ = sx["summary"]["L_loop_nH"], cx["summary"]["L_loop_nH"]
                        res[f"comparison_vs_stock_route_{stem}"] = {
                            "L_loop_nH": [a_, b_], "relative_change": b_ / a_ - 1,
                            "threshold": LOOP_L_THRESHOLD, "counts": abs(b_ / a_ - 1) > LOOP_L_THRESHOLD}
        res["outcome"] = ("rejected (acceptance)" if not res["accepted"] else
                          "counts" if res["comparison_vs_stock_route"]["counts"] else "below threshold")
        (ROOT / f"results/gan/epc90133-board-export-{args.case}.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
        print(args.case, res["outcome"], json.dumps({k: res[k]["pass"] for k in ("L1_drc", "L2_nets", "L3_power_loop", "L4_extraction")}),
              json.dumps(res.get("comparison_vs_stock_route", {}).get("L_loop_nH")), res.get("comparison_vs_stock_route", {}).get("relative_change"),
              flush=True)
        return 0 if res["accepted"] else 2
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
