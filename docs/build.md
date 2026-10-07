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

**Fourth mesh (1 October 2026, declared before its run as a separate revision;
[result](../results/gan/fasthenry-via-cavity-mesh4.json)).** The three-mesh result above stays recorded as failed.
Launch 1 reran only the old meshes (a default left at three) and wrote no evaluation; it is kept under runs/.
Launch 2 ran the (w/8, 9) mesh: 52.068 pH (1.5 mm) and 71.721 pH (3 mm, 336k filaments, about 5.5 h at 4.9 GB),
reusing the earlier meshes. Declared outcome: **pass**. From w/6 to w/8 the values change by 0.05 % and 0.03 % and
the E1 difference by 0.02 % (limit 1 %); E1 is +2.47 % (tolerance 3 %); both values lie inside the E2 bracket, at 34 %
and 25 % of its width. So this single-via benchmark now passes its declared inductance mesh criterion. The refinement
changed the plane-grid pitch, the plane thickness subdivision and the via subdivision together, so the location of
the earlier discretization error (via, pad, junction or planes) was not isolated. The criterion covers L and its
difference only: R still changes by 7.8 % and 4.9 % between the last two meshes, so R is not converged. The scope is unchanged: board via arrays, plane holes, Kelvin and multi-layer vias are
still not qualified, and the bracket width (23.5 and 33.7 pH here) remains the per-via representation uncertainty.

### Via-array, plane-hole and FasterCap qualification: plan review and first bounded step (2 October 2026)

A session drafted three qualification plans while hardware is blocked: via arrays in a closed cavity against an
independent 2D reference, plane holes and slots, and a FasterCap diagnosis. An external review accepted the topics and
asked for revised acceptance criteria before any expensive run. Disposition, after checking both against the code and the
stored logs:

- **Accepted from the review.** Benchmark errors are reported as discretization and representation errors of declared
  benchmark geometries, with a separate statement of their applicability to the board. They are not board error bars.
  The drafted V2 check is dropped, because nothing derives its premise (the same fractional position in the bracket for
  every arrangement). A via-array benchmark needs new cavity sizes (six vias at 0.6 mm span 3 mm between centres, wider
  than the existing 1.5 and 3 mm cavities), the board's via section (square, side 0.847 × drill, drill 0.198 mm) and a
  stated excitation (individual ports or a parallel array). It also needs a later case for the 35-via source cluster.
  "Exact square coax" is not available: the via script uses an equivalent-diameter approximation. The extractor checks copper only
  on each segment's centre line ([epc90133_extract.py](../scripts/epc90133_extract.py), `connect`). Vias whose nearest
  nodes coincide keep separate vertical segments. FasterCap's reference point sets each panel's side by the sign of
  (point − vertex)·normal (`Autorefine.cpp` around line 6142). Case H's point is the centre of a convex box, so every slab
  face was already oriented correctly. The drafted D3 (moving the point outside) is dropped for that reason. K1 needs
  side-edge fringing removed, not only end effects. Compute estimates are guesses until one case is profiled.
- **Added from the stored logs.** The air diagnostics took 11–25 minutes per refinement step at `-a0.01` and reached
  2–4 million panels, so "minutes each" was wrong. Case H's dielectric runs did not refine: iteration 0 (3,576 panels)
  and iteration 1 (4,132 panels) gave identical, unphysical matrices. The stopping rule therefore fired at once, with
  FasterCap's relative-refinement indicator at 14,299 (about 1.5 in air). In air the same geometry also started
  unphysical but refined to a physical matrix. The FasterCap evidence therefore points first at automatic refinement
  stopping on an unresolved starting mesh, ahead of the dielectric description. That is not yet tested. The drafted D1
  (slab at εr = 1) cannot test the interface: the earlier εr 1/1 run reports "0 dielectric" panels, so FasterCap drops
  an interface whose two permittivities are equal.
- **Order.** (1) The topology audit below, at no solver cost. (2) A FasterCap diagnosis with user-controlled meshes,
  declared separately. (3) A precise declaration of the via-array and slot benchmarks, using the audit's geometry.
  Profile one case before committing compute. Measurement readiness keeps priority when the equipment inventory arrives.

**Mesh topology audit** (`python scripts/audit_epc90133_mesh_topology.py`, declared in its docstring and committed at
89e5e32 before its run; [result](../results/gan/epc90133-mesh-topology-audit.json)). The audit parses the decks that
the unchanged production extractor builds (A, B at m1 and m2, G at m1, B with pad junctions, and B with the grid shifted
by half a pitch). It computes no inductance. Findings:

- **Slots.** On the ground return planes (mid-layers 1–4), each row of six switch-node or VIN vias under a transistor
  pin has antipads that merge into one slot, about 0.66 × 3.66 mm (six such slots, plus nine two-via slots, about
  0.69 × 1.37 mm, under the capacitors). Every hole of at least half a pitch is crossed by a grid line, so no hole is
  invisible to the mesh (F1 = 0 in every deck).
- **Width overreach (T1).** Segment widths extend into those holes. On mid-layer 1, 27 % of the hole area is covered at
  m1 with the production grid. The grid's x-lines are aligned to the pin rows, so they run down the slot centres, and
  segments 0.425 mm wide either side reach about 0.12 mm into each slot. With the grid shifted by s/2 in x the cover is
  9–11 %; at m2 it is 8–9 % at every offset tested. 3–12 segments per m1 deck, and 0–23 per m2 or shifted deck, have more
  than half their width off their own copper. The electrical effect of this cover is not known; the slot benchmark is
  where it gets measured.
- **Via attachments (T4).** No grid node is shared by two vias in any deck, offsets included (F4 = 0), so the merge
  risk raised for 0.6 mm via rows does not occur on these grids. One via end (group SW-03, top layer, m1) attaches
  0.59 mm from its centre (F3); at m2 the largest distance is 0.13 mm.
- **Mesh splitting (T3).** On the top layer a 15-node (m1) or 72-node (m2) fragment of one island is joined to the rest
  only through vias.

Consequences for the benchmarks: the slot benchmark uses the measured slot (0.66 × 3.66 mm, six 0.198 mm drills at
0.6 mm) at m1 and m2, with the production alignment (slot-centred) and a shifted grid. The via-array benchmark does not
need a merged-attachment case for these grids.

**Benchmark designs (draft for review; no script, criterion or run yet).** Each becomes a script whose docstring
declares the criteria, committed before its first run, after one profiled case.

- *Via arrays.* Closed plane-pair cavities at the top-layer/mid-layer-1 stack, as in the single-via check. The wall
  clearance from the array's bounding box is declared, and two clearances are used so that differences can be formed.
  Board via section (square, side 0.847 × 0.198 mm), arrangements: one via, a row of six at 0.6 mm, a row of six at
  1.2 mm, 3 × 3 at 0.6 mm, and later the 35-via source cluster from the board's drill coordinates. Each via is its own
  port, so FastHenry returns the full N × N matrix; the parallel-array inductance is derived from it, not measured
  separately. Two representations: the production rule (via end tied to the nearest plate node, plates at the board's
  m1/m2 pitches, production alignment and a shifted grid) and a resolved one (fine plates, ideal pads).
  Reference: between perfectly conducting plates the field is two-dimensional, so L = μ0 ε0 (h + δ) C2D⁻¹. Here C2D is
  the 2D capacitance matrix of the via cross-sections inside the wall, with the wall as reference and every conductor
  equipotential (the perfect-conductor limit). FasterCap 2D gives C2D: it passed its 2D coax known answer to 0.01 %
  and is independent of FastHenry. A small Python solver could cross-check it, but is not needed for this step. The
  2D reference cannot fix the via's length inside the copper (the E2 bracket), so it is compared through quantities in
  which that cancels: ratios of mutual inductances (Mij/M12; the factor h + δ cancels), and cavity-size differences of
  self, mutual and parallel-array values (the E1 construction). Absolute values are reported against the E2 bracket
  only. Tolerances: reference accuracy plus the 2D mesh change, declared with the script.
- *Plane holes and slots.* P1, holes through both plates: for hole sizes much larger than the plate gap, current in the
  plane pair is a 2D sheet current with an inductance per square of μ0 (h + δ), and the hole is an insulating
  boundary. The reference is therefore a 2D sheet-current (Laplace, Neumann at the hole edge) count of squares. A
  Python finite-difference solver gives it for any hole shape, including the measured slot, and is itself checked
  against exact strip results (L/W squares without a hole) and the small-circular-hole limit. The sheet picture
  has an O(h/size) error at hole edges, so its applicability is stated as a ratio and tested with two plate gaps.
  The strip is long enough that the terminals sit several widths from the hole. P2, a slot in the return plate only
  (the board case): no reference exists. Checks are mesh stability of the added inductance (with an absolute floor, so
  a near-zero addition does not make the relative change unstable), the trend as the slot shrinks, and agreement
  between the production-rule mesh at m1/m2 (slot-centred and shifted) and a resolved mesh. That last comparison is
  the number the audit's 27 % cover calls for.
- *Applicability.* Each result is reported as the error of the benchmark geometry, with a separate statement of which
  board features it resembles and how. Turning it into board uncertainty needs a transfer argument or a
  representative board-subgeometry check, declared separately.

**FasterCap with user-controlled meshes** (`python scripts/fastercap_manual_mesh_check.py`, declared at 4cf9434,
revision 2 at de2aebf; criteria in the docstring). The script writes its own graded panel meshes for case H's geometry
(three meshes), switches FasterCap's refinement off, and adds a partly filled plate capacitor (K1). K1 runs only if the
case-H part passes.

- *Run 1 failed and was stopped, kept* ([report](../results/gan/fastercap-manual-mesh-check-run1-failed.json)). With
  `-m1e9` alone every 4 mm matrix was unphysical, air included, and the 2 mm values did not converge. FasterCap sets the
  threshold that decides at which hierarchy level two panels interact to `-d` × `-m` (`SolveCapacitance.cpp`;
  `Autorefine.cpp`, `RefineCriteria`). `-m1e9` therefore made panels interact through coarse super-panels. The same
  coupling makes every automatic iteration 0 (`-m` 1e32) unphysical, which is what case H and the air diagnostics show.
  On a 1 m probe cube the threshold moves the result from 69.0 pF (1e9) to 72.66 pF (0.01) and 72.67 pF (all links).
- *Revision 2* uses threshold 0.01 (`-d1e-11`) and adds D5, a rerun of M2 at threshold 0.001.
  - Air form: complete and passing. C′ = 37.53, 37.52 and 37.50 pF/m on M1–M3: a 0.05 % change from M2 to M3 (D2,
    limit 1 %) and −0.53 % against Hammerstad–Jensen (D3, limit 1 %). Every matrix is physical and no run refined (D0).
    So FasterCap's 3D solver gives a physical, mesh-stable, accurate result for this thin strip when the mesh is
    resolved and the interaction threshold is tight.
  - Dielectric form: see the run state below.
- *Reading so far.* Case H's unphysical matrices are explained, at least in part, by settings rather than by the
  dielectric input: the automatic mode never left a coarse interaction threshold. Whether the dielectric description is
  also sound is what the dielectric form of revision 2 decides.
- *An independent 2D reference for D4* ([script](../scripts/microstrip_bem_reference.py),
  [result](../results/gan/microstrip-bem-reference.json); declared before run 4 produced any finer dielectric value).
  D4 compares with FasterCap's own 2D value, and FasterCap's automatic 2D refinement is now known to stall. The new
  boundary-element solver ([circuit_tools/bem2d.py](../src/circuit_tools/bem2d.py)) gained dielectric interfaces: bound
  charge with normal-field continuity, exact coated coax reproduced to 0.005 % after extrapolation. For case H's cross-section it gives
  **123.10 pF/m**: B1, the wide-slab version, lies within 0.06 % of Hammerstad–Jensen, and B2, panel convergence, is
  0.009 %. FasterCap's case H value at `-a0.001` (123.23) agrees within 0.11 %, so D4's reference stands. Its `-a0.005`
  value was 15.7 % low, another automatic stall.

- *Run state, 2 October 2026.* Revision 2 was stopped at the end of the working day during the dielectric M2 call ([report](../results/gan/fastercap-manual-mesh-check-run2-incomplete.json), outcome 'incomplete, stopped'; no check evaluated). Completed: air M1–M3 and dielectric M1. Dielectric M1 took 10 and 27 minutes for its two lengths and gave physical matrices, unlike case H, with C′ = 116.8 pF/m, 5.2 % below the 2D reference (123.2 pF/m). The air form was within 0.5 % on the same mesh, so the dielectric value is either not converged at M1 or still carries an error; the finer meshes decide. Not run: dielectric M2/M3, D5, the automatic run from M1, and K1. The rerun takes an estimated 3–5 hours and should be launched detached, so it is not a child of a session shell.
- *Run 3, 2–3 October 2026, failed, kept* ([report](../results/gan/fastercap-manual-mesh-check-run3-failed.json)). It was
  launched detached at 23:33 but shared the host with the two FastHenry benchmarks below and the via-array references.
- *Run 4, 3 October 2026, failed, kept* ([report](../results/gan/fastercap-manual-mesh-check-run4-failed.json)). It ran
  mostly alone. It reproduced air M1–M3 and dielectric M1 exactly and gave dielectric M2 C′ = 118.3 pF/m (−3.9 % against
  the 2D reference). Dielectric M3 at 2 mm exceeded its 1 h limit, so D2 and D4 cannot pass and K1 was not run. It was
  stopped during M3 at 4 mm.
- *Diagnosis: discretisation at the strip edges, not the dielectric description.* A 2D boundary-element emulation with
  the same panel layout as each 3D mesh (`emulate_2d` in
  [fastercap_edge_mesh_check.py](../scripts/fastercap_edge_mesh_check.py)) gives air −0.48 % and dielectric −5.5 % and
  −4.0 % on M1 and M2. FasterCap's 3D values are −0.46 %, −5.1 % and −3.9 %. So FasterCap's 3D dielectric solution is
  what these meshes should give, and the shortfall comes from panels too coarse where strip and dielectric meet; at M3
  it would still be −2.8 %. In 2D, refining only the panels at the strip's side edges removes it: 1.25 µm gives −0.76 %,
  0.6 µm gives −0.13 %. The diagnosis is therefore substantially resolved, and the 3D qualification unfinished. Case H's
  unphysical matrices came from the automatic settings (a coarse interaction threshold that the automatic mode never
  tightened). With a tight threshold and the declared meshes, FasterCap's 3D dielectric values match an independent 2D
  emulation of the same panels. No edge-refined 3D value exists yet (see the next item), so FasterCap's 3D dielectric
  accuracy has not been shown directly.
- *Edge-refined 3D confirmation, run 1 failed and stopped* (`python scripts/fastercap_edge_mesh_check.py`, declared at
  bcd1c3e; [report](../results/gan/fastercap-edge-mesh-check-run1-failed.json)). Mesh E1 has 1.25 µm panels at the strip
  edges, with a predicted error of −0.76 %. The 2 mm case took 2.6 h and gave a physical matrix. The 4 mm case was
  stopped at the owner's decision after about 2 h 10 min, so no C′ and no D4 or D6 verdict exists. Its 3 h limit had
  been set without profiling and would very likely have been exceeded. In future, time limits come from a profiled or
  scaled estimate with margin. The diagnosis above does not depend on this run. FasterCap stays unqualified for board
  geometry, and K1 (partly filled plates) has not been run.
  Dielectric M1 at 4 mm exceeded its 1 h limit (27 minutes in run 2), so D2 could not pass. It was stopped during
  dielectric M2. The air results reproduce run 2 exactly. Run 4 is queued to start alone after the FastHenry jobs.

