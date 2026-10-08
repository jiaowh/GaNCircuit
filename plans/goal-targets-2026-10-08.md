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

Model (owner decision, 8 October 2026, before any goals result was read): the datasheet's gate-charge curve (Fig. 7)
is the truth. EPC2302QG is the primary model (goals cases `<case>-qg`); its Crss about 23 % outside Fig. 5 is listed
as a model inconsistency (template M1). The vendor model's goals runs (started first) are reported alongside.

Later owner clarification (8 October 2026): both Figures 5 and 7 are trusted
as required datasheet targets. The earlier primary-model designation identifies
the model used in those runs; it does not waive the Figure 5 failure. A replacement
model must meet both figures and retain the other passing datasheet checks before
being accepted as datasheet-consistent. Existing results retain their model identity
and M1 limitation. No board result is reclassified or overwritten by this decision.
