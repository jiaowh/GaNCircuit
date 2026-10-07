# Agent-driven GaN half-bridge pipeline

Active project direction from 28 September 2026. It supersedes
[the co-design toolset plan](autonomous-circuit-toolset-plan.md) as the
implementation priority. That plan's contracts for artifacts, provenance, result
semantics and the runner interface remain in force and are reused here. Its
silicon NMOS/amplifier demonstration is a paused development fixture.

## 1. Objective

GaN power transistors switch faster and with lower losses than silicon, and
are displacing it in data-center supplies, fast chargers, motor drives and
electric vehicles. That speed makes designs unforgiving. Real-board behavior
depends on a whole chain: compact model, package and PCB parasitics, gate
driver, thermal coupling and the measurement itself. Experienced engineers
currently work through that chain by hand.

The project builds and validates an agent-driven pipeline for one commercial
EPC GaN FET and its half-bridge development board. EPC publishes the datasheet,
SPICE models, schematic, bill of materials, Gerber files and performance data;
section 3 lists the terms that still need checking. Engineers supervise
checkpoints instead of performing each step:

**datasheet → model → layout-aware simulation → automated measurement → closure report**

The end-to-end run should show which checkpoints still need a human and which
loops can close on their own.

### Workflow methods review incorporated on 28 September 2026

The owner's review of *AI Agents for GaN Power Electronics Workflow and
Methods V1* is incorporated below; see the [review record](../docs/gan-workflow-methods-review.md).
The owner's decision now selects EPC90133 with EPC2302 as the active target.
The EPC9097/EPC2204 work below remains historical evidence and reusable tooling;
it does not qualify EPC2302. The new target requires its own source, model and
board qualification. Existing LTspice tools remain reusable.
Commercial transistor dimensions remain fixed; the design variables are the
surrounding circuit and PCB layout.

## 2. Scope

**Core.**

- Static and switching behavior of the vendor model against the datasheet.
- Basic switching-charge behavior: gate charge, output charge and the
  voltage dependence of Coss.
- Dead-time selection and its effect on efficiency.
- Tests at controlled, measured temperatures: room temperature and at least
  one elevated case temperature.
- Hard-switched double-pulse and efficiency testing.
- Layout-aware simulation with extracted loop parasitics.
- One layout revision taken through checks and human review to fabrication.

**Extension**, for students continuing beyond the credited project:

- Advanced device effects fitted from measurement: dynamic RDS(on),
  output-capacitance losses, and detailed dead-time and temperature
  dependence.
- Soft-switching operation.
- Further GaN application circuits from EPC's evaluation-board portfolio.
- Progressive removal of human checkpoints for well-bounded tasks (section 7).

**Out of scope.** Physical redesign of the GaN device, such as TCAD of the
commercial part. The vendor materials do not supply a structure or process
recipe, and fitting electrical curves cannot recover one.

## 3. Target device, board and source terms

**Selected target: EPC90133 with EPC2302.** This owner decision completes the
platform choice at G0. Source files and terms are recorded below; physical board
identity and lab inventory remain unresolved. The KiCad route is the track R
reconstruction, with edit/refill qualification still open. EPC's official EPC90133
page lists a 100 V, 40 A half-bridge with two EPC2302 plus an EPC2038, a uP1966E
driver, schematic, BOM, Gerbers and a quick-start guide; editable Altium files
are available on request. No ODB++ stackup link is listed. EPC's EPC2302 product
page lists an LTspice model and a 3 x 5 mm package. These page listings do not
establish that files have been downloaded, their reuse terms, board revision or
physical-board identity.

Download status: the EPC2302 datasheet (29 April 2026), EPC90133 QSG v1.0
(6 September 2022) and schematic are downloaded, readable and checksummed in
[the target source record](../devices/epc/epc90133-sources.json). The existing
unmodified LTspice library contains `EPC2302 gatein drainin sourcein`; it runs
through the LTspice adapter and is the provisional G2 baseline (section 8). The
BOM and Gerbers (B5253 Rev 2.0) are retrieved, checksummed and audited
(`scripts/audit_epc90133_board_files.py`); they do not establish the purchased
board's revision or population, which are checked on arrival. The QSG lists an 80 V maximum bus input under its stated
conditions; the device's 100 V rating is not a project-approved operating limit.

