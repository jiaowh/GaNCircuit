# Agent-driven GaN power-electronics pipeline

## Current target and next deliverable

The owner selected **EPC90133/EPC2302** on 28 September 2026. EPC lists a
100 V device-rated, 40 A half bridge with two EPC2302s and the uP1966E driver.
The quick-start guide lists an 80 V maximum bus input under its stated conditions;
these ratings are not an approved project test envelope.
The EPC2302 datasheet, EPC90133 guide and schematic are downloaded locally,
with checksums in [the new source record](devices/epc/epc90133-sources.json).
The existing vendor LTspice library contains EPC2302, but it has not yet been
run or qualified for this target. BOM/Gerber retrieval and revision/population
checks remain open. EPC lists Altium files on request.

The unmodified EPC2302 model now runs through the LTspice adapter, and a
[table baseline](results/gan/epc2302-baseline.json) compares it with the datasheet.
Every row with a datasheet limit is inside it. Capacitances, output charge and RDS(on) are within
0.2–7% of typical, and total gate charge is 4% low. The table's gate-charge sub-values
(QGD −34%, QG(TH) −31%) remain unresolved, and their cause is not established.
The model also reproduces all 24 digitized datasheet curves in Figs. 1–6 and 8–10
([comparison](results/gan/epc2302-curve-comparison.json)). The margins are so small that
EPC probably drew these curves from the same model, so they show that our runner is faithful,
not that the model matches hardware. The gate-charge curve, Fig. 7, does **not** match
([comparison](results/gan/epc2302-fig7-comparison.json)): the model's Miller plateau
is 24% narrower, and its charge after the plateau is about 1.2 nC (8%) low. The cause is not
established, and no model tuning follows. The owner reviewed this on 28 September 2026. The unmodified model is a provisional baseline for board simulation; Fig. 7 and the sub-charges stay open, and switching times or losses that depend on gate charge are not validated.
The EPC90133 BOM and Gerbers (board B5253 Rev 2.0, 8 copper layers) are retrieved,
and an [audit](results/gan/epc90133-board-audit.json) cross-checks them with the stackup,
schematic and guide. See [build notes](docs/build.md#epc2302-datasheet-curves-g2-curve-slice).
A tested Gerber reader now turns the EPC90133 files into inspectable geometry: copper on all
eight layers, drills and nets ([summary](results/gan/epc90133-geometry.json), renders in
`results/gan/epc90133-geometry/`). It finds VIN, GND and SW as separate nets, and it shows
the power loop the datasheet describes, returning through the GND plane on mid-layer 1.
A [BOM-based schematic](devices/epc/epc90133-schematic.json) of the power stage matches the BOM
part for part, and its LTspice netlist passes a static-state check. That check shows the circuit is
connected as drawn; it is not a switching prediction. The schematic's uP1966A label, where the BOM says
uP1966E, stays recorded. So does a design-folder name that mentions EPC2301.
The FastHenry via/return check at the board's stack ([result](results/gan/fasthenry-via-cavity.json)) **fails its declared mesh criterion**: absolute inductances still move 1.2–1.5% between the two finest meshes. It stays recorded as failed. What passed is narrow: the *difference* in spreading inductance between two closed benchmark cavities at 100 MHz matches the analytic answer within 2.5%, and errors common to both can cancel in a difference. That does not qualify arbitrary board planes, holes or via arrays. Both via values lie inside their bracket; the declared representation uncertainty is the bracket width (about 23.5 and 33.7 pH for the two cavities), and even that applies to the benchmark geometry, not to every board via.
Owner decision (29 September 2026): defer the fourth mesh and proceed with exploratory board extraction.
Step 1 is done: an [annotated power-loop overlay](results/gan/epc90133-power-loop.json)
(renders in `results/gan/epc90133-power-loop/`) checks both EPC2302 footprints against the datasheet
land pattern (pins, orientation, pin nets: pass). It locates the 7 top-side Ci and 10 bottom-side Cm capacitors
and groups the loop's vias by the layers they actually connect, and it fixes the extraction ports. It shows two stacked loops
(top layer over mid-layer 1, and a second through G5, G6 and the bottom layer via Cm). It also shows that the return
plane under both FETs is slotted by SW via clearances. That is a plane-hole case not yet qualified.
Steps 2–3 now run end to end, as exploratory work (interim results in
[build notes](docs/build.md#epc90133-exploratory-extraction-and-switching-sensitivity-g3-steps-23-interim)).
The via representation changes neither the extracted loop inductance (under 2%) nor the switching predictions.
The extra copper layers and the Cm capacitors do: 0.50 → 0.28 nH, and rise overshoot 55 → 36 V. No variant resembles
EPC's measured Fig. 9 (about 7 V at about 0.6 GHz against 36 V at 0.28 GHz), so the gap is probably not the loop
inductance alone; the candidates are untested. [Literature notes](docs/gan-layout-literature-notes.md)
add missing package inductance, switch-node capacitance and the probe response as cases to test.
Originally planned next: exploratory extractions under explicit, alternative geometry assumptions; and a switching
sensitivity bench that shows which assumptions change the predictions, to decide where qualification is worth
the effort. Those simulations carry the Fig. 7 gate-charge limitation.
Retain the accepted LTspice adapter and FastHenry checks. The previous
EPC2204/EPC9097 evidence below is historical and does not validate the new pair.

**Active direction (28 September 2026):** an agent-driven pipeline for a commercial EPC GaN FET and its half-bridge development board: datasheet → vendor model → layout-aware simulation → automated measurement → closure report. See the [GaN half-bridge pipeline plan](plans/gan-halfbridge-pipeline-plan.md). Selected target: EPC90133 board with EPC2302 FETs (owner decision, 28 September 2026).

**Historical EPC9097/EPC2204 results, retained as reference.** The first piece of Stage 1 works. LTspice 26.1.1 runs in batch mode behind the project's runner interface. [Known-answer checks](results/toolset/ltspice-fixtures.json) pass: operating point, transient, AC, nested sweeps, a diode, and binary/ASCII output. The unmodified EPC2204 vendor model runs at the datasheet's table conditions, and a [baseline report](results/gan/epc2204-baseline.json) compares it with the datasheet. Resistance, capacitances, output charge and total gate charge come out within 0.1–6.4% of the datasheet typicals. The first run reported gate charge 33% low, which turned out to be an LTspice accuracy-setting artifact; it is fixed, and the result is checked against the model's own equations. The model also matches every datasheet curve EPC drew ([gate charge](results/gan/epc2204-fig7-comparison.json), [all other curves](results/gan/epc2204-curve-comparison.json)): 23 of 23 curves pass pre-declared tolerances, with legend labels verified. An earlier reported failure (Fig. 6 stored energy) came from our digitizer's axis calibration, and was found and fixed after review. The table's gate-charge sub-values (QGS, QGD, QG(TH)) are not reproduced by EPC's own curve under plateau-based boundaries, so they remain unresolved; they may use different definitions or different source data. The owner accepted this model baseline (gate G2) for board simulation, with those subcharges recorded as an open exception to revisit during switching measurements. Now in progress: simulation of the stock EPC9097 board (gate G3). A [switching bench](results/gan/epc9097-switching-ideal-layout.json) simulates the board's half bridge: two unmodified EPC2204 models, the board's gate resistors and capacitors, and a behavioural gate driver calibrated to its datasheet (EPC publishes no driver model). It runs at the conditions of EPC's published waveforms, with the power-loop inductance swept because it has not yet been extracted from the layout. The sweep shows why extraction matters. In this simplified bench, the switch node peaks at 52 V with 0.2 nH but 96 V with 0.8 nH from a 48 V bus, against a 100 V rating. That is a sensitivity result, not a safe operating limit: gate-loop and common-source inductance are omitted and the driver is approximate. EPC's measured waveforms are [digitized and compared](results/gan/epc9097-switching-vs-qsg.json). The switching-node fall time, which mainly tests the device, follows the expected trend with current but is 23–35% slower in EPC's measurement. The dead-time plateau, which mainly tests the driver timing, is 2.4 ns shorter. Candidate causes are known but untested. The source of the 130 MHz ringing in EPC's screenshots, and of their slower rise, is unidentified. The power loop, the bus network, the probe path and parasitics the bench omits are all candidates. EPC publishes two layout revisions of the board. Both stay candidates until evidence links one to our board, or to EPC's measurements, which need not match. G3 stays open until the matching layout's parasitics are extracted. Not yet done: layout and parasitics, and any hardware measurement. See [the EPC2204 baseline](docs/build.md#epc2204-vendor-model-baseline-stage-1-first-slice). ngspice has been removed; LTspice is the circuit simulator.

The work below built reusable infrastructure: immutable revisions, artifact provenance, result semantics and a bounded simulator runner. It also built a silicon NMOS/DEVSIM development fixture, which is now paused. That history is kept for reference.

## Adopted workflow methods and next work

The [active plan](plans/gan-halfbridge-pipeline-plan.md) incorporates the
[V1 workflow review](docs/gan-workflow-methods-review.md): explicit stage handoffs,
bounded layout optimization, guarded model tuning, predictions frozen before
fabrication, held-out measurements and evaluation of agent effort/reliability
against a baseline. These are planned capabilities; the full autonomous loop
has not been demonstrated. EPC90133/EPC2302 is now selected; EPC9097/EPC2204
is retained as historical reference work.

Reusable FastHenry qualification covers tested bars and plane pairs, with failed case C
and subsequent passing check D kept separate. Vias, plane holes and solder-bar
connections remain outside that qualification. The historical EPC9097 6-layer ODB++ population
(EPC2619, 4.7/1 ohm gate resistors, uP1966A) differs from the simulation BOM.
Keep geometry, fitted parts and measurement-board identities separate. Reuse
the extraction methods after identifying the selected EPC90133 geometry.
Internal-only FastHenry use is recorded in `95b0fad`; its restrictive MIT-authored
terms are not the standard MIT License. See [build notes](docs/build.md#fasthenry-inductance-extraction-tool-qualification-g3).

## Earlier implementation history

This project is developing tools that general-purpose AI agents can use to design semiconductor devices, connect circuits, run simulations, inspect results, and iterate. **Custom device design and circuit co-design are in scope from the first working demonstration.**

The [co-design toolset plan](plans/autonomous-circuit-toolset-plan.md) describes the architecture, proposed operations, implementation sequence, and evaluation gates. The recommended first target is a custom planar NMOS and a simple amplifier, with independent device-to-circuit validation. The [reference notes](plans/autonomous-toolset-reference-notes.md) connect the decisions to local papers and upstream tools.

Current status: the first implementation slice is available as a Python library and CLI. It includes immutable circuit revisions, artifact storage, a bounded simulator adapter (ngspice at the time, since replaced by LTspice), and a validity-aware diode fitting fixture; see [build instructions and scope](docs/build.md). The complete physical NMOS-to-amplifier co-design loop is still under construction. Legacy preflight results describe the earlier pilot only.

The first [NMOS DC characterization](results/device-reference/nmos-dc-characterization.json) collected all nine points at 300 K over Vgs/Vds = 0.45, 0.50, and 0.55 V, with a predeclared six-point training set and three-point held-out gate slice. The [two-mesh grid comparison](results/device-reference/nmos-characterization-comparison.json) passes all 36 terminal-current and six finite-span slope checks; the maximum drain-current change is 0.1872%. A [central slope step-size check](results/device-reference/nmos-step-size-comparison.json) also passes on the coarser mesh. The CLI now imports immutable NMOS datasets and computes secants. These checks cover sampled simulated behavior; continuous-domain, model, circuit, and physical-device validation remain unfinished. See [characterization replay and limits](docs/build.md#nmos-dc-characterization).

**Generated device (28 September 2026).** The upstream MOS reference is retired as the amplifier candidate: its gate barely controls the current (gm/gds ≈ 0.063). A replacement planar NMOS is now generated from one [parameter specification](devices/planar-nmos-lc1.json) (1 µm gate, 10 nm oxide, n+ poly, 3.3 V). Its simulated curves show clear turn-off (79.5 mV/dec, Ion/Ioff 4e7), saturation, and gm/gds of 70–240 at mid-supply. A common-source operating point (Vgs 0.6 V, W 23.9 µm, RD 16.5 kΩ, 100 µA) gives an estimated gain of −11, checked on three meshes. The fitted model and ngspice amplifier simulation are the next steps. See [generated planar NMOS](docs/build.md#generated-planar-nmos-candidate-lc1).

- `papers/`: reference literature and historical index.
- [Public device benchmark sources](docs/device-benchmark-sources.md): diode/MOSFET reference data, candidate Infineon CoolGaN resources, provenance limits, and validation sequence for future sessions.
- `plans/gan-halfbridge-pipeline-plan.md`: active direction, dated 28 September 2026.
- `plans/autonomous-circuit-toolset-plan.md`: co-design toolset plan (11 September 2026); its contracts are reused, and its NMOS demonstration is paused.
- `results/`: executed toolset and device-reference reports.
- Earlier research-plan history (superseded by the toolset plan) was removed from the working tree and remains in git history at commit `9a8e25b`. The earlier fidelity/ranking pilot (`FINAL-PLAN.md`, `protocol/`, `pilot-inputs/`, pilot results) was removed from the working tree and remains in git history at commit `79b80fa`.

The official DEVSIM diode and planar MOS scripts complete, with [finite-current and conservation checks](results/device-reference/audit.json). A [diode junction-refinement check](results/device-reference/qualification.json) passes at 0.5 V, and a [known-answer 2D resistor fixture](results/device-reference/current-normalization.json) checks the A/cm current convention. The [four-mesh planar-MOS endpoint check](results/device-reference/planar-mos-openblas-qualification.json) now passes: the last drain-current change is 0.184%, below the fixed 1% tolerance. [Runtime comparison](results/device-reference/math-runtime-comparison.json) confirms agreement on the same mesh after adopting local OpenBLAS. See [replay instructions and limits](docs/build.md#optimized-math-runtime-and-mos-endpoint-check). Next: expose physical device revisions, select an amplifier operating region, validate its model bridge, and perform independent circuit checks. Endpoint mesh agreement alone does not validate that full workflow.
