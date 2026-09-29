"""Verify retained NMOS characterization receipts before numerical comparison."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from circuit_tools.nmos_data import NMOSDataset
from circuit_tools.nmos_metrics import dc_secants

QUALIFICATION = ROOT / "results/device-reference/planar-mos-openblas-qualification.json"
REQUIRED_FILES = {"dataset.json", "experiment.json", "gmsh_mos2d.msh", "points.json",
                  "runner-source.py", "solve-info.json", "stderr.log", "stdout.log", "worker.py"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def local_path(value):
    if not isinstance(value, str) or not value:
        raise ValueError("artifact path must be a nonempty string")
    path = (ROOT / value).resolve()
    path.relative_to(ROOT)
    return path


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_evidence(source, *, qualification_path=None):
    """Return a validated (report, dataset); this does not qualify accuracy.

    A report is bound to the retained endpoint qualification. NMOSDataset
    checks convergence flags, finite currents, and relative conservation.
    This loader additionally checks the worker receipts and declared biases.
    """
    report = read_json(source) if isinstance(source, (str, Path)) else source
    if not isinstance(report, dict) or report.get("schema") != "nmos-characterization-run/1":
        raise ValueError("invalid characterization report schema")
    execution = report.get("execution", {})
    if (report.get("outcome") != "pass" or execution.get("status") != "completed"
            or type(execution.get("returncode")) is not int or execution["returncode"] != 0
            or report.get("observed_points") != 9 or report.get("missing_point_ids") != []):
        raise ValueError("characterization execution is incomplete")
    dataset_path = local_path(report.get("dataset_path"))
    work = dataset_path.parent
    if dataset_path.name != "dataset.json":
        raise ValueError("unexpected dataset filename")
    artifacts = report.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("artifact receipts missing")
    resolved = {local_path(path): expected for path, expected in artifacts.items()}
    if not {work / name for name in REQUIRED_FILES}.issubset(resolved):
        raise ValueError("required worker artifact receipt missing")
    for path, expected in resolved.items():
        if not isinstance(expected, str) or digest(path) != expected:
            raise ValueError(f"artifact hash mismatch: {path.name}")
    if digest(dataset_path) != report.get("dataset_sha256"):
        raise ValueError("dataset hash mismatch")
    dataset = NMOSDataset.from_dict(read_json(dataset_path))
    if dataset.fingerprint != report.get("dataset_fingerprint"):
        raise ValueError("dataset fingerprint mismatch")
    provenance = report.get("provenance", {})
    if dataset.to_dict()["provenance"] != provenance:
        raise ValueError("dataset provenance differs from report")
    experiment = report.get("experiment", {})
    if read_json(work / "experiment.json") != experiment:
        raise ValueError("experiment artifact differs from report")
    if canonical_hash(experiment) != provenance.get("experiment_sha256"):
        raise ValueError("experiment identity mismatch")
    if digest(work / "runner-source.py") != provenance.get("runner_sha256"):
        raise ValueError("runner identity mismatch")
    if digest(work / "gmsh_mos2d.msh") != provenance.get("mesh_sha256"):
        raise ValueError("mesh identity mismatch")
    if (experiment.get("schema") != "nmos-dc-experiment/1" or experiment.get("temperature_k") != 300.
            or experiment.get("body_source_bias_v") != 0. or experiment.get("retries") != 0
            or experiment.get("split_policy") != "hold out the complete central gate-bias slice before fitting"):
        raise ValueError("experiment metadata is unsupported")
    planned = experiment.get("points", [])
    observed = [{"id": r["id"], "vgs_v": r["vgs_v"], "vds_v": r["vds_v"]} for r in dataset.records]
    if planned != observed or len(observed) != 9:
        raise ValueError("dataset biases/order differ from experiment")
    if (sorted(dataset.train_ids) != sorted(experiment.get("train_ids", []))
            or sorted(dataset.holdout_ids) != sorted(experiment.get("holdout_ids", []))):
        raise ValueError("dataset split differs from experiment")
    if len(dataset.holdout_ids) != 3 or any(r["vgs_v"] != .5 for r in dataset.records if r["id"] in dataset.holdout_ids):
        raise ValueError("holdout must be the complete central gate slice")
    if read_json(work / "points.json") != dataset.to_dict()["records"]:
        raise ValueError("raw worker points differ from dataset")
    solves = read_json(work / "solve-info.json")
    if not isinstance(solves, list) or len(solves) < 9 or any(not isinstance(s, dict) or s.get("converged") is not True for s in solves):
        raise ValueError("missing or nonconverged solver receipts")
    dc_secants(dataset)

    qualification_path = qualification_path or QUALIFICATION
    qualification = read_json(qualification_path)
    if digest(qualification_path) != provenance.get("qualification_sha256"):
        raise ValueError("endpoint qualification identity mismatch")
    if qualification.get("outcome") != "pass" or qualification.get("provenance", {}).get("source_unchanged") is not True:
        raise ValueError("endpoint qualification is not accepted")
    level = report.get("mesh_level")
    pair = qualification["mesh_comparisons"][-1]
    if type(level) is not int or pair.get("outcome") != "pass" or level not in pair.get("levels", []):
        raise ValueError("mesh is outside the accepted endpoint pair")
    case = qualification["cases"][level]
    if (case.get("status") != "completed" or case.get("solver_converged") is not True
            or case.get("mesh_sha256") != provenance.get("mesh_sha256")):
        raise ValueError("mesh differs from the qualified source case")
    qp = qualification["provenance"]
    revision = canonical_hash({"base_mesh": qp["source_mesh_sha256"], "construction": qp["construction_sha256"]})
    if provenance.get("device_revision") != revision:
        raise ValueError("device revision differs from qualification")
    backend = qualification["backend"]
    if provenance.get("runtime") != backend or provenance.get("physics_sha256") != backend["imported_physics_sha256"]:
        raise ValueError("runtime/physics differ from qualification")
    return report, dataset
