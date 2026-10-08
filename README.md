# GaNCircuit

GaNCircuit is a research project on using software agents to help design and test GaN power circuits. The aim is to connect the whole engineering process: read a transistor datasheet, check its simulation model, account for the circuit board's layout, measure the hardware, and explain where the predictions agree or disagree with the measurements.

The current target is EPC's **EPC90133 development board**, which uses two **EPC2302 100 V GaN transistors** and a **uP1966E gate driver**. The two transistors form a half-bridge: they take turns connecting an output node to the supply or ground. This is a basic building block of power converters.

GaN devices switch fast enough that small amounts of inductance in the board, package and gate connections can cause substantial voltage spikes and ringing. Understanding those effects is central to this project.

## Current status

**The simulation workflow runs, but the board predictions are not yet validated. Preparing for our own measurements is the priority.**

As of 7 October 2026:

| Area | What works | What remains open |
|---|---|---|
| Transistor model | The original EPC2302 model runs in LTspice. It passes the checks for 24 datasheet curves and the limited table rows tested. | The gate-charge curve fails. Switching times and losses that depend on gate charge remain unvalidated. |
| Board simulation | The published layout has been read, power and gate paths extracted, and switching cases compared with EPC's waveform. | No tested case passes every waveform criterion. Board extraction is still exploratory. |
| Measurements | A draft test plan, proposed probe locations and preparation studies are available. | The exact lab equipment, actual board identity and approved first-power procedure are still needed. No project hardware measurements are reported. |
| Software agents | Agents have reproduced script results, passed results between stages and stopped on deliberately changed inputs. | These are execution tests. They do not demonstrate independent engineering judgement or a validated automated measurement loop. |
| New board design | The KiCad reconstruction reproduces EPC's saved geometry and passes the independent net readback. A qualified edit workflow moves parts and vias and reshapes copper areas while keeping the rest of EPC's copper unchanged. | Edited boards now feed the inductance extraction. The first candidate, input capacitors 0.4 mm closer to the transistors, changed loop inductance by under 1 %, below what the extraction can resolve. Nothing is approved for fabrication. |

The simulation baseline is frozen. Broad parameter sweeps and further diagnosis of the ringing are on hold unless they answer a specific decision. The stock-board simulation checkpoint, **G3**, remains open.

For detailed results and replay instructions, see the [build notes](docs/build.md). The [project plan](plans/gan-halfbridge-pipeline-plan.md) defines the scope, stage interfaces and approval checkpoints.

## What the project is building

The work is divided into three student-owned stages. A stage can use ordinary scripts, software agents, or both; the project does not require exactly three agents.

| Stage | Main task | Output |
|---|---|---|
| 1. Datasheet to model | Run the vendor model and compare it with the datasheet under the stated conditions. | A model report with passing checks, discrepancies and limits on its use. |
| 2. Layout-aware simulation | Add the board's electrical connections, resistance, inductance and coupling to the circuit simulation. | Predicted waveforms and performance, with the layout, assumptions and checks recorded. |
| 3. Test and explain | Measure the board and compare the results with predictions made before the test. | A report explaining agreement, remaining errors and what should change next. |

Each stage passes versioned, machine-readable records to the next. Those records identify the exact inputs, conditions, units, checks and unresolved issues. A result should remain traceable to the model, layout and settings that produced it.

The core scope includes switching charge, dead time, double-pulse tests, efficiency measurements, room and elevated temperatures, and one revised PCB taken through review and fabrication. Dynamic on-resistance, detailed output-capacitance losses, soft switching and further boards are extensions. Redesigning the commercial transistor itself is outside the scope.

One matching waveform cannot separate transistor, layout, driver and probe errors. Each needs its own evidence. The original vendor model stays as the baseline; any tuning must be justified by device-level evidence and saved separately.

## Stage 1: checking the EPC2302 model

The project's [LTspice adapter](src/circuit_tools/ltspice.py) writes test circuits, runs LTspice in batch mode, reads waveforms and checks whether the run completed correctly. The unmodified EPC2302 model runs through this adapter with `reltol=1e-6`; the default tolerance was too loose for gate-charge integration.

The results are:

