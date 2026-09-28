"""Check central NMOS secants over three bias steps on one fixed mesh."""
import argparse
import json
import math
from pathlib import Path

try:
    from .nmos_evidence import ROOT, digest, load_evidence, local_path, read_json
    from .compare_nmos_characterization import POLICY, comparison
except ImportError:
    from nmos_evidence import ROOT, digest, load_evidence, local_path, read_json
    from compare_nmos_characterization import POLICY, comparison
from circuit_tools.nmos_metrics import dc_secants


def compare_steps(sources, *, qualification_path=None):
    try:
        policy = read_json(POLICY)["planned_step_size_check"]
        if policy["half_spans_v"] != [.05, .025, .0125] or policy["relative"] != .01 or policy["absolute_S_per_cm"] != 1e-8:
            raise ValueError("frozen step-size policy changed")
        if len(sources) != 3:
            raise ValueError("three predeclared bias-step reports are required")
        loaded = [load_evidence(p, qualification_path=qualification_path) for p in sources]
        first = loaded[0][0]
        first_manifest = {k: v for k, v in first["experiment"].items() if k != "points"}
        first_worker = digest(local_path(first["dataset_path"]).parent / "worker.py")
        metrics = []
        for (report, dataset), half_span in zip(loaded, policy["half_spans_v"]):
            for key in ("device_revision", "mesh_sha256", "physics_sha256", "runtime", "qualification_sha256"):
                if not first["provenance"].get(key) or first["provenance"][key] != report["provenance"].get(key):
                    raise ValueError(f"fixed-mesh identity differs: {key}")
            if report["mesh_level"] != first["mesh_level"]:
                raise ValueError("mesh levels differ")
            if {k: v for k, v in report["experiment"].items() if k != "points"} != first_manifest:
                raise ValueError("non-bias experiment settings differ")
            if digest(local_path(report["dataset_path"]).parent / "worker.py") != first_worker:
                raise ValueError("worker implementations differ")
            expected = [{"id": f"g{g}_d{d}", "vgs_v": gate, "vds_v": drain}
                        for g, gate in enumerate((.5-half_span, .5, .5+half_span))
                        for d, drain in enumerate((.5-half_span, .5, .5+half_span))]
            if report["experiment"]["points"] != expected:
                raise ValueError("bias steps differ from declared schedule")
            secants = dc_secants(dataset)
            gm, gds = secants["gm_vds_0.5"]["value"], secants["gds_vgs_0.5"]["value"]
            ratio = gm / gds if gds != 0. else None
            metrics.append({"half_span_v": half_span, "dataset_fingerprint": dataset.fingerprint,
                "gm": secants["gm_vds_0.5"], "gds": secants["gds_vgs_0.5"],
                "gm_over_gds": ratio if ratio is not None and math.isfinite(ratio) else None})
        pairs = []
        for i in range(2):
            for name in ("gm", "gds"):
                pairs.append({"metric": name, "half_spans_v": policy["half_spans_v"][i:i+2], "units": "S/cm",
                    **comparison(metrics[i][name]["value"], metrics[i+1][name]["value"], .01, 1e-8)})
        return {"outcome": "pass" if all(p["pass"] for p in pairs) else "fail",
            "mesh_level": first["mesh_level"], "policy_sha256": digest(POLICY),
            "tolerances": {"relative": .01, "absolute_S_per_cm": 1e-8},
            "metrics": metrics, "comparisons": pairs,
            "claim_boundary": "Central gm/gds secant step-size agreement on one fixed mesh only. Smaller-stencil mesh accuracy, continuous-domain, model, circuit and physical-device validation remain unresolved."}
    except (OSError, KeyError, TypeError, ValueError, IndexError, AttributeError) as exc:
        return {"outcome": "unresolved", "reason": str(exc)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs=3, type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = {"schema": "nmos-step-size-comparison/1", **compare_steps(args.reports)}
    result["inputs"] = [{"path": str(p), "sha256": digest(p) if p.is_file() else None} for p in args.reports]
    result["implementation"] = {str(p.relative_to(ROOT)): digest(p) for p in
        (Path(__file__).resolve(), ROOT / "scripts/nmos_evidence.py", ROOT / "scripts/compare_nmos_characterization.py",
         ROOT / "src/circuit_tools/nmos_data.py", ROOT / "src/circuit_tools/nmos_metrics.py")}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"outcome": result["outcome"], "report": str(args.out), "reason": result.get("reason")}))
    return 0 if result["outcome"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
