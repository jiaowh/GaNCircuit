# Recheck of the edited PhD plans

Reviewed 8 September 2026: `phd-plan-v12.md`, `thesis-implementation-plan-v2.md`, `claim1-implementation-plan-v2.md`, and `audit-evaluation-2026-09-08.md`.

**Verdict: substantial scientific improvement; suitable for a supervisor discussion and a bounded feasibility pilot, but not yet a consistent protocol for the full experiments.** The revised thesis proposition is defensible as a PhD hypothesis. Several operational rules still invalidate, or leave undefined, the measurements supporting it. No circuit toolchain was executed in this review. Numerical checks below use the documents' stated assumptions.

## What the revision resolves

The following are substantive corrections, rather than wording changes:

- The thesis now asks about incremental value beyond task-matched accuracy and allows size, selection and interaction effects.
- The non-separability gate is removed, with correct complete-pair loss algebra and consistency diagnostics.
- Derivative supervision is restricted to a rank-deficient subspace, with a full-space comparator.
- The interpretation of probes is limited to decodability; behavioural response fidelity is the main construct.
- Margin definitions are invariant to physical-unit changes, with gains converted out of dB for ratio margins.
- Passive values and testbench/layout context are added to model inputs.
- Offset sensitivity receives explicit supervision; propagation includes cross-property covariance and retains the simulator-linearisation control.
- Claim 3 is separated into fixed-candidate and closed-loop studies, with natural versus deliberately corrupted models distinguished.
- DRC, grouped holdouts, early reservation of evaluation episodes, power planning and conditional preprint release are added.

The FALCON amendment is valid: stored pairs can measure finite response error without re-simulation. My earlier audit correctly described the old probes-only protocol as insufficient for response replication; the new stored-pair protocol adds a legitimate measurement. It still does not establish controlled local derivatives or process transfer.

The evaluation document is also right that the device bridge, tile and chip were already gated. The remaining workload concern is that opening a gate requires available time as well as data: the core workload has grown despite those projects being optional.

## Remaining findings, in priority order

### R1 — Blocking: claim 3 does not operationally implement the claim 1 endpoint

**Locations:** thesis implementation §5.1, lines 557–569; claim 1 §1, lines 61–69.

Claim 1's PCM requires nominal pass across the corner set and mismatch evaluation at the design's nominal worst corner. Claim 3's ladder checks the *starting episode's* worst corner, then accepts using “worst corner” without an explicit new 29-corner nominal scan for each repaired candidate. Sizing changes can change the worst corner. Reusing the old corner does not implement PCM for the new candidate.

Also, claim 1 can escalate to PCM-full as its primary endpoint, while claim 3 explicitly fixes PCM and claims to inherit the shortcut validation. The protocol needs to inherit the *outcome* of that validation, including escalation. A shortcut checked on claim 1's original designs is not automatically valid on repaired designs, particularly after finger changes.

**Fix:** write a single executable endpoint definition: nominal scan on the new candidate, selection of its worst corner, then the specified mismatch test. The old corner can remain an inexpensive screening rung. Record the endpoint selected after claim 1 validation, propagate it to all later studies, and validate shortcut performance on a random sample of repaired designs. Recost accordingly.

### R2 — Blocking: uncertainty labels do not yet have the claimed inferential validity

**Locations:** claim 1 §1, lines 61–96; thesis implementation §5.1.

The two-stage rule uses 50 draws, stops if their Wilson interval excludes 0.90, and otherwise substitutes a fresh 200-draw interval. Pre-registering this rule does not make the selected interval a 95% confidence procedure.

I enumerated the two independent binomial stages using a two-sided normal critical value of 1.95996398454. At true p=0.90, the final selected interval covers p with probability **0.927729**, not 0.95. At p=0.88, coverage is **0.930765**. These calculations concern the stated ideal Bernoulli model, before numerical failures or repeated candidate selection.

Three further issues remain:

- **Numerical failures are excluded from the yield denominator.** This estimates yield conditional on solver convergence. Failure to converge may correlate with unstable or badly biased circuits; the 10% inspection threshold does not remove bias below that threshold. For example, 92 passing draws and 8 unresolved draws produce an apparent 100% conditional pass fraction, while the all-draw pass fraction is unresolved between 92% and 100%.
- **Indeterminate labels are not integrated into the analyses.** The eight-class decomposition assumes definite P/C/M outcomes; the predictor and hierarchical model remain binary. A stacked label-frequency plot measures certification outcomes, not directly the fraction of circuits whose underlying yield exceeds the threshold. Explicit handling of indeterminates is still needed in decomposition, training and inference.
- **Final confirmation does not change the solved endpoint.** Claim 3 stops on an initial acceptance and merely reports an independent confirmation afterward. That estimates time to preliminary certification plus a confirmation rate, not time to confirmed success. Both are legitimate, but they must be named separately or the loop must continue after failed/indeterminate confirmation.

