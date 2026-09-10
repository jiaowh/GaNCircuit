# Review of v13 and the v3 implementation plans

Reviewed: `phd-plan-v13.md`, `thesis-implementation-plan-v3.md`, and `claim1-implementation-plan-v3.md`, against the previous review. Date: 8 September 2026.

**Assessment: the research direction remains PhD-worthy, and the endpoint specification has materially improved. The full experimental protocol is still not ready to freeze.** The remaining problems are concentrated in statistical definitions, conflicting operative sections, and the interaction between the new sampling rule and the budget. Several are definite mathematical errors rather than questions to defer to a simulator pilot.

This review included document cross-checks and independent finite-binomial enumeration in JavaScript. It did not run ngspice, extraction or layout. The numerical checks assume independent Bernoulli chip outcomes, as the proposed yield procedure does. No plans were edited by this review.

## Corrections that now work at the design level

- `CERTIFY` re-scans the candidate's nominal corners and selects its own worst corner. The old episode corner is explicitly a screen.
- The endpoint selected by claim 1 is shared with the later claims, including escalation to all-corner mismatch.
- Unresolved simulations contribute outcome bounds instead of disappearing from the denominator.
- Nominal-failure inheritance follows the conjunction definition; yield-only escape is a separate mechanism measurement.
- Forward models are restored as scientifically relevant, with comparable reference-label calibration.
- The canonical parameter schema includes variable passives and sources, signed source encoding, realised displacement and group-based device correspondence.
- Study 3A explicitly bypasses performance early exits, and study 3B continues after failed or indeterminate confirmation.
- The proposed 3B selection rule guarantees four distinct natural models, and the intended analysis is reduced to paired utility contrasts.

These address the substance of earlier findings. However, a correct new paragraph does not resolve an incompatible old rule that remains in an operative section.

## Findings requiring correction

### 1. The conservative quantile has the wrong sign for upper-bound constraints

**Location:** thesis implementation §5.2, approximately line 687.

The rule evaluates every property at `nominal - 1.28*sigma`. This is conservative for a lower bound, such as minimum gain, but optimistic for an upper bound, such as maximum power. It would reward greater power uncertainty by making the evaluated power smaller.

For a Gaussian approximation in the stated physical units, use:

`q_i = mu_i - s_i * 1.28155 * sigma_i`

where `s_i=+1` for a lower-bound constraint and `s_i=-1` for an upper-bound constraint. Then evaluate the correctly signed margin at q_i. For lower bounds this is the 10th percentile, not the 90th percentile; for upper bounds it is the 90th percentile. If normality is assumed in transformed units, the quantile must instead be constructed and inverse-transformed consistently in those units. Signed two-sided constraints need both tails.

Even after fixing the sign, 90% marginal feasibility does not imply 90% joint feasibility: two independent 90% constraints have 81% joint yield. The worst marginal quantile can be a ranking heuristic, but cannot be described as matching the joint-yield endpoint. Validate it against joint probability or use a stated joint-risk allocation.

**Priority: blocking for the proposed ranking score.**

### 2. The new uncertainty calibration does not establish the claimed coverage

**Location:** claim 1 §1, approximately lines 82–91; repeated in the thesis and change logs.

Pooling is sensible, and calibrating the complete stopping rule is a legitimate approach. The statements that the current rule is an actually valid 95% interval and that inflating the discard rule cannot rescue its coverage are not established.

I independently enumerated `X~Bin(50,p)` and `Y~Bin(200,p)`. Stage 1 stops if its Wilson interval excludes 0.90; otherwise stage 2 reports the interval using X+Y and n=250. At z=2.40:

| True p | Final interval coverage | Probability of escalation |
|---:|---:|---:|
| 0.002 | 0.904747 | effectively zero |
| 0.0024 | 0.886793 | effectively zero |
| 0.88 | 0.974232 | 0.967502 |
| 0.90 | 0.976785 | 0.990645 |
| 0.95 | 0.980560 | 0.999970 |
| 0.98 | 0.987205 | effectively one |

On the grid p=0.780, 0.781, ..., 0.980, the minimum coverage is approximately **0.961081 at p=0.888**. The quoted 0.9685 therefore needs its actual grid and code attached; it is not a grid-independent property. More fundamentally, restricting calibration to 0.78–0.98 cannot support an interval claim for designs outside that range, and a finite grid alone does not certify the gaps between grid points. Low-p undercoverage does not itself imply excessive false certification at p<0.90; interval coverage and decision error are different estimands and should be tested separately.

The assertion that critical-value inflation cannot rescue the discard rule is also false on the stated calibration range. Keeping independent second-stage draws and using z=3 gives minimum coverage approximately **0.990673** over the same 0.001-spaced grid. Pooling is more efficient use of observations; it is not a necessary condition for adequate coverage.

