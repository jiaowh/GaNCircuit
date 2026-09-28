# Building and running the first slice

The library has no mandatory runtime dependencies beyond Python 3.10+. Circuit
simulations use LTspice through `circuit_tools.ltspice`; ngspice was removed
on 28 September 2026 when LTspice became the project simulator. GaN and
LTspice commands run natively on Windows from the repository root. The paused
DEVSIM device fixture still runs under Linux or WSL (see the later sections).

```sh
PYTHONPATH=src python -m pytest -q tests
PYTHONPATH=src python -m circuit_tools capabilities
PYTHONPATH=src python -m circuit_tools circuit-create examples/divider.json
PYTHONPATH=src python scripts/verify_ltspice_fixtures.py
PYTHONPATH=src python scripts/verify_diode_bridge.py
PYTHONPATH=src python scripts/epc2204_baseline.py
```

### LTspice installation

Install LTspice from the
[official Analog Devices download](https://ltspice.analog.com/software/LTspice64.msi).
On this host it was installed on 28 September 2026 from an MSI whose Authenticode
signature is valid (Analog Devices International UC), SHA-256
`249ebde3c84e01f4ce5b5ff78c6c7588f049bac85ae1635f968cfdbe4f4ecd03`, with
`msiexec /i LTspice64.msi /qn`. That installs per-user without administrator
rights, at `%LOCALAPPDATA%\Programs\ADI\LTspice\LTspice.exe`, version
26.1.1.0. The adapter finds that path, `C:\Program Files\ADI\LTspice`, the
`LTSPICE_EXE` environment variable, or an explicit `--executable`. An explicit
path never falls back to another installation.

### Vendor model files

EPC files live in `vendor/epc/`, which git ignores because the library is
"all rights reserved". `devices/epc/sources.json` records each URL, retrieval
date and SHA-256. EPC's server rejects requests without a browser-like
User-Agent. `scripts/epc2204_baseline.py` refuses to run if the downloaded
`EPCGaNLibrary.zip` does not match the recorded checksum, and it extracts the
`.lib` file itself.

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
PYTHONPATH=src python -m circuit_tools simulate bench.cir --library EPCGaNLibrary.lib \
  --output runs/my-bench
```

Use a new output directory for each run. The adapter keeps the exact
netlist, copies and hashes every model library the netlist loads, and retains
the LTspice log, the `.raw` waveforms, the parsed `result.json` and the
provenance record. A netlist may load only libraries passed with `--library`,
referenced by bare file name. A supplied library that itself loads other
files is rejected.

A run is `completed` only when all of these hold:
- LTspice exits with status 0;
- it writes a finite, parseable `.raw` file with at least one point;
- the log has no unrecovered failure;
- every `.meas` declared in the netlist has a value;
- the log's "Files loaded" list names only the bench and the supplied
  libraries.

Otherwise the run is `failed`, with every reason in its message. The log rules
come from real LTspice 26.1.1 output:
- Setup errors appear as `bench.cir(3): This sub-circuit name is not
  defined.`, without the word "error".
- Terminal solver failures ("Time step too small", "Singular matrix",
  "Iteration limit reached") take precedence over warning phrases such as
  "too small". A second review found this gap.
- A failed operating-point method followed by a successful one (for example
  Newton, then Gmin stepping) is a normal recovery, not an error.
- Only declared `.meas` names count as measurements; lines such as
  `temp = 27` do not.
- Unclassified lines (for example `Changing Tseed`) are kept as notices in the
  provenance record.

In batch mode LTspice 26.1.1 does not load its own standard component
libraries: an undefined `1N4148` fails as an undefined model. Acceptance belongs to a separate fixed evaluator. Missing
tools, malformed data and timeouts do not establish a physical specification
failure. SPICE input is trusted executable simulator input, not a sandboxed
upload format.

Raw-file notes established by the fixtures:
- Traces are float32 unless `.options numdgt` is above 6, which makes LTspice
  store float64. Float32 limits absolute agreement to about 1e-7 relative.
- LTspice sorts `.ac list` frequencies.
- When each `.step` has a single AC point, the file is indexed by the stepped
  parameter instead of frequency.

## Evidence and limitations

The [LTspice fixture report](../results/toolset/ltspice-fixtures.json) checks
the adapter against analytical answers:
- a resistive divider (`.op`);
- an RC step response (trace and `.meas`);
- RC magnitude and phase at the corner frequency (complex AC);
- a nested DC sweep split into its steps (float64 traces);
- an 11-point Shockley diode at 300 K;
- binary against ASCII output of the same bench.

All pass with LTspice 26.1.1. The first run failed two checks because of
evaluator assumptions (frequency ordering, and a float32 tolerance), which were
corrected as noted above. On 28 September 2026 the project owner opened the EPC2204 RDS(on) bench in
LTspice's interactive window. All seven operating-point values matched the
batch run to the window's 6 significant figures
([record](../results/toolset/ltspice-gui-check.json)). Only one
operating-point bench was compared this way.

The diode bridge in `circuit_tools.models` fits log current against voltage,
binds the result to a dataset and device revision, checks a disjoint holdout,
and gates SPICE export on validation. It is restricted to 300 K DC/OP and an
explicit voltage domain. Its unit tests use declared synthetic fixture data.
Those tests are software evidence, not physical-device validation.

The [executed bridge replay](../results/toolset/diode-bridge.json) additionally
fits real native-SPICE diode observations and simulates the exported model.
It now runs through LTspice. Its maximum current discrepancy is about 0.032%
(0.031% previously under ngspice), below the fixed 0.2% fixture tolerance.
This still uses a native-SPICE source device, not TCAD.

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

Not yet done: a compact model fitted over the operating region, circuit-simulator
simulation of the amplifier with that model, a direct-TCAD load-line check,
and dynamic behavior. Constant mobility without velocity saturation or
mobility degradation makes strong-inversion currents optimistic; the chosen
low-overdrive point is less affected.

## EPC2204 vendor-model baseline (Stage 1, first slice)

`scripts/epc2204_baseline.py` runs the unmodified `EPC2204` subcircuit from
EPC's LTspice library (version 1.105, 10 June 2026) at the conditions of the
datasheet's electrical-characteristics table (datasheet revised 26 November
2024). Its comparison rules are fixed in the script:
- limit compliance and deviation from the typical value are reported
  separately. Being inside a datasheet limit does not show accuracy.
- A row is flagged for review when it is outside a limit or more than ±25%
  from the typical value. The band is a screening aid, not an acceptance
  tolerance.

All benches use `.options reltol=1e-6` (see the gate-charge finding below).
The script writes [the baseline report](../results/gan/epc2204-baseline.json)
and [simulated curves](../results/gan/epc2204-model-curves.json): output and
transfer characteristics, COSS against VDS, and the VGS–QG gate-charge curve.
These are for the later comparison with digitized datasheet curves.

Result, 28 September 2026 (second revision): all 14 benches complete.

| Quantity | Model | Datasheet typ (limits) | Deviation from typ | Review |
|---|---|---|---|---|
| RDS(on), 5 V, 16 A | 4.40 mΩ | 4.4 (max 6) mΩ | 0.0% | no |
| VGS(th), 4 mA | 1.17 V | 1.1 (0.8–2.5) V | +6.4% | no |
| VSD, 0.5 A | 1.61 V | 1.6 V | +0.3% | no |
| CISS / CRSS / COSS at 50 V | 644.5 / 2.31 / 304.8 pF | 644 (max 851) / 2.3 / 304 (max 456) pF | +0.1 / +0.6 / +0.3% | no |
| COSS(ER) / COSS(TR), 0–50 V | 401.4 / 501.6 pF | 401 / 501 pF | +0.1 / +0.1% | no |
| QOSS, 50 V | 25.1 nC | 25 (max 38) nC | +0.3% | no |
| QG, 50 V, 16 A, 5 V | 5.65 nC | 5.7 (max 7.4) nC | −0.8% | no |
| QGS | 1.35 nC | 1.8 nC | −24.9% | no (at the band edge) |
| QGD | 0.65 nC | 0.8 nC | −18.6% | no |
| QG(TH) | 0.73 nC | 1.0 nC | −27.5% | yes |

**Gate-charge finding.** The first baseline reported QG = 3.8 nC (−33%). That
was a simulation artifact.
- *Cause:* with LTspice's default `reltol` (1e-3), the transient loses gate
  charge once the transistor is on. QG fell to 2.5 nC at a 0.02 ns step and
  2.45 nC at 2 mA drive. Changing the integration method, `chgtol` or the
  solver did not help; `reltol=1e-6` did.
- *Now:* QG = 5.652 nC. Tightening to 1e-7 changes it by 3e-9 (relative).
  That shows insensitivity to further `reltol` tightening at the chosen time
  step, not absolute accuracy at that level.
  QG from the model's own charge equations, with parameters read from the
  local library, between the simulated start and VGS = 5 V states, is
  5.647 nC (0.1% agreement, declared tolerance 1%). A small-signal check at
  VGS = 3–4.5 V gives about 1085 pF, matching the equations' 1.085 nC per
  volt there.
- *Separate probe:* LTspice honours charge expressions that depend on other
  nodes' voltages; a known-answer probe gave exactly 2.000 mA.
- *What remains:* QGS, QGD and QG(TH) are 19–28% below the typicals under
  both the transient and the equations. These are unresolved differences in
  extracted values, not established model errors, until EPC's boundary
  definitions are matched. Candidates are EPC's extraction
  definitions (not stated), test conditions, or the model's
  sub-threshold/plateau charge. QGD depends strongly on where the plateau is
  taken to end: 0.38 / 0.65 / 1.00 nC for VDS = 10 / 5 / 1 V. No model
  tuning is justified.

Gate-charge bench self-checks, all recorded in the report:
- *Starting bias:* VGS 0.046 V, VDS 50.0 V, 16 A in the clamp diode, the
  transistor off.
- *Gate-current balance:* residual under 0.7 nA against a 10 mA drive.
- *Integration resolution:* halving the samples changes QG by 2e-6.
- *Drain transition:* at VGS = 5 V, VDS is 0.070 V and the transistor carries
  16 A.
- *Plateau:* about 2.05 V.
- *Drive current:* the declared check (10 mA against 2 mA, 0.5% tolerance)
  **fails** at +0.57%. A diagnostic added afterwards integrates the model's
  gate-leakage current: 6.6 pC at 10 mA, 35 pC at 2 mA. With leakage removed,
  the stored charge agrees to 0.06%. This diagnostic evidence supports
  leakage as the main cause; it does not conclusively resolve the
  difference.

Other results:
- *COSS consistency:* output charge integrated from the small-signal COSS
  curve agrees with a 0 → 50 V transient ramp to 0.002% (tolerance 2%).
- *Temperature:* RDS(on) rises by a factor of 1.70 from 25 °C to 125 °C in
  the model. The datasheet curve has not been digitized.
- *Not independent validation:* the close agreement in resistance,
  capacitance, output charge and total gate charge may reflect the quantities
  EPC fitted the model to.

The equation comparison checks numerical consistency with the vendor
model. These are model-to-datasheet consistency results. Datasheet values are
vendor-described, and nothing here is a hardware measurement. The first
revision of this report used one combined outcome that called QG
"inside-datasheet-limits" only because it was below the maximum. It was
replaced after review.

### Gate-charge curve against datasheet Figure 7

EPC's datasheet figures are vector drawings, so they can be read exactly
rather than traced from an image.

- **Digitizing.** `scripts/digitize_datasheet_figure.py` reads the plotted
  polyline and calibrates the axes by fitting the tick-label positions. It
  needs PyMuPDF, which runs under WSL; Windows Smart App Control blocks it on
  the host.

  ```sh
  python3 scripts/digitize_datasheet_figure.py --page 3 --region 330 295 600 500 \
    --curve-color 0 0.47 0.29 --x-name qg_nC --y-name vgs_V \
    --figure "Figure 7: Gate Charge (ID = 16 A, VDS = 50 V)" \
    --output results/gan/epc2204-fig7-digitized.json
  python scripts/compare_epc2204_gate_charge.py
  ```

  [Figure 7](../results/gan/epc2204-fig7-digitized.json) has 25 vertices.
  Tick-label calibration residuals are 0.015 nC and 0.034 V, and the frame
  corners map to 0–5.99 nC and 0–4.99 V. The trace's half line width
  corresponds to about 0.03 V.
- **Comparison rule.** The rule in `scripts/compare_epc2204_gate_charge.py`
  is: model VGS within ±0.10 V of the datasheet VGS at every vertex's charge.
  It was chosen after the datasheet coordinates were extracted, but before
  any model comparison. The model curve is shifted by 0.028 nC for the
  bench's 0.046 V starting gate voltage.
- **Result, 28 September 2026:** [pass](../results/gan/epc2204-fig7-comparison.json).
  The worst difference is 0.014 V, at the knee after the plateau.

| Feature (same algorithm for both) | Model | Datasheet curve | Datasheet table |
|---|---|---|---|
| Plateau voltage | 2.06 V | 2.04 V | — |
| Plateau start (plateau-based QGS) | 1.37 nC | 1.39 nC | QGS 1.8 nC |
| Plateau width, ±0.05 V band | 1.03 nC | 1.00 nC | QGD 0.8 nC |
| Charge at VGS = 1.17 V (model VGS(th)) | 0.75 nC | 0.75 nC | QG(TH) 1.0 nC |
| Charge at VGS = 5 V | 5.66 nC | 5.67 nC | QG 5.7 nC |

- **What it shows.** The unmodified model reproduces the curve EPC drew. The
  subcharge differences reported against the table also appear between EPC's
  own curve and its own table. So the table's QGS, QGD and QG(TH) use boundary
  definitions or data that are not stated and are not reproduced by
  plateau-based extraction from the published curve. They are no longer
  evidence of a model discrepancy. They remain unresolved as extracted values,
  and EPC's definitions would be needed to settle them.
- **Limits.** The close fit may reflect that EPC fitted the model to this
  curve, so it is consistency, not independent validation. Both sides are
  vendor material; no hardware has been measured.
