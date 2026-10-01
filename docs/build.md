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

### EPC90133 power-loop geometry and ports (G3 extraction, step 1)

```sh
PYTHONPATH=src python scripts/epc90133_power_loop.py   # results/gan/epc90133-power-loop.json, renders in results/gan/epc90133-power-loop/
```

Step 1 of the exploratory extraction the owner set on 29 September 2026. The script identifies the loop
and fixes the ports; it extracts nothing. Paste openings only locate the parts. A contact is the solder-mask
opening on copper, because the EPC2302 land is mask defined and fab note 7 makes the mask 1:1 with the Gerber.
Component windows are rasterized at 5 µm. Checks C1–C5 were declared in the docstring before the first run.

Result (run 3): C2–C5 pass; C1 fails, for a board reason that does not affect the contacts.
- **EPC2302 footprints.** Q1 and Q2 each have seven contacts in the datasheet orientation (fit RMS 0.011 mm,
  next-best orientation 0.25 mm). Pin centres lie within 0.021 mm of the land pattern, and every contact is
  mask-defined all round. The nets match the pin functions: Q1 drains on VIN and sources on SW, Q2 drains on
  SW and sources on GND. The two gates are on separate nets. The mask openings are 0.075 mm wider than EPC's
  recommended land pattern (0.375 vs 0.30 mm; 0.475 vs 0.40 mm), and the lengths match within 0.015 mm. I read the
  aperture widths in the Gerber header before writing the check, so this is a finding, not a blind test.
- **C1 (paste on mask-open copper) fails.** On the outer pins 1, 2 and 7 the stencil opening is a full rounded
  rectangle, while the mask stays closed between the side-flank notches, so 16–20% of each opening prints on
  mask-covered copper. The board's stencil also differs from the datasheet stencil drawing (one opening per long pin, not two).
- **Capacitors.** Ci1–Ci7 (0603 pads, 1.45 mm pad pitch) lie in a top-side row. Cm1–Cm10 (0805 pads, 1.95 mm)
  lie on the bottom directly beneath and extend further right. Each capacitor has one VIN and one GND contact.
- **Two stacked loops.** Top loop: Ci → top VIN copper → Q1 → SW → Q2 → 35 GND vias (13 in Q2's source pins,
  22 in a row just below Q2) → mid-layer 1 → GND vias beside the Ci row → Ci. Second loop: G5, G6 and the
  bottom layer repeat the VIN/SW pours, and Cm returns through them to Q1's drain vias. All vias run top to bottom.
