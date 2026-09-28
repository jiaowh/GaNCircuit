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

## Diode mesh qualification

With the pinned DEVSIM source and runtime configured as described in
[the reuse spike](reuse-spike.md), run:

```sh
python3 scripts/qualify_device_references.py --run
```

The runner compares three junction mesh spacings in the official 1D diode
fixture, retains solver logs, and checks convergence, final terminal-current
balance, and current stability at 0.5 V. The endpoint spacing stays fixed, so
this is a local junction-refinement check, not global mesh convergence over a
bias domain. Its current convention is A/cm² for the 1D model's unit area.
The [qualification report](../results/device-reference/qualification.json)
records the policy, tolerances, provenance, and observed results.

The executed three-mesh check used 399, 465, and 531 nodes. Its largest
adjacent current change was about 0.0012%, within the declared 0.1% relative
plus 1e-12 A/cm² absolute tolerance. All eight solves on each mesh reported
convergence. The reference audit also rejects incomplete reports, malformed
current records, and log-hash mismatches when a recorded hash is available.

This numerical diode check does not qualify the planar NMOS mesh or its 2D
out-of-plane normalization. Those checks remain prerequisites for the NMOS
characterization and circuit-model bridge.

## Device-to-circuit current units

`circuit_tools.device_units.current_per_cm_to_amperes(current_a_per_cm, width_m)`
converts a signed 2D current in A/cm of out-of-plane width to amperes using a
separately declared width in metres. For example, 3 A/cm at a 1 µm width gives
300 µA. Use it only after establishing the backend's current convention.
The lateral gate dimension in the cross-section is not this width. Exported
amperes must not receive another width multiplier in the circuit model.

With the same local DEVSIM environment, replay the normalization check with:

```sh
python3 scripts/qualify_current_normalization.py
python3 scripts/qualify_planar_mos.py --run --refinements 2
```

The [normalization report](../results/device-reference/current-normalization.json)
compares two uniform resistor cross-sections against `J = q n mu V/L` and
`I_native = J * contact_width_cm`. Both contact-current balance and the
two-width scaling check pass. This establishes the A/cm convention for the
tested cm-based 2D equations; it does not validate MOS physics or terminal charge.

The [planar-MOS report](../results/device-reference/planar-mos-qualification.json)
retains adjacent mesh comparisons at Vg = Vd = 0.5 V, Vs = Vb = 0 V and 300 K.
Subdivision preserves physical names, region areas, contact/interface lengths,
and the bounding box. Acceptance uses a fixed 1% relative plus 1e-10 A/cm
absolute current tolerance. The original mesh versus its first refinement
changes drain/source current by about 2.9%, exceeding that tolerance.
`--refinements 2` also evaluates the next finer mesh; the report records its
outcome separately and accepts only the last adjacent pair. Even a passing
endpoint comparison does not qualify an entire bias domain or local slopes.

The executed three-mesh run completed all nine solves per mesh. Bulk-region
node counts were 2249, 8752, and 34523; adjacent drain-current changes were
2.886% and 1.395%. The last comparison therefore remains **unresolved** under
the fixed 1% tolerance. The finest case took about 236 seconds, close to the
240-second per-case limit. Targeted refinement and investigation of the
near-contact/junction discretization are the next tasks; simply increasing
the tolerance would not qualify the existing mesh. These results concern
numerical stability of the research model, not fabricated-device accuracy.

## Optimized math runtime and MOS endpoint check

The [four-level uniform-mesh run](../results/device-reference/planar-mos-openblas-qualification.json)
passes the last adjacent comparison with 0.184% drain-current change, retaining
the same 1% relative plus 1e-10 A/cm absolute tolerance. All nine solves on each
mesh converge. This is an endpoint check at Vg = Vd = 0.5 V, not a bias-domain
or transconductance qualification.

The run uses workspace-local OpenBLAS, pinned in
[math-runtime-lock.json](../devices/math-runtime-lock.json). The
[same-mesh runtime check](../results/device-reference/math-runtime-comparison.json)
passes at 1e-8 relative plus 1e-10 A/cm absolute tolerance: drain, gate and
source currents match the original runtime exactly in the retained records;
the body-current difference is about 5.5e-16 A/cm. The level-2 run took about
84 seconds versus 236 seconds previously; this is an observed replay timing,
not a controlled performance benchmark. The finest level took about 545 seconds.

