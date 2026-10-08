# Project continuity

Read `README.md` for current implementation status, then
`plans/gan-halfbridge-pipeline-plan.md` for scope, gates and the active work order
(section 10). Inspect current files and git status before acting; another session
may have progressed the work. Executed results and replay instructions belong in
`docs/build.md`, not in this instruction file.

## Purpose and work selection

Build and validate **datasheet → vendor model → layout-aware simulation →
measurement → closure** for EPC90133/EPC2302. Three student-owned stages do not
require three reasoning agents. Use ordinary scripts for deterministic work;
assess the agent's contribution against a baseline.

Measurement readiness is the priority. Equipment inventory and actual board
identity are still needed from the lab's responsible person. The hardware plan
(`docs/epc90133-hardware-test-plan.md`) is a draft, not an approved executable
procedure. G3 stays open. Do not launch broad sweeps, repeat completed agent
milestones or extend deferred solvers just because hardware information is pending.
Choose bounded work using plan section 10's decision and stop rule.

The owner has no power-electronics background: explain in plain language and
recommend a course of action rather than offering unexplained technical choices.

## Evidence rules

- Record source, retrieval date, checksum and reuse terms for every EPC file.
  Public downloads do not establish unrestricted reuse. Vendor files, reconstructed
  EPC geometry and local solver builds stay in git-ignored `vendor/` and `.tools/`;
  this repository is public. Editable Altium files are available on request, but
  the owner decided not to send an EPC inquiry.
- Keep the original vendor model as baseline. Tune only with separate evidence
  isolating a device discrepancy across conditions; save a separate revision and
  test held-out conditions. Do not fit away layout, driver or probe errors.
  Unidentified causes are a valid result.
- Demonstrate execution in the selected simulator. A published format or zero exit
  code does not prove a valid run. Separate execution, passed checks, provisional
  predictions and physical validation.
- Declare method, acceptance checks, alternatives and compute limits before a study.
  Preserve failed, incomplete and invalid runs. Label post-result amendments as
  retrospective. Never overwrite the first frozen prediction score.
- Bind complete dependencies (imported helpers, extractions, vendor models) when
  a bench next changes. The switching manifest still needs its transitive
  `epc2204_baseline.py` helper. Do not rerun solvers solely for metadata. Validate
  upstream status and artifact identity before reuse.
- One matching waveform cannot separate device, layout, driver, thermal and probe
  errors. Each attributed layer needs independent evidence. Benchmark errors are
  not board error bars without a transfer argument. Two meshes show sensitivity,
  not convergence; never divide single-via inductance by via count.
- Keep return paths and mutual coupling in extracted networks. Capacitor C/ESR/ESL,
  package, driver and probe assumptions stay explicit. Use matched controls and
  hold other conditions fixed when attributing a change.
- QSG Fig. 9 is periodic buck operation, not double pulse. Equivalence was checked
  only for the recorded A/B cases with ideal supplies, ideal output source and 25 C.
  Say 'one published layout found', not 'only one layout exists'.

## Limits that must survive downstream summaries

Read the relevant report and build-note section before quoting numbers.

- **Model:** EPC2302 runs unmodified with `reltol=1e-6`. The 24 curve passes and
  limited table checks do not resolve Fig. 7 gate charge or QGD/QG(TH). No tuning
  is justified; gate-charge-dependent switching times and losses are unvalidated.
  EPC2302QG (`scripts/epc2302_qg_variant.py`, run 3) is a Fig. 7-following
  SENSITIVITY revision, not a tuned or validated model; it puts CRSS 23 % outside
  Fig. 5, so Figs. 5 and 7 cannot both be met in this structure (E7 decides).
  The stored plateau width (2.19 nC) is sampling-dependent: 2.40 nC resampled.
- **Extraction:** A/I/B/G are exploratory; no second full-board mesh has run.
  Fourth-mesh single-via inductance passes, resistance is unconverged; arrays,
  holes and Kelvin/multilayer connections are not qualified by that pass.
  FasterCap is not qualified for 3D board use and is not a current prerequisite.
