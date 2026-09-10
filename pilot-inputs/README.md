# Inputs required to start the circuit pilot

This directory intentionally contains no invented circuit or PDK data. `protocol/pilot_preflight.py` reports missing inputs until the actual reference assets are supplied and pinned.

`toolchain.json` must identify the container image digest, source commits, executable versions, PDK installation/model hashes, licences, solver retry options and command adapters for schematic simulation, layout, DRC, LVS and RC extraction. Record the expected result-property names and failure/timeout exit codes for each adapter. API keys are environment variables, never manifest fields.

Each `five_transistor_ota/` and `miller_ota/` directory must contain:

* `topology.json`: topology/source/reference IDs; reference netlist path and SHA256; legal sizing variables and ranges; units and tied-device groups; geometry grid; finger rule; model bins; source/load/context values; complete property test definitions, thresholds, inequality directions and margin scales; device-equivalence mapping policy. Use actual source values, not defaults guessed from the plan.
* `testbench.spice`: the reproducible benchmark testbench and a manifest of all included files. Every measured scalar needs an unambiguous parser and finite/nonfinite status rule. PDK model files stay in their pinned installation.
* `layout-template.json`: exact ALIGN template, constraints and device mappings with its source commit/hash, plus reference DRC/LVS/extraction outputs or their paths.

Reproduce the reference sizing before writing a successful preflight report. File presence alone does not validate a circuit. The physical runner and training harness are implementation tasks in `FINAL-PLAN.md`; the scripts currently supplied perform numerical verification, budgeting and readiness checks only.
