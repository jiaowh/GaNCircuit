# EPC90133 hardware test plan (draft v0.1, 30 September 2026)

Status: **draft for owner review; not approved.** Nothing is energized until G4's test plan and interlocks are
approved (plan section 8). This draft follows plan section 4 (Stage 3), section 7 (safety) and the external
reviews of 30 September 2026. It measures the stock board first, as the plan requires.

## Purpose

The simulation does not reproduce EPC's published switch-node waveform (QSG Fig. 9). Its overshoot is several
times larger, its turn-on is faster and its ringing decays more slowly (docs/build.md, tests 5–7). Several
explanations remain, and one published waveform cannot tell them apart. The measurements below are chosen so that
each explanation predicts a *different pattern* across operating conditions, not one matching waveform.

| # | Candidate explanation | What it predicts that the others do not |
|---|---|---|
| H1 | Common-source inductance (board source copper shared with the driver return, and/or inside the package) slows the turn-on | Rise time and overshoot depend on the turn-on di/dt: rise time grows with switched current; the gate-source voltage at the die shows a dip during the current rise |
| H2 | The real driver is weaker or slower than the behavioural model | Rise time depends on the gate resistor value but not on current or bus voltage; the driver's output edge, measured with the power stage off, is slower than modelled |
| H3 | Losses missing from the model (output-capacitance or dielectric loss) damp the ringing | Damping depends on bus voltage and temperature, not on the probe; the ringing frequency stays at the loop's LC value |
| H4 | The measurement chain (probe loading, ground path, bandwidth) shaped EPC's recording | Changing the probe or its connection changes the recorded overshoot and frequency while the circuit is unchanged |
| H5 | The model's gate charge (the EPC2302 Fig. 7 discrepancy) slows or speeds the Miller interval | Rise time scales with the measured Miller charge; device-level gate-charge measurement differs from the model |
| H6 | The actual dead time is shorter than the nominal 10 ns | The dead-time plateau measured at the driver outputs, with no power stage load, differs from 10 ns |

These explanations are not exclusive. The aim is to bound each one with its own evidence (the per-layer error
budget).

## Board facts and limits (QSG v1.0, Table 1)

- Gate-drive supply VDD 7.5–12 V (J1). PWM logic high 3.5–5.5 V, edges under 10 ns, minimum pulse widths
  50 ns (high) and 200 ns (low).
- Bus VIN up to 80 V. **The switch-node ringing must stay below 100 V** for the EPC2302. Output current up to 40 A,
  limited by die temperature.
- Start-up order: gate-drive supply, then PWM, then raise the bus slowly from 0 V.
- Dead time is set by R620/R625 (120 Ω populated, nominally 10 ns).
- The switch-node MMCX J32 is described in the guide but absent from the published layout. Plan the probe
  connection from the actual board.

## Safety envelope (independent of the software)

- A current-limited bus supply with hardware over-voltage and over-current trips, a bus-discharge path, the
  enclosure interlock and an emergency stop (plan section 7).
- A hardware limit on double-pulse width, so the inductor current cannot run away if the PWM source misbehaves.
- The first energization is at **12 V bus**. The bus rises in steps (12, 24, 36, 48 V), with a human checkpoint at
  each step. At each step the measured switch-node peak must leave margin to the 100 V limit before the next step.
  **The simulated overshoots are sensitivity results, not a safe envelope**: the unvalidated full-board simulation
  reaches about 84 V at 48 V.
- Any instrument control by software goes through a non-LLM layer that enforces this envelope.

## Equipment checklist (to compare with the lab inventory)

