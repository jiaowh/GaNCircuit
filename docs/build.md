# Building and running the first slice

## Active target switch on 28 September 2026

The owner selected **EPC90133/EPC2302**. The EPC2204/EPC9097 commands and results
below remain reproducible reference work, not the current target's acceptance.
See [source inventory](../devices/epc/epc90133-sources.json) and the
[active plan](../plans/gan-halfbridge-pipeline-plan.md).

Downloaded: EPC2302 datasheet (29 April 2026), EPC90133 QSG v1.0
(6 September 2022), and schematic. All three open as PDFs; files remain outside git.
The unmodified library at `vendor/epc/ltspice/EPCGaNLibrary.lib` contains
`.subckt EPC2302 gatein drainin sourcein`. Presence is not execution or validation:
the EPC2302 smoke run, table/curve baseline and board bench remain to be built.
Use new result paths and the new part's actual test conditions; do not overwrite
EPC2204 results or transplant EPC9097 component values and parasitics.

The LTspice adapter qualification remains useful. FastHenry checks qualify only
the geometries already tested; EPC2302 uses a 3 x 5 mm QFN package, so the old
bare-die solder-bar assumptions do not transfer. Obtain/audit the new BOM,
Gerbers, stackup and population before extraction. No physical board ownership,
board purchase, EPC contact or hardware operation is implied by this switch.

### EPC2302 vendor model baseline (G2, table slice)

```sh
PYTHONPATH=src python scripts/epc2302_baseline.py
```

Writes `results/gan/epc2302-baseline.json` and `results/gan/epc2302-model-curves.json`;
netlists, logs and raw files go to the git-ignored `runs/epc2302-baseline-*`.
The script checks the library archive against `devices/epc/sources.json`, and the extracted
library and the datasheet (revised 29 April 2026) against `devices/epc/epc90133-sources.json`.
It leaves `scripts/epc2204_baseline.py` unchanged and imports its interpolation, parameter
and charge-equation helpers. They apply because the EPC2302 subcircuit has the same structure
as EPC2204; only parameter values differ. The table's min/typ/max columns were read by word position
on datasheet page 2. Test conditions are EPC2302's own: RDS(on) at 50 A, VGS(th) at 14 mA,
gate charge with a 50 A load at 50 V. The gate drive is 40 mA nominal and 8 mA for sensitivity,
the same 5:1 ratio used for EPC2204.

Result (28 September 2026): the unmodified model runs in LTspice. All 13 table rows are
produced, and every row with a datasheet limit is inside it. Deviation from typical:
RDS(on) −1.4%, CISS +1.2%, CRSS +7.2%, COSS −0.6%, COSS(ER) −2.5%, COSS(TR) and QOSS +0.2%,
QG −4.2%, VGS(th) +16% (1.51 V vs 1.3 V), VSD +22% (1.83 V vs 1.5 V, "defined by design").
The model's `rg_value` equals the datasheet RG (0.5 Ω). RDS(on) rises ×1.77 from 25 °C to 125 °C
(informational). Two rows exceed the 25% screening band: QGD −34% and QG(TH) −31%.
QGS is −17%. EPC2204 had the same sub-charge pattern, which also remained unresolved. The cause is not established.
Boundary definitions are one possible explanation, not a demonstrated one. QGD depends strongly
on the bench's end point: 0.8, 1.5 and 2.6 nC for VDS ending at 10, 5 and 1 V. QG(TH) is
taken at the model's own threshold, 0.2 V above the datasheet typical. A higher threshold
moves the charge endpoint later, so it cannot explain why the model's QG(TH) is low.

Self-checks, all passing: AC-integrated and transient QOSS/EOSS agree to 5e-5.
Transient QG agrees with the model's charge equations to 0.1%. QG changes by 4e-8 from reltol
1e-6 to 1e-7. Drive current: raw terminal QG differs by 0.76% between 40 mA and 8 mA. After
subtracting the model's own gate leakage along each trajectory, the stored charge differs by
0.34%. That is stable within the 0.5% tolerance, not unchanged. This criterion was declared
before the first run, using EPC2204's leakage finding.
The default reltol gives QG 16.4 nC (−25%), so EPC2204's under-integration artifact recurs,
and EPC2302 benches must keep `reltol=1e-6`. On the first run the direct 125 °C RDS(on)
operating point failed to converge (Gmin and source stepping). The adapter reported the failure.
Both RDS(on) benches now sweep the drain current from 0 to 50 A, and the 25 °C value is unchanged.
After review, the reltol convergence outcome treats only a missing value as a failure;
previously an exact-zero change would also have failed.

### EPC2302 datasheet curves (G2, curve slice)

```sh
python scripts/digitize_datasheet_figures.py --pdf vendor/epc/epc90133/EPC2302_datasheet.pdf \
    --output results/gan/epc2302-datasheet-figures.json --pages 3 4
PYTHONPATH=src python scripts/epc2302_curve_benches.py
python scripts/compare_epc2302_gate_charge.py      # Fig. 7
python scripts/compare_epc2302_curves.py           # Figs. 1-6, 8-10
```

Digitizer revision 3 drops exact duplicate tick labels, because EPC2302 Fig. 2 draws its labels twice.
EPC2204's output is byte-identical under revision 3, including when rerun on the Windows host.
Every EPC2302 axis paired all its labels with grid lines. Scope: Figs. 1–10, the electrical curves.
Figs. 11 (safe operating area) and 12 (thermal response) are not model outputs.
Fig. 6 has no legend or arrows. Its QOSS/EOSS assignment is checked by integrating V dQ along
the digitized charge curve: this gives 5.279 µJ against the drawn energy curve's 5.273 µJ at 100 V.
Tolerances were fixed after digitizing and before any model comparison. They follow the EPC2204 rule:
5% of the datasheet value plus 1% of the axis full scale. Log capacitance: 0.05 decade.
Fig. 9: 0.03. Fig. 10: 0.01, because its whole curve moves by only about 0.025. The RDS(on)-against-VGS
benches first failed to converge with 25–100 A forced. They now ramp the drain current from 0 at each VGS,
and at 5 V they reproduce the baseline's 1.380/2.441 mΩ exactly.

Result: all 24 curves in Figs. 1–6 and 8–10 pass. Legend or ordering assignments agree
everywhere, and blue/red mean 25/125 °C in every temperature figure. The worst point uses 1–16% of its
allowed error. EPC2204's margins were similarly small. Agreement this close suggests these
typical curves may have been drawn from this model, or from a shared source. If so, they show that our runner
reproduces EPC's model, not that the model matches hardware.

Fig. 7 (gate charge, ID = 50 A, VDS = 50 V) fails its declared checks. The vertical VGS error
reaches 0.27 V at the plateau exit (tolerance 0.10 V). The horizontal charge check fails at 3.0 and
3.5 V, where the model is 1.25 and 1.21 nC low. Below the plateau the model is 5–7% low. Its plateau
is 2.19 nC wide against 2.87 nC on EPC's curve, at 2.40 V against 2.37 V. At the 4.98 V endpoint the comparator uses, the model has 22.4 nC
and EPC's curve 23.6 nC. EPC's curve value is close to its table QG (23 nC typical), and the axes fit to 0.007 nC;
the 0.27 V failure is far larger than that. Axis-fit residual is not a complete digitization-uncertainty estimate. EPC2204's Fig. 7 matched its model to 0.018 V, so
unlike EPC2204 this drawn curve is not a replay of the library model. Why is not established.
The comparator's model offset (charge from 0 V to the bench's 0.146 V start) first used EPC2204's
initial-slope estimate: 0.34 nC. The model's charge equations give 0.47 nC, so the equation value
replaced it after the first run. Both fail; the report keeps both.
Threshold charge, reported at both thresholds as the owner asked. At 1.3 V: model 4.15 nC, EPC curve 4.44 nC.
At 1.506 V: model 4.83 nC, EPC curve 5.16 nC. The table QG(TH) is 6.3 nC, and EPC's own curve
reaches it at neither threshold. EPC's curve has its plateau start at 8.4 nC (table QGS 8.9) and width 2.87 nC (table QGD 2.3).
No model tuning follows from this: the discrepancy is between the vendor's model and the vendor's
drawing, and nothing isolates it to the device. G2 disposition (owner review, 28 September 2026): the unmodified model is a provisional baseline for G3. Fig. 7 and the table sub-charges stay open, and gate-charge-dependent switching times and losses must not be labelled validated.

### EPC90133 board files (G3 preparation)

```sh
python scripts/audit_epc90133_board_files.py   # writes results/gan/epc90133-board-audit.json
```

