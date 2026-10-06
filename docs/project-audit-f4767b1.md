# Project audit at f4767b1

5 October 2026. Reviewed the working tree at `f4767b1`, including the uncommitted
README rewrite. This is a code and evidence audit, not a new qualification run or
approval to energize hardware. Historical reports and implementation code were
left unchanged.

**Overall assessment:** the project has a working simulation and analysis chain,
with substantial recorded evidence and appropriately provisional board results.
It has not yet validated the real board or demonstrated independent engineering
judgement by agents. Measurement readiness remains the right priority. The newest
input-logic work adds useful static checks, but overstates what those checks prove
about power-up. The agent handoff checker also accepts some unsupported records.

Six actionable findings follow. P1 means correct before the hardware procedure is
reviewed or relied on; P2 means correct before the affected tool is reused for a
decision; P3 means a lower-priority verification or maintenance issue.

## 1. P1: the power-up claim is stronger than the input-logic evidence

**Locations:** `scripts/epc90133_input_logic.py:245`,
`docs/epc90133-hardware-test-plan.md:65` and `:363`,
`docs/build.md:1443`, and plan section 10 item 8(d2).

L5 passes solely because the driver's minimum POR threshold, 3.8 V, is greater
than the logic's minimum operating supply, 1.65 V. It then labels static idle
configurations as the commands present at driver enable. The hardware plan says
that no input state, “including power-up,” commands both gates on with the selected
jumpers. The build notes call these configurations “Safe as designed.”

That comparison establishes supply-range ordering. It does not establish when
the logic outputs, jumper-select inputs or RC nodes settle during a supply ramp,
or their relationship to driver enable. The evaluator explicitly replaces each
RC node with its settled input and contains no supply-ramp or start-up timing
model. It also excludes the PWM source's behaviour. A static complementary truth
table cannot establish absence of transient overlap.

**Required correction:** retain L1–L3 and the static jumper classifications, but
describe L5 as a supply-threshold check. Keep actual commands at enable, power-down
behaviour and transient overlap unresolved until the planned E1 work supplies
evidence. Replace “safe” with the precise result: complementary static commands
with the RC paths selected. Reopen the power-up portion of hardware-plan item 5.

The plan still requires bus-off tests and approval before energization, which
limits the immediate consequence. This finding does not show that the physical
board has a start-up fault; it shows that the claimed exclusion is unsupported.

## 2. P2: the dead-time evaluator can claim a guarantee despite an unbounded term

**Location:** `scripts/epc90133_input_logic.py:216–225`.

`datasheet_limits_guarantee_positive_dead_time` is simply `worst > 0`, while the
same result says diode-discharge delay is an **unbounded reduction**. In addition,
the value named `worst_case_gate_command_dead_time_ns` uses the room-temperature
RC minimum, although the function separately computes a lower minimum with X7R
temperature drift. Interpolated threshold limits and assumed residual voltage
also need to retain their stated status as assumptions.

A solver-free counterexample changes only the in-memory resistor value to
1,000 ohms. The function returns a 38.94 ns “worst case” and a positive-dead-time
guarantee while still reporting the unbounded reduction. This is a test of the
function, not a proposal to fit that resistor or a prediction for the board.

**Required correction:** report the computed interval as conditional on the
listed assumptions. A guarantee must remain unavailable while a subtractive term
is unbounded. Separate the room-temperature and temperature-inclusive arithmetic,
and test that an incomplete bound cannot become a guarantee.

**Impact on stored results:** none of the current 120-ohm values changes. The
recorded −7.03 ns conditional result and `false` guarantee replay exactly. The
current conclusion that positive dead time has not been guaranteed stands.

## 3. P2: the independent handoff checker accepts wrong identities and extra predictions

**Locations:** `scripts/e2e_check.py:78–126` and `:166–183`;
`src/circuit_tools/handoff.py:127–170`.

The checker rehashes listed files and recomputes selected checks, but it does not
fully connect the record's descriptive fields to those files. Its prediction
loop checks that required rows exist, without rejecting additional rows.

Starting with the saved clean C1 records, each of these isolated in-memory
changes still returns an empty problem list:

| Changed field | Unsupported record accepted by the checker |
|---|---|
| I-1 model identity | `library: nonexistent.lib`, `subckt: EPC2204` |
| I-2 network | `extraction: nonexistent.json`, variant G, mesh m2, junction pad, while the checked extraction remains A:m1:mid |
| I-2 predictions | An extra usable prediction for an invented case, claiming efficiency 0.9999 |
| Assessment reference | `reference_data.path: nonexistent.json` and a 64-zero hash |

The checker uses fixed workspace paths for several checks, which lets those
checks pass even when the record names something else. These are structural
identity and coverage errors, separate from the deliberately manual review of
engineering claims.

**Required correction:** bind model, network and reference fields to the exact
listed artifacts and their contents. For this frozen pilot, check the expected
device and extraction identity explicitly. Require an exact, unique set of
prediction case/metric pairs, rejecting extras and duplicates. Add fault tests
for each accepted counterexample before another agent evaluation.

**Impact on stored results:** all three original C1 records still pass the current
checker. The historical clean-run/reference agreement and injected-model-change
rejection are not reversed. X2 should be read as passing the implemented checks,
not as proof that every handoff field was independently verified.

## 4. P2: malformed handoffs can crash validation instead of producing a rejection

**Locations:** `src/circuit_tools/handoff.py:100–106` and
`scripts/e2e_check.py:129–136`.

