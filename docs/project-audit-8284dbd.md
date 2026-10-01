# Project audit at 8284dbd

Review date: 1 October 2026 (client date). Some existing run notes are dated 2 October;
this review identifies the snapshot by commit rather than inferring their chronology.

## Assessment

The engineering direction remains sound, but progress is uneven. Model execution,
geometry, coupled-network representation and diagnostic discipline have advanced.
Board prediction remains exploratory; hardware validation and the agent-workflow
contribution are not yet demonstrated. Stopping the late-cycle diagnostic is the
right priority decision. No current hardware or layout decision requires resolving it.
No schedule baseline was supplied, so this is an assessment of direction and readiness,
not a claim that the project is on schedule.

G1 is recorded as accepted; EPC2302 G2 is provisional with the gate-charge exception;
G3 stays open; G4 is not ready for execution; G5/G6 remain future work. The equipment
inventory and responsible lab person's involvement are the immediate dependencies.
G3 need not match an incompletely documented vendor screenshot before measurement
readiness can progress. Hardware execution still requires the separate G4 approvals.

## Findings, in priority order

### 1. Test 12 does not establish that no energy returns to ideal sources

Evidence: `scripts/epc90133_energy_budget.py:173-195`, its saved report, and
`docs/build.md` test 12. The computed quantity is the integral of v~ i~, where each
tilde is the deviation from a one-period moving average. This is a useful declared
decomposition, and its balance passes. It is not automatically a physical separation
of nonlinear transient energy into baseline and ring energy.

Writing v = vbar + v~ and i = ibar + i~ gives

    vi = vbar ibar + vbar i~ + ibar v~ + v~ i~.

The calculation retains only the last term. For an ideal constant-voltage source,
v~ is zero away from filter boundaries, regardless of its current. Its negligible
reported contribution therefore does not demonstrate absence of returned energy.
Likewise, Q1's nonlinear channel contribution is a filtered deviation-power share,
not yet a uniquely established share of physical excess heat.

Recommended wording: “Q1 contributes 59–64% of the declared ring-deviation loss
metric; the deviation-power balance and selected step check pass. Whole-window
power balance fails near the switching edge.” Withdraw the unconditional source-
return claim. The resistor contributions remain useful under this decomposition.
No new simulation is needed merely to correct the interpretation. If an energy claim
later matters, retain cross terms, define a reference trajectory or storage-energy
boundary, and check actual source power over the relevant window.

### 2. Test 13 supports a bias trend, not the claim that early cycles are explained

Evidence: `results/gan/epc90133-q1-bias-ring.json`, B comparison entries. Both 2.5 V
and 3 V have **zero matching cycles** under the declared ±0.15 V rule. The first
transient cycle is at about 2.806 V with zeta 0.00856. Local results at 2.5 and 3 V
bracket that zeta, but this is not a matched-state demonstration; the gate bias also
changes during the cycle. Every matched B comparison from 3.5 through 5 V fails.

Use “partial turn-on increases local damping and is qualitatively consistent with
stronger early damping; it does not explain the later gap.” Preserve the declared
not-supported result. The G+50 pH clamped/active confound is correctly disclosed.
This was a legitimate diagnostic, but its expected negative overall verdict makes
it a poor justification for another open-ended diagnostic sequence.

### 3. The hardware plan has the right purpose but needs a concrete measurement design

Evidence: `docs/epc90133-hardware-test-plan.md`, envelope, equipment, E1–E6 and
held-out sections. The plan explicitly remains unapproved and non-executable.
Pulse/current/temperature limits, trip implementation, discharge verification,
numerical stop thresholds and probe-specific uncertainty must be resolved with
the lab's responsible person. Operator stop decisions and independent protection
need separate acceptance records. The listed starting voltage is a draft proposal,
not an approved safe condition.

Additional points to resolve in that revision:

- E1 at VIN=0 is informative but does not uniquely identify loaded switching drive.
  Declare the gate load, bootstrap state, supply conditions and accessible voltage
  being measured; use energized gate observations to test transfer of the E1 model.
