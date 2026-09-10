# Claim 1 implementation plan, v1

**Claim being implemented (v11 §3).** Of AI-sized designs that meet specification pre-layout, the fraction that still meets it after extracted parasitics, across corners, and under Monte Carlo mismatch, reported as curves against specification margin, differs by generator, circuit family and layout policy. Failures are decomposed into parasitic, corner and mismatch causes. Which designs survive is predictable from pre-layout features, with the predictor holding on families and generators it was not fitted on.

**Deliverables.** A preprint at month 4 with one family under both layout policies; a submitted paper at month 6; and the pipeline, populations and result database that claims 2 and 3 run on. Dates assume the half-time effort of v11 §6 and a start in month 1.

Dated 7 September 2026. Companion to `phd-plan-v11.md`. Facts about the benchmarks below were read from the primary PDFs in `papers/` on this date. Items marked "[verify]" have not been checked on a running tool and are on the month 1 list in §10. Two things this plan found that v11 states differently are in §12.

---

## 1. Fixed definitions

These are frozen before any population is generated (§9, pre-registration). Changing one after the runs start is reported as a change.

**Property.** A scalar the testbench measures. The property list per circuit is the benchmark's list, so that the verdict matches what the generator optimised. AMS-SizingBench OTAs report DC gain, unity-gain bandwidth and DC power; its switched-capacitor and filter circuits add settling, distortion and passband figures; AnalogSAGE's problems report power, gain, common-mode rejection, power-supply rejection, gain-bandwidth, phase margin and supply-noise rejection through a testbench adapted from AnalogGym. Phase margin is added to every amplifier's list where the benchmark omits it, because a design whose phase margin falls to zero after layout is not a survivor whatever its gain does; it is added as a reported property, not as a specification constraint, unless the benchmark constrains it.

**Specification.** The benchmark's own inequality constraints on those properties.

- AMS-SizingBench states each circuit's specification as a boolean expression of thresholds (for the telescopic OTA: figure of merit above 0.1, gain above 55 dB, unity-gain bandwidth above 10 MHz, power below 50 µW) and declares a design feasible when every threshold holds. Used verbatim.
- AnalogSAGE states ten specification sets (Table 2 of its paper), for example task 3: power at most 100 µW, gain at least 80 dB, CMRR and PSRR at least 50 dB, gain-bandwidth at least 1 MHz, phase margin at least 60°, PSRN at least 50 dB. Used verbatim. Supply and load are not stated in the paper and are taken from its released testbench [verify].
- OSIRIS's five circuits carry no specification. The paper measures only the root-mean-square difference between pre- and post-layout AC traces and the area. For those five a specification is written once per circuit, anchored on the OSIRIS reference sizing: each property's threshold is the reference design's simulated value relaxed by a fixed amount (10% in linear units, 1 dB on gains, 5° on phase margin), so the reference passes with a known margin. This is the only place a specification is written rather than taken, and it is labelled as ours.

**Pass at a stage.** All constraints met at that stage. No partial credit.

**Margin.** For each property i with threshold t_i, the signed normalised distance m_i = s_i (x_i - t_i) / |t_i|, with s_i = +1 for lower bounds and -1 for upper bounds. Gain-like and bandwidth-like properties are converted to logarithmic units (dB, decades) before normalising, so that a given margin means the same thing across properties; the mapping is fixed per property in the property table. The design's margin is the minimum m_i over its constrained properties, and the property attaining it is the limiting property. Both are recorded.

**Survival curve.** For a set of designs D that pass at stage 0 and a stage S, F_S(τ) = |{d ∈ D : m_0(d) ≥ τ and d passes S}| / |{d ∈ D : m_0(d) ≥ τ}|, with τ swept over the observed range of pre-layout margin m_0. Reported per generator, per family and per policy, with Wilson intervals. A second presentation, survival against a uniformly tightened specification, is computed from the same data for the supplement; it is not the headline because it mixes properties.

**Cells.** Every design that passes stage 0 is evaluated under combinations of three binary factors: extraction (schematic or extracted netlist), corners (typical only, or the corner set), mismatch (nominal devices, or Monte Carlo).

