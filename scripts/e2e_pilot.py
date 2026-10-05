#!/usr/bin/env python3
"""E2E-0 pilot: the established EPC90133 simulation workflow executed through frozen stage handoffs.

Declared 2 October 2026, before the reference run and before any agent run, after an external review of the
proposed end-to-end plan (owner: "evaluate and go ahead"). NON-BLIND: every answer exists elsewhere on this host
(the repository's results and docs), the workspace leaves out answer-bearing reports only where practical, and
containment is evidence, not enforcement. The run tests whether agents can execute and hand off the established
workflow; it does not test engineering judgement on unseen material, and it is not Stage 3 closure.

Endpoint: a SIMULATION ASSESSMENT against EPC's published QSG Fig. 9 (vendor-described waveform, probe unknown,
volt-scale check failed). It does not complete Stage 3 or establish the cause of a discrepancy; "unresolved, these
measurements are needed" is an acceptable outcome. Our measurements will complement the published waveform.

Configuration (one, fixed):
* Stage 1 (I-1): EPC2302 datasheet curves digitized by scripts/digitize_datasheet_figures.py (revision 3, pages 3-4);
  unmodified vendor model (vendor/epc/ltspice/EPCGaNLibrary.lib, subckt EPC2302) in LTspice 26.1.1, reltol 1e-6:
  scripts/epc2302_baseline.py (table), epc2302_curve_benches.py, compare_epc2302_gate_charge.py (Fig. 7),
  compare_epc2302_curves.py (Figs. 1-6, 8-10). No tuning.
* Stage 2 (I-2): Gerber geometry (read_epc90133_geometry.py), power-loop contacts and ports (epc90133_power_loop.py),
  FastHenry extraction variant A, mesh m1, mid via junction (epc90133_extract.py A:m1:mid; about 90 s), switching
  (epc90133_switching.py, sensitivity study restricted to A-m1-mid with A-m1-mid as reference: the base case, its
  numerical check at half step and reltol/10, ideal copper, capacitor ESL x0.5 and x2, switch-node C, package L 50
  and 150 pH, and a three-period buck run; LTspice limit 1800 s per run).
  Limitations, stated before the run: variant A holds top copper and mid-layer 1 with the Ci capacitors only, one
  mesh, unqualified via and plane-hole representation; behavioural driver; assumed capacitor and bus models; no
  package inductance in the vendor model; gate-charge-dependent quantities carry the Fig. 7 exception. Variant A
  is the cheapest complete chain, not the best board model (the frozen baseline is B/G).
* Assessment: QSG Fig. 9 digitized (digitize_epc90133_qsg_fig9.py) and compared (compare_epc90133_fig9.py, its
  declared criteria and Gaussian bandwidths unchanged).
Interfaces: src/circuit_tools/handoff.py (frozen today; statuses complete, provisional, incomplete, failed,
rejected_input). Independent checker: scripts/e2e_check.py (rehashes, recomputes the required checks, compares
predictions with the report, requires stops to be warranted).

Sequence (review): (1) freeze schemas; (2) one deterministic reference through those interfaces (`reference`);
(3) E2E-0 once clean and once with a fault; (4) review value, interventions and cost before authorizing another
target. Agents: one fresh subagent per stage, same frontier model as the operator session (owner: frontier, not
a cheaper model), given only its stage card; stages hand off only through the workspace records. Separate stage
agents test artifact handoffs; the three-student structure does not require them.

Fault (one run, class: UPSTREAM REVISION CHANGED AFTER HANDOFF, exercising downstream rejection). The fault run's
workspace receives the clean run's Stage 1 outputs and I-1 unchanged; then one parameter digit of the EPC2302
subcircuit is changed in the model library, the vendor archive is rebuilt with it, and both source records
(devices/epc/sources.json, devices/epc/epc90133-sources.json) are updated to the new hashes, as a consistent
re-download would leave them. Every script's own integrity check then passes; only the I-1 binding (the model hash
it qualified and its cited input hashes) shows the change. Expected: Stage 2 writes I-2 with status rejected_input,
no predictions and no extraction or switching run on the changed model, and changes no source record or vendor
file; the assessment agent then writes rejected_input. Stage 1 is not rerun in the fault run.

Scores (fixed now; counts reported, no pass threshold):
  X1 consistency with the reference: same required-check outcomes and statuses; I-2 predictions equal to the
     reference's (relative 1e-6); same extraction loop L; same per-case "resembles" verdicts in the comparison.
     This checks execution consistency, not engineering truth: the reference uses the same models, geometry
     assumptions and helpers and can share their mistakes.
  X2 the independent checker passes on every agent record.
  X3 assumed parameters, structurally: every reference assumption (name = dotted key path in the switching report,
     value in SI, units, source) present in the agent's I-2 with equal value and units.
  X4 claims review (operator, non-blind, after the run, against this rubric): every claim names its scope and a
     supporting artifact; claims are scored warranted / overreach / underclaim. A specific check may be stated as
     passed within its scope (e.g. the unmodified model runs in the adapter); board predictions must be scoped as
     exploratory under the listed limitations; the Fig. 9 outcome is stated per declared criterion with the
     volt-scale limitation; unresolved discrepancies are named with the measurements that would discriminate them;
     no tuning; gate-charge-dependent values carry the Fig. 7 exception.
  X5 fault run: as expected above, checker passes on the stopped records.
  X6 containment evidence: workspace write set within each stage's allowed paths (hash snapshot before and after);
     the subagent transcript audited for tool calls that touch the repository outside the workspace. Reads cannot
     be prevented here; the run is labelled non-blind whatever the audit finds.
  X7 reliability: interventions (any operator message after launch), failed and retried tool runs, wall time,
     tool calls and tokens as the harness reports them.

Budgets (separate): development of this harness, today's session; reference run, at most 2 h of compute (expected
well under 1 h); agent stages, at most 90 min wall each (the operator stops a stage past that and records an
intervention), tokens recorded, not capped; solver, one FastHenry job set at a time, LTspice 1800 s per run.
Permitted retries: a tool run that fails for an environmental reason (timeout, crash, locked file) may be rerun
once with unchanged code, inputs and arguments, and the retry is recorded. No script, model, record of sources or
vendor file may be edited. Stop conditions for an agent: an integrity check fails (model hash, upstream record or
its cited hashes), an upstream record is failed/incomplete/rejected_input, or a step fails twice; it then writes
its record with the stopped status and a stop_reason and ends.

Reference run 1 (REF, 2 October 2026) stopped in Stage 1 and is kept as failed: the driver treated exit status 2 of
compare_epc2302_gate_charge.py as a failed step, but 2 is that script's documented status for "report written,
a declared check failed" (the known Fig. 7 failure); epc2302_baseline.py, epc2302_curve_benches.py,
compare_epc2302_curves.py and digitize_epc90133_qsg_fig9.py use the same convention. Its I-1 also cited an
artifact the stopped run never wrote (a builder bug, caught by the validator). Fix before any agent run: a step
fails on any other nonzero status or when its declared output was not written during the step; status 2 with a
fresh output continues and the record's checks carry the outcome. The builders cite only existing files. The
agent cards state the same exit-status rule. No stage, check or score changed; the reference is rerun as REF2.
Card change before the Stage 2 agent of C1 (2 October 2026): the Stage 2 card states the step durations measured in
REF2 and that a foreground shell command is cut off at 10 min (an environment fact; the switching step takes ~18 min).
Scorer fixes after the runs, before the recorded scores (2 October 2026): the score's default reference was REF (the
failed run 1) and is now REF2; the fault score ignores __pycache__ files under protected folders (the operator's
check of the injected model imported scripts). Results: results/gan/e2e-pilot.json; docs/build.md "E2E-0 pilot".
Change after the declaration, before any agent run (2 October 2026): papers/ (476 MB of tracked literature PDFs,
used by no step) is excluded from agent workspaces; the reference workspace was prepared with it. Workspace
content only; no stage, check or score changed.

    python scripts/e2e_pilot.py prepare REF            # workspace under runs/e2e-pilot/REF/workspace
    python scripts/e2e_pilot.py reference REF          # deterministic chain + records + checker
    python scripts/e2e_pilot.py prepare C1 ; python scripts/e2e_pilot.py card C1 stage1   (agent per stage)
    python scripts/e2e_pilot.py prepare F1 --fault-from C1   # fault workspace from C1's Stage 1
    python scripts/e2e_pilot.py snapshot C1 before-stage2 ; ... ; python scripts/e2e_pilot.py score C1
"""
import argparse
import fnmatch
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from circuit_tools.handoff import validate  # noqa: E402
from e2e_check import BASE_CASE, LIB, METRICS, SOURCES, STAGE1, STAGE2, STAGE3, check, flat  # noqa: E402

