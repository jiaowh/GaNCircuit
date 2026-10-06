#!/usr/bin/env python3
"""Independent checker for E2E-0 handoff records (scripts/e2e_pilot.py; frozen 2 October 2026, before any run).

It does not trust a record's own account. For one record in a workspace it
1. validates the structure and status rules (src/circuit_tools/handoff.py), with its upstream record;
2. rehashes every cited input and artifact, and the upstream record, against the workspace files;
3. recomputes each required check from the cited artifacts and requires the record's outcome to agree;
4. for I-2, requires a prediction row for every case and metric of the switching report, equal to the report;
5. for a stopped record, requires the stop to be warranted by a recomputed failure (or a missing artifact).
It reads only the workspace. It never judges whether a claim is warranted; that is the declared claims review.

Revision 2 (5 October 2026, project audit at f4767b1, findings 3 and 4). A record that is not a JSON object, or
that fails structural validation, is rejected with structured problems before any artifact is read (it no longer
raises). Descriptive identity fields are bound to the pilot's frozen artifacts: I-1 model library and subcircuit
(the library path, its listed hash, and the subcircuit named in the source record); I-2 network (the extraction
path, listed with its hash, and variant/mesh/junction equal to the extraction file's own case); the assessment's
reference_data (the Fig. 9 path, its hash and its listing). I-2 predictions must form exactly the set of report
cases x metrics, with no duplicates and no extra rows. Identity is checked against the frozen pilot; a new target
needs its own expected identities.

    python scripts/e2e_check.py <workspace> handoffs/I-1.json   # prints problems as JSON; exit 1 if any
"""
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from circuit_tools.handoff import STOPPED, validate  # noqa: E402

LIB = "vendor/epc/ltspice/EPCGaNLibrary.lib"
SOURCES = "devices/epc/epc90133-sources.json"
G = "results/gan/"
STAGE1 = {"figures": G + "epc2302-datasheet-figures.json", "baseline": G + "epc2302-baseline.json",
          "curves": G + "epc2302-model-curves.json", "extra": G + "epc2302-model-curves-extra.json",
          "fig7": G + "epc2302-fig7-comparison.json", "comparison": G + "epc2302-curve-comparison.json"}
STAGE2 = {"geometry": G + "epc90133-geometry.json", "power_loop": G + "epc90133-power-loop.json",
          "extraction": G + "epc90133-extraction/A-m1-mid.json", "switching": G + "epc90133-switching-e2e.json"}
STAGE3 = {"fig9": G + "epc90133-qsg-fig9.json", "comparison": G + "epc90133-fig9-e2e-comparison.json",
          "summary": G + "epc90133-fig9-e2e-summary.md"}
BASE_CASE = "A-m1-mid"
METRICS = {"sw_fall_time_90_10_s": "s", "sw_rise_time_10_90_s": "s", "sw_overshoot_above_bus_V": "V",
           "sw_peak_V": "V", "ringing_frequency_Hz": "Hz", "ringing_damping_ratio": "1", "q1_vds_peak_V": "V"}
REQUIRED = {"I-1": ("S1-MODEL-HASH", "S1-RUN", "S1-TABLE-LIMITS", "S1-TABLE-SCREEN", "S1-CURVES", "S1-FIG7"),
            "I-2": ("S2-UPSTREAM", "S2-MODEL-BINDING", "S2-GEOMETRY", "S2-POWER-LOOP", "S2-EXTRACTION",
                    "S2-SWITCHING", "S2-NUMERICAL"),
            "assessment": ("A-UPSTREAM", "A-TIME-SCALE", "A-VOLT-SCALE", "A-BINDING")}
