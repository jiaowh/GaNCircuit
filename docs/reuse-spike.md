# Reference and reuse spike

This spike is pinned to the source snapshots present under `devices/` and keeps
backend availability separate from source inspection. It does not claim TCAD
results when the simulator is absent.

## Environment result

On 2026-09-14 the host initially had no `ngspice`, `devsim`, or `gmsh`
executable, and WSL could not create an instance without escalation. A
workspace-local DEVSIM 2.11.0 wheel, NumPy 2.2.6, ngspice 42, and extracted
Ubuntu BLAS/LAPACK/gfortran runtime are now available under `.tools/`. The
official diode and planar-MOS scripts both complete with return code 0 under
that isolated runtime. This is script execution evidence only: it does not
establish physical acceptance, calibration, or mesh/convergence qualification.

Replay with the pinned source and local runtime:

For a fresh checkout, obtain the official sources and install the Python
packages in a local environment. Linux BLAS/LAPACK must be available to DEVSIM:

```sh
git clone https://github.com/devsim/devsim devices/devsim-upstream
git -C devices/devsim-upstream checkout 43b41ca845184c47e22b72d144db7e7db8509377
python3 -m pip install --target .tools/python devsim==2.11.0 numpy==2.2.6
```

The exact wheel and Ubuntu runtime package hashes used on this host are in
[`runtime-lock.json`](../devices/runtime-lock.json). The exports below apply to
the project-local Ubuntu library extraction on this host; use the appropriate
system library paths on another Linux installation.

```text
export PYTHONPATH="$PWD/.tools/python"
export LD_LIBRARY_PATH="$PWD/.tools/runtime/usr/lib/x86_64-linux-gnu:$PWD/.tools/runtime/usr/lib/x86_64-linux-gnu/blas:$PWD/.tools/runtime/usr/lib/x86_64-linux-gnu/lapack"
export DEVSIM_MATH_LIBS="$PWD/.tools/runtime/usr/lib/x86_64-linux-gnu/blas/libblas.so.3:$PWD/.tools/runtime/usr/lib/x86_64-linux-gnu/lapack/liblapack.so.3"
python3 scripts/device_reference.py --run
python3 scripts/audit_device_references.py
```

The runner copies input meshes into an isolated work directory, records complete
stdout/stderr logs, checks the DEVSIM commit pin, and exits nonzero for an
unavailable or failed reference. A missing backend is never treated as a pass.

## DEVSIM reference

Source: `devices/devsim-upstream`, expected commit
`43b41ca845184c47e22b72d144db7e7db8509377` (official repository
[`devsim/devsim`](https://github.com/devsim/devsim)). The snapshot contains the
official `examples/diode/diode_1d.py` and
`examples/mobility/gmsh_mos2d.py` references. The diode ramps contact bias to
0.5 V; the MOS example loads the Gmsh mesh and ramps gate and drain bias. These
are source-level facts, not completed simulation results. The upstream license
is Apache-2.0, SHA-256
`3ddf9be5c28fe27dad143a5dc76eea25222ad1dd68934a047064e56ed2fa40c`.

Reuse decision: adopt the official diode and planar-MOS scripts as provenance
fixtures after a Linux environment with real DEVSIM is available. Keep their
mesh, contact definitions, solver settings, convergence state, and output files
in the evidence record. Parameterization must first regenerate geometry from a
single device specification; changing a Python label alone is insufficient.
The 2-D current convention and charge behavior remain qualification items.

## SpiceXplorer leaf-package inspection

Source: `devices/spicexplorer-release`, expected commit
`263d0322f8900dc331536fbbe6c0e804514fc454` (release README identifies v1.1.2).
The release table and package READMEs describe these leaf packages:
`spicexplorer-core`, `spicexplorer-circuitgraph`, `spicexplorer-netlist2xschem`,
`spicexplorer-netlist2tf`, `spicexplorer-gmid`, `spicexplorer-waveview`,
`spicexplorer-layout`, and `spicexplorer-signoff`. Their useful reusable
contracts are deterministic netlist graph/round-trip, symbolic transfer
function with recorded assumptions, waveform loading and measurements, and
structured unavailable verdicts for missing layout/signoff tools.

Reuse decision: use `spicexplorer-core` plus `spicexplorer-circuitgraph` as
candidate circuit representation references, and `spicexplorer-waveview` as a
candidate result/measurement contract. Do not make them a dependency of the
device backend yet. `spicexplorer-core` wraps SPICE through `spicelib` and still
requires a simulator for live results. The package READMEs explicitly describe
runtime discovery and unavailable outcomes for signoff tools, which matches the
runner's honest-failure requirement. The `netlist2xschem` README currently
mentions a peer `spicexplorer-circuitgraph` dependency despite the release table
describing leaf tools as peer-independent; resolve this packaging inconsistency
before adoption.

Licensing: the checked-out release has `platform/LICENSE` and
`analog-db/LICENSE` (both SHA-256
`6377c6f314b79302972d6a34a9ab7c4a90c4b445b402c9dbf20937d73093bb35`), but no
per-package LICENSE or root LICENSE. Record the applicable license text and
package provenance before redistributing any leaf package. This is an adoption
gate, not a claim that the code is unlicensed.

## ngspice wrapper comparison

Pinned primary-source wrapper: `devices/mcp-spice` at commit
`034813cd2e445dfb06f1efcb643f5926582fa1f8`, MIT license (LICENSE SHA-256 to be
recorded before redistribution). Its documented contract is a content-addressed
UTF-8 netlist, bounded `.op`/transient/DC analyses, structured readings and
documentary receipts. The implementation explicitly treats nonzero ngspice exit,
missing output, timeout, and even exit-0 error text as failures. This is a good
reference for result identity and failure semantics. It has not been executed
here because Deno is not installed; the local ngspice binary is 42 while the
wrapper source targets ngspice 44.2. It is therefore an inspected wrapper, not
an adopted backend.

The SpiceXplorer core contract remains the candidate Python circuit layer. A
future comparison should run the same netlist and observables through direct
batch ngspice and one wrapper, recording simulator version, raw output, recipe,
and result hashes.
