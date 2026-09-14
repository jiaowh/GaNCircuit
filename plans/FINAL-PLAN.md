# Final consolidated research plan

> **Historical research protocol.** On 11 September 2026 the project owner redirected the project toward a reusable agent toolset, with custom semiconductor-device design and circuit co-design from the start. Read the [active toolset plan](autonomous-circuit-toolset-plan.md). The text below is preserved for the earlier experiment; its frozen priorities, exclusions and resource gates do not govern the new toolset programme.

9 September 2026. Working title: **Local response fidelity, candidate ranking and model-based physical verification of AI-sized analog circuits.**

The research direction is retained. The next committed task is a small fidelity-versus-ranking pilot, followed by a measured resource decision. This is the final operational consolidation; there is no further numbered prose revision scheduled. New experimental measurements populate the manifests and result tables, rather than adding competing definitions.

## Read these three operational artifacts

1. [Endpoint and uncertainty specification](protocol/endpoint.md): sampled event, fixed sample size, exact intervals, unresolved outcomes, screening, repeated-search confirmation, and physical parameters.
2. [Analysis specification](protocol/analysis.md): matched model roster, fixed-candidate ranking, resolvable pairs, independent calibration, paired repair contrasts, and claim-1 inference.
3. [Executable experiment manifest](protocol/experiment-manifest.json) and its [generated resource report](results/protocol-check/report.md): actual jobs in each branch, with separate CPU/GPU/physical-construction ledgers.

The previous latest plans are replaced by pointers to this document, with their full text preserved as historical background. Old operational paragraphs, resource totals and changelogs have no authority over these three artifacts. Literature motivation, device-model observations and optional-project discussions remain available in the archive; none is reverified merely by being archived.

## Decisions now fixed

* Fixed **250-chip exact binomial certification** replaces the grid-calibrated 50/250 Wilson procedure. There is no cheap 50-chip certification budget. The 20-chip screen and adaptive-loop confirmation each have their own explicit rule.
* The physical certificate requires nominal pass and **the same random chip passing every constrained property at every one of the 29 corners**. Worst-nominal-corner results are diagnostics, not equivalent certificates. This resolves shortcut scope, cross-corner coupling, and repaired-design escalation by removing substitution altogether. It is a stricter, more expensive endpoint than v13's shortcut, deliberately exposed in the ledger.
* Upper-bound marginal diagnostics use the upper quantile; lower bounds use the lower quantile. Joint predicted yield is computed separately and is never inferred from 90% marginal feasibility.
* Interval overlap produces unresolved pairs, never Kendall tau-b equality ties. The score is a yield probability with its own binomial interval; quantile margins do not inherit that interval.
* Study 3A estimates incremental ranking information. Study 3B uses three paired utility contrasts only. The superseded multi-predictor survival regression and causal mediation are removed.
* All headline natural rankers receive the same uncertainty-information access. Rankers are selected on independent calibration episodes, before any final-test labels are exposed.
* Chip calibration uses chip outcomes. The separate operational certificate predictor uses the three protocol outcomes. No single probability is scored against both events.
* Continuous moves and k=2 are the committed repair condition. Finger, action/k sweeps, the separate proposer diagnostic and shortcut-validation campaigns are removed. The compact-model bridge, crossbar tile and chip are outside this execution commitment.

## Pilot: first empirical decision, not a late optional milestone

The pilot tests whether nominal response fidelity distinguishes useful rankers at practical action sizes. It makes **no mismatch-yield or full physical-certificate claim**. That narrower question can be answered before paying for the full stochastic endpoint.

Use the five-transistor OTA and Miller OTA, ALIGN only, at tt/1.80 V/27 °C. Reproduce the registered reference sizing, testbench and layout for both before training. If either cannot be reproduced, record a two-topology pilot failure; do not silently substitute an easier circuit. Report a completed one-topology result as such, with the gate unmet.

