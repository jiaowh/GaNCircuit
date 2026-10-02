# Repository audit at 75d6f35

2 October 2026. Requested against the overnight handoff. Reviewed current README,
active plan, hardware plan, changed scripts and committed reports since 8284dbd,
with emphasis on via qualification, FasterCap H, agent milestones and KiCad.
This is a targeted code/evidence audit, not an independent rerun of the EM or
LTspice studies or a certification of the hardware procedure.

The handoff's numerical outcomes are supported. G3 remains open, measurement
readiness remains the priority, and neither board extraction nor FasterCap board
capacitance is qualified by the overnight work. Six actionable findings follow.
Existing results have not been rewritten and implementation fixes are not part
of this audit.

## Findings

### 1. P2: baseline reports completion after the comparison fails

`scripts/agent_milestone.py:218-225` chooses `status: completed` before invoking
the comparison and then records its return code without using it to change that
status or checking the output artifacts. A mocked subprocess returning 1
reproduces `status: completed, returncode: 1`, with no comparison written.

This is a false-success path in the deterministic baseline used to evaluate
agents. The separate scorer's output comparison provides another check, so this
does not invalidate the recorded clean-run scores. Before another milestone,
make completion depend on a successful subprocess and complete, readable output;
record failure and captured diagnostics otherwise.

### 2. P2: baseline input checks still crash or accept absent required panels

`scripts/agent_milestone.py:205-215` reads the figure after K1 even if it is
missing and parses switching JSON without handling decode failures. Reproductions:

| Input | Observed outcome |
|---|---|
| Missing digitized figure | FileNotFoundError; no agent-report.json |
| Malformed switching JSON with matching manifest hash | JSONDecodeError; no agent-report.json |
| Figure with empty checks object | K3 passes because all() receives no panels |

The missing-switching-file fix only covers that particular file kind. Require
both named panels explicitly, stop after failed prerequisite checks, and turn
parse/schema failures into structured stops. Add focused regression tests for
these paths. These are new fault cases; they do not change the historical five
fault-run outcomes.

### 3. P2: FasterCap H can qualify physically invalid matrices

`scripts/fastercap_board3d_check.py:118-135` passes every returned matrix to
`pair()`, takes the difference between lengths and scores only H1/H2/H3.
There is no matrix-validity gate. Two negative pair capacitances can have a
positive difference. A solver-free synthetic reproduction supplied negative
diagonal matrices at every 3D setting, with their difference matching the 2D
reference: H1, H2, H3 and `all_pass` were all true.

The real stored run is already failed; this finding does not promote or reverse
it. Its JSON also lacks the explicit invalid-3D disposition recorded in prose.
Before reuse, validate matrix dimensions, finite values, signs, reciprocity and
positive definiteness within declared numerical tolerances, then require
physical validity for derived quantities and qualification. Preserve raw invalid
matrices for diagnosis. Put the post-hoc invalidity disposition in a separate
assessment bound to the original report, rather than rewriting its declaration.

### 4. P2: README still presents a deviation metric as physical loss

`README.md:221-223` says most of the ring's loss sits in the upper transistor's
channel. Test 12's shares are of the declared integral of voltage and current
deviations, not a physical heat partition; the whole-window Tellegen check failed.
`docs/build.md:1023` already states the narrower interpretation. This summary
reintroduces the claim withdrawn in the previous audit. Replace it with the
59-64% share of the declared ring-deviation metric and retain the distinction
between local damping, transient decay and energy accounting.

### 5. P2: the via pass does not localize the old mesh error to the via itself

The handoff's numerical pass is correct: adjacent-mesh L changes are 0.04949%
and 0.02928%, the difference changes 0.02430%, E1 is +2.47486%, and E2 is inside
both brackets. E2 is a bracket check, not an independent exact accuracy test.

