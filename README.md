# GaNCircuit: an agent-driven GaN power-electronics pipeline

## What the project is

GaNCircuit builds a largely automated path from a power transistor's datasheet to a tested circuit board. It
has four steps:

1. Qualify the manufacturer's simulation model of the transistor.
2. Simulate the transistor on its real board, including the board copper's electrical side effects.
3. Measure the real board safely.
4. Use the gap between prediction and measurement to improve understanding and, later, the board design.

The long-term aim is for software agents to carry out much of this loop. They would work through versioned
artifacts, declared checks and recorded decisions, with humans at safety-critical points.

The subject is the **EPC2302**, a 100 V gallium-nitride (GaN) power transistor from EPC, on EPC's **EPC90133**
development board. The board is a *half-bridge*: two EPC2302s in series, driven by a uP1966E gate driver. The upper
switch (Q1) and the lower switch (Q2) take turns connecting the *switch node* to a 48 V supply or to ground. That
produces the square pulses at the heart of most power converters, such as a buck converter stepping 48 V down.

GaN transistors switch in about a nanosecond. At that speed, a few tenths of a nanohenry of stray inductance in the
board copper produce voltage spikes and ringing large enough to matter for losses, noise and device stress.
Predicting the switching waveform therefore needs both a good transistor model and a good description of the
layout.

```mermaid
flowchart LR
    DS["EPC2302 datasheet"] --> M["Vendor model<br/>in LTspice"]
    M -->|"Stage 1: compare<br/>with datasheet graphs"| CHK1{{"24 of 25 match"}}
    G["EPC90133 layout files<br/>(8 copper layers)"] --> GEO["Board geometry,<br/>nets, footprints"]
    GEO --> FH["FastHenry:<br/>copper inductance"]
    M --> SW["Switching simulation"]
    FH --> SW
    SW -->|"Stage 2: compare with<br/>EPC's measured waveform"| CHK2{{"does not match yet"}}
    SW -.->|"Stage 3"| HW["Measurements on<br/>real hardware"]
```

The full plan, with its checkpoints (gates G0–G6), stage interfaces and safety rules, is in
[plans/gan-halfbridge-pipeline-plan.md](plans/gan-halfbridge-pipeline-plan.md).

## How the pipeline is organised

The work falls into three stages. Each has its own inputs, outputs and acceptance checks, so every layer of error can be
bounded with its own evidence:

| Stage | Question | Evidence it uses |
|---|---|---|
| 1. Device | Does the vendor model, run in our simulator, reproduce the datasheet? | datasheet tables and graphs |
| 2. Board | Does the model on the extracted board reproduce the board's switching waveform? | layout files, EPC's published waveform |
| 3. Measurement | Does the prediction hold on real hardware, including at conditions not used for tuning? | our own measurements |

One matching waveform cannot tell a transistor error from a layout error or a probe error. For that reason the
stages are kept separate, and the vendor model is never tuned to make a board waveform fit.

## Stage 1: the transistor model

EPC supplies an LTspice model of the EPC2302. The project runs it through its own LTspice adapter
(`src/circuit_tools/ltspice.py`). The adapter writes the test circuit, runs LTspice in batch mode, reads the waveforms
and reports failures honestly: a simulation that needed convergence fallbacks counts as failed, not as a result.
One scoped exception exists, for small-signal checks only: an operating point that LTspice reached through fallbacks
is accepted if a rule declared beforehand checks the solved state itself (bias voltages within stated limits, a
complete sweep), and such results are flagged.

- **Datasheet table.** Every table value that has a limit falls inside it. Capacitances, output charge and on-resistance
  are within 0.2–7 % of their typical values; total gate charge is 4 % low
  ([table comparison](results/gan/epc2302-baseline.json)).
- **Datasheet graphs.** The graphs are digitized from the PDF's vector drawings, calibrated from the plot frames and grid.
  24 of 25 graphs match closely ([comparison](results/gan/epc2302-curve-comparison.json)). The match is so close that EPC
  probably drew them from the same model. That shows our simulator runs the model faithfully, not that the model matches
  real parts.
- **The exception: gate charge (Fig. 7).** The model's Miller plateau is 24 % narrower than the datasheet curve, and its
  charge after the plateau is about 1.2 nC low ([Fig. 7 comparison](results/gan/epc2302-fig7-comparison.json)). The cause
  is not known. Simulated switching times and switching losses depend on gate charge, so they are not treated as
  validated.
- **Model status.** The unmodified model is the provisional baseline for the board stage. A tuned model would be stored
  as a separate revision, and only if device-level evidence isolated the discrepancy to the transistor. Simulations use
  `reltol=1e-6`, because the default tolerance under-integrates gate charge.

