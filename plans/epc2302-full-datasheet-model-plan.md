# EPC2302 whole-datasheet model proposal

Owner clarification, 8 October 2026: the target is the whole datasheet, not only
Figures 5 and 7. This is a proposed sequence, not an executed calibration study.
The original vendor model and prior prediction reports remain immutable references.

Status (9 October 2026): the coverage record exists (`scripts/epc2302_coverage.py`, run 2;
`results/gan/epc2302-coverage.md`). EPC2302DS covers steps 1-4 for electrical rows and curves;
leakage rows are flagged, BVDSS unsupported, QGD/QG(TH) unresolved. Step 5 (thermal network,
ratings/SOA checker) is open. Neither model satisfies the whole datasheet.

## Acceptance meaning

Use the pinned April 29, 2026 datasheet identified in
`devices/epc/epc90133-sources.json`. Build a requirement record for every table row,
curve and applicable note: page, quantity, units, test conditions, typical/limit
classification, method, tolerance, evidence and status. Every condition and every
curve in a figure needs its own check. An unsupported or unresolved requirement
prevents a claim of full coverage; absence of a check is never a pass.

Separate three outcomes: reproducing published typical electrical/thermal behavior,
checking a simulated operating point against published limits, and validation on
physical devices. A nominal model is not required to equal minimum, typical and
maximum values simultaneously. Limit compliance does not establish typical accuracy.
Absolute-maximum limits are not a request to invent destruction behavior in SPICE.

## Coverage inventory and proposed checks

This inventory identifies the work; it does not assert that untested entries pass.
The saved baseline covers only selected rows, and its 25% typical-deviation band is
an informational screen, not a whole-datasheet acceptance tolerance.

| Datasheet item | Required assessment | Existing evidence / gap |
|---|---|---|
| BVDSS table row | Specified gate bias and drain-current criterion; audit breakdown representation | Not in saved table baseline; unsupported physics must remain explicit |
| IDSS | Off-state drain leakage at the printed bias | Not in saved table baseline |
| IGSS forward, room temperature | Gate leakage at the printed bias | Not in saved table baseline |
| IGSS forward, elevated temperature | Gate leakage with the stated temperature | Not in saved table baseline; inspect temperature dependence |
| IGSS reverse | Reverse gate leakage at the printed bias | Not in saved table baseline |
| VGS(th) | Specified current and drain/gate connection; limits and typical error separately | Saved baseline exists; typical agreement is not exact |
| RDS(on) | Specified current, gate voltage and temperature | Saved baseline exists |
| VSD | Specified reverse current and gate bias | Saved baseline exists; typical discrepancy requires disposition |
| CISS, CRSS, COSS | Each capacitance at the printed bias; consistent AC frequency convention | Saved baseline and Figure 5 checks exist |
| COSS(ER), COSS(TR) | Derive using the datasheet's energy/charge definitions and voltage range | Saved baseline exists |
| RG | Check implemented internal resistance and terminal interpretation | Recorded parameter agreement; not a dynamic validation |
| QG | Gate-current integration with declared origin, leakage treatment and endpoint | Saved baseline and Figure 7 checks; mismatch remains |
| QGS, QGD, QG(TH) | Explicit segment boundaries and both curve/table comparisons | Definitions/source inconsistency unresolved; do not fit silently to incompatible targets |
| QOSS | Output-current integration under the stated voltage/gate conditions | Saved baseline and Figure 6 checks exist |
| QRR | Distinguish stored-carrier recovery from capacitive displacement current | Not in saved table baseline; zero QRR must not be interpreted as zero commutation current |
| Figures 1 and 2 | Every output/transfer curve at its printed gate bias and temperature | Original model passes saved checks |
| Figures 3 and 4 | On-resistance curves at each printed current/temperature | Original model passes saved checks |
| Figures 5a and 5b | All capacitance curves on both scales | Original passes; EPC2302QG fails CRSS comparison |
| Figure 6 | Output charge and stored energy; cross-check their integral relation | Original passes saved checks |
| Figure 7 | Whole gate-charge curve, both voltage and charge errors | Original fails; EPC2302QG passes this figure only |
| Figure 8 | Reverse-conduction curves at each printed temperature | Original passes saved checks |
| Figures 9 and 10 | Temperature dependence of resistance and threshold | Original passes saved checks |
| Thermal-resistance table and Figure 12 | Separate thermal network(s), correct case/board boundary conditions, pulse and duty-factor response | Not established by the electrical model; do not combine incompatible thermal boundaries or substitute board-specific ambient resistance |
| Maximum ratings, Figure 11 SOA and repetitive-overvoltage duty-factor illustration | Application limit checks with current, voltage, temperature and duration; distinguish checks from physical failure prediction | Electrical curve agreement does not validate SOA, reliability or destruction behavior |
| Package, pin assignment, layout and assembly/thermal notes | Companion footprint/connectivity/layout/thermal checks where applicable | Not electrical curve-fitting targets; retain traceable coverage outside the SPICE subcircuit |

