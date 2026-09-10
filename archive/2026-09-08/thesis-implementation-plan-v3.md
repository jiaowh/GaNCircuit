# Thesis implementation plan, v3

**Scope.** The build plan for the whole thesis of `phd-plan-v11.md`, claim by claim: claim 1 (measurement), claim 2 (fidelity), claim 3 (utility), and the three gated items (compact-model bridge, computing-in-memory tile, chip). It absorbs `claim1-implementation-plan.md` v1 by reference, amends it where facts checked today differ, and gives claims 2 and 3 the same level of definition. Every definition a reported result depends on is fixed here and carried into a per-claim pre-registration document.

**Deliverables.** Three papers (survival, fidelity, utility), one pipeline and result database that all three run on, one gated device-modelling paper, and a thesis. Dates assume the half-time effort of v11 §6 and a start in month 1.

Dated 8 September 2026. Companion to `phd-plan-v12.md` and `claim1-implementation-plan-v2.md`. Facts about papers were read from the primary PDFs in `papers/` on this date; facts about tools, repositories and shuttles from their public pages on this date. Sources are listed in §11. Items marked "[verify]" have not been checked on a running tool and are collected in §10. Places where this plan disagrees with v11, with the claim 1 plan, or with `papers/README.md` are collected in §9.

**v3 revises v2 in response to the recheck (`phd-plan-recheck-v12-2026-09-08.md`), whose findings were validated numerically before being applied — every figure it quotes reproduces exactly.** The changes: one canonical endpoint specification that claim 3 actually executes, replacing a reused starting-design corner (§2.7, §5.1); study 3A's "fully evaluated" made real by removing early exits (§5.4); separate analysis specifications for 3A and 3B, because 3B's six rankers cannot support fits promised on nine (§5.4); arm A restored as a scientifically relevant site of the fidelity question rather than a null the pairwise arms must beat (§4.1); one canonical parameter and device schema replacing prose that still said "snapped to model bins" in the executable rules (§2.7, §5.1); and a budget rebuilt from consistent rules, which raises the claim 3 total from about 9,800 to about 13,600 core-hours (§5.5). Listed in §13.

**v2 revised v1 the same day, in response to the external audit (`phd-plan-audit-2026-09-08.md`) and its evaluation (`audit-evaluation-2026-09-08.md`).** The audit found thirteen defects; all thirteen are accepted, and four further problems surfaced in evaluating it. The changes that alter what the thesis measures, rather than how it is described, are: a dimensionless margin (§4.1, claim 1 plan §1); derivative supervision on a genuinely rank-deficient subspace, resolving a flat contradiction in v1 §4.3 that made instrument 6 vacuous (§4.3, §4.5); passive, source and testbench-context features without which the skeleton cannot represent a compensation capacitor (§4.2); the non-separability gate demoted from pass/fail to diagnostic, with arm B's absolute prediction and Jacobian anchor defined (§4.3); offset-derivative supervision made a precondition of the propagation test rather than a bonus (§4.6); claim 3 split into a fixed-candidate ranking study and a closed-loop utility study (§5.4, §5.7); the accept criterion fixed at claim 1's PCM (§5.1), which also repairs the budget (§5.5); and a prospective power simulation before each of claims 1 and 3 (§4.11, §5.4). Everything is listed with its finding in §12.

---

## 0. How to read this document

- §1 maps claims to deliverables, dependencies and the parts of the database each produces and consumes.
- §2 fixes the infrastructure all three claims share: process, toolchain, the mismatch model as it actually reads, sensitivity labels, extraction, the database, and the compute model.
- §3, §4 and §5 are the per-claim plans. Each has the same shape: fixed definitions, data, method, instruments or baselines, analysis and figures, compute, build order, risks, and what a negative result means.
- §6 covers the three gated items with their gates and their fallbacks.
- §7 is the month-by-month schedule with decision points.
- §8 is the pre-registration and the honesty rules.
- §2.7 is the canonical schema: parameters, encodings, legal moves, device correspondence and the endpoint. Where any other section disagrees with it, it wins.
- §12 lists every change from v1, with the audit finding each answers; §13 lists every change from v2.
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
3. Claim 3 draws its repair episodes from claim 1's population and its rankers from claim 2. A ranker is never trained on any design that appears in a claim 3 episode, nor on any post-layout or Monte Carlo result of such a design, **nor on any design from the same optimiser run or the same topology-and-specification cell as such a design**. Exclusion by exact design id is not enough, because trajectory designs from one run are near-duplicates of that run's final design.
   **The episode set is therefore drawn and frozen at month 6, not at month 30.** v1 trained the rankers over months 6 to 30 and drew the episode set at months 30 to 32, from the same claim 1 database that supplies claim 2's training pools; the exclusion was retroactive and would have required retraining all twelve rankers. Claim 1 now emits a frozen `episodes_v1` table when the database is tagged at month 6 (claim 1 plan §13), and claim 2's training-set construction reads its hold-out flag from month 6 onward.
4. Claim 1's headline curves use only the primary population (the final design of each run) and only pre-registered cells. Trajectory designs train the survival predictor and seed claim 2; they never enter a survival curve.
5. Claim 2's response error for a model is computed only on designs held out from that model's training set, and, where the arm distinguishes them, on directions in the orthogonal complement of that model's trained derivative subspace (§4.3). Held-out designs and held-out directions are independent exclusions and both are recorded.
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

The default sensitivity source is therefore **central finite differences by re-simulation on the full testbench**: two runs per direction, a relative step of 2% in log-sizing space as the working default, and a step of 0.5 standard deviations for the per-device offset parameters. `.SENS` is tried in month 1 on the first working netlist; it is used only if it reaches the sizing and mismatch parameters and agrees with finite differences within 5% on a sample of ten designs. Either outcome is recorded and reported, since v11 §7 lists this as a risk and the answer is worth stating publicly.

**Which parameters are differentiated.** W and L only. These are the independent continuous parameters; multiplicity and finger count are integers and are handled as discrete actions, never as continuous coordinates. v1's design vector took `log10` of multiplicity and stepped 2% in it, which is meaningless for a quantity that goes 1, 2, 3. Tied device parameters — devices constrained equal by a matched-pair rule — are differentiated once as a single independent parameter, and the tie structure is recorded per topology.

**Step size is chosen against three constraints, not asserted.** A step must (a) exceed the layout manufacturing grid, or the perturbed netlist is identical to the unperturbed one and the difference is identically zero; (b) stay inside the device's model bin, because the mismatch slope coefficients jump at bin boundaries (§2.2); and (c) sit in the regime where the central difference has converged. Constraints (a) and (b) are checked per device from the recorded grid quantisation and bin clearance of claim 1 plan §1. Constraint (c) is measured at month 2 by a convergence check at 1%, 2% and 4% on **ten designs spanning each family's operating regimes**, not one design per family as v1 proposed — a single design cannot tell a converged step from one that happens to work at that bias point. Every derivative record carries its step, its no-op flag and its bin-crossing flag; no-op and bin-crossing derivatives are excluded from every headline and their counts are reported.

Cost: a design with 20 sizing variables costs 40 stage-0 simulations for a full sizing Jacobian, and a design with 15 devices costs 120 more for the four offset parameters per device. At the AutoCkt schematic figure of 2.4 s per simulation this is minutes per design, which is why the sensitivity budget in §4.9 is dominated by how many designs get a full Jacobian, not by how the Jacobian is computed.

### 2.4 Extraction and device correspondence

Magic's own documentation states that resistance extraction "does not work well with hierarchy" and recommends flattening before parasitic extraction, and that subcircuit calls may be renumbered. Extraction therefore flattens, and device correspondence between the schematic and extracted netlists comes from netgen's LVS device match report, stored per design as an explicit device map, never from name matching. The claim 1 plan's month-1 item "extracted netlists preserve device instance names" is withdrawn.

**The map is complete and unambiguous, not one-to-one.** v1 required one-to-one correspondence and a loud failure otherwise. That rule rejects valid layouts: a multi-finger device legitimately extracts as parallel devices, and parallel devices are legitimately merged. The requirement is that every schematic device map to a non-empty set of extracted devices, every extracted device to exactly one schematic device, and the split/merge factor be recorded per device. This matters physically as well as bookkeeping-wise, because the sky130 mismatch term scales as `1/sqrt(l*w*mult)`: whether a device appears as one instance of width W or N instances of width W/N changes its mismatch magnitude by a factor of sqrt(N). The **offset-aggregation rule** — how the standardised offsets of N extracted devices represent one schematic device's draw, and how the reverse mapping is formed for claim 2's offset inputs — is fixed in month 1, pre-registered, and verified against a deliberately multi-fingered reference device.

**An independent DRC stage precedes LVS** (claim 1 plan §3). A layout tool's claim to respect design rules by construction is exactly the kind of tool-reported success this thesis exists to check, so it is checked with Magic against the sky130 rule deck rather than believed.

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

### 2.7 The canonical schema

Everything below is defined once, here, and referenced everywhere else. v2 corrected several of these in introductory prose while leaving the executable rules in §4.1, §4.2, §5.1 and the claim 1 `canonicalise` stage saying something different — and where prose and an executable rule disagree, the rule is what runs. This section is the rule.

**Parameters.** Three disjoint groups per topology.

| Group | Contents | Differentiated? | Changed by? |
|---|---|---|---|
| Continuous `x` | log10 width and log10 length per transistor; log10 resistance, log10 capacitance and the signed encoding of each source value **wherever the benchmark exposes that device as a sizing variable**; tied devices contribute one coordinate | yes | continuous actions |
| Discrete `d` | multiplicity, finger count | no | discrete actions |
| Context `c` | supply, load, temperature, corner id, testbench id, layout policy | no | fixed per evaluation and recorded |

v2 restricted `x` to transistor W and L. That is wrong wherever a compensation capacitor, a bias resistor or a reference current is a variable the generator searches — and on the Miller, Ahuja and feed-forward amplifiers it is. A quantity that can be changed must be in the parameter vector and in the derivative protocol; adding it as an input feature only lets the model *see* it, not be differentiated with respect to it.

**Source and passive encoding.** Resistances and capacitances are positive and take log10. Source values can be zero or negative, so a logarithm is undefined; they are encoded as `asinh(v / v_0)` with a per-class scale `v_0` fixed in the pre-registration, which is smooth, signed, and reduces to a logarithm for large magnitudes. v2 said "the log of the device's own value ... voltage in volts" with no rule for zero or negative, which does not survive contact with a ground-referenced source.

**Legal moves and realised displacement.** A requested change `h·u` is applied, then range-checked, then quantised to the manufacturing grid. **The quantised endpoint is what is simulated, so the realised displacement is `x' - x`, not `h·u`.** Every derivative record stores the requested direction, the realised displacement and their angle; a finite difference is reported against the realised displacement, and records whose angle exceeds a pre-registered tolerance are excluded and counted. v2 required only that a step exceed the grid, which stops a step from being a no-op but does not make the difference quotient a derivative along the direction that was asked for.

Where a smooth derivative is wanted rather than a realised finite change, it is taken on the **unquantised schematic** and the grid-quantised move is validated separately against it. The two are different objects and the thesis reports both rather than conflating them.

**Device correspondence.** The schematic-to-extracted map is an **equivalence-group** map, not a function in either direction: a group of schematic devices corresponds to a group of extracted devices, and both sides may have more than one member. v2 required every extracted device to belong to exactly one schematic device, which permits splitting and forbids genuine merging, while the surrounding text claimed to support both. Two rules follow:

- **Devices whose mismatch draws must stay independent are never merged.** Matched pairs, and any device the propagation test differentiates with respect to, are instantiated separately in the extracted netlist even where a tool would merge them. Merging is permitted only inside a group whose members share a draw by construction.
- **Scalar aggregation is not assumed to preserve response.** Where a group has more than one member on either side, the group's offset is defined by the pre-registered aggregation rule *and* the group is flagged; response and propagation results are reported with and without flagged groups, because a scalar aggregate cannot represent different local parasitics on nominally identical devices.

**The endpoint.** One specification, executed identically wherever a design is certified:

```
CERTIFY(design, policy):
  1. layout under policy; DRC; LVS; extract
  2. nominal scan over the 29-corner set on the extracted netlist
     -> if any corner fails, FAIL (nominal)
     -> else worst_corner := argmin over corners of the design's margin
  3. mismatch draws at worst_corner, under the calibrated two-stage
     rule of claim 1 plan §1
  4. PASS / FAIL / INDETERMINATE from the conjunction of 2 and 3
```

Three things this fixes. The worst corner is **re-derived for the design being certified**; v2's claim 3 reused the starting episode's worst corner, and a sizing change can move it, so reusing it does not implement the endpoint. The nominal 29-corner scan is **part of the endpoint**, not an earlier stage's leftover, so it is costed. And step 3's mismatch set is whatever claim 1's shortcut validation selected — if that validation escalated to all-corner mismatch, `CERTIFY` escalates with it everywhere. **The selected endpoint is a value recorded in the month 6 database tag and read by claims 2 and 3**, not a constant written independently into three documents.

The episode's original worst corner survives as a **screening rung** inside claim 3's ladder, which is cheap and is allowed to be wrong. It is not the endpoint.

**Shortcut validity on repaired designs.** Claim 1 validates the worst-corner shortcut on claim 1's designs. Repaired candidates are not those designs — they have been perturbed, sometimes in finger count, which moves device geometry and mismatch magnitude together. A random sample of **40 repaired candidates that reach `CERTIFY`** is therefore re-run at all-corner mismatch, as the same validation on the population that matters, and the result is reported beside claim 1's. Budgeted in §5.5.

## 3. Claim 1, measurement

**Claim (v12 §3).** Of AI-sized designs that meet specification pre-layout, the fraction that still meets it after extracted parasitics, across corners, and under Monte Carlo mismatch, reported as curves against specification margin, differs by generator, circuit family and layout policy. Failures decompose over an eight-class partition into parasitic, corner and mismatch causes. Which designs pass is predictable from pre-layout features, with the predictor holding on topologies and generators it was not fitted on.

**The motivating claim is stated over named studies, not over the field.** v11 and v12 opened with "every one of those numbers is measured before layout, at the typical corner, with perfectly matched devices", which is a universal claim over a literature nobody has enumerated. What is defensible, and what the paper says, is the enumeration itself: a table of the generators in this study's population plus the systems reviewed in `papers/README.md`, each with the verification endpoint its paper actually reports — pre-layout or post-layout, single corner or corner set, nominal or Monte Carlo — with a citation per row and an explicit "not stated" where the paper does not say. The gap is then visible rather than asserted, and a counterexample makes the table more useful rather than falsifying the thesis.

`claim1-implementation-plan.md` v1 is the detailed plan and stands as written except where amended below. This section restates its structure so this document is self-contained, then lists the amendments in place.

### 3.1 Structure, restated

**Definitions.** Property, specification and pass are the benchmark's own, with phase margin added as a reported property everywhere it is missing and as a constraint only where the benchmark constrains it. **Margin is dimensionless**: `m_i = s_i * log10(x_i / t_i)` for ratio-scale properties and `m_i = s_i * (x_i - t_i) / Delta_i` with a pre-registered scale `Delta_i` for signed or zero-threshold ones. v1's `s_i (x_i - t_i)/|t_i|` applied after a log conversion was unit-dependent — a factor of 7.6 between log10(Hz) and log10(MHz) on a representative bandwidth — and since the limiting property is the argmin of `m_i`, its identity could flip on a unit change. The design's margin is the minimum over constrained properties, and the property attaining it is the limiting property. The survival curve is `F_S(tau)`, the fraction of designs with pre-layout margin at least `tau` that pass stage S, with Wilson intervals and a separately drawn indeterminate band, reported per generator pooled across families and per family pooled across generators; the three-way breakdown is a supplement carrying its own n.

**Cells.** A factorial over extraction, corners and mismatch: 0 (schematic, typical, nominal), P, C, M, PC, PM, PCM, CM, plus a 40-design PCM-full subsample that validates the worst-corner shortcut. The factorial exists so that failure causes can be attributed; a sequential flow would attribute every failure to whichever stage ran first.

**Conditions.** Corner set of 29 points (tt, ss, ff at three supplies and three temperatures, plus sf and fs at nominal). Monte Carlo is mismatch only, 50 chips per design, 200 for designs **whose Wilson interval contains the yield threshold** — v1 and the claim 1 plan v1 both wrote this backwards, as designs falling "within the Wilson interval of the threshold", and a constant has no Wilson interval. Yield threshold 0.90, with **three-valued labels** (pass, fail, indeterminate) rather than a hard cut through the middle of the noise: the standard error of a pass fraction at true yield 0.9 is 0.042 at 50 chips and 0.021 at 200. The full pass-fraction distribution is stored and 0.99 is reported in the supplement with its resolution caveat.

