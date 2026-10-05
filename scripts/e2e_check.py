#!/usr/bin/env python3
"""Independent checker for E2E-0 handoff records (scripts/e2e_pilot.py; frozen 2 October 2026, before any run).

It does not trust a record's own account. For one record in a workspace it
1. validates the structure and status rules (src/circuit_tools/handoff.py), with its upstream record;
2. rehashes every cited input and artifact, and the upstream record, against the workspace files;
3. recomputes each required check from the cited artifacts and requires the record's outcome to agree;
4. for I-2, requires a prediction row for every case and metric of the switching report, equal to the report;
5. for a stopped record, requires the stop to be warranted by a recomputed failure (or a missing artifact).
It reads only the workspace. It never judges whether a claim is warranted; that is the declared claims review.

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
    kind = KIND.get(rec.get("schema"))
    up = load(ws, rec["upstream"]["path"]) if isinstance(rec.get("upstream"), dict) and rec["upstream"].get("path") else None
    problems = [f"schema: {x}" for x in validate(rec, up)]
    if kind is None:
        return problems
    for key in ("inputs", "artifacts"):
        for f in rec.get(key) or []:
            if not isinstance(f, dict) or "path" not in f:
                continue
            q = ws / f["path"]
            if not q.is_file():
                problems.append(f"{key}: {f['path']} does not exist")
            elif sha(q) != f.get("sha256"):
                problems.append(f"{key}: {f['path']} hash differs from the record")
    truth = recompute(ws, kind, rec)
    stated = {c.get("id"): c.get("outcome") for c in rec.get("checks") or [] if isinstance(c, dict)}
    stopped = rec.get("status") in STOPPED
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
        rows = {(p.get("case"), p.get("metric")): p for p in rec.get("predictions") or [] if isinstance(p, dict)}
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