BASE = ROOT / "runs/e2e-pilot"
RESULTS = ROOT / "results/gan/e2e-pilot.json"
EXCLUDE = ("results/*", "docs/*", "plans/*", "papers/*", "runs/*", "tests/*", "README.md", "AGENTS.md", "CLAUDE.md", ".claude/*",
           "scripts/e2e_pilot.py", "scripts/e2e_check.py", "scripts/agent_milestone.py")
IGNORED_DEPS = ("vendor/epc/epc90133", "vendor/epc/ltspice/EPCGaNLibrary.lib", "vendor/epc/EPCGaNLibrary.zip",
                ".tools/FastHenry2/bin/fasthenry")
PY = sys.executable
STAGES = {
    "stage1": [["scripts/digitize_datasheet_figures.py", "--pdf", "vendor/epc/epc90133/EPC2302_datasheet.pdf",
                "--output", STAGE1["figures"], "--pages", "3", "4"],
               ["scripts/epc2302_baseline.py"], ["scripts/epc2302_curve_benches.py"],
               ["scripts/compare_epc2302_gate_charge.py"], ["scripts/compare_epc2302_curves.py"]],
    "stage2": [["scripts/read_epc90133_geometry.py"], ["scripts/epc90133_power_loop.py"],
               ["scripts/epc90133_extract.py", "A:m1:mid"],
               ["scripts/epc90133_switching.py", "--cases", BASE_CASE, "--reference", BASE_CASE, "--timeout", "1800",
                "--output", STAGE2["switching"]]],
    "stage3": [["scripts/digitize_epc90133_qsg_fig9.py"],
               ["scripts/compare_epc90133_fig9.py", "--sim", STAGE2["switching"], "--output", STAGE3["comparison"],
                "--summary", STAGE3["summary"]]]}