**FasterCap runner: a false-success path closed (3 October 2026).** With three jobs running, WSL's *free* memory fell to
tens of MB, while most of the 8 GB sat in page cache. FasterCap sizes its out-of-core storage from free memory, and in some
via-array reference runs it printed "Cannot go out-of-core, terminating process" during an automatic iteration and still
exited 0. The shared runner then read the last matrix printed, from an earlier, unconverged iteration, as the result.
`run_problem` in [fastercap_known_answer.py](../scripts/fastercap_known_answer.py) now rejects a log that reports that
termination, or that ends an automatic run with its last change above the requested `-a` value. It is unit-tested on
synthetic logs (tests/test_fastercap_run_problem.py). Every earlier FasterCap result log passes the gate except
known-answer case E at `-a0.001`, which was already recorded as failed (time). No earlier result was a hidden false
success. The case H assessment was regenerated to bind the changed helper's hash; only the hash changed.

**Plane-pair slot benchmark** (`python scripts/plane_hole_benchmark.py`, declared at b5c1775;
[report](../results/gan/plane-hole-benchmark.json)). A plane-pair strip (6.8 × 5.1 mm, board stack) with a slot of
the measured size (0.65 × 3.65 mm) across or along the current, or a smaller one. The slot is cut through both plates
(P1) or only through the return plate (P2), as on the board. Meshes use the production rule at the board pitches m1 and
m2 (grid aligned to the slot centre, as the production grid is to the pin rows, and shifted by half a pitch) and at
finer pitches. The P1 reference is a new 2D sheet-current solver ([circuit_tools/sheet.py](../src/circuit_tools/sheet.py);
exact for a plain strip, and within about 1 % of the dilute-hole formula after extrapolation). It gives dL = μ0 (h + δ) dN
for the slot's added squares dN, with slot edges on cell faces so that no staircase error enters.

- *Reference (R1 converged: 0.06 % and 0.04 % between the two finest cells; a 2D sheet picture with the slot through
  both plates).* A slot across the current adds 0.89 squares, 150 pH in this plane pair. The same slot along the current adds 0.12 squares, 21 pH, seven times less. On the
  board the slots run along y, as does most of the return current under the transistors (a geometric reading, not an
  extracted current), which resembles the cheaper orientation.
- *Board pitches.* FastHenry's slot inductance there is well below the reference, and it depends on grid alignment:

  | Slot (P1) | m1 aligned | m1 shifted | m2 aligned | m2 shifted | 2D reference |
  |---|---|---|---|---|---|
  | across, 0.65 × 3.65 | 97.6 pH | 90.1 | 94.2 | 123.0 | 149.7 |
  | along, 3.65 × 0.65 | 7.4 | 17.7 | 12.1 | 19.3 | 20.7 |
  | small, across | 26.9 | – | 17.0 | – | 27.4 |

  The slot in the return plate only (P2, the board's case) behaves similarly: 83/77 pH (m1) and 79/103 pH (m2) across the
  current, 6/14 and 9/15 pH along it. The unslotted strip comes out at 204–205 pH against 224 pH from L/W. That matches
  every copper edge being widened by half a pitch (L/(W + s) gives 207 pH at m1), the same width overreach the topology
  audit measured on the board.
- *Network diagnostic, not supported* ([assessment](../results/gan/plane-hole-network-assessment.json),
  [script](../scripts/assess_plane_hole_network.py), declared before it was run). In the plane-pair limit, the production
  mesh should act as a resistor network of its kept segments. That network reproduces the unslotted strip (FastHenry
  within 1–5 %) and the direction of every alignment effect, but FastHenry's slot inductance is only 0.62–0.77 of the
  network's. So mesh topology alone does not explain the board-pitch values, and a slot-specific factor remains. One
  candidate is 3D field fringing at the slot edges, which both the network and the sheet reference omit. The fine meshes
  and the half-gap case (check P1c) test it.
- *Run 1 complete; declared outcome: fail* ([report](../results/gan/plane-hole-benchmark.json)). The f4 profile (the
  unslotted strip) exceeded both the 75-minute rule and its 3 h limit, so as declared every f4 run was dropped. The checks
  then use f3 as the finest mesh with m2 for comparison. Each f3 run took 22–89 minutes on the shared host.
  - R1 passes (reference converged to 0.1 % or better).
  - **P1a fails:** across-slot dL changes 14.7 % from m2 to f3. **P2a fails:** 13.6 % (10.7 pH).
  - **P1b fails:** at f3 FastHenry's across-slot dL through both plates is 108.0 pH against the sheet reference's 149.7 pH
    (−27.9 %). The along-slot and small slots show similar ratios (0.73 and 0.58).
  - **P1c passes:** with the gap halved the shortfall falls to −16.0 %. An error that scales roughly with h is what
    field fringing over a distance of order h at the slot edges would give. A straight-line extrapolation to zero gap
    leaves about −4 %, comparable to the unconverged f3 mesh error. So the sheet picture is not an accurate known
    answer at the board's ratio of gap to slot size; it overestimates the slot's effect. The extrapolation is a
    reading, not a declared check, and f3 is not converged.
  - *Production-mesh differences from f3* (reported; f3 is itself not converged, so these are differences, not
    established accuracy errors): across-slot cases −17 % to +15 %. The
    along-current slot in the return plate only, the board-like case, gives 5.6–15.3 pH against 11.6 pH (−52 % to
    +32 %). The production alignment (grid lines through the slot centre) gives the low end: −52 % at m1 and −21 % at m2.
    The small slot at m1 is +68 %. Grid alignment alone moves these values by factors of up to 2.4.
  - *What this might mean for the board extraction (a hypothesis).* The board's pin-row slots lie along the return
    current. For that case, slot in the return plate only, the finest mesh gives 11.6 pH in this benchmark strip
    (unconverged), and the production m1 grid about half of it. Against a loop inductance of 260–280 pH in variants B
    and G, that would make slot representation a percent-level effect rather than a dominant one. The hypothesis needs
    a transfer argument or a board-subgeometry check: the board's current paths, layer stack and slot count are not
    reproduced here. The 150 and 21 pH figures above belong to the 2D reference with both plates slotted, not to the
    board-like case.

**Via-array benchmark** (`python scripts/via_array_benchmark.py`, declared at d220f0e; revision 5 at the commit before
567de11; [report](../results/gan/via-array-benchmark.json)). Closed plane-pair cavities at the board stack hold one via,
a row of six at 0.6 mm (as under each pin), a row of six at 1.2 mm, or a 3 × 3 grid at 0.6 mm. Each cavity is used at two
wall clearances, with the board's via section. Each via is its own FastHenry port, so the full inductance matrix comes
out. Representations: the production rule at the board pitches m1 and m2 (nearest-node attachment, grid through the
via rows), and a resolved single mesh (pitch about w/2, ideal pads). The reference is the 2D field between perfectly
conducting plates, L = μ0 ε0 (h + δ) C2D⁻¹. It is compared through quantities in which the via's length inside the
copper cancels: mutual-inductance ratios, and cavity-size differences.

- *Runs 1–4, kept as failed.* Run 1 solved every case but could not read FastHenry's full impedance matrix. Runs 2 and 3
  took some references from memory-terminated FasterCap runs (the runner gap above). Run 4 completed and failed V0:
  FasterCap's automatic 2D refinement sometimes stalls. Some single-via references sat 1.3–2.1 % above the closed form
  at one or both `-a` settings, while converged ones agreed with it to 0.02 %. Two `-a` settings therefore cannot
  certify a reference.
- *Revision 5: a new reference solver,* [circuit_tools/bem2d.py](../src/circuit_tools/bem2d.py). It is a 2D
  boundary-element solver with explicit corner-graded panels: exact coax to 4 × 10⁻⁷, square via to 0.004 % of the closed
  form (tests/test_bem2d.py). **V0 passes:** every reference changes by ≤ 0.05 % between 16 and 32 panels per via side,
  and every single-via reference is within 0.004 % of the closed form. In three of 23 cavities FasterCap's run-4
  reference differed from it by 1.3–2.1 %.
- *Resolved FastHenry mesh (single mesh, as declared).* Mutual-inductance ratios agree within 2.9 %, except the farthest
  pair in the smaller cavity, 7.2 % (**V1 fails**). Cavity differences agree within 1.3 % for the six-via row, but the
  single via is 4.5 % off (**V2 fails**). The parallel-array inductance lies inside the physical bracket (**V3 passes**).
  For comparison, the single-via cavity check at this pitch was also several percent off before refinement, so these
  failures may be mesh error. That is not established: no second resolved mesh was run (the six-via row took 2.9 h at
  this pitch).
- *Board pitches (reported, not judged).* Individual mutual ratios are off by up to 12 % at m2 and 19 % at m1, and the
  six-via row's cavity difference of via 1's self inductance is off by 22 % at m1. The parallel-array inductance lands
  anywhere between 0.19 and 1.06 of the physical bracket; the 3 × 3 grid at m1 lies above it. For arrays it sits nearer
  the gap-only end (0.19–0.44) than for a single via (0.45–0.82), so one bracket position cannot be carried from a single
  via to an array.
- *Dividing by the via count is wrong by a factor 1.6–2.6.* In the same cavity, six vias at 0.6 mm have 2.05 times the
  inductance of one via divided by six, six at 1.2 mm 1.56 times, and nine at 0.6 mm 2.62 times (reference values).
- *Applicability.* These are errors of closed cavities with these arrangements at 100 MHz. On the board, vias pass
  through slotted planes and meet several layers. The numbers show the size of representation effects at the board
  pitches; they are not error bars for the extracted board network.

**Audit at 9ca735d (3 October 2026), applied without reruns.**
- The user-mesh FasterCap runner (also used by the edge-mesh check) now applies the same `run_problem` gate as the
  shared runner. None of the 37 stored user-mesh and edge-mesh logs reports a memory termination.
- Both FastHenry benchmarks now run through [circuit_tools/wslrun.py](../src/circuit_tools/wslrun.py), which records
  the Linux solver's PID and on timeout stops that process after checking its name (tests/test_wslrun.py). Before,
  only wsl.exe was stopped, so a timed-out case could keep running beside the next one, and the via script did not
  catch a timeout at all.
- The via benchmark binds `bem2d.py` and `wslrun.py` in its manifest. On `--resume`, both benchmarks refuse a report whose
  dependencies changed.
- V1 now fails if any expected ratio is missing (tests/test_via_array_checks.py). The stored V1 used complete ratio
  sets, so its failure stands.
- The stored reports predate these changes, and their verdicts are unchanged.
- Wording narrowed: slot figures are differences from an unconverged mesh, via figures are mutual-inductance ratios,
  and the FasterCap diagnosis is substantially resolved with its 3D qualification unfinished.

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
  *Corrected by test 9 (below):* these are the vendor model's terminal voltages, not its channel-control
  voltage behind the internal 0.5 Ω rg, and the 1.07 V figure is Q2's own turn-off tail at the start of the
  diagnostics window, not the rise. During the rise, Q2's internal VGS stays below about 1 V and its channel
  shows no appreciable positive current in any completed case, so comparing the 2.0 V terminal peak with DC
  conduction overstated the evidence for false turn-on within the model.
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

### EPC90133 switching test 9: full extracted resistance and vendor-model internal nodes

After an external method audit (1 October 2026, [audit](epc90133-simulation-method-audit-2026-10-01.md)):
the bench's branch network kept the full inductance and coupling matrices but only the diagonal resistance.
`scripts/audit_epc90133_network_transfer.py` (the auditor's) shows the diagnostic loop resistance at 100 MHz
falls from 2.03 to 1.12 mΩ (B) and 1.03 mΩ (G). Network revision `full_r` (opt-in; the baseline stays as it
was) keeps each branch's resistor and adds the off-diagonal terms as a behavioural source.
`scripts/qualify_epc90133_network_transfer.py` checks it in LTspice AC at 100 MHz
([result](../results/gan/epc90133-network-transfer-qualification.json)): a synthetic known-answer network
(error 3e-7), the diagnostic loading of B and G against the auditor's independent solve, and the complete
35-port (B) and 47-port (G) open-circuit impedance matrices against R + jωL (about 1e-6), for both
representations. Run 1 stopped because a behavioural source carrying the whole row formed source/inductor
loops that LTspice rejects; the split form fixed it. This qualifies the representation at 100 MHz, not the
extraction's accuracy or any transient's numerical convergence.

Test 9 (`--study fullr`, declared before its runs) also saves the vendor model's internal nodes
(`V(x*:gate)`, `V(x*:source)`, `I(x*:bswitch)`) without changing the model.
[Report](../results/gan/epc90133-switching-fullr.json);
[assessment](../results/gan/epc90133-test9-assessment.json) (`scripts/assess_epc90133_test9.py`).

- **Reproduction:** the baseline reruns (B, G, G + 50 pH) match test 7 exactly on every switching metric.
- **Full R on B changes nothing material:** overshoot 35.65 → 35.56 V, frequency +0.01 %, damping ratio
  0.0104 → 0.0112 (+8 %, below the materiality threshold).
- **The three full-R G cases timed out** at 3600 s (the dense behavioural coupling of 47 branches makes each
  step slow). They are kept as failed runs; the G step check was not evaluated. Test 10's small-signal analysis
  gives the full-R effect on G's ring without a transient.
- **No appreciable positive Q2 channel current in the sampled rise windows of these three cases.** This is not
  a statement that false turn-on is absent under other conditions.
  During the rise (from 1 ns before the switch node passes 10 % to +60 ns), Q2's internal VGS peaks at 0.56 V
  (B), 0.87 V (G) and 1.01 V (G + 50 pH), against terminal peaks of 0.26, 2.00 and 1.93 V. Its channel current
  reaches at most 0 to 70 µA positive (the traces are stored to 10 µA), and −2.3 to −3.1 A negative at the
  start of the window, where Q2 is still in reverse conduction from the dead time. That is not "no conduction".
  (Wording corrected after an external audit, 2 October 2026.) The terminal
  spike on G is a fast voltage between the extracted gate path and the model's internal rg that does not reach
  the channel-control node. The report's own diagnostics window (from −5 ns) starts in Q2's turn-off tail,
  which is where its 2.4–2.7 V internal maxima and test 7's 1.07 V "without the low-side path" come from; the
  assessment uses the rise window instead. These are model diagnostics: the physical device's internal gate
  network is not characterized, so the Q2 gate measurement in the hardware plan stays.

### EPC90133 test 10: local small-signal ring check (ring dynamics, separated from excitation)

Following the first-principles review ([review](epc90133-first-principles-review-2026-10-01.md)): separate how
strongly the edge excites the ring, what sets its frequency and decay, and what the probe records. Test 10
(`scripts/epc90133_ringdown.py`, declared before its runs) addresses the second question only, and only locally.
The bench is frozen 60 ns after Q1's turn-on command (Q1 on, Q2 off, 48 V, the 11.06 A load as a DC current
source, so the load branch is open in AC). LTspice linearizes it there, without changing the vendor model, and
the driving-point impedance at Q2's drain-source port gives the local ring mode (one-pole-pair fit; residuals
2e-4 to 0.025). There are two forms: the active driver at rest, and a control with ideal clamps on both FETs'
model-terminal VGS. [Report](../results/gan/epc90133-ringdown.json).

