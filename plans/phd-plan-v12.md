# PhD Research Plan, v12

**Working title:** When does a learned circuit model's response to a design change match the simulator's, and does that decide whether AI-sized analog circuits pass model-based physical verification?

**Candidate:** part-time, The Hong Kong Polytechnic University. **Proposed supervisor:** Prof. Yang Chai (Applied Physics). **Co-supervisor:** to be named in electronic design automation or machine learning.

Dated 8 September 2026. Supersedes v11 of 7 September. Changes from v11 are listed in §9; they come from two sources — the fact-checking in `thesis-implementation-plan-v1.md` §9.1, and the external audit of 8 September (`phd-plan-audit-2026-09-08.md`) with its evaluation (`audit-evaluation-2026-09-08.md`). The v9 source list still applies except where §9 of v10, v11 and this version correct it.

Companion documents: `thesis-implementation-plan-v2.md` (the build plan for all three claims) and `claim1-implementation-plan-v2.md`. Where this plan and those disagree, those are correct and the disagreement is a bug in this one.

---

## 1. What we are trying to achieve

AI systems now size and lay out analog circuits and report first-try pass rates above 90%. Every one of those numbers is measured before layout, at the typical corner, with perfectly matched devices. The checks that decide whether a chip works — extracted parasitics, process-voltage-temperature corners and device mismatch — are not in the score. One system that does re-simulate after layout (PANDA) loses more than half its bandwidth on its only reported op-amp. Nobody has reported, for a population of AI designs, how many survive.

The same systems increasingly replace the simulator inside their search loops with a learned model. A search uses that model for one thing: to predict what a proposed change will do. What is reported instead is accuracy on held-out designs, and that is a different quantity.

The goal is two things, in order:

1. Measure how much of today's AI analog design output passes **model-based physical verification**, and why it fails.
2. Establish when a learned model's predicted response to a change is faithful on the properties that limit the specification, and whether that fidelity carries information about repair cost beyond what task-matched accuracy already carries.

**What "survives" means here, stated once and kept.** The endpoint is model-based physical verification under the SkyWater 130 nm kit and this flow: extracted parasitics from Magic, the kit's own corner definitions, and the kit's own area-scaled mismatch model. It is not silicon, and no claim in this thesis is about manufacturing yield in a fab. The statistical model is a model; what the thesis measures is how designs and surrogates behave under it. v11's title asked whether circuits "survive layout and manufacturing variation", which overclaimed, and the implementation plan already applied the narrower discipline (`thesis-implementation-plan-v2.md` §2.2).

Everything in this plan serves one of those two goals. Anything that does not is in §8.

## 2. Thesis proposition

> Under specified layout and statistical process models, a learned circuit model's local response fidelity on the constraints that are active at a design provides **incremental** information about repair decisions **beyond task-matched value accuracy**. How much it provides depends on training coverage, action scale and proposal quality. Controlled experiments identify the conditions under which it improves physical-verification efficiency and the conditions under which it does not.

This is a hypothesis with boundary conditions, and each clause is an estimand with an effect size and an interval.

v11's thesis statement asserted in advance that response fidelity "is not measured by aggregate accuracy" and "is set by which designs the training set covers rather than how many". Those are the things the experiments are supposed to estimate, and writing them as premises made two of the studies require a particular answer. They are now predictions, marked on the figures as predictions, with designs that can show them false.

**Two things the proposition deliberately does not say.**

It does not say aggregate accuracy is useless. The test is *incremental* value over a task-matched comparator ladder — limiting-property value error and local value error, not merely the global accuracy the surrounding literature reports. Those three quantities differ along three axes at once (response versus value, one property versus all, local versus global), and a comparison against only the weakest of them could not say which axis did the work.

It does not say quantity is irrelevant. Size effect, selection effect and their interaction are all estimated. A flat size axis is one possible outcome, not a requirement.

## 3. Claims

**Claim 1, measurement.** Of AI-sized designs that meet specification pre-layout, the fraction that still meets it after extracted parasitics, across corners, and under Monte Carlo mismatch — reported as curves against specification margin — differs by generator, circuit family and layout policy. Failures are decomposed into parasitic, corner and mismatch causes over an eight-class partition. Which designs pass is predictable from pre-layout features, with the predictor holding on topologies and generators it was not fitted on. The fall with margin is expected; the shape, the decomposition, the policy gap and the out-of-sample predictor are the claim.

**Claim 2, fidelity.** In a learned circuit model, the per-property response error — the difference between the model's predicted change under a design change and the simulated change — is estimated against training coverage, training quantity and derivative supervision, and compared against task-matched value accuracy on the same designs. Supervising the model on simulator sensitivities inside a restricted subspace improves, or fails to improve, its response on the subspace's orthogonal complement; either result is reported. The model's sensitivity to per-device parameter offsets, where that sensitivity is supervised, propagated through the kit's mismatch covariance, predicts or fails to predict the Monte Carlo spread of each property and their joint distribution.