- **Via layers.** Q1's source vias and Q2's drain vias (SW) bond only to the top, G5, G6 and bottom layers.
  They pass through mid-layers 1–4 on slot pads inside long clearances in the GND planes. Q1's drain-pin vias
  (VIN) also pass through those planes. So the return plane directly under both FETs is slotted and perforated,
  a plane-hole case that is not qualified. Q1 pin 2's vias also bond to mid-layer 1, where the datasheet
  places the high-side gate return. Kelvin candidates: the pin 2 via nearest the gate (0.45/0.49 mm from pin 2's gate end).
- **Ports.** Each net is one conductor with a reference terminal (VIN: Q1.D, SW: Q2.D, GND: Q2.S). A branch
  port runs from each other terminal to it: every Ci/Cm VIN and GND pad, and Q1.S. A single FastHenry run then
  gives the coupled matrix of all branches, including mutual terms between nets, rather than one loop number.
  Baseline junction: each terminal's nodes inside its contacts are one equipotential; the alternative is centroid nodes.
  Not modelled: the EPC2302 package and internal metallization (the vendor model has no package inductance) and
  capacitor ESL/ESR, which the bench states separately.
- **Fabrication facts used.** Vias up to 0.010 in are filled with non-conductive material and plated over (IPC-4761
  type VII), with barrel plating of at least 20 µm (the actual thickness is not given). Mask and layer
  registration are each within 0.003 in.

Run history. Run 1 failed C2 and C5 because my component windows also held neighbouring parts' contacts
(its report is kept as `epc90133-power-loop-run1-failed.json`). Contacts cut by a window edge are now dropped,
with the windows unchanged. Run 2's via labels were wrong: per-via disks counted slot pads as functional,
and keying groups on the contact split via pairs. Run 3 measures distance from the hull of the joined vias.
Limits: component positions come from paste and silkscreen, not a placement file, and the 1-mil board raster
does not resolve sub-pitch copper. Ci/Cm reference designators follow the silkscreen order read from the renders.

### EPC90133 exploratory extraction and switching sensitivity (G3 steps 2–3, interim)

```sh
PYTHONPATH=src python scripts/epc90133_extract.py A:m1:mid I:m1:mid B:m1:mid   # results/gan/epc90133-extraction/
PYTHONPATH=src python scripts/epc90133_switching.py                            # results/gan/epc90133-switching-sensitivity.json
```

Specifications are in each script's docstring, fixed before its first board run. This work is exploratory:
the via check failed, plane holes and via arrays are unqualified, and two meshes show sensitivity, not convergence.

Extraction (coarse mesh m1, 100 MHz), with the diagnostic loop inductance at Q1 (Q2 and every capacitor shorted):

| Variant | Copper | Capacitors | Loop L | Time |
|---|---|---|---|---|
| A, via junction mid / gap / pad | top layer, mid-layer 1 | Ci | 0.502 / 0.493 / 0.500 nH | ~1.5 min |
| I | all 8 layers | Ci | 0.300 nH | 71 min |
| B (reference) | all 8 layers | Ci, Cm | 0.281 nH | 110 min |

The network, not this one number, goes to the bench: every branch pair keeps its mutual inductance.
The via representation moves the loop inductance by under 2% in A. The additional copper moves it by −40%.
Ci current shares in A range from 4% (Ci1) to 23% (Ci6).

Switching (double pulse at Fig. 9 edge currents, 28.9 A turn-off and 11.1 A turn-on, both matched after a
timing correction; driver, dead time, 25 °C and an ideal probe fixed):

| Case | Rise overshoot above bus | Ringing | tr | tf |
|---|---|---|---|---|
| A, three via variants | 54.5–54.9 V | 203–205 MHz | 0.88 ns | 4.01 ns |
| I | 40.0 V | 266 MHz | 0.83 ns | 4.05 ns |
| B | 35.7 V | 283 MHz | 0.83 ns | 4.08 ns |
| B, capacitor body ESL ×0.5 / ×2 | 34.3 / 38.1 V | 288 / 273 MHz | 0.83 ns | 4.09 / 4.07 ns |
| ideal copper (1 pH branches) | 2.1 V | 1151 MHz | 1.30 ns | 4.39 ns |
| QSG Fig. 9 measurement, read by eye | about 7 V | about 0.6 GHz | 1.7 ns | 3.7 ns |

- The overshoot comes almost entirely from the extracted copper. With ideal copper it falls to 2 V.
  The via representation is immaterial. The extra copper layers are material (55 → 40 V), and so is adding Cm (40 → 36 V).
  The capacitor-ESL assumption changes the overshoot by about ±2 V, which is material by the declared 1 V rule, but it is secondary.
- **None of the extraction variants resembles the measurement.** Fig. 9 rings at a higher frequency than any
  extracted case and with far less overshoot. Raising the loop inductance (package terms, which the literature notes
  suggest are missing) would lower the frequency further. So the disagreement probably does not come from the loop
  inductance alone. Candidates, none tested: missing damping (Coss loss, frequency-dependent resistance), missing
  switch-node capacitance, the behavioural driver's edge speed (simulated tr 0.83 ns against 1.7 ns measured), and the
  unknown probe path behind Fig. 9, whose ringing may belong to the measurement loop. The rise time and switching
  losses also depend on gate charge (EPC2302 Fig. 7 exception).
- Numerical check: on A, maxstep/2 and reltol/10 changed no waveform metric by more than 1e-4. The first ringing
  detector reported 3.98 GHz there by picking numerical wiggles; it was replaced by settled-level crossings with
  hysteresis before this sweep. On B, the same check exceeded the adapter's 600 s limit and has not run.
- The periodic-buck equivalence case failed to find its operating point on B (the inductor initial condition); it has
  not yet run. Until it does, this double pulse is not shown to be equivalent to Fig. 9's continuous operation.
- Still running or queued: B with gap and pad vias, A on the fine mesh m2. Added before their first run: package
  inductance of 50 and 150 pH per terminal (assumed), and a switch-node capacitance of 135 pF to GND and 2 pF to
  VIN (parallel-plate overlap from the Gerbers, no fringing).

Test runs 3–4 (29 September 2026, later the same day):
- B with gap vias: loop L 0.271 nH (−4% from mid); with pad vias 0.261 nH (−7%, 132 min). On the full board, with 784 via
  segments against A's 87, the via representation matters more than on A (<2%), but far less than the extra copper (−40%).
  Its effect on switching has not yet been run through the bench.
- Numerical check, run on A because B exceeds the 600 s limit: halving maxstep and dividing reltol by 10 changes
  every metric by less than 1% (ringing frequency −0.02%, damping +0.9%). **Pass.**
- Switch-node capacitance, 135 pF on B: overshoot 35.7 → 34.6 V, ringing 283 → 266 MHz, tf 4.08 → 4.22 ns.
  This is too small to explain the gap to Fig. 9.
- **Package inductance (50 and 150 pH per terminal, on A): numerically unresolved, so do not use.** With the package
  inductors, V(SW) shows single-timestep spikes, up to about 90 V, while it should be flat at the bus voltage. These are either
  numerical artefacts or a resonance the 20 ps step does not resolve. The printed metrics (tr 1.54/3.0 ns, overshoot 36/24 V,
  a non-monotonic tf of 7.0/4.0 ns) are contaminated by them. Next: a finer step or a damping resistance across the package
  inductors, and a check that the spikes are gone before any metric is read.
- On B, the package and periodic cases exceeded the adapter's 600 s limit and were moved to A.
- The periodic-buck case (3 periods of 4 µs at a 20 ps maximum step) also exceeded 600 s on A. The double pulse is
  therefore still not shown to be equivalent to Fig. 9's continuous operation. Options: raise the adapter's limit
  (a change to the accepted G1 adapter), use a coarser step away from the edges, or use fewer, shorter periods at a matched
  steady state. Test 4's report: `results/gan/epc90133-switching-test4.json` (its package cases are unusable, as above).

### EPC90133 QSG Fig. 9 digitized (G3 comparison target)

```sh
python scripts/digitize_epc90133_qsg_fig9.py   # PyMuPDF, Windows host; results/gan/epc90133-qsg-fig9.json
```

Fig. 9 looks like one wide scope picture, but the PDF stores it as two raster screenshots side by side
(xref 119, rising edge; xref 117, falling edge), with EPC's labels drawn over them as text. A 250 kHz on-time of
about 1.15 µs cannot fit on a 10 ns/div screen, so these are two separate zoomed captures. The distance between
the edges in the printed figure is not time. The method and checks are in the script's docstring. They were written
after I viewed the images and before the first run. The grid pitch is detected per axis (the pixels are not square:
31.8 px/div vertically, 50.7 px/div horizontally), with the trace masked out. Its flat parts had made a 1.5× pitch
look best in a first probe. Zero volts is each panel's settled low level; only the rising panel carries a ground marker.

| Check | Result |
|---|---|
| grid lines uniform (≤ 1.5 px), both panels' pitch within 1 % | pass (0.45 px; pitches equal) |
| time scale: digitized edge against EPC's printed tr 1.7 ns / tf 3.7 ns (±0.4 ns) | pass (1.68 / 3.63 ns) |
| volt scale: settled swing within 2 V of 48 V | **fail**: 45.8 V (rising), 44.5 V (falling) |
| zero: ground marker within 1 V of the settled low level | pass (0.9 V) |

The volt-scale failure is recorded, not tuned away. Either the displayed amplitude reads 5–7 % low (probe gain
or attenuation setting), or the switch node's swing really was smaller than 48 V (for example, supply drop under
load). Voltages are therefore also compared as a fraction of the swing. Time metrics do not depend on it.

Measured (vendor-described; probe, bandwidth and probing point not stated):

| Edge | Metric | Value |
|---|---|---|
| rising (Q1 turns on at the valley current) | 10–90 % rise | 1.68 ns |
| | overshoot above settled level | 5.7 V (0.124 of swing) |
| | ringing (damped-cosine fit, first crest to 25 ns) | 264 MHz, decay time 7.8 ns, damping ratio ≈ 0.077 |
| | dead-time plateau before the rise | 7.1 ns at about −2.5 V (minimum −3.6 V) |
| falling (Q1 turns off at the peak current) | 90–10 % fall | 3.63 ns |
| | undershoot below settled level | 4.6 V, no ringing above pixel noise |

