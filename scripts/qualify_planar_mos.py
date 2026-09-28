#!/usr/bin/env python3
"""Bounded planar MOS mesh/current qualification using the pinned DEVSIM example."""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; UP=ROOT/"devices/devsim-upstream"; SRC=UP/"examples/mobility"
MESH=SRC/"gmsh_mos2d.msh"; PIN="43b41ca845184c47e22b72d144db7e7db8509377"
BIAS={"gate":.5,"drain":.5,"source":0.0,"body":0.0}

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def head(p):
    try: return subprocess.check_output(["git","-C",str(p),"rev-parse","HEAD"],text=True).strip()
    except (OSError,subprocess.CalledProcessError): return None

def mesh_data(p):
    ls=p.read_text().splitlines(); nodes={}; elems=[]; i=0
    while i<len(ls):
        if ls[i]=="$Nodes":
            n=int(ls[i+1])
            for row in ls[i+2:i+2+n]:
                f=row.split(); nodes[int(f[0])]=tuple(map(float,f[1:4]))
            i+=n+2
        elif ls[i]=="$Elements":
            n=int(ls[i+1])
            for row in ls[i+2:i+2+n]:
                f=row.split(); typ,nt=int(f[1]),int(f[2]); elems.append((typ,tuple(map(int,f[3:3+nt])),tuple(map(int,f[3+nt:]))))
            i+=n+2
        i+=1
    return ls,nodes,elems

def subdivide(src,dst):
    ls,nodes,elems=mesh_data(src); mids={}; out=[]
    next_id = max(nodes) + 1
    def mid(a,b):
        nonlocal next_id
        k=tuple(sorted((a,b)))
        if k not in mids:
            x=nodes[a]; y=nodes[b]; mids[k]=next_id
            next_id += 1
            nodes[mids[k]]=tuple((x[j]+y[j])/2 for j in range(3))
        return mids[k]
    for typ,tags,ns in elems:
        if typ==1:
            m=mid(*ns); out += [(1,tags,(ns[0],m)),(1,tags,(m,ns[1]))]
        elif typ==2:
            a,b,c=ns; ab,bc,ca=mid(a,b),mid(b,c),mid(c,a)
            out += [(2,tags,(a,ab,ca)),(2,tags,(ab,b,bc)),(2,tags,(ca,bc,c)),(2,tags,(ab,bc,ca))]
        else: raise ValueError(f"unsupported mesh element type: {typ}")
    p0,p1=ls.index("$PhysicalNames"),ls.index("$EndPhysicalNames")
    text=["$MeshFormat","2.1 0 8","$EndMeshFormat"]+ls[p0:p1+1]+["$Nodes",str(len(nodes))]
    text += [f"{k} {v[0]:.17g} {v[1]:.17g} {v[2]:.17g}" for k,v in sorted(nodes.items())]
    text += ["$EndNodes","$Elements",str(len(out))]
    text += [" ".join(map(str,(j,t,len(tags),*tags,*ns))) for j,(t,tags,ns) in enumerate(out,1)]
    text += ["$EndElements",""]; dst.write_text("\n".join(text))
    return {"nodes":len(nodes),"elements":len(out),"line_elements":sum(t==1 for t,_,_ in out),"triangle_elements":sum(t==2 for t,_,_ in out),
            "source_sha256":digest(src),"refined_sha256":digest(dst)}

HARNESS=r'''import json, runpy,devsim as ds
records=[]; original=ds.solve
def wrapped(*a,**kw):
    kw["info"]=True; result=original(*a,**kw); records.append(result)
    if not result.get("converged",False): raise ds.error("nonconverged")
    return result
ds.solve=wrapped
runpy.run_path(r"__SCRIPT__",run_name="__main__")
with open("solve-info.json", "w") as stream:
    json.dump(records, stream, indent=2)
print("QUALIFY_SOLVES",len(records)); print("QUALIFY_ALL_CONVERGED",int(all(r.get("converged",False) for r in records)))
for c in ds.get_contact_list(device="mos2d"): print("QUALIFY_CONTACT",c,ds.get_parameter(device="mos2d",name=c+"_bias"))
for r in ("gate","bulk","oxide"): print("QUALIFY_NODES",r,len(ds.get_node_model_values(device="mos2d",region=r,name="x")))
'''