**Fix:** choose a simple procedure with a stated guarantee, or provide full calibration code and the domain of the guarantee. One conservative option is exact binomial intervals with error allocated across the two possible looks; another is a valid confidence sequence. Use a separate rule for the 20-chip screen and fixed 200-chip confirmation: a calibration for the 50/250 stopping rule does not automatically calibrate those different experiments. [Time-uniform confidence sequences](https://arxiv.org/abs/1810.08240)

**Priority: blocking for the current statistical assurances.**

### 3. The calibration makes the cheap certification path impossible

**Location:** claim 1's yield rule; thesis implementation §5.5.

For all successes, the lower Wilson bound is `n/(n+z^2)`. With n=50 and z=2.40 it is:

`50 / (50 + 2.40^2) = 0.896700`.

Therefore **no candidate can certify 90% yield at the 50-draw stage**. Even 50/50 escalates to 250. The large escalation probabilities in the table above are not rare near-threshold exceptions; they include excellent designs.

The current scenario prices 960 3A candidates and 1,584 certification attempts at the 50-draw cost, relegating escalation to a generic 40% contingency. Each escalation adds `200*60/3600 = 3.333` core-hours. If those 2,544 evaluations escalate, the extra cost is **8,480 core-hours**, before other changes. That is a scenario illustrating the mismatch, not a forecast of their actual yield distribution. Every candidate that certifies must, however, have escalated under the present rule.

The table's printed rows correctly sum to **9,651 core-hours**. The problem is its branch assumptions, not addition. The claimed saving from reducing 3B from twelve rankers to six is also stale: **v2 already ran six**. Relative to v2, the new lower estimate instead relies on the changed ladder unit cost and assumed number of checks.

Other costs still need explicit treatment:

- The k/action sweep is priced only as ladder checks although it is a closed-loop experiment with certification and confirmation.
- 16,000 nominal perturbation layouts/extractions at 90 seconds each cost **400 core-hours**, not the stated 200.
- The mismatch-response line `40 designs × 12 directions × 50 draws` has one endpoint per direction. For central differences, as used elsewhere, it needs **48,000 draws**, not 24,000. A forward-difference design with reused base draws is possible, but must be named and costed that way.
- The all-corner endpoint selected on shortcut failure needs a separate scenario and reduction decision; 40% is not an adequate substitute for that branch.
- Define the primary budget ledger: whether a ladder evaluation, certification and confirmation are one candidate check or multiple charged checks. “Confirmation cost counts against the budget” is ambiguous when the budget is 25 checks, not simulator seconds.

**Priority: high. Do not freeze the resource commitment using the current total.**

### 4. Two incompatible primary analyses still coexist

**Location:** thesis implementation §5.4, approximately lines 731–751.

The new text explicitly limits 3B to paired contrasts with no ranker-level covariates. Immediately afterward, the unchanged **Primary model**, **Primary test**, power simulation and alternative-shape paragraphs reinstate the rejected fidelity/accuracy survival regression, ranker random effects, nested tests, free breakpoint and interactions.

This is not resolved by the canonical schema: that schema defines parameters and certification, not precedence between these statistical models.

**Fix:** replace the whole obsolete analysis block with separate 3A and 3B specifications. Specify the 3A model as carefully as the old survival model, including independent training replications and model-level clustering. State which question each study can answer. If 3B only compares chosen rankers, the headline claim should not still promise an independently established incremental fidelity-versus-search-cost relationship.

There is an additional selection problem: the fourth natural model is selected using **3A regret on the same 60 episodes later used in 3B**. That is adaptation to evaluation tasks, even though no gradient training occurs. Use separate calibration episodes, nested episode splits, or choose the models from independent claim-2 calibration data before exposing any final-test episode labels. Define “best natural” unambiguously in the paired contrasts.

**Priority: blocking for preregistration and confirmatory interpretation.**

### 5. Overlapping intervals are not ordinary Kendall tau-b ties

**Location:** thesis implementation §5.4, approximately lines 715–719.

Consider intervals A=[0,2], B=[1,3], C=[2.5,4]. A overlaps B and B overlaps C, but A is definitely below C. Treating both overlaps as equality ties would require A=B=C, contradicting the resolved A<C ordering.

Interval overlap is non-transitive; ordinary tied ranks are equivalence classes. Consequently “tau-b against that partial order” is not a complete specification of a standard Kendall tau-b calculation. The standard implementation consumes paired rankings/values and their equality ties. [SciPy Kendall tau documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.kendalltau.html)

**Fix:** measure concordance only over resolved pairs, retaining the comparable-pair fraction, or define a proper interval/partial-order metric. Report uncertainty bounds for top-k regret. Do not force overlapping intervals into ordinary tie labels unless using an explicitly defined transitive grouping with the lost information disclosed.

Also, a calibrated interval for a Bernoulli pass fraction is **not an interval for a property quantile or quantile margin**. Those score intervals require their own estimator and uncertainty procedure. Thus the candidate score, its uncertainty and the rank statistic must be defined together.

**Priority: blocking for the stated ranking statistic.**

### 6. Chip yield, design feasibility and certification are still mixed

**Location:** thesis implementation §5.2 and claim 1 §1.

The propagated joint probability is the probability that **one random chip** passes all constraints. The certified verdict is the result of a statistical procedure deciding whether the design's underlying yield clears 0.90. Those are different random events. Taking Brier score between the chip-pass probability and the design-certified verdict is not a calibrated scoring test of either quantity.

**Fix:** score predicted chip yield against independent chip outcomes or observed pass fractions using a suitable observation model. For design-feasibility calibration, predict `P(underlying yield >= 0.90 | available data)` with epistemic uncertainty, or explicitly predict the probability of the certification algorithm returning PASS. Do not use the same probability for all three.

The proposed censored likelihood has a related problem. A sample-derived confidence interval is not an interval known to contain the latent yield. Integrating a latent-yield model over that interval as though it were an observed censoring range is not automatically a valid likelihood. Use the observed success/failure counts and the sampling protocol in a binomial/hierarchical model, with a defensible treatment of unresolved draws. Similarly, the two label-based survival curves are not guaranteed to bracket truth when definite labels can be wrong; they bracket assignments of indeterminate labels conditional on the definite labels being correct. State and propagate the remaining uncertainty.

**Priority: high for the population and calibration conclusions.**

### 7. The ranking mechanism is disconnected from the selected model set

**Location:** thesis implementation §§4.6, 5.2 and 5.4.

The nine natural rankers remain A, B and B-S across three training conditions. The arm that learns offset derivatives is separately named **B-S-z**, with **B-mc** as an alternative. Neither appears in the selected ranker set. Yet §5.2 says ranking uses propagated sigma and covariance and that models without offset supervision use nominal margins only.

As written, the main ranker experiment does not clearly contain the models needed to test its uncertainty-aware score. If B-S is implicitly replaced by B-S-z, that must be explicit and its extra information and label cost controlled.

**Fix:** supply a small table giving each selected ranker's training labels, available nominal/uncertainty outputs, ranking score, calibration access and cost. Either keep all rankers on a common nominal score for a nominal study, or introduce explicit, matched comparisons for mismatch-aware ranking. Avoid confounding a fidelity contrast with access to an entire additional uncertainty model.

**Priority: high for connecting claim 2 to claim 3.**

### 8. The repaired-design shortcut check has no operational failure rule

**Location:** canonical schema §2.7; claim 1 corner-shortcut validation.

Forty repaired candidates are re-evaluated at all corners, but the text says their result is reported rather than specifying what happens if the shortcut fails on them. Zero discrepancies in 40 still supports only a 7.2% one-sided upper discrepancy bound. It cannot recertify the claimed 5% tolerance for the repaired population; reducing this to twenty widens the bound further.

The claim-1 sample-size arithmetic for 60 independent, exactly classified designs is correct. But the discrepancy itself is estimated from noisy, possibly indeterminate certification labels. Separate an operational certificate-disagreement rate from an underlying-yield disagreement rate. The denominator for false acceptance among shortcut passes is the number of shortcut passes, not the total sample of sixty.

**Fix:** define a repaired-population acceptance bound, sampling denominator and escalation/rerun rule. For all-corner mismatch, also state whether the target is minimum per-corner yield or the probability that the same random chip passes every corner; those are different events. Make confirmation use the selected endpoint, not silently return to worst-corner-only draws after all-corner escalation.

**Priority: high for the physical-verification scope of the final result.**

## Numerical check method

The coverage values above were obtained by summing exact binomial probabilities, evaluated in double precision using log-factorials, over all first-stage counts 0–50 and additional counts 0–200. There was no Monte Carlo simulation error in the enumeration. Wilson bounds used:

`center = (k/n + z^2/(2n)) / (1 + z^2/n)`

`halfwidth = z*sqrt((k/n)*(1-k/n)/n + z^2/(4n^2)) / (1 + z^2/n)`.

The final interval was the n=50 interval when it excluded 0.90, and the n=250 pooled interval otherwise. The discard comparison used only the second count and n=200. This specifies the rule sufficiently to reproduce the reported points and distinguishes it from alternative implementations that use different critical values for screening and reporting.

## Readiness and the next step

The theoretical framing is now much stronger than the original plan. This review does not suggest abandoning the topic or adding more model arms by default. The present risk is treating accumulated correction paragraphs as an executable research design.

Before another version expands the plan, produce three compact, authoritative artifacts:

1. **Endpoint and uncertainty specification:** exact sampled event, sampling/stopping rules, interval procedure, unresolved outcomes, confirmation and shortcut escalation.
2. **Analysis specification:** one score and uncertainty definition for 3A, a small set of 3B contrasts, model selection on independent calibration episodes, and clear limits on what each study establishes.
3. **Executable experiment manifest:** branch probabilities from the actual sampling rule, model roster, nominal scans, chip draws, layouts, certifications and confirmations. Recompute the scenarios from it.

Delete superseded operational paragraphs rather than asking readers to resolve them. The detailed v13 source-of-truth policy is useful, but it is not a substitute for one internally consistent analysis.

**Recommendation:** proceed with a bounded pilot once the mathematical rules above are corrected. The early fidelity-versus-ranking pilot remains an open scheduling decision rather than a committed milestone; it is still the most valuable early test of the PhD premise. The full campaign and four-year half-time resource commitment remain conditional on that evidence.
