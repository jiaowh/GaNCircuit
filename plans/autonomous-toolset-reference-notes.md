# Reference notes for the autonomous device/circuit toolset

11 September 2026. Supports the [active plan](autonomous-circuit-toolset-plan.md). Local PDF page numbers below count from the first PDF page. Findings are from selected full-paper passages and current primary-source documentation; upstream software was not installed or reproduced during this planning task. Proposed architecture and priorities are engineering judgments drawn from this evidence, not claims made by all cited authors.

## Local papers: what to take forward

| Paper and inspected pages | Relevant evidence | Consequence for this project |
|---|---|---|
| [Analog-DB](<../papers/(2026) Analog-DB_Agent-First_Analog_IC_Database arXiv2609.01286.pdf>), pp. 4-6, 12-13 | Separates topology, constraints, behavioral contract and process binding; uses metric recipes and verification tiers. Reported evidence is nominal schematic, with limited supervised agent cases | Reuse durable circuit contracts and tiered evidence. Add a physical-device binding and evaluate autonomous tool use independently |
| [SPICEAssistant](../papers/spiceassistant.pdf), pp. 3-6 | Uses deterministic waveform-reading tools with explicit target/tolerance checks; studies limitations of direct model interpretation of sampled data/images | Return measured quantities with units, windows, recipe versions and source data. Use plots for diagnosis without relying on visual reading for acceptance |
| [AutoSizer](<../papers/(2026) AutoSizer_AMS-SizingBench_LLM_Agent_Sizing arXiv2602.02849.pdf>), pp. 4-6 | Separates search within a numerical space from decisions that revise that space; shares simulation history | Provide budgeted optimizers as tools while retaining agent control over device changes, characterization and circuit topology |
| [AnalogAgent](<../papers/(2026) AnalogAgent_Self-Improving_Analog_Design_LLM_Agents arXiv2603.23910.pdf>), pp. 2, 15 | Separates generation, diagnosis and knowledge curation; memory retains transferable repair knowledge grounded in outcomes | Evidence-linked repair knowledge is useful later, but persistent memory and multi-agent roles are established techniques |
| [PANDA](../papers/panda.pdf), pp. 1-4 | Coordinates topology, sizing, placement and routing with explicit handoffs. Table 2 reports an OTA post-layout UGB below its stated target | Preserve per-constraint outcomes: completing a flow is distinct from satisfying its specification |
| [OSIRIS](../papers/osiris.pdf), pp. 5-7 | Produces layout variants with physical checks, extraction and paired circuit metrics using four amplifier templates | Reuse layout evidence conventions when that lane is added; the scope does not establish arbitrary custom-device support |
| [iPREFER](<../papers/iPREFER BSIM-CMG parameter extractor.pdf>), pp. 1-2, 4-5 | Separates TCAD data, IV/CV features, extraction and validation for a particular nanosheet/BSIM-CMG setting | Automated TCAD-to-model conversion is prior art. Qualification must be specific to the device/model family and relevant derivatives |
| [Compact Model Parameter Extraction via Derivative-Free Optimization](<../papers/Compact model parameter extraction derivative-free optimization.pdf>), pp. 1-2, 10 | Uses classical parameter fitting, robust/relative error objectives and separate validation; examples include diode and ASM-HEMT DC extraction | Start with a conventional constrained fit. Its DC results do not establish MOS charge or dynamic fidelity |
| [Bűrmen et al., compact modelling with free software](<../papers/(2024) Burmen_Free_Software_Compact_Modelling_Verilog-A_OpenVAF_OSDI InfMIDEM.pdf>), pp. 2-3, 5 | Discusses current-and-charge formulations, derivatives and historical charge-conservation problems | Validate stored charge and numerical behavior before allowing dynamic circuit claims |
| [A SPICE-compatible Neural Network Compact Model for Efficient IC Simulations](<../papers/BSIM-NN machine learning compact model EDTM2025.pdf>), pp. 2-3 | Includes terminal currents and charges, geometry dependence, derivatives and charge-reference treatment | Learned models remain optional; replacing a full model with an IV-only network would remove essential capability |

