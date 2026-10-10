#!/usr/bin/env python3
"""Candidate comparison page: every built layout candidate, its extracted parasitics and its S1-S13 goal values.

Reads saved results only (no solver): the goals assessments (scorer revision 2; vendor model primary, EPC2302DS alternative), the
board-export reports and the per-candidate extraction reports under the git-ignored reconstruction export folder
(numbers only). Every value is compared with stock through the same route: green better, red worse; extraction
changes smaller than the route's declared 4 % comparison threshold are tinted pale. Writes
results/gan/epc90133-candidates.json (the data) and epc90133-candidates.html in the repository root (the page). Rerun after any
new candidate, extraction or goals assessment, then republish the page.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results/gan"
EXPORT = ROOT / "vendor/epc/epc90133/reconstruction/export"
# Vendor model primary from 9 October 2026 (owner decision); EPC2302DS shown as the alternative.
# Per model, assessments searched in order; a design is taken from the first file that scores it.
ASSESS = {"vendor": [RES / "epc90133-goals-assessment-V8d075.json", RES / "epc90133-goals-assessment-vendor-rev2.json"],
          "EPC2302DS": [RES / "epc90133-goals-assessment-ds-rev2.json"]}
GOAL_NAME = {"V8+d0.075": "V8d075", "stock+csw": "stock", "V8+d0.075+csw": "V8d075"}  # candidate id -> design name
# Sensitivity rows scored from their own assessment and compared with their own reference row, not plain stock.
OWN_ASSESS = {"K1": {"vendor": [RES / "epc90133-goals-assessment-K1.json"]}, "K2": {"vendor": [RES / "epc90133-goals-assessment-K2.json"]},"stock+csw": {"vendor": [RES / "epc90133-goals-assessment-V8d075-csw.json"]},
              "V8+d0.075+csw": {"vendor": [RES / "epc90133-goals-assessment-V8d075-csw.json"]}}
OWN_REF = {"stock+csw": "stock+csw", "V8+d0.075+csw": "stock+csw"}
ROUTE_THRESHOLD = 0.04
PRIMARY = ("ramp-Ls50", "step-Ls50")

# id, label, what changed, extraction file stems (A, G) under EXPORT/<folder>/extraction, board-export report
CANDIDATES = [
    ("stock", "Stock", "EPC's published layout, rebuilt in KiCad (the reference)", "stock", "A-m1-mid-stock", "G-m1-mid-stock", None),
    ("V6", "V6", "Every other via removed in Q1's slotted via columns", "V6", "A-m1-mid-V6", None, "V6"),
    ("V7", "V7", "Every other via removed in Q2's slotted via columns", "V7", "A-m1-mid-V7", None, "V7"),
    ("V8", "V8", "Every other via removed under both FETs (20 of 40)", "V8", "A-m1-mid-V8", "G-m1-mid-V8", "V8"),
    ("V9", "V9", "Every third via kept under both FETs", "V9", "A-m1-mid-V9", None, "V9"),
    ("L3a", "L3a", "Input capacitors Ci1-Ci7 moved 0.40 mm toward Q1", "L3a", "A-m1-mid-L3a", None, "L3a"),
    ("d0.100", "Dielectric 0.100 mm", "Power-loop dielectric 0.127 -> 0.100 mm", "stock", "A-m1-mid-d0.100-stock", None, None),
    ("d0.075", "Dielectric 0.075 mm", "Power-loop dielectric 0.075 mm (thinnest standard)", "stock", "A-m1-mid-d0.075-stock", None, None),
    ("d0.050", "Dielectric 0.050 mm *", "Sensitivity only: below the industry-practice limit", "stock", "A-m1-mid-d0.050-stock", None, None),
    ("V8+d0.100", "V8 + 0.100 mm", "V8 with 0.100 mm dielectric", "V8", "A-m1-mid-d0.100-V8", None, None),
    ("V8+d0.075", "V8 + 0.075 mm", "V8 with 0.075 mm dielectric (best screened legal combination)", "V8", "A-m1-mid-d0.075-V8", "G-m1-mid-d0.075-V8", None),
    ("V8+d0.050", "V8 + 0.050 mm *", "Sensitivity only: below the industry-practice limit", "V8", "A-m1-mid-d0.050-V8", None, None),
    ("K1", "K1 Kelvin return", "Q2 driver ground joined to Q2's source on the top layer; probe trace moved to the bottom through one new via", "K1", "A-m1-mid-K1", "G-m1-mid-K1", "K1"),
    ("K2", "K2 isolated driver return", "K1 plus the three driver ground vias cut off from the inner planes: the driver's ground reaches the planes only through Q2's source copper and the bottom layer", "K2", "A-m1-mid-K2", "G-m1-mid-K2", "K2"),
    ("stock+csw", "Stock + SW capacitance", "Reference for the row below: stock with 135 pF switch-node-to-ground capacitance (estimate)", "stock", "A-m1-mid-stock", "G-m1-mid-stock", None),
    ("V8+d0.075+csw", "V8 + 0.075 mm + SW capacitance", "V8 + 0.075 mm with 188.8 pF (the thinner layer adds 53.8 pF); compared with the row above", "V8", "A-m1-mid-d0.075-V8", "G-m1-mid-d0.075-V8", None),
]

NOT_IN_TABLE = [
    ("R80 gate-resistor swaps (1.2-1.5 ohm, with and without V8)", "Superseded: the owner's goals fix the parts list. Kept in results/gan/epc90133-search-G*.json and the design-round assessments."),
    ("Screens S1-S8 (filled return-plane slots)", "Invalid: the fills bonded non-GND vias to the ground plane (results/gan/epc90133-layout-screen.json)."),
    ("V6/V7/V8 run 1", "Defective builds (a thin slit per slot), replaced by revision 2; kept as *-run1-slit."),
    ("Added return vias (round 2b)", "Four legal additions changed screened loop inductance by -0.02 %; earlier additions damaged the power path."),
    ("L4a low-side driver return", "Inspected 9 October, not built: the low-side gate probe connection blocks a top-layer return."),
    ("L3b capacitors with their return vias", "Not built."),
    ("P1 Ci7 into the empty capacitor slot", "Rejected at build: the slot lies inside an EPC solder-mask opening, so the pad is not mask-defined (results/gan/epc90133-board-export-P1.json)."),
    ("Gate return with existing vias", "Not buildable: the probe connection (R22, J22, J2) encloses the driver's top-layer ground; K1 adds one via instead."),
]

# Goal columns: key, goal, label, metric, unit, scale, better ('lower', 'higher', None), digits
COLUMNS = [
    ("S1", "S1", "Peak voltage", "vpk_V", "V", 1, "lower", 1),
    ("S2", "S2", "Overshoot", "overshoot_V", "V", 1, "lower", 2),
    ("S3", "S3", "Settling", "settling_s", "ns", 1e9, "lower", 1),
    ("S4tr", "S4", "Rise time", "tr_s", "ns", 1e9, "lower", 2),
    ("S4tf", "S4", "Fall time", "tf_s", "ns", 1e9, "lower", 2),
    ("S5", "S5", "dv/dt", "dvdt_V_per_ns", "V/ns", 1, None, 1),
    ("S6i", "S6", "Q1 peak current", "id_peak_A", "A", 1, "lower", 1),
    ("S6d", "S6", "Q1 di/dt", "didt_A_per_ns", "A/ns", 1, "lower", 1),
    ("S7max", "S7", "Gate max", "vgs_max_V", "V", 1, "lower", 2),
    ("S7min", "S7", "Gate min", "vgs_min_V", "V", 1, "higher", 2),
    ("S8", "S8", "Q2 gate spike", "q2_gate_peak_V", "V", 1, "lower", 2),
    ("S10", "S10", "Eon + Eoff", "eon_eoff_J", "uJ", 1e6, "lower", 2),
    ("S12", "S12", "Efficiency (FET only)", "efficiency", "%", 100, "higher", 3),
]
TARGETS = {"S1": "<= 80 V", "S2": "<= 9.6 V and -10 % vs stock", "S3": "<= stock", "S4": "<= 1.1 x stock",
           "S5": "limit not set", "S6": "<= stock", "S7": "+5.5 / -3 V", "S8": "< 0.5 V", "S9": "Q2 spike < 0.8 V",
           "S10": "-10 % vs stock", "S11": "optimum 5-15 ns", "S12": "+0.3 points", "S13": "S1, S2, S7, S8 at corners"}


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def rel(p):
    return Path(p).resolve().relative_to(ROOT).as_posix()


def extraction(folder, stem):
    if not stem:
        return None
    p = EXPORT / folder / "extraction" / f"{stem}.json"
    if not p.is_file():
        return {"missing": rel(p)}
    d = load(p)
    s = d["summary"]
    out = {"source": rel(p), "outcome": d.get("outcome"),
           "L_loop_nH": s["L_loop_nH"], "R_loop_mohm": s["R_loop_mohm"]}
    for k in ("L_cs_Q1_pH", "L_cs_Q2_pH"):
        if k in s:
            out[k] = s[k]
    return out


def goals(assessments, cid):
    name = GOAL_NAME.get(cid, cid)
    for assessment in assessments:
        if Path(assessment).is_file() and name in load(assessment)["designs"]:
            break
    else:
        return None
    d = load(assessment)["designs"][name]
    out = {"verdict": d["verdict"], "all_met": d.get("all_met"), "source": rel(assessment), "values": {}}
    for a in PRIMARY:
        m = d["conditions"][a]["metrics"]
        out["values"][a] = None if m is None else {c[3]: m[c[3]] for c in COLUMNS}
    out["dead_time_optimum_ns"] = d.get("dead_time_optimum_ns")
    passed = total = 0
    for row in d["corners"].values():
        for x in row.values():
            if x["S1_S2_S7_S8"] is not None:
                total += 1
                passed += all(x["S1_S2_S7_S8"].values())
    out["corners"] = {"passed": passed, "usable": total, "declared": sum(len(r) for r in d["corners"].values())}
    return out


def build():
    rows = []
    for cid, label, what, folder, a_stem, g_stem, export in CANDIDATES:
        exp = None
        if export:
            e = load(RES / f"epc90133-board-export-{export}.json")
            exp = {"accepted": e.get("accepted"), "source": rel(RES / f"epc90133-board-export-{export}.json"),
                   "checks": {k: e[k].get("pass") for k in ("L1_drc", "L2_nets", "L3_power_loop", "L4_extraction")}}
        own = OWN_ASSESS.get(cid)
        rows.append({"id": cid, "label": label, "what": what, "board_export": exp, "ref": OWN_REF.get(cid),
                     "A": extraction(folder, a_stem), "G": extraction(folder, g_stem),
                     "goals": {m: goals(own.get(m, []) if own else p, cid) for m, p in ASSESS.items()}})
    return {"schema": "epc90133-candidates/1", "reference": "stock", "route_threshold": ROUTE_THRESHOLD,
            "primary_conditions": list(PRIMARY), "columns": COLUMNS, "targets": TARGETS,
            "not_in_table": NOT_IN_TABLE, "candidates": rows,
            "sources": {m: [rel(x) for x in ps + [y for o in OWN_ASSESS.values() for y in o.get(m, [])] if Path(x).is_file()]
                        for m, ps in ASSESS.items()}}


PAGE = r"""<title>EPC90133 Layout Candidates</title>
<style>
/* Layout: one dense comparison sheet; candidates down the side, parasitics then goals across, a sticky name column. */
:root {
  --bg: #f6f7f5; --panel: #ffffff; --ink: #1d2320; --muted: #5d6762; --rule: #d9ddda;
  --head: #eceeeb; --accent: #2f5d50;
  --good: #1f7a45; --good-bg: #d9f0e1; --good-pale: #eef8f1;
  --bad: #a3322b; --bad-bg: #f7dcd9; --bad-pale: #fbefed;
  --na: #8a938e; --shade: rgba(29, 35, 32, 0.16);
  --sans: "IBM Plex Sans", system-ui, sans-serif; --mono: "IBM Plex Mono", ui-monospace, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #141816; --panel: #1b201d; --ink: #e5eae6; --muted: #9aa49f; --rule: #2f3632; --head: #222824; --accent: #8fc1b0;
  --good: #7fd6a0; --good-bg: #1e3d2a; --good-pale: #18291f; --bad: #f09a92; --bad-bg: #462421; --bad-pale: #2c1c1a; --na: #6f7873; --shade: rgba(0, 0, 0, 0.45);
  color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #141816; --panel: #1b201d; --ink: #e5eae6; --muted: #9aa49f; --rule: #2f3632; --head: #222824; --accent: #8fc1b0;
  --good: #7fd6a0; --good-bg: #1e3d2a; --good-pale: #18291f; --bad: #f09a92; --bad-bg: #462421; --bad-pale: #2c1c1a; --na: #6f7873; --shade: rgba(0, 0, 0, 0.45);
  color-scheme: dark }