The board page lists only the BOM, the Gerber zip, the quick-start guide and the schematic; there is no
ODB++ or test-point report. The editable Altium design is offered through "Ask a GaN Expert". It is
optional and not requested. The Gerbers are board **B5253 Rev 2.0**, dated 18 January 2022.
The quick-start guide names PCB B5253. One published layout was found; that does not prove no other revision exists.
The Gerbers have 8 copper layers, matching the included stackup: 2.8 mil copper, dielectrics
5/5/7.2/5/7.2/5/5 mil FR370-HR (εr 4.8), 63.2 mil in total. All BOM parts appear in the
layout PDF except the optional J32 (MMCX) and the "TBD" Cout. The guide still describes J32 as the
switch-node MMCX, and its measurement-point photo is labelled EPC90132.
The layout's extra parts are fiducials, the unpopulated J22/J33 holes, LB labels and S items.
BOM, schematic and guide agree on EPC2302, EPC2038, 1 Ω/0 Ω gate resistors and 2.2 Ω R70/R75.
The schematic labels U80 uP1966A, while the BOM and guide say uP1966E; EPC9097 had the same discrepancy.
The schematic prints "19 mΩ" for Q1/Q2, where the BOM says 1.9 mΩ.
Datasheet page 6 describes the board's layout: the power loop returns on mid-layer 1 directly
beneath the FETs, and the gate return uses a Kelvin via beside the source. Extraction therefore
needs qualified vias. The guide's Fig. 9 is a measured waveform: 48 V → 13.8 V, 20 A, 250 kHz,
2.2 µH, fall time 3.7 ns and rise time 1.7 ns. These are candidate G3 comparison conditions.
None of this identifies a physical board that we have.

### Via and plane-pair return check in FastHenry (G3 preparation)

```sh
python scripts/fasthenry_via_cavity.py --jobs 3 --precond diag   # results/gan/fasthenry-via-cavity.json
```

The specification was fixed in the script's docstring before the first run. Geometry: a closed square
plane pair at the B5253 stack between the top layer and mid-layer 1 (71 µm copper, 127 µm gap), with a
return wall of explicit vertical segments and one explicit 0.25 mm square via on ideal pads. Ports sit
at the via's bottom pad, and the frequency is 100 MHz. Plates are explicit segment grids, the form the
board reader will emit. E1, the declared known answer: L(3 mm) − L(1.5 mm) = µ0(h+δ)/2π · ln(D2/D1).
In this difference the via, its junctions and the square-coax constant cancel; tolerance 3%.
E2, a bracket rather than a known answer: FastHenry places the via between plate mid-planes, so
the true value lies between the gap-only and full-segment values. Mesh criterion: the fine and
middle meshes agree within 1% for each L and for the E1 difference.

Result (28 September 2026). Declared outcome: **fail**, on the mesh criterion.

| Mesh (pitch, filaments through t) | L, 1.5 mm cavity | L, 3.0 mm cavity |
|---|---|---|
| w/2, 3 | 54.599 pH | 74.904 pH |
| w/4, 5 | 52.872 pH | 72.636 pH |
| w/6, 7 | 52.094 pH | 71.742 pH |

- Mesh: the absolute values change by 1.47% and 1.23% from the middle to the fine mesh (limit 1%), so
  they have not converged. The E1 difference changes by only 0.58%. The unconverged part is what cancels
  in E1: the via, its junctions and the pads.
- E1: FastHenry 19.65 pH against the 19.18 pH reference, +2.45% (tolerance 3%). This validates only
  the difference in spreading inductance between these two closed cavities at 100 MHz, and that
  difference is mesh-stable. Errors common to both cavities can cancel in it, so it does not qualify
  arbitrary board planes, plane holes or via arrays.
- E2: both values lie inside the bracket, at 34% and 25% of its width, and were still falling with
  refinement. L − L_low (7.9 and 8.4 pH) is the distance from the lower analytic reference, not an
  uncertainty bound. As the specification declares, the representation uncertainty is the bracket
  width: 23.5 pH (1.5 mm cavity) and 33.7 pH (3.0 mm cavity). Even those widths are specific to the
  benchmark geometry; they are not proven bounds for board vias. A board via array cannot be
  estimated by dividing a single-via value by the via count, because arrangement and mutual coupling matter.

Owner review (29 September 2026): the check stays recorded as failed; the fourth mesh is deferred.
Board extraction proceeds as exploratory work under explicit geometry assumptions, and the
sensitivity of circuit predictions to those assumptions decides where further qualification is worthwhile.

Orchestration and solver notes, none of which change the geometry, meshes or tolerances. The first
sequential driver was killed by a tool timeout. My first parallel resume read an empty `Zc.mat`: FastHenry
creates the file when it starts, so the check now looks for an impedance matrix. The reused `run_fasthenry`
30-minute limit killed the fine 3 mm case, so the via script now has its own runner with no limit.
Preconditioners: on the finished fine 1.5 mm case, `-p diag` gave the default's impedance to every printed digit
(0.00107254 + 0.0327315j Ω; 187 s against 759 s), and `-p seg` agreed within one unit in the last digit
(1640 s). `diag` was used for both 3 mm cases, and the report records each case's preconditioner.
A parallel default-preconditioner run of the middle 3 mm case ended without a result, so no second
comparison is available. The fine 3 mm case took 150k filaments and 54 minutes.

Scope, unchanged from the specification: this does not qualify antipads, via arrays, Kelvin vias,
multi-layer vias, open plane edges or thin barrels. A converged E2 would need a fourth mesh, of roughly
340k filaments and several hours on this host, declared before it runs.

### EPC90133 geometry reader and nets (G3 preparation)

```sh
PYTHONPATH=src python scripts/read_epc90133_geometry.py   # results/gan/epc90133-geometry.json and renders
```

`src/circuit_tools/gerber.py` rasterizes RS-274X copper at a chosen pitch and reads Excellon drills.
It supports the subset Altium used here: linear and multi-quadrant arcs, C/R/O apertures,
macro primitives 1/4/20/21, regions and dark/clear polarity. Everything else raises an error
rather than being dropped. `tests/test_gerber.py` checks known areas for each construct.
The reader runs at 1 mil (25.4 µm) pitch on the 50.8 mm board. Its render reproduces the silkscreen
"EPC90133 Rev. 2.0 / 80 V max. VIN" and the component placement shown in the guide.
The drill layer-pair file shows all 445 holes are through-holes, top to bottom; 394 of them are 0.198/0.254 mm vias.
The same file's design path names "EPC90133 (Die EPC2301) ... 80V 1_9 mE EPC2301 ... Rev2_0",
while the BOM, schematic and guide say EPC2302. This is recorded; what it means is unknown.

Connectivity: copper islands per layer, joined by each plated hole where copper surrounds its rim.
The check fixed before the first run passes: the VIN (TP2), GND (TP1) and SW probe points are three distinct nets.
Around the power stage, layers 1–4 below the top are almost entirely GND, and layers 5–6 carry VIN
and SW pours. The top-layer net render (`results/gan/epc90133-geometry/GTL-power-stage.png`) shows the loop
the datasheet describes. Ci1–Ci7 bridge the VIN pour and a GND strip. Q1's fingers interleave VIN and SW,
and Q2's interleave SW and GND. Q2's source returns through vias to the GND plane on mid-layer 1.
Inner layers keep pads on non-connecting vias inside their clearances; that is why mid-layer 1 has 219 islands.
Limits: a raster at 25 µm resolves clearances but not sub-pitch features. Component positions come
from the render, not a placement file. Nothing here is yet meshed for FastHenry.

### EPC90133 BOM-based schematic (G3 preparation)

```sh
PYTHONPATH=src python scripts/epc90133_schematic.py   # results/gan/epc90133-schematic-check.json
```

`devices/epc/epc90133-schematic.json` transcribes the power stage from QSG Figs. 13–15. Its values are
set by the BOM, and the script checks every part number against the recorded BOM file (all match).
It records three label discrepancies: U80 is uP1966A on the schematic but uP1966E in the BOM and guide;
Q1/Q2 are labelled "19 mΩ"; the design folder names EPC2301. The default population ties the driver
net labelled "4.7 V" to VCC (5 V). The synchronous bootstrap (Q60 EPC2038, D60/D61/D63 and so on) is
transcribed but not simulated. Its diode orientations were not confirmed, and the bench uses an ideal 5 V high-side
supply across C81. The uP1966E output stages reuse the EPC9097 bench's behavioural model, which is
calibrated to the uP1966E datasheet rather than to any EPC9097 measurement.
Static-state check, with a 48 V bus and a 48 Ω load from SW to 24 V: low side on gives SW 0.0007 V;
high side on gives 47.999 V; gates are at 4.998 V. Run 1 sampled the both-off state 30 ns after turn-off
and failed at 2.4 V: my bench design ignored the time needed to recharge both FETs' output capacitance
through 48 Ω. Its report is kept (`epc90133-schematic-check-run1-failed.json`). The revised check,
a 2 µs off interval, gives 24.000 V and passes. This shows the netlist is connected as drawn.
It makes no switching claim.