Finding the operating state: LTspice reaches it only through fallbacks (Gmin or source stepping, pseudo-
transient). Run 1 was stopped (state search too slow). In run 2, each network's baseline active state seeds its
other forms. Revision 3, an evaluation rule declared before it was applied, accepts a form whose only failure
reasons are operating-point fallbacks, if its own operating point passes the state checks (switch node ≥ 47 V,
Q1 internal VGS 5 ± 0.1 V, Q2 internal VGS 0 ± 0.1 V) and its sweep is complete. Six forms are accepted that
way and flagged; every state check passed (switch node 47.64–47.67 V).

| Network | local ζ, active (f) | local ζ, clamped | transient ζ (f), same case | consistent (f ±3 %, ζ ±25 %) |
|---|---|---|---|---|
| B | 0.0035 (290 MHz) | 0.0035 | 0.0104 (283 MHz) | no (ζ ×0.33) |
| B, full R | 0.0043 | 0.0043 | 0.0112 | no |
| G | 0.0066 (303 MHz) | 0.0054 | 0.0138 (299 MHz) | no (ζ ×0.48) |
| G, full R | 0.0076 | 0.0064 | timed out (test 9) | — |
| G + 50 pH (assumed) | 0.0220 (262 MHz) | 0.0175 | 0.0264 (261 MHz) | yes (ζ −17 %) |
| G + 50 pH, full R | 0.0228 | 0.0184 | timed out | — |

What this shows, within this model (narrowed after an external audit, 2 October 2026):

- **On B and G, this single local linearization does not account for the transient's decay**: the transient's
  ζ is two to three times the local mode's, with the frequency within 1–3 %. The linearization is about a DC
  equilibrium with the load as a current source, not the transient's actual state at 60 ns, so the difference
  can involve a changing bias point, several modes or the transient decay estimator, as well as amplitude
  dependence. Q2's voltage-dependent capacitance over the large swing (25–36 V on a 48 V bus) remains a
  candidate; none of these is isolated.
- **On G + 50 pH (assumed package source inductance) the local mode and the transient agree** (frequency within
  0.5 %, ζ within 17 %).
- **Substantial damping remains in the clamped circuit** (ζ 0.0175 against 0.0220 active on G + 50 pH). This
  does not say where it comes from: clamping changes the circuit and its mode, the internal gate resistance
  remains, and active minus clamped is not an additive gate-loop contribution. Attribution, including to the
  package inductors' numerical damping resistors (10 GHz corner, test 5), needs the energy accounting or a
  targeted control.
- **Full extracted resistance adds about 0.001 to the local ζ** (+23 % on B, +15 % on G, +4 % on G + 50 pH),
  small against the measured 0.072–0.077, as the review's scale estimate predicted.
- **Q2's internal gate voltage participates more in the G + 50 pH mode** (0.041 V per volt at the switch node,
  against 0.002–0.016 in the other active cases).

Revision 4 (evaluation only) checks every form's own solved operating point, kept separately from its starting
guess: all twelve pass (switch node 47.63–47.67 V, Q1 internal VGS 4.98–5.00 V, Q2 about 0 V).

These are statements about the linearized model at one state, not about the board. The half-power cross-check
is resolved only for the G + 50 pH cases (B and G bands are under 10 frequency steps wide).

### EPC90133 ring decay, cycle by cycle (existing traces)

After an external audit (2 October 2026): before calling the B/G mismatch amplitude-dependent, read the saved
transient traces cycle by cycle. `scripts/epc90133_ring_decay.py` (method declared before its first run, no
simulation; [result](../results/gan/epc90133-ring-decay.json)) finds alternating extrema of the turn-on
switch-node trace, measures each extremum against the mean of its neighbours (a moving baseline; about
peak-to-peak, a description corrected after run 1 with no number changed), and forms per-cycle frequency and ζ.

| Case | first cycle: p-p, ζ, f | last three cycles: p-p, ζ, f | test 10 local mode ζ, f | late cycles approach local mode |
|---|---|---|---|---|
| B | 65 V, 0.0086, 282 MHz | 34–35 V, 0.0072, 289 MHz | 0.0035, 290 MHz | no |
| G | 47 V, 0.0119, 299 MHz | 17–18 V, 0.0107, 303 MHz | 0.0066, 303 MHz | no |
| G + 50 pH | 21 V, 0.0255, 261 MHz | 3.4–4.0 V, 0.0327, 219 MHz | 0.0220, 262 MHz | no |

- **On B and G, the per-cycle ζ hardly changes over the observed range** (rank correlation with amplitude −0.08
  and −0.29) and stays about twice the local mode's. Over that range this does not look like amplitude
  dependence; under the declared reading it points to a different mode or state than the one linearized. The
  70 ns trace ends while the ring is still large (B: 34 V p-p), so the small-amplitude limit is not observed.
- **The estimator matters:** B's per-cycle ζ (0.0072–0.0086) is below the 0.0104 that the switching bench's
  estimator (first-to-third extreme about the level of the last 20 ns) reports; part of the earlier factor of
  three is the estimator, not the circuit.
- **On G + 50 pH the late cycles move away from the local mode** (ζ up to 0.033, frequency down to 219 MHz at
  a few volts), which suggests a second mode or a baseline effect at small amplitude; not examined further.

Envelope decay is not energy loss; that is the energy budget's question.

### EPC90133 switching test 11: driver output-stage representation (excitation)

The uP1966E datasheet constrains its output stage in two separate ways: output resistance at 500 mA (0.7/1.4 Ω
typical/maximum sourcing, 0.4/0.8 Ω sinking) and edge times into 3000 pF (8 ns rise, 4 ns fall typical). The
bench's driver (ramp) meets both with the typical resistances behind a source ramp calibrated to the edge
times. A near-step source behind larger resistances meets them too: calibrated on the same 3000 pF bench to
8.0/4.0 ns, it needs 1.213/0.606 Ω, inside the maxima (declared check D1 passes). Test 11 (`--study driver`,
declared before its runs; [report](../results/gan/epc90133-switching-driver.json)) runs both on B, G and
G + 50 pH (assumed package source inductance). All cases are usable, the ramp cases reproduce tests 7/9 exactly,
and the step check (G + 50 pH, step, 50 ps) changes no metric by more than 0.1 %.

| Network | overshoot, ramp → step | rise time | frequency, ζ | materiality |
|---|---|---|---|---|
| B | 35.7 → 25.8 V (−28 %) | 0.83 → 0.95 ns (+15 %) | +1.3 %, +3 % | overshoot and rise material |
| G | 25.2 → 16.8 V (−34 %) | 0.88 → 1.04 ns (+18 %) | +0.6 %, +2 % | overshoot and rise material |
| G + 50 pH | 11.1 → 10.8 V (−3 %) | 1.66 → 1.78 ns (+7 %) | −0.2 %, −2 % | none |

What this shows, within this model:

- **Two drivers that both meet the selected datasheet constraints (output resistance at 500 mA, edge times
  into 3000 pF) excite the turn-on ring very differently** on B and G (a third
  less overshoot with the step form), while the ring's frequency and damping barely change. The driver form
  acts on excitation, not on the ring dynamics, as the first-principles review's separation expects.
- **With the assumed 50 pH package source inductance the driver form hardly matters.** A plausible reading is
  that the source inductance's feedback on the gate then sets the turn-on, but this test does not isolate that.
  Whether the board is in the sensitive or the insensitive regime therefore depends on the package
  inductance, which is itself assumed.
- **Consequence for the measurement plan:** the driver's actual output behaviour into a gate load is a model
  input, not only a check. Its edge times into 3000 pF do not fix it; the gate-current waveform (or the gate
  voltage into a known load with the power stage unpowered, hardware plan E1) is what separates these forms.
- Neither form is identified as the real driver; both meet the typical edge times and stay inside the maximum
  resistances. That is not a check against every datasheet limit (propagation delays, supply and bootstrap
  behaviour were not compared). The step case on G (16.8 V, 1.04 ns) is still far from Fig. 9 (5.7 V, 1.67 ns).

### EPC90133 test 12: energy budget of the turn-on ring

`scripts/epc90133_energy_budget.py` (declared before its first run; [result](../results/gan/epc90133-energy-budget.json))
saves every node voltage and element current, inside the vendor model too, from 10 ns before Q1's turn-on, and
forms each element's absorbed power. The ring's losses are the deviations of voltage and current from their
one-period moving averages, multiplied and integrated from the first switch-node peak to 60 ns after the command,
so that the 11 A conduction loss and the bus charging L1 are excluded. Element groups are assigned by name. The
vendor model's charge elements each depend only on their own voltage (the one cross term has a zero coefficient),
so its storage is lossless and its losses sit in rg, rd, rs, the channel, the gate diodes and leakage resistors.
LTspice reports switch currents with the opposite sign to other elements (checked on a small circuit).

Run 1 stopped in post-processing (a raw file saved from a start time has its time axis starting at 0; fixed). The
checks: E1, the whole-window Tellegen sum, **fails** in every case (1.7–3.0 % of the largest element power). The
residual sits at the switching edge: 1.6 % of samples exceed the tolerance, all within about 2 ns of the edge, and
after command + 5 ns it is at most 1.2e-3. E2, the same balance for the ring's deviations, passes (2.5e-9 to
6.2e-8), and E3, the ring-loss shares at a halved step on G + 50 pH, passes (largest change 0.2 points). So the ring
accounting is internally consistent; the edge itself is not resolved by this bookkeeping.

Shares of the declared ring-deviation metric (the integral of v~ i~, defined above), not an independently
established partition of physical excess heat:

| Share of the ring-deviation loss metric | B | G | G + 50 pH (assumed) |
|---|---|---|---|
| Q1 channel | 64 % | 63 % | 59 % |
| gate loops (Q1/Q2 rg, driver outputs, R80–R83) | 0 % | 19 % | 29 % |
| network copper (diagonal R) | 13 % | 6 % | 2 % |
| capacitor ESR | 8 % | 4 % | 1 % |
| Q1 + Q2 rd and rs | 15 % | 8 % | 2 % |
| package inductors' numerical damping resistors | — | — | 6.5 % |
| total ring-deviation loss | 457 nJ | 388 nJ | 151 nJ |

What this shows, within this model:

- **This decomposition cannot show whether energy returns to the ideal sources.** Writing v = v̄ + v~ and
  i = ī + i~, the element power vi has four terms and the metric keeps only v~ i~. An ideal constant-voltage
  source has v~ = 0 away from the filter's ends whatever its current, so its small share (under 0.1 nJ on B) is
  a property of the metric, not evidence that no energy returns to it. (An earlier reading claimed that it was;
  withdrawn after an external audit, 1 October 2026.) The deviation balance (E2) and the step check (E3) pass;
  the whole-window power balance (E1) fails near the switching edge. A physical energy claim would need the
  cross terms, a declared reference trajectory or storage-energy boundary, and the sources' actual power over
  the window; it is not pursued while no decision depends on it.
- **Q1's channel contributes 59–64 % of the ring-deviation metric in every case.** When the ring starts, Q1's internal gate voltage is
  only about 2.5 V (test 9 traces), and it reaches 4.6 V 20 ns later. But on B the transient's per-cycle ζ stays at
  about 0.0071 even when Q1 is fully on (4.9–5.0 V), twice test 10's local mode. Q1's partial turn-on therefore does
  not explain the whole gap.
- **With the extracted gate paths, the gate loops take 19–29 % of the metric**, mostly in Q2's internal
  gate resistor and the driver outputs, so the driver's output resistance is part of the ring's damping as well as
  its excitation (test 11).
- **The numerical damping resistors take 6.5 % of the metric on G + 50 pH**: a contribution, not the main one.

Shares attribute the simulated ring's dissipation, not the board's; envelope decay is a different quantity.

### EPC90133 test 13: Q1's gate bias and the ring's damping (local AC control)

Hypothesis from test 12, within the model: the ring is damped mainly by Q1's channel while Q1 is still turning on.
`scripts/epc90133_q1_bias_ring.py` (declared before any run; [result](../results/gan/epc90133-q1-bias-ring.json))
repeats test 10's local AC analysis with Q1's gate clamped at 2.5–4.5 V. It compares each result with the
transient cycles at the same Q1 internal gate voltage. Before the run it was already clear from test 12's data
that the declared 5 V comparison fails; this is recorded in AGENTS.md. Run 1 crashed writing its report after B
(a NumPy boolean); run 2 reproduces B exactly.

| Q1 gate clamped at | 2.5 V | 3.0 V | 3.5 V | 4.0 V | 4.5 V | 5 V (test 10) | transient cycles |
|---|---|---|---|---|---|---|---|
| B: local ζ | 0.0092 | 0.0052 | 0.0042 | 0.0038 | 0.0036 | 0.0035 | 0.0086 at about 2.8 V, then 0.0070–0.0075 |
| G + 50 pH: local ζ | 0.0228 | 0.0191 | 0.0182 | 0.0179 | 0.0177 | 0.0175 | 0.0255 at about 3 V, then 0.025–0.027 |

Verdict as declared: **not supported** on either network. Within the model:

- **Partial turn-on raises the local damping** (B: ζ 0.0092 at 2.5 V down to 0.0035 at 5 V), which is
  qualitatively consistent with the stronger damping of the first transient cycle (0.0086 at about 2.8 V). It is
  not a matched-state result: under the declared ±0.15 V rule, B has **no matching cycles at 2.5 or 3 V**, so the
  first cycles were not compared, and Q1's gate voltage changes during each cycle. (An earlier wording said the
  first cycles were explained; corrected after an external audit, 1 October 2026.)
- **It does not explain the later gap**: every matched B comparison (3.5–5 V) fails; once Q1's gate passes about
  3.5 V the local ζ is within 20 % of its fully-on value, while the transient's cycles stay about twice as damped.
- **On G + 50 pH the comparison mixes forms**, a limitation of this test's design: the clamped local cases also
  remove the gate-loop path, which test 12 puts at 29 % of the transient's ring loss, so a lower local ζ is
  expected there for that reason alone. B, which has no extracted gate path, is the clean case.

On hold (owner decision after the project audit, 1 October 2026): an element-by-element comparison of the local AC
mode's losses with the transient's would address B's later cycles, but no hardware or layout decision depends on it
now. Measurement readiness comes first.

Script hardening after the same audit (not rerun; the stored report is from 8284dbd): a fallback-only acceptance
now requires the adapter's failed status and a nonempty list of recognized reasons, and the report separates an
incomplete comparison from a rejected hypothesis. Neither change alters the stored verdicts.

### EPC90133 driver-only bench: supply and bootstrap at VIN = 0 (E1 preparation)

