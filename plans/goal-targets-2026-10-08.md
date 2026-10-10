# Goal targets from the owner's execution template (8 October 2026)

Source: the owner's "AI Agent Execution Template simple version.docx" (repository root, untracked), received
8 October 2026. It replaces the 5 October owner rule (overshoot as the single objective, FET loss at most +5 %,
Q2 gate peak not above stock) as the design target. Bracketed template values are the owner's; `[x]` fields are
still unfilled and are listed under open inputs. Nothing here is a hardware limit or a safe envelope.

## What changes against the current direction

| Item | Previous rule (5 October) | Template |
|---|---|---|
| Objective | overshoot only; loss and Q2 gate as constraints | thirteen goals S1-S13, all must pass |
| Allowed changes | layout and gate-resistor values (R80) | copper, vias, component positions on the parasitic paths; topology, schematic and **BOM fixed** |
| Overshoot | lower than stock | <= 20 % of VIN (9.6 V at 48 V) **and** at least 10 % lower than baseline |
| Losses | FET loss at most +5 % | Eon+Eoff 10 % lower; efficiency +0.3 points |
| Corners | four driver/package alternatives | VIN 40-60 V, load 0-100 %, parasitics +/-10 % |
| Process | declared studies, assessor | approval after the baseline and before releasing D1; at most 30 iterations; iteration_log.csv |

Consequence: a fixed BOM excludes gate-resistor changes, so V8+R80-1.3 (the lead candidate under the 5 October
rule) is out of scope. Its remaining completion runs are paused, not run. V8 (thinned power-loop vias) is a
permitted geometry change.

## Baseline against the goals (existing G search runs, no new simulation)