- **Waveform:** Fig. 9 time-scale check passes, voltage-scale check fails. Use
  `results/gan/epc90133-fig9-summary.md`, not old by-eye readings. No case meets all
  criteria. Package L is assumed, not identified by a waveform match or stock E3
  measurements. Owner decision (7 October 2026): new simulations default to an
  assumed package source inductance of 50 pH (within EPC's < 0.2 nH LGA estimate);
  label it 'assumed 50 pH' and report a 0 pH alternative alongside. Existing
  reports keep their settings; do not rerun only to change the default. Probe
  filters do not bound loading/location errors. PHASE-ball stress remains unresolved.
  Damping study (7 October): vendor capacitor data (devices/capacitor-sources.json;
  bench CAP_MODEL values are assumptions, Ci 2x and ESR 5-7x off) and the tested loss
  forms close neither the overshoot nor the damping gap; only an unrealistic 1 ohm ESR
  matches the damping. Earlier G runs omit the board's switch-node capacitance (C_SW).
  Check vendor data for the BOM part before calling a component value realistic.
- **Mechanisms:** test 11's driver forms meet selected resistance/edge constraints,
  not every datasheet limit. Test 9 bounds positive Q2 channel current only in
  sampled rise windows. Test 12's shares describe a ring-deviation metric, not
  heat or energy not returned to ideal sources. Test 13 remains 'not supported':
  partial turn-on raises local damping but fails matched-cycle comparisons.
  Full-R transient evidence is on B; G evidence is local AC.
- **Design target (8 October 2026):** the owner's execution template, goals S1-S13 with the BOM fixed
  (`plans/goal-targets-2026-10-08.md`), replaces the rule below; gate-resistor changes are out of scope, and
  stock and V8 do not meet S2, S8 or S10 in the existing runs. The rule below describes the earlier rounds.
- **Design (5 October rule):** overshoot is the single objective, FET loss at most +5% over stock
  and Q2 gate peak not above stock are constraints. R80 1.5 ohm is the best tested
  candidate under four declared driver/package alternatives (assessor revision 5,
  `results/gan/epc90133-design-round3-assessment-rev5.json`). It is provisional,
  not a frozen prediction or hardware margin. It also meets C1/C2 under all four
  alternatives with EPC2302QG (`results/gan/epc90133-qgfit-assessment.json`); an E4
  prediction carries both models' values. Use settled loss estimator revision 2;
  earlier round-1/2a efficiency figures are invalid. Stackup plus R80 is untested.
  E9 converter efficiency cannot alone resolve C1's 0.05–0.09 W FET-loss increment;
  a thermal method is a candidate without a board-specific uncertainty budget.
- **Reconstruction:** track R reproduces saved EPC geometry; independent readback
  passes (`results/gan/epc90133-reconstruct-verify.json`). Frozen fills are not
  refillable design intent: refill changes about 1–2% of power/gate-region copper.
  `scripts/epc90133_edit_workflow.py` run 2 QUALIFIES a geometry-edit workflow
  (stock holes as fill keep-outs; edit lists on the base text) for move_footprint
  and move_via; `--suite reshape` run 2 qualifies reshape (rectangular add/cut on
  one layer, clearance cut-back). Candidates built with them still need their own
  DRC/net/extraction checks. Saved-geometry checks are not fabrication approval.
  Edited boards reach the extraction through `scripts/epc90133_board_export.py`
  (EPC-frame package); its X0 failed (-1.8 % loop L from sub-10 um representation),
  so compare candidates only with stock through the same route, 4 % threshold.
  L3a (Ci 0.40 mm toward Q1) is legal but +0.75 %: below threshold. DRC shows no gap below EPC's
  rule by more than the declared 1 um tolerance.
- **Agents:** milestones 1/2 and E2E-0 demonstrate non-blind execution/handoffs,
  not judgement or hardware closure. Milestone containment means 'no new git-status
  changes detected', not no writes to ignored files. Agents may read this file and
  docs (owner, 5 October); test judgement with predictions frozen before new
  measurements. Do not revive the unrun M3 answer-leaking draft.

## Hardware, sources and deferred work

- Hardware protection/interlocks remain independent of the language-model agent.
  No energized testing before the test plan and protection are approved. Removing
  human checkpoints needs recorded reliability evidence; fabrication release and
  envelope expansion retain review.
- Verify actual board revision/population. Schematic uP1966A conflicts with BOM
  uP1966E; J32 is absent in the published layout. Connect by verified silkscreen,
  not the QSG's conflicting VDD pin text. There is no VIN bleed resistor.
- Input-logic checks establish complementary static commands with selected RC
  paths, never 'safe' commands. Power-up/down and transient overlap are unresolved.
  Datasheet limits do not guarantee positive dead time; measure it at VIN = 0.
  Keep shutdown/discharge and numerical limits in the hardware plan. Simulation
  peaks do not define a safe envelope.
- FastHenry's MIT-authored notice is not the standard MIT License. `95b0fad` records
  internal noncommercial use only: no redistribution or assumed partner/commercial
  permission. FasterCap uses LGPL 2.1 or later.
- EPC9097/EPC2204 and DEVSIM/NMOS are paused reference work, not prerequisites.
  Preserve evidence and replay code; current benches import EPC2204/EPC9097 helpers.
  EPC9165 purchase waits for an unanswered measurement question.

## Practical work rules

- Reuse LTspice 26.1.1 and its adapter; do not convert vendor models or add adapters
  without a concrete need. KiCad 10.0.6 is the pinned board tool.
- WSL is capped at 8 GB. Run one large B extraction case at a time; profile long
  jobs and derive timeouts from evidence. FastHenry `-p diag` matched the default.
  Other projects share this host: never kill processes by name, restart WSL or
  change its settings. Long Windows runs use the recorded WMI method with the
  full Python path and redirected logs; a Start-Process child died with its session.
- Stop after a failed edit before launching a run; enforce this in shell scripts
  (for example `set -e` in bash), not separate unchecked lines.
- Reconstruction runs on Windows; WSL Python lacks shapely. Passing unit tests
  does not prove every solver/reconstruction dependency is installed.
- Keep verification tied to changed behavior or a named decision. Do not run large
  exports or simulations as generic cleanup checks. Prefer deleting unnecessary
  work to simplifying, optimizing or automating it.
- If bounded work is delegated, use the owner's cheaper-model preference and
  review the output. Explain outcomes, verification and remaining limits plainly.
- Source/benchmark interpretation: `docs/device-benchmark-sources.md`. Latest
  applied audit: `docs/project-audit-0f07a6a.md` and its build notes.