body { background: var(--bg); color: var(--ink); font-family: var(--sans); font-size: 14px; }
main { padding-block: 28px 48px; padding-inline: 16px; max-width: 1500px; margin: 0 auto; display: grid; gap: 20px; }
h1 { font-size: 22px; margin: 0; text-wrap: balance; letter-spacing: -0.01em; }
h2 { font-size: 15px; margin: 0 0 8px; }
p { margin: 0; line-height: 1.5; max-width: 75ch; color: var(--muted); }
.top { display: flex; flex-wrap: wrap; gap: 12px 24px; align-items: end; justify-content: space-between; }
.meta { font-family: var(--mono); font-size: 12px; color: var(--muted); }
.controls { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.seg { display: inline-flex; border: 1px solid var(--rule); border-radius: 6px; overflow: hidden; background: var(--panel); }
.seg button { font: inherit; font-size: 13px; padding: 6px 12px; border: 0; background: transparent; color: var(--muted); cursor: pointer; }
.seg button[aria-pressed="true"] { background: var(--accent); color: var(--bg); }
.seg button:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 14px; font-size: 12px; color: var(--muted); align-items: center; }
.sw { display: inline-block; width: 12px; height: 12px; border-radius: 2px; vertical-align: -2px; margin-right: 4px; }
.sheet { display: grid; gap: 8px; min-width: 0; }
.nav { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; position: sticky; top: env(safe-area-inset-top, 0px); z-index: 5; background: var(--bg); padding-block: 6px; }
.nav button { font: inherit; font-size: 12px; padding: 4px 9px; border: 1px solid var(--rule); border-radius: 5px; background: var(--panel); color: var(--ink); cursor: pointer; }
.nav button:hover { border-color: var(--accent); }
.nav button.on { background: var(--accent); border-color: var(--accent); color: var(--bg); }
.nav button:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.nav .arrow { font-size: 14px; padding: 2px 10px; }
.nav .hint { margin-left: auto; font-size: 11.5px; color: var(--muted); }
.frame { position: relative; min-width: 0; }
.wrap { overflow: auto; max-height: calc(100dvh - 120px); min-height: 320px; background: var(--panel); border: 1px solid var(--rule); border-radius: 8px;
  scrollbar-width: auto; scrollbar-color: var(--muted) var(--head); cursor: grab; overscroll-behavior-x: contain; }