One bounded preparation task for hardware-plan E1 (work-order item 4 of the project audit at 8284dbd).
`scripts/epc90133_driver_only.py` (declared before any run, with stop rules; [report](../results/gan/epc90133-driver-only.json),
[assessment](../results/gan/epc90133-driver-only-assessment.json) by `scripts/assess_epc90133_driver_only.py`) puts the
uP1966E output stages (test 11's ramp and step forms) on their supplies: VCC from the 5 V LDO behind C80, BOOT from
C81 charged by the internal bootstrap switch (a diode through the datasheet's 0.2 V at 100 µA and 0.9 V at 100 mA:
Is 4.2e-8 A, Rs 5.2 Ω). The stages' ramps scale with the actual supply voltage and their pull-up current is drawn
from it. The power stage is unpowered (VIN = 0, two unmodified EPC2302 models, no inductor). Run 1 crashed in
post-processing (lists subtracted as arrays) and wrote no report; run 2 is the one allowed fix run. All 13 LTspice
runs complete without fallbacks (C3), and the stages still give 8.0/4.0 ns into 3000 pF (C2).

**C1 fails as declared and stays failed.** It compared C81's charge loss across the first high-side turn-on with the
pull-up current only. At VIN = 0 the bootstrap switch recharges C81 during that turn-on (about 8 of the 17 nC), which
the check omitted: an error in the check's design. Post hoc, the pull-up charge minus the bootstrap-diode charge
equals C81's loss within 0.013 % in all six edge runs, so the supply wiring is consistent.

What the run answers, within this model:

- **E1 at VIN = 0 can tell test 11's two driver forms apart** (Q1). At the Q2 gate pad (the R22/J2 net) the 10-90 %
  rise is 21.6 ns (ramp) against 24.7 ns (step) without gate-loop inductance, and 20.6 against 23.9 ns with an
  assumed 1 nH; the largest voltage difference near an edge is 2.2 and 1.8 V. Both exceed the provisional
  placeholders (0.3 ns, 0.5 V), which E0's characterized resolution will replace. Into the real gate load at zero
  drain bias (about 17 nC drawn per turn-on) the step form is the slower one, because of its larger resistance; at
  3000 pF the two are identical by construction. The edges are about 20-25 ns, not the datasheet's 8 ns into 3000 pF.
- **The high-side supply in a short sequence is well below the switching bench's ideal 5.0 V** (Q2). After a 0.5 µs
  low-side pre-charge, BOOT-PHASE is 4.30 V before the first high-side pulse and Q1's gate pad settles at 4.42 V
  (4.54 V on the second pulse); with an extra 2.2 Ω in the charging path (R70/R75, connections not transcribed) 4.30 V,
  and with C81 at 50 nF 4.55 V with a 0.22 V drop per turn-on (0.09 V at 100 nF). C81 recharges through the switch's
  5 Ω with a time constant near 0.5 µs, so a 0.5 µs pre-charge is about one time constant. VCC droops by about 10 mV.
- **Start-up without a low-side pulse is not answered.** With both FETs off at VIN = 0 the switch node was held only
  by the bench's assumed 1 MΩ; it rose to about 1.1 V and left BOOT-PHASE at 3.7 V after 200 µs, below the 3.94 V
  maximum BOOT POR threshold. The declared premise that PHASE stays near ground was an assumption the bench does not
  support; the real node depends on leakage paths the model does not represent.
- **Dead-time overcharge is not answered** (Q3). Both excursion runs started at 3.82 V, below VCC minus the switch
  drop, so their 0.17-0.19 V rise is ordinary recharge, not charging above VCC. A run from the settled state needs a
  new declaration.

Consequences for E1 (hardware plan), all conditional on this bench's declared short sequence and assumed bootstrap
circuit; they do not establish the energized board's gate supply:
- Before the first high-side pulse, the procedure requires a verified bootstrap state, not a fixed pre-charge time:
  the BOOT-PHASE voltage at C81 is measured and must be within a stated limit of its settled value. The 0.5 µs
  sequence here left it near 4.3 V.
- The supply state is recorded as a model input: predictions made with the ideal 5.0 V high-side supply assume a
  gate level that this short sequence does not reach.
- BOOT-PHASE in continuous operation (dead-time overcharge, unspecified clamp) is an open quantity to measure.
- The switch node stayed within 0.9 V of ground during the simulated sequence. That does not justify connecting a
  ground-referenced probe's return to J1's switch-node reference: the connection would tie the switch node to earth
  through the probe and change the circuit. Measuring Q1's gate to ground with a separate ground return is also not
  a gate-to-source measurement. The actual probe connection for Q1 is to be specified with the probes.
These are statements about the behavioural driver and the vendor model, not about the board. (Wording corrected
after an external review, 1 October 2026.)

### EPC90133 input logic: can any input state command both gates on? (hardware plan open item 5)

The uP1966E has no HI/LI lockout, so shoot-through protection rests on the board's input logic, its jumpers and the
PWM source. `devices/epc/epc90133-input-logic.json` transcribes QSG Fig. 16 (dead-time and bypass) with the
main-sheet and driver-sheet connections: four 74LVC1G99 configurable gates, two SN74LVC1G66 switches, the R620/C620/D620
and R625/C625/D625 delay networks, the pull-downs and the J630/J640 headers. Both logic datasheets are recorded in
`devices/epc/epc90133-sources.json`. `scripts/epc90133_input_logic.py` (checks declared at fab26fd before the first
run; [report](../results/gan/epc90133-input-logic.json); tests/test_epc90133_input_logic.py) evaluates the
transcription as recorded: L1 BOM, L2 the gate function against all 16 rows of the 74LVC1G99 function table parsed
from the PDF, L3 the QSG's documented settings, L5 supply-threshold order. All pass. Run 1's class label for
two-input settings was wrong where a polarity jumper inverts one channel (its recorded states were right); it is kept
as `results/gan/epc90133-input-logic-run1-label-defect.json`, and run 2 changed only the label.

*Corrected after the project audit at f4767b1* (revision 3, [report](../results/gan/epc90133-input-logic-rev3.json);
the run-2 report is kept unchanged). Run 2's L5 described the commands at driver enable as the static idle state,
which a supply-threshold comparison cannot show; L5 is now only that comparison, and power-up, power-down and
transient overlap are open (E1). The dead-time bound is conditional and never reported as a guarantee while the
discharge delay is unbounded (run 2's `worst > 0` rule could have reported one for a larger resistor; at 120 ohm
it correctly reported none). Revision 3 binds an input manifest (evaluator, transcription, imported helper, both
source records, the five vendor files read and the uP1966E datasheet behind the driver constants, with the
repository revision as context). Its classifications and L1-L3 are identical to run 2.

Each input channel is Y = (C ? B : A) XOR D: U610 gives InBufQup = PWM1 XOR PolQup; U611 gives InBufQlow = (Dual ?
PWM2 : PWM1) XOR PolQlow. U612/U614 select the RC-delayed copy when UseDT is high and are disabled (3-state) when
SWbyp is high, when U615/U616 connect PWM1/PWM2 straight to HIN/LIN. J630 sets PolQlow (1-2), PolQup (3-4) and Dual
(5-6); J640 sets SWbyp (1-2) and UseDT (5-6); pin 3 of J640 is unconnected, so its 3-4 position equals no jumper.

Across all 64 horizontal jumper combinations:

- **Complementary static commands with the RC paths selected, 4 combinations**: J630 1-2 or 3-4 with J640 5-6
  (and the same with an ineffective 3-4 on J640). In steady state the gate commands are complementary from PWM1,
  and each turn-on passes through an RC delay; this does not exclude transient overlap. With open inputs only the
  synchronous-rectifier FET is commanded on.
- **Both gates on at idle, 8**: J630 1-2 and 3-4 together (both polarity bits set) without full bypass. Both
  commands are high with PWM1 low or unplugged.
- **Both follow PWM1, 8**: no J630 jumper, or J630 1-2 with 5-6, without full bypass. Both gates are on whenever
  PWM1 is high (PWM2 open).
- **Complementary but no added dead time, 4**: a single-input polarity jumper with no J640 jumper (the pull-downs
  select dead-time bypass).
- **Two-input, 40**: dual mode or full bypass. Both gates are on for one PWM1/PWM2 combination (usually both high;
  PWM1 low with PWM2 high for J630 3-4 with 5-6), which the PWM source must avoid.

Supply-threshold order: the logic and U80 share the 5 V VCC from U100, and U80's minimum POR threshold (3.8 V) is
above the 74LVC parts' 1.65 V minimum supply. (Run 2 concluded from this that the commands at enable are the idle
state of the jumper setting; that is withdrawn. The ordering says nothing about when outputs, select inputs and RC
nodes settle during the supply ramp, nor about power-down.)

Dead time from datasheet limits (L4, arithmetic, informational): the RC delay R C ln((VOH - V0)/(VOH - VT+)) is 9.6 ns
typical (EPC's Fig. 4 rule gives 9.9 ns for 120 Ω) and 6.3-12.9 ns over R ±1 %, C ±10 %, VT+ limits (interpolated to
5.0 V) and an assumed 0-0.3 V residual voltage, or 5.3-14.8 ns with X7R temperature drift. The two channels'
gate delays may differ by up to 7.3 ns and the uP1966E's delay matching by up to 6 ns, so stacked limits give a
conditional lower bound of about -7 ns at the gate commands (-8 ns with X7R drift; typical about 8 ns), conditional
on the interpolated thresholds and assumed residual voltage. The capacitor's discharge delay, which shortens the dead
time, is not bounded by any datasheet used here, so no guarantee can follow from these data whatever the bound's
sign. Stacked worst cases are pessimistic; the result is only that the datasheets do not guarantee a positive dead
time. The uP1966E datasheet recommends at least 30 ns; EPC recommends 5-15 ns for this
board.

Consequences (hardware plan): the first-power procedure gains a jumper-configuration entry, with the shoot-through
and zero-dead-time settings named as stop conditions, and a measured dead time at the driver outputs before any bus
voltage. Open item 5 is answered for the schematic. The actual board's jumpers and its measured dead time remain
open. Scope: static logic of the published schematic; no timing simulation, no PWM-source behaviour, no noise, not a
measurement of our board.

### EPC90133 first-power content and channel requirements (5 October 2026)

Equipment-independent parts of the first-power procedure are drafted in the hardware plan (v0.4) for the lab's
review. **The QSG's procedure text does not match this board's connectors.** It names VDD "J1, Pin-1" and ground
"J1, Pin-2", but the 12 V input is J90, whose pin 1 is GND in both the schematic and the layout. The silkscreen marks
GND at the square pad and VDD at the round pad. Following the QSG's pin numbers would reverse the gate-drive supply,
so connections are made by silkscreen label. J80's silkscreen (PWM1, GND, PWM2, GND) matches the schematic. The
board has no bleed resistor on VIN, so a discharge path and its verification are part of the procedure. Shutdown
keeps VDD and PWM on until the bus is verified discharged, because the driver's output state below POR is not stated
in the datasheet text read. The double-pulse width limit is given as t1 = L I / V for the user-fitted inductor.

`scripts/epc90133_probe_requirements.py` ([result](../results/gan/epc90133-probe-requirements.json); a derivation
with declared allowances, no pass/fail) turns recorded waveform features into channel requirements. At Fig. 9's
features, the system bandwidth is 0.89 GHz (set by the 264 MHz ring at 3 % amplitude error), with 6.0 GS/s and
168 ps deskew. At the fastest usable simulated case (0.80 ns, 300 MHz): 1.36 GHz, 12.5 GS/s, 80 ps. A floating Q1
gate measurement needs at least 54 dB CMRR. Probe tip capacitance does not limit the choice (20 pF shifts the ring
by 1 %). The first version computed the edge dv/dt from the largest step and the fastest edge of different cases.
It was corrected to a per-case value before the result was recorded.

### EPC90133 design round 1: owner targets on the stock board (5 October 2026)

Owner targets, each relative to the EPC original (the stock BOM in the same simulation): T1 lower switch-node
overshoot, T2 Q1 Eon + Eoff not higher, T3 estimated efficiency at 48 V -> 12 V not lower. Declared at 832a5e1 before
any run (`scripts/epc90133_switching.py --study design`; assessment `scripts/assess_epc90133_design.py`, committed at
b7af345 before the results). Operating point: continuous buck 48 V -> 12 V, 20 A, 250 kHz, 2.2 µH, as a double pulse at
the converter's edge currents (28.2 A turn-off, 11.8 A turn-on). Network G-m1-mid, 100 ps step. Design space: parts
that can be changed on the stock board: R80 (Q1 turn-on resistor) 1 (stock), 2.2 and 3.3 ohm, and R80 2.2 ohm with a
7.5 ns dead time. The dead-time candidate is inadmissible until E1 measures the dead-time margin. Robust rule: a target
counts only if it holds under all four unresolved alternatives ({ramp, step driver} x {package source inductance 0,
50 pH}): T1 at least max(1 V, 10 %) lower, T2 and T3 at most 2 % higher. The efficiency estimate counts FET losses only
(one off interval with both edges and dead times at the converter's currents, plus Q1's on-time conduction). It
excludes inductor, copper, capacitor and gate-drive losses, so its absolute value (about 99.1-99.2 %) is optimistic.
It serves only for ranking.

Run ([report](../results/gan/epc90133-design-round1.json); fix runs
[report](../results/gan/epc90133-design-round1-fix.json);
[assessment](../results/gan/epc90133-design-round1-assessment.json)): 13 of 16 cases are usable. Three 100 ps timing
runs stalled at the start of the transient (LTspice reduced Tseed to 1e-17 s) and hit the 1800 s limit: stock with
the step driver and 50 pH, and R80 3.3 ohm under two alternatives. The declared 50 ps fix pair resolved the candidate
(R80 2.2 ohm at 50 ps matches 100 ps within 0.011 % on every target metric: the numerical check passes). The stock
case stalled again at 50 ps (3600 s), so that alternative's T1 comparison stays open. Assessment revision 1 reported
'undetermined' wherever an alternative was missing, even when another had already failed. One failure already decides
'not met', so revision 2 corrects the precedence; the v1 output is kept as
`results/gan/epc90133-design-round1-assessment-v1-precedence-defect.json`.

Result (change against stock under each alternative that ran):

| Design | Overshoot | Q1 Eon + Eoff | FET loss | Q2 gate peak |
|---|---|---|---|---|
| R80 2.2 ohm | -16 to -60 % | +7.5 to +14 % | +1.5 to +18 % | -10 to -41 % |
| R80 2.2 ohm, dead time 7.5 ns | -16 to -61 % | +7.4 to +13 % | -0.8 to +15 % | -9 to -41 % |
| R80 3.3 ohm | -44 to -75 % | +14 to +17 % | +9 to +20 % | -23 to -47 % |

*T3 and the efficiency figures in the table above are invalid (loss-estimator revision 2, see "layout round 2a"); the
rerun is revision 2 below.*

Verdicts: **no candidate meets all three targets.** T1 holds under every alternative that ran but stays undetermined
(the stock step-driver, 50 pH case is missing). T2 and T3 are not met. A larger R80 slows Q1's turn-on: Eon rises
while the overshoot falls. The shorter dead time recovers only about 0.05 W of the roughly 0.3 W extra loss. The
overshoot benefit shrinks to about 16 % when an assumed 50 pH package source inductance already slows the edge, so
the size of the trade depends on an unresolved device property. A side result, not a target: Q2's gate spike during
Q1's turn-on falls by 10-47 %, a better false-turn-on margin.