Prepare the optional runtime on this Ubuntu/WSL host, after the existing
DEVSIM prerequisites in [reuse-spike.md](reuse-spike.md):

```sh
mkdir -p .tools/downloads
(cd .tools/downloads && apt-get download libopenblas0-pthread=0.3.26+ds-1ubuntu0.1)
echo '7dc3b4384c02aecb87eb8b70fa26c5843a08af242f4638aa4b36922bdc4f5b04  .tools/downloads/libopenblas0-pthread_0.3.26+ds-1ubuntu0.1_amd64.deb' | sha256sum --check
dpkg-deb -x .tools/downloads/libopenblas0-pthread_0.3.26+ds-1ubuntu0.1_amd64.deb .tools/openblas
export PYTHONPATH="$PWD/.tools/python"
export LD_LIBRARY_PATH="$PWD/.tools/runtime/usr/lib/x86_64-linux-gnu:$PWD/.tools/openblas/usr/lib/x86_64-linux-gnu/openblas-pthread"
export DEVSIM_MATH_LIBS="$PWD/.tools/openblas/usr/lib/x86_64-linux-gnu/openblas-pthread/libopenblas.so.0"
export OPENBLAS_NUM_THREADS=1
python3 scripts/qualify_planar_mos.py --run --refinements 3 --timeout 600 \
  --out results/device-reference/planar-mos-openblas-qualification.json
```

Two local-refinement experiments are retained as rejected research attempts:
[transition splits](../results/device-reference/planar-mos-local-qualification.json)
and [Delaunay edge repair](../results/device-reference/planar-mos-delaunay-qualification.json).
Their early levels disagreed with the uniform sequence, and their final solves
were stopped. The local policy is not an accepted replacement for uniform
refinement. Implementation snapshots and exact mesh/log hashes support replay
of the successful uniform run.

## NMOS DC characterization

The [executed characterization report](../results/device-reference/nmos-dc-characterization.json)
records nine completed DC points in 172.5 seconds at 300 K. Vgs and Vds each
take 0.45, 0.50, and 0.55 V; source and body stay at zero. Before execution,
the experiment reserves the complete Vgs = 0.50 V slice (three points) for
holdout and the other six points for training. No model has been fitted.

Using the environment exports in the OpenBLAS section above, replay with:

```bash
python3 scripts/characterize_planar_mos.py --mesh-level 2 --timeout 600
```

The runner checks the accepted mesh, pinned upstream source, physics hash,
math libraries, and thread setting before execution. Its unique work directory
retains the experiment, runner snapshot, mesh, solver diagnostics, terminal
currents, and immutable dataset. The report links these artifacts by SHA-256.
`NMOSDataset` rejects nonfinite currents, nonconverged points, duplicate
biases, incomplete or overlapping splits, and excessive current imbalance.
Currents remain in A/cm; conversion to amperes requires an explicit device width.

A passing collection means all scheduled data satisfy this software contract.
The original collection report retains its endpoint-only qualification scope.
The separate grid comparison below adds mesh evidence at the sampled biases
and for finite-span secants; it does not establish continuous-domain or model
accuracy. These are numerical reference simulations, with no physical-device
validation claim.

### Mesh agreement over the sampled grid

The [level-3 characterization](../results/device-reference/nmos-dc-characterization-fine.json)
completed all nine points in 1037.8 seconds. The
[grid comparison](../results/device-reference/nmos-characterization-comparison.json)
passes all 36 terminal-current comparisons and six centred secant comparisons
against level 2. The largest drain-current change is 0.187163%; the largest
gm and gds changes are 0.009754% and 0.172651%, respectively. The fixed thresholds
are 1% plus 1e-10 A/cm for currents and 1% plus 1e-8 S/cm for secants.
Near-zero gate/body currents use the absolute floor; relative changes there
are not useful accuracy measures.