The library has no mandatory runtime dependencies beyond Python 3.10+. Circuit
simulations use LTspice through `circuit_tools.ltspice`; ngspice was removed
on 28 September 2026 when LTspice became the project simulator. GaN and
LTspice commands run natively on Windows from the repository root. The paused
DEVSIM device fixture still runs under Linux or WSL (see the later sections).

```sh
PYTHONPATH=src python -m pytest -q tests
PYTHONPATH=src python -m circuit_tools capabilities
PYTHONPATH=src python -m circuit_tools circuit-create examples/divider.json
PYTHONPATH=src python scripts/verify_ltspice_fixtures.py
PYTHONPATH=src python scripts/verify_diode_bridge.py
PYTHONPATH=src python scripts/epc2204_baseline.py
```

### LTspice installation

Install LTspice from the
[official Analog Devices download](https://ltspice.analog.com/software/LTspice64.msi).
On this host it was installed on 28 September 2026 from an MSI whose Authenticode
signature is valid (Analog Devices International UC), SHA-256
`249ebde3c84e01f4ce5b5ff78c6c7588f049bac85ae1635f968cfdbe4f4ecd03`, with
`msiexec /i LTspice64.msi /qn`. That installs per-user without administrator
rights, at `%LOCALAPPDATA%\Programs\ADI\LTspice\LTspice.exe`, version
26.1.1.0. The adapter finds that path, `C:\Program Files\ADI\LTspice`, the
`LTSPICE_EXE` environment variable, or an explicit `--executable`. An explicit
path never falls back to another installation.

### Vendor model files

EPC files live in `vendor/epc/`, which git ignores because the library is
"all rights reserved". `devices/epc/sources.json` records each URL, retrieval
date and SHA-256. EPC's server rejects requests without a browser-like
User-Agent. `scripts/epc2204_baseline.py` refuses to run if the downloaded
`EPCGaNLibrary.zip` does not match the recorded checksum, and it extracts the
`.lib` file itself.

Build and install with `python3 -m pip install .` in a virtual environment.
For an offline build, supply setuptools and wheel locally and use
`python3 -m pip wheel --no-build-isolation --no-deps .`.

## Circuit operations

`circuit-create` returns an artifact ID and a circuit revision. `inspect ID`
reads an artifact; `netlist ID` emits a SPICE body. `circuit-patch ID patch.json`
creates a child artifact. A patch contains `expected_revision` and any of
`upsert`, `remove`, and `connect`:

```json
{"expected_revision": "<revision returned by create>", "connect": {"R2": {"p": "supply"}}}
```

The supported primitives are resistors, independent voltage sources, diodes,
and MOS instances. Values use SI units; named terminals are `p/n`, `a/k`, and
`d/g/s/b`. Ground is `0`. This layer validates syntax, primitive names and
numeric values; it does not prove full circuit connectivity or model validity.
Model definitions and analysis commands belong in the simulation fixture.

```sh
PYTHONPATH=src python -m circuit_tools simulate bench.cir --library EPCGaNLibrary.lib \
  --output runs/my-bench
```

Use a new output directory for each run. The adapter keeps the exact
netlist, copies and hashes every model library the netlist loads, and retains
the LTspice log, the `.raw` waveforms, the parsed `result.json` and the
provenance record. A netlist may load only libraries passed with `--library`,
referenced by bare file name. A supplied library that itself loads other
files is rejected.

A run is `completed` only when all of these hold:
- LTspice exits with status 0;
- it writes a finite, parseable `.raw` file with at least one point;
- the log has no unrecovered failure;
- every `.meas` declared in the netlist has a value;
- the log's "Files loaded" list names only the bench and the supplied
  libraries.

Otherwise the run is `failed`, with every reason in its message. The log rules
come from real LTspice 26.1.1 output:
- Setup errors appear as `bench.cir(3): This sub-circuit name is not
  defined.`, without the word "error".
- Terminal solver failures ("Time step too small", "Singular matrix",
  "Iteration limit reached") take precedence over warning phrases such as
  "too small". A second review found this gap.
- A failed operating-point method followed by a successful one (for example
  Newton, then Gmin stepping) is a normal recovery, not an error.
- Only declared `.meas` names count as measurements; lines such as
  `temp = 27` do not.
- Unclassified lines (for example `Changing Tseed`) are kept as notices in the
  provenance record.

In batch mode LTspice 26.1.1 does not load its own standard component
libraries: an undefined `1N4148` fails as an undefined model. Acceptance belongs to a separate fixed evaluator. Missing
tools, malformed data and timeouts do not establish a physical specification
failure. SPICE input is trusted executable simulator input, not a sandboxed
upload format.

Raw-file notes established by the fixtures:
- Traces are float32 unless `.options numdgt` is above 6, which makes LTspice
  store float64. Float32 limits absolute agreement to about 1e-7 relative.
- LTspice sorts `.ac list` frequencies.
- When each `.step` has a single AC point, the file is indexed by the stepped
  parameter instead of frequency.

## Evidence and limitations

The [LTspice fixture report](../results/toolset/ltspice-fixtures.json) checks
the adapter against analytical answers:
- a resistive divider (`.op`);
- an RC step response (trace and `.meas`);
- RC magnitude and phase at the corner frequency (complex AC);
- a nested DC sweep split into its steps (float64 traces);
- an 11-point Shockley diode at 300 K;
- binary against ASCII output of the same bench.

All pass with LTspice 26.1.1. The first run failed two checks because of
evaluator assumptions (frequency ordering, and a float32 tolerance), which were
corrected as noted above. On 28 September 2026 the project owner opened the EPC2204 RDS(on) bench in
LTspice's interactive window. All seven operating-point values matched the
batch run to the window's 6 significant figures
([record](../results/toolset/ltspice-gui-check.json)). Only one
operating-point bench was compared this way.

The diode bridge in `circuit_tools.models` fits log current against voltage,
binds the result to a dataset and device revision, checks a disjoint holdout,
and gates SPICE export on validation. It is restricted to 300 K DC/OP and an
explicit voltage domain. Its unit tests use declared synthetic fixture data.
Those tests are software evidence, not physical-device validation.

The [executed bridge replay](../results/toolset/diode-bridge.json) additionally
fits real native-SPICE diode observations and simulates the exported model.
It now runs through LTspice. Its maximum current discrepancy is about 0.032%
(0.031% previously under ngspice), below the fixed 0.2% fixture tolerance.
This still uses a native-SPICE source device, not TCAD.

The [device reference report](../results/device-reference/latest.json) records
successful executions of the official diode and planar MOS examples. Run
`python3 scripts/audit_device_references.py` to check their finite terminal
currents, final biases and current conservation. These limited checks pass;
they do not qualify mesh refinement or 2D current normalization.
The [reuse spike](reuse-spike.md)
records upstream selection and remaining qualification work.

Still required for the planned first release: qualified geometry edits and
mesh refinement, NMOS DC characterization and fitting, model-domain enforcement
at circuit evaluation, direct-TCAD load-line verification, durable queued jobs
with cancellation/recovery, and tested MCP access. AC, transient, fabrication
readiness and autonomous co-design success are not claimed by this slice.

## Diode mesh qualification

With the pinned DEVSIM source and runtime configured as described in
[the reuse spike](reuse-spike.md), run:

```sh
python3 scripts/qualify_device_references.py --run
```

The runner compares three junction mesh spacings in the official 1D diode
fixture, retains solver logs, and checks convergence, final terminal-current
balance, and current stability at 0.5 V. The endpoint spacing stays fixed, so
this is a local junction-refinement check, not global mesh convergence over a
bias domain. Its current convention is A/cm² for the 1D model's unit area.
The [qualification report](../results/device-reference/qualification.json)
records the policy, tolerances, provenance, and observed results.

The executed three-mesh check used 399, 465, and 531 nodes. Its largest
adjacent current change was about 0.0012%, within the declared 0.1% relative
plus 1e-12 A/cm² absolute tolerance. All eight solves on each mesh reported
convergence. The reference audit also rejects incomplete reports, malformed
current records, and log-hash mismatches when a recorded hash is available.

This numerical diode check does not qualify the planar NMOS mesh or its 2D
out-of-plane normalization. Those checks remain prerequisites for the NMOS
characterization and circuit-model bridge.

## Device-to-circuit current units

`circuit_tools.device_units.current_per_cm_to_amperes(current_a_per_cm, width_m)`
converts a signed 2D current in A/cm of out-of-plane width to amperes using a
separately declared width in metres. For example, 3 A/cm at a 1 µm width gives
300 µA. Use it only after establishing the backend's current convention.
The lateral gate dimension in the cross-section is not this width. Exported
amperes must not receive another width multiplier in the circuit model.

With the same local DEVSIM environment, replay the normalization check with:

```sh
python3 scripts/qualify_current_normalization.py
python3 scripts/qualify_planar_mos.py --run --refinements 2
```

The [normalization report](../results/device-reference/current-normalization.json)
compares two uniform resistor cross-sections against `J = q n mu V/L` and
`I_native = J * contact_width_cm`. Both contact-current balance and the
two-width scaling check pass. This establishes the A/cm convention for the
tested cm-based 2D equations; it does not validate MOS physics or terminal charge.

The [planar-MOS report](../results/device-reference/planar-mos-qualification.json)
retains adjacent mesh comparisons at Vg = Vd = 0.5 V, Vs = Vb = 0 V and 300 K.
Subdivision preserves physical names, region areas, contact/interface lengths,
and the bounding box. Acceptance uses a fixed 1% relative plus 1e-10 A/cm
absolute current tolerance. The original mesh versus its first refinement
changes drain/source current by about 2.9%, exceeding that tolerance.
`--refinements 2` also evaluates the next finer mesh; the report records its
outcome separately and accepts only the last adjacent pair. Even a passing
endpoint comparison does not qualify an entire bias domain or local slopes.

The executed three-mesh run completed all nine solves per mesh. Bulk-region
node counts were 2249, 8752, and 34523; adjacent drain-current changes were
2.886% and 1.395%. The last comparison therefore remains **unresolved** under
the fixed 1% tolerance. The finest case took about 236 seconds, close to the
240-second per-case limit. Targeted refinement and investigation of the
near-contact/junction discretization are the next tasks; simply increasing
the tolerance would not qualify the existing mesh. These results concern
numerical stability of the research model, not fabricated-device accuracy.

## Optimized math runtime and MOS endpoint check

The [four-level uniform-mesh run](../results/device-reference/planar-mos-openblas-qualification.json)
passes the last adjacent comparison with 0.184% drain-current change, retaining
the same 1% relative plus 1e-10 A/cm absolute tolerance. All nine solves on each
mesh converge. This is an endpoint check at Vg = Vd = 0.5 V, not a bias-domain
or transconductance qualification.

The run uses workspace-local OpenBLAS, pinned in
[math-runtime-lock.json](../devices/math-runtime-lock.json). The
[same-mesh runtime check](../results/device-reference/math-runtime-comparison.json)
passes at 1e-8 relative plus 1e-10 A/cm absolute tolerance: drain, gate and
source currents match the original runtime exactly in the retained records;
the body-current difference is about 5.5e-16 A/cm. The level-2 run took about
84 seconds versus 236 seconds previously; this is an observed replay timing,
not a controlled performance benchmark. The finest level took about 545 seconds.

Prepare the optional runtime on this Ubuntu/WSL host, after the existing
DEVSIM prerequisites in [reuse-spike.md](reuse-spike.md):

```sh
mkdir -p .tools/downloads
(cd .tools/downloads && apt-get download libopenblas0-pthread=0.3.26+ds-1ubuntu0.1)
echo '7dc3b4384c02aecb87eb8b70fa26c5843a08af242f4638aa4b36922bdc4f5b04  .tools/downloads/libopenblas0-pthread_0.3.26+ds-1ubuntu0.1_amd64.deb' | sha256sum --check
dpkg-deb -x .tools/downloads/libopenblas0-pthread_0.3.26+ds-1ubuntu0.1_amd64.deb .tools/openblas
export PYTHONPATH="$PWD/.tools/python"
export LD_LIBRARY_PATH="$PWD/.tools/runtime/usr/lib/x86_64-linux-gnu:$PWD/.tools/openblas/usr/lib/x86_64-linux-gnu/openblas-pthread"
export DEVSIM_MATH_LIBS="$PWD/.tools/openblas/usr/lib/x86_64-linux-gnu/openblas-pthread/libopenblas.so.0"
export OPENBLAS_NUM_THREADS=1
python3 scripts/qualify_planar_mos.py --run --refinements 3 --timeout 600 \
  --out results/device-reference/planar-mos-openblas-qualification.json
```

Two local-refinement experiments are retained as rejected research attempts:
[transition splits](../results/device-reference/planar-mos-local-qualification.json)
and [Delaunay edge repair](../results/device-reference/planar-mos-delaunay-qualification.json).
Their early levels disagreed with the uniform sequence, and their final solves
were stopped. The local policy is not an accepted replacement for uniform
refinement. Implementation snapshots and exact mesh/log hashes support replay
of the successful uniform run.

## NMOS DC characterization

The [executed characterization report](../results/device-reference/nmos-dc-characterization.json)
records nine completed DC points in 172.5 seconds at 300 K. Vgs and Vds each
take 0.45, 0.50, and 0.55 V; source and body stay at zero. Before execution,
the experiment reserves the complete Vgs = 0.50 V slice (three points) for
holdout and the other six points for training. No model has been fitted.

Using the environment exports in the OpenBLAS section above, replay with:

```bash
python3 scripts/characterize_planar_mos.py --mesh-level 2 --timeout 600
```

The runner checks the accepted mesh, pinned upstream source, physics hash,
math libraries, and thread setting before execution. Its unique work directory
retains the experiment, runner snapshot, mesh, solver diagnostics, terminal
currents, and immutable dataset. The report links these artifacts by SHA-256.
`NMOSDataset` rejects nonfinite currents, nonconverged points, duplicate
biases, incomplete or overlapping splits, and excessive current imbalance.
Currents remain in A/cm; conversion to amperes requires an explicit device width.

A passing collection means all scheduled data satisfy this software contract.
The original collection report retains its endpoint-only qualification scope.
The separate grid comparison below adds mesh evidence at the sampled biases
and for finite-span secants; it does not establish continuous-domain or model
accuracy. These are numerical reference simulations, with no physical-device
validation claim.

### Mesh agreement over the sampled grid

The [level-3 characterization](../results/device-reference/nmos-dc-characterization-fine.json)
completed all nine points in 1037.8 seconds. The
[grid comparison](../results/device-reference/nmos-characterization-comparison.json)
passes all 36 terminal-current comparisons and six centred secant comparisons
against level 2. The largest drain-current change is 0.187163%; the largest
gm and gds changes are 0.009754% and 0.172651%, respectively. The fixed thresholds
are 1% plus 1e-10 A/cm for currents and 1% plus 1e-8 S/cm for secants.
Near-zero gate/body currents use the absolute floor; relative changes there
are not useful accuracy measures.

```bash
python3 scripts/characterize_planar_mos.py --mesh-level 3 --timeout 1800 \
  --out results/device-reference/nmos-dc-characterization-fine.json
python3 scripts/compare_nmos_characterization.py \
  results/device-reference/nmos-dc-characterization.json \
  results/device-reference/nmos-dc-characterization-fine.json \
  --out results/device-reference/nmos-characterization-comparison.json
```

The comparator verifies every required worker artifact, dataset fingerprint,
raw point records, solver-convergence receipts, experiment/split consistency,
and links to the accepted endpoint mesh and runtime qualification. It records
input, implementation and policy hashes. Invalid evidence is `unresolved`;
complete converged evidence exceeding tolerance is `fail`. Passing establishes
agreement at the nine sampled biases and for the six 0.10 V secants only.

### Reusable dataset and slope operations

The CLI can validate and store a characterization dataset, then calculate its
six centred drain-current secants. These operations share `NMOSDataset` and
`dc_secants` with the verification scripts. Replace the dataset path with the
`dataset_path` recorded in the relevant run report:

```bash
PYTHONPATH=src python3 -m circuit_tools --store runs/nmos-store nmos-import \
  results/device-reference/nmos-characterization-work/7691c1a627154de8bcc1db7dcd23cd50/dataset.json
PYTHONPATH=src python3 -m circuit_tools --store runs/nmos-store nmos-secants \
  e222b6dfd8625bd9bb85dc49b4978a358edc9509071d71caddafe87e1741eed5
```

The second command uses the artifact ID returned by the first for the retained
original dataset. The [executed secant output](../results/device-reference/nmos-dc-secants.json)
binds its calculations to that dataset fingerprint. Each metric retains its
endpoint IDs, biases, currents, span, numerator, and S/cm units. The helper
rejects incomplete/asymmetric grids and nonfinite arithmetic. Calculating a
secant does not qualify mesh or derivative accuracy.

### Central slope step-size check

The [fixed verification policy](../devices/nmos-grid-verification-policy.json)
declares half-spans of 0.05, 0.025, and 0.0125 V about Vgs = Vds = 0.50 V.
All three level-2 grids completed. The
[step-size comparison](../results/device-reference/nmos-step-size-comparison.json)
passes the fixed 1% plus 1e-8 S/cm tolerance for both adjacent comparisons.
For the final reduction, central gm changes by 0.000437% and gds by 0.001551%.
This is fixed-mesh, central-bias numerical evidence; smaller-stencil mesh
accuracy and continuous-domain accuracy remain separate checks.

With the OpenBLAS environment configured above:

```bash
python3 scripts/characterize_planar_mos.py --mesh-level 2 --half-span .025 \
  --out results/device-reference/nmos-dc-characterization-half-step.json
python3 scripts/characterize_planar_mos.py --mesh-level 2 --half-span .0125 \
  --out results/device-reference/nmos-dc-characterization-quarter-step.json
python3 scripts/compare_nmos_step_sizes.py \
  results/device-reference/nmos-dc-characterization.json \
  results/device-reference/nmos-dc-characterization-half-step.json \
  results/device-reference/nmos-dc-characterization-quarter-step.json \
  --out results/device-reference/nmos-step-size-comparison.json
```

At the smallest step, gm is 0.557864 S/cm and gds is 8.807663 S/cm;
their ratio is about 0.06334. This diagnostic suggests revisiting the physical
device or operating point before targeting voltage gain. It is not an
executed amplifier result. The intended physical-device revision and
independent circuit validation remain unfinished.

## Generated planar NMOS (candidate lc1)

The upstream `gmsh_mos2d` reference is retired as the amplifier candidate and
kept as a numerical regression fixture (see AGENTS.md). Its replacement is
generated from one specification,
[planar-nmos-lc1.json](../devices/planar-nmos-lc1.json): geometry, doping,
junction grading, contacts, supply and mesh spacings. `scripts/planar_nmos.py`
builds the structure with DEVSIM's internal 2D mesher (no gmsh) and the upstream
`simple_physics` package: constant mobility, SRH, no velocity saturation,
no gate tunneling or interface charge, 300 K. The spec's `junction_depth` is the
half-point of the erfc source/drain profile; the metallurgical junction is
reported by `inspect`. Currents are A/cm (x100 = uA/um).

With the DEVSIM/OpenBLAS environment exports above:

```bash
python3 scripts/planar_nmos.py inspect devices/planar-nmos-lc1.json --mesh-scale 2
python3 scripts/planar_nmos.py sweep devices/planar-nmos-lc1.json --mesh-scale 2
for s in 2 1 0.5; do
  python3 scripts/planar_nmos.py op devices/planar-nmos-lc1.json --vg 0.6 --vd 1.65 --mesh-scale $s
done
# metrics and plots (needs matplotlib for the PNG; Windows Python works)
python scripts/analyze_planar_nmos.py results/nmos-design/lc1/sweep-mesh2.json \
  --structure results/nmos-design/lc1/inspect-mesh2.json
python scripts/analyze_planar_nmos.py --op results/nmos-design/lc1/op-mesh2.json \
  results/nmos-design/lc1/op.json results/nmos-design/lc1/op-mesh0.5.json
```

A point is recorded only after a DEVSIM solve that did not raise, and only if
terminal currents are conserved within 1e-6 relative plus 1e-9 A/cm. The
observed conservation residual is an absolute floor of about 1e-11 to 2e-10
A/cm, so currents below about 1e-9 A/cm (0.1 pA/um) are marked unresolved.
The Newton relative-update target is 1e-6: tighter targets stall in roundoff
noise from near-zero electron densities when the device is off at high drain bias.

**Structure** ([inspect](../results/nmos-design/lc1/inspect-mesh2.json)):
L = 1 um gate over 10 nm oxide with n+ poly; surface junctions at 0.544 and
1.456 um (44 nm gate overlap each side, 0.91 um metallurgical channel);
source/drain junction 0.153 um deep; contacts touch only n+ (source/drain),
p (body) and n+ poly (gate).

**Curves** ([sweep](../results/nmos-design/lc1/sweep-mesh2.json),
[analysis](../results/nmos-design/lc1/analysis-mesh2.json), plot
`results/nmos-design/lc1/analysis-mesh2.png`; coarse mesh, 2883 bulk nodes,
208 s): subthreshold slope 79.5 mV/dec, linear-extrapolated Vt 0.38 V
(constant-current 0.34 V), DIBL 6.5 mV/V, Ion 570 uA/um and Ioff 13.5 pA/um at
3.3 V (ratio 4e7), flat output saturation. At Vd = 1.65 V, gm/gds is 241, 113
and 69 at Vg = 0.5, 0.75 and 1.0 V (the old reference: 0.063). These agree
with hand estimates (Vt about 0.3 V, SS about 77 mV/dec). The coarse-mesh curves
are exploratory; only the operating point below has a mesh check.

**Amplifier operating point** ([amplifier-point](../results/nmos-design/lc1/amplifier-point.json)):
common-source stage, RD to VDD = 3.3 V, Vout,Q = VDD/2 for swing. |Av| = gm RD /
(1 + gm RD / (gm/gds)) with gm RD = (gm/Id)(VDD - Vout), so |Av| of about 10 needs
gm/Id of about 7 /V, reached at Vgs = 0.6 V (Vov about 0.2-0.25 V). Finest-mesh
stencil (45879 bulk nodes): Id 4.19 uA/um, gm/Id 7.20 /V, gm/gds 172. With W =
23.9 um: Id = 100 uA, RD = 16.5 kOhm, gm = 0.72 mS, gm RD = 11.9, **Av = -11.1**,
330 uW. gm/gds exceeds the stage gain about 15x. Across three meshes (4x node steps)
gm/Id and gm/gds change 0.9%/0.6% and 1.3%/0.7%; Id changes 3.5% then 2.1%,
so the bias current carries roughly 3% mesh uncertainty. With gm/Id = 7.2 /V, a
10 mV threshold shift moves Id by about 7%, so the circuit should set Vgs for
the target Vout from the fitted model rather than fixing 0.6 V.

Not yet done: a compact model fitted over the operating region, circuit-simulator
simulation of the amplifier with that model, a direct-TCAD load-line check,
and dynamic behavior. Constant mobility without velocity saturation or
mobility degradation makes strong-inversion currents optimistic; the chosen
low-overdrive point is less affected.

## EPC2204 vendor-model baseline (Stage 1, first slice)

`scripts/epc2204_baseline.py` runs the unmodified `EPC2204` subcircuit from
EPC's LTspice library (version 1.105, 10 June 2026) at the conditions of the
datasheet's electrical-characteristics table (datasheet revised 26 November
2024). Its comparison rules are fixed in the script:
- limit compliance and deviation from the typical value are reported
  separately. Being inside a datasheet limit does not show accuracy.
