# Claim 1 implementation plan, v2

**Claim being implemented (v11 §3).** Of AI-sized designs that meet specification pre-layout, the fraction that still meets it after extracted parasitics, across corners, and under Monte Carlo mismatch, reported as curves against specification margin, differs by generator, circuit family and layout policy. Failures are decomposed into parasitic, corner and mismatch causes. Which designs survive is predictable from pre-layout features, with the predictor holding on families and generators it was not fitted on.

**Deliverables.** A preprint at month 4 with one family under both layout policies; a submitted paper at month 6; and the pipeline, populations and result database that claims 2 and 3 run on. Dates assume the half-time effort of v11 §6 and a start in month 1.

Dated 8 September 2026, revising v1 of 7 September. Companion to `phd-plan-v12.md` and `thesis-implementation-plan-v2.md`. Facts about the benchmarks below were read from the primary PDFs in `papers/` on 7 September 2026. Items marked "[verify]" have not been checked on a running tool and are on the month 1 list in §10. Things this plan found that v11 states differently are in §12.

**v2 revises v1 in response to the external audit of 8 September 2026 (`phd-plan-audit-2026-09-08.md`) and its evaluation (`audit-evaluation-2026-09-08.md`).** The substantive changes are: a dimensionless margin (§1), an explicit signoff conjunction with a measured inheritance escape rate replacing a false implication (§1), three-valued yield labels and a corrected near-threshold rule (§1), model bins separated from the layout grid (§1), a predeclared corner-shortcut tolerance and escalation rule (§1), an eight-class failure decomposition with its mapping to claim 3's strata (§1), a finger-variation campaign (§1, §5), an honest topology count with the replication rebalanced onto contrasts the data can carry (§2), an independent DRC stage (§3), a hierarchical model with paired policy tests replacing independent two-proportion tests (§7), and a prospective power simulation at month 3 that sets the seed count (§2, §4). Every change is listed in §14.

---

## 1. Fixed definitions

These are frozen before any population is generated (§9, pre-registration). Changing one after the runs start is reported as a change.

**Property.** A scalar the testbench measures. The property list per circuit is the benchmark's list, so that the verdict matches what the generator optimised. AMS-SizingBench OTAs report DC gain, unity-gain bandwidth and DC power; its switched-capacitor and filter circuits add settling, distortion and passband figures; AnalogSAGE's problems report power, gain, common-mode rejection, power-supply rejection, gain-bandwidth, phase margin and supply-noise rejection through a testbench adapted from AnalogGym. Phase margin is added to every amplifier's list where the benchmark omits it, because a design whose phase margin falls to zero after layout is not a survivor whatever its gain does; it is added as a reported property, not as a specification constraint, unless the benchmark constrains it.

**Specification.** The benchmark's own inequality constraints on those properties.

- AMS-SizingBench states each circuit's specification as a boolean expression of thresholds (for the telescopic OTA: figure of merit above 0.1, gain above 55 dB, unity-gain bandwidth above 10 MHz, power below 50 µW) and declares a design feasible when every threshold holds. Used verbatim.
- AnalogSAGE states ten specification sets (Table 2 of its paper), for example task 3: power at most 100 µW, gain at least 80 dB, CMRR and PSRR at least 50 dB, gain-bandwidth at least 1 MHz, phase margin at least 60°, PSRN at least 50 dB. Used verbatim. Supply and load are not stated in the paper and are taken from its released testbench [verify].
- OSIRIS's five circuits carry no specification. The paper measures only the root-mean-square difference between pre- and post-layout AC traces and the area. For those five a specification is written once per circuit, anchored on the OSIRIS reference sizing: each property's threshold is the reference design's simulated value relaxed by a fixed amount (10% in linear units, 1 dB on gains, 5° on phase margin), so the reference passes with a known margin. This is the only place a specification is written rather than taken, and it is labelled as ours.

**Pass at a stage.** All constraints met at that stage. No partial credit.

**Margin.** A margin must be dimensionless, so that the limiting property does not change when bandwidth is written in Hz rather than MHz. For each constrained property i:

- **Ratio-scale properties** — positive quantities with positive thresholds: gain, unity-gain bandwidth, power, CMRR, PSRR, PSRN, slew rate, settling time. `m_i = s_i · log10(x_i / t_i)`, with `s_i = +1` for lower bounds and `-1` for upper bounds. Invariant to the unit in which x_i and t_i are expressed, because the unit cancels inside the ratio.
- **Interval-scale and zero-crossing properties** — signed quantities, or quantities whose threshold is zero: phase margin in degrees, input-referred offset in volts. `m_i = s_i · (x_i - t_i) / Δ_i`, with `Δ_i` a fixed tolerance scale in the property's own units, pre-registered per property and never derived from the data. Initial values: 10° for phase margin, 1 mV for input-referred offset.

The scale class, and `Δ_i` where it applies, are fixed per property in the property table and frozen in the pre-registration. The design's margin is the minimum m_i over its constrained properties, and the property attaining it is the limiting property. Both are recorded. Gains are still *reported* in dB; a dB value never enters a margin.

**Why this changed.** v1 defined `m_i = s_i (x_i - t_i) / |t_i|` with gain-like and bandwidth-like properties "converted to logarithmic units before normalising". That composition is not scale-invariant. For a 10 MHz bandwidth against an 8 MHz threshold it gives `(7 - 6.903)/6.903 = 0.014` in log10(Hz) and `(1 - 0.903)/0.903 = 0.107` in log10(MHz) — a factor of 7.6 between two equally defensible unit choices. Since the limiting property is the argmin of m_i across properties, its identity could flip on a unit change, and the limiting property drives this plan's survival-curve τ axis, claim 3's episode stratification, claim 3's ranking objective and claim 3's primary regressor. The log-ratio above is what the v1 definition was reaching for.

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