| Need | Why | Minimum | Preferred |
|---|---|---|---|
| Oscilloscope | edges of 1–4 ns, ringing near 250 MHz | 1 GHz, 5 GS/s, 4 channels | 2 GHz or more, 10 GS/s or more |
| Switch-node probe | the main waveform; H4 | 1 GHz passive probe with a spring-tip or solder-in connection at the Q2 pads | optically isolated high-bandwidth probe (IsoVu class) for comparison |
| Second switch-node connection | H4: the same node through a different connection | a different ground path (e.g., a long ground lead) for a deliberate comparison | — |
| Low-side gate probe | H1, H2 (gate-source voltage) | 500 MHz passive probe at Q2's gate and source pads | — |
| High-side gate probe | H1, H2 on Q1 | — | optically isolated probe (common-mode rejection at 48 V, 10+ V/ns) |
| Inductor-current probe | double-pulse current (H1 needs the switched current) | 50 MHz current probe, 30 A | — |
| Deskew and edge source | probe timing and bandwidth (H4) | a deskew fixture; a pulse generator with sub-ns edges | — |
| Bus supply | power stage | 0–60 V, 10 A, current limit and OVP | 0–80 V |
| Gate-drive supply | VDD | 7.5–12 V, 1 A | — |
| Pulse generator | PWM and double pulse | 2 channels, 5 V logic, edges < 10 ns, burst mode | — |
| Double-pulse inductor | known load | an air-core or low-capacitance inductor of about 2–10 µH, rated for 30 A peak | — |
| Buck load (E6) | continuous operation at Fig. 9 conditions | 2.2 µH inductor (QSG), electronic or resistive load for 20 A at 13.8 V | — |
| Known capacitors | loop inductance by frequency shift (E2) | C0G 0402/0603 of 47, 100 and 220 pF | — |
| Thermal control | the core scope includes controlled test temperature | thermocouple on the case; heatsink per QSG Fig. 10 | hot plate or chamber for a second temperature |
| Device analyzer (lab has a B1506A) | H5: EPC2302 gate charge and capacitances measured on spare devices | a fixture or adaptor that fits the EPC2302 package | — |
| Double-pulse tester (lab has a PD1550A) | device switching in a known fixture, if a fixture for this small GaN package exists | — | — |

## Experiments

Each experiment records the raw waveforms, all instrument settings, the probe and its connection, the board
identity (silkscreen revision, fitted population), the case temperature and the time.

- **E0, measurement chain first.** Probe deskew on a known edge. The step response of each probe and connection
  gives its bandwidth and ringing. Without this, no device or layout conclusion is drawn (plan section 4).
- **E1, driver alone (H2, H6).** Power stage unpowered (VIN = 0 V): measure PWM-to-gate delays, gate-voltage
  edges and the dead time at the gate pins. This isolates driver timing and strength from the power stage.
- **E2, loop inductance by frequency shift (parasitic layer).** At a low bus (12–24 V) and low current, measure
  the ringing frequency, then add a known C0G capacitor across Q2 (drain to source) and measure again. The shift
  gives the loop inductance and the effective capacitance, independently of damping. Compare with the extracted
  0.26–0.28 nH (variant B).
- **E3, double-pulse matrix (H1, H2, H3).** Bus at 24, 36 and 48 V; turn-on current at 5, 11 and 20 A; turn-off
  current at 10, 20 and 29 A. Record the rise and fall times, overshoot, ringing frequency and damping, and, where
  the probes allow, the low-side gate-source voltage. Signatures:
  - rise time growing with current points to H1 (common-source);
  - damping changing with bus voltage at a constant frequency points to H3;
  - neither current nor voltage changing the rise time points to H2.
- **E4, gate-resistor change (H2 against H1).** Replace R80 (1 Ω) with 2.2 Ω, and repeat part of E3. The model
  predicts how rise time and overshoot scale with the gate resistance under H1 and under H2, and the predictions
  differ.
- **E5, second temperature.** Repeat an E3 subset at a controlled higher case temperature (for example 75 °C):
  RDS(on), damping (H3) and switching times.
- **E6, Fig. 9 conditions with a known probe (H4).** Continuous buck, 48 V → 13.8 V, 20 A, 250 kHz, 2.2 µH, with the
  E0-characterized probe. Then repeat with a deliberately different probe connection. If our trace differs from
  EPC's published one, and the connection change reproduces part of the difference, the measurement chain
  explains part of Fig. 9.
- **E7, device characterization (H5), if a fixture exists.** Gate charge, capacitances and RDS(on) of spare EPC2302
  samples on the B1506A, compared with the unmodified model and the datasheet Fig. 7. Only this evidence, if it
  isolates a device discrepancy, could justify a separately stored tuned model revision.

## Held-out conditions and frozen predictions

Before any measurement, freeze the simulation's predictions (model and extraction revisions, bench settings,
predicted metrics with their stated sensitivity ranges) for all conditions. Use E0–E4 at 24–48 V for calibration
and diagnosis. Hold out, and score unchanged:

- the bus at 60 V (below the 80 V rating and only if the measured peaks leave margin to 100 V);
- turn-off at 25 A with R80 = 2.2 Ω;
- the second temperature.

Report the first held-out score as it is; later corrections create new revisions and do not overwrite it.

## Open items for the owner

1. The lab's oscilloscope and probes (bandwidth, isolated probe, current probe), supplies and pulse generator,
   compared with the checklist above.
2. Whether spare EPC2302 devices and a B1506A fixture for them can be obtained (E7).
3. Approval of the envelope and the step-wise bus increase before G4.
