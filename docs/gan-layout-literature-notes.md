# Board-level GaN layout, extraction and switching literature: notes for G3/G4

Read 29 September 2026. Files and checksums: [devices/literature-sources.json](../devices/literature-sources.json)
(the PDFs stay in the git-ignored `vendor/literature/`). These are vendor descriptions and
published methods. None of them validates our extraction or switching bench.
The four IEEE papers found in the search were not available and are not used.

## What each source contributes

| Source | What it provides | Limits for our use |
|---|---|---|
| EPC AN005, *Circuit Simulation Using EPC Device Models* (2019) | The model structure: nonlinear charge sources for CGS/CGD/CDS, a MESFET-like channel current, and constant RD, RS, RG "that depend on the device and package parasitic resistances". There is no package inductance and no loss element in the capacitances. EPC's own comparison with a measured test circuit is described as "not perfect; overshoot and ringing is qualitatively reproduced". | It describes the V091 model generation (EPC1001/EPC2001 era). The EPC2302 library model may differ; its structure matched EPC2204's (docs/build.md), but that has not been checked against AN005. |
| EPC WP010, *Optimizing PCB Layout* (Reusch, 2019) | The first-inner-layer return layout that the EPC90133 uses. On EPC2015 buck boards (12 V, 4-layer, 2 oz): the optimal layout gives about 0.4 nH, and measured overshoot falls from 100% of VIN at 1.6 nH to 30% at 0.4 nH. Inductance depends on the top-to-inner-layer distance, not on board thickness. | The inductances are EPC simulations with an unnamed tool; the overshoot is EPC's measurement. The device, voltage and stack differ from ours. |
| EPC layout webinar slides | Rules for the design: place vias as close as possible to the innermost connection, spread the via connections, and "the GND return does not need to carry full current". An example shows 1.0 nH with 70% overshoot and 0.4 nH with 30%. | Presentation only; no method is given. |
| EPC WP009, Reusch and Strydom on paralleling | Common-source and loop inductance drive losses; the LGA package inductance is estimated below 0.2 nH. | The EPC2302 is a QFN, not an LGA, and its package inductance is not given. |
| DTU, IAS 2020 accepted manuscript | ANSYS Maxwell FEA at 500 MHz, a fast analytic loop model, and loop inductance measured from the drain-source ringing frequency with the known Coss in DCM at a 50 V bus (400 MHz passive probe), agreeing within 7% with their equation. EPC2029 (80 V): 1.7 nH vertical layout, 1.1 nH minimal layout. The layout also adds switch-node capacitance through plane overlap. | Their numbers are their layouts. |
| Chen et al., *Energies* 2026, 19, 383 (CC BY) | Ansys Q3D 2023 extraction of a 650 V GaN double-pulse board. The inductance changes little with frequency (8.50 → 8.43 nH, 10 MHz → 1 GHz), while the AC resistance rises about threefold per decade (5.9 → 17.2 → 53 mΩ). Spreading the vias lowers the loop inductance by about 12–26%. The loop inductance is inferred from the ringing frequency (26–29 nH, with a 250 MHz probe). | The loop is 30–100 times ours. |
| Mistri et al., *Electronics* 2026, 15, 3079 (CC BY review) | Probes below about 500 MHz underestimate overshoot by 5–15%. Recommended system bandwidth is 3–5 times the signal content. Voltage-current synchronization should be within 5% of the transition (200–500 ps for 1–5 ns edges). Coaxial shunts add loop inductance, which matters on 48–100 V boards. It tabulates typical ranges of loop, gate-loop and common-source inductance. | Secondary review; its typical ranges (3–10 nH for "optimized multilayer PCBs") do not describe EPC-class layouts. |
| Nexperia, *Switching evaluation of fast GaN devices* (2021) | System bandwidth combines scope and probe (for example, a 350 MHz scope with a 200 MHz probe gives a 174 MHz system and 18% amplitude error). Switch-node and inductor-winding capacitance are listed as main parasitics. | Vendor tutorial. |

## Implications for our work

1. **Our copper extraction is lower than published values for similar layouts, and it omits known terms.**
   The coarse-mesh B result, 0.28 nH, is below EPC's 0.4 nH (a different, older board) and DTU's 1.1–1.7 nH
   for 80 V EPC parts. That comparison is only a plausibility check. Two omissions bias our loop inductance low:
   - the EPC2302 package, since the vendor model has no package inductance (AN005 structure);
   - capacitor mounting inside the body, which the bench carries only as an assumed ESL.
   A package-inductance sensitivity case is needed. Its value for the QFN is unknown and must be stated as an
   assumption, not taken from the LGA estimate.
2. **Switch-node capacitance from the layout is missing.** FastHenry gives only inductance and resistance.
   The SW pours on G5/G6/bottom lie over GND and VIN copper, and DTU and Nexperia list this capacitance as a main
   parasitic. It lowers the ringing frequency and adds switching loss. A parallel-plate estimate from the
   Gerber overlap areas is a quick first bound; FastCap (the companion tool) would need its own qualification.
3. **The bench's damping is not established.** At 100 MHz the extracted loop resistance is about 4 mΩ, and the bench holds it fixed.
   Q3D results show copper AC resistance rising about threefold per decade; at the simulated 200 MHz ringing
   that is a modest increase and does not explain the gap alone. AN005 says EPC's own model reproduces
   overshoot and ringing only qualitatively.
4. **The measured waveform is not yet a quantitative target.** By eye, QSG Fig. 9 shows about 7 V
   of rise-edge overshoot and ringing near 0.6 GHz. The simulation gives 55 V at 0.2 GHz. The probe, scope
   bandwidth and probe connection behind Fig. 9 are not stated. A 0.6 GHz ring needs roughly a 2–3 GHz system to
   be measured with small error, so the measurement chain can distort both the amplitude and the frequency.
   Fig. 9 should be digitized with a declared method, and any comparison should pass the simulated waveform through
   an assumed probe/scope response and state that assumption.
5. **Candidate isolating experiments for G4** (per-layer error budget, plan section 4):
   - loop inductance from the ringing frequency with known Coss at a low bus voltage (DTU), repeated
     with a known added capacitance to separate L from C;
   - probe bandwidth and deskew characterization on a known edge before comparing edges;
   - comparison of the stock board with and without the Cm population, which separates the two stacked loops.
6. **Tool choice.** The papers use Ansys Q3D and Maxwell (FEA) for board extraction, and one power-module paper uses
   FastHenry as its reference. That supports FastHenry as a reasonable open choice, not our unqualified
   via-array and plane-hole cases. The plan's declared EM cross-check (G5) remains to be chosen.