**Signoff is a conjunction, not an implication.** v1 skipped PM and PCM for designs failing P, on the ground that "a nominal failure cannot reach a 90% pass fraction". That is false in general. For a property whose nominal value sits at an extremum, mismatch moves chips across the threshold in the design's favour: a property distributed as z² with z standard normal, against a lower bound of 0.01, fails at nominal while `P(|z| > 0.1) = 0.920` of chips pass. Whether it is false on *these* families and properties is an empirical question, and v1 answered it by assumption. It is also false as bookkeeping: a skipped cell is unmeasured, not observed, and the failure decomposition below is a partition over measured cells.

The rule becomes an explicit conjunction with a measured escape rate.

- **Pass at a cell = nominal pass at that cell AND yield pass at that cell.** The two are recorded separately and neither is ever derived from the other.
- **Inheritance is measured, not assumed.** A stratified subsample of 200 P-failing designs — spread over families, generators and both policies, drawn by a seeded rule and pre-registered — is run at PM and PCM anyway. The fraction reaching a 0.90 pass fraction is the **inheritance escape rate**, reported as a number whatever it is. Below 1%, inheritance is applied to the remaining P-failures and the escape rate is published as its justification. At or above 1%, inheritance is withdrawn and PM and PCM run on every design that produced a layout, with the compute taken from the reduction ladder in §5.
- A cell that is neither measured nor inherited is recorded as `not measured`, never as `inherited fail`, and is excluded from the decomposition's denominator with the count reported.

Pass in a corner cell means pass at every corner in the set. Pass in a Monte Carlo cell is the three-valued label defined under "Monte Carlo" below.

**Corner shortcut, with a predeclared tolerance and an escalation rule.** The worst corner is the corner in the PC (or C) cell at which the design's margin is smallest. It is selected with *nominal* devices, so it need not be the corner of lowest yield: the cheap PCM cell and the exhaustive PCM-full cell are different endpoints and this plan does not use one name for both. PCM is the primary endpoint. PCM-full on the 40-design subsample validates it, against a rule fixed in advance:

- **Tolerance.** The shortcut is accepted if PCM and PCM-full agree on the pass/fail/indeterminate label for at least 38 of the 40 designs (95%), and if no disagreement is a PCM pass that PCM-full fails by more than one Monte Carlo standard error.
- **Escalation.** If the tolerance is not met, the subsample doubles to 80. If it still is not met, PCM-full becomes the primary endpoint for the headline curves, the compute is taken from the reduction ladder in §5, and the shortcut is reported as a measured negative result about corner selection under mismatch — which is itself worth publishing.

The same PCM endpoint, at the same 29-corner-shortcut definition, is what claim 3's accept criterion means (thesis plan §5.1). v1 of the thesis plan described claim 3's accept criterion as "all 29 corners, 50 chips", which is PCM-**full**; that inconsistency is resolved in favour of PCM here and there.

**Corner set.** Process tt, ss, ff at supply 1.62, 1.8, 1.98 V and temperature -40, 27, 125 °C (27 points), plus sf and fs at nominal supply and 27 °C. Twenty-nine corners. This follows the CACE default for sky130 (tt, ff, ss enumerated, sf and fs available, three supplies, three temperatures) with the two skewed corners added because they move differential pairs. Circuits with a different nominal supply (the AMS-SizingBench bandgap runs at 2.0 V and is not an amplifier) are outside the families anyway. [verify: that every library section resolves for every device type the families use, including capacitors and resistors.]

**Monte Carlo.** Mismatch only: the sky130 library's mismatch switch on, process variation off, because process variation is covered by corners and the two together double-count. Two stages, with the near-threshold rule stated in the only direction that is well defined:

1. Fifty chips per design. Form the Wilson 95% interval of the **observed pass fraction**.
2. If that interval **contains Y\***, the design is near threshold and is rerun with two hundred fresh chips; the two-hundred-chip estimate replaces the fifty-chip one.

v1 said "designs whose fifty-chip pass fraction lies within the Wilson 95% interval of Y\*". Y\* = 0.90 is a constant and has no Wilson interval. The rule above is what was meant, and since it is pre-registered the wording is not cosmetic.

**Labels are three-valued.** After the second stage a design is `pass` if the lower end of its Wilson interval is at or above Y\*, `fail` if the upper end is below Y\*, and `indeterminate` otherwise. At Y\* = 0.90 the standard error of a pass fraction is about 0.042 at fifty chips and 0.021 at two hundred, so the indeterminate band is not a rare edge case — it is exactly where this study concentrates. Indeterminate designs are retained with their counts and intervals, drawn as a separate band on every survival curve, and never silently coerced. A survival curve therefore has three stacked regions, not one line, and the paper says so.

**Numerical status.** A chip that fails to converge is recorded as `numerical`, excluded from both numerator and denominator of the pass fraction, and counted per design. A design with more than 10% `numerical` chips is escalated to inspection rather than scored, and the count of such designs is reported per family and policy.

