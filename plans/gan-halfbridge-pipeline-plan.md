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

**To be selected at gate G0.** The owner's notes cite EPC90121 resources and
EPC2204 models. They belong to different boards. EPC's quick-start guides and
datasheets, checked 28 September 2026, give two candidate pairs:

| | EPC9097 + EPC2204 | EPC90121 + EPC2050 |
|---|---|---|
| Rating | 100 V, 20 A half-bridge | 350 V, 4 A half-bridge |
| FETs | Two EPC2204 (100 V, 6 mΩ max) plus one EPC2038 | Two EPC2050 |
| Gate driver | uPI uP1966E | onsemi NCP51820 |
| Published measurements | Not yet checked | QSG Figs. 12–13: switch-node and inductor-current waveforms, efficiency and loss at 280 V → 28 V, 50 kHz |
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
assembly therefore need care in the layout stage.

**Owner decision, 28 September 2026: EPC9097 with EPC2204 is the provisional
first target.** Its lower voltage makes it a more manageable start, subject to
the actual test envelope and equipment. Its published resources also include
ODB++ data, the layer stackup and a test-point report, which help the layout
stage. EPC90121 with EPC2050 remains the alternative, if the lab already
supports it or its published measurements prove decisive. Do not combine one
board's measurements or gate driver with the other board's device model.
According to the owner, both EPC landing pages offer the Altium files on
request.

Immediate deliverable: the unmodified EPC2204 model running through an
LTspice adapter, with parsed results and a reproducible test bench. The lab
inventory and the Altium request proceed in parallel and do not block
simulator setup.

Selection criteria:

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

## 5. Simulator selection and adapter

Choose the simulator from the selected vendor model and the available
licenses. Do not convert the vendor model to another simulator's syntax.

| Candidate | Status |
|---|---|
| LTspice | **Selected, 28 September 2026** (version 26.1.1; EPC publishes an LTspice library containing the EPC2204). First candidate if the selected EPC model supports it. Free, with command-line batch execution, so simulations run without the GUI. The switches `-b` (batch run producing a `.raw` file), `-Run`, `-ascii` (ASCII `.raw`) and `-netlist` are documented in a community mirror of LTspice's help ([ltwiki](https://ltwiki.org/LTspiceHelp/LTspiceHelp/Command_Line_Switches.htm)). Confirm them against the installed version's own help at G1. Not yet installed on the Windows host. |
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
| G0 Target and sources | Confirmed FET/board pair; provenance and terms record; KiCad route; instrument and license inventory | Owner approves |
| G1 Simulator adapter | Selected simulator installed and pinned; adapter with known-answer and vendor-model runs | Adoption gate in section 5 |
| G2 Model baseline | Stage 1 comparison of the unmodified model against the digitized datasheet | Declared tolerances; every discrepancy classified |
| G3 Stock-board simulation | Reference schematic simulated with parasitics extracted from the stock layout | Extraction known-answer check; switching predictions with stated assumptions |
| G4 Stock-board measurement | Approved test plan; interlocks verified; double-pulse and efficiency measurements on the unmodified EPC board | Measurement-chain characterization; first per-layer error budget |
| G5 Own layout | KiCad revision driven by G3–G4 results; checks; human review; fabrication | Connectivity, DRC and review sign-off |
| G6 Closure | Own board measured; back-fit; closure report; checkpoint log | End-to-end run with a record of which checkpoints needed a human |

Status, 28 September 2026:

- **G1** is open. LTspice 26.1.1 is installed and pinned. The adapter passes its known-answer fixtures, runs the unmodified vendor model, and, after review, rejects failed runs it previously reported as completed. Still missing: the comparison with an interactive GUI run.
- **G2** is open. The datasheet-table baseline runs with convergence and equation checks. The gate-charge curve (Fig. 7) matches within 0.014 V, and the table's subcharge differences are traced to the table's own boundary definitions. Still missing: the other datasheet curves.

G1 and G2 can proceed in simulation while G0's lab inventory is completed. No
hardware is energized before G4's test plan and interlocks are approved.

## 9. Open decisions for the project owner

1. Confirm the provisional EPC9097/EPC2204 target once the test envelope and
   equipment are known.
2. Available licenses (PSpice, Spectre) and whether LTspice may be installed
   on the lab and development hosts.
3. Lab inventory: oscilloscope and probe bandwidth, isolated or differential
   probes, current sensing, supplies, electronic load, temperature control.
4. Whether to request EPC's Altium files, and the budget for fabricating
   boards.
