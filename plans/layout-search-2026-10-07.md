# EPC90133 layout candidate search (declared 7 October 2026)

Owner instruction (7 October 2026): keep searching for layout candidates until one is found; substantial rebuilds
are accepted. This file fixes the success criteria and the method before any search run.

## What counts as a found candidate

All of the following, against stock built through the same route (matched control):

1. **Legal board**: built with the qualified edit workflow (`scripts/epc90133_edit_workflow.py` primitives,
   `scripts/epc90133_board_export.py`), DRC as stock (0 unconnected, no shorts, no clearance below EPC's 0.150 mm,
   isolated copper as stock, no new DRC types), pad nets equal to stock's, power-loop contact checks C2-C5 pass.
   New primitives get their own dry check and DRC before use.
2. **Loop inductance change beyond the representation uncertainty**: more than 4 % lower than stock through the same
   route, in the extraction variant the candidate is judged on.
3. **Owner rule (5 October 2026)** in the switching simulation under all four alternatives (ramp/step driver x
   assumed package source inductance 0/50 pH): worst-case overshoot lower than stock's, FET loss (estimator revision
   2, settled) at most 5 % above stock, Q2 gate peak not above stock.

A stackup-only change (dielectric thickness) counts as a candidate if it meets 2-3; it needs no geometry legality
beyond the stackup itself, but must be stated as a fabrication-specification change.

## Method

1. **Screening (upper bounds, not designs).** Idealized raster edits on EPC's geometry (`scripts/epc90133_layout_screen.py`),
   variant A (top + mid-layer 1, about 2 minutes), each against stock A. A screen that cannot reach 4 % even
   idealized is dropped. Screens are labelled screening; no screen result is a candidate.
2. **Legal build** of promising ideas through the KiCad route, variant A first (cheap), compared with stock through
   the route.
3. **Confirmation** on variant B (all copper + bottom bank) when the idea touches vias or layers that A omits, and on
   G for the switching rule (C2 needs the gate network). Large solver jobs one at a time (8 GB WSL).
4. **Switching** with the declared four alternatives, assessed by the owner rule.

## Families to examine (order: cheapest informative first)

- F1 return-plane slots on mid-layer 1 (In1) under Q1/Q2 and under the input capacitors: per-via antipads instead
  of merged slots, or fewer/relocated vias.
- F2 return-via placement (L3b): capacitors with their GND return vias moved toward the FETs, with the bottom bank
  and bottom switch-node copper rebuilt to allow it.
- F3 stackup: thinner top-to-In1 dielectric (round 2a: 0.050 mm meets every rule except C2 by +3 mV in the 0 pH
  cases), alone and with R80 1.5 ohm (untested combination; needs G).
- F4 connections: Kelvin/separated gate-driver returns (L4), judged on G.

## Rules kept

Declare each screen/candidate in code before its run; keep failed and rejected runs; label retrospective changes;
time limits from profiles; no claim beyond the model (exploratory extraction, unvalidated device model, behavioural
driver). A found candidate is a simulation prediction to test against hardware, not a validated improvement.