| Cell | Netlist | Corner | Mismatch | Purpose | Run on |
|---|---|---|---|---|---|
| 0 | schematic | typical | off | generator's own verdict; population entry | all |
| P | extracted | typical | off | parasitic effect alone | all |
| C | schematic | corner set | off | corner effect alone | all |
| M | schematic | typical | MC | mismatch effect alone | all |
| PC | extracted | corner set | off | finds the worst corner post-layout | designs passing P |
| PM | extracted | typical | MC | post-layout mismatch | designs passing P |
| PCM | extracted | worst corner | MC | signoff | designs passing PC |
| CM | schematic | worst corner | MC | schematic signoff control | designs passing C |
| PCM-full | extracted | every corner | MC | validates the worst-corner shortcut | 40-design subsample |

A design that fails P fails PM and PCM by definition, since a nominal failure cannot reach a 90% pass fraction; those cells are skipped and the verdict recorded as inherited. Pass in a corner cell means pass at every corner in the set. The worst corner is the corner in the PC (or C) cell at which the design's margin is smallest. Pass in a Monte Carlo cell means the per-chip pass fraction is at least Y*.

**Corner set.** Process tt, ss, ff at supply 1.62, 1.8, 1.98 V and temperature -40, 27, 125 °C (27 points), plus sf and fs at nominal supply and 27 °C. Twenty-nine corners. This follows the CACE default for sky130 (tt, ff, ss enumerated, sf and fs available, three supplies, three temperatures) with the two skewed corners added because they move differential pairs. Circuits with a different nominal supply (the AMS-SizingBench bandgap runs at 2.0 V and is not an amplifier) are outside the families anyway. [verify: that every library section resolves for every device type the families use, including capacitors and resistors.]

**Monte Carlo.** Mismatch only: the sky130 library's mismatch switch on, process variation off, because process variation is covered by corners and the two together double-count. Fifty chips per design in stage one. Designs whose fifty-chip pass fraction lies within the Wilson 95% interval of Y* are rerun with two hundred fresh chips, and the two-hundred-chip estimate replaces the fifty-chip one. Seeds are logged so any chip can be regenerated. [verify: the sky130 library exposes mismatch-only as a section or switch separate from its process Monte Carlo section; CACE's example uses a corner named `mc`, and which of the two that enables must be read from the library file.]

**Yield threshold.** Y* = 0.90. Fifty chips resolve 0.90 to about ±0.08 and two hundred to about ±0.04; no benchmark states a yield target. The full pass-fraction distribution is stored, and the supplement reports Y* = 0.99 with the caveat that two hundred chips cannot resolve it.

**Failure decomposition.** Each design gets a pass pattern over its cells. Among designs that fail PCM, the headline decomposition counts which single factor is sufficient on its own to cause failure: parasitic (fails P), corner (fails C), mismatch (fails M), each combination of those, and "interaction only" for designs that pass all three single-factor cells and still fail PCM. It is a partition, so fractions sum to one, reported per generator, family and policy. The single-factor cells are why the design is factorial: a sequential flow of layout, then corners, then mismatch would attribute every failure to whichever stage ran first.

**Layout policy.** A named, single-pass, deterministic procedure from sized netlist to GDS with fixed settings. Two policies:

- ALIGN, default flow, one constraint file per topology written once and applied to every sizing of that topology.
- OSIRIS baseline: sequence-pair placement solved as an integer program, simulated annealing on half-perimeter wire length, Dijkstra global routing, A* detailed routing, design rules respected by construction. OSIRIS reports about 39 s per layout on its circuits against 48 to 80 s for ALIGN's single pass, and its pipeline already runs netgen LVS, Magic extraction and ngspice. Code and dataset are on Hugging Face under `hardware-fab/osiris`; the paper states no licence [verify].

One layout per design per policy, no retries, no best-of-N. Best-of-N over OSIRIS's finger and halo perturbations is a separate condition on the month 4 family only, labelled as such. MAGICAL is not a policy: OSIRIS reports it produced no valid layout for the low-pass filter.

**Finger rule.** None of the generators searches finger count: AMS-SizingBench sizes with a discrete width times an integer multiplier at fixed length, and AnalogSAGE searches per-device length, width and multiplier. Finger count is therefore a layout-time rule: the minimum valid finger assignment satisfying the topology's matched-pair constraints, applied identically under both policies and recorded per device.

