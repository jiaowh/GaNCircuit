"""Small JSON CLI over the engineering library."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from .adapters import discover_capabilities, run_ngspice
from .core import ArtifactStore, Circuit, CircuitPatch, RevisionConflict, ValidationError
from .nmos_data import NMOSDataset
from .nmos_metrics import dc_secants


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="circuit-tools")
    parser.add_argument("--store", default="runs/store")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("capabilities")
    create = commands.add_parser("circuit-create")
    create.add_argument("input", help="Circuit JSON file; numeric values use SI units")
    nmos_import = commands.add_parser("nmos-import", help="Validate and store an NMOS DC dataset")
    nmos_import.add_argument("input", help="nmos-dc-dataset/1 JSON; terminal currents use A/cm")
    inspect = commands.add_parser("inspect")
    inspect.add_argument("artifact")
    secants = commands.add_parser("nmos-secants", help="Calculate finite-span DC slopes from a stored 3x3 dataset")
    secants.add_argument("artifact")
    patch = commands.add_parser("circuit-patch")
    patch.add_argument("artifact")
    patch.add_argument("patch", help="JSON with expected_revision and upsert/remove/connect")
    netlist = commands.add_parser("netlist")
    netlist.add_argument("artifact")
    simulate = commands.add_parser("simulate")
    simulate.add_argument("netlist", help="Trusted local SPICE input")
    simulate.add_argument("--output", required=True, help="New run directory")
    simulate.add_argument("--executable", default="ngspice")
    simulate.add_argument("--timeout", type=float, default=30)
    simulate.add_argument("--result-file", default="measurements.dat")
    args = parser.parse_args(argv)
    try:
        if args.command == "capabilities":
            result = {k: asdict(v) for k, v in discover_capabilities().items()}
        elif args.command == "simulate":
            result = asdict(run_ngspice(Path(args.netlist), args.output,
                executable=args.executable, timeout_s=args.timeout, result_file=args.result_file))
            print(json.dumps(result, indent=2, allow_nan=False))
            return 0 if result["status"] == "completed" and result["measurements"] else 2
        elif args.command == "nmos-import":
            dataset = NMOSDataset.from_dict(_read(args.input))
            store = ArtifactStore(args.store)
            result = {
                "artifact": store.put("NMOSDCDataset", dataset.to_dict()),
                "fingerprint": dataset.fingerprint,
                "points": len(dataset.records),
                "train_points": len(dataset.train_ids),
                "holdout_points": len(dataset.holdout_ids),
                "temperature_k": dataset.temperature_k,
                "current_units": "A/cm",
                "scope": "Dataset contract validated; accuracy and physical validation require separate evidence.",
            }
        else:
            store = ArtifactStore(args.store)
            if args.command == "circuit-create":
                circuit = Circuit.from_dict(_read(args.input))
                result = {"artifact": store.put("CircuitDesign", circuit.to_dict()), "revision": circuit.revision}
            elif args.command == "inspect":
                result = store.get(args.artifact)
            elif args.command == "nmos-secants":
                artifact = store.get(args.artifact)
                if artifact["kind"] != "NMOSDCDataset":
                    raise ValidationError("expected an NMOSDCDataset artifact")
                dataset = NMOSDataset.from_dict(artifact["payload"])
                result = {
                    "artifact": args.artifact,
                    "dataset_fingerprint": dataset.fingerprint,
                    "secants": dc_secants(dataset),
                    "scope": "Finite-span DC calculations; mesh and derivative step-size accuracy require separate evidence.",
                }
            else:
                artifact = store.get(args.artifact)
                if artifact["kind"] != "CircuitDesign":
                    raise ValidationError("expected a CircuitDesign artifact")
                circuit = Circuit.from_dict(artifact["payload"])
                if args.command == "netlist":
                    print(circuit.export_spice(), end="")
                    return 0
                circuit = circuit.patch(CircuitPatch(**_read(args.patch)))
                result = {"artifact": store.put("CircuitDesign", circuit.to_dict(), [args.artifact]), "revision": circuit.revision}
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, RevisionConflict) as exc:
        print(json.dumps({"status": "failed", "message": str(exc)}), file=sys.stderr)
        return 2
