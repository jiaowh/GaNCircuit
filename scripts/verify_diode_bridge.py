#!/usr/bin/env python3
"""Exercise fitting/validation/export on real SPICE data (not TCAD evidence)."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from circuit_tools.ltspice import run_ltspice
from circuit_tools.models import CharacterizationDataset, ShockleyDiodeModel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", default=None)
    args = parser.parse_args()
    output = ROOT / "runs" / ("diode-bridge-" + uuid.uuid4().hex)
    source = ROOT / "examples/ltspice/diode_dc.cir"
    reference = run_ltspice(source, output / "reference", executable=args.executable)
    if reference.status != "completed" or not reference.measurements:
        print(json.dumps({"outcome": "unresolved", "message": reference.message}))
        return 2
    device = "native-spice-fixture:" + hashlib.sha256(source.read_bytes()).hexdigest()
    points = [{"id": f"point-{i}", "voltage": v, "current": current, "temperature": 300.0}
              for i, (v, current) in enumerate(zip(reference.measurements["v(anode)"], reference.measurements["i(d1)"])) if v >= .2]
    train = [r["id"] for i, r in enumerate(points) if i % 2 == 0]
    holdout = [r["id"] for i, r in enumerate(points) if i % 2]
    dataset = CharacterizationDataset.from_records(points, {"device_revision": device, "source": reference.provenance}, train, holdout)
    model = ShockleyDiodeModel.fit(dataset, device_revision=device, name="fitted_diode").validate(dataset, max_relative_error=.002)
    netlist = "\n".join(("* Exported fitted diode fixture", "V1 anode 0 0", "D1 anode 0 fitted_diode",
        model.export_spice(), ".temp 26.85", ".options tnom=26.85 gmin=1e-18", ".dc V1 0.2 0.5 0.05", ".end", ""))
    replay = run_ltspice(netlist, output / "exported", executable=args.executable)
    error = None
    if replay.status == "completed" and replay.measurements:
        currents = replay.measurements["i(d1)"]
        if len(currents) == len(points):
            error = max(abs(actual - row["current"]) / row["current"] for actual, row in zip(currents, points))
    report = {"schema": "diode-bridge/1", "scope": "Native LTspice diode fixture data; not a TCAD-derived physical device",
        "simulator": "ltspice",
        "outcome": "pass" if error is not None and error <= .002 else "unresolved",
        "dataset_hash": dataset.fingerprint, "device_revision": device,
        "train_ids": train, "holdout_ids": holdout, "heldout_mean_relative_error": model.heldout_error(dataset),
        "export_replay_max_relative_error": error, "tolerance": .002, "model": model.export_spice(),
        "reference_provenance": reference.provenance, "replay_provenance": replay.provenance,
        "evidence_directory": str(output.relative_to(ROOT))}
    destination = ROOT / "results/toolset/diode-bridge.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"outcome": report["outcome"], "report": str(destination), "export_error": error}, indent=2))
    return 0 if report["outcome"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