.wrap:focus-visible { outline: 2px solid var(--accent); }
.wrap.drag { cursor: grabbing; user-select: none; }
.wrap::-webkit-scrollbar { height: 14px; width: 12px; }
.wrap::-webkit-scrollbar-track { background: var(--head); }
.wrap::-webkit-scrollbar-thumb { background: var(--muted); border-radius: 7px; border: 3px solid var(--head); }
.fade { position: absolute; top: 1px; bottom: 15px; width: 28px; pointer-events: none; opacity: 0; transition: opacity .15s; z-index: 4; }
.fade.r { right: 13px; background: linear-gradient(to left, var(--shade), transparent); }
.fade.l { left: 186px; background: linear-gradient(to right, var(--shade), transparent); }
.fade.show { opacity: 1; }
table { border-collapse: separate; border-spacing: 0; font-variant-numeric: tabular-nums; font-size: 12.5px; }
th, td { border-bottom: 1px solid var(--rule); border-right: 1px solid var(--rule); padding: 6px 8px; text-align: right; white-space: nowrap; vertical-align: top; }
thead th { background: var(--head); font-weight: 600; position: sticky; top: 0; z-index: 2; }
thead tr.sub th { top: var(--grp-h, 0px); }
thead tr.grp th { text-align: center; font-size: 11px; letter-spacing: 0.04em; text-transform: uppercase; color: var(--muted); }
thead tr.sub th { font-weight: 500; }
thead .tgt { display: block; font-weight: 400; font-size: 10.5px; color: var(--muted); }
th.name, td.name { position: sticky; left: 0; z-index: 1; background: var(--panel); text-align: left; min-width: 170px; white-space: normal; }
thead th.name { z-index: 3; background: var(--head); }
td.name b { display: block; font-size: 13px; }
td.name small { color: var(--muted); font-size: 11px; line-height: 1.35; display: block; max-width: 220px; }
tr.ref td { font-weight: 600; }
tr.sens td { border-top: 2px solid var(--rule); }
.v { display: block; font-family: var(--mono); font-size: 12px; padding: 1px 4px; border-radius: 3px; }
.v small { font-family: var(--sans); font-size: 10.5px; opacity: 0.85; margin-left: 4px; }
.good { background: var(--good-bg); color: var(--good); }
.bad { background: var(--bad-bg); color: var(--bad); }
.good.pale { background: var(--good-pale); }
.bad.pale { background: var(--bad-pale); }
.na { color: var(--na); font-family: var(--sans); font-size: 11px; }
.chip { display: inline-block; font-family: var(--sans); font-size: 10.5px; padding: 0 6px; border-radius: 9px; border: 1px solid currentColor; margin-top: 2px; }
.chip.met { color: var(--good); } .chip.not { color: var(--bad); } .chip.und { color: var(--na); }
.lbl { color: var(--muted); font-size: 10.5px; margin-right: 3px; font-family: var(--sans); }
.cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }
.card { background: var(--panel); border: 1px solid var(--rule); border-radius: 8px; padding: 14px 16px; min-width: 0; }
.card ul { margin: 0; padding-left: 18px; display: grid; gap: 6px; line-height: 1.45; }
.card li span { color: var(--muted); }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>
<main>
  <div class="top">
    <div style="display:grid;gap:6px;min-width:0">
      <h1>EPC90133 layout candidates</h1>
      <p>Every built candidate against stock, through the same KiCad route. Extracted parasitics come from variant A (partial board, used for ranking) and variant G (full board with gate paths). Goal values use the assumed 50 pH package inductance and show both driver models as <b>ramp / step</b>. Simulation results only, not hardware limits.</p>
    </div>
    <div class="controls">
      <span class="lbl">Goal values from</span>
      <div class="seg" role="group" aria-label="Transistor model">
        <button type="button" id="m-vendor" data-model="vendor" aria-pressed="true">Vendor model (primary)</button>
        <button type="button" id="m-ds" data-model="EPC2302DS" aria-pressed="false">EPC2302DS</button>
      </div>
    </div>
  </div>
  <div class="legend">
    <span><i class="sw good"></i>better than stock</span>
    <span><i class="sw bad"></i>worse than stock</span>
    <span><i class="sw good pale"></i><i class="sw bad pale"></i>extraction change below the 4 % route threshold</span>
    <span><span class="chip met">met</span> <span class="chip not">not met</span> <span class="chip und">undetermined</span> goal verdict (both drivers)</span>
    <span class="meta" id="gen"></span>
  </div>
  <div class="sheet">
    <div class="nav" id="nav" aria-label="Jump to columns">
      <button type="button" class="arrow" id="prev" aria-label="Scroll left">&#8592;</button>
      <button type="button" class="arrow" id="next" aria-label="Scroll right">&#8594;</button>
      <span id="jumps" style="display:contents"></span>
      <span class="hint">Drag the table, use the arrows, or Shift + scroll wheel</span>
    </div>
    <div class="frame"><div class="wrap" id="wrap" tabindex="0" aria-label="Candidate table"><table id="t"></table></div>
      <div class="fade l" id="fl"></div><div class="fade r" id="fr"></div></div>
  </div>
  <div class="cols">
    <div class="card"><h2>How to read it</h2><ul>
      <li>Percentages are the change from stock in the same column. Lower inductance and resistance are shown as better; lower inductance also raises switching energy (S10) and current slope (S6) in this model.</li>
      <li>Lower common-source inductance (L<sub>cs</sub>) means less gate disturbance; on the high side, coupling into the gate path also slows the edge, which lowers overshoot.</li>
      <li>Goal columns are blank where a candidate has no switching run. Stock and V8 have full goal runs; V8 + 0.075 mm has its corners, but its two main cases ran past the 1-hour limit, so most of its goals are undetermined.</li>
      <li>The last two rows add the switch-node capacitance that the thinner layer raises; V8 + 0.075 mm is compared there with stock under the same addition. Corners and dead time were not run for them.</li>
      <li>S9 and S11 are verdicts on derived quantities; S13 counts corner runs (40/60 V, no load, parasitics ±10 %, both drivers) that keep S1, S2, S7 and S8.</li>
      <li>Hover a value to see the saved report it comes from.</li>
    </ul></div>
    <div class="card"><h2>Not in this table</h2><ul id="notin"></ul></div>
  </div>