Per topology and independent training panel, draw 512 legal sizing designs. Three panels and A/B/B-S give 18 small per-topology MLP fits. All arms get identical value-label access, including the central-difference endpoints. B-S alone adds derivative supervision within a subspace of rank min(4,d-1), where d is the number of continuous sizing coordinates and d>=2 is required. The four requested directions lie in that subspace; d<=4 does not license full-rank derivative supervision. Use the manifest's architecture, optimiser, epochs and loss weight; standardise each output from training data only. Arm B and B-S receive the same nominal reference label as A. Fix the training seeds and the derivative subspace before generating labels. No hyperparameter search in this pilot.

Use 8 independent calibration bases and 12 independent final-test bases per topology. Each base gets eight common legal candidates: four seeded random directions, each at requested maximum coordinate changes 0.02 and 0.10 decades, within-bin and grid-valid, with invalid proposals counted and replaced up to 100 draws per base. Use signed-source changes in the registered transformed coordinate scale. Generate directions outside the trained subspace for the transfer diagnostic; candidate ranking uses the same directions for every arm and the full realised displacement. Freeze test bases, candidates and model predictions before opening test labels. Exclude training runs and near-duplicates using the analysis specification. No language-model proposer is required for this bounded pilot.

Obtain schematic nominal properties for each base/candidate and nominal extracted properties after regenerating its layout. Primary ranking truth is the extracted worst-property **nominal** margin at the single pilot corner; every valid candidate is evaluated, including nominal failures. Secondary ranking truth is the schematic margin. Rankers are trained on schematic labels and use their predicted nominal margin in both comparisons: the physical comparison explicitly measures transfer across extraction, not physical-model training. It may fail because of that transfer gap; keep the two results separate. Propagated uncertainty U is not needed in this pilot.

Run three repeated deterministic simulations of each reference before collection. Define solver tolerance as max(1e-4 dimensionless margin, five times the largest observed repeat difference). If this exceeds 0.01, stop and diagnose the testbench. Candidate differences within this tolerance are unresolved. Structural failures remain a separate bottom outcome; report concordance among scorable pairs separately from structural-failure detection. Report response RMSE, global/local/limiting-property value RMSE, resolvable-pair concordance and top-1/top-2 regret for every model, action size and topology. Bootstrap whole base episodes for descriptive intervals; with three panels this is a feasibility study, not the final 3A association test.

Use calibration bases to select one model per arm by lowest mean top-2 nominal extracted regret, tie-breaking by panel ID. Open final-test labels once. Do not choose the best topology or action scale after looking at test results. Publish a full result table even if fidelity loses to local value error.

Pilot gates, evaluated once:

1. Both topology/reference flows pass DRC/LVS and produce finite, repeatable property vectors; at least 90% of attempted candidate layouts are structurally valid.
2. At least 18 of the 24 test bases have a nonempty resolvable-pair set and at least 25% of candidate pairs are resolvable when pooled within each topology.
3. On independent calibration data, natural models span at least a 20% relative response-RMSE range (best vs worst, denominator worst). Report the value-error range alongside it; a manufactured corruption does not satisfy this gate.
4. No positive-effect gate: a null or reversed fidelity/ranking relation with gates 1–3 satisfied is a valid pilot result and is retained. It supports an estimation study, not a promised fidelity advantage. If gates 1–3 fail, stop the full programme at the corresponding infrastructure/range/resolution limit and publish that limitation.
5. Before full launch, the measured stage-runtime distribution and available compute must cover the explicit endpoint ledger; the power/split/baseline gates in the analysis specification must also pass. Neither a favourable pilot nor the old total overrides this gate.

## Concrete work order and deliverables