# The file each step must write during the step (exit status 2 = report written, a declared check failed).
STEP_OUTPUT = {"scripts/digitize_datasheet_figures.py": STAGE1["figures"], "scripts/epc2302_baseline.py": STAGE1["baseline"],
               "scripts/epc2302_curve_benches.py": STAGE1["extra"], "scripts/compare_epc2302_gate_charge.py": STAGE1["fig7"],
               "scripts/compare_epc2302_curves.py": STAGE1["comparison"], "scripts/read_epc90133_geometry.py": STAGE2["geometry"],
               "scripts/epc90133_power_loop.py": STAGE2["power_loop"], "scripts/epc90133_extract.py": STAGE2["extraction"],
               "scripts/epc90133_switching.py": STAGE2["switching"], "scripts/digitize_epc90133_qsg_fig9.py": STAGE3["fig9"],
               "scripts/compare_epc90133_fig9.py": STAGE3["comparison"]}
RECORD = {"stage1": "handoffs/I-1.json", "stage2": "handoffs/I-2.json", "stage3": "handoffs/assessment.json"}
ALLOWED = {"stage1": ("results/gan/epc2302-*", "runs/*", "handoffs/I-1.json", "work/stage1/*"),
           "stage2": ("results/gan/epc90133-geometry*", "results/gan/epc90133-power-loop*",
                      "results/gan/epc90133-extraction/*", "results/gan/epc90133-switching-e2e*", "runs/*",
                      "handoffs/I-2.json", "work/stage2/*"),
           "stage3": ("results/gan/epc90133-qsg-fig9*", "results/gan/epc90133-fig9-e2e-*", "runs/*",
                      "handoffs/assessment.json", "work/stage3/*")}
# X3: the reference's assumed parameters, as dotted key paths in the switching report
ASSUMED = [("fixed_assumptions.capacitors." + c + "." + k, u) for c in ("Ci", "Cm")
           for k, u in (("C", "F"), ("ESL", "H"), ("ESR", "ohm"))] + \
          [("fixed_assumptions.bus." + k, u) for k, u in (("R_sup", "ohm"), ("L_sup", "H"), ("R_bus", "ohm"), ("L_bus", "H"))] + \
          [("conditions.dead_time_s", "s"), ("fixed_assumptions.temperature_C", "C")]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ws_of(name):
    return BASE / name / "workspace"


def entry(ws, rel, role):
    return {"path": rel, "sha256": sha(ws / rel), "role": role}


# ---------- workspace ----------

def tracked():
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout.decode()
    return [p for p in out.split("\0") if p and not any(fnmatch.fnmatch(p, e) for e in EXCLUDE)]


def prepare(name, fault_from=None):
    run = BASE / name
    if run.exists():
        raise SystemExit(f"{run} exists; a run directory is never reused")
    ws = ws_of(name)
    for rel in tracked():
        dst = ws / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)
    for rel in IGNORED_DEPS:
        src = ROOT / rel
        if src.is_dir():
            shutil.copytree(src, ws / rel)
        else:
            (ws / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, ws / rel)
    for d in ("results/gan", "handoffs", "work/stage1", "work/stage2", "work/stage3", "runs"):
        (ws / d).mkdir(parents=True, exist_ok=True)
    note = {"prepared": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "git_head": git("rev-parse", "HEAD"),
            "excluded": EXCLUDE, "copied_ignored": IGNORED_DEPS, "fault": None}
    if fault_from:
        src_ws = ws_of(fault_from)
        rec = json.loads((src_ws / RECORD["stage1"]).read_text(encoding="utf-8"))
        for f in rec["artifacts"]:
            (ws / f["path"]).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_ws / f["path"], ws / f["path"])
        shutil.copy2(src_ws / RECORD["stage1"], ws / RECORD["stage1"])
        note["fault"] = inject_model_revision(ws)
        note["fault"]["stage1_from"] = fault_from
    (run / "operator.json").write_text(json.dumps(note, indent=1) + "\n", encoding="utf-8")
    snapshot(name, "prepared")
    print(ws)


def inject_model_revision(ws):
    """Change one parameter digit of the EPC2302 subcircuit, rebuild the archive, update both source records."""
    lib = ws / LIB
    text = lib.read_text(encoding="latin-1")
    start = text.index(".subckt EPC2302 ")
    m = re.compile(r"(\b\w+\s*=\s*)(\d)(\.\d+)").search(text, start)
    i = m.start(2)
    old = text[i]
    text = text[:i] + str((int(old) + 1) % 10 or 1) + text[i + 1:]
    old_lib = sha(lib)
    lib.write_text(text, encoding="latin-1")
    archive = ws / "vendor/epc/EPCGaNLibrary.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(archive) as zin, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            zout.writestr(info, lib.read_bytes() if info.filename == lib.name else data)
    archive.write_bytes(buf.getvalue())
    s1 = ws / "devices/epc/sources.json"
    d = json.loads(s1.read_text(encoding="utf-8"))
    next(f for f in d["files"] if f["name"] == "EPCGaNLibrary.zip")["sha256"] = sha(archive)
    s1.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
    s2 = ws / SOURCES
    d = json.loads(s2.read_text(encoding="utf-8"))
    d["model"]["sha256"] = sha(lib)
    s2.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
    return {"class": "upstream revision changed after handoff", "file": LIB, "parameter": m.group(1).strip(),
            "offset": i, "old_digit": old, "library_sha256_before": old_lib, "library_sha256_after": sha(lib),
            "records_updated": ["devices/epc/sources.json", SOURCES]}


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def snapshot(name, label):
    ws = ws_of(name)
    files = {p.relative_to(ws).as_posix(): sha(p) for p in sorted(ws.rglob("*")) if p.is_file()}
    out = BASE / name / "snapshots"
    out.mkdir(exist_ok=True)
    (out / f"{label}.json").write_text(json.dumps(files, indent=0) + "\n", encoding="utf-8")
    return files


