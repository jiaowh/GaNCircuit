# EPC90133 simulation-only report (9 October 2026)

This report closes the simulation-only phase of the EPC90133 work: the stage before any measurement on our own
board. It states what the simulations show, what they do not show, and which questions only measurements can
answer. Nothing here is validated against hardware. Detailed evidence and replay instructions are in the
[build notes](build.md); the figures below come from the saved reports linked in each section.

## Bottom line

- **The transistor model matches EPC's published curves well, but not the whole datasheet.** A calibrated version of
  EPC's model (EPC2302DS) matches all 25 published curves and 11 of 13 switching and conduction table values (the
  other two are unresolved). Its leakage is inside the datasheet limits but far from typical; it has no breakdown
  behaviour and no thermal model.
- **The board simulation does not reproduce EPC's measured switching waveform.** Edge speeds and ringing frequency
  match. The voltage spike is about twice EPC's, and the ringing dies away about three times too slowly.
- **No layout tested meets all thirteen design goals.** The best candidate, V8, meets three goals, narrowly misses two
  and fails the rest. The search is paused. Further layout runs would rest on the same unresolved assumptions, which
  only measurement can settle. It is not paused because the remaining layouts were shown to fail.
- **The main unknowns are the inductance inside the transistor package and the missing damping.** Both change the
  goal verdicts. Measurements on the board are the next step.

## 1. What was simulated

The chain runs from the transistor datasheet to a board-level switching simulation:

1. **Transistor model.** EPC's LTspice model of the EPC2302, checked against the datasheet.
2. **Board.** EPC's published layout files, rebuilt as an editable KiCad design that reproduces EPC's copper. The
   copper of the power and gate-drive paths is converted into an inductance and resistance network (FastHenry).
3. **Switching bench.** The transistors, a behavioural gate-driver model and the board network, run at the board's
   published operating point (48 V in, 20 A, 250 kHz). Results are compared with EPC's measured waveform (Figure 9 of
   the quick-start guide) and with the owner's thirteen layout goals (S1-S13).

## 2. Transistor model

[Coverage record](../results/gan/epc2302-coverage.md) (both models, every datasheet item).

| Area | EPC's model | EPC2302DS (calibrated) |
|---|---|---|
| 24 curves: current, resistance, capacitance, output charge, reverse conduction, temperature | all pass | all pass |
| Gate-charge curve (Figure 7) | fails | passes |
| Table values with a definite target (11 rows) | pass | pass |
| Two gate-charge table values (QGD, QG(TH)) | unresolved | unresolved |
| Leakage currents (4 rows) | inside limits, flagged | same |
| Breakdown voltage | not represented | same |
| Reverse recovery (datasheet: zero) | zero | zero |
| Thermal resistance and thermal response | no model | same |
| Maximum ratings, safe operating area | not checked | same |

The two gate-charge table values are unresolved because EPC's own gate-charge curve gives different values under
the table's definitions. Leakage is inside the datasheet limits but 0.5-59 times the typical values, and it does
not change with temperature as a real part's would. The model contains no breakdown mechanism, so the 100 V rating
cannot be tested in simulation. EPC2302DS adds two small gate-charge corrections to EPC's model. It is a
calibration to the published curves, not identified device physics. EPC's original model is kept unchanged as the
reference.

The thermal and rating items are labelled open, not passed. Matching published typical curves is not the same as
validating the model against a real device.

## 3. Comparison with EPC's measured waveform

EPC's Figure 9 is a screenshot of the switch-node voltage. Its time scale checks out against EPC's printed rise and
fall times. Its voltage scale reads 5-7 % low, so voltage readings from it carry that caveat.

| Quantity | EPC Figure 9 | Simulation (EPC2302DS, board network G, assumed 50 pH) |
|---|---|---|
| Rise time | 1.68 ns | 1.71 ns |
| Fall time | 3.63 ns | 3.98 ns |
| Ringing frequency | 264 MHz | 262 MHz |
| Overshoot above the supply | 5.7 V | 11.3 V |
| Damping ratio (how fast the ringing dies away) | 0.077 | 0.025 |
| Settling to within 2 % | 18.3 ns | not settled within 45 ns |

Source: [generated summary](../results/gan/epc90133-fig9-ds-summary.md); ideal probe at the transistor.

What was tried, and what it showed:

- **The gate-charge correction does not close the gap.** EPC's model and EPC2302DS give nearly the same overshoot and
  damping. This rules out that correction as the fix, not the transistor model as a contributor.
- **Measuring at the guide's probe holes (J33) may explain part of the overshoot.** Reading the simulated voltage
  there lowers the overshoot to 9.2 V, about a third of the gap. The damping is unchanged. This is indicative only:
  adding the probe holes changed the board network more than the limit set before the run, and the guide does not
  confirm that Figure 9 was taken at J33.
- **Damping remains unexplained.** Probe bandwidth, sourced capacitor data, extra capacitor loss and partial
  transistor turn-on were each tested; none matches the damping without an unrealistic value.

Candidate causes still open: the real package inductance, the probe's own loading and ground lead, and energy
losses the model lacks (output-capacitance loss, high-frequency copper resistance).

## 4. Layout goals

The owner's template fixes the parts list and allows changes to copper, vias and component positions. Results use
EPC2302DS and an assumed 50 pH package source inductance, under two gate-driver models ("ramp" and "step"). A goal
counts as met only if it holds under both. Assessment:
[goals scoring, revision 2](../results/gan/epc90133-goals-assessment-ds-rev2.json).

