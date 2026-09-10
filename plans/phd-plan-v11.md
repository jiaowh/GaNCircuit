# PhD Research Plan, v11

**Working title:** Do learned circuit models respond to design changes the way the simulator does, and does that decide whether AI-designed analog circuits survive layout and manufacturing variation?

**Candidate:** part-time, The Hong Kong Polytechnic University. **Proposed supervisor:** Prof. Yang Chai (Applied Physics). **Co-supervisor:** to be named in electronic design automation or machine learning.

Dated 7 September 2026. Supersedes v10. Changes from v10 are listed in §9; all rest on passages read in the primary PDFs, indexed in `papers/README.md`. The v9 source list (§15) still applies except where §9 of v10 and §9 below correct it.

---

## 1. What we are trying to achieve

AI systems now size and lay out analog circuits and report first-try pass rates above 90%. Every one of those numbers is measured before layout, at the typical corner, with perfectly matched devices. The checks that actually decide whether a chip works, extracted parasitics, process-voltage-temperature corners and device mismatch, are not in the score. One system that does re-simulate after layout (PANDA) loses more than half its bandwidth on its only reported op-amp. Nobody has reported, for a population of AI designs, how many survive.

The same systems increasingly replace the simulator inside their search loops with a learned model. A search uses that model for one thing only: to predict what a proposed change will do. Nobody checks whether the model's predicted response to a change matches the simulator's. Accuracy on held-out designs is reported instead, and it is not the same quantity.

The goal is therefore two things, in order:

1. Measure how much of today's AI analog design output survives physical signoff, and why it fails.
2. Make the learned models that guide search faithful on the properties signoff bites on, and show that this fidelity, not accuracy, is what saves expensive checks.

Everything in this plan serves one of those two. Anything that does not is in §8.

## 2. Thesis statement

A learned circuit model is useful for signoff-aware design search to the extent that its predicted response to a design change matches the simulator's on the properties that limit the specification. That per-property response fidelity (a) is not measured by aggregate accuracy, (b) is set by which designs the training set covers rather than how many, (c) extends from sizing changes to manufacturing spread through the model's sensitivity to per-device parameters, and (d) predicts how many expensive post-layout and Monte Carlo checks a repair loop needs.

## 3. Claims

**Claim 1, measurement.** Of AI-sized designs that meet specification pre-layout, the fraction that still meets it after extracted parasitics, across corners, and under Monte Carlo mismatch, reported as curves against specification margin, differs by generator, circuit family and layout policy. Failures are decomposed into parasitic, corner and mismatch causes. Which designs survive is predictable from pre-layout features, with the predictor holding on families and generators it was not fitted on. The fall with margin is expected; the shape, the decomposition, the policy gap and the out-of-sample predictor are the claim.

**Claim 2, fidelity.** In a learned circuit model, the per-property response error, the difference between the model's predicted change under a design change that moves property X and the simulated change, comes apart from aggregate accuracy and from what a probe can read out of the model. Which properties are affected is set by training coverage, not quantity. Supervising the model on simulator sensitivities along some directions improves, or fails to improve, its response along directions it never saw; either result is reported. The model's sensitivity to per-device parameter offsets, propagated through the process's known mismatch covariance, predicts, or fails to predict, the Monte Carlo spread of each property.

**Claim 3, utility.** On specifications limited by layout or by variation, the per-property response error on the limiting properties predicts the number of expensive checks a model-guided repair loop needs, for continuous sizing moves and for discrete finger-count moves, and aggregate accuracy does not.

Claim 1 is a paper, not a thesis. Claims 2 and 3 are the thesis. Claim 1 is first because it builds the pipeline claims 2 and 3 run on, and because one group already holds the code that produces its headline number (§7).

**What is already established, and what is not.** That a model's aggregate accuracy need not track its usefulness for control is known in model-based reinforcement learning: one-step likelihood "is not always correlated with control performance" (Lambert et al., 2020); two models are value-equivalent if they yield the same Bellman updates on the functions the planner uses (Grimm et al., 2020); weighting the model loss by value gradients beats maximum likelihood at low capacity (Voelcker et al., 2022). In surrogate-assisted optimisation, one controlled study with an adjustable pseudo-surrogate finds that for two of three model-management strategies performance stops improving above an accuracy of 0.7 to 0.8 (Hanawa et al., 2025). Claim 3 therefore tests a known principle in a new domain. What no prior work measures, in circuits or elsewhere, is a surrogate's per-property response to a design change against the simulator's, or its Jacobian agreement, and whether that quantity predicts search cost. The one analog paper that reports both held-out accuracy and iterations-to-target (arXiv 2512.00712) reports them as separate tables and does not relate them.