</main>
<script>
const DATA = __DATA__;
const $ = (s) => document.querySelector(s);
let model = "vendor";
try { const m = localStorage.getItem("cand-model-v2"); if (m === "vendor" || m === "EPC2302DS") model = m; } catch (e) {}
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
function cmp(v, r, better, pale) {
  if (v == null || r == null || better == null || r === 0) return { cls: "", pct: null };
  const d = v / r - 1;
  if (Math.abs(d) < 1e-9) return { cls: "", pct: 0 };
  const good = better === "lower" ? d < 0 : d > 0;
  return { cls: (good ? "good" : "bad") + (pale && Math.abs(d) < DATA.route_threshold ? " pale" : ""), pct: d };
}
function cell(v, r, better, digits, src, pale, isRef) {
  if (v == null) return '<span class="na">–</span>';
  const c = isRef ? { cls: "", pct: null } : cmp(v, r, better, pale);
  const pct = c.pct == null ? "" : `<small>${c.pct > 0 ? "+" : ""}${(c.pct * 100).toFixed(1)} %</small>`;
  return `<span class="v ${c.cls}" title="${esc(src)}">${v.toFixed(digits)}${pct}</span>`;
}
function chip(v) {
  if (v === true) return '<span class="chip met">met</span>';
  if (v === false) return '<span class="chip not">not met</span>';
  return '<span class="chip und">undetermined</span>';
}
const PAR = [
  ["A", "L_loop_nH", "A loop L", "nH", 4, true], ["A", "R_loop_mohm", "A loop R", "mΩ", 3, true],
  ["G", "L_loop_nH", "G loop L", "nH", 4, true], ["G", "R_loop_mohm", "G loop R", "mΩ", 3, true],
  ["G", "L_cs_Q1_pH", "L<sub>cs</sub> Q1", "pH", 1, true], ["G", "L_cs_Q2_pH", "L<sub>cs</sub> Q2", "pH", 1, true]];
