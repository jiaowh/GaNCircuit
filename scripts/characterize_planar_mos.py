"""Collect a small, pre-split NMOS DC grid using an endpoint-qualified mesh pair.

The grid is exploratory characterization: the prior mesh check covers only
the centre bias. Full-domain mesh/slope verification is a later acceptance gate.
"""
import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
try:
    from .qualify_planar_mos import UP, SRC, PIN, digest, head
except ImportError:
    from qualify_planar_mos import UP, SRC, PIN, digest, head


WORKER = r'''import json, math, runpy
from pathlib import Path
import devsim as ds

manifest = json.loads(Path("experiment.json").read_text())
solves = []
original = ds.solve
def checked_solve(*args, **kwargs):
    kwargs["info"] = True
    result = original(*args, **kwargs)
    solves.append(result)
    Path("solve-info.json").write_text(json.dumps(solves, indent=2))
    if not result.get("converged", False):
        raise ds.error("nonconverged solve; no data accepted")
    return result
ds.solve = checked_solve
# Optional field exports do not affect equations or solutions. This fixture
# retains solver diagnostics and terminal data; record omitted export requests.
ds.write_devices = lambda *args, **kwargs: print("OMITTED_FIELD_EXPORT", kwargs)
runpy.run_path(manifest["reference_script"], run_name="__main__")
records = []
for point in manifest["points"]:
    ds.set_parameter(device="mos2d", name="gate_bias", value=point["vgs_v"])
    ds.set_parameter(device="mos2d", name="drain_bias", value=point["vds_v"])
    ds.solve(type="dc", absolute_error=1e30, relative_error=1e-10, maximum_iterations=100)
    for contact, expected in (("gate",point["vgs_v"]),("drain",point["vds_v"]),("source",0.0),("body",0.0)):
        if ds.get_parameter(device="mos2d",name=contact+"_bias") != expected:
            raise ValueError("terminal bias differs from the experiment")
    currents = {}
    for contact in ("gate","drain","source","body"):
        currents[contact] = sum(ds.get_contact_current(device="mos2d", contact=contact, equation=equation)
                                for equation in ("ElectronContinuityEquation","HoleContinuityEquation"))
    if not all(math.isfinite(value) for value in currents.values()):
        raise ValueError("nonfinite terminal current")
    records.append(dict(point, currents_a_per_cm=currents, solver_converged=True))
    Path("points.json").write_text(json.dumps(records, indent=2, allow_nan=False))
    print("CHARACTERIZED", point["id"], flush=True)
'''


def experiment(half_span=.05):
    if isinstance(half_span, bool) or not isinstance(half_span, (int, float)) or not math.isfinite(half_span) or not 0 < half_span <= .05:
        raise ValueError("half-span must be positive, finite and at most 0.05 V")
    biases = (.5-half_span, .5, .5+half_span)
    if len(set(biases)) != 3:
        raise ValueError("half-span is too small to resolve three distinct biases")
    points = [{"id":f"g{g}_d{d}", "vgs_v":gate, "vds_v":drain}
              for g,gate in enumerate(biases) for d,drain in enumerate(biases)]
    return {"schema":"nmos-dc-experiment/1", "temperature_k":300.0,
            "reference_script":str(SRC/"gmsh_mos2d.py"), "points":points,
            "train_ids":[p["id"] for p in points if p["vgs_v"] != .5],
            "holdout_ids":[p["id"] for p in points if p["vgs_v"] == .5],
            "split_policy":"hold out the complete central gate-bias slice before fitting",
            "body_source_bias_v":0.0, "retries":0}