**Claim 3, utility.** On specifications limited by layout or by variation, the per-property response error on the limiting property carries information about the number of expensive checks a model-guided repair loop needs, beyond limiting-property value error and local value error. Measured in two linked studies: a fixed-candidate ranking study that isolates the ranker, and a closed-loop study that measures realised cost against conventional baselines.

Claim 1 is a paper, not a thesis. Claims 2 and 3 are the thesis. Claim 1 is first because it builds the pipeline claims 2 and 3 run on, and because one group already holds the code that produces its headline number (§7).

**What is already established, and what is not.** That a model's aggregate accuracy need not track its usefulness for control is known in model-based reinforcement learning: one-step likelihood "is not always correlated with control performance" (Lambert et al., 2020); two models are value-equivalent if they yield the same Bellman updates on the functions the planner uses (Grimm et al., 2020); weighting the model loss by value gradients beats maximum likelihood at low capacity (Voelcker et al., 2022). In surrogate-assisted optimisation, one controlled study with an adjustable pseudo-surrogate finds that for two of three model-management strategies performance stops improving above an accuracy of 0.7 to 0.8 (Hanawa et al., 2025). Claim 3 therefore tests a known principle in a new domain.

**The novelty claim, stated at its true width.** v11 said that no prior work, "in circuits or elsewhere", measures a surrogate's per-property response or Jacobian agreement in connection with search cost. The "or elsewhere" is not defensible and is withdrawn. Sobolev training targets derivatives directly (Czarnecki et al., 2017); Tsay (2021) evaluates derivative-trained surrogates on downstream optimisation; and the model-based and derivative-free optimisation literature ties the quality of a model's gradient approximation to optimisation behaviour explicitly — Giovannelli and colleagues analyse function, gradient and Hessian approximation together with the optimisation that consumes them (arXiv 2311.12253, to obtain). Two of those three are already in this thesis's own bibliography as method sources. DNN-Opt's critic already takes a design and a change and predicts the resulting specifications, so the change-conditioned model is not a new object either.

What is claimed instead is a **documented combination**, presented as a comparison matrix rather than as an absence: derivative accuracy, local finite-change error, constrained ranking under a specification, post-layout targets, mismatch propagation, and held-out search utility — on circuits, with the response measured against the simulator that defines truth, and related to the cost of a repair loop. Originality is claimed for that combination and for the resulting insight, not for the ingredients. The one analog paper that reports both held-out accuracy and iterations-to-target (arXiv 2512.00712) reports them as separate tables and does not relate them.

