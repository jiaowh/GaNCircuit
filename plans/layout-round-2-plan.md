# Layout round 2: plan for 6 October 2026

**Current status (6 October 2026; read first).** The three-target formulation below is historical. The owner's
decision of 5 October 2026 makes overshoot the single objective, with FET loss at most 5 % above stock and the Q2 gate
peak not above stock as constraints (round 3 specification below; result: R80 1.5 ohm is the best tested candidate,
docs/build.md "design round 3"). The fabrication route is track R: a KiCad 10 reconstruction from EPC's Gerbers and
layout PDF, which reproduces the saved geometry exactly. KiCad's zone refill does not reproduce EPC's copper (audit at
0f07a6a: 1-2 % area change in the power/gate window), so an edit/refill workflow must be qualified before any G5
geometry edit. Sections that state three targets or an undecided route are kept as written on 5 October.

Draft, 5 October 2026. For the owner and the working session. Nothing here is declared yet: each step's
declaration goes into its script's docstring and is committed before that step runs, as usual.

## Why a layout round

Round 1 (docs/build.md "design round 1") changed only parts on the stock board. Every gate-resistor change cut the
overshoot but raised Q1's switching energy and the FET loss, so no candidate met all three owner targets. In the
model, the way to get lower overshoot without a slower edge is a smaller power-loop (and common-source) inductance.
That is a geometry change. Round 2 asks:

> Which manufacturable geometry changes to the EPC90133 layout meet all three targets, overshoot lower, Eon + Eoff
> not higher and estimated 48 V -> 12 V efficiency not lower, with the stock gate resistors, under the same four
> unresolved alternatives and the same robust rule as round 1?

The targets, operating point, alternatives, robust rule and efficiency estimate are reused unchanged from round 1.
That keeps the two rounds comparable and stops the rule from moving after results come in.

## What we know going in

