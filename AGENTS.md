# Project continuity

Read `README.md` for current implementation status and links to executed results, then `plans/gan-halfbridge-pipeline-plan.md` for the active direction. Inspect current files before relying on historical chat summaries; implementation may have progressed in another session.

## Active direction (28 September 2026)

The project builds and validates an agent-driven pipeline for a commercial EPC GaN FET and its half-bridge development board: datasheet → vendor model → layout-aware simulation → automated measurement → closure report. Three student-owned stages (datasheet-to-model, layout-aware design, test-and-closure) connect through versioned artifacts with declared inputs, outputs and acceptance checks. The software need not consist of exactly three independently reasoning agents. The plan records the owner's brief and refinements.

Rules from the owner's refinements that every session must keep:

- Record the source, retrieval date, checksum and reuse terms of every EPC file. Publicly downloadable files are not automatically licensed for unrestricted reuse. Gerber or schematic downloads are not automatically KiCad-importable, and EPC lists editable Altium files as available on request.
- Demonstrate that the vendor model runs correctly in the selected simulator before using its results. A published model format does not show that our runner can execute it.
- Keep the original vendor model as the baseline. Tune only when evidence isolates the discrepancy to the device, and store any tuned model as a separate revision. Otherwise fitted device parameters can absorb layout, driver or measurement errors.
- A per-layer error budget needs separate evidence for each layer. One matching waveform cannot separate transistor, parasitic and probe errors.
- Core scope includes basic switching-charge behavior, dead-time and controlled test temperature. Dynamic RDS(on), Coss losses, soft switching and further boards are extensions.
- Hardware protection and interlocks stay independent of the language-model agent. Remove a human checkpoint only when a recorded reliability history supports it.

Provisional target (owner, 28 September 2026): EPC9097 board with EPC2204 FETs (100 V). EPC90121/EPC2050 (350 V) is the alternative. Never mix one board's measurements or driver with the other's model. The immediate deliverable is the unmodified EPC2204 model running through an LTspice adapter, with parsed results and a reproducible bench.

Simulator: choose the one that suits the selected vendor model and the available licenses. LTspice is the first candidate if the model supports it; PSpice and Spectre are also valid. ngspice is not a project requirement. Add the chosen simulator as an adapter behind the existing runner interface: it writes the test bench, launches the simulator, reads waveforms and reports measurements. Do not convert the vendor model to another simulator's syntax.

Status, 28 September 2026: LTspice 26.1.1 is installed per-user and `src/circuit_tools/ltspice.py` is the circuit adapter. `scripts/verify_ltspice_fixtures.py` passes; `scripts/epc2204_baseline.py` runs the unmodified EPC2204 model against the datasheet table (see docs/build.md). ngspice has been removed from the code and the host at the owner's request. EPC files live in the git-ignored `vendor/epc/`, recorded in `devices/epc/sources.json`. Open Stage 1 items: classify the gate-charge shortfall (QG 3.8 nC against 5.7 typical), digitize the datasheet curves, and compare one bench with an interactive LTspice run. The DEVSIM fixture runs under WSL; KiCad, PSpice and Spectre are not installed.

## Paused silicon fixture

The DEVSIM/ngspice silicon NMOS work was an assistant-selected development fixture, not the application. Preserve the generated device and results, but GaN progress does not depend on finishing them. The reusable parts are the immutable revisions, artifact provenance, result semantics and runner interface.

- The upstream `gmsh_mos2d` reference is retired as an amplifier candidate and kept as a numerical regression fixture (weak gate control, gm/gds ≈ 0.063 on the sampled grid). Do not spend sessions verifying it or proving its failure mechanism.
- `devices/planar-nmos-lc1.json` (L = 1 µm, 10 nm oxide, 3.3 V) is built by `scripts/planar_nmos.py` and analyzed by `scripts/analyze_planar_nmos.py`. Its common-source point (Vgs 0.6 V, W 23.9 µm, RD 16.5 kΩ, 100 µA) gives Av ≈ −11 from device-simulator derivatives, checked on three meshes. These are simulated results under constant-mobility physics; see docs/build.md "Generated planar NMOS".
- Possible follow-up if the fixture resumes: fit a DC model over the amplifier region with a predeclared holdout, simulate the stage in LTspice, compare with direct device-simulator load-line points, then make one circuit-driven device change. The IRDS comparison remains deferred.

## Working preferences

Explain progress in plain language: what capability now works, how it advances the full loop, and what remains unfinished. Do not report only test counts and numerical tolerances. Keep verification tied to a concrete design decision or acceptance gate. Reserve refinement studies, audits and large exports for decisions that need them.

The user requested cheaper subagents for bounded delegated work; review their outputs before accepting them and continue locally if they are unavailable.

For benchmarking and source provenance, read `docs/device-benchmark-sources.md`. Keep simulated reference data, vendor-described measurements, model-fit validation, and physical-device validation distinct.