- A row is flagged for review when it is outside a limit or more than ±25%
  from the typical value. The band is a screening aid, not an acceptance
  tolerance.

All benches use `.options reltol=1e-6` (see the gate-charge finding below).
The script writes [the baseline report](../results/gan/epc2204-baseline.json)
and [simulated curves](../results/gan/epc2204-model-curves.json): output and
transfer characteristics, COSS against VDS, and the VGS–QG gate-charge curve.
These are for the later comparison with digitized datasheet curves.

Result, 28 September 2026 (second revision): all 14 benches complete.

| Quantity | Model | Datasheet typ (limits) | Deviation from typ | Review |
|---|---|---|---|---|
| RDS(on), 5 V, 16 A | 4.40 mΩ | 4.4 (max 6) mΩ | 0.0% | no |
| VGS(th), 4 mA | 1.17 V | 1.1 (0.8–2.5) V | +6.4% | no |
| VSD, 0.5 A | 1.61 V | 1.6 V | +0.3% | no |
| CISS / CRSS / COSS at 50 V | 644.5 / 2.31 / 304.8 pF | 644 (max 851) / 2.3 / 304 (max 456) pF | +0.1 / +0.6 / +0.3% | no |
| COSS(ER) / COSS(TR), 0–50 V | 401.4 / 501.6 pF | 401 / 501 pF | +0.1 / +0.1% | no |
| QOSS, 50 V | 25.1 nC | 25 (max 38) nC | +0.3% | no |
| QG, 50 V, 16 A, 5 V | 5.65 nC | 5.7 (max 7.4) nC | −0.8% | no |
| QGS | 1.35 nC | 1.8 nC | −24.9% | no (at the band edge) |
| QGD | 0.65 nC | 0.8 nC | −18.6% | no |
| QG(TH) | 0.73 nC | 1.0 nC | −27.5% | yes |

