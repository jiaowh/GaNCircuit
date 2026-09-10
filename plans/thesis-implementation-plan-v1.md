# Thesis implementation plan, v1

**Scope.** The build plan for the whole thesis of `phd-plan-v11.md`, claim by claim: claim 1 (measurement), claim 2 (fidelity), claim 3 (utility), and the three gated items (compact-model bridge, computing-in-memory tile, chip). It absorbs `claim1-implementation-plan.md` v1 by reference, amends it where facts checked today differ, and gives claims 2 and 3 the same level of definition. Every definition a reported result depends on is fixed here and carried into a per-claim pre-registration document.

**Deliverables.** Three papers (survival, fidelity, utility), one pipeline and result database that all three run on, one gated device-modelling paper, and a thesis. Dates assume the half-time effort of v11 §6 and a start in month 1.

Dated 8 September 2026. Companion to `phd-plan-v11.md` and `claim1-implementation-plan.md`. Facts about papers were read from the primary PDFs in `papers/` on this date; facts about tools, repositories and shuttles from their public pages on this date. Sources are listed in §11. Items marked "[verify]" have not been checked on a running tool and are collected in §10. Places where this plan disagrees with v11, with the claim 1 plan, or with `papers/README.md` are collected in §9.

---

## 0. How to read this document

- §1 maps claims to deliverables, dependencies and the parts of the database each produces and consumes.
- §2 fixes the infrastructure all three claims share: process, toolchain, the mismatch model as it actually reads, sensitivity labels, extraction, the database, and the compute model.
- §3, §4 and §5 are the per-claim plans. Each has the same shape: fixed definitions, data, method, instruments or baselines, analysis and figures, compute, build order, risks, and what a negative result means.
- §6 covers the three gated items with their gates and their fallbacks.
- §7 is the month-by-month schedule with decision points.
- §8 is the pre-registration and the honesty rules.
- §9 lists corrections to carry into `phd-plan-v12.md`, into claim 1 plan v2, and into `papers/README.md`.
- §10 is the verify list, split into month 1 and before submission.
- §11 lists what was read today.

Terminology follows v11. A **property** is a scalar a testbench measures. A **specification** is a benchmark's inequality constraints on properties. A **design** is a topology plus a snapped sizing. A **cell** is one of claim 1's evaluation conditions (0, P, C, M, PC, PM, PCM, CM). A **change** is a vector over sizing parameters, or over per-device mismatch offsets. The **limiting property** of a design at a cell is the constrained property with the smallest normalised margin there. **Response error** and **Jacobian agreement** are defined in §4.1; they are the thesis's central measured quantities and are used with those definitions everywhere.

## 1. Thesis map

| Claim | Output | Months | Produces | Consumes |
|---|---|---|---|---|
| 1, measurement | survival paper; preprint month 4, submitted month 6 | 1 to 6 | pipeline, populations, result database, per-design failure diagnosis, pre-layout survival predictor | nothing prior |
| 2, fidelity, pre-layout | fidelity paper, submitted about month 18 | 6 to 18 | arms A, B, B-S trained at stage 0; instruments 1 to 6; constructed shortcut sets; coverage-versus-quantity result; FALCON replication | claim 1 stages `canonicalise`, `sim0`, `features`; claim 1 trajectory designs as a seed set |
| 2, fidelity, physical | extension or follow-up paper | 18 to 30 | post-layout and Monte Carlo targets; per-device offset inputs; propagation test; units comparison | claim 1 database tagged at month 6: layouts, extracted netlists, per-corner and per-chip property vectors |
| 3, utility | utility paper, submitted about month 42 | 30 to 42 | repair loop, baselines, the error-versus-cost result for continuous and finger moves | claim 1 failure diagnoses and populations; claim 2 rankers with measured error profiles |
| Bridge (gated) | device-modelling paper | 12 to 24 | a simulator-ready statistical compact model of one measured device | the group's variability data (the gate) |
| Tile (gated) | section of the utility paper, or a fourth paper | 36 to 44 | repair loop and instruments on a crossbar family | claim 3 loop code; the bridge model or Synaptogen |
| Chip (gated) | thesis chapter | shuttle-dependent | one measured amplifier | an open sky130 shuttle slot; an output buffer designed from the start |
| Write-up | thesis | 42 to 48 | | everything above |

**Dependency rules, stated so that a slip in one claim does not silently corrupt another.**

1. Claim 2's pre-layout work needs only the first three pipeline stages, so it starts in month 6 whether or not the claim 1 paper is in review.
2. Claim 2's physical work uses the claim 1 database exactly as tagged at month 6. If claim 1 designs are re-run later, claim 2 keeps the tagged snapshot and the change is recorded.
3. Claim 3 draws its repair episodes from claim 1's population and its rankers from claim 2. A ranker is never trained on any design that appears in a claim 3 episode, nor on any post-layout or Monte Carlo result of such a design. The exclusion is enforced by design id at training time, not by convention.
4. Claim 1's headline curves use only the primary population (the final design of each run) and only pre-registered cells. Trajectory designs train the survival predictor and seed claim 2; they never enter a survival curve.
5. Claim 2's response error for a model is computed only on designs held out from that model's training set, and on directions recorded as untrained where the arm distinguishes them.
6. The bridge and the tile feed nothing into claims 1 to 3. If both are cut, all three claims stand.

## 2. Shared infrastructure

### 2.1 Process and toolchain

SkyWater 130 nm (sky130A through open_pdks), ngspice, Magic, netgen, ALIGN with `ALIGN-pdk-sky130`, the OSIRIS baseline placer, the AutoSizer harness, AnalogSAGE's loop, and CACE. One container image; versions in the image manifest and in every result row.

Tool states read today, 8 September 2026:

- **ngspice** 47, released 11 August 2026. The OSDI interface for OpenVAF-compiled Verilog-A has been present since version 39. One version must satisfy the sky130 mismatch models, the AutoSizer harness (whose code cites the version 34 manual) and CACE [verify].
- **CACE**, last PyPI release 26 June 2026; datasheet format 5.2, with 4.0 deprecated; command line offers `-j JOBS`, `-s {schematic,layout,pex,rcx,best}`, `-p PARAMETER`, `--parallel-parameters`, `--sequential`, `--max-runs`, `--run-path`, `--nofail`. Netlist sources live in directories `schematic`, `layout`, `pex` (capacitance only) and `rcx` (resistance and capacitance). The claim 1 plan's "extracted" is `rcx`; `pex` is never used, because a capacitance-only extraction would understate the wire resistance that the study is about. The claim 1 plan's note that the CACE slides show format 5.0 is superseded.
- **AutoSizer**, last commit 26 May 2026; the release commit added `test_magic_pex.py`. The README describes a full-flow mode (`pre_layout_only=False`) that runs ALIGN's `schematic2layout.py`, then Magic parasitic extraction through `run_pex()`, then a second simulation with pre-versus-post degradation per metric, on the best pre-layout design only. Configuration keys `pdk_lib_path`, `align_pdk_path`, `pex_script_path`. Model selection through `--model gemini-2.5-flash` using `google-generativeai` and a `GOOGLE_API_KEY`. No licence file was found. The README as fetched today names four circuits with layout support (telescopic, folded-cascode, five-transistor and current-mirror OTAs) alongside the sentence that support covers "simple OTAs and amplifiers"; the verbatim README text is read in month 1 before this is treated as the ALIGN list (§9).
- **OSIRIS**, dataset and code on Hugging Face under `hardware-fab/osiris`, dataset card licence CC-BY-4.0. The licence of `osiris_code.zip` is checked separately [verify].
- **ALIGN**, public with a sky130 PDK repository. No 2026 release note was found; the container pins a commit.
- **AnalogSAGE**. The only repository found by name is `wznmickey/AnalogSAGE`: seven commits, last updated in May, no licence, modules `BO.py`, `candidate.py`, `compress.py`, `evalTask.py`, `insight.py`, `knowledge.py`, `queryPinecone.py`, `refine.py`, `reflection.py`, `sizing.py`, `sizing_mix.py`, `tolology.py`, and a README requiring PySpice, ngspice, a PDK, and pre-generated knowledge and topology vector databases through Pinecone. It is not confirmed to be the authors' release. Month 1 confirms with the authors; if there is no official release, AnalogSAGE is re-implemented from its published specification sets as one more generator and labelled as a re-implementation everywhere it appears.
- **Gemini 2.5 Flash**. Google's own deprecation page, read today, lists no announced shutdown date for `gemini-2.5-flash`; third-party trackers claim October 2026. The harness's model client is wrapped so any served model can be substituted, and the model identifier and date are recorded per run.

### 2.2 The sky130 mismatch model, as it actually reads

This subsection is load-bearing for claim 1's Monte Carlo, for claim 2's offset inputs and propagation test, and for claim 3's variation-limited specifications. It was read from the SkyWater device model files and the open_pdks conversion today.

Each device is a subcircuit wrapping a binned `.model` card, so the instance parameters `l`, `w` and `mult` reach the model expressions. In the open_pdks conversion, four parameters carry a mismatch term of the form

```
<param> = { <nominal> + ... + MC_MM_SWITCH * AGAUSS(0,1.0,1) * (<param>_slope / sqrt(l*w*mult)) }
```

for `vth0`, `voff` and `nfactor`, and of the same form multiplied by the nominal oxide thickness for `toxe`. The slope coefficients are per device type and per bin group. Read today:

| Device | toxe_slope | vth0_slope | voff_slope | nfactor_slope | lint_slope | wint_slope |
|---|---|---|---|---|---|---|
| `nfet_01v8` | 3.443e-03 | 3.356e-03 (bin group 2 uses vth0_slope1 = 7.356e-03) | 0.007 | 0.0 | 0.0 | 0 |
| `pfet_01v8` | 4.443e-03 / 6.443e-03 / 3.443e-03 | 5.856e-03 / 7.356e-03 / 4.356e-03 | 0.0 / 0.0 / 0.007 | 0.1 / 0.1 / 0.0 | 0.0 | 0 |

(The three-value rows are the base, `_slope1` and `_slope2` variants selected by bin group.)

Six consequences, all fixed here:

1. **The reference covariance is diagonal.** One independent standard normal draw per device per parameter, scaled by that bin's slope divided by the square root of `l*w*mult`. There is no device-spacing term, no correlation between parameters, and the same area law applies to all four. Claim 2's propagation test therefore reduces to a diagonal quadratic form, given in §4.6. v11 §4's phrase "each with its own area scaling" overstates the model and is corrected in §9. Drennan and McAndrew's finding that silicon threshold mismatch "does not follow a simplistic 1/(sqrt(area)) law, especially for wide/short and narrow/long devices" remains the reason to carry all four parameters rather than a single threshold term, and it is also the reason this plan never claims the sky130 statistical model is silicon. What the propagation test checks is agreement between the model's sensitivity and the simulator under the process kit's own covariance; that is a statement about the learned model, not about the fab.
2. **Slopes jump at bin boundaries.** A sizing change that crosses a bin boundary changes a device's mismatch coefficient discontinuously, and can change `vth0_slope` to `vth0_slope1`. All intervention and propagation directions in claim 2 are constructed within a bin, and any bin crossing along a simulated path is logged and reported.
3. **Some slopes are zero.** `nfactor_slope` is zero for the n-channel device and for one p-channel bin group; `voff_slope` is zero for two p-channel bin groups; `lint` and `wint` carry no mismatch at all. Properties whose spread is dominated by a parameter with a zero slope on the devices that matter cannot be predicted by propagation for a trivial reason. The property table records, per family, which of the four parameters are live on the input pair and the mirror devices.
4. **Draws are positional.** ngspice consumes its pseudo-random stream in device instantiation order, so the same seed on the schematic and on the extracted netlist does not give the same per-device draws. Per-chip correspondence between cells M and PM, and every claim 2 use of the draw as a known model input, therefore needs explicit offsets rather than a shared seed.
5. **Explicit per-device offsets, by patch.** The pipeline ships a patched copy of the sky130 device subcircuits in which each mismatch term reads `MC_MM_SWITCH * z_<param> * (<param>_slope / sqrt(l*w*mult))`, with `z_<param>` a subcircuit parameter whose default value is `AGAUSS(0,1.0,1)`. Behaviour is unchanged when nothing is passed, and fully determined when the four standard normal values per device are passed from outside. This is the mechanism that makes the per-chip draw a known model input in claim 2 and makes M and PM comparable chip by chip in claim 1. Checks in month 1: that ngspice evaluates an `AGAUSS` default once per instance rather than once per subcircuit definition; that the patched subcircuits reproduce nominal results exactly; that they pass netgen; and that passing an explicit vector reproduces a logged random chip [verify]. This closes v10 §9's open question "whether the mismatch terms can be set as explicit per-device parameters" by construction rather than by hope, and the fallback is stated in §4.10.
6. **Units and switches.** Whether `l` and `w` in these expressions are in metres or micrometres is read from the installed files in month 1; the n-channel `vth0_slope` of 3.356e-03 is consistent with about 3.4 mV·µm, which is the right order for a 4.1 nm oxide when Pelgrom's 30 mV·µm at 50 nm oxide is scaled down, so micrometres is the expectation [verify]. The library's `mc` section sets `MC_MM_SWITCH=0` and `MC_PR_SWITCH=1`, so `.lib ... mc` gives global process variation only. Sections named `tt_mm`, `ss_mm`, `ff_mm`, `sf_mm`, `fs_mm` with `MC_MM_SWITCH=1` and `MC_PR_SWITCH=0` are reported in the installed `sky130.lib.spice` [verify on the installed file]. Mismatch-only Monte Carlo uses those sections, or sets the two switches explicitly after the `.lib` line; it never uses `mc`. Off-bin geometries fail to match a model, which is why sizings are snapped and the snap logged.

### 2.3 Sensitivity labels

Claim 2's arm B-S, instrument 5 and the propagation test all need simulator sensitivities. ngspice's `.SENS` computes the DC operating point or AC small-signal sensitivity of one output "to all non-zero device parameters" by numerical perturbation, and its own manual warns that the numerical method "may demonstrate second order effects in highly sensitive parameters, or may fail to show very low but non-zero sensitivity". The manual does not say whether parameters inside a subcircuit-wrapped binned model are reached, and its output is per node voltage or source branch current, not per testbench property.

The default sensitivity source is therefore **central finite differences by re-simulation on the full testbench**: two runs per direction, a relative step of 2% in log-sizing space, with 1% and 4% run once per family as a step-size check, and a step of 0.5 standard deviations for the per-device offset parameters. `.SENS` is tried in month 1 on the first working netlist; it is used only if it reaches the sizing and mismatch parameters and agrees with finite differences within 5% on a sample of ten designs. Either outcome is recorded and reported, since v11 §7 lists this as a risk and the answer is worth stating publicly.

Cost: a design with 20 sizing variables costs 40 stage-0 simulations for a full sizing Jacobian, and a design with 15 devices costs 120 more for the four offset parameters per device. At the AutoCkt schematic figure of 2.4 s per simulation this is minutes per design, which is why the sensitivity budget in §4.9 is dominated by how many designs get a full Jacobian, not by how the Jacobian is computed.

### 2.4 Extraction and device correspondence

Magic's own documentation states that resistance extraction "does not work well with hierarchy" and recommends flattening before parasitic extraction, and that subcircuit calls may be renumbered. Extraction therefore flattens, and device correspondence between the schematic and extracted netlists comes from netgen's LVS device match report, stored per design as an explicit device map, never from name matching. The claim 1 plan's month-1 item "extracted netlists preserve device instance names" is replaced by "the LVS device map is complete and one-to-one for every design", checked in stage `lvs` and failed loudly.

Extraction settings, fixed once and recorded: flatten, `ext2spice cthresh 0`, `ext2spice rthresh 0`, `ext2spice extresist on`, ngspice format. A design whose extraction produces no resistance network is a bug, not a result.

### 2.5 Result database

One columnar table per stage keyed by design id and policy, raw simulator outputs kept as files addressed by content hash, nothing overwritten, reruns appended with a new run id. Claim 1's tables are in its own plan §3. This plan adds:

- `training_sets`: id, claim, selection strategy, size, seed, the design ids in it, the directions recorded as trained, and the construction script commit.
- `models`: id, arm, skeleton, capacity, units mode, training-set id, seed, hyperparameters as a blob, training code commit, and the checkpoint hash.
- `predictions`: model id, design id, cell, property, predicted value, and where relevant predicted change and predicted spread.
- `responses`: model id, design id, direction id, step size, property, simulated change, predicted change, and the co-movement of the held properties.
- `jacobians`: design id, property, parameter, simulated partial derivative, model partial derivative, source (finite difference or `.SENS`).
- `probes`: model id, layer, probe family, target, control-task flag, score, and the description-length columns.
- `episodes`: episode id, design id, failure cell, limiting property, method id, and the ordered list of proposals with their costs and verdicts.

Every row carries the container image digest.

### 2.6 Compute model

One consumer graphics card, one 32-core workstation. Simulations are queued one per job with a per-design seed; layout jobs run on their own queue because ALIGN and the OSIRIS placer are single-threaded and take about a minute each. Training runs on the graphics card; the models in this plan are small, and the reference point for size is that the whole Tan et al. study ran about five million parameters per model on one consumer card.

Budget estimates in each claim are recomputed from measured runtimes at the end of the claim 1 month-2 timing study, before any harvest is launched. Until then the working figures are AutoCkt's 2.4 s per schematic testbench and about 91 s with parasitics, Gao's post-layout figures of 80 plus or minus 15 s per iteration on an operational transconductance amplifier, and OSIRIS's 25 to 48 s per layout on a 32-core machine.

## 3. Claim 1, measurement

**Claim (v11 §3).** Of AI-sized designs that meet specification pre-layout, the fraction that still meets it after extracted parasitics, across corners, and under Monte Carlo mismatch, reported as curves against specification margin, differs by generator, circuit family and layout policy. Failures decompose into parasitic, corner and mismatch causes. Which designs survive is predictable from pre-layout features, with the predictor holding on families and generators it was not fitted on.

`claim1-implementation-plan.md` v1 is the detailed plan and stands as written except where amended below. This section restates its structure so this document is self-contained, then lists the amendments in place.

### 3.1 Structure, restated

**Definitions.** Property, specification and pass are the benchmark's own, with phase margin added as a reported property everywhere it is missing and as a constraint only where the benchmark constrains it. Margin is the signed normalised distance `m_i = s_i (x_i - t_i) / |t_i|` with gain-like and bandwidth-like properties converted to logarithmic units first; the design's margin is the minimum over constrained properties, and the property attaining it is the limiting property. The survival curve is `F_S(tau)`, the fraction of designs with pre-layout margin at least `tau` that pass stage S, with Wilson intervals, reported per generator, family and policy and never pooled across generators.

**Cells.** A factorial over extraction, corners and mismatch: 0 (schematic, typical, nominal), P, C, M, PC, PM, PCM, CM, plus a 40-design PCM-full subsample that validates the worst-corner shortcut. The factorial exists so that failure causes can be attributed; a sequential flow would attribute every failure to whichever stage ran first.

**Conditions.** Corner set of 29 points (tt, ss, ff at three supplies and three temperatures, plus sf and fs at nominal). Monte Carlo is mismatch only, 50 chips per design, 200 for designs whose pass fraction lands within the Wilson interval of the yield threshold. Yield threshold 0.90, with the full pass-fraction distribution stored and 0.99 reported in the supplement with its resolution caveat.

**Populations.** Eight generators (genetic, Bayesian, trust-region Bayesian, ADO-LLM, LEDRO, EEsizer, AutoSizer, AnalogSAGE), ten seeds per circuit at a 300-sample budget, over OSIRIS's five circuits, the ALIGN-supported amplifiers of AMS-SizingBench, and AnalogSAGE's specification sets applied both by AnalogSAGE and, as additional specification sets, to fixed AMS-SizingBench operational transconductance amplifiers under the other seven generators. Two single-pass layout policies, ALIGN and the OSIRIS baseline placer, one layout per design each. Target about 1,500 to 2,000 designs passing stage 0.

**Pipeline.** Nine stages, each a pure function from record to record plus a log: `harvest`, `canonicalise`, `sim0`, `layout`, `lvs`, `extract`, `sim`, `verdict`, `features`. Failures are logged by stage and never folded together.

**Predictor.** Pre-layout features only (per-property margins, device geometry, operating point, a finite-difference fragility feature, structure), logistic regression and gradient-boosted trees against a margin-only baseline, evaluated leave-one-family-out and leave-one-generator-out with area under the ROC curve, Brier score and calibration.

**Build order.** One family end to end under both policies before widening. Preprint at month 4, submission at month 6.

### 3.2 Amendments

**A1, Monte Carlo sections.** The mismatch-only library sections or explicit switches of §2.2 replace the open question in claim 1 plan §1 about which section the CACE `mc` corner enables. If CACE drives the simulations, its Monte Carlo condition must set `MC_MM_SWITCH` and `MC_PR_SWITCH` explicitly rather than relying on a corner name [verify in CACE 5.2 condition syntax].

**A2, per-chip correspondence.** Cells M and PM use explicit per-device offsets through the patched subcircuits of §2.2, keyed by the LVS device map of §2.4, so that the same chip can be simulated on both netlists and the mismatch component of a post-layout failure can be separated from an interaction with parasitics. If the patch fails its month-1 check, M and PM use independent draws; the decomposition still holds in aggregate, the per-chip pairing is dropped, and claim 2's offset-input arm falls back to §4.10.

**A3, extraction.** Flatten before resistance extraction; correspondence from the LVS device map; settings as in §2.4. The claim 1 plan's device-name assumption is withdrawn.

**A4, netlist source naming.** "Extracted" means CACE's `rcx` (resistance and capacitance). `pex` (capacitance only) is never used and the distinction is stated in the paper, because a capacitance-only comparison would understate exactly the effect being measured.

**A5, budget semantics.** AutoSizer's README states `n_trials: 3` and `max_total_designs: 100` per trial, while the paper states a 300-sample budget; the relation between the harness's outer iterations and the paper's budget is read from the code in month 1 [verify]. All eight generators are configured to the same per-run budget, and the configuration used is reported as a table.

**A6, the ALIGN list.** The README fetched today names four layout-supported circuits (telescopic, folded-cascode, five-transistor and current-mirror operational transconductance amplifiers) as well as the general sentence about "simple OTAs and amplifiers". If the verbatim README does name them, the claim that "AutoSizer publishes no per-circuit ALIGN list" is wrong and is corrected in v12 (§9); the month 1 to 2 experiment that runs ALIGN on all twenty-four circuits still runs, because a README list is a claim about the tool and the experiment is a measurement of it, and because the difference between the two is itself reportable.

