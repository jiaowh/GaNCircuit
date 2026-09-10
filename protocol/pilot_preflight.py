"""Read-only physical pilot readiness check. Does not substitute synthetic labels."""
import json
import shutil
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
m = json.loads((ROOT / "protocol" / "experiment-manifest.json").read_text())
inputs = ROOT / m["pilot"]["input_root"]
missing = [str(inputs / name) for name in m["pilot"]["required_inputs"] if not (inputs / name).is_file()]
tools = {name: shutil.which(name) for name in ("ngspice", "magic", "netgen")}
pdk = os.environ.get("PDK_ROOT")
status = {
    "status": "BLOCKED" if missing or not all(tools.values()) or not pdk or not Path(pdk).is_dir() else "INPUTS_PRESENT_REPRODUCTION_REQUIRED",
    "tools": tools,
    "PDK_ROOT": pdk,
    "missing_inputs": missing,
    "circuit_simulations_run": 0,
    "note": "Preflight checks existence only. Model patch, DRC/LVS, layout reproducibility, simulator adapter and training harness must pass the pilot launch checklist before data collection."
}
out = ROOT / "results" / "pilot"
out.mkdir(parents=True, exist_ok=True)
(out / "preflight.json").write_text(json.dumps(status, indent=2)+"\n")
print(json.dumps(status, indent=2))
raise SystemExit(2 if status["status"] == "BLOCKED" else 0)
