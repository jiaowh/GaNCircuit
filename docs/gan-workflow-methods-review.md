# GaN workflow methods review

**Record date: 28 September 2026**  
**Source reviewed:** *AI Agents for GaN Power Electronics Workflow and Methods, V1.docx* (reviewed for workflow methods; see the active [pipeline plan](../plans/gan-halfbridge-pipeline-plan.md) and [build notes](build.md)).

## Adopted methods

Keep the commercial FET and its vendor model as the project baseline. The workflow has three student-owned stages connected by versioned artifacts and explicit acceptance checks:

1. **Datasheet to model (I1):** a qualified, unchanged vendor model, its operating conditions, and its error report.
2. **Layout-aware design (I2):** the selected layout and extracted parasitics, predicted behavior, and test requirements.
3. **Test and closure (I3):** raw measurements, instrument and test settings, measurement error, and uncertainty.

Validate the full measurement chain on the stock board before fabricating a project layout. If tuning is later justified, keep a separate model revision and isolate evidence for driver, layout, probe, and thermal effects; evaluate tuning against held-out data. For layout optimization, fix the topology and search bounded geometry first. Consider component values and dead time when evidence calls for them. Add learned inverse mapping only after collecting examples and establishing a fixed-search baseline.

Define the electromagnetic cross-check method and its pass criteria before relying on extracted parasitics. Freeze predictions for a new board before fabrication and measurement; record the held-out outcome without rewriting the frozen prediction. Evaluate agent assistance against fixed-script and manual baselines, including human interventions, runtime, cost, and failures.

## Project status and boundaries

The owner has selected EPC90133/EPC2302 as the active target. EPC's official
EPC90133 page lists a 100 V, 40 A half-bridge with two EPC2302 plus an EPC2038,
uP1966E, schematic, BOM, Gerbers and a quick-start guide; editable Altium files
are available on request. No ODB++ stackup link is listed. EPC lists an LTspice
model for EPC2302 and a 3 x 5 mm package. These listings do not establish that
files have been downloaded or their reuse terms, nor do they identify the
physical board or its fitted revision. G0 target selection is complete; source
inventory, provenance and terms, board identity, lab inventory and KiCad route
remain open.

The subsequent source check downloaded the EPC2302 datasheet and EPC90133
QSG/schematic and found EPC2302 in the existing vendor LTspice library.
See [the target source record](../devices/epc/epc90133-sources.json) for hashes
and pending files. Model execution and qualification remain open.

Existing scripts implement parts of the workflow, not full autonomy. G1's
LTspice adapter qualification is reusable. The EPC2204 baseline remains an
accepted historical EPC9097 result, with unresolved datasheet table subcharges
recorded as its G2 exception; it does not validate EPC2302. EPC2302's unmodified
model smoke run and datasheet comparisons are open at G2. The EPC9097 switching
bench is historical sensitivity evidence and is paused for the selected target.
Its voltage peaks, ringing interpretation and effective dead-time estimate are
not a safe envelope or validated closure result. The active EPC90133 G3 board
simulation remains open pending file, layout and population identification and
parasitic extraction.