**Gate-charge finding.** The first baseline reported QG = 3.8 nC (−33%). That
was a simulation artifact.
- *Cause:* with LTspice's default `reltol` (1e-3), the transient loses gate
  charge once the transistor is on. QG fell to 2.5 nC at a 0.02 ns step and
  2.45 nC at 2 mA drive. Changing the integration method, `chgtol` or the
  solver did not help; `reltol=1e-6` did.
- *Now:* QG = 5.652 nC. Tightening to 1e-7 changes it by 3e-9 (relative).
  That shows insensitivity to further `reltol` tightening at the chosen time
  step, not absolute accuracy at that level.
  QG from the model's own charge equations, with parameters read from the
  local library, between the simulated start and VGS = 5 V states, is
  5.647 nC (0.1% agreement, declared tolerance 1%). A small-signal check at
  VGS = 3–4.5 V gives about 1085 pF, matching the equations' 1.085 nC per
  volt there.
- *Separate probe:* LTspice honours charge expressions that depend on other
  nodes' voltages; a known-answer probe gave exactly 2.000 mA.
- *What remains:* QGS, QGD and QG(TH) are 19–28% below the typicals under
  both the transient and the equations. These are unresolved differences in
  extracted values, not established model errors, until EPC's boundary
  definitions are matched. Candidates are EPC's extraction
  definitions (not stated), test conditions, or the model's
  sub-threshold/plateau charge. QGD depends strongly on where the plateau is
  taken to end: 0.38 / 0.65 / 1.00 nC for VDS = 10 / 5 / 1 V. No model
  tuning is justified.

