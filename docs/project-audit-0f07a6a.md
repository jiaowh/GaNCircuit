# Project direction and 6 October 2026 work audit

Reviewed at `0f07a6a`, 6 October 2026 (Singapore). Scope: today's commits, current README and active plans,
design assessor revision 4, Track R reconstruction and checks, research provenance, and measurement readiness.
The working tree was clean at audit start. This audit adds a report and supporting numerical evidence; it does
not alter production code, previous results, or the original reconstructed board.

## Assessment of direction and progress

The direction remains coherent: qualify the original EPC2302 model, account for the EPC90133 layout, measure
the stock board, then test a revised design and close the prediction/measurement loop. The strongest evidence
is currently for repeatable simulation and artifact handoffs. It is not yet a validated board model or an
automated hardware workflow. G3 remains open; G4 measurements and G5 fabrication have not been completed.

Measurement readiness should remain the engineering priority. The missing equipment inventory, received-board
identity, probe/channel plan and approved first-power procedure prevent the most informative next experiments.
The reconstruction is useful preparation for G5, but its completion does not resolve those dependencies.

The owner's current design objective is lower overshoot with two constraints: no more than 5% extra simulated
FET loss, and no higher Q2 gate peak. R80 = 1.5 ohm remains the best tested candidate under the four declared
alternatives and both assessment rules. Its headline 33% worst-case overshoot reduction is a model result;
the response is only about 4–11% with the assumed 50 pH package source inductance. The 4.34% worst loss increase
leaves a model margin, not an established hardware margin. The candidate is provisional, not a frozen prediction.

Today's substantive progress:

- Revision 4 fixes the earlier assessor's missing-alternative, pair-selection and control-gating defects.
  The stored-data regression reproduces the 1.5-ohm selection under the original and amended rules.
- Track R produces a saved KiCad reconstruction with 106 footprints and 445 drills. Its stored reports pass the
  declared round-trip checks; all five reports' script hashes match the current scripts. The final saved-fill
  report records zero shorts and unconnected pads. Failed attempts remain visible.
- Gerber macro and decimal Excellon fixes have regression tests.
- All ten downloaded files in today's literature manifest match their recorded SHA-256 values. No vendor files
  are tracked in git. Direct inspection confirms that the held EPC2302 subcircuit contains no inductors.

## Findings, ordered by priority

### 1. High: a missing objective can still produce a selected design

Locations: `scripts/assess_epc90133_design.py:175`, `:274`, `:332`.

In the existing synthetic test fixture, set only
`R80-1.5@ramp-Ls50.metrics.event_b_turn_on_at_valley.sw_overshoot_above_bus_V` to null.
The assessor still selects `R80-1.5`, with ranking `[["R80-1.5", null]]`. It checks C1/C2 before ranking but does
not require a complete objective. A second probe sets that case's `usable` to the string `"false"`; it is treated
as true and the design is selected. Null case objects and a list-valued manifest raise AttributeError instead
of the documented structured rejection.

Require correct object types, a literal boolean usability flag, and finite numeric values for every metric
needed by the requested verdict/ranking. Missing objective evidence must prevent selection; malformed data
must produce exit 2 and reasons. Add these counterexamples to the fault tests.

These probes do not invalidate the stored 1.5-ohm result, whose normal-input regression passes. They do prevent
using the current assessor as a reliable general agent acceptance gate.

### 2. High before G5 edits: saved-fill reconstruction does not qualify ordinary KiCad refilling

Location: `scripts/epc90133_reconstruct_final.py:253` and its saved-fill DRC/round-trip checks.

The script writes each zone boundary from the island's exterior; interior holes are represented in the saved
fill. This preserves the manufactured picture but does not establish that KiCad can regenerate it. The docs
acknowledge frozen fills, but “Track R complete” and “editable design” need this practical qualification.

Audit experiment: copy the final `.kicad_pcb` and `.kicad_pro` into ignored scratch, run KiCad 10.0.6 DRC with
`--refill-zones --save-board`, export all eight copper layers, then compare with the saved final Gerber exports
using the project's geometric reader. The original board was not changed.

- Whole-layer symmetric-difference area / original area: 3.53–3.91%.
- Excluding a 1 mm board-edge margin and subtracting every drill disk from both geometries: 2.29–2.83%.
- In G's power/gate window (14, 22)–(33, 37.5) mm, also subtracting drills: 0.98–1.85%.
- Refilled DRC still reports zero unconnected items and no shorting_items, but isolated-copper items rise from
  13 to 43 and two solder-mask-bridge items appear.

These are geometry differences, not predicted inductance errors. The experiment does not isolate every cause
or show that every changed region is electrically important. It does establish that zero shorts/unconnected
does not ensure preservation of the geometry used for extraction. The effect is not confined to the outline
or drilled-away material.

Keep the original as a frozen geometry reference. Before layout optimization, demonstrate a bounded edit
workflow: preserve intended holes/keepouts, check a no-edit refill, move one representative component, inspect
copper/mask/paste and net changes, and rerun the relevant geometry/DRC checks. If refill cannot preserve stock,
explicitly define and check a geometry-edit workflow instead. Do not treat the current saved-fill pass as
fabrication approval.

### 3. High: failed DRC commands can pass using stale or empty reports

Locations: `scripts/epc90133_reconstruct_final.py:345–393`; the same return-code/freshness pattern appears in
`scripts/epc90133_reconstruct_nets.py`.