**A7, AnalogSAGE provenance.** Confirm the repository with the authors in month 1. If there is no official release, AnalogSAGE becomes a re-implementation from its published specification sets, labelled as such in every figure, and the paper says so plainly.

**A8, language-model client.** Wrap the harness's model client so a substitute model can be used, and record model identifier and date per run. Google's own page lists no shutdown date for `gemini-2.5-flash` today, so the risk is live but not dated.

**A9, new related work to check before the preprint.** ZOAF (arXiv 2606.02869) and the row-based analog layout synthesis paper (arXiv 2606.21767) surfaced in today's sweep and are read before month 4. Neither title suggests a population survival result.

**A10, finger override.** The finger rule stays as the claim 1 plan states it, the minimum valid finger assignment satisfying the topology's matched-pair constraints, applied identically under both policies and recorded per device, because no generator in the population searches finger count. Its implementation must additionally accept an explicit per-device finger assignment as an override, because claim 3 makes finger count an action (§5.1). The override is unused in claim 1 and its default path is the rule.

**A11, scoop status today.** No paper found through 8 September 2026 measures a population of AI-sized designs after extraction, corners or Monte Carlo. The nearest are per-design: the Pan group's simulation-aware layout refinement (arXiv 2608.13767), PANDA, SABLE, and the white-box gm/ID work. PANDA's single operational transconductance amplifier remains the sharpest published illustration: unity-gain bandwidth falls from 10.84 MHz to 4.192 MHz against an 8 MHz target while gain and phase margin survive, and the paper selects the best completed attempt rather than repairing the miss. PANDA's process node is not stated anywhere in its paper, which is worth noting when citing it. AutoSizer's repository still reports no post-layout numbers as of its last commit.

## 4. Claim 2, fidelity

**Claim (v11 §3).** In a learned circuit model, the per-property response error, the difference between the model's predicted change under a design change that moves property X and the simulated change, comes apart from aggregate accuracy and from what a probe can read out of the model. Which properties are affected is set by training coverage, not quantity. Supervising the model on simulator sensitivities along some directions improves, or fails to improve, its response along directions it never saw; either result is reported. The model's sensitivity to per-device parameter offsets, propagated through the process's known mismatch covariance, predicts, or fails to predict, the Monte Carlo spread of each property.

### 4.1 Fixed definitions

These are frozen in the claim 2 pre-registration at month 8 and are used unchanged in claim 3.

**Design vector.** For a topology T with n_d devices, the sizing vector x collects per device the logarithm base ten of width, length and multiplicity, plus the integer finger count. The offset vector z collects, per device, four standardised mismatch coordinates (`vth0`, `toxe`, `voff`, `nfactor`), each a standard normal at nominal, so z = 0 is the nominal chip. A design is (T, x); a chip is (T, x, z).

**Change.** A change is a vector u in sizing space, with a step size h, applied as x -> x + h u in log-sizing space so that a step is multiplicative in device geometry. Finger changes are integer and are handled as a separate discrete action set in claim 3, not as directions here.

**Simulated response.** For property i, `D_i(d, u, h) = f_i(x + h u) - f_i(x)` computed by the testbench at stage 0 (later, at a physical cell).

**Model response.** For arm B, the model predicts the change directly. For arms A and the supervised head, the predicted change is the difference of two predictions. Both are written `Dhat_i(d, u, h)`.

**Response error, the thesis's central quantity.** Per property, per design, per direction, per step:

```
e_i(d, u, h) = ( Dhat_i(d, u, h) - D_i(d, u, h) ) / s_i
```

where `s_i` is the standard deviation of property i over the evaluation set, in the units mode being used. The signed form is kept; the reported statistic is the median absolute value over the evaluation set, with the interquartile range, per property. A second, scale-free statistic is reported beside it: the fraction of (design, direction) pairs on which the model gets the **sign** of the change right, which is what a ranker actually needs.

**Jacobian agreement.** Where a full Jacobian is available, per property i and design d: the cosine similarity between the model's gradient of property i with respect to x and the simulator's, and the relative error of the gradient norm. Cosine similarity is reported because a ranker cares about direction, and norm error separately because a repair step size cares about magnitude.

**Aggregate accuracy, the comparator.** Coefficient of determination and mean relative error per property on held-out designs, computed exactly as the surrounding literature computes them, so that the thesis's claim of divergence is made against the quantity that literature reports. Mean relative error excludes samples whose true value is below a per-property floor, and the floor is stated, because that metric penalises small denominators (a point the radio-frequency graph-network paper makes explicitly when it declines to report the coefficient of determination for multimodal metrics).

**Evaluation set.** For a given model, the designs held out from its training set, restricted to topologies held out where the fold is a leave-topology-out fold. No response error is ever computed on a training design.

**Property table (the premise check, one page).** For every property of every family: whether it is determined by the inputs (all of them are, through the simulator); whether reading it from a representation plausibly requires a ratio rather than a linear combination; whether a squared-error target on per-chip data rewards it (nominal properties yes, spread-defined properties no); whether it is hidden (only the per-chip draw is); which of the four mismatch parameters are live on the devices that dominate it, given the zero slopes catalogued in §2.2; and its units mapping. Produced in month 6 and published as an appendix whatever it says.

### 4.2 The model skeleton

**Correction first.** v11 §4 says the skeleton is "a published learned circuit model (CktGNN- or INSIGHT-style)". Both are the wrong shape for this thesis, for reasons read from the papers:

- CktGNN's Open Circuit Benchmark is a **behavioural** abstraction: an operational amplifier's stages become voltage-controlled current sources with parasitic resistors and capacitors, with node features ranging over transconductance, resistance and capacitance. The DICE authors state plainly that it "is not suitable for device-level circuit evaluation since its circuit graphs do not use transistors as fundamental components". A model on that abstraction cannot be asked about a width change, so it cannot answer this thesis's question.
- INSIGHT has no public code, takes a flat parameter sequence rather than a graph, and is trained per topology ("For a given analog circuit topology"). It is a strong per-topology comparator, not a cross-topology skeleton.

**Primary skeleton, fixed here.** A device-level graph over the snapped netlist:

- **Nodes**: one per device and one per net. Node type is a one-hot over device classes (n-channel transistor, p-channel transistor, resistor, capacitor, current source, voltage source) and net classes (ground, supply, other), following DICE's nine-type scheme.
- **Edges**: one per device terminal, connecting the device node to the net node, typed by terminal role (drain, source, gate, bulk for transistors; the two terminals of a passive). Terminal-typed edges are used rather than net-collapsed edges because two terminals of one device can share a net, which makes a plain device-net edge ambiguous; that ambiguity is the stated motivation for the terminal-level representation of the few-shot pretraining work. Gate and bulk edges are directed from net to device, since the net drives the device far more than the reverse, as in DICE.
- **Node features**: device nodes carry log width, log length, log multiplicity, finger count, the model bin index as a one-hot, and the four mismatch slope coefficients of that bin (process metadata, legitimately available to any surrogate, and needed if the model is to have any chance on the propagation test); net nodes carry only their class.
- **Global token**: one node connected to every other node, whose embedding is the graph readout, in the style of the pin-level transformer's graph token. Readout is the concatenation of the global token, a mean pool and a sum pool.
- **Backbone**: four to six generalised graph convolution layers with edge features (the DeeperGCN family used both by the few-shot pretraining work and by the radio-frequency graph network), hidden width 256, GraphNorm, LeakyReLU, residual connections.
- **Head**: one multilayer perceptron per property over the readout, with a mask so that one model spans families with different property lists, as FALCON does with its masked squared-error loss.
- **Offset input** (physical stage only): the per-device standardised offsets z are appended to device node features, zero at nominal.

**Capacity control.** A per-family multilayer perceptron on the flat sizing vector (five layers, widths 200 to 500, as in the published supervised benchmark models) is trained per topology. It bounds how much of any observed gap is representation rather than capacity, which matters because on a fixed topology with a dozen variables a small network fits nominal behaviour almost exactly.

**Published comparators.** DICE's encoder (public code) is used as an optional pretrained initialisation and reported as an ablation. FALCON's edge-centric network (public code, MIT licence) is re-trained on this data as a second published skeleton, because its representation is the dual of the one above (nets as nodes, devices as edges) and a result that holds on both is much harder to dismiss. CktGNN is cited as related work and not run. INSIGHT is re-implemented per topology from its published description only if the per-family control turns out to be the binding comparator, and is labelled a re-implementation.

### 4.3 The arms

All arms share the skeleton, the training data budget, the optimiser and the tuning effort. Differences are the input, the target and the loss.

**Arm A, forward.** Input (T, x); output the property vector. Loss: masked mean squared error on z-scored properties. This is the standard published surrogate and the reference point for aggregate accuracy.

**Arm B, change-based.** Input a pair of designs on the same topology, (T, x_a, x_b); output the change in each property. Representation of the pair follows pairwise difference regression: the shared encoder is applied to both designs and the head consumes the concatenation of the two readouts, their difference, and the raw change vector. **The head must not be separable.** If the model factorises as g(x_a) - g(x_b), then the pairwise loss provably reduces to a single-point loss and the arm is arm A wearing a different hat; the same paper shows the pairwise uncertainty becomes a constant independent of the query. Non-separability is enforced by construction (the head is a nonlinear multilayer perceptron over the concatenation including the raw change) and checked empirically: on a held-out set, the maximum absolute difference between the model's prediction for pair (a, b) and the difference of its predictions on two anchored pairs must exceed a pre-registered threshold, or the arm is reported as having collapsed to A.

**Pair construction.** Pairs are within a topology. The log-sizing distance between members is stratified into bins covering 0.02 to 1.0 decades, sampled uniformly across bins so that small and large changes are equally represented, because shortcut failures are expected on large changes where the linearisation breaks. The number of pairs is capped at twenty per design to keep the quadratic blow-up bounded; the pairwise literature's own stated limitation is that the training set becomes the square of the design set.

**Arm B-S, change-based with derivative supervision.** Arm B plus a Sobolev term on a recorded subset of directions. Loss:

```
L = L_value + sum_j w_j * L_derivative_j
```

