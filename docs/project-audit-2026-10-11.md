# Review of 9-11 October work and further exploration

11 October 2026, Singapore. Reviewed HEAD `6cfc6b0`. Retrospective audit of the
recent layout, switching, scoring, copper-loss and thermal work. This does not
change a frozen prediction, acceptance threshold or original result.

The five pre-existing untracked files (owner template, literature inventory,
research note, overlap result and overlap script) were left unchanged. No board
export, LTspice, FastHenry or large thermal calculation was run. New evidence:
`results/gan/project-audit-2026-10-11.json`; replay:
`python scripts/audit_epc90133_2026_10_11.py` (NumPy and SciPy required).

## Assessment

The recent work establishes useful simulation tradeoffs, but no acceptable new
layout. K2's lower gate spike comes with longer settling; C3 did not improve that
balance. The synthetic six-goal networks are fragile partial-goal results, not
buildable designs or all-goals solutions. Further exploration is justified only
as a bounded test of whether a coordinated physical layout can improve that
tradeoff. Copying the nine numerical settings into a layout specification is not
justified.

Two confirmed software defects need attention before their outputs are used for
new acceptance or thermal-ranking decisions. The existing switching result
arithmetic survives this audit. Measurement readiness remains the project
priority; board identity, equipment and an approved procedure remain outstanding.

## Findings, ordered by consequence

### 1. High: the outperform scorer can accept violations of its declared rule

`scripts/assess_epc90133_outperform.py:39-62` checks VIN and relative metrics but
omits S7's +5.5/-3 V gate limits, does not require finite metrics, and does not
validate model identity or other matched conditions. The declaration explicitly
retains S7 (`plans/goal-targets-2026-10-08.md`, "Outperforms stock").

Three controlled counterexamples start with the saved stock cases and halve only
the reported low-side gate-peak metric to supply the required gain. Each then
introduces one fault: a 6 V gate maximum; NaN FET loss; or a different recorded
vendor-library hash. Both declared and amended rules return `pass: true` in every
case. These are deliberately inconsistent audit fixtures, not simulations.

The network search also duplicates the goals logic. Its S3 omits the main
scorer's settling-censor check: an unfinished 500 ns trace compared with 600 ns
passes the search's S3 but fails the official S3. Its case handling also lacks the
main scorer's complete input checks. In the actual 79 usable networks, no
censored/interpretation-invalid case was found and all eight evaluated goals
agree with the main scorer. Thus this defect does not change the saved six-goal
count. K1/K2/C3 remain failures of the outperform rule.

Repair before the next acceptance decision: reuse the main goal checks; enforce
S7, finite metrics, matching model and operating/bench conditions, and complete
usable evidence. Preserve old verdicts and publish a new assessor revision with
these counterexamples as regression tests.

### 2. High for thermal claims: the grid creates heat paths across absent copper

`scripts/epc90133_thermal.py:66` averages adjacent copper fractions to set lateral
conductance. In a two-cell check, one cell is solid copper and the next contains
none. With laminate conductivity set to zero to isolate copper, the code still
connects them with **0.0136906 W/K**. The copper-only connection should be zero.
Consequently an air/laminate gap can receive artificial copper conductance. A
fraction-based average also cannot distinguish differently connected shapes
having the same area fraction.

At lines 75-77 and 143-149 every plated barrel connects the layer nodes at its
cell, without separate barrel nodes or layer-specific copper contact/antipad
information. Barrel conduction itself is real; direct coupling to a plane that
does not touch the barrel is not established by this representation. This is
particularly relevant when comparing driver-via isolation and return islands.

The slab/via checks and energy balance verify the chosen equations, not these
missing geometric relationships. The reported approximately 1 K V8 change and
near-equality of K1/K2 should therefore remain unqualified thermal sensitivities,
not evidence that the layouts have equivalent cooling or a known thermal penalty.
The effect on the real board's temperatures has **not** been quantified here.

Before thermal ranking: fix copper-interface transport and barrel/plane contact
representation, test a gap and an isolated barrel, then decide whether a small
matched board comparison is useful. Do not rerun the full thermal family first.