## 4. Method

**Process and tools.** SkyWater 130 nm only. It is the process the measured generators run on; it has per-device mismatch models scaled by area, two automatic layout tools (ALIGN, OSIRIS's baseline placer), Magic extraction and ngspice. Sizings are snapped to model bins before simulation and the snap is logged.

**Circuit families.** OSIRIS's five circuits, the ALIGN-supported amplifiers of AMS-SizingBench, and AnalogSAGE's ten op-amp problems. Fixed topologies; AI chooses sizings. AI-invented topologies are excluded because each needs its own layout template, so a topology population would measure the layout tool. AutoSizer publishes no per-circuit ALIGN list; its README says "simple OTAs and amplifiers". The exact subset is established by running ALIGN on all twenty-four circuits in months 1 to 2 and is reported as a result, not assumed.

**Populations (claim 1).** Sizings from every generator AutoSizer's harness already re-implements under one budget (genetic, Bayesian, trust-region Bayesian, ADO-LLM, LEDRO, EEsizer), from AutoSizer itself, and from AnalogSAGE. Two single-pass layout policies, one layout per design each: ALIGN and the OSIRIS baseline. Failures logged by stage: geometric rejection, bin snap, place-and-route, layout-versus-schematic, extraction, specification. Monte Carlo in two stages: fifty chips per design, two hundred for designs whose pass fraction lands near the threshold.

**The model (claims 2 and 3).** One cross-topology skeleton, a published learned circuit model (CktGNN- or INSIGHT-style), taking the netlist as a graph plus sizing plus, optionally, a vector of per-device parameter offsets that is zero at nominal. Per-family small networks are run as a capacity control. Three arms on identical simulation budgets:

- A: plain forward model, design in, performance out.
- B: change-based model, design and change in, change in performance out. The hypothesis is that putting the used quantity on the target trains better; B versus A tests it.
- B-S: arm B additionally supervised on simulator sensitivities along a recorded subset of directions, in sizing and in per-device offsets.

A fourth arm, B-het, which predicts a mean and a spread from a few simulated chips per design, is run only if the propagation test in claim 2 fails, to establish whether the spread was learnable at all.

B-S against B is reported at each of the four dataset sizes separately, never pooled. Sobolev training's advantage is reported to be "especially significant in cases of low data volume and/or optimal points near the boundary of the training dataset" (Tsay, 2021), and the coverage-versus-quantity design below spans a factor of ten in size, so a pooled comparison would hide the interaction that claim 2 is about.

**Why per-device offsets are an input, not an inferred latent.** A chip's mismatch draw has four random terms per device, so twenty to forty dimensions on these families, against about a dozen output scalars. It is known exactly in simulation but not identifiable from the outputs, and offset sees only the difference within a matched pair. Inferring the draw would test identifiability, which is linear algebra, not a model. Supplying it as an input and asking whether the model's sensitivity to it is faithful tests the model. The first-order spread of any property is the model's per-device sensitivity vector propagated through the process's area-scaled covariance, so a faithful sensitivity gives the spread with no per-chip training at all. That is the propagation test.

The covariance carries all four SkyWater mismatch terms (vth0, toxe, voff, nfactor), each with its own area scaling, not a single Pelgrom threshold term. Threshold mismatch "does not follow a simplistic 1/sqrt(area) law, especially for wide/short and narrow/long devices, which are common geometries in analog circuits" (Drennan and McAndrew, 2003), and op-amp input pairs sit in exactly those regimes. A propagation test built on the area law alone would misestimate spread for a reason that has nothing to do with the model.

**Instruments, fixed in advance.**

1. Linear probe on the model's internals.
2. Nonlinear probe, to separate "not there" from "probe too weak".
3. Control task: both probes on meaningless targets; every probe score is reported net of this.
4. Supervised head on the same skeleton and data, predicting the property directly; a failure to learn X counts only if this head reaches X.
5. Intervention test: for each property, a sizing direction chosen from simulator sensitivities that moves X while holding the other monitored properties near still; a second set moves the shortcut candidates without moving X. For large changes the path is simulated and co-movement regressed out.
6. Held-out-direction test: arm B-S scored separately on trained and untrained directions.
7. Propagation test: predicted spread from the model's per-device sensitivities against Monte Carlo spread.

Shortcut candidates are found by correlation inside each training set and by construction: training sets in which a cheap feature is made to co-vary with a property.

**Coverage versus quantity.** Three selection strategies (random, language-model-proposed, chosen near failure boundaries) crossed with four dataset sizes spanning a factor of ten. The claim needs the size axis flat and the selection axis not. Repeated on FALCON's public million-circuit set with probes only, since its process is closed. A secondary prediction is recorded in advance: with abundant data the best selection keeps hard, boundary examples, and with scarce data it keeps easy ones (Sorscher et al., 2022), so the ranking of the three strategies is expected to change across the size axis.

**Repair loop (claim 3).** A candidate that passes pre-layout goes through layout, extraction, corners and Monte Carlo. The measured shortfall ("extracted parasitics cut bandwidth by 35%") is fed to a language model that proposes repairs. Action space: continuous sizing changes and finger-count changes, both representable in the netlist. Placement is fixed by the layout policy, not an action, because predicting the effect of a placement move needs layout as an input and that is a different model. The change model ranks proposals; only the top-ranked pay for an expensive check. Expensive checks to a passing design are counted. Baselines on the same harness: language model alone, Bayesian optimisation on the expensive simulation, multi-fidelity Bayesian optimisation, and the post-layout sizing loop of Gao et al. (2024), re-implemented from the paper because no code is published. The headline is whether per-property response error predicted which searches went badly, not whether the loop wins.

**Units.** The full battery is repeated in ordinary and logarithmic units on inputs and outputs.

## 5. What makes a negative result a finding

Before "the model failed to learn X" can be said: the supervised head must reach X (information was there), the per-family control must be run (not a capacity artefact), the control-task baseline must be subtracted (not probe flexibility), and the alternative arms must be run (not one architecture). The mechanism is stated in advance and makes a further prediction that is then tested: shortcut learning predicts that adding coverage along the constructed shortcut direction closes the gap without adding quantity; the conditional-mean argument predicts that a squared-error model learns no spread unless the objective or the input carries it.

If the cross-topology model shows no response gap outside the constructed sets, the finding is that these models are more faithful than expected, and claim 3 is tested on the constructed sets. If per-property error predicts search cost no better than aggregate error, that is the answer to claim 3 and claims 1 and 2 stand.

## 6. Timeline

Assumes roughly half-time effort. If it slips, Year 4 becomes Year 5; nothing is reordered.

- **Months 1 to 2.** Reproduce AutoSizer's full flow (ALIGN, Magic, post-layout simulation) on its supported amplifiers. Establish the ALIGN-supported subset by running all twenty-four circuits. Time a fresh layout per sizing under both policies. Run the two sensitivity checks from §9 on the first working netlist.
- **Months 1 to 6.** Survival pipeline and populations. Preprint with one family and both policies at month 4. Submit claim 1 paper by month 6.
- **Months 6 to 18.** Arms A, B, B-S at the pre-layout stage. Instruments 1 to 6. Constructed shortcut sets. Coverage-versus-quantity on own simulations and on FALCON. Submit the fidelity paper around month 18.
- **Months 18 to 30.** Add post-layout and Monte Carlo targets. Per-device offset inputs. Propagation test. Units comparison. Extend or follow up the fidelity paper.
- **Months 30 to 42.** Repair loop against baselines. Submit the utility paper.
- **Months 42 to 48.** Write up.

**Gated, outside the spine.** Decided by the supervisor's answers in §10.

- *Compact-model bridge.* A simulator-ready statistical compact model of one device the group has measured, in the dual-network style of Novkin and Amrouch, exported as Verilog-A or OSDI. Runs in months 12 to 24 only if the group holds device-to-device variability data and agrees to its publication. Otherwise cut at month 12. The device is whatever the group measures; the bridge does not care which. If it is a GaN HEMT, from the group, a collaborator, or a foundry sample set, the physical baseline is ASM-HEMT or MVSG rather than BSIM, the folder already holds the ASM-HEMT extraction and physics-informed GaN modelling papers, and the variability that matters is p-GaN gate threshold spread, dynamic on-resistance and self-heating rather than area-scaled mismatch. The deliverable is the same: a Verilog-A model with per-device statistical parameters that ngspice can Monte Carlo. This is the only place GaN enters the plan; see §8 for why it enters nowhere else.
- *Computing-in-memory tile.* The repair loop and instruments on a fixed resistive-memory crossbar family, where every specification is variation-limited by construction. Runs in months 36 to 44 only if the bridge delivered a device model and the op-amp loop finished on schedule. The op-amp loop is the primary test of claim 3 either way. Two facts fix how the bridge would reach the tile. NeuroSim, CrossSim and AIHWKit do not load Verilog-A: NeuroSim V1.5 takes per-output mean and standard deviation from Monte Carlo SPICE or silicon in its "circuit expert" mode, CrossSim takes a user-written Python programming-error function, and AIHWKit describes itself as working "at the algorithmic and functional levels, as opposed to hardware and circuit design levels". So the device model runs in ngspice Monte Carlo and its statistics are handed over. And the SkyWater resistive-memory primitive is a deterministic filament model with seventeen fixed parameters and no statistical hooks, in a repository archived read-only in April 2026; the substitute is Synaptogen, a Verilog-A model trained on 6,000 cycles of 512 measured 1T1R devices that reproduces cycle-to-cycle and device-to-device variability.
- *Chip.* A 1×2-tile shuttle submission of one AI-sized amplifier, under a thousand euros, if a slot lines up near month 20. One chip is one sample and proves nothing about variation. Design the output buffer for the shuttle's analog switch from the start or the measurement is worthless. A GaN multi-project-wafer slot (X-FAB XG035 or imec GaN-IC through Europractice) is not a substitute: it costs many times the ceiling, needs a hand-drawn layout under a licensed design kit, and would carry a circuit outside the measured families.

## 7. Risks

- **Infrastructure eats a year.** The ALIGN-plus-Magic path already exists in AutoSizer's public code; month 2 is a reproduction. If the OSIRIS placer cannot be made to work, the first paper ships with ALIGN alone and says so.
- **Scoop on claim 1.** AutoSizer's repository has a full-flow mode that computes per-metric post-layout degradation for the best design per run; as of its last commit on 26 May 2026 neither the paper nor the README reports any post-layout, corner or Monte Carlo result. GLOVA's group holds the schematic-level equivalent at 28 nm. Analog-DB (September 2026) adds 68 pre-layout circuits on three open processes and states that all verification is pre-layout and mismatch is not modelled. The group closest to the headline number is now identifiable: the Pan group at UT Austin holds the MAGICAL lineage, a layout-aware Bayesian sizer (ICCAD 2023), and an August 2026 agent that already runs 31 extractions and 11 post-layout simulations per design on a MAGICAL-derived generator, at 65 nm and 40 nm, with no corners or Monte Carlo. A population survival number is one experiment away for them. The flag flip yields one nominal number on a subset; the curves, decomposition, policy gap and out-of-sample predictor do not fall out of it. Preprint at month 4 regardless, and earlier if one family is ready.
- **No response gap exists.** Covered in §5.
- **Absorption.** A systems group adds probing to FALCON or INSIGHT. Held-out-topology accuracy is already a published axis: with FALCON retrained by the authors of arXiv 2508.16403 and tested on five topologies excluded from training, weighted mean relative error is 28.8%, against 1.1% with their fine-tuning. That kind of test is cheap to bolt on, and it is aggregate accuracy, which the thesis says is the wrong quantity. The constructed shortcut sets, held-out directions and propagation test are the parts unlikely to be bolted onto a systems paper; if they are, pivot weight to claim 3.
- **Sensitivity analysis does not reach parameters inside the process's device wrappers.** Fallback is finite differences by re-simulation, seconds per design.
- **Department fit.** An Applied Physics committee may read this as computer science. The gated bridge and tile exist for this, and the §10 questions decide whether they run. A co-supervisor in EDA or ML is named before submission.
- **The conventional approach wins the loop.** Expected and reported; the thesis is the map, not the method.

## 8. Deliberately left out

- **The latent world-model framing (Tan et al., arXiv 2607.27017, v3, 31 July 2026).** Every instrument above predates it: linear probes (Alain and Bengio, 2016), control tasks (Hewitt and Liang, 2019), shortcut learning (Geirhos et al., 2020), derivative supervision (Czarnecki et al., 2017). The paper's hidden-variable mechanism has nothing to grip in circuits, where every property is determined by the inputs. Cited as related work; not load-bearing.
- **A per-chip latent-variable arm and an explicit-spread-label arm.** Replaced by the propagation test, which asks the same question with a known covariance and no inference.
- **A JEPA-style latent-predictive arm.** Its self-supervised motivation is weak for a dozen exact scalars that cost a second each.
- **A three-month premise check.** The property table (input-determined or not, rewarded by the objective or not) is a one-page appendix.
- **Placement moves in the repair loop.** Need layout as a model input; different model.
- **GaN as a process for claims 1 to 3.** Three platforms were considered: X-FAB XG035 (GaN-on-Si depletion-mode HEMTs, 100 to 650 V, PCell and SPICE-model PDK, open-access MPW via Europractice since 2025), imec GaN-IC (200 V GaN-on-SOI enhancement-mode p-GaN HEMTs with depletion-mode HEMTs and Schottky diodes, MPW via Europractice under a design-kit licence), and Hanhua Semiconductor (Suzhou; GaN-on-sapphire and GaN-on-Si epitaxy and foundry services, no public IC design platform). None can carry the spine, for four reasons that do not depend on which platform. The design kits are licensed, so a population of netlists could not be published and none of the sizing generators in §4 has been ported to them. ALIGN, MAGICAL and Magic have no GaN process abstraction, so there is no automatic layout policy to measure. The platforms offer n-channel HEMTs only, so the op-amp families do not exist; GaN-IC design is gate drivers, level shifters and half-bridges. And signoff there is dominated by dynamic on-resistance, trapping and self-heating rather than by extracted parasitics and area-scaled mismatch, with no public statistical model of p-GaN threshold spread to serve as the propagation test's reference covariance. Whether AI-designed GaN power circuits survive dynamic on-resistance and thermal signoff is a real open question, but it replaces this thesis's layout-and-mismatch spine rather than extending it. GaN therefore enters only through the compact-model bridge in §6, as one candidate device, and only if measured device populations exist.
- **AI-invented topologies, process transfer, aging, a full pivot to compute-in-memory co-design, a learned device model as ground truth, a language model inside the core model.** Reasons unchanged from v9 §14. EXPLORE, the strongest topology generator read, reaches 65% success at tolerance 0.01 on a six-component power-converter benchmark and 0 to 26% at seven to ten components, which confirms that a topology population would be dominated by generator validity rather than by layout.

## 9. Changes from v10 and items to verify

Changed in v11, each against the primary PDF:

- §3 gains a paragraph placing claim 3 against model-based reinforcement learning and the one controlled surrogate-accuracy study, and narrows the stated gap to per-property response fidelity and Jacobian agreement.
- §4 requires B-S versus B to be reported per dataset size (Tsay, 2021).
- §4 requires the propagation covariance to carry all four SkyWater mismatch terms (Drennan and McAndrew, 2003).
- §4 records that Gao et al. (2024) publish no code; the baseline is re-implemented.
- §4 and §6 make the ALIGN-supported subset a month 1 to 2 result, since AutoSizer publishes no list.
- §6 fixes how a device model reaches the tile (ngspice statistics into NeuroSim's circuit-expert mode or CrossSim's custom error function) and names Synaptogen as the ReRAM substitute.
- §7 names the Pan group as the likely scoop source and updates AutoSizer's status.
- §7 adds the held-out-topology result for FALCON to the absorption risk, with corrected numbers (28.8% against 1.1%, five topologies; an earlier figure of 216.7% circulated from a superseded version and is not in v3).
- §6 and §8 record the GaN entry points: a GaN HEMT is an admissible device for the compact-model bridge, and X-FAB XG035, imec GaN-IC and Hanhua Semiconductor are recorded with the reasons none can carry claims 1 to 3 or the chip. Platform facts are from the vendors' and Europractice's public pages, read 7 September 2026; MPW pricing was not obtained and "many times the ceiling" is an estimate to confirm if the chip is pursued.

Verify items from v9 §15 and v10 §9 now closed:

- FALCON: the primary paper states a 45 nm CMOS process design kit and a fixed 30 GHz simulation frequency.
- EXPLORE: figures above, from its Table 1 and Table 2.
- SABLE: 16 nm FinFET on Spectre, an LC-VCO and a two-stage op-amp, three corners with worst-corner gating, no layout, no Monte Carlo.
- Tan et al.: v3, 31 July 2026, confirmed from the arXiv stamp.
- EEsizer's variation numbers: confirmed against the paper (PTM 90 nm, o3, size σ 5 nm and Vth σ 10 mV, 10 then 50 samples, 78% and 76%). The authors themselves say a full Monte Carlo with device models "should also be used".
- Analog-DB: the "23 circuit-kit bindings" and "17 of 23 imported sizings failed their testbenches" figures refer to the regulator corpus, not all 68 circuits.
- Derivative loss in neural-network compact models: present in the Hu group's BSIM-NN line (gm, gds and their derivatives; charge second derivatives), in the Amrouch group's dual-network and KAN models, and in Kam et al. 2021; absent in the gate-all-around ANN model and, explicitly, in NN-VS; the physics-informed papers use PDE or DAE residuals instead. The lineage claim in v9 §3 is stated as "the SPICE-integrated neural compact models supervise on conductances up to second order", not as universal.
- NeuroSim, CrossSim, AIHWKit Verilog-A ingestion: none; see §6.
- SkyWater ReRAM statistical parameters: none; see §6.
- OpenFASoC op-amps measured in silicon: no public count exists. The tapeout README names op-amp tiles on the SkyWater Nanofab run but reports no measurements. Item dropped.
- Gao et al. (2024) code: none published.
- Liu 2021 and ParaGraph: now in the folder, read at survey level; both predict parasitics or use parasitic embeddings for sizing on single designs and neither predicts survival of a population, so claim 1's out-of-sample predictor stands as stated. ParasGB (July 2026) adds 20 analog designs at 180 nm BCD and 6 SRAM subsets at TSMC 28 nm with post-layout RC labels, public but on closed processes; related work for the predictor, not a population source.

Still to verify before submission:

- Whether ngspice `.SENS` reaches width, length and the mismatch parameters inside the SKY130 subcircuits.
- Whether the mismatch terms can be set as explicit per-device parameters for the offset-input arm.
- Budak et al. (ISPD 2023), Learn-by-Compare (DAC 2024), PVTSizing (DAC 2024) and the two glayout papers: not open-access; download through the library before submission.
- Kinget (JSSC 2005) for the mismatch-tradeoff citation; paywalled.

## 10. Questions for the supervisor before submission

1. Which computing in memory: device-level and neuromorphic, or macro- and architecture-level?
2. Does the group hold device-to-device and cycle-to-cycle variability data on any device, and may a student model and publish it?
3. Is a co-supervisor in EDA or ML acceptable, and who?
4. Will the department examine a thesis whose first paper is a measurement study on an open process and whose core is a study of learned models?

Answers to 2 and 4 decide whether the bridge and tile run and whether the department is the right one.

## 11. Resources

One consumer graphics card. A 32-core workstation. Free open process kits. Monte Carlo budget: claim 1 about 175,000 post-layout simulations for a two-thousand-design population, one to four days; claim 2 about 100,000 pre-layout simulations for the propagation evaluation set, hours. If the claim 1 budget binds, the yield-estimation literature now in the folder (normalising-flow and variational importance sampling, learned-prior multi-corner analysis) offers cheaper estimators for the near-threshold designs; brute-force Monte Carlo stays the reference. Chip, if any, under a thousand euros.

## 12. Sources

`papers/README.md` indexes all 156 papers in the folder by the section they support, lists what could not be obtained open-access, and records the verified findings behind §9.
