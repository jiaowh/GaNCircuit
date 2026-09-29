#!/usr/bin/env python3
"""Simulate the unmodified EPC2302 model for the datasheet curves not covered by the baseline.

Adds RDS(on) against VGS for 25-100 A at 25 C and 50 A at 125 C (Figs. 3-4),
CISS/CRSS against VDS (Fig. 5), reverse conduction at 25 and 125 C with
VGS = 0 V (Fig. 8), and normalized RDS(on) (50 A, 5 V) and VGS(th) (14 mA)
against temperature (Figs. 9-10). Library checks and numerical settings are
those of scripts/epc2302_baseline.py. Output: results/gan/epc2302-model-curves-extra.json;
comparison: scripts/compare_epc2302_curves.py.
"""
import hashlib
import json
import math
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from circuit_tools.ltspice import parse_raw, run_ltspice
import epc2302_baseline as bl

OUTPUT = ROOT / "results/gan/epc2302-model-curves-extra.json"
TEMPS = tuple(12.5 * k for k in range(13))  # 0 .. 150 C
DRAIN_CURRENTS_FIG3 = (25, 50, 75, 100)
S = bl.SUBCKT


def benches():
    b = {}
    # Nested sweep: for each VGS (outer), the drain current ramps from 0 A (inner), which gives
    # the solver continuation. Forcing 25-100 A directly failed Gmin and source stepping on the
    # first run. VGS stops at 2.9 V: the datasheet axis starts at 3 V.
    b["rds_vs_vgs_25C"] = bl.HEAD + f"""* RDS(on) against VGS: drain current ramped 0 -> {max(DRAIN_CURRENTS_FIG3)} A at each VGS, 25 C
Id 0 d 0
Vg g 0 5
X1 g d 0 {S}
.temp 25
.dc Id 0 {max(DRAIN_CURRENTS_FIG3)} 0.5 Vg 5 2.9 -0.01
.end
"""
    b["rds_vs_vgs_125C"] = bl.HEAD + f"""* RDS(on) against VGS: drain current ramped 0 -> 50 A at each VGS, 125 C
Id 0 d 0
Vg g 0 5
X1 g d 0 {S}
.temp 125
.dc Id 0 50 0.5 Vg 5 2.9 -0.01
.end
"""
    b["ciss_crss_curve_ac"] = bl.HEAD + f"""* CISS and CRSS against VDS: AC on gate, drain held at VDS (AC ground)
.param vds=50
Vg g 0 0 AC 1
Vd d 0 {{vds}}
X1 g d 0 {S}
.temp 25
.step param vds 0 100 0.5
.ac list {bl.AC_FREQ:g}
.end
"""
    for t in (25, 125):
        b[f"reverse_{t}C"] = bl.HEAD + f"""* Reverse conduction: VGS = 0 V, drain swept below the source
Vd d 0 0
Vg g 0 0
X1 g d 0 {S}
.temp {t}
.dc Vd 0 -5 -0.01
.end
"""
    for t in TEMPS:
        b[f"rds_on_{t:g}C"] = bl.HEAD + f"""* RDS(on) against temperature: VGS = 5 V, drain current swept to 50 A
Vg g 0 5
Id 0 d 0
X1 g d 0 {S}
.temp {t:g}
.dc Id 0 50 0.5
.end
"""
        b[f"vgs_th_{t:g}C"] = bl.HEAD + f"""* VGS(th) against temperature: drain tied to gate, sweep until ID = 14 mA
Vg g 0 0
X1 g g 0 {S}
.temp {t:g}
.dc Vg 0 3 1m
.end
"""
    return b


