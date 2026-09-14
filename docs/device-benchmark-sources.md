# Public diode and planar-MOSFET benchmark sources

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