Seeds are logged so any chip can be regenerated. [verify: the sky130 library exposes mismatch-only as a section or switch separate from its process Monte Carlo section; CACE's example uses a corner named `mc`, and which of the two that enables must be read from the library file.]

**Yield threshold.** Y\* = 0.90. Fifty chips resolve 0.90 to about ±0.08 and two hundred to about ±0.04; no benchmark states a yield target. The full pass-fraction distribution is stored, so any reader can re-threshold. The supplement reports Y\* = 0.99 with the caveat that two hundred chips cannot resolve it — at true yield 0.99 the fifty-chip estimator cannot distinguish 0.99 from 0.95, and the supplement figure carries that statement on its axis.

**What is being estimated.** The endpoint is inference about the design's underlying yield under the kit's own mismatch model, not a finite-sample operational criterion, which is why the labels are three-valued and why near-threshold designs get more chips. The distinction is stated in the paper because the two endpoints answer different questions and the literature routinely conflates them.

**Failure decomposition.** Each design gets a pass pattern over its cells. Among designs that fail PCM, the decomposition is over the **eight** classes formed by which single factors are individually sufficient — parasitic (fails P), corner (fails C), mismatch (fails M) — namely the seven non-empty subsets of {P, C, M} plus "interaction only" for designs that pass all three single-factor cells and still fail PCM. It is a partition over designs with all three single-factor cells measured, so fractions sum to one on that denominator, and the `not measured` count is reported beside it. Reported per generator, family and policy. The single-factor cells are why the design is factorial: a sequential flow of layout, then corners, then mismatch would attribute every failure to whichever stage ran first.

**Mapping to claim 3's four episode strata.** Claim 3 (thesis plan §5.1) stratifies episodes over four classes, and the map from eight to four must be stated here rather than improvised there. A design is assigned to exactly one stratum by this rule, applied in order:

1. `interaction-only` — passes P, C and M individually and fails PCM.
2. `mismatch-sufficient` — fails M (whatever else it fails).
3. `parasitic-sufficient` — fails P and not M.
4. `corner-sufficient` — fails C and neither P nor M.

The ordering is a choice, made so that the rarest and most interesting mechanisms are not absorbed by the commonest, and it is pre-registered. The multi-factor classes are still reported in full in the eight-class decomposition; the four-class map exists only to draw claim 3's episode set.

**Stratum supply is not guaranteed.** The `interaction-only` stratum requires designs that pass P, C and M individually and still fail PCM. There is no reason to expect fifteen of them, and if parasitic failures dominate — which PANDA's single reported amplifier suggests they may — the stratum could be near-empty. The count in each of the four strata is therefore a **month 6 reported number**, and claim 3's episode allocation is set from the observed counts rather than assumed to be fifteen apiece. If a stratum yields fewer than eight episodes, claim 3 runs with an unbalanced allocation, records it, and drops that stratum from the failure-class fixed effect rather than pretending to a balance it does not have.

**Layout policy.** A named, single-pass, deterministic procedure from sized netlist to GDS with fixed settings. Two policies:

- ALIGN, default flow, one constraint file per topology written once and applied to every sizing of that topology.
- OSIRIS baseline: sequence-pair placement solved as an integer program, simulated annealing on half-perimeter wire length, Dijkstra global routing, A* detailed routing, design rules respected by construction. OSIRIS reports about 39 s per layout on its circuits against 48 to 80 s for ALIGN's single pass, and its pipeline already runs netgen LVS, Magic extraction and ngspice. Code and dataset are on Hugging Face under `hardware-fab/osiris`; the paper states no licence [verify].

One layout per design per policy, no retries, no best-of-N. Best-of-N over OSIRIS's finger and halo perturbations is a separate condition on the month 4 family only, labelled as such. MAGICAL is not a policy: OSIRIS reports it produced no valid layout for the low-pass filter.

**Finger rule.** None of the generators searches finger count: AMS-SizingBench sizes with a discrete width times an integer multiplier at fixed length, and AnalogSAGE searches per-device length, width and multiplier. Finger count is therefore a layout-time rule for the primary population: the minimum valid finger assignment satisfying the topology's matched-pair constraints, applied identically under both policies and recorded per device.

**Consequence, and the campaign that answers it.** Because the rule is a deterministic function of topology and sizing, finger count is perfectly collinear with sizing across the whole primary population. A model trained on this population has never observed a finger response and cannot rank finger moves — which is half of claim 3's action space. A dedicated **finger-variation set** is therefore harvested alongside the population: 300 designs spread over the families, each simulated at its rule assignment and at two to four alternative valid assignments, at stage 0 and at cell P under both policies. It is the only source of finger-response supervision anywhere in the thesis. It is budgeted in §5, and if it is cut then claim 3's discrete action set is cut with it and the utility paper says so. The finger override of the thesis plan §3.2 A10 is the mechanism; in v2 it is used, not merely available.

**Geometry, model bins and the layout grid.** v1 said "each device's W and L are snapped to the nearest sky130 model bin". That conflates two different things and, taken literally, destroys every derivative claim 2 depends on.

Model binning is **model selection**, not geometry quantisation. A sky130 device subcircuit selects a `.model` card by which W/L *interval* the instance falls in; any geometry inside that interval is legal and simulable, and there is no universal list of permitted point geometries. The real quantisation is the layout manufacturing grid, which is a separate and much finer constraint.

Three operations, applied in this order and logged separately:

1. **Range check.** W and L must lie inside the benchmark's own ranges and inside the union of the device's model bins. A design outside either is a `geometric rejection`, counted.
2. **Grid quantisation.** W and L are quantised to the sky130 manufacturing grid [verify the grid value against the installed technology file; the expectation is 0.005 µm]. This is the only quantisation applied, it is what the layout tools impose anyway, and the quantisation distance is recorded per device.
3. **Bin identification.** The model bin each device lands in is recorded, together with the **clearance to the nearest bin boundary** in W and in L. Nothing is moved. A design that lands in no bin after quantisation is a `no valid bin` failure, counted separately.

**Consequences carried into claims 2 and 3.**

- Derivatives — finite differences and the model's Jacobian alike — are taken with respect to W and L, which are the independent continuous parameters. Multiplicity and finger count are integers and are handled as discrete actions, never as continuous coordinates. The thesis plan v1 design vector took `log10` of multiplicity and stepped 2% in it; multiplicity goes 1, 2, 3 and a 2% step in its logarithm is meaningless.
- A perturbation must exceed the grid or it is a no-op. Steps that quantise to the same geometry are recorded as `no-op perturbation`, excluded from any derivative, and counted.
- A perturbation should stay inside the device's bin, because the mismatch slope coefficients change discontinuously at bin boundaries (thesis plan §2.2). Step sizes are chosen relative to the recorded bin clearance, and any bin crossing is logged and excluded from derivative headlines.

v1's single "bin snap" failure class is replaced by `geometric rejection`, `no valid bin`, and a recorded grid-quantisation distance. AMS-SizingBench's discrete width list is checked against both the grid and the bins [verify]; AnalogSAGE's continuous ranges need only grid quantisation.

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

**Target size, counted honestly.** v1's "roughly twenty to twenty-eight families" overstates the diversity. AnalogSAGE's ten problems are specification sets, not topologies (§12); applying them to two fixed AMS-SizingBench OTAs creates specification variety, not topology variety. The OSIRIS five-transistor OTA and Miller amplifier are counted separately from their AMS-SizingBench counterparts even though they are the same circuits under different testbenches. The number of **genuinely distinct topologies** is about thirteen to eighteen, and the number of structurally distinct families is smaller still, since five-transistor, current-mirror, telescopic and folded-cascode OTAs are close relatives. Every count in the paper distinguishes topologies from specification sets from testbench variants, and the distinct-topology number is the one used wherever generalisation is claimed.

Eight generators at ten seeds is about 2,000 runs; after the generators' own success rates about 1,500 to 2,000 designs pass stage 0.

**Where the replication is spent.** Two thousand designs over roughly twenty families, eight generators and two policies is about **ten designs per (generator, family, policy) cell** — before the survival curve conditions on m_0 ≥ τ and shrinks n further at every point along the axis. A Wilson interval on ten designs spans roughly ±30 percentage points. v1's headline figure, survival per generator faceted by family with one panel per policy, therefore could not have supported the claim that survival differs by generator, family and policy. More seeds do not fix this; it is a question of which contrasts the replication is spent on.

The design is restructured around what the data can carry:

- **Headline contrasts, adequately powered.** Survival per **generator**, pooled across families with family as a random effect (n ≈ 250 per generator per policy); survival per **family**, pooled across generators (n ≈ 100 per family per policy); and the **policy gap**, which is paired within design and is therefore the best-powered contrast in the study.
- **Supplement, reported but not claimed.** The full generator × family × policy breakdown, every panel carrying its own n, with no significance test attached.
- **Inference.** A hierarchical logistic model of pass at each cell, with crossed random effects for family and generator and policy as a within-design fixed effect, replaces the independent two-proportion tests of v1 §7.
- **Prospective power simulation, month 3, before the full harvest.** Simulate the whole analysis on synthetic survival data at plausible effect sizes and the planned n, and report the minimum detectable difference for each headline contrast. The seed count and the family list are set by that simulation, not by round numbers. If it says the generator contrast needs more than ten seeds, seeds rise and the family list shrinks: breadth is cut before power is.

If the ALIGN-supported subset is small, seeds go up to hold the population near two thousand and the power simulation is rerun on the actual family list.

**Provenance.** Every design carries family, generator, seed, harness commit, language-model identifier and date, the raw sizing as proposed, the snapped sizing, the generator's own stage 0 property vector and ours. A disagreement between the two stage 0 vectors beyond simulator tolerance is a bug to be found before proceeding.

## 3. Pipeline

One Python package, one containerised toolchain, one results database. Each stage is a pure function from an input record to an output record plus a log, so any design can be rerun from any stage. Ten stages in v2; v1 had nine, before the independent DRC stage was added.

**Experiment manifest.** Alongside the pipeline, a single machine-readable manifest enumerates every experimental cell in this claim — family × generator × seed × policy × pipeline cell — with, per cell, the expected count of schematic simulations, layout and extraction calls, per-corner chip simulations and language-model calls. It is generated in month 1, is the input to every compute estimate in §5, and is diffed against measured counts at month 2 and month 6. The audit's objection to v1's budget was not that the numbers were wrong but that nothing forced them to be complete; the manifest is what forces it.

**Toolchain (pinned, one container image).** open_pdks sky130A, ngspice, Magic, netgen, ALIGN with its sky130 PDK abstraction, OSIRIS, the AutoSizer harness, AnalogSAGE, and CACE. Versions recorded in the image manifest and in every result row. [verify: one ngspice version satisfies the sky130 mismatch models, the AutoSizer harness (which cites the version 34 manual) and CACE.]

**Stages.**

1. `harvest`: run a generator on a family; emit primary and trajectory designs with provenance. Wraps the AutoSizer harness for its six generators and itself; wraps AnalogSAGE's loop.
2. `canonicalise`: map each generator's sizing representation onto one canonical netlist per topology with a device table (W, L, fingers, multiplier, model). Geometric checks, then bin snap. Emit the snapped netlist and the snap log.
3. `sim0`: our stage 0 re-simulation with the benchmark's testbench; compare with the generator's values.
4. `layout`: run a policy; emit GDS, runtime, and a stage code on failure (placement, routing).
5. `drc`: an **independent** Magic design-rule check against the sky130 rule deck, run on the produced GDS regardless of what the layout tool reported. A tool's claim to respect design rules by construction is precisely the kind of tool-reported success this study exists to check, so it is checked rather than believed. Violations are recorded by rule and by count; a design with any violation is a `drc` failure and does not proceed. Added in v2: v1 had DRC only as a failure code the layout tool could choose to emit.
6. `lvs`: netgen against the quantised netlist, emitting the explicit device map of the thesis plan §2.4.
7. `extract`: Magic extraction to a spice netlist with parasitic resistance and capacitance; flatten before resistance extraction; settings fixed once (`cthresh 0`, `rthresh 0`, `extresist on`) and recorded. Schematic-to-extracted device correspondence comes from the LVS device map, never from instance names.
8. `sim`: run a cell on a netlist. Corners selected by library section, supply and temperature; Monte Carlo by the mismatch switch with explicit per-device offsets (thesis plan §2.2) and a logged seed. Emit the property vector per corner per chip, with a numerical-status flag per run.
9. `verdict`: apply the specification; emit pass flags, margins, limiting property, worst corner, pass pattern, Monte Carlo pass fraction with its Wilson interval, the three-valued yield label, the near-threshold flag and the numerical-status counts.
10. `features`: compute the pre-layout feature vector (§6).

**Device map cardinality.** The map from schematic devices to extracted devices is **not required to be one-to-one**. A multi-finger device legitimately extracts as parallel devices and parallel devices are legitimately merged, so a rule that fails loudly on any one-to-many map would reject valid layouts. The requirement is that the map be *complete and unambiguous*: every schematic device maps to a non-empty set of extracted devices, every extracted device to exactly one schematic device, and the split/merge factor is recorded. It matters physically, because the sky130 mismatch term scales as `1/sqrt(l·w·mult)`: how fingers are represented in the extracted netlist changes the mismatch magnitude, and therefore changes the M-versus-PM comparison and claim 2's offset inputs. The aggregation rule — how the offsets of N extracted devices combine to represent one schematic device's draw — is fixed in month 1 and pre-registered.

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
- Stages 2 to 10 implemented and run on the first family for one generator, ten seeds, both policies, all cells. This is the pipeline's integration test. The first family is the OSIRIS Miller amplifier: it has a reference sizing and a matched-pairs file, both policies have been run on it by the OSIRIS authors, and it is small.
- The independent DRC stage exercised against a known-good and a known-bad layout, so that a clean DRC report is evidence rather than a default.
- Grid, bin and derivative checks (§1, "Geometry, model bins and the layout grid"): the manufacturing grid value read from the technology file; the bin clearance distribution measured over the first family; a step-size convergence check for central differences at 1%, 2% and 4% on ten designs spanning the family's operating regimes, not one design; and the no-op perturbation rate at each step size. These decide the derivative step for the whole thesis and cost a day.
- OSIRIS baseline placer running on new sizings of that family. If it does not run by the end of month 2, the preprint ships with ALIGN alone (v11 §7) and OSIRIS moves to month 5.
- Layout, extraction and simulation time per design measured under each policy; the population size and the cell budget (§5) confirmed or scaled.
- Pre-registration document frozen and committed (§9).

**Month 3.**
- All eight generators on the first family, ten seeds each, all cells. First survival curves, decomposition and policy gap.
- **Prospective power simulation (§2), before the full harvest is launched.** The whole analysis is simulated on synthetic survival data at plausible effect sizes and the planned n, and the minimum detectable difference is reported for each headline contrast: generator, family and the paired policy gap. The seed count and the family list for the harvest are set by its output. This is the decision that v1 made implicitly by choosing round numbers, and it is cheap to make explicitly now rather than to discover at month 6.
- Predictor fitted within-family as a smoke test only.
- Remaining families' testbenches wrapped, constraint files written, property tables frozen.

**Month 4.**
- Preprint: one family, all generators, both policies, curves, decomposition, policy gap, the best-of-N OSIRIS condition. Stated as a preview of the population study.
- **The preprint is conditional, which v1's decision D3 was not.** v1 committed to a month 4 preprint "regardless of completeness". That is the right instinct against the scoop risk and the wrong rule when the incomplete part is the endpoint's validity. The preprint goes out at month 4 **provided** the margin definition is settled, the corner shortcut has been checked against its predeclared tolerance on the first family, and the yield labelling rule is the three-valued one of §1. Those are months 1 to 3 work and are expected to hold. If any of them is unresolved, the preprint slips to the first month in which they are, and the reason is recorded. A preprint reporting an endpoint the authors cannot yet defend is a worse scoop defence than a preprint one month later.
- Harvest launched on all families.

**Month 5.**
- All families through PCM; two-hundred-chip reruns; the PCM-full subsample against its tolerance; the 200-design inheritance subsample; the finger-variation set.
- Predictor with leave-one-family-out and leave-one-generator-out evaluation.

**Month 6.**
- Analysis frozen, figures, paper submitted. Database and pipeline tagged as the input to claims 2 and 3.
- **The `episodes_v1` table emitted and frozen** (§13): the four-stratum assignment of every PCM-failing design, the stratum counts, the seeded draw of claim 3's episode set, and the hold-out flag that claim 2 honours from month 6 onward. This is the fix for the scheduling contradiction in the thesis plan's dependency rule 3.

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

v2 adds three lines to the table above:

| Item | Runs | Netlist | Condition |
|---|---|---|---|
| Inheritance subsample (§1) | 100 (PM) + 100 (PCM) | extracted | 200 P-failing designs, per policy |
| Finger-variation set (§1) | 1 (sim0) + 1 (P) per variant | both | 300 designs × 2 to 4 variants, per policy |
| PCM-full escalation reserve | 1,450 | extracted | 40 further designs if the §1 tolerance fails |

If 60% of designs pass P and 40% pass PC, the extracted runs are about 80 per design per policy and the schematic runs about 110 per design. For two thousand designs and two policies that is about 320,000 extracted runs and 220,000 schematic runs before reruns, plus about 116,000 extracted runs for the PCM-full subsample, about 40,000 for the inheritance subsample and about 3,000 for the finger set. Post-layout op-amp testbenches on ngspice take tens of seconds; the AutoCkt paper reports 2.4 s schematic against 91 s with parasitics for its testbench. At 30 s per extracted run and 32 workers the main population is about four days; at 90 s it is about eleven. The v11 §11 figure of 175,000 post-layout simulations assumed one post-layout Monte Carlo cell; the factorial roughly doubles it.

**These are scenario figures, not an upper bound, and they are not treated as one.** They assume the pass rates above, no reruns beyond the near-threshold rule, and no failed jobs. The manifest of §3 enumerates the cells; measured median *and tail* runtimes from month 2, including failed and retried jobs, replace every number here before the harvest is launched, and a contingency supported by those measurements is added on top. Dividing core-hours by 32 assumes 32 independent workers with adequate memory and no serial bottleneck; the layout and DRC queues are single-threaded and are measured separately.

Reduction ladder if the budget binds, in this order: drop CM; reduce the corner set to the nine process-temperature points at nominal supply; reduce seeds from ten to six but only if the month 3 power simulation says the headline contrasts survive it. **PCM-full, the inheritance subsample and the finger-variation set are not on the ladder above population size**, because each of them is what licenses an inference the rest of the study depends on: the corner shortcut, the signoff conjunction, and claim 3's discrete action set respectively. Population size is cut before any of them, and breadth is cut before power. If the near-threshold reruns dominate, the importance-sampling yield estimators in the folder (v11 §11) are tried on those designs, validated against brute-force Monte Carlo on a held-out set before use; brute force stays the reference.

## 6. Survival predictor

**Question.** From pre-layout information alone, can one predict whether a design survives PCM, on families and generators the predictor never saw?

**Features, all from the snapped schematic netlist and the stage 0 operating point.** No layout information.

- Per-property margins m_i and the limiting property.
- Device geometry: W, L, fingers, area per device; total gate area; ratio of input-pair area to total; minimum device area; count of minimum-length devices.
- Operating point: gm/ID, drain-source margin above saturation and gate overdrive per device from the DC operating point; bias currents; compensation-to-load capacitance ratio.
- Schematic sensitivity: the finite-difference change of each property for a fixed small relative change in each device's W, summarised per property as the norm and the maximum over devices. This is the fragility feature and the closest thing to a parasitic proxy without a layout. One schematic run per device per design.
- Structural: device count, net count, fanout of the highest-impedance node, topology identity as a one-hot that is dropped in the leave-one-family-out condition so the predictor cannot memorise families.

**Models.** Logistic regression on standardised features as the baseline; gradient-boosted trees as the main model, same features. A margin-only model is a third baseline, because the honest null is that survival is just margin.

**Protocol.** Leave-one-**topology**-out and leave-one-generator-out, each fold reporting area under the ROC curve, Brier score and a calibration curve on the held-out group. Folds are grouped by topology rather than by "family", because families as v1 counted them include the same topology under different testbenches and specification sets (§2), and a fold that puts the OSIRIS Miller amplifier in training and the AMS-SizingBench Miller amplifier in test is not a held-out topology. Trajectory designs are grouped with the run and topology they came from, never split across a fold: designs from one optimiser run are near-duplicates of each other and of that run's final design, so exclusion by exact design id is not enough. The claim holds if the main model beats the margin-only baseline on held-out topologies and generators with intervals that do not cross. If it does not, that is reported. Fitted on primary plus trajectory designs; evaluated on primary designs only.

**Interpretation.** Permutation importance per fold, reported as a distribution, not one ranking.

**Prior art.** ParaGraph and Liu 2021 predict parasitics or use parasitic embeddings for single designs; ParasGB gives post-layout labels on closed processes. None predicts survival of a population. A ParaGraph-style parasitic estimate is not a feature here because training it would need layouts.

## 7. Analysis and figures

Fixed before the harvest; anything else is exploratory and labelled so.

1. Survival curves F_S(τ) for S in {P, C, M, PM, PCM}: per generator pooled across families, and per family pooled across generators, one panel per policy, with Wilson intervals and the indeterminate band drawn separately. The full generator × family × policy facet grid moves to the supplement with per-panel n printed on it (§2).
2. Failure decomposition as stacked bars per generator and family, one panel per policy.
3. Policy gap: F_PCM under ALIGN against F_PCM under OSIRIS per family, with the best-of-N OSIRIS condition on the month 4 family as a third point.
4. Predictor: ROC and calibration per held-out family and generator; permutation importance.
5. Stage ledger: counts of geometric rejection, bin snap, topology outside layout library, place-and-route, LVS, extraction and specification failures per family, generator and policy.
6. Runtime table: layout, extraction and simulation time per design per policy.
7. PCM against PCM-full agreement on the subsample, against the predeclared 38-of-40 tolerance of §1, with the escalation outcome stated.
7a. Inheritance escape rate: the fraction of the 200-design P-failing subsample that reaches a 0.90 pass fraction at PM or PCM (§1).
7b. Stage ledger for the new `drc` stage: violations by rule and by policy, which is a result about the layout tools in its own right.
8. Supplement: survival against a tightened specification; Y* = 0.99 curves; trajectory-population curves; stage 0 agreement between generator-reported and re-simulated values; bin snap distances; AnalogSAGE designs against same-specification designs from the other generators.

**Inference.** A hierarchical logistic model of pass at each cell, with crossed random effects for family and generator, replaces v1's independent two-proportion tests. The **policy comparison is paired**: both policies are applied to the same designs (one layout per design per policy), so a two-proportion test is the wrong instrument and McNemar's test, or the within-design fixed effect in the hierarchical model, is the right one. Generator and family contrasts are reported as model estimates with intervals, Holm-corrected across the pre-registered contrast list. No test is the headline; the curves are, and every curve carries its n.

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

`prereg/claim1-preregistration.md`, committed at the end of month 2, containing: the property and specification tables per family; the **margin scale class and Δ_i per property** (§1); the corner set; Y\* and the **three-valued labelling rule** (§1); Monte Carlo sample sizes and the near-threshold rule stated in the correct direction; the **corner-shortcut tolerance and escalation rule** (§1); the **inheritance subsample draw** (§1); the **eight-class decomposition and its map to claim 3's four strata** (§1); the finger rule and the **finger-variation set** (§1); the **grid, range and bin operations and the derivative step rule** (§1); the extraction and DRC settings; the **device-map cardinality and offset-aggregation rule** (§3); the population definition including the AnalogSAGE topology rule; the **headline contrast list and the hierarchical model specification** (§7); the predictor features, models and topology-grouped protocol (§6); and the figure list in §7. The month 3 power simulation's output — the seed count and family list it implies — is committed as an addendum before the harvest launches. Its commit hash is cited in the paper. Deviations are listed in a section of the paper.

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
- The sky130 manufacturing grid value in the installed technology file, and the bin-clearance distribution over the first family's devices (§1).
- Central-difference convergence at 1%, 2% and 4% on ten designs spanning the first family's operating regimes, and the no-op perturbation rate at each (§1, §4 month 2).
- That Magic DRC runs on ALIGN and OSIRIS output against the sky130 rule deck without manual intervention, and that it flags a deliberately broken layout (§3).
- That netgen's device map is complete and unambiguous under multi-finger and parallel-device splitting and merging, and what the split/merge factor is for a representative multi-finger device (§3).

## 11. Risks specific to the build

- **OSIRIS placer does not run on new sizings.** Month 2 fallback: ALIGN alone in the preprint; OSIRIS in the paper if it runs by month 5; otherwise the policy gap is ALIGN against ALIGN with a perturbed constraint file, labelled as a weaker comparison.
- **ALIGN supports few of the thirteen amplifiers.** Families come mostly from OSIRIS and the written AnalogSAGE constraint files; seeds per circuit go up; the supported subset is reported as a finding about the tools.
- **AnalogSAGE's topologies rarely match the layout library.** Then AnalogSAGE contributes few designs and the paper says so; the same-specification comparison under the other generators still runs. Writing constraint files for its most frequent topologies is bounded at three topologies.
- **Extracted-run time at the high end.** The reduction ladder in §5, in its stated order.
- **Generator-reported and re-simulated stage 0 values disagree.** Stop and find the cause before harvesting; likely causes are simulator version, testbench edits and bin snap. The population is defined on our re-simulation and the disagreement rate is reported.
- **Language-model generators drift.** Model identifiers and dates recorded; a generator whose model is no longer served runs on the nearest available and is labelled.
- **Scoop.** Month 4 preprint under the conditions in §4: the margin definition settled, the corner shortcut checked against its tolerance, the yield labelling three-valued. If a population survival number appears first, the contribution narrows to the decomposition, policy gap and predictor, which a flag flip does not produce.
- **A stratum comes up empty.** The `interaction-only` class may be rare (§1). It is a month 6 reported number and claim 3's allocation follows it; a stratum below eight episodes is dropped from claim 3's failure-class effect rather than padded.
- **The power simulation says ten seeds is not enough.** Then the family list shrinks and the seed count rises, at month 3, before the harvest. This is the intended outcome of running the simulation, not a failure of it.
- **DRC failures are common under one or both policies.** That is a result about the layout tools and belongs in the stage ledger and the paper's headline, not a bug. It does, however, cut the population, so the month 2 integration test measures the DRC pass rate on the first family before the harvest is sized.

## 12. Corrections to carry into v12

- **AnalogSAGE's ten problems are not fixed-topology families.** v11 §4 lists "AnalogSAGE's ten op-amp problems" under circuit families with "fixed topologies; AI chooses sizings". The paper's ten tasks are specification sets; the agent picks a topology from a fifty-entry database and then sizes it. In this plan AnalogSAGE is a generator whose designs enter the population only when their topology has a constraint file, and its ten specifications are additionally applied to fixed AMS-SizingBench OTAs under the other generators. v11 §4 should say so.
- **OSIRIS's circuits have no specification.** OSIRIS measures only an RMSE between pre- and post-layout AC traces and area. Specifications for its five circuits are written here, anchored on its reference sizings. v11 §4 should record that these five specifications are ours.

- **"Sizings are snapped to model bins" is wrong as v11 §4 states it.** Model binning selects a model card by W/L interval; it does not quantise geometry. The quantisation that exists is the layout manufacturing grid. v11 §4's sentence should be replaced by the three operations in §1 ("Geometry, model bins and the layout grid"), because taken literally it makes every finite difference in claim 2 either a no-op or a jump.
- **The endpoint must be named once.** v11 speaks of "signoff" without distinguishing worst-corner Monte Carlo (PCM) from all-corner Monte Carlo (PCM-full). PCM is the primary endpoint, PCM-full validates it against a predeclared tolerance, and claim 3's accept criterion is PCM. v11 §3 and §4 should say which.
- **"Survive layout and manufacturing variation" overclaims.** The endpoint is model-based physical verification under the sky130 kit and this flow. The thesis implementation plan §2.2 already states the discipline — "this plan never claims the sky130 statistical model is silicon" — and v11's working title and §1 should adopt it.
- **The finger rule needs a companion campaign.** v11 §4's finger rule is confirmed as layout-time, because no generator searches finger count. But that makes finger count collinear with sizing across the whole population, so v11 §4 must also record the finger-variation set of §1, without which claim 3's discrete action set has no training support.

Two smaller points: the v11 §11 simulation budget was for one post-layout Monte Carlo cell and roughly doubles under the factorial design here; and the pipeline has ten stages in v2, not nine, after the independent DRC stage was added.

## 13. Hand-off to claims 2 and 3

The database leaves claim 1 with, per design: the quantised netlist, both layouts, both extracted netlists, the DRC and LVS reports with the device map, property vectors at every corner and chip, per-chip mismatch offsets, the pass pattern, worst corner and three-valued yield label, and the feature vector. Claim 2's propagation test needs the per-chip draws as *known inputs*, which the explicit per-device offsets of the thesis plan §2.2 supply; recovering them from a bare seed is the fallback, and both are checked in month 1.

**Claim 3's episode set is drawn and frozen at month 6, not at month 30.** The thesis plan's dependency rule 3 requires that no ranker is ever trained on a design appearing in a claim 3 episode. But claim 2's rankers are trained over months 6 to 30 and both claim 2's training pools and claim 3's episodes come from this database, so an episode set drawn at month 30 makes that exclusion retroactive and unenforceable — every ranker would have to be retrained. Claim 1 therefore emits, at month 6 when the database is tagged, a frozen `episodes_v1` table: the four-stratum assignment of every PCM-failing design (§1), the seeded draw of the episode set from it, and a hold-out flag that claim 2's training-set construction reads and honours from month 6 onward. If the month 6 stratum counts do not support the intended allocation, the allocation changes then, once, and is recorded.

Claim 3's repair loop needs the failure diagnosis per design, which the verdict stage emits as the limiting property, the cell at which it failed, the worst corner and the per-property pre-versus-post deltas. The **finger-variation set** of §1 is handed to claim 2 as the only training data carrying a finger response, and to claim 3 as the evidence that its discrete action set is rankable at all.

## 14. Changes from v1

Every change below responds to the audit of 8 September 2026 and its evaluation. The finding each answers is given in brackets.

1. **Margin is dimensionless** (F10). `m_i = s_i log10(x_i/t_i)` for ratio-scale properties, `s_i (x_i - t_i)/Δ_i` with a pre-registered `Δ_i` for signed and zero-threshold ones. v1's normalise-after-log composition was unit-dependent by a factor of 7.6 on a representative bandwidth, and the limiting property is its argmin. §1.
2. **Signoff is an explicit conjunction and inheritance is measured** (F8). v1's "a nominal failure cannot reach a 90% pass fraction" is false in general; a 200-design subsample now measures the escape rate rather than assuming it is zero. Unmeasured cells are labelled `not measured`. §1.
3. **The corner shortcut has a predeclared tolerance and escalation rule** (F8). PCM is the primary endpoint, PCM-full validates it at 38 of 40, and failure escalates rather than being noted. Claim 3's accept criterion is PCM, resolving the two-endpoints-one-name inconsistency with the thesis plan. §1.
4. **Yield labels are three-valued and the near-threshold rule is stated correctly** (F9). v1's "within the Wilson interval of Y\*" was undefined, since Y\* is a constant; the rule is that the sample's interval contains Y\*. Indeterminate designs are retained as a band. Numerical failures have a status policy. §1.
5. **Model bins are separated from the layout grid** (F5). Nothing is snapped to a bin. Range check, grid quantisation and bin identification are three logged operations; derivatives are with respect to W and L only; multiplicity and fingers are integers; no-op perturbations and bin crossings are counted. §1.
6. **The failure decomposition is eight classes with an explicit map to claim 3's four strata, and stratum supply is a reported number** (F8). §1.
7. **A finger-variation set is harvested** (F6). Without it the finger rule makes finger count collinear with sizing and claim 3's discrete action set has no training support. §1, §5.
8. **The topology count is stated honestly and the replication is rebalanced** (F13). About thirteen to eighteen distinct topologies, not twenty-eight families. Headline contrasts are generator-pooled, family-pooled and the paired policy gap; the three-way facet grid moves to the supplement with its n printed. §2.
9. **A prospective power simulation at month 3 sets the seed count and family list** (F13, F11). §2, §4.
10. **An independent DRC stage is added** (F13). A layout tool's claim to respect design rules by construction is exactly the kind of tool-reported success this study exists to check. §3.
11. **The device map may be one-to-many, with a recorded split/merge factor and a fixed offset-aggregation rule** (F13). v1's one-to-one requirement would have failed valid multi-finger layouts. §3.
12. **Inference is hierarchical and the policy comparison is paired** (F13). McNemar or a within-design effect replaces independent two-proportion tests on what is a paired design. §7.
13. **The predictor's folds are grouped by topology and by run** (F13). Exclusion by exact design id does not separate near-duplicate trajectory designs. §6.
14. **Claim 3's episode set is drawn and frozen at month 6** (evaluation addendum to F11). Drawing it at month 30 made the thesis plan's ranker-exclusion rule retroactive and unenforceable. §13.
15. **An experiment manifest is generated in month 1 and budgets are scenario figures with tail runtimes and contingency** (audit §3). §3, §5.
16. **The month 4 preprint is conditional on the endpoint being defensible** (audit §4). §4, §11.