```bash
python3 scripts/characterize_planar_mos.py --mesh-level 3 --timeout 1800 \
  --out results/device-reference/nmos-dc-characterization-fine.json
python3 scripts/compare_nmos_characterization.py \
  results/device-reference/nmos-dc-characterization.json \
  results/device-reference/nmos-dc-characterization-fine.json \
  --out results/device-reference/nmos-characterization-comparison.json
```

The comparator verifies every required worker artifact, dataset fingerprint,
raw point records, solver-convergence receipts, experiment/split consistency,
and links to the accepted endpoint mesh and runtime qualification. It records
input, implementation and policy hashes. Invalid evidence is `unresolved`;
complete converged evidence exceeding tolerance is `fail`. Passing establishes
agreement at the nine sampled biases and for the six 0.10 V secants only.

### Reusable dataset and slope operations

The CLI can validate and store a characterization dataset, then calculate its
six centred drain-current secants. These operations share `NMOSDataset` and
`dc_secants` with the verification scripts. Replace the dataset path with the
`dataset_path` recorded in the relevant run report:

```bash
PYTHONPATH=src python3 -m circuit_tools --store runs/nmos-store nmos-import \
  results/device-reference/nmos-characterization-work/7691c1a627154de8bcc1db7dcd23cd50/dataset.json
PYTHONPATH=src python3 -m circuit_tools --store runs/nmos-store nmos-secants \
  e222b6dfd8625bd9bb85dc49b4978a358edc9509071d71caddafe87e1741eed5
```

The second command uses the artifact ID returned by the first for the retained
original dataset. The [executed secant output](../results/device-reference/nmos-dc-secants.json)
binds its calculations to that dataset fingerprint. Each metric retains its
endpoint IDs, biases, currents, span, numerator, and S/cm units. The helper
rejects incomplete/asymmetric grids and nonfinite arithmetic. Calculating a
secant does not qualify mesh or derivative accuracy.

### Central slope step-size check

The [fixed verification policy](../devices/nmos-grid-verification-policy.json)
declares half-spans of 0.05, 0.025, and 0.0125 V about Vgs = Vds = 0.50 V.
All three level-2 grids completed. The
[step-size comparison](../results/device-reference/nmos-step-size-comparison.json)
passes the fixed 1% plus 1e-8 S/cm tolerance for both adjacent comparisons.
For the final reduction, central gm changes by 0.000437% and gds by 0.001551%.
This is fixed-mesh, central-bias numerical evidence; smaller-stencil mesh
accuracy and continuous-domain accuracy remain separate checks.

With the OpenBLAS environment configured above:

```bash
python3 scripts/characterize_planar_mos.py --mesh-level 2 --half-span .025 \
  --out results/device-reference/nmos-dc-characterization-half-step.json
python3 scripts/characterize_planar_mos.py --mesh-level 2 --half-span .0125 \
  --out results/device-reference/nmos-dc-characterization-quarter-step.json
python3 scripts/compare_nmos_step_sizes.py \
  results/device-reference/nmos-dc-characterization.json \
  results/device-reference/nmos-dc-characterization-half-step.json \
  results/device-reference/nmos-dc-characterization-quarter-step.json \
  --out results/device-reference/nmos-step-size-comparison.json
```

At the smallest step, gm is 0.557864 S/cm and gds is 8.807663 S/cm;
their ratio is about 0.06334. This diagnostic suggests revisiting the physical
device or operating point before targeting voltage gain. It is not an
executed amplifier result. The intended physical-device revision and
independent circuit validation remain unfinished.

## Generated planar NMOS (candidate lc1)

The upstream `gmsh_mos2d` reference is retired as the amplifier candidate and
kept as a numerical regression fixture (see AGENTS.md). Its replacement is
generated from one specification,
[planar-nmos-lc1.json](../devices/planar-nmos-lc1.json): geometry, doping,
junction grading, contacts, supply and mesh spacings. `scripts/planar_nmos.py`
builds the structure with DEVSIM's internal 2D mesher (no gmsh) and the upstream
`simple_physics` package: constant mobility, SRH, no velocity saturation,
no gate tunneling or interface charge, 300 K. The spec's `junction_depth` is the
half-point of the erfc source/drain profile; the metallurgical junction is
reported by `inspect`. Currents are A/cm (x100 = uA/um).