| Goal | Target | Stock (ramp / step) | V8 (ramp / step) | V8 verdict |
|---|---|---|---|---|
| S1 peak voltage | <= 80 V | 59.3 / 58.7 V | 59.5 / 58.6 V | met |
| S2 overshoot | <= 9.6 V and 10 % below stock | 11.15 / 10.47 V | 11.33 / 10.38 V | not met |
| S3 settling | <= stock | 131.5 / 132.2 ns | 133.2 / 130.3 ns | not met (ramp, +1.3 %) |
| S4 rise and fall times | <= 1.1 x stock | 1.73 / 1.83 ns rise | 1.79 / 1.87 ns rise | met |
| S5 dv/dt | limit not set | reported | reported | undetermined |
| S6 current slope | <= stock | 38.0 / 29.9 A/ns | 37.5 / 30.9 A/ns | not met (step, +3 %) |
| S7 gate-voltage extremes | +5.5 / -3 V | within | within | met |
| S8 low-side gate spike | < 0.5 V | 1.93 / 1.64 V | 1.85 / 1.56 V | not met |
| S9 shoot-through | gate spike below 0.8 V | spike above | spike above | undetermined |
| S10 switching energy | 10 % below stock | 5.70 / 5.94 uJ | 5.73 / 5.97 uJ | not met |
| S11 best dead time | 5-15 ns | 2.5 ns | 2.5 ns | not met |
| S12 efficiency | +0.3 points | 99.128 / 99.126 % | 99.124 / 99.123 % | not met |
| S13 corners (40/60 V, no load, parasitics +-10 %) | S1, S2, S7, S8 hold | S2, S8 fail | S2, S8 fail | not met |

V8 thins the via rows under the transistors so the return current runs closer to the power loop. In S11, 2.5 ns
is the shortest dead time sampled, so the true optimum may be even shorter. S12 counts transistor losses only, so
it cannot see copper-loss savings. One V8 corner run stalled and is undetermined; V8 fails S13 on other corners
anyway.

**What the screens show.** Scaling every board inductance together meets S2 only near half the stock value.
Switching energy (S10) then gets worse, because most of it is the transistors' own output-charge loss and lower
inductance raises the rest. The best permitted combination tried (V8 plus the thinnest standard dielectric) lowers
loop inductance by about 28 % in a partial model, where overshoot is still about 11 V. An ideal low-side gate
connection, which removes all of the board's shared return copper, still leaves a 1.1-1.3 V gate spike against
S8's 0.5 V, because of the assumed package inductance.

**What they do not show.** These screens cover particular families of changes. They do not prove that no permitted
layout meets the goals. A low-side driver return redesign (L4a) was examined on 9 October. On the top layer, the
low-side gate probe connection blocks a direct return to the transistor's source. A separate return would need a
driver-ground redesign on an inner layer, plus a new via-editing tool, so it was not built. Its benefit is
uncertain: the ideal-connection screen above suggests the spike would stay above S8's limit, but it is a screen, not a
proven floor, and it was run with EPC2302DS only. Moving the capacitors together with their return vias (L3b) is
untested.

## 5. What depends on assumptions

| Assumption | Effect on the results | What would resolve it |
|---|---|---|
| Package source inductance 50 pH (EPC states < 0.2 nH; value unknown) | Strongly sets overshoot, rise time and the S8 floor; earlier runs without it overshoot far more | Switching measurements at several currents, compared with frozen predictions |
| Missing damping (simulated 3x too slow) | Settling (S3), overshoot and the corner verdicts | Switch-node measurement with a characterized probe at a known point |
| Gate-driver model (two forms meet the datasheet) | Overshoot differs substantially between the two | Gate-drive waveform measured with the power supply off |
| Board extraction (one mesh, vias and slotted planes not fully qualified) | Absolute inductances; comparisons use the same route to limit this | A second mesh or measurement; benchmarks are not board error bars |
| Capacitor values (bench values are assumptions) | Vendor-sourced values plus switch-node capacitance moved overshoot 11.3 to 12.1 V, damping barely | Vendor data for the fitted parts (partly in hand) |
| Transistor-only efficiency estimate | S12 cannot be judged | Converter efficiency measurement with a declared uncertainty |
| Ideal probe in simulation | Comparison with Figure 9 | Characterized probe and connection on the real board |

## 6. What measurement must answer first

The [hardware test plan](epc90133-hardware-test-plan.md) is a draft, not an approved procedure. Before any energized
test, it needs the lab's equipment list and confirmation of the actual board (revision and fitted parts). In
order, the first measurements that would most reduce the uncertainty are:

1. Characterize the probes and connections at the planned points.
2. Measure the gate-drive waveforms with the power supply off, which separates the two driver models.
3. Measure switching at several currents and voltages against predictions frozen beforehand. This constrains the
   package inductance and the damping. It will not settle every cause on its own, and unidentified causes are an
   acceptable outcome.

Hardware protection stays independent of any software agent, and simulated peak voltages do not define a safe test
envelope.

## Evidence

| Topic | Report |
|---|---|
| Transistor model coverage | [epc2302-coverage.md](../results/gan/epc2302-coverage.md), [EPC2302DS checks](../results/gan/epc2302-ds-variant.json) |
| Waveform comparison | [Figure 9 summary](../results/gan/epc90133-fig9-ds-summary.md), [J33 probe scoring](../results/gan/epc90133-probe-reference-j33-ds.json) |
| Layout goals | [assessment revision 2](../results/gan/epc90133-goals-assessment-ds-rev2.json), [goal definitions](../plans/goal-targets-2026-10-08.md) |
| Audit of this work | [project audit, 274cd46](project-audit-274cd46.md) |