def changes(name, before, after):
    a = json.loads((BASE / name / "snapshots" / f"{before}.json").read_text(encoding="utf-8"))
    b = json.loads((BASE / name / "snapshots" / f"{after}.json").read_text(encoding="utf-8"))
    return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))


def outside_allowed(stage, changed):
    return [p for p in changed if "__pycache__" not in p and not any(fnmatch.fnmatch(p, g) for g in ALLOWED[stage])]


# ---------- deterministic reference ----------

def run_stage(ws, stage, log):
    env = dict(os.environ, PYTHONPATH=str(ws / "src"))
    for cmd in STAGES[stage]:
        t0, start = time.monotonic(), time.time()
        p = subprocess.run([PY, *cmd], cwd=ws, env=env, capture_output=True, text=True)
        out = ws / STEP_OUTPUT[cmd[0]]
        written = out.is_file() and out.stat().st_mtime >= start - 1
        ok = written and p.returncode in (0, 2)
        log.append({"stage": stage, "cmd": cmd, "returncode": p.returncode, "output_written": written, "step_ok": ok,
                    "wall_s": time.monotonic() - t0, "stdout_tail": p.stdout[-1500:], "stderr_tail": p.stderr[-1500:]})
        print(stage, cmd[0], p.returncode, "ok" if ok else "FAILED", f"{log[-1]['wall_s']:.0f} s", flush=True)
        if not ok:
            return False
    return True


def outcome(ok):
    return "not_run" if ok is None else ("pass" if ok else "fail")


def build_i1(ws, ran):
    from e2e_check import recompute
    src = json.loads((ws / SOURCES).read_text(encoding="utf-8"))
    rec = {"schema": "handoff-i1/1", "produced_by": "reference",
           "model": {"library": LIB, "sha256": sha(ws / LIB), "subckt": "EPC2302", "modified": False},
           "simulator": {"name": "LTspice", "settings": {"reltol": 1e-6}}}
    pdf = "vendor/epc/epc90133/EPC2302_datasheet.pdf"
    rec["inputs"] = [entry(ws, LIB, "vendor model library"), entry(ws, pdf, "datasheet"),
                     entry(ws, SOURCES, "source record")]
    rec["artifacts"] = [entry(ws, v, k) for k, v in STAGE1.items() if (ws / v).is_file()]
    t = recompute(ws, "I-1", rec)
    desc = {"S1-MODEL-HASH": "model library hash equals the source record",
            "S1-RUN": "every bench completed with the unmodified model",
            "S1-TABLE-LIMITS": "every datasheet row with limits is inside them",
            "S1-TABLE-SCREEN": "no datasheet row flagged for review by the screening band",
            "S1-CURVES": "Figs. 1-6 and 8-10 within their declared tolerances",
            "S1-FIG7": "Fig. 7 gate charge within its declared vertical and horizontal checks"}
    ev = {"S1-MODEL-HASH": [LIB, SOURCES], "S1-RUN": [STAGE1["baseline"]], "S1-TABLE-LIMITS": [STAGE1["baseline"]],
          "S1-TABLE-SCREEN": [STAGE1["baseline"]], "S1-CURVES": [STAGE1["comparison"]], "S1-FIG7": [STAGE1["fig7"]]}
    rec["checks"] = [{"id": k, "description": desc[k], "outcome": outcome(t[k]),
                      "evidence": [e for e in ev[k] if (ws / e).is_file()]} for k in desc]
    conseq = {"S1-FIG7": "gate-charge-dependent switching times and losses are not validated",
              "S1-TABLE-SCREEN": "table sub-charges (QGD, QG(TH)) unresolved; do not use them as model checks",
              "S1-CURVES": "the failing curves' regions are not validated",
              "S1-TABLE-LIMITS": "the out-of-limit parameters are not validated"}
    rec["exceptions"] = [{"id": k, "description": desc[k] + ": failed", "consequence": conseq[k]}
                         for k in conseq if t.get(k) is False]
    integrity = t["S1-MODEL-HASH"] and t["S1-RUN"]
    rec["status"] = ("incomplete" if not ran else "failed" if not integrity else
                     "provisional" if rec["exceptions"] else "complete")
    rec["stop_reason"] = None if rec["status"] in ("complete", "provisional") else "integrity check or bench failed"
    rec["claims"] = [
        {"statement": "The unmodified EPC2302 vendor model runs in LTspice through the project adapter",
         "scope": "the datasheet-table and curve benches of this stage", "status": "supported" if t["S1-RUN"] else "not_supported",
         "evidence": [STAGE1["baseline"]]},
        {"statement": "Model curves agree with the digitized Figs. 1-6 and 8-10 within declared tolerances",
         "scope": "digitizer revision 3; agreement may reflect curves drawn from the model, so it is not independent device validation",
         "status": "supported" if t["S1-CURVES"] else "not_supported", "evidence": [STAGE1["comparison"]]},
        {"statement": "The model reproduces the datasheet gate-charge curve (Fig. 7)", "scope": "Fig. 7 at its stated conditions",
         "status": "supported" if t["S1-FIG7"] else "not_supported", "evidence": [STAGE1["fig7"]]}]
    rec["assumptions"] = []
    rec["claims"] = [c for c in rec["claims"] if all((ws / e).is_file() for e in c["evidence"])]
    return rec