**Endpoint, named once.** `PCM` — extracted, worst corner, Monte Carlo — is the primary signoff endpoint. `PCM-full` — extracted, every corner, Monte Carlo — validates the worst-corner shortcut on a 40-design subsample against a predeclared tolerance of 38-of-40 label agreement, with an escalation rule if it fails (claim 1 plan §1). The worst corner is selected with nominal devices and so need not be the corner of lowest yield, which is what the subsample tests. **Claim 3's accept criterion is PCM**; v1 described it as "all 29 corners, 50 chips", which is PCM-full, and that inconsistency is resolved here and in §5.1.

**Signoff is a conjunction.** Nominal pass and yield pass are recorded separately and neither is derived from the other. v1's claim that "a nominal failure cannot reach a 90% pass fraction" is false in general, and the escape rate is now measured on a 200-design subsample rather than assumed to be zero (claim 1 plan §1).

**Populations.** Eight generators (genetic, Bayesian, trust-region Bayesian, ADO-LLM, LEDRO, EEsizer, AutoSizer, AnalogSAGE), ten seeds per circuit at a 300-sample budget, over OSIRIS's five circuits, the ALIGN-supported amplifiers of AMS-SizingBench, and AnalogSAGE's specification sets applied both by AnalogSAGE and, as additional specification sets, to fixed AMS-SizingBench operational transconductance amplifiers under the other seven generators. Two single-pass layout policies, ALIGN and the OSIRIS baseline placer, one layout per design each. Target about 1,500 to 2,000 designs passing stage 0.

**Pipeline.** Ten stages, each a pure function from record to record plus a log: `harvest`, `canonicalise`, `sim0`, `layout`, `drc`, `lvs`, `extract`, `sim`, `verdict`, `features`. The independent `drc` stage is new in v2. Failures are logged by stage and never folded together.

**Predictor.** Pre-layout features only (per-property margins, device geometry, operating point, a finite-difference fragility feature, structure), logistic regression and gradient-boosted trees against a margin-only baseline, evaluated leave-one-**topology**-out and leave-one-generator-out with area under the ROC curve, Brier score and calibration. Folds group trajectory designs by run and topology, not by exact design id.

**Build order.** One family end to end under both policies before widening. A prospective power simulation at month 3 sets the seed count and the family list before the harvest launches. Preprint at month 4, conditional on the margin definition, the corner shortcut check and the yield labelling being settled. Submission at month 6, when the database and the frozen `episodes_v1` table are tagged.

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

**Design vector.** For a topology T with n_d devices, the **continuous** sizing vector x collects per device the logarithm base ten of width and length, with tied devices contributing one coordinate rather than one per device. The **discrete** part d collects per device the integer multiplicity and finger count. v1 put `log10` of multiplicity into the continuous vector; multiplicity goes 1, 2, 3 and a 2% step in its logarithm is meaningless, so multiplicity joins finger count on the discrete side and both are handled as actions, never as directions. The offset vector z collects, per device, four standardised mismatch coordinates (`vth0`, `toxe`, `voff`, `nfactor`), each a standard normal at nominal, so z = 0 is the nominal chip. A design is (T, x, d); a chip is (T, x, d, z). Jacobians and directional derivatives are with respect to x only.

**Margin, used identically here and in claims 1 and 3.** `m_i = s_i * log10(x_i / t_i)` for ratio-scale properties; `m_i = s_i * (x_i - t_i) / Delta_i` with a pre-registered `Delta_i` for signed or zero-threshold ones. Dimensionless by construction, so that the limiting property does not depend on whether bandwidth is written in Hz or MHz. One definition, in the claim 1 pre-registration, imported here and by claim 3.

**Change.** A change is a vector u in continuous sizing space, with a step size h, applied as x -> x + h u in log-sizing space so that a step is multiplicative in device geometry. Every step is checked against the three constraints of §2.3 — larger than the manufacturing grid, inside the device's model bin, in the converged regime — and steps failing the first two are recorded as no-op or bin-crossing and excluded from derivative headlines. Multiplicity and finger changes are integer and are handled as discrete action sets in claim 3, not as directions here.

**Simulated response.** For property i, `D_i(d, u, h) = f_i(x + h u) - f_i(x)` computed by the testbench at stage 0 (later, at a physical cell).

**Model response.** For arm B, the model predicts the change directly. For arms A and the supervised head, the predicted change is the difference of two predictions. Both are written `Dhat_i(d, u, h)`.

**What this means for arm A, stated because it bounds the claim — and v2 overstated it.** For arm A and for the supervised head, `Dhat - D` is *identically* the difference of the two pointwise prediction errors at `x` and at `x + h u`. v2 concluded from this that "only arms B and B-S can carry a mechanism that pointwise accuracy does not already determine". That is too strong, and the overcorrection would have thrown away a real question.

Response error is a functional of the pointwise error **field**, not of any scalar **summary** of it. A summary — R², mean relative error, even limiting-property value error — does not determine the spatial covariance of the errors, and it is that covariance which decides response fidelity. Two constructions make the gap concrete. A predictor with a constant bias per property has arbitrarily large value error and **exactly correct** responses everywhere, since the bias cancels in the difference. A predictor whose error oscillates on the scale of a typical design change has comparable value mean-squared error and **poor** responses. So for arm A the divergence between response fidelity and summary accuracy is a genuine, non-trivial empirical question, and the mechanism to name is **local error structure** — its correlation length relative to the action scale — rather than an architectural property that only pairwise models possess.

Arm A therefore stays a scientifically relevant model, not a null the pairwise arms must beat for the thesis to be valid. What the identity does license is narrower and still worth stating: for arm A, response error carries no information beyond the pointwise error field, so a finding there is about *which functional of the error field matters*, while for arms B and B-S it can additionally be about what the training objective put in the model. Both are reported, and the figures distinguish them.

**Arm A gets the same calibration arm B gets.** Arm B is given a per-context reference label to produce absolute values (below). Granting that one-point calibration to B and not to A would make the aggregate-accuracy comparison unfair in B's favour, so **arm A's predictions are offered in both forms** — raw, and recentred on the same measured reference — and both appear in every comparison. On held-out topologies, where a reference label is a real cost, the comparison is reported at equal label budget.

**Response error, the thesis's central quantity.** Per property, per design, per direction, per step:

```
e_i(d, u, h) = ( Dhat_i(d, u, h) - D_i(d, u, h) ) / s_i
```

where `s_i` is the standard deviation of property i over the evaluation set, in the units mode being used. The signed form is kept; the reported statistic is the median absolute value over the evaluation set, with the interquartile range, per property.

Two scale-free statistics are reported beside it. **Sign agreement**: the fraction of (design, direction) pairs on which the model gets the sign of the change right. **Pairwise ordering agreement**: over candidate pairs at the same design, the fraction on which the model orders the two changes as the simulator does. v1 described sign agreement as "what a ranker actually needs"; that is wrong, and the correction matters because claim 3 rests on it. A ranker orders candidates against each other, and in a repair loop most surviving candidates improve the limiting property, so their signs are all the same and sign agreement is constant across them. Ordering agreement is the quantity a ranker consumes; sign agreement is reported as the weaker, more familiar summary.

**Jacobian agreement.** Where a full Jacobian is available, per property i and design d: the cosine similarity between the model's gradient of property i with respect to x and the simulator's, and the relative error of the gradient norm. Cosine similarity is reported because a ranker cares about direction, and norm error separately because a repair step size cares about magnitude.

**The anchor, for the pairwise arms.** Arm B takes two designs, so "the model's gradient with respect to x" is ambiguous and v1 left it so. The definition: the gradient is taken with respect to the **second argument, evaluated on the diagonal** — `grad_b Dhat_i(x_a, x_b)` at `x_a = x_b = x`. This is the derivative the loop actually uses when it scores a small change from the current design, it coincides with arm A's gradient when the model happens to be separable, and it is the only choice under which the three arms' Jacobians are comparable quantities. The off-diagonal derivative `grad_a` at a distant anchor is reported once, as a diagnostic of anchor dependence, and never mixed into a headline.

**Aggregate accuracy, and the other comparators the claim needs.** v1 pitted response error on the limiting property against one comparator, global aggregate accuracy. Those two differ along three axes at once — response versus value, limiting-property versus all-property, local versus global — so winning would not say which axis did the work. The comparator set is therefore a ladder, every rung computed on the same held-out designs, the same calibration sets and the same scales:

1. **Global aggregate accuracy.** Coefficient of determination and mean relative error per property on held-out designs, computed exactly as the surrounding literature computes them, so that the thesis's claim of divergence is made against the quantity that literature reports. Mean relative error excludes samples whose true value is below a per-property floor, and the floor is stated, because that metric penalises small denominators (a point the radio-frequency graph-network paper makes explicitly when it declines to report the coefficient of determination for multimodal metrics).
2. **Limiting-property value error.** The same pointwise error, restricted to the property that limits the design. This isolates *localisation and property weighting* from *response fidelity*, and it is the rung v1 was missing: without it, an advantage for limiting-property response error could be nothing more than the fact that it looks at the right property.
3. **Local value error.** Pointwise error over the local candidate distribution — the designs a proposer actually generates around the episode's starting point — rather than over the global held-out set. This isolates *locality*.
4. **Feasibility calibration.** Brier score and calibration of the model's implied pass/fail verdict on held-out candidates.
5. **Ranking agreement.** Ordering agreement and top-k regret against the simulator's ordering on a fully evaluated candidate batch (§5.4).

Response fidelity earns its place only if it adds predictive power over rungs 2 and 3, not merely over rung 1.

**Absolute predictions from a change model.** Arm B outputs changes, so aggregate accuracy is undefined for it unless an anchor is fixed. The anchor: **one reference per (topology, context) pair**, not one per topology — a design's property vector depends on supply, load, temperature, corner and layout policy, so a single stored vector cannot anchor predictions made under a different context. `f(x_ref, c)` is measured once per pair and stored, with `fhat_B(x, c) = f(x_ref, c) + Dhat(x_ref, x; c)`. The reference sizing is the topology's benchmark default, fixed in the pre-registration and excluded from every training and evaluation set; the number of reference measurements is `topologies × contexts` and is costed in §4.9. Anchor sensitivity is reported once, by recomputing arm B's aggregate accuracy against five alternative reference sizings; if it varies materially, that is a finding about the pairwise arm and is reported rather than smoothed away.

**Evaluation set.** For a given model, the designs held out from its training set, restricted to topologies held out where the fold is a leave-topology-out fold, and grouped so that trajectory designs from one optimiser run never straddle the split. No response error is ever computed on a training design. Where the arm distinguishes trained from untrained directions, the direction exclusion is independent of the design exclusion and both are recorded (§4.3).

**Property table (the premise check, one page).** For every property of every family: whether it is determined by the inputs (all of them are, through the simulator); whether reading it from a representation plausibly requires a ratio rather than a linear combination; whether a squared-error target on per-chip data rewards it (nominal properties yes, spread-defined properties no); whether it is hidden (only the per-chip draw is); which of the four mismatch parameters are live on the devices that dominate it, given the zero slopes catalogued in §2.2; and its units mapping. Produced in month 6 and published as an appendix whatever it says.

### 4.2 The model skeleton

**Correction first.** v11 §4 says the skeleton is "a published learned circuit model (CktGNN- or INSIGHT-style)". Both are the wrong shape for this thesis, for reasons read from the papers:

- CktGNN's Open Circuit Benchmark is a **behavioural** abstraction: an operational amplifier's stages become voltage-controlled current sources with parasitic resistors and capacitors, with node features ranging over transconductance, resistance and capacitance. The DICE authors state plainly that it "is not suitable for device-level circuit evaluation since its circuit graphs do not use transistors as fundamental components". A model on that abstraction cannot be asked about a width change, so it cannot answer this thesis's question.
- INSIGHT has no public code, takes a flat parameter sequence rather than a graph, and is trained per topology ("For a given analog circuit topology"). It is a strong per-topology comparator, not a cross-topology skeleton.

**Primary skeleton, fixed here.** A device-level graph over the snapped netlist:

- **Nodes**: one per device and one per net. Node type is a one-hot over device classes (n-channel transistor, p-channel transistor, resistor, capacitor, current source, voltage source) and net classes (ground, supply, other), following DICE's nine-type scheme.
- **Edges**: one per device terminal, connecting the device node to the net node, typed by terminal role (drain, source, gate, bulk for transistors; the two terminals of a passive). Terminal-typed edges are used rather than net-collapsed edges because two terminals of one device can share a net, which makes a plain device-net edge ambiguous; that ambiguity is the stated motivation for the terminal-level representation of the few-shot pretraining work. Gate and bulk edges are directed from net to device, since the net drives the device far more than the reverse, as in DICE.
- **Node features**: for **transistors**, log width, log length, log multiplicity, finger count, the model bin index as a one-hot, and the four mismatch slope coefficients of that bin (process metadata, legitimately available to any surrogate, and needed if the model is to have any chance on the propagation test). For **passives and sources**, the log of the device's own value — resistance in ohms, capacitance in farads, current in amperes, voltage in volts — in a shared value slot, with a per-class mask so that the slot is interpreted by node type. Net nodes carry only their class.
  **This is a correction, not a detail.** v1 gave every device node width, length and multiplicity and gave passives no value at all. Width and length are meaningless for a compensation capacitor, so as specified the model could not distinguish two designs differing only in Cc — and Cc is a first-order determinant of bandwidth and phase margin on the Miller, Ahuja and feed-forward compensated amplifiers, which is to say on three of OSIRIS's five circuits and on exactly the properties claim 1 reports as failing after layout. A surrogate that cannot see the compensation capacitor cannot answer this thesis's question.
- **Global condition token**: one node connected to every other node, carrying the **testbench context** — supply voltage, load capacitance and resistance, temperature, corner identifier, testbench identifier, and, at the physical stage, the layout policy identifier. Its embedding is the graph readout, in the style of the pin-level transformer's graph token. Readout is the concatenation of the global token, a mean pool and a sum pool.
  **Why the context has to be an input.** The skeleton spans families whose testbenches differ in load and supply, and claim 3 requires predictions under two layout policies. Without these features the same recorded input has several legitimate outputs, and the target is not a function of the model's inputs. The target function the thesis fits is `f(T, x, d, z, corner, load, supply, temperature, policy)`, and every one of those arguments is either an input or is held fixed and recorded as fixed.
- **Backbone**: four to six generalised graph convolution layers with edge features (the DeeperGCN family used both by the few-shot pretraining work and by the radio-frequency graph network), hidden width 256, GraphNorm, LeakyReLU, residual connections.
- **Head**: one multilayer perceptron per property over the readout, with a mask so that one model spans families with different property lists, as FALCON does with its masked squared-error loss.
- **Offset input** (physical stage only): the per-device standardised offsets z are appended to device node features, zero at nominal. Where the LVS device map splits or merges devices (§2.4), the offset-aggregation rule fixed there determines what a schematic device node's z means.

**Capacity control.** A per-family multilayer perceptron on the flat sizing vector (five layers, widths 200 to 500, as in the published supervised benchmark models) is trained per topology. It bounds how much of any observed gap is representation rather than capacity, which matters because on a fixed topology with a dozen variables a small network fits nominal behaviour almost exactly.

**Published comparators.** DICE's encoder (public code) is used as an optional pretrained initialisation and reported as an ablation. FALCON's edge-centric network (public code, MIT licence) is re-trained on this data as a second published skeleton, because its representation is the dual of the one above (nets as nodes, devices as edges) and a result that holds on both is much harder to dismiss. CktGNN is cited as related work and not run. INSIGHT is re-implemented per topology from its published description only if the per-family control turns out to be the binding comparator, and is labelled a re-implementation.

### 4.3 The arms

All arms share the skeleton, the training data budget, the optimiser and the tuning effort. Differences are the input, the target and the loss.

**Arm A, forward.** Input (T, x); output the property vector. Loss: masked mean squared error on z-scored properties. This is the standard published surrogate and the reference point for aggregate accuracy.

**Arm B, change-based.** Input a pair of designs on the same topology, (T, x_a, x_b); output the change in each property. Representation of the pair follows pairwise difference regression: the shared encoder is applied to both designs and the head consumes the concatenation of the two readouts, their difference, and the raw change vector. The head is a nonlinear multilayer perceptron over that concatenation, so it is *architecturally capable* of non-separability; whether it uses that capacity is measured, not required.

**Separability is a diagnostic, not an acceptance criterion.** v1 required the model's anchored-pair discrepancy to exceed a pre-registered threshold or the arm was "reported as having collapsed to A", and decision D4 made that a pass/fail gate at month 8. That is backwards, and the reason is elementary: for a deterministic property the exact change is

```
D(a, b) = f(b) - f(a)
```

which **is** separable, and which satisfies `D(a,a) = 0`, antisymmetry `D(a,b) = -D(b,a)` and cycle consistency `D(a,c) = D(a,b) + D(b,c)`. An accurate change model approaches those identities. A gate that demands departure from them rewards approximation error and would discard arm B precisely when it works. D4 is removed from §7 as a gate.

What replaces it is a set of reported diagnostics, all cheap, none load-bearing:

- **Anchored-pair discrepancy**, the quantity v1 gated on, reported as a distribution rather than thresholded.
- **Cycle consistency**, the median absolute value of `D(a,c) - D(a,b) - D(b,c)` over held-out triples, scaled by `s_i`.
- **Reflexivity and antisymmetry**, `Dhat(a,a)` and `Dhat(a,b) + Dhat(b,a)`.

These describe how the pairwise arm behaves. The question of whether pairwise training buys anything is settled where it should be — by comparing arms A, B and B-S at matched data, matched epochs and matched tuning effort on response error, ordering agreement and Jacobian agreement.

**A correction to the loss algebra v1 cited.** For a separable predictor with pointwise errors `e_j`, the complete all-pairs squared loss is

```
sum_a sum_b (e_b - e_a)^2 = 2N sum_j e_j^2 - 2 (sum_j e_j)^2 = 2N sum_j (e_j - ebar)^2
```

so it reduces to the *centred* single-point loss scaled by 2N, not to the ordinary single-point loss. The difference is not pedantic: the pairwise loss is invariant to adding a constant to every pointwise error, so a constant offset per property is unidentified from pairs alone. This is a second reason arm B needs the explicit reference anchor of §4.1, and it is why the sparse distance-stratified pair sampling below changes the effective loss again and is reported as a design choice rather than treated as equivalent to the complete loss.

**Pair construction.** Pairs are within a topology and within a testbench context. The log-sizing distance between members is stratified into bins covering 0.02 to 1.0 decades, sampled uniformly across bins so that small and large changes are equally represented, because shortcut failures are expected on large changes where the linearisation breaks. The number of pairs is capped at twenty per design to keep the quadratic blow-up bounded; the pairwise literature's own stated limitation is that the training set becomes the square of the design set. Because this sparse stratified sample is not the complete all-pairs loss whose algebra is given above, the sampling scheme is reported as part of the arm's definition and an ablation at fifty pairs per design is run once, at one dataset size, to bound its effect.

**Arm B-S, change-based with derivative supervision.** Arm B plus a Sobolev term on a recorded subset of directions. Loss:

```
L = L_value + sum_j w_j * L_derivative_j
```

