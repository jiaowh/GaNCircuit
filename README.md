# GaNCircuit: an agent-driven GaN power-electronics pipeline

## The goal

The project is building a mostly automated way to go from a transistor's datasheet to a tested circuit
board. The transistor is the **EPC2302**, a fast power switch made from gallium nitride (GaN). The board
is EPC's **EPC90133**, which uses two of these switches to chop a 48 V supply into pulses, the basic
building block of power converters. The long-term aim is for software, with AI agents helping, to
predict how the board will behave. We then check that prediction against real measurements and use what
we learn to design a better board.

The work splits into three stages:
1. **The transistor on its own:** does our simulation of the chip behave like the datasheet says?
2. **The board:** does our simulation of the chip on its actual circuit board behave like the real board?
3. **Real measurements:** testing actual hardware safely and comparing it with the predictions.

```mermaid
flowchart LR
    DS["EPC2302 datasheet"] --> M["Vendor model<br/>in LTspice"]
    M -->|"Stage 1: compare<br/>with datasheet graphs"| CHK1{{"24 of 25 match"}}
    G["EPC90133 layout files<br/>(8 copper layers)"] --> GEO["Board geometry,<br/>nets, footprints"]
    GEO --> FH["FastHenry:<br/>loop inductance"]
    M --> SW["Switching simulation"]
    FH --> SW
    SW -->|"Stage 2: compare with<br/>EPC's measured waveform"| CHK2{{"does not match yet"}}
    SW -.->|"Stage 3 (not started)"| HW["Measurements on<br/>real hardware"]
```

The full plan, including its checkpoints (gates G0–G6) and safety rules, is in
[plans/gan-halfbridge-pipeline-plan.md](plans/gan-halfbridge-pipeline-plan.md).

## What we've done

### Stage 1: the transistor (mostly done)
- EPC provides a simulation model of the EPC2302. We showed it runs correctly in our circuit simulator,
  LTspice ([table comparison](results/gan/epc2302-baseline.json)).
- We compared it with 25 graphs from the datasheet. 24 match closely
  ([comparison](results/gan/epc2302-curve-comparison.json)). They match so closely that EPC probably drew them
  from the same model, so this shows our simulation runs the model faithfully, not that the model matches real parts.
- One graph doesn't match: the one showing how much electric charge it takes to switch the transistor on
  ([Fig. 7 comparison](results/gan/epc2302-fig7-comparison.json)). We haven't worked out why.
- Because of that mismatch, we don't yet trust simulated switching speeds or energy losses. The owner accepted the
  unmodified model as a provisional baseline for Stage 2 (gate G2, 28 September 2026). The model is not tuned.

### Stage 2: the board (tools built, results not trusted yet)
- **We can read the board's layout.** EPC publishes the manufacturing files: copper shapes on 8 stacked layers,
  plus about 450 drilled holes (vias) that connect the layers. Our software turns these into a map of which copper
  belongs to which part of the circuit ([geometry](results/gan/epc90133-geometry.json)). It checks that the transistors'
  pads are in the right places ([power-loop overlay](results/gan/epc90133-power-loop.json), pictures in
  `results/gan/epc90133-power-loop/`).

  ![Top layer of the EPC90133 power stage: VIN in red, switch node in green, ground in blue, with the two transistors (Q1, Q2), the Ci capacitor row and the via groups](results/gan/epc90133-power-loop/top.png)

  *Top copper layer around the two transistors, drawn from EPC's files. Red is the input supply (VIN), green the switch
  node (SW), blue ground (GND). The numbered rectangles are the transistor pins; dots are vias. The arrows show the
  switching current's path: from the capacitors (top) through Q1 and Q2, then down through vias to the ground plane below.*

  ![Cross-sections through the board showing all eight copper layers and the vias under Q2](results/gan/epc90133-power-loop/sections.png)

  *Side views cut through the board (height exaggerated). Each row of colour is one copper layer, and vertical bars
  are vias. The switch-node vias pass through holes in the ground layers, leaving slots in the return path.*

- **We can calculate the board's hidden effects.** Copper paths act like tiny unwanted coils (inductance). When the
  switch flips in about a nanosecond, these tiny coils cause voltage spikes and ringing. A tool called FastHenry calculates
  them from the copper shapes. We found that the deeper copper layers matter a lot, while the fine details of how vias are
  modelled barely matter. That saved us from spending hours refining the wrong thing.
