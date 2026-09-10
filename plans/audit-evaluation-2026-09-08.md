# Evaluation of the professional audit, 8 September 2026

Assessed against `phd-plan-v11.md`, `thesis-implementation-plan-v1.md`, `claim1-implementation-plan.md` and `papers/README.md`. Each finding is checked for factual accuracy against the source text, mathematical correctness where it makes a mathematical claim, and whether the plans already address it.

**Overall: the audit is sound.** Every one of F1–F13 identifies a real defect. Nine are upheld in full, four need qualification, none is wrong. The arithmetic it does check out. Its weakest habit is failing to credit places where the implementation plan already fixes what it criticises in v11.

---

## Scoreboard

| # | Verdict | Severity | Cost to fix |
|---|---|---|---|
| F1 novelty too broad | Upheld, qualified | Low–moderate | Hours (wording) |
| F2 non-separability rule | **Upheld** | High | Days |
| F3 held-out directions leak | **Upheld — strongest catch** | High | Weeks |
| F4 read-versus-use overreach | Upheld | Moderate | Days |
| F5 geometry vs sensitivity | **Upheld** | High | Weeks |
| F6 targets underdetermined | **Upheld — two decisive sub-findings** | High | Weeks |
| F7 offset identifiability | **Upheld** | High | Days (design) + sim budget |
| F8 endpoint inconsistent | Upheld; counterexample correct but narrow | High | Days |
| F9 yield label uncertainty | Upheld | Moderate–high | Days |
| F10 mismatched comparator | **Upheld — contains the single best catch** | High | Days |
| F11 too few units, biased tau | Upheld, one qualification | High | Structural |
| F12 coverage framing | Upheld | Moderate | Days |
| F13 breadth and physical validity | **Upheld** | High | Structural |
| §3 budget | Upheld, arithmetic verified | High | Downstream of F8 |
| §4 scope | Partly already implemented | — | — |

---

## F1. Novelty statement too broad — upheld, with qualification

The quoted target is real. v11 §3: *"What no prior work measures, in circuits or elsewhere, is a surrogate's per-property response to a design change against the simulator's, or its Jacobian agreement, and whether that quantity predicts search cost."* "Or elsewhere" is not defensible against the derivative-free and model-based optimisation literature, where the quality of a model's gradient approximation is explicitly tied to optimisation behaviour.

Three qualifications:

1. **Two of the four citations are already yours.** Sobolev training (arXiv 1706.04859), Tsay 2021 and DNN-Opt are all in `papers/README.md` (lines 80, 83, 101) and cited in the plans as *method sources*, not overlooked prior art. DNN-Opt's change-conditioned critic is already explicitly conceded in implementation §5 ("v9's remark that no prior change-prediction model exists inside circuits is withdrawn"). The audit presents ground you have already given up.
2. **Only Giovannelli (arXiv 2311.12253) actually bites**, because it is the one that analyses gradient/Hessian approximation quality *and* downstream optimisation together. It is not in the folder. Get it.
3. **The Bian and Xie preprint (arXiv 2608.24963) is unverifiable from this workspace** and is not in `papers/`. It is doing load-bearing work in the audit ("directly studies the dependence of surrogate benefit on its role, local operating radius and the base solver") — if real, it is the closest overlapping work in the whole review. Verify it exists before you rewrite §3 around it.

Note also that `papers/README.md` line 169 already states the gap correctly and narrowly: *"No prior work measures per-property response fidelity or Jacobian agreement with the simulator. State the gap that narrowly."* Your own index is more careful than v11 §3. This is a wording slip, not a conceptual error.

The audit's fix "replace 'accuracy does not' with a test of incremental predictive value" is **already implemented** in §5.4 — the nested likelihood-ratio comparison with both directions of nesting reported. The audit did not credit it.

## F2. Non-separability acceptance rule — upheld

