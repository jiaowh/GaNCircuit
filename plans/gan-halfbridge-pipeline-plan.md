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
platform choice at G0. Source-file inventory, terms, physical board identity,
lab inventory and the KiCad route remain unresolved. EPC's official EPC90133
page lists a 100 V, 40 A half-bridge with two EPC2302 plus an EPC2038, a uP1966E
driver, schematic, BOM, Gerbers and a quick-start guide; editable Altium files
are available on request. No ODB++ stackup link is listed. EPC's EPC2302 product
page lists an LTspice model and a 3 x 5 mm package. These page listings do not
establish that files have been downloaded, their reuse terms, board revision or
physical-board identity.

Download status: the EPC2302 datasheet (29 April 2026), EPC90133 QSG v1.0
(6 September 2022) and schematic are downloaded, readable and checksummed in
[the target source record](../devices/epc/epc90133-sources.json). The existing
unmodified LTspice library contains `EPC2302 gatein drainin sourcein`; it has
not yet been executed for this target. BOM/Gerber retrieval and consistency
checks remain open. The QSG lists an 80 V maximum bus input under its stated
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
  netlist-driven design. Choose one route at G0 and record it:
  - request the Altium files and use KiCad's Altium importer, then verify
    against the Gerbers;
  - re-enter the schematic programmatically from the PDF and BOM, and check
    connectivity against the Gerbers;
  - treat the stock Gerbers only as a geometry reference for parasitic
    extraction.
- Vendor performance data are vendor-described measurements. They are not an
  audited raw dataset, and their measurement setup may differ from ours.

## 4. Pipeline stages and interfaces

Three stages, one per student. Each consumes and produces versioned artifacts
through the shared runner and provenance contracts. A stage may use one
reasoning agent, several, or ordinary scripts. What must be fixed first is the
interface: inputs, outputs and acceptance checks. The supervisor integrates the
stages, and the whole pipeline runs end to end weekly on the shared device,
board and framework.

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
| Acceptance | The model runs without modification, and convergence and warnings are checked, not just the exit code. Agreement tolerances are declared per curve before comparison. Every discrepancy is classified as model, digitization, or test-condition mismatch. |

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
| Work | Build the KiCad design programmatically from the reference schematic. Extract the power-loop and gate-loop parasitics with a declared method. Simulate switching with those parasitics, then iterate the layout. |
| Outputs | Versioned KiCad project, extraction report with its method, switching-simulation results, fabrication package |
| Acceptance | Schematic–layout connectivity matches the reference netlist. DRC passes. The extraction method has passed a known-answer check and is cross-checked on the stock EPC layout. A human review signs off before fabrication release. |

Programmatic KiCad control uses the scripting interface and `kicad-cli`
(for DRC and exports); pin the KiCad version once it is installed. Candidate
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
- **Targets are relative to the EPC original under the same model:** overshoot lower, Eon + Eoff not higher, estimated
  efficiency not lower. These are comparisons between layouts simulated with the same unvalidated model and must be labelled so;
  switching energy carries the EPC2302 Fig. 7 gate-charge exception. The operating point must be one declared value: the
  draft's efficiency case is 48 V → 12 V, while EPC's Fig. 9 is 48 V → 13.8 V, 20 A, 250 kHz.
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
them independently. Learn a mapping between geometry and parasitics only after
paired examples exist; compare its value with the fixed search baseline. This
is staged research work, not a prerequisite for the current stock-board extraction.
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
| Work | Drive the instruments through double-pulse and efficiency tests with the safety interlocks active. Extract waveform metrics: switching times, overshoot, ringing frequency and damping, switching energy, dead-time behavior, efficiency. Back-fit parasitic and model parameters and assemble the per-layer error budget. |
| Outputs | Raw waveforms with instrument settings; extracted metrics; back-fit results with uncertainty and parameter correlations; the closure report |
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
documented, so disagreements can be attributed before our own layout adds
unknowns. Then fabricate and measure our layout.

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
a fixed-script or manually guided baseline on the same task. Decide before the
own-board search whether performance improvement over the vendor board is a
success requirement, and define its metric and constraints if so.

## 5. Simulator selection and adapter

Choose the simulator from the selected vendor model and the available
licenses. Do not convert the vendor model to another simulator's syntax.

