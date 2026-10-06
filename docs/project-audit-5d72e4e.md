# Overnight design audit at 5d72e4e

6 October 2026, Asia/Singapore. Scope: design round 1 revision 2, round 3,
their evaluator, recorded solver fallbacks, and the resulting E4 recommendation.
This is a review, not a new design round. No solver was launched, scientific
report overwritten, implementation changed, or commit pushed during this audit.

**Disposition: retain R80 = 1.5 ohm as the best tested candidate for E4 within
the declared model and four alternatives. The saved numerical result survives
review. The evaluator is not yet a reliable automatic acceptance gate, and some
claims and chronology need correction. Hardware predictions remain unfrozen.**

## Findings, in priority order

### 1. High: a missing alternative can silently shrink the acceptance rule

`scripts/assess_epc90133_design.py:77-82` derives the alternative list from the
input cases instead of requiring the four declared alternatives. If an entire
alternative is omitted from every report, it disappears from the rule rather
than producing an undetermined constraint.

Fault probe: keeping only step-Ls0 cases still produces a ranking, including
R80-2.2-dt7.5 as the winner and R80-1.5 as eligible, despite three missing
alternatives. This is particularly misleading because the dead-time candidate
fails the loss constraint in the actual ramp-Ls0 results.

Require the declared alternative set independently of available cases. Reject
unknown alternatives and structurally inconsistent case names/parameters; retain
missing declared cases as undetermined. All four alternatives are present for
the actual 1.5-ohm decision, so this defect does not reverse that decision.

### 2. High: declared controls are evidence, but are not acceptance gates

The round-3 reproduction and half-step requirements in
`scripts/epc90133_switching.py:312-321` are not evaluated by the design assessor.
Removing both controls, or doubling both controls' reported FET loss, leaves the
same 1.5-ohm ranking. Merely including the check report in `--extra` does not
make its result affect acceptance. The generic `numerical_check` field in the
switching report is for another study and does not implement this check.

The Gear checks also silently skip missing evidence
(`scripts/assess_epc90133_design.py:85-103`). Removing the usable
R80-2.2 step-Ls50 Gear check and the stock ramp-Ls0 Gear check still leaves both
`passes` and `tight_within_0.1pct` true. The declared step-Ls50 comparison is
conditional on a usable trapezoidal result; that result exists in this probe.

Require the applicable check set and every required metric, and explicitly gate
round-3 selection on reproduction and the selected candidate's numerical check.
The actual reproduction, half-step and four Gear comparisons pass; the finding
concerns unattended reuse and incomplete or corrupted inputs.

### 3. Medium: input compatibility and loss-estimator validity are not checked

`metrics()` trusts `usable` and the presence of numbers. The assessor merges
reports without verifying operating conditions, extraction/model identity,
loss-estimator revision or the explicit settling flag. Hashing the supplied
reports identifies what was assessed; it does not establish compatibility.

A disposable copy with the 1.5-ohm cases marked estimator revision 1,
`settled_within_2pct=false`, and extraction parameter A-m1-mid still selects
1.5 ohm. Require the supported estimator and settling status for C1, consistent
conditions and dependencies, and method/step pairing verified from parameters.
Do not require identical evaluator hashes across declared revisions: permitted
changes need an explicit compatibility rule.

For the actual inputs, extraction, vendor-library and listed helper hashes
agree across reports. All eight stock/candidate waveforms used for the 1.5-ohm
comparison reproduce their saved metrics and revision-2 loss values exactly;
all eight settle by the implemented rule. This finding is not evidence of a
wrong input in the stored decision.

The switching manifest also omits the transitive `epc2204_baseline.py` helper
imported by `epc2302_baseline.py`, including `library_path`. Complete dependency
binding remains a follow-up when the bench next changes; no metadata-only
simulation rerun is warranted.

### 4. Medium: the cross-method rule was retrospective to an affected result

The statement "before any result it affects" in the assessor docstring, and
the corresponding build-note/user-summary claim, is too strong.

Commit 1b24989 is dated 5 October 19:58:24 +08:00. The affected
R80-2.2-dt7.5@ramp-Ls50-gear run started at 19:27:33 and its log reports
42.757 seconds elapsed (the adapter records 49.032 seconds). Its stock
trapezoidal result was also already available. The rule was committed before
the resulting assessment commit, but after this simulation result existed.
Describe it as a retrospective assessment amendment, preserve the original
rule, and distinguish original-rule verdicts from amended verdicts.

This does not change the 1.5-ohm choice: all four of its comparisons use matched
methods. Nor does the mixed-method exception rescue the dead-time candidate:
its matched ramp-Ls0 comparison already fails C1.