Reading, within this model: the gate-drive changes available on the stock board trade overshoot against switching
energy; none lowers both. Meeting all three targets would need a change that lowers the loop or common-source
inductance rather than slowing the edge, which means a layout change and a new board. The trade-off and its size are
provisional simulation predictions, not a frozen prediction record and not validated values (EPC2302 Fig. 7
exception, behavioural driver, exploratory extraction).

**Revision 2 (loss-estimator revision 2; 5 October 2026).** The first rev-2 launch (PID 29988) ended at 16:52 with no
error output after 7 of 16 cases, apparently when its launching session closed (Start-Process did not detach it from
the session's process tree). Long runs are now started through WMI (`Win32_Process.Create`), outside any session.
The 9 cases that never started ran unchanged as a continuation
([report](../results/gan/epc90133-design-round1-rev2-cont.json)). The persistent stock step-driver, 50 pH stall is
not a start-up stall: the partial raw file shows normal progress to 1.753 µs and then steps of about 1e-19 s, 0.76 ns
after Q2's turn-on command. Further trapezoidal runs stalled the same way at other edges (20 ns, 1.82-1.94 µs,
4.74-4.75 µs), and a smaller step makes it worse (75 ps stalls at 20 ns in profiling). Declared fallbacks: the Gear
fallback and its extension were committed before the runs they cover (d5184f3, 55d9f7d); the cross-method rule
(1b24989, 19:58) is a retrospective amendment, committed after R80-2.2-dt7.5@ramp-Ls50-gear, a result it affects,
had finished (19:28; audit at 5d72e4e). Gear integration at the same 100 ps step, Gear
pairs compared with each other only, valid if a declared Gear-versus-trapezoidal check passes
([report](../results/gan/epc90133-design-round1-rev2-gear.json),
[extension](../results/gan/epc90133-design-round1-rev2-gear2.json)). **The check passes by a wide margin**: on
stock and R80 2.2 ohm (step-Ls0), R80 2.2 ohm (step-Ls50) and stock (ramp-Ls0), overshoot, FET loss and Q2 gate peak
agree within 0.05 %, and the stock-to-candidate differences within 0.3 %. Gear stalls too, but rarely: stock ramp-Ls50
with Gear stopped at 4.98 µs. Where only a trapezoidal stock case and a Gear candidate exist, a cross-method comparison
is allowed, and it decides a constraint only outside a 0.1 % margin. The rev-2 timeouts are kept in the reports.
Without this amendment the dead-time candidate's ramp-Ls50 comparison is undetermined; its verdict stays 'not met'
either way, because its matched ramp-Ls0 comparison already fails C1.

Rev-2 result, against stock under each alternative (all four alternatives now resolved for every candidate;
[assessment, round-1 rule](../results/gan/epc90133-design-round1-rev2-assessment.json),
[assessment, owner's round-3 rule](../results/gan/epc90133-design-round1-rev2-assessment-round3.json)):

| Design | Overshoot (stock 25.1 / 16.6 / 11.2 / 10.9 V) | FET loss | Q2 gate peak |
|---|---|---|---|
| R80 2.2 ohm | 10.0 / 6.9 / 9.4 / 8.0 V (-16 to -60 %) | +5.5 to +9.0 % | -10 to -41 % |
| R80 3.3 ohm | 5.0 / 4.2 / 6.3 / 5.0 V (-44 to -80 %) | +10.4 to +14.2 % | -23 to -57 % |
| R80 2.2 ohm, dead time 7.5 ns | 9.9 / 6.8 / 9.4 / 8.0 V (-16 to -61 %) | +3.0 to +6.3 % | -9 to -41 % |

(Alternatives in the order ramp-Ls0, step-Ls0, ramp-Ls50, step-Ls50.) Under the round-1 rule T1 is now met by every
candidate, and T2 and T3 are not. Under the owner's rule (overshoot objective; FET loss at most +5 % and Q2 gate
peak not above stock under all four), **every round-1 candidate fails the loss constraint**. The binding alternative
is the ramp driver without package inductance, where the slower edge costs the most. The shorter dead time recovers
about 2.5 points of loss and fails only there (+6.3 %), but it stays inadmissible until E1 measures the dead-time
margin. A straight-line reading puts the largest admissible R80 at about 1.6-1.8 ohm, so round 3 tests 1.2, 1.5
and 1.8 ohm.

### EPC90133 design round 3: the largest admissible Q1 turn-on resistor (5 October 2026)

Owner's rule (decision of 5 October; plans/layout-round-2-plan.md): overshoot is the single objective. Constraints
under all four alternatives: C1 FET loss at most 5 % above stock's, C2 Q2 die gate peak during Q1's turn-on not
above stock's. Candidates are ranked by their worst-case overshoot. Declared at 8b6cc4b before any run: R80 1.2, 1.5
and 1.8 ohm (E12 parts; a resistor swap on the stock board), chosen from rev 2's straight-line reading. Same bench as
rev 2. step-Ls50 runs directly with Gear, and stock is not rerun. A reproduction control, stock@ramp-Ls0-repro,
**reproduces rev 2 exactly** (identical netlist hashes for the timing and main runs, zero metric difference), so
round 3 is compared with rev 2's stock cases. Reports: [main](../results/gan/epc90133-design-round3.json), Gear
fallbacks [a](../results/gan/epc90133-design-round3-gear-a.json) and
[b](../results/gan/epc90133-design-round3-gear-b.json), [numerical check](../results/gan/epc90133-design-round3-check.json),
[assessment](../results/gan/epc90133-design-round3-assessment.json). Trapezoidal stalls were frequent (6 of 13 cases;
Gear stalled in 2 of 8). Each was handled by a fallback declared beforehand. The R80 1.2 ohm 50 ps ramp-Ls50 pair
(results/gan/epc90133-design-round3-ms50-a.json) finished after the assessment: stock usable, R80 1.2 ohm unusable;
no decision depends on it.

| R80 | Overshoot ramp-Ls0 / step-Ls0 / ramp-Ls50 / step-Ls50 (stock 25.1 / 16.6 / 11.2 / 10.9 V) | FET loss | Q2 gate peak | Verdict |
|---|---|---|---|---|
| 1.2 ohm | 21.3 / 14.2 / - / - V (-15, -14 %) | +1.9, +1.4 % | lower | undetermined (Ls50 cases stalled with both methods) |
| **1.5 ohm** | **16.8 / 11.4 / 10.8 / 9.7 V (-33, -31, -4, -11 %)** | **+4.3, +3.3, +2.4, +2.6 %** | **lower in all four** | **meets C1 and C2; worst case 16.8 V** |
| 1.8 ohm | - / 9.2 / 10.2 / 9.0 V (-44, -9, -17 %) | +5.1 % (step-Ls0), +3.7, +3.9 % | lower | not met (C1, step-Ls0) |
| 2.2 ohm (rev 2) | 10.0 / 6.9 / 9.4 / 8.0 V | +5.5 to +9.0 % | lower | not met |

**Result: R80 1.5 ohm is the best tested candidate** (the tested grid does not exclude values between 1.5 and
1.8 ohm or other parts; no further search is needed to justify E4). It is the only candidate that meets both
constraints under every
alternative, and it lowers the worst-case overshoot from 25.1 V to 16.8 V (-33 %). In absolute terms the loss cost
is at most 0.09 W at 240 W, about 0.035 efficiency points under this FET-only estimate. R80 1.2 ohm cannot outrank
it whatever its missing cases show, because its ramp-Ls0 overshoot alone (21.3 V) exceeds 16.8 V. R80 1.8 ohm misses
C1 by 0.1 points under step-Ls0, a same-method comparison. Numerical check (declared at 8dfc08a): R80 1.5 ohm at
50 ps matches 100 ps within 0.002 % on overshoot, FET loss and Q2 gate peak.

Reading: the benefit depends on the unresolved package source inductance. Without it, R80 1.5 ohm cuts the overshoot
by about a third. With an assumed 50 pH the edge is already slow, and the cut is only 4-11 %. The decision is robust
to that unknown (C1 and C2 hold in all four alternatives), but the size of the improvement is not. Measuring the stock
board's overshoot and Q2 gate waveform before the swap (E3/E4) can constrain the alternatives, but cannot by itself
identify the package inductance: driver behaviour, model discrepancy and probe response are competing explanations.
The before/after swap tests the predicted response. The largest predicted loss increase, +4.34 %, leaves 0.66 points
to C1; that is a margin within the model, not a hardware margin or an uncertainty bound, and the half-step check
covers step-Ls0 only. The shorter
dead time would allow a larger R80 (rev 2: 2.2 ohm with 7.5 ns fails C1 only under ramp-Ls0, at +6.3 %), but it stays
inadmissible until E1. A layout lever was not run (plan order step 3). Round 2a on A gives at most -11 to -23 %
overshoot for +3.1-3.8 % loss at the 0.050 mm gap; adding that to R80 1.5 ohm's +4.3 % suggests, but does not show,
that the combination would exceed C1 (percentages from two different models; the combination was not simulated).
Combined with 1.2 ohm, the same addition (about -25 % at about +4-6 % loss) does not clearly beat 1.5 ohm alone. It
needs a new board, and deferring it for that reason stands without a verdict. These are provisional simulation
predictions for experiment E4 (R80 swap) on the purchased board, not yet a frozen prediction record (that needs the
approved conditions, hardware plan 'Frozen prediction record') and not validated values (EPC2302 Fig. 7 exception,
behavioural driver, exploratory extraction G).

**Assessor revision 4 (6 October 2026; audit at 5d72e4e, docs/project-audit-5d72e4e.md).** The audit reproduced the
round-3 assessment exactly and found the evaluator unsafe as an unattended gate: a missing alternative dropped out of
the rule, the declared reproduction and half-step controls did not affect the selection, missing Gear-check cases were
skipped, and incompatible inputs (estimator revision 1, unsettled loss, another extraction) were accepted.
`scripts/assess_epc90133_design.py` revision 4 requires the four declared alternatives, checks every case's name
against its parameters and the reports' conditions and extraction/library hashes (input rejected otherwise, exit 2),
counts a loss only from estimator revision 2 with a settled window, requires the Gear check's whole case set, gates
the selection on the reproduction control and the top candidate's half-step check, and emits each comparison as a
resolved pair. It reports verdicts under the amended rule and under the original rule without the cross-method
fallback. Fault tests: tests/test_design_assessment.py (every audit probe now yields no selection or a rejection).
Rerun on the same inputs plus the finished ms50-a report, no simulation:
[assessment rev 4](../results/gan/epc90133-design-round3-assessment-rev4.json); per-alternative verdicts and
overshoots identical to the stored assessment (kept), and **R80 1.5 ohm is selected under both rules**, with all four
of its comparisons same-method (two trapezoidal, two Gear).

**Assessor revision 5 (6 October 2026; audit at 0f07a6a, docs/project-audit-0f07a6a.md finding 1).** Revision 4 still
selected R80 1.5 ohm when one of its overshoot values was null (ranking `[["R80-1.5", null]]`), treated `usable:
"false"` as true, and raised AttributeError on a null case or a list-valued manifest. Revision 5 checks types before
use (objects where objects are expected, `usable` a literal boolean, absent only for a case with no metrics, every
metric read a finite number or null) and rejects malformed input with exit 2 and reasons. A design whose overshoot is
missing under any alternative has objective "undetermined" and is never ranked or selected. The audit's probes are
fault tests in tests/test_design_assessment.py. Rerun on the stored inputs, no simulation:
[assessment rev 5](../results/gan/epc90133-design-round3-assessment-rev5.json); verdicts, pairs, ranking and the
**R80 1.5 ohm selection are identical to revision 4 under both rules**.

### EPC2302 gate-charge sensitivity: does R80 1.5 ohm depend on Fig. 7? (7 October 2026)

Question (owner): the vendor model fails datasheet Fig. 7, and R80 1.5 ohm acts by slowing the Miller plateau. Does the
decision change if EPC's drawn curve, not EPC's model, describes the device? Two steps, each declared before its runs.

**Step 1: a Fig. 7-following model revision** (`scripts/epc2302_qg_variant.py`, declared at a0123c5;
[report](../results/gan/epc2302-qg-variant.json)). EPC2302QG is the vendor subcircuit, renamed, with three charge terms
scaled: kgs on the linear gate-source capacitance ags1, kgd on the gate-drain terms agd1/agd2/agd5, and (declared
fallback) kon on the on-state term ags2. The derived library is git-ignored in vendor/epc/derived/ (EPC model text);
the report records factors and hashes. It is a sensitivity case, not tuning under the project's rule: nothing isolates
the Fig. 7 discrepancy to the device. Run 1 crashed (the curve was thinned by sample index, and the variant's
transient crowded 4.3 million points into a short stretch). Run 2 failed: a trapezoidal start-up stall at t = 0 (step
about 7e-20 s, 45.6 million points in 3.3 ns of the quiescent state) timed out a fit run. Both are kept, and revisions 2
and 3 are labelled retrospective: charge-resampled curve, V0 against a fresh vendor run, Newton fit, Gear integration
with a Gear-vs-trapezoidal check (V0b). **Run 3 passes**: V0 exact, V0b within 4e-7, and V1, the comparator's own
Fig. 7 checks (vertical 0.10 V, horizontal 5 % + 0.25 nC), which the vendor model fails. The kon fallback was needed:
kgs 1.096, kgd 1.230, kon 0.718. The charge-equation check is within 1 %.

Two findings. (1) **Figs. 5 and 7 cannot both be matched in this model structure.** The variant's CRSS is 23 % above
the vendor model's at every VDS, outside the Fig. 5b tolerance (0.05 decade) everywhere; CISS +10 %, COSS +1 %. Which
one the device follows needs a measurement (hardware plan E7: gate charge and C-V on the B1506A). (2) **The plateau-width
feature depends on sampling.** On a curve resampled every 0.01 nC, the vendor model's plateau is 2.40 nC (start 7.79),
not 2.19 nC (start 7.89) as on the stored, index-thinned curve. The stored '24 % narrow' is about 16 % on the resampled
curve. The horizontal failure (1.25 nC low at 3.0 V) does not depend on sampling.

**Step 2: the design comparison with both models** (`--study qgfit`, declared at 636ddd7 with
`scripts/assess_epc90133_qgfit.py`; [report](../results/gan/epc90133-qgfit.json),
[assessment](../results/gan/epc90133-qgfit-assessment.json)). Stock and R80 1.5 ohm, four alternatives, both models,
all with Gear at 100 ps, extraction G-m1-mid. All 17 cases are usable. The 50 ps check on the variant passes (within
6e-6). The vendor cases reproduce the stored round-1/round-3 values within 0.04 %.

| Alternative | Vendor model: overshoot stock -> R80 1.5 | loss | Variant: overshoot stock -> R80 1.5 | loss |
|---|---|---|---|---|
| ramp, assumed 50 pH | 11.2 -> 10.8 V (-4 %) | +2.4 % | 10.4 -> 9.7 V (-7 %) | +2.5 % |
| step, assumed 50 pH | 10.9 -> 9.7 V (-11 %) | +2.6 % | 9.7 -> 8.4 V (-14 %) | +2.6 % |
| ramp, 0 pH | 25.1 -> 16.8 V (-33 %) | +4.3 % | 22.3 -> 14.6 V (-34 %) | +4.2 % |
| step, 0 pH | 16.6 -> 11.4 V (-31 %) | +3.3 % | 14.4 -> 9.6 V (-33 %) | +3.3 % |

Q2 gate peak is lower with R80 1.5 ohm in all eight comparisons. **Both models: R80 1.5 ohm meets C1 and C2 under all four
alternatives.** Reading (fixed in the assessor): the decision does not depend on the Fig. 7 discrepancy within these
models, and an E4 prediction should carry both models' values as the range over the unresolved gate charge. The
variant itself moves the stock board: overshoot -7 to -14 %, rise time +2 to +6 %, Eon+Eoff +2 to +3 %, FET loss
+1.4 to +2 %. This is the size of the gate-charge uncertainty in the stock-board prediction (E3). Neither model is
shown to describe the real EPC2302.

### EPC90133 track R step 1: copper in KiCad (6 October 2026)

Track R (plans/layout-round-2-plan.md) rebuilds an editable KiCad design from EPC's Gerbers, for our own board
(G5). Step 1 converts the eight copper layers. `scripts/epc90133_reconstruct.py` applies each layer's drawing
commands in order (copper added, cut-outs removed) with shapely. It splits polygons with holes into hole-free pieces,
because KiCad graphic polygons have none, and writes a KiCad 10 board with the GM1 outline. kicad-cli then exports
Gerbers for comparison. The board file is a derivative of EPC's layout and the repository is public, so it stays in
the git-ignored vendor/epc/epc90133/reconstruction/. Only the script and the summary report are committed.

Run 1 crashed (hole splitting exceeded the recursion limit; no report). Run 2 FAILED its declared pixel criteria on
every layer (XOR 0.20-0.58 %, mismatch regions up to 0.73 mm^2) and is kept
([report](../results/gan/epc90133-reconstruct-copper-run2-failed.json)). The diagnosis is that the mismatch exists
before KiCad, and every mismatched pixel lies within 0.041 mm (1.6 pixels) of a true edge. The reader's raster
fills every pixel an edge touches, so the revision-1 criteria tested the raster rather than the conversion.
Revision 2, declared before run 3, compares geometry exactly and keeps a raster cross-check. **Run 3 passes**
([report](../results/gan/epc90133-reconstruct-copper.json)): on every layer the symmetric difference is at most
0.000004 % of the copper area (largest piece 2e-6 mm^2), every raster mismatch lies within 0.042 mm of an edge,
and the outline is exact. Scope: copper shapes only, no parts, nets, vias, drills, mask or zones (steps 2-4). Arcs
are 5-degree polygons, as in the reader. The raster reader used for the extractions has the same ~1-pixel
(0.025-0.04 mm) edge uncertainty, which is far below the extraction meshes.

**Step 2a: which side each part is on (6 October 2026).** EPC's layout PDF (an Altium export inside the Gerber
package) carries hidden text tags for every pad (`PA<ref><pin>`, boxes about the pad's size, 0.2-0.5 mm off), a
tag at each designator, and a bookmark tree with every part's pad names and EPC's full netlist (37 named nets, 301
pads). The bookmarks list all 118 parts on every layer page, so they do not give the side. Four quick side tests
each misplaced parts in the stacked power stage, where top Ci capacitors sit directly over bottom Cm capacitors.
`scripts/epc90133_reconstruct_parts.py` therefore declares a rule: netlist consistency on our copper connectivity
first, then mask-pad size, then openings already claimed by other parts, then earlier anchors, and silkscreen only
for through-hole and mechanical parts, whose side changes no copper. Run 1 failed: a paste veto that was already
known to be unreliable, plus independent pad snapping that let two pins share an opening. Run 2 failed: the
switches' unnamed auxiliary pad, the inductor's large pads beyond a fixed snap radius, and the standoffs. Both are
kept ([run 1](../results/gan/epc90133-reconstruct-sides-run1-failed.json),
[run 2](../results/gan/epc90133-reconstruct-sides-run2-failed.json)), each with a revision declared before the
next run. **Run 3 passes all five checks** ([report](../results/gan/epc90133-reconstruct-sides.json)): all 301 pads
matched one-to-one to mask openings; 47 parts on top and 59 on the bottom; and every net with two or more pads on
one copper island. The 26 parts whose side earlier scripts had established (Ci top, Cm bottom, Q1, Q2, U80 and
R80-R83 top) were all placed correctly by the evidence; the anchor rule was not needed once. Per-part sides and
pad positions are EPC-derived and stay in the git-ignored reconstruction folder. Next: footprints built from these
pads (mask, paste, copper, drills), placed in the KiCad board, and a mask/paste round trip.

**Step 2b: footprints from the board's own pads (6 October 2026).** `scripts/epc90133_reconstruct_footprints.py`
places 106 footprints built from EPC's pads, not from libraries, because several parts have none and EPC's land
patterns may differ. Each pad's copper is its mask opening cut to the existing copper, so pads add no copper.
Each footprint carries its own mask and paste shapes, plated pads get drill-size holes, and the two standoffs get
non-plated holes. All 299 named pads carry EPC's net names. Runs 1-4 failed and are kept:
- run 1 crashed: our Gerber reader could not parse KiCad's parameterised macros (fixed, regression test added;
  EPC's files are read unchanged);
- run 2 failed on a coordinate bug, and run 3 was an accidental identical repeat;
- run 4 failed only on mask openings wrongly given to the two standoff holes.
**Run 5 passes all checks** ([report](../results/gan/epc90133-reconstruct-footprints.json)). Copper, mask and
paste on every layer round-trip through KiCad with at most 0.000023 % difference, every named pad has copper and
EPC's net, and every drill is accounted for. KiCad's DRC is reported, not checked: the copper is still unnetted
graphics, so shorts and clearance hits against it are expected until step 3 gives it nets.

**Steps 3-4: nets on the copper, vias, stackup (6 October 2026).** `scripts/epc90133_reconstruct_nets.py` turns
each copper island into a KiCad zone. The zone takes the net of the EPC pads on its connected group (islands joined
across layers through plated holes). Its fill is EPC's copper exactly, written as KiCad stores fills: one outline,
with every hole joined by a zero-width slit; a known-answer test reproduces the area exactly. Every plated hole
that is not a component pad becomes a drill-size via with its net. The stackup comes from EPC's stackup file
(8 x 2.8 mil copper; dielectrics 5/5/7.2/5/7.2/5/5 mil FR370-HR; 63.2 mil total). Core/prepreg is not stated in
the file, so all dielectrics are written as prepreg, an assumption with no effect on the Gerbers.

Run 1 failed only the drill comparison, because our Excellon reader ignored KiCad's decimal points (fixed,
regression test; EPC's file is read unchanged). It is kept
([report](../results/gan/epc90133-reconstruct-nets-run1-failed.json)). **Run 2 passes all checks**
([report](../results/gan/epc90133-reconstruct-nets.json)):
- the Gerbers of all 12 copper, mask and paste layers round-trip exactly;
- all 445 drill holes come back with the same position, size and plating;
- no copper group carries two nets;
- KiCad's own DRC finds zero shorts and zero unconnected items, so KiCad's connectivity matches EPC's netlist;
- the stackup total is 63.2 mil.

The result has 1206 zones and 394 vias; 29 islands carry no net, which KiCad also reports as isolated copper.
Other DRC violations are reported, not checked, because KiCad's default rules are not EPC's: drill-size vias give
annular-ring and via-diameter hits, and EPC's tighter clearances give clearance hits.

Still open for track R:
- the silkscreen layers are not yet reconstructed;
- the DRC rules should be set to EPC's (from the .RUL file in the Gerber package) and every remaining violation
  explained;
- zone fills are EPC's copper frozen: a KiCad refill would regenerate them by KiCad's rules.

**Step 5: rings, silkscreen, EPC's rules, explained DRC (6 October 2026). Track R complete.**
`scripts/epc90133_reconstruct_final.py` writes the final board (vendor/epc/epc90133/reconstruction/epc90133.kicad_pcb
and .kicad_pro, git-ignored). Changes over steps 3-4:
- vias and plated pads get real rings: the largest circle inside EPC's copper on every connected layer, capped
  at the measured via pad (about 0.65 mm for both drill sizes) or the pad's mask opening;
- zone priorities follow nesting;
- netless pads follow KiCad's convention (unused pins get 'unconnected-(part-pin)'; the unnamed auxiliary pads
  in Q1/Q2's gate pads take VGu/VGl);
- the outline is one rectangle, the silkscreen is added, and back-side references are mirrored;
- EPC's .RUL rules are applied: 5.91 mil clearance, the smallest of six (the export lost the named rules' net
  scopes), 5 mil width and 2 mil mask expansion. Edge, hole and via minima are not in EPC's file and are not
  enforced.