- **Datasheet table:** the tested rows with specified limits are inside those limits. Total gate charge is about 4% below the typical value. This is a limited table check, not verification of every device specification. See the [table report](results/gan/epc2302-baseline.json).
- **Datasheet curves:** all 24 curves in Figures 1–6 and 8–10 pass the declared checks. They were digitized from the PDF's vector drawings. Their very close agreement suggests they may have been drawn from the same model, so the result mainly supports correct model execution. See the [curve comparison](results/gan/epc2302-curve-comparison.json).
- **Gate charge, Figure 7:** the model's Miller plateau is narrower than EPC's curve (about 16–24%, depending on how the curve is sampled), and charge after the plateau is about 1.2 nC low. The cause and the table's QGD/QG(TH) discrepancies remain unresolved. See the [gate-charge comparison](results/gan/epc2302-fig7-comparison.json). A separate sensitivity revision of the model that follows Figure 7 [exists](results/gan/epc2302-qg-variant.json), but it puts the reverse-transfer capacitance 23% above Figure 5. The tested parameter scaling does not match both figures. A different representation does: **EPC2302DS** adds two small charge steps, placed where the gate-charge test goes but the capacitance curves do not, and passes Figure 7 together with all 24 other curves and every existing table and numerical check ([report](results/gan/epc2302-ds-variant.json)). It is a calibration to EPC's published curves, not identified device physics. The leakage, breakdown and reverse-recovery rows and the thermal and rating data are not yet checked for any model, so it does not yet cover the whole datasheet. With either model, the R80 1.5 Ω design candidate meets its constraints ([assessment](results/gan/epc90133-qgfit-assessment.json)).

The original model remains the reproducible **provisional baseline**. Owner clarification (8 October 2026): trust both the capacitance curves (Figure 5) and gate-charge curve (Figure 7) as required datasheet targets. A separately stored datasheet-calibrated candidate must pass both and preserve the other passing checks; neither existing model meets that joint requirement. The goals study's Figure 7-primary results retain their recorded model and limitations. Agreement with the datasheet is distinct from validation against hardware.

## Stage 2: modelling the board

### Reconstructing the published layout

The EPC90133 BOM and manufacturing files describe an eight-copper-layer board, B5253 Rev 2.0. The project reads the Gerber and drill files, identifies supply, ground and switch-node copper, and locates component contacts and vias. It also has a transcribed schematic and a map of the gate-drive paths.

![EPC90133 top copper and power-loop connections](results/gan/epc90133-power-loop/top.png)

*The published power stage: input supply in red, switch node in green and ground in blue. The power-loop return runs through an inner ground layer.*

The board has two stacked power loops: one through the nearby top-side capacitors, and another through lower copper layers and bottom-side capacitors. Via clearances leave slots in the inner return planes, which makes their representation in the extraction important.

The file audit also found unresolved differences: the schematic names uP1966A while the BOM names uP1966E, and the guide's J32 switch-node connector has no footprint in the published layout. One published layout has been found; it still needs to be checked against the board received by the lab.

See the [source inventory](devices/epc/epc90133-sources.json), [board audit](results/gan/epc90133-board-audit.json), [power-loop report](results/gan/epc90133-power-loop.json) and [gate-loop report](results/gan/epc90133-gate-loop.json).

### Extracting resistance and inductance

FastHenry converts the copper geometry into an electrical network. The circuit keeps the coupling between branches, including the gate and return paths. The loop-inductance numbers below summarize the variants; they are not substitutes for those networks.

| Variant | Included geometry | Approximate power-loop inductance |
|---|---|---|
| A | Top copper and first inner layer, nearby capacitors | 0.49–0.50 nH |
| I | All copper layers, nearby capacitors | 0.30 nH |
| B | All copper layers, nearby and bottom-side capacitors | 0.26–0.28 nH |
| G | B plus gate-drive paths and separate source contacts, with a finer top-layer grid | 0.26 nH |

These values are **exploratory estimates**. Changing the via-to-plane connection model changes B's loop inductance by up to 7%. No second full-board mesh has been run, so board-level mesh convergence has not been established.

Tool checks give a mixed picture:

- FastHenry passes known-answer checks for bars and plane pairs. A single-via benchmark passes its inductance check after a fourth mesh refinement; its resistance is still changing.
- Via-array checks pass some criteria and fail others. At the board's pitches, mutual-inductance ratios differ from the independent reference by up to about 20%. A single-via value cannot be divided by the via count.
- Slot checks also have mixed results. Board-pitch results differ by −52% to +68% from the finest mesh run, which is itself unconverged. The production board grid partly fills the slots with its finite-width segments.