**Bin snap.** Before any simulation, each device's W and L are snapped to the nearest sky130 model bin. The snap distance is recorded per device. A design whose snapped netlist no longer passes stage 0 is a "bin snap" failure, excluded from the population and counted. AMS-SizingBench's discrete width list may already sit on bins [verify]; AnalogSAGE's continuous ranges will not.

## 2. Populations

**Circuit families.** Fixed topologies; AI chooses sizings.

- OSIRIS's five circuits: Miller, Ahuja and feed-forward compensated amplifiers, a five-transistor OTA, and a low-pass filter (11, 15, 13, 5 and 13 devices). Each ships as a netlist template, an AC testbench (1 kHz to 1 GHz) and a matched-pairs file. A DC and transient testbench is added for the properties the written specification needs.
- The ALIGN-supported amplifiers of AMS-SizingBench. The benchmark has twenty-four sky130 circuits: five logic cells, two ring oscillators, three Sallen-Key filters around a folded-cascode OTA, a bandgap, an LDO, a switched-capacitor integrator, two single-stage common-source amplifiers, and eleven OTAs (five-transistor, current-mirror, telescopic, folded-cascode, and six multi-stage: active-zero, gain-boosted, nested-Miller, three-stage simple-Miller, damping-factor-control, indirect-compensation, with 24 to 35 sizing variables each). The candidates are the thirteen amplifier rows. AutoSizer publishes no ALIGN list, so the supported subset is a month 1 to 2 result.
- AnalogSAGE's ten problems, handled as described under "AnalogSAGE" below.

The OSIRIS five-transistor OTA and Miller amplifier have counterparts in AMS-SizingBench; they stay separate families because testbenches and specifications differ, and the overlap is noted.

**Generators.** The six the AutoSizer harness re-implements under one budget of 300 simulated samples per run: a genetic algorithm (population 20), Bayesian optimisation (Matérn 5/2 Gaussian process, upper-confidence-bound acquisition, 10 initial samples), trust-region Bayesian optimisation, and three language-model sizers, ADO-LLM, LEDRO and EEsizer, all on Gemini 2.5 Flash. Plus AutoSizer itself (up to three outer iterations of 100 inner samples on the same model at temperature 0.4). Plus AnalogSAGE. Eight generators. The AutoSizer paper reports three trials per circuit; here every generator runs ten seeds per circuit at the 300-sample budget. Language-model generators run with the model the paper used where it is still served, otherwise the nearest available, with the model identifier and date recorded per run. Reported success rates in the AutoSizer paper range from 25% to 100% by generator and difficulty tier, so the population will be uneven across generators; curves are reported per generator with their own intervals, never pooled across generators.

**OSIRIS families in the harness.** OSIRIS ships fixed sizings, not a sizer. Its netlist templates are wrapped as AMS-SizingBench-style circuits (a configuration file with the netbench, the variable widths and multipliers, and the written specification) so that all eight generators size them.

**AnalogSAGE.** Its ten problems are specification sets, not circuits: the agent selects a topology from a database of fifty candidates and then sizes it by Bayesian optimisation over per-device length, width and multiplier ranges. It reports 96% pass at one attempt on the ten tasks. It is therefore a generator whose output is a topology and a sizing. A design enters the population only if its topology matches one for which a constraint file exists (the OSIRIS and AMS-SizingBench amplifiers, plus any topology in its database that occurs in at least twenty of its runs, for which a constraint file is then written). Designs on other topologies are logged as "topology outside layout library" in the stage ledger and reported as a count. The ten specifications are also applied, as additional specification sets, to the AMS-SizingBench two-stage and folded-cascode OTAs under the other seven generators, so that AnalogSAGE's designs have same-specification comparators.

**Population definition.** The primary population is the final design each run reports. A run reporting no passing design contributes nothing and is counted. The secondary population is every candidate a run evaluated that passed stage 0, labelled "trajectory"; it widens the margin axis and trains the predictor, and never enters the headline curves.