| Candidate | Status |
|---|---|
| LTspice | **Selected, 28 September 2026** (version 26.1.1; EPC lists LTspice models for EPC2204 and EPC2302). Free, with command-line batch execution, so simulations run without the GUI. The switches `-b` (batch run producing a `.raw` file), `-Run`, `-ascii` (ASCII `.raw`) and `-netlist` are documented in a community mirror of LTspice's help ([ltwiki](https://ltwiki.org/LTspiceHelp/LTspiceHelp/Command_Line_Switches.htm)). Installed and accepted at G1; the GUI/batch comparison is recorded below. The EPC2302 model itself still needs a smoke run. |
| PSpice | Valid for EPC's PSpice model, subject to the available installation and license. |
| Spectre | Valid with the matching model and a simulator license; runs from the command line without the ADE GUI. |

Add the selected simulator as one adapter behind the existing
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

New artifact types:

- DatasheetDigitization
- VendorModel (with source terms)
- Bench
- LayoutRevision
- ParasiticExtraction
- TestPlan
- MeasurementRun
- ErrorBudget
- ClosureReport

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
| G2 Model baseline | Stage 1 comparison of the unmodified model against the digitized datasheet | Declared tolerances; every discrepancy classified |
| G3 Stock-board simulation | Reference schematic simulated with parasitics extracted from the stock layout | Extraction known-answer check; switching predictions with stated assumptions |
| G4 Stock-board measurement | Approved test plan; interlocks verified; double-pulse and efficiency measurements on the unmodified EPC board | Measurement-chain characterization; first per-layer error budget |
| G5 Own layout | KiCad revision driven by G3–G4 results; checks; human review; fabrication | Connectivity, DRC, declared EM cross-check and review sign-off; blind predictions frozen before fabrication |
| G6 Closure | Own board measured; back-fit; closure report; checkpoint log | Score frozen predictions on held-out measurements; preserve first score; report agent performance and human interventions against a baseline |

Status, 28 September 2026 (updated after the EPC90133/EPC2302 selection):