| Order | Task and acceptance evidence | Output |
|---|---|---|
| 1 | Acquire and pin ngspice, Magic, netgen, ALIGN/Sky130 PDK, reference netlists and testbenches; verify licences and model switches. Build a container; hash everything. | `pilot-inputs/toolchain.json`, per-topology input files |
| 2 | Implement canonicalisation, testbench adapter, layout/DRC/LVS/extraction, per-stage timeouts, result/status schema and caching. Reproduce both references, deliberate DRC failure, explicit-offset identity and solver repeats. | reference QA report and timings |
| 3 | Implement A/B/B-S training and the fixed-batch evaluator. Generate frozen train/calibration/test partitions, labels and predictions. | model/data hashes; disjoint split audit |
| 4 | Run the bounded pilot and evaluate the five gates without changing them. | model-by-base results, uncertainty and gate decision |
| 5 | Only if gates pass, populate physical calibration data and measure all-corner sample costs. Pin baseline implementations and run the pre-test power calculation. | measured manifest, exact budget allocation, frozen episode IDs |
| 6 | Launch claim 1, then final 3A and 3B against the frozen endpoint and analyses, within the approved compute allocation. | papers, reproducible database and execution ledger |

These are implementation tasks, not claims that a simulator pipeline already exists. Missing tool/model facts are preflight requirements, not guessed constants. `.SENS` is optional; finite differences are the reference. A new topology, finger action, uncertainty method, or device chapter is outside the committed run list.

## Resource decision

The [generated report](results/protocol-check/report.md) supersedes every previous budget table. It prices all nominal scans, full 250-draw certifications, fresh 250-draw confirmations, construction reuse, independent calibration, central-difference endpoints and the remaining loop branches. There is no claim of savings from twelve rankers becoming six: **v2 already used six**. The original 9,651-hour rows summed correctly; their assumptions were inadequate.

The stricter reference event makes the original population and loop breadth very expensive. The current placeholder ledger gives roughly **966,000 CPU core-hours** for the full campaign scenario and **5.06 million** for the all-candidates-reach-every-stage branch at the same unit runtimes, before measured retry overhead. Those totals are scenario calculations, not forecasts, and the latter is a branch-count cap rather than a wall-time bound. The full scenario alone is about 3.45 years at uninterrupted, perfectly utilised 32-core throughput; real queues and failures add time. **The old full campaign is therefore not committed as a feasible four-year half-time workload.** Do not launch it on the strength of the 13,500-hour estimate.

The pilot allocation is about **37 CPU core-hours plus 18 GPU-hours** using unmeasured per-job/per-fit placeholders, excluding installation and implementation effort. It is the bounded work that starts now. The full programme requires a measured compute allocation or a separately scoped follow-on study; silently weakening the certificate is not the reduction rule. This is a resource gate with a concrete stop outcome, not an invitation to keep revising prose until the estimate looks small.

## Checks completed in this workspace

Run `python3 protocol/check_protocol.py` to reproduce the numerical checks and ledger; run `python3 protocol/pilot_preflight.py` to check local simulator/input availability. Both scripts use the Python standard library. In this Windows workspace Python was available through Ubuntu/WSL.

The executed checks reproduced the feedback: the old 50/50 lower Wilson limit is **0.8967001435** and the old adaptive interval's coverage at p=0.002 is **0.9047468180**. Under the replacement fixed-250 rule, preliminary certification requires at least **235 successes**, and the per-episode error-allocated confirmation requires at least **239**. At true joint yield 0.95, the confirmation test passes only about **40.16%** of independent attempts; at 0.98 it passes about **99.50%**. This conservatism is a real cost of the stated repeated-search guarantee, not hidden in a contingency allowance. The grid regression check passed; the coverage guarantee itself comes from exact tail inversion, not that grid.

The [executed pilot preflight](results/pilot/preflight.json) is **blocked**: ngspice, Magic, netgen, a configured PDK, the two testbenches and pinned layout inputs are absent. **Zero circuit simulations have been run.** No synthetic data are presented as empirical pilot evidence. The specification and numerical checks are ready; the first executable research task is the toolchain/reference reproduction in row 1 above.