Other sampled chronology is consistent with prospective declarations: d5184f3
(17:07:50) precedes the first Gear timing run (17:08:46); 55d9f7d (19:16:04)
precedes its extension (19:17:11); 8b6cc4b (18:38:34) precedes round 3
(18:39:38); 8dfc08a (21:25:25) precedes the half-step timing run (21:26:04).
The interruption's cause remains inferred, not established by these logs.

### 5. Medium: several interpretations exceed the tested scope

- **Best tested candidate**, not a demonstrated optimum over stock-board part
  swaps. The tested resistor grid supports 1.5 ohm; it does not exclude values
  between 1.5 and 1.8 ohm or other components. No further search is necessary
  merely to justify E4.
- **Not frozen.** Build notes around lines 1614-1617, the layout plan, AGENTS.md,
  and the assessment scope call these frozen predictions. The hardware plan
  correctly says approved conditions and a frozen prediction record are still
  missing. Call the results provisional simulation predictions for E4.
- **Stock measurements do not uniquely identify package inductance.** The
  "which regime applies" wording in E4 and the build notes should be conditional.
  Driver behaviour, model discrepancy and probe response remain competing
  explanations. Stock data can constrain alternatives; the before/after swap
  tests the predicted response.
- **The combined stackup/R80 option is untested.** Adding percentage changes
  from A's dielectric study and G's resistor study does not prove their combined
  C1 result. Deferring the option for cost and the need for a new board is
  reasonable; "would exceed C1" is a hypothesis, not an evaluated verdict.

The maximum predicted loss increase is 4.342%, leaving 0.658 percentage points
to the 5% constraint. This is a margin within the model, not a hardware margin
or an uncertainty bound. The half-step result applies to step-Ls0 only; it
does not establish the numerical sensitivity of every alternative.

### 6. Low: fallback reporting is incomplete or mislabeled

`scripts/assess_epc90133_design.py:146-148,167-169` lists mixed-method pairs in
`compared_at_50ps` even though those pairs use 100 ps, and emits the main-case
metrics/relative changes without substituting the pairs actually used for
verdicts. Thus accepted Gear cases can appear missing in the metrics table.
Report a resolved pair record per design/alternative, including both case
identities, methods, steps and metrics; derive verdicts and tables from it.

## Verified result

All eight report hashes and the assessor hash match the saved round-3 assessment.
Replaying the assessor produces an identical JSON object. Reprocessing the
existing raw files with the current metric code reproduces all eight selected
stock/candidate records exactly, with matching raw and netlist hashes. This
checks reproducibility; it is not independent physical validation of the loss
estimator or device model.

| Alternative | Solver pair | Stock overshoot | 1.5-ohm overshoot | FET loss change | Q2 gate-peak change |
|---|---|---:|---:|---:|---:|
| ramp, Ls = 0 | Gear / Gear | 25.078 V | 16.788 V | +4.342% | -22.820% |
| step, Ls = 0 | trapezoidal / trapezoidal | 16.586 V | 11.406 V | +3.332% | -17.775% |
| ramp, Ls = 50 pH | trapezoidal / trapezoidal | 11.195 V | 10.772 V | +2.373% | -2.576% |
| step, Ls = 50 pH | Gear / Gear | 10.883 V | 9.725 V | +2.587% | -6.253% |

The loss increment is 0.049-0.085 W. The reproduction control has identical
metrics and main-netlist hash. The selected half-step check changes overshoot,
loss and Q2 gate peak by -0.000216%, +0.001702% and -0.000175%, respectively.
The Gear checks' largest per-case difference is 0.04414%; their loss-difference
comparison differs by 0.2901%, consistent with the declared separate thresholds.

Round-1 loss ranges also reproduce: 2.2 ohm +5.470 to +8.976%; 3.3 ohm
+10.394 to +14.193%; 2.2 ohm / 7.5 ns +2.987 to +6.262%. Ramp-Ls0 is the
binding case for all three. The incomplete 1.2-ohm candidate cannot beat
1.5 ohm's worst-case overshoot because one resolved case is already 21.3 V.

The extra 50 ps report has now finished: stock ramp-Ls50 is usable, but
R80-1.2 ramp-Ls50 is unusable. This report was already modified in the working
tree at audit start and was left untouched. No decision depends on it.

## Recommended follow-up

Keep 1.5 ohm as the candidate for the approved E4 experiment. Before reusing
the evaluator as an agent acceptance gate, fix findings 1-3 with fault tests
and emit the actual comparison pairs. Correct the retrospective/frozen/untested
claims while retaining the original reports. Measurement readiness remains the
engineering priority; this audit does not call for another broad sweep.

Audit scratch evidence is in the ignored `runs/audit-5d72e4e/`: `audit.py`,
`output.txt`, disposable fault reports and assessments, `raw_check.py`, and
`raw-output.txt`. No full test-suite certification is claimed. The local
origin/gan-pipeline tracking ref points to 5d72e4e; remote state was not refreshed.