Run 1 crashed (silkscreen file naming). Run 2 failed only on two undeclared DRC categories, and is kept
([report](../results/gan/epc90133-reconstruct-final-run2-failed.json)). The run also showed that KiCad lists at
most 499 items per DRC type. **Run 3 passes all five checks**
([report](../results/gan/epc90133-reconstruct-final.json)):
- all 14 Gerber layers (8 copper, mask, paste and silkscreen on both sides) and all 445 drills round-trip
  exactly;
- KiCad finds 0 shorts and 0 unconnected items, and no EPC net changed;
- every remaining DRC item is in a declared category:
  - 499+ clearance items at EPC's rule within 1 um, the arcs being 5-degree polygons. A second DRC at the rule
    minus 1 um reports none, so no gap is below EPC's rule by more than the declared 1 um geometric tolerance;
  - 8 edge items on a 0.25 mm ring centred on the outline. EPC's Altium export draws the outline into every
    copper Gerber, and the fab trims it, so it is not real copper;
  - SO3's 3 mm plated hole, which EPC's copper gives no ring;
  - EPC's silkscreen near the edge, 13 isolated netless islands, and the footprints not being from a library.

Limits:
- the zones hold EPC's fills frozen. A KiCad refill does NOT reproduce them (audit at 0f07a6a, on a scratch copy:
  0.98-1.85 % symmetric-difference area in G's power/gate window, 2.3-2.8 % over the board interior with drills
  excluded; isolated-copper items 13 -> 43, two solder-mask bridges). This board reproduces the saved geometry; an
  edit/refill workflow is not qualified, and zero shorts/unconnected does not show that extraction geometry is
  preserved;
- the named EPC clearance rules (gate drive, logic, PSU, FET) lost their scopes, so only the board minimum is
  enforced;
- this is EPC's published layout (B5253 Rev 2.0), not yet checked against the board we buy.

**Audit at 0f07a6a: runner fixes and an independent readback (6 October 2026).** The audit found that both track R
DRC steps ignored kicad-cli's exit status and read fixed report paths, so a failed command with a stale `{}` report
passed R3 and R4; that the reports did not identify the board checked; and that R5 looked only at pads the script had
itself assigned. `src/circuit_tools/kicad.py` `run_drc` now writes each report to a fresh path, requires exit status
0, validates the drc.v1 structure and the report's source board, and checks that the board did not change
(tests/test_kicad_drc.py with a fake kicad-cli). `scripts/epc90133_reconstruct_final.py` (revision 3) and
`epc90133_reconstruct_nets.py` use it, and step 5 now binds board, project, input board, DRC reports, KiCad version
and helpers by hash. The stored step 3-5 reports were made before this change and stand; nothing was rebuilt.
`scripts/verify_epc90133_reconstruction.py` (declared at 4c69320 before its first run) checks the saved board
without reusing the construction. Run 1 **passes V1-V4**
([report](../results/gan/epc90133-reconstruct-verify.json)):
- V1: KiCad's IPC-D-356 export of the saved board lists all 288 pads of EPC's netlist, read directly from the layout
  PDF, each with EPC's net;
- V2: the 13 other pad records are each explained by a declared rule: 10 numbered pads outside EPC's netlist carry
  KiCad 'unconnected' nets, Q1/Q2's unnamed auxiliary gate pads coincide with gate pads and carry VGU/VGL, and SO1/SO2
  are unplated N/C holes;
- V3: all 443 vias and plated through-hole pads have rings larger than their drills or are listed as ringless;
- V4: a fresh DRC of this exact board (SHA-256 79ba8e1e..., the hash the audit recorded) reports 0 shorts and 0
  unconnected items, and 0 clearance items at EPC's rule minus 1 um.
This binds the current local board to a passing check. It cannot show retroactively that run 3 checked the same file,
and it does not address KiCad's refill (above).

### EPC90133 geometry-edit workflow qualified for two primitives (7 October 2026)

The audit at 0f07a6a required one bounded edit workflow before any G5 geometry change. Cause of the refill problem:
each EPC copper island is a KiCad zone outlined by its exterior, so a refill regenerates EPC's holes from KiCad's single
0.150 mm clearance and fills the rest. A labelled feasibility probe (scratch only) confirmed it. A plain refill
reproduced the audit's numbers exactly (window 1.06 %, 48 mm^2 of top-layer copper added against 0.6 removed,
isolated copper 43). With one copper-fill keep-out per stock hole, nothing was added, and every difference vanished
at a 10 um tolerance with drills excluded. The residue is KiCad's arc approximation (5 um default).

Workflow (`scripts/epc90133_edit_workflow.py`, declared at 786cf18):
- **Editable base:** the verified saved board (SHA-256 checked against the readback verifier) plus 5,680 fill keep-outs.
  Each keep-out is an island's interior ring minus the islands inside it, split into hole-free pieces. Written to
  git-ignored vendor/epc/epc90133/reconstruction/edit/.
- **Edits:** ordered lists of primitives applied to the base text. KiCad-saved boards are outputs and are never
  edited. `move_footprint(ref, dx, dy)`; `move_via(x, y, dx, dy)`, which also moves every zone and keep-out inside
  the via's clearance holes, so EPC's hole shape travels with the via and the old hole fills.
- **Each build:** KiCad refill, a fresh DRC, Gerbers, IPC-D-356, and a zone-free copy for pad-only copper.

Run 1 crashed in W2's zone parser and is kept
([report](../results/gan/epc90133-edit-workflow-run1-crashed.json)): three keep-outs are triangles, and the parser did
not close their rings. W0 and W1 had passed. Revision 2 fixes only the parser. **Run 2 qualifies the workflow**
([report](../results/gan/epc90133-edit-workflow.json)):
- **W0, no edit:** copper on all eight layers equals EPC's Gerbers within 10 um (zero residual), mask and paste
  equal, DRC 0 unconnected / no shorts / no mask bridges / isolated copper 13 / no clearance below the rule, and
  IPC-D-356 pad nets equal the verified board's.
- **W1, Ci7 moved -0.30 mm in x:** copper outside the edit window is unchanged within 1 um. Inside it, copper equals
  W0 plus the new pad copper (no change: the pads stay on their own VIN/GND copper). DRC and nets are as W0. Ci7's mask
  and paste openings equal EPC's translated by the move. Moving it back gives W0 exactly.
- **W2, GND via (24.16, 36.40) moved +0.20 mm in x:** five zones and keep-outs moved on each of In5/In6 (the
  via's clearance holes). 0.31 mm^2 of copper changed per layer, equal to the expected geometry (old hole filled,
  translated hole cut, pad moved) with zero residual. Outside the window nothing changed. The via is at the new
  position on GND, none at the old, the DRC is as W0, and moving it back gives W0 exactly.

Scope: this qualifies these two primitives on this board. A saved-geometry or workflow pass is not fabrication
approval.