With the DEVSIM/OpenBLAS environment exports above:

```bash
python3 scripts/planar_nmos.py inspect devices/planar-nmos-lc1.json --mesh-scale 2
python3 scripts/planar_nmos.py sweep devices/planar-nmos-lc1.json --mesh-scale 2
for s in 2 1 0.5; do
  python3 scripts/planar_nmos.py op devices/planar-nmos-lc1.json --vg 0.6 --vd 1.65 --mesh-scale $s
done
# metrics and plots (needs matplotlib for the PNG; Windows Python works)
python scripts/analyze_planar_nmos.py results/nmos-design/lc1/sweep-mesh2.json \
  --structure results/nmos-design/lc1/inspect-mesh2.json
python scripts/analyze_planar_nmos.py --op results/nmos-design/lc1/op-mesh2.json \
  results/nmos-design/lc1/op.json results/nmos-design/lc1/op-mesh0.5.json
```

A point is recorded only after a DEVSIM solve that did not raise, and only if
terminal currents are conserved within 1e-6 relative plus 1e-9 A/cm. The
observed conservation residual is an absolute floor of about 1e-11 to 2e-10
A/cm, so currents below about 1e-9 A/cm (0.1 pA/um) are marked unresolved.
The Newton relative-update target is 1e-6: tighter targets stall in roundoff
noise from near-zero electron densities when the device is off at high drain bias.

**Structure** ([inspect](../results/nmos-design/lc1/inspect-mesh2.json)):
L = 1 um gate over 10 nm oxide with n+ poly; surface junctions at 0.544 and
1.456 um (44 nm gate overlap each side, 0.91 um metallurgical channel);
source/drain junction 0.153 um deep; contacts touch only n+ (source/drain),
p (body) and n+ poly (gate).

**Curves** ([sweep](../results/nmos-design/lc1/sweep-mesh2.json),
[analysis](../results/nmos-design/lc1/analysis-mesh2.json), plot
`results/nmos-design/lc1/analysis-mesh2.png`; coarse mesh, 2883 bulk nodes,
208 s): subthreshold slope 79.5 mV/dec, linear-extrapolated Vt 0.38 V
(constant-current 0.34 V), DIBL 6.5 mV/V, Ion 570 uA/um and Ioff 13.5 pA/um at
3.3 V (ratio 4e7), flat output saturation. At Vd = 1.65 V, gm/gds is 241, 113
and 69 at Vg = 0.5, 0.75 and 1.0 V (the old reference: 0.063). These agree
with hand estimates (Vt about 0.3 V, SS about 77 mV/dec). The coarse-mesh curves
are exploratory; only the operating point below has a mesh check.

**Amplifier operating point** ([amplifier-point](../results/nmos-design/lc1/amplifier-point.json)):
common-source stage, RD to VDD = 3.3 V, Vout,Q = VDD/2 for swing. |Av| = gm RD /
(1 + gm RD / (gm/gds)) with gm RD = (gm/Id)(VDD - Vout), so |Av| of about 10 needs
gm/Id of about 7 /V, reached at Vgs = 0.6 V (Vov about 0.2-0.25 V). Finest-mesh
stencil (45879 bulk nodes): Id 4.19 uA/um, gm/Id 7.20 /V, gm/gds 172. With W =
23.9 um: Id = 100 uA, RD = 16.5 kOhm, gm = 0.72 mS, gm RD = 11.9, **Av = -11.1**,
330 uW. gm/gds exceeds the stage gain about 15x. Across three meshes (4x node steps)
gm/Id and gm/gds change 0.9%/0.6% and 1.3%/0.7%; Id changes 3.5% then 2.1%,
so the bias current carries roughly 3% mesh uncertainty. With gm/Id = 7.2 /V, a
10 mV threshold shift moves Id by about 7%, so the circuit should set Vgs for
the target Vout from the fitted model rather than fixing 0.6 V.

Not yet done: a compact model fitted over the operating region, ngspice
simulation of the amplifier with that model, a direct-TCAD load-line check,
and dynamic behavior. Constant mobility without velocity saturation or
mobility degradation makes strong-inversion currents optimistic; the chosen
low-overdrive point is less affected.