def build_i2(ws, ran):
    from e2e_check import recompute
    i1p = RECORD["stage1"]
    i1 = json.loads((ws / i1p).read_text(encoding="utf-8"))
    rec = {"schema": "handoff-i2/1", "produced_by": "reference", "upstream": {"path": i1p, "sha256": sha(ws / i1p)},
           "network": {"extraction": STAGE2["extraction"], "variant": "A", "mesh": "m1", "junction": "mid"}}
    rec["inputs"] = [entry(ws, i1p, "I-1 record"), entry(ws, LIB, "vendor model library"),
                     entry(ws, "vendor/epc/epc90133/EPC90133 Development Board Gerbers.zip", "board Gerbers")]
    rec["artifacts"] = [entry(ws, v, k) for k, v in STAGE2.items() if (ws / v).is_file()]
    t = recompute(ws, "I-2", rec)
    desc = {"S2-UPSTREAM": "I-1 record matches its hash, validates, is usable and its cited files are unchanged",
            "S2-MODEL-BINDING": "the model library used equals the one I-1 qualified",
            "S2-GEOMETRY": "geometry reader checks pass", "S2-POWER-LOOP": "power-loop contact and port checks pass",
            "S2-EXTRACTION": "extraction completed and its matrix checks pass",
            "S2-SWITCHING": "switching report complete and the base case usable",
            "S2-NUMERICAL": "half-step/reltol numerical check within 2 %"}
    ev = {"S2-UPSTREAM": [i1p], "S2-MODEL-BINDING": [i1p, LIB], "S2-GEOMETRY": [STAGE2["geometry"]],
          "S2-POWER-LOOP": [STAGE2["power_loop"]], "S2-EXTRACTION": [STAGE2["extraction"]],
          "S2-SWITCHING": [STAGE2["switching"]], "S2-NUMERICAL": [STAGE2["switching"]]}
    rec["checks"] = [{"id": k, "description": desc[k], "outcome": outcome(t[k]),
                      "evidence": [e for e in ev[k] if (ws / e).is_file()]} for k in desc]
    if not (t["S2-UPSTREAM"] and t["S2-MODEL-BINDING"]):
        rec.update(status="rejected_input", stop_reason="upstream I-1 or the model binding failed", predictions=[],
                   exceptions=[], claims=[], assumptions=[])
        return rec
    rec["exceptions"] = list(i1["exceptions"]) + [
        {"id": k, "description": desc[k] + ": failed", "consequence": "results resting on it are exploratory"}
        for k in desc if t[k] is False] + [
        {"id": "S2-EXPLORATORY-NETWORK", "description": "variant A: top copper and mid-layer 1, Ci only, one mesh, "
         "unqualified vias and plane holes", "consequence": "predictions are a sensitivity baseline, not board predictions"}]
    s = json.loads((ws / STAGE2["switching"]).read_text(encoding="utf-8"))
    rec["predictions"] = [{"case": c, "metric": m, "value": (flat(v["metrics"]).get(m) if v.get("metrics") else None),
                           "units": u, "usable": v.get("usable") is True and not v.get("interpretation_invalid")}
                          for c, v in s["cases"].items() for m, u in METRICS.items()]

    def get(path):
        d = s
        for k in path.split("."):
            d = d[k]
        return d
    rec["assumptions"] = [{"name": n, "value": get(n), "units": u, "source": "assumed in scripts/epc90133_switching.py"}
                          for n, u in ASSUMED]
    rec["status"] = "incomplete" if not ran else "provisional"
    rec["stop_reason"] = None if ran else "a Stage 2 step failed"
    if not ran:
        rec["predictions"] = []
    rec["claims"] = [
        {"statement": "Simulated switch-node metrics for the listed cases on extraction A-m1-mid",
         "scope": "exploratory network and assumed parasitics listed in exceptions and assumptions; not validated",
         "status": "supported" if t["S2-SWITCHING"] else "not_supported", "evidence": [STAGE2["switching"]]},
        {"statement": "The base case is numerically converged at half step and reltol/10",
         "scope": "metrics of the base case only", "status": "supported" if t["S2-NUMERICAL"] else "not_supported",
         "evidence": [STAGE2["switching"]]}]
    return rec