**Reshape primitive qualified (7 October 2026; suite `--suite reshape`, declared at f1182f6).** Layout improvements
need new copper shapes (owner), so a zone-outline primitive was added. `reshape(layer, net, add, cut)` works on
rectangles in EPC millimetres:
- **cut:** every zone on the layer loses the region, and the region becomes a keep-out. That is needed because the
  board-outline ring is a netless zone covering the whole board, kept empty inside by keep-outs.
- **add:** the region merges into the net's zone it touches; other nets' zones lose the region grown by EPC's 0.150114 mm
  clearance; keep-outs lose the region.
- Zones split into pieces become one zone each; holes become keep-outs computed against the edited outlines.

Test site: the straight SW/VIN boundary on F.Cu right of Q1 (gap 0.163 mm, no pads, nearest via 0.8 mm away). A dry
text check before any run found the ring-zone problem; the fix is recorded in the code. Run 1 failed and is kept
([report](../results/gan/epc90133-edit-reshape-run1-failed.json)): the zone rebuild left two extra ')' per rebuilt line,
so KiCad stopped reading before the board outline without an error (DRC: no Edge.Cuts edges, 184-203 unconnected).
Revision 2 fixes the substitutions and refuses an unbalanced board before any refill. **Run 2 qualifies the
primitive** ([report](../results/gan/epc90133-edit-reshape.json)), with W0 passing again:
- **Z1, cut a 2.0 x 0.3 mm notch from VIN:** exactly 0.600 mm^2 removed, equal to W0 minus the notch with zero
  residual;
- **Z1R, cut then add back:** equals W0 exactly;
- **Z2, VIN edge moved 0.20 mm toward SW over 2 mm:** 0.684 mm^2 changed, equal to the expected geometry (VIN plus
  the region, SW cut back by the clearance) with zero residual; smallest VIN-to-SW gap 0.153 mm (rule 0.150).

In every case nothing changed outside the edit window on any layer, the DRC is as stock (0 unconnected, isolated copper
13, no new types), the pad nets are unchanged, and mask and paste equal EPC's.

Scope: rectangular regions on one layer, qualified at one site. A board candidate built with these primitives still
needs its own DRC, net and extraction checks. Nothing here is fabrication approval.

**Edited board -> extraction route, and the first layout candidate L3a (7 October 2026;
`scripts/epc90133_board_export.py`, declared at 77ac049).** The driver writes an edited board as an EPC-style Gerber
package: KiCad's aux origin at EPC's origin, so coordinates are EPC's, with EPC file names and plated and non-plated
drills in one Excellon file. `read_epc90133_geometry.EXPORT_ENV`, set only in the child processes, makes the
power-loop contact finder and the extraction read it, with a manifest hash check. **X0 run 1 (stock through the
route) is not qualified as declared** ([report](../results/gan/epc90133-board-export-x0.json)):
- drills are identical, and the power-loop contacts and check outcomes are identical;
- but A:m1:mid gives 0.4925 against 0.5017 nH (-1.8 %; one port self-inductance 8.8 %; 2,805 against 2,756 mesh
  nodes). The rasters differ by 12,000-27,000 pixels per layer outside holes, because micrometre edge differences flip
  1 mil pixels and the pin-aligned mesh puts pad edges on grid lines. On the top layer, EPC also draws 14 mm^2 of copper
  over drill holes that KiCad leaves empty. A diagnostic that cleared the top hole disks of EPC's own Gerbers crashed
  because Ci1's GND terminal lost all its mesh nodes.

So the extraction is sensitive at about 2 % to sub-10 um representation and to the hole-copper convention, inside
the 2-4 % via/mesh sensitivity already recorded. **Retrospective amendment:** edited boards are compared only with
stock exported through the same route, and a loop-inductance change counts only beyond 4 %.

Candidate **L3a** (layout plan L3): Ci1-Ci7 move 0.40 mm toward Q1, about 0.26 mm short of the Q1 switch-node bars.
The 20 VIN stitching vias under their pads move with them through a new group primitive `move_vias`; the shared
inner-layer slots move once. Top GND copper is widened 0.40 mm by `reshape`. The GND via row at y = 34.90 and the bottom
capacitors stay: moving the row would put it against the bottom Cm VIN pads, which cannot follow because of the bottom
switch-node fingers.
- **Run 1 was rejected and kept** (package export/L3a-run1-rejected): a 0.011 mm^2 GND sliver isolated on In1 where the
  x = 16.05 via pair nears the plane edge; EPC's frozen silk ticks on the moved pads (14 silk_over_copper); the
  power-loop Ci window (fixed at y >= 33.0) dropped the moved VIN pads; and a driver key error.
- **Revision 2** (retrospective): silk wholly within a moved part's pad box grown by 0.5 mm moves with it;
  net-carrying zones in edited builds drop isolated fill islands (KiCad's default; stock's 13 isolated islands are all
  netless and unaffected); the Ci window follows the move.
- **Run 2 passes acceptance L1-L4** ([report](../results/gan/epc90133-board-export-L3a.json)): DRC identical in kind
  and count to stock, pad nets equal, power-loop checks C2-C5 pass, extraction complete.

**Result: below threshold.** Loop L 0.4925 -> 0.4962 nH (+0.75 %), R 4.04 -> 4.02 mohm, capacitor current shares
redistributed (Ci3 and Ci6 up, Ci2, Ci4 and Ci5 down). As declared, no switching run follows. Reading (a hypothesis,
not isolated): in this stacked loop the return current rises to the top through the GND via row under the capacitors,
so moving the capacitor pads without that row does not shorten the vertical loop. The row is blocked by the bottom
capacitors. A worthwhile L3 needs the return vias and the bottom capacitor bank moved together, a larger redesign.
`move_footprint` gained the silk rule after W1 was qualified; L3a's DRC is its check.

### EPC90133 layout search (7 October 2026; plans/layout-search-2026-10-07.md)

Owner instruction: keep searching until a layout candidate is found; substantial rebuilds are accepted. The plan
fixes what counts before any run: a legal board (DRC as stock, pad nets equal, power-loop checks pass), loop
inductance more than 4 % below stock through the same route in the variant judged, and the owner rule (worst-case
overshoot lower, FET loss at most +5 %, Q2 gate peak not higher) under the four driver/package alternatives, plus a
50 ps numerical check.

**Screens (`scripts/epc90133_layout_screen.py`) are invalid.** They filled the return-plane slots on mid-layer 1
(In1) under Q1 and Q2 on EPC's raster: S1 -19 %, S2 -9 %, S4 -54 %, S6 -13.9 %, S7 -8.9 %, S8 -50.7 %. After V8's
legal build gave -12.5 % against S8's -50.7 %, a check found why (recorded retrospectively; `--check-bonding`): inside
each EPC slot the column's vias are joined by a strip of their own net's copper (switch node or VIN), and the fills
touched those strips. 9-54 non-GND vias per screen were bonded to the GND plane, a partial short like S5. No screen
number is an upper bound; the legal builds are this family's evidence.

**Via thinning V6-V8 (`scripts/epc90133_board_export.py`, primitive `remove_vias`).** Every other via is removed in
the slotted non-GND columns under Q1 (x = 18.0, 20.1, 21.9, 23.0 mm; V6), Q2 (x = 19.2, 20.9, 22.7; V7) or both
(V8, 20 of 40 vias). The slots on every inner layer become EPC-size per-via antipads (r = 0.3275 mm), so the
return plane runs between the remaining vias. Run 1 left a thin slit per slot (a keep-out piece cut a chord across
the curved slot outline) and is kept; revision 2 tests containment by area. Run 2: all three are legal (DRC, nets,
power-loop checks as stock); variant A loop inductance against stock through the route:

| Case | Loop L (nH) | Change |
|---|---|---|
| stock (route) | 0.4925 | |
| V6 (Q1) | 0.4717 | -4.2 % |
| V7 (Q2) | 0.4502 | -8.6 % |
| V8 (both) | 0.4311 | -12.5 % |

Loop resistance is unchanged within 0.4 %. A preliminary switching run on A (V8 against stock, four alternatives)
gave overshoot -6 to -14 % and FET loss +1.9 to +3.5 %; the Q2 gate peak rose by 2 mV at 0 pH, failing C2, but A
has no gate loops (its Q2 peak is only about 0.25 V), so the rule is judged on G. Because lower loop inductance
raises Q1's turn-on energy in this model (round 2a), the decisive G run also tries V8 with R80 1.5 ohm and, declared
before any G result, 1.2 ohm (smaller loss increment). V9 (every third via kept) is declared and built; it goes to
B/G only if it beats V8 on A by more than 4 % of stock. Fewer vias also carry the switch-node current to the inner
and bottom layers; that heating is not modelled.

### EPC90133 layout round 2a: thinner power-loop dielectric (5 October 2026)

Plan: plans/layout-round-2-plan.md. Declared at 87b174d before any run. Question: does a thinner top-to-mid-layer-1
dielectric (the power loop's return gap; stock 0.127 mm) meet design round 1's three targets with the stock gate
resistors? `scripts/epc90133_extract.py` gained an opt-in gap override (`A:m1:mid:d<mm>`). The default and
stock-height decks are byte-identical to the previous version. Variant A extractions
(results/gan/epc90133-extraction-layout/): loop L 0.502 nH (0.127 mm, stock), 0.469 (0.100), 0.436 (0.075), 0.401 nH
(0.050). Halving the gap lowers this variant's loop inductance by 20 %: the rest of the loop is lateral. Run 1 of the
extractions wrote the 0.100 mm report, then crashed printing a relative path (log kept in runs/). Switching:
`--study layout`, the same operating point, alternatives, robust rule and assessment as round 1, variant A (ranking
only: no gate loops, not a board prediction).

**Loss-estimator revision 2.** The first run ([report](../results/gan/epc90133-layout-round2a.json), kept) gave FET
losses that jumped from +59 % to -15 % between neighbouring cases. The loss window ended 40 ns after the valley turn-on,
while the switch node was still ringing. FET terminal energy equals loss only if the energy stored in the device
capacitances is the same at both ends of the window, and here it was not: Q2's turn-on segment read 0.77, 3.60 and
0.66 µJ in three neighbouring cases. **Every T3 verdict and efficiency figure from round 1 and from round 2a's first
run is invalid.** T1 and T2 use threshold-defined edge windows and are unaffected, so round 1's "no candidate meets all
three" stands through T2. Revision 2, declared at 6031d30 before any rerun: Q1's second pulse lasts 600 ns, the window
runs to 450 ns after the turn-on, and a settling check requires the window energy at 400 and 450 ns to agree within
2 %. Round 2a rerun ([report](../results/gan/epc90133-layout-round2a-rev2.json),
[assessment](../results/gan/epc90133-layout-round2a-rev2-assessment.json)): all 16 cases usable and settled (0.3-1.4 %).
Round 1 reruns on G with revision 2 (launched 5 October, about 3 h; results/gan/epc90133-design-round1-rev2.json).

Result (change against stock under the four alternatives):

| Gap | Loop L | Overshoot | Eon + Eoff | FET loss |
|---|---|---|---|---|
| 0.100 mm | -6.6 % | -3 to -7 % | +1.3 to +2.9 % | +1.2 to +1.8 % |
| 0.075 mm | -13 % | -6 to -15 % | +2.4 to +6.3 % | +1.2 to +2.5 % |
| 0.050 mm | -20 % | -11 to -23 % | +3.7 to +11 % | +3.1 to +3.8 % |

Verdicts: no gap meets all three. T1 is met only at 0.050 mm, T2 at none, and T3 only at 0.100 mm (within the 2 %
tolerance), where T1 fails. **In this model, lowering the loop inductance raises Q1's turn-on energy.** The loop
inductance takes up voltage while the current rises, and the earlier extraction variants show the same direction (loop
L 0.50 / 0.30 / 0.28 nH / ideal copper: Eon 1.78 / 2.69 / 2.89 / 3.92 µJ, Eoff 1.6-1.8 µJ). The total FET loss rises
too, by about 3 % at 0.050 mm. So, with these target definitions, overshoot and loss pull against each other for
loop-inductance changes as they do for gate resistors. In absolute terms the loss changes are small (0.05 W, about
0.02 efficiency points at 240 W), but the targets are strict "not higher". Plan update: the owner decides whether T2
should become total loss and whether the tolerance should allow small increases. Variant A ranks only. Its gate loops
and inner layers are missing, and its loop L (0.50 nH) is about twice G's, so the size of these changes on the board
would differ.

### EPC90133 layout round 2b: added return vias, and the geometry-edit layer (5 October 2026)

`scripts/epc90133_board_edit.py` edits the rasterized layers in memory; the Gerber files are never touched.
`scripts/read_epc90133_geometry.py` now has `derive(grids, holes)` split out of `load_board`, and its via bonds,
probes, counts and labels were verified identical. An added plated via gets a pad where it sits on its own net's
copper and an antipad where other copper is within the clearance. Rules: R1 drill at least 0.198 mm (the board's
smallest); R2 at least 0.52 mm to any hole (the smallest via spacing in the power area); R3 no component pad (paste)
nearby; R4 bonds on at least two layers; R5 no net merges and no split islands, re-derived after each edit; R6 no
antipad in VIN or SW copper. The 0.125 mm annular ring and 0.2 mm clearance are assumptions (fab rules open).
`scripts/epc90133_extract.py --edits <json>` applies a checked edit list and records it with hashes. Tests:
tests/test_epc90133_board_edit.py (6).

Declared at e07063a. The candidate: every GND via the rules accept on a 0.25 mm grid over the loop area, applied
greedily. Revision 1 (before R6, kept as devices/epc/layout-edits/vias-gnd-greedy-r1-cuts-power-path.json) accepted
22 vias. Most sat between the FETs, where their antipads perforated the top-layer switch-node copper, the main path
from Q1's source to Q2's drain, and the A mesh lost Q1's source connection. R6 was added in response. Revision 2
accepts only 4 vias, all about 3.5 mm left of Q2. Their extraction on A: loop L 0.5016 nH against 0.5017 nH for stock
(-0.02 %). The declared switching runs were skipped because a 0.02 % network change cannot move any target beyond its
tolerance (a deviation from the declaration, recorded here).

Reading: **at the board's own via spacing, and without perforating the power path, the published layout leaves
essentially no room for more return vias in the loop area.** EPC's layout is already saturated with vias there.
Further loop-inductance reduction would have to come from capacitor placement (L3) or the stackup (round 2a), and in
this model both raise the turn-on energy (round 2a).

### EPC9165 board files and probe access (deferred second-board candidate)

Owner, 1 October 2026 (plan section 9, item 10): audit EPC9165's published files and locate gate and switch-node
probe access before any purchase. Files are recorded in `devices/epc/epc9165-sources.json` (BOM and Gerbers fetched
directly; the board page refuses automated fetches). `scripts/audit_epc9165_board_files.py` (declared before its
first run; [report](../results/gan/epc9165-board-audit.json)) and `scripts/assess_epc9165_probe_access.py`
(post hoc; [result](../results/gan/epc9165-probe-access.json)).

Runs: run 1 passed its checks but is kept as failed
([report](../results/gan/epc9165-board-audit-run1-failed.json)): it read the FETs' nets from top copper, while the
EPC2302s are on the bottom side, so it never saw the gate pads. Run 2 (the one fix run; a crash while writing its
report was fixed by a cast) takes the FET side from the paste layers: 7 bottom paste pads inside every FET outline,
none on top. Its heatsink-side rule sampled the mask outside the small (about 1.35 mm) bottom openings at the
mounting holes and returned no side, so its "inside heatsink" flags are unusable. The post-hoc assessment records
the mask at the hole centres (open on the bottom at all four holes, on top at none), takes the heatsink to be on
the bottom, and re-reads the same contacts; their counts match run 2.

Document consistency:
- **Board identity is unresolved.** The Gerbers are B5309 Rev 1.0 ("EPC9165B", files dated 19 August 2021); the
  schematic in the guide is B5284 Rev 1.0 (2022). Which one EPC ships, and which produced the guide's waveforms, is
  not established; a purchased board's silkscreen settles the first.
- 8 copper layers, matching the stackup (62 mil). MPQ1918 in BOM and schematic. Every fitted BOM part is in the
  layout except the heatsink-kit spacers SO1-SO4; the layout adds unfitted footprints (J1_F1/F2, J1_CS*, R4/R5_CS*),
  the controller edge connector J61 and S5-S9.

Geometry (assembly page placed on the drill file within 0.011 mm; checks G1-G4 pass):
- **The four EPC2302s and their gate resistors are on the bottom, under the heatsink** (Wakefield 567-94AB on 1 mm
  spacers, footprint 57.9 x 20.7 mm on mechanical layer 13). The two phases' FET pairs sit at x 38-46 and 66-74 mm.
- **Gates: no access with the heatsink fitted.** Each gate net has three exposed contacts, all on the bottom under
  the heatsink: the FET's gate pad and the gate-side pads of its two 0402 gate resistors, 1.5-2 mm away. There is no
  gate-probe footprint (EPC90133 has the J1/J2 MMCX footprints). Measuring a gate needs the heatsink removed, which
  limits operation to thermally light conditions such as double pulse.
- **Switch node: reachable on the top side close to the FETs.** Each phase's switch-node net has top-side contacts
  1.1-2.2 mm from its FETs (the largest a 2.8 x 2.65 mm pad 1.5 mm away; not yet tied to a designator), then the
  output inductor's terminal pad about 17 mm away. No connector footprint exists, so a probe would be soldered in;
  the nearest ground contact for its return was not assessed.
- **The two 100 mil headers (J1_F1/F2) are not on the switch node**: none of their pins shares a net with any FET.
  The guide calls J1_F1 a voltage-loop-gain injection point.
- Not determined: which FET of each pair is the high side, and the drivers' side.

Consequence for the comparison (plan section 9, item 10): a switch-node comparison with the heatsink fitted is
feasible with a solder-in probe; gate-voltage data, which the hardware plan requires at every switching point
(E3), are only possible without the heatsink, so a matched comparison would be double-pulse, not continuous
operation at the guide's currents. These are readings of EPC's published B5309 files, not of a physical board.

### Agent-workflow milestone 1: a bounded, scored agent run

Plan section 10, item 7, advanced at the owner's request (1 October 2026). `scripts/agent_milestone.py` (declared
before any run; [result](../results/gan/agent-milestone-1.json)) gives an agent and a plain-script baseline the
same task. Given a manifest of the Fig. 9 comparison's inputs, with expected hashes taken from the committed
comparison report, the task is to check the inputs (K1 file hashes, K2 the comparison script's hash, K3 the
digitized figure's own checks, K4 the switching reports' completeness), then either run the existing comparison
into a sandbox or stop with the reason. Each agent is a fresh subagent on a cheaper model, given only the task
card. Run A has clean inputs. In run B, one digit inside a trace of one switching report is changed, so the
file still parses and a careless run would produce plausible numbers.