def select_mesh(report, level):
    if report.get("outcome") != "pass" or report.get("provenance", {}).get("source_unchanged") is not True:
        raise ValueError("requires a passed endpoint qualification with unchanged sources")
    pairs = report.get("mesh_comparisons", [])
    if not pairs or pairs[-1].get("outcome") != "pass" or level not in pairs[-1].get("levels", []):
        raise ValueError("mesh level must belong to the accepted final endpoint pair")
    row = report["cases"][level]
    if row.get("status") != "completed" or not row.get("solver_converged"):
        raise ValueError("mesh source case is incomplete")
    path = (ROOT/row["stdout_log"]).resolve().parent/"gmsh_mos2d.msh"
    path.relative_to(ROOT)
    if digest(path) != row.get("mesh_sha256"):
        raise ValueError("retained mesh hash mismatch")
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualification", type=Path, default=ROOT/"results/device-reference/planar-mos-openblas-qualification.json")
    parser.add_argument("--mesh-level", type=int, choices=(2,3), default=2)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--half-span", type=float, choices=(.05,.025,.0125), default=.05,
                        help="Bias offsets about 0.5 V; smaller grids support derivative step-size checks")
    parser.add_argument("--out", type=Path, default=ROOT/"results/device-reference/nmos-dc-characterization.json")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("timeout must be positive")
    args.out = args.out.resolve()
    manifest = experiment(args.half_span)
    work = args.out.parent/"nmos-characterization-work"/uuid.uuid4().hex
    work.mkdir(parents=True)
    report = {"schema":"nmos-characterization-run/1", "outcome":"unresolved",
              "scope":"Exploratory 300 K DC grid; only the centre bias has prior mesh evidence. No model export or full-domain accuracy claim.",
              "experiment":manifest, "mesh_level":args.mesh_level}
    try:
        source = json.loads(args.qualification.read_text())
        mesh = select_mesh(source, args.mesh_level)
        if head(UP) != PIN or subprocess.run(["git","-C",str(UP),"diff","--quiet","HEAD"]).returncode:
            raise ValueError("pinned upstream source is missing or dirty")
        import devsim.python_packages.simple_physics as physics
        backend = source["backend"]
        if importlib.metadata.version("devsim") != backend["version"] or digest(Path(physics.__file__)) != backend["imported_physics_sha256"]:
            raise ValueError("runtime physics differs from endpoint qualification")
        libraries = [{"path":p,"sha256":digest(Path(p))} for p in os.environ.get("DEVSIM_MATH_LIBS", "").split(os.pathsep) if p]
        if libraries != backend.get("math_libraries"):
            raise ValueError("math runtime differs from endpoint qualification")
        if os.environ.get("OPENBLAS_NUM_THREADS") != backend.get("openblas_num_threads"):
            raise ValueError("math thread configuration differs from endpoint qualification")
        provenance = {"device_revision":hashlib.sha256(json.dumps({
            "base_mesh":source["provenance"]["source_mesh_sha256"],
            "construction":source["provenance"]["construction_sha256"]}, sort_keys=True).encode()).hexdigest(),
            "mesh_sha256":digest(mesh), "physics_sha256":digest(Path(physics.__file__)),
            "qualification_sha256":digest(args.qualification), "runtime":backend,
            "experiment_sha256":hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
            "runner_sha256":digest(Path(__file__)), "mesh_domain_status":"endpoint_only"}
        report["provenance"] = provenance
        shutil.copy2(mesh,work/"gmsh_mos2d.msh")
        shutil.copy2(Path(__file__),work/"runner-source.py")
        (work/"experiment.json").write_text(json.dumps(manifest,indent=2))
        (work/"worker.py").write_text(WORKER)
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join([str(SRC),str(UP),env.get("PYTHONPATH", "")])
        started = time.monotonic()
        try:
            process = subprocess.run([sys.executable,str(work/"worker.py")], cwd=work, env=env,
                                     capture_output=True,text=True,timeout=args.timeout)
            stdout,stderr,returncode = process.stdout,process.stderr,process.returncode
            status = "completed" if returncode == 0 else "failed"
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout,bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr,bytes) else (exc.stderr or "")
            status,returncode = "timeout",None
        (work/"stdout.log").write_text(stdout)
        (work/"stderr.log").write_text(stderr)
        report["execution"] = {"status":status,"returncode":returncode,"elapsed_s":time.monotonic()-started,"timeout_s":args.timeout}
        records = json.loads((work/"points.json").read_text()) if (work/"points.json").is_file() else []
        report["observed_points"] = len(records)
        report["missing_point_ids"] = sorted(set(p["id"] for p in manifest["points"])-set(p["id"] for p in records))
        if status == "completed" and not report["missing_point_ids"]:
            from circuit_tools.nmos_data import NMOSDataset
            dataset = NMOSDataset.from_records(records,provenance,manifest["train_ids"],manifest["holdout_ids"])
            (work/"dataset.json").write_text(json.dumps(dataset.to_dict(),indent=2,allow_nan=False))
            report.update(outcome="pass",dataset_sha256=digest(work/"dataset.json"),dataset_fingerprint=dataset.fingerprint,
                          dataset_path=str((work/"dataset.json").relative_to(ROOT)),domain_accuracy="unresolved")
    except (OSError,ValueError,KeyError,ImportError) as exc:
        report["reason"] = str(exc)
    report["artifacts"] = {str(p.relative_to(ROOT)):digest(p) for p in work.iterdir() if p.is_file()}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"outcome":report["outcome"],"report":str(args.out),"observed_points":report.get("observed_points"),"reason":report.get("reason")},indent=2))
    return 0 if report["outcome"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