### 3. Medium: numerical network settings were translated too literally into geometry

`scripts/epc90133_direction_screen.py:166-195` changes the inductance matrix and
selected couplings; it leaves resistance and geometry-derived capacitance
unchanged. Positive definiteness is an algebraic admissibility check, not proof
that fixed-stackup copper can realize the matrix. Moving copper changes several
of these properties together.

The nine groups are not independent physical lengths. CM overlaps VIN and GND.
For N3_00 the actual self-inductance ratios are approximately:

| Branch group | Ratio to stock |
|---|---:|
| Ci input branches | 1.248 |
| Cm input branches | 0.892 = 1.248 x 0.715 |
| Cm ground branches | 0.440 = 0.616 x 0.715 |

Thus "longer input connections" is already misleading for the Cm bank. Even
these ratios are inductance ratios, not trace-length ratios. The coupling factors
are not direct common-source-inductance ratios either.

The search used assumed capacitor values and omitted explicit C_SW in its plain
nominal cases. The matched capacitance/source checks required of a final design
are absent for the synthetic winners. Their switching losses and times also
retain the vendor model's gate-charge limitation and the assumed 50 pH package
source inductance. No hardware performance claim follows.

### 4. Medium: necessity and completeness claims exceed the tests

README's "needs nine coordinated changes" / "no subset ... works", and the same
wording in the goals plan/build notes, are too strong. Only three grouped subsets
were tested: couplings alone, gate side, and power side. Their failure establishes
only that **those three subsets** did not retain the six-goal result. No
leave-one-factor-out study or complete subset search was performed. Each factor's
necessity remains unknown.

Likewise, 80 sampled networks (79 usable), with later rounds focused near earlier
leaders, are a bounded search, not an exhaustive proof or an infeasibility bound.
Round 4's centres were selected before the delayed rounds 2-3 rescoring; this
affects the search path, not the validity of individually completed cases.

The six-goal result evaluates eight goals, not all thirteen. It gains S2 and S8,
loses S4, and increases Eon+Eoff by approximately 10-12% and FET loss by about 7%.
S10 was already missed by stock; it is further from its target. At x0.9 both
winners miss S8 (about 0.529 V against <0.5 V). By the declared stage-3c rule they
are **fragile model optima, not design targets**. Uniform +/-10% L is not a complete
manufacturing/model uncertainty study.

### 5. Medium: new runners and evidence records still have acceptance gaps

The local `runs/C3-chain.ps1` sets `ErrorActionPreference = Continue`, logs native
exit codes, then launches G regardless of the A/export acceptance result. It
gates switching on report existence rather than the preceding command's success
and fresh report identity. The tracked board-export runner likewise continues
after the power-loop child return code and starts extraction before computing
L1-L3 acceptance (`scripts/epc90133_board_export.py:375-391`). This conflicts with
the project rule to stop after a failed edit. C3's saved final acceptance passes;
no failed upstream run was shown to contaminate its successful result here.

The copper-loss and thermal reports bind geometry and their own script but omit
important imported helpers/terminal records. Thermal reports do not bind the
goals report, dead-time report or copper-map contents; the map is only a path.
Thermal input reads bypass the case's usability/model checks, and reaching the
50-iteration nonlinear limit does not produce an explicit failure. Do not treat
energy balance alone as a convergence/validation gate. Bind these dependencies
and fail closed when the tools next change; no metadata-only solver rerun is needed.

Both new models also read stock terminal boxes. They cannot automatically follow
the newly permitted moved/rotated/opposite-side components. Their current
K1/K2/V8 uses do not move FETs/capacitors, but free-placement studies need candidate
terminal mapping before these models can assess them.

### 6. Low: continuity documents contain incompatible current rules

README still states a 1 mm movement envelope, while the 10 October owner correction
explicitly permits position, rotation and board-side changes when viable. The
earlier research note's restrictions are historical. Active plan section 10 still
leads with the earlier pause while the goals plan records the subsequent owner
instruction to explore combinations. The later README does record a pause again;
these need one dated current summary, without deleting the intervening evidence.