Gate-charge bench self-checks, all recorded in the report:
- *Starting bias:* VGS 0.046 V, VDS 50.0 V, 16 A in the clamp diode, the
  transistor off.
- *Gate-current balance:* residual under 0.7 nA against a 10 mA drive.
- *Integration resolution:* halving the samples changes QG by 2e-6.
- *Drain transition:* at VGS = 5 V, VDS is 0.070 V and the transistor carries
  16 A.
- *Plateau:* about 2.05 V.
- *Drive current:* the declared check (10 mA against 2 mA, 0.5% tolerance)
  **fails** at +0.57%. A diagnostic added afterwards integrates the model's
  gate-leakage current: 6.6 pC at 10 mA, 35 pC at 2 mA. With leakage removed,
  the stored charge agrees to 0.06%. This diagnostic evidence supports
  leakage as the main cause; it does not conclusively resolve the
  difference.

Other results:
- *COSS consistency:* output charge integrated from the small-signal COSS
  curve agrees with a 0 → 50 V transient ramp to 0.002% (tolerance 2%).
- *Temperature:* RDS(on) rises by a factor of 1.70 from 25 °C to 125 °C in
  the model. The datasheet curve has not been digitized.
- *Not independent validation:* the close agreement in resistance,
  capacitance, output charge and total gate charge may reflect the quantities
  EPC fitted the model to.

The equation comparison checks numerical consistency with the vendor
model. These are model-to-datasheet consistency results. Datasheet values are
vendor-described, and nothing here is a hardware measurement. The first
revision of this report used one combined outcome that called QG
"inside-datasheet-limits" only because it was below the maximum. It was
replaced after review.

### Gate-charge curve against datasheet Figure 7

EPC's datasheet figures are vector drawings, so their curves can be read
exactly rather than traced from an image.

- **Digitizing.** `scripts/digitize_datasheet_figures.py` reads every plotted
  curve on datasheet pages 2–3. It needs PyMuPDF, which runs under WSL;
  Windows Smart App Control blocks it on the host.

  ```sh
  python3 scripts/digitize_datasheet_figures.py   # under WSL
  python scripts/compare_epc2204_gate_charge.py
  ```

  Revision 2 calibrates each axis from the plot's own geometry:
  - the plot frame (the dark stroked rectangle);
  - grid lines found in a 600 dpi render (PyMuPDF does not return them as
    drawings).

  Each tick label is paired with its nearest line, and the fit uses the line
  positions. Text boxes sit up to 3.3 pt off their ticks, so the label
  positions only choose the line. Points are clipped to the frame.
  `tests/test_digitize_figures.py` pins this; it runs under WSL.

  Revision 1 fitted the axes to text-box centres and clipped to the label
  range. See the correction note below.
- **Comparison rule.** The rule in `scripts/compare_epc2204_gate_charge.py`
  is: model VGS within ±0.10 V of the datasheet VGS at every vertex's charge.
  It was chosen after the datasheet coordinates were first extracted, but
  before any model comparison. The model curve is shifted by 0.028 nC for the
  bench's 0.046 V starting gate voltage.
- **Result (digitizer revision 2):** [pass](../results/gan/epc2204-fig7-comparison.json).
  The worst difference is 0.018 V, at the plateau onset.

| Feature (same algorithm for both) | Model | Datasheet curve | Datasheet table |
|---|---|---|---|
| Plateau voltage | 2.06 V | 2.05 V | — |
| Plateau start (plateau-based QGS) | 1.37 nC | 1.40 nC | QGS 1.8 nC |
| Plateau width, ±0.05 V band | 1.03 nC | 1.01 nC | QGD 0.8 nC |
| Charge at VGS = 1.17 V (model VGS(th)) | 0.75 nC | 0.76 nC | QG(TH) 1.0 nC |
| Charge at VGS = 5 V | 5.66 nC | 5.67 nC | QG 5.7 nC |

- **What it shows.** The unmodified model reproduces the gate-charge curve EPC
  drew. Under plateau-based boundaries, EPC's curve does not reproduce EPC's
  table values for QGS, QGD and QG(TH). The table may use different
  definitions, or come from different source data (for example, a different
  measurement or device population). This comparison cannot tell which. These
  remain unresolved extracted-value differences; they are not evidence of a
  model error.
- **Limits.** The close fit may reflect that EPC fitted the model to this
  curve, so it is consistency, not independent validation. Both sides are
  vendor material; no hardware has been measured.
### Other datasheet curves (Figures 1–6, 8, 9)

```sh
PYTHONPATH=src python scripts/epc2204_curve_benches.py   # extra model benches
python3 scripts/digitize_datasheet_figures.py            # under WSL
python scripts/compare_epc2204_curves.py
```

- **Extra benches.** `scripts/epc2204_curve_benches.py` adds the model
  simulations the baseline lacked:
  - RDS(on) against VGS at 8/16/24/32 A (25 °C) and 16 A (125 °C);
  - CISS and CRSS against VDS;
  - reverse conduction at 25 and 125 °C;
  - RDS(on) at 0–150 °C.

  At low VGS, a forced drain current beyond the channel's capability drives
  VDS to meaningless values. Only the range each figure plots is compared.
- **Tolerances.** These were fixed before any of these figures were digitized
  or compared. Each is a screening tolerance on vendor "typical" curves:

  | Figures | Tolerance |
  |---|---|
  | 1, 2, 8 (current) | 5% + 1.6 A |
  | 3, 4 (RDS(on)) | 5% + 0.16 mΩ |
  | 5a (capacitance, linear) | 5% + 9 pF |
  | 5b (capacitance, log) | 0.05 decades |
  | 6 (QOSS / EOSS) | 5% + 0.4 nC / 5% + 0.016 µJ |
  | 9 (normalized RDS(on)) | 0.03 |

- **Curve assignment.** Labels come from the legends, which have coloured
  swatches. PyMuPDF does not return the swatches as drawings, so the digitizer
  samples each swatch's colour from a render and matches it to a curve (colour
  distance at most 0.05). For Fig. 6 it reads the direction of the two arrows
  that point each curve to its axis.

  Independently, physical ordering rules assign the same labels without using
  the values under test:
  - more current at higher VGS;
  - less current and more resistance at 125 °C;
  - higher drain current reaches a given RDS(on) at higher VGS;
  - CISS > COSS > CRSS;
  - charge is concave in voltage.

  A figure whose legend and ordering disagree is marked unresolved. They agree
  in every figure.

[Result (digitizer revision 2), 28 September 2026](../results/gan/epc2204-curve-comparison.json):
all 23 curves pass at every compared point.

| Figure | Curves | Worst error / allowed |
|---|---|---|
| 1 Output characteristics, 25 °C | VGS 2, 3, 4, 5 V | 0.06–0.16 |
| 2 Transfer, VDS = 3 V | 25, 125 °C | 0.15, 0.16 |
| 3 RDS(on) vs VGS | 8, 16, 24, 32 A | 0.07–0.09 |
| 4 RDS(on) vs VGS, 16 A | 25, 125 °C | 0.03, 0.04 |
| 5a/5b Capacitances | CISS, COSS, CRSS | 0.01–0.03 |
| 6 Output charge / stored energy | QOSS, EOSS | 0.08, 0.07 |
| 8 Reverse conduction | 25, 125 °C | 0.23, 0.21 |
| 9 Normalized RDS(on) | 0–150 °C | 0.03 |