## Stage 2: the board

### Reading the layout

EPC publishes the board's manufacturing files: the BOM, and Gerber and drill files for 8 copper layers with about 450 vias
([audit](results/gan/epc90133-board-audit.json)). Our Gerber reader (`src/circuit_tools/gerber.py`) rasterizes each
layer. `scripts/read_epc90133_geometry.py` then assigns copper to nets such as the input supply, switch node and ground
([geometry](results/gan/epc90133-geometry.json)). A schematic transcribed from the BOM
([devices/epc/epc90133-schematic.json](devices/epc/epc90133-schematic.json)) passes a static connectivity check.

`scripts/epc90133_power_loop.py` locates the transistor and capacitor contacts from the solder-mask and paste layers. It
checks them against the EPC2302 footprint (size, orientation, gate, source and drain pins) and defines exact electrical
ports for extraction ([power-loop overlay](results/gan/epc90133-power-loop.json)).

![Top layer of the EPC90133 power stage: VIN in red, switch node in green, ground in blue, with the two transistors (Q1, Q2), the Ci capacitor row and the via groups](results/gan/epc90133-power-loop/top.png)

*Top copper layer around the two transistors, drawn from EPC's files. Red is the input supply (VIN), green the switch
node (SW), blue ground (GND). The numbered rectangles are the transistor pins; dots are vias. The arrows show the
switching current's path: from the capacitors (top) through Q1 and Q2, then down through vias to the ground plane below.*

![Cross-sections through the board showing all eight copper layers and the vias under Q2](results/gan/epc90133-power-loop/sections.png)

*Side views cut through the board (height exaggerated). Each row of colour is one copper layer, and vertical bars are
vias. The switch-node vias pass through holes in the ground layers, leaving slots in the return path.*

The board has two stacked power loops. One runs on the top layer over mid-layer 1 through the input capacitors next to
the transistors (Ci). The other runs through the lower layers to capacitors on the bottom side (Cm).

`scripts/epc90133_gate_loop.py` maps the gate-drive loops the same way
([gate-loop geometry](results/gan/epc90133-gate-loop.json)). It covers:
- the driver's ball pattern;
- the gate resistors (1 Ω on turn-on, 0 Ω on turn-off);
- each transistor's gate pin;
- the source pins that the driver returns to.

### Extracting the copper's inductance

`scripts/epc90133_extract.py` turns the copper into a FastHenry model and computes the inductance and resistance of every
branch between the ports. It keeps the mutual coupling between branches in the circuit, instead of reducing the board
to one loop-inductance number. Several representations of the board are extracted, so that modelling choices show up
as sensitivities:

| Variant | Copper included | Power-loop inductance |
|---|---|---|
| A | top layer and mid-layer 1, Ci capacitors | 0.49–0.50 nH |
| I | all copper, Ci capacitors | 0.30 nH |
| B | all copper, Ci and Cm capacitors | 0.26–0.28 nH |
| G | B plus the gate-drive loops and split source pins, with a finer mesh on the top layer | 0.26 nH (one mesh) |

- **Deeper layers.** The deeper copper layers lower the loop inductance by about 40 %.
- **Via representation.** Three via-to-plane junction models change the result by under 2 % on A and up to 7 % on B.
- **Mesh.** Only the coarse mesh has been run on the full board, so these numbers carry no mesh-convergence evidence.
- **Qualification.** FastHenry passes known-answer checks for bars and plane pairs ([result](results/gan/fasthenry-known-answer.json)).
  A single via in a plane pair converges with a fourth, finer mesh ([result](results/gan/fasthenry-via-cavity-mesh4.json));
  with three meshes it had failed its mesh criterion. That benchmark does not cover the board's via arrays, plane holes
  or the slotted return plane under the transistors, so those are not qualified and board extractions stay exploratory.

### Simulating the switching

`scripts/epc90133_switching.py` combines the vendor model, a behavioural uP1966E driver calibrated to its datasheet and an
extracted board network. It runs them in a *double-pulse* test: one turn-off and one turn-on, at the same inductor
currents as EPC's published buck waveform. A continuous (periodic) buck simulation gives the same edges within 1.3 % on
A and 0.7 % on B, so the simpler test stands in for continuous operation.

Every case carries its own numerical checks:
- no single-step voltage spikes;
- a rerun at half the time step for selected cases (in the gate-path study, G itself was rerun at first; its
  package-inductance variants and controls were not, and G + 50 pH was checked later, see below);
- convergence without fallbacks.

Cases that fail are kept for inspection but receive no verdict. Device quantities are taken at the transistor's die
terminals and switch-node quantities at the pads.