| Fact | Value | Source |
|---|---|---|
| Loop inductance by extraction variant | A 0.50 nH, B 0.28 nH, G 0.26 nH | build notes, extraction |
| Overshoot against loop inductance (13.8 V point, old bench) | A 55 V, B 36 V, ideal copper 2 V | build notes, test 1-4 |
| Top to mid-layer-1 dielectric (the power loop's return gap) | 0.127 mm (5 mil) | power-loop report |
| Input capacitors Ci1-Ci7 | row at y 33.8-35.3 mm; Q1 centre at y 31.0, Q2 at y 26.0 | power-loop report |
| Plated vias of VIN/SW/GND in the extraction window | 189, in 111 groups | power-loop report |
| Extraction cost | A about 90 s, B about 2 h, G about 3.4 h | extraction runs |
| Switching cost per case at 100 ps (with its timing run) | A about 1 min, G about 20 min | round 1 logs |
| Known stall | stock, step driver, 50 pH stalls at 100 and 50 ps at the 12 V point | round 1 fix runs |

Variant A (top layer and mid-layer 1, input capacitors only) has no gate loops and no inner layers. It can rank
changes to the power loop, but not to the common-source or gate routing, and its absolute numbers are not G's.

## Found on 5 October, after this plan was drafted

1. **In the model, lower loop inductance raises Q1's turn-on energy.** Earlier runs: loop L 0.50 / 0.30 / 0.28 nH /
   ideal copper gives Eon 1.78 / 2.69 / 2.89 / 3.92 µJ, with Eoff nearly unchanged (1.6-1.8 µJ). The loop
   inductance takes up voltage during the current rise (a turn-on snubber); the stored energy then rings out and is
   dissipated elsewhere, largely outside the standard Eon window. Round 2a (stackup on A, rev 1) confirms it: a
   thinner gap cuts the overshoot (T1 met only at 0.050 mm, -11 to -23 %) but raises Eon by 3-21 %, so T2 fails.
   **With Eon + Eoff in the standard windows, T1 and T2 pull against each other for loop-L changes as well as for
   gate resistors.** Proposed for the owner: replace T2 with total FET loss per period (the T3 quantity), which
   counts the ring energy wherever the FETs dissipate it, or keep T2 and accept that no change in either family
   meets it.
2. **The loss estimate (T3) of round 1 and round 2a rev 1 was invalid.** Its window ended during the ringing, so
   terminal energy included a stored-energy swing of several µJ. Estimator revision 2 (window to 450 ns after the
   turn-on, settling check) is declared. Round 2a reruns with it on 5 October; round 1 reruns overnight on G.

3. **Status at the end of 5 October.** Steps 1-5 ran early. Round 2a (stackup): no gap meets all three targets;
   with the corrected loss estimator, FET loss rises 1-4 % as the gap shrinks. Round 2b (vias): the geometry-edit
   layer works (6 tests), but under the board's spacing and without perforating the power path only 4 vias fit, and
   they change loop L by 0.02 %. Round 1 is rerunning on G overnight with the corrected estimator
   (results/gan/epc90133-design-round1-rev2.json; assess with `scripts/assess_epc90133_design.py
   results/gan/epc90133-design-round1-rev2.json --output results/gan/epc90133-design-round1-rev2-assessment.json`).
   **First decision for 6 October:** with every change tried so far, the overshoot and loss targets pull against
   each other in this model. Either redefine the targets (for example a loss tolerance, or total loss in place of
   Eon + Eoff), or accept the trade and freeze the best candidates as predictions for the board measurements. Then
   choose between L3 (capacitor placement, hard, the last loop-L lever) and track R (editable design).

## Owner decision, 5 October 2026 (evening): one objective, overshoot

The owner adopted Claude's recommendation. For this evaluation board, overshoot is the objective, because it sets
how much bus voltage the board can use safely (EPC2302 rated 100 V; the uP1966E PHASE pin only 85 V absolute
maximum; the board is rated 80 V in). Efficiency becomes a constraint, and the separate Eon + Eoff target is dropped
(it is part of the loss).

**Round 3 (to declare in the script before running, 6 October):**
- Objective: minimise the switch-node overshoot above the bus at Q1's turn-on, at 48 V -> 12 V, 20 A, 250 kHz.
- Constraints, under all four alternatives ({ramp, step driver} x {package source L 0, 50 pH}):
  C1 FET loss per period (estimator revision 2, settled) at most 5 % above stock (about 0.1 W, 0.04 efficiency
     points at 240 W);
  C2 Q2's die gate peak during Q1's turn-on not above stock's (false-turn-on margin);
  C3 only changes allowed by the board-edit rules or by part swaps on the stock board.
- A candidate is ranked by its worst-case overshoot over the four alternatives, among candidates that meet C1-C3
  under all four.
- Order: (1) assess round 1 rev 2 (overnight G run: R80 1 / 2.2 / 3.3 ohm with the corrected loss estimator);
  (2) R80 sweep on G to find the largest R80 that keeps C1 (for example 1.5, 1.8, 2.7 ohm, chosen from (1) and
  declared before running); (3) only if a layout lever could beat the R80 result within C1, the stackup gap
  combined with the chosen R80 (A ranks, G confirms).
- The result is a provisional simulation prediction for the purchased board (R80 swap at experiment E4); it becomes a
  frozen prediction only in the frozen prediction record at the approved conditions.

**Round 3 done (5 October 2026, evening; docs/build.md "design round 3").** Round 1 rev 2: every candidate fails C1
(R80 2.2 ohm +5.5 to +9.0 %, 3.3 ohm +10 to +14 %, 2.2 ohm with 7.5 ns +3.0 to +6.3 %). Round 3 (R80 1.2/1.5/1.8 ohm):
**R80 1.5 ohm is the best tested candidate**, the only one that meets C1 and C2 under all four alternatives. Worst-case overshoot
25.1 -> 16.8 V (-33 %), FET loss +2.4 to +4.3 %, Q2 gate peak lower in all four. 1.8 ohm misses C1 by 0.1 point;
1.2 ohm cannot outrank 1.5. Step (3) was not run: adding round 2a's figures (a different model) suggests, without a simulated verdict, that a
gap change would not beat 1.5 ohm within C1, and it needs a new board. The improvement shrinks to 4-11 % if the
package source inductance is near 50 pH; stock-board measurements (E3) can constrain that, and the swap (E4) tests
the predicted response. Evaluator hardened after the audit at 5d72e4e (revision 4, docs/build.md 'design round 3');
the selection is unchanged. Solver note: trapezoidal stalls are
frequent on this bench, and Gear (checked equal within 0.05 %) is the declared fallback.

## Candidate changes, balancing effort and effect

| # | Change | Expected effect on loop L | Effort | Tooling needed | Manufacturability question |
|---|---|---|---|---|---|
| L1 | Thinner top to mid-layer-1 dielectric: 0.127 (stock), 0.100, 0.075, 0.050 mm | moderate; the vertical part of the loop scales with the gap, the lateral part does not | **easy** | a per-layer height override in the extraction (layer mid-planes come from the stackup) | which prepregs the fab offers; the stackup must stay symmetric or be accepted as is |
| L2 | More return vias next to Q2's source and the Ci ground pads (fill free space in the existing via groups) | small to moderate; the 189 vias already carry the return | **medium** | geometry-edit layer: add a via (drill + pads on each layer it connects) with clearance checks | drill size and spacing rules from the fab notes (vias at most 0.010 in are filled and plated over) |
| L3 | Input capacitors moved closer to the FETs (shift the Ci row toward Q1, or add a Ci pair beside the FETs) | potentially the largest: shrinks the loop area | **hard** | geometry-edit layer: move pads and the copper under them; re-check nets and clearances | placement against the gate driver and other parts; assembly rules |
| L4 | Kelvin or separated source return for the gate drivers (lower common-source coupling) | changes the excitation, not the loop L; may lower Eon | **hard**, and only on G | geometry-edit layer on G's gate nets | routing space near the driver |

**Balance:** start with L1, which is the cheapest and gives the first answer. Build the geometry-edit layer once
and use it for L2 first, the simplest edit, which also tests the tool. Attempt L3 only if L1 + L2 fall short. L4
needs G at every step and is costly, so it is listed but not scheduled for tomorrow.

Before any compute, a quick bound (step 1) tells us how much loop-L reduction the targets need. If L1's whole
range cannot deliver it even optimistically, we skip straight to L2/L3.

## Schedule for tomorrow

| Time | Step | Output | Stop or go |
|---|---|---|---|
| 09:00-09:30 | **0. Agree the round.** Owner confirms the question, the reuse of round 1's rule, the candidate list and the budget below. Owner answers the manufacturability questions or marks them "assume and record". | decisions recorded in this file | go when confirmed |
| 09:30-10:00 | **1. Required reduction (no solver).** From existing results, fit overshoot and Eon against loop inductance (A, I, B, ideal copper; round 1 stock). Estimate the loop-L reduction at which T1 (at least max(1 V, 10 %)) holds without R80 changes. | number with its basis, in the build notes | if L1's best case cannot plausibly reach it, start step 3 sooner |
| 10:00-11:00 | **2. Stackup override (code + check).** Add an opt-in layer-height override to `scripts/epc90133_extract.py` (default decks verified byte-identical, as for round 1). Known-answer check: the A extraction at stock heights reproduces 0.50 nH exactly. | code, test, declaration of round 2a | go if the reproduction is exact |
| 11:00-12:30 | **3. Round 2a: L1 on A.** 4 heights x A extraction (about 6 min in total), then switching under the 4 alternatives at the 12 V point (about 16 short runs). Assess with round 1's rule against A-stock. | report + assessment | if no height meets all three on A, L1 alone is not the answer |
| 13:30-16:00 | **4. Geometry-edit layer.** Raster edits applied before meshing: add via (drill, pads, layer span), with rule checks (clearance to other nets, drill size, keep-out of component pads) and a net check after the edit. Tests: an edit that breaks a rule is refused; adding a via to an existing group changes connectivity only where intended. | `src/circuit_tools/` module + tests | go if the tests pass |
| 16:00-17:00 | **5. Round 2b: L2 on A.** 2-3 via patterns (declared before running), alone and combined with the best L1 height. Same assessment. | report + assessment | pick at most two candidates for G |
| 17:00-17:40 | **6. Overnight launch.** The best one or two candidates on G (about 3.4 h each; at most two heavy WSL jobs at once, launched with Start-Process). Their switching cases run the next morning. | launch records | |

Budget for tomorrow: at most 12 A extractions, at most 40 A switching cases, at most 2 G extractions overnight.
Profile the first case of each kind before committing the rest, and set time limits from those profiles.

## Parallel track R: editable design reconstructed from the Gerbers

Needed only to fabricate a redesigned board, not for the simulation. It resolves owner decision 1 without an
Altium request.

1. Copper: KiCad GerbView exports each copper layer into a `.kicad_pcb` as tracks and polygons (no nets).
2. Parts: footprints from EPC's KiCad library (installed; EPC2302 = D0606F_100V) and standard libraries, placed
   from the layout PDF's pad tokens (designator and pin per pad, e.g. PAJ9001 = J90 pin 1) and checked against
   the BOM.
3. Nets: assigned from our own connectivity extraction (scripts/read_epc90133_geometry.py) and checked against
   the transcribed schematic (power stage, gate driver, input logic; the remaining sheets need transcribing).
4. Pours become KiCad zones with the same net and clearance; vias carry their drill sizes from the drill file.
5. **Acceptance: round trip.** The reconstructed design's exported Gerbers and drill file must match EPC's originals
   layer by layer (raster difference and drill-by-drill comparison) within a stated tolerance, and KiCad's design
   rule check must pass or every exception must be explained. Only a design that passes is used as a base for edits.

Effort: about one to two days. Terms: the result is a derivative of EPC's layout; internal design work only,
not published or shared until EPC's reuse terms are checked.

**Done, 6 October 2026** (docs/build.md "track R"). All five steps pass their declared checks; failed runs are
kept. Deviations from the steps above:
- footprints are built from the board's own pads rather than library footprints;
- part positions and sides come from the layout PDF's hidden pad tags and EPC's bookmark netlist, decided by
  netlist consistency on the copper;
- copper pours are zones holding EPC's exact fills.

Result:
- all 14 Gerber layers and 445 drills round-trip exactly;
- KiCad DRC finds 0 shorts and 0 unconnected items, with EPC's 5.91 mil clearance;
- remaining items are explained: EPC's outline drawn into every copper Gerber, SO3's ringless 3 mm hole, EPC's
  silkscreen at the edge, and gaps at EPC's rule within 1 um.

Board file: vendor/epc/epc90133/reconstruction/epc90133.kicad_pcb (git-ignored).

## Rules that carry over

- Declare before running: candidates, rule and budget in the docstring, committed and pushed.
- Compare like with like: a candidate is compared with stock in the same variant (A with A-stock, G with G-stock).
  A ranks candidates; G confirms them. An A result is never reported as a board prediction.
- A target is met only under all four alternatives. One failure means "not met"; a missing case means
  "undetermined", never "met".
- Results become frozen predictions for a redesigned board once recorded. They cannot be validated without fabricating it. The
  stock-board measurements (E1-E4) still decide whether the model's trends can be trusted.
- Keep failed and stalled runs. Do not tune the vendor model. Never kill processes by name, and keep the host's
  other project in mind.

## Decisions needed from the owner

1. **Fabrication route** (decided 6 October 2026: track R; the paragraph below is the 5 October text). A redesigned board needs editable design files. We have Gerbers only; KiCad 10 and EPC's
   KiCad library are installed, but the route is undecided (no Altium request, under the no-inquiry decision).
   Tomorrow's work does not depend on it; a fabricated test does. Gerbers are editable text, but they hold
   only flattened shapes per layer (no components, nets or design rules). Small changes (stackup, added vias)
   could be made as checked Gerber edits: every affected layer, mask and drill file, with our own clearance and
   net checks. Moving capacitors or rerouting changes copper, mask, paste, silkscreen and placement together, and
   pours do not reflow, so those changes belong in a real design tool (KiCad import as graphics, then a manual
   rebuild). The simulation edits the rasterized layers in memory and never touches the Gerber files.
2. **Manufacturing constraints.** The fab's available prepreg thicknesses, minimum drill and annular ring, and
   whether the stackup may change. Without answers, each round records its assumption.
3. **A-ranking.** Whether ranking on A and confirming only the best on G is acceptable (recommended: yes, on cost).
4. **Common-source routing (L4).** Whether it is worth G-only compute later, given that the round 1 trade-off
   already involves common-source coupling.

## Not in scope tomorrow

Layout changes outside the power and gate loops, new parts or a different FET, thermal design, and any
energized measurement (still waiting on the equipment inventory).
