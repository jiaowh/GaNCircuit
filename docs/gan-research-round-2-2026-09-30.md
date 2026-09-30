# Research round 2: lab instruments, damping and passive loop measurement

Collected 30 September 2026. This round targets questions the earlier notes left open ([layout notes](gan-layout-literature-notes.md), [source-return supplement](gan-reference-supplement-2026-09-30.md)) and the hypotheses H1-H6 of the [draft hardware plan](epc90133-hardware-test-plan.md). Provenance, checksums and reuse terms: [manifest](../devices/literature-research-2-2026-09-30.json). The PDFs are in the git-ignored `vendor/literature/2026-09-30-research-2/`. No simulation, extraction or plan file was changed.

## 1. Pinned EPC files are current

The EPC2302 datasheet and the EPC-hosted uP1966E datasheet were downloaded again. Both are byte-identical to the pinned copies, so EPC has not silently revised them. uPI's product page quotes timing figures that differ from that datasheet (see the earlier supplement) but links no datasheet to compare against. The driver-revision question therefore stays open, and the pinned calibration stays in use.

## 2. What the lab's Keysight instruments can and cannot do for this project

**PD1550A (double-pulse tester): not suitable for EPC2302 switching.** Its data sheet describes a power-module system. The standard interface boards take 62 mm and FM3 modules, and other packages need a custom board designed with Keysight. Its voltage and current probes are specified at 200 MHz. Our edges are 1.7-3.6 ns and the ringing is about 264 MHz, so that bandwidth would distort exactly the quantities in question (the earlier Nexperia note: probe and scope bandwidths combine). A PD1550A result would also describe the device in Keysight's fixture, not in the EPC90133 layout. It does not replace board measurements.

**B1506A (power device analyzer): useful for the device layer, with a fixture to arrange.**

- Capacitances (Ciss, Coss, Crss, Cgs, Cgd) at 1 kHz-1 MHz with bias up to 3 kV. This covers the EPC2302 table and curve conditions (Coss 1.0 nF at 50 V).
- Gate charge (Qg, Qgs1/Qg(th), Qgs2, Qgd), range 1 nC-100 µC, 10 pC resolution, only with the H21/H51/H71 fixture options and the gate-charge socket adapter. EPC2302 QG is 23 nC, so the range is adequate. The data sheet lists the drain voltage under high current as not supported for one option and ±60 V for the others. Whether the lab unit can reproduce the datasheet condition (VDS 50 V, ID 50 A) depends on its fitted option. Confirm the option before planning around it.
- No standard socket for a 3 × 5 mm QFN is listed. A small adapter board on the universal socket module would be needed. At these measurement frequencies its inductance matters little. Its stray capacitance must be removed by open compensation and stated.
- The gate-charge function is specified "for Nch MOSFETs and IGBTs". An EPC2302 is an n-channel enhancement device, but its gate is limited to +6/−4 V. The gate drive settings must respect that limit, and the first test should use a sacrificial part.

**Why this matters.** G2 left the Fig. 7 gate-charge discrepancy (plateau 24% narrow) and the table sub-charges (QGD, QG(TH)) unresolved. H5 in the hardware plan needs the device's actual Miller charge. A B1506A measurement on a few EPC2302 parts would provide device-layer evidence independent of the board. That separation is what the per-layer error budget needs. Part-to-part spread must be recorded: one part is not the datasheet's typical value.

## 3. Output-capacitance loss as the missing damping (H3)

- Samperi et al. (Energies 2025, CC BY) review Coss hysteresis loss measurement methods (Sawyer-Tower and variants). Across the cited studies, GaN HEMTs show the lowest hysteresis loss of Si superjunction, SiC and GaN. Matioli et al. (EPFL) describe the same methods and a steady-state dynamic RON method.
- Zhu, Matioli et al. (IEEE TPEL 2024, author version) propose a resonant-Sawyer-Tower method that avoids hard turn-off losses. They measure six commercial GaN HEMTs, all rated 600-650 V. The dissipated energy depends on peak voltage, transient frequency and, for some parts, switching frequency.
- Almost all published measurements are on 650 V GaN. **No Coss-loss data for 100 V EPC parts was found.**
- Our interpretation: the literature does not support assuming that Coss loss alone explains the measured damping ratio (0.072-0.077, against 0.008 for the B baseline in results/gan/epc90133-fig9-summary.md). It does not exclude it either. H3's prediction in the hardware plan (damping changes with bus voltage and temperature, not with the probe) remains the right test. A Sawyer-Tower measurement on EPC2302 would be a separate device experiment and an extension, not core scope.

