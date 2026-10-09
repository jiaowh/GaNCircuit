# Review of 8 October work, audited 9 October 2026

Reviewed commit: `274cd46a197507d185c0d70045912616fbc29dc2`, branch `gan-pipeline`.
Scope: EPC2302DS, the S1-S13 goals and layout stopping argument, Fig. 9 and J33,
the extraction parser change, saved evidence and current summaries. Read README,
active plan section 10, the relevant build notes and the previous applied audit.
The tracked tree was clean; the owner's Word template was already untracked and
was left untouched. HEAD matched the locally recorded origin branch; no network
fetch was made, so this is not independent verification of the live remote.

**Assessment:** useful, reproducible simulation progress, but the final narrative
overstates what has been excluded. Stopping broad layout iterations and prioritizing
measurement is reasonable. Declaring all remaining legal layouts infeasible, or
claiming that one measurement will identify the missing physics, is not supported.
G3 remains open. This review does not change any frozen result or acceptance rule.

## Findings, ordered by priority

### 1. High: the layout screens do not prove infeasibility of the permitted design space

Locations: `README.md:152-168`, `docs/build.md:3479-3483` and `:3509-3549`,
`scripts/epc90133_switching.py:611-652` and `:422-427`.

The scalar sweep changes every extracted branch inductance together, keeping
coupling coefficients fixed, and leaves resistance, capacitors and assumed package
inductance unchanged. It explores one family of networks. Real copper, via and
driver-return edits can change their entries independently. Failure of the sampled
scales to meet S2 and S10 together is not a bound over those other networks; even
the continuous interval between sampled scales has no demonstrated bound.

The combined-stack gate uses variant A's loop reduction as a screen for G switching
behavior. The evidence explicitly says A is a partial ranking model. V8 itself
changes A by -12.5% but G by -4.95%, illustrating why an A percentage cannot be
inserted into the whole-G scalar sweep as a proven prediction. The -27.6% A result
can justify not spending more computation, but not a universal impossibility claim.

The ideal low-side gate connection is a useful sensitivity case, but no proof makes
its peak the minimum over every allowed gate-loop/coupling arrangement. Removing
all board gate impedance is not established as a monotonic optimization of this
transient. Its 1.10-1.28 V failure is conditional on the unchanged excitation and
lumped shared 50 pH package representation.

S12 has an additional scope problem: the scorer uses FET-only efficiency, which
cannot assess a layout's copper-loss improvement or total converter efficiency.
Failure of that proxy is not proof that the template's converter target is
unreachable. S11 identifies the best *sampled* dead time of the tested networks,
not an optimum for every allowable geometry.

Recommended disposition: **no tested candidate meets all goals; V8 is a provisional
tested candidate, and the search is stopped for limited expected information gain**.
Do not claim the template's alternative completion condition (each unmet goal shown
unreachable) has been achieved. No additional sweep is required to make this correction.

### 2. High before acceptance use: the new goals assessor can ignore disqualifying evidence

Locations: `scripts/assess_epc90133_goals.py:48-50`, `:105-114`, `:128-166`.

An in-memory copy of a saved usable case, with only `interpretation_invalid` set,
still produces scored metrics. The existing switching and Fig. 9 evaluators have
an explicit interpretation-invalid exclusion; the new goals scorer does not.
It also trusts supplied report contents without checking upstream identities or
compatibility and silently replaces duplicate case names when merging reports.

S5 has no limit and is absent from `verdict`, while `all_met` combines only that
dictionary. Consequently the code can call its implemented subset complete without
S5 ever being decided. The appropriate state for an unset required goal is
undetermined, and it must prevent an all-goals pass. `combine([])` also returns
true, although the present fixed primary/corner lists do not trigger that path.

These are acceptance-gate defects, not evidence that the saved V8 failure is wrong:
the exact saved design assessments replay identically. Fix invalidity/identity
checks and required-goal completeness before using the scorer to certify a result.
Current S13 is the declared set of separate voltage/load/L-scale screens; it does
not establish robustness over every combined corner or R/C uncertainty.

### 3. Medium: the J33 headline loses its failed-control and observation limits

Locations: `README.md:126-129`, `scripts/epc90133_switching.py:511-527`,
`scripts/epc90133_probe_reference.py:128-139`, `docs/build.md:3551-3573`.

The build notes correctly preserve the failed extraction control and label the
later interpretation retrospective. README instead says probe location explains
part of the discrepancy without carrying that qualification. The JSON probe
assessment reports both cases as usable but has no study-level control verdict;
numerical usability must not be mistaken for acceptance of the declared experiment.

Recomputed from the saved data:

| Quantity | Value |
|---|---:|
| J33 extraction loop-L change against original G | -1.1953%, limit 0.5%: fail |
| Q2-pin overshoot within the J33 transient | 11.2175 V |
| J33 differential overshoot in that same transient | 9.2239 V |
| Digitized Fig. 9 overshoot | 5.6981 V |
| Fraction of the gap removed | 36.1191% |
| Fitted damping, Q2 / J33 | 0.0248025 / 0.0247913 |

Thus the arithmetic is sound as a within-transient, ideal-observation sensitivity.
The failed control prevents calling it the declared decisive experiment. The
overshoot residual is 3.5258 V, 0.5258 V beyond the absolute 3 V comparison limit;
Fig. 9's voltage-scale failure still limits interpretation of that difference.
The 2.023 V falling dip is measured below its reverse-conduction plateau, whereas
the 3.134 V undershoot uses the settled low level: keep those quantities separate.