- **G1** is met (28 September 2026). LTspice 26.1.1 is installed and pinned. The adapter passes its known-answer fixtures and runs the unmodified vendor model. After two reviews, it rejects failed runs it previously reported as completed. An interactive GUI run of the RDS(on) bench matched the batch values ([record](../results/toolset/ltspice-gui-check.json)).
- **G2, EPC2204 historical result:** accepted for the EPC9097 stock-board simulation, with a documented exception (owner review, 28 September 2026). The datasheet-table baseline runs with convergence and equation checks. Every datasheet curve is digitized with frame/grid calibration and legend-verified labels; 23 of 23 pass pre-declared tolerances (worst point uses 22.8% of its allowed error). The reviewer independently reproduced the extraction, comparisons and 88 tests under WSL. **Exception:** table QGS/QGD/QG(TH) values remain unresolved because EPC's own curve does not reproduce them; they may use different definitions or source data. Total QG matches. No tuning is justified. This result is not EPC2302 validation.
- **G2, EPC2302:** provisional baseline for G3 (owner review, 28 September 2026). The unmodified model runs in LTspice; limited table rows are inside their limits and QG is 4% low; 24 digitized curves in Figs. 1–6 and 8–10 pass. Fig. 7 gate charge fails its declared checks, and the table QGD/QG(TH) are unresolved. No tuning is justified; gate-charge-dependent switching times and losses must not be labelled validated.
- **G3, EPC90133:** open. BOM/Gerbers (B5253 Rev 2.0) are audited, the Gerber reader gives copper, drills and nets, and a BOM-based schematic passes a static check. The FastHenry via/plane-pair check fails its mesh criterion and stays recorded as failed; owner decision (29 September 2026): defer the fourth mesh and extract exploratorily, then use prediction sensitivity to choose further qualification. *Update, 30 September 2026:* power-loop variants A/I/B are extracted on the coarse mesh only (no m2 board extraction has run); QSG Fig. 9 is digitized with a declared uncertainty; the double pulse matches continuous operation on A and on B (ideal supplies, 25 °C, ideal output source); no tested single change or combination reproduces Fig. 9 (docs/build.md, tests 5–6). The gate and source-return paths were not extracted then; *update, 1 October 2026:* variant G extracts them (one mesh, unqualified vias, exploratory; docs/build.md test 7). Separated sensitivity cases (test 6, assumed values) show that common-source inductance is material: 25–50 pH cut the simulated overshoot by 39–51 % with the frequency staying within 11 % of the measurement, while the same inductance with a Kelvin return, or in the drain, raises it. Gate-loop inductance is minor. Layout is therefore not excluded. *Test 7 (1 October 2026):* with the extracted gate paths the overshoot falls from 35.7 to 25.2 V; the split controls attribute about 7 V to the high-side gate path, with magnetic coupling of the forward gate path a supported mechanism within this model (not isolated from the gate path's own impedance); the low-side path lifts Q2's die VGS to 2.0 V. G + an assumed 50 pH package source matches Fig. 9's rise and frequency, but overshoot and damping fail; consistency, not identification. PHASE-ball stress is unresolved.
- **G3, EPC9097 historical work:** paused for the selected target. The prior switching bench and layout investigation remain historical sensitivity evidence and do not block EPC90133 work.
  - *Done:* the board files are recorded with checksums and terms. A double-pulse bench runs two unmodified EPC2204 models with a datasheet-calibrated behavioural uP1966E driver (no vendor driver model exists), at EPC's published 48 V → 12 V, 1 MHz conditions, with the loop inductance swept.
  - *Comparison:* EPC's published switch-node screenshots are digitized and compared diagnostically ([docs](../docs/build.md#epc9097-switching-bench-g3-before-layout-extraction)).
  - *Owner review, 28 September 2026:* useful as a sensitivity study; G3 stays open until the matching layout's parasitics are extracted.
  - *Open:* EPC publishes two layouts (6-layer ODB++ and 4-layer Rev 2.0 Gerbers). Identify our board's revision and, separately, the revision behind EPC's published waveforms; they need not match. Both files stay candidates until evidence connects one to the board or the measurements. Then verify the extraction tool on a known geometry, extract the power and gate paths including return paths, and rerun the comparison.
  - *Sensitivity, not a limit:* in the simplified bench the switch node reaches 96 V from 48 V at 0.8 nH. With gate-loop and common-source inductance omitted, an approximate driver and assumed capacitors, this prioritises extraction; it does not set a safe envelope or a margin below 100 V.
  - *Extraction tool:* FastHenry 3.0.1 is built locally (MIT licence: internal noncommercial use, no redistribution; owner confirmed on 28 September 2026 that the project uses it internally and does not distribute it). It passes its known-answer checks for bars and a thin-dielectric plane pair ([docs](../docs/build.md#fasthenry-inductance-extraction-tool-qualification-g3)). The original perfect-conductor reference check remains failed; a later skin-effect diagnosis motivated a replacement check declared before its run, which passes. Vias and plane holes are not yet qualified.
  - *Unidentified:* the source of EPC's 130 MHz ringing (power loop, bus network or probe path), and the cause of the slower measured rise. Measurement-path dominance is one candidate. The effective dead time inferred from the plateau (about 7.6 ns) depends on the driver model.

G1–G3 can proceed in simulation while G0's lab inventory is completed. No
hardware is energized before G4's test plan and interlocks are approved.

## 9. Open decisions for the project owner

1. Selected: EPC90133/EPC2302. Resolve source-file inventory and terms, physical
   board identity, lab inventory, and the KiCad route before board extraction.
2. Available licenses (PSpice, Spectre) and whether LTspice may be installed
   on the lab and development hosts.
3. Lab inventory: oscilloscope and probe bandwidth, isolated or differential
   probes, current sensing, supplies, electronic load, temperature control.
   Owner, 30 September 2026: the lab has a Keysight B1506A (power device analyzer)
   and a PD1550A (double-pulse tester). Both test devices in their own fixtures, not
   an assembled evaluation board; the owner is checking what is available for board
   measurements. The B1506A could later measure EPC2302 gate charge and capacitances
   (the open Fig. 7 question) if a fixture for its small package is available.
4. Whether to request EPC's Altium files, and the budget for fabricating
   boards.
5. Owner decision, 30 September 2026: an EPC90133 will be purchased. On arrival,
   record its silkscreen revision and fitted population. Identify separately the board
   and population used for EPC's published measurements. No ownership is assumed.
6. FastHenry use beyond the internal-only scope recorded in `95b0fad`, including
   partner or commercial collaboration. The restrictive MIT-authored notice is not the
   standard MIT License; keep source/binaries out of git. Separate local builds
   do not by themselves settle whether a broader use is permitted.
7. Owner decision, 30 September 2026: no EPC inquiry will be sent. Fig. 9's probe,
   probing point and dead-time setting, and the EPC2302 package inductance, stay unknown
   and are treated as assumptions or measured on our board.
8. Owner decision, 30 September 2026: the agent-workflow milestone (section 10, item 7)
   is a project goal but not the current priority.
9. Define I-1/I-2/I-3 schemas, layout variables,
   held-out validation conditions and whether board-performance improvement is required.

## 10. Immediate work and dependencies

Updated 29 September 2026 (owner review of the via check):

1. Annotated power-loop overlay of the stock EPC90133: component contacts located
   from paste layers and checked against copper, solder-mask openings and the EPC2302
   footprint (dimensions, orientation, gate/source/drain mapping); copper paths,
   return planes, via groups with their connected layers, and exact extraction ports.
2. Exploratory FastHenry extraction with explicit geometry assumptions: variant A
   (top layer and mid-layer 1, Ci only), an intermediate variant (additional copper,
   Ci only) and variant B (all copper, Ci and Cm), with explicit alternative via and
   junction representations. Keep return paths and mutual coupling in the extracted
   network. Two meshes are a sensitivity check, not proof of convergence. Capacitor
   capacitance, ESR and ESL assumptions stay explicit and separate from copper geometry.
3. Switching sensitivity: a double-pulse bench with the current matched at each edge,
   and, for a direct comparison with QSG Fig. 9 (continuous 250 kHz buck operation), a
   periodic buck bench or demonstrated equivalent switching conditions. Driver, dead
   time, temperature and measurement assumptions stay fixed across extraction variants.
   Spend qualification or mesh refinement where the sensitivity changes a decision.

4. Literature review (29 September 2026, docs/gan-layout-literature-notes.md) adds items to the
   sensitivity study: an EPC2302 package-inductance case (value unknown, stated as an assumption,
   because the vendor model has none); a switch-node capacitance estimate from the Gerber plane
   overlaps (FastHenry gives L and R only); and a declared digitization of QSG Fig. 9, compared
   only after passing the simulation through a stated probe/scope response. G4 candidate isolating
   experiments: loop L from ringing frequency with known Coss and a known added capacitance,
   probe characterization, and the stock board with and without Cm.

5. Capacitance extraction (added 29 September 2026): FasterCap (FastFieldSolvers, FastCap2-compatible
   input, multiple dielectric regions, automatic refinement, batch mode; LGPL 2.1 or later per its README,
   https://github.com/ediloren/FasterCap). Before use: record version, source and checksum and read the
   licence file itself; pass known-answer checks (parallel plates with fringing, microstrip over a ground
   plane) with a declared refinement criterion; then extract SW/VIN/GND capacitances of the power stage
   to replace the parallel-plate estimate (135 pF SW-GND). Its LGPL terms would also avoid FastHenry's
   internal-only restriction for this part of the flow.

6. External review of the test-5 findings (30 September 2026), in its recommended order:
   (a) correct overclaims and enforce result status in code: unusable cases stay inspectable but are
   structurally excluded from comparisons and verdicts, and reports bind their inputs by hash;
   (b) bound the omitted gate and source-return paths with cases that separate gate, common-source,
   drain and source inductance (test 6), and extract those paths if the bound is material;
   (c) develop the hardware plan in parallel (draft v0.1: docs/epc90133-hardware-test-plan.md, not approved). It should test explicit competing explanations and
   include held-out operating conditions, not seek one matching waveform.
7. Agent-workflow milestone (review item 7). The project has stronger evidence for its engineering
   tools than for an agent-driven contribution: the I-1/I-2/I-3 schemas are open, the GaN studies do
   not consistently use the immutable artifact store, and there is no scored agent-versus-script or
   manual baseline. Next software milestone: one reproducible, bounded run that consumes declared
   artifacts (the extraction, digitized-figure and model records), checks their validity, produces the
   Fig. 9 comparison and stops correctly. It records interventions, failures, wall time and cost, and
   it is run once by the agent and once by the plain scripts for comparison.

G3 remains open, and gate-charge-dependent timing and losses remain unvalidated.
Physical board identity, lab inventory and any EPC request remain open; sending a
request requires an explicit instruction. No simulation sensitivity result alone
establishes a safe test envelope.