**Declared extraction range** (added 30 September 2026 after an external review; method in the digitizer's
docstring). Each metric is recomputed over 324 combinations of reasonable extraction choices (rising edge; 54 for
the falling edge): two trace estimators, three settled-level windows, two ring-fit starts, three ring-fit ends,
and the grid pitch at ±2 standard errors. Ranges: rise 1.67–1.69 ns, overshoot 5.69–5.73 V, ringing 262–265 MHz
(damped-cosine fit; 266–267 MHz from crest spacing), damping ratio 0.072–0.077, plateau 7.09–7.11 ns, fall
3.62–3.64 ns. One pixel is 0.20 ns and 0.31 V, so edge times are known to about a pixel, not to the second
decimal. These ranges cover the extraction choices only. They do not cover the unknown probe, probing point or
scope processing behind the screenshot, nor systematic effects of line rendering. A simulated value counts as
"consistent with the declared extraction range" if it lies inside the range widened by one pixel (time and voltage) or
inside the range (frequency and damping). A second review (30 September 2026) noted that these ranges measure sensitivity to
the processing choices only. They are not a complete uncertainty interval: the unknown probe response, the
failed volt-scale check and other raster or fit errors are outside them. So "consistent" here means consistent
with the declared extraction range, and the narrow 262–265 MHz range should not be read as the frequency's
full uncertainty.

**Correction to the earlier by-eye reading.** The by-eye values in the tables above (about 7 V, about 0.6 GHz)
came from the stitched picture. The digitized ringing is 262–265 MHz. Extraction variants I (266 MHz) and B
(282 MHz) are within 1–8 % of it, so the earlier statement that "no variant resembles the measurement" was wrong
for frequency, although neither variant lies inside the declared extraction range. The large gaps are the overshoot
(B 35 V against 5.7 V), the rise time (0.83 against 1.68 ns) and the damping (B damping ratio about 0.008–0.010
against 0.072–0.077).

### EPC90133 switching test 5: package spikes removed, periodic buck equivalence (G3)

```sh
PYTHONPATH=src python scripts/epc90133_switching.py --study periodic --output results/gan/epc90133-switching-periodic.json
```

**Package-inductance spikes.** In test 4 the time step collapsed to about 2×10⁻²⁰ s wherever the spikes appeared.
They also appeared during the flat on-state, not only at edges. On the stored A-pkg50pH netlist I tried two remedies:

- a resistor across each package inductor, R = 2π·10 GHz·L (3.1 Ω for 50 pH), removed every spike, with
  trapezoidal or Gear integration;
- Gear integration alone left 625 spikes.

With the resistor, the two integration methods agree within 0.1 % on every metric. So the spikes were numerical,
and test 4's 7.0 ns fall time was one of them. The clean result for A with 50 pH is: fall time 3.92 ns, rise time
1.54 ns, overshoot 36.2 V, ringing 179 MHz, damping ratio 0.014. At the ringing frequency the resistor carries about
3 % of the inductor current. Every case now runs a spike check (no sample more than 5 V from the mean of its
neighbours); a case with spikes is marked unusable.

**Periodic buck equivalence (A-m1-mid). Pass.** Previous starts failed:

- run 1: an operating point with 11 A in the inductor and both FETs off;
- test 4: a `uic` start, which stalled at 0.77 ps;
- test 5, run 1: an operating point with the low-side FET on, found only by LTspice's pseudo-transient fallback
  (which the adapter rightly reports as failed). A `.nodeset` guess did not help.

The bench now starts like the double pulse, from the all-off, zero-current operating point. A first pulse ramps
the inductor to the peak current, and three 250 kHz periods follow. The duty cycle from the double pulse's average
slopes drifted −0.30 A per period, because the edges and dead times lose volt-seconds. One correction from that
drift (duty cycle 0.2916 → 0.2952) gives:

- valley currents 11.36, 11.34 and 11.34 A: spread 0.17 %, within the declared 2 %;
- edge currents 28.91 A (at the peak) and 11.34 A (at the valley);
- against the double pulse, every metric changes by less than 1.3 %: fall time +1.0 %, rise time −0.2 %,
  overshoot +0.1 %, frequency 0.00 %, damping ratio +1.3 %.

On A, the double pulse therefore reproduces continuous-operation edges at matched currents. Scope of this check: A's
network, with ideal driver supplies, 25 °C and an ideal output-voltage source. It supports the double pulse on the
other networks, but it is not a direct check of B or of the physical board. The same check on B is test 6 (below). Reports: `results/gan/epc90133-switching-periodic.json`, with
run 2 (the drifting duty cycle) kept as `epc90133-switching-periodic-run2-drift.json`.

**Running B cases.** Six B cases in parallel all exceeded the 600 s limit, and so did two in parallel with one
A run. Each LTspice process uses up to 16 threads, and concurrent processes slow each other far more than the job
count suggests. B cases run one at a time (`--jobs 1`).

### EPC90133 switching test 5: candidate causes of the gap to Fig. 9 (G3 diagnosis)

```sh
PYTHONPATH=src python scripts/epc90133_switching.py --study causes --output results/gan/epc90133-switching-causes.json
PYTHONPATH=src python scripts/epc90133_switching.py --study causes --only B-m1-mid-ms100 B-esr1-ms100 B-cgd \
    --output results/gan/epc90133-switching-causes-2.json
python scripts/compare_epc90133_fig9.py --sim results/gan/epc90133-switching-causes.json \
    results/gan/epc90133-switching-causes-2.json          # results/gan/epc90133-fig9-comparison.json
```

The specification is in the switching script's docstring ("Test 5"). Each case changes one thing from the unmodified
reference B-m1-mid. The comparison script passes every saved trace through zero-phase Gaussian scope responses
(none, 2 GHz, 1 GHz, 500 MHz, 350 MHz) and measures it with the digitizer's own definitions. Its "resembles the
measurement" criteria were fixed before the first comparison: rise and fall time within 25 %, overshoot within 3 V
and within 0.05 of swing, frequency within 10 %, damping ratio within a factor 1.5. These are judgement criteria,
not validation tolerances.

Numerical controls, all passing, but on related configurations rather than on every case that uses them:

- the B package, combined and follow-up cases use a 100 ps maximum step, because 20 ps exceeded 600 s even with B
  running alone. Against 20 ps, 100 ps changes every metric by at most 1.3 % on B without package inductance and on A
  with it. A B package case itself was not checked in test 5; test 6 checks one directly;
- the package damping-resistor corner at 20 GHz instead of 10 GHz changes every metric by less than 0.4 % on A,
  except the damping ratio (−8 %, below the 20 % materiality threshold). Test 6 repeats it on B;
- every case: edge currents within tolerance and no spikes.

These checks support the B package results as exploratory evidence. If a B package case becomes central to a
decision, it has to be verified directly.

