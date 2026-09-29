"""Compare final currents across mesh policies without treating either as truth."""
import argparse
import hashlib
import json
import math
from pathlib import Path

try:
    from .qualify_planar_mos import BIAS, compare_currents
except ImportError:
    from qualify_planar_mos import BIAS, compare_currents


def compare(reference, candidate, *, reference_level=-1, candidate_level=-1,
            relative=1e-2, absolute=1e-10, same_mesh=False):
    for field in ("commit", "source_mesh_sha256", "script_sha256", "construction_sha256"):
        left = reference.get("provenance", {}).get(field)
        right = candidate.get("provenance", {}).get(field)
        if not left or left != right:
            return {"outcome": "unresolved", "reason": f"different or missing {field}"}
    for field in ("version", "imported_physics_sha256"):
        left = reference.get("backend", {}).get(field)
        if not left or left != candidate.get("backend", {}).get(field):
            return {"outcome": "unresolved", "reason": f"different or missing backend {field}"}
    pair = []
    for report, level in ((reference,reference_level), (candidate,candidate_level)):
        cases = report.get("cases", [])
        if not cases:
            return {"outcome": "unresolved", "reason": "missing final mesh run"}
        try:
            case = cases[level]
        except IndexError:
            return {"outcome": "unresolved", "reason": "requested mesh level is absent"}
        rows = case.get("contact_rows", {})
        if case.get("status") != "completed" or not case.get("solver_converged") or set(rows) != set(BIAS):
            return {"outcome": "unresolved", "reason": "incomplete final mesh evidence"}
        for name, row in rows.items():
            if len(row) != 4 or not all(math.isfinite(v) for v in row) or row[0] != BIAS[name]:
                return {"outcome": "unresolved", "reason": "invalid final contact data"}
        pair.append(case)
    if same_mesh and (not pair[0].get("mesh_sha256") or pair[0].get("mesh_sha256") != pair[1].get("mesh_sha256")):
        return {"outcome": "unresolved", "reason": "mesh hashes differ"}
    currents = compare_currents(pair, relative, absolute)
    return {"outcome": "pass" if len(currents) == 4 and all(c["pass"] for c in currents) else "fail",
            "currents": currents, "reference_mesh_outcome": reference.get("outcome"),
            "candidate_mesh_outcome": candidate.get("outcome"),
            "mesh_hashes": [case.get("mesh_sha256") for case in pair]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("reference", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--reference-level", type=int, default=-1)
    parser.add_argument("--candidate-level", type=int, default=-1)
    parser.add_argument("--relative-tolerance", type=float, default=1e-2)
    parser.add_argument("--absolute-tolerance", type=float, default=1e-10)
    parser.add_argument("--same-mesh", action="store_true")
    args = parser.parse_args()
    reports = [json.loads(path.read_text()) for path in (args.reference, args.candidate)]
    if not all(math.isfinite(v) and v > 0 for v in (args.relative_tolerance,args.absolute_tolerance)):
        parser.error("tolerances must be positive finite")
    result = compare(*reports, reference_level=args.reference_level, candidate_level=args.candidate_level,
                     relative=args.relative_tolerance, absolute=args.absolute_tolerance, same_mesh=args.same_mesh)
    result.update(schema="planar-mesh-policy-comparison/1",
                  scope="Cross-policy endpoint agreement only; neither report is independent physical ground truth",
                  levels=[args.reference_level,args.candidate_level], require_same_mesh=args.same_mesh,
                  tolerances={"relative_current": args.relative_tolerance, "absolute_current_A_per_cm": args.absolute_tolerance},
                  inputs=[{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                          for p in (args.reference,args.candidate)],
                  evaluator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
    print(json.dumps(result, indent=2))
    return 0 if result["outcome"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