Mathematically correct and it lands. For a deterministic property, `D(a,b) = f(b) − f(a)` *is* separable by construction. A model that approaches the truth approaches separability. §4.3 requires the anchored-pair discrepancy to *exceed* a pre-registered threshold, and D4 (month 8) makes it a pass/fail gate. So the gate penalises accuracy.

I verified the audit's algebra. For a separable predictor with pointwise errors `e_j`, the complete all-pairs squared loss is

```
Σ_a Σ_b (e_b − e_a)² = 2N Σ e² − 2(Σ e)² = 2N Σ (e_j − ē)²
```

Correct, and it makes the sharper point the audit only gestures at: the pairwise loss is **invariant to adding a constant to every pointwise error**, so a constant offset is unidentified. Your §4.3 claim that "the pairwise loss provably reduces to a single-point loss" is therefore true only up to centring and a factor of 2N. Worth restating precisely, since the whole non-separability apparatus is built on it.

**One overstatement in the audit:** it says the rule "can reject the correct limit". Strictly, §4.3 and D4 *relabel* arm B as collapsed and rewrite the comparison around A, B-S and B-J. The consequence is that a well-fitting arm B gets dropped from the headline, which is bad in the way the audit says, but "reject" is too strong.

The two ancillary gaps the audit finds are real:

- **Arm B has no absolute property estimate**, yet §4.1 defines aggregate accuracy (R², MRE) on absolute values and §4.11 figure 1 plots "one point per model" against it. Arm B's point on that axis is currently undefined.
- **Arm B's Jacobian is ambiguous.** §4.1 defines Jacobian agreement as "the model's gradient of property i with respect to x". Arm B takes two designs. Which argument, at which anchor, is unspecified.

Both must be fixed before the month-8 pre-registration freezes.

## F3. Held-out direction test leaks the Jacobian — upheld; the strongest single catch

Two distinct problems, both real.

**The rank argument.** §4.3's dictionary is coordinate directions + per-property intervention directions + 40 random unit directions, with 40% marked trained. On a 20–35 variable topology that is roughly 29 trained directions in a 20–35 dimensional space. Directional derivatives are linear measurements `y = Ug`. A trained set of that size generically spans the whole space, so the full gradient is identified and an "untrained" direction is a linear combination of trained ones — no derivative information is withheld. Instrument 6's stated interpretation, *"the cleanest available evidence of a model that contains a property without using it"* (§4.5), does not survive this. Any observed gap would measure optimisation and generalisation slack, not withheld information.

**The internal contradiction, which the audit found and which is worse.** §4.3 says both:

> "Forty per cent of the dictionary is marked trained and used in B-S's derivative term; the remainder is untrained and is the substrate of instrument 6."

and, four sentences later:

> "Derivatives are supervised through random projections onto directions drawn uniformly from the unit sphere, one per sample per epoch."

These are mutually exclusive. If supervision is on fresh uniform random projections each epoch, then over training every direction is trained in expectation and instrument 6 measures nothing at all. This is a flat contradiction inside one subsection, and instrument 6 is one of the seven load-bearing instruments. **Resolve this before anything else in claim 2.**

The audit's fix is correct: construct a genuinely rank-deficient training subspace, evaluate on its orthogonal complement, and report the rank and conditioning of the trained set at each design.

## F4. "Read versus use" exceeds the instruments — upheld

