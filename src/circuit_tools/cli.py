"""Small JSON CLI over the engineering library."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from .adapters import discover_capabilities, run_ngspice
from .core import ArtifactStore, Circuit, CircuitPatch, RevisionConflict, ValidationError


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="circuit-tools")
    parser.add_argument("--store", default="runs/store")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("capabilities")
    create = commands.add_parser("circuit-create")
    create.add_argument("input", help="Circuit JSON file; numeric values use SI units")
    inspect = commands.add_parser("inspect")
    inspect.add_argument("artifact")
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
        else:
            store = ArtifactStore(args.store)
            if args.command == "circuit-create":
                circuit = Circuit.from_dict(_read(args.input))
                result = {"artifact": store.put("CircuitDesign", circuit.to_dict()), "revision": circuit.revision}
            elif args.command == "inspect":
                result = store.get(args.artifact)
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
