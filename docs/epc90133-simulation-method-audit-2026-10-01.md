# EPC90133 simulation-method investigation, 1 October 2026

Reviewed baseline: `79f98b5`. This is a method audit, not G3 acceptance. No LTspice
or field-solver jobs were launched. The vendor model and existing simulation
results were not changed. A NumPy-only matrix diagnostic was added and executed.

## 1. Extraction-to-SPICE resistance transfer is incomplete (confirmed)

`scripts/epc90133_switching.py:network` emits all mutual inductances but only the
diagonal entries of the extracted resistance matrix. This omission was already
disclosed in its docstring; its size on the current networks had not been quantified.

`scripts/audit_epc90133_network_transfer.py` independently constructs an incidence-
matrix solve from the saved ports. It reproduces the extractor's full-matrix
summary and repeats the calculation using the resistance actually represented in
the switching bench. Results: `results/gan/epc90133-network-transfer-audit.json`.

| Network | Full-matrix loop R | Diagonal-only loop R | Change |
|---|---:|---:|---:|
| B-m1-mid | 2.0344 mOhm | 1.1245 mOhm | -44.7% |
| G-m1-mid | 2.0342 mOhm | 1.0344 mOhm | -49.1% |

These are 100 MHz diagnostic impedances with capacitors and Q2 shorted, not the
switching circuit's damping resistance. The absolute difference is approximately
1 mOhm; it does not establish an explanation for the whole damping discrepancy.
Current sharing and gate-return voltage also change: on G, Q1's resistive return
transfer changes from 0.0157 to 0.5801 mOhm, Q2's from 0.4041 to 0.1788 mOhm.
Those are transfer terms, not discrete resistors to place in the gate circuit.

The earlier diagonal-R scaling experiment does not test restoration of these
terms. The next numerical improvement should retain full R as well as full L,
with an AC terminal-impedance check against the saved extraction before switching.
Keep the current approximation as a separately named baseline.

Checks that passed: port ordering matches matrix ordering; independent full-R
loop values reproduce the saved summaries; full R is positive definite for these
two cases; rounding L and K to the generator's six significant digits preserves
positive definiteness (G minimum eigenvalue 6.27366 -> 6.27367 pH). No evidence here
that serialization destroys passivity. Frequency dependence and geometry accuracy
are separate, untested questions.

## 2. The reported "die VGS" is not the internal channel VGS (confirmed)

The bench's `die_nodes` map to the external terminals of the EPC2302 subcircuit,
after any added package inductance. In the pinned local library, EPC2302 has
`gatein`, `drainin`, `sourcein` terminals followed by internal rg, rd and rs.
At 25 C, rg is 0.5 Ohm and rs is approximately 0.1766 mOhm. Its channel-current
expression uses internal `gate`, `drain`, `source` voltages.

Therefore the current diagnostics correctly exclude the added package inductors,
but the label "die" overstates what they measure. During switching, internal
resistor voltage drops separate terminal VGS from channel-control VGS. Comparing
the transient 2 V terminal peak directly with a DC current at 2 V does not establish
transient channel conduction. Terminal drain current also includes displacement
current, as the existing notes correctly acknowledge.

Recommended correction: name the existing quantity vendor-model terminal VGS;
save internal VGS and channel-source current separately in a diagnostic revision,
without changing the vendor model's equations. Keep physical gate-pad measurements
separate from model-internal quantities. The Q2 false-turn-on hypothesis remains
worth measuring; this audit neither proves nor dismisses it.

## 3. Driver calibration does not qualify the switching driver model (high-priority assumption)

`epc9097_switching.py:drive_stage`, reused by EPC90133, is a ramped ideal voltage
source through resistance and a nearly instantaneous switch, with programmed
source resets. Calibration fits two edge times into one 3000 pF load. That does not
identify the output I-V response under Miller feedback, inactive-pin behaviour,
or channel timing mismatch. The EPC90133 bench also uses ideal 5 V supplies.
Extraction G explicitly omits the C80/C81 supply loops; the schematic record has
4.7 uF local VCC decoupling and a 100 nF bootstrap capacitor.