The pre-run amendment already says the guide offers J33 and J32 and does not
establish which was used for Fig. 9. J33 is a documented candidate observation
point, not independently confirmed as the Fig. 9 connection. Likewise, a different
capacitor-ground waveform weakens that specific ideal-observation explanation;
it cannot establish what EPC actually measured with an unknown loaded probe.

### 4. Medium: model comparison and proposed measurement are overinterpreted

Locations: `docs/build.md:3493-3497` and the handoff summary reviewed in this task.

EPC2302DS and the vendor model producing similar overshoot/damping show that this
particular gate-charge correction does not close the gap. They share most equations,
including output-charge and loss assumptions. This does not rule out the transistor
model as a contributor. The vendor model does not match Fig. 7; calling both models
jointly datasheet-matching also obscures their different qualification states.

EPC2302DS does pass the declared D0-D5 regression. D3 means no violated tested limit
and no *new* review flag: QGD and QG(TH) remain flagged. Leakage, breakdown, reverse
recovery, thermal and ratings coverage remain open. This is partial calibration,
not every datasheet table value matching or physical device validation.

A measurement with a characterized probe and known connection would constrain
the discrepancy. It would not, by itself, settle package inductance and missing
loss independently of device capacitance, board extraction and driver excitation.
The existing hardware plan's measurement-chain/driver checks and discriminating
conditions are needed; unidentified contributions remain an acceptable outcome.
Probe loading, package representation, device loss, copper loss, driver behavior,
board identity and extraction error remain hypotheses rather than an exhaustive
or identified causal breakdown.

### 5. Medium: dependency binding remains incomplete after the bench changed

Location: `scripts/epc90133_switching.py:1668-1683`.

The switching manifest still omits the transitive `scripts/epc2204_baseline.py`
helper despite the continuity rule requiring it when the bench next changes. The
probe evaluator records its own hash and two data files but omits its imported
comparison and digitizer code, which determine the numbers. The DS generator's
module manifest is more complete and includes the EPC2204 helper.

All 60 recorded hash references checked in this audit match their local files.
That supports the recorded dependencies, not the completeness of their lists.
Bind the missing dependencies on the next code correction and preserve historical
reports. Do not rerun physical solvers solely to repair metadata.

### 6. Low: current-status documentation is internally inconsistent

- README's top table is dated 7 October, while later sections describe DS/V8.
  Line 53 still says neither model meets Figs. 5 and 7; line 51 describes DS passing.
- The selected R80 part swap in README and active plan section 10 conflicts with
  the later fixed-BOM target. Preserve it as historical work, not the active choice.
- AGENTS still says no board run uses DS and requires a 0 pH alternative. The later
  recorded owner decision in build notes and switching declaration uses DS/50 pH
  only. Reconcile continuity text to that recorded decision, without relabeling old runs.
- The final build note says 51/52 goals cases are usable. The four inputs actually
  bound to the saved DS assessment contain **55/56** usable cases (44 nominal,
  dead-time and scale cases plus 12 voltage/load cases). The separate ideal-gate
  report adds two usable cases, making **57/58** across those five reports.
  The sole failure is still V8/ramp/Ls50/L-scale 0.9. It must remain undetermined.
- The generated Fig. 9 table prints 45.0 ns for traces still outside the band at
  the observation boundary. It should carry a censored/not-settled flag rather
  than look like a measured settling time. The prose already states the limitation.

## Verification and limits

Replay: `python scripts/audit_epc90133_2026_10_09.py` from the repository root.
Evidence: `results/gan/project-audit-274cd46.json`. Scratch goals replay:
`runs/audit-274cd46/goals-assessment.json` (ignored).

- 60 recorded hash references match, including the DS library/report, extracted
  networks, assessor inputs and recorded imported modules. These include repeated
  references, not 60 distinct files. D0-D5 saved outcomes all read pass.
- Goals replay reproduces both design records exactly, including failed/undetermined
  outcomes. The invalidity fault probe changes only a copy in memory.
- J33 rising metrics recomputed from terminal traces reproduce overshoot and damping.
- The saved single-job FastHenry output has 49 ports. Parsing it and applying the
  inverse/inverse path reproduces the saved raw impedance matrix exactly in this
  environment; port order matches. This supports the parser repair for this artifact,
  not arbitrary output formats or board-mesh accuracy.
- `python -m unittest discover -s tests -p test_fig9_comparison.py`: 10 tests pass.
  No generic full-suite run, geometry export, fit, LTspice or FastHenry run was made.
- No vendor or local-solver files are tracked. A read-only Windows process check
  found no active LTspice/FastHenry/Python job after the audit commands finished;
  it is not an inventory of every possible process inside WSL.

No new external source or board measurement was acquired. Original source reuse
terms remain in force. This audit leaves production code and prior evidence unchanged;
it adds its own replay script, evidence, report and build note.

## Recommended next work

Correct the summaries and acceptance gates in bounded software work. Retain DS as
the recorded partial calibration and V8 as a provisional tested geometry. Preserve
the stalled corner; do not spend another long solver run to turn a known overall
failure into a complete table. Obtain the actual board identity and equipment list,
then review the draft measurement-chain/driver/first-power procedure. Freeze the
approved-condition predictions before measurements. Continue to defer broad layout
searches: the reason is unresolved model confidence and limited decision value,
not a proved impossibility of all permissible layouts.