### Comparing with EPC's measurement

The only published board measurement is EPC's switch-node waveform in the quick-start guide (QSG Fig. 9: 48 V to
13.8 V, 20 A, 250 kHz). `scripts/digitize_epc90133_qsg_fig9.py` reads it from the screenshot pixels with a declared
method and reports how much each reading depends on the extraction choices (one pixel is 0.2 ns and 0.31 V). The time
scale checks out against EPC's printed rise and fall times. The voltage scale reads 5–7 % short of the 48 V swing, and
that failed check is recorded ([digitized values](results/gan/epc90133-qsg-fig9.json)).

`scripts/compare_epc90133_fig9.py` compares each usable simulation with the measurement. It passes the simulation
through a range of assumed probe bandwidths (2 GHz to 350 MHz) and applies acceptance criteria fixed before the
comparison. The headline table is generated in [results/gan/epc90133-fig9-summary.md](results/gan/epc90133-fig9-summary.md).

| | Measured (Fig. 9) | Simulated, variant B | Variant G + 50 pH package source (assumed) |
|---|---|---|---|
| Turn-on rise time | 1.67–1.69 ns | 0.83 ns | 1.66 ns |
| Overshoot above the bus | 5.7 V | about 35 V | about 11 V |
| Ringing frequency | 262–265 MHz | 284 MHz | 262 MHz |
| Ringing damping ratio | 0.072–0.077 | about 0.008 | about 0.025 |
| Turn-off fall time | 3.62–3.64 ns | 3.96 ns (within the fall-time criterion) | 3.93 ns |

For variant B, the ringing frequency and the turn-off edge are close, but the turn-on edge is too fast and its
ringing far too large and too slowly damped. With the board's gate-drive copper (variant G) and an assumed package
inductance, rise time and frequency match; the overshoot is still twice the measured value and the damping a third.
The package value is an assumption, so this is consistency, not identification.