## What remains supported

- All 80 saved search entries replay exactly: 79 usable; 37 reach five goals and
  two reach six at nominal conditions. The eight-goal subset agrees with the
  main scorer for every usable driver/candidate pair.
- All 182 checked extraction/helper hash references match current files. All
  selected switching reports record the same vendor-library hash. This checks
  recorded identity, not independent validation of EPC's physical model.
- K1/K2/C3's current export manifests match their acceptance reports, and all
  48 listed exported files match their manifests. DRC was not rerun; assembly and
  fabrication readiness were not established.
- K2's stored smaller-step and matched-C_SW checks support its reported tradeoff.
  C3's gate-loop prediction failed (755 pH versus a prediction below stock's
  561 pH); its gate reduction was also below the predicted range. These failures
  were explicitly retained. C3's lack of follow-up checks follows its declared
  failure gate and is not an omitted success demonstration.
- V8d075's plain nominal cases remain incomplete. The matched C_SW comparison
  and corner failures are useful, but cannot establish the missing
  plain-versus-C_SW attribution. The revised build note makes this distinction.
- Copper loss is a first DC/equipotential-terminal estimate, not total converter
  loss or a qualified thermal input. Two grids demonstrate sensitivity only.
- The 9 October whole-datasheet record explicitly retains uncovered items; the
  new board thermal calculation does not turn EPC2302 into a whole-datasheet model.

These checks do not revalidate all raw waveforms, the full-board extraction,
literature reuse permissions, or every new geometry primitive. G3 remains open.

## Evaluation of the proposed directions

| Direction | Assessment and next useful question |
|---|---|
| Shorter power return; coordinated capacitor/FET/via placement | Strongest physical redesign hypothesis. Include both capacitor banks and their returns. A capacitor-only move does not test it. First show a legal placement and continuous return paths. |
| Deliberately longer VIN/SW paths | Low priority as a standalone instruction. The factors describe a coupled inductance matrix, not requested lengths. Accept a longer route only as part of a complete layout whose extracted performance is better. |
| Move the driver/resistors; tighten both drive paths | Plausible enabling geometry for a coordinated redesign. Moving toward Q2 can harm Q1; retain both gate loops, bootstrap/local supply paths and fixed probes. The present ideal-supply switching bench cannot certify C80/C81 supply-loop performance. |
| Separate driver-return routes for both transistors | Worth one feasibility drawing, with distinct Q1 source/switch-node and Q2 source/ground references. C3 proves a particular Q2 island can be built, not that the desired pair of couplings can be realized or that it improves the overall tradeoff. |

EPC specifically advises keeping EPC2302's source pads joined in a plane and
taking the driver-return connection near the gate; the nearby source pad is not
a separate internal Kelvin pin. Preserve that when drawing islands. Source:
[EPC engineer's explanation](https://forum.epc-co.com/t/does-epc2302-has-a-kelvin-source-connection/334),
reviewed online 11 October 2026; no EPC file downloaded or redistributed.

The permitted edit types are consistent with the proposal. This is not evidence
that every desired network change has a legal implementation. Fixed connectors,
mechanical holes and outside-loop copper constrain a candidate-specific edit
mask; they do not establish an exact rectangle or restore the old 1 mm limit.
Electrical vias remain editable under the recorded interpretation.

Recommendation: repair the acceptance defects, then consider **one coordinated
placement/routing feasibility drawing** at the stock stackup. It should preserve
the fixed features, joined source pads and driver supply/logic references, and
identify every necessary tooling extension. Compare its intended full network
changes with stock; do not demand literal nine-factor matching. Stop if no legal
implementation can be drawn. If feasible, declare at most one candidate G
extraction (one heavy job, existing 15 h cap), followed by a matched stock/candidate
pair under both drivers; state capacitance assumptions and all thirteen goal
statuses. Any promising result then needs its separately bounded numerical and
corner checks. No such study was launched by this audit. Do not spend another
broad network sweep trying to turn the existing fragile six-goal optimum into a
fabrication recommendation.