Metadata correction: the last local filename is misleading. Its cover identifies Tung, Salahuddin and Hu, **SISPAD 2024**, DOI 10.1109/SISPAD62626.2024.10733248, rather than EDTM 2025. The file is left unchanged to preserve existing links. [Author-hosted publication](https://escholarship.org/uc/item/7fh7q151)

The derivative-free extraction paper provides a useful [author implementation](https://github.com/rafapm/dfo_parameter_extraction). Reproducing its loss/optimization approach is a candidate baseline; its supported device models are not automatically the right family for the first NMOS bridge.

## Current upstream systems

| Primary source inspected | What it establishes | Reuse decision |
|---|---|---|
| [SpiceXplorer release](https://github.com/MacAnalog/spicexplorer-release) | Public circuit graph, units/measurement, waveform, optimization and physical-flow packages; per-package documentation and provenance | Highest-priority circuit-library inspection. Audit selected packages and reproduce custom-model loading; do not require the full UI or layout stack |
| [ltspice-mcp](https://github.com/cognitohazard/ltspice-mcp) | Existing agent simulation/measurement/job interfaces and schematic operations, including an ngspice path | Compare against direct batch fixtures and reuse if custom devices and evidence contracts fit |
| [mcp-spice](https://github.com/Casys-AI/mcp-spice) | Bounded analyses with persistent input/result identity and explicit limits | Useful reference for compact execution contracts; not a complete custom-device environment |
| [Hdl21](https://github.com/dan-fritchman/Hdl21) | Python structural circuit description, external modules, VLSIR conversion and netlist generation | Alternative construction representation if the selected circuit foundation lacks an appropriate one |
| [AutoSizer repository](https://github.com/yuxi120407/AutoSizer) | Configurable templates, numerical optimization and optional physical-flow integration | Consider tasks/optimizer integration after the custom-device slice; validate actual supported paths |
| [PANDA repository](https://github.com/PKU-IDEA/PANDA) | Current examples depend on commercial infrastructure; documentation distinguishes smoke runs and physical outcomes | Optional orchestration reference, with package access/license review before reuse |
| [MCP tools specification](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) | Machine-readable input/output schemas and tool-result conventions | Thin access layer over the engineering library; pin client/protocol compatibility |

SpiceXplorer's current repository is broader than the local Analog-DB paper. Conversely, published workflow descriptions should not be treated as proof that every upstream adapter works in this workspace. The phase-A reuse spike resolves those implementation questions.

## Device backend: details that affect the first implementation

Use [DEVSIM](https://github.com/devsim/devsim), a Python-scriptable semiconductor simulator, with the reproducible [2D MOS examples](https://github.com/devsim/devsim/tree/main/examples/mobility). The initial task is a declared isothermal research device, not prediction of an unspecified manufacturing process.

1. **Regenerate real geometry.** The [construction script](https://github.com/devsim/devsim/blob/main/examples/mobility/gmsh_mos2d_create.py) imports an existing mesh and duplicates some dimensions from the Gmsh description. A single canonical device specification must drive geometry, remeshing, and doping. Inspect resulting region/contact coordinates after a physical edit.
2. **Check dimensional conventions.** The upstream example's lateral `gate_width` must not be mistaken for out-of-plane transistor width. The [simple physics implementation](https://github.com/devsim/devsim/blob/main/python_packages/simple_physics.py) uses centimeter-based constants. Verify current/charge scaling with dedicated fixtures; dimensional analysis suggests per-out-of-plane-length normalization for 2D data, and the adapter must establish its exact convention experimentally.
3. **Do not assume a temperature model.** The same simple physics code has incomplete temperature dependencies. Start at 300 K and qualify any temperature extension separately.
4. **Inspect convergence explicitly.** The [solver documentation](https://devsim.net/solver.html) describes informational solves returning convergence state. Missing convergence exceptions do not establish successful physics. Preserve residuals, continuation history and failed points.
5. **Separate current from charge.** The [equation/model documentation](https://devsim.net/models.html) describes contact-current and contact-charge contributions. DC current agreement alone cannot validate dynamics.
6. **Use a small direct reference circuit.** DEVSIM documents [device/circuit coupling](https://devsim.net/circuits.html). Assess it for dynamic reference comparisons; the first DC amplifier can also be checked by direct TCAD load-line solves.

The [OpenVAF usage guide](https://openvaf.github.io/docs/getting-started/usage/) and [ngspice OSDI documentation](https://github.com/imr/ngspice/blob/master/README_OSDI.md) describe the model-compilation/loading path. Test the exact source/compiler/OSDI/simulator combination with a known-answer model. Successful compilation establishes compatibility, not model accuracy.

For later characterization and physical implementation, inspect [CACE](https://cace.readthedocs.io/en/latest/), [SKY130's documented status](https://skywater-pdk.readthedocs.io/en/main/status.html), and [ALIGN's SKY130 support](https://github.com/ALIGN-analoglayout/ALIGN-pdk-sky130). None supplies process/layout support for an arbitrary custom TCAD device automatically.

## Additional paper found for the clarified scope

[AgenticTCAD](https://arxiv.org/html/2512.23742v1), especially sections III-C and IV, already uses a language-model workflow to construct devices, run Sentaurus and optimize device metrics. The reported experiment includes device-specific physics, convergence recovery and structured electrical feedback. Treat it as close prior art for agent-driven device design. Its device optimization result does not establish our proposed circuit-model validation or circuit-driven co-design performance.

The useful research question is therefore specific: can a general agent use this toolset to decide whether to change a physical device, gather more characterization, repair a model, change circuit connectivity/bias, or fix numerical settings, and then obtain an independently accepted device/circuit design within a measured budget? This is a proposed evaluation question, not a completed novelty claim.