The driver datasheet specifies output resistance at 500 mA, edge times at 3000 pF,
bootstrap behaviour, and delay mismatch. These are separate constraints. A common
propagation delay is largely an alignment issue here; unequal delays affect dead
time. Source: [uP1966E datasheet, pp. 3, 5, 8](https://epc-co.com/epc/Portals/0/epc/documents/datasheets/uP1966E_datasheet.pdf),
checked 1 October 2026; the existing source manifest records the pinned local file.

Test 8 adds both pin capacitances and clamp paths into ideal rails. It supports
sensitivity to the driver representation, not identification of the real output
stage or a hardware margin. Calibration should be checked again for each changed
driver representation. A small driver-only bench is a better place to resolve
commutation numerical behaviour than repeated hour-long whole-board runs.

## 4. The loss and frequency model is incomplete (known, still material)

The entire transient uses one R/L extraction at 100 MHz; observed ringing is near
260-300 MHz and the edges contain higher frequencies. Diagonal-R scaling is neither
a full matrix frequency check nor a broadband passive model. The FastHenry
[user guide, section 2.2](https://www.fastfieldsolvers.com/Download/FastHenry_User_Guide.pdf)
distinguishes single-frequency equivalents from frequency-dependent reduced models.
This does not require a tool change: first qualify transfer of the matrix already
available, then spend extra extraction time only if a decision needs it.

The inspected EPC2302 library uses charge-defined capacitances and channel/series
resistance; it has no explicit Coss hysteresis-loss model or package inductors.
This does NOT mean it has zero capacitive-path dissipation: its series resistances
still dissipate current. Capacitor C/ESR/ESL are assumed constants, supplies and the
output source are idealized, and temperature is fixed at 25 C. Missing or misplaced
loss remains a candidate for the damping mismatch, not an identified cause. Do not
fit a transistor parameter or arbitrary resistor to Fig. 9 before isolating it.

## 5. Validation and comparison have narrower scope than the whole circuit

- The single-sample spike check inspects only V(q2_d). "usable" does not certify
  PHASE, internal gate voltages, or current traces. Test 8 demonstrates this distinction.
  Give numerical/physical dispositions per observable, including structured test-8
  criteria, rather than extending one global pass flag to every quantity.
- Double-pulse/periodic equivalence was shown on A and B under ideal supply/load
  assumptions. It has not established G with a realistic bootstrap/supply model.
  Match operating history as well as edge current when those dynamics are introduced.
- Fig. 9 is raster-derived and fails its voltage-scale check. Gaussian filtering
  models bandwidth only: it is not probe loading, probe grounding, or a different
  pickup location. Keep the current waveform comparison diagnostic.
- One damped sinusoid is fitted to the ring. Fit residuals are reported but do not
  gate the damping verdict. Inspect fit residuals and window sensitivity before using
  a small damping difference to choose between mechanisms.

## Recommended sequence

1. Fix terminal-versus-internal diagnostic naming and make observable validity explicit.
2. Qualify full-R/full-L transfer with a small known matrix and the saved B/G matrices;
   then perform one declared switching comparison if the corrected transfer passes.
3. Characterize the driver model in a small bench against its stated constraints;
   keep assumptions and alternative representations separate. No speculative wide sweep.
4. Continue equipment inventory and the concrete probe plan in parallel. Measurements
   should identify supply behaviour, actual timing and damping before model tuning.
5. Defer finer G meshing, wider optimization and device fitting until their outcomes
   could change a decision. G3 remains open.

Reproduction (WSL on this host, existing local NumPy):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.tools/python python3 scripts/audit_epc90133_network_transfer.py
```

The diagnostic asserts its matrix residual and agreement with the existing full-
matrix summaries. It binds the extraction and generator files by SHA-256. It does
not run or validate LTspice, and it does not assess a physical board.