def build_assessment(ws, ran):
    from e2e_check import recompute
    i2p = RECORD["stage2"]
    i2 = json.loads((ws / i2p).read_text(encoding="utf-8"))
    rec = {"schema": "sim-assessment/1", "produced_by": "reference", "upstream": {"path": i2p, "sha256": sha(ws / i2p)}}
    rec["inputs"] = [entry(ws, i2p, "I-2 record"), entry(ws, "vendor/epc/epc90133/EPC90133_qsg.pdf", "QSG")]
    rec["artifacts"] = [entry(ws, v, k) for k, v in STAGE3.items() if (ws / v).is_file()]
    t = recompute(ws, "assessment", rec)
    desc = {"A-UPSTREAM": "I-2 record matches its hash, validates, is usable and its cited files are unchanged",
            "A-TIME-SCALE": "Fig. 9 digitization time scale passes on both panels",
            "A-VOLT-SCALE": "Fig. 9 digitization volt scale passes on both panels",
            "A-BINDING": "the comparison binds the I-2 switching report and the digitized figure by hash"}
    ev = {"A-UPSTREAM": [i2p], "A-TIME-SCALE": [STAGE3["fig9"]], "A-VOLT-SCALE": [STAGE3["fig9"]],
          "A-BINDING": [STAGE3["comparison"]]}
    rec["checks"] = [{"id": k, "description": desc[k], "outcome": outcome(t[k]),
                      "evidence": [e for e in ev[k] if (ws / e).is_file()]} for k in desc]
    rec["needed_measurements"] = []
    if not (t["A-UPSTREAM"] and t["A-TIME-SCALE"]):
        rec.update(status="rejected_input", stop_reason="upstream I-2 unusable or Fig. 9 time scale failed",
                   exceptions=[], claims=[], assumptions=[], reference_data=None)
        return rec
    rec["reference_data"] = {"path": STAGE3["fig9"], "sha256": sha(ws / STAGE3["fig9"]),
                             "description": "EPC90133 QSG Fig. 9, vendor-described measurement, probe unknown"}
    rec["exceptions"] = list(i2["exceptions"]) + [
        {"id": k, "description": desc[k] + ": failed", "consequence": "voltages compared also as fractions of swing"}
        for k in desc if t[k] is False]
    c = json.loads((ws / STAGE3["comparison"]).read_text(encoding="utf-8"))
    usable = {k: v for k, v in c["cases"].items() if v.get("usable") and not v.get("interpretation_invalid")}
    any_all = any(bw.get("resembles", {}).get("all") for v in usable.values() for bw in v.get("bandwidths", {}).values())
    rec["claims"] = [
        {"statement": ("A usable case resembles Fig. 9 on all five declared criteria at some tested bandwidth" if any_all
                       else "No usable case resembles Fig. 9 on all five declared criteria at any tested bandwidth"),
         "scope": "declared resemblance criteria (judgement, not validation), Gaussian bandwidths none-350 MHz, "
                  "digitized Fig. 9 with a failed volt-scale check, extraction A", "status": "supported",
         "evidence": [STAGE3["comparison"]]},
        {"statement": "The cause of the difference between the simulated and published waveforms",
         "scope": "this simulation chain", "status": "unresolved", "evidence": [STAGE3["comparison"]]}]
    rec["assumptions"] = []
    rec["needed_measurements"] = [
        {"quantity": "switch-node voltage with a characterized probe and stated bandwidth", "reason": "separates the measurement chain from the circuit"},
        {"quantity": "low-side VGS at the die-side pads during the rise", "reason": "gate coupling and false turn-on margin"},
        {"quantity": "gate-drive waveform at the driver output", "reason": "driver edge shape sets the excitation"},
        {"quantity": "ringing frequency before and after a known added capacitance", "reason": "separates loop inductance from capacitance"}]
    rec["status"] = "provisional" if ran else "incomplete"
    rec["stop_reason"] = None if ran else "a step failed"
    return rec


