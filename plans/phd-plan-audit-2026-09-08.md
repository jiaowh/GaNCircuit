# Professional audit of the PhD research and implementation plans

Date: 8 September 2026

**Verdict: a credible PhD direction requiring major revision before full execution.** The research question is worthwhile. The current experiments do not yet support several of the claims they are meant to establish, and the proposed four-year, half-time schedule is insufficiently evidenced. I would support a bounded feasibility phase, conditional on the corrections below, rather than approve the complete experimental programme unchanged.

Reviewed: `phd-plan-v11.md`, `thesis-implementation-plan-v1.md`, and the incorporated `claim1-implementation-plan.md`. The implementation plan's corrections take precedence when assessing the intended design; they do not make the contradictory statements in v11 suitable for submission. This is a document, mathematical and targeted primary-source audit. No simulator or layout pipeline was executed. The workspace contains plans and literature, but no implementation or experimental results demonstrating readiness. This review does not certify every literature entry or establish an exhaustive absence of prior art.

## 1. Does this qualify as a PhD?

Potentially, yes. PolyU requires an original proposition supported by evidence and argument that makes a significant contribution to knowledge, alongside sustained independent research. A paper count is not a substitute for that proposition. The proposed sequence—physical verification failures, surrogate response fidelity, and consequences for repair decisions—can form a coherent empirical doctorate. [PolyU research postgraduate handbook](https://www.polyu.edu.hk/gs/rpghandbook/section2/)

| Dimension | Assessment |
|---|---|
| Importance | Strong: expensive physical verification is a meaningful bottleneck. |
| Coherence | Strong if all chapters address when a surrogate can support reliable physical-design decisions. |
| Originality | Plausible at the circuit-specific combination level; overstated at the general methodological level. |
| Scientific validity | Several major defects remain, especially direction holdouts, change-model consistency and yield definitions. |
| Technical feasibility | Plausible on a reduced set of circuits; unproven across the proposed populations and tools. |
| Statistical feasibility | Not demonstrated: few independent topologies and rankers, noisy yield labels, and no prospective power analysis. |
| Half-time schedule | Overextended as written; integration and experimental multiplicity are underestimated. |
| Department fit | Unresolved. The core belongs naturally in EDA/electrical engineering with ML expertise; Applied Physics acceptance needs explicit supervisory agreement. |

The strongest original contribution would be a **validated, actionable criterion for when circuit surrogates can safely screen physical repair candidates**, with controlled evidence explaining its scope. A benchmark can support that contribution. Showing that gradients matter, that accuracy and utility differ, or that derivative supervision sometimes helps is insufficient by itself.

The plan has real strengths: explicit falsification branches, simple controls, provenance, fixed evaluation snapshots, censored optimisation outcomes, conventional baselines that may win, and separation of simulator linearisation error from learned-model error. Preserve these.

## 2. Findings that affect the thesis's validity

### F1. The novelty statement is too broad

**Location:** research plan §3; implementation §§4.13 and 5.

The assertion that nobody in circuits “or elsewhere” measures surrogate response or Jacobian agreement in connection with search is not defensible as written. Sobolev training already targets derivatives; Tsay studies derivative-trained surrogate optimisation; Giovannelli and colleagues analyse function, gradient and Hessian approximation and downstream optimisation. DNN-Opt establishes that change-conditioned circuit prediction is not a new model category. [Sobolev training](https://arxiv.org/abs/1706.04859), [Tsay 2021](https://www.sciencedirect.com/science/article/pii/S0098135421001976), [Giovannelli et al.](https://arxiv.org/abs/2311.12253), [DNN-Opt](https://arxiv.org/abs/2110.00211)

A recent preprint also directly studies the dependence of surrogate benefit on its role, local operating radius and the base solver. It is relevant overlapping work, not proof that this circuit study has been done. [Bian and Xie, August 2026 preprint](https://arxiv.org/abs/2608.24963)

**Fix:** build a comparison matrix covering derivative accuracy, local finite-change error, constrained ranking, post-layout targets, mismatch, and held-out search utility. Claim originality only for the documented combination and resulting insight. Replace “accuracy does not” with a test of *incremental predictive value beyond strong, task-matched accuracy metrics*.

### F2. The non-separability acceptance rule rewards inconsistency with the target

**Location:** implementation §4.3; decision D4.

For a deterministic property, the exact change is

`D(a,b) = f(b) - f(a)`.

It is inherently separable and obeys `D(a,a)=0`, antisymmetry and cycle consistency: `D(a,c)=D(a,b)+D(b,c)`. An accurate change model should approach these identities. Requiring its anchored-pair discrepancy to exceed a positive threshold can reject the correct limit and reward approximation error.

An unrestricted pair architecture is a legitimate empirical arm; non-separability is not a scientific success criterion. Also, for a separable predictor with point errors e_j, complete all-pairs squared loss equals `2N Σ(e_j - mean(e))²`, rather than ordinary single-point squared loss in general. It leaves a constant offset unidentified. The proposed sparse distance-weighted pair sampling changes the loss further.

**Fix:** remove D4 as a pass/fail requirement. Compare forward and pairwise training with matched resources. Report cycle consistency as a diagnostic. Define exactly how arm B supplies absolute property estimates for the aggregate-accuracy comparator, and which pair argument is differentiated at which anchor for its Jacobian.

### F3. The held-out-direction test can leak the complete Jacobian

**Location:** implementation §§4.3 and 4.5.

At a fixed design, directional derivatives are linear measurements `y=Ug` of the gradient g. If the trained directions have rank equal to the number of free continuous variables, the entire gradient is identified; another direction is a new linear combination, not withheld derivative information.

The dictionary has coordinate directions, intervention directions and forty random directions. Its 40% training subset can already span the full parameter space of these small circuits. Uniform random projections each epoch also conflict with the stated fixed trained/untrained dictionary unless restricted to the training subspace.

**Fix:** distinguish held-out direction vectors from genuinely withheld subspaces. Construct a rank-deficient training subspace, evaluate its orthogonal complement, and report rank and conditioning at each design. Hold out designs and neighbourhoods independently. If different training points use different subspaces, describe what information is withheld locally and globally. Do not interpret this test as evidence that a representation “contains but does not use” a property.

### F4. The “read versus use” interpretation exceeds the instruments

**Location:** implementation §§4.5, 4.11 and 8.

A probe recovering a property establishes decodability under the probe protocol. A wrong predicted response establishes behavioural approximation error. Neither demonstrates that a particular internal representation causally mediates the prediction. A retrained supervised head on the skeleton establishes learnability within that model class; it is not necessarily a certificate about the original frozen representation.

Property-isolating directions may not exist: after projecting a property's gradient away from other property gradients, the remainder can be zero or numerically negligible. Circuit trade-offs and tied sizing variables make this a practical concern. Regressing out co-movement over a large nonlinear path does not recover a causal intervention on one property.

**Fix:** make behavioural response fidelity the primary construct. Use singular-value diagnostics and constrained least squares to find feasible interventions, reject ill-conditioned cases, and disclose residual co-movement. Treat probes as optional supporting evidence. Claims about internal causal use require separate representation interventions and validity checks.

### F5. The geometry rules conflict with continuous sensitivity experiments

**Location:** claim 1 §1; implementation §§2.2, 2.3, 4.1 and 5.1.

“Snap to the nearest model bin” conflates model selection with geometry quantisation. ngspice selects bins using width/length intervals, not a universal list of permitted point geometries. Some process intervals can be narrow; the actual installed model and layout grid must determine feasibility. [ngspice manual, model binning](https://ngspice.sourceforge.io/docs/ngspice-manual.pdf)

If every perturbation is snapped back to a discrete representative, a small central difference can become identically zero and a larger one a jump. Differentiating an unconstrained smooth model would then estimate a different function from the pipeline. Multiplicity and fingers are also not automatically continuous variables.

**Fix:** separate layout grid, valid model intervals, tied device parameters, integer multiplicity and finger counts. Preserve valid continuous geometries within bins; project only genuinely invalid actions under a stated rule. Differentiate with respect to independent continuous parameters. Record no-op perturbations and bin crossings. Choose finite-difference steps relative to bin clearance and numerical convergence, with checks over representative operating regimes rather than one design per family.

### F6. Physical targets are not fully defined by the model inputs

**Location:** implementation §§4.2, 4.6 and 5.2.

The graph's stated features omit numerical values for several device classes, and do not explicitly condition on testbench load, supply, temperature or layout policy. If these vary, the same recorded input can have multiple legitimate outputs. The repair ranker must predict physical changes under two policies, yet policy conditioning is not specified.

A deterministic fixed layout policy can be learned implicitly from sizing. Two policies must be distinguished; if layout is stochastic, its seed or conditional distribution must be handled. Finger changes also require non-default finger assignments in the training or calibration data; claim 1's default-only layouts do not supply this coverage.

**Fix:** define a target function such as `f(T,x,z,corner,load,policy)` or explicit separate models where context is fixed. Include passive/source values and all relevant testbench context. Specify whether each target is a nominal property, corner-specific property, quantile, joint yield or worst-case statistic. Supply the physical training-label budget and a dedicated finger experiment.

### F7. Offset inputs alone cannot identify mismatch sensitivity

**Location:** implementation §§4.3, 4.6 and 4.9.

From training values only at z=0, the functions `fhat(x,z)` and `fhat(x,z)+a(x)·z` fit nominal data equally well but have arbitrary different offset sensitivities. Supplying a zero-valued input and known mismatch coefficients does not resolve this.

Derivative labels in offset directions can resolve it, so the propagation idea is feasible. The written protocol must specify which designs get those training labels and what they cost. Central differences themselves require off-nominal simulator evaluations. “No per-chip training” should mean no dense Monte Carlo training, not no mismatch-related supervision.

Also, correct marginal standard deviations do not establish joint multi-specification yield: cross-property covariance and nonlinear tails matter. Under the linear Gaussian approximation the natural object is `J_z J_zᵀ`, not only its diagonal.

**Fix:** specify nominal-only, offset-derivative-supervised and sampled-offset controls. Keep the excellent simulator-Jacobian versus Monte Carlo decomposition. Limit conclusions to simulated spread unless joint yield is separately validated. Use a fresh final mismatch sample independent of training and candidate selection.

### F8. The verification endpoint is inconsistent, and one implication is false

**Location:** claim 1 §1; implementation §§3.1 and 5.1.

Claim 1 calls worst-nominal-corner Monte Carlo “signoff”, with all-corner Monte Carlo on a subsample. Claim 3 calls all 29 corners with mismatch the full claim-1 accept criterion. These are different endpoints. The nominal worst corner need not be the corner with the lowest yield.

The statement that a nominal failure cannot reach 90% yield is false in general. As a mathematical counterexample, let a property be z² with standard-normal z and require it to exceed 0.01. The nominal value fails, while about 92% of draws pass. This is not a prediction about the benchmark; it disproves the proposed general implication.

It is legitimate to require both nominal pass and yield pass, but that must be an explicit conjunction. Skipped cells then remain unmeasured, not observed evidence of a pure mismatch or interaction effect.

**Fix:** define nominal robustness, minimum per-corner yield and simultaneous across-corner yield separately. Choose a common primary endpoint. Validate any corner shortcut with a predeclared error tolerance and escalation rule. Run the full factorial on a representative diagnosis subset if interaction attribution is claimed. The seven combinations of sufficient single-factor failures plus interaction-only also need an explicit mapping to claim 3's four episode strata.

### F9. Yield labels and adaptive stopping need uncertainty treatment

**Location:** claim 1 §§1, 6 and 7; implementation §5.1.

For true yield near 0.9, the approximate standard error is 0.042 at 50 samples and 0.021 at 200. Point-estimate thresholding therefore produces uncertain binary labels precisely where the study concentrates. Wilson intervals across designs do not account for this within-design classification uncertainty. The rule describing an estimate lying in the “Wilson interval of the threshold” is also ambiguous; the intended rule is presumably that the sample's interval contains the threshold.

The twenty-chip ladder can reject good near-threshold candidates by sampling noise. Repeatedly selecting candidates using noisy passes can overstate final success without an independent acceptance sample.

**Fix:** choose either a finite-Monte-Carlo operational endpoint or inference about underlying yield, and label it accordingly. For the latter, use a valid sequential/confidence procedure or a prespecified two-stage rule whose error is evaluated by simulation. Allow indeterminate cases, retain counts, and use fresh final validation draws. Include unresolved simulator failures in an explicit numerical-status policy.

### F10. Claim 3 compares fidelity against an inadequately matched alternative

**Location:** implementation §§4.1 and 5.4.

Limiting-property response error is tailored to the decision; global aggregate error dilutes that information. Outperforming it could reflect localisation or property weighting rather than a distinct response-fidelity mechanism. Sign accuracy relative to the starting design does not determine the ordering of two improving candidates.

For arm A, response error equals the difference between two pointwise prediction errors. This makes local error structure and correlation important competing explanations.

**Fix:** compare against limiting-property value error, local candidate-distribution error, feasibility calibration, candidate-ranking agreement and top-k regret, as well as global accuracy. Use common fixed calibration sets and scales. Replace the ambiguous dimensional-log margin normalisation with dimensionless ratios for positive quantities or physically meaningful fixed tolerance scales for signed/zero-threshold properties. The identified limiting property should not change merely because bandwidth is expressed in Hz instead of MHz.

### F11. Claim 3 has too few independent model units and biased ranking observations

**Location:** implementation §§5.4 and 5.8.

Sixty episodes times twelve rankers is not 720 independent observations about model quality. Fidelity varies substantially at the ranker level, and rankers sharing architecture, data and training procedures are dependent. A crossed-effects survival analysis is sensible, but cannot manufacture independent information. Leave-one-ranker-out validation may retain nearly identical training conditions in the training fold.

Constructed-shortcut and noise-damaged models may drive the correlation. That would establish behaviour under controlled corruption, not a predictive rule for naturally trained models. Kendall tau computed only on selected candidates is subject to selection bias; the discarded candidates are exactly those needed to evaluate screening quality. Changing proposer history also changes candidate distributions between rankers.

**Fix:** run two linked experiments: a fixed-candidate, fully evaluated ranking study isolating the ranker, and a closed-loop study measuring realised utility. Separate natural and deliberately degraded models. Add independent training replications, simulate power using realistic clustering/censoring, and validate by training-condition and topology groups. Use random fully evaluated proposal batches for ranking diagnostics. Treat mediation as exploratory unless its causal assumptions are established.

### F12. Coverage versus quantity is framed as a predetermined answer

**Location:** research plan §§2 and 4; implementation §§4.4 and 4.7.

There is no general reason quantity must have a flat effect while coverage matters. More data can improve coverage; boundary sampling can improve boundary performance while reducing global performance. Rejection sampling to change correlations can also change property marginals, density and effective support. The data-pruning result does not make distance to a circuit specification threshold equivalent to example difficulty.

**Fix:** estimate size effects, selection effects and their interaction without requiring a flat axis. Define measurable coverage and evaluation distributions. Match marginals where possible and disclose residual shifts. Count candidate screening, rejected simulations and derivative labels in acquisition budgets. Report both equal-design-count and equal-simulator-cost comparisons. FALCON probes alone are a supporting replication of representation findings, not a replication of response fidelity.

### F13. Population breadth and physical validity are overstated

**Location:** claim 1 §§2, 3, 6 and 7; research plan §1.

Many specification sets on the same circuit do not create independent topologies. Ten seeds per generator/circuit give imprecise per-cell survival curves, especially after margin filtering. Increasing seeds cannot repair missing topology diversity. Same-design layout policies are paired; independent two-proportion tests ignore that pairing. Trajectory-based training also requires run/topology/near-duplicate grouping, not only exact design-ID exclusion.

The pipeline specifies LVS but no explicit post-generation DRC acceptance stage. A tool's claim to generate legal layouts does not establish DRC-clean output for every sizing. One-to-one schematic-to-extracted device correspondence may fail when fingers are split or parallel devices merged, affecting mismatch covariance and correspondence.

**Fix:** use topology-based groups, distinguish supported-population survival from end-to-end generator success, and report stage exclusions. Use paired policy comparisons and clustered uncertainty. Add explicit DRC and extraction sanity checks against small reference structures. Define split/merge device mapping and mismatch aggregation. Describe the endpoint as model-based physical verification under the stated kit and flow; reserve claims about manufacturing survival for evidence that supports them.

## 3. Implementation viability and budget

The implementation plan is more concrete than v11, but its counts are not a defensible upper bound.

**Claim 3 acceptance costs:** a full accept run with 29 corners and 50 chips is 1,450 extracted simulations. At the plan's own 60 seconds per simulation, that is approximately **24.2 core-hours per candidate**, before layout and extraction. At 200 chips it is approximately **96.7 core-hours**. The table assigns about 1,100 core-hours collectively to accept runs, validation, k sweeps and action-set conditions: this covers only about 45 of the smaller accept runs before those other tasks. There are 1,080 method–episode combinations even before the sweeps. These are scenario calculations, not predictions of actual solve rates, but they invalidate the claimed upper-bound interpretation.

**Experimental multiplication:** three k values and three action sets can multiply loop runs by nine if fully crossed. The advertised extra 3,000 checks do not establish coverage of that design. Training seeds, tuning, units, capacity controls, folds and skeletons also multiply model fitting. Three dataset-selection strategies × four sizes × four unconditional arms × three seeds already gives 144 fits before those extras.

**Missing cost semantics:** nominal labels reused from claim 1 have an acquisition cost; derivative-labelled arms consume extra simulator calls; physical sizing perturbations need regenerated layouts unless the experiment deliberately holds parasitics fixed. Monte Carlo gradients need a definition and sampling budget. At 32 workers, dividing core-hours by 32 assumes adequate memory, independent throughput and no serial bottleneck.

**Readiness:** AutoSizer's public README documents optional ALIGN/Magic flow and limited layout support, but a documented code path does not demonstrate reproducibility on this population. The reviewed README gives broad subset wording, not a definitive four-circuit layout support list; the implementation's proposed correction to v11 should remain unconfirmed until tied to a specific commit. [AutoSizer repository](https://github.com/yuxi120407/AutoSizer)

**Required budget revision:** enumerate every experimental cell in a machine-readable manifest; separate proposals, schematic calls, layout/extraction calls, per-corner chip simulations, final validation, GPU fitting, API cost and storage. Measure representative median and tail runtimes, include failed jobs, and apply a contingency supported by the pilot. Training amortisation should be shown as cost per solved design over realistic reuse counts, not assumed free.

## 4. A viable thesis scope and execution sequence

Suggested thesis proposition:

> Under specified layout and statistical process models, local response fidelity on active circuit constraints provides incremental information about repair decisions beyond task-matched value accuracy. Its value depends on training coverage, action scale and proposal quality; controlled experiments identify when it improves physical-verification efficiency and when it does not.

This is a hypothesis to test, with effect sizes and boundary conditions. It avoids asserting in advance that aggregate accuracy is useless or quantity irrelevant.

**Minimum defensible scope:** one process; initially three or four genuinely distinct amplifier topologies; one validated layout policy; one conventional and one AI-assisted generator; forward, pairwise and derivative-supervised models; per-family controls; a fixed-candidate ranking experiment; and one closed-loop repair study with strong conventional baselines. The exact final topology/model counts must follow the power and generalisation objectives, rather than these pilot counts being treated as sufficient for all claims.

Move probes/description length, FALCON replication, the second layout policy, the full units battery and expanded generator comparisons behind explicit value-and-resource gates. Remove the compact-model bridge, crossbar tile and chip from the committed thesis workload. They can remain extensions. Adding a device chapter to secure departmental fit would create another substantial research project; it does not substitute for agreement that the core thesis belongs in the department.

**First 8–12 weeks:** run one complete DRC/LVS/RC-extraction example, then a small population; establish independent continuous variables and numerical sensitivity convergence; demonstrate explicit mismatch replay and validate its distribution; fix the yield endpoint; time the complete accept criterion. Produce reproducible logs and reference cases.

**By month 6:** test the central fidelity-versus-ranking premise with simple per-family models, common candidate batches and natural training differences. Run a small repair pilot. This should precede the full graph/probe programme. If the useful error variation appears only in manufactured failures, reassess practical significance at this point, not month 18 or 30.

**Subsequent work:** expand the physical study to the justified population, complete controlled coverage and derivative experiments, then run the powered utility comparison. Treat paper dates as targets conditional on evidence quality. “Preprint regardless of completeness” is inappropriate where the missing work concerns the validity of the headline endpoint.

A reduced programme can plausibly fit four to five part-time years with reliable EDA support and protected research time. That is a planning judgment, not a demonstrated schedule. The current breadth should not be committed without pilot measurements and named supervisory expertise.

## 5. What an examiner would need to see

1. One clearly stated original proposition, positioned against derivative-aware optimisation and circuit-sizing prior art.
2. A physically and numerically validated reference pipeline, with precise limits on manufacturing claims.
3. Experiments that isolate response fidelity from local value accuracy, training budget, proposal quality and artificial model damage.
4. Uncertainty estimates and generalisation tests at the topology, training-condition and episode levels.
5. A useful conclusion: a selection rule, failure diagnostic, demonstrated efficiency gain, or a precisely bounded negative result that changes what practitioners should do.

Reporting both outcomes is good scientific practice. It does not make every outcome a doctoral contribution. A null effect with narrow, practically meaningful bounds across credible settings can be important. An inconclusive result from low power, an unidentifiable model or a broken pipeline cannot serve the same role.

**Recommendation:** retain the topic, revise the central experimental logic, narrow the committed scope, and authorise a feasibility phase with deliverable-based gates. The main risk is not lack of possible papers; it is completing a large amount of implementation without obtaining valid evidence for the thesis's central proposition.
