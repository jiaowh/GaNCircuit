"""Compare nine NMOS DC points and six finite-span secants on two meshes."""
import argparse
import json
import math
from pathlib import Path

try:
    from .nmos_evidence import ROOT, digest, load_evidence, read_json
except ImportError:
    from nmos_evidence import ROOT, digest, load_evidence, read_json
from circuit_tools.nmos_metrics import dc_secants

POLICY = ROOT / "devices/nmos-grid-verification-policy.json"


def comparison(a, b, relative, absolute):
    scale = max(abs(a), abs(b))
    delta = abs(b - a)
    if not all(math.isfinite(value) for value in (a, b, delta, scale)):
        raise ValueError("comparison arithmetic must remain finite")
    return {"first": a, "second": b, "absolute_delta": delta,
            "comparison_scale": scale, "relative_delta": delta / scale if scale else 0.,
            "absolute_floor_dominated": absolute >= relative * scale,
            "allowed_delta": absolute + relative * scale,
            "pass": delta <= absolute + relative * scale}


def compare_reports(first, second, *, qualification_path=None):
    try:
        policy = read_json(POLICY)
        if (policy.get("current_tolerance") != {"relative": .01, "absolute_A_per_cm": 1e-10}
                or policy.get("secant_tolerance") != {"relative": .01, "absolute_S_per_cm": 1e-8}
                or policy.get("mesh_levels") != [2, 3]
                or policy.get("vgs_v") != [.45, .5, .55] or policy.get("vds_v") != [.45, .5, .55]):
            raise ValueError("frozen verification policy changed")
        a, da = load_evidence(first, qualification_path=qualification_path)
        b, db = load_evidence(second, qualification_path=qualification_path)
        if [a["mesh_level"], b["mesh_level"]] != policy["mesh_levels"]:
            raise ValueError("reports must use coarse/fine levels 2 and 3 in order")
        if a["experiment"] != b["experiment"]:
            raise ValueError("experiments differ")
        for key in ("device_revision", "physics_sha256", "runtime", "qualification_sha256", "experiment_sha256", "runner_sha256"):
            if not a["provenance"].get(key) or a["provenance"][key] != b["provenance"].get(key):
                raise ValueError(f"provenance identity differs: {key}")
        if a["provenance"]["mesh_sha256"] == b["provenance"]["mesh_sha256"]:
            raise ValueError("mesh identities must differ")
        planned = [{"id": f"g{g}_d{d}", "vgs_v": gate, "vds_v": drain}
                   for g, gate in enumerate(policy["vgs_v"]) for d, drain in enumerate(policy["vds_v"])]
        if a["experiment"]["points"] != planned:
            raise ValueError("bias grid differs from frozen policy")
        currents = []
        for x, y in zip(da.records, db.records):
            for terminal in ("gate", "drain", "source", "body"):
                currents.append({"id": x["id"], "terminal": terminal, "units": "A/cm",
                    **comparison(x["currents_a_per_cm"][terminal], y["currents_a_per_cm"][terminal], .01, 1e-10)})
        sa, sb = dc_secants(da), dc_secants(db)
        slopes = [{"name": name, "units": "S/cm", "first_endpoints": sa[name], "second_endpoints": sb[name],
                   **comparison(sa[name]["value"], sb[name]["value"], .01, 1e-8)} for name in sorted(sa)]
        return {"outcome": "pass" if all(r["pass"] for r in currents + slopes) else "fail",
                "policy_sha256": digest(POLICY), "mesh_levels": [2, 3],
                "current_tolerances": policy["current_tolerance"], "slope_tolerances": policy["secant_tolerance"],
                "dataset_fingerprints": [da.fingerprint, db.fingerprint], "currents": currents, "slopes": slopes,
                "claim_boundary": "Mesh agreement at nine sampled biases and six finite-span secants only; derivative step-size, continuous-domain, model, circuit and physical-device accuracy remain separate gates."}
    except (OSError, KeyError, TypeError, ValueError, IndexError, AttributeError) as exc:
        return {"outcome": "unresolved", "reason": str(exc)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("first", type=Path)
    parser.add_argument("second", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = {"schema": "nmos-characterization-comparison/1", **compare_reports(args.first, args.second)}
    result["inputs"] = [{"path": str(p), "sha256": digest(p) if p.is_file() else None} for p in (args.first, args.second)]
    result["implementation"] = {str(p.relative_to(ROOT)): digest(p) for p in
        (Path(__file__).resolve(), ROOT / "scripts/nmos_evidence.py", ROOT / "src/circuit_tools/nmos_data.py", ROOT / "src/circuit_tools/nmos_metrics.py")}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"outcome": result["outcome"], "report": str(args.out), "reason": result.get("reason")}))
    return 0 if result["outcome"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