with derivative targets from §2.3. Weighting follows the scaling recipe of the Sobolev surrogate work: min-max scale the outputs and each derivative to the unit interval on the training set, then set every w_j to one, which removes the free parameter that the gradient-enhanced physics-informed literature found to matter (there, a weight of 0.01 was best and a weight of 1 was worse than no derivative term at all). Because that literature disagrees on whether the weight is benign, a three-point sweep over {0.01, 0.1, 1.0} of an additional global multiplier is run once, at the second-smallest dataset size, and then fixed for everything else and reported. Derivatives are supervised through random projections onto directions drawn uniformly from the unit sphere, one per sample per epoch, which is the standard estimator and avoids paying for a full Jacobian per sample. First order only: second-order supervision is not run, and the reason is stated (cost, and the fact that a rectified-linear network's second derivative is degenerate).

**Directions recorded as trained.** Per topology, a fixed dictionary is built: the coordinate directions, the per-property intervention directions of instrument 5, and forty random unit directions. Forty per cent of the dictionary is marked trained and used in B-S's derivative term; the remainder is untrained and is the substrate of instrument 6. The split is per topology, fixed by seed, and pre-registered.

**Arm B-J, an ablation, not a headline.** Arm B with a Jacobian-norm penalty instead of derivative targets, using the single-random-projection estimator with regularisation strength 0.01. It costs no simulator sensitivities at all. If it recovers most of B-S's held-out-direction advantage, that is a cheap and useful finding; if it does not, it isolates the value of true derivative labels.

**Arm B-het, conditional.** Runs only if the propagation test of §4.6 fails. Predicts a mean and a spread per property from a handful of simulated chips per design, trained with the beta-scaled negative log likelihood at beta = 0.5, not the plain likelihood, because the plain heteroscedastic likelihood is known to produce "very poor but stable parameter estimates" by scaling down the gradient on poorly-predicted points. Its purpose is a control: to establish whether the spread was learnable from this data at all.

**Training protocol, identical across arms.** AdamW; initial learning rate 1e-3; batch 256; reduce on plateau by half after five epochs without validation improvement; early stopping after ten; gradient clipping at norm 1; inputs z-scored after the log transform; outputs z-scored per property on training statistics; three seeds for every cell of every study and five for anything in a headline figure; identical epoch budget across arms; the same held-out folds. Every arm gets the same number of tuning trials, drawn from the same random search space, and the search space is pre-registered.

### 4.4 Data, coverage and quantity

**Source of designs.** Three pools, all on the claim 1 families and all simulated by the claim 1 pipeline stages `canonicalise` and `sim0`:

1. Claim 1's trajectory designs (every candidate any generator evaluated that passed the geometric and bin checks). Free, already simulated, but distributed the way optimisers wander, which is itself a coverage story worth reporting.
2. Fresh random sizings inside the benchmark's own ranges.
3. Designs proposed by the selection strategies below.

**Coverage versus quantity, the designed experiment.** Three selection strategies crossed with four dataset sizes, spanning a factor of ten: N in {2,000, 4,300, 9,300, 20,000} designs. Every cell is trained with three seeds; the headline cells with five.

- **Random.** Uniform in log-sizing space inside the benchmark ranges.
- **Language-model proposed.** A model is given the netlist, the specification and the design conventions and asked for sizings, in the manner of the language-model generators already in the harness. Recorded with model identifier and date.
- **Boundary.** Chosen near failure boundaries with the straddle acquisition, `1.96 * sigma(x) - |fhat(x) - t|`, evaluated against each constrained property's threshold t, with the surrogate an ensemble trained on a seed set, and candidates drawn uniformly at random rather than on a grid, which is how the acquisition's originators do it. The acquisition prefers points both uncertain and near a threshold.

**Pre-registered secondary prediction.** With abundant data the best selection keeps hard, boundary examples, and with scarce data it keeps easy ones, so the ranking of the three strategies is expected to change across the size axis. This is the data-pruning result transplanted, and the margin analogue of its difficulty metric is exactly the distance to a specification threshold that the straddle acquisition uses, which makes the transplant tight rather than loose. The prediction is written down before the runs.

**What the claim needs.** The size axis roughly flat and the selection axis not, in response error on the affected properties. Aggregate accuracy is expected to improve with size on every strategy; that contrast is the point, and it is plotted on one pair of axes.

**Replication on a closed process.** The same coverage-versus-quantity design is repeated on FALCON's public dataset (about one million Cadence-simulated circuits, twenty expert-designed topologies in five families, 45 nm, every simulation at a fixed 30 GHz), with probes only, since no simulator is available for that process and therefore no intervention or propagation test can run. The download size is not stated in the repository and is measured before this is scheduled. Agreement between an open 130 nm operational-amplifier set and a closed 45 nm millimetre-wave set makes the coverage claim hard to dismiss as a process artefact; disagreement is reported as a boundary on the claim.

### 4.5 Instruments

Seven instruments, fixed in advance, each with its protocol.

**1. Linear probe.** Ridge regression from a frozen representation to a property, fitted with gradients blocked from the model, one probe per layer plus one on the readout, scored by the coefficient of determination on held-out designs. Regularisation chosen on a validation split.

**2. Nonlinear probe.** A multilayer perceptron probe, hidden width swept over {16, 64, 256} and depth over {1, 2}, best validation cross-entropy or squared error selected, reported beside the linear probe. The information-theoretic argument for always using the most expressive probe and the control-task argument for restraint are both respected by reporting both numbers rather than choosing a side.

**3. Control task and description length.** Two independent guards against reading a probe's own flexibility as a property of the model.

- *Control task.* For each design, a control target is drawn once from the empirical distribution of the real property and is a deterministic function of the design's discrete identity (the topology identifier and the vector of snapped bin indices), which is the circuit analogue of the word-type construction. Selectivity is the probe score on the real property minus the probe score on the control. Every probe number in the thesis is reported net of this.
- *Description length.* The online (prequential) code, with the standard block schedule at 0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.25, 12.5, 25, 50 and 100 per cent of the probe training set. This is included because probe accuracy has been shown to reverse its ranking of layers across random seeds while the description length stays stable, and this thesis reports layer comparisons.

**4. Supervised head, the learnability certificate.** A separate head on the same skeleton and the same data, trained to predict the property directly. A statement of the form "the model failed to learn X" is only made when this head reaches X.

**5. Intervention test.** For design d and property i:

- Compute the simulator Jacobian J at d (§2.3).
- Build `u_i` as the component of the gradient of property i orthogonal to the span of the other monitored properties' gradients, normalised. This moves i while holding the rest still, exactly to first order.
- Evaluate at a small step (2% in log-sizing space) and at a large step, with the path simulated at five points out to 0.3 decades. At the large step the held properties do move; their co-movement is measured and regressed out of the response error rather than assumed away.
- Build a second direction set that moves the shortcut candidates without moving i: directions in the null space of the gradient of i with a large component along a shortcut feature's gradient.
- Score: response error on the first set (a model that uses the property tracks it) and response magnitude on the second (a model that uses a shortcut moves when it should not).
- All directions are constructed within a model bin, and any bin crossing along a path is logged and that path excluded from the headline with the exclusion count reported.

**6. Held-out-direction test.** Arm B-S scored separately on directions marked trained and untrained in §4.3. The gap between them is the cleanest available evidence of a model that contains a property without using it, and it is the only instrument that isolates whether derivative supervision generalises across directions.

**7. Propagation test.** In §4.6.

**Shortcut candidates.** Found two ways. By correlation inside each training set: any cheap feature (a single device width, a width ratio, total gate area, a bias current) whose correlation with a property exceeds a pre-registered threshold on that training set. And by construction: training sets in which a chosen cheap feature is deliberately made to co-vary with a property, so that a gap can be attributed to the shortcut rather than to accident. The constructed sets are described in §4.7.

### 4.6 The propagation test

**Statement.** The first-order spread of property i under manufacturing mismatch is the model's sensitivity to the per-device offsets, propagated through the process covariance. Because §2.2 established that covariance is the identity in the standardised coordinates z, the propagated spread is simply

```
sigma_hat_i = sqrt( sum_k ( d fhat_i / d z_k )^2 )
```

evaluated at the design's nominal chip, where k runs over the four mismatch coordinates of every device. No per-chip training is needed at all; a faithful sensitivity gives the spread for free. That is the test.

**The two-way decomposition, which is what makes the result interpretable.** Three quantities are compared, not two:

1. `sigma_MC`, the Monte Carlo spread from simulated chips (the truth).
2. `sigma_sim`, the same first-order propagation using the **simulator's** finite-difference offset Jacobian.
3. `sigma_hat`, the same propagation using the **model's** offset Jacobian.

`sigma_sim` against `sigma_MC` measures how good first-order propagation is for that property at that design, independently of any learned model. `sigma_hat` against `sigma_sim` measures the model. Without this control, a property whose spread is genuinely nonlinear in the offsets (an offset voltage near a null, a phase margin near a pole crossing) would be scored as a model failure. The thesis reports both ratios, per property, as distributions of the logarithm of the ratio over the evaluation set, plus the rank correlation across designs, which is what a yield-aware search would actually use.

**Evaluation set.** 500 designs spanning the families, each with: the model's offset Jacobian by automatic differentiation; the simulator's offset Jacobian by central differences at 0.5 standard deviations, which is 2 × 4 × n_devices simulations; and 200 chips for the Monte Carlo reference, giving a relative error on a spread of about five per cent.

**If it fails.** Arm B-het runs, to establish whether the spread was learnable from per-chip samples at all. The conditional-mean argument predicts that a squared-error model learns no spread unless the objective or the input carries it; the offset input is exactly the "input carries it" branch, so a failure of propagation with a success of B-het localises the failure to the sensitivity rather than to the information.

### 4.7 Constructed shortcut sets

For each of three chosen properties per family, a training set is built in which a cheap feature is made to co-vary with the property beyond its natural correlation, by rejection sampling designs until the correlation reaches a pre-registered target (0.9, against a natural baseline that is measured and reported). A matched control set of the same size has the correlation broken by the same rejection sampling in the opposite direction.

The mechanism then makes a further prediction that is tested rather than asserted: adding coverage along the constructed shortcut direction closes the response gap without adding quantity. Operationally, a third set of the same size adds designs that vary the property while holding the shortcut feature fixed, and the prediction is that the response error on that property falls to the control set's level at unchanged N.

### 4.8 Units

The full battery is repeated in ordinary and logarithmic units, on inputs (widths, lengths, currents) and on outputs (decibels, decades). The two-by-two of input units against output units is run at one dataset size; the remaining studies use the two diagonal modes. This is worth doing because the published supervised benchmark for this domain normalises everything linearly to the unit interval and never compares, so the question is open in the literature, and because a coordinate change is exactly the kind of intervention that moves what a probe can read without moving what a model uses.

### 4.9 Compute

Estimates at stage 0, at the AutoCkt schematic figure of 2.4 s per testbench, to be replaced by measured runtimes after claim 1's month-2 study.

| Item | Simulations | Core-hours |
|---|---|---|
| Training pools, all sizes and strategies, with reuse across cells | about 60,000 | 40 |
| Derivative labels for B-S (4,000 designs, 40 directions, central differences) | 320,000 | 215 |
| Intervention evaluation (500 designs, 12 properties, 2 direction sets, small step and a 5-point large-step path, plus the Jacobians that construct the directions where not already paid for) | about 120,000 | 80 |
| Propagation evaluation (500 designs: offset Jacobians plus 200 chips each) | 160,000 | 107 |
| Units, ablations, seeds | about 60,000 | 40 |
| **Pre-layout total** | **about 720,000** | **about 480**, roughly 15 hours on 32 cores |

The physical stage is bounded by restricting post-layout and Monte Carlo response measurement to 200 designs and 40 directions, which is 16,000 post-layout simulations at roughly 90 s, about 400 core-hours, plus reuse of every chip claim 1 already simulated. v11 §11's figure of about 100,000 pre-layout simulations for the propagation evaluation set is close to the propagation line above and is superseded by this table.

### 4.10 Fallbacks

- **The subcircuit patch fails.** Then the offsets cannot be set explicitly. Fallback: run mismatch with a logged seed and recover the draws by reading them out of ngspice's own listing of the resolved model parameters per instance [verify that the parameters can be dumped per instance]. If that also fails, the offset-input arm is dropped, the propagation test is run against the simulator's offset Jacobian only as a statement about first-order propagation in this process, and the model side of the test is reported as not runnable with the reason. Claim 2's other three parts are unaffected.
- **`.SENS` does not reach the parameters.** Covered: finite differences are the default, not the fallback.
- **The response gap is absent outside the constructed sets.** Then the finding is that these models are more faithful than the world-model and shortcut literature would predict, reported as such, and claim 3 is tested on the constructed sets, where the error profile is manufactured on purpose and therefore spans a known range.
- **The cross-topology model is much worse than per-family models.** Report both; the per-family control exists precisely to keep this from being read as a fidelity result.

### 4.11 Analysis and figures

Fixed before training. Anything else is exploratory and labelled.

1. Response error against aggregate accuracy, one point per model, per property, with the rank correlation between them. The claim is that the correlation is weak on the affected properties; the figure has to be able to show that it is strong, and does so if it is.
2. Per-property response error by arm (A, B, B-S, B-J) at each dataset size separately, never pooled, because the derivative-supervision literature states its advantage is largest at low data volume and near the training boundary and that comparison would be hidden by pooling.
3. Held-out-direction gap for B-S, trained against untrained directions, per property.
4. Coverage against quantity: response error on the affected properties, three strategies by four sizes, with the pre-registered flip prediction marked on the plot.
5. Probe scores net of control task, with description length beside them, per layer, per property, against response error on the same property. The read-versus-use gap is this figure.
6. Intervention test: response error on property-moving directions against response magnitude on shortcut-moving directions, per model.
7. Propagation: distributions of log(sigma_sim / sigma_MC) and log(sigma_hat / sigma_sim) per property, plus rank correlation across designs.
8. Constructed shortcut sets: response error on shortcut, control and coverage-added sets, at equal N.
9. Units: the full battery in two modes, with the two-by-two at one size.
10. FALCON replication: probes and aggregate accuracy under the three selection strategies and four sizes.

Statistical treatment: differences between arms and strategies are tested with paired tests across seeds and folds with Holm correction, reported beside effect sizes; no test is a headline; the curves and distributions are.

### 4.12 Build order, months 6 to 30

- **Months 6 to 8.** Property table. Skeleton implemented and trained as arm A on the trajectory pool; leave-topology-out folds fixed; aggregate accuracy reproduced to the level the literature reports, as an acceptance test of the implementation. Pair construction and arm B. Claim 2 pre-registration frozen and committed.
- **Months 8 to 12.** Sensitivity labels; arm B-S and the weight sweep; arm B-J. Instruments 1 to 4 with control tasks and description length. Direction dictionaries.
- **Months 12 to 15.** Instrument 5 and 6. Constructed shortcut sets and the coverage-adds-not-quantity prediction.
- **Months 15 to 18.** Coverage versus quantity, all twelve cells. FALCON replication. Units. Fidelity paper submitted about month 18.
- **Months 18 to 24.** Physical targets: post-layout and Monte Carlo properties as targets, offsets as inputs, the patched subcircuits in the loop.
- **Months 24 to 30.** Propagation test with its two-way decomposition; B-het if it fails; extension or follow-up paper.

### 4.13 Risks specific to claim 2

- **Absorption.** The nearest occupant is now a zero-shot analog evaluator on this very process: sixty amplifier topologies (sixteen from AnalogGym plus forty-four new), 60,000 parameter-performance pairs each, about 3.6 million instances on sky130 with ngspice, a pin-level transformer, and a held-out-topology result of 0.143 mean absolute percentage error against 0.301 for a multilayer perceptron. That is a bigger cross-topology dataset on the thesis's own process than the thesis will build. It reports no code or data release. Two consequences: the thesis does not compete on dataset size, and if that dataset is released it should be used, with the thesis's contribution staying the response, intervention, held-out-direction and propagation measurements, none of which that work performs. This changes v11 §7's absorption paragraph (§9).
- **The change-based arm collapses to the forward arm.** Guarded by the non-separability check in §4.3, which is a pre-registered pass or fail, not a judgement.
- **Derivative supervision helps everywhere, including untrained directions.** That is a clean positive result for B-S and is reported as such; the claim is written to accept either outcome.
- **Probes are uninformative because everything is decodable.** Likely on a cross-topology model with a rich readout, and the reason the intervention test, not the probe, is the load-bearing instrument. The probe's role is to establish the contrast, and a flat probe result with a large response gap is the cleanest form of the claim.

## 5. Claim 3, utility

**Claim (v11 §3).** On specifications limited by layout or by variation, the per-property response error on the limiting properties predicts the number of expensive checks a model-guided repair loop needs, for continuous sizing moves and for discrete finger-count moves, and aggregate accuracy does not.

**What is already known, so that the claim is stated at its true width.** That a model's aggregate accuracy need not track its usefulness for control is established outside circuits: one-step likelihood is "not always correlated with control performance" in model-based reinforcement learning, where the reported correlation between validation likelihood and episode reward ranges from 0.59 down to 0.07 and to minus 0.06 depending on the setting, and where fine-tuning a model to raise its likelihood from 4.827 to 4.85 dropped the reward from 176 to 98; two models are value-equivalent when they induce the same Bellman updates on the functions the planner uses; and weighting the model loss by value gradients beats maximum likelihood at low capacity. In surrogate-assisted optimisation, a controlled study with an adjustable pseudo-surrogate finds that performance stops improving above a pairwise comparison accuracy of about 0.7 to 0.8 for two of its three model-management strategies, and is flat in accuracy for the third. Inside circuits, one 2026 sizing paper states that "no prior work provides quantitative analysis of how prediction accuracy relates to convergence" and separately concludes that "convergence depends on the measurement-feedback architecture, not prediction accuracy"; and the closest analog optimisation paper that reports both held-out accuracy and iterations-to-target reports them as two tables and never relates them, with its own numbers showing two methods sharing a surrogate family differing by more than a factor of ten in iterations.

So claim 3 tests a known principle in a new domain, and the specific new quantity is the **per-property** response error on the **limiting** property, against the aggregate accuracy that the surrounding literature reports.

**One prior-art correction that narrows the novelty claim.** A learned model conditioned on a change already exists in analog sizing: DNN-Opt's critic takes a design and a delta and predicts the resulting specifications, trained on the roughly N-squared pseudo-samples formed from all pairs of evaluated designs, and it selects which candidate to simulate. That is a change model used as a ranker. What it does not do, and what no circuit paper found does, is measure the model's response fidelity against the simulator or relate it to search cost. The thesis's claim is therefore about the measurement, not about the object, and v9's remark that no prior change-prediction model exists inside circuits is withdrawn (§9). The combination that does appear unoccupied is a language-model proposer with a learned ranker gating expensive physical checks.

### 5.1 Fixed definitions

**Episode.** A triple (design, layout policy, specification) drawn from claim 1's database, where the design passes cell 0 and fails cell PCM under that policy. Each episode carries claim 1's diagnosis: the limiting property at PCM, the cell at which it first failed, the per-property pre-versus-post deltas, and the worst corner.

**Episode set.** 60 episodes, stratified 15 apiece over claim 1's four failure classes (parasitic-sufficient, corner-sufficient, mismatch-sufficient, interaction-only), spread across families, generators and both policies, with the allocation fixed by a seeded draw and pre-registered. Every design in the episode set, and every post-layout or Monte Carlo result belonging to it, is excluded from every ranker's training data by design id.

**Actions.** Two sets, run as separate conditions and also jointly:

- *Continuous.* A change in log-sizing space, bounded to 0.3 decades per device per step, clipped to the benchmark's ranges, snapped to model bins, with the snap logged.
- *Finger.* A change of plus or minus one or two fingers on any device, subject to the matched-pair constraints of the topology, applied through the finger override of §3.2.

Placement is not an action. Predicting the effect of a placement move needs the layout as a model input, which is a different model, and the exclusion is stated rather than assumed.

**Cheap check.** One stage-0 simulation of a candidate. Allowed to every method, counted separately, never the headline currency.

**Expensive check, as a ladder.** A candidate that survives the cheap check is laid out under the episode's policy, LVS'd and extracted, then evaluated on a ladder that stops at the first failure:

1. extracted netlist, worst corner from the diagnosis, nominal devices: 1 simulation;
2. extracted netlist, worst corner, 20 chips: 20 simulations.

A candidate that survives the ladder is a **provisional pass**. The **accept criterion** is the full signoff cell of claim 1, extracted, all 29 corners, 50 chips (200 if near threshold), run once, on the provisional pass only. An episode is solved when a candidate meets the accept criterion.

**Cost.** The primary currency is the number of expensive checks. The secondary currency is simulator seconds, because the ladder makes checks unequal and because a method that fails early cheaply should not be penalised for it. Both are reported; the pre-registered headline is the number of checks.

**Budget and censoring.** 25 expensive checks per episode. Episodes not solved within the budget are **right-censored, not dropped**. Censoring is expected to be common, and treating unsolved episodes as missing would bias every comparison toward methods that fail fast, so the analysis in §5.4 is a survival analysis from the start.

**Model-management strategy.** The number k of top-ranked candidates that pay for an expensive check per round, k in {1, 2, 4}. This is a controlled factor rather than a fixed choice, because the one controlled study of surrogate accuracy against optimiser performance found that whether accuracy matters at all depends on the management strategy.

### 5.2 The loop

Per round, for the model-guided method:

1. **Diagnose.** From the verdict stage: the limiting property, the failing cell, the measured shortfall in the property's own units, and the per-property pre-versus-post deltas. Rendered as a sentence, for example "extracted parasitics cut unity-gain bandwidth by 35 per cent; phase margin unchanged".
2. **Propose.** A language model receives the netlist, the diagnosis, the action space with its bounds, the device operating regions at the last evaluated point, and the full history of previous proposals with their measured outcomes, and returns 16 candidate repairs with a one-line reason each. The prompt structure follows what the published language-model sizers actually do: operating regions and previous best designs as few-shot context, explicit instructions about the direction and size of the correction, and a re-request on malformed output.
3. **Screen.** Each candidate gets one cheap check. Candidates that fail the geometric or bin checks are discarded and counted.
4. **Rank.** The change model predicts, for each surviving candidate, the change in every property at the signoff cell, and the candidates are ordered by predicted worst-property margin there.
5. **Check.** The top k pay for an expensive check.
6. **Update.** History is appended; the loop returns to step 2 until an accept or the budget.

The layout is regenerated at every expensive check, because the sizing changed. The policy is fixed within an episode.

### 5.3 Baselines

All on the same harness, the same episodes, the same budget, the same accept criterion.

- **B1, language model alone.** Steps 1, 2, 3 and 5 with no ranker: the first k candidates that pass the cheap check pay for an expensive check. This isolates the ranker.
- **B2, Bayesian optimisation on the expensive simulation.** Constrained multi-objective acquisition ensemble, whose code is public. Batch 5; the two-stage constraint handling, feasibility-first before any feasible point and the six-objective Pareto front afterwards; recommendation pruning threshold 0.05; differential-evolution acquisition optimiser with population 100 and 2,000 evaluations; the paper's exploration constants.
- **B3, multi-fidelity Bayesian optimisation.** Low fidelity is stage 0, high fidelity is the expensive ladder. Squared-exponential automatic-relevance-determination Gaussian process at low fidelity; nonlinear fusion at high fidelity with the product-plus-sum kernel; weighted expected improvement with feasibility factors; the fidelity gate that evaluates at high fidelity only when the low-fidelity posterior variance falls below 0.01; multiple-start acquisition optimisation with the paper's 10 and 40 per cent sampling around the incumbents.
- **B4, the published post-layout sizing loop, re-implemented.** Two coupled Bayesian models, a tree-structured Parzen estimator plus Gaussian process on pre-layout and a Gaussian process on post-layout, sharing a joint prior with the stated posterior update of the high-fidelity kernel, expected improvement on both, and a fixed interval of one post-layout evaluation every five pre-layout evaluations. **The paper publishes no code, and it does not state: the Gaussian process kernel family, the estimator's quantile, the kernel-density bandwidth, the number of random initial points, the penalty weight in the figure of merit, or how the acquisition is optimised over the mixed continuous and integer space.** Our choices, logged as ours and reported in the paper: Matern 5/2 with automatic relevance determination and a constant mean; quantile 0.15; Scott's rule for bandwidth; 10 random initial points; penalty weight 1.0 on the clipped violation; acquisition optimised over 2,000 random candidates with local refinement of the best ten. Sensitivity to the two most consequential choices, the post-layout interval and the quantile, is reported as a small sweep on a subset of episodes.
- **B5, multi-fidelity Bayesian neural network.** Two output heads for schematic and post-layout on shared weights, Hamiltonian Monte Carlo posterior with 200 samples, two hidden layers of 100, trust-region search with batch 8, and the paper's own choice of assigning fidelity at random to selected candidates, which its authors leave as future work.
- **B6, discount re-run.** One expensive check measures a per-property discount, the ratio of post-layout to pre-layout value; the pre-layout specification is tightened by that ratio; the episode's original generator is re-run pre-layout under the tightened specification; the result gets another expensive check; repeat. This is the dynamic over-design trick used by a published robust sizing framework, which reports that it "generally takes no more than two rounds" on a single-stage amplifier. It is cheap and may well win, which is why it is in the table.

### 5.4 The headline analysis

**Rankers.** Twelve rankers from claim 2, chosen before any episode runs to span the error range: arms A, B and B-S at each of three pre-registered combinations of dataset size and selection strategy, which is nine; plus two constructed-shortcut models whose response error on one named property is bad by construction; plus one model degraded by label noise, to extend the range upward. Each carries, measured on held-out designs of the same family at the physical cells: response error per property, response error on the episode's limiting property, sign accuracy, Jacobian cosine agreement, and aggregate accuracy.

**Outcome.** Number of expensive checks to accept, right-censored at 25.

**Primary model.** A mixed-effects survival model (accelerated failure time on the log of the check count, with a proportional-hazards fit reported alongside), with random effects for episode and for ranker, and fixed effects for: response error on the limiting property; aggregate accuracy; initial margin shortfall; failure class; family; action set (continuous, finger, joint); and k.

**Primary test.** A nested comparison: does the limiting-property response error add predictive power over aggregate accuracy? Reported as a likelihood-ratio test, a difference in information criterion, and, because a single p-value on twelve rankers is thin evidence, a leave-one-ranker-out cross-validated concordance. The reverse nesting is reported too. If aggregate accuracy survives and per-property error does not, that is the answer to claim 3 and is reported as plainly as the other direction.

**Pre-registered alternative shapes.** Two, both fitted and compared before looking at which is prettier:

- *Saturation.* Cost improves with fidelity up to a threshold and then flattens, as the controlled surrogate study found above accuracy 0.7 to 0.8. A piecewise-linear fit with a free breakpoint is fitted alongside the linear one.
- *Strategy dominance.* The management strategy k explains more than any fidelity measure, which is what that same study found for one of its three strategies, and what the self-calibrating sizing paper concluded when it attributed convergence to the feedback architecture rather than to prediction accuracy. The k main effect and its interaction with fidelity are in the model from the start.

**Secondary, mediation.** The rank correlation, Kendall tau, between the ranker's ordering of a round's candidates and the ordering the simulator would have given, computed on every round where at least four candidates were eventually evaluated. This is the metric the neural-architecture-search predictor literature uses, and it sits between the model's error and the loop's cost. Whether tau mediates the relation between response error and check count is a pre-registered secondary question: if it does, the mechanism is clean; if per-property error predicts cost while tau does not, that is a finding about which errors matter.

### 5.5 Compute

Per expensive check: layout about 60 s on the single-threaded queue, extraction about 30 s, then 1 to 21 simulations at roughly 60 s each on the extracted netlist, so about 0.37 core-hours as a working average with the ladder's early exits.

| Item | Checks | Core-hours |
|---|---|---|
| 12 rankers times 60 episodes times up to 25 checks | up to 18,000 | up to 6,700 |
| 6 baselines times 60 episodes times up to 25 checks | up to 9,000 | up to 3,300 |
| Accept runs, ladder validation, k sweep, action-set conditions | about 3,000 | about 1,100 |
| **Total** | **up to 30,000** | **about 11,000, roughly 14 days wall on 32 cores** |

These are upper bounds: solved episodes stop early, and the ladder means most checks cost one or twenty-one simulations rather than the full signoff. The budget is recomputed from measured runtimes at month 30 before the loop is launched, and the reduction ladder is: k fixed at 2 rather than swept; rankers cut from twelve to eight, keeping the extremes of the error range; episodes cut from 60 to 40 while keeping the four failure classes balanced. Episode count is cut last, because the analysis's power comes from episodes times rankers.

### 5.6 Figures

1. Checks to accept, per method, as survival curves with censoring marked. The loop against all six baselines.
2. Checks to accept against response error on the limiting property, one point per (ranker, episode) with ranker means, faceted by failure class, with the fitted linear and saturating curves.
3. The same against aggregate accuracy, on the same axes and the same scale. These two figures are the claim.
4. The nested-model comparison as a table with both directions of nesting and the cross-validated concordance.
5. Kendall tau per round against response error, and the mediation result.
6. Action set: continuous against finger against joint, per method.
7. k sweep: cost against fidelity at each k, testing the strategy-dominance shape.
8. Cost in simulator seconds beside cost in checks, so a reader can see the ladder's effect.

### 5.7 Build order, months 30 to 42

- **Months 30 to 32.** Episode set drawn and frozen. Loop harness: diagnosis renderer, proposer, screener, ranker interface, ladder, accept. Claim 3 pre-registration frozen and committed, including the ranker list and their measured error profiles, which are known before any episode runs.
- **Months 32 to 34.** B1 and B6 (the cheap baselines) on all episodes; the harness's acceptance test is that B6 reproduces the qualitative behaviour its source paper reports.
- **Months 34 to 37.** B2, B3, B5, and the B4 re-implementation with its sensitivity sweep.
- **Months 37 to 40.** The twelve rankers on all episodes; the k sweep; the action-set conditions.
- **Months 40 to 42.** Analysis, figures, paper submitted.

### 5.8 Risks and negative results

- **The conventional approach wins.** Expected, and reported. The headline is whether response error predicted which searches went badly, not whether the loop wins. B6 in particular may beat everything, and that is a useful thing to publish.
- **Censoring dominates.** If most episodes are unsolved by every method, the survival model still works but power collapses. Mitigation: episode difficulty is stratified by initial margin shortfall as well as failure class, and a pilot of 10 episodes at month 32 measures the solve rate before the full set runs. If the pilot solve rate is below about a quarter, the budget rises to 40 checks and the episode count falls to 40, which keeps the compute constant.
- **All rankers are similar.** Then the range of response error is too narrow to regress against. Mitigation is built in: the constructed-shortcut models and the noise-degraded model exist to widen the range on purpose, and their error profiles are known before the episodes run.
- **The proposer is the bottleneck.** If the language model rarely proposes a repair that could work, every method's cost is dominated by the proposer and no fidelity measure predicts anything. Diagnostic: the fraction of rounds in which at least one proposed candidate would have passed had it been checked, measurable after the fact on a subsample by checking all sixteen candidates in ten episodes. That subsample is budgeted (about 1,000 extra checks, inside the accept-and-validation line above) and reported whatever it shows.
- **Model drift.** As in claim 1: the proposer's model identifier and date are recorded per round, and a change of model mid-study is a reported event, not a silent one.

## 6. Gated items

These sit outside the spine. Each has a gate, a deliverable, a fallback, and a date at which it is cut if the gate has not opened. If all three are cut, claims 1 to 3 stand unchanged.

### 6.1 Compact-model bridge, months 12 to 24

**Gate.** The group holds, or will measure, device-to-device and cycle-to-cycle variability data on one device, and agrees that a student may model and publish it (supervisor question 2). Decided by month 12; cut if unanswered.

**What the published record says about the intended deliverable, and why it changes.** v11 §6 specifies "a simulator-ready statistical compact model ... in the dual-network style of Novkin and Amrouch, exported as Verilog-A or OSDI". Reading that paper today, the authors did not export to Verilog-A. They integrated hand-written C implementations of their current and charge networks into an unnamed commercial simulator, and they state the reason directly: Verilog-A "cannot perform matrix multiplications efficiently, which results in a significant performance loss of any integrated NN", and simulator-side code cannot use the graphics card. Their speed results are for that C integration: an eight-neuron network at 56.1 thousand DC points per second against 52.6 for the simulator's built-in compact model and 24.5 for the Verilog-A version of it. Separately, the OpenVAF compiler's own materials list arrays, genvars, hidden states, Laplace filters, paramsets and hierarchical modules as unsupported, and neither the compiler's presentation nor the free-software compact-modelling survey mentions statistical or random-distribution constructs at all. A neural network of any width inside Verilog-A therefore cannot be assumed to compile or to be fast.

**Deliverable, restated as a ladder.** The deliverable is unchanged in purpose (a model of one measured device that ngspice can Monte Carlo) and changed in form:

1. **Primary.** A physics-based or empirical compact model of the device with **explicit statistical parameters**, in Verilog-A compiled through OpenVAF to OSDI, in the style of the ferroelectric capacitor model that carries one parameter's standard deviation as a Monte Carlo variable. Parameter statistics are extracted by backward propagation of variance: measure a set of device performances, compute the sensitivity of each performance to each model parameter by simulation, and solve the resulting linear system in the variances for the parameter variances, checking that the sensitivity matrix is well conditioned and that no solved variance is negative. This is the method the mismatch-modelling literature uses, and it produces exactly the object claim 2's propagation test consumes: a diagonal (or, if the conditioning demands it, correlated) covariance over named model parameters.
2. **Secondary, only if the compiler allows it.** A small neural correction network on top, with weights as parameters, checked first for whether the current OpenVAF supports the array constructs it needs [verify]. If it does not, the correction is a polynomial or spline in the same Verilog-A, which is what the compact-modelling community uses in practice.
3. **Fallback.** If Verilog-A cannot carry the model at all, the model stays in Python, the statistics are produced by a sweep, and the handoff to any circuit simulation is by a table plus a covariance, which is exactly the handoff the tile needs anyway (§6.2).

**Validation.** Held-out measured devices for the mean behaviour; a distribution comparison for the statistics; and one circuit-level check, an ngspice Monte Carlo of a small circuit built from the modelled device, because a device model with correct currents and wrong small-signal slopes does not converge in a circuit simulator. Derivative terms in the loss are used for that reason, following the neural compact-modelling line that supervises on transconductance and output conductance and their derivatives.

**If the device is a gallium nitride transistor** (from the group, a collaborator, or a foundry sample set), the physical baseline is the industry-standard surface-potential high-electron-mobility model rather than a bulk silicon model, the variability that matters is threshold spread, dynamic on-resistance and self-heating rather than area-scaled mismatch, and there is a demonstrated route: a recent paper fits that model in ngspice 42 with a published model version, tuning about forty core parameters by Bayesian optimisation from datasheet curves alone. That is the extraction harness to reuse; the thesis's addition would be the statistics, which that paper does not do.

### 6.2 Computing-in-memory tile, months 36 to 44

**Gate.** The bridge delivered a device model, and the operational-amplifier loop of claim 3 finished on schedule. Decided at month 36. The operational-amplifier loop is the primary test of claim 3 either way.

**Why it is a good test.** Every specification is variation-limited by construction, so claim 2's propagation and claim 3's cost regression are run where the effects are central rather than marginal, with no engineered specifications needed.

**Family.** One fixed resistive-memory crossbar with its word-line and bit-line drivers, sense amplifiers and column converters, with a scripted regular layout and one converter design taken from the literature and held constant. Design variables: array size, converter resolution, stored conductance range and number of levels, wire width and multiplicity, and the sizing of the sense path.

**Properties.** Inference accuracy of a fixed small network mapped onto the tile, energy per multiply-accumulate, read latency.

**Cheap and expensive checks.** Cheap: the ideal-wire, nominal-cell tile model. Expensive: a statistical array simulation with extracted or modelled wire resistance, per-cell programming and read noise from the device model's statistics, and temperature. The same three-way decomposition as claim 1 (wiring, corners, per-cell mismatch) applies unchanged.

**How a device model reaches the tools, verified today.** None of the three statistical simulators ingests Verilog-A, so the handoff is statistical in every case, and the three differ in what they accept and in what they model:

- **NeuroSim V1.5** has a device-expert mode (per-state conductance distributions, stuck faults, drift, supplied as comma-separated tuples in `mem_states.csv`) and a circuit-expert mode which takes, verbatim, "mean and standard deviation for each output state ... in a comma separated format (.csv file), where each row of the file corresponds to the mean for each given output (post-ADC) and the standard deviation of the output", generated from Monte Carlo SPICE or silicon. The two modes are used separately to avoid double counting. It does **not** model current-resistance drop along the lines; its own future-work section names lookup-table noise modelling for that.
- **CrossSim** takes a user-written programming-error function: set `error_model` to a new keyword, add a clause to `applyCustomProgrammingError` in `weight_error_device_custom.py`, and return a modified conductance matrix in normalised units, which is then used as a matrix of standard deviations. It **does** model array parasitic resistance, with three one-transistor-one-resistor topologies and an internal iterative circuit solver, and it models read noise resampled every multiply-accumulate and converter quantisation with several range options.
- **AIHWKit** is functional. Its own conclusion says it is "solely focused on the algorithmic development and functional verification for ANN training and inference on emerging analog chips" and "is not intended to estimate run time, latency, or power performance of a hardware chip". v11's quoted phrase about "algorithmic and functional levels" does not appear in the paper and is corrected in §9.

So the tile uses CrossSim where line resistance and programming error matter and NeuroSim where power, area and latency matter, with the device statistics generated by ngspice Monte Carlo of the bridge model and handed to each in its own format. That division is stated because it determines which of the tile's three properties can be trusted from which tool.

**Device model if the bridge is cut.** The SkyWater resistive-memory primitive is a deterministic filament model with seventeen fixed parameters and no statistical hooks, in a repository archived read-only in April 2026, so it cannot carry a variation study. The substitute is Synaptogen, a generative model trained on 6,000 cycles of 512 measured one-transistor-one-resistor devices, reproducing cycle-to-cycle and device-to-device variability with quantile transforms and a Gaussian-mixture device model, released under the MIT licence with a Zenodo archive. Its Verilog-A implementation is documented as tested in a commercial simulator only; whether it compiles through OpenVAF and runs in ngspice is the first check of the tile month [verify]. Its published benchmarks are in a commercial simulator and include a 256-by-256 crossbar write taking about 25 days, which sets the array size the tile can afford.

### 6.3 Chip

**Gate, restated against today's schedule.** v11 §6 assumes "a slot lines up near month 20". Checked today: the most recent SkyWater shuttle on the shared-tile service, TTSKY26c, opened 26 May 2026 and closed on 7 September 2026, with delivery estimated 27 March 2027; the earlier TTSKY26b closed 18 May 2026 with delivery 4 November 2026. No later SkyWater shuttle is announced. The gate is therefore restated: **if a SkyWater shuttle opens with a close date between months 16 and 24**, submit; otherwise the chip is not attempted and the thesis says so. The assumption of a month-20 slot is not supported by anything public today (§9).

**Cost, from the published specification page today.** Tiles at about 70 euros each (a 2025 figure), analog pins at 40 euros for the first two and 100 euros for each further pin, minimum project 140 euros. A one-by-two tile of 160 by 225 micrometres with two analog pins is 220 euros; with four pins it is 420 euros. Plus a development kit and shipping, the total stays under a thousand euros, as v11 states.

**The measurement constraint, which decides the design.** The shared shuttle places an analog switch between pads and the design, specified at under 500 ohms, under 5 picofarads and 4 milliamps, with at most six analog pins and metal 5 reserved for the power grid. For a high-impedance amplifier output that is not a small perturbation: the measurement is of the design plus the switch. Either an on-chip output buffer is designed from the start, or the measurement is arranged so the path cancels, and either costs area on a very small tile. This is a design-time decision, not a measurement-time one.

**What it can and cannot show.** One chip is one sample from the manufacturing distribution. It can confirm that a nominal design works and that the simulated nominal was right; it cannot test a claim about variation. It is a demonstration, and the thesis does not depend on it.

## 7. Schedule and decision points

| Months | Claim 1 | Claim 2 | Claim 3 | Gated |
|---|---|---|---|---|
| 1 to 2 | toolchain, AutoSizer full-flow reproduction, ALIGN subset experiment, verify list, first family end to end, pre-registration frozen | sensitivity and offset checks piggyback in month 1 | | |
| 3 to 4 | all generators on the first family; preprint at month 4 | | | |
| 5 to 6 | all families through the signoff cell; predictor; paper submitted; database tagged | property table begins | | |
| 6 to 12 | | skeleton, arms A and B, pre-registration frozen at month 8, derivative labels, arms B-S and B-J, instruments 1 to 4 | | bridge starts if gate open at month 12 |
| 12 to 18 | | instruments 5 and 6, constructed shortcuts, coverage versus quantity, FALCON replication, units; fidelity paper about month 18 | | bridge |
| 18 to 24 | | physical targets, offset inputs | | bridge delivers or is cut at month 24 |
| 24 to 30 | | propagation test, B-het if needed, follow-up paper | | |
| 30 to 36 | | | episode set, harness, pre-registration at month 30, cheap baselines, expensive baselines | |
| 36 to 42 | | | rankers, k sweep, action sets, analysis, paper about month 42 | tile starts if gate open at month 36 |
| 42 to 48 | write-up | write-up | write-up | tile to month 44 |

**Decision points.**

- **D1, month 2.** Does the OSIRIS placer run on new sizings? If not, the preprint ships with ALIGN alone and OSIRIS moves to month 5; if it still fails, the policy comparison becomes ALIGN against ALIGN with a perturbed constraint file, labelled as the weaker comparison it is.
- **D2, month 2.** Does the subcircuit patch work? Decides whether per-chip correspondence and the offset-input arm are available, and triggers the fallbacks in §3.2 and §4.10.
- **D3, month 4.** Preprint goes out regardless of completeness.
- **D4, month 8.** Does arm B clear the non-separability check? If not, it is reported as having collapsed to arm A and the arm comparison is rewritten around A, B-S and B-J.
- **D5, month 12.** Bridge gate. Supervisor's answer to question 2.
- **D6, month 18.** Is there a response gap outside the constructed sets? If not, §4.10's branch applies and claim 3 runs on the constructed sets.
- **D7, month 30.** Claim 3 compute recomputed from measured runtimes; the reduction ladder in §5.5 applied if needed.
- **D8, month 32.** Episode pilot solve rate. Below about a quarter, the budget rises to 40 checks and the episode count falls to 40.
- **D9, month 36.** Tile gate.
- **D-chip, whenever a shuttle opens with a close date in months 16 to 24.**

If the whole plan slips, Year 4 becomes Year 5 and nothing is reordered.

## 8. Pre-registration and the honesty rules

**Three pre-registration documents**, each committed to the repository and cited by commit hash in its paper, with a deviations section in the paper listing every departure:

- `prereg/claim1-preregistration.md`, month 2. Contents as in the claim 1 plan §9, plus the amendments of §3.2.
- `prereg/claim2-preregistration.md`, month 8. The property table; the definitions of response error, Jacobian agreement and aggregate accuracy in §4.1; the skeleton and its hyperparameter search space; the arms and their losses; the non-separability threshold; the direction dictionaries and the trained-untrained split; the probe families and the control-task construction; the description-length schedule; the constructed-shortcut targets; the dataset sizes and selection strategies; the coverage-flip secondary prediction; the units modes; the propagation evaluation set and its two-way decomposition; the figure list.
- `prereg/claim3-preregistration.md`, month 30. The episode set with its stratification; the action sets; the ladder and the accept criterion; the budget and the censoring rule; the twelve rankers with their already-measured error profiles; the primary survival model and the nested test; the two alternative shapes; the mediation question; the figure list.

**Before "the model failed to learn X" may be written**, all four must hold, as in v11 §5: the supervised head reaches X (the information was there); the per-family control has been run (not a capacity artefact); the control-task baseline has been subtracted (not probe flexibility); and the alternative arms have been run (not one architecture). In addition, the mechanism must be stated in advance and must make a further prediction that is then tested: shortcut learning predicts that adding coverage along the constructed shortcut direction closes the gap without adding quantity (§4.7); the conditional-mean argument predicts that a squared-error model learns no spread unless the objective or the input carries it (§4.6).

**Both directions are reported.** Every claim in §3, §4 and §5 is written so that the opposite outcome is a result: if survival is high, if the response gap is absent, if derivative supervision generalises, if propagation works, if aggregate accuracy predicts search cost as well as per-property error does, the finding is stated plainly and the thesis is the map either way.

**Nothing is pooled that the pre-registration says is reported separately**, in particular arm B-S against B at each dataset size, and survival curves per generator.

## 9. Corrections to carry into v12 and elsewhere

### 9.1 Into `phd-plan-v12.md`

1. **§4, mismatch covariance.** "The covariance carries all four SkyWater mismatch terms (vth0, toxe, voff, nfactor), each with its own area scaling" overstates the model. All four share the same area law, one over the square root of `l*w*mult`; what differs is the per-device, per-bin slope coefficient, and several of those coefficients are zero. The covariance in standardised coordinates is the identity. The Drennan and McAndrew citation still belongs, as the reason to carry four parameters rather than one and as the reason not to claim the model is silicon, but not as evidence that the kit implements four different area laws.
2. **§4, the model skeleton.** "A published learned circuit model (CktGNN- or INSIGHT-style)" should become a device-level graph skeleton. CktGNN's benchmark is a behavioural abstraction whose nodes are transconductance stages, resistors and capacitors, and the DICE authors state it "is not suitable for device-level circuit evaluation"; INSIGHT is per-topology, takes no graph, and has no public code. The public device-level comparators are DICE's encoder and FALCON's edge-centric network.
3. **§4, per-chip draws.** "It is known exactly in simulation" is true only with the subcircuit patch of §2.2; with a bare seed the draws are positional and do not correspond between netlists. Say so.
4. **§7, the FALCON absorption numbers.** The 28.8 per cent against 1.1 per cent comparison is not like-for-like and should not be presented as one. The 1.1 per cent is a five-topology average for the competing method trained per class on three in-class topologies and fine-tuned at its first graph layer; the 28.8 per cent is FALCON trained on nineteen topologies and fine-tuned at its output head, and the per-topology spread behind that average is wide. FALCON's own paper reports a different held-out experiment: one excluded topology at 30.4 per cent zero-shot, falling to 0.9 per cent after fine-tuning only its output head on about 30,000 samples of that topology. The honest statement is that held-out-topology accuracy is cheap to bolt on and is already reported by two groups with incompatible protocols, which strengthens rather than weakens the argument that aggregate accuracy is the wrong quantity.
5. **§7, absorption, missing occupant.** ZEROSIM (arXiv 2511.07658) belongs in the risk and in §4: a pin-level transformer surrogate on SkyWater 130 nm across sixty amplifier topologies (sixteen from AnalogGym plus forty-four new), 60,000 parameter-performance pairs per topology for about 3.6 million instances, eleven properties, trained with a percentage-error loss, evaluated zero-shot on ten unseen topologies at 0.143 mean absolute percentage error against 0.301 for a multilayer perceptron, with a reinforcement-learning sizing demonstration. It is the closest thing to this thesis's skeleton on this thesis's process, and it reports no code or data release. It does not measure response fidelity, intervention behaviour, held-out directions or propagation.
6. **§2 and §8, prior change models.** DNN-Opt's critic already takes a design and a change and predicts the resulting specifications, trained on the roughly N-squared pairs of evaluated designs, and uses it to choose what to simulate. The thesis's change-based arm is therefore not the first change-conditioned circuit model; its novelty is that the response is measured against the simulator and related to search cost. v9 §3's "Inside circuits I found no prior change-prediction model" is withdrawn.
7. **§6, the bridge deliverable.** The dual-network paper integrated C code into an unnamed commercial simulator and states that Verilog-A cannot do matrix multiplication efficiently; OpenVAF's own materials list arrays and several other constructs as unsupported and mention no statistical constructs. "Exported as Verilog-A or OSDI" is not established for a neural model. Restate the deliverable as the ladder in §6.1.
8. **§6, AIHWKit quote.** The phrase "at the algorithmic and functional levels, as opposed to hardware and circuit design levels" is not in the paper. The paper says it is "solely focused on the algorithmic development and functional verification for ANN training and inference on emerging analog chips" and "is not intended to estimate run time, latency, or power performance of a hardware chip". Replace the quotation.
9. **§6, tile tooling.** Add that NeuroSim V1.5 does not model current-resistance drop along the array lines while CrossSim does model parasitic resistance with an internal circuit solver, so the two tools answer different parts of the tile question and both are needed. NeuroSim's circuit-expert input is a comma-separated file of post-converter output means and standard deviations; CrossSim's is a Python function returning a modified conductance matrix.
10. **§6, chip timing.** No SkyWater shuttle is currently announced with a close date after 7 September 2026, when TTSKY26c closed. "If a slot lines up near month 20" should become a conditional on a shuttle opening at all, with the tile prices and the pin pricing as quoted in §6.3.
11. **§7, sensitivity risk.** Invert it. Finite differences by re-simulation are the plan of record, at two runs per direction; `.SENS` is an optimisation to be adopted only if it reaches the parameters and agrees. This removes a risk and costs nothing, since the finite-difference budget is already in §4.9.
12. **§11, budgets.** Claim 2's pre-layout budget is about 720,000 stage-0 simulations and about 480 core-hours (§4.9), not 100,000; claim 1's post-layout budget roughly doubles under the factorial, as the claim 1 plan already noted; and claim 3 adds up to about 11,000 core-hours (§5.5).
13. **§4, circuit families.** Carry the two corrections the claim 1 plan already listed: AnalogSAGE's ten problems are specification sets rather than fixed-topology families, and the OSIRIS circuits carry no specification, so the five specifications used are ours.

### 9.2 Into `claim1-implementation-plan.md` v2

Amendments A1 to A10 of §3.2, plus: CACE's datasheet format is 5.2, not the 5.0 shown in the 2024 slides; "extracted" means CACE's `rcx` and never `pex`; the device-name preservation assumption is replaced by the LVS device map; and the OSIRIS dataset licence is CC-BY-4.0 on its dataset card, leaving only the code archive's licence open.

### 9.3 Into `papers/README.md`

1. The file `(2020) Probing_the_Probing_Paradigm arXiv2005.01810.pdf` is **not** that paper. It is Klafka and Ettinger, "Spying on your neighbors: Fine-grained probing of contextual embeddings for information about surrounding words", ACL 2020, which is indeed arXiv 2005.01810. Ravichander, Belinkov and Hovy, "Probing the Probing Paradigm: Does Probing Accuracy Entail Task Relevance?", is arXiv 2005.00719 and is not in the folder. Relabel the row and obtain the missing paper.
2. The instrument attribution "decodable is not used" belongs to Ravichander's control datasets and to amnesic probing, both summarised in Belinkov's survey, not to the information-theoretic probing paper, which argues the opposite methodological point: always use the most expressive probe.
3. Add ZEROSIM's identifier (arXiv 2511.07658) and correct its row with the facts in §9.1 item 5.
4. Add a note to the DNN-Opt row that its critic is change-conditioned and trained on pairwise pseudo-samples.
5. Add ZOAF (arXiv 2606.02869) and the row-based analog layout synthesis paper (arXiv 2606.21767) as to-read for the claim 1 related work.
6. PANDA's process node is not stated anywhere in its paper; the row should not imply one.
7. Synaptogen: the repository states the MIT licence and a Zenodo archive; the paper documents testing in a commercial simulator only.
8. OSIRIS: the Hugging Face dataset card gives CC-BY-4.0.

## 10. Verify list

### 10.1 Month 1, each about half a day on a running toolchain

1. Units of `l` and `w` in the mismatch expressions, and the resulting numerical value of the threshold area coefficient.
2. Which sections of the installed `sky130.lib.spice` set `MC_MM_SWITCH=1` with `MC_PR_SWITCH=0`, and what CACE's Monte Carlo condition enables.
3. That ngspice evaluates an `AGAUSS` default once per subcircuit instance; that the patched device subcircuits reproduce nominal results exactly, pass netgen, and reproduce a logged random chip when given explicit offsets.
4. Whether ngspice can dump resolved per-instance model parameters, as the fallback if item 3 fails.
5. Whether `.SENS` reaches width, length and the mismatch parameters inside the sky130 subcircuits, and whether it agrees with central differences within 5 per cent on ten designs.
6. That netgen's device map is complete and one-to-one on flattened extracted netlists.
7. That ALIGN output is readable by Magic and passes netgen against the snapped netlist with no manual editing; any manual step is scripted and counted as part of the policy.
8. OSIRIS: the code archive's licence; whether the baseline placer runs standalone on a new sizing; whether its matched-pairs file can serve as ALIGN's constraint file so one file per topology serves both policies.
9. AutoSizer: the verbatim README ALIGN list; the relation between `n_trials`, `max_total_designs` and the paper's 300-sample budget; the repository licence; whether the harness accepts a new circuit from a configuration file alone; what the full-flow mode actually does; the token cost of ten seeds per circuit for four language-model generators.
10. AnalogSAGE: whether `wznmickey/AnalogSAGE` is the authors' release; if so its licence, topology database size, testbenches, supply and load conditions and per-topology selection frequencies; if not, the re-implementation decision.
11. The AMS-SizingBench width list against sky130 model bins.
12. That one ngspice version satisfies the sky130 mismatch models, the AutoSizer harness and CACE.
13. CACE 5.2's Monte Carlo condition syntax and its batch interface, against the thin-runner decision.
14. That every corner library section resolves for every device type the families use, including resistors and capacitors, and that the mismatch switch applies to every device type and to nothing else when process variation is off.
15. FALCON's dataset download size, format and licence.
16. Whether DICE's pretrained encoder checkpoint is downloadable, for the initialisation ablation.

### 10.2 Before submission

- Obtain Ravichander et al., arXiv 2005.00719.
- Obtain through the library: the joint sizing-and-layout paper (ISPD 2023), Learn-by-Compare (DAC 2024), PVTSizing (DAC 2024), the two layout-generator papers, and Kinget (JSSC 2005).
- Read ZOAF (arXiv 2606.02869) and the row-based layout synthesis paper (arXiv 2606.21767).
- Check whether ZEROSIM has released code or data, and whether its dataset can be used.
- Check the current OpenVAF release for array support and for any statistical constructs, for §6.1.
- Compile Synaptogen's Verilog-A through OpenVAF and run it in ngspice, for §6.2.
- Check whether any SkyWater shuttle has opened, for §6.3.
- Check whether the AutoSizer authors, or the Pan group, have published a population post-layout number.

## 11. Sources read for this document

**Primary PDFs in `papers/`, read 8 September 2026** by four parallel extractions covering: learned circuit models (CktGNN, INSIGHT, DICE, GCN-RL, the few-shot pretraining graph network, the radio-frequency informed graph network, the supervised analog and radio-frequency benchmarks, FALCON, ZEROSIM, the threshold-specification work, the extrapolation study, and pairwise difference regression); methodology instruments (linear probes, control tasks, information-theoretic probing, minimum description length probing, the probing-classifier survey, shortcut learning, Sobolev training, Sobolev-trained surrogates for optimisation, Jacobian regularisation, gradient-enhanced physics-informed networks, gradient-enhanced approximations, gradient-enhanced networks for airfoil design, heteroscedastic uncertainty, the pitfalls of heteroscedastic estimation, data pruning beyond scaling laws, threshold-boundary active learning, lightweight probabilistic propagation, sloppiness and identifiability, and the extrapolation-of-physical-laws note); search loops and baselines (the post-layout sizing loop, multi-fidelity Bayesian optimisation, the acquisition-ensemble methods, multi-fidelity surrogates, robust reinforcement-learning sizing, layout-aware Bayesian neural networks, objective mismatch, value equivalence, iterative value-aware model learning, value-gradient weighting, the surrogate-accuracy study, neural-architecture-search predictors, function-family structure, joint surrogate learning of sensitivities, self-calibrating equation-based sizing, DNN-Opt, trust-region reinforcement learning, AutoCkt, PANDA, EEsizer, ADO-LLM, LEDRO); and variability and gated items (Pelgrom, Drennan and McAndrew, backward propagation of variance, variability-aware compact modelling, distributionally robust design, four yield-estimation papers, the dual-network compact model, the OpenVAF materials and the free-software compact-modelling survey, ferroelectric variability modelling, the datasheet-driven high-electron-mobility extraction, Synaptogen, NeuroSim V1.5, the CrossSim manual, AIHWKit, ASiM, the memristive-crossbar tutorial, the precision review, and two of the group's device papers).

**Tool and repository pages, read 8 September 2026**: the SkyWater device mismatch corner files for the n-channel and p-channel 1.8 V transistors; the open_pdks model conversion as documented by the UCSC tutorial and community threads; the ngspice news and sensitivity-analysis documentation; the CACE repository, datasheet-format and command-line documentation; the AutoSizer repository, its README and its commit history; the ALIGN repositories; the OSIRIS dataset card; the FALCON repository; the Synaptogen repository; the DICE, CktGNN and AICircuit repositories; Magic's `ext2spice` command reference; Google's Gemini deprecation page; and the shared-shuttle chip list and analog specification pages.

Facts stated without a "[verify]" marker were read from one of the sources above. Estimates are labelled as estimates. Anything that could not be found is said to be not found rather than inferred.