- H3/H4 signatures are hypotheses, not exclusive signatures. Changing probe loading
  changes the circuit, so “while the circuit is unchanged” is too strong. Bound
  loading separately from observation response.
- Convert proposed hypothesis signatures to quantitative predictions only for the
  selected feasible conditions. Freeze a prior baseline; if E1 calibrates the driver,
  freeze a separate revised prediction before diagnostic switching/held-out data.
- Do not make the proposed 60 V point mandatory. Select a feasible held-out set
  before observing its data, within the eventually approved envelope.
- Efficiency is core scope in the main plan but lacks an explicit input/output-power
  measurement and uncertainty procedure in this draft. Keep it as a later named
  deliverable rather than silently replacing it with waveform matching.

### 4. Other progress claims need narrower wording

- Test 11 checks selected output resistance and 3000 pF edge-time constraints. It
  does not show that either representation meets **every** driver datasheet limit.
  The observed 28–34% overshoot sensitivity is useful without that overclaim.
- Test 9 supports “no appreciable positive Q2 channel current in the sampled rise
  windows of these cases.” Avoid categorical absence of false turn-on under all
  conditions; reverse conduction is present at the window start.
- Full R is qualified as a representation at 100 MHz. Its transient effect is
  demonstrated on B; G evidence is local AC because its full-R transients timed out.
  Neither establishes broadband extraction accuracy.

### 5. Continuity and reproducibility lag the diagnostic work

The main plan still says the EPC2302 model needs execution and the BOM/Gerbers need
retrieval; its G3 summary retains the corrected “die VGS 2 V” reading. README calls
package source inductance “the remaining lead,” omits the later driver-form result,
and its early description does not explain the scoped verified-OP fallback exception.
`docs/build.md` ends test 13 with the next loss diagnostic, although the latest owner
notes correctly hold it. Reconcile current summaries while retaining historical runs.

Tests 12/13 record selected report hashes, which match current files, but their own
input manifests do not directly bind every extraction, imported bench/helper and
vendor-model dependency used to generate their new simulations. A hash of an older
report alone does not verify those files at execution. Bind the complete dependency
set when these benches next change; do not rerun expensive cases solely for metadata.

Code-review hardening item: test 13's `only_fallback = all(...)` is true for an empty
reason list. Require an explicit eligible failure status and nonempty recognized
reasons, and distinguish incomplete comparisons from hypothesis rejection. No
evidence here shows that this edge case affected the stored results.

## Recommended work order

1. Correct the interpretation and synchronize current summaries; preserve results.
2. Obtain the exact equipment/board inventory and responsible lab contact. Produce
   the channel/connection plan and executable first-power procedure for review.
3. Use the already authorized driver-only bootstrap/supply bench as one bounded
   preparation task if it answers E1 setup questions. Declare outputs and stop rules;
   do not let it expand into another fit to Fig. 9.
4. After approval, characterize measurement chains and driver behavior, then execute
   the approved first energized condition. Freeze revisions and held-out predictions.
5. Keep AC-versus-transient loss attribution, finer G extraction and broad sweeps on
   hold until a named decision needs them.

The agent contribution remains a separate open milestone: one bounded artifact-to-
comparison run with interventions, failures, time and cost scored against scripts.
The owner's decision deprioritizes it now; it must still return before claiming an
agent-driven pipeline has been validated. No integrated loop or per-layer physical
error budget follows from the current simulation diagnostics alone.

## Verification and limits of this audit

Read README, the active plan, hardware plan, tests 9–13 write-ups, relevant scripts
and saved results at 8284dbd. Checked the six declared input-file hashes across the
test-9 assessment and tests 12/13: all match. Inspected test-12 E1/E2/E3 statuses and
test-13 comparisons directly. No new LTspice or extraction runs were launched.

The WSL unittest attempt discovered 96 tests: 88 passed, 7 skipped, and one test
module failed to import because that Python environment lacks numpy. Therefore this
audit does not certify a clean full-suite run. Windows `python` was not on PATH.
No dependencies were installed. No physical equipment, board or raw oscilloscope
data were available for review. Only this audit record was added; baseline models,
results and project claims were not rewritten as part of this review.