[Verify before submission: the 8 September audit cites a preprint (Bian and Xie, arXiv 2608.24963) said to study the dependence of surrogate benefit on the surrogate's role, local operating radius and base solver. It is not in `papers/` and its existence is unconfirmed. If it is real it is the closest overlapping work and belongs in the matrix.]

## 4. Method

**Process and tools.** SkyWater 130 nm only. It is the process the measured generators run on; it has per-device mismatch models scaled by area, two automatic layout tools (ALIGN, OSIRIS's baseline placer), Magic extraction and ngspice.

**Geometry, model bins and the layout grid.** v11 said sizings "are snapped to model bins before simulation". That conflates two things and, taken literally, destroys every derivative in claim 2. Model binning is **model selection**: a device subcircuit picks a `.model` card by which W/L *interval* the instance falls in, and any geometry inside that interval is legal. The quantisation that actually exists is the layout manufacturing grid. So: geometries are range-checked, quantised to the grid, and their model bin and their **clearance to the bin boundary** recorded — nothing is moved to a bin. Derivatives are taken with respect to W and L, the independent continuous parameters; multiplicity and finger count are integers and are actions, not directions. Every perturbation is checked to exceed the grid (or it is a no-op with an identically zero difference) and to stay inside the bin (where the mismatch slopes jump), and no-ops and bin crossings are logged and counted.

**Margins are dimensionless.** `m_i = s_i · log10(x_i / t_i)` for ratio-scale properties, and `m_i = s_i · (x_i − t_i) / Δ_i` with a pre-registered tolerance scale for signed or zero-threshold ones. v11 inherited a definition that normalised by the threshold *after* a log conversion, which is not scale-invariant: a 10 MHz bandwidth against an 8 MHz threshold gives 0.014 in log10(Hz) and 0.107 in log10(MHz). Since the limiting property is the argmin of the margin across properties, its identity could flip on a unit change — and the limiting property drives claim 1's curve axis, claim 3's episode stratification, claim 3's ranking objective and claim 3's primary regressor.

**Circuit families.** OSIRIS's five circuits, the ALIGN-supported amplifiers of AMS-SizingBench, and AnalogSAGE's specification sets. Fixed topologies; AI chooses sizings. AI-invented topologies are excluded because each needs its own layout template, so a topology population would measure the layout tool.

Counted honestly, this is about **thirteen to eighteen genuinely distinct topologies**, not the "twenty to twenty-eight families" of earlier drafts: AnalogSAGE's ten problems are specification sets rather than topologies, applying them to fixed OTAs creates specification variety rather than topology variety, and the OSIRIS five-transistor OTA and Miller amplifier are the same circuits as their AMS-SizingBench counterparts under different testbenches. Every count in the papers distinguishes topologies from specification sets from testbench variants, and the distinct-topology number is the one used wherever generalisation is claimed. The ALIGN-supported subset is established by running ALIGN on all twenty-four circuits in months 1 to 2 and is reported as a result.

**Populations (claim 1).** Sizings from every generator AutoSizer's harness already re-implements under one budget (genetic, Bayesian, trust-region Bayesian, ADO-LLM, LEDRO, EEsizer), from AutoSizer itself, and from AnalogSAGE. Two single-pass layout policies, one layout per design each: ALIGN and the OSIRIS baseline. Failures logged by stage, including an **independent Magic DRC stage** — a layout tool's claim to respect design rules by construction is exactly the kind of tool-reported success this study exists to check.

**Where the replication is spent.** Two thousand designs over roughly twenty families, eight generators and two policies is about **ten designs per (generator, family, policy) cell**, before the survival curve conditions on margin and shrinks n further at every point. A Wilson interval on ten designs spans about ±30 percentage points, so the three-way facet grid cannot carry the claim. Headline contrasts are therefore generator-pooled across families (n ≈ 250), family-pooled across generators (n ≈ 100), and the **paired** policy gap, which is the best-powered contrast because both policies run on the same designs. The three-way grid is a supplement with its n printed on every panel. Inference is a hierarchical logistic model with crossed random effects; the policy comparison uses McNemar rather than a two-proportion test, because it is paired. A **prospective power simulation at month 3** sets the seed count and the family list before the harvest launches — breadth is cut before power.

**The signoff endpoint, named once.** `PCM` — extracted netlist, worst corner, Monte Carlo mismatch — is the primary endpoint. `PCM-full` — every corner with mismatch — validates the worst-corner shortcut on a 40-design subsample against a predeclared tolerance, with an escalation rule if it fails. The worst corner is chosen with nominal devices and so need not be the corner of lowest yield, which is what the subsample tests. Claim 3's accept criterion is PCM.

**Signoff is a conjunction.** Nominal pass and yield pass are recorded separately and neither is derived from the other. Earlier drafts skipped post-layout Monte Carlo for designs failing at nominal, on the ground that a nominal failure cannot reach 90% yield. That is false in general — a property distributed as z² against a lower bound of 0.01 fails at nominal while 92.0% of chips pass — so the escape rate is now measured on a 200-design subsample rather than assumed to be zero. Yield labels are **three-valued**: at true yield 0.9 the standard error of a pass fraction is 0.042 at fifty chips and 0.021 at two hundred, so a hard threshold runs through the middle of the noise, and indeterminate designs are retained as a band rather than coerced.

**The model (claims 2 and 3).** One cross-topology skeleton: a **device-level graph** over the netlist, with device and net nodes, terminal-typed edges, and a DeeperGCN-family backbone. v11 proposed a "CktGNN- or INSIGHT-style" model; both are the wrong shape — CktGNN's benchmark is a behavioural abstraction whose nodes are transconductance stages rather than transistors, and INSIGHT is per-topology with no public code. DICE's encoder and FALCON's edge-centric network are the public device-level comparators.

Node features carry, for transistors, log width, log length, log multiplicity, finger count, bin index and the bin's four mismatch slope coefficients; and **for passives and sources, the device's own value** — resistance, capacitance, current, voltage. That last is not a detail. Width and length are meaningless for a compensation capacitor, and without a value feature the model cannot distinguish two designs differing only in Cc — on the Miller, Ahuja and feed-forward compensated amplifiers, which is three of OSIRIS's five circuits, and on exactly the properties claim 1 reports as failing after layout. A **global condition token** carries supply, load, temperature, corner, testbench identity and layout policy, so that the target is a function of the model's inputs rather than of context the model cannot see.

Per-family small networks are run as a capacity control. Arms on identical simulation budgets:

- **A**, plain forward model, design in, performance out.
- **B**, change-based, design and change in, change in performance out, with a per-topology reference design supplying absolute values so that aggregate accuracy is defined for it.
- **B-S**, arm B additionally supervised on simulator sensitivities **inside a restricted subspace** (below), with **B-S-full** as the spanning-supervision comparator.
- **B-S-z**, arm B-S with derivative supervision extended to per-device offset directions. This is the arm the propagation test is about.
- **B-mc**, trained on a handful of off-nominal chips per design, as the alternative route to offset information.
- **B-J**, a Jacobian-norm penalty instead of derivative targets, costing no simulator sensitivities.

**Non-separability is a diagnostic, not a gate.** v11's implementation required arm B's anchored-pair discrepancy to exceed a threshold or the arm was declared collapsed. That is backwards: for a deterministic property the exact change `D(a,b) = f(b) − f(a)` **is** separable and satisfies `D(a,a) = 0`, antisymmetry and cycle consistency, so an accurate change model approaches those identities and a gate demanding departure from them rewards approximation error. The identities are reported as diagnostics; whether pairwise training buys anything is settled by comparing arms at matched resources.

**Derivative supervision is confined to a rank-deficient subspace, and this is what makes the held-out-direction test mean anything.** At a fixed design, directional derivatives are linear measurements `y = Ug` of the gradient. A trained direction set that spans the parameter space identifies the whole gradient, so an "untrained" direction is a linear combination of trained ones and no derivative information is withheld. The v11 implementation's dictionary — coordinate directions plus intervention directions plus forty random ones, 40% marked trained — spans a twenty-to-thirty-five dimensional space comfortably, and it also contradicted itself by elsewhere supervising on fresh uniform random projections each epoch, under which every direction is trained in expectation. So: a random subspace `S` of dimension `floor(n/2)` is fixed per topology, supervision happens only inside `S`, evaluation happens on its orthogonal complement, and **the realised rank and conditioning of the trained set are reported at every design**. The restriction costs the model something, and B-S-full measures how much.

**Why per-device offsets are an input, and what that does and does not buy.** A chip's mismatch draw has four random terms per device — twenty to forty dimensions on these families against about a dozen output scalars — so it is known exactly in simulation but not identifiable from the outputs. Supplying it as an input and asking whether the model's sensitivity to it is faithful tests the model.

But the sensitivity must be **supervised**. v11 said a faithful sensitivity gives the spread "with no per-chip training at all". That is wrong as a matter of identifiability: from data at z = 0 only, `fhat(x,z)` and `fhat(x,z) + a(x)·z` fit equally well for any `a`, so the offset sensitivity is arbitrary. Offset-direction derivative labels resolve it, and they are cheap but not free — four parameters times the device count times two runs per labelled design. "No per-chip training" survives only in its true, narrower sense: **no dense Monte Carlo training**. The nominal-only arms are run as the control the identifiability argument predicts should be uninformative.

The propagation test reports the **full covariance** `J_z J_zᵀ`, not only its diagonal: marginal standard deviations do not give joint multi-specification yield, and the off-diagonals are free once `J_z` is computed. The three-way decomposition — Monte Carlo spread, simulator-Jacobian propagation, model-Jacobian propagation — separates the model's error from the linearisation's, and is kept.

The covariance in standardised coordinates is the **identity**: all four SkyWater mismatch terms share the same area law, one over the square root of `l·w·mult`; what differs is the per-device, per-bin slope coefficient, and several of those coefficients are zero. v11 said each term has "its own area scaling", which overstated the kit. Drennan and McAndrew's finding that threshold mismatch "does not follow a simplistic 1/sqrt(area) law" remains the reason to carry four parameters rather than one, and the reason never to claim the kit's statistical model is silicon.

**Instruments, fixed in advance.** Linear and nonlinear probes; a control task subtracted from every probe score, with description length beside it; a supervised head in two variants (frozen backbone, and full retrain) certifying different things; an intervention test; the held-out-direction test; and the propagation test.

**What the instruments license.** A probe recovering a property establishes decodability under the probe protocol. A wrong predicted response establishes behavioural approximation error. Every intervention here acts on the model's *inputs*, not on its internal representation. So **behavioural response fidelity is the primary construct**, probes are supporting evidence, and the phrase "contains but does not use" does not appear as a conclusion. v11's read-versus-use framing claimed more than these instruments deliver.

The intervention test also **checks that an isolating direction exists before constructing one**. With a dozen coupled properties on twenty-odd parameters, the component of one property's gradient orthogonal to the others can be numerically negligible, in which case the constructed direction is noise. A pre-registered conditioning rule excludes those cases, and a property excluded on most designs is reported as *not isolable in this family* — a finding about the circuit, not a gap in the results.

**Coverage versus quantity.** Three selection strategies (random, language-model-proposed, chosen near failure boundaries) crossed with four dataset sizes spanning a factor of ten. What is estimated is the **size effect, the selection effect and their interaction**, each with an interval, on three explicitly defined evaluation distributions (uniform, boundary, and the candidate distribution claim 3's proposer actually generates) — because "coverage" is meaningless without saying coverage of what. v11 said the claim "needs the size axis flat and the selection axis not", which wrote the experiment to require a result, and sat badly beside its own expectation that accuracy improves with size.

Acquisition cost is counted in full — proposals generated, candidates screened, simulations rejected, derivative labels bought — and every comparison is reported **twice**, at equal design count and at equal simulator cost. Rejection sampling that changes a correlation also changes marginals, density and support, so the constructed-shortcut sets use marginal-matched acceptance and disclose the residual shift.

The secondary prediction from the data-pruning literature — that the best selection keeps hard examples with abundant data and easy ones with scarce data — is recorded before the runs as a **transplanted hypothesis**. v11 called the transplant "tight"; distance to a specification threshold in output space is related to but not the same as distance to a decision boundary in a learned representation.

**Replication on FALCON's public dataset** covers probes and aggregate accuracy, and **also response fidelity**: the dataset is a million parameter-performance pairs, so wherever two designs of the same topology appear, the finite change is computable from stored rows with no simulator. Control over direction and step size is lost; a response-fidelity measurement on a closed 45 nm process is gained.

**Repair loop (claim 3), as two linked studies.** A single closed loop cannot isolate the ranker: each ranker steers its own proposer history, so rankers never face common candidates, and a rank correlation computed on the candidates a ranker itself promoted is range-restricted by construction. So:

- **Study 3A, fixed-candidate ranking.** A common batch of sixteen proposals per episode, **every candidate fully evaluated once**, scored offline by every ranker. Ordering agreement, top-k regret, feasibility calibration. No selection bias, no candidate-distribution differences, and the expensive evaluation amortised across all rankers. This carries the mechanism.
- **Study 3B, closed loop.** The live loop with a reduced ranker set, measuring checks to accept under right-censoring, against conventional baselines including a dynamic over-design re-run that may well win. This carries the utility.

Action space: continuous sizing changes and finger-count changes. The finger action set is **gated on a dedicated finger-variation training set**, because claim 1's finger rule makes finger count a deterministic function of sizing and no other design in the thesis carries a finger response. Placement is not an action; predicting a placement move needs layout as a model input, which is a different model.

Rankers span the error range, and three of the twelve are deliberately corrupted to widen it. **Natural and manufactured rankers are analysed separately, always**: a slope driven by manufactured models establishes behaviour under controlled corruption, not a rule for models anyone would train. A **prospective power simulation at month 28** reports the minimum detectable effect before any episode runs.

**Units.** The full battery is repeated in ordinary and logarithmic units on inputs and outputs. This is separate from, and does not substitute for, the dimensionless margin definition above.

## 5. What makes a negative result a finding

Before "the model failed to learn X" can be said: the full-retrain supervised head must reach X (the information was there and this class on this data can extract it), the per-family control must be run (not a capacity artefact), the control-task baseline must be subtracted (not probe flexibility), and the alternative arms must be run (not one architecture). The mechanism is stated in advance and makes a further prediction that is then tested: shortcut learning predicts that adding coverage along the constructed shortcut direction closes the gap without adding quantity; the conditional-mean argument predicts that a squared-error model learns no spread unless the objective or the input carries it.

**Every negative result is reported with the power it had.** A null effect with narrow, practically meaningful bounds across credible settings is a contribution. An inconclusive result from low power, an unidentifiable model or a broken pipeline is not, and pretending otherwise at month 42 is the failure mode the three power simulations (months 3, 8 and 28) exist to prevent. Each runs while the counts it governs are still changeable.

If the cross-topology model shows no response gap outside the constructed sets, the finding is that these models are more faithful than expected, and claim 3 runs on a ranker set dominated by constructed models — with its conclusion explicitly scoped to behaviour under controlled corruption, which is a real but much narrower contribution. If per-property response error adds nothing over limiting-property value error and local value error, that is the answer to claim 3, reported as plainly as the other direction, and claims 1 and 2 stand.

## 6. Timeline

Assumes roughly half-time effort. If it slips, Year 4 becomes Year 5; nothing is reordered.

- **Months 1 to 2.** Reproduce AutoSizer's full flow (ALIGN, Magic, post-layout simulation). Establish the ALIGN-supported subset. Independent DRC exercised against known-good and known-bad layouts. Grid, bin-clearance and finite-difference convergence measured on ten designs spanning the first family's operating regimes. The mismatch subcircuit patch checked. Corner shortcut checked against its tolerance on the first family.
- **Month 3.** Prospective power simulation; the seed count and family list follow from it. Then the harvest.
- **Months 1 to 6.** Survival pipeline and populations. Preprint at month 4, **conditional** on the margin definition, the corner shortcut check and the yield labelling being settled — v11's "regardless of completeness" is the right instinct against the scoop risk and the wrong rule when the incomplete part is the validity of the headline endpoint. Claim 1 paper submitted by month 6, when the database and the **frozen episode set** are tagged.
- **Months 6 to 18.** Arms A, B, B-S, B-S-full, B-J at the pre-layout stage. Instruments 1 to 6. Constructed shortcut sets. Coverage-versus-quantity. FALCON replication. Power simulation at month 8. Fidelity paper around month 18.
- **Months 18 to 30.** Post-layout and Monte Carlo targets. Per-device offset inputs and offset derivative labels; arms B-S-z and B-mc. Propagation test with the full covariance. Units comparison.
- **Months 28 to 42.** Power simulation, then study 3A, then study 3B against baselines. Utility paper.
- **Months 42 to 48.** Write up.

**Why the episode set is frozen at month 6.** Claim 3's rankers must never be trained on a design appearing in a claim 3 episode, nor on a near-duplicate from the same optimiser run. But the rankers are trained from month 6 and both they and the episodes draw from claim 1's database, so an episode set drawn at month 30 would make the exclusion retroactive and require retraining every ranker. Claim 1 emits the frozen table at month 6 and claim 2 honours its hold-out flag from then on.

**Gated, outside the spine.** Decided by the supervisor's answers in §10. Each has a gate, a fallback and a date at which it is cut; if all three are cut, claims 1 to 3 stand unchanged.

- *Compact-model bridge*, months 12 to 24, if the group holds device-to-device variability data and agrees to its publication. The deliverable is a compact model with **explicit statistical parameters** in Verilog-A through OpenVAF, with parameter statistics extracted by backward propagation of variance. v11 specified "the dual-network style of Novkin and Amrouch, exported as Verilog-A or OSDI"; those authors did not export to Verilog-A — they integrated hand-written C into a commercial simulator and stated that Verilog-A "cannot perform matrix multiplications efficiently" — and OpenVAF's own materials list arrays among unsupported constructs. A neural network inside Verilog-A cannot be assumed to compile or to be fast, so the deliverable is a ladder ending in a Python model plus a table and covariance.
- *Computing-in-memory tile*, months 36 to 44, if the bridge delivered and the op-amp loop finished on schedule. NeuroSim, CrossSim and AIHWKit do not ingest Verilog-A; the handoff is ngspice Monte Carlo statistics into NeuroSim's circuit-expert mode or CrossSim's error function. The SkyWater ReRAM primitive has no statistical hooks; Synaptogen is the substitute.
- *Chip*, a shuttle submission under a thousand euros if a slot opens. One chip is one sample and proves nothing about variation. No SkyWater shuttle is currently announced with a close date after 7 September 2026.

## 7. Risks

- **Infrastructure eats a year.** The ALIGN-plus-Magic path exists in AutoSizer's public code, but a documented code path is not a demonstration of reproducibility on this population. Month 2 is a reproduction, and if the OSIRIS placer cannot be made to work the first paper ships with ALIGN alone and says so.
- **Scoop on claim 1.** AutoSizer's repository has a full-flow mode and reports no post-layout, corner or Monte Carlo result as of its last commit. The Pan group at UT Austin holds the MAGICAL lineage, a layout-aware Bayesian sizer and an August 2026 agent already running extractions and post-layout simulations per design at 65 nm and 40 nm with no corners or Monte Carlo. A population survival number is one experiment away for them. The curves, decomposition, policy gap and out-of-sample predictor do not fall out of a flag flip. Preprint at month 4 under the conditions in §6.
- **No response gap exists.** Covered in §5.
- **Absorption.** ZEROSIM (arXiv 2511.07658) is a pin-level transformer surrogate on this thesis's own process across sixty amplifier topologies with about 3.6 million instances — a bigger cross-topology dataset than this thesis will build, reporting no code or data release. It does not measure response fidelity, intervention behaviour, held-out directions or propagation. Two consequences: do not compete on dataset size, and use their data if it is released. Held-out-topology accuracy is cheap to bolt on and is already reported by two groups with incompatible protocols, which strengthens rather than weakens the argument that aggregate accuracy is the wrong quantity to report alone.
- **The natural ranker range is narrow.** Then claim 3's answer concerns manufactured models, and is scoped to that. Recognised at month 18 (decision D6), not at month 42.
- **Sensitivity analysis does not reach parameters inside the process's device wrappers.** Not a risk: finite differences by re-simulation are the plan of record, at two runs per direction, and `.SENS` is an optimisation adopted only if it reaches the parameters and agrees within 5%.
- **Department fit.** An Applied Physics committee may read this as computer science. The gated bridge and tile exist for this, and the §10 questions decide whether they run. Adding a device chapter to secure departmental fit would be another substantial research project and does not substitute for agreement that the core thesis belongs in the department. A co-supervisor in EDA or ML is named before submission.
- **The conventional approach wins the loop.** Expected and reported; the thesis is the map, not the method.

## 8. Deliberately left out

- **The latent world-model framing (Tan et al., arXiv 2607.27017).** Every instrument predates it: linear probes (Alain and Bengio, 2016), control tasks (Hewitt and Liang, 2019), shortcut learning (Geirhos et al., 2020), derivative supervision (Czarnecki et al., 2017). Its hidden-variable mechanism has nothing to grip in circuits, where every property is determined by the inputs. Cited as related work; not load-bearing.
- **A per-chip latent-variable arm.** Replaced by the propagation test, which asks the same question with a known covariance and no inference.
- **A JEPA-style latent-predictive arm.** Its self-supervised motivation is weak for a dozen exact scalars that cost a second each.
- **Placement moves in the repair loop.** Need layout as a model input; different model.
- **GaN as a process for claims 1 to 3.** Three platforms were considered (X-FAB XG035, imec GaN-IC, Hanhua Semiconductor). None can carry the spine, for four reasons independent of platform: the design kits are licensed, so a netlist population could not be published and no sizing generator has been ported; ALIGN, MAGICAL and Magic have no GaN process abstraction, so there is no automatic layout policy to measure; the platforms offer n-channel HEMTs only, so the op-amp families do not exist; and signoff there is dominated by dynamic on-resistance, trapping and self-heating rather than by extracted parasitics and area-scaled mismatch, with no public statistical model of p-GaN threshold spread to serve as a reference covariance. Whether AI-designed GaN power circuits survive dynamic on-resistance and thermal signoff is a real open question, but it replaces this thesis's spine rather than extending it. GaN enters only through the compact-model bridge, as one candidate device.
- **AI-invented topologies, process transfer, aging, a full pivot to compute-in-memory co-design, a learned device model as ground truth, a language model inside the core model.** Reasons unchanged. EXPLORE, the strongest topology generator read, reaches 65% success at tolerance 0.01 on a six-component power-converter benchmark and 0 to 26% at seven to ten components, which confirms that a topology population would be dominated by generator validity rather than by layout.

## 9. Changes from v11

### From the 8 September audit and its evaluation

1. **§2, the thesis proposition** is a hypothesis with boundary conditions and an incremental-value test, not an assertion that aggregate accuracy is useless and quantity irrelevant.
2. **§3, novelty** drops "in circuits or elsewhere" and claims a documented combination presented as a comparison matrix. Giovannelli (arXiv 2311.12253) to obtain; the audit's Bian and Xie citation to verify.
3. **§1 and the title** describe the endpoint as model-based physical verification under the stated kit and flow, not manufacturing survival.
4. **§4, margins** are dimensionless. The previous definition was unit-dependent by a factor of 7.6 on a representative bandwidth, and the limiting property is its argmin.
5. **§4, geometry.** Nothing is snapped to a model bin. Range check, grid quantisation and bin identification are three separate logged operations; derivatives are with respect to W and L only; multiplicity leaves the continuous design vector.
6. **§4, the endpoint** names PCM and PCM-full separately and says which is primary. Signoff is a conjunction of nominal pass and yield pass, and the implication from nominal failure to yield failure is false in general (counterexample in §4). Yield labels are three-valued.
7. **§4, the skeleton** carries passive and source values and a global condition token. Without them the model cannot distinguish two designs differing only in the compensation capacitor.
8. **§4, non-separability** is a diagnostic, not a gate. The exact change is separable, so a gate demanding non-separability rewards error.
9. **§4, derivative supervision** is confined to a rank-deficient subspace, with rank and conditioning reported, because a spanning trained set withholds no derivative information and the held-out-direction test would measure nothing.
10. **§4, the propagation test** requires offset-derivative supervision — the offset sensitivity is unidentified from nominal-only data — and reports the full covariance rather than only marginal spreads. "No per-chip training" is narrowed to "no dense Monte Carlo training".
11. **§4, instruments** are scoped to what they license; "contains but does not use" is withdrawn as a conclusion; the intervention test checks isolability before constructing directions.
12. **§4, coverage versus quantity** estimates size, selection and interaction effects on three named evaluation distributions, at equal design count and equal simulator cost. It no longer "needs" a flat size axis.
13. **§4, FALCON** replicates response fidelity on stored within-topology pairs, not only probes.
14. **§4, claim 3** is two linked studies — fixed-candidate ranking and closed loop — because the closed loop alone cannot isolate the ranker. Natural and manufactured rankers are analysed separately.
15. **§4, populations.** The distinct-topology count is stated honestly; headline survival contrasts are generator-pooled, family-pooled and the paired policy gap; inference is hierarchical and the policy test is McNemar.
16. **§4, fingers.** The finger action set is gated on a dedicated finger-variation set, because the finger rule makes finger count collinear with sizing across the whole population.
17. **§4, DRC.** An independent Magic DRC stage is added.
18. **§5 and §6.** Three prospective power simulations at months 3, 8 and 28; negative results reported with the power they had; the month 4 preprint conditional on the endpoint being defensible.
19. **§6.** The claim 3 episode set is drawn and frozen at month 6, since drawing it at month 30 would make the ranker exclusion retroactive.

### From the implementation plan's fact-checking (carried forward from `thesis-implementation-plan-v1.md` §9.1)

20. **§4, mismatch covariance.** All four SkyWater terms share one area law; what differs is the per-bin slope, and several slopes are zero. The covariance in standardised coordinates is the identity. v11's "each with its own area scaling" overstated the kit.
21. **§4, the skeleton.** "CktGNN- or INSIGHT-style" is wrong: CktGNN's benchmark is a behavioural abstraction the DICE authors state "is not suitable for device-level circuit evaluation", and INSIGHT is per-topology with no public code. The device-level comparators are DICE's encoder and FALCON's network.
22. **§4, per-chip draws** are known exactly only with the subcircuit patch; with a bare seed they are positional and do not correspond between netlists.
23. **§7, FALCON absorption numbers.** The 28.8% against 1.1% comparison is not like-for-like and is withdrawn as stated.
24. **§7, absorption.** ZEROSIM (arXiv 2511.07658) added as the nearest occupant on this process.
25. **§2 and §8, prior change models.** DNN-Opt's critic is already change-conditioned; v9's "no prior change-prediction model inside circuits" is withdrawn.
26. **§6, the bridge deliverable** restated as a ladder; "exported as Verilog-A or OSDI" is not established for a neural model.
27. **§6, the AIHWKit quotation** replaced with the paper's actual wording.
28. **§6, tile tooling.** NeuroSim does not model line resistance while CrossSim does, so both are needed.
29. **§6, chip timing** conditional on a shuttle opening at all.
30. **§7, sensitivity risk** inverted: finite differences are the plan of record.
31. **§11, budgets.** Claim 2's pre-layout budget is about 896,000 stage-0 simulations and about 600 core-hours; claim 1's post-layout budget roughly doubles under the factorial; claim 3 adds about 9,800 core-hours. All are scenario figures derived from an experiment manifest, not upper bounds, and GPU fitting — over a thousand fits — is costed rather than omitted.
32. **§4, circuit families.** AnalogSAGE's ten problems are specification sets rather than fixed-topology families, and the five OSIRIS specifications are ours.

### Still to verify before submission

- Whether `.SENS` reaches width, length and mismatch parameters inside the SKY130 subcircuits (an optimisation, not a dependency).
- The sky130 manufacturing grid value and the bin-clearance distribution; finite-difference convergence on ten designs per family.
- That Magic DRC runs on ALIGN and OSIRIS output unattended and flags a deliberately broken layout.
- That netgen's device map is complete and unambiguous under multi-finger splitting and parallel-device merging, and the offset-aggregation rule that follows.
- FALCON's within-topology pair density, to size the response-fidelity replication.
- Giovannelli et al. (arXiv 2311.12253); the existence of arXiv 2608.24963; Ravichander et al. (arXiv 2005.00719).
- Budak et al. (ISPD 2023), Learn-by-Compare (DAC 2024), PVTSizing (DAC 2024), the two glayout papers, Kinget (JSSC 2005): not open-access; obtain through the library.

## 10. Questions for the supervisor before submission

1. Which computing in memory: device-level and neuromorphic, or macro- and architecture-level?
2. Does the group hold device-to-device and cycle-to-cycle variability data on any device, and may a student model and publish it?
3. Is a co-supervisor in EDA or ML acceptable, and who?
4. Will the department examine a thesis whose first paper is a measurement study on an open process and whose core is a study of learned models?

Answers to 2 and 4 decide whether the bridge and tile run and whether the department is the right one.

## 11. Resources

One consumer graphics card. A 32-core workstation. Free open process kits.

Simulation budget, as scenario figures from the experiment manifest rather than upper bounds, to be recomputed from measured median and tail runtimes at month 2: claim 1 roughly 320,000 extracted and 220,000 schematic runs for a two-thousand-design population under the factorial, plus about 116,000 for the PCM-full subsample; claim 2 about 896,000 pre-layout simulations, about 600 core-hours; claim 3 about 25,600 expensive checks, about 9,800 core-hours. The graphics card, not the simulator, is claim 2's binding resource from months 8 to 18, at over a thousand model fits.

If the claim 1 budget binds, the yield-estimation literature in the folder offers cheaper estimators for near-threshold designs, validated against brute force on a held-out set before use; brute force stays the reference. Chip, if any, under a thousand euros.

## 12. Sources

`papers/README.md` indexes the papers in the folder by the section they support, lists what could not be obtained open-access, and records the verified findings behind §9. Corrections to that index are listed in `thesis-implementation-plan-v2.md` §9.3.