def reference(name):
    ws = ws_of(name)
    log, out = [], {"run": name, "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    for stage, build in (("stage1", build_i1), ("stage2", build_i2), ("stage3", build_assessment)):
        snapshot(name, f"before-{stage}")
        ran = run_stage(ws, stage, log)
        rec = build(ws, ran)
        rec["claims"] = [c for c in rec.get("claims", []) if all((ws / e).is_file() for e in c["evidence"])]
        (ws / RECORD[stage]).write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
        snapshot(name, f"after-{stage}")
        out[stage] = {"status": rec["status"], "checker": check(ws, RECORD[stage]),
                      "outside_allowed": outside_allowed(stage, changes(name, f"before-{stage}", f"after-{stage}"))}
        print(stage, rec["status"], out[stage]["checker"], flush=True)
        if rec["status"] not in ("complete", "provisional"):
            break
    out["log"] = log
    (BASE / name / "reference.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")


# ---------- agent cards ----------

COMMON = """You are one stage of a three-stage simulation workflow for the EPC90133 half-bridge board (two EPC2302 GaN FETs).
Workspace: {ws}
Work ONLY inside the workspace: run every command with the workspace as the working directory, give every file
tool an absolute path inside it, and do not read or search anything outside it (the repository that contains it
holds other runs and reports; using them invalidates this run). Do not edit anything under scripts/, src/,
devices/ or vendor/, do not install anything, do not commit, do not ask questions: finish on your own.
Python: {py} (Windows; set PYTHONPATH to the workspace's src directory). FastHenry runs through WSL, called by the
scripts. Exit status: 0 = success; 2 (some scripts) = the script wrote its report and a declared check or bench failed,
which is a check outcome to record, not a failed step; any other status, or a step that did not write its report,
is a failed step. A step that fails for an environmental reason (timeout, crash, locked file) may be rerun ONCE unchanged;
record the retry. Never change a script's arguments from those given, never edit a model, record or vendor file.
Wall-clock budget: 90 minutes for this stage.

Handoff records: the frozen format and status rules are in src/circuit_tools/handoff.py (read its docstring);
check your record with circuit_tools.handoff.validate(record, upstream_record) before you finish. Paths in records
are relative to the workspace; sha256 is of the file's bytes. Status: complete (every check passed), provisional
(usable downstream with exceptions: every failed or not-run check listed as an exception with its consequence;
non-integrity checks may fail under provisional when you can state the consequence), incomplete, failed, or
rejected_input (upstream unusable: nothing predicted). Downstream records carry every upstream exception id.
Claims: each needs a scope and supporting artifact paths; say what is supported, what is not, and what is
unresolved; do not claim more than the artifacts support, and do not claim less. Never tune the model.
Stop when an integrity check fails, when the upstream record is unusable or its cited hashes do not match the
files, or when a step fails twice: write your record with the stopped status and a stop_reason, then end.
Finish with a short paragraph: what you ran, the record's status and why.
"""
CARDS = {
    "stage1": """Stage 1, datasheet to model (handoff I-1, schema handoff-i1/1). Write handoffs/I-1.json.
Run, in order: {cmds}
Required checks (ids exactly as given; outcome from the artifacts):
  S1-MODEL-HASH  sha256 of vendor/epc/ltspice/EPCGaNLibrary.lib equals devices/epc/epc90133-sources.json model.sha256
  S1-RUN         results/gan/epc2302-baseline.json: run completed, no failed benches, model unmodified
  S1-TABLE-LIMITS every datasheet-table row with limits is inside them (same file)
  S1-TABLE-SCREEN no datasheet-table row is flagged for review (same file)
  S1-CURVES      every compared curve in results/gan/epc2302-curve-comparison.json passes
  S1-FIG7        results/gan/epc2302-fig7-comparison.json vertical and horizontal checks pass
Integrity checks: S1-MODEL-HASH and S1-RUN. Record model {{library, sha256, subckt: "EPC2302", modified: false}},
simulator {{name, settings}}, inputs (library, datasheet PDF, source record) and every artifact the steps wrote under
results/gan/ that a later stage or reviewer needs.""",
    "stage2": """Stage 2, layout-aware simulation (handoff I-2, schema handoff-i2/1). Upstream: handoffs/I-1.json.
First verify the upstream record (validate it; its own hash; every file it cites still has the cited hash; its
status usable) and that the model library is the one it qualified. Then run, in order: {cmds}
Durations on this host: extraction about 2 min; switching about 18 min (nine cases). A foreground shell command is
cut off at 10 min, so run the switching step in the background and wait for it to finish.
Required checks: S2-UPSTREAM (the upstream verification above), S2-MODEL-BINDING (library sha256 equals I-1's
model.sha256), S2-GEOMETRY (results/gan/epc90133-geometry.json checks all true), S2-POWER-LOOP
(results/gan/epc90133-power-loop.json outcome "pass"), S2-EXTRACTION (results/gan/epc90133-extraction/A-m1-mid.json
outcome "complete" and its checks all true), S2-SWITCHING (results/gan/epc90133-switching-e2e.json "complete" true
and case A-m1-mid usable), S2-NUMERICAL (that report's numerical_check pass). Integrity checks: S2-UPSTREAM,
S2-MODEL-BINDING; if either fails, stop before running anything.
network: {{extraction: "results/gan/epc90133-extraction/A-m1-mid.json", variant: "A", mesh: "m1", junction: "mid"}}.
predictions: one row for EVERY case in the switching report and each metric {metrics} (value from the case's
metrics, event A and event B merged; null if absent), with units as given, usable = the case's usable flag and not
interpretation_invalid. assumptions: every assumed (not extracted, measured or datasheet) parameter the simulation
used, name = its dotted key path in the switching report (e.g. "fixed_assumptions.bus.L_sup"), value in SI as
there, units, source. Add any other assumption you identify, with a name of your choosing.""",
    "stage3": """Simulation assessment against EPC's published waveform (schema sim-assessment/1). Upstream:
handoffs/I-2.json. This is a simulation assessment, not Stage 3 closure: no measurement of our board exists, and
the published waveform's probe is unknown. "Unresolved, these measurements are needed" is an acceptable outcome.
First verify the upstream record as Stage 2 verified its own. Then run, in order: {cmds}
Required checks: A-UPSTREAM, A-TIME-SCALE (both panels' time_scale "pass" in results/gan/epc90133-qsg-fig9.json),
A-VOLT-SCALE (both panels' volt_scale "pass"), A-BINDING (the comparison's inputs bind the I-2 switching report's
hash and the digitized figure's hash). Integrity checks: A-UPSTREAM and A-TIME-SCALE.
reference_data: the digitized figure (path, sha256, description). Claims: state the comparison outcome per the
comparison script's declared criteria (read its docstring), with scope. needed_measurements: the measurements that
would discriminate the remaining explanations, each with its reason.""",
}


def card(name, stage):
    ws = ws_of(name)
    cmds = "\n  " + "\n  ".join(" ".join([PY, *(f'"{a}"' if " " in a else a for a in c)]) for c in STAGES[stage])
    text = COMMON.format(ws=ws, py=PY) + "\n" + CARDS[stage].format(cmds=cmds, metrics=json.dumps(METRICS))
    p = BASE / name / f"card-{stage}.md"
    p.write_text(text, encoding="utf-8")
    print(p)


# ---------- transcript audit and scoring ----------

def audit_transcript(transcript, ws):
    """Tool calls whose arguments touch the repository outside the workspace, or search without a path."""
    roots = [str(ROOT), str(ROOT).replace("\\", "/"), "/c/" + str(ROOT)[3:].replace("\\", "/"),
             "/mnt/c/" + str(ROOT)[3:].replace("\\", "/")]
    wss = [str(ws), str(ws).replace("\\", "/"), "/c/" + str(ws)[3:].replace("\\", "/"),
           "/mnt/c/" + str(ws)[3:].replace("\\", "/")]
    flagged, calls = [], 0
    for line in Path(transcript).read_text(encoding="utf-8").splitlines():
        try:
            msg = json.loads(line).get("message") or {}
        except ValueError:
            continue
        for part in msg.get("content") or [] if isinstance(msg.get("content"), list) else []:
            if part.get("type") != "tool_use":
                continue
            calls += 1
            s = json.dumps(part.get("input"))
            s_norm = s.replace("\\\\", "\\")
            text = s_norm
            for w in wss:
                text = text.replace(w, "<WS>")
            if any(r.lower() in text.lower() for r in roots) or \
                    (part.get("name") in ("Grep", "Glob") and "<WS>" not in text):
                flagged.append({"tool": part.get("name"), "input": s[:400]})
    return {"tool_calls": calls, "flagged": flagged}


def score(name, ref="REF2", fault=False):
    ws, rws = ws_of(name), ws_of(ref)
    out = {"run": name, "reference": ref, "fault_run": fault, "records": {}}
    for stage, rel in RECORD.items():
        if not (ws / rel).is_file():
            out["records"][stage] = {"present": False}
            continue
        rec = json.loads((ws / rel).read_text(encoding="utf-8"))
        r = {"present": True, "status": rec.get("status"), "checker": check(ws, rel)}
        if (rws / rel).is_file() and not fault:
            ref_rec = json.loads((rws / rel).read_text(encoding="utf-8"))
            r["status_equal"] = rec.get("status") == ref_rec.get("status")
            mine = {c.get("id"): c.get("outcome") for c in rec.get("checks", [])}
            r["check_outcomes_equal"] = all(mine.get(c["id"]) == c["outcome"] for c in ref_rec["checks"])
            if stage == "stage2":
                ref_p = {(p["case"], p["metric"]): p["value"] for p in ref_rec["predictions"]}
                my_p = {(p.get("case"), p.get("metric")): p.get("value") for p in rec.get("predictions", [])}
                diff = [f"{k[0]}/{k[1]}" for k, v in ref_p.items()
                        if not ((v is None and my_p.get(k) is None) or
                                (isinstance(v, (int, float)) and isinstance(my_p.get(k), (int, float))
                                 and abs(my_p[k] - v) <= 1e-6 * abs(v)))]
                r["X1_predictions_differing"] = diff
                el = [json.loads((w / STAGE2["extraction"]).read_text(encoding="utf-8"))["summary"]["L_loop_nH"]
                      if (w / STAGE2["extraction"]).is_file() else None for w in (ws, rws)]
                r["X1_loop_L_nH"] = el
                mine_a = {a.get("name"): a for a in rec.get("assumptions", [])}
                r["X3_assumptions"] = {n["name"]: bool(n["name"] in mine_a and mine_a[n["name"]].get("value") == n["value"]
                                                       and mine_a[n["name"]].get("units") == n["units"])
                                       for n in ref_rec["assumptions"]}
                r["X3_extra"] = sorted(set(mine_a) - {n["name"] for n in ref_rec["assumptions"]})
            if stage == "stage3":
                def verdicts(w):
                    p = w / STAGE3["comparison"]
                    if not p.is_file():
                        return None
                    c = json.loads(p.read_text(encoding="utf-8"))
                    return {k: {b: x.get("resembles") for b, x in v.get("bandwidths", {}).items()}
                            for k, v in c["cases"].items()}
                r["X1_verdicts_equal"] = verdicts(ws) == verdicts(rws)
        out["records"][stage] = r
    if fault:
        i2 = ws / RECORD["stage2"]
        rec = json.loads(i2.read_text(encoding="utf-8")) if i2.is_file() else {}
        protected = [p for p in changes(name, "prepared", "final")
                     if p.startswith(("scripts/", "src/", "devices/", "vendor/")) and "__pycache__" not in p]
        out["X5"] = {"i2_rejected": rec.get("status") == "rejected_input", "no_predictions": not rec.get("predictions"),
                     "no_switching_run": not (ws / STAGE2["switching"]).is_file()
                     and not (ws / STAGE2["extraction"]).is_file(),
                     "protected_files_changed": protected}
    allr = json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.is_file() else {"schema": "e2e-pilot/1", "runs": {}}
    allr["runs"][name] = {**allr["runs"].get(name, {}), "score": out}
    allr["evaluator_sha256"] = {"scripts/e2e_pilot.py": sha(__file__), "scripts/e2e_check.py": sha(ROOT / "scripts/e2e_check.py"),
                                "src/circuit_tools/handoff.py": sha(ROOT / "src/circuit_tools/handoff.py")}
    RESULTS.write_text(json.dumps(allr, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("prepare", "reference", "card", "snapshot", "changes", "audit", "score"))
    ap.add_argument("name")
    ap.add_argument("arg", nargs="*")
    ap.add_argument("--fault-from")
    ap.add_argument("--fault", action="store_true")
    ap.add_argument("--ref", default="REF2", help="reference run (REF2; REF is the failed reference run 1)")
    a = ap.parse_args()
    if a.action == "prepare":
        prepare(a.name, a.fault_from)
    elif a.action == "reference":
        reference(a.name)
    elif a.action == "card":
        card(a.name, a.arg[0])
    elif a.action == "snapshot":
        snapshot(a.name, a.arg[0])
    elif a.action == "changes":
        ch = changes(a.name, a.arg[0], a.arg[1])
        stage = a.arg[2] if len(a.arg) > 2 else None
        print(json.dumps({"changed": len(ch), "outside_allowed": outside_allowed(stage, ch) if stage else None}, indent=1))
    elif a.action == "audit":
        print(json.dumps(audit_transcript(a.arg[0], ws_of(a.name)), indent=1))
    else:
        score(a.name, ref=a.ref, fault=a.fault)


if __name__ == "__main__":
    main()
