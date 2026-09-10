"""Standard-library numerical checks and explicit experiment ledger.

Run: python3 protocol/check_protocol.py
No simulator is invoked, no physical pilot results are generated.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "protocol-check"


def pmf(n, p):
    if p == 0:
        return [1.0] + [0.0] * n
    if p == 1:
        return [0.0] * n + [1.0]
    return [math.exp(math.lgamma(n + 1) - math.lgamma(k + 1)
                     - math.lgamma(n - k + 1) + k * math.log(p)
                     + (n - k) * math.log1p(-p)) for k in range(n + 1)]


def tail(n, k, p, upper):
    masses = pmf(n, p)
    return math.fsum(masses[k:] if upper else masses[:k + 1])


def cp(k, n, alpha=0.05, sides=2):
    """Tail inversion; sides=1 returns the two separate one-sided limits."""
    a = alpha / sides
    def solve(lower):
        if lower and k == 0:
            return 0.0
        if not lower and k == n:
            return 1.0
        lo, hi = 0.0, 1.0
        for _ in range(55):
            mid = (lo + hi) / 2
            prob = tail(n, k, mid, lower)
            if (prob < a) == lower:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2
    return solve(True), solve(False)


def wilson(k, n, z=2.4):
    v = k / n
    denom = 1 + z * z / n
    center = (v + z * z / (2 * n)) / denom
    half = z * math.sqrt(v * (1 - v) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def old_coverage(p):
    first, extra = pmf(50, p), pmf(200, p)
    coverage = escalation = 0.0
    for k, mass in enumerate(first):
        lo, hi = wilson(k, 50)
        if lo <= 0.9 <= hi:
            escalation += mass
            coverage += mass * math.fsum(extra[j] for j in range(201)
                                        if wilson(k + j, 250)[0] <= p <= wilson(k + j, 250)[1])
        elif lo <= p <= hi:
            coverage += mass
    return {"p": p, "coverage": coverage, "escalation_probability": escalation}


def check_statistics():
    assert abs(wilson(50, 50)[0] - 50 / (50 + 2.4 ** 2)) < 1e-12
    assert wilson(50, 50)[0] < 0.90
    assert abs(cp(50, 50)[0] - 0.025 ** (1 / 50)) < 1e-12
    assert abs(cp(0, 50)[1] - (1 - 0.025 ** (1 / 50))) < 1e-12
    assert abs(cp(0, 60, sides=1)[1] - (1 - 0.05 ** (1 / 60))) < 1e-12
    assert abs(cp(5, 10)[0] - 0.1870860284473985) < 1e-11
    intervals = [cp(k, 250) for k in range(251)]
    assert all(intervals[k][0] <= intervals[k+1][0] and intervals[k][1] <= intervals[k+1][1] for k in range(250))
    grid = sorted(set([i / 1000 for i in range(1001)] + [0.0024]))
    coverages = [(p, math.fsum(m for m, (lo, hi) in zip(pmf(250, p), intervals) if lo <= p <= hi)) for p in grid]
    minimum = min(coverages, key=lambda v: v[1])
    assert minimum[1] >= 0.95 - 1e-10
    certificate_min = next(k for k in range(251) if intervals[k][0] >= 0.9)
    confirmation_min = next(k for k in range(251) if cp(k, 250, 0.05 / 25, 1)[0] >= 0.9)
    old = [old_coverage(p) for p in (0.002, 0.0024, 0.88, 0.90, 0.95, 0.98)]
    assert abs(old[0]["coverage"] - 0.904747) < 1e-6
    # Non-transitive overlap example: only A/C is a resolved pair.
    intervals_abc = [(0, 2), (1, 3), (2.5, 4)]
    resolved = [(a, b) for a in range(3) for b in range(a+1, 3)
                if intervals_abc[a][1] < intervals_abc[b][0] or intervals_abc[b][1] < intervals_abc[a][0]]
    assert resolved == [(0, 2)]
    # Increasing uncertainty must worsen both lower/upper-bound safety margins.
    for s in (1, -1):
        margins = [s * ((10 - s * 1.2815515655 * sigma) - 10) for sigma in (1, 2)]
        assert margins[1] < margins[0]
    assert abs(0.9 ** 2 - 0.81) < 1e-12
    return {"old_wilson_50_of_50_lower": wilson(50, 50)[0],
            "old_rule": old, "fixed_250_CP_grid_minimum": {"p": minimum[0], "coverage": minimum[1]},
            "coverage_basis": "exact binomial tail inversion; grid is only a numerical regression test",
            "certificate_min_successes_of_250": certificate_min,
            "confirmation_min_successes_of_250_alpha_0_002": confirmation_min,
            "resolution_at_250": {str(p): {"preliminary_pass_probability": math.fsum(pmf(250,p)[certificate_min:]),
                                         "confirmation_pass_probability": math.fsum(pmf(250,p)[confirmation_min:])}
                                  for p in (0.9, 0.95, 0.98, 0.99)},
            "assertions": "passed"}


def ledger(m):
    rows = []
    costs = m["cost_seconds"]
    def add(name, count, kind, scenario="shared"):
        assert count >= 0 and count == int(count)
        rows.append(dict(name=name, count=int(count), unit=kind, scenario=scenario,
                         core_hours=count * costs[kind] / 3600))
    p = m["pilot"]
    train = p["topologies"] * p["independent_panels"] * p["train_designs_per_topology_panel"]
    bases = p["topologies"] * (p["calibration_bases_per_topology"] + p["test_bases_per_topology"])
    evaluations = bases * (1 + p["candidates_per_base"])
    add("pilot training nominal + central endpoint labels", train * (1+2*p["derivative_directions"]), "schematic_job", "pilot")
    add("pilot calibration/test nominal values", evaluations, "schematic_job", "pilot")
    add("pilot physical nominal values", evaluations, "physical_nominal_response_job", "pilot")
    add("pilot physical construction", evaluations, "layout_drc_lvs_extract_bundle", "pilot")
    add("pilot reference solver repeats", p["topologies"]*3, "schematic_job", "pilot")
    add("pilot reference physical repeats", p["topologies"]*3, "physical_nominal_response_job", "pilot")
    add("pilot reference construction", p["topologies"], "layout_drc_lvs_extract_bundle", "pilot")
    add("pilot model fits", p["gpu_fits"], "gpu_fit_placeholder", "pilot_gpu")
    c, chips = m["corners"], m["chips"]
    c1 = m["claim1"]
    # All factorial jobs, no performance early exits; valid-design allocation.
    add("claim1 schematic full factorial", c1["designs"] * c * (1+chips), "schematic_job")
    add("claim1 extracted full factorial", c1["designs"] * c1["policies"] * c * (1+chips), "extracted_job")
    add("claim1 physical construction", c1["designs"] * c1["policies"], "layout_drc_lvs_extract_bundle")
    c2 = m["claim2"]
    for row in c2["schematic_label_rows"]:
        add("claim2 " + row["name"], math.prod(row["factors"]), "schematic_job")
    nominal = c2["nominal_response_designs"] * c2["nominal_response_directions"] * 2
    add("claim2 nominal response single registered corner", nominal, "physical_nominal_response_job")
    add("claim2 nominal perturbation construction", nominal, "layout_drc_lvs_extract_bundle")
    perturbed = c2["mismatch_response_designs"] * c2["mismatch_response_directions"] * 2
    add("claim2 mismatch central response full corners", perturbed * c2["mismatch_response_chips"] * c, "extracted_job")
    add("claim2 mismatch endpoint nominal scans", perturbed * c, "extracted_job")
    add("claim2 mismatch endpoint construction", perturbed, "layout_drc_lvs_extract_bundle")
    add("claim2 shared uncertainty nominal and chip vectors", c2["uncertainty_training_designs"] * c * (1+c2["uncertainty_training_chips"]), "extracted_job")
    add("claim2 uncertainty construction", c2["uncertainty_training_designs"], "layout_drc_lvs_extract_bundle")
    add("claim2 uncertainty schematic references", c2["uncertainty_training_designs"]*c, "schematic_job")
    for row in c2["gpu_fit_rows"]:
        add("claim2 " + row["name"], math.prod(row["factors"]), "gpu_fit_placeholder", "gpu")
    c3 = m["claim3"]
    for tag, episodes in (("3A test", c3["test_episodes"]), ("independent calibration", c3["calibration_episodes"])):
        count = episodes * c3["batch_candidates"]
        add(tag + " schematic values", count + episodes, "schematic_job")
        add(tag + " full nominal and chip vectors", count * c * (1+chips), "extracted_job")
        add(tag + " construction", count, "layout_drc_lvs_extract_bundle")
        add(tag + " base nominal values", episodes * c, "extracted_job")
        add(tag + " base construction", episodes, "layout_drc_lvs_extract_bundle")
    runs = c3["test_episodes"] * (c3["loop_rankers"] + c3["loop_baselines"])
    maximum = runs * m["candidate_cap"]
    sc = c3["scenario"]
    assert 0 <= sc["confirmations"] <= sc["nominal_passing_certification_attempts"] <= sc["certification_attempts"] <= sc["screen_20chip_candidates"] <= sc["candidate_checks"] <= maximum
    for scenario, checks, screens, certs, nominal_pass, confirms, rounds in (
        ("loop_scenario", sc["candidate_checks"], sc["screen_20chip_candidates"], sc["certification_attempts"], sc["nominal_passing_certification_attempts"], sc["confirmations"], sc["proposal_rounds_per_episode_method"]),
        ("loop_full_branch_cap", maximum, maximum, maximum, maximum, maximum, m["round_cap"]),
        ("loop_all_rejected_at_nominal_screen", maximum, 0, 0, 0, 0, m["round_cap"])):
        add("3B proposal schematic screens", runs*rounds*m["proposals_per_round"], "schematic_job", scenario)
        add("3B candidate construction", checks, "layout_drc_lvs_extract_bundle", scenario)
        add("3B original-corner nominal screen", checks, "extracted_job", scenario)
        add("3B independent 20-chip screen", screens*20, "extracted_job", scenario)
        # Reuse old-corner nominal job in the full 29-corner scan, not a second layout.
        add("3B remaining nominal scan", certs*(c-1), "extracted_job", scenario)
        add("3B fixed 250-chip certification", nominal_pass*chips*c, "extracted_job", scenario)
        add("3B fresh fixed 250-chip confirmation", confirms*m["confirmation_chips"]*c, "extracted_job", scenario)
    totals = {}
    for row in rows:
        totals[row["scenario"]] = totals.get(row["scenario"], 0) + row["core_hours"]
    totals["campaign_scenario_cpu_hours"] = totals["shared"] + totals["loop_scenario"]
    totals["campaign_full_branch_cpu_hours"] = totals["shared"] + totals["loop_full_branch_cap"]
    return rows, totals


def main():
    m = json.loads((ROOT / "protocol" / "experiment-manifest.json").read_text())
    stats = check_statistics()
    rows, totals = ledger(m)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "statistics.json").write_text(json.dumps(stats, indent=2)+"\n")
    (OUT / "ledger.json").write_text(json.dumps({"rows": rows, "totals": totals}, indent=2)+"\n")
    lines = ["# Executed protocol checks and resource ledger", "", "Generated by `protocol/check_protocol.py`. These are numerical checks and planning counts, **not circuit-pilot results**.", "", "## Statistical checks", "", "```json", json.dumps(stats, indent=2), "```", "", "## Resource rows", "", "All times use unmeasured manifest placeholders. Full-corner evaluation is budgeted even when per-chip failure early exits may save work. GPU rows are device-hours, not CPU core-hours.", "", "| Row | Scenario | Count | Unit | CPU/GPU hours |", "|---|---|---:|---|---:|"]
    lines += [f"| {r['name']} | {r['scenario']} | {r['count']:,} | {r['unit']} | {r['core_hours']:,.2f} |" for r in rows]
    lines += ["", "## Totals", "", "```json", json.dumps(totals, indent=2), "```", "", "The scenario and full-branch cap are alternatives, never added. Pilot is separate. Shared costs conservatively assume every allocated design is structurally valid. The scenario loop counts are inherited planning assumptions, **not estimated branch probabilities**. No 50-chip certificate path exists. Every nominal-passing certification and confirmation pays for 250 chips.", "", "A job-runtime multiplier of 2 and two complete-workload retry copies produce a sixfold CPU stress case; this is sensitivity analysis, not a confidence bound or forecast. Timeouts supply a different, much larger operational ceiling. Recompute from measured per-stage attempts, failure rates and runtime distributions before launch. Acquisition/intervention/ablation rows are explicit spending caps, not unbounded extra sampling. GPU fits are enumerated separately; their duration is an unmeasured placeholder. Tool installation, implementation, covariance estimation, model inference, proposer API charges and BO refits are not priced as simulator time and require separate measured operating allocations before full launch."]
    (OUT / "report.md").write_text("\n".join(lines)+"\n")
    print(json.dumps({"statistics": stats, "totals": totals}, indent=2))


if __name__ == "__main__":
    main()