**Target size.** Five OSIRIS circuits, up to thirteen AMS-SizingBench amplifiers and the AnalogSAGE specification sets give roughly twenty to twenty-eight families. Eight generators at ten seeds is about 2,000 runs; after the generators' own success rates about 1,500 to 2,000 designs pass stage 0, matching the v11 §11 budget. If the ALIGN-supported subset is small, seeds go up to hold the population near two thousand.

**Provenance.** Every design carries family, generator, seed, harness commit, language-model identifier and date, the raw sizing as proposed, the snapped sizing, the generator's own stage 0 property vector and ours. A disagreement between the two stage 0 vectors beyond simulator tolerance is a bug to be found before proceeding.

## 3. Pipeline

One Python package, one containerised toolchain, one results database. Each stage is a pure function from an input record to an output record plus a log, so any design can be rerun from any stage.

**Toolchain (pinned, one container image).** open_pdks sky130A, ngspice, Magic, netgen, ALIGN with its sky130 PDK abstraction, OSIRIS, the AutoSizer harness, AnalogSAGE, and CACE. Versions recorded in the image manifest and in every result row. [verify: one ngspice version satisfies the sky130 mismatch models, the AutoSizer harness (which cites the version 34 manual) and CACE.]

**Stages.**

1. `harvest`: run a generator on a family; emit primary and trajectory designs with provenance. Wraps the AutoSizer harness for its six generators and itself; wraps AnalogSAGE's loop.
2. `canonicalise`: map each generator's sizing representation onto one canonical netlist per topology with a device table (W, L, fingers, multiplier, model). Geometric checks, then bin snap. Emit the snapped netlist and the snap log.
3. `sim0`: our stage 0 re-simulation with the benchmark's testbench; compare with the generator's values.
4. `layout`: run a policy; emit GDS, runtime, and a stage code on failure (placement, routing, design rule check).
5. `lvs`: netgen against the snapped netlist.
6. `extract`: Magic extraction to a spice netlist with parasitic resistance and capacitance; settings fixed once (coupling capacitance on, resistance on, thresholds zero) and recorded. [verify: extracted netlists preserve device instance names so per-instance mismatch draws correspond between M and PM.]
7. `sim`: run a cell on a netlist. Corners selected by library section, supply and temperature; Monte Carlo by the mismatch switch and a logged seed. Emit the property vector per corner per chip.
8. `verdict`: apply the specification; emit pass flags, margins, limiting property, worst corner, pass pattern, Monte Carlo pass fraction with interval, and the near-threshold flag.
9. `features`: compute the pre-layout feature vector (§6).

**Characterisation runner.** CACE already does most of stage 7 on sky130: a YAML datasheet lists properties with minimum, typical and maximum limits, enumerates process corners, supply and temperature, runs ngspice from a template testbench, selects the netlist source (schematic, layout-extracted), and runs Monte Carlo as an iteration sweep with a seed. Its output is a summary table with a pass or fail per property. Month 1 decides between driving CACE and writing a thin runner. The default is a thin runner that reads CACE-format datasheets, so that every family's specification is a CACE datasheet reusable by anyone, because the pipeline needs one job per simulation on a queue with per-design seeds, which is not what CACE's whole-datasheet invocation is built for [verify against the current CACE version; the slides are from June 2024 and show format 5.0].

**Results database.** One table per stage keyed by design id and policy, in a columnar file format, with raw simulator outputs kept as files addressed by content hash. Nothing is overwritten; reruns append with a new run id.

**Testbench discipline.** Each benchmark's testbench is used as shipped, wrapped so the netlist under test, the corner section, supply, temperature, the mismatch switch and the seed can be set from outside. Where a shipped testbench cannot be wrapped that way the modification is minimal and diffed against the original in the repository.

**Scheduler.** A job queue over the 32-core workstation, one worker per core, one simulation per job, retries on simulator crash with the crash recorded. Layout jobs run on a separate queue because ALIGN and OSIRIS are single-threaded and take about a minute each.

## 4. Build order and milestones

One rule: get one family from generator to PCM verdict under both policies before widening. That is the scoop defence (v11 §7) and the fastest way to find the bugs that matter.