Results: the generated table [`results/gan/epc90133-fig9-summary.md`](../results/gan/epc90133-fig9-summary.md)
(ideal probe; declared extraction range; criteria passed at any bandwidth). It is written by
`scripts/compare_epc90133_fig9.py` from the comparison report and is the single source for headline numbers. The
values quoted below come from it. The damping ratio there comes from the digitizer's damped-cosine fit; the bench's
own log-decrement value is slightly higher (0.010 for B). The 1 Ω ESR case first exceeded 600 s at 20 ps; it is
listed as excluded and was rerun at 100 ps.

What these cases establish, and what they do not:

- **No tested case or combination meets all the criteria.** Every case passes the fall time. The frequency passes
  only for cases without package inductance, and the rise time only with it. The overshoot passes for none of them:
  the lowest is 14.3 V (combined, 350 MHz Gaussian). The damping passes only for the 1 Ω ESR probe (ζ 0.066), which
  is a sizing device, not a physical model.
- **Package inductance, applied equally to drain and source, is the only tested change that brings the rise time
  into the criterion** (50 pH: 1.67 ns, within about a pixel of the measured 1.67–1.69 ns). It also lowers the
  frequency (284 → 223 MHz), and tripling it barely lowers the overshoot further (21 → 18.5 V). Because drain and
  source carried the same value, these cases do not show which path acts. The driver returns at the source pads, so
  the source term is common-source inductance, but its share is not isolated. Test 6 separates them. The EPC2302
  package inductance is not published; 50 pH is an assumption.
- **A weaker driver lowers the overshoot without moving the frequency** (35 → 23 V at the datasheet maximum
  resistance). The real uP1966E output resistance is unknown between typical and maximum.
- **Scaling the diagonal branch resistances by 1.68 changes the damping by 7 %.** This tests one approximation of
  frequency-dependent copper loss. The bench drops the off-diagonal resistance and uses a single frequency, so it is
  not a general test of a frequency-dependent impedance network. For scale: the extracted loop resistance is 2 mΩ at
  100 MHz, and the measured decay implies roughly 60–70 mΩ at this loop's impedance (L ≈ 0.28 nH, C ≈ 1.1 nF).
- **Capacitor ESR damps the later ringing but hardly the first peak** (0.3 Ω: ζ ×3, overshoot 35 → 34 V; 1 Ω: ζ
  0.066, overshoot 31 V). This holds for loss placed in the capacitors. Loss elsewhere (in the FET's output
  capacitance, in the switch node, or in a measurement path) need not behave the same way, and none was tested. The
  source of the missing loss is not identified.
- **A zero-phase Gaussian bandwidth limit cannot explain the waveform under the tested assumptions.** At 350 MHz the
  B overshoot drops only 35 → 27 V, with the frequency and damping unchanged. Under the Gaussian model, cutting a
  20 V ring to 5.7 V at 264 MHz needs about 140 MHz, which would itself make the rise at least about 2.4 ns. Probe
  loading, the probing location and resonant measurement paths (ground lead, adapter) are outside this test and
  remain candidates.
- **A linear 13.6 pF gate–drain capacitance has a modest effect** (overshoot 35 → 29 V, rise 0.83 → 0.91 ns). It
  restores the Fig. 7 Miller-charge deficit only on average (2.87 nC datasheet plateau against the model's 2.19 nC at
  50 V). The real discrepancy is voltage dependent and unresolved, so this does not show that the gate-charge
  discrepancy is minor.
- **The dead-time plateau differs.** Simulated 10–12 ns at −1.7 to −1.9 V, measured 7.1 ns at −2.5 V. The BOM
  populates R620/R625 with 120 Ω (checked 30 September 2026), which QSG Fig. 4 maps to 10 ns, and the bench turns
  that into an 11.9 ns switch-node plateau. An effective dead time of roughly 5 ns is therefore an inference that
  depends on the behavioural driver model; it is not a measurement of the driver's dead time. The EPC9097
  comparison, made with the same modelling approach, also inferred a shorter dead time (about 7.6 ns). That is not
  independent evidence that the driver is the cause. The deeper measured plateau (−2.5 V against −1.8 V) is
  unexplained (third-quadrant behaviour or measurement).

Figure: `python scripts/plot_epc90133_fig9.py --sim results/gan/epc90133-switching-causes.json
results/gan/epc90133-switching-causes-2.json --cases B-m1-mid:none B-pkg50pH:none B-drvmax:none B-esr1-ms100:none`
writes `results/gan/epc90133-fig9-overlay.png`. The falling edge agrees closely; on the rising edge every simulated
ring is 3–6 times the measured one.

**Where this leaves G3 (after test 5).** Within these approximations, the overshoot gap needs a slower or softer
turn-on of Q1, and the damping gap needs about 60–70 mΩ of equivalent loss that no modelled element supplies. The
tested power-loop refinements (via representation, the coarse extraction variants, capacitor ESL, switch-node
capacitance) changed results by a few percent to tens of percent. They do not bound circuit paths that are missing
altogether, namely the gate loop and the common-source return, and no finer-mesh (m2) board extraction has run.
Layout is therefore not excluded as a material contributor; test 6 bounds the missing paths. Hardware measurements
are needed to separate the driver, package, loss and measurement candidates, and the hardware plan should test them
as explicit competing explanations with held-out operating conditions. Whether simulation alone can narrow them
further is open. G3 stays open.

### EPC90133 switching test 6: separated gate and source paths (G3 diagnosis, after review)

```sh
PYTHONPATH=src python scripts/epc90133_switching.py --study paths --output results/gan/epc90133-switching-paths.json
PYTHONPATH=src python scripts/epc90133_switching.py --study periodic --periodic-ext B-m1-mid --periodic-maxstep 100e-12     --output results/gan/epc90133-switching-periodic-B.json
python scripts/compare_epc90133_fig9.py --sim results/gan/epc90133-switching-causes.json     results/gan/epc90133-switching-causes-2.json results/gan/epc90133-switching-paths.json
```

Why: an external review (30 September 2026) pointed out that the bench returns both drivers at the FET source pads and
has no gate-loop inductance, and that test 5's package cases put equal inductance on drain and source, so they could
not show which path matters. The specification is in the switching script's docstring ("Test 6"). It adds one
inductance per FET to B at the 100 ps step, with assumed values (not extracted) and the 10 GHz damping resistor.

Changes to the bench, recorded before the rerun:

- reports are saved after every case, because the first test-6 run was interrupted and lost its report;
- each test-6 transient ends 80 ns after the valley turn-on. In the first run the 0.5 nH gate case stalled (steps of
  1e-19 s; Gear integration also stalled) at Q1's second turn-off, 150 ns after the valley turn-on, an edge no metric
  uses. The 2 nH gate case of that run also failed, because I stopped its LTspice process while it was running,
  mistaking it for an orphan.