with derivative targets from §2.3. Weighting follows the scaling recipe of the Sobolev surrogate work: min-max scale the outputs and each derivative to the unit interval on the training set, then set every w_j to one, which removes the free parameter that the gradient-enhanced physics-informed literature found to matter (there, a weight of 0.01 was best and a weight of 1 was worse than no derivative term at all). Because that literature disagrees on whether the weight is benign, a three-point sweep over {0.01, 0.1, 1.0} of an additional global multiplier is run once, at the second-smallest dataset size, and then fixed for everything else and reported. First order only: second-order supervision is not run, and the reason is stated (cost, and the fact that a rectified-linear network's second derivative is degenerate).

**Derivative supervision is confined to a rank-deficient subspace. This replaces two mutually exclusive rules in v1.**

v1 said both that "forty per cent of the dictionary is marked trained and used in B-S's derivative term" and that "derivatives are supervised through random projections onto directions drawn uniformly from the unit sphere, one per sample per epoch". Those cannot both be true. If supervision is on fresh uniform projections, then over training every direction is trained in expectation and instrument 6 — the held-out-direction test, one of the seven load-bearing instruments — measures nothing at all.

Worse, even the dictionary rule as written withholds nothing. At a fixed design, directional derivatives are linear measurements `y = U g` of the gradient `g`. v1's dictionary was the coordinate directions plus the intervention directions plus forty random ones; forty per cent of that is roughly 29 directions in a 20-to-35-dimensional continuous sizing space, which generically **spans it**. The full gradient is then identified from the trained directions, and an "untrained" direction is a linear combination of trained ones — a new measurement of an already-determined quantity, not withheld information. Instrument 6's stated interpretation, evidence of a model that "contains a property without using it", does not survive that.

The construction in v2:

- Per topology, let `n` be the number of independent continuous parameters after ties are collapsed (§2.3). Fix a **trained subspace** `S` of dimension `r = floor(n/2)`, drawn as a random `r`-dimensional subspace by a pre-registered seed, plus the per-property intervention directions of instrument 5 **projected into S** so that they remain usable.
- B-S's derivative term supervises **only on directions inside S**. The random-projection estimator is retained for efficiency but the projections are drawn uniformly from the unit sphere *of S*, not of the full space. One per sample per epoch, as before.
- Instrument 6 evaluates on directions drawn from the **orthogonal complement of S**, which by construction carries **no direct derivative labels**. The stronger statement — that no training signal touched it — would be false: value labels across designs constrain the function in every direction, so a model can and probably will learn something about the complement from values alone. What is withheld is derivative supervision, and that is what the instrument isolates.
- Because of that, the comparison instrument 6 reports is not the S-versus-complement gap on its own, which would confound derivative transfer with whatever values already supplied. It is **B-S against B on the same complement directions**: B has value labels and no derivative labels anywhere, so the difference between them on the complement is the transfer attributable to derivative supervision. The within-model S-versus-complement gap is reported beside it as a descriptive statistic.
- **The coordinate metric defining orthogonality is stated**, because "orthogonal" is not basis-free: orthogonality is taken in the log-sizing coordinates of §2.7 under the identity metric, after tied coordinates are collapsed and each coordinate is standardised by its range across the training set. A different metric gives a different complement, and the choice is pre-registered rather than left implicit.
- The **rank and conditioning of the realised trained set are computed and reported at every design**: the singular values of the stacked trained-direction matrix, its numerical rank at a stated tolerance, and the fraction of the gradient's norm lying in `S` versus its complement. If the realised rank exceeds `r`, that is a bug and the run is discarded.
- `r = floor(n/2)` is a choice with a cost: half the derivative labels are unusable for training. The alternative, spanning supervision, buys a better model and destroys the instrument. Since instrument 6 exists to answer a question no cheaper instrument answers, the model pays. A spanning-supervision arm, **B-S-full**, is trained alongside at the same label budget and reported, so the cost of the restriction is measured rather than assumed.

The subspace is per topology, fixed by seed, and pre-registered.

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

**Pre-registered secondary prediction.** With abundant data the best selection keeps hard, boundary examples, and with scarce data it keeps easy ones, so the ranking of the three strategies is expected to change across the size axis. This is the data-pruning result transplanted. v1 called the transplant "tight rather than loose" on the ground that the margin is the analogue of the difficulty metric; that overstates it, and v2 does not. Sorscher's difficulty is distance to a decision boundary in a *learned representation* for a classification task; distance to a *specification threshold* in output space is a related but distinct object, and the prediction is recorded as a transplanted hypothesis rather than as a corollary.

**What is estimated, and what is not required.** v1 said "the claim needs the size axis flat and the selection axis not", which writes an experiment to require a result. There is no general reason quantity must have a flat effect: more data can improve coverage, and boundary sampling can improve boundary performance while degrading global performance. The tension is visible inside v1's own text, which expects aggregate accuracy to improve with size on every strategy — and since response error for arm A is identically a difference of pointwise errors (§4.1), an improving accuracy axis makes a flat response-error axis unlikely for that arm.

What is estimated instead: **the size effect, the selection effect and their interaction**, each with an interval, on response error on the affected properties and on every comparator rung of §4.1. The pre-registered hypothesis is that the selection effect is larger than the size effect over this range, and that the interaction is non-zero. A flat size axis is one possible outcome, not a requirement, and the figure is drawn so that a strong size effect is as readable as a weak one.

**Evaluation distribution, stated because it decides the answer.** Response error is reported on three explicitly defined evaluation sets, since "coverage" is meaningless without saying coverage of what: a **uniform** set over the benchmark ranges, a **boundary** set near specification thresholds, and a **loop** set drawn from the candidate distributions claim 3's proposer actually generates. A strategy that wins on one and loses on another is the expected result and is reported as such.

**Budget semantics.** The boundary strategy needs a surrogate ensemble, rejection sampling and candidate screening, none of which appear in v1's training-pool line. Every strategy's acquisition cost is counted in full — proposals generated, candidates screened, simulations rejected, derivative labels purchased — and the comparison is reported **twice**: at equal design count and at equal simulator cost. They will not give the same ranking, and the difference is a result rather than an inconvenience.

**Replication on a closed process.** The same coverage-versus-quantity design is repeated on FALCON's public dataset (about one million Cadence-simulated circuits, twenty expert-designed topologies in five families, 45 nm, every simulation at a fixed 30 GHz). No simulator is available for that process, so the intervention and propagation tests cannot run there.

**Response fidelity can be replicated there after all, which v1 assumed it could not.** The dataset is a million parameter-performance pairs. Wherever two designs of the same topology and context both appear in it, the finite change `D = f(b) - f(a)` is computable directly from stored rows with no simulator at all. What is lost is control over direction and step size; what is gained is a genuine response-fidelity measurement on a closed 45 nm process. The replication is therefore: probes and aggregate accuracy as in v1, **plus** response error and ordering agreement on naturally occurring within-topology pairs, with the realised distribution of pair distances and directions reported so a reader can see how it differs from the designed dictionary. Pair density per topology is measured when the download size is measured [verify]; if a topology yields too few usable pairs, it contributes probes only and says so.

Agreement between an open 130 nm operational-amplifier set and a closed 45 nm millimetre-wave set makes the coverage claim hard to dismiss as a process artefact; disagreement is reported as a boundary on the claim. Where the replication is probes-only, it is described as a replication of the *representation* findings, not of response fidelity.

### 4.5 Instruments

Seven instruments, fixed in advance, each with its protocol.

**What this instrument set can and cannot license, stated before the instruments so that no figure caption has to walk it back.** A probe recovering a property establishes **decodability under the probe protocol**. A wrong predicted response establishes **behavioural approximation error**. Every intervention below acts on the model's *inputs*, not on its internal representation. None of that demonstrates that a particular internal representation causally mediates a prediction, and v1's "read versus use" framing claimed more than the instruments deliver.

So: **behavioural response fidelity is the primary construct** of claim 2, and it is what the headline figures measure. Probes are supporting evidence about decodability and are reported net of their control task. The phrase "contains but does not use" appears nowhere in the thesis as a conclusion; where the contrast between a high probe score and a large response error is reported, it is described as what it is — a property is decodable from the representation and the model's behaviour does not track it — with the causal reading named as a hypothesis that would need representation-level interventions this thesis does not run.

**1. Linear probe.** Ridge regression from a frozen representation to a property, fitted with gradients blocked from the model, one probe per layer plus one on the readout, scored by the coefficient of determination on held-out designs. Regularisation chosen on a validation split.

**2. Nonlinear probe.** A multilayer perceptron probe, hidden width swept over {16, 64, 256} and depth over {1, 2}, best validation cross-entropy or squared error selected, reported beside the linear probe. The information-theoretic argument for always using the most expressive probe and the control-task argument for restraint are both respected by reporting both numbers rather than choosing a side.

**3. Control task and description length.** Two independent guards against reading a probe's own flexibility as a property of the model.

- *Control task.* For each design, a control target is drawn once from the empirical distribution of the real property and is a deterministic function of the design's discrete identity (the topology identifier and the vector of snapped bin indices), which is the circuit analogue of the word-type construction. Selectivity is the probe score on the real property minus the probe score on the control. Every probe number in the thesis is reported net of this.
- *Description length.* The online (prequential) code, with the standard block schedule at 0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.25, 12.5, 25, 50 and 100 per cent of the probe training set. This is included because probe accuracy has been shown to reverse its ranking of layers across random seeds while the description length stays stable, and this thesis reports layer comparisons.

**4. Supervised head, the learnability certificate.** Two variants, because v1's single "separate head on the same skeleton and the same data" was ambiguous about whether the backbone is retrained, and the two answer different questions.

- **4a, frozen backbone.** A head trained on the frozen representation of the model under test. This certifies what *that representation* supports.
- **4b, full retrain.** A head and backbone trained together from scratch on the same data, same budget, same folds. This certifies what the *model class and data* support.

A statement of the form "the model failed to learn X" requires 4b to reach X — the information was there and this architecture on this data can extract it. Where 4a fails and 4b succeeds, the finding is about the representation the training objective actually produced, which is a narrower and more interesting statement, and it is reported as such.

**5. Intervention test.** For design d and property i:

- Compute the simulator Jacobian J at d (§2.3), with respect to the independent continuous parameters only.
- **Check that an isolating direction exists before constructing one.** Form the matrix of the other monitored properties' gradients, take its singular value decomposition, and compute the component of `grad f_i` orthogonal to their span together with the fraction of `||grad f_i||` that component carries. Circuit trade-offs are strongly coupled — gain against bandwidth, both against power — and with a dozen monitored properties on twenty-odd parameters the residual can be numerically negligible, in which case a "property-isolating direction" is a direction along numerical noise and the model's response to it means nothing. **Pre-registered rejection rule:** the design is excluded from this instrument for property i unless the orthogonal component carries at least 10% of the gradient norm and the condition number of the other-gradient matrix is below 10^4. Exclusions are counted and reported per property and per family, and a property excluded on most designs is reported as **not isolable in this family**, which is a finding about the circuit rather than a gap in the results.
- Build `u_i` as that orthogonal component, normalised. This moves i while holding the rest still, to first order.
- Evaluate at a small step and at a large step, with the path simulated at five points out to 0.3 decades. At the large step the held properties do move; their co-movement is measured and **reported alongside** the response error as well as regressed out. Regressing out co-movement over a long nonlinear path is a statistical adjustment, not a controlled intervention on one property, and the residual co-movement is disclosed on every figure so the reader can judge how much the adjustment is carrying.
- Build a second direction set that moves the shortcut candidates without moving i: directions in the null space of the gradient of i with a large component along a shortcut feature's gradient, subject to the same conditioning rule.
- Score: response error on the first set (a model that tracks the property follows it) and response magnitude on the second (a model that leans on a shortcut moves when it should not).
- All directions are constructed within a model bin and above the manufacturing grid (§2.3); bin crossings and no-op steps along a path are logged and those paths excluded from the headline with the counts reported.

**6. Held-out-direction test.** Arm B-S scored separately on directions inside its trained subspace `S` and on directions drawn from the orthogonal complement of `S` (§4.3). Because supervision never touches the complement, and because the realised rank of the trained set is measured and reported at every design, a gap between the two is evidence that derivative supervision does not generalise across directions.

That is the whole of what it shows. v1 called this "the cleanest available evidence of a model that contains a property without using it"; it is not evidence of that, both because the instrument as v1 specified it withheld no information at all (§4.3) and because generalisation across directions is a statement about the fitted function, not about internal use. It is the only instrument that isolates whether derivative supervision transfers off the supervised subspace, which is a worthwhile question on its own terms, and it is reported as that question's answer.

Arm **B-S-full**, supervised on the full space at the same label budget, is the comparator that says what the rank restriction cost the model.

**7. Propagation test.** In §4.6.

**Shortcut candidates.** Found two ways. By correlation inside each training set: any cheap feature (a single device width, a width ratio, total gate area, a bias current) whose correlation with a property exceeds a pre-registered threshold on that training set. And by construction: training sets in which a chosen cheap feature is deliberately made to co-vary with a property, so that a gap can be attributed to the shortcut rather than to accident. The constructed sets are described in §4.7.

### 4.6 The propagation test

**Statement.** The first-order spread of property i under manufacturing mismatch is the model's sensitivity to the per-device offsets, propagated through the process covariance. Because §2.2 established that covariance is the identity in the standardised coordinates z, the propagated spread is

```
sigma_hat_i = sqrt( sum_k ( d fhat_i / d z_k )^2 )
```

evaluated at the design's nominal chip, where k runs over the four mismatch coordinates of every device.

**The offset sensitivity has to be supervised; it is not free.** v11 §4 and v1 of this plan said a faithful sensitivity gives the spread "with no per-chip training at all". That is wrong as a matter of identifiability. If a model is trained only on data at `z = 0`, then `fhat(x, z)` and `fhat(x, z) + a(x)·z` fit the training data equally well for **any** `a`, so `d fhat / d z` is arbitrary and the propagated spread is arbitrary with it. Supplying a zero-valued input and the known slope coefficients does not resolve this; nothing in the nominal data constrains the offset direction.

So the propagation test has a precondition, and the arms are split accordingly:

- **Nominal-only arms (A, B).** No offset supervision of any kind. Their propagation result is reported as the *control*: it shows what the unconstrained offset sensitivity of a nominally-trained surrogate looks like, which the identifiability argument predicts should be uninformative. If it is informative, that is a surprise worth investigating and is reported as one.
- **Offset-derivative-supervised arm (B-S-z).** Arm B-S with derivative supervision extended to offset directions, using the 0.5-standard-deviation central differences of §2.3. **This is the arm the propagation test is about.** Labels: 4 parameters × n_devices × 2 runs per labelled design, which is 120 simulations on a 15-device circuit — costed explicitly in §4.9 rather than absorbed.
- **Sampled-offset arm (B-mc).** Trained on a handful of off-nominal chips per design rather than on offset derivatives, as the alternative route to the same information. This is the "input carries it" branch of the conditional-mean argument.

"No per-chip training" is retained only in its true, narrower sense: **no dense Monte Carlo training**. A few offset derivative labels per design is not dense Monte Carlo, and the distinction is the interesting one.

**Which designs get offset labels.** The 500-design propagation evaluation set of this section, plus 1,000 training designs stratified across families, fixed by seed and pre-registered. That is the whole offset-label budget and it appears as its own line in §4.9.

**The two-way decomposition, which is what makes the result interpretable.** Three quantities are compared, not two:

1. `sigma_MC`, the Monte Carlo spread from simulated chips (the truth).
2. `sigma_sim`, the same first-order propagation using the **simulator's** finite-difference offset Jacobian.
3. `sigma_hat`, the same propagation using the **model's** offset Jacobian.

`sigma_sim` against `sigma_MC` measures how good first-order propagation is for that property at that design, independently of any learned model. `sigma_hat` against `sigma_sim` measures the model. Without this control, a property whose spread is genuinely nonlinear in the offsets (an offset voltage near a null, a phase margin near a pole crossing) would be scored as a model failure. The thesis reports both ratios, per property, as distributions of the logarithm of the ratio over the evaluation set, plus the rank correlation across designs, which is what a yield-aware search would actually use.

**Marginal spreads are not yield, and the claim is scoped accordingly.** Correct per-property standard deviations do not establish joint multi-specification yield: whether a chip passes depends on all constrained properties at once, so cross-property covariance and nonlinear tails both matter. Under the linear-Gaussian approximation the natural object is the full matrix

```
Sigma = J_z J_z^T
```

whose diagonal is the marginal variances the formula above gives. `J_z` is already computed, so the off-diagonals are free, and v2 reports the full matrix: per-property spread, the induced **correlation** between limiting properties, and a Gaussian-orthant estimate of joint yield compared against the Monte Carlo pass fraction. Where that estimate is validated, the propagation result speaks about yield. Where it is not, the conclusion is scoped to **per-property simulated spread under the kit's own mismatch model**, and the paper says which.

**Final validation is on a fresh sample.** The Monte Carlo reference for any design used to select or tune anything is redrawn with fresh seeds before it enters a headline number, so that a spread the model was implicitly fitted toward is not also its own test.

**Evaluation set.** 500 designs spanning the families, each with: the model's offset Jacobian by automatic differentiation; the simulator's offset Jacobian by central differences at 0.5 standard deviations, which is 2 × 4 × n_devices simulations; and 200 fresh chips for the Monte Carlo reference, giving a relative error on a spread of about five per cent. Devices whose mismatch slope for a parameter is zero (§2.2, note 3) contribute a structurally null coordinate; those coordinates are retained in the sum, where they contribute nothing, and are reported separately so that a property whose spread has no live parameter on its dominant devices is identified as untestable by propagation rather than scored as a model failure.

**If it fails.** Arm B-het runs, to establish whether the spread was learnable from per-chip samples at all. The conditional-mean argument predicts that a squared-error model learns no spread unless the objective or the input carries it; the offset input is exactly the "input carries it" branch, so a failure of propagation with a success of B-het localises the failure to the sensitivity rather than to the information.

### 4.7 Constructed shortcut sets

For each of three chosen properties per family, a training set is built in which a cheap feature is made to co-vary with the property beyond its natural correlation, by rejection sampling designs until the correlation reaches a pre-registered target (0.9, against a natural baseline that is measured and reported). A matched control set of the same size has the correlation broken by the same rejection sampling in the opposite direction.

**Rejection sampling moves more than the correlation, and the shift is measured.** Rejecting designs to hit a target correlation necessarily reshapes the marginal distribution of both the property and the feature, the joint density, and the effective support of the training set, so the shortcut set and its control differ in more than the intended way and a gap between them is not automatically attributable to the shortcut. Two mitigations, both pre-registered: the acceptance rule is **marginal-matched** where feasible, by rejecting against a target joint that preserves each marginal, using an importance-weighted acceptance rather than a hard filter; and whatever residual shift remains is **reported** — the marginals, the effective sample size after weighting, and the support overlap between the three sets are shown beside every result that uses them. Where marginal matching is infeasible at the target correlation, the target is lowered until it is, and the achieved correlation is reported rather than the intended one.

The mechanism then makes a further prediction that is tested rather than asserted: adding coverage along the constructed shortcut direction closes the response gap without adding quantity. Operationally, a third set of the same size adds designs that vary the property while holding the shortcut feature fixed, and the prediction is that the response error on that property falls to the control set's level at unchanged N.

### 4.8 Units

The full battery is repeated in ordinary and logarithmic units, on inputs (widths, lengths, currents) and on outputs (decibels, decades). The two-by-two of input units against output units is run at one dataset size; the remaining studies use the two diagonal modes. This is worth doing because the published supervised benchmark for this domain normalises everything linearly to the unit interval and never compares, so the question is open in the literature, and because a coordinate change is exactly the kind of intervention that moves what a probe can read without moving what a model uses.

### 4.9 Compute

Estimates at stage 0, at the AutoCkt schematic figure of 2.4 s per testbench, to be replaced by measured runtimes after claim 1's month-2 study.

| Item | Simulations | Core-hours |
|---|---|---|
| Training pools, all sizes and strategies, with reuse across cells | about 60,000 | 40 |
| **Selection-strategy acquisition overhead** (boundary surrogate ensemble refits, candidates screened and rejected, language-model proposals discarded) | about 40,000 | 27 |
| Derivative labels for B-S and B-S-full (4,000 designs, 40 directions, central differences) | 320,000 | 215 |
| **Offset derivative labels for B-S-z** (1,000 training designs, 4 parameters × n_devices × 2, at 15 devices) | 120,000 | 80 |
| **Sampled-offset training data for B-mc** (2,000 designs × 8 chips) | 16,000 | 11 |
| Intervention evaluation (500 designs, 12 properties, 2 direction sets, small step and a 5-point large-step path, plus the Jacobians that construct the directions where not already paid for) | about 120,000 | 80 |
| Propagation evaluation (500 designs: offset Jacobians plus 200 fresh chips each) | 160,000 | 107 |
| Units, ablations, seeds | about 60,000 | 40 |
| **Pre-layout total** | **about 896,000** | **about 600**, roughly 19 hours on 32 cores at full utilisation |

**Model fitting, which v1 omitted entirely.** Three selection strategies × four sizes × five arms (A, B, B-S, B-S-full, B-J) × three seeds is 180 fits, before the five-seed headline cells, the per-family capacity controls across roughly twenty topologies, the two units modes with a two-by-two at one size, the leave-topology-out folds, the weight sweep, and the equal-tuning-effort search trials each arm is entitled to. The realistic count is over a thousand fits. At the models' size — the reference point in §2.6 is about five million parameters on one consumer card — a fit is minutes to low hours, so the graphics card, not the simulator, is claim 2's binding resource for months 8 to 18. A measured per-fit time from the month 8 acceptance test replaces this estimate, and the fit count is enumerated in the experiment manifest (claim 1 plan §3) rather than described.

**These are scenario figures.** They assume the stated pass rates, no failed jobs and independent throughput on 32 cores. Measured median and tail runtimes from claim 1's month 2 study, including failures and retries, replace every line here before any harvest, with a contingency supported by that measurement.

The physical stage's response measurement needs its target named before it can be costed, which v2 did not do. 200 designs × 40 directions × 2 (central difference) is 16,000 **nominal** post-layout simulations, about 400 core-hours at 90 s — and that buys the response of the **nominal extracted property only**. If the target is a mismatch quantile or a yield, each perturbed design needs chips, not one simulation, and the cost is multiplied by the draw count.

The decision, taken here: the physical response measurement is of **nominal extracted properties**, at 200 designs and 40 directions, and every claim made from it is scoped to nominal post-layout response. Mismatch response is measured separately and much more narrowly — **40 designs × 12 directions × 50 draws**, about 24,000 simulations and 600 core-hours — because that is what the propagation and quantile-margin machinery of §5.2 actually consumes, and pretending a nominal difference measures it would be wrong. Both lines are in the manifest.

The **finger-variation set** is subject to the same distinction. Claim 1 harvests it at stage 0 and cell P, which are nominal, so it supplies **nominal extracted finger-response evidence**. It does not license finger-response claims at the mismatch endpoint. If claim 3's finger action set is to be ranked on quantile margins, a mismatch subset of the finger set — 60 designs × 2 assignments × 50 draws, about 6,000 simulations — is required, and it is budgeted in claim 1 plan §5 as part of the finger campaign rather than assumed.

Layout regeneration is a separate line: any perturbation evaluated at a physical cell needs its own layout and extraction, at 90 s per design per direction on the single-threaded queue, which for the nominal set alone is about 200 core-hours and was not previously stated. v11 §11's figure of about 100,000 pre-layout simulations for the propagation evaluation set is close to the propagation line above and is superseded by this table.

### 4.10 Fallbacks

- **The subcircuit patch fails.** Then the offsets cannot be set explicitly. Fallback: run mismatch with a logged seed and recover the draws by reading them out of ngspice's own listing of the resolved model parameters per instance [verify that the parameters can be dumped per instance]. If that also fails, the offset-input arm is dropped, the propagation test is run against the simulator's offset Jacobian only as a statement about first-order propagation in this process, and the model side of the test is reported as not runnable with the reason. Claim 2's other three parts are unaffected.
- **`.SENS` does not reach the parameters.** Covered: finite differences are the default, not the fallback.
- **The response gap is absent outside the constructed sets.** Then the finding is that these models are more faithful than the world-model and shortcut literature would predict, reported as such. Claim 3 then runs on a ranker set dominated by constructed and degraded models, and the utility paper's conclusion is explicitly scoped to **behaviour under controlled corruption** rather than to a predictive rule for naturally trained models. That is a real but much narrower contribution, and decision D6 exists so the narrowing is a recognised event at month 18 rather than a discovery at month 42.
- **The cross-topology model is much worse than per-family models.** Report both; the per-family control exists precisely to keep this from being read as a fidelity result.

### 4.11 Analysis and figures

Fixed before training. Anything else is exploratory and labelled.

1. Response error against **each comparator rung of §4.1** — global aggregate accuracy, limiting-property value error, local value error — one point per model, per property, with the rank correlation for each. The claim is that the correlation with global accuracy is weak on the affected properties; the figure has to be able to show that it is strong, and does so if it is. Arm A's points are marked, because for that arm response error is a functional of pointwise error by construction (§4.1) and the correlation there is a consistency check rather than a finding.
2. Per-property response error by arm (A, B, B-S, B-J) at each dataset size separately, never pooled, because the derivative-supervision literature states its advantage is largest at low data volume and near the training boundary and that comparison would be hidden by pooling.
3. Held-out-direction gap for B-S: inside the trained subspace against its orthogonal complement, per property, with **B-S-full** on the same axes so the cost of the rank restriction is visible, and with the realised rank and conditioning of the trained set reported per design (§4.3).
4. Coverage against quantity: response error on the affected properties, three strategies by four sizes, on each of the three evaluation distributions of §4.4, drawn **twice** — at equal design count and at equal simulator cost. Size effect, selection effect and their interaction are reported with intervals; the pre-registered flip prediction is marked on the plot as a hypothesis, and a strong size effect is as readable as a weak one.
5. Probe scores net of control task, with description length beside them, per layer, per property, against response error on the same property. This figure shows that a property can be decodable from the representation while the model's behaviour does not track it. It is not evidence of causal non-use, and its caption says so (§4.5).
6. Intervention test: response error on property-moving directions against response magnitude on shortcut-moving directions, per model, with the **isolability diagnostics** beside it — the fraction of gradient norm in the orthogonal component, the conditioning, the exclusion counts per property and family, and the residual co-movement at the large step (§4.5).
7. Propagation: distributions of log(sigma_sim / sigma_MC) and log(sigma_hat / sigma_sim) per property, plus rank correlation across designs, **faceted by arm** so that the nominal-only control (A, B), the offset-derivative-supervised arm (B-S-z) and the sampled-offset arm (B-mc) are never pooled — the identifiability argument of §4.6 predicts they should differ, and pooling them would hide exactly that. Plus the induced correlation matrix between limiting properties and the Gaussian-orthant joint-yield estimate against the Monte Carlo pass fraction.
8. Constructed shortcut sets: response error on shortcut, control and coverage-added sets, at equal N.
9. Units: the full battery in two modes, with the two-by-two at one size.
10. FALCON replication: probes and aggregate accuracy under the three selection strategies and four sizes.

11. Separability diagnostics for arm B: anchored-pair discrepancy, cycle consistency, reflexivity and antisymmetry, each as a distribution (§4.3). Descriptive; no threshold attached.

Statistical treatment: differences between arms and strategies are tested with paired tests across seeds and folds with Holm correction, reported beside effect sizes; no test is a headline; the curves and distributions are.

**Prospective power, month 8, before the studies run.** The coverage-versus-quantity design and the arm comparison are simulated at plausible effect sizes with the planned seeds and folds, and the minimum detectable difference is reported for each. Three seeds per cell and five on headline cells are v1's numbers; if the simulation says they cannot separate the strategies at the effect sizes the literature reports, the seed count rises and the number of cells falls. The point of running it at month 8 rather than at month 18 is that the cell count is still changeable then.

### 4.12 Build order, months 6 to 30

- **Months 6 to 8.** Property table. `episodes_v1` hold-out flag wired into training-set construction before any ranker is fitted (§1, rule 3). Skeleton implemented — including passive and source values and the global condition token (§4.2) — and trained as arm A on the trajectory pool; leave-topology-out folds fixed with run-level grouping; aggregate accuracy reproduced to the level the literature reports, as an acceptance test of the implementation. Pair construction, the reference anchor per topology, and arm B. Trained subspaces `S` constructed per topology with their rank recorded. Prospective power simulation (§4.11). Claim 2 pre-registration frozen and committed.
- **Months 8 to 12.** Sensitivity labels; arm B-S and the weight sweep; arm B-J. Instruments 1 to 4 with control tasks and description length. Direction dictionaries.
- **Months 12 to 15.** Instrument 5 and 6. Constructed shortcut sets and the coverage-adds-not-quantity prediction.
- **Months 15 to 18.** Coverage versus quantity, all twelve cells. FALCON replication. Units. Fidelity paper submitted about month 18.
- **Months 18 to 24.** Physical targets: post-layout and Monte Carlo properties as targets, offsets as inputs, the patched subcircuits in the loop. Offset derivative labels harvested and arms B-S-z and B-mc trained (§4.6).
- **Months 24 to 30.** Propagation test with its three-way decomposition and the full covariance; B-het if it fails; extension or follow-up paper.

### 4.13 Risks specific to claim 2

- **Absorption.** The nearest occupant is now a zero-shot analog evaluator on this very process: sixty amplifier topologies (sixteen from AnalogGym plus forty-four new), 60,000 parameter-performance pairs each, about 3.6 million instances on sky130 with ngspice, a pin-level transformer, and a held-out-topology result of 0.143 mean absolute percentage error against 0.301 for a multilayer perceptron. That is a bigger cross-topology dataset on the thesis's own process than the thesis will build. It reports no code or data release. Two consequences: the thesis does not compete on dataset size, and if that dataset is released it should be used, with the thesis's contribution staying the response, intervention, held-out-direction and propagation measurements, none of which that work performs. This changes v11 §7's absorption paragraph (§9).
- **The change-based arm collapses to the forward arm.** Guarded by the non-separability check in §4.3, which is a pre-registered pass or fail, not a judgement.
- **Derivative supervision helps everywhere, including untrained directions.** That is a clean positive result for B-S and is reported as such; the claim is written to accept either outcome.
- **Probes are uninformative because everything is decodable.** Likely on a cross-topology model with a rich readout, and the reason the intervention test, not the probe, is the load-bearing instrument. The probe's role is to establish the contrast, and a flat probe result with a large response gap is the cleanest form of the claim.

## 5. Claim 3, utility

**Claim (v11 §3).** On specifications limited by layout or by variation, the per-property response error on the limiting properties predicts the number of expensive checks a model-guided repair loop needs, for continuous sizing moves and for discrete finger-count moves, and aggregate accuracy does not.

**What is already known, so that the claim is stated at its true width.** That a model's aggregate accuracy need not track its usefulness for control is established outside circuits: one-step likelihood is "not always correlated with control performance" in model-based reinforcement learning, where the reported correlation between validation likelihood and episode reward ranges from 0.59 down to 0.07 and to minus 0.06 depending on the setting, and where fine-tuning a model to raise its likelihood from 4.827 to 4.85 dropped the reward from 176 to 98; two models are value-equivalent when they induce the same Bellman updates on the functions the planner uses; and weighting the model loss by value gradients beats maximum likelihood at low capacity. In surrogate-assisted optimisation, a controlled study with an adjustable pseudo-surrogate finds that performance stops improving above a pairwise comparison accuracy of about 0.7 to 0.8 for two of its three model-management strategies, and is flat in accuracy for the third. Inside circuits, one 2026 sizing paper states that "no prior work provides quantitative analysis of how prediction accuracy relates to convergence" and separately concludes that "convergence depends on the measurement-feedback architecture, not prediction accuracy"; and the closest analog optimisation paper that reports both held-out accuracy and iterations-to-target reports them as two tables and never relates them, with its own numbers showing two methods sharing a surrogate family differing by more than a factor of ten in iterations.

So claim 3 tests a known principle in a new domain, and the specific new quantity is the **per-property** response error on the **limiting** property, tested for **incremental predictive value beyond task-matched value accuracy** — not merely beyond the global aggregate accuracy the surrounding literature happens to report. The comparator ladder of §4.1 is what makes the test a real one; v1 compared against the weakest available alternative and would have been unable to say whether an advantage came from response fidelity, from looking at the right property, or from looking in the right neighbourhood.

**The novelty claim, narrowed.** v11 §3 asserts that no prior work, "in circuits or elsewhere", measures a surrogate's response or Jacobian agreement in connection with search cost. The "or elsewhere" is not defensible. Sobolev training targets derivatives directly; Tsay's derivative-trained surrogates are evaluated on downstream optimisation; and the derivative-free and model-based optimisation literature ties the quality of a model's gradient approximation to optimisation behaviour explicitly — Giovannelli and colleagues analyse function, gradient and Hessian approximation together with the optimisation that consumes them [obtain: arXiv 2311.12253, not in `papers/`]. Two of those three are already in this thesis's own bibliography as method sources.

What v12 claims instead is the **documented combination**, and it is stated as a comparison matrix rather than as an absence: derivative accuracy, local finite-change error, constrained ranking under a specification, post-layout targets, mismatch propagation, and held-out search utility, on circuits, with the response measured against the simulator that defines truth. Originality is claimed for that combination and for the resulting insight, not for the individual ingredients. `papers/README.md` already states the gap this narrowly; v11 §3 does not, and that is a wording slip to fix rather than a conceptual error to defend.

**The Bian and Xie preprint is real, and it is closer than the audit suggested.** The arXiv record was retrieved on 8 September 2026: Chengkuo Bian and Pengcheng Xie, *"Why and When Neural Networks Improve Local Approximation in Optimization"*, arXiv 2608.24963, submitted 25 August 2026. It is a general derivative-free-optimisation paper, not a circuits paper, and it argues that whether a neural surrogate pays is delimited by three factors — **role** (proposing candidates the true objective must still approve, versus replacing a gradient the solver depends on), **radius** (a model fitted to an optimisation path is reliable only inside a bounded neighbourhood), and **room** (a surrogate can only accelerate progress the base method is still able to make) — "rather than the fit accuracy a training curve reports". It formalises radius-aware local generalisation, relates it to the classical fully linear condition, and tests each factor with surrogate class, training pipeline and base method held fixed over 117 benchmark instances.

Three of its reported results bear directly on this thesis and are treated as prior art rather than as background:

1. Fit accuracy does not delimit surrogate benefit. That is this thesis's own premise, now published in the general setting.
2. Removing the gradient term from the training loss cut surrogate acceptance from 0.703 to 0.148 — arm B-S against arm B in this thesis's vocabulary, in another domain.
3. A model-based trust-region solver, which leaves little room, dropped from 88 to 86 instances solved when the same surrogate was attached. That is the strategy-dominance shape §5.4 already fits as a pre-registered alternative.

**What this leaves, and what it strengthens.** It narrows the novelty claim: the general principle is no longer this thesis's to establish, and §5's framing above is written accordingly. It also strengthens the premise, because an independent group testing the same idea with a different method and a different base solver found it holds — a question two groups arrive at separately is more likely to be a real one. What remains unoccupied is the circuit-specific instantiation: response fidelity measured against the simulator that defines truth, on **constrained** ranking under a specification, at **physical verification endpoints** carrying parasitics, corners and mismatch, with claim 1's population measurement underneath it. Their "radius" is this thesis's action scale, and the framing is adopted explicitly rather than reinvented — the coverage-versus-quantity design (§4.4) and the action-scale conditions (§5.1) are its circuit instances and cite it as such.

Being a preprint, it is cited as one; neither peer review nor the correctness of its numbers is assumed, and the thesis does not rest on either. It is added to `papers/README.md` and read in full before the claim 2 pre-registration freezes at month 8.

**The comparison matrix, which is the form the novelty claim now takes.**

| Work | Derivative accuracy measured | Local finite-change error | Constrained ranking | Post-layout targets | Mismatch propagation | Related to search cost |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Sobolev training (1706.04859) | yes | no | no | no | no | no |
| Tsay 2021, Sobolev surrogates | yes | partly | no | no | no | yes |
| Giovannelli et al. (2311.12253) | yes | yes | no | no | no | yes |
| Bian and Xie (2608.24963) | yes | yes, as radius | no | no | no | yes |
| DNN-Opt | no | no | yes | no | no | partly |
| FALCON, ZEROSIM, INSIGHT | no | no | no | no | no | no |
| PANDA, SABLE, layout-aware sizers | no | no | yes | yes | partly | no |
| **This thesis** | yes | yes | yes | yes | yes | yes |

No single cell in the bottom row is new. The row is the claim, and it is stated as a combination rather than as an absence — which is also why a newly discovered overlapping paper adds a row to this table instead of threatening the thesis.

**One prior-art correction that narrows the novelty claim.** A learned model conditioned on a change already exists in analog sizing: DNN-Opt's critic takes a design and a delta and predicts the resulting specifications, trained on the roughly N-squared pseudo-samples formed from all pairs of evaluated designs, and it selects which candidate to simulate. That is a change model used as a ranker. What it does not do, and what no circuit paper found does, is measure the model's response fidelity against the simulator or relate it to search cost. The thesis's claim is therefore about the measurement, not about the object, and v9's remark that no prior change-prediction model exists inside circuits is withdrawn (§9). The combination that does appear unoccupied is a language-model proposer with a learned ranker gating expensive physical checks.

### 5.1 Fixed definitions

**Episode.** A triple (design, layout policy, specification) drawn from claim 1's database, where the design passes cell 0 and fails cell PCM under that policy. Each episode carries claim 1's diagnosis: the limiting property at PCM, the cell at which it first failed, the per-property pre-versus-post deltas, and the worst corner.

**Episode set.** 60 episodes over claim 1's four failure classes (parasitic-sufficient, corner-sufficient, mismatch-sufficient, interaction-only), spread across families, generators and both policies, with the allocation fixed by a seeded draw and pre-registered.

**Drawn and frozen at month 6, not at month 30.** v1 drew it at months 30 to 32 while training the rankers from months 6 to 30, out of the same claim 1 database — which made the exclusion rule retroactive and would have required retraining all twelve rankers. Claim 1 emits the frozen `episodes_v1` table when the database is tagged at month 6 (claim 1 plan §13), and claim 2 honours its hold-out flag from month 6 onward.

**The exclusion radius is set by counting, not by choosing the strictest rule available.** v2 excluded every design from the same optimiser run **or the same topology-and-specification cell**. The second half is far stronger than deduplication and can be catastrophic: with roughly thirteen to eighteen distinct topologies and 60 episodes spread across families, generators and both policies, excluding whole topology-and-specification cells could remove most of claim 2's training data — and nothing in v2 checked. The rule in v3:

1. **Always excluded:** the episode design itself, all its physical results, and every design from the same optimiser run (which produces genuine near-duplicates of it).
2. **Excluded by distance, not by cell:** any design within a pre-registered log-sizing distance of an episode design on the same topology and context. The threshold is set at month 6 from the measured near-duplicate distance distribution, not guessed.
3. **Counted before freezing.** The month 6 tag reports the retained training and evaluation counts per topology under the chosen radius. If any topology retains too little to train on, the radius shrinks or that topology contributes no episodes, and the decision is recorded. Freezing a split without knowing what it leaves behind is how a study discovers at month 12 that it has no data.
4. **The reserved pool is larger than the episode set.** 120 designs are reserved and flagged, and the 60 episodes are drawn from within them, so that if the month 28 power simulation calls for more episodes they can be added without touching a design any ranker was trained on. v2 reserved exactly 60, which would have made any increase impossible.

**The allocation follows the observed stratum counts, not a round number.** v1 assumed 15 apiece. The `interaction-only` stratum requires designs that pass P, C and M individually and still fail PCM, and there is no reason to expect fifteen of them; if parasitic failures dominate it may be near-empty. Claim 1 reports the four counts at month 6 and the allocation is set from them, once, and recorded. A stratum yielding fewer than eight episodes is dropped from the failure-class fixed effect in §5.4 rather than padded, and the paper says which strata the result covers. The 8-to-4 mapping from claim 1's eight-class decomposition is fixed in claim 1 plan §1 rather than improvised here.

**Actions.** Two sets, run as separate conditions and also jointly:

- *Continuous.* A change in the continuous parameter vector `x` of §2.7, bounded to 0.3 decades per device per step, range-checked and **grid-quantised** — not snapped to a model bin — with the realised displacement, the quantisation distance and the identified bin recorded. v2's text here still said "snapped to model bins", which contradicted its own correction; this is the executable rule and it now matches §2.7.
- *Finger.* A change of plus or minus one or two fingers on any device, subject to the matched-pair constraints of the topology, applied through the finger override of §3.2.

  **Gated on training support.** Claim 1's finger rule makes finger count a deterministic function of topology and sizing, so across the primary population finger count is perfectly collinear with sizing and a model trained on it has never observed a finger response. The finger action set therefore depends on the **finger-variation set** of claim 1 plan §1 — 300 designs at two to four alternative valid assignments, at stage 0 and cell P under both policies. If that set is harvested, the finger conditions run. If it is cut, the finger action set is cut with it and the utility paper reports continuous moves only, saying why. v1 made finger moves a headline action set with no training data anywhere in the thesis that could support ranking them.

Placement is not an action. Predicting the effect of a placement move needs the layout as a model input, which is a different model, and the exclusion is stated rather than assumed.

**Cheap check.** One stage-0 simulation of a candidate. Allowed to every method, counted separately, never the headline currency.

**Expensive check, as a ladder.** A candidate that survives the cheap check is laid out under the episode's policy, LVS'd and extracted, then evaluated on a ladder that stops at the first failure:

1. extracted netlist, **the episode's** worst corner, nominal devices: 1 simulation. **Rung criterion:** the candidate meets every constraint at that corner. This rung uses the starting design's corner deliberately — it is a cheap screen that is allowed to be wrong, not the endpoint, and §2.7 re-derives the corner for certification.
2. extracted netlist, same corner, 20 chips: 20 simulations. **Rung criterion:** the upper end of the calibrated interval of claim 1 plan §1 is at or above Y\* = 0.90 — that is, the rung rejects only candidates the 20 chips can *exclude* from acceptability, not every candidate that fails to demonstrate it.

v1 gave the ladder no rung criterion at all, and the obvious reading — 18 of 20 chips must pass — would reject a candidate at true yield exactly 0.90 about a third of the time, since `P(X >= 18) = 0.677` for `X ~ Bin(20, 0.9)`. Screening a candidate out on 20 chips is a decision made on a standard error of 0.067, and the ladder exists to save money, not to make acceptance decisions. The one-sided rule above puts the noise on the side of spending an extra check rather than discarding a good repair, and the realised rejection rate at each rung is reported.

A candidate that survives the ladder is a **provisional pass** and is submitted to `CERTIFY` (§2.7): its own 29-corner nominal scan, its own worst corner, then the mismatch test under claim 1's selected endpoint. v2 wrote the accept criterion as "extracted, worst corner, 50 chips" while the ladder's corner was the *episode's* corner, so as written it did not re-derive the corner and did not run the nominal scan — it was not the claim 1 endpoint, only a description of one. §2.7 is now the single executable definition and this section calls it.

The cost of that correction is real and is in §5.5: a certification is 29 nominal simulations plus 50 to 250 mismatch draws, about 1.3 core-hours rather than the 0.83 v2 assumed.

**An episode is solved when a candidate is *confirmed*, not when one is first certified.** The accepted candidate is the survivor of many noisily screened ones, so its certification is upward-biased by selection. v2 stopped the loop at first certification and reported an independent confirmation afterwards, which measures *time to preliminary certification plus a confirmation rate* — a legitimate quantity, but not the one the claim names. In v3:

- A certified candidate is re-evaluated once on a **fresh independent mismatch sample** (200 draws, new seeds) at its own worst corner.
- If the confirmation passes, the episode is **solved** and the check count is recorded.
- If it fails or is indeterminate, **the loop continues** from the next round, carrying the failed confirmation into the proposer's history, and the confirmation cost counts against the budget.

The primary outcome is therefore **checks to confirmed accept**. Checks to first certification, and the confirmation rate, are reported as named secondary quantities so that both are available and neither is mistaken for the other.

**Shortcut validity on repaired designs** is not inherited from claim 1 (§2.7): 40 repaired candidates reaching `CERTIFY` are re-run at all-corner mismatch, because a shortcut validated on claim 1's designs is not automatically valid after a repair, least of all after a finger change.

**Cost.** The primary currency is the number of expensive checks. The secondary currency is simulator seconds, because the ladder makes checks unequal and because a method that fails early cheaply should not be penalised for it. Both are reported; the pre-registered headline is the number of checks.

**Budget and censoring.** 25 expensive checks per episode. Episodes not solved within the budget are **right-censored, not dropped**. Censoring is expected to be common, and treating unsolved episodes as missing would bias every comparison toward methods that fail fast, so the analysis in §5.4 is a survival analysis from the start.

**Model-management strategy.** The number k of top-ranked candidates that pay for an expensive check per round, k in {1, 2, 4}. This is a controlled factor rather than a fixed choice, because the one controlled study of surrogate accuracy against optimiser performance found that whether accuracy matters at all depends on the management strategy.

### 5.2 The loop

Per round, for the model-guided method:

1. **Diagnose.** From the verdict stage: the limiting property, the failing cell, the measured shortfall in the property's own units, and the per-property pre-versus-post deltas. Rendered as a sentence, for example "extracted parasitics cut unity-gain bandwidth by 35 per cent; phase margin unchanged".
2. **Propose.** A language model receives the netlist, the diagnosis, the action space with its bounds, the device operating regions at the last evaluated point, and the full history of previous proposals with their measured outcomes, and returns 16 candidate repairs with a one-line reason each. The prompt structure follows what the published language-model sizers actually do: operating regions and previous best designs as few-shot context, explicit instructions about the direction and size of the correction, and a re-request on malformed output.
3. **Screen.** Each candidate gets one cheap check. Candidates that fail the geometric or bin checks are discarded and counted.
4. **Rank.** The change model predicts, for each surviving candidate, the change in every property at the endpoint cell, and the candidates are ordered by predicted worst-property margin there.

   **What "the property at the endpoint cell" means, since a stochastic cell has no single property vector.** v2 left this undefined, which leaves both the ranking objective and the feasibility calibration undefined with it. The target statistic is fixed here: for each property, the model predicts the **nominal value at the candidate's predicted worst corner** and the **standard deviation induced by mismatch**, the latter from the propagation machinery of §4.6. The ranking score is the predicted margin at a pre-registered quantile — `m_i` evaluated at `nominal - k·sigma_i` with `k = 1.28`, the 90th-percentile point matching Y\* = 0.90 — minimised over constrained properties. The **limiting property under mismatch** is the argmin of that quantile margin, which is a different and more appropriate quantity than the argmin of the nominal margin, and it is what claim 3's primary regressor uses.

   Feasibility calibration is then well posed: the model's implied pass probability is the predicted joint probability that every constrained property clears its threshold, computed from the predicted means and the propagated covariance of §4.6, and the Brier score is taken against the certified verdict. Arms without offset supervision cannot produce `sigma_i` and are scored on nominal margins only, with that limitation stated wherever they appear.
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

**Claim 3 is two linked studies, not one.** v1 tried to isolate the ranker inside the closed loop, which cannot work: each ranker steers its own proposer history (§5.2 step 6), so rankers face different candidate streams and are never compared on common candidates; and the Kendall tau that was to mediate the effect was computed only on candidates the ranker itself had promoted, which is exactly the wrong sample for judging screening quality. v2 separates the two questions.

**Study 3A, the fixed-candidate ranking study — isolates the ranker.** For each of 60 episodes, a **common candidate batch** of 16 proposals is generated once, by the proposer with no ranker in the loop, and every candidate in it is evaluated to a **common numerical score**. Every ranker then scores the same batch offline.

**"Fully evaluated" means no early exit, which v2's wording did not deliver.** v2 said the batch was fully evaluated "through the ladder and the accept criterion", but the ladder stops at the first failing rung. A candidate rejected at rung 1 would have an endpoint verdict and no property vector, so two rejected candidates would be mutually unordered and the promised "simulator's true ordering" would not exist. In 3A the ladder's performance-based early exits are **bypassed**: every candidate with a valid layout is carried through the full `CERTIFY` specification of §2.7 and yields the complete property vector and margin at the endpoint, whatever its verdict. That is what makes the ordering real, and it is why 3A costs what §5.5 now says it costs rather than what v2 said.

**Candidates that cannot be scored get an explicit bottom category.** A candidate failing structurally — geometric rejection, no valid bin, DRC, LVS, extraction — has no margin and is not given a fabricated one. It is assigned to a bottom class, **tied** with the others in it, and the rank statistics use a tie-aware coefficient (Kendall tau-b) with the tie count reported. A ranker that correctly puts structural failures last is credited for it; none is credited for ordering within the tie.

**Ordering under Monte Carlo noise needs a tie rule even after full evaluation.** The endpoint margin is estimated from finite draws, so two candidates whose intervals overlap are not reliably ordered by the simulator either. The "true" ordering is therefore a **partial order**: candidates whose calibrated margin intervals overlap are treated as tied, and tau-b is computed against that partial order. The fraction of pairs that are tied is reported per episode, because an episode in which the simulator itself cannot separate the candidates cannot discriminate between rankers, and it should be visible when that happens rather than diluting the estimate silently.

Outcomes: tie-aware ordering agreement against the partial order on the whole batch, top-k regret at k in {1, 2, 4}, feasibility calibration, and detection rate of at least one certifiable candidate. No selection bias, no candidate-distribution differences between rankers, and no layout regeneration per ranker — the expensive evaluation is paid once and amortised across all twelve. This is where the relation between response fidelity and screening quality is measured.

**Study 3B, the closed-loop utility study — measures realised cost.** The loop of §5.2, with a reduced ranker set (see below), measuring checks to accept under censoring. This is where the practical question is answered: does a better ranker actually save expensive checks in a live loop, against the baselines.

3A carries the mechanism; 3B carries the utility. v1 asked one under-powered experiment to carry both.

**Rankers.** Twelve rankers from claim 2, chosen before any episode runs to span the error range: arms A, B and B-S at each of three pre-registered combinations of dataset size and selection strategy, which is nine; plus two constructed-shortcut models whose response error on one named property is bad by construction; plus one model degraded by label noise, to extend the range upward. Each carries, measured on held-out designs of the same family at the physical cells: response error per property, response error on the episode's limiting property, **limiting-property value error, local value error** (§4.1), ordering agreement, Jacobian cosine agreement, and aggregate accuracy.

All twelve run in study 3A, where they are cheap.

**Study 3B runs six, selected by a rule that guarantees they are distinct.** Ordered by measured limiting-property response error, 3B takes the natural rankers at ranks 1, 5 and 9 of the nine (the two extremes and the median), plus **the natural ranker with the best 3A top-k regret among the remaining six**, plus one constructed-shortcut model and the noise-degraded model. That is **four distinct natural rankers and two manufactured**, and the selection cannot collapse — v2 said "the extremes and midpoint ... plus the best natural ranker", which could and probably would have duplicated an extreme, leaving three.

**Natural and manufactured rankers are analysed separately, always.** Three of the twelve are deliberately corrupted, and §5.8 says outright that they exist to widen the error range. They will sit at the extreme of the x-axis and would dominate any fitted slope, so a relationship driven by them would establish behaviour under controlled corruption and nothing more. **In study 3A**, where all twelve are available, every fit is reported twice: on the nine natural rankers alone, which is the result that speaks about models anyone would train, and on all twelve, which speaks about the mechanism across a manufactured range. Where the two disagree, the natural-only fit is the headline and the disagreement is the finding.

**Study 3B cannot support those fits and no longer claims to.** With four distinct natural rankers, a regression carrying several correlated fidelity measures, multiple covariates, ranker random effects, a free breakpoint and interactions has almost no model-level generalisation evidence behind it, whatever a power simulation says about episode-varying coefficients. v2 promised "nine natural" and "all twelve" fits without noticing that 3B has neither. The two studies therefore get **separate analysis specifications**, and the division of labour is explicit:

- **3A carries the model-quality association.** The relation between fidelity measures and ranking quality is estimated there, across twelve rankers, 60 episodes and 960 fully evaluated candidates, where the covariate range is widest and the outcome is cheapest.
- **3B carries realised utility, as a small set of preplanned paired contrasts** — not a model-selection regression. Three contrasts, fixed in the pre-registration: best natural ranker against no ranker (B1), best natural against the median natural, and best natural against the noise-degraded model. Each is a paired comparison across the same 60 episodes, analysed with a stratified survival model carrying episode random effects and **no ranker-level covariates**, because with four natural rankers there is nothing to regress on. The fidelity-versus-cost relation is *checked for consistency* against 3A's estimate and is not independently fitted.

**The minimum practically meaningful effect comes from circuit design, not from another field.** v2's power simulation had no target effect size, and transplanting one from the surrogate-optimisation literature would import that field's cost structure along with it. The target is set from what a repair loop is worth here: one expensive check under `CERTIFY` costs about 0.9 core-hours and roughly an hour of wall time on the layout queue, and a repair episode is worth automating only if the ranker saves enough checks to beat the engineer time it displaces. The pre-registered minimum meaningful effect is therefore **a 25% reduction in median checks to certified accept**, and the month 28 power simulation is run against that number rather than against a standardised effect size.

**Outcome, study 3B.** Number of expensive checks to accept, right-censored at 25.

**Primary model.** A mixed-effects survival model (accelerated failure time on the log of the check count, with a proportional-hazards fit reported alongside), with random effects for episode and for ranker, and fixed effects for: response error on the limiting property; **limiting-property value error; local value error;** aggregate accuracy; initial margin shortfall; failure class; family; action set; and k.

**Primary test.** A nested comparison: does the limiting-property response error add predictive power **over the task-matched value comparators**, not merely over global aggregate accuracy? v1 tested only the latter, and since the two quantities differ in three ways at once — response versus value, limiting-property versus all-property, local versus global — a win would not have said which difference did the work. Reported as a likelihood-ratio test, a difference in information criterion, and a leave-one-ranker-out cross-validated concordance. The reverse nesting is reported too.

**Leave-one-ranker-out is a weak instrument and is labelled as one.** Rankers built from one skeleton, one codebase and overlapping data are not independent, so a training fold that omits one still contains near-identical training conditions. It is reported alongside a **leave-one-training-condition-out** split, which holds out all rankers sharing a dataset size and selection strategy together, and a **leave-one-topology-group-out** split on the episode side. Where these disagree with leave-one-ranker-out, the more conservative is the headline.

**Prospective power simulation, month 28, before any episode runs.** The survival model is simulated at plausible effect sizes with realistic ranker-level clustering, the expected censoring rate from the month 32 pilot's predecessor, and the planned 60 episodes by 6 rankers, and the minimum detectable effect is reported. If the design cannot detect an effect of the size the surrogate-accuracy literature reports, that is known at month 28 — when the episode count, ranker count and budget are still changeable — rather than at month 42. v1 had no power analysis anywhere, only a risk paragraph.

If aggregate accuracy survives and per-property error does not, that is the answer to claim 3 and is reported as plainly as the other direction.

**Pre-registered alternative shapes.** Two, both fitted and compared before looking at which is prettier:

- *Saturation.* Cost improves with fidelity up to a threshold and then flattens, as the controlled surrogate study found above accuracy 0.7 to 0.8. A piecewise-linear fit with a free breakpoint is fitted alongside the linear one.
- *Strategy dominance.* The management strategy k explains more than any fidelity measure, which is what that same study found for one of its three strategies, and what the self-calibrating sizing paper concluded when it attributed convergence to the feedback architecture rather than to prediction accuracy. The k main effect and its interaction with fidelity are in the model from the start.

**Secondary, mediation.** The rank correlation, Kendall tau, between the ranker's ordering and the simulator's, computed **on study 3A's fully evaluated common batches**, not on the candidates a ranker promoted inside its own loop. v1 computed it "on every round where at least four candidates were eventually evaluated", and since candidates are evaluated only when the ranker puts them in its top k, that is range restriction by construction: the discarded candidates are precisely the ones that reveal screening quality. Study 3A exists so that this metric has an unbiased sample.

Whether tau from 3A mediates the relation between response error and 3B's check count is a pre-registered secondary question, and it is **exploratory**: mediation requires causal assumptions — no unmeasured confounding between mediator and outcome, correct ordering, no interaction — that this design does not establish, so the result is reported as a decomposition of association and labelled as such. If tau mediates, the mechanism is clean; if per-property error predicts cost while tau does not, that is a finding about which errors matter.

### 5.5 Compute

**Unit costs, from one set of rules applied everywhere.** At 60 s per extracted simulation, 60 s layout and 30 s extraction:

| Unit | Contents | Core-hours |
|---|---|---:|
| Ladder check | layout, extraction, 1 to 21 simulations (11 average with early exits) | 0.21 |
| `CERTIFY` (§2.7) | layout, extraction, **29-corner nominal scan**, 50 mismatch draws | 1.34 |
| `CERTIFY`, escalated | as above with 250 pooled draws | 4.68 |
| Confirmation | 200 fresh draws at the certified candidate's worst corner, no relayout | 3.33 |

v2 costed a certification at 0.83 core-hours by counting 50 chips and nothing else. The 29-corner nominal scan is part of the endpoint (§2.7), and it was missing.

| Item | Count | Core-hours |
|---|---:|---:|
| **Study 3A**: 60 batches × 16 candidates, each through full `CERTIFY` with **no early exit** | 960 | 1,288 |
| **Study 3B** (6 rankers) + 6 baselines, ladder checks, at a 55% early-stop realisation | ~9,900 of 18,000 | 2,062 |
| **Certification attempts** — every provisional pass, not every solved episode | ~1,584 | 2,125 |
| **Confirmations** of certified candidates, 200 fresh draws | ~648 | 2,160 |
| Shortcut re-validation on 40 **repaired** candidates at all-corner mismatch (§2.7) | 40 | 968 |
| k sweep and action sets, 8 conditions on a 20-episode subset | ~4,000 | 833 |
| Proposer diagnostic, all 16 candidates in 10 episodes | 160 | 215 |
| **Scenario total** | | **about 9,650** |
| **With 40% contingency** for tail runtimes, failed jobs and escalations to 250 draws | | **about 13,500**, roughly 18 days wall on 32 cores |

**What the recheck found wrong in v2's table, and what each correction cost.**

- *Confirmations were understated by a factor of five.* v2 printed 270 core-hours for 400 confirmations of 200 chips. That is 80,000 simulations, which at 60 s is **1,333 core-hours**, and the count was wrong too — confirmations follow certifications, not solved episodes.
- *Study 3A was costed as if candidates were cheap checks.* v2 printed 360 core-hours for 960 candidates. Fully evaluating a candidate to a common score means running `CERTIFY` on it, which is 1,288 core-hours; even 50 chips alone with no corner scan would have been 800.
- *Certification attempts were confused with solved episodes.* v2 multiplied an assumed 35% solve rate by an accept cost. Every provisional pass incurs a certification, including those that fail or come back indeterminate, so the attempt count is roughly `methods × episodes × attempts-per-episode`, not `solved episodes`.
- *v2's printed rows summed to 9,820 against a stated total of "about 9,800"* — arithmetically consistent, which is how the individual errors survived: a correct total over wrong rows.

The total lands close to v2's figure by coincidence, not by cancellation: the corrections above add roughly 4,700 core-hours, and reducing study 3B from twelve rankers to six removes roughly the same amount. The number now follows from the rules rather than being reverse-engineered to fit.

**Still scenario figures.** They assume the stated early-stop and attempt rates, 60 s per simulation, no failed jobs, and independent throughput on 32 cores. Layout, DRC and extraction are single-threaded and queue separately. Every row is a line in the experiment manifest (claim 1 plan §3), with its own counters for proposals, language-model calls, layout and extraction calls, nominal corner scans, mismatch draws, certification attempts and confirmations; all are recomputed from measured median **and tail** runtimes at month 30, including failures and retries.

Reduction ladder if it binds, in order: the k sweep drops to k = 2 fixed; action-set conditions drop to continuous only; the repaired-design shortcut check drops from 40 to 20 with the wider bound stated; study 3B's rankers cut from six to five, keeping both extremes and both manufactured models; episodes cut from 60 to 40 last. Study 3A is never cut — it is where the mechanism is measured, and per unit of evidence it is the cheapest thing in the study.

### 5.6 Figures

1. Checks to **confirmed** accept, per method, as survival curves with censoring marked, with checks to first certification drawn beside them as the named secondary quantity. The loop against all six baselines.
2. Checks to accept against response error on the limiting property, one point per (ranker, episode) with ranker means, faceted by failure class, with the fitted linear and saturating curves, and **natural rankers plotted distinctly from constructed and degraded ones**.
3. The same against each comparator: limiting-property value error, local value error, and global aggregate accuracy, on the same axes and the same scale. These figures are the claim, and the comparison that matters is against the first two, not the last.
3a. Study 3A: tie-aware ordering agreement against the simulator's partial order, and top-k regret, on the fully evaluated common batches — against response error on the quantile-margin limiting property and against each comparator. Twelve rankers, fitted on the natural nine and on all twelve. This is the ranker-isolating result and it is where the mechanism lives.
3b. Study 3A: the fraction of candidate pairs the simulator itself cannot order at the endpoint's Monte Carlo resolution, per episode. An episode above a pre-registered tie fraction discriminates between no rankers and is reported as such rather than diluted into the average.
3c. Study 3B: the three preplanned paired contrasts, as paired differences with episode-level intervals. No ranker-level regression, because four natural rankers cannot support one.
4. The nested-model comparison as a table with both directions of nesting and the cross-validated concordance.
5. Kendall tau from study 3A against response error, and the mediation decomposition, labelled exploratory.
6. Action set: continuous against finger against joint, per method.
7. k sweep: cost against fidelity at each k, testing the strategy-dominance shape.
8. Cost in simulator seconds beside cost in checks, so a reader can see the ladder's effect.
9. Confirmation rate of certified candidates against their certification pass fraction, which is the size of the winner's curse, and the number of episodes that required a second certification after a failed confirmation.
10. Ladder rung rejection rates, so a reader can see how much screening noise the loop absorbed.

### 5.7 Build order, months 30 to 42

- **Month 28.** Prospective power simulation for the survival model (§5.4), before anything is committed. Episode count, ranker count and budget are set by it.
- **Months 30 to 32.** Episode set — already drawn and frozen at month 6 (§5.1) — re-checked against the realised stratum counts. Loop harness: diagnosis renderer, proposer, screener, ranker interface, ladder, accept. Claim 3 pre-registration frozen and committed, including both studies, the ranker list split into natural and manufactured, and their measured error profiles, which are known before any episode runs.
- **Months 32 to 34.** **Study 3A on all 60 common batches** — ranker-isolating, independent of the loop harness's maturity, and the single most informative thing in claim 3 per core-hour, though no longer cheap in absolute terms now that full evaluation means full `CERTIFY` (§5.5). B1 and B6 (the cheap baselines) on all episodes; the harness's acceptance test is that B6 reproduces the qualitative behaviour its source paper reports. Pilot solve rate measured on 10 episodes (D8).
- **Months 34 to 37.** B2, B3, B5, and the B4 re-implementation with its sensitivity sweep.
- **Months 37 to 40.** Study 3B: six rankers on all episodes; the k sweep and action-set conditions on the 20-episode subset; fresh-sample confirmation of accepted candidates.
- **Months 40 to 42.** Analysis, figures, paper submitted.

### 5.8 Risks and negative results

- **The conventional approach wins.** Expected, and reported. The headline is whether response error predicted which searches went badly, not whether the loop wins. B6 in particular may beat everything, and that is a useful thing to publish.
- **Censoring dominates.** If most episodes are unsolved by every method, the survival model still works but power collapses. Mitigation: episode difficulty is stratified by initial margin shortfall as well as failure class, and a pilot of 10 episodes at month 32 measures the solve rate before the full set runs. If the pilot solve rate is below about a quarter, the budget rises to 40 checks and the episode count falls to 40, which keeps the compute constant.
- **All rankers are similar.** Then the range of response error is too narrow to regress against. The constructed-shortcut and noise-degraded models exist to widen the range on purpose, and their error profiles are known before the episodes run — but widening a range with manufactured models is not the same as finding one among natural models, and a result that holds only with them in the fit establishes behaviour under controlled corruption. That is why every fit is reported on the nine natural rankers alone as well as on all twelve (§5.4), and why a natural-only null with a manufactured-inclusive effect is written up as exactly that, rather than as a confirmation.
- **The natural range is narrow *and* study 3A shows no relation.** Then claim 3's answer is that response fidelity does not discriminate among models anyone would actually train, which is a legitimate bounded negative result provided the power simulation of month 28 says the design could have detected an effect of the reported size. If it could not, the result is inconclusive rather than negative, and the write-up says so; an inconclusive result from low power is not a doctoral contribution and pretending otherwise at month 42 is the failure mode this schedule exists to avoid.
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
- **D4, month 8. Removed as a gate.** v1 made arm B's survival conditional on its anchored-pair discrepancy exceeding a threshold. Since the exact change `D(a,b) = f(b) - f(a)` is separable, satisfies `D(a,a) = 0`, antisymmetry and cycle consistency, an accurate change model approaches those identities, and a gate demanding departure from them would discard arm B precisely when it works (§4.3). The separability diagnostics are reported as distributions; whether pairwise training buys anything is settled by comparing arms at matched resources.
- **D4a, month 8 (replacement).** Does the prospective power simulation (§4.11) say the planned seeds and cells can separate the selection strategies at plausible effect sizes? If not, seeds rise and cells fall, then, while both are still changeable.
- **D5, month 12.** Bridge gate. Supervisor's answer to question 2.
- **D6, month 18.** Is there a response gap outside the constructed sets? If not, §4.10's branch applies and claim 3 runs on the constructed sets.
- **D7, month 28 to 30.** Claim 3 power simulation, then compute recomputed from measured runtimes; the reduction ladder in §5.5 applied if needed.
- **D10, month 6.** Do claim 1's four stratum counts support the intended episode allocation? The allocation is set from the observed counts, once, and a stratum below eight episodes is dropped from the failure-class effect (§5.1).
- **D11, month 6.** Was the finger-variation set harvested? If not, claim 3's discrete action set is cut and the utility paper reports continuous moves only (§5.1).
- **D12, month 2.** Does the corner shortcut meet its predeclared tolerance on the first family? Escalation as in claim 1 plan §1; the month 4 preprint is conditional on this and on the margin and yield-labelling rules being settled.
- **D8, month 32.** Episode pilot solve rate. Below about a quarter, the budget rises to 40 checks and the episode count falls to 40.
- **D9, month 36.** Tile gate.
- **D-chip, whenever a shuttle opens with a close date in months 16 to 24.**

If the whole plan slips, Year 4 becomes Year 5 and nothing is reordered.

## 8. Pre-registration and the honesty rules

**Three pre-registration documents**, each committed to the repository and cited by commit hash in its paper, with a deviations section in the paper listing every departure:

- `prereg/claim1-preregistration.md`, month 2. Contents as in the claim 1 plan §9, plus the amendments of §3.2.
- `prereg/claim2-preregistration.md`, month 8. The property table; the margin definition imported from claim 1; the definitions of response error, ordering agreement, Jacobian agreement **with its diagonal anchor**, and the full **comparator ladder** of §4.1; arm B's **reference anchor** per topology; the skeleton including passive and source value features and the global condition token; its hyperparameter search space; the arms and their losses; the separability **diagnostics** and the fact that none of them gates; the **trained subspace `S` per topology, its dimension, its seed and the rank-reporting rule**; the probe families and the control-task construction; the description-length schedule; the **isolability rejection rule** for instrument 5; the constructed-shortcut targets and the **marginal-matching acceptance rule**; the dataset sizes, selection strategies and the **three evaluation distributions**; the size/selection/interaction estimands and the coverage-flip secondary prediction as a hypothesis; the **equal-N and equal-cost reporting rule**; the units modes; the **offset-label budget and which designs receive it**; the propagation evaluation set, its three-way decomposition and the full-covariance reporting; the power simulation's output; the figure list.
- `prereg/claim3-preregistration.md`, month 30, with the episode set frozen at month 6. **Both studies, 3A and 3B, and which questions each answers**; the episode set with its stratification and the observed stratum counts; the action sets and the finger gate; the ladder **with its per-rung criterion**; the accept criterion as claim 1's PCM; the fresh-sample confirmation rule; the budget and the censoring rule; the twelve rankers **split into natural and manufactured** with their already-measured error profiles and the rule that every fit is reported on the natural nine as well as on all twelve; the primary survival model and the nested test **against the task-matched value comparators**; the three cross-validation splits; the two alternative shapes; the mediation question labelled exploratory; the power simulation's output; the figure list.

**Before "the model failed to learn X" may be written**, all four must hold, as in v11 §5: the supervised head reaches X (the information was there); the per-family control has been run (not a capacity artefact); the control-task baseline has been subtracted (not probe flexibility); and the alternative arms have been run (not one architecture). In addition, the mechanism must be stated in advance and must make a further prediction that is then tested: shortcut learning predicts that adding coverage along the constructed shortcut direction closes the gap without adding quantity (§4.7); the conditional-mean argument predicts that a squared-error model learns no spread unless the objective or the input carries it (§4.6).

**Both directions are reported.** Every claim in §3, §4 and §5 is written so that the opposite outcome is a result: if survival is high, if the response gap is absent, if derivative supervision generalises, if propagation works, if aggregate accuracy predicts search cost as well as per-property error does, the finding is stated plainly and the thesis is the map either way.

**Nothing is pooled that the pre-registration says is reported separately**, in particular arm B-S against B at each dataset size, survival curves per generator, propagation results by arm, and claim 3's fits on natural against manufactured rankers.

**Nothing is claimed that the instruments do not license.** Probes establish decodability; response error establishes behavioural approximation error; input-space interventions establish neither internal use nor causal mediation. Where a conclusion would require a representation-level intervention this thesis does not run, it is stated as a hypothesis and named as one (§4.5).

**Every negative result is accompanied by the power it had.** A bounded null across credible settings is a contribution; an inconclusive result from low power, an unidentifiable model or a broken pipeline is not, and the difference is decided by the prospective power simulations at months 3, 8 and 28 rather than argued after the fact.

## 9. Corrections to carry into v12 and elsewhere

### 9.1 Into `phd-plan-v12.md`

**Corrections arising from the 8 September audit** (items A to J), followed by the fact-checking corrections already in v1 (items 1 to 13).

A. **§2, thesis statement.** Rewrite as a hypothesis with boundary conditions rather than an assertion. Proposed: *under specified layout and statistical process models, local response fidelity on active circuit constraints provides incremental information about repair decisions beyond task-matched value accuracy; its value depends on training coverage, action scale and proposal quality, and controlled experiments identify when it improves physical-verification efficiency and when it does not.* v11's clauses (a) "is not measured by aggregate accuracy" and (b) "is set by coverage rather than quantity" assert in advance what the experiments are meant to estimate.

B. **§3, novelty.** Drop "in circuits or elsewhere". Sobolev training targets derivatives, Tsay evaluates derivative-trained surrogates on downstream optimisation, and the model-based optimisation literature ties gradient-approximation quality to optimisation behaviour explicitly. Claim originality for the documented combination, presented as a comparison matrix (§5 of this plan). Obtain Giovannelli et al., arXiv 2311.12253; verify whether Bian and Xie, arXiv 2608.24963, exists.

C. **§1 and title, manufacturing claims.** "Survive layout and manufacturing variation" overclaims. The endpoint is model-based physical verification under the sky130 kit and this flow. §2.2 of this plan already states the discipline; the title and §1 should adopt it.

D. **§4, margins.** Add the dimensionless margin definition (claim 1 plan §1). v11 inherits an implicitly unit-dependent one through the claim 1 plan.

E. **§4, geometry.** "Sizings are snapped to model bins" is wrong. Model binning selects a model card by W/L interval; the quantisation that exists is the layout grid. Replace with the three operations of claim 1 plan §1, and record that derivatives are with respect to W and L only.

F. **§4, the propagation test.** Delete "with no per-chip training at all" as an unqualified claim. Offset sensitivity is unidentified from nominal-only data; it needs offset-derivative supervision, which is cheap but is not free (§4.6). "No dense Monte Carlo training" is the defensible version.

G. **§3 and §4, the endpoint.** Name PCM and PCM-full separately and say which is primary. Record that signoff is a conjunction of nominal pass and yield pass, and that v11's implication from nominal failure to yield failure is false in general.

H. **§4, fingers.** The finger rule makes finger count collinear with sizing across the whole population. Record the finger-variation set, without which claim 3's discrete action set has no training support.

I. **§6, timeline and §7, preprint.** Make the month 4 preprint conditional on the endpoint being defensible rather than "regardless of completeness". Add the three power simulations (months 3, 8, 28) as gates on seed counts, cell counts and episode counts.

J. **§4 and §11, populations and budgets.** State the distinct-topology count honestly (about thirteen to eighteen, not twenty to twenty-eight families), record that the headline survival contrasts are generator-pooled and family-pooled with the three-way grid in the supplement, and replace the budget figures with the manifest-derived scenario figures of §4.9 and §5.5, described as scenarios rather than upper bounds.

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
17. The sky130 manufacturing grid value in the installed technology file, and the distribution of bin clearance over the first family's devices — both needed before any derivative step is chosen (§2.3).
18. Central-difference convergence at 1%, 2% and 4% on ten designs spanning the first family's operating regimes, and the no-op perturbation rate at each step.
19. That Magic DRC runs on ALIGN and OSIRIS output against the sky130 rule deck without manual intervention, and that it flags a deliberately broken layout.
20. That netgen's device map is complete and unambiguous under multi-finger splitting and parallel-device merging, and what the split/merge factor is for a representative multi-fingered device; and the offset-aggregation rule that follows (§2.4, §2.7).
21. That the extraction flow can be made to **preserve separately instantiated devices** where §2.7 requires independent mismatch draws, and what it costs in extraction time if merging is disabled for matched pairs.
22. The realised angle between requested and grid-quantised displacement, over the first family at the working step size — the tolerance in §2.7 cannot be set until this is measured.
23. Re-run the two-stage coverage calibration of claim 1 plan §1 on the installed simulator's actual draw sequence, to confirm the enumerated coverage holds for ngspice's pseudo-random stream rather than only for the ideal Bernoulli model.

### 10.2 Before submission

- Obtain Ravichander et al., arXiv 2005.00719.
- Obtain Giovannelli et al., arXiv 2311.12253, on function, gradient and Hessian approximation and downstream optimisation. It is the prior-art item that actually constrains claim 3's novelty statement (§5) and it is not in `papers/`.
- **Closed.** arXiv 2608.24963 (Bian and Xie, *"Why and When Neural Networks Improve Local Approximation in Optimization"*, submitted 25 August 2026) exists; the record was retrieved on 8 September 2026. Obtain the full text, add it to `papers/README.md`, and read it before the claim 2 pre-registration freezes. Its treatment is in §5.
- Measure FALCON's within-topology pair density, to size the response-fidelity replication of §4.4 rather than only the probe replication.
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

## 12. Changes from v1, with the finding each answers

v1 was written on 8 September 2026 and audited the same day. All thirteen of the audit's findings are accepted; four further problems surfaced while checking it and are marked **[new]**. Nothing below is a change of description only — each alters what is measured, what is claimed, or what the study can conclude.

### Changes that alter what is measured

1. **Margin is dimensionless** (F10). `s_i log10(x_i/t_i)` for ratio-scale properties, `s_i (x_i - t_i)/Δ_i` with a pre-registered scale for signed and zero-threshold ones. v1's normalise-after-log composition differed by a factor of 7.6 between log10(Hz) and log10(MHz) on a representative bandwidth, and the limiting property is its argmin — so the identity of the limiting property could flip on a unit change. It drives claim 1's τ axis, claim 3's stratification, claim 3's ranking objective and claim 3's primary regressor. §3.1, §4.1, claim 1 plan §1.

2. **Derivative supervision is confined to a rank-deficient subspace, and instrument 6 evaluates on its orthogonal complement** (F3). v1 said both that B-S trains on a fixed 40% dictionary and that it trains on fresh uniform random projections each epoch. Those are mutually exclusive, and under the second, instrument 6 measures nothing. Even the dictionary rule withheld nothing, since roughly 29 trained directions generically span a 20-to-35-dimensional space and directional derivatives are linear measurements of the gradient. Rank and conditioning are now reported at every design, and arm **B-S-full** measures what the restriction cost. §4.3, §4.5.

3. **Passive values, source values and testbench context are model inputs** (F6). v1's node features gave every device width, length and multiplicity and gave passives no value at all, so the model could not distinguish two designs differing only in the compensation capacitor — on three of OSIRIS's five circuits, and on exactly the properties claim 1 reports as failing after layout. A global condition token carries supply, load, temperature, corner, testbench and layout policy. §4.2.

4. **Offset-derivative supervision is a precondition of the propagation test** (F7). From nominal-only data, `fhat(x,z)` and `fhat(x,z) + a(x)·z` fit equally well, so `∂fhat/∂z` is arbitrary. Three arms now separate nominal-only (control), offset-derivative-supervised (the test) and sampled-offset (the alternative route). The label budget is costed. "No per-chip training" survives only in its true sense: no *dense Monte Carlo* training. §4.6, §4.9.

5. **The propagation test reports the full covariance `J_z J_z^T`, not only its diagonal** (F7). Marginal spreads do not give joint multi-specification yield; the off-diagonals are free once `J_z` is computed. Where the Gaussian-orthant joint estimate is validated the result speaks about yield; where it is not, it is scoped to per-property spread. §4.6.

6. **Model bins are separated from the layout grid; derivatives are with respect to W and L only** (F5). Nothing is snapped to a bin — binning is model selection over W/L intervals, not geometry quantisation. Multiplicity leaves the continuous design vector (a 2% step in `log10` of an integer that goes 1, 2, 3 is meaningless). Step size is checked against grid, bin clearance and convergence, the last on ten designs per family rather than one. §2.3, §4.1, claim 1 plan §1.

7. **The accept criterion is claim 1's PCM, not PCM-full** (F8). v1 used one name for two endpoints: claim 1's signoff cell is worst-corner Monte Carlo, while claim 3's accept criterion was written as all 29 corners. PCM is primary; the worst-corner shortcut is validated once in claim 1 against a predeclared 38-of-40 tolerance with an escalation rule. This is also what makes claim 3's budget close — 50 simulations per accept run against 1,450. §3.1, §5.1, §5.5.

8. **The ladder's 20-chip rung has a stated criterion** **[new]**. v1 gave none. The obvious reading, 18 of 20, rejects a true-0.90 candidate a third of the time (`P(X≥18) = 0.677`). The rule is one-sided — reject only what 20 chips can exclude — and rung rejection rates are reported. §5.1.

9. **A finger-variation set is harvested, and the finger action set is gated on it** (F6). Claim 1's finger rule makes finger count a deterministic function of sizing, so no training design anywhere in v1 carried a finger response, while claim 3 made finger moves a headline action set. §5.1, claim 1 plan §1.

### Changes that alter what can be claimed

10. **Claim 3 is split into a fixed-candidate ranking study (3A) and a closed-loop utility study (3B)** (F11). In v1's single closed loop each ranker steered its own proposer history, so rankers were never compared on common candidates, and Kendall tau was computed only on candidates the ranker had itself promoted — range restriction by construction. 3A fully evaluates a common 16-candidate batch per episode once and amortises it across all twelve rankers. §5.4, §5.5, §5.7.

11. **Natural and manufactured rankers are analysed separately, always** (F11). Three of twelve are deliberately corrupted and sit at the extreme of the x-axis; a slope driven by them establishes behaviour under controlled corruption, not a rule for models anyone would train. Every fit is reported on the natural nine and on all twelve. §5.4, §5.8.

12. **The comparator is task-matched, not the weakest available** (F10). Limiting-property response error is now tested against limiting-property *value* error and local value error as well as global aggregate accuracy, because those three differ along three axes at once and v1 could not have said which did the work. §4.1, §5.4.

13. **Arm A's response error is identified as a functional of pointwise error** (F10). For arm A and the supervised head, `Dhat - D` is identically the difference of two pointwise errors, so only the pairwise arms can carry a mechanism that accuracy does not already determine. Stated in the definition and in every caption. §4.1.

14. **Sign agreement is demoted; ordering agreement is what a ranker consumes** (F10). v1 called sign agreement "what a ranker actually needs"; in a repair loop most surviving candidates improve the limiting property, so their signs agree and the statistic is constant across them. §4.1.

15. **The non-separability gate is removed; D4 is withdrawn** (F2). The exact change `f(b) - f(a)` is separable and satisfies reflexivity, antisymmetry and cycle consistency, so a gate demanding departure from those identities rewards approximation error. The diagnostics are reported as distributions. The all-pairs loss algebra is corrected: it reduces to the *centred* single-point loss scaled by 2N, leaving a constant offset unidentified — a second reason arm B needs an explicit anchor. §4.3, §7.

16. **Arm B's absolute prediction and Jacobian anchor are defined** (F2). A per-topology reference design supplies absolute values so aggregate accuracy is computable for the pairwise arm; the Jacobian is the diagonal derivative with respect to the second argument. v1 left both undefined while plotting arm B against aggregate accuracy. §4.1.

17. **The "read versus use" framing is withdrawn** (F4). Probes establish decodability; response error establishes behavioural error; every intervention here acts on inputs, not on representations. Behavioural response fidelity is the primary construct and the causal reading is named as a hypothesis. Instrument 4 splits into frozen-backbone and full-retrain variants, which certify different things. §4.5.

18. **Instrument 5 checks that isolating directions exist before constructing them** (F4). With a dozen coupled properties on twenty-odd parameters, the component of one property's gradient orthogonal to the others can be numerical noise. A pre-registered rejection rule (10% of gradient norm, condition number below 10⁴) excludes ill-conditioned cases, and a property excluded on most designs is reported as not isolable in that family. Residual co-movement is disclosed, not only regressed out. §4.5.

19. **Coverage versus quantity estimates effects rather than requiring one** (F12). v1 said "the claim needs the size axis flat"; there is no general reason it must be, and v1's own expectation that accuracy improves with size sits badly beside it. Size effect, selection effect and interaction are estimated with intervals, on three named evaluation distributions, reported at equal design count *and* equal simulator cost. §4.4.

20. **Rejection sampling is marginal-matched and its residual shift is reported** (F12). Rejecting to a target correlation reshapes marginals, density and support, so a gap between the shortcut set and its control is not automatically the shortcut's doing. §4.7.

21. **FALCON supports a response-fidelity replication, not only probes** (F12, evaluation addendum). Within-topology pairs in the stored dataset give `f(b) - f(a)` with no simulator. What is lost is control over direction and step; what is gained is response fidelity on a closed 45 nm process. §4.4.

22. **The novelty statement is narrowed to a documented combination** (F1). "In circuits or elsewhere" is dropped; a comparison matrix replaces the absence claim; Giovannelli is to be obtained and the audit's Bian and Xie citation is to be verified. `papers/README.md` already stated the gap this narrowly. §5, §9.1, §10.2.

### Changes that make the design enforceable

23. **The episode set is drawn and frozen at month 6** **[new]**. v1 trained the rankers months 6 to 30 and drew the episode set at month 30, from the same database — making the exclusion rule retroactive and requiring all twelve rankers to be retrained. §1 rule 3, §5.1, claim 1 plan §13.

24. **Exclusion is by run and topology group, not by design id** (F13). Trajectory designs from one optimiser run are near-duplicates of that run's final design. §1 rule 3, §3.1.

25. **Stratum supply is a measured number and the 8-to-4 mapping is explicit** (F8, plus **[new]** on supply). Claim 1's decomposition has eight classes; claim 3 draws from four. The `interaction-only` stratum may be near-empty, so the allocation follows the observed counts and a stratum below eight episodes is dropped rather than padded. §5.1, claim 1 plan §1.

26. **Three prospective power simulations, at months 3, 8 and 28** (F11, F13). v1 had none — only a risk paragraph saying power might collapse. Each runs while the counts it governs are still changeable. §4.11, §5.4, claim 1 plan §2 and §4.

27. **Leave-one-ranker-out is supplemented by leave-one-training-condition-out** (F11). Rankers sharing a skeleton, codebase and data are not independent, so omitting one leaves near-identical conditions in the training fold. §5.4.

28. **Mediation is labelled exploratory** (F11). Its causal assumptions are not established by this design. §5.4.

29. **An independent DRC stage, and a device map that may be one-to-many** (F13). A layout tool's claim to respect design rules by construction is exactly the tool-reported success this thesis exists to check. v1's one-to-one map requirement would have failed valid multi-finger layouts, and the offset-aggregation rule that follows matters physically, since mismatch scales as `1/sqrt(l·w·mult)`. §2.4, §3.1.

30. **Signoff is a conjunction with a measured escape rate** (F8). v1's "a nominal failure cannot reach a 90% pass fraction" is false in general — a property distributed as z² against a lower bound of 0.01 fails at nominal while 92.0% of chips pass. A 200-design subsample measures the rate rather than assuming it is zero, and unmeasured cells are labelled `not measured`. §3.1, claim 1 plan §1.

31. **Yield labels are three-valued and the near-threshold rule is stated correctly** (F9). A constant has no Wilson interval; the rule is that the *sample's* interval contains Y\*. At true yield 0.9 the standard error is 0.042 at 50 chips, so the indeterminate band is where the study lives. Numerical failures have a status policy. Accepted candidates get a fresh-sample confirmation against the winner's curse. §3.1, §5.1, claim 1 plan §1.

32. **Budgets are scenario figures derived from an experiment manifest** (audit §3). v1's claim 3 table allocated about 1,100 core-hours to a line requiring several thousand, and omitted GPU fitting entirely — 180 fits before headline seeds, capacity controls, units modes and folds. The manifest is built in month 1, budgets are recomputed from measured median and tail runtimes including failed jobs, and nothing is described as an upper bound that is not one. §3.1, §4.9, §5.5.

33. **Claim 1's replication is rebalanced onto contrasts the data can carry** (F13). Ten designs per (generator, family, policy) cell cannot support v1's headline figure. Headline contrasts are generator-pooled, family-pooled and the paired policy gap; the three-way grid moves to the supplement with its n printed; inference is hierarchical and the paired policy comparison uses McNemar rather than a two-proportion test. §3.1, claim 1 plan §2 and §7.

34. **The month 4 preprint is conditional on the endpoint being defensible** (audit §4). "Regardless of completeness" is the right instinct against the scoop risk and the wrong rule when the incomplete part is the validity of the headline endpoint. §7 D12, claim 1 plan §4.

### What was considered and not changed

- **The gated items.** The audit recommends removing the compact-model bridge, the crossbar tile and the chip from the committed workload. They are already outside the spine, each with a gate, a fallback and a cut date, and §1 rule 6 already states that all three claims stand if all three are cut. No change.
- **Narrowing to three or four topologies.** The audit's minimum-defensible-scope recommendation pulls against its own F13, which objects that the topology population is too narrow for the generalisation claims. The reconciliation is that they are different claims: claim 1's population-survival headline needs breadth and is what F13's power argument bites, while claims 2 and 3 need depth and can start narrow. Claim 2's month 6 to 12 work therefore begins on three or four topologies as the audit suggests, and claim 1 keeps its population, rebalanced as in item 33. Cutting claim 1 to four topologies would remove its contribution rather than repair it.

## 13. Changes from v2, with the recheck finding each answers

v2 was rechecked on 8 September 2026 (`phd-plan-recheck-v12-2026-09-08.md`). **Every numerical claim in that recheck was reproduced independently before any of it was applied**, and every one held: the two-stage coverage figures to six decimal places (0.927729 at p = 0.90, 0.930765 at p = 0.88), the Wilson interval for 38/40 (83.5%–98.6%), the one-sided bounds at zero events in 40 and 200 (7.2% and 1.49%), and each budget row. The textual findings were checked against the files and all were present. The findings are therefore accepted in full.

### Blocking findings

1. **One canonical endpoint, executed rather than described** (R1). v2's claim 3 ladder used the *starting episode's* worst corner and then "accepted" on a corner it never re-derived, with no nominal 29-corner scan on the candidate being certified — so it did not implement claim 1's endpoint, it described one. A sizing change can move the worst corner. §2.7 now holds a single `CERTIFY` specification that re-derives the corner and includes the nominal scan; the episode's old corner survives as a cheap screening rung that is allowed to be wrong. The endpoint claim 1's validation selects — PCM or, on escalation, all-corner — is a **value recorded in the month 6 tag and read by claims 2 and 3**, not a constant written independently into three documents. Shortcut validity is re-checked on 40 *repaired* candidates, because a shortcut validated on claim 1's designs need not hold after a repair, least of all a finger change. Cost: about +0.5 core-hours per certification, in §5.5.

2. **The yield procedure is made valid, not merely pre-registered** (R2). Pre-registering an adaptive rule does not make its selected interval a confidence interval, and v2's did not: enumerated coverage 0.9277 at p = 0.90 against a nominal 0.95, because at p near the threshold a covering stage-1 interval is discarded by construction. Two structural fixes, both checked by enumeration: draws are **pooled** (250, not 200), and the critical value is **calibrated to the whole procedure by simulation** over a pre-registered grid, with the realised coverage curve published. Inflating the critical value alone does not rescue the discard rule — its worst case plateaus below 0.95 — but with pooling, z ≈ 2.40 reaches 0.9685. A time-uniform confidence sequence is the named fallback. Claim 1 plan §1.

3. **Numerical failures become bounds, not exclusions** (R2). v2 dropped non-converging chips from numerator and denominator, silently estimating yield *conditional on convergence* — and non-convergence correlates with the marginal circuits the study is about. 92 passes with 8 unresolved is not a 100% pass fraction; it is [0.92, 1.00]. Reproducible retries first, then interval bounds, with the unresolved fraction reported as a figure. Claim 1 plan §1.

4. **Indeterminate labels enter every analysis** (R2). v2 retained them and drew them as a band, leaving the decomposition, the predictor and the inference binary — which made the band decoration and meant the plots measured certification outcomes rather than underlying yield. Now: bracketing survival curves, decomposition denominators with an exclusion count and a bounds fallback above 15%, a predictor trained on definite labels with the indeterminates as a calibration diagnostic, and a censored likelihood in the hierarchical model. Claim 1 plan §1.

5. **Study 3A's "fully evaluated" is made real** (R4). v2 promised the simulator's true ordering of all sixteen candidates while routing them through a ladder that stops at the first failing rung — so two rejected candidates would have been mutually unordered and the promised ordering would not exist. Performance early exits are now bypassed in 3A; structural failures get an explicit tied bottom class; and because endpoint margins are estimated from finite draws, the "true" ordering is a **partial order** with overlapping candidates tied, scored with a tie-aware coefficient and the tie fraction reported per episode. §5.4.

6. **Checks to *confirmed* accept is the primary outcome** (R2). v2 stopped the loop at first certification and reported confirmation afterwards, which measures time to preliminary certification plus a confirmation rate — a legitimate quantity, but not the one the claim names. The loop now continues after a failed or indeterminate confirmation, and both quantities are reported under separate names. §5.1.

### High-priority findings

7. **Arm A is restored as a scientifically relevant model** (R7). v2 overcorrected the audit's F10 into "only B and B-S can carry a mechanism". Response error is a functional of the pointwise error **field**, not of any scalar **summary** of it: a constant-bias predictor has large value error and exactly correct responses; an oscillatory error with the same mean-squared value error has poor ones. The fidelity-versus-summary-accuracy question is therefore live for arm A, and the mechanism to name is **local error structure** relative to the action scale. Arm A also now receives the same reference-label calibration arm B gets, at equal label budget, since granting it to one arm and not the other made the comparison unfair. §4.1.

8. **References are per (topology, context), not per topology** (R7). A stored property vector cannot anchor predictions made under a different supply, load, temperature, corner or layout policy. §4.1, costed in §4.9.

9. **Shortcut and escape subsamples are sized from the bounds they must support** (R3). 38/40 is an observed proportion whose 95% interval is 83.5%–98.6%, and 40/40 bounds the discrepancy rate only at 7.2% — so 40 designs cannot certify a 5% tolerance. The shortcut subsample is **60** (zero discrepancies bounds at 4.87%), escalating to 150 for a 2% bound; the yield-only escape subsample is **300**, since 200 bounds only at 1.49% and cannot certify "below 1%" as v2 claimed. Agreement is decomposed into definite-label agreement, false acceptance among shortcut passes, and indeterminate fraction, because a raw agreement count can be dominated by indeterminate–indeterminate pairs. Claim 1 plan §1.

10. **Conjunction bookkeeping is separated from mechanism measurement** (R3). Once pass is the conjunction of nominal and yield pass, a nominal-failing design fails the conjunction whatever its yield does, so no escape rate licenses or forbids inheriting that verdict — v2 made a definitional consequence contingent on a measurement. Inheritance of the conjunction label is unconditional; the yield-only escape rate is measured because it is interesting, not because it authorises anything. Claim 1 plan §1.

11. **3A and 3B get separate analysis specifications** (R6). v2's 3B ran six rankers — at most four distinct natural ones, possibly three if "best" duplicated an extreme — while later paragraphs still promised fits on "nine natural" and "all twelve". 3B's selection rule now guarantees four distinct natural rankers; the model-quality association lives in 3A where twelve exist; and 3B is **three preplanned paired contrasts** with no ranker-level covariates, because four rankers cannot support a regression carrying correlated fidelity measures, a free breakpoint and interactions. The **minimum practically meaningful effect is set from circuit-design economics** — a 25% reduction in median checks to confirmed accept — rather than transplanted from another field. §5.4.

12. **The budget is rebuilt from one set of rules** (R5). v2's confirmation row was understated fivefold (270 against 1,333 core-hours), 3A was costed as cheap checks rather than certifications (360 against 1,288), and certification *attempts* were confused with *solved episodes*. v2's rows summed correctly to its stated total, which is how the individual errors survived. The corrections add about 4,700 core-hours and reducing 3B from twelve rankers to six removes about as much, so the total is close to v2's by coincidence rather than cancellation: **about 9,650 as a scenario, about 13,500 with contingency**. §5.5.

13. **Physical response measurement names its target** (R5). 16,000 single post-layout simulations buy **nominal** extracted response. A mismatch quantile or yield needs draws per perturbed design, so a separate and much narrower mismatch-response line is budgeted, and layout regeneration gets its own row. The finger-variation set, harvested at stage 0 and cell P, supplies nominal finger-response evidence and does not license finger claims at the mismatch endpoint without its own mismatch subset. §4.9.

14. **One canonical schema replaces duplicated prose** (R8). v2 corrected "snap to model bins" in its introductions while §5.1's action definition and claim 1's `canonicalise` stage — the executable rules — still said it. §2.7 is now the single definition of parameters, encodings, legal moves, device correspondence and the endpoint, and it wins wherever another section disagrees. Four substantive fixes inside it: passives and sources that are sizing variables enter the **continuous parameter vector**, not merely the feature vector; source values use a signed `asinh` encoding, since a logarithm is undefined at zero and negative; device correspondence is an **equivalence-group** map, since v2's rule permitted splitting and forbade genuine merging while claiming both, and devices whose mismatch draws must stay independent are never merged; and derivatives are reported against the **realised grid-quantised displacement**, with smooth schematic derivatives kept as a separate object rather than conflated with finite grid moves.

### Points settled before pre-registration

15. **"No direct derivative labels", not "no training signal"** (point 1). Value labels constrain the function in every direction, so the complement is not untouched. Instrument 6's reported comparison is **B-S against B on the same complement directions**, which isolates derivative transfer; the within-model gap is descriptive beside it. The coordinate metric defining orthogonality is stated, since "orthogonal" is not basis-free. §4.3, §4.5.

16. **The ranker's target statistic at a stochastic cell is defined** (point 2). Predicted nominal value at the candidate's predicted worst corner plus a propagated standard deviation; ranking on the margin at the 90th-percentile point matching Y\* = 0.90; the **limiting property under mismatch** is the argmin of that quantile margin, not of the nominal margin. Feasibility calibration is then well posed. Arms without offset supervision are scored on nominal margins only, and that is stated wherever they appear. §5.2.

17. **The exclusion radius is counted before it is frozen** (point 3). v2 excluded whole topology-and-specification cells, which with thirteen to eighteen topologies could have removed most of claim 2's training data — and nothing checked. Exclusion is now by run plus a measured near-duplicate distance, retained counts per topology are reported at month 6 before freezing, and **120 designs are reserved** so that the month 28 power simulation can increase the episode count without touching a training design. §5.1.

18. **Validation and final-test designs are disjoint** (point 4). A fresh mismatch seed does not restore a tuned-on design to test status, because what was tuned on was its nominal and structural information. Claim 1 plan §6.

19. **The novelty matrix is supplied and the universal claim is narrowed** (point 5). The motivating sentence is replaced by an enumerated table of named systems and the endpoint each actually reports, with "not stated" where a paper is silent — so a counterexample improves the table rather than falsifying the thesis. §3, §5.

20. **Bian and Xie is verified, and it is closer than the audit said** (point 5). The record exists: arXiv 2608.24963, submitted 25 August 2026. It reports that fit accuracy does not delimit surrogate benefit, that removing the gradient term from the training loss cut surrogate acceptance from 0.703 to 0.148, and that a trust-region solver with little room lost ground when a surrogate was attached. The first is this thesis's premise in the general setting, the second is B-S against B in another domain, and the third is §5.4's strategy-dominance shape. The novelty claim narrows to the circuit-specific instantiation; the premise strengthens, since two groups reached the question independently. §5.

### What the recheck asked for that is not in v3

- **The feasibility pilot.** The recheck recommends a small fixed-batch study with per-family models in the first six months, before the full graph and probe programme. That is a scheduling decision for the supervisor rather than a protocol correction, and it interacts with claim 1's month 1 to 6 critical path. It is carried to §7 as an open decision, not silently adopted or dismissed.
- **The workload objection.** The recheck notes that the core workload has grown even though the gated projects were already optional, and v3 grows it further — the endpoint correction, full evaluation in 3A, and the larger validation subsamples all cost compute. This is acknowledged rather than argued away: v3 is a more expensive plan than v2, and the reduction ladders in §4.9, §5.5 and claim 1 plan §5 are what absorb it. Whether the whole programme fits a half-time schedule remains, as the audit said, a planning judgment that pilot measurements settle and this document does not.