def run_case(mesh,work,timeout):
    work.mkdir(parents=True); shutil.copy2(mesh,work/"gmsh_mos2d.msh")
    h=work/"harness.py"; h.write_text(HARNESS.replace("__SCRIPT__",str(SRC/"gmsh_mos2d.py")))
    env=os.environ.copy(); env["PYTHONPATH"]=os.pathsep.join([str(SRC),str(UP),env.get("PYTHONPATH","")]).rstrip(os.pathsep)
    started = time.monotonic()
    try:
        p=subprocess.run([sys.executable,str(h)],cwd=work,env=env,text=True,capture_output=True,timeout=timeout)
        (work/"stdout.log").write_text(p.stdout); (work/"stderr.log").write_text(p.stderr)
        contacts={}; nodes={}; rows={}; invalid_data = False
        for line in p.stdout.splitlines():
            f=line.split()
            if len(f)==3 and f[0]=="QUALIFY_CONTACT": contacts[f[1]]=float(f[2])
            elif len(f)==3 and f[0]=="QUALIFY_NODES": nodes[f[1]]=int(f[2])
            elif len(f)==5 and f[0] in BIAS:
                try:
                    values = [float(x) for x in f[1:]]
                    if all(math.isfinite(x) for x in values):
                        rows[f[0]] = values
                    else:
                        invalid_data = True
                except ValueError: pass
        totals={k:v[-1] for k,v in rows.items()}
        imb=abs(sum(totals.values()))/max(sum(abs(v) for v in totals.values()),1e-30) if set(totals)==set(BIAS) else None
        return {"status":"completed" if p.returncode==0 and not invalid_data else "failed","returncode":p.returncode,"solver_converged":"QUALIFY_ALL_CONVERGED 1" in p.stdout,
                "solve_count":int(next((x.split()[1] for x in p.stdout.splitlines() if x.startswith("QUALIFY_SOLVES ")),0)),
                "contacts":contacts,"contact_rows":rows,"nodes":nodes,"relative_current_imbalance":imb,
                "elapsed_s":time.monotonic()-started,
                "mesh_sha256":digest(mesh), "harness_sha256":digest(h),
                "artifacts":{p.name:digest(p) for p in work.iterdir() if p.is_file()},
                "stdout_log":str((work/"stdout.log").relative_to(ROOT)),"stderr_log":str((work/"stderr.log").relative_to(ROOT))}
    except subprocess.TimeoutExpired as e:
        for name, data in (("stdout.log", e.stdout), ("stderr.log", e.stderr)):
            (work/name).write_text(data.decode(errors="replace") if isinstance(data, bytes) else (data or ""))
        return {"status":"timeout","reason":f"timeout after {timeout}s","stdout_log":str((work/"stdout.log").relative_to(ROOT)),"stderr_log":str((work/"stderr.log").relative_to(ROOT))}

def qualify(cases,tol,rel_mesh=1e-2,abs_mesh=1e-10):
    if len(cases)!=2 or any(c.get("status")!="completed" or not c.get("solver_converged") for c in cases): return "unresolved"
    for c in cases:
        if c.get("contacts")!=BIAS or set(c.get("contact_rows",{}))!=set(BIAS): return "unresolved"
        for name, row in c["contact_rows"].items():
            if len(row) != 4 or not all(math.isfinite(v) for v in row) or row[0] != BIAS[name]:
                return "unresolved"
        x=c.get("relative_current_imbalance")
        if x is None or not math.isfinite(x) or x>tol: return "unresolved"
    a,b=cases
    if any(b["nodes"].get(r,0)<=a["nodes"].get(r,0) for r in ("gate","bulk","oxide")): return "unresolved"
    for name in BIAS:
        av=a["contact_rows"][name][-1]; bv=b["contact_rows"][name][-1]
        if not all(math.isfinite(x) for x in (av,bv)): return "unresolved"
        if abs(bv-av)>abs_mesh+rel_mesh*max(abs(av),abs(bv),abs_mesh): return "unresolved"
    return "pass"