**Correction (digitizer revision 1).** The first comparison reported
- 22 of 23 passes;
- an EOSS failure below about 28 V;

and attributed the failure to EPC's drawing of Fig. 6. That was wrong: the
failure came from our digitizer. Revision 1 fitted the axes to tick-label text
centres, which sit about 2.3 pt from the Fig. 6 grid lines. It then clipped
points to the label range, which removed valid low-energy points. The owner's
review found this. With frame and grid calibration:
- EPC's energy curve starts at the origin;
- it passes the unchanged tolerance.

The Fig. 5a/Fig. 6 cross-check now agrees within about 1–3%. It integrates
EPC's own Fig. 5a COSS curve, without the model:

| VDS | Fig. 6 as drawn | From EPC's Fig. 5a COSS | Model |
|---|---|---|---|
| 10 V | 0.040 µJ | 0.039 µJ | 0.039 µJ |
| 50 V | 0.503 µJ | 0.501 µJ | 0.502 µJ |

**Limits.**
- All comparisons are against vendor-drawn typical curves. The model was
  probably fitted to them, so agreement is consistency, not independent
  validation.
- Temperature curves test the model's `Temp` dependence; no self-heating is
  modelled.

## EPC9097 switching bench (G3, before layout extraction)

```sh
python scripts/epc9097_switching.py              # LTspice; about 20 min (see "Run time")
python scripts/digitize_epc9097_qsg_waveforms.py # PyMuPDF; ran on the Windows host on 28 September 2026
python scripts/compare_epc9097_qsg.py
```

**Board sources.** The EPC9097 files are recorded in `devices/epc/sources.json`
(`board_files`); they are kept in the git-ignored `vendor/epc/epc9097/`. Facts
taken from them:
- the driver is the uP1966E (BOM and QSG v3.0; the 2020 schematic still says
  uP1966A);
- 1 Ω turn-on and 0 Ω turn-off gate resistors (R80–R83);
- seven 220 nF, 100 V loop capacitors;
- 10 ns default dead time, set at the driver inputs;
- the driver's internal bootstrap supplies the high side (the synchronous
  bootstrap option is not fitted).

EPC publishes **two layouts**. One is 6-layer (the ODB++, the landing-page
stackup and the 2024 test-point report). The other is 4-layer, "B5239 Rev
2.0" (the Gerber zip, 2023). Both carry the same 38 nets. Parasitic extraction
must use the revision of the board under test, which is not yet known.

The ODB++ component data do not match the EPC9097 BOM for the power stage.
All 107 reference designators match, but:
- Q1 and Q2 are listed as EPC2619, not EPC2204;
- the gate resistors are 4.7 Ω on and 1 Ω off, not 1 Ω and 0 Ω;
- U80 is a uP1966A, not a uP1966E.

The Q1/Q2 footprint is EPC's D0133 package (2.50 × 1.50 mm), whose STEP model
EPC links from the EPC2204 product page. The 6-layer file therefore looks like
the same design with a different population, but whether its copper matches a
shipped EPC9097 is not established. The Rev 2.0 layout PDF names R80–R83
without values. Details are in `devices/epc/sources.json`
(`odb_population_vs_bom`). The simulation uses the BOM's values.

**Bench.** `scripts/epc9097_switching.py` runs a buck double pulse with two
unmodified EPC2204 models at the conditions of EPC's published waveforms:
48 V → 12 V, 1 MHz, 2.2 µH, 10 ns dead time. It is converter-equivalent: Q1
turns off at the load current plus half the 4.1 A ripple, and turns on again
after the converter's 750 ns off time, at the load current minus half the
ripple.

Assumptions, all recorded in the report:
- **Driver.** EPC publishes no uP1966E SPICE model, so the driver is
  behavioural. Each output pin is a ramped source behind the datasheet's
  typical resistance (0.7 Ω source, 0.4 Ω sink), connected only while that pin
  is active. The ramps (8.25 ns up, 3.73 ns down) were calibrated in the same
  run to the datasheet's 8 ns rise and 4 ns fall into 3000 pF.
  - A first version varied the switch resistance instead. It could not slow
    the edge below the RC limit (4.6 ns), so it was replaced.
  - Propagation delay is omitted, since it shifts both channels equally.
- **Supplies.** A 4.8 V ideal floating high-side supply and 5 V on the low
  side.
- **Capacitors and bus.** The loop capacitors are one ideal 1.54 µF, with no
  DC-bias derating. The bus network behind them uses assumed values.
- **Parasitics.** All loop inductance is lumped at Q1's drain and **swept**
  (0.01–0.8 nH), not extracted. Gate-loop and common-source inductance are
  zero.

[Result, 28 September 2026](../results/gan/epc9097-switching-ideal-layout.json),
10 A load (Q1 turns off at 11.9 A and on at 7.9 A):

| Loop L | Rise 10–90 % | Peak V(sw) | Ringing | Eon (Q1) | Fall 90–10 % | Eoff (Q1) |
|---|---|---|---|---|---|---|
| 0.01 nH | 1.19 ns | 48.3 V | none | 1.33 µJ | 3.20 ns | 0.50 µJ |
| 0.2 nH | 0.87 ns | 51.8 V | 640 MHz | 1.23 µJ | 3.04 ns | 0.51 µJ |
| 0.4 nH | 0.70 ns | 69.4 V | 448 MHz | 1.08 µJ | 2.95 ns | 0.45 µJ |
| 0.8 nH | 0.70 ns | 95.7 V | 305 MHz | 0.71 µJ | 2.93 ns | 0.55 µJ |

- **Energies.** Eon and Eoff are terminal V·I integrals of Q1, as a
  measurement would take them. Eoff therefore includes Q1's stored output
  energy, which is dissipated at the next turn-on.
- **10 pH row.** The report lists 2.9 GHz "ringing" on a 0.02 V overshoot; that
  is a detector artifact, not ringing.
- **Physics check.** The ringing frequency implies 309–342 pF with each swept
  inductance. That is the model's COSS near 48 V (304 pF at 50 V), as expected
  for the loop resonating with the lower FET's output capacitance.
- **Sensitivity to loop inductance.** In this simplified bench, the switch
  node reaches 96 V from a 48 V bus at 0.8 nH, near the 100 V rating (the
  QSG requires ringing below 100 V).
  - The figure is conditional: gate-loop and common-source inductance are
    omitted, the driver is approximate, and the capacitor and bus properties
    are assumed.
  - It shows that the peak voltage is sensitive to loop inductance, which is
    why extraction is the priority. It does **not** establish a safe
    operating envelope or a reliable margin below the rating.
- **Insensitive quantities.** The fall time changes by only 9% across the
  sweep. The reverse-conduction plateau before the rise lasts exactly the
  dead time plus 1.1 ns (5.1 / 11.1 / 17.1 ns for 4 / 10 / 16 ns). The lower
  gate's peak during the rise is 0.35–0.37 V (0.59 V with the maximum driver
  resistance). That is below the 0.8 V minimum threshold, so the simulation
  shows no false turn-on.
- **15 A** (at 0.4 nH): fall 2.10 ns, Eon 1.31 µJ, the same 21 V overshoot.
- **Numerics.** For the 0.4 nH, 10 A reference case, halving the maximum step
  and tightening `reltol` to 1e-7 together changes each checked metric by
  less than 0.11% (tolerance 2%). That supports this case's numerical
  stability. The other sweep cases were not refined separately.

**Run time.** Most cases solve in about 3 s. Three 0.4 nH cases took 330–380
s: LTspice took about 6 million sub-femtosecond steps during Q1's turn-off,
while VGS1 passed through 1.2–1.5 V. The log says "Changing Tseed to 2e-15".
The waveform stays continuous. The fine-step rerun of the reference case took
8 s without the stall and agrees with it; the other two stalled cases (4 and
16 ns dead time) have no separate refinement. Two script fixes made the run fit in memory on this host:
- the bench saves only the seven traces the metrics use (`.save`), with Q1's
  drain current read as I(Lloop);
- the script keeps only each run's status summary.

**EPC's measured waveforms.** QSG Figs. 12–14 (0, 10 and 15 A; 10 V/div,
10 ns/div) are raster oscilloscope screenshots, not vector drawings.
`scripts/digitize_epc9097_qsg_waveforms.py` reads them from pixels:
- the grid, from grey-pixel rows and columns fitted to a uniform pitch;
- zero volts, from the channel ground marker;
- the trace, from the blue pixels.

Resolution is about 0.3 V and 0.2 ns per pixel. Its check: the settled swing
must be within 2 V of the 48 V bus, with grid lines within 1.5 px of uniform.
All six panels pass, with swings of 49.1–49.8 V. The low level reads −1.3 V
at every load, a likely marker offset; treat levels as ±1.5 V.

