# EPC90133 hardware test plan (draft v0.2, 30 September 2026)

Status: **draft for owner review; not approved, and not yet an executable lab procedure** (the envelope values
below are still open). v0.2 applies an external audit: the driver has no input lockout, the driver's PHASE/BOOT
ratings are tighter than the FET's, and categorical signatures became quantitative predictions. A further audit (1 October 2026) made Q2's gate-source voltage a prerequisite throughout E3 and recorded the simulated PHASE-ball stress as unresolved; test 8 narrowed it, and the PHASE-to-GND undershoot near the driver became a stop criterion. Nothing is energized until G4's test plan and interlocks are
approved (plan section 8). This draft follows plan section 4 (Stage 3), section 7 (safety) and the external
reviews of 30 September 2026. It measures the stock board first, as the plan requires.

## Purpose

The simulation does not reproduce EPC's published switch-node waveform (QSG Fig. 9). Its overshoot is several
times larger, its turn-on is faster and its ringing decays more slowly (docs/build.md, tests 5–7). Several
explanations remain, and one published waveform cannot tell them apart. The measurements below are chosen so that
each explanation predicts a *different pattern* across operating conditions, not one matching waveform.

| # | Candidate explanation | What it predicts that the others do not |
|---|---|---|
| H1 | Common-source inductance (board source copper shared with the driver return, and/or inside the package) slows the turn-on | Rise time and overshoot depend on the turn-on di/dt: rise time grows with switched current; the gate-source voltage at the die shows a dip during the current rise. Extraction G estimates the high side's board part at only 0.9 pH (low side 48 pH), so for Q1's turn-on H1 now mainly concerns the package |
| H1b | Coupling between the power loop and the high-side gate-drive loop slows Q1's turn-on (test 7: the extracted high-side gate path lowers the simulated overshoot by 7 V; mechanism not isolated) | Like H1 in the switching data; separable from package inductance only with the gate-loop geometry changed (for example E4's gate-resistor change shifts H1 and H1b differently in the bench) or with E8-type passive measurements of the gate-loop coupling |
| H2 | The real driver is weaker or slower than the behavioural model | The driver's output edge, measured with the power stage off (E1), is slower than modelled; with that measured edge in the bench, the predicted rise times match across E3 without other changes. Rise time is not expected to be independent of current or bus voltage under H2 (the Miller interval and di/dt still vary), so H2 is tested by its predicted dependence, not by the absence of one |
| H3 | Losses missing from the model (output-capacitance or dielectric loss) damp the ringing | Damping depends on bus voltage and temperature, not on the probe; the ringing frequency stays at the loop's LC value |
| H4 | The measurement chain (probe loading, ground path, bandwidth) shaped EPC's recording | Changing the probe or its connection changes the recorded overshoot and frequency while the circuit is unchanged |
| H5 | The model's gate charge (the EPC2302 Fig. 7 discrepancy) slows or speeds the Miller interval | Rise time scales with the measured Miller charge; device-level gate-charge measurement differs from the model |
| H6 | The actual dead time is shorter than the nominal 10 ns | The dead-time plateau measured at the driver outputs, with no power stage load, differs from 10 ns |

