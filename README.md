# Autonomous semiconductor-device and circuit design tools

This project is developing tools that general-purpose AI agents can use to design semiconductor devices, connect circuits, run simulations, inspect results, and iterate. **Custom device design and circuit co-design are in scope from the first working demonstration.**

Read the [active toolset plan](plans/autonomous-circuit-toolset-plan.md) for the architecture, proposed operations, implementation sequence, and evaluation gates. The recommended first target is a custom planar NMOS and a simple amplifier, with independent device-to-circuit validation. The [reference notes](plans/autonomous-toolset-reference-notes.md) connect the decisions to local papers and upstream tools.

Current status: the first implementation slice is available as a Python library and CLI. It includes immutable circuit revisions, artifact storage, a bounded ngspice adapter, and a validity-aware diode fitting fixture. Real ngspice divider and custom-diode checks pass; see [build instructions and scope](docs/build.md) and the [executed circuit report](results/toolset/circuit-fixtures.json). The complete physical NMOS-to-amplifier co-design loop is still under construction. Legacy preflight results describe the earlier pilot only.

- `papers/`: reference literature and historical index.
- [Public device benchmark sources](docs/device-benchmark-sources.md): diode/MOSFET reference data, provenance limits, and validation sequence for future sessions.
- `plans/autonomous-circuit-toolset-plan.md`: active direction, dated 11 September 2026.
- `protocol/`, `pilot-inputs/`, `results/`: preserved earlier fidelity/ranking pilot specification, numerical checks, and readiness results.
- `plans/FINAL-PLAN.md` and `archive/`: earlier research direction, superseded in priority by the toolset plan.

The official DEVSIM diode and planar MOS scripts now complete, with [finite-current and conservation checks](results/device-reference/audit.json). The next release gate is mesh/current-normalization qualification, followed by the NMOS characterization/model bridge and independent amplifier validation.