function render() {
  document.querySelectorAll(".seg button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.model === model)));
  const cols = DATA.columns;
  const groups = []; cols.forEach((c) => { const g = groups[groups.length - 1]; if (g && g.goal === c[1]) g.n++; else groups.push({ goal: c[1], n: 1 }); });
  const order = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10", "S11", "S12", "S13"];
  let h = '<thead><tr class="grp"><th class="name" rowspan="2">Candidate</th><th colspan="1" rowspan="2">Build</th><th colspan="6" data-jump="Parasitics">Extracted parasitics</th>';
  const subs = [];
  order.forEach((g) => {
    const cs = cols.filter((c) => c[1] === g);
    const n = Math.max(cs.length, 1);
    h += `<th colspan="${n}" data-jump="${g}">${g}<span class="tgt">${esc(DATA.targets[g])}</span></th>`;
    if (cs.length) cs.forEach((c) => subs.push(`<th>${esc(c[2])}<span class="tgt">${esc(c[4])}</span></th>`));
    else subs.push(`<th>${g === "S9" ? "Shoot-through" : g === "S11" ? "Best dead time" : "Corners kept"}<span class="tgt">${g === "S11" ? "ns" : g === "S13" ? "count" : "verdict"}</span></th>`);
  });
  h += '</tr><tr class="sub">' + PAR.map((p) => `<th>${p[2]}<span class="tgt">${p[3]}</span></th>`).join("") + subs.join("") + "</tr></thead><tbody>";
  for (const c of DATA.candidates) {
    const isRef = c.id === (c.ref || DATA.reference);
    const ref = DATA.candidates.find((x) => x.id === (c.ref || DATA.reference));
    const ex = c.board_export;
    const build = isRef ? '<span class="na">reference</span>' : ex ? (ex.accepted ? '<span class="chip met" title="' + esc(ex.source) + '">legal</span>' : '<span class="chip not">rejected</span>') : '<span class="na" title="stackup change only">stackup</span>';
    h += `<tr class="${isRef ? "ref" : ""}${c.ref ? " sens" : ""}"><td class="name"><b>${esc(c.label)}</b><small>${esc(c.what)}</small></td><td>${build}</td>`;
    for (const [v, k, , , dg, pale] of PAR) {
      const x = c[v], rx = ref[v];
      h += `<td>${x && !x.missing ? cell(x[k], rx && rx[k], "lower", dg, x.source, pale, isRef) : '<span class="na">' + (x && x.missing ? "file missing" : "not run") + "</span>"}</td>`;
    }
    const g = c.goals[model], rg = ref.goals[model];
    order.forEach((goal) => {
      const cs = cols.filter((col) => col[1] === goal);
      const verdict = g ? chip(g.verdict[goal]) : "";
      if (!g) { h += `<td colspan="${Math.max(cs.length, 1)}"><span class="na">no switching run</span></td>`; return; }
      if (!cs.length) {
        let body = "";
        if (goal === "S11") body = cell(g.dead_time_optimum_ns, rg && rg.dead_time_optimum_ns, null, 1, g.source, false, true);
        if (goal === "S13") body = `<span class="v" title="${esc(g.source)}">${g.corners.passed} / ${g.corners.usable}${g.corners.usable < g.corners.declared ? " <small>(" + (g.corners.declared - g.corners.usable) + " stalled)</small>" : ""}</span>`;
        h += `<td>${body}${verdict}</td>`; return;
      }
      cs.forEach((col, i) => {
        const [, , , key, , scale, better, dg] = col;
        const parts = DATA.primary_conditions.map((a) => {
          const v = g.values[a] && g.values[a][key], r = rg && rg.values[a] && rg.values[a][key];
          return `<span class="lbl">${a.split("-")[0]}</span>` + cell(v == null ? null : v * scale, r == null ? null : r * scale, better, dg, g.source + " · " + a, false, isRef);
        });
        h += `<td>${parts.join("")}${i === cs.length - 1 ? verdict : ""}</td>`;
      });
    });
    h += "</tr>";
  }
  $("#t").innerHTML = h + "</tbody>";
  layout();
}
const wrap = $("#wrap");
const nameW = () => (document.querySelector("th.name") || { offsetWidth: 0 }).offsetWidth;
const smooth = () => (matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth");
function layout() {
  const grp = document.querySelector("thead tr.grp");
  if (grp) wrap.style.setProperty("--grp-h", grp.getBoundingClientRect().height + "px");
  $("#fl").style.left = nameW() + 1 + "px";
  $("#jumps").innerHTML = [...document.querySelectorAll("th[data-jump]")]
    .map((th) => `<button type="button" data-to="${th.dataset.jump}">${th.dataset.jump}</button>`).join("");
  document.querySelectorAll("#jumps button").forEach((b) => b.addEventListener("click", () => {
    const th = document.querySelector(`th[data-jump="${b.dataset.to}"]`);
    wrap.scrollTo({ left: th.offsetLeft - nameW(), behavior: smooth() });
  }));
  edges();
}
function edges() {
  const max = wrap.scrollWidth - wrap.clientWidth;
  $("#fl").classList.toggle("show", wrap.scrollLeft > 2);
  $("#fr").classList.toggle("show", wrap.scrollLeft < max - 2);
  const x = wrap.scrollLeft + nameW() + 4;
  let cur = null;
  document.querySelectorAll("th[data-jump]").forEach((th) => { if (th.offsetLeft <= x) cur = th.dataset.jump; });
  document.querySelectorAll("#jumps button").forEach((b) => b.classList.toggle("on", b.dataset.to === cur));
}
wrap.addEventListener("scroll", edges, { passive: true });
addEventListener("resize", layout);
const page = (dir) => wrap.scrollBy({ left: dir * (wrap.clientWidth - nameW()) * 0.8, behavior: smooth() });
$("#prev").addEventListener("click", () => page(-1));
$("#next").addEventListener("click", () => page(1));
wrap.addEventListener("keydown", (e) => {
  if (e.key === "ArrowRight") { page(1); e.preventDefault(); }
  if (e.key === "ArrowLeft") { page(-1); e.preventDefault(); }
});
let drag = null;
wrap.addEventListener("pointerdown", (e) => {
  if (e.pointerType !== "mouse" || e.button !== 0) return;
  drag = { x: e.clientX, y: e.clientY, l: wrap.scrollLeft, t: wrap.scrollTop, moved: false };
});
addEventListener("pointermove", (e) => {
  if (!drag) return;
  const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
  if (!drag.moved && Math.hypot(dx, dy) < 4) return;
  drag.moved = true; wrap.classList.add("drag");
  wrap.scrollLeft = drag.l - dx; wrap.scrollTop = drag.t - dy;
});
addEventListener("pointerup", () => { drag = null; wrap.classList.remove("drag"); });
document.querySelectorAll(".seg button").forEach((b) => b.addEventListener("click", () => {
  model = b.dataset.model; try { localStorage.setItem("cand-model-v2", model); } catch (e) {} render();
}));
$("#notin").innerHTML = DATA.not_in_table.map(([a, b]) => `<li><b>${esc(a)}</b><br><span>${esc(b)}</span></li>`).join("");
$("#gen").textContent = "Generated " + DATA.generated + " from saved results";
render();
</script>
"""


def main():
    import datetime
    data = build()
    data["generated"] = datetime.date.today().isoformat()
    (RES / "epc90133-candidates.json").write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    page = PAGE.replace("__DATA__", json.dumps(data).replace("</", "<\\/"))
    (ROOT / "epc90133-candidates.html").write_text(page, encoding="utf-8")
    for r in data["candidates"]:
        a, g = r["A"], r["G"]
        print(f"{r['id']:10s} A {a and a.get('L_loop_nH')}  G {g and g.get('L_loop_nH')}  goals "
              f"{ {m: bool(v) for m, v in r['goals'].items()} }")


if __name__ == "__main__":
    main()