Correct in principle: a probe establishes decodability under the probe protocol, and a wrong predicted response establishes behavioural error. Neither licenses a claim that a particular internal representation causally mediates the prediction. All of your instruments except the probes are **input-space** interventions; none is a representation intervention. Combined with F3 (which removes instrument 6's interpretive force), the "contains but does not use" language is not supported by the instrument set.

Partly self-aware: §4.13 already says "the intervention test, not the probe, is the load-bearing instrument". The fix is largely to demote the language, which is cheap.

Two specific catches worth acting on:

- **Instrument 4's status is ambiguous.** §4.5 says "a separate head on the same skeleton and the same data". If the backbone is retrained, this certifies learnability in the model class, not the frozen representation. State which.
- **Property-isolating directions may not exist.** §4.5 builds `u_i` as the component of ∇f_i orthogonal to the span of the other monitored properties' gradients. With ~12 monitored properties and strongly coupled circuit trade-offs (gain and bandwidth, in particular), that residual can be numerically negligible. The plan has no conditioning check. Add singular-value diagnostics and an explicit rejection rule for ill-conditioned designs — cheap, and it prevents you from constructing directions that are pure numerical noise and then interpreting the model's response to them.

## F5. Geometry rules conflict with continuous sensitivity — upheld

The technical point is right and it matters. ngspice model binning selects a model card by W/L *interval*; it does not impose a discrete set of permitted geometries. So claim 1 §1's *"each device's W and L are snapped to the nearest sky130 model bin"* conflates two different things, and the real quantisation source — the layout grid — is never separated out.

The consequence the audit draws is the damaging one. Claim 2 §4.1 defines changes as continuous 2% steps in log-sizing space, and §2.3 computes central differences at that step. If every perturbed geometry is snapped back to a discrete representative, then a 2% step is either a **no-op** (identical netlist, derivative identically zero) or a **jump** to the next representative. The learned model, differentiating an unconstrained smooth function, then estimates a different object from the one the pipeline produces. Your entire derivative-supervision and Jacobian-agreement programme sits on this.

Also correct, and easy to miss: **multiplicity is not continuous.** §4.1's design vector takes `log10` of width, length *and multiplicity*, and steps 2% in it. Multiplicity is an integer that goes 1, 2, 3. A 2% step in `log10(m)` is meaningless.

The fix list is right: separate layout grid from valid model intervals from tied parameters from integer multiplicity and fingers; preserve continuous geometries within a bin; differentiate only with respect to genuinely independent continuous parameters; log no-op perturbations and bin crossings. Add step-size convergence checks across operating regimes — §2.3's "1% and 4% run once per family" is thin for a quantity this load-bearing.

## F6. Physical targets not fully defined by the model inputs — upheld; two decisive sub-findings

The general point (same input, multiple legitimate outputs) is correct, and two of its instances are concrete enough to check.

**Missing passive and source values — verified.** §4.2's device node features are: log width, log length, log multiplicity, finger count, bin index one-hot, four mismatch slopes. Node *types* include resistor, capacitor, current source, voltage source — but there is **no resistance, capacitance or source-value feature anywhere**. Width and length are meaningless for a compensation capacitor. As specified, the model cannot distinguish two designs that differ only in Cc. On Miller-compensated amplifiers — three of OSIRIS's five circuits — Cc is a first-order determinant of bandwidth and phase margin, which are exactly the properties claim 1 reports as failing after layout. This is a straightforward specification bug and it invalidates the skeleton as written.

**Finger coverage — verified, and it breaks half of claim 3.** Claim 1 §1's finger rule is "the minimum valid finger assignment satisfying the topology's matched-pair constraints, applied identically under both policies" — a deterministic function of topology and sizing. Amendment A10 adds an override that is "unused in claim 1". So every training design has fingers determined by the rule, the finger feature is collinear with sizing across the entire training set, and the model has never observed a finger response. Claim 3 §5.1 then makes ±1 and ±2 fingers a headline action set and asks that model to rank the resulting candidates. It cannot. Either budget a dedicated finger-variation labelling campaign or drop the discrete action set from claim 3's headline.

Testbench context (load, supply, temperature) and layout policy are also absent from §4.2's features while varying across families and across claim 3's two policies. The audit's `f(T, x, z, corner, load, policy)` framing is the right correction.

## F7. Offset inputs alone cannot identify mismatch sensitivity — upheld

The identifiability argument is elementary and correct: from data at `z = 0` only, `fhat(x,z)` and `fhat(x,z) + a(x)·z` are indistinguishable, so `∂fhat/∂z` is arbitrary. Supplying a zero-valued input and the known slope coefficients does not help.

The specific casualty is v11 §4's headline framing: *"a faithful sensitivity gives the spread with no per-chip training at all."* That is only true for a model that was somehow given offset-direction information. Arms A and B never are. Arm B-S is (v11 §4: supervision "in sizing and in per-device offsets"; §2.3 budgets a 0.5-σ step for offset parameters), so the propagation test is meaningful *for B-S* and vacuous for the others — which is not how §4.6 or figure 7 present it. The audit's phrasing is right: "no per-chip training" should mean no dense Monte Carlo training, not no mismatch-related supervision. State which designs get offset derivative labels, and cost them: 4 parameters × n_devices × 2 runs is 120 simulations per design on a 15-device circuit, and §4.9 currently buries this.

**The covariance point is also correct and cheap to act on.** §4.6 produces per-property marginal `sigma_hat_i` only. Under the linear-Gaussian approximation the full object is `J_z J_zᵀ`; the diagonal alone cannot give joint multi-specification yield, which is what claim 1's pass fraction and claim 3's variation-limited specifications actually depend on. You already compute `J_z`, so the off-diagonals are free. Until they are validated, scope the propagation conclusion to per-property simulated spread.

Keep the `sigma_sim` / `sigma_MC` / `sigma_hat` three-way decomposition — the audit is right that it is the best thing in §4.6.

## F8. Verification endpoint inconsistent, one implication false — upheld, with the counterexample correctly scoped

**The inconsistency is real and expensive.** Claim 1 §1 defines cell PCM as "extracted, worst corner, MC" and calls it signoff; PCM-full (all 29 corners × MC) runs on a 40-design subsample as a *validation* of that shortcut. Claim 3 §5.1 then defines its accept criterion as "the full signoff cell of claim 1, extracted, all 29 corners, 50 chips" — which is PCM-**full**, not PCM. Two different endpoints under one name. The audit's observation that the nominal worst corner need not be the lowest-yield corner is also correct: the worst corner is selected at cell PC with nominal devices, then mismatch is run only there.

**The counterexample is mathematically correct.** Claim 1 §1 asserts *"a nominal failure cannot reach a 90% pass fraction"*. Take a property `z²` with `z ~ N(0,1)` and require it to exceed 0.01: the nominal value is 0 and fails, while `P(|z| > 0.1) = 0.920`. The implication is false in general.

**But its practical bite is limited, and the audit says so itself** ("This is not a prediction about the benchmark"). The counterexample needs a specification that is a lower bound on a quantity minimised at nominal. For gain, bandwidth, power and phase margin the nominal is the median or the best case, so the shortcut is probably safe in practice.

The half that does bite is the second-order one: **skipping PM and PCM for P-failures means those cells are unmeasured, not observed.** Since the failure decomposition in claim 1 §1 is presented as a partition summing to one, and claim 3 §5.1 stratifies its episode set on that partition, a censored cell propagates into both. Make the conjunction (nominal pass AND yield pass) explicit rather than deriving one from the other.

The strata-mapping gap is real: claim 1's decomposition has **eight** classes (seven non-empty subsets of {parasitic, corner, mismatch} plus interaction-only), claim 3 §5.1 draws 15 episodes apiece from **four**. A design failing both P and C belongs to two "sufficient" classes and the mapping is undefined.

**One thing the audit misses here:** there is no guarantee claim 1 produces 15 interaction-only episodes at all. That stratum requires designs that pass P, C and M individually yet fail PCM. If parasitic-sufficient failures dominate — which PANDA's single reported op-amp suggests — the stratum could be near-empty, and §5.1 has no contingency for a stratum that cannot be filled.

## F9. Yield labels and adaptive stopping — upheld

The standard errors check out: at true yield 0.9, `sqrt(0.9·0.1/50) = 0.042` and `sqrt(0.9·0.1/200) = 0.021`. With `Y* = 0.90` as a hard threshold, the binary label is genuinely uncertain exactly where the study concentrates its attention, and Wilson intervals *on the survival curve across designs* do not represent within-design classification uncertainty.

**The ambiguity the audit flags is a real drafting error.** Claim 1 §1 and implementation §3.1 both say designs whose pass fraction "lies within the Wilson interval of the threshold" get 200 chips. `Y* = 0.90` is a constant; it has no Wilson interval. The intended rule is presumably that the *sample's* interval contains 0.90. Fix the wording — it is a pre-registered rule.

**The 20-chip ladder rung is worse than the audit says: it has no stated pass criterion at all.** §5.1 says the ladder "stops at the first failure" but never defines failure for rung 2. If the natural reading (≥90% of 20, i.e. ≥18) is intended, then a candidate at true yield exactly 0.90 passes with probability `P(X≥18) = 0.677` for `X ~ Bin(20, 0.9)` — a third of genuinely acceptable candidates are discarded by sampling noise, and the discard is silent.

The winner's-curse concern is real, though slightly overstated: §5.1 does run the accept criterion as a separate evaluation on the provisional pass, so there is some independence. The bias that remains is selection across many noisily-screened candidates within an episode, not absence of a fresh sample.

## F10. Claim 3's comparator is inadequately matched — upheld; contains the best catch in the audit

**The confound is real and it is the central methodological problem with claim 3.** §5.4 pits "response error on the limiting property" against "aggregate accuracy" (§4.1: R²/MRE per property on held-out designs). These differ along three axes at once — response vs value, limiting-property vs all-property, local vs global. Winning tells you nothing about which axis did the work. The fix is cheap because you already compute the ingredients: add limiting-property *value* error, local candidate-distribution error, feasibility calibration and top-k regret as comparators.

**The arm-A observation is deep and undercuts part of claim 2's framing.** §4.1 defines the predicted change for arm A as the difference of two predictions. So for arm A, and for the supervised head, response error is *identically* a difference of two pointwise errors. It is not an independent quantity; whether it "comes apart from aggregate accuracy" is a question about the local correlation structure of pointwise error, not about a distinct fidelity mechanism. Only arms B and B-S can carry an independent mechanism at all. The thesis statement should say so.

**The margin-normalisation catch is the single most valuable item in the audit, and it is worse than stated.** The margin is `m_i = s_i(x_i − t_i)/|t_i|` with gain-like and bandwidth-like properties converted to log units *first*. That composition is not scale-invariant. For a 10 MHz bandwidth against an 8 MHz target:

- in `log10(Hz)`: `(7 − 6.903)/6.903 = 0.014`
- in `log10(MHz)`: `(1 − 0.903)/0.903 = 0.107`

A factor of 7.6 between two equally defensible unit choices. The **limiting property is the argmin over properties of this quantity**, so the identity of the limiting property can flip on a unit change. That is not a cosmetic issue: the limiting property drives

- claim 1's survival-curve τ axis and its headline figures,
- claim 3's episode diagnosis and stratification,
- the ranker's objective in §5.2 step 4 ("ordered by predicted worst-property margin"),
- and the definition of "response error on the limiting property", which is claim 3's primary regressor.

Note that §4.8's units battery does **not** catch this — that tests model input/output units, not the margin definition. Fix: use `log(x_i/t_i)` for positive quantities, which is dimensionless and unit-invariant by construction, and a fixed physically meaningful tolerance scale for signed or zero-threshold properties (phase margin in degrees).

The sign-accuracy correction also lands. §4.1 asserts sign accuracy is "what a ranker actually needs". It is not: ranking requires ordering among candidates, most of which will be improvements over the same starting point, and sign relative to the start is constant across them.

## F11. Too few independent units, biased ranking observations — upheld, one qualification

**Qualification first:** the audit's "60 × 12 is not 720 independent observations" is right about clustering but slightly unfair. The primary regressor — response error on *the episode's* limiting property — does vary within ranker across episodes, so this is not a 12-point regression. §5.4's mixed-effects model with ranker random effects handles the clustering correctly. What it cannot do is manufacture information, and the audit's real point stands: there is **no prospective power analysis anywhere in the plan**, only a risk paragraph in §5.8. For a study whose analysis is the deliverable, simulate the power under realistic clustering and censoring before month 30.

The three specific biases are all confirmed and all serious:

- **Artificial rankers as leverage points.** Three of twelve rankers (two constructed-shortcut, one noise-degraded) are deliberately corrupted, and §5.8 says outright that they "exist to widen the range on purpose". They will sit at the extreme of the x-axis and dominate any fitted slope. A relationship driven by them establishes behaviour under controlled corruption — a legitimate but much narrower claim than "a predictive rule for naturally trained models". Separate the two populations in the analysis and report both.
- **Kendall tau is computed on a selected set.** §5.4 computes tau "on every round where at least four candidates were eventually evaluated" — and candidates are evaluated only if the ranker put them in its top k. The discarded candidates are precisely the ones that reveal screening quality. Range restriction by construction.
- **Candidate distributions differ between rankers.** §5.2 step 6 appends outcomes to the proposer's history, so each ranker faces a different candidate stream. Rankers are never compared on common candidates.

The audit's structural fix — split into (a) a fixed-candidate, fully-evaluated ranking study that isolates the ranker and (b) a closed-loop study that measures realised utility — is the **single most useful recommendation in the whole review**. It resolves all three biases at once, and (a) is far cheaper than (b) because it needs no layout regeneration per round.

**A scheduling contradiction the audit misses.** Thesis dependency rule 3 requires that "a ranker is never trained on any design that appears in a claim 3 episode ... enforced by design id at training time". But §4.12 trains the rankers over months 6–30 while §5.7 draws the episode set at months 30–32, and both draw from the same claim 1 database (§4.4 pool 1 is claim 1's trajectory designs; §5.1 episodes come from claim 1's population). The exclusion is unenforceable as scheduled. Either draw and freeze the episode set at month 6, or budget to retrain all twelve rankers after month 32.

## F12. Coverage versus quantity is framed as a predetermined answer — upheld

The framing objection is fair and the text is explicit about it. Both v11 §4 and implementation §4.4 say *"the claim needs the size axis flat and the selection axis not"* — an experiment written to require a particular result. There is no general reason quantity must be flat over a 10× range, and §4.4 itself predicts the opposite for the comparator: "aggregate accuracy is expected to improve with size on every strategy". Given F10's observation that response error for arm A is a functional of pointwise errors, a flat size axis and an improving accuracy axis are in tension. Reframe as estimating size effects, selection effects and their interaction.

The three supporting points are all correct:

- **Rejection sampling moves more than correlation.** §4.7 rejection-samples to a target correlation of 0.9 with a control that breaks it "by the same rejection sampling in the opposite direction". This necessarily reshapes marginals, density and effective support, so the shortcut set and its control differ in more than the intended way. Match marginals where possible; disclose the residual shift.
- **Budget semantics.** §4.4's boundary strategy needs a surrogate ensemble, rejection sampling and candidate screening, none of which appear in §4.9's "training pools ~60,000". Comparing strategies at equal design count is not comparing them at equal simulator cost. Report both.
- **The Sorscher transplant is looser than claimed.** §4.4 says the margin analogue "makes the transplant tight rather than loose". Sorscher's difficulty is distance to a decision boundary in a *learned representation* for classification; distance to a *specification threshold* in output space is related but not the same object.

**One place the audit is too pessimistic.** It says FALCON probes "are a supporting replication of representation findings, not a replication of response fidelity", and §4.4 accepts that framing because no simulator is available for that process. But FALCON's dataset is a million parameter–performance pairs over twenty topologies. Wherever two designs of the same topology both appear, the finite change `D = f(b) − f(a)` is directly computable from stored data — no simulator needed. You lose control over direction and step size, but you get a genuine response-fidelity replication on naturally occurring pairs, on a closed 45 nm process. That is a meaningfully stronger replication than probes alone and it is nearly free. Worth checking pair density per topology when you measure the download in §10.1 item 15.

## F13. Population breadth and physical validity — upheld

**The topology-count objection is correct.** Claim 1 §2 reaches "roughly twenty to twenty-eight families", but that count includes AnalogSAGE's ten *specification sets* applied to two fixed AMS-SizingBench OTAs, and counts the OSIRIS five-transistor OTA and Miller amplifier separately from their AMS-SizingBench counterparts. Genuine distinct topologies are perhaps 13–18, and the effective count for leave-one-family-out generalisation is lower still, since five-transistor, current-mirror, telescopic and folded-cascode OTAs are structurally close relatives.

**The power objection is the decisive one and the plan does not address it.** Eight generators × ten seeds × ~20 families gives ~2,000 runs and ~1,500–2,000 stage-0 passes, which is **~10 designs per (generator, family, policy) cell**. Figure 1 in claim 1 §7 is survival curves *per generator, faceted by family, one panel per policy* — so each panel rests on about ten designs, before the curve conditions on `m_0 ≥ τ` and shrinks n further at every point along the axis. Wilson intervals on n=10 span roughly ±30%. The headline figure cannot support the claim that survival "differs by generator, circuit family and layout policy". Seeds cannot fix this; it is a design-of-experiment problem about where the replication is spent.

**The pairing objection is correct and cheap to fix.** Both layout policies run on the *same* designs (claim 1 §1: "one layout per design per policy"). §7 tests policy differences with "two-proportion tests with Holm correction", which assume independent samples. Use McNemar or a paired equivalent.

**The DRC objection is fair and slightly embarrassing for the thesis's own thesis.** Claim 1 §3's stages are layout → lvs → extract, with DRC appearing only as a possible failure code emitted by the layout tool, and OSIRIS characterised as having "design rules respected by construction". The whole premise of claim 1 is that tool-reported success does not survive real verification. Accepting a layout tool's self-declaration of DRC-cleanliness contradicts that premise. Add an independent Magic DRC gate.

**The device-correspondence objection is real.** §2.4 requires netgen's device map to be "complete and one-to-one for every design" and to fail loudly otherwise. But a multi-finger device legitimately extracts as parallel devices, and parallel devices are legitimately merged — both produce one-to-many or many-to-one maps on *valid* designs. As written, the rule fails good layouts. It also matters physically: the sky130 mismatch expression scales as `1/sqrt(l·w·mult)`, so how fingers are represented in the extracted netlist changes the mismatch magnitude, and therefore changes claim 1's M-versus-PM decomposition and claim 2's offset inputs.

**On manufacturing claims:** the audit is right about v11, whose title asks whether circuits "survive layout and manufacturing variation". But implementation §2.2 note 1 already applies exactly the discipline the audit asks for — "this plan never claims the sky130 statistical model is silicon ... that is a statement about the learned model, not about the fab". Carry that sentence into v12's title and §1; the work is already done.

## §3. Budget — upheld, arithmetic verified

Every number checks out:

- Accept run: 29 × 50 = 1,450 simulations; at 60 s that is 24.17 core-hours. At 200 chips, 29 × 200 × 60 s = 96.7 core-hours.
- §5.5's 1,100 core-hour line covers 1100/24.2 ≈ 45 of the smaller accept runs, and must also absorb ladder validation, the k sweep and the action-set conditions.
- Method–episode combinations: (12 rankers + 6 baselines) × 60 = 1,080, each needing at least one accept run on success. Even at a 25% solve rate that is ~270 accepts ≈ 6,500 core-hours against 1,100 allocated.
- The nine-fold multiplication: k ∈ {1,2,4} × three action sets, against 3,000 checks budgeted where eight extra conditions × 60 episodes × 25 checks is 12,000.
- Model fitting: 3 strategies × 4 sizes × 4 arms × 3 seeds = 144 fits before headline five-seed cells, tuning trials, two units modes, per-family capacity controls across ~20 families, and leave-topology-out folds. §4.9 has no GPU line at all.

**The synthesis the audit does not make, and it is the useful one:** most of this blow-up is *downstream of F8*. If the accept criterion is claim 1's actual PCM (worst corner, 50 chips = 50 simulations = 0.83 core-hours) rather than PCM-full (1,450 simulations = 24.2 core-hours), the accept line shrinks by a factor of 29 and §5.5's budget becomes roughly defensible. Resolving the endpoint inconsistency in favour of the validated worst-corner shortcut dissolves most of the budget problem. That makes F8 the highest-leverage fix in the review — it is cheap, and it buys back the compute.

The audit's demand for a machine-readable manifest of every experimental cell, with separate lines for proposals, schematic calls, layout/extraction, per-corner chip simulations, final validation, GPU fitting, API cost and storage, is the right instrument and should be built in month 1 rather than month 30.

## §4 and §5. Scope and examiner expectations

The proposed thesis proposition is better than v11 §2 — it is a hypothesis with boundary conditions rather than an assertion that aggregate accuracy is useless and quantity irrelevant. It absorbs the F1, F10 and F12 fixes in one sentence. Adopt it, or something close to it.

Three qualifications:

1. **"Remove the compact-model bridge, crossbar tile and chip from the committed thesis workload" is already done.** v11 §6 and implementation §6 have all three outside the spine, each with a gate, a fallback and a cut date (D5 month 12, D9 month 36), and §1 dependency rule 6 states "if both are cut, all three claims stand". The audit is asking for something the plans already implement.
2. **§4's "three or four genuinely distinct amplifier topologies" is in tension with F13.** F13's complaint is that the topology population is too narrow for the generalisation claims; §4's remedy narrows it further. The reconciliation — which the audit gestures at but does not state — is that they are different claims with different needs: claim 1's population-survival headline *needs breadth* and is the thing F13's power argument bites, while claims 2 and 3 need depth and can start narrow. Cutting to 3–4 topologies would gut claim 1's contribution. Read §4 as scoping the *claim 2/3 pilot*, not claim 1.
3. **The month-4 preprint objection is fair.** D3 commits to "preprint goes out regardless of completeness", and F8/F9 concern the validity of the endpoint that preprint would report. A preprint with an unvalidated worst-corner shortcut and an ambiguous yield rule is a scoop defence that costs credibility. Make D3 conditional on the endpoint being fixed, which months 1–2 can deliver.

The §5 examiner list is conventional and correct. Its closing distinction — that a bounded null result is a contribution while an inconclusive one from low power is not — is exactly the risk F11 and F13 quantify, and it is the argument for doing the power simulation before month 30 rather than discovering the problem at month 42.

---

## What to do first

Ordered by leverage, not by finding number.

1. **Fix the margin definition (F10).** Use `log(x_i/t_i)`. One line, and it currently corrupts the τ axis, the limiting property, the episode strata and claim 3's primary regressor.
2. **Resolve the accept endpoint (F8) and recost (§3).** Cheap, and it buys back thousands of core-hours.
3. **Resolve the §4.3 contradiction between the fixed trained/untrained dictionary and per-epoch random projections (F3).** Instrument 6 is meaningless until this is settled.
4. **Add passive and source values to the node features, and decide the finger-coverage question (F6).** The first is a specification bug; the second determines whether claim 3 keeps its discrete action set.
5. **Separate model bins from the layout grid, and drop multiplicity from the continuous vector (F5).** Everything derivative-related depends on it.
6. **Split claim 3 into a fixed-candidate ranking study and a closed-loop utility study (F11), and add limiting-property value error as a comparator (F10).**
7. **Drop D4 as a pass/fail gate; define arm B's absolute prediction and its Jacobian anchor (F2).**
8. **Draw and freeze the episode set early, or budget to retrain the rankers (F11 addendum).**
9. **Power-simulate claim 1's per-panel survival curves and claim 3's survival model before committing to ten seeds and sixty episodes (F13, F11).**

Items 1–5 are all achievable inside the existing months 1–8 window and none requires new compute.
