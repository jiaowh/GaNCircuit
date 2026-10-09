"""Retrospective, solver-free audit of 274cd46. Does not modify prior evidence.

Budget: stored JSON/matrix reads, one goals-assessor replay, selected probe metric
recomputation and in-memory fault probes; no LTspice/FastHenry/geometry runs.
Writes separate audit evidence and ignored scratch. Checks are audit checks, not
new acceptance criteria for the historical studies.
"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import assess_epc90133_goals as goals
import compare_epc90133_fig9 as fig
import epc90133_extract as ext


def load(p):
    return json.loads((ROOT / p).read_text(encoding="utf-8"))


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def main():
    scratch = ROOT / "runs/audit-274cd46"
    scratch.mkdir(exist_ok=True)
    out = {"schema": "project-audit/1", "reviewed_commit": "274cd46",
           "date": "2026-10-09", "scope": __doc__, "script_sha256": sha(__file__)}
    checks = []

    def check(p, expected, source):
        p = Path(p)
        got = sha(p) if (ROOT / p).is_file() else None
        checks.append({"file": str(p), "source": source, "matches": got == expected,
                       "expected": expected, "actual": got})

    prefix = "results/gan/"
    reports = [prefix + "epc90133-goals-G-ds" + s + ".json" for s in ("", "-v40", "-v60", "-i0")]
    out["case_counts"] = {}
    for p in reports + [prefix + "epc90133-goals-G-ds-ctlls.json", prefix + "epc90133-switching-probe-j33-ds.json"]:
        d = load(p)
        out["case_counts"][p] = {"total": len(d["cases"]), "usable": sum(c.get("usable") is True for c in d["cases"].values()),
                                 "unusable": [k for k, c in d["cases"].items() if c.get("usable") is not True]}
        m = d["input_manifest"]
        for group in ("modules", "extractions"):
            for f, h in m[group].items():
                check(f, h, p)
        for key in ("ds_library",):
            check(m[key]["file"], m[key]["sha256"], p)
            check(m[key]["report"], m[key]["report_sha256"], p)
    for name, script in (("epc90133-goals-assessment-ds.json", "assess_epc90133_goals.py"),
                         ("epc90133-probe-reference-j33-ds.json", "epc90133_probe_reference.py")):
        d = load(prefix + name)
        check("scripts/" + script, d["evaluator_sha256"], name)
        for f, h in d["inputs"].items():
            check(f, h, name)
    model = load(prefix + "epc2302-ds-variant.json")
    check("scripts/epc2302_ds_variant.py", model["evaluator_sha256"], "model")
    for p, h in model["input_manifest"]["modules"].items():
        check(p, h, "model")
    check(prefix + "epc2302-baseline.json", model["input_manifest"]["vendor_baseline"], "model")
    out["model_checks"] = {k: v.get("outcome") for k, v in model.items() if k.startswith("D")}
    out["hash_checks"] = checks

    replay = scratch / "goals-assessment.json"
    p = subprocess.run([sys.executable, str(ROOT / "scripts/assess_epc90133_goals.py"), *reports,
                        "--output", str(replay)], cwd=ROOT, capture_output=True, text=True, timeout=60)
    out["goals_replay"] = {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr,
                           "designs_identical": p.returncode == 0 and load(replay)["designs"] == load(prefix + "epc90133-goals-assessment-ds.json")["designs"]}
    d = load(reports[0])
    c = d["cases"]["stock@ramp-Ls50-gear-ds"]
    bad = copy.deepcopy(c)
    bad["interpretation_invalid"] = "audit injected invalidity"
    out["fault_probes"] = {"goals_scores_interpretation_invalid_case": goals.metrics(bad, 48) is not None,
                           "empty_goal_set_combines_to_pass": goals.combine([])}
    out["goals_verdict_keys"] = list(load(replay)["designs"]["V8"]["verdict"])

    a = load(prefix + "epc90133-extraction/G-m1-mid.json")
    b = load(prefix + "epc90133-extraction/G-m1-mid-j33.json")
    raw = ROOT / b["evidence_directory"] / "Zc_j0.mat"
    rows, cols, kind, matrix = ext.parse_matrix_file(raw.read_text())
    saved = np.array(b["Z_raw_real"]) + 1j * np.array(b["Z_raw_imag"])
    roundtrip = np.linalg.inv(np.linalg.inv(matrix))
    out["j33_extraction"] = {"matrix_kind": kind, "matrix_sha256": sha(raw), "port_order_matches": rows == b["port_order"],
                             "relative_matrix_error": float(np.max(abs(roundtrip - saved)) / np.max(abs(saved))),
                             "loop_L_relative_change": b["summary"]["L_loop_nH"] / a["summary"]["L_loop_nH"] - 1,
                             "declared_control_limit": 0.005}
    probe = load(prefix + "epc90133-switching-probe-j33-ds.json")
    scored = load(prefix + "epc90133-probe-reference-j33-ds.json")
    name = "G-m1-mid-j33-Ls50-probe-ds"
    c = probe["cases"][name]
    t = c["traces"]
    terms = t["terminals"]
    v = np.array(terms["j33_sw"]["rising"]) - np.array(terms["j33_gnd"]["rising"])
    tt = t["start_s"] + t["step_s"] * np.arange(len(v))
    r = fig.edge(tt, v, True)
    q2 = scored["cases"][name]["pairs"]["q2_d-0"]["none"]
    j33 = scored["cases"][name]["pairs"]["j33_sw-j33_gnd"]["none"]
    measured = scored["measured"]["overshoot_V"]
    out["probe_replay"] = {"saved_j33": j33, "saved_q2": q2, "fig9_overshoot_V": measured,
                           "recomputed_j33_overshoot_V": r["overshoot_above_settled_V"],
                           "recomputed_j33_zeta": r["ring_damping_ratio"],
                           "fraction_of_gap_closed": (q2["overshoot_V"] - j33["overshoot_V"]) / (q2["overshoot_V"] - measured)}
    target = ROOT / "results/gan/project-audit-274cd46.json"
    target.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"hash_checks": len(checks), "hash_mismatches": [x for x in checks if not x["matches"]],
                      "goals_replay": out["goals_replay"], "fault_probes": out["fault_probes"],
                      "j33_extraction": out["j33_extraction"], "probe_replay": out["probe_replay"]}, indent=2))


if __name__ == "__main__":
    main()