These benchmark results identify weaknesses in the method. They do not establish error bars for the board. See the [extraction qualification notes](docs/build.md#via-array-plane-hole-and-fastercap-qualification-plan-review-and-first-bounded-step-2-october-2026).

Capacitance extraction is unfinished. FasterCap passes some simple checks, but is **not qualified for 3D board use**. Early 3D results were unphysical. Explicit meshes produce physical results, and a separate 2D calculation points to coarse edge panels as the likely cause of the remaining shortfall. The refined 3D check was stopped before it produced a complete result. The switching studies still use a stated capacitance estimate.

### Comparing simulation with EPC's waveform

The switching bench combines the EPC2302 model, a behavioural driver model and an extracted board network. It uses a double-pulse test with the edge currents matched to EPC's published buck-converter waveform. Periodic buck checks agree within 1.3% on A and 0.7% on B under the tested ideal-supply, 25 °C conditions. That comparison does not establish equivalence for every model variant or operating condition.

The reference is **Figure 9 of EPC's quick-start guide**, at 48 V input, 13.8 V output, 20 A and 250 kHz. The project digitizes the screenshot and compares usable simulations under several assumed probe bandwidths.

The screenshot's time scale passes a check against EPC's printed rise and fall times. Its voltage swing reads 5–7% below 48 V, so the voltage-scale check fails. The following measured values therefore retain that limitation; their extraction ranges are not a complete measurement uncertainty.

| Quantity | EPC Figure 9 | Variant B | Variant G + assumed 50 pH package source inductance |
|---|---|---|---|
| Rise time | 1.67–1.69 ns | 0.83 ns | 1.66 ns |
| Overshoot above the supply | 5.7 V | 35.0 V | 11.3 V |
| Ringing frequency | 262–265 MHz | 284 MHz | 262 MHz |
| Damping ratio, which describes how quickly ringing decays | 0.072–0.077 | 0.008 | 0.025 |
| Fall time | 3.62–3.64 ns | 3.96 ns | 3.93 ns |

*Simulation values use the ideal-probe results in the [generated comparison summary](results/gan/epc90133-fig9-summary.md).*

![Published waveform compared with four simulation variants](results/gan/epc90133-fig9-overlay-g.png)

*Black: EPC's waveform. Blue: B. Orange: B with assumed shared source inductance. Green: G. Red: G with assumed package source inductance. Adding the gate paths and package assumption improves parts of the turn-on waveform, but the simulated ringing still decays too slowly.*

**No tested case meets all the comparison criteria.** In particular, matching rise time and ringing frequency does not explain the overshoot or damping.

### What the studies have taught us

The studies narrow the questions for measurement:

- **Gate-drive connections matter.** Including the board's gate paths reduces overshoot substantially. Controlled comparisons support magnetic coupling between the high-side gate path and the power loop as one mechanism within the model. Layout has not been ruled out as a cause of the remaining gap.
- **The driver is not fully characterized by its datasheet edge times.** Two representations that meet the selected resistance and edge-time constraints produce substantially different overshoot. The actual gate waveform needs to be measured.
- **Package inductance could matter, but its value is unknown.** The assumed 50 pH case matches some waveform features and still fails others. It does not identify the real package inductance.
- **Damping remains unexplained.** Added capacitor loss can increase damping but barely reduces the first peak. Full extracted resistance has little effect in the B transient study. Partial transistor turn-on raises local damping but does not explain the matched ringing cycles. The energy study does not support a physical heat-loss breakdown.
- **Probe location explains part of the overshoot gap, not the damping.** Reading the simulated switch node where
  EPC's guide places the probe (the J33 holes) instead of at the transistor lowers the overshoot from 11.2 to 9.2 V
  (EPC's waveform: 5.7 V) and produces part of the dip on the falling edge. The damping is unchanged, so the
  missing ring loss still needs another explanation.
- **Probe bandwidth alone is insufficient.** The tested bandwidth filters do not close the gap. Probe loading, connection location and resonances remain untested. A fixed added gate capacitor also does not resolve or bound the voltage-dependent gate-charge discrepancy.
- **Low-side gate spikes and driver-pin stress still need measurements.** Sampled model traces show no appreciable positive low-side channel current during the examined turn-on windows. This does not establish immunity to false turn-on in hardware. Driver PHASE-pin voltage extremes remain unresolved and depend strongly on driver-model assumptions.

- **A stock-board design change is selected for testing.** The goal is lower switch-node overshoot, with FET loss at most 5 % above stock and no larger low-side gate spike. Under those constraints the best of the tested part swaps is a 1.5 Ω high-side turn-on resistor instead of 1 Ω. It meets the constraints under all four unresolved driver and package assumptions, and it lowers the worst-case simulated overshoot by about a third. With an assumed 50 pH package inductance, the gain shrinks to 4-11 %. Larger resistors cut overshoot further but exceed the loss limit. Tested layout changes, a thinner power-loop dielectric and extra return vias, gave smaller or no gains. These are model rankings to be checked on the purchased board.

Failed, incomplete and invalid cases remain in the record and are excluded from acceptance verdicts. Numerical checks include spike detection and selected smaller-time-step runs. Passing those checks establishes only their stated scope, not overall physical accuracy. The [build notes](docs/build.md) preserve the individual studies and their limitations.

## Layout goals: what can change and what it achieves

The owner's design template sets thirteen goals (S1-S13) and fixes the bill of materials, schematic and topology. It
allows changes to copper, vias and component positions on the switching paths. The open limits follow common
industry practice: inner dielectric 0.075-0.127 mm, and parts moved at most 1 mm (an assumption, as there is no
standard for this). Results use the EPC2302DS model and an assumed 50 pH package inductance. Loop inductance changes
come from a partial board model used for ranking.

| Changeable | Tried | Result | Goals it can move |
|---|---|---|---|
| Power-loop vias | V6-V9: thin the via rows under the transistors so the return plane runs closer | V8 lowers loop inductance 12.5 %; thinning further adds little | S2, S3, S10 only through inductance |
| Inner dielectric | 0.100, 0.075 mm (and 0.050 mm as a check) | 0.075 mm alone -13 %; with V8 -28 % (-36 % at 0.050 mm) | same as above |
| Decoupling capacitor positions | Input capacitors 0.4 mm closer (all the room available) | Under 1 % | same as above |
| Capacitor return vias | Planned | Not built | same as above |
| Transistor and driver positions | Move tool qualified | Not built | mainly inductance; driver position affects the gate loop |
| Gate loop / Kelvin return | Ideal gate loop simulated as a bound | Low-side gate spike still 1.1-1.3 V against 0.5 V | S8: not reachable while the package inductance is shared |
| Switch-node copper area | Reasoned only | Would need about 10 times the existing switch-node capacitance to move the dead-time optimum | S11: not reachable |

What the bounds show, given the fixed parts:

- **S2 overshoot (at most 9.6 V)** needs the whole board's inductance cut to about half. The best legal combination
  reaches about -28 %, where the simulated overshoot is still about 11 V.
- **S10 switching energy (-10 %)** cannot be met: most of it is the transistors' own output-charge loss, fixed by the
  parts, and lower inductance raises the rest.
- **S8 false turn-on**, **S11 dead time** and **S12 efficiency** are set by the package, the operating point and
  the transistors, not by copper, in this model.
- The best candidate, V8, passes **S1, S4 and S7**. It narrowly misses **S3 settling** (133.2 against 131.5 ns) and
  **S6 di/dt** (30.9 against 29.9 A/ns), both within about 3 % of the baseline.

With the parts fixed, the goals pull against each other: lowering the power-loop inductance lowers overshoot (S2)
but speeds up the current change (S6) and raises switching energy (S10). No copper change can improve all three
against the baseline, so further layout iterations only trade one goal for another.

These verdicts depend on the assumed package inductance and on the unexplained damping difference from EPC's
measured waveform, so they are simulation results to be checked by measurement, not hardware limits.

## Stage 3: preparing for measurements

The owner decided to purchase an EPC90133. Receipt, revision and fitted components have not yet been confirmed in the project record. The lab has a Keysight B1506A and PD1550A, which test devices in their own fixtures; their availability does not establish a setup for measuring this assembled board. The board-test equipment inventory is still needed from the lab's responsible person.

The [hardware test plan](docs/epc90133-hardware-test-plan.md) is a draft, not an approved executable procedure. It covers probe characterization, driver timing with the power bus off, switching at several currents and voltages, gate-resistor changes, temperature and efficiency. Some conditions will be reserved to test predictions without using them for fitting.

Preparation completed so far includes:

- **Probe locations on the published layout.** Candidate points exist for the switch node, low-side gate and driver PHASE-to-ground voltage. Their connection paths and loading need checking with the actual board and selected probes. Connector fitting is deferred to the lab's review.
- **Driver supply and bootstrap simulation.** This bounded study shows that a bus-off gate measurement could distinguish the two driver models. A short pre-charge leaves the high-side gate supply below the switching bench's ideal 5 V. Its original charge-balance check failed because the declaration omitted a recharge path; that failure is kept. Start-up without a low-side pulse and dead-time overcharge remain unanswered. See the [assessment](results/gan/epc90133-driver-only-assessment.json).
- **Input-logic review, 5 October.** The current [report](results/gan/epc90133-input-logic-rev3.json) checks the transcribed logic against the BOM, logic function table and guide settings. It identifies input and jumper combinations that can command both gates on. Its calculation from datasheet limits does not guarantee positive dead time. This is a static check, not a timing or start-up measurement, and does not qualify shoot-through protection.

The next dependency is the equipment inventory and actual board identity. Those allow the draft to become a reviewed channel plan and first-power procedure, followed by characterization, frozen predictions and approved measurements. The [active work order](plans/gan-halfbridge-pipeline-plan.md#10-immediate-work-and-dependencies) is maintained in the plan. Further simulation needs a named decision it could change and a bounded stop rule; waiting for equipment alone does not justify another study.

Hardware protection must remain independent of any language-model agent. The uP1966E has no input lockout, and simulated voltage peaks do not establish a safe operating envelope. No EPC inquiry is planned under the owner's current decision.

## What has been demonstrated with agents

The agent experiments test whether an agent can execute a specified workflow, preserve its records and stop when inputs are unacceptable.

| Experiment | Result | Limit of the result |
|---|---|---|
| [Milestone 1](results/gan/agent-milestone-1.json) | One clean comparison matched the script baseline; one corrupted-input run stopped correctly. | A bounded execution task with no engineering decision. |
| [Milestone 2](results/gan/agent-milestone-2.json) | Four clean runs and five fault runs behaved as specified. | The containment check detects new git-status changes, not writes to ignored files. |
| [E2E-0 pilot](results/gan/e2e-pilot.json) | Agents ran model checks, extraction, switching and assessment through versioned handoffs. The clean run matched the reference; a model changed after handoff was rejected. No interventions were needed. | A simulation-only, non-blind test. The assessment is not hardware closure. |

The clean E2E-0 agent run took about 33 minutes and 347,000 tokens, compared with 21.6 minutes for the successful script reference. Its engineering results remained provisional throughout. A draft judgement evaluation was not run because the expected answers were accessible. Agent runs use the normal project context and tools, as in real use. Judgement is tested on material whose answer is not written down anywhere: predictions frozen before a measurement and scored against it.

The pilot therefore demonstrates useful execution and handoff behaviour, while the value and cost of broader agent use still need review. Measurement readiness takes priority over another target.

## Tools and repository guide

| Tool | Role and current status |
|---|---|
| Python 3.10+ and `circuit_tools` | Simulation adapters, geometry, analysis, input records and reports. Studies use NumPy, SciPy, Pillow, Matplotlib and other listed dependencies. |
| LTspice 26.1.1, Windows | Runs the vendor model and board circuits. Adapter checks pass; this does not validate every model. |
| FastHenry 3.0.1, WSL | Resistance and inductance extraction. Qualified for specific simple geometries; board use remains exploratory. |
| FasterCap 6.0.7, WSL | Capacitance extraction under investigation. Not qualified for 3D board use. |
| PyMuPDF, openpyxl and xlrd | Read datasheets, digitize curves, and read BOM and stackup files. |
| KiCad 10.0.6 | Saved EPC geometry reconstructed and independently checked; geometry-edit workflow qualified for moving parts and vias and reshaping copper. |

| Location | Contents |
|---|---|
| [src/circuit_tools/](src/circuit_tools/) | Reusable library, simulator adapters, Gerber reader and artifact handling. |
| [scripts/](scripts/) | Studies and evaluators; each study's docstring states its method and checks. |
| [devices/](devices/) | Vendor source records, checksums, reuse terms and transcribed circuit information. |
| [results/](results/) | Saved reports, including unsuccessful runs. Read the status inside each report. |
| [docs/build.md](docs/build.md) | Detailed results, setup and replay instructions. |
| [plans/gan-halfbridge-pipeline-plan.md](plans/gan-halfbridge-pipeline-plan.md) | Scope, responsibilities, interfaces, decisions and acceptance gates. |
| [tests/](tests/) | Automated tests for the tools and result checks. |
| `vendor/`, `runs/`, `.tools/` | Git-ignored vendor downloads, simulation working files and local tool builds. |

### Running the work

Start with the setup and replay instructions in the [build notes](docs/build.md). A fresh clone does not include vendor files or external solvers, and `pyproject.toml` does not install all study dependencies. Retrieve files according to the records in `devices/` and configure the required tools before running a study.

Examples from the repository root in PowerShell, with the configured Python environment active and `python` on `PATH`:

```powershell
$env:PYTHONPATH = 'src'
python -m pytest -q tests
python scripts/verify_ltspice_fixtures.py
python scripts/epc2302_baseline.py
python scripts/epc90133_power_loop.py
```

These commands cover the tests, LTspice adapter checks, model table comparison and board geometry. Extraction and switching studies have additional inputs and can take hours. Use the recorded commands for the desired study; comparison defaults do not regenerate the complete multi-study summary. Read output paths before rerunning, as some scripts update saved reports.

On the current host, WSL is capped at 8 GB. Run one large B extraction case at a time, and profile long solver jobs before choosing their time limits. The latest recorded full-suite check passed on Windows and WSL; that is a software check, not hardware validation.

### Source files and reuse

Every EPC file needs a source URL, retrieval date, checksum and reuse terms. Public availability does not grant unrestricted redistribution. Vendor files and local solver builds are kept outside git.

FastHenry's MIT-authored notice is **not the standard MIT License**: the recorded permission covers internal non-commercial use and prohibits redistribution. FasterCap uses LGPL 2.1 or later. See the source and tool records before reusing either beyond the project's recorded scope.

Gerbers and PDF schematics provide manufacturing and circuit information; they do not constitute an editable, connected KiCad design. EPC lists Altium files as available on request. The project instead rebuilds an editable KiCad 10 design from EPC's Gerbers and layout PDF (`scripts/epc90133_reconstruct*.py`; [docs/build.md](docs/build.md) "track R"). The rebuilt design has EPC's copper, 106 parts with footprints taken from the board's own pads, EPC's net names, vias with rings measured from EPC's copper, and EPC's stackup and clearance rule. Its exported Gerbers and drill file reproduce EPC's exactly. KiCad's design-rule check finds no shorts and no unconnected pads, and every remaining finding has a declared explanation. The design is a derivative of EPC's layout, so it is kept out of this repository. A separate check reads the saved design back through KiCad and confirms that each of the 288 pads in EPC's netlist carries EPC's net. The copper pours are EPC's shapes frozen as drawn. A plain KiCad refill does not reproduce them: about 1-2 % of the copper area changes in the power and gate region, because KiCad regenerates EPC's clearance holes from a single rule. The edit workflow (`scripts/epc90133_edit_workflow.py`) therefore marks every stock hole as an area where KiCad may not pour copper. With that, a refill reproduces EPC's copper within 10 µm, and moving a part or a via changes copper only where the edit requires. A separate reshaping step adds or cuts rectangular copper regions and keeps the required gap to other nets; it is also qualified.

## Related and deferred work

- **EPC9097 / EPC2204:** the earlier target, retained as reference. It established reusable LTspice and digitization methods; its results do not qualify the EPC2302 or EPC90133.
- **EPC9165:** a possible second board, with its files and probe access reviewed. Purchase is deferred until EPC90133 measurements leave a question that this board could help answer. See the [selection note](docs/second-board-selection-2026-10-01.md).
- **Silicon NMOS / DEVSIM:** a paused development fixture that produced reusable runner, revision and artifact tools. See the [earlier toolset plan](plans/autonomous-circuit-toolset-plan.md).

The long-term deliverable remains a measured, reviewed circuit improvement and a documented account of which engineering tasks agents can perform reliably, where humans are still needed, and what the evidence actually supports.
