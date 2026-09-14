# Building and running the first slice

This is a development foundation for the active toolset plan. The library has no
mandatory runtime dependencies beyond Python 3.10+. Circuit simulations require
ngspice. Commands below run from the repository root in Linux or WSL.

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m circuit_tools capabilities
PYTHONPATH=src python3 -m circuit_tools circuit-create examples/divider.json
python3 scripts/verify_circuit_fixtures.py --executable .tools/ngspice/usr/bin/ngspice
python3 scripts/verify_diode_bridge.py --executable .tools/ngspice/usr/bin/ngspice
```

On this Windows host, `scripts/bootstrap-ngspice.ps1` downloads and verifies the
Ubuntu 24.04 amd64 ngspice 42 package, then unpacks it inside `.tools/`. It does
not install a system package. WSL needs the shared libraries required by that
Ubuntu binary. On another Linux platform, install a compatible ngspice and omit
the `--executable` argument.

Build and install with `python3 -m pip install .` in a virtual environment.
For an offline build, supply setuptools and wheel locally and use
`python3 -m pip wheel --no-build-isolation --no-deps .`.

## Circuit operations

`circuit-create` returns an artifact ID and a circuit revision. `inspect ID`
reads an artifact; `netlist ID` emits a SPICE body. `circuit-patch ID patch.json`
creates a child artifact. A patch contains `expected_revision` and any of
`upsert`, `remove`, and `connect`:

```json
{"expected_revision": "<revision returned by create>", "connect": {"R2": {"p": "supply"}}}
```

The supported primitives are resistors, independent voltage sources, diodes,
and MOS instances. Values use SI units; named terminals are `p/n`, `a/k`, and
`d/g/s/b`. Ground is `0`. This layer validates syntax, primitive names and
numeric values; it does not prove full circuit connectivity or model validity.
Model definitions and analysis commands belong in the simulation fixture.

```sh
PYTHONPATH=src python3 -m circuit_tools simulate examples/divider.cir \
  --output runs/my-divider --executable .tools/ngspice/usr/bin/ngspice
```

Use a new output directory for each run. The adapter retains the exact input,
stdout, stderr, simulator log, raw measurements and provenance. It ignores
ngspice startup files and currently accepts self-contained netlists only.
SPICE input is trusted executable simulator input, not a sandboxed upload format.
`completed` means the process completed; acceptance belongs to a separate fixed
evaluator. Missing tools, malformed data, and timeouts do not establish a
physical specification failure. The CLI succeeds only when measurements exist.

## Evidence and limitations

The fixed circuit evaluator checks a 2 V equal-resistor divider against 1 V,
and an 11-point custom native SPICE diode model against the Shockley equation
at 300 K. It records the evaluator hash, simulator binary hash, input hash,
raw measurements, tolerances and outcomes. This checks native `.model` loading;
it does not qualify Verilog-A/OSDI or a TCAD-derived model.

The diode bridge in `circuit_tools.models` fits log current against voltage,
binds the result to a dataset and device revision, checks a disjoint holdout,
and gates SPICE export on validation. It is restricted to 300 K DC/OP and an
explicit voltage domain. Its unit tests use declared synthetic fixture data.
Those tests are software evidence, not physical-device validation.

The [executed bridge replay](../results/toolset/diode-bridge.json) additionally
fits real native-SPICE diode observations and simulates the exported model.
Its maximum current discrepancy was about 0.031%, below the fixed 0.2%
fixture tolerance. This still uses a native-SPICE source device, not TCAD.

The [device reference report](../results/device-reference/latest.json) records
successful executions of the official diode and planar MOS examples. Run
`python3 scripts/audit_device_references.py` to check their finite terminal
currents, final biases and current conservation. These limited checks pass;
they do not qualify mesh refinement or 2D current normalization.
The [reuse spike](reuse-spike.md)
records upstream selection and remaining qualification work.

Still required for the planned first release: qualified geometry edits and
mesh refinement, NMOS DC characterization and fitting, model-domain enforcement
at circuit evaluation, direct-TCAD load-line verification, durable queued jobs
with cancellation/recovery, and tested MCP access. AC, transient, fabrication
readiness and autonomous co-design success are not claimed by this slice.
