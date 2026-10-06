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

Added the same day, after a pointer from the owner: the EPC paralleling paper already held
(vendor/literature/EPC_Paralleling_High_Speed_GaN_Reusch.pdf, p. 4) says that "the LGA GaN transistor has a total
package inductance estimated to be under 0.2 nH". This is an estimate and an upper bound, for the LGA package rather
than EPC2302's QFN, and for the whole package path rather than the source part shared with the gate loop. It is
consistent with the 0 / 50 pH bracket, but it does not exclude larger source inductance (an even split of 0.2 nH
gives up to about 100 pH per terminal). In round 3 the R80 1.5 ohm benefit fell from about -33 % at 0 pH to -4 to
-11 % at 50 pH, so the lower end of the E4 prediction may be optimistic if the true value is above 50 pH. No rerun
is planned; E3's stock-board data constrain this before the swap, and a single 100 pH case would be added only if
the frozen prediction record needs it. The held paper is EPC application note AN020, "Effectively Paralleling
Enhancement Mode Gallium Nitride Transistors" (D. Reusch, 2016; confirmed on epc-co.com). Claims passed along with
this pointer that were not traced to a source and are not used: an MDPI "0.1 nH benchmark" (no paper named; none
of the held PDFs states a package value other than AN020's), WLCSP connections below 100 pH (no source; a different
package), and D2PAK at 5-7 nH (background figure, no source checked).

The MDPI source, identified later the same day by the owner: Singh and Tripathi, "Paralleling of Gallium Nitride
Power Semiconductor Devices: A Review and Future Perspectives", Electronics 2026, 15, 1607
(doi:10.3390/electronics15081607, CC BY; read in full from the owner's copy; the publisher blocks automated
download, so no local file). Its 0.2 nH (p. 11) repeats EPC's LGA estimate (its ref. [73], Reusch and Strydom,
PCIM 2014). Its 0.1 nH (p. 15, Fig. 11) is a simulation setting for the common-source inductance of one of two
paralleled half bridges (48 V to 12 V, 25 A), and a mismatch at which current sharing degrades. It is not an
extracted or measured package inductance, so the claim built on it misreads the source. The review gives no QFN or
EPC2302 value; it says only, without numbers, that QFN packages exceed LGA. Useful secondhand points:
- common-source inductance is ranked the most damaging parasitic, ahead of loop inductance, which agrees with
  tests 6-7 here;
- quoting its ref. [88] (Lu et al., APEC 2016), about 300 pH of common-source inductance raises turn-on loss by
  about 15 % and turn-off loss by about 10 %, and about 500 pH causes partial turn-off;
- its Fig. 14 is from EPC's layout presentation, already held.
Our board values (L_cs about 1 pH for Q1 and 48 pH for Q2, extracted) and the 0 / 50 pH package cases lie well below
those levels. Nothing here changes the E4 prediction or the package-inductance question.

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