def main():
    lib, archive_sha = bl.library_path()
    lib_sha, _ = bl.verify_target_sources(lib)
    run_root = ROOT / "runs" / ("epc2302-curves-" + uuid.uuid4().hex)
    runs, raws = {}, {}
    for name, text in benches().items():
        text = text.replace("\n.end\n", f"\n.options reltol={bl.RELTOL:g}\n.end\n")
        r = run_ltspice(text, run_root / name, libraries=[lib], timeout_s=600)
        runs[name] = r
        if r.status == "completed":
            raws[name] = parse_raw(r.result_path)
    failed = {n: r.message for n, r in runs.items() if r.status != "completed"}
    curves = {}
    def rds_at(raw, i_d):
        """RDS(on) in mOhm at drain current i_d for every outer VGS step."""
        vgs, rds = [], []
        for k in range(raw.n_steps):
            s = raw.step(k)
            vgs.append(s["v(g)"][0])
            rds.append(bl.at(s["i(id)"], s["v(d)"], i_d) / i_d * 1e3)
        return {"vgs_V": vgs, "rds_mohm": rds}
    if "rds_vs_vgs_25C" in raws:
        curves["rds_vs_vgs_25C"] = {f"id_{i_d}A": rds_at(raws["rds_vs_vgs_25C"], i_d) for i_d in DRAIN_CURRENTS_FIG3}
    if "rds_vs_vgs_125C" in raws:
        curves["rds_vs_vgs_125C_50A"] = rds_at(raws["rds_vs_vgs_125C"], 50)
    if "ciss_crss_curve_ac" in raws:
        s = raws["ciss_crss_curve_ac"]
        if s.axis != "vds":
            raise SystemExit(f"unexpected sweep axis {s.axis!r}")
        w = 2 * math.pi * bl.AC_FREQ
        curves["ciss_crss_25C"] = {"vds_V": [x.real for x in s.values["vds"]],
                                   "ciss_pF": [-i.imag / w * 1e12 for i in s.values["i(vg)"]],
                                   "crss_pF": [i.imag / w * 1e12 for i in s.values["i(vd)"]]}
    for t in (25, 125):
        if f"reverse_{t}C" in raws:
            s = raws[f"reverse_{t}C"].values
            curves[f"reverse_{t}C"] = {"vsd_V": [-v for v in s["v(d)"]], "isd_A": list(s["i(vd)"])}
    rds, vth = {}, {}
    for t in TEMPS:
        r = runs[f"rds_on_{t:g}C"]
        if r.status == "completed":
            mm = r.measurements
            rds[t] = bl.at(mm["i(id)"], mm["v(d)"], 50.0) / 50.0
        r = runs[f"vgs_th_{t:g}C"]
        if r.status == "completed":
            mm = r.measurements
            vth[t] = bl.cross(mm["v(g)"], [-x for x in mm["i(vg)"]], bl.VTH_CURRENT)
    if 25 in rds:
        curves["rds_on_vs_temperature_50A_5V"] = {"tj_C": sorted(rds), "normalized": [rds[t] / rds[25] for t in sorted(rds)],
                                                  "rds_ohm": [rds[t] for t in sorted(rds)]}
    if 25 in vth and all(vth.values()):
        curves["vgs_th_vs_temperature_14mA"] = {"tj_C": sorted(vth), "normalized": [vth[t] / vth[25] for t in sorted(vth)],
                                                "vgs_th_V": [vth[t] for t in sorted(vth)]}
    report = {"schema": "epc2302-model-curves-extra/1",
              "run_outcome": "completed" if not failed else "incomplete", "failed_benches": failed,
              "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "model": {"library_sha256": lib_sha, "archive_sha256": archive_sha, "subcircuit": S, "modified": False},
              "numerics": {"reltol": bl.RELTOL}, "evidence_directory": str(run_root.relative_to(ROOT)),
              "runs": {n: {"status": r.status, "message": r.message, "warnings": r.provenance.get("log_warnings")}
                       for n, r in runs.items()},
              "curves": curves}
    OUTPUT.write_text(json.dumps(report, allow_nan=False) + "\n")
    print(json.dumps({"run_outcome": report["run_outcome"], "failed": failed, "curves": sorted(curves)}, indent=2))
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
