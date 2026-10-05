# Layout round 2: plan for 6 October 2026

Draft, 5 October 2026. For the owner and the working session. Nothing here is declared yet: each step's
declaration goes into its script's docstring and is committed before that step runs, as usual.

## Why a layout round

Round 1 (docs/build.md "design round 1") changed only parts on the stock board. Every gate-resistor change cut the
overshoot but raised Q1's switching energy and the FET loss, so no candidate met all three owner targets. In the
model, the way to get lower overshoot without a slower edge is a smaller power-loop (and common-source) inductance.
That is a geometry change. Round 2 asks:

> Which manufacturable geometry changes to the EPC90133 layout meet all three targets, overshoot lower, Eon + Eoff
> not higher and estimated 48 V -> 12 V efficiency not lower, with the stock gate resistors, under the same four
> unresolved alternatives and the same robust rule as round 1?

The targets, operating point, alternatives, robust rule and efficiency estimate are reused unchanged from round 1.
That keeps the two rounds comparable and stops the rule from moving after results come in.

## What we know going in

| Fact | Value | Source |
|---|---|---|
| Loop inductance by extraction variant | A 0.50 nH, B 0.28 nH, G 0.26 nH | build notes, extraction |
| Overshoot against loop inductance (13.8 V point, old bench) | A 55 V, B 36 V, ideal copper 2 V | build notes, test 1-4 |
| Top to mid-layer-1 dielectric (the power loop's return gap) | 0.127 mm (5 mil) | power-loop report |
| Input capacitors Ci1-Ci7 | row at y 33.8-35.3 mm; Q1 centre at y 31.0, Q2 at y 26.0 | power-loop report |
| Plated vias of VIN/SW/GND in the extraction window | 189, in 111 groups | power-loop report |
| Extraction cost | A about 90 s, B about 2 h, G about 3.4 h | extraction runs |
| Switching cost per case at 100 ps (with its timing run) | A about 1 min, G about 20 min | round 1 logs |
| Known stall | stock, step driver, 50 pH stalls at 100 and 50 ps at the 12 V point | round 1 fix runs |

Variant A (top layer and mid-layer 1, input capacitors only) has no gate loops and no inner layers. It can rank
changes to the power loop, but not to the common-source or gate routing, and its absolute numbers are not G's.

## Candidate changes, balancing effort and effect

| # | Change | Expected effect on loop L | Effort | Tooling needed | Manufacturability question |
|---|---|---|---|---|---|
| L1 | Thinner top to mid-layer-1 dielectric: 0.127 (stock), 0.100, 0.075, 0.050 mm | moderate; the vertical part of the loop scales with the gap, the lateral part does not | **easy** | a per-layer height override in the extraction (layer mid-planes come from the stackup) | which prepregs the fab offers; the stackup must stay symmetric or be accepted as is |
| L2 | More return vias next to Q2's source and the Ci ground pads (fill free space in the existing via groups) | small to moderate; the 189 vias already carry the return | **medium** | geometry-edit layer: add a via (drill + pads on each layer it connects) with clearance checks | drill size and spacing rules from the fab notes (vias at most 0.010 in are filled and plated over) |
| L3 | Input capacitors moved closer to the FETs (shift the Ci row toward Q1, or add a Ci pair beside the FETs) | potentially the largest: shrinks the loop area | **hard** | geometry-edit layer: move pads and the copper under them; re-check nets and clearances | placement against the gate driver and other parts; assembly rules |
| L4 | Kelvin or separated source return for the gate drivers (lower common-source coupling) | changes the excitation, not the loop L; may lower Eon | **hard**, and only on G | geometry-edit layer on G's gate nets | routing space near the driver |

**Balance:** start with L1, which is the cheapest and gives the first answer. Build the geometry-edit layer once
and use it for L2 first, the simplest edit, which also tests the tool. Attempt L3 only if L1 + L2 fall short. L4
needs G at every step and is costly, so it is listed but not scheduled for tomorrow.

Before any compute, a quick bound (step 1) tells us how much loop-L reduction the targets need. If L1's whole
range cannot deliver it even optimistically, we skip straight to L2/L3.

## Schedule for tomorrow

| Time | Step | Output | Stop or go |
|---|---|---|---|
| 09:00-09:30 | **0. Agree the round.** Owner confirms the question, the reuse of round 1's rule, the candidate list and the budget below. Owner answers the manufacturability questions or marks them "assume and record". | decisions recorded in this file | go when confirmed |
| 09:30-10:00 | **1. Required reduction (no solver).** From existing results, fit overshoot and Eon against loop inductance (A, I, B, ideal copper; round 1 stock). Estimate the loop-L reduction at which T1 (at least max(1 V, 10 %)) holds without R80 changes. | number with its basis, in the build notes | if L1's best case cannot plausibly reach it, start step 3 sooner |
| 10:00-11:00 | **2. Stackup override (code + check).** Add an opt-in layer-height override to `scripts/epc90133_extract.py` (default decks verified byte-identical, as for round 1). Known-answer check: the A extraction at stock heights reproduces 0.50 nH exactly. | code, test, declaration of round 2a | go if the reproduction is exact |
| 11:00-12:30 | **3. Round 2a: L1 on A.** 4 heights x A extraction (about 6 min in total), then switching under the 4 alternatives at the 12 V point (about 16 short runs). Assess with round 1's rule against A-stock. | report + assessment | if no height meets all three on A, L1 alone is not the answer |
| 13:30-16:00 | **4. Geometry-edit layer.** Raster edits applied before meshing: add via (drill, pads, layer span), with rule checks (clearance to other nets, drill size, keep-out of component pads) and a net check after the edit. Tests: an edit that breaks a rule is refused; adding a via to an existing group changes connectivity only where intended. | `src/circuit_tools/` module + tests | go if the tests pass |
| 16:00-17:00 | **5. Round 2b: L2 on A.** 2-3 via patterns (declared before running), alone and combined with the best L1 height. Same assessment. | report + assessment | pick at most two candidates for G |
| 17:00-17:40 | **6. Overnight launch.** The best one or two candidates on G (about 3.4 h each; at most two heavy WSL jobs at once, launched with Start-Process). Their switching cases run the next morning. | launch records | |

Budget for tomorrow: at most 12 A extractions, at most 40 A switching cases, at most 2 G extractions overnight.
Profile the first case of each kind before committing the rest, and set time limits from those profiles.

## Rules that carry over

- Declare before running: candidates, rule and budget in the docstring, committed and pushed.
- Compare like with like: a candidate is compared with stock in the same variant (A with A-stock, G with G-stock).
  A ranks candidates; G confirms them. An A result is never reported as a board prediction.
- A target is met only under all four alternatives. One failure means "not met"; a missing case means
  "undetermined", never "met".
- Results are frozen predictions for a redesigned board. They cannot be validated without fabricating it. The
  stock-board measurements (E1-E4) still decide whether the model's trends can be trusted.
- Keep failed and stalled runs. Do not tune the vendor model. Never kill processes by name, and keep the host's
  other project in mind.

## Decisions needed from the owner

1. **Fabrication route.** A redesigned board needs editable design files. We have Gerbers only; KiCad 10 and EPC's
   KiCad library are installed, but the route is undecided (no Altium request, under the no-inquiry decision).
   Tomorrow's work does not depend on it; a fabricated test does.
2. **Manufacturing constraints.** The fab's available prepreg thicknesses, minimum drill and annular ring, and
   whether the stackup may change. Without answers, each round records its assumption.
3. **A-ranking.** Whether ranking on A and confirming only the best on G is acceptable (recommended: yes, on cost).
4. **Common-source routing (L4).** Whether it is worth G-only compute later, given that the round 1 trade-off
   already involves common-source coupling.

## Not in scope tomorrow

Layout changes outside the power and gate loops, new parts or a different FET, thermal design, and any
energized measurement (still waiting on the equipment inventory).