Before any agent run, two changes were made and recorded. The baseline's K3 first read a non-panel entry of the
figure's checks. K4 first required a completeness field that the two oldest switching reports predate, which
made every correct run stop. K4 now accepts such a report if every case carries its usable flag. The unused
sandboxes were regenerated.

| Run | Outcome | Scores (S1 outcome, S2 containment, S3 interventions, S4 caveat) | Wall time | Tool calls | Tokens |
|---|---|---|---|---|---|
| baseline (plain script) | completed | — | 7.6 s | — | — |
| A, agent, clean inputs | completed; comparison identical to the baseline's | all pass | 46 s | 9 | 54k |
| B, agent, corrupted input | stopped at K1, named the file, no comparison written | S1-S3 pass (S4 not applicable) | 28 s | 5 | 51k |

The milestone passes as declared. The containment score compares the repository's git status before and after; it
cannot see changes to git-ignored files (including another sandbox under runs/) or further changes to a file already
modified, so it supports "no new git-status changes detected", not a complete absence of writes outside the
sandbox. Nothing indicates that an agent wrote outside its sandbox. Its scope is narrow: one task, one run each, so there is no reliability
statistic. The agent made no engineering decision; it checked declared artifacts, ran an existing script and
stopped correctly on a corrupted input. One unscored imprecision: run B's report says the volt scale fails in the
rising panel, while it fails in both. The baseline is six times faster and costs nothing per run. The agent's
value would lie in tasks the scripts do not already encode. Next steps would be repeated runs for a failure rate,
further fault types (a failed upstream check, a missing file, a changed evaluator) and a task that requires a
decision, such as preparing a declared switching case from a change request with its numerical checks.

### Agent-workflow milestone 2: repeated runs and fault coverage

Declared before its runs in `scripts/agent_milestone.py` ([result](../results/gan/agent-milestone-2.json)). The task card,
checks and scores are the same as in milestone 1. It adds three clean runs and four fault kinds, each with the check that
must stop it:
- a wrong evaluator hash, which must stop at K2;
- a missing switching report, which must stop at K1;
- the figure record's falling-panel time scale set to fail, with the manifest updated, which must stop at K3;
- a report set to `"complete": false`, with the manifest updated, which must stop at K4.

Before the agent runs, the plain baseline crashed on the missing-file fault (it read the absent file in K4); that was
fixed and is recorded as a finding about the hand-written script. A scoring-only bug (a relative results path) was
fixed after the runs and before the recorded scores.

| Result | Count |
|---|---|
| clean runs completed, comparison identical to the baseline, volt-scale caveat reported | 4 of 4 (with milestone 1's A) |
| fault runs stopped at the expected check, file named where there is one, no comparison written | 5 of 5 (with milestone 1's B) |
| new git-status changes outside runs/ detected, interventions | none |
| per run | 21-72 s, 5-10 tool calls, 50-56k tokens (cheaper model); baseline under 8 s |

Within this one task family the agent behaved as specified every time. Nine runs are too few for a useful failure
rate, and the agent still made no engineering decision; the next step is a task that requires one, judged against
a declared expected answer. The task card permits repository reads and the operator's fault description is
reachable, so these were not blinded fault tests.

**Baseline fixes after the audit at 75d6f35 (2 October 2026).** The plain baseline, not the agents, had three more
faults: it reported `completed` whatever the comparison's exit code and output; it crashed on a missing figure or a
malformed switching report; and its K3 passed a figure record whose checks named no panel. Completion now needs a
zero exit, a readable comparison holding its result keys and the summary file (otherwise `failed`, with the captured
output); both panels are required by name; unreadable inputs become structured stops; the manifest's structure (entries, bare file names, hashes, kinds,
one figure) is validated before any entry is used (tests/test_agent_milestone_baseline.py). The recorded milestone outcomes stand: the scorer compared the agents'
outputs with the baseline's comparison directly, and the faults above were not among the declared fault kinds.

### E2E-0 pilot: the simulation workflow end to end through stage handoffs

Declared before its runs in `scripts/e2e_pilot.py` (2 October 2026; [result](../results/gan/e2e-pilot.json)) after an
external review of the end-to-end plan, which reduced it to this pilot. **Non-blind.** Its endpoint is a simulation
assessment against QSG Fig. 9; it is not Stage 3 closure. The stages hand off through frozen records
(`src/circuit_tools/handoff.py`: I-1, I-2 and the assessment, with complete/provisional/incomplete/failed/rejected_input
states and exception inheritance). An independent checker (`scripts/e2e_check.py`) rehashes cited files, recomputes
every required check, compares predictions with the report and requires stops to be warranted. Configuration:
EPC2302 Stage 1 benches, extraction A:m1:mid, the switching sensitivity study on A (nine cases), then the Fig. 9
comparison. Each stage ran in a copied workspace without results, docs or plans, one fresh subagent per stage on the
operator's frontier model, given only its stage card.

- **Reference.** Run 1 stopped on a driver bug: it treated exit status 2 (report written, declared check failed) as
  a failed step. It is kept. Run 2 completed in 21.6 min of compute; all three records are provisional and the
  checker found no problems.
- **Clean run C1.** It matched the reference exactly: statuses, every check outcome, all 63 predictions, loop L
  0.502 nH and the per-case Fig. 9 verdicts. All 12 reference assumptions were named with equal values, plus 23
  more. The checker passes all three records. Stages took 3.6, 25 and 4.5 min, with 15/36/22 tool calls and
  94k/121k/132k tokens. No interventions or retries.
- **Fault run F1** (C1's Stage 1, then the EPC2302 model's k2 changed, the archive rebuilt and both source records
  updated, so every script's own check passes). Stage 2 rejected its input before any step: both integrity checks
  failed, nothing was predicted and no protected file was touched. The assessment rejected in turn. The checker
  passes both stopped records.
- **Claims review** (operator, non-blind). All 18 C1 claims were warranted, with no overreach or underclaim. The
  assessment's needed measurements cite hardware-plan items (E7, E8, J1/J2, B1506A) that no artifact in the run
  supports, and some sentences echo AGENTS.md almost verbatim.
- **Containment.** Every subagent receives the repository's AGENTS.md as project instructions, so the answers were in
  the agents' context whatever the workspace held. The transcript audit found no tool call touching the repository
  outside the workspaces. One stage wrote a scratch note outside its allowed folder; the cards never named that
  folder.

Reading: agents on a frontier model can execute this workflow and hand it off through declared records, and they
stopped on an upstream change that the scripts accepted. Consistency with the reference checks execution, not
engineering truth (same models, assumptions and helpers). The pilot does not show judgement on unseen material. A
blind test needs a separate session in an isolated directory with only permitted inputs, a frozen reference method,
and an independent review of geometry, ports, pinout, driver and benchmark applicability. Owner decision, 5 October 2026: agents may read AGENTS.md and the docs. In real use the agent runs with this context and all tools, so workflow runs are tested that way and no isolated session is required. Judgement is tested on material whose answer is not written down anywhere: frozen predictions scored against new measurements (hardware plan, 'Frozen prediction record'). Per the review, a second
target waits for the owner's assessment of value, interventions and cost. The agents took about 33 min of wall time
and 347k tokens; the scripts alone took 22 min and no tokens.

### KiCad groundwork (G5 preparation)

Owner, 1 October 2026: prepare the route to our own board design, without design work that waits on measurements.
- **KiCad 10.0.6** is installed for the current user from the official installer (checksum matched the published
  SHA-256; a winget download stalled, so the file was fetched directly into the git-ignored `.tools/kicad`).
  `kicad-cli` runs.
- **EPC's own KiCad library** (EPC_2024Q4a; source recorded in `devices/epc/epc-library-sources.json`) loads in
  KiCad 10: `kicad-cli fp upgrade` converts all 47 footprints, and the EPC2302 footprint (D0606F_100V) renders. Its
  seven pads sit at the datasheet's 0.85 mm pitch with the datasheet's pinout; mask and paste are custom polygons.
  EPC's newer Altium library (2026 Q3b) is also recorded. Using EPC's published footprint avoids drawing one by hand.
- **Route, still the owner's choice (plan section 3):** editable Altium board files would need an EPC request, which
  the owner has ruled out, so the remaining routes are re-entering the schematic (the transcribed power stage in
  `devices/epc/epc90133-schematic.json` is a start) with EPC's library footprints, or using the Gerbers as geometry
  reference only.
- Not done: comparing D0606F_100V geometrically with the land patterns on EPC90133 and EPC9165; a uP1966E footprint
  (not in EPC's library); any schematic or layout.

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
- **Case H, a 3D board-like check (1 October 2026, `scripts/fastercap_board3d_check.py`, declared before its run;
  [result](../results/gan/fastercap-board3d-check.json)): failed and invalid in its 3D part.** It modelled a thin strip
  over a finite FR-4-like slab in 3D and compared it per metre, through two strip lengths, with the same cross-section
  in 2D, using a declared refinement sequence.
  - H3 fails: the 2D reference changes by 15.8 % between -a0.005 and -a0.001 (123.2 pF/m at -a0.001, matching case
    G). Another case where the coarser setting stopped early.
  - H1 and H2 were not evaluated: the -a0.002 run on the 4 mm strip exceeded the declared 3 h limit.
  - The 3D Maxwell matrices are unphysical (negative diagonal, positive off-diagonal terms, less capacitance for the
    longer strip), so the derived 178 pF/m is not an accuracy result.
  - A post-hoc diagnostic (runs/fastercap-h-diag, not a declared check) shows where the fault is. The same strips
    without the slab give a physical 3D matrix, and the 2D air value reproduces case G's 37.75 pF/m. So the fault
    lies in this 3D dielectric-interface input, although it uses the same syntax and reference-point convention as
    case C, whose accuracy comparison passed (case C as a whole failed its mesh check, 3.3 % against 0.5 %). The
    exact cause is not isolated, and the air diagnostic does not rule out a solver issue triggered by a dielectric.
    The air 4 mm run was stopped at 5.7 GB of the 8 GB WSL limit, before it gave a result.
  - Validity gate (2 October 2026, after the audit at 75d6f35, which reproduced `all_pass` from synthetic
    negative-diagonal matrices): the check script now requires every matrix to be square, finite, reciprocal,
    positive definite, with positive diagonal, non-positive off-diagonal and non-negative row sums (relative
    tolerance 1e-3) before it forms a pair capacitance, C' or a pass; invalid matrices are kept raw with their
    reasons (tests/test_fastercap_validity.py). The stored report is not rewritten. A separate post-hoc assessment
    bound to its hash (`scripts/assess_fastercap_board3d.py`,
    [result](../results/gan/fastercap-board3d-assessment.json)) records the disposition: all five 3D matrices
    invalid (non-positive diagonal, positive off-diagonal, not positive definite), both 2D matrices valid, derived
    C' unusable, declared verdict failed and unchanged. The assessment binds by hash the gate module it imports and
    that module's helpers (`scripts/fastercap_known_answer.py`); the check's future reports bind those helpers too.
  - FasterCap stays unqualified for 3D board geometry. Before any board capacitance extraction, the 3D dielectric
    description needs its own small known-answer check (for example a parallel-plate capacitor partly filled with
    dielectric). Nothing depends on this now.
- **Runner fixes after an external audit (30 September 2026), no case or tolerance changed.** A timeout now stops
  only that run's FasterCap process (by its recorded PID, checked to still be FasterCap), not every process of that
  name on the shared host; an unknown or empty `--only` is rejected instead of reporting `all_pass` over no cases;
  the report is checkpointed after each case and records the requested cases and whether all of them ran. Checked
  by a forced 3 s timeout on case C (its process was stopped, the report shows `complete: true, all_pass: false`)
  and by rejected `--only nosuch` and empty `--only`. The recorded eight-case results are unaffected.