Results against B at the same step (from `comparison_to_reference` in the report; values from the generated summary):

| Case (one inductance per FET) | tr (ns) | overshoot (V) | f (MHz) | ζ | change against B |
|---|---|---|---|---|---|
| B, 100 ps step | 0.83 | 35.0 | 284 | 0.008 | — |
| drain 50 pH | 1.10 | 39.7 | 243 | 0.010 | overshoot +12 %, f −14 % |
| source 50 pH, driver at the die (Kelvin) | 1.10 | 39.7 | 243 | 0.010 | identical to drain 50 pH |
| source 25 pH, driver at the pad (common-source) | 1.16 | 22.4 | 267 | 0.012 | overshoot −39 %, f −6 % |
| source 50 pH, driver at the pad (common-source) | 1.51 | 17.4 | 250 | 0.018 | overshoot −51 %, f −11 % |
| gate 0.5 nH | 0.82 | 36.0 | 283 | 0.008 | overshoot +3 % |
| gate 2 nH | 0.80 | 38.2 | 282 | 0.008 | overshoot +10 % |
| drain + source 50 pH (test 5's package case) | 1.67 | 21.3 | 223 | 0.017 | overshoot −43 %, f −21 % |

What this shows:

- **The common-source coupling, not the inductance itself, is what lowers the overshoot.** 50 pH in the source with the
  driver returning at the die behaves exactly like 50 pH in the drain: more loop inductance, higher overshoot, lower
  frequency. The same 50 pH with the driver returning at the pad halves the overshoot and slows the edge.
- **Common-source inductance is the only tested single change that moves the overshoot and rise time towards the
  measurement while keeping the frequency near it.** At 50 pH the case meets three of the five criteria (rise time,
  within the declared extraction range plus a pixel; fall time; frequency 250 MHz, within 10 %). The overshoot (17.4 V
  against 5.7 V) and the damping (0.018 against about 0.075) still fail, at every tested probe bandwidth.
- **Test 5's equal drain-and-source package case mixed two opposite effects.** Its frequency drop came mostly from the
  drain term.
- **Gate-loop inductance alone is minor and slightly adverse** (0.5–2 nH: overshoot +3 to +10 %).
- **Layout is therefore not excluded.** The board's own common-source path (the source copper shared by the power loop
  and the gate-drive return between the FET source pad and the Kelvin via) and the package's source inductance are both
  unextracted and unpublished, and this path is now a leading candidate. Extracting it (L_cs and L_ks in the parasitic
  set, plan section 4) is the next simulation step. The values here are an assumed bracket, and the EPC2302 package's
  internal split between power source and Kelvin source is not known.

Numerical checks, direct on the new configurations:

- gate 0.5 nH at a 50 ps step against 100 ps: every metric within 0.1 % (pass);
- B-pkg50pH at 50 ps: every metric within 0.1 % of 100 ps, but its spike detector found one 5.2 V single-sample
  spike 847 ns after the first turn-off, in the flat off-state, far from both measured windows. By the declared rule
  the case is unusable, so the automatic comparison excludes it. It is recorded as a failed check, not a pass;
- B-pkg50pH with the 20 GHz damping-resistor corner exceeded 600 s: no result.

So the B package results remain supported by checks on related configurations, as before, plus one direct check that
formally failed on a spike outside the measured windows.

Direct checks of the leading common-source case, B-Ls50-csi (second review, 30 September 2026;
`results/gan/epc90133-switching-csi-checks.json`). All pass, and none is material:

| Check | overshoot | rise | frequency | damping ratio |
|---|---|---|---|---|
| 50 ps step instead of 100 ps | 0.0 % | 0.0 % | 0.0 % | 0.0 % |
| damping-resistor corner 20 GHz instead of 10 GHz | +0.7 % | −0.2 % | −0.1 % | −7.8 % |
| damping-resistor corner 5 GHz | −1.4 % | +0.3 % | 0.0 % | +15.7 % |

The overshoot, rise time and frequency of this case are numerically stable to about 1.5 %. Its damping ratio is
partly set by the numerical damping resistors (−8 to +16 %), so it should be quoted with that spread. In the same
run, device metrics moved to die terminals: Q1's peak Vds reads 52.09 V at the die against 51.75 V at the pad.

**Periodic buck equivalence on B. Pass.** Same method as on A, on the full-board network at the 100 ps step, compared
with the double pulse at the same step (`results/gan/epc90133-switching-periodic-B.json`). After one duty-cycle
correction, the valley currents of three successive periods are 11.34, 11.33 and 11.32 A (spread 0.17 %), and every
metric is within 0.7 % of the double pulse: fall time +0.6 %, rise time −0.1 %, overshoot 0.0 %, frequency +0.1 %,
damping −0.7 %. Scope: ideal driver supplies, 25 °C and an ideal output-voltage source, without package or
common-source inductance. It is not a check of the physical board.

### EPC90133 extraction G and switching test 7: extracted gate-drive and source paths (G3 diagnosis)

```sh
python scripts/epc90133_extract.py G:m1:mid --jobs 2        # ~3.4 h; run detached, not from a session shell
PYTHONPATH=src python scripts/epc90133_switching.py --study gateloop --jobs 2 --timeout 3600 \
    --output results/gan/epc90133-switching-gateloop.json
PYTHONPATH=src python scripts/epc90133_switching.py --study gateloop --only B-m1-mid-ms100 G-m1-mid-ctl \
    --timeout 3600 --output results/gan/epc90133-switching-gateloop-ctl.json
PYTHONPATH=src python scripts/epc90133_switching.py --study gateloop --only G-m1-mid G-m1-mid-ctl-hs G-m1-mid-ctl-ls \
    --jobs 3 --timeout 3600 --output results/gan/epc90133-switching-gateloop-split.json
PYTHONPATH=src python scripts/epc90133_phase_check.py
python scripts/compare_epc90133_fig9.py --sim results/gan/epc90133-switching-causes.json \
    results/gan/epc90133-switching-causes-2.json results/gan/epc90133-switching-paths.json \
    results/gan/epc90133-switching-gateloop-ctl.json results/gan/epc90133-switching-gateloop-split.json \
    results/gan/epc90133-switching-gateloop.json
```

Why: test 6 left the board's own gate-drive and shared source paths unextracted, and its leading case used an
assumed common-source inductance. Extraction G adds them. Its specification is in `scripts/epc90133_extract.py`
(variant G) and test 7's in the switching script's docstring. Before the first run, an external audit added: both
FETs' die gate-source extremes and drain currents (a 0 V source in Q2's drain), the driver PHASE-ball voltage,
and a matched control, because G changes the extraction window, local mesh and source terminals as well as the
gate paths.