Both final DRC subprocess return codes are ignored. Existing report files are not removed or uniquely named,
and absent fields default to empty lists. A fault probe executes the actual R3/R4 AST statements with both
commands returning 1 and pre-existing `{}` report files: **R3 = true and R4 = true**.

Check command completion, use fresh per-run paths, validate the DRC schema and required arrays, and bind the
reports to the board checked. Keep failed reports as failed. This is a reusable-runner defect; no evidence was
found that today's recorded KiCad calls failed in this way.

### 4. Medium: reconstruction reports do not identify the complete inputs or exact board checked

Locations: report construction in `scripts/epc90133_reconstruct_parts.py:359`,
`epc90133_reconstruct_footprints.py:255`, `epc90133_reconstruct_nets.py:267`, and
`epc90133_reconstruct_final.py:397`.

The reports hash their own script, but do not bind the output board/project, input footprint board or side
assignment file, imported helpers, actual extracted Gerber/PDF/drill files, or DRC/export artifacts. Early
stages check the zip, while consumers read mutable extracted files. Later stages also consume upstream outputs
without validating their corresponding passing report. A path alone cannot identify the current local board
as the one that passed, especially because it is ignored by git and overwritten by reruns.

At the next reconstruction change, record a full manifest, upstream status and artifact hashes, KiCad version,
and output/report hashes. Preserve run-specific artifacts. No expensive simulation rerun is needed for this.
The audit evidence records the current original-board SHA-256; it cannot retroactively prove its identity at
the earlier run time.

### 5. Medium: R5 is not an independent check of the exported pad nets

Location: `scripts/epc90133_reconstruct_final.py:394–395`.

`pad_net_change` is populated only after the code has skipped pads with an existing net. R5 then asks whether
that list contains pads with an existing net. It does not reread the saved board and compare the original EPC
pad-to-net mapping. A wrong net assignment can retain identical Gerber geometry, so R1 is not a substitute.
Likewise, R5's ring claim is handled by construction/listing rather than a saved-output validation.

Read the saved board back through KiCad and compare every named pad's net with the independently parsed EPC
mapping, with explicit rules for unnamed pads. Verify ring size/listed exceptions there too. This finding is
about assurance strength; no actual wrong EPC pad net was demonstrated in this audit.

### 6. Low: current summaries contain superseded decisions and stronger wording than the checks

- README still says future blind evaluations need a separate isolated session, while the 5 October owner
  decision accepts normal project context and tests judgement against new measurements.
- Active plan section 10 says the efficiency procedure is still to be written, although hardware-plan E9 exists.
  It also retains the earlier three-target design conclusion without the subsequent one-objective outcome.
- The layout plan's final “Decisions needed” still calls the reconstruction route undecided; its opening and
  schedule retain superseded targets. Mark historical sections explicitly and lead with the current decision.
- Build notes say a DRC at clearance minus 1 micrometre proves no gap is below EPC's rule. It establishes the
  relaxed threshold only; report “within the declared 1 micrometre geometric tolerance.”
- Today's research note recommends a thermal loss method as capable of resolving 0.05–0.09 W, but its manifest
  records abstract-only review and there is no board-specific sensitivity/uncertainty budget. Treat this as a
  candidate method. E9 converter efficiency does not by itself isolate the small FET-only loss increment.

## Verification and limits

- Full unittest discovery passes on Windows Python 3.12: **185 tests, 23.1 s**.
- Full unittest discovery passes in WSL Python: **185 tests, 39.6 s**.
- The suite includes the stored round-3 assessment replay. No LTspice/FastHenry study was rerun.
- Five reconstruction script hashes and ten literature-file hashes were checked and match.
- Fault probes and the isolated KiCad refill ran as described above. Their numerical output is in
  `results/gan/project-audit-0f07a6a.json`; scripts, disposable boards and full DRC reports are in ignored
  `runs/audit-0f07a6a/`. The first geometry-comparison attempt in WSL failed because shapely is absent there;
  it succeeded in the installed Windows environment. Passing unit tests therefore does not establish that
  all reconstruction dependencies are installed in WSL.
- Literature contents were not comprehensively re-reviewed. Attempts to fetch the Micromachines and arXiv
  primary pages failed (429/cache miss); this audit certifies the local manifest hashes, not every literature
  interpretation. The no-inductor observation was checked directly in the held EPC2302 model.
- Reconstruction rules were revised after failed attempts. Keeping those failures and declaring each next run
  is good practice, but a subsequent pass is not independent validation of the relaxed rule. The side-assignment
  bare-pad “connected inside part” exception remains heuristic; the final report uses no such exceptions.

## Recommended next work

1. Fix the acceptance-gate defects above and add the demonstrated fault tests before further agent runs.
2. Keep R80 = 1.5 ohm as the provisional E4 candidate; do not launch another broad parameter sweep.
3. Complete the equipment/board identity record with the responsible lab person, then turn the hardware draft
   into the reviewed probe/channel and first-power procedure. Specify how the small loss constraint will be
   evaluated or explicitly left unresolved before interpreting E4 as meeting all objectives.
4. While that information is pending, qualify one bounded KiCad edit/refill workflow. Defer larger geometry
   optimization and fabrication claims until its geometry and evidence checks work.
5. Freeze predictions at approved conditions before measurement. Use the held-out measurement scores and
   recorded interventions/cost to demonstrate the agent contribution; execution milestones alone are insufficient.