**Fix:** calibrate the complete two-stage test, use an appropriate confidence sequence or an explicit error-spending procedure, or adopt fixed-sample validation. Use reproducible solver retries followed by unresolved-outcome bounds. Define analysis rules for all three labels. Distinguish preliminary certification from independently confirmed success. Time-uniform inference provides one established approach to adaptive sampling. [Howard et al.](https://arxiv.org/abs/1810.08240)

### R3 — High: the shortcut-validation thresholds are not statistical assurances

**Location:** claim 1 §1, lines 55–66.

Agreement on 38/40 designs is a 95% observed proportion, not evidence that true agreement is at least 95%. Its ordinary 95% Wilson interval is approximately **83.5%–98.6%**. Even zero discrepancies in 40 independent designs gives a one-sided 95% upper discrepancy bound of about **7.2%**. Likewise, zero yield-only escapes in 200 designs gives an upper bound of about **1.49%**, so that sample cannot certify a rate below 1%.

These thresholds can be operational pilot heuristics, but should not be described as validation of a population error tolerance. Agreement can also be dominated by indeterminate–indeterminate pairs, concealing poor discrimination among plausible passes.

The inheritance rule contains a separate logical redundancy: after nominal pass becomes an explicit conjunction, nominal-failing designs fail that conjunction regardless of their yield-only escape rate. Measuring their yield is useful for mechanism analysis; its escape rate does not determine whether conjunction failure can be inherited.

**Fix:** decide whether the tolerance is descriptive or inferential. For the latter, choose sample sizes and acceptance counts from a confidence bound or calibrated test. Report false acceptance among shortcut passes and the indeterminate fraction separately. Separate conjunction bookkeeping from yield-only mechanism measurements.

### R4 — Blocking: “fully evaluated batch” conflicts with early stopping

**Location:** thesis implementation §5.4, lines 604–605, and §5.5.

Study 3A promises the simulator's true ordering of all sixteen candidates. But evaluating each candidate “through the ladder and the accept criterion” still permits stopping after a failing rung. That may establish endpoint failure without measuring every property needed for the proposed worst-margin ranking. Two rejected candidates can remain unordered, and some apparently rejected candidates can be sampling-noise rejects.

**Fix:** in 3A, bypass performance early exits for candidates with valid layouts and obtain the common numerical score needed for ranking. Structural failures can be assigned an explicit bottom category, with ties. Alternatively redefine 3A as binary screening and measure precision/recall or detection of a feasible candidate, without claiming full numerical ordering. Monte Carlo-based rankings need tie/uncertainty rules even after every candidate is evaluated.

### R5 — High: the budget still has verifiable errors and omissions

**Location:** thesis implementation §5.5, lines 639–652; claim 1 §5.

At the stated 60 seconds per extracted chip simulation:

| Item | Written estimate | Arithmetic or unresolved cost |
|---|---:|---:|
| 400 confirmations × 200 chips | 270 core-hours | **1,333.3 core-hours** |
| 960 fully evaluated 3A candidates | 360 core-hours | **800 core-hours for 50 chips each alone**, before layout, corners or extra draws |
| Same 960 candidates, including 29 nominal corners and 50 chips | not explicitly costed | **1,264 core-hours**, before layout/extraction and adaptive reruns |
| Sum of listed core-hour rows | about 9,800 | **9,820**, consistent with the rounded total before correcting individual rows |

Replacing only the confirmation row brings the printed-row sum to approximately **10,883 core-hours**. This is not a corrected total: other omissions still need resolution.

The accept line multiplies solved episodes by an accept cost, but every provisional candidate can incur acceptance simulations, including candidates that fail or remain indeterminate. The number of acceptance attempts is not the number of solved episodes. Claim 1 also budgets '+150' near-threshold runs while its text says **200 fresh** draws replace the original 50; this is 250 total draws, not 200.

Physical response measurements remain costed as 16,000 single post-layout simulations. If the target is a mismatch quantile or yield, each perturbed design requires multiple chips; if it is a nominal property only, say so and limit the claim. Regenerated layouts and corner scans also need explicit rows. A P-only finger dataset supplies nominal extracted finger-response evidence, not automatically PCM mismatch evidence.

**Fix:** make the experiment manifest concrete before asserting that the budget closes. Separate candidate checks, corner scans, chip simulations, acceptance attempts and final confirmations. Keep scenarios, but calculate every scenario from one set of consistent rules.

### R6 — High: the reduced closed-loop study still promises analyses on unavailable models

**Location:** thesis implementation §5.4, lines 610–627; §5.8 and §8.

Study 3B runs six rankers: three natural range representatives, the best natural model, and two corrupted models. This supplies **at most four distinct natural rankers**, possibly fewer if “best” duplicates an extreme. Later paragraphs still require every fit on “nine natural” and “all twelve” models. Those fits are available for 3A, not 3B's check-count outcome.

The survival regression retains several correlated accuracy measures, multiple covariates, random ranker effects, a free breakpoint and interactions. Four natural rankers do not necessarily make every episode-varying coefficient unidentifiable, but provide very weak model-level generalisation evidence. Merely scheduling a power simulation does not settle this.

**Fix:** write separate analysis specifications for 3A and 3B and define unique ranker selection. Put the broad model-quality association study in 3A; make 3B a small set of preplanned paired utility contrasts, or add independent natural model replications and simplify its regression. Set the minimum practically meaningful effect from circuit-design decisions, rather than transplanting an effect size from another domain.

### R7 — High: response fidelity has been overcorrected into a requirement for pairwise models

**Location:** thesis implementation §4.1, line 205.

The statement that only B/B-S can carry a mechanism not already determined by pointwise accuracy is too strong. For a forward model, response error is indeed the difference of endpoint errors. But global or local *summaries* of value accuracy do not determine the spatial covariance of those errors. A constant-bias predictor can have substantial value error and exact responses; an oscillatory error with comparable value MSE can yield poor responses. This remains a legitimate fidelity-versus-summary-accuracy question for arm A.

**Fix:** retain A as a scientifically relevant model, not an arm that pairwise models must beat to make the thesis valid. Frame the mechanism as local error structure, candidate ordering and constraint decisions. For pairwise absolute predictions, give A equivalent access to the measured reference label, especially on held-out topologies; otherwise B receives one-point calibration that A does not. Define reference values per testbench/physical context rather than one property vector for every context.

### R8 — High: the operational device and parameter definitions still contradict the corrections

**Locations:** thesis implementation §§2.3–2.4, 4.1–4.2 and 5.1; claim 1 §3.

- Thesis §5.1 still says repaired candidates are “snapped to model bins”; claim 1's actual `canonicalise` stage still says “Geometric checks, then bin snap.” These are executable rules, so the corrected introductory prose does not override the ambiguity safely.
- A map requiring every extracted device to belong to exactly one schematic device permits splitting but excludes true many-to-one merging, despite claiming support for both. Use equivalence groups or preserve separately instantiated devices where independent mismatch draws matter. A scalar aggregation cannot automatically preserve nonlinear responses under different local parasitics.
- The continuous vector now includes only transistor W/L. If Cc, resistances or bias-source values are intended sizing actions, they must enter the independent parameter vector and derivative protocol. Adding them as input features alone does not do this.
- Source-value features use logarithms without rules for zero or negative sources; use sign/magnitude or another explicit finite encoding.
- A derivative at the requested direction is not necessarily a derivative along the realised grid-quantised displacement. Record actual endpoint displacement, or use smooth schematic derivatives and validate finite grid moves separately.

**Fix:** replace the duplicated prose definitions with one canonical schema for parameters, contexts, transformations, legal moves, device correspondence and measured targets.

## Additional points to settle before preregistration

1. “No training signal ever touched” the orthogonal complement is too strong: value labels across designs contain information about variation in those directions. The valid statement is that no *direct derivative labels* supervise that complement. Compare improvement against B on the same directions; an S-versus-complement gap alone does not prove absence of transfer. Report the coordinate metric used to define orthogonality.
2. The ranker predicts “every property at the signoff cell,” but a stochastic cell has no single property vector until a statistic is specified. Choose nominal values, quantiles, moments or joint-yield scores explicitly. Define the limiting property for mismatch-induced joint failure and how uncertainty produces the claimed Brier/calibration score.
3. Reserving an episode pool at month 6 is good. Excluding every topology–specification cell containing one episode is much stronger than run-level deduplication and can remove most training data if episodes cover all cells. Enumerate retained training/evaluation counts before freezing the split; reserve a sufficiently large pool if month 28 power analysis may increase episode count.
4. A fresh Monte Carlo seed does not make a repeatedly tuned-on design a fresh test design. Keep validation and final test designs distinct, in addition to independent mismatch draws.
5. The novelty matrix is promised but not yet supplied. The opening still uses universal claims about all reported AI success numbers. Narrow those to named studies and endpoints. I re-opened the cited Bian–Xie preprint: the arXiv record exists, lists the authors and a 25 August 2026 submission. It can be moved from “existence unconfirmed” to “verified preprint, assess overlap.” This does not establish peer review or correctness of its results. [arXiv record](https://arxiv.org/abs/2608.24963)

## PhD viability after revision

The revised proposition is substantially more defensible than v11. It no longer relies on novelty of derivative supervision, a guaranteed failure of aggregate accuracy, or a causal interpretation of probes. A rigorous result about when local response information adds practical value under physical constraints could support a PhD.

The execution risk has not fallen proportionately: additional arms, covariance evaluation, finger campaigns, common-batch evaluation and more elaborate inference have increased the work. The central utility premise is still tested around months 32–34. Run a small fixed-batch study with per-family models in the first six months, before committing to the full graph/probe programme. This is a pilot, not a demand to restrict every eventual generalisation claim to four topologies.

**Recommended next revision:** correct R1–R8, instantiate the experiment manifest and a single endpoint specification, and run the small feasibility study. These are protocol consolidation and validation tasks; they do not require another round of adding model arms or ancillary research topics. I would endorse the research direction conditionally, but would not yet sign off the full experiment plan or its four-year half-time schedule.