A damped-cosine fit finds persistent ringing at 129–134 MHz in all six panels
([digitized data](../results/gan/epc9097-qsg-waveforms.json)). That is the same
frequency at 0, 10 and 15 A and on both edges. Similar frequency across loads
does not identify where the resonance sits. It could belong to the power loop,
the bus network or the probe connection; the source remains unidentified.

[Comparison](../results/gan/epc9097-switching-vs-qsg.json), simulation at
0.4 nH. It is diagnostic, with no pass/fail tolerance: the measured values were
digitized before the comparison categories were chosen, the loop inductance is
not extracted, and EPC does not state the probe, bandwidth or probing point.

| Quantity (what it tests) | 10 A meas / sim | 15 A meas / sim |
|---|---|---|
| Fall time (device output charge, Qoss/I) | 3.97 / 2.95 ns | 2.59 / 2.10 ns |
| Dead-time plateau (driver timing) | 8.7 / 11.1 ns | 8.7 / 11.3 ns |
| Plateau depth below settled low (lower FET reverse conduction) | 3.7 / 1.9 V | 3.6 / 2.0 V |
| Rise time (loop L, drive, bandwidth) | 2.37 / 0.70 ns | 2.44 / 0.68 ns |
| Persistent ringing | 130 MHz / 448 MHz | 131 MHz / 449 MHz |

What this shows, and what it does not:
- **Fall time.** Both measurement and simulation fall faster at the higher
  current, in about the Qoss/I proportion. The measurement is 23–35% slower.
  - Possible causes: switch-node capacitance the bench omits (inductor
    winding, PCB, probe), or measurement bandwidth.
  - This is not evidence against the device model until those layers are
    measured separately (G4).
- **Plateau.** In simulation it is dead time + 1.1 ns. Under the present
  behavioural driver and plateau definition, the measured 8.7 ns corresponds to
  an effective dead time of about 7.6 ns rather than the nominal 10.
  - This is a model-dependent hypothesis, not a measurement of EPC's dead
    time.
  - If true, it would be within the RC setting's tolerance plus the driver's
    delay mismatch (1.5 ns typical, 6 ns maximum).
  - The measured plateau is deeper than simulated. The cause is unresolved:
    the level offset, the probe, or ground-path voltage are candidates.
- **Rise time and ringing.** The measured rise is 2.4 ns against a simulated
  0.7 ns.
  - *Bandwidth estimate.* If the simulated edge were exact, the measurement
    system's own rise time would be about 2.3 ns (roughly 150 MHz). This
    assumes the simulation is correct, so it cannot independently show that
    bandwidth caused the difference. A slower real edge (gate-loop or
    common-source inductance, a weaker driver) would also explain it.
  - *Implied inductance.* A 130 MHz ring with one COSS (304 pF) would need
    4.8 nH, an order of magnitude above the swept range. The resonance could
    instead involve other capacitances or a bus or probe path.
  - *Candidate explanations*, none established: the measurement path, the
    bus network, and parasitics the bench omits. Characterising our probes on
    a known edge (G4) and extracting the loops (G3) can separate them.
  - Overshoot is not compared, because the measurement bandwidth is unknown.
- **Not yet tested.** The 0 A case (Fig. 12) needs a negative valley current
  and is not simulated yet.

**Next (G3; the gate stays open until the matching layout's parasitics are
extracted).**
1. Identify the layout revision of our physical board.
2. Separately, identify the revision used for EPC's published waveforms; the
   two need not match. Until evidence connects a revision to the board or the
   measurements, the 6-layer and 4-layer files stay separate candidates.
3. Verify the extraction tool on a known-answer geometry.
4. Extract the power and gate paths, including their return paths.
5. Rerun the switching comparison with those parasitics. The unmodified
   transistor model is preserved.

## FastHenry inductance extraction: tool qualification (G3)

FastHenry 3.0.1 is the candidate extraction tool. It is MIT's original solver,
with FastFieldSolvers' 64-bit Linux fixes
([ediloren/FastHenry2](https://github.com/ediloren/FastHenry2), branch `master`,
commit `363e43e`).

- **Licence.** MIT's 1994 licence permits "internal, noncommercial" use and
  prohibits distribution without MIT's written consent. The source and binary
  therefore stay in the git-ignored `.tools/FastHenry2`. The owner confirmed on
  28 September 2026 that the project uses it internally and does not
  distribute it (commit `95b0fad`). These are restrictive MIT-authored terms,
  not the standard permissive MIT License. The notice was checked in the pinned
  local `src/fasthenry/induct.h` and the
  [upstream source](https://github.com/ediloren/FastHenry2/blob/master/src/fasthenry/induct.h).
  Separate builds do not by themselves establish permission for broader partner
  or commercial use; that scope needs a separate institutional determination.
  Keep source and binaries out of teaching repositories and shared artifacts.
- **Build** (Ubuntu 24.04 under WSL, gcc 13.3). `-fcommon` restores the
  pre-GCC-10 linking of shared globals that this old code needs; no other flag
  changes.

  ```sh
  cd .tools && git clone https://github.com/ediloren/FastHenry2.git && cd FastHenry2
  git checkout 363e43ed57ad3b9affa11cba5a86624fad0edaa9
  ./config x64 && make fasthenry CFLAGS='-O -DFOUR -m64 -fcommon'
  sha256sum bin/fasthenry   # bcd646263ac24d6e724ac6f3c11101be1fb42d5bf8e0d80884e53505d7a7e299 on this host
  ```

- **Qualification.** `python scripts/fasthenry_known_answer.py` runs on
  Windows and calls FastHenry through `wsl`. Tolerances were declared in the
  script before the first run. Each case uses three meshes, and the two finest
  must agree within 1%.

[Result, 28 September 2026](../results/gan/fasthenry-known-answer.json):

| Case | FastHenry (finest mesh) | Reference | Error | Declared check |
|---|---|---|---|---|
| A: bar 10 × 1 × 0.035 mm, 1 Hz, partial self-inductance | 6.978 nH | 6.969 nH (Grover) | +0.13% | pass (1%) |
| B: go-and-return bars 5 mm apart, 1 Hz | 10.646 nH | 10.635 nH, 2(L − M) (Grover) | +0.10% | pass (1%) |
| C: plates 10 mm wide, 0.127 mm gap, 35 µm Cu, 100 MHz, per length | 16.27 nH/m | 15.51 nH/m (Palmer, perfect conductors) | +4.9% | **fail** (3%) |
| D(i): same plates, 1 GHz | 15.73 nH/m | 15.76 nH/m (Palmer, gap + one skin depth) | −0.19% | pass (3%) |
| D(ii): ratio 1 GHz / 100 MHz | 0.96638 | 0.96618, (h + δ₁)/(h + δ₂) | +0.02% | pass (1%) |

Inductance per unit length is the difference between 20 mm and 10 mm loops,
which removes end and port effects. Mesh changes between the two finest meshes
are 0.06–0.26%.

- **Case C.** C failed its declared check, and the failure is kept in the
  report. The subsequent diagnosis points to an incomplete reference rather
  than a tool error. Palmer's formula assumes perfect conductors, but at 100 MHz copper
  carries current in a 6.6 µm skin depth. That adds internal inductance of
  about δ/h = 5.2%.
- **Case D.** D was declared after that diagnosis and before it was run. Its
  frequency dependence is a prediction with nothing fitted. With the skin
  correction, C's own value is −0.12% from the corrected reference;
  this is recorded as a diagnostic, not a pass.
- **Mesh lesson for extraction.** At 1 GHz the coarsest mesh (9 × 3
  filaments) is 2.5% off. Filaments must resolve the skin depth, so every
  board extraction needs its own mesh-refinement check.
- **Scope.** This qualifies FastHenry for straight conductors and thin-
  dielectric plane pairs like the EPC9097 power loop. It does not yet cover
  vias, plane meshing with holes, or the EPC2204's solder-bar connections.
  Those need their own checks when the board geometry uses them.

**Current handoff.** Committed A/B/D results supersede the earlier message
that the replacement check had not run. This documentation update makes no
claim of a fresh solver run. Prepare via qualification and geometry readers
for each layout candidate independently. Board extraction waits for the
physical board's identity and fitted population; a matched comparison against
EPC additionally needs the measurement-board identity. Editable Altium files
help geometry conversion but do not alone establish fitted components.

The [active plan](../plans/gan-halfbridge-pipeline-plan.md) and
[V1 review record](gan-workflow-methods-review.md) specify the adopted layout
search, stage handoffs and blind validation. These are future work; they do
not alter executed results or justify tuning the vendor model.