**Month 1.**
- Container with the toolchain. AutoSizer's full-flow mode reproduced on its telescopic OTA end to end. The paper never describes this mode; the only trace is an ALIGN PDK path, a Magic extraction script path and per-metric degradation keys in its configuration file, so the reproduction is against the repository, and the first job is to read that code and record what it does. This is the toolchain's acceptance test.
- The two sensitivity checks from v11 §9 on that netlist (whether ngspice `.SENS` reaches width, length and mismatch parameters inside the sky130 subcircuits; whether the mismatch terms can be set as explicit per-device parameters). They serve claim 2 but cost a day here and settle the fallback early.
- Property table and specification table for the first family, frozen.
- ALIGN run on all twenty-four AMS-SizingBench circuits; the supported subset recorded with the failure stage for each unsupported one.
- CACE evaluated as the runner (§3).

**Month 2.**
- Stages 2 to 9 implemented and run on the first family for one generator, ten seeds, both policies, all cells. This is the pipeline's integration test. The first family is the OSIRIS Miller amplifier: it has a reference sizing and a matched-pairs file, both policies have been run on it by the OSIRIS authors, and it is small.
- OSIRIS baseline placer running on new sizings of that family. If it does not run by the end of month 2, the preprint ships with ALIGN alone (v11 §7) and OSIRIS moves to month 5.
- Layout, extraction and simulation time per design measured under each policy; the population size and the cell budget (§5) confirmed or scaled.
- Pre-registration document frozen and committed (§9).

**Month 3.**
- All eight generators on the first family, ten seeds each, all cells. First survival curves, decomposition and policy gap.
- Predictor fitted within-family as a smoke test only.
- Remaining families' testbenches wrapped, constraint files written, property tables frozen.

**Month 4.**
- Preprint: one family, all generators, both policies, curves, decomposition, policy gap, the best-of-N OSIRIS condition. Stated as a preview of the population study.
- Harvest launched on all families.

**Month 5.**
- All families through PCM; two-hundred-chip reruns; the PCM-full subsample.
- Predictor with leave-one-family-out and leave-one-generator-out evaluation.

**Month 6.**
- Analysis frozen, figures, paper submitted. Database and pipeline tagged as the input to claims 2 and 3.

## 5. Compute budget

Per design that passes stage 0, in testbench runs (one run is the full testbench at one corner for one chip). Extracted cells are per policy; schematic cells are once per design.

| Cell | Runs | Netlist | Condition |
|---|---|---|---|
| P | 1 | extracted | all |
| C | 29 | schematic | all |
| M | 50 | schematic | all |
| PC | 29 | extracted | passes P |
| PM | 50 (+150 near threshold) | extracted | passes P |
| PCM | 50 (+150) | extracted | passes PC |
| CM | 50 | schematic | passes C |
| PCM-full | 1,450 | extracted | 40 designs |

If 60% of designs pass P and 40% pass PC, the extracted runs are about 80 per design per policy and the schematic runs about 110 per design. For two thousand designs and two policies that is about 320,000 extracted runs and 220,000 schematic runs before reruns, plus about 116,000 extracted runs for the PCM-full subsample. Post-layout op-amp testbenches on ngspice take tens of seconds; the AutoCkt paper reports 2.4 s schematic against 91 s with parasitics for its testbench. At 30 s per extracted run and 32 workers the main population is about four days; at 90 s it is about eleven. The v11 §11 figure of 175,000 post-layout simulations assumed one post-layout Monte Carlo cell; the factorial roughly doubles it. The figure is recomputed from measured runtimes in month 2 before the harvest is launched.

Reduction ladder if the budget binds, in this order: drop PCM-full to 20 designs; drop CM; reduce the corner set to the nine process-temperature points at nominal supply; reduce seeds from ten to six. Population size is cut last. If the near-threshold reruns dominate, the importance-sampling yield estimators in the folder (v11 §11) are tried on those designs, validated against brute-force Monte Carlo on a held-out set before use; brute force stays the reference.

## 6. Survival predictor

**Question.** From pre-layout information alone, can one predict whether a design survives PCM, on families and generators the predictor never saw?

**Features, all from the snapped schematic netlist and the stage 0 operating point.** No layout information.