Sources: [EPC90133](https://epc-co.com/epc/products/evaluation-boards/epc90133),
[EPC2302](https://epc-co.com/epc/products/gan-fets-and-ics/epc2302).

Prior candidates and work remain in the record:

| | EPC9097 + EPC2204 (historical) | EPC90121 + EPC2050 (not selected) |
|---|---|---|
| Rating | 100 V, 20 A half-bridge | 350 V, 4 A half-bridge |
| FETs | Two EPC2204 (100 V, 6 mΩ max) plus one EPC2038 | Two EPC2050 |
| Gate driver | uPI uP1966E | onsemi NCP51820 |
| Published measurements | QSG v3.0 switch-node screenshots digitized; diagnostic comparison at 48 V → 12 V, 1 MHz, 10/15 A; measurement setup and board identity unresolved | QSG Figs. 12–13: switch-node and inductor-current waveforms, efficiency and loss at 280 V → 28 V, 50 kHz |
| Lab safety burden | Lower bus voltage | 280–350 V bus; stronger interlock and enclosure requirements |

Sources:
[EPC9097](https://epc-co.com/epc/products/evaluation-boards/epc9097),
[EPC90121 QSG Rev 1.0](https://epc-co.com/epc/Portals/0/epc/documents/guides/EPC90121_qsg.pdf),
[EPC2204 datasheet](https://epc-co.com/epc/Portals/0/epc/documents/datasheets/EPC2204_datasheet.pdf).

Model files: EPC's application note
[AN005](https://epc-co.com/epc/Portals/0/epc/documents/product-training/Circuit_Simulations_Using_Device_Models.pdf)
says its LTspice, PSpice, TSpice and Spectre models share the same equations
and include temperature effects on conductivity and threshold. EPC also
publishes a separate thermal RC-network model for the EPC2204. That per-part
model availability has not yet been checked for the EPC2050.

The EPC2204 is a passivated bare die with solder bars. Its footprint and
assembly therefore needed care in the historical layout work. EPC2302 uses a
3 x 5 mm package, whose footprint and assembly still need to be checked for the
selected design.

Do not combine one board's measurements or gate driver with another board's
device model. The EPC90133 page lists the uP1966E driver, matching the selected
board; its listed Gerbers do not by themselves establish a KiCad design or
stackup.

First deliverable after the selection (done 28 September 2026; historical): inventory
and record the unmodified EPC2302 model and all EPC90133 source files and terms, then
demonstrate the model running through the LTspice adapter. Both are done, and G2 for
EPC2302 is a provisional baseline (section 8). Measurement still follows only after the
physical board, its layout revision and its population are identified.

Historical EPC9097 work used a 6-layer ODB++ layout listing EPC2619,
4.7 ohm turn-on / 1 ohm turn-off resistors and uP1966A; the published BOM used
by our bench specifies EPC2204, 1 ohm / 0 ohm and uP1966E. The 4-layer Rev 2.0
Gerbers do not establish part values. Preserve separate records for geometry,
population and measurement identity. Neither candidate is established as our
physical board or the board used for EPC's screenshots. Editable Altium files
alone would not establish the fitted population or measurement-board identity.

Selection criteria (used for the completed platform selection and retained for
future changes):

1. A vendor model in a format our selected simulator runs (section 5).
2. A downloadable schematic, BOM and Gerber set.
3. Published performance data at stated test conditions.
4. Bus voltage and current that the available lab equipment and safety
   arrangements can support.
5. A practical route to a KiCad design.

Source rules:

- Record the URL, retrieval date, file version, checksum and stated terms for
  every vendor file. Do not assume unrestricted reuse or redistribution
  because a file is publicly downloadable. Keep vendor files outside git
  unless their terms permit redistribution; store the checksums and retrieval
  script instead.
- EPC lists the editable Altium sources as available on request. Gerbers and
  PDF schematics do not import directly into KiCad as a linked,
  netlist-driven design. Track R reconstructs the saved geometry from Gerbers and
  the layout PDF; it does not yet qualify refilling or editing the board. The
  route and its checks are recorded in the build notes.
- Vendor performance data are vendor-described measurements. They are not an
  audited raw dataset, and their measurement setup may differ from ours.

## 4. Pipeline stages and interfaces

Three stages, one per student. Each consumes and produces versioned artifacts
through the shared runner and provenance contracts. A stage may use one
reasoning agent, several, or ordinary scripts. What must be fixed first is the
interface: inputs, outputs and acceptance checks. The supervisor integrates the
stages. Rerun the affected stages when their inputs or implementation change;
reserve full end-to-end runs for an integration change or a declared evaluation.
There is no weekly rerun requirement.

The common interfaces are:

| Interface | Required handoff |
|---|---|
| I-1 model to design | Unmodified model revision and any separately justified tuned revision; simulator/settings; qualified operating range; curve errors, uncertainty and unresolved exceptions |
| I-2 design to test and reviewer | Layout and component revisions; stackup; extraction method, frequency range, ports and return paths; predicted metrics and uncertainty; test conditions and requirements |
| I-3 test to model and design | Raw measurements and instrument settings; board identity; comparison with frozen predictions; uncertainty and per-layer attribution, including unidentified causes |

All handoffs use machine-readable, versioned records with units and source
references, plus a readable summary. Freeze exact field schemas before their
consuming agent is implemented. Existing scripts and runner interfaces are
building blocks; an integrated autonomous three-stage loop is not yet demonstrated.

### Stage 1: datasheet-to-model

| | |
|---|---|
| Inputs | Datasheet PDF, vendor model files (with provenance record), selected simulator adapter |
| Work | Digitize datasheet curves with a recorded digitization uncertainty. Generate test benches that reproduce each curve's stated conditions: output and transfer characteristics, RDS(on) against temperature, capacitances against VDS, gate charge, and switching tests where specified. Run the **unmodified** vendor model and compare. |
| Outputs | Digitized datasets; bench netlists; the baseline comparison report; a tuned model revision, only when the tuning rule below allows one |
| Acceptance | The model runs without modification, and convergence and warnings are checked, not just the exit code. Agreement tolerances are declared per curve before comparison. Attribute discrepancies only where evidence distinguishes model, digitization and test-condition errors; otherwise record them as unresolved with their consequence for downstream use. |

**Tuning rule.** The original vendor model is kept and always reported. Tune
only when all of the following hold:

1. Separate evidence has corrected or bounded the layout, driver and
   measurement contributions.
2. The discrepancy repeats across operating points.
3. The tuned model passes conditions held out from the fit.

A tuned model is a new revision that lists the changed parameters and why.
Otherwise device parameters would absorb errors from other layers.

### Stage 2: layout-aware design

| | |
|---|---|
| Inputs | Reference schematic and BOM, the KiCad route chosen at G0, the Stage 1 model, footprints and stackup |
| Work | Use the checked stock geometry and netlist as the baseline. Extract the power and gate paths with a declared method. Simulate a bounded set of candidate changes; create and verify the KiCad changes needed for the selected design. |
| Outputs | Versioned KiCad project, extraction report with its method, switching-simulation results, fabrication package |
| Acceptance | Schematic–layout connectivity matches the reference netlist. DRC passes. The extraction method has passed a known-answer check and is cross-checked on the stock EPC layout. A human review signs off before fabrication release. |

Programmatic KiCad control uses the scripting interface and `kicad-cli`
(for DRC and exports); KiCad 10.0.6 is installed per-user and pinned (1 October 2026). Candidate
extraction tools include open inductance solvers such as FastHenry, or
field solvers. Adopt one only after it reproduces a known-answer geometry.
Before designing our own board, simulate the stock EPC layout, so that a
measured reference exists before any layout change.

#### Parasitic extraction interface and Agent 2 stop criteria (draft v0.1, 29 September 2026)

Source: [Layout Parasitic Extraction and Agent 2 Stop Criteria.docx](Layout%20Parasitic%20Extraction%20and%20Agent%202%20Stop%20Criteria.docx)
(candidate platform EPC90133), adopted here with the corrections marked below.

Parasitics to extract, all "Must":

| Group | Parasitic | Location | Status (29 September 2026) |
|---|---|---|---|
| Power loop | L_d | decoupling capacitor (+) to high-side drain | extracted as the VIN branches (exploratory) |
| Power loop | L_sw | high-side source to low-side drain | extracted as the SW branch (exploratory) |
| Power loop | L_s | low-side source through return vias and inner plane to capacitor (−) | extracted as the GND branches (exploratory) |
| Common source | L_cs (HS, LS) | source pad to Kelvin branch point | extracted in variant G (exploratory, one mesh, 1 October 2026): Q1 0.9 pH, Q2 47.7 pH |
| Gate loop | L_g | driver output through R_g to gate | extracted as G's gate-drive branches, with their couplings to the power loop (exploratory) |
| Gate loop | L_ks | Kelvin source back to driver ground | extracted as G's gate-return branches (exploratory) |
| Capacitance | C_sw-gnd | switch-node copper to ground | parallel-plate estimate only (135 pF); FasterCap planned |

Five steps: (1) read the layout and stackup (KiCad for our own boards; the stock EPC90133 is read from its Gerbers);
(2) cut out the power and gate loops and place ports on FET pads, capacitor pads and driver pins; (3) field-solve
L and R (FastHenry) and C (FasterCap); (4) reduce the matrices to named segment values; (5) write them to a parameter
file `parasitics.inc` that the LTspice bench includes, so that a new layout changes only that file.

Corrections adopted with the draft:
- **Keep the coupling.** Partial inductances do not add up to the loop inductance without their mutual terms, and on this
  board they are large (VIN and GND paths 0.13 mm apart). `parasitics.inc` carries the segment values *and* the coupling
  between them (the current bench's K elements). Agent 2 may rank segments by their contribution, but it must
  simulate with the full coupled network.
- **Stop only on resolvable improvement.** The draft stops at "less than 1% improvement over 5 consecutive
  iterations". An improvement counts only if it exceeds the declared extraction and simulation uncertainty (today the
  via representation alone moves the loop inductance 2–4%, and the mesh is not shown to converge), within a declared
  iteration and compute budget. Budget exhaustion without meeting targets is not success (rule below).
- **Current targets (owner, 5 October 2026):** minimize overshoot, subject to FET loss at most 5% above stock
  and Q2 gate peak not above stock under all four declared driver/package alternatives. This replaces the draft's
  three objectives; Eon + Eoff is no longer a separate target. These are relative comparisons under the same
  unvalidated model, not hardware margins. Use settled loss estimator revision 2 and retain the Fig. 7 exception.
  The design operating point is 48 V → 12 V, 20 A, 250 kHz; EPC's Fig. 9 uses 13.8 V output.
- **Tool identities.** The draft names FastHenry2 (the FastFieldSolvers distribution) and PyLTSpice. The qualified tools are
  FastHenry 3.0.1 (internal-only licence) and the project's own LTspice adapter (G1). Changing either needs its licence
  recorded and the known-answer checks rerun.
- Human review approval stays a required stop condition (section 7).

#### Layout optimization and stopping rules

Keep the reference circuit topology fixed for the first layout demonstration.
Declare a bounded set of geometry variables, fabrication/connectivity constraints,
operating corners and performance targets before optimization. Begin with
generated candidate layouts and a reproducible fixed search baseline:

1. Extract each candidate's coupled parasitics, with physical ports and return paths.
2. Simulate switching and identify which changes could meet the targets.
3. Rebuild feasible geometry, rerun connectivity/DRC, then re-extract and simulate.

Target parasitic values are search guidance, not proof that a layout can realize
them independently. A learned geometry-to-parasitics model is deferred; the
current work does not require a surrogate or an autonomous search framework.
If layout changes alone are insufficient, permit declared component and dead-time
changes within the approved design envelope, retaining the original baseline.

Stop when the actual extracted candidate meets declared performance targets over
specified corners, constraints pass, and improvement falls below a predefined
threshold or the search budget is exhausted. Budget exhaustion without meeting
targets is not success. Define the higher-accuracy electromagnetic cross-check's
tool, quantities, frequency range and allowed disagreement before release;
do not use an unspecified "high-accuracy" check as an acceptance gate.

### Stage 3: test and closure

| | |
|---|---|
| Inputs | Approved test plan (operating envelope, sequence, limits), instrument inventory, board under test, Stage 1–2 predictions |
| Work | Perform approved double-pulse and efficiency tests with the independent safety interlocks active. Extract metrics and compare them with frozen predictions. Attribute discrepancies only where the measurements distinguish their causes. Automate instrument operations after the setup and procedure are established. |
| Outputs | Raw waveforms with instrument settings; extracted metrics; prediction scores; an error budget including unidentified contributions; the closure report. Parameter fits are optional and require identifiable parameters, uncertainty, correlations and held-out checks. |
| Acceptance | Measurements stay inside the approved envelope. Probe deskew and bandwidth are characterized before device conclusions are drawn. Each error-budget layer has its own supporting evidence. Parameters the experiments cannot distinguish are reported as unidentified. |

**Separate evidence per layer.** One matching waveform cannot uniquely
separate transistor, parasitic and probe errors. The test plan must include
experiments that isolate each layer, for example:

| Layer | Isolating evidence |
|---|---|
| Measurement chain | Probe deskew and bandwidth checks on a known signal; the current-sense insertion impedance |
| Parasitics | Ringing frequency before and after adding a known capacitance; impedance measurement of the unpopulated or stock board; agreement with extraction |
| Device | Static and charge measurements under datasheet conditions; double-pulse tests across current, voltage and gate resistance, so that parameters affect waveforms differently |
| Gate driver | The driver's propagation delay and output measured separately from the power stage |
| Thermal | Controlled, measured case temperature; repeated tests at two temperatures |

**Order.** Measure the unmodified EPC board first. Its layout is fixed and
documented, so it removes a changing layout as a confounder. It does not by itself
make every discrepancy identifiable. Then fabricate and measure our layout.

**Blind prediction and learning evaluation.** After stock-board calibration,
freeze the new board's layout, component population, model/extraction revisions,
simulation settings, operating conditions, predicted metrics with uncertainty,
and acceptance thresholds before fabrication and before seeing its measurements.
Separate calibration and held-out validation data. Score the first blind prediction
unchanged; later corrections produce new revisions and do not overwrite that score.
Feedback must first distinguish measurement, driver, parasitic, device and thermal
contributions; it does not automatically authorize device-model tuning.

Report agent reliability as well as electrical agreement: human interventions,
failed/retried tool runs, elapsed engineering time and compute/model cost against
a fixed-script or manually guided baseline on the same task. Use the owner's
single objective and constraints above for design ranking. Before a hardware
claim, declare how each constraint will be measured and what uncertainty permits
a decision; an unresolved constraint cannot be counted as met.

## 5. Simulator selection and adapter

Choose the simulator from the selected vendor model and the available
licenses. Do not convert the vendor model to another simulator's syntax.

LTspice 26.1.1 and the existing `circuit_tools.ltspice` adapter are selected and
accepted at G1. The unmodified EPC2302 model runs through it. Additional simulator
adapters are deferred until a selected model or lab requirement needs one.

Keep the selected simulator behind the existing
`circuit_tools` runner interface. The adapter:

1. Writes the test bench.
2. Launches the simulator in batch mode.
3. Reads the waveform output.
4. Reports measurements with their units and provenance.

It must return a parsed-output status and must not treat exit code 0 as
success. The shared experiment, artifact and results tooling stays unchanged.

**Adoption gate.** The adapter is accepted when it:

- runs a known-answer circuit with an analytical result;
- runs the unmodified vendor model;
- reproduces a GUI run of the same bench;
- surfaces convergence failures and warnings in the result.

## 6. Reuse from the existing repository

Reuse:

- the immutable revisions and artifact store;
- content hashes and provenance records;
- the job/outcome separation (pass, fail, unresolved, not-supported);
- the parsed-output rule for simulator results;
- the CLI.

The ngspice adapter was removed on 28 September 2026 after the LTspice adapter
passed the same known-answer role (it remains in git history). The DEVSIM and NMOS scripts and results stay as a paused
fixture. They are not prerequisites and are not extended for GaN.

Use the existing study reports and hash-bound handoff records. I-1/I-2 and the
simulation-assessment schemas are implemented in `src/circuit_tools/handoff.py`.
Define I-3 against the actual measurement inputs when those are known. Do not
create an additional artifact taxonomy or migrate every study into the artifact
store as a prerequisite for measurements.

## 7. Safety and human checkpoints

Hardware protection is independent of the language-model agent. It includes:

- a current-limited supply;
- hardware overcurrent and overvoltage trips;
- a hardware limit on pulse width;
- bus discharge;
- the enclosure interlock and an emergency stop.

The agent sends requests through an ordinary, non-LLM instrument-control layer
that enforces the approved envelope. That layer rejects out-of-envelope
commands whatever the agent asks.

Initial human checkpoints:

- selection of the target and its source terms;
- acceptance of any model tuning;
- layout release to fabrication;
- first power-on of each board;
- any expansion of the test envelope;
- sign-off of the closure report.

A checkpoint can become automatic for a well-bounded task only after a
recorded history of reviewed runs shows the agent's decisions would have
matched the reviewer's. The checkpoints for fabrication release and test
envelope expansion are removed last.

## 8. Gates

| Gate | Deliverable | Acceptance |
|---|---|---|
| G0 Target and sources | Confirmed FET/board pair; provenance and terms record; KiCad route; instrument and license inventory | Owner approves target; record remaining source and lab items |
| G1 Simulator adapter | Selected simulator installed and pinned; adapter with known-answer and vendor-model runs | Adoption gate in section 5 |
| G2 Model baseline | Stage 1 comparison of the unmodified model against the digitized datasheet | Declared tolerances; supported attribution or explicit unresolved exceptions |
| G3 Stock-board simulation | Reference schematic simulated with parasitics extracted from the stock layout | Extraction known-answer check; switching predictions with stated assumptions |
| G4 Stock-board measurement | Approved test plan; interlocks verified; double-pulse and efficiency measurements on the unmodified EPC board | Measurement-chain characterization; first per-layer error budget |
| G5 Own layout | KiCad revision driven by G3–G4 results; checks; human review; fabrication | Connectivity, DRC, declared EM cross-check and review sign-off; blind predictions frozen before fabrication |
| G6 Closure | Own board measured; closure report including unresolved causes; checkpoint log | Score frozen predictions on held-out measurements; preserve first score; report agent performance and human interventions against a baseline. Fitting is not required for closure. |

Current gate status (7 October 2026): G1 is met; EPC2302 G2 is provisional with
the Fig. 7 and sub-charge exceptions; G3 remains open. No project hardware
measurements or approved G4 procedure are recorded. Track R reproduces the saved
EPC geometry, but KiCad refill changes it; this is preparation for G5, not a
completed or released new layout. Detailed evidence is in the [README](../README.md)
and [build notes](../docs/build.md). Preserve failed and superseded runs there.

Simulation can proceed with explicit assumptions while the lab inventory is
completed. No hardware is energized before G4's test plan and interlocks are approved.

## 9. Open decisions for the project owner

1. **Actual board and equipment.** Confirm receipt, silkscreen revision and fitted
   components with the lab's responsible person, and record scope/probes, current
   sensing, supplies, load, temperature control and protection equipment. The
   B1506A and PD1550A are device testers; their presence does not establish an
   assembled-board measurement setup. Hardware-plan open items hold the details.
2. **Measurement approval.** Review the channel plan, numerical first-power limits,
   independent protection and the feasible calibration/held-out conditions. Decide
   how to evaluate the small FET-only loss constraint, or explicitly leave it
   unresolved; converter efficiency alone does not isolate that loss.
3. **Own-board release.** After stock-board evidence and a qualified edit workflow,
   agree the bounded layout change and fabrication budget. Track R is the selected
   reconstruction route. No Altium request or other EPC inquiry is planned.
4. **Broader use.** Any use beyond FastHenry's recorded internal noncommercial scope
   needs its terms resolved first. Internal-only use was recorded at `95b0fad`.
5. **Further agent or board evaluations.** Review value and cost before another
   target or execution milestone. EPC9165 remains a deferred candidate: its file
   and probe-access audit is done, but purchase needs a measurement question the
   EPC90133 cannot answer. See the [selection note](../docs/second-board-selection-2026-10-01.md).

## 10. Immediate work and dependencies

Current work order, 7 October 2026. This replaces the accumulated list of completed
studies and obsolete next steps. Methods, declarations and executed outcomes remain
in the scripts, saved reports and [build notes](../docs/build.md).

1. Obtain the board identity and equipment inventory (owner/lab).
2. Complete and review the probe/channel plan and executable first-power procedure
   in [the hardware plan](../docs/epc90133-hardware-test-plan.md). Include uncertainty,
   numerical limits, independent protection and discharge verification. The
   driver-only and input-logic preparation studies are already recorded; startup
   and transient overlap remain measurement questions, not established guarantees.
3. After approval, characterize the measurement chain and driver; freeze predictions
   and held-out conditions using the hardware plan's frozen-prediction record;
   perform approved stock-board measurements, then evaluate the R80 1.5 ohm candidate
   in E4. It is the best tested simulation candidate, not a frozen or validated
   hardware improvement. Efficiency E9 and controlled temperature remain core work.
4. Use the measurements to decide what model or layout change is justified. Keep
   unidentified causes explicit. The geometry-edit workflow is qualified for moving
   parts and vias (7 October 2026, `scripts/epc90133_edit_workflow.py` run 2: no-edit,
   one part move and one via move checked for copper/mask/paste, connectivity, DRC
   and reversibility). Edits needing new copper shapes (L3) need a zone-outline
   primitive and its own check before use.
5. Evaluate the agent's judgement against the frozen predictions and new
   measurements, with interventions, retries, time and cost recorded against a
   script or guided baseline. Agents may read normal project context. Milestones
   1/2 and E2E-0 already establish their stated non-blind execution/handoff behavior;
   repeating them does not establish engineering judgement.

**Work selection and stopping.** Before any additional study, name the decision
it could change, the observable result that would change it, and a bounded compute
budget. Prefer existing reports or a small discriminating check. Stop when the
result resolves that decision, cannot distinguish the alternatives, or reaches the
budget; record unresolved outcomes. Waiting for equipment is not itself a reason
to start another simulation study.

**Deferred until needed by such a decision:** broad sweeps, finer full-board meshes,
late-cycle loss attribution, further FasterCap qualification, surrogate models,
additional simulator adapters, another target and recurring end-to-end agent runs.
Their existing scripts and evidence remain available for replay. FasterCap is not
qualified for 3D board use; benchmark discrepancies do not establish board error
bars.

Core scope and G0–G6 remain unchanged: a measured stock board, one reviewed layout
revision through fabrication and measurement, and evidence about agent reliability.
No simulation sensitivity result alone establishes a safe test envelope.