**Extraction G-m1-mid** ([result](../results/gan/epc90133-extraction/G-m1-mid.json), run 4, 12,279 s, 80,922
filaments, 47 ports). Its checks pass: all ports connected, every gate terminal has nodes, L symmetric (0.05 %),
positive definite. Runs 1–3 failed or were stopped (long `.equiv` lines; a session-shell time limit; stopped for
the day), and run 4 ran as an independent process. It is an exploratory estimate under declared geometry
assumptions: vias and plane holes are unqualified, the local mesh has no convergence evidence (one mesh), and
the package interior is ideal.

| Quantity | G-m1-mid | B-m1-mid |
|---|---|---|
| power-loop inductance at Q1 | 0.257 nH | 0.281 nH |
| board common-source inductance, Q1 (high side) | 0.9 pH | not represented |
| board common-source inductance, Q2 (low side) | 47.7 pH | not represented |

The high side's gate return is a separate top-layer trace to source pin 2, so it shares almost no source copper
with the power loop. The low side's returns through the top GND pour and shares much more. The 8 % lower loop
inductance comes from the changes that are not gate paths (window, local mesh, split source pins), since the loop
does not include the gate nets.

**Switching, test 7** (bench values; B at the 100 ps step; overshoot above the bus):

| Case | overshoot (V) | tr (ns) | f (MHz) | ζ | Q2 die VGS during the rise, max / min (V) |
|---|---|---|---|---|---|
| B-m1-mid-ms100 | 35.7 | 0.83 | 282.5 | 0.010 | 1.07 / −0.03 |
| G-m1-mid-ctl (G network, B's ideal gate drive) | 32.3 | 0.83 | 295.6 | 0.011 | 1.07 / −0.03 |
| G-m1-mid-ctl-hs (high side ideal, low side extracted) | 32.0 | 0.83 | 296.8 | 0.014 | 2.37 / −1.61 |
| G-m1-mid-ctl-ls (low side ideal, high side extracted) | 25.3 | 0.89 | 298.2 | 0.011 | 1.07 / −0.02 |
| G-m1-mid (both extracted) | 25.2 | 0.88 | 299.4 | 0.014 | 2.00 / −1.26 |
| G-m1-mid-ms50 (step check) | 25.2 | 0.88 | 299.3 | 0.014 | 2.00 / −1.26 |
| G + package source 25 pH (assumed) | 13.3 | 1.23 | 279.3 | 0.021 | 1.88 / −1.59 |
| G + package source 50 pH (assumed) | 11.1 | 1.66 | 261.2 | 0.026 | 1.93 / −1.88 |

The G-ctl, ctl-hs and ctl-ls controls were declared before their runs (ctl before G's first result, the split
after ctl). Every case passes its edge-current and spike checks. The 50 ps rerun was made for G alone and changes
no G metric by more than 0.1 %; G+25/50 pH and the controls ran at 100 ps only. Earlier halved-step checks on B
(B-Ls50-csi) do not directly cover G+package, so G-m1-mid-Ls50 needs its own 50 ps check before a decision rests
on its Fig. 9 match.

What this shows, scoped to this unvalidated model and exploratory extraction:

- **The G–B overshoot change (−10.4 V) splits into two parts.** The network change (G-ctl against B) accounts
  for −3.4 V and +4.6 % frequency, consistent with the 8 % lower loop inductance (which alone predicts about
  +4.3 %). The board's gate-drive copper (G against G-ctl) accounts for −7.0 V and a 6 % slower rise.
- **The high-side gate-drive path carries that −7 V; the low-side path adds the damping.** ctl-ls matches G
  in overshoot and rise time, and ctl-hs matches G-ctl; the two parts add up to within 0.3 V.
- **Supported mechanism within this model: magnetic coupling of the forward gate path, about 10 pH in effect.**
  The split controls establish that the high-side gate path causes the simulated reduction. The calculation below
  (100 MHz, zero gate current) supports coupling as the explanation, but it does not separately quantify the
  coupling's contribution against the gate path's own impedance during switching.
  `scripts/epc90133_gate_coupling.py` ([result](../results/gan/epc90133-gate-coupling.json)) repeats the
  extractor's L_cs solve (1 A commutation-loop current, 100 MHz) and adds the voltages induced in the forward
  gate branches (driver ball → gate resistor → gate), which g_summary's L_cs leaves out. The induced die VGS per
  ampere, as an inductance with L_cs's sign:

  | FET | return side (L_cs) | forward, turn-on path | total, turn-on path | total, turn-off path |
  |---|---|---|---|---|
  | Q1 (high side) | +0.9 pH | +9.1 pH | +10.0 pH | +5.3 pH |
  | Q2 (low side) | +47.7 pH | −4.1 pH | +43.6 pH | +38.7 pH |

  Q2's value comes from shared source copper (classic common-source inductance) and has the same sign, so Q1's
  +10 pH also opposes its turn-on. It is the same order as test 6, where 25 pH at the pad lowered the overshoot by
  12.6 V. One frequency and one mesh: an estimate. For layout (Stage 2) this means the forward gate path's
  placement relative to the power loop matters, not only the shared source copper.
- **An invalid check, kept.** Case G-m1-mid-nogpk removed every coupling term between gate-drive and power
  branches ([report](../results/gan/epc90133-switching-gateloop-coupling.json): overshoot 9.4 V, rise 1.54 ns).
  It was declared as a coupling test, but the branch network's terms also represent shared copper (the branches
  share reference nodes, for example 238 pH between the PHASE-ball return and Q1's source pin 2), so removing
  them adds spurious common-source inductance instead of removing coupling. Its result carries no physical
  meaning; the calculation above replaces it. After an external audit (1 October 2026) the case declaration and
  its committed report carry `interpretation_invalid`, and the materiality, Fig. 9 and PHASE scripts exclude any
  case that carries it, whatever its `usable` flag (which only records the numerical checks).
- **The low-side path disturbs Q2's gate.** With it extracted, Q2's die VGS reaches 2.0 V during the rise
  (2.37 V with the high side ideal, whose faster turn-on raises di/dt), against 1.07 V without it. The
  unmodified model conducts 3.9 A at VGS 2.0 V and 38 A at 2.3 V (DC, VDS 48 V, 25 °C); its VGS(th) is
  1.51 V, and the datasheet allows 0.8–2.5 V. The terminal currents include capacitive current, so channel
  conduction is not measured directly. This is a false-turn-on margin question for the hardware (the Q2
  gate probe in the plan), and it means the lower overshoot cannot be read as an improved design.
- **With assumed package source inductance, G moves closer to Fig. 9 than B did.** In the Fig. 9 comparison
  ([summary](../results/gan/epc90133-fig9-summary.md)), G+50 pH passes rise time, fall time and frequency
  (1.66 ns, 3.93 ns, 262 MHz), as B-Ls50-csi did, with a lower overshoot (11.3 V against 17.4 V). G+25 pH passes
  the same three. Overshoot (about twice the measured 5.7 V) and damping (0.025 against 0.077) still fail at
  every probe bandwidth. G alone passes only the fall time: its 300 MHz frequency is more than 10 % above the
  measurement. The package value is assumed, one waveform cannot separate the layers, and the simulated
  dead-time plateau (about 12 ns against 7.1 ns) is still unexplained. So this shows consistency, not
  identification, and G3 stays open.
- **PHASE-ball stress is unresolved.** The raw PHASE-to-GND minima (−8 V on G, −24 and −28 V with package
  inductance) are sub-picosecond spikes (half-widths 0.2–0.35 ps) at the ideal low-side stage's switching
  instant. Averaged over a declared 10 ps window, the extremes are −2.2 to −3.7 V and +47 to +64 V, inside
  −5/+85 V ([check](../results/gan/epc90133-test7-phase-check.json)). This shows only that the *filtered*
  waveform is inside the rating; averaging does not establish that the discarded excursions are numerical
  artefacts. The step dependence was checked on G alone (raw minimum −8.2 V at 100 ps, −9.4 V at 50 ps; averaged
  values identical), not on the package-inductance cases with the largest minima. Resolving it needs a physically
  regularized driver output stage (finite switching speed) or a targeted numerical check on those cases. The raw
  values in the test 7 reports are kept. Simulated sensitivity results, not a safe limit (narrowed after an
  external audit, 1 October 2026). Test 8, below, follows this up.

Running notes: the LTspice adapter's per-run bound was raised from 600 s to 3600 s (`MAX_TIMEOUT_S`), because
G's first timing run exceeded 600 s. A timeout still returns a failed run. Test 7 run 1 was stopped after that
timeout, and its partial report is kept (`epc90133-switching-gateloop-run1-stopped.json`). With the higher bound,
single G LTspice runs took 2.4–9.5 min with two or three running at once, except ctl-ls (about 28 min per run,
cause not examined).

Next, in order: record this in the hardware plan's predictions (Q2 VGS during the high-side turn-on; the
high-side gate-loop coupling as a separate hypothesis); a second-mesh or window check of G only if a decision
depends on the 8 % loop difference; and the measurement itself, which is what can separate these layers.


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