def compare_currents(pair, relative, absolute):
    comparisons = []
    if len(pair) != 2 or any(c.get("status") != "completed" for c in pair):
        return comparisons
    for name in BIAS:
        rows = [c.get("contact_rows", {}).get(name, []) for c in pair]
        if any(len(row) != 4 or not all(math.isfinite(x) for x in row) for row in rows):
            continue
        av, bv = [row[-1] for row in rows]
        delta = abs(bv-av)
        scale = max(abs(av), abs(bv), absolute)
        comparisons.append({"contact": name, "absolute_delta_A_per_cm": delta,
                            "relative_delta": delta/scale, "pass": delta <= absolute+relative*scale})
    return comparisons


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--out", type=Path, default=ROOT/"results/device-reference/planar-mos-qualification.json")
    ap.add_argument("--timeout", type=int, default=240)
    ap.add_argument("--refinements", type=int, choices=(1, 2, 3), default=1)
    ap.add_argument("--mesh-policy", choices=("uniform", "surface-bands"), default="uniform")
    ap.add_argument("--conservation-tolerance", type=float, default=1e-4)
    ap.add_argument("--mesh-relative-tolerance", type=float, default=1e-2)
    ap.add_argument("--mesh-absolute-tolerance", type=float, default=1e-10)
    args = ap.parse_args()
    args.out = args.out.resolve()
    implementation_files = [Path(__file__), Path(__file__).with_name("mesh_invariants.py"),
                            Path(__file__).with_name("refine_planar_mesh.py"),
                            Path(__file__).with_name("mesh_delaunay.py")]
    implementation_hashes = {p.name: digest(p) for p in implementation_files}
    tolerances = (args.conservation_tolerance, args.mesh_relative_tolerance, args.mesh_absolute_tolerance)
    if args.timeout <= 0 or not all(math.isfinite(x) and x > 0 for x in tolerances):
        ap.error("timeout/tolerances must be positive finite")
    observed = head(UP)
    try:
        import devsim
        import devsim.python_packages.simple_physics as physics
        backend = {"available": True, "version": importlib.metadata.version("devsim"),
                   "python": sys.executable, "imported_physics": str(physics.__file__),
                   "imported_physics_sha256": digest(Path(physics.__file__)),
                   "math_libraries": [{"path": p, "sha256": digest(Path(p))}
                                      for p in os.environ.get("DEVSIM_MATH_LIBS", "").split(os.pathsep) if p],
                   "openblas_num_threads": os.environ.get("OPENBLAS_NUM_THREADS")}
    except Exception as exc:
        backend = {"available": False, "reason": repr(exc)}
    if observed != PIN:
        backend = {"available": False, "reason": f"source pin mismatch: {observed}"}
    elif subprocess.run(["git", "-C", str(UP), "diff", "--quiet", "HEAD"]).returncode:
        backend = {"available": False, "reason": "tracked upstream source differs from pinned commit"}
    cases, meshes, invariants, pairs = [], [], [], []
    if args.run and backend["available"]:
        from mesh_invariants import compare_invariants, invariants as mesh_summary
        root = args.out.parent/"planar-mos-qualification-work"/uuid.uuid4().hex
        root.mkdir(parents=True)
        snapshot = root/"implementation"
        snapshot.mkdir()
        for path in implementation_files:
            shutil.copy2(path, snapshot/path.name)
        meshes = [MESH]
        for level in range(1, args.refinements+1):
            target = root/f"mesh-{level}.msh"
            if args.mesh_policy == "uniform":
                generation = subdivide(meshes[-1], target)
            else:
                from refine_planar_mesh import refine
                generation = refine(meshes[-1], target)
            before, after = mesh_summary(meshes[-1]), mesh_summary(target)
            check = compare_invariants(before, after)
            check.update(baseline=before, refined=after, generation=generation)
            invariants.append(check)
            meshes.append(target)
        if all(check["pass"] for check in invariants):
            for level, mesh in enumerate(meshes):
                cases.append(run_case(mesh, root/f"level-{level}", args.timeout))
        else:
            cases = [{"status": "invalid_mesh", "reason": "geometry invariants changed"}]
    else:
        cases = [{"status": "available_not_run" if backend["available"] else "missing_backend",
                  "reason": "pass --run" if backend["available"] else backend["reason"]}]
    for level in range(len(cases)-1):
        pair = cases[level:level+2]
        pairs.append({"levels": [level, level+1], "outcome": qualify(pair, *tolerances),
                      "currents": compare_currents(pair, args.mesh_relative_tolerance, args.mesh_absolute_tolerance)})
    outcome = pairs[-1]["outcome"] if pairs else "unresolved"
    source_unchanged = implementation_hashes == {p.name: digest(p) for p in implementation_files}
    if not source_unchanged:
        outcome = "unresolved"
    report = {
        "schema": "device-reference-planar-mos-qualification/2", "outcome": outcome, "backend": backend,
        "provenance": {"commit": observed, "expected_commit": PIN, "source_mesh_sha256": digest(MESH),
                       "implementation_at_start": implementation_hashes, "source_unchanged": source_unchanged,
                       "evaluator_sha256": implementation_hashes[Path(__file__).name], "script_sha256": digest(SRC/"gmsh_mos2d.py"),
                       "construction_sha256": digest(SRC/"gmsh_mos2d_create.py"),
                       "invariant_checker_sha256": digest(Path(__file__).with_name("mesh_invariants.py")),
                       "local_refiner_sha256": digest(Path(__file__).with_name("refine_planar_mesh.py"))},
        "mesh_policy": {"refinements": args.refinements, "method": args.mesh_policy,
                        "invariants": invariants, "acceptance": "last adjacent pair; earlier comparisons retained"},
        "tolerances": {"conservation_relative_current": tolerances[0], "mesh_relative_current": tolerances[1],
                       "mesh_absolute_current_A_per_cm": tolerances[2]},
        "execution_limits": {"per_case_timeout_s": args.timeout},
        "selected_mesh_sha256": cases[-1].get("mesh_sha256") if outcome == "pass" else None,
        "current_definition": {"unit": "A/cm", "out_of_plane_width": "apply separately once",
                               "columns": ["bias_V", "electron_current_native", "hole_current_native", "total_current_native"]},
        "cases": cases, "mesh_comparisons": pairs,
        "claim_boundary": "Endpoint only at Vg=Vd=0.5 V, Vs=Vb=0 V, 300 K; no bias-domain, slope, or physical-device validation. Upstream oxide material label is Silicon; oxide equations are assigned by simple_physics."
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    print(json.dumps({"outcome": outcome, "report": str(args.out), "pairs": pairs}, indent=2))
    return 0 if outcome == "pass" else 2
if __name__=="__main__": raise SystemExit(main())