- **We can simulate the switching.** The board's calculated inductances go into the circuit simulation alongside the
  transistor models. That lets us predict the voltage waveform when the switch flips.

### What doesn't work yet
- **The prediction doesn't match EPC's measured waveform.** We now read EPC's published waveform (QSG Fig. 9) from
  its pixels with a declared method, instead of by eye. The ringing frequency agrees: 264 MHz measured, 266–284 MHz
  simulated with the full board. (The earlier reading of about 0.6 GHz was wrong: the figure is two zoomed
  screenshots stitched side by side.) The spike does not agree: about 36 V simulated against 5.7 V measured. Our
  edge is also twice as fast (0.83 ns against 1.68 ns), and our ringing dies away about 7 times more slowly.

  ![EPC's measured waveform against four simulated cases](results/gan/epc90133-fig9-overlay.png)

  *EPC's measurement (black) against the simulation with the board as extracted (blue), with 50 pH of assumed
  package inductance (orange), with a weaker gate driver (green), and with extra loss added to damp the ringing (red).
  The turn-off edge (right) matches. At turn-on (left) every simulated ring is several times larger than the measured one.*

  ![Simulated switch-node voltage for each board variant at turn-on and turn-off](results/gan/epc90133-switching-waveforms.png)

  *Simulated switch-node voltage when the top transistor turns on (left) and off (right), for each extraction variant.
  With no board inductance (blue) the edge is almost clean. With the extracted copper, the voltage rings far above the
  48 V supply. Adding more of the board (orange → green → yellow) lowers the spike but does not reach the ~55 V peak read
  from EPC's measurement (dashed line). The turn-off edge barely depends on the layout. The dashed line is an early
  by-eye reading; the digitized peak is 51.5 V (5.7 V above a settled 45.8 V).*
- **We tested the suspected missing pieces one at a time.** None of them, and no combination we tried, reproduces
  the measurement:
  - inductance inside the transistor's package reproduces the slower edge, but it pulls the ringing frequency away
    from the measurement;
  - a weaker gate driver lowers the spike without moving the frequency, but not far enough;
  - the missing Miller charge seen in the datasheet's gate-charge curve lowers the spike a little;
  - extra energy loss can reproduce the measured damping, but it would need about 60–70 mΩ in the loop, 30 times the
    copper's resistance, and it barely lowers the first spike;
  - a slow measuring probe cannot explain it on its own: one slow enough to hide the spike would also slow the edge
    more than EPC measured.

  EPC's measurement also shows a shorter dead time than the board's resistors should set (about 5 ns against 10 ns).
  The older EPC9097 board showed the same thing, so the gate driver's timing is suspect on both boards.
- **What would settle it:** the remaining suspects (the real driver, the package, losses inside the transistor and
  EPC's probe) cannot be told apart from a single published waveform. We would need our own measurements with a
  known probe.

### Stage 3: real hardware (not started)
- We have no board and have made no measurements. That comes later, with safety hardware that works independently
  of the software.

**In one sentence:** we have a working chain of tools that goes from the manufacturer's files to a predicted waveform.
Its predictions don't match reality yet, and the next job is to find out why.

## What's next

Done on 29–30 September 2026:
- the sensitivity runs: the package-inductance spikes were numerical and are removed, and a continuous-operation
  (periodic buck) run now shows the simplified double-pulse test gives the same edges;
- EPC's measured waveform, digitized with a declared method;
- the candidate causes, tested one at a time against it (see above and the
  [build notes](docs/build.md#epc90133-switching-test-5-candidate-causes-of-the-gap-to-fig-9-g3-diagnosis)).

1. **Plan the hardware stage.** This is now the step that can close the gap. Decide whether to buy an EPC90133, list
   the lab equipment, and design experiments that isolate each suspect:
   - a known probe on a known point;
   - ringing measured at several currents and bus voltages;
   - dead time measured at the driver outputs;
   - loop inductance measured from the ringing frequency with a known added capacitor.
2. **Ask EPC** (only on the owner's instruction) which probe, probing point and dead-time setting produced Fig. 9, and
   whether a package inductance for the EPC2302 is available.
3. **Driver timing.** The measured dead time is shorter than the nominal setting on both boards. Look for published
   uP1966E delay data before blaming the layout.
4. **Add capacitance extraction with FasterCap.** Qualify it on known answers (a parallel-plate capacitor with
   fringing, a microstrip line), then replace the rough ~135 pF switch-node estimate with an extracted value. Today's
   bench shows that estimate changes the spike by only about 1 V, so this matters more for switching losses and for our own
   board than for closing the current gap.
5. **Complete the parasitic set in the extraction interface.** The draft
   [parasitic extraction and Agent 2 stop criteria](plans/Layout%20Parasitic%20Extraction%20and%20Agent%202%20Stop%20Criteria.docx),
   adopted with corrections in the [plan](plans/gan-halfbridge-pipeline-plan.md), lists seven "must" parasitics.
   The power-loop three (L_d, L_sw, L_s) are extracted. Common-source inductance, the two gate-loop inductances and
   switch-node capacitance are not yet extracted. The values go into one `parasitics.inc` file that the simulation reads,
   with the coupling between segments kept.
6. **Later:** our own board layout in KiCad, with predictions frozen before fabrication and scored against measurements.

Gate G3 (stock-board simulation) stays open until the gap with the measurement is explained or bounded.

## Tools

| Tool | What it does here | Status |
|---|---|---|
| Python 3.10+ with numpy, scipy, Pillow, matplotlib | glue, analysis, geometry, plots | in use |
| `circuit_tools` (this repo, `src/`) | runner interface, artifact store, LTspice adapter, Gerber reader | in use; 95 tests |
| **LTspice 26.1.1** | circuit simulation of the vendor model and board (batch mode on Windows) | qualified (gate G1) |
| **FastHenry 3.0.1** | inductance/resistance extraction from copper geometry (under WSL) | qualified for bars and plane pairs; board use exploratory. Internal-only use; not redistributed (licence note below) |
| PyMuPDF | reads datasheets and digitizes their graphs | in use |
| openpyxl, xlrd | read EPC's BOM and stackup files | in use |
| DEVSIM | device simulator for the paused silicon NMOS fixture (WSL) | paused |
| **FasterCap** | capacitance extraction between conductors (switch-node, VIN and GND copper), the companion to FastHenry | planned, not installed; LGPL 2.1+ per its README, [source](https://github.com/ediloren/FasterCap). Must pass known-answer checks before board use |
| KiCad | our own board design (Stage 2, later) | not installed |
| PSpice, Spectre | alternative simulators | not installed; ngspice was removed |

EPC files, papers and FastHenry itself are not in git: they live in the git-ignored `vendor/` and `.tools/`,
with sources, dates and checksums recorded in `devices/`. FastHenry's MIT-authored notice is restrictive and is not the
standard MIT License; internal use was confirmed by the owner (commit `95b0fad`).

## Repository layout

- `src/circuit_tools/`: the library (LTspice adapter, Gerber/drill reader, revisions, artifacts, CLI).
- `scripts/`: one script per study, each with its specification in its docstring (for example
  `epc2302_baseline.py`, `read_epc90133_geometry.py`, `epc90133_power_loop.py`, `epc90133_extract.py`,
  `epc90133_switching.py`).
- `devices/`: source records (URLs, dates, checksums, terms) and transcribed schematics.
- `results/`: committed result reports; failed runs are kept alongside with `-failed` in the name.
- `docs/`: [build and replay notes](docs/build.md), [literature notes](docs/gan-layout-literature-notes.md),
  [benchmark sources](docs/device-benchmark-sources.md), [workflow review](docs/gan-workflow-methods-review.md).
- `plans/`: the active [pipeline plan](plans/gan-halfbridge-pipeline-plan.md) and the reused toolset plan.
- `tests/`: unit and known-answer tests.
- `vendor/`, `runs/`, `.tools/`: git-ignored vendor files, simulation scratch output and local tool builds.

## How to run

```sh
PYTHONPATH=src python -m pytest -q tests                  # unit and known-answer tests
PYTHONPATH=src python scripts/verify_ltspice_fixtures.py  # LTspice adapter checks
PYTHONPATH=src python scripts/epc2302_baseline.py         # Stage 1: model vs datasheet table
PYTHONPATH=src python scripts/epc90133_power_loop.py      # Stage 2: board geometry, footprints, ports
PYTHONPATH=src python scripts/epc90133_extract.py B:m1:mid --jobs 3   # FastHenry extraction (about 2 h)
PYTHONPATH=src python scripts/epc90133_switching.py       # switching sensitivity from all extractions
```

The vendor files must first be downloaded to `vendor/` as recorded in `devices/`. Details, expected results
and known limits for every command are in [docs/build.md](docs/build.md).

## Project rules

- Record the source, retrieval date, checksum and reuse terms of every vendor file.
- Keep the original vendor model as the baseline; tune it only when evidence isolates a discrepancy to the device,
  and store any tuned model separately.
- Declare checks and tolerances before running them, and keep failed runs.
- A simulated sensitivity is not a safe operating limit. Hardware protection stays independent of any AI agent.

## Detailed technical status

**Stage 1 numbers.** Every datasheet-table row with a limit is inside it. Capacitances, output charge and RDS(on)
are within 0.2–7% of typical, and total gate charge is 4% low. The gate-charge sub-values (QGD −34%, QG(TH) −31%) are
unresolved. In Fig. 7 the model's Miller plateau is 24% narrower, and its charge after the plateau is about 1.2 nC (8%) low.
Simulations keep `reltol=1e-6`: the default under-integrates gate charge. See
[build notes](docs/build.md#epc2302-datasheet-curves-g2-curve-slice).

**Board files.** BOM and Gerbers are board B5253 Rev 2.0, 8 copper layers
([audit](results/gan/epc90133-board-audit.json)). The schematic labels the driver uP1966A where the BOM says uP1966E,
and a design-folder name mentions EPC2301. Both stay recorded. A [BOM-based schematic](devices/epc/epc90133-schematic.json)
passes a static connectivity check.

**Power loop.** Two stacked loops exist: the top layer over mid-layer 1, and a second one through the lower layers to
the bottom-side Cm capacitors. The return plane under both transistors is slotted by switch-node via clearances, a case
that is not qualified.

**Via check.** The FastHenry via/plane-pair benchmark ([result](results/gan/fasthenry-via-cavity.json)) fails its
declared mesh criterion and stays recorded as failed. Only the spreading-inductance difference between two closed benchmark
cavities passed. The declared via representation uncertainty is the bracket width (23.5/33.7 pH), and it applies to the
benchmark only. The owner deferred the finer mesh on 29 September 2026.

**Extraction and switching (exploratory, interim).**

| Variant | Loop L | Rise overshoot | Ringing |
|---|---|---|---|
| A: top + mid-layer 1, Ci (three via representations) | 0.49–0.50 nH | 54.5–54.9 V | 0.20 GHz |
| I: all copper, Ci | 0.30 nH | 40.0 V | 0.27 GHz |
| B: all copper, Ci + Cm | 0.28 nH (0.27 gap, 0.26 pad via representation) | 35.7 V | 0.28 GHz |
| ideal copper | — | 2.1 V | 1.15 GHz |
| EPC's measurement (QSG Fig. 9, digitized; probe unknown) | — | 5.7 V | 0.26 GHz |

See [build notes](docs/build.md#epc90133-exploratory-extraction-and-switching-sensitivity-g3-steps-23-interim).

## History

- **EPC9097/EPC2204 (paused reference).** The first target, kept as reference evidence. The LTspice adapter was
  qualified on it, and the EPC2204 model matched all 23 datasheet curves. A switching bench swept the loop inductance
  before any extraction. EPC publishes two layout revisions of that board, and neither is linked to a physical board.
  See [build notes](docs/build.md#epc2204-vendor-model-baseline-stage-1-first-slice).
- **Silicon NMOS/DEVSIM fixture (paused).** An earlier development fixture built the reusable infrastructure: immutable
  revisions, artifact provenance, result semantics and a bounded simulator runner. Its device and results are kept. See
  [generated planar NMOS](docs/build.md#generated-planar-nmos-candidate-lc1) and the
  [co-design toolset plan](plans/autonomous-circuit-toolset-plan.md).