KIND = {"handoff-i1/1": "I-1", "handoff-i2/1": "I-2", "sim-assessment/1": "assessment"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(ws, rel):
    try:
        return json.loads((ws / rel).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def flat(m):
    return {**m["event_a_turn_off_at_peak"], **m["event_b_turn_on_at_valley"]}


def upstream_ok(ws, rec):
    """Recomputed S2-UPSTREAM / A-UPSTREAM: the upstream record exists, matches its cited hash, validates, is
    usable (complete or provisional) and every file it cites still has the cited hash."""
    up = rec.get("upstream") or {}
    p = ws / str(up.get("path", ""))
    if not p.is_file() or sha(p) != up.get("sha256"):
        return False, None
    u = load(ws, up["path"])
    if u is None or validate(u, load(ws, (u.get("upstream") or {}).get("path", "")) if u.get("upstream") else None):
        return False, u
    if u.get("status") not in ("complete", "provisional"):
        return False, u
    for f in (u.get("inputs") or []) + (u.get("artifacts") or []):
        q = ws / f["path"]
        if not q.is_file() or sha(q) != f["sha256"]:
            return False, u
    return True, u


def listed(rec, path):
    """sha256 under which rec lists path among its inputs or artifacts, or None."""
    for key in ("inputs", "artifacts"):
        for f in rec.get(key) or []:
            if isinstance(f, dict) and f.get("path") == path:
                return f.get("sha256")
    return None


def bound(ws, rec, path, cited_sha, what):
    """Problems if path is not the expected file, not listed by the record, or its hash differs."""
    out = []
    q = ws / path
    if not q.is_file():
        return [f"{what}: {path} does not exist"]
    actual = sha(q)
    if listed(rec, path) != actual:
        out.append(f"{what}: {path} is not listed among inputs/artifacts with its current hash")
    if cited_sha is not None and cited_sha != actual:
        out.append(f"{what}: cited hash differs from {path}")
    return out


def identity(ws, kind, rec):
    """Identity problems: the record's descriptive fields must name the pilot's frozen artifacts."""
    out = []
    if kind == "I-1":
        m = rec.get("model") or {}
        src = load(ws, SOURCES)
        subckt = ((src or {}).get("model") or {}).get("subcircuit", "").split()[:1]
        if m.get("library") != LIB:
            out.append(f"model.library {m.get('library')!r} is not {LIB}")
        else:
            out += bound(ws, rec, LIB, m.get("sha256"), "model.library")
        if not subckt or m.get("subckt") != subckt[0]:
            out.append(f"model.subckt {m.get('subckt')!r} is not the source record's {subckt[:1]}")
    elif kind == "I-2":
        n = rec.get("network") or {}
        if n.get("extraction") != STAGE2["extraction"]:
            out.append(f"network.extraction {n.get('extraction')!r} is not {STAGE2['extraction']}")
        else:
            out += bound(ws, rec, STAGE2["extraction"], None, "network.extraction")
            case = (load(ws, STAGE2["extraction"]) or {}).get("case") or {}
            for k in ("variant", "mesh", "junction"):
                if n.get(k) != case.get(k):
                    out.append(f"network.{k} {n.get(k)!r} differs from the extraction's {case.get(k)!r}")
    elif kind == "assessment":
        r = rec.get("reference_data") or {}
        if r.get("path") != STAGE3["fig9"]:
            out.append(f"reference_data.path {r.get('path')!r} is not {STAGE3['fig9']}")
        else:
            out += bound(ws, rec, STAGE3["fig9"], r.get("sha256"), "reference_data")
    return out


def recompute(ws, kind, rec):
    """{check id: True/False/None} from the artifacts (None: the artifact needed is missing or unreadable)."""
    out = {}
    if kind == "I-1":
        src, a = load(ws, SOURCES), {k: load(ws, v) for k, v in STAGE1.items()}
        lib_sha = sha(ws / LIB) if (ws / LIB).is_file() else None
        out["S1-MODEL-HASH"] = bool(src and lib_sha == src["model"]["sha256"]
                                    and lib_sha == (rec.get("model") or {}).get("sha256"))
        b = a["baseline"]
        out["S1-RUN"] = None if b is None else (b.get("run_outcome") == "completed" and not b.get("failed_benches")
                                                and b.get("model", {}).get("modified") is False)
        t = (b or {}).get("datasheet_table")
        out["S1-TABLE-LIMITS"] = None if not t else all(r.get("limit_check") in ("inside-limits", "no-limits")
                                                         for r in t.values())
        out["S1-TABLE-SCREEN"] = None if not t else not any(r.get("review") for r in t.values())
        c = a["comparison"]
        out["S1-CURVES"] = None if not c else all(v.get("outcome") == "pass" for v in c["summary"].values())
        f = a["fig7"]
        out["S1-FIG7"] = None if not f else (f["vertical_check"]["outcome"] == "pass"
                                             and f["horizontal_check"]["outcome"] == "pass")
    elif kind == "I-2":
        ok, u = upstream_ok(ws, rec)
        out["S2-UPSTREAM"] = ok
        lib_sha = sha(ws / LIB) if (ws / LIB).is_file() else None
        out["S2-MODEL-BINDING"] = bool(u and lib_sha == (u.get("model") or {}).get("sha256"))
        a = {k: load(ws, v) for k, v in STAGE2.items()}
        out["S2-GEOMETRY"] = None if not a["geometry"] else all(a["geometry"]["checks"].values())
        out["S2-POWER-LOOP"] = None if not a["power_loop"] else a["power_loop"].get("outcome") == "pass"
        e = a["extraction"]
        out["S2-EXTRACTION"] = None if not e else (e.get("outcome") == "complete" and all(e["checks"].values()))
        s = a["switching"]
        out["S2-SWITCHING"] = None if not s else (s.get("complete") is True
                                                  and (s["cases"].get(BASE_CASE) or {}).get("usable") is True)
        out["S2-NUMERICAL"] = None if not s else bool((s.get("numerical_check") or {}).get("pass"))
    else:
        ok, u = upstream_ok(ws, rec)
        out["A-UPSTREAM"] = ok
        f, c = load(ws, STAGE3["fig9"]), load(ws, STAGE3["comparison"])
        panels = (f or {}).get("checks") or {}
        have = all(isinstance(panels.get(k), dict) for k in ("rising", "falling"))
        out["A-TIME-SCALE"] = None if not have else all(panels[k].get("time_scale") == "pass" for k in ("rising", "falling"))
        out["A-VOLT-SCALE"] = None if not have else all(panels[k].get("volt_scale") == "pass" for k in ("rising", "falling"))
        sw = next((x for x in (u or {}).get("artifacts", []) if x["path"] == STAGE2["switching"]), None)
        if c is None or sw is None or not (ws / STAGE3["fig9"]).is_file():
            out["A-BINDING"] = None
        else:
            sims = (c.get("inputs") or {}).get("sim") or {}
            out["A-BINDING"] = (sw["sha256"] in sims.values() and (c.get("inputs") or {}).get("fig9_sha256") == sha(ws / STAGE3["fig9"]))
    return out


def check(ws, rel):
    ws = Path(ws)
    rec = load(ws, rel)
    if rec is None:
        return ["record missing or unreadable"]
    if not isinstance(rec, dict):
        return ["schema: record is not a JSON object"]
    schema = rec.get("schema")
    kind = KIND.get(schema) if isinstance(schema, str) else None
    u = rec.get("upstream")
    up = load(ws, u["path"]) if isinstance(u, dict) and isinstance(u.get("path"), str) and u["path"] else None
    problems = [f"schema: {x}" for x in validate(rec, up)]
    if kind is None or problems:
        return problems  # structural rejection: nothing below is read from a malformed record
    for key in ("inputs", "artifacts"):
        for f in rec.get(key) or []:
            if not isinstance(f, dict) or "path" not in f:
                continue
            q = ws / f["path"]
            if not q.is_file():
                problems.append(f"{key}: {f['path']} does not exist")
            elif sha(q) != f.get("sha256"):
                problems.append(f"{key}: {f['path']} hash differs from the record")
    stopped = rec.get("status") in STOPPED
    if not stopped:
        problems += [f"identity: {x}" for x in identity(ws, kind, rec)]
    truth = recompute(ws, kind, rec)
    stated = {c.get("id"): c.get("outcome") for c in rec.get("checks") or [] if isinstance(c, dict)}
    for cid in REQUIRED[kind]:
        t = truth.get(cid)
        if cid not in stated:
            problems.append(f"required check {cid} absent")
        elif t is None:
            if stated[cid] != "not_run" and not stopped:
                problems.append(f"{cid}: its artifact is missing, so it cannot be '{stated[cid]}'")
        elif stated[cid] != ("pass" if t else "fail") and not (stopped and stated[cid] == "not_run"):
            problems.append(f"{cid}: record says {stated[cid]}, recomputed {'pass' if t else 'fail'}")
    if stopped:
        warranted = [c for c in REQUIRED[kind] if truth.get(c) is False or (truth.get(c) is None and c in stated)]
        if not warranted:
            problems.append("stopped, but no required check fails or lacks its artifact on recomputation")
    elif any(truth.get(c) is False for c in REQUIRED[kind][:2]):  # the first two are integrity checks
        problems.append(f"usable status despite a failed integrity check ({', '.join(REQUIRED[kind][:2])})")
    if kind == "I-2" and not stopped:
        s = load(ws, STAGE2["switching"])
        preds = [p for p in rec.get("predictions") or [] if isinstance(p, dict)]
        rows = {(p.get("case"), p.get("metric")): p for p in preds}
        if len(rows) != len(preds):
            problems.append("predictions contain duplicate case/metric rows")
        expected = {(case, metric) for case in ((s or {}).get("cases") or {}) for metric in METRICS}
        for key in sorted(set(rows) - expected, key=str):
            problems.append(f"prediction {key[0]}/{key[1]} is not in the switching report")
        for case, c in ((s or {}).get("cases") or {}).items():
            m = flat(c["metrics"]) if c.get("metrics") else {}
            usable = c.get("usable") is True and not c.get("interpretation_invalid")
            for metric, unit in METRICS.items():
                p = rows.get((case, metric))
                if p is None:
                    problems.append(f"prediction {case}/{metric} absent")
                    continue
                v, ref = p.get("value"), m.get(metric)
                same = (v is None and ref is None) or (isinstance(v, (int, float)) and isinstance(ref, (int, float))
                                                      and math.isclose(v, ref, rel_tol=1e-9, abs_tol=0.0))
                if not same or p.get("units") != unit or p.get("usable") is not usable:
                    problems.append(f"prediction {case}/{metric} differs from the report")
    return problems


def main():
    problems = check(Path(sys.argv[1]), sys.argv[2])
    print(json.dumps({"record": sys.argv[2], "problems": problems, "pass": not problems}, indent=1))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