- Per-property margins m_i and the limiting property.
- Device geometry: W, L, fingers, area per device; total gate area; ratio of input-pair area to total; minimum device area; count of minimum-length devices.
- Operating point: gm/ID, drain-source margin above saturation and gate overdrive per device from the DC operating point; bias currents; compensation-to-load capacitance ratio.
- Schematic sensitivity: the finite-difference change of each property for a fixed small relative change in each device's W, summarised per property as the norm and the maximum over devices. This is the fragility feature and the closest thing to a parasitic proxy without a layout. One schematic run per device per design.
- Structural: device count, net count, fanout of the highest-impedance node, topology identity as a one-hot that is dropped in the leave-one-family-out condition so the predictor cannot memorise families.

**Models.** Logistic regression on standardised features as the baseline; gradient-boosted trees as the main model, same features. A margin-only model is a third baseline, because the honest null is that survival is just margin.

**Protocol.** Leave-one-family-out and leave-one-generator-out, each fold reporting area under the ROC curve, Brier score and a calibration curve on the held-out group. The claim holds if the main model beats the margin-only baseline on held-out families and generators with intervals that do not cross. If it does not, that is reported. Fitted on primary plus trajectory designs; evaluated on primary designs only.

**Interpretation.** Permutation importance per fold, reported as a distribution, not one ranking.

**Prior art.** ParaGraph and Liu 2021 predict parasitics or use parasitic embeddings for single designs; ParasGB gives post-layout labels on closed processes. None predicts survival of a population. A ParaGraph-style parasitic estimate is not a feature here because training it would need layouts.

## 7. Analysis and figures

Fixed before the harvest; anything else is exploratory and labelled so.

1. Survival curves F_S(τ) for S in {P, C, M, PM, PCM}, per generator, faceted by family, one panel per policy, with Wilson intervals.
2. Failure decomposition as stacked bars per generator and family, one panel per policy.
3. Policy gap: F_PCM under ALIGN against F_PCM under OSIRIS per family, with the best-of-N OSIRIS condition on the month 4 family as a third point.
4. Predictor: ROC and calibration per held-out family and generator; permutation importance.
5. Stage ledger: counts of geometric rejection, bin snap, topology outside layout library, place-and-route, LVS, extraction and specification failures per family, generator and policy.
6. Runtime table: layout, extraction and simulation time per design per policy.
7. PCM against PCM-full agreement on the subsample, as the check on the worst-corner shortcut.
8. Supplement: survival against a tightened specification; Y* = 0.99 curves; trajectory-population curves; stage 0 agreement between generator-reported and re-simulated values; bin snap distances; AnalogSAGE designs against same-specification designs from the other generators.

Differences between generators, families and policies at fixed τ are tested by two-proportion tests with Holm correction and reported beside the intervals. No test is the headline; the curves are.

## 8. Repository layout

```
claim1/
  env/            container definition, tool versions, PDK commit
  datasheets/     one CACE-format YAML per family: properties, limits, conditions
  circuits/       canonical netlist template, testbench wrapper, ALIGN constraint
                  file and OSIRIS matched-pairs file per topology
  harvest/        generator wrappers (AutoSizer harness, AnalogSAGE)
  stages/         canonicalise, sim0, layout, lvs, extract, sim, verdict, features
  queue/          job scheduler and worker
  db/             schema and loaders for the result tables
  analysis/       curves, decomposition, predictor, figures
  prereg/         claim1-preregistration.md, frozen month 2
```

## 9. Pre-registration

`prereg/claim1-preregistration.md`, committed at the end of month 2, containing: the property and specification tables per family; the units mapping for margins; the corner set; Y*; Monte Carlo sample sizes and the near-threshold rule; the worst-corner rule; the finger rule; the extraction settings; the population definition including the AnalogSAGE topology rule; the predictor features, models and protocol; and the figure list in §7. Its commit hash is cited in the paper. Deviations are listed in a section of the paper.

## 10. Verify in month 1

Each can invalidate a definition above; each is a half-day check on a running toolchain.