### EPC90133 switching test 8: driver output stage regularized (PHASE-ball stress)

Question: is test 7's PHASE-ball undershoot (raw minima to −28 V) a property of the circuit or of the ideal driver
stage? In test 7 each driver pin is a source behind a switch that opens from 1 mΩ to 100 MΩ in about a picosecond,
with nothing on the pin, so the current in the extracted gate-return copper is cut almost instantly. A CMOS output
pin has output capacitance and body/ESD diodes that carry that current. Test 8 (`--study phase`, declared in
`scripts/epc90133_switching.py` before its runs) adds to every driver ball a capacitance to its stage reference
and clamp diodes to the reference and to a 5 V rail. The uP1966E datasheet gives neither value, so the capacitance
is bracketed at 10 and 100 pF (assumptions). The declared criteria judge the raw extremes, without averaging.

```sh
PYTHONPATH=src python scripts/epc90133_switching.py --study phase --jobs 3 --timeout 3600     --output results/gan/epc90133-switching-phase.json                       # run 1
PYTHONPATH=src python scripts/epc90133_switching.py --study phase --jobs 2 --timeout 3600     --only G-m1-mid-Ls50-pin10 G-m1-mid-Ls50-pin10-ms50     --output results/gan/epc90133-switching-phase-2.json                     # substitute step check
PYTHONPATH=src python scripts/epc90133_phase_partial.py                       # event A from the timing runs
```

Raw PHASE-to-GND extremes on G + 50 pH package source (assumed), the test 7 case with the largest minimum:

| Case | event A (Q1 turn-off) min / max | event B (Q1 turn-on) min / max | source |
|---|---|---|---|
| unregularized, 100 ps | −28.3 / +47.7 V (0.33 ps wide) | −3.0 / +55.9 V | [run 1](../results/gan/epc90133-switching-phase.json) |
| unregularized, 50 ps | −28.3 / **+114.3 V** | −8.0 / +55.9 V | run 1 |
| 10 pF + clamps, 100 ps | −3.59 / +48.4 V (2.2 ns wide) | −2.25 / +56.2 V | run 1 and [step check](../results/gan/epc90133-switching-phase-2.json) |
| 10 pF + clamps, 50 ps | −3.59 / +48.0 V | **−7.46** / +56.2 V (one sample; −2.32 V without it) | step check |
| 100 pF + clamps (timing run, stopped) | −3.66 / +47.2 V (2.2 ns wide) | not reached | [partial](../results/gan/epc90133-test8-phase-partial.json) |
| G alone, 100 pF (timing run, stopped) | −3.42 / +47.4 V | not reached | partial |

What happened, against the declared criteria:

- **The three 100 pF cases timed out** at 3600 s in their timing runs (femtosecond steps from the first turn-on at
  20.7 ns). They are kept as failed runs. Their partial raw files reach event A in two cases; those values come
  from timing runs (same circuit, different edge timing) and are supplementary, outside the declared criteria.
- **The substitute step check** (10 pF at 50 ps, declared after run 1 and before its run) **fails formally at event
  B**: −7.46 V against −2.25 V. That minimum is one sample, taken where the step had collapsed to about 1e-19 s
  0.36 ns after the turn-on command; Q1's gate shows the same one-sample jump to −9 V, and the next lowest point is
  −2.32 V. Excluding it is a judgement made after the run, so the criterion stays failed in the record. Event A
  passes it (−3.594 V at both steps).