These explanations are not exclusive. The aim is to bound each one with its own evidence (the per-layer error
budget). The right-hand column describes qualitative tendencies. Before measurement, each is replaced by a
quantitative prediction from the bench (the hypothesis's parameter varied over its stated range, with the
bench's uncertainty), and an explanation is favoured only where its prediction fits and the competing ones do
not, beyond that uncertainty.

## Board facts and limits (QSG v1.0, Table 1)

- Gate-drive supply VDD 7.5–12 V (J1). PWM logic high 3.5–5.5 V, edges under 10 ns, minimum pulse widths
  50 ns (high) and 200 ns (low).
- Bus VIN up to 80 V. **The switch-node ringing must stay below 100 V** for the EPC2302. Output current up to 40 A,
  limited by die temperature.
- **The driver's ratings are tighter than the FET's** (uP1966E datasheet, Aug. 2021, p. 7, absolute maximum):
  PHASE to GND −5 V to +85 V, BOOT to GND 0 to 85 V, BOOT to PHASE −0.3 to 7 V. BOOT sits about 5 V above PHASE,
  so a switch-node peak near 80 V at the driver's PHASE ball already reaches the BOOT rating, and undershoot
  below −5 V exceeds the PHASE rating. The PHASE ball is not the Q2 drain pad: ringing there is not measured by a
  probe at Q2 and needs its own estimate (the extraction G network has the U80.PH terminal). The simulated
  PHASE-ball undershoot is unresolved: the raw minima reach −8 to −28 V as sub-picosecond excursions of the ideal
  driver stage, and only a filtered version is inside the rating (docs/build.md, test 7). Test 8 (assumed pin
  capacitance and clamps to ideal rails, not a qualified driver model) shows these extremes are sensitive to
  driver-model assumptions and partly numerically unstable; its verdict is unresolved
  (results/gan/epc90133-test8-assessment.json). No simulated value here is a hardware margin. The PHASE-to-GND voltage is therefore measured at each bus step, at the accessible point nearest
  U80's PHASE and GND balls (chosen and characterized in E0; the WLCSP balls themselves cannot be probed), and
  its undershoot trend is a stop criterion, like Q2's VGS.
- **The driver has no input lockout** (datasheet p. 5): "There is no lockout between HI and LI inputs: both GaN
  devices can be driven on at the same time." Shoot-through protection depends on the board's input and
  dead-time circuitry and on the PWM source, which must be assessed from the schematic and on the bench (E1).
  The driver cannot be credited with it.
- Start-up order: gate-drive supply, then PWM, then raise the bus slowly from 0 V.
- Dead time is set by R620/R625 (120 Ω populated, nominally 10 ns).
- The switch-node MMCX J32 is described in the guide but absent from the published layout. Plan the probe
  connection from the actual board.

## Safety envelope (independent of the software)

- A current-limited bus supply with hardware over-voltage and over-current trips, a bus-discharge path, the
  enclosure interlock and an emergency stop (plan section 7).
- A hardware limit on double-pulse width, so the inductor current cannot run away if the PWM source misbehaves.
- The first energization is at **12 V bus**. The bus rises in steps (12, 24, 36, 48 V), with a human checkpoint at
  each step. At each step the measured switch-node peak and undershoot must leave margin to the tighter of the
  FET limit (100 V) and the driver's PHASE/BOOT ratings (above) before the next step.
  **The simulated overshoots are sensitivity results, not a safe envelope**: the unvalidated full-board simulation
  reaches about 84 V at 48 V, which would already exceed the driver's ratings.
- Low-side false turn-on: in simulation (test 7, docs/build.md) the board's low-side gate path lifts Q2's die
  gate-source voltage to about 2.0 V during Q1's turn-on at 48 V and 11 A (2.4 V if Q1 switches faster), above
  the model's 1.51 V threshold and inside the datasheet's 0.8–2.5 V range. Q2's gate-source voltage is therefore
  measured from the first energized step, and its trend with bus voltage and current is a stop criterion before
  each step up. The simulated values are sensitivities, not limits.
- Shoot-through: since the driver has no lockout, the PWM source and the board's input circuitry must be shown
  (E1, power stage unpowered) never to command both gates on, including at power-up, power-down and with an
  input open, before the bus is energized.
- Any instrument control by software goes through a non-LLM layer that enforces this envelope.
- **Not yet specified (required before approval):** the double-pulse width limit and its hardware
  implementation, the maximum inductor current per step, the supply current-trip and over-voltage-trip
  settings, the case-temperature limit and how it is measured, the stop criteria at each checkpoint, and the
  ramp for any step above 48 V (the 60 V held-out condition below lies outside the listed steps).

## Equipment checklist (to compare with the lab inventory)

| Need | Why | Minimum | Preferred |
|---|---|---|---|
| Oscilloscope | edges of 1–4 ns, ringing near 250 MHz | 1 GHz, 5 GS/s, 4 channels | 2 GHz or more, 10 GS/s or more |
| Switch-node probe | the main waveform; H4 | 1 GHz passive probe with a spring-tip or solder-in connection at the Q2 pads | optically isolated high-bandwidth probe (IsoVu class) for comparison |
| Second switch-node connection | H4: the same node through a different connection | a different ground path (e.g., a long ground lead) for a deliberate comparison | — |
| Low-side gate probe | H1, H2 (gate-source voltage); Q2 false-turn-on margin (required from the first energized step) | 500 MHz passive probe at Q2's gate and source pads | — |
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
| Device analyzer (lab has a B1506A) | H5: EPC2302 gate charge and capacitances measured on spare devices | fixture option H21, H51 or H71 with the gate-charge socket adapter (gate charge is not available without one of them); a small adapter board for the 3 × 5 mm QFN on the universal socket module (no standard QFN socket is listed) | an option that supports the datasheet gate-charge condition (VDS 50 V, ID 50 A) |
| Double-pulse tester (lab has a PD1550A) | not suitable here: its standard interface boards take 62 mm and FM3 modules, other packages need a custom board designed with Keysight, and its probes are specified at 200 MHz, too slow for 1.7 ns edges and 264 MHz ringing | — | — |
| Network or impedance analyzer (E8, optional) | loop inductance of the unpowered board, separating layout from device and driver | VNA to at least 100 MHz with fixture de-embedding, or an impedance analyzer to 120 MHz | — |
| Second EPC90133 (E8, optional) | shunt-thru measurement needs the FETs removed | one board, not used for switching tests | — |

## Experiments

Each experiment records the raw waveforms, all instrument settings, the probe and its connection, the board
identity (silkscreen revision, fitted population), the case temperature and the time.

- **E0, measurement chain first.** Probe deskew on a known edge. The step response of each probe and connection
  gives its bandwidth and ringing. Without this, no device or layout conclusion is drawn (plan section 4).
- **E1, driver alone (H2, H6).** Power stage unpowered (VIN = 0 V): measure PWM-to-gate delays, gate-voltage
  edges and the dead time at the gate pins. This isolates driver timing and strength from the power stage.
- **E2, loop inductance by frequency shift (parasitic layer).** At a low bus (12–24 V) and low current, measure
  the ringing frequency, then add a known C0G capacitor across Q2 (drain to source) and measure again. The shift
  gives an estimate of the loop inductance and the effective capacitance. It assumes the same ringing mode before
  and after (checked, not presumed), a capacitance that is linear at the operating point, a mounting inductance
  of the added capacitor small against the loop, and light damping: the method uses the damped frequency, which
  is within 0.3 % of the natural frequency at the measured damping ratio of about 0.075, but that error grows
  with damping and with a damping change caused by the added part. Probe loading shifts both readings. Report
  the estimate with an uncertainty from each assumption, and compare with the extracted network (variant B:
  0.26–0.28 nH loop; G when available), not with a single number.
- **E3, double-pulse matrix (H1, H2, H3).** Bus at 24, 36 and 48 V; turn-on current at 5, 11 and 20 A; turn-off
  current at 10, 20 and 29 A. Record the rise and fall times, overshoot, ringing frequency and damping, and Q2's
  gate-source voltage, which is a prerequisite at every point (safety section); no point runs without it. Also
  record the PHASE-to-GND voltage near the driver (safety section). Before the measurement, each hypothesis's bench variant
  predicts the rise-time slope against current and against bus voltage, and the damping against bus voltage,
  with uncertainty. Tendencies, to be quantified:
  - H1 (common-source) predicts a stronger rise-time dependence on switched current than H2 does;
  - H3 predicts damping that changes with bus voltage at nearly constant frequency;
  - H2 predicts the dependence computed with the E1-measured driver edge; it does not predict independence.
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
  isolates a device discrepancy, could justify a separately stored tuned model revision. Keep the gate drive
  within the EPC2302 limits (+6/−4 V), start with a sacrificial part, remove the adapter's stray capacitance by
  open compensation, and record part-to-part spread over several samples.
- **E8, passive loop inductance (parasitic layer), optional.** On a second, depopulated board: short one FET
  position and connect a VNA across the other (shunt-thru), then add the input capacitors one group at a time
  (method: Tranchero et al., Zenodo 20617321, 2026). The alternative, an impedance analyzer with both FETs gated on
  (Wolfspeed PRD-08710), would need both gates held on together. The driver does not prevent that (no lockout,
  datasheet p. 5), but it would mean deliberately bypassing the board's dead-time circuitry on an unpowered
  board, and it is not proposed here. Before use: de-embed the fixture and pass a sub-nH known-answer check.
  Compare with the extracted network, and with E2 on the powered board. E2 minus E8 estimates the package
  contribution only if the two measurements represent comparable ports, current paths and ringing modes, with
  fixture effects included; otherwise the difference is not a bound. Both measurements' errors carry into it.
  Sources and limits: docs/gan-research-round-2-2026-09-30.md.

## Held-out conditions and frozen predictions

Before any measurement, freeze the simulation's predictions (model and extraction revisions, bench settings,
predicted metrics with their stated sensitivity ranges) for all conditions. Use E0–E4 at 24–48 V for calibration
and diagnosis. Hold out, and score unchanged:

- the bus at 60 V (below the 80 V rating), only with its own ramp and checkpoint above 48 V, and only if the
  measured peaks and undershoot at 48 V leave margin to the driver's PHASE/BOOT ratings as well as to 100 V;
- turn-off at 25 A with R80 = 2.2 Ω;
- the second temperature.

Report the first held-out score as it is; later corrections create new revisions and do not overwrite it.

## Open items for the owner

1. The lab's oscilloscope and probes (bandwidth, isolated probe, current probe), supplies and pulse generator,
   compared with the checklist above.
2. Whether spare EPC2302 devices and a B1506A fixture for them can be obtained (E7), and which B1506A fixture
   option (H21, H51 or H71) the lab has. Open as of 30 September 2026.
3. Whether a VNA or impedance analyzer is available, and whether a second board may be depopulated (E8). Open as
   of 30 September 2026.
4. Approval of the envelope and the step-wise bus increase before G4, after its open values (safety envelope
   section) are filled in.
5. The board's input and dead-time circuitry (schematic review and E1): whether any input state, including
   power-up and an open input, can command both gates on.
