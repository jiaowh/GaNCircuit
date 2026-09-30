# Targeted references for source-return extraction and measurement

Collected 30 September 2026 while the implementation worker was active. This is a separate supplement; no simulation, extraction or existing literature files were changed. Provenance: [source manifest](../devices/literature-supplement-2026-09-30.json). Downloaded PDFs remain under the git-ignored `vendor/literature/2026-09-30-supplement/`.

## What is worth reading now

### 1. EPC AN003: Using Enhancement Mode GaN-on-Silicon Power FETs

[Official PDF](https://epc-co.com/epc/Portals/0/epc/documents/product-training/using_gan_r4.pdf), downloaded. Read page 3, Figures 8-9, alongside the already collected WP009.

The note explains how common-source inductance couples power-current slew into gate voltage and can produce off-state gate ringing and unintended turn-on. Its layout advice separates gate and power returns close to the device.

Project implication: reducing the switch-node peak through source feedback is not sufficient evidence of an improved design. Inspect both devices' intrinsic VGS, drain current and loss as well. The note does not supply EPC2302 package inductance or validate our assumed 25-50 pH values.

### 2. Woehrle, Burger and Ambacher (2023): Power Module Design for GaN Transistors Enabling High Switching Speed in Multi-Kilowatt Applications

[Publisher full text](https://doi.org/10.1002/ente.202300460), [Fraunhofer repository and licence](https://publica.fraunhofer.de/entities/publication/fe5552b0-e231-4ea4-a8eb-d1b4762cffc8). Full HTML reviewed, particularly section 5 and Tables 1-2. PDF retrieval failed (repository connection reset; publisher HTTP 403). Repository declares CC BY 4.0.

This is a 650 V module design with finite-element extraction and switching simulation. It separately extracts power/gate loop quantities and their mutual coupling; reported power-to-gate mutual terms are 36 pH on the high side and 18 pH on the low side. These are geometry-specific simulated values, not measurements of our board.

Project implication: retain the power-to-gate-return mutual terms even with a Kelvin connection. A shared copper segment alone need not describe all coupling. Do not copy these values into EPC90133. Use the extraction and equivalent-circuit discussion as a method reference.

### 3. EPC AN023: Accurately Measuring High Speed GaN Transistors

[Official PDF](https://epc-co.com/epc/Portals/0/epc/documents/application-notes/AN023%20Accurately%20Measuring%20High%20Speed%20GaN%20Transistors.pdf), downloaded. Read page 4, Table 3 and Figures 7-9, and the following discussion of differential measurements.

EPC compares probe grounding arrangements and near/far probing positions on EPC9080. Its examples show why probe connection inductance and input capacitance matter in addition to bandwidth.

Project implication: the hardware plan should record probe model, tip/return arrangement and exact copper pickup points, and characterize the measurement path. Our Gaussian filtering study does not cover these resonant or loading effects. This note does not identify the probe used for EPC90133 QSG Fig. 9.

### 4. TI SSZTBC7: Power Tips: Calculate an R-C Snubber in Seven Steps

[Official PDF](https://www.ti.com/lit/pdf/ssztbc7), John Betten, May 2016; downloaded. Frequency-shift method on pages 1-2.

It estimates an equivalent resonant L and C by adding capacitance and observing the frequency shift. Use as a reference for designing the proposed added-capacitance experiment, not as a prescription to add a snubber to the stock board.

Our interpretation: the experiment needs the same identifiable ringing mode before and after the change. Added-capacitor mounting impedance, voltage-dependent capacitance, probe loading and damping can affect the inferred equivalent values. The result would not independently identify every branch inductance. The PDF's notice restricts reuse; no open licence is established. Cite the method; do not redistribute the PDF or reproduce its figures.

## Relevant papers found but not fully obtained

- Ke Li, Cyril Buttay, Angel Pena Quintal and Paul Evans, *Investigation of Mutual Inductance on GaN-HEMT Switching in a Half-Bridge Circuit*, IEEE DMC 2024, [DOI 10.1109/DMC62632.2024.10812133](https://doi.org/10.1109/DMC62632.2024.10812133). Publisher abstract reviewed only. It reports Q3D extraction, circuit reduction and experimental comparison of coupling effects. A particularly relevant full-text candidate; do not implement its reduction method from the abstract alone. No accessible author manuscript was located in this search.
- Maria Giorgia Spitaleri, Francesco Iannuzzo, Emre Gurpinar and Giacomo Scelba, *Systematic investigation on the effects of tracks' mutual coupling on a GaN-based three-level bridge leg*, Power Electronic Devices and Components 12 (2025), 100120, [DOI 10.1016/j.pedc.2025.100120](https://doi.org/10.1016/j.pedc.2025.100120), [SSRN preprint record](https://ssrn.com/abstract=5212922). Publisher abstract/highlights and preprint record reviewed only; full PDF not obtained. Simulation study emphasizing power/gate-return mutual terms. Publisher labels it open access under a Creative Commons licence, but the exact variant was not verified. Different topology and voltage class; not an EPC90133 benchmark.

## Material already available, and one revision caveat

The uP1966E Aug. 2021 datasheet is already stored and checksummed in `devices/epc/sources.json`; no duplicate was downloaded. The current [uPI product page](https://www.upi-semi.com/upisemi/products/ic/gan-solution/gan-fet-driver/up1966e/) advertises 30 ns typical propagation delay and 6.7/3.9 ns rise/fall times. These headline values differ from the older EPC-hosted datasheet used by the project. Do not silently replace the pinned driver calibration: first resolve document revision and test conditions if revisiting timing. This difference does not establish the cause of the inferred dead-time discrepancy.

## How this changes the next work

1. Extraction: represent actual gate and return pickup ports and preserve their coupling to the power network; keep package and PCB contributions distinct.
2. Simulation review: observe intrinsic VGS and current alongside switch-node overshoot before interpreting source feedback as beneficial.
3. Hardware planning: specify probing geometry and a controlled added-capacitance experiment with a mode-identification check and held-out operating points.

No further broad literature collection is needed before the next extraction result. The two abstract-only papers are useful reading leads, not blockers. None of these sources closes G3, establishes our package values or changes the decision not to contact EPC.