However, `scripts/fasthenry_via_cavity.py:102-132` changes the entire plane-grid
pitch and plane thickness subdivision together with the via subdivision. There
is no control isolating the via, pad or junction region. The handoff's assertion
that the old failure was resolution around the via itself, and
`docs/build.md:196-198`'s localization to the via/junction/pad region, go beyond
that evidence. Say that the benchmark now passes its declared inductance mesh
criterion; the location of the previous discretization error was not isolated.

Nor does this certify every impedance quantity: R changes by 7.82% and 4.86%
between the last two meshes. The declared mesh check is for L and its difference,
so this does not revoke the pass; it limits its interpretation. Keep the
geometry-specific 23.5/33.7 pH bracket widths and all board-array, hole and
multi-layer limitations. No new solver run is needed to correct this wording.

### 6. P3: current-state summaries are inconsistent

- `README.md:295` still says KiCad is not installed, while build notes and source
  records describe 10.0.6 and the loaded EPC library.
- `README.md:145-146` says the gate-path package variants were not half-step
  checked, while its later paragraph correctly records G+50 pH's check.
- Plan section 8's G3 status (`plans/gan-halfbridge-pipeline-plan.md:430`) still
  leads with a failed via check and deferred fourth mesh, without the later pass.
- `docs/build.md:2246` says FasterCap case C passed, although its qualification
  table records a mesh failure. Its fine-setting accuracy comparison passed;
  overall qualification did not.

Synchronize these summaries while retaining the dated failed runs. Do not change
the historical verdicts.

## Handoff verification and limits

- Initial tracked working tree was clean. HEAD and the local tracking ref
  origin/gan-pipeline both named 75d6f35. No remote fetch was performed, so this
  verifies local tracking state rather than independently checking the server.
  Git emitted warnings about inaccessible global-ignore and pytest-cache paths.
- Milestones 1 and 2 contain the stated four clean and five fault outcomes,
  counting milestone 1's two runs only once. They demonstrate this task family,
  not engineering judgement or a useful reliability estimate. S2 remains only
  a git-status-change detector. The task card allows repository reads and the
  operator's fault description is reachable; these are not blinded fault tests.
- Milestone 3 is not tracked. Its draft exists locally under the ignored
  runs/agent-milestone/m3-draft directory. 'Moved out of the repository' means
  out of version control, not outside the agent-readable workspace. The required
  hidden-scorer/held-out design remains necessary before running it.
- Both local EPC library archive SHA-256 values match
  devices/epc/epc-library-sources.json. Reuse permission is not established and
  the archives remain ignored. The KiCad load/47-footprint result was reviewed
  as recorded evidence; installation and GUI loading were not independently
  repeated in this audit.
- FasterCap H's committed data support the 15.758% 2D change, missing finest
  long-strip result and invalid matrices. The air diagnostic supports focusing
  on the dielectric case; it does not isolate the precise input error or rule
  out every solver issue triggered by a dielectric. Case C is not an overall
  passing dielectric qualification.
- The hardware draft explicitly remains unapproved and non-executable. The
  corrected high-side probe connection and measured bootstrap prerequisite are
  present. Exact equipment, board identity, numerical limits, channel plan and
  lab-responsible-person approval remain dependencies. This audit supplies no
  new hardware operating instructions or safety certification.

## Verification performed

WSL: `PYTHONPATH=src python3 -m pytest -q tests -p no:cacheprovider`:
**105 passed, 52 subtests passed in 14.66 s**. Python was unavailable on this
session's Windows PATH; WSL access required a sandbox escalation, which succeeded.
This is a fresh WSL result, not a fresh Windows-suite result.

Isolated reproductions in ignored runs/audit-75d6f35/check_baseline.py and
check_fastercap.py use temporary inputs and mocked subprocess/solver responses.
They do not invoke EM solvers, rerun agents, or change historical reports.
`git diff --check` passed before this report was added. No long simulations or
background jobs were launched, and no unrelated processes were stopped.

Next work: fix the result-status and validity gates with regression tests,
synchronize the summaries, then continue measurement readiness with the owner's
equipment inventory. Keep broad simulation sweeps and board design deferred.