Three solver-free examples reproduce the problem:

| Input | Result |
|---|---|
| A handoff file containing the JSON list `[]` | `AttributeError` before schema validation |
| A check with `evidence: [{}]` | `TypeError: unhashable type: 'dict'` |
| An exception with `id: []` | `TypeError: unhashable type: 'list'` |

The existing malformed-input test covers some missing fields but does not cover
these nested types. Further recomputation also indexes artifact fields without
first validating their shape.

**Required correction:** validate top-level and nested types before dictionary
lookups, set construction or recomputation. Return structured problems for invalid
records and artifacts. Add focused fault tests rather than relying on broad
exception suppression. This matters because handoffs are generated by agents and
need to fail predictably when they are malformed.

## 5. P2: the new input-logic report does not bind its complete evidence set

**Location:** `scripts/epc90133_input_logic.py:229–262`.

The report records the evaluator and transcription hashes, but not the imported
BOM/source-verification helper, the source inventory or the vendor files consumed
by the run. `verified()` checks files against the source inventory that exists
at execution time; the report does not freeze that inventory. The uP1966E values
used for L4/L5 are hardcoded and its datasheet is not verified by this script.

Consequently, changing a helper or consistently updating a source record and its
file can change the evidence without changing either of the two recorded hashes.
This falls short of the project's rule to bind complete dependencies when a bench
is added or changed.

**Required correction:** add an input manifest covering the helper, source
records, BOM, schematic, guide and relevant component datasheets, including the
driver source used for the constants. Include a repository revision as useful
context, without treating it as a substitute for hashes of ignored vendor files.
Preserve the existing report and attach any correction as a separate assessment.

**Impact on stored results:** no changed input was found. All seven files in the
EPC90133 source inventory match their current recorded hashes, both report hashes
match current files, and the input-logic replay matches after newline normalization.
This is a traceability gap, not evidence that the existing numbers are wrong.

## 6. P3: the current full test suite fails in WSL

**Location:** `tests/test_wslrun.py:35`.

Fresh command:

```sh
PYTHONPATH=src python3 -m pytest -q tests -p no:cacheprovider
```

Result under WSL Python 3.12: **157 passed, 68 subtests passed, 1 failed in 36.79 s**.
The timeout test supports either WSL or native bash in its setup, but its final
process check unconditionally invokes `wsl`. Inside Linux that executable is
absent, producing `FileNotFoundError`.

**Required correction:** choose the process-inspection command for the current
platform, as the runner does. Keep the assertion that the actual child process
has ended. Re-run this test and then the suite after the correction.

The failure occurs in the post-timeout assertion; it is not evidence that the
solver was left running. No fresh Windows-suite result was obtained because
Python was not on this session's Windows PATH. Earlier passing suite records
remain historical results, not a pass for the current tree.

## Engineering conclusions that remain supported

- **Device stage:** the EPC2302 model is a provisional baseline. The 24 passing
  curve checks support execution against the published curves. Figure 7 and the
  table sub-charges remain unresolved; physical switching timing and losses are
  not validated, and no tuning is justified.
- **Board stage:** the generated Figure 9 summary supports the README's numbers.
  No tested variant meets every criterion. G plus an assumed package inductance
  is a sensitivity result, not identification of the real board's missing effect.
  The failed voltage-scale check and unknown probe chain remain material limits.
- **Extraction:** the single-via inductance pass does not qualify via arrays,
  plane slots or board resistance. The via-array report still has V0/V3 passing
  and V1/V2 failing. Slot differences against an unconverged mesh do not give
  board error bars. FasterCap's saved invalid-matrix assessment and unfinished
  3D qualification do not support board capacitance extraction yet.
- **Hardware:** equipment, actual board identity, numerical limits, channel
  uncertainty, protection and approval remain open. The new logic work does not
  close those dependencies. Efficiency remains an unfinished core deliverable.
- **Agents:** the pilot demonstrates execution consistency and handoff behaviour
  on a familiar workflow. It is non-blind, shares engineering assumptions with
  the script reference, and has not established a cost or judgement advantage.

The README rewrite generally preserves these limits. The stronger start-up
wording remains in the hardware plan, build notes and active plan and needs
correction there. No additional broad simulation campaign is justified by this
audit.

## Verification, artifacts and scope

The [audit evidence JSON](../results/gan/project-audit-f4767b1.json) records the
counterexamples, source checks, test outcome and hashes of the reviewed files.
Local solver-free reproductions are in
`runs/audit-f4767b1/reproduce.py` and `reproductions.json`; these are git-ignored.
They substitute copies of parsed records in memory and do not modify the pilot
workspaces. The input-logic replay writes only to the audit directory.

Reviewed areas include the current README and plan, earlier audits, the hardware
plan, input-logic evaluator and tests, handoff schema and checker, pilot records,
Figure 9 comparison, extraction manifests, recent benchmark gates and solver
timeout handling. This is targeted coverage, not a line-by-line review of every
historical script or an independent derivation of every numerical reference.

No LTspice, FastHenry or FasterCap studies were rerun, and no agent benchmark or
hardware experiment was launched. WSL execution required sandbox escalation;
the test suite and solver-free checks ran successfully through that access.
Git reported inaccessible global-ignore/cache paths, as in earlier audits.

Recommended order: correct the start-up claims and conditional dead-time
semantics; close the checker and provenance gaps before reuse; repair the portable
test; then continue the equipment inventory, probe plan and first-power procedure.
Keep the original simulation baseline and historical verdicts unchanged.