## 4. Measuring loop inductance without switching

These methods could give layout-only evidence on the unpowered board before any switching test. That would separate the layout layer from the device and driver layers.

- **Impedance analyzer, devices gated on** (Wolfspeed PRD-08710, 2024). Measuring across the DC link with the FETs off gives a series RLC dominated by Coss. With the gates biased on, the Coss term is removed and the loop becomes a series R-L. The note recommends a frequency on the high-frequency inductance plateau and inside the analyzer's accurate range (it suggests 10 MHz, and names an E4990A, 20 Hz-120 MHz). It covers open/short compensation and residual removal. Limitation for us: the note is written for SiC modules of several nH. At 10 MHz, 0.3-0.5 nH is only 19-31 mΩ of reactance, similar to the loop resistance. Fixture residuals would need to be well below 0.1 nH. Applicability to our loop is not shown and would need its own known-answer check.
- **Resonance of a modified DC-link capacitor** (EPE 2023, IEEE 10264516, abstract only): reports sub-nH commutation-loop measurements on a GaN half-bridge in agreement with simulation. Full text needed before using the method.
- **Incremental VNA shunt-thru measurement** (Tranchero et al., Zenodo 20617321, June 2026, CC BY 4.0). One FET position is replaced by a short and the two VNA ports connect across the other. Capacitors are then added one group at a time, so each contribution is measured by difference. On a 650 V GaN inverter they measured 4.5 nH for PCB plus DC link, against 5.9 nH from double-pulse voltage drops. They attribute the 1.4 nH difference to the package, close to its 1.2 nH datasheet value. Their 8 mm fixture was not de-embedded, which they justify for a loop of several nH. For our 0.3-0.5 nH loop, de-embedding would be essential.

For the EPC90133 there are two routes. Gating the FETs on needs both gates on at once. (Correction after an external audit, 30 September 2026: an earlier version said the driver normally prevents this. The uP1966E datasheet, p. 5, states that there is no lockout between its HI and LI inputs; any protection comes from the board's input and dead-time circuitry, which is not assessed here.) The shunt-thru route avoids that but needs the FETs removed, so it should use a second board or a bare PCB, not the board used for switching tests. Either route needs a sub-nH known-answer check (for example a short strip of known geometry) before its result is trusted. The package inductance could then be estimated as switching-derived loop inductance minus the passive measurement, as that paper does, but that difference carries both measurements' errors.

## 4a. Keep the power-to-gate-return mutual terms

Spitaleri et al. (PEDC 2025, CC BY-NC-ND; Q3D simulation of a 400 V three-level GaN leg) build reduced models from the full RL matrix. With self-inductances only, switching energy deviates from the complete model by up to 13%. Keeping the mutual terms between each power source path and its gate return reduces this to 3%. This supports extraction variant G keeping every mutual term in the network rather than reducing it to loop and source self-inductances. Their numbers are for their layout and do not transfer to ours.

## 5. Checked and not found

- **EPC2302 package inductance.** EPC's layout slides (rev. 3/2024) and How2AppNote 031 (EPC9165, four EPC2302) define the parasitics and repeat the layout guidance. Neither gives a package value. The 25-50 pH cases stay assumptions, consistent with the owner's decision not to ask EPC.
- **Newer EPC model library or thermal model.** No announcement of a revised EPC2302 model was found. The pinned library remains the baseline.
- **An open-source full-wave EM tool used for sub-nH GaN loop validation** (candidate for the G5 cross-check). Published validations use commercial tools (Q3D, Maxwell, ADS). Choosing the G5 tool stays open.

## How this changes the next work

1. **Owner inventory question.** Which B1506A fixture option is fitted (H21, H51 or H71), and is there a QFN adapter or budget for one? If available, device-level Qg and C-V on several EPC2302 parts is the most direct way to settle the open G2 gate-charge item and H5.
2. **Hardware plan.** Record that the PD1550A is not a substitute for board switching measurements (fixture and 200 MHz probes). Add an optional passive loop-inductance measurement: VNA shunt-thru on a second, depopulated board, or an impedance analyzer with the gates held on. It needs a sub-nH known-answer check and fixture de-embedding. Ask the owner whether a VNA or impedance analyzer is available.
3. **Simulation.** Nothing here changes the next step: complete the G extraction and test 7.
