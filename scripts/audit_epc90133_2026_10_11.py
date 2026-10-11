"""Retrospective audit of 9-11 October work; no circuit/field/board solver runs.

Recompute saved search scores, check recorded file identities, and exercise small
acceptance/thermal counterexamples. Write separate evidence; preserve all studies.
"""
import contextlib
import copy
import hashlib
import io
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy import sparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import assess_epc90133_goals as goals
import assess_epc90133_outperform as outperform
import epc90133_network_search as search
import epc90133_thermal as thermal


def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    out = {"schema": "epc90133-audit-2026-10-11/1", "reviewed_head": "6cfc6b0",
           "scope": "9-11 October; stored data, source review and small counterexamples; no board reruns",
           "audit_script_sha256": sha(__file__)}
    state = read(search.OUTDIR / "search.json")
    rounds = {r: search.load_cases(r) for r in range(1, 5)}
    mismatches, official_diff, censored, invalid = [], [], [], []
    count = Counter()
    for name, entry in state["networks"].items():
        cases = rounds[entry["round"]]
        replay = search.score(cases, name)
        if replay != entry["score"]:
            mismatches.append(name)
        count[str(replay["count"]) if replay["usable"] else "unusable"] += 1
        if not replay["usable"]:
            continue
        for driver in search.DRIVERS:
            case = cases[f"{name}@{driver}-gear"]
            reference = cases[f"stock@{driver}-gear"]
            if case.get("interpretation_invalid"):
                invalid.append(f"{name}@{driver}")
            m, s = goals.metrics(case, 48), goals.metrics(reference, 48)
            if m["settling_censored"]:
                censored.append(f"{name}@{driver}")
            a, b = search.goals(m, s), goals.goals(m, s, 48)
            if any(a[k] != b[k] for k in a):
                official_diff.append(f"{name}@{driver}")
    out["search_replay"] = {"networks": len(state["networks"]), "count_histogram": dict(count),
                            "stored_score_mismatches": mismatches, "official_subset_differences": official_diff,
                            "censored_cases": censored, "invalid_cases": invalid}

    # Check recorded hashes, distinguishing changed source from changed run inputs.
    checks = []
    reports = list(search.OUTDIR.glob("round*.json"))
    reports += [ROOT / f"results/gan/epc90133-goals-G-{n}.json" for n in ("K1", "K2", "C3", "V8d075-csw")]
    for p in reports:
        rep = read(p)
        manifest = rep.get("input_manifest", {})
        refs = {**manifest.get("extractions", {}), **manifest.get("modules", {})}
        for f, digest in refs.items():
            fp = ROOT / f
            checks.append({"report": p.relative_to(ROOT).as_posix(), "file": f,
                           "status": "missing" if not fp.exists() else "match" if sha(fp) == digest else "different"})
    out["recorded_hashes"] = {"count": len(checks), "status_counts": dict(Counter(c["status"] for c in checks)),
                              "exceptions": [c for c in checks if c["status"] != "match"]}
    out["model_identities"] = sorted({read(p)["input_manifest"]["vendor_library"]["sha256"] for p in reports})

    # Verify current candidate packages and their accepted report identity.
    packages = {}
    for n in ("K1", "K2", "C3"):
        base = ROOT / f"vendor/epc/epc90133/reconstruction/export/{n}"
        rep = read(ROOT / f"results/gan/epc90133-board-export-{n}.json")
        man = read(base / "export.json")
        packages[n] = {"accepted": rep["accepted"], "manifest_matches_report": sha(base / "export.json") == rep["manifest_sha256"],
                       "files_checked": len(man["files"]),
                       "mismatched_files": [f for f, h in man["files"].items() if sha(base / f) != h]}
    out["candidate_packages"] = packages

    # Isolate rule handling using real saved stock cases, with specified faults.
    scratch = ROOT / "runs/audit-2026-10-11"
    scratch.mkdir(parents=True, exist_ok=True)
    stock = read(ROOT / "results/gan/epc90133-goals-G.json")
    candidate_replay = {}
    keys = outperform.NO_WORSE + outperform.EDGES + (outperform.GAIN,)
    for name in ("K1", "K2", "C3"):
        candidate = read(ROOT / f"results/gan/epc90133-goals-G-{name}.json")
        saved = read(ROOT / f"results/gan/epc90133-outperform-{name}.json")
        errors = []
        for driver in search.DRIVERS:
            m = goals.metrics(candidate["cases"][f"{name}@{driver}-gear"], 48)
            s = goals.metrics(stock["cases"][f"stock@{driver}-gear"], 48)
            for k in keys:
                value = 100 * (m[k] / s[k] - 1)
                if value != saved["relative_change_pct"][driver][k]:
                    errors.append(f"{driver}:{k}")
        candidate_replay[name] = {"relative_metric_mismatches": errors, "saved_verdicts": saved["verdicts"]}
    out["candidate_metric_replay"] = candidate_replay
    k2_checks = {}
    for tag in ("ms50", "csw"):
        cases = read(ROOT / f"results/gan/epc90133-goals-G-K2-{tag}.json")["cases"]
        if tag == "ms50":
            cases.update(read(ROOT / "results/gan/epc90133-goals-G-K2-ms50-stock.json")["cases"])
        k2_checks[tag] = {}
        for driver in search.DRIVERS:
            m = goals.metrics(cases[f"K2@{driver}-gear-{tag}"], 48)
            s = goals.metrics(cases[f"stock@{driver}-gear-{tag}"], 48)
            k2_checks[tag][driver] = {k: 100 * (m[k] / s[k] - 1) for k in ("q2_gate_peak_V", "settling_s", "didt_A_per_ns")}
    out["K2_confirmation_relative_percent"] = k2_checks
    base = {**stock, "cases": {f"probe@{d}-gear": copy.deepcopy(stock["cases"][f"stock@{d}-gear"])
                               for d in search.DRIVERS}}
    for case in base["cases"].values():
        case["metrics"]["event_b_turn_on_at_valley"]["q2_gate_peak_during_rise_V"] *= 0.5
    faults = {}
    for kind in ("S7_overvoltage", "nonfinite_loss", "model_mismatch"):
        rep = copy.deepcopy(base)
        for case in rep["cases"].values():
            if kind == "S7_overvoltage":
                case["metrics"]["gate_and_current_diagnostics"]["event_a"]["q1_vgs_max_V"] = 6.0
            elif kind == "nonfinite_loss":
                case["metrics"]["period_loss"]["fet_loss_W"] = float("nan")
        if kind == "model_mismatch":
            rep["input_manifest"]["vendor_library"]["sha256"] = "0" * 64
        source, result = scratch / f"{kind}.json", scratch / f"{kind}-result.json"
        source.write_text(json.dumps(rep), encoding="utf-8")
        previous = sys.argv
        try:
            sys.argv = ["assess_epc90133_outperform.py", "probe", str(source), "--output", str(result)]
            with contextlib.redirect_stdout(io.StringIO()):
                outperform.main()
            faults[kind] = read(result)["verdicts"]
        finally:
            sys.argv = previous
    out["outperform_fault_probes"] = faults
    s = goals.metrics(stock["cases"]["stock@ramp-Ls50-gear"], 48)
    m, ref = dict(s, settling_s=500e-9, settling_censored=True), dict(s, settling_s=600e-9)
    out["censored_settling_probe"] = {"search_S3": search.goals(m, ref)["S3"],
                                      "official_S3": goals.goals(m, ref, 48)["S3"]}

    # Two adjacent cells: copper occupies only the left cell; remove laminate
    # conductivity to isolate the implementation's copper-only bridge.
    cf = [np.array([[1., 0.]]) for _ in range(8)]
    rows, cols, vals, _, nc, _ = thermal.build(cf, [], 0.2e-3, 0., thermal.DIEL_MIL, k_lam=0.)
    matrix = sparse.csr_matrix((vals, (rows, cols)), shape=(8 * nc, 8 * nc))
    out["thermal_gap_probe"] = {"copper_left_fraction": 1, "copper_right_fraction": 0,
                                "laminate_conductivity": 0, "computed_lateral_conductance_W_per_K": float(-matrix[0, 1]),
                                "expected_copper_only_conductance": 0}
    empty = [np.zeros((1, 1)) for _ in range(8)]
    rows, cols, vals, _, _, _ = thermal.build(empty, [(0, 0, 0.1981e-3)], 0.2e-3, 0., thermal.DIEL_MIL, k_lam=0.)
    matrix = sparse.csr_matrix((vals, (rows, cols)), shape=(8, 8))
    out["thermal_via_probe"] = {"all_plane_copper_fractions": 0,
                                "adjacent_plane_node_conductances_W_per_K": [float(-matrix[i, i + 1]) for i in range(7)],
                                "limitation": "No independent barrel node or per-layer pad/antipad contact representation"}
    factors = state["networks"]["N3_00"]["factors"]
    out["overlapping_factor_effects"] = {"Ci_VIN_self_L_ratio": factors["VIN"],
                                         "Cm_VIN_self_L_ratio": factors["VIN"] * factors["CM"],
                                         "Cm_GND_self_L_ratio": factors["GND"] * factors["CM"]}
    out["source_hashes"] = {str(Path(m.__file__).relative_to(ROOT)): sha(m.__file__)
                            for m in (goals, outperform, search, thermal)}
    target = ROOT / "results/gan/project-audit-2026-10-11.json"
    target.write_text(json.dumps(out, indent=2, default=lambda v: v.item() if isinstance(v, np.generic) else str(v)) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