![EPC's measured waveform against four simulated cases](results/gan/epc90133-fig9-overlay-g.png)

*EPC's measurement (black) against the simulation with:*
- *the power loop as extracted, variant B (blue);*
- *variant B plus an assumed 50 pH in the source path shared with the gate driver (orange);*
- *variant G, which adds the board's gate-drive copper (green);*
- *variant G plus an assumed 50 pH of package source inductance (red).*

*The turn-off edge (right) matches. At turn-on (left) the gate-drive copper and the assumed package inductance each
lower the first peak, and the red case matches the measured rise time and frequency. Every simulated ring still
decays far more slowly than the measured one, which dies out within about three cycles.*

### What the diagnosis shows so far

Candidate causes were added one at a time, each with its own numerical checks. The results below hold for the
approximations stated; none of them yet reproduces the measurement on every criterion.

- **The board's gate-drive copper matters.** Extraction G adds the driver, gate resistors and each transistor's
  gate and source return to the extracted network. With it, the overshoot falls from about 36 V to 25 V. A matched
  control (same network, ideal gate drive) and two split cases separate the causes:
  - about a third of the drop comes from G's slightly different network (8 % less loop inductance);
  - the rest comes from the high-side gate-drive path. Its gate return shares almost no source copper with the
    power loop (0.9 pH). A calculation from the extracted network supports magnetic coupling of the forward gate
    path (driver, gate resistor, gate) as the mechanism within this model: at 100 MHz and zero gate current it is
    equivalent to about 10 pH of common-source inductance, which would slow the high-side turn-on. That calculation
    does not separate the coupling from the gate path's own impedance during switching;
  - the low-side path adds damping. It also produces a spike of about 2 V at the low-side transistor's model
    terminals during the high-side turn-on. Inside the model, behind its internal gate resistance, the
    channel-control voltage stays below about 1 V and the sampled traces show no appreciable positive channel
    current, so this is not evidence of false turn-on in the model; the real device still needs a measurement. Its gate return shares 48 pH with
    the power loop. A lower overshoot bought this way is not a better design.
- **Common-source inductance in the package** is one candidate among several. Adding an assumed 50 pH of package source
  inductance to G gives the measured rise time (1.66 ns) and frequency (262 MHz), with an overshoot of 11 V, twice
  the measured value. Overshoot and damping still fail. Halving the time step changes its five reported
  switching metrics by under 0.04 % (stability over two steps, not general convergence). The package value is assumed, not published, so this is
  consistency, not identification. The same inductance placed where the gate driver does not share it behaves like
  extra loop inductance and makes the overshoot worse.
- **Gate-loop inductance** alone, without coupling, of 0.5–2 nH changes the overshoot by only 3–10 %.
- **The driver's output stage** sets how strongly the edge excites the ring. Two driver representations that both
  meet the selected uP1966E constraints (output resistance and edge times into 3000 pF) differ by about a third in
  overshoot on B and G (G: 25 V against 17 V) with the same ringing frequency and damping. With the assumed 50 pH
  package source inductance the difference nearly vanishes. Edge times into a capacitor therefore do not fix the
  driver; its gate waveform has to be measured.
- **The ring's damping** in the B and G simulations is two to three times what a small-signal analysis of the settled
  circuit gives; in every simulated case it stays three to seven times below the measured value. Within the model, the upper transistor's channel carries
  59–64 % of a declared ring-deviation metric (the integral of voltage and current deviations, not a physical heat
  partition; the whole-window energy balance fails), and the transistor still turning on raises the local damping.
  Neither accounts for the decay. Local damping, transient decay and energy accounting are separate quantities. This is not pursued further in simulation until a decision needs it.
- **Extra capacitor loss** can reproduce the measured damping (about 60–70 mΩ in the loop) but barely lowers the
  first peak. Loss located elsewhere, such as in the transistor's output capacitance, is untested.
- **Probe bandwidth** alone cannot explain the gap. Probe loading, connection point and resonances are untested.
- **The missing gate charge**, added as one fixed capacitor, lowers the overshoot a little. The real discrepancy
  depends on voltage, so this approximation does not bound it.
- **Dead time.** EPC's waveform shows a shorter dead-time step than the model gives for the board's 10 ns setting;
  read through our driver model, about 5 ns. That is a model-dependent inference, not a measurement.

The probe EPC used, its connection point, the dead-time setting and the package's internal inductance are not
published. They are treated as stated assumptions or left to our own measurements.

## Stage 3: measurements

An EPC90133 board is to be bought. A draft test plan ([docs/epc90133-hardware-test-plan.md](docs/epc90133-hardware-test-plan.md))
chooses measurements for which each remaining explanation predicts a different pattern:
- probe characterisation first;
- driver timing with the power stage off;
- loop inductance from the ringing-frequency shift with a known added capacitor;
- a matrix of bus voltages and currents;
- a gate-resistor change;
- a second temperature;
- the Fig. 9 conditions with a known probe.

Predictions are frozen before measuring, and some conditions are held out for scoring.

Safety does not depend on software. The setup uses:
- a current-limited supply with hardware trips;
- an interlock and an emergency stop;
- a bus voltage raised in steps with a human check at each step.

Simulated peak voltages are sensitivity results, not a safe operating envelope.

## Current state and next steps

The tool chain works end to end: vendor files → model qualification → layout geometry → inductance extraction →
switching simulation → comparison with a measurement. Its board-level predictions do not yet match EPC's waveform.
Gate G3 (stock-board simulation) stays open until the gap is explained or bounded. Further simulation now gains little
without measurements, so measurement readiness comes first.

Next steps:
1. **Measurement readiness.** The simulation baseline is frozen: the original driver model and the
   regularized-driver variants stay as separate recorded cases. The next work starts from the lab's exact equipment
   and the purchased board's identity, and turns them into
   a probe-and-channel plan (switch node, low-side gate voltage, driver PHASE-to-ground and current measured together,
   with connection points, probe loading, bandwidth, grounding and uncertainty), and the hardware draft into an
   executable first-power procedure with numerical limits, independent hardware trips, discharge verification and
   measurement uncertainty. A small simulation of the driver alone, with its bootstrap and supply capacitors, prepares
   the unpowered driver measurement.
2. **Measure the board** once that procedure and its interlocks are approved (gate G4): measurement chain and
   unpowered driver checks first, then the first energized condition, with predictions and held-out conditions
   frozen before diagnostic switching data are taken. Efficiency (input and output power with an uncertainty) is
   a separate G4 measurement, not replaced by waveform matching.
3. **Complete the parasitic set** if a decision needs it: switch-node capacitance with FasterCap, within the scope
   its known-answer checks support. All values go into one `parasitics.inc` file, with the couplings kept.
4. **Agent runs.** A first bounded run works: an agent given only a task card checks the declared inputs of the Fig. 9
   comparison, runs it with the same result as the plain script, and stops correctly when an input has been altered
   ([result](results/gan/agent-milestone-1.json)). That is one narrow task run once each. Next are repeated runs and
   tasks in which the agent has to make a decision.
5. **Later:** our own board layout in KiCad, with predictions frozen before fabrication and scored against measurements.

## Tools

| Tool | What it does here | Status |
|---|---|---|
| Python 3.10+ with numpy, scipy, Pillow, matplotlib | glue, analysis, geometry, plots | in use |
| `circuit_tools` (this repo, `src/`) | runner interface, artifact store, LTspice adapter, Gerber reader | in use; 101 tests |
| **LTspice 26.1.1** | circuit simulation of the vendor model and board (batch mode on Windows) | qualified (gate G1) |
| **FastHenry 3.0.1** | inductance and resistance extraction from copper geometry (under WSL) | qualified for bars and plane pairs; board use exploratory; internal use only (licence note below) |
| PyMuPDF | reads datasheets and digitizes their graphs | in use |
| openpyxl, xlrd | read EPC's BOM and stackup files | in use |
| **FasterCap 6.0.7** | capacitance extraction between conductors (under WSL) | built; LGPL 2.1+. Known-answer checks: 4 of 8 pass (specific benchmark geometries, including a 2D microstrip on a dielectric); its accuracy setting is not an error bound. A 3D strip-over-dielectric check failed and its 3D matrices are unphysical; not qualified for 3D or board geometry ([results](results/gan/fastercap-known-answer.json), [3D check](results/gan/fastercap-board3d-assessment.json)) |
| KiCad 10.0.6 | our own board design | installed per-user (checksum verified); EPC's KiCad library loads (47 footprints); no board design started, route choice open |
| DEVSIM | device simulator for the paused silicon fixture (WSL) | paused |

EPC files, papers and FastHenry itself are not in git. They live in the git-ignored `vendor/` and `.tools/`, with sources,
retrieval dates, checksums and reuse terms recorded in `devices/`. FastHenry's MIT-authored notice is restrictive and is not
the standard MIT License. It permits internal non-commercial use and forbids redistribution.

## Repository layout

- `src/circuit_tools/`: the library (LTspice adapter, Gerber and drill reader, revisions, artifacts, CLI).
- `scripts/`: one script per study, each with its specification in its docstring.
- `devices/`: source records (URLs, dates, checksums, terms) and transcribed schematics.
- `results/`: committed result reports. Failed runs are kept alongside, with `-failed` in the name.
- `docs/`: [build and replay notes](docs/build.md) with the full numbers and limits of every study,
  [literature notes](docs/gan-layout-literature-notes.md), [benchmark sources](docs/device-benchmark-sources.md),
  [workflow methods](docs/gan-workflow-methods-review.md), [hardware test plan](docs/epc90133-hardware-test-plan.md).
- `plans/`: the [pipeline plan](plans/gan-halfbridge-pipeline-plan.md) and the reused toolset plan.
- `tests/`: unit and known-answer tests.
- `vendor/`, `runs/`, `.tools/`: git-ignored vendor files, simulation scratch output and local tool builds.

## How to run

```sh
PYTHONPATH=src python -m pytest -q tests                  # unit and known-answer tests
PYTHONPATH=src python scripts/verify_ltspice_fixtures.py  # LTspice adapter checks
PYTHONPATH=src python scripts/epc2302_baseline.py         # Stage 1: model against the datasheet table
PYTHONPATH=src python scripts/epc90133_power_loop.py      # Stage 2: board geometry, footprints, ports
PYTHONPATH=src python scripts/epc90133_extract.py B:m1:mid --jobs 3   # FastHenry extraction (about 2 h)
PYTHONPATH=src python scripts/epc90133_switching.py       # switching simulation from the extractions
PYTHONPATH=src python scripts/compare_epc90133_fig9.py    # comparison with EPC's measured waveform
```

The vendor files must first be downloaded to `vendor/` as recorded in `devices/`. Expected results and known limits for
each command are in [docs/build.md](docs/build.md).

## Project rules

- Record the source, retrieval date, checksum and reuse terms of every vendor file.
- Keep the original vendor model as the baseline. Tune it only when evidence isolates a discrepancy to the device, and
  store any tuned model separately.
- Declare checks and tolerances before running them, and keep failed runs.
- A simulated sensitivity is not a safe operating limit. Hardware protection stays independent of any AI agent.

## Reference work in this repository

- **EPC9097 with EPC2204.** An earlier target board, kept as reference. The LTspice adapter was first qualified on it,
  and the EPC2204 model matches all 23 of its datasheet curves. See
  [build notes](docs/build.md#epc2204-vendor-model-baseline-stage-1-first-slice).
- **Silicon NMOS with DEVSIM.** A development fixture that produced the reusable infrastructure: immutable revisions,
  artifact provenance, result semantics and a bounded simulator runner. See
  [generated planar NMOS](docs/build.md#generated-planar-nmos-candidate-lc1) and the
  [co-design toolset plan](plans/autonomous-circuit-toolset-plan.md).