Figure numbers alone are not sufficient identifiers: this datasheet uses Figure 13
for both the overvoltage illustration on page 5 and the layout illustration on page 6.
Use page and caption in requirement records. Packaging/marking information remains
source metadata; it cannot be validated by running an electrical simulation.

## Recommended sequence

1. **Complete the executable coverage audit first.** Reuse saved evidence only after
   artifact/status checks. Add the missing electrical table checks. Read table column
   positions and footnotes directly before transcribing limits. Declare typical-value
   tolerances for newly covered rows before candidate results; retain existing curve
   tolerances. Report any table/curve definition conflict as unresolved. Do not move
   endpoints or widen tolerances after a failed fit.
2. **Start from the original model and fit jointly.** Freeze DC channel, resistive and
   leakage parameters during the first charge correction. Fit a small, declared set
   of existing charge parameters against Figures 5, 6 and 7 simultaneously, treating
   every curve's acceptance as a constraint. Minimize the worst normalized violation;
   do not let a good average hide one failing curve. Use full, charge-resampled traces,
   not plateau width alone. A failed local search does not prove infeasibility.
3. **If necessary, assess one small charge-model extension.** The candidate direction
   is additional gate-bias dependence, preserving off-state capacitance while changing
   switching charge. This is a hypothesis, not an identified physical cause. Derive
   consistent terminal charges and currents, including all cross-voltage derivatives;
   merely setting added charge to zero at VGS=0 does not preserve capacitance there.
   Require conservation, smooth behavior and no artificial energy generation from
   the added storage elements. Prefer a few interpretable parameters over a lookup
   table shaped only to one switching trajectory. Do not fit board overshoot.
4. **Run the complete electrical regression on a passing candidate.** All existing
   curve checks plus newly covered rows must have explicit outcomes. Recheck output
   energy, temperature behavior, reverse conduction and leakage. Check integration,
   terminal-current balance, smaller time steps/tighter tolerance, and a second drive
   current. Any regression rejects the candidate. New voltage/current/temperature
   probes without reference measurements are robustness checks, not validation.
5. **Complete thermal and limit-check coverage separately.** Fit or source an
   appropriate thermal model with matching boundaries; add ratings/SOA checks to the
   evaluation layer. Unsupported items remain open and prevent a full-datasheet claim.
   Do not impose an arbitrary breakdown clamp or label a successful transient as
   proof of reliability. A complete device representation may require electrical and
   thermal submodels plus operating-limit checks, rather than one electrical subcircuit.
6. **Then evaluate board consequences.** Keep board, driver, BOM and extraction fixed
   for matched comparisons with each model. Use assumed 50 pH and report 0 pH alongside.
   Report overshoot and settling using an explicitly declared settling band, observation
   window and remain-within rule. Preserve original predictions. Neither a desired
   board result nor a datasheet fit constitutes hardware validation.

## Proposed first execution boundary

Decision: can a small charge correction meet the joint dynamic targets without
breaking the rest of the electrical datasheet? The coverage audit precedes fitting.
For the first declared model family, propose at most four adjustable parameters,
40 fit evaluations or 20 minutes of solver wall time, whichever comes first, using
LTspice 26.1.1 and the existing adapter. These are proposed bounds, not permission to
silently broaden the search. Declare the exact family, parameter bounds, counted
calls and per-run timeout before execution. Stop on invalid numerics or exhausted
budget and retain every failure. A structural fallback requires its own recorded
method and budget. No board sweep is part of that first fit.

Acceptance uses the existing Figure 5 linear/log and Figure 7 vertical/horizontal
rules, plus Figure 6 and the remaining checks. The fixed final verification suite
gets an explicit run list and separate budget before it starts; no repeated solver
runs solely for metadata. Bind all imported helpers, data and vendor/derived files
in the candidate manifest. Store derived EPC model text in git-ignored vendor/ only.

Deliverable: candidate model if successful, whole-datasheet coverage report with
pass/fail/unresolved/unsupported states, numerical evidence, all regressions and
limits of use. If any required item remains open, report partial coverage rather
than claiming the whole datasheet has been satisfied.