Source: results/gan/epc90133-search-G.json (G-m1-mid through the KiCad route, design operating point
48 V, Ia 28.2 A / Ib 11.8 A, which is the template's 48 V to 12 V, 20 A, 250 kHz, 2.2 uH point, 100 ps, Gear).
"Ls50" is the assumed 50 pH package source inductance (owner default of 7 October); "Ls0" is the reported
alternative. ramp/step are the two driver forms. Efficiency is FET-only (estimator revision 2).

| Case | Vpk V | Overshoot V (% VIN) | tr ns | tf ns | Eon+Eoff uJ | Q2 gate peak V | Eff. % |
|---|---|---|---|---|---|---|---|
| stock ramp-Ls50 | 59.3 | 11.1 (23.2) | 1.68 | 4.18 | 5.58 | 1.94 | 99.14 |
| stock step-Ls50 | 59.0 | 10.8 (22.5) | 1.79 | 4.22 | 5.78 | 1.66 | 99.14 |
| stock ramp-Ls0 | 72.4 | 24.2 (50.5) | 0.88 | 4.21 | 5.10 | 1.98 | 99.19 |
| stock step-Ls0 | 64.1 | 15.9 (33.2) | 1.05 | 4.28 | 5.43 | 1.40 | 99.17 |
| V8 ramp-Ls50 | 59.5 | 11.3 (23.6) | 1.75 | 4.18 | 5.63 | 1.85 | 99.14 |
| V8 step-Ls50 | 59.0 | 10.8 (22.4) | 1.83 | 4.23 | 5.82 | 1.59 | 99.14 |
| V8 ramp-Ls0 | 68.1 | 19.9 (41.4) | 0.92 | 4.23 | 5.23 | 1.53 | 99.17 |
| V8 step-Ls0 | 61.1 | 12.8 (26.8) | 1.10 | 4.31 | 5.50 | 1.11 | 99.17 |

Reading (simulation sensitivities, model limits as in AGENTS.md: gate-charge-dependent times and losses are
unvalidated):

* S1 Vpk <= 80 V: stock and V8 pass in every case.
* S2: stock is above 20 % of VIN in every case; V8 is not 10 % lower at Ls50 (+1.8 % / -0.3 %). Not met. At Ls50,
  meeting 9.6 V needs about 14 % less overshoot than stock.
* S4 tr/tf <= 10 % slower: V8 +4 % / +2 % (rise) at Ls50: met.
* S7 gate within +5.5 / -3 V: met (Q1 -0.2 to 5.04 V).
* S8 low-side false turn-on < 0.5 V: the simulated Q2 gate peak during the rise is 1.4-2.0 V on stock, above the
  0.8 V Vth minimum (test 13: partial turn-on). Not met by stock or V8; it is a gate-loop/common-source target, not
  a power-loop one.
* S10 Eon+Eoff 10 % lower: V8 is 0.7-2.5 % higher. Not met.
* S12 +0.3 efficiency points: at 240 W this is 0.72 W, about a third of the simulated 2.08 W FET loss. Unlikely from
  layout alone; the FET-only estimator also cannot show it (C1 note in AGENTS.md).
* S3, S5, S6, S9, S11, S13 and the model goal M1 are not yet evaluated in this form.

## Conflicts and open inputs (template versus the recorded board)

* Stackup: the template says 4 layers; the EPC90133 design files have 8 copper layers (GTL, G1-G6, GBL).
* Measurement connectors: the template names MMCX J32/J33. J32 is absent in the published layout; J33 is a pair of
  plated holes used for the switch-node probe (QSG Fig. 8).
* Unfilled: driver, copper weight, dielectric, Er, S5 dv/dt limit, the DRC table, FET/driver and capacitor movement
  limits, stackup freedom, and all test-agent instrument fields. Where the design files define a value (stackup,
  EPC's DRC), that value is used and marked as taken from the files.
* Package inductance: the template has one parasitic corner (+/-10 %); the project reports assumed 50 pH and 0 pH.
  Proposed: assumed 50 pH as the baseline, 0 pH reported alongside, and +/-10 % applied to the extracted network.
* Parasitic extraction: the template asks for named lumped paths (Ld, Lsw, Ls, Lcs, Lg, Lks, Csw_gnd) at 100 MHz.
  The project keeps the full coupled network for simulation (AGENTS.md: keep return paths and mutual coupling); the
  named values would be reported from it, not substituted for it. FasterCap is not qualified for 3D board use, so
  Csw_gnd stays the audited board value until it is.

## Proposed order of work

1. Baseline report against S1-S13 (template stop point: owner approval before any optimization).
2. Geometry families aimed at the failing goals: gate-loop / Kelvin return (F4) for S8; power-loop return vias (F2)
   with V8 for S2. Every candidate is legal, keeps the BOM, and goes through the same KiCad route as stock.
3. The J33 probe-reference test (running) continues: it bears on D3's probe point and on any later back-fit.

## Evaluation protocol (declared 8 October 2026, before any goals run)

Owner instruction (8 October 2026): no approval stop; validate, evaluate and continue until a final acceptable
result is found. Runs: `scripts/epc90133_switching.py --study goals` (conditions in its docstring); scoring:
`scripts/assess_epc90133_goals.py` (definitions in its docstring). Primary conditions are ramp-Ls50 and step-Ls50
with the bench's assumed capacitor values (comparable with the earlier rounds); 0 pH is reported. A final candidate
is also rerun with the sourced capacitor data and C_SW (`--sourced` equivalent) and must keep its verdicts there.
The four nominal stock cases repeat the G search's stock cases and must reproduce them (overshoot, losses within
0.1 %), which checks that the goals cases are the search cases plus the stored settling trace.

Acceptable final result: a legal geometry-only candidate (BOM unchanged) that meets every goal, or, if no such
candidate is found, the best candidate with each unmet goal shown unreachable within the model by a bound (for
example an idealized screen that also fails it), not merely untried.

Status (9 October 2026): neither end state is reached. No tested candidate meets every goal, and the uniform
inductance-scaling, combined-stack and ideal-gate screens each cover one family of networks under the assumed lumped
50 pH package inductance; they do not bound every legal copper, via, coupling or gate-return change. S12's FET-only
estimator cannot assess converter efficiency, S11 reports the best sampled dead time, and S5 has no limit. V8 is the
best tested candidate and is provisional; the search is stopped for limited expected information gain.

Model (owner decision, 8 October 2026, before any goals result was read): the datasheet's gate-charge curve (Fig. 7)
is the truth. EPC2302QG is the primary model (goals cases `<case>-qg`); its Crss about 23 % outside Fig. 5 is listed
as a model inconsistency (template M1). The vendor model's goals runs (started first) are reported alongside.

Later owner clarification (8 October 2026): both Figures 5 and 7 are trusted
as required datasheet targets. The earlier primary-model designation identifies
the model used in those runs; it does not waive the Figure 5 failure. A replacement
model must meet both figures and retain the other passing datasheet checks before
being accepted as datasheet-consistent. Existing results retain their model identity
and M1 limitation. No board result is reclassified or overwritten by this decision.

## Layout limits (owner decision, 8 October 2026: "go with industry standard")

The template's unfilled layout limits are set as follows. There is no industry standard for how far parts may move,
so the position limits are a stated assumption, not a standard.

* Inner dielectric (top to mid-layer 1, the power-loop return gap; stock 0.127 mm): 0.075-0.127 mm, the range of
  widely stocked prepregs (1080 glass style at about 0.075 mm). 0.050 mm (106 style) is reported as a sensitivity
  only. The other stackup layers stay as in the design files.
* FET and driver positions: within 1 mm of stock (assumed). Decoupling capacitors: positions within 1 mm (assumed);
  their number and parts are fixed by the BOM.

## Combined-stack screen (declared 8 October 2026, before its runs)

Question: does any combination of the remaining power-loop changeables reach the loop-inductance reduction that the
bound sweep says S2 needs? All of them act mainly through loop inductance. Cases on variant A (top + mid-layer 1,
about 2 minutes each) through the KiCad route, each against stock through the route at the same dielectric:
stock and V8 at 0.100, 0.075 (limit) and 0.050 mm (sensitivity), via `scripts/epc90133_extract.py
A:m1:mid:d<mm> --loop <package>/power-loop.json --tag <case>`. Capacitor moves are not added: L3a showed only
0.75 % within the available room. Expected from the single-family results (round 2a: 0.100 -> -6.6 %, 0.075 ->
-13 %; V8 -12.5 %): about -20 to -25 % for V8 at 0.075 mm.
Gate to a full G extraction and goals run (fixed now): at least 45 % lower loop inductance than stock at the
stock dielectric, the level at which the bound sweep (x0.5: 9.81 / 7.42 V) starts to meet S2. Below it the screen
confirms the bound reasoning with real geometry and no G run is spent. A is a ranking variant (no gate loops); its
loop inductance is not the board's.
Run 1 of the screen is INVALID and kept (`*-run1-invalid-epc-gerbers.json`, `runs/stack-screen-*-run1-invalid.log`):
`scripts/epc90133_extract.py` was called directly without `EPC90133_GERBER_EXPORT`, which the route sets to the
package directory, so both "stock" and "V8" read EPC's Gerbers (their reports record geometry_source epc_gerbers)
and V8 came out identical to stock. Run 2 sets the variable per package, as `epc90133_board_export.child` does.
Run 2 result (package geometry, variant A, against stock through the route at 0.127 mm, 0.4925 nH): stock -6.6 /
-13.1 / -20.1 % at 0.100 / 0.075 / 0.050 mm; V8 -12.5 % at 0.127 mm and -20.0 / -27.6 / -36.0 %. Best legal
combination (V8 at 0.075 mm) -27.6 %, below the 45 % gate; no G extraction is spent on it. Even the 0.050 mm
sensitivity (-36 %) stays below the gate.

## Confirmation run: V8 + 0.075 mm on the full board (declared 9 October 2026, before any of its runs)

Labelled as declared AFTER the combined-stack screen failed its 45 % gate (-27.6 %). This is not a gate pass and
not a search: one candidate, one run, owner request after a review (docs/build.md, correction note of 9 October).

Decision it serves: whether V8 + 0.075 mm or V8 is the candidate to carry if a revised board is fabricated.
Question: does the variant-A advantage survive the full coupled G network, and what are its S1-S13 values against
stock and V8 under matched conditions? It cannot show that this is the best design or settle layout feasibility.

Method:
1. Extraction `G:m1:mid:d0.075` of the V8 KiCad package, called as the combined-stack screen run 2 did
   (`EPC90133_GERBER_EXPORT` = the V8 package directory; `--loop` its power-loop.json; `--tag V8`), one FastHenry job
   (`--jobs 1`; about 3 GB, the host has about 5 GB available beside another project's job). Output
   `G-m1-mid-d0.075-V8.json` in the package's extraction folder. Checks: outcome complete, every extractor check
   passes, geometry_source names the V8 KiCad export (the screen's run-1 failure mode). Matched controls: stock and
   V8 G extractions through the same route at 0.127 mm (same x-y mesh; only the layer heights change).
   Time: the J33 single-job G extraction took 21,755 s; expected 5-7 h. If it has not finished after 15 h it is
   recorded as incomplete and stopped by PID only.
2. Goals switching, vendor model (owner decision, 9 October), assumed 50 pH, the standard goals case set for
   `--ext-file stock, V8, V8d075` (nominal, then --vin 40, --vin 60, --iout 0; one process at a time, LTspice jobs
   2, timeout 3,600 s per case). Stock and V8 are rerun as matched controls; reproduction check: their nominal
   overshoot and FET loss within 0.1 % of `epc90133-goals-G.json`. Scoring: `assess_epc90133_goals.py` revision 2 on
   the four new reports.
3. Switch-node capacitance: the thinner dielectric raises the SW copper's capacitance to mid-layer 1, which the
   inductance extraction omits. Parallel-plate estimate from the V8 package rasters (SW on the top layer over GND on
   G1, no fringing) at 0.127 and 0.075 mm. If the increase, scaled by the observed +0.8 V for the whole 135 pF on G,
   exceeds 0.1 V of overshoot, a nominal-only sensitivity with that capacitance is declared separately; otherwise
   the estimate is reported and no case is run.

Frozen prediction (before any result): G loop inductance -10 to -20 % against stock (V8 gave -4.95 % on G for
-12.5 % on A); overshoot still above S2's 9.6 V under the ramp driver; S6 and S10 no better than V8. No follow-up
sweep follows whatever the outcome; the candidate page gets the new row.

Pre-result amendment (9 October 2026, 13:30, while the extraction runs; no switching case has started): the owner
needs results by 17:45. Step 2 as declared would take about 3 h after the extraction (a goals case takes about
5 min, as in the vendor goals runs of 8 October). Changed to: the full goals case set for V8d075 only (nominal,
--vin 40, --vin 60, --iout 0, run in parallel, up to 14 LTspice cases at once on the 16-thread host); stock and V8
are scored from their complete vendor goals reports of 8 October (`epc90133-goals-G{,-v40,-v60,-i0}.json`); the
matched control reruns stock and V8 at the nominal point under another case name (`--vin 48`, identical operating
point) and must reproduce those reports' nominal overshoot and FET loss within 0.1 %. If it does not, the V8d075
verdicts are reported as not comparable. Parallelism changes no case definition. The original chain (cmd PID 24040)
is stopped by PID after the extraction process is confirmed independent of it.

Switching run 2 (declared 9 October 2026 before its launch; run 1 was stopped for CPU oversubscription, see
docs/build.md): at most 8 LTspice cases at once, as on 8 October. Process A: V8d075 nominal goals set, 4 jobs.
Process B, one after another with 4 jobs each: the stock/V8 --vin 48 control, V8d075 --vin 40, --vin 60, --iout 0,
then the switch-node capacitance sensitivity (`--csw stock=135 V8d075=188.84`: nominal ramp/step-Ls50 with that
SW-to-GND capacitance; stock keeps the 135 pF estimate, V8d075 adds the computed +53.84 pF of
`results/gan/epc90133-csw-dielectric.json`). Reading: a V8d075 goal whose verdict against stock (S1, S2, S3, S4, S6,
S7, S8, S10 at the nominal point) differs between the plain and the -csw pair is reported as capacitance-sensitive,
not as met. Unchanged: reproduction control within 0.1 %, scoring with stock and V8 from the 8 October reports.

Run 2 procedural change (9 October 2026, 17:35-17:40, before any V8d075 result was read): with 8 cases at once the
first timing stages took about 13 min (792-849 s) against 72-146 s for identical netlists on 8 October (same
library, LTspice 26.1.1, 16 solver threads each, CPU not throttled; cause not identified). Process B (control,
corners, C_SW) was stopped after 13 min; process A (V8d075 nominal, 4 jobs) continues alone; B's five steps are
queued to run one after another after A (4 jobs), then scoring (`runs/confirm-V8d075-queue.ps1`). No case
definition, check or reading rule changed.

## "Outperforms stock" rule and the gate-return candidate (owner decision, 10 October 2026)

Declared after the V8d075 run-2 result and before any gate-return geometry, extraction or switching result exists.
Owner decision: the search target is a simulated layout that outperforms stock, defined as **no worse plus a clear
gain**. This is a separate rule beside S1-S13 (which stay recorded and scored); it does not relax any goal limit.
Vendor model, assumed 50 pH, G network, nominal 48 V point, judged under BOTH ramp-Ls50 and step-Ls50:

- **No worse:** every stock-relative goal quantity is no more than 0.5 % worse than stock: S1 peak voltage, S2
  overshoot, S3 settling, S6 Q1 peak current and di/dt, S10 Eon + Eoff, S12 FET-only loss/efficiency. S4 rise/fall
  time stays within its own 1.10 x stock, and S7 within its own +5.5 / -3 V. The 0.5 % allowance is five times the
  largest change seen in the 50 ps time-step checks (within 0.1 %); a numerical check of the deciding cases is
  required before a win is claimed.
- **Clear gain:** Q2's gate peak during the rise (S8 quantity) at least 10 % below stock's. (V8d075's 34 % shorter
  board common-source path gave 6-9 %.)
- The switch-node capacitance assumption must be the same for candidate and stock; a candidate that changes the
  SW copper or dielectric is judged in a matched with-C_SW pair.

Base: **stock**, not V8 (V8 already exceeds the 0.5 % allowance: ramp overshoot +1.8 %, settling +1.3 %).
Candidate: a local low-side gate-driver return (research note ranking 1), using existing vias and the qualified
KiCad edit route. First step, no solver: a read-only feasibility inspection of the saved geometry; if a legal
route needs a new via, whole-driver ground isolation, cut source pads or moved probe features, the candidate stops
there. If feasible: the edit, its DRC/net/power-loop checks, one G extraction (planned from the 6.47 h V8d075 case,
15 h cap), then the nominal stock/candidate pair under both drivers (4 cases plus a 50 ps check of deciding cases).
Stop after that pair whatever the outcome; corners only by a separate declaration.

### Trade-off screen against the "outperforms stock" rule (declared 10 October 2026, before its runs)

Inspection result (read-only, no solver; recorded in docs/build.md): a top-layer driver return to Q2's source pad is
blocked by the chain U80 LGL trace - R83 - VGl - R22 - NetJ2_1 trace - J22 - J2, which surrounds the driver's top
GND copper, and inner-layer returns still share Q2's source vias; the existing-via gate-return candidate therefore
stops as declared above. Saved results also show that the ideal low-side gate stage (EPC2302DS, 50 pH) lowers the Q2
gate peak by 33-34 % but lengthens settling by 12-15 % and raises overshoot by 0.9-1.6 %.

Screen (`scripts/epc90133_tradeoff_screen.py`, no field solver): per-metric relative changes against stock, both
drivers, of every saved direction (uniform board-L scale x0.9/x1.1, V8, ideal low-side gate), and a linear program
over non-negative mixes within the directions' tested ranges: (a) is the rule (all no-worse quantities <= +0.5 %, S4
<= +10 %, Q2 gate peak <= -10 %) feasible; (b) the largest Q2 gate-peak reduction and the largest improvement of each
other quantity with the rest no worse. Linear superposition is a SCREENING assumption: an infeasible result
means no mix of these directions passes to first order, not that no layout can. One run before it: the vendor-model
ideal low-side gate at 50 pH, `stock@{ramp,step}-Ls50-gear-ctlls` (2 cases, about 1-4 min each, timeout 3,600 s),
replacing the EPC2302DS stand-in; the EPC2302DS direction is reported alongside. The C_SW direction is reported
but not mixed (the trimmable copper is unidentified, and it is a different bench condition).
Reading: if (a) is infeasible, the rule is reported as not reachable by these directions, no geometry candidate is
built for it, and the owner is told which directions or rule changes the screen leaves open. No limit is changed here.

### Amendment after the trade-off screen, and best-achievable targets (owner, 10 October 2026; POST-RESULT)

Labelled RETROSPECTIVE: made after the screen showed the 0.5 % rule infeasible. The owner chose to allow settling (S3
quantity) up to +5 % against stock; every other no-worse quantity stays within +0.5 %, rise/fall within S4's
+10 %, and Q2's gate peak must be at least 10 % lower, under both drivers. The original rule's verdict (not met) is kept.

Owner instruction: for goals that cannot be met, search for the best achievable value instead, with every design
physically feasible and practically realistic (standard fabrication, legal clearances, fixed BOM, probes and
functions kept). Screen optima (linear, keeping S1, S3 within +5 %, S4, S6, S7): S2 overshoot cannot improve under
both drivers; S10 at best -0.3 %; S12 none; S11 is not a layout property; S8 (Q2 gate peak) -25 / -30 % at the
screen's edge (ideal-gate fraction 0.8 with lower loop L, not a realistic layout). S8 is the only failing goal with
room, so the search proceeds with it.

Candidate K1 (declared before its build): Q2 Kelvin-style driver return on the top layer. The NetJ2_1 trace between
R22 pad 1 (16.379, 26.9) and probe pin J22.1 (16.05, 24.795) moves to the bottom layer: one new via of the board's
smallest size (0.3488 mm pad, 0.1981 mm drill) beside R22 pad 1 on NetJ2_1, a 0.30 mm NetJ2_1 strip on B.Cu to J22.1;
the freed top-layer gap (y about 25.80-26.44) becomes GND copper joining the driver's GND copper to Q2's source-pad
copper. All on stock (base). Clearances >= EPC's 0.150114 mm. Via in pad is avoided (filled vias would be needed).
New primitive add_via in the qualified KiCad route; acceptance: L1 DRC as stock (0 unconnected, no shorts, no new
types, nothing below the clearance rule), L2 pad nets equal stock's, L3 power-loop checks as stock, drill file equal
to stock's plus exactly the new hole, gate-loop checks K1-K5 pass on the export, then one G extraction (6.47 h
profile, 15 h cap). Frozen prediction: board common-source L of Q2 at least 30 % below stock's 48 pH; Q2 gate peak
-5 to -15 %; settling +1 to +6 %; ramp overshoot within +1 %. Then the nominal stock/K1 pair under both drivers
against the amended rule, a 50 ps check of deciding cases, and the four corners only if the nominal pair passes.
Corrected for practicality before build (owner, same day): via beside the pad, not in it.
