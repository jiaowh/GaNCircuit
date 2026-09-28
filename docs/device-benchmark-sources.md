# Public device benchmark sources

Recorded 14 September 2026 at the project owner's request so later sessions retain the benchmark discussion. Sources were inspected online during that discussion. This note records candidate sources and intended use; it does not establish that their data have been downloaded, imported, or benchmarked locally. Check current artifacts for execution status.

## Sources to assess

| Source | Available material | Intended use and limits |
|---|---|---|
| [DEVSIM examples](https://devsim.net/examples.html), [diode scripts](https://github.com/devsim/devsim/tree/main/examples/diode), [planar MOS scripts](https://github.com/devsim/devsim/tree/main/examples/mobility) | Device structures, physics definitions, meshes or mesh-generation inputs, and simulation scripts | Reproduce reference behavior and qualify our units, mesh, solver settings and automation. These are numerical references, not measured silicon. Repeating the same solver is a regression check, not independent experimental validation |
| [Silvaco level-1 diode extraction example](https://silvaco.com/examples/utmost4/section1/example5/index.html) | Public numerical `.uds` data described by the vendor as measured forward/reverse current and reverse-bias capacitance, plus an extracted SPICE model | Benchmark data import, constrained model fitting and held-out electrical predictions. Numerical data are visible as text; running the vendor's extraction workflow requires its commercial tools. Measurement provenance has not been independently established |
| [Silvaco BSIM3 MOSFET extraction example](https://www.silvaco.com/examples/utmost4/section1/example9/index.html) | Numerical MOSFET characterization data with dimensions, temperature and bias metadata, and a model-extraction example | Candidate conventional MOSFET electrical/model-fitting benchmark. Audit individual datasets and provenance before labeling them experimental ground truth. Electrical metadata do not provide a complete physical structure or fabrication recipe |
| [MESD MOSFET Electrical Simulation Dataset](https://github.com/SJTU-YONGFU-RESEARCH-GRP/MESD-MOSFET-Electrical-Simulation-Dataset) | JSON current/capacitance curves with bias, dimensions, temperature and model metadata across multiple technologies | Broader model-fitting and generalization benchmark. Explicitly generated using BSIM simulations, not physical measurements. Select and verify a planar-device subset; the collection also covers other architectures. Anonymized foundry bindings do not establish our custom device's physical geometry |

Silvaco's publicly accessible examples are not assumed to have an open redistribution license. Check applicable terms before bundling their data in this repository. MESD's repository states CC BY 4.0; retain attribution and verify the terms of the selected files when importing. Record source URL, revision or retrieval date, checksum, units and provenance for every imported dataset.

## Recommended validation sequence

1. **Numerical/device setup:** reproduce the DEVSIM reference cases, check terminal-current conservation, and demonstrate mesh-refinement stability. Compare simple diode cases against analytical predictions only within the assumptions of those predictions. Qualify 2D out-of-plane current/charge normalization explicitly.
2. **Model bridge:** use public diode and MOSFET characterization to test import, fitting and export. Hold out complete bias sweeps or device geometries as appropriate, rather than relying only on random neighboring points. Evaluate current error with absolute floors, threshold behavior, and relevant local slopes such as gm/gds. Capacitance data support only the dynamic claims actually covered by the measurements and model.
3. **End-to-end co-design:** freeze the agent's selected physical device and circuit. Re-solve direct TCAD at fresh operating points relevant to the circuit, including mesh/solver refinement of the optimized device. Compare load-line, output voltage, power and DC transfer slope against the compact-model circuit. Do not count interpolation of fitting data as a fresh TCAD check.

The recommended starting combination is DEVSIM references for numerical verification, Silvaco diode/BSIM3 examples for extraction benchmarks, and MESD for later breadth. This is a proposal for benchmark adoption, not a claim that these sources already validate the implementation.

## Interpretation rules

- A fitted I-V curve does not uniquely determine geometry, doping, contacts or fabrication history. Matching electrical data can validate fitting performance without establishing a physically correct TCAD reconstruction.
- Predictive accuracy for fabricated custom devices requires sufficiently documented measured devices or our own measurements, with calibration and independent validation data separated.
- A DC-only model cannot establish bandwidth, delay, settling or noise accuracy. Terminal-charge/dynamic validation remains a separate gate.
- Use current repository reports for progress. The planning conversation's earlier statement that implementation had not started is historical; the README now describes implemented circuit tooling and executed device references.

## Infineon CoolGaN reference track

Recorded 15 September 2026 at the project owner's request after inspecting
the [Infineon GaN transistor catalog](https://www.infineon.com/products/power/gallium-nitride/gallium-nitride-transistor).
Keep this as a candidate commercial-device benchmark and later power-circuit
application track while continuing the planar-NMOS custom-device milestone.

- The [IGT60R070D1 datasheet](https://www.infineon.com/dgdl/Infineon-IGT60R070D1-DataSheet-v02_14-EN.pdf?fileId=5546d46265f064ff016686028dd56526)
  provides electrical and thermal characteristics, characteristic diagrams,
  test circuits, and half-bridge application context. Its published curves
  are vendor reference information, not an independently audited raw
  measurement dataset.
- Vendor SPICE models are useful candidates for testing model import,
  terminal mapping, convergence, and electrical agreement. In an
  [Infineon support response about IGLD65R055D2](https://community.infineon.com/t5/GaN/The-SPICE-model-of-CoolGaN-devices-cannot-be-opened-in-LT-Spice-XVII/td-p/1134074),
  Infineon states that its models are assessed in SIMetrix and supplies an
  LTspice-compatible attachment. This does not establish ngspice compatibility.
- The inspected materials do not provide a complete physical structure and
  calibrated TCAD recipe for reconstructing or redesigning the commercial
  device. Fitting electrical curves cannot establish a unique physical
  geometry. Keep vendor-model simulations, datasheet comparisons, and
  physical-device validation separate.
- Proposed adoption sequence: select one part; inspect its model and usage
  terms; record version, checksum, terminals and domain; run bounded DC
  tests in ngspice; compare against documented datasheet conditions. Add a
  switching half-bridge only after charge/transient support is validated.
  Check redistribution terms before bundling vendor files.

Status at recording: web assessment only; no Infineon model has been
downloaded, imported, or validated in this project by this assessment.

## EPC GaN half-bridge track (active)

Recorded 28 September 2026. This is the active application in
[the GaN pipeline plan](../plans/gan-halfbridge-pipeline-plan.md), and it
replaces CoolGaN as the primary commercial track. CoolGaN remains an
alternative.

This record comes from a web check of EPC PDFs and documentation. No EPC files
have been downloaded into the project or run locally.

- **Board–FET pairing.** EPC90121 uses the EPC2050: 350 V, 4 A, onsemi
  NCP51820 driver ([QSG Rev 1.0](https://epc-co.com/epc/Portals/0/epc/documents/guides/EPC90121_qsg.pdf)).
  The EPC2204 board is EPC9097: 100 V, 20 A, uPI uP1966E driver
  ([board page](https://epc-co.com/epc/products/evaluation-boards/epc9097)).
  Owner decision: EPC9097/EPC2204 is the provisional first target, with EPC90121/EPC2050 as the alternative.
- **Design files.** The EPC90121 QSG points to its landing page for the
  schematic, BOM and Gerbers. The owner read both landing pages (EPC9097 and
  EPC90121), and both offer the Altium files on request; the QSG does not
  mention them. EPC9097's resources also include ODB++ data, the layer stackup
  and a test-point report. EPC's HTML pages refused automated fetches.
- **Terms.** The QSG's evaluation-board notice restricts use to evaluation and
  conveys no patent license. No separate license for the design files was
  found. Do not commit vendor files until their terms are checked; record the
  URL, date, version and checksum instead.
- **Vendor measurements.** The EPC90121 QSG shows switch-node and
  inductor-current waveforms (Fig. 12) and efficiency and loss curves
  (Fig. 13) at 280 V → 28 V, 50 kHz. These are vendor-described measurements
  under the vendor's setup, not audited raw data. Measured data for EPC9097 are
  not yet checked.
- **Models.** [AN005](https://epc-co.com/epc/Portals/0/epc/documents/product-training/Circuit_Simulations_Using_Device_Models.pdf)
  says EPC's LTspice, PSpice, TSpice and Spectre models share the same
  equations and include temperature effects on conductivity and threshold.
  EPC publishes an FEA-derived three-stage thermal RC model for the EPC2204.
  A published format does not show that our runner executes the model
  correctly; that is gate G1.