- ngspice `.SENS` reach into sky130 subcircuit parameters (v11 §9).
- Explicit per-device mismatch parameters (v11 §9).
- Which sky130 library section or switch gives mismatch-only Monte Carlo, and what CACE's `mc` corner enables.
- Magic extracted netlists preserve device instance names, so per-instance draws correspond between M and PM.
- The corner library sections resolve for every device type in the families, including capacitors and resistors; the mismatch switch applies to every device type and to nothing else when process variation is off.
- ALIGN's output can be read by Magic for extraction and passes netgen LVS against the snapped netlist without manual editing; any manual step is scripted and counted as part of the policy.
- OSIRIS: licence; whether its baseline placer runs standalone on a new sizing rather than only on its released dataset; whether its matched-pairs file format is what ALIGN's constraint file needs, so that one file per topology serves both policies.
- AutoSizer harness: Gemini 2.5 Flash still served or what replaces it; token cost of ten seeds per circuit for four language-model generators; repository licence, which the paper does not state; whether the harness accepts a new circuit (an OSIRIS template) from a configuration file alone; what the full-flow mode actually does.
- AnalogSAGE: what its released code contains (topology database, testbenches, supply and load conditions), its licence, and how often each topology is selected across its runs, which decides which constraint files to write.
- AMS-SizingBench width list against sky130 bins.
- Every benchmark's stage 0 verdict is on ngspice with sky130A; any benchmark on another simulator or PDK variant is re-simulated on ours and the discrepancy reported.
- Current CACE datasheet format and batch interface.

## 11. Risks specific to the build

- **OSIRIS placer does not run on new sizings.** Month 2 fallback: ALIGN alone in the preprint; OSIRIS in the paper if it runs by month 5; otherwise the policy gap is ALIGN against ALIGN with a perturbed constraint file, labelled as a weaker comparison.
- **ALIGN supports few of the thirteen amplifiers.** Families come mostly from OSIRIS and the written AnalogSAGE constraint files; seeds per circuit go up; the supported subset is reported as a finding about the tools.
- **AnalogSAGE's topologies rarely match the layout library.** Then AnalogSAGE contributes few designs and the paper says so; the same-specification comparison under the other generators still runs. Writing constraint files for its most frequent topologies is bounded at three topologies.
- **Extracted-run time at the high end.** The reduction ladder in §5, in its stated order.
- **Generator-reported and re-simulated stage 0 values disagree.** Stop and find the cause before harvesting; likely causes are simulator version, testbench edits and bin snap. The population is defined on our re-simulation and the disagreement rate is reported.
- **Language-model generators drift.** Model identifiers and dates recorded; a generator whose model is no longer served runs on the nearest available and is labelled.
- **Scoop.** Month 4 preprint regardless of completeness, as in v11 §7. If a population survival number appears first, the contribution narrows to the decomposition, policy gap and predictor, which a flag flip does not produce.

## 12. Two corrections to carry into v12

- **AnalogSAGE's ten problems are not fixed-topology families.** v11 §4 lists "AnalogSAGE's ten op-amp problems" under circuit families with "fixed topologies; AI chooses sizings". The paper's ten tasks are specification sets; the agent picks a topology from a fifty-entry database and then sizes it. In this plan AnalogSAGE is a generator whose designs enter the population only when their topology has a constraint file, and its ten specifications are additionally applied to fixed AMS-SizingBench OTAs under the other generators. v11 §4 should say so.
- **OSIRIS's circuits have no specification.** OSIRIS measures only an RMSE between pre- and post-layout AC traces and area. Specifications for its five circuits are written here, anchored on its reference sizings. v11 §4 should record that these five specifications are ours.

Two smaller points: the v11 §11 simulation budget was for one post-layout Monte Carlo cell and roughly doubles under the factorial design here; and the finger rule in v11 §4 is confirmed as a layout-time rule because no generator in the population searches finger count.

## 13. Hand-off to claims 2 and 3

The database leaves claim 1 with, per design: the snapped netlist, both layouts, both extracted netlists, property vectors at every corner and chip, per-chip mismatch seeds, the pass pattern and worst corner, and the feature vector. Claim 2's propagation test needs the per-chip draws, so the mismatch parameter values per device per chip must be recoverable from the seed; that is checked in month 1. Claim 3's repair loop needs the failure diagnosis per design, which the verdict stage already emits as the limiting property and the cell at which it failed.