- **The 10 pF regularization changes no switching metric materially** (overshoot +2.8 %, damping ratio +2.4 %,
  the others under 0.2 %; all below the declared materiality threshold; Q2's die VGS peak 2.08 V, unchanged).
- **Step stability of G + 50 pH's switching metrics:** halving the step changes the five reported metrics by
  under 0.04 % (unregularized and 10 pF alike). This shows stability over these two steps, not general
  convergence, and says nothing about PHASE stability.

Reading, scoped to this unvalidated bench. Test 8 changed two things at once, pin capacitance and clamp paths,
with the clamps tied to ideal rails: assumed circuit changes, not a qualified model of the uP1966E output stage.
What it supports: **the PHASE extremes are sensitive to driver-model assumptions, and some of them are
numerically unstable.** Without regularization, the event A maximum (48 → 114 V) and the event B minimum
(−3.0 → −8.0 V) move with the step, while the event A minimum (−28.3 V) does not. With either assumed pin
capacitance, event A's undershoot is a 2 ns dip of about −3.6 V. Neither the assumed capacitances nor the
resulting 1.4 V distance from the −5 V rating establishes a hardware margin. The structured verdict is
[results/gan/epc90133-test8-assessment.json](../results/gan/epc90133-test8-assessment.json)
(`scripts/assess_epc90133_test8.py`, no simulation): declared test incomplete (C1 rating and C3 bracket lack the
100 pF cases, the declared step check never ran), substitute step check passes at event A and fails at event B,
**PHASE stress unresolved**. Switching-metric eligibility (the `usable` flag) is kept separate from it.

This simulation baseline is frozen here (external review, 1 October 2026): the original driver model and the
test 8 variants stay as separate, recorded cases, and no finer G mesh, broad sweep or tuning is justified by the
current decisions. The PHASE-to-GND undershoot near the driver is a measurement item and a stop criterion in the
hardware plan. Simulated sensitivity results, not a safe limit.

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

## FasterCap capacitance extraction: tool qualification (G3)

FasterCap 6.0.7 (FastFieldSolvers) is the candidate capacitance extractor, for the switch-node capacitance and the
other capacitive parasitics. It is licensed LGPL 2.1 or later, which allows use and redistribution; the source and
binary still stay in the git-ignored `.tools/`, like FastHenry.

- **Build** (Ubuntu 24.04 under WSL, gcc 13.3, cmake 3.28.3, wxWidgets 3.2.4 base). The README's headless route; the
  only change, made in a build copy, is the wxWidgets version that CMake asks for (3.0 → 3.2).

  ```sh
  cd .tools && git clone https://github.com/ediloren/FasterCap.git \
      && git clone https://github.com/ediloren/LinAlgebra.git && git clone https://github.com/ediloren/Geometry.git
  sudo apt-get install cmake libwxgtk3.2-dev
  bash scripts/build_fastercap.sh      # -> .tools/FasterCap-bin/FasterCap
  ```

  Commits are recorded in the script header and in the report. At run time wxWidgets prints harmless "Assert
  failure" lines (FasterCap README).
- **Qualification.** `python scripts/fastercap_known_answer.py` (Windows, calling FasterCap through `wsl`). Cases,
  references and tolerances are declared in its docstring before the recorded run. Each case runs at `-a0.005`
  and `-a0.001` (FasterCap's automatic refinement), and the two must agree within 0.5 %. Run 1 stopped at case D:
  in 2D, FasterCap takes the last conductor as the reference and prints an (N−1) × (N−1) matrix, which the
  evaluator first misread. The fix changed only the reading.

[Result, 30 September 2026](../results/gan/fastercap-known-answer.json):

| Case | FasterCap (-a0.001) | Reference | Error | Mesh change | Declared check |
|---|---|---|---|---|---|
| A: unit cube in air (3D) | 73.47 pF | 73.51 pF (Hwang and Mascagni) | −0.05 % | 0.88 % | **fail** (mesh) |
| B: sphere in air, 1 mm (3D) | 0.11094 pF | 0.11127 pF | −0.30 % | 0.01 % | pass (1 %) |
| C: sphere with a dielectric shell, εr 4.3 (3D) | 0.18058 pF | 0.18054 pF | +0.02 % | 3.3 % | **fail** (mesh) |
| D: coax in air (2D) | 80.27 pF/m | 80.26 pF/m | +0.01 % | 0.00 % | pass (0.5 %) |
| E: coax with a dielectric layer (2D) | did not finish in 1800 s | 145.6 pF/m | +2.1 % at -a0.005 | — | **fail** (time) |
| F: coplanar strips, zero thickness (2D) | 20.95 pF/m | 21.32 pF/m (conformal mapping) | −1.7 % | 0.10 % | **fail** (1 %) |
| G(i): microstrip w = 2h, t = h/100, air (2D) | 37.75 pF/m | 37.70 pF/m (Hammerstad–Jensen) | +0.13 % | 0.26 % | pass (2 %) |
| G(ii): the same on εr 4.3 (2D) | 123.05 pF/m | 123.04 pF/m | +0.004 % | 0.08 % | pass (2 %) |

What this shows:

- **`-a` is a stopping rule, not an error bound.** In A and C the finer setting lands within 0.05 % of the answer,
  but the `-a0.005` runs stop 0.9 % and 3.3 % away. A board extraction therefore needs its own refinement
  sequence with a declared convergence check, not one `-a` setting.
- **Finite-thickness conductors on a planar dielectric work** (G, the geometry closest to board copper over a
  prepreg), in 2D and at modest cost.
- **Dielectric interfaces are expensive.** C needed 480,000 panels and 24 minutes for one sphere; E, a 2D case with
  curved concentric interfaces, still changed by 0.3 % per refinement when it was stopped. The cause of E's slow
  convergence is not established. G shows it is not a general failure of planar 2D dielectrics.
- **Zero-thickness conductors are not qualified.** F's automatic refinement stopped at 54 panels. Under-resolved
  edge singularities are a plausible cause, but not isolated. Board copper will be modelled with its thickness.
- **Scope.** FasterCap is not qualified for board use. The four passes (B, D, G(i), G(ii)) support only those
  benchmark geometries: B a sphere in air in 3D, D a 2D coax, and G a finite-thickness microstrip in 2D against an
  approximate closed-form reference (Hammerstad–Jensen), which is a useful check but not qualification of a
  3D board. A's value is close to its reference, but A **failed** its declared mesh check and stays a failure;
  it is not evidence of qualification. Not covered: 3D board geometry with FR-4 and solder mask, holes and vias.
  Before board use: a board-like 3D check with a declared refinement sequence, a follow-up check declared for F
  (finite thickness or manual mesh) and a diagnosis of E, if a board model needs curved interfaces.
- **Runner fixes after an external audit (30 September 2026), no case or tolerance changed.** A timeout now stops
  only that run's FasterCap process (by its recorded PID, checked to still be FasterCap), not every process of that
  name on the shared host; an unknown or empty `--only` is rejected instead of reporting `all_pass` over no cases;
  the report is checkpointed after each case and records the requested cases and whether all of them ran. Checked
  by a forced 3 s timeout on case C (its process was stopped, the report shows `complete: true, all_pass: false`)
  and by rejected `--only nosuch` and empty `--only`. The recorded eight-case results are unaffected.
