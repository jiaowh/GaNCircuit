# Research round 3: own-board geometry, gate resistor, efficiency and agent workflows

6 October 2026. Manifest: devices/literature-research-3-2026-10-06.json (URLs, SHA-256, reuse terms). PDFs are
in the git-ignored vendor/literature/2026-10-06-research-3/. Each entry below was read only to the depth stated in
the manifest's review_scope, mostly the abstract or scope page. Claims marked "search summary" come from search
results and have not been checked against the source.

Why this round: the project now has a best tested stock-board change (R80 1.5 ohm). The next open questions are the
geometry of our own board (G5), the E4 gate-resistor prediction, the E9 efficiency procedure and the agent-workflow
goal. The package inductance search was repeated because the R80 result's size depends on it.

## 1. EPC2302 package inductance: still not published

A search result suggested that EPC's 3x5 mm QFN overview lists package parasitic inductance. Page 5 of
Controllers_Gate_Drive_PCB_Layout.pdf (already held, research round 2) lists ratings, charges and thermal
resistance only. No EPC2302-specific value was found elsewhere. The 0 / 50 pH alternatives therefore stay
assumptions, and only measurement (E3/E4, optionally E8) can narrow them.

## 2. Geometry for our own board

- **Infineon DG165832 (2025)**, half-bridge design guide for 60-200 V GaN: component selection, PCB architecture and
  layout, optimisation process. **Infineon AN010933 (2025)**: stackup, placement and layout rules for a 100 V GaN
  part in a different package (PowIR-SMD). Both are vendor guidance from a second manufacturer, useful as an
  independent check on EPC's rules when we choose geometry levers.
- Search summary (Analog Devices article, not downloaded; DTU IAS 2020 paper already held): lateral loops have the
  highest inductance. Vertical loops (capacitors on the bottom) are lower. The "optimal" layout puts the
  capacitors next to the FETs on the same layer and returns the current on the first inner layer, and EPC90133
  already uses it. A further option places the FETs back to back on both sides with symmetric capacitors.
- Reading for G5: EPC90133 already uses the optimal-layout pattern, which agrees with round 2b's finding that the
  loop is saturated with vias. The remaining levers are the first-dielectric thickness (round 2a), capacitor size
  and position (L3), and structural changes such as double-sided placement. Double-sided placement needs the
  editable design (track R) and a fabrication budget.
- Rebuilding an editable design from Gerbers: KiCad's GerbView "Export to PCB editor" gives copper only, not a
  normal design (no nets or footprints), and negative polygons convert poorly (search summary, KiCad forum). The
  track R reconstruction therefore stays a manual or scripted footprint-and-net rebuild, checked against our own
  Gerber reader (src/circuit_tools/gerber.py).

## 3. Gate-resistor sizing (E4)

**Kozak et al., IEEE JESTPE 2019** derive 2nd- and 4th-order analytical models for the GATE-voltage overshoot of
normally-off GaN HEMTs at turn-on, including nonlinear capacitances. Given a target overshoot, the models give the
required gate resistance. The authors validate them with a double-pulse tester on an EPC part (EPC8010). The
quantity differs from round 3's objective (switch-node overshoot), but it bears on two things: Q1's own
gate-voltage margin when R80 changes, and an independent analytical cross-check for the E4 prediction record. It
is not a substitute for the simulated switch-node prediction.

## 4. Efficiency and FET-loss measurement (E9, constraint C1)

- **IEA 4E (2023)**: electrical efficiency measurements of Si and GaN chargers verified against calorimetry.
- **arXiv:2308.12685**: transistor loss from a thermal model, calibrated with low DC current at reduced gate
  voltage (so high current does not heat the tracks); Si, SiC and GaN.
- Reading: round 3's C1 is a FET-loss constraint, while E9 as drafted measures converter efficiency (input minus
  output power). The difference in FET loss between stock and R80 1.5 ohm is about 0.05-0.09 W in the model. That
  is well below what electrical input-output measurement resolves at 240 W, so the thermal method is the only one
  of these that could test C1 directly. Recommend adding a thermal FET-loss option to E9 (case-temperature rise,
  calibrated at low current) before E4 is approved.

## 5. Agent-driven design workflows

- **Agentic EDA: A Handoff Perspective (arXiv:2606.19795, Sep 2026)**: survey of 115 LLM-agent EDA systems
  organised by handoff objects between stages. It matches our I-1/I-2/I-3 handoff structure, and its abstract
  covers no power electronics or PCB layout.
- **D2S-FLOW (arXiv:2502.16540)**: LLM extraction of datasheet parameters for SPICE models, scored on retrieval
  accuracy; the abstract reports no electrical validation of the resulting models. Our Stage 1 instead validates the
  vendor model against digitized curves (G2), so stage-1 claims should cite validation, not extraction accuracy.
- **PHIA (arXiv:2411.14214)**: LLM agent for converter modulation design, not layout or device models.
- Reading: none found that combines device model, layout extraction and measurement closure for a power stage.
  That is a positioning note for the pipeline write-up, based on abstracts only.

## 6. Checked and not obtained

The Analog Devices article (download timed out; cite by link). Wu et al., IET Power Electronics 2022, on overshoot
and crosstalk in low-voltage GaN (access terms not checked). Zenodo 22799087, an open double-pulse dataset (CC
BY-SA 4.0) for a Si MOSFET, not GaN. EPC boards with EPC2302 and published files (EPC9165, already recorded as the
deferred second board; EPC90142; EPC9186) are candidate layout comparisons for G5, and their files are not
retrieved.

## How this changes the next work

1. E9: add a thermal FET-loss method as the only one of these that can resolve C1's 0.05-0.09 W effect (draft
   change, needs review).
2. E4 prediction record: include Q1's gate-voltage overshoot alongside the switch-node prediction. The Kozak models
   are an optional analytical cross-check.
3. G5 geometry: the lever list is gap, capacitor size and position, and double-sided placement. Double-sided
   placement and capacitor moves need track R and a fabrication budget (owner question).
4. Package inductance stays a measurement question.
