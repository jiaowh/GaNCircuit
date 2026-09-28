#!/usr/bin/env python3
"""Simulate the unmodified EPC2204 model for the datasheet curves not covered by the baseline.

Adds RDS(on) against VGS for several drain currents and two temperatures
(datasheet Figs. 3-4), CISS/CRSS against VDS (Fig. 5), reverse conduction at
25 and 125 C (Fig. 8) and RDS(on) against temperature (Fig. 9). It uses the
baseline's library check and numerical settings. Output curves go to
results/gan/epc2204-model-curves-extra.json; the comparison is
scripts/compare_epc2204_curves.py.
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
import epc2204_baseline as bl

OUTPUT = ROOT / "results/gan/epc2204-model-curves-extra.json"
TEMPS_FIG9 = (0, 25, 50, 75, 100, 125, 150)
DRAIN_CURRENTS_FIG3 = (8, 16, 24, 32)


def benches():
    b = {}
    b["rds_vs_vgs_25C"] = bl.HEAD + f"""* RDS(on) against VGS: drain current forced, VGS swept, 25 C
.param id=16
Id 0 d {{id}}
Vg g 0 5
X1 g d 0 EPC2204
.temp 25
.step param id list {' '.join(str(i) for i in DRAIN_CURRENTS_FIG3)}
.dc Vg 2 5 0.01
.end
"""
    b["rds_vs_vgs_125C"] = bl.HEAD + """* RDS(on) against VGS: 16 A forced, VGS swept, 125 C
Id 0 d 16
Vg g 0 5
X1 g d 0 EPC2204
.temp 125
.dc Vg 2 5 0.01
.end
"""
    b["ciss_crss_curve_ac"] = bl.HEAD + f"""* CISS and CRSS against VDS: AC on gate, drain held at VDS (AC ground)
.param vds=50
Vg g 0 0 AC 1
Vd d 0 {{vds}}
X1 g d 0 EPC2204
.temp 25
.step param vds 0 100 0.5
.ac list {bl.AC_FREQ:g}
.end
"""
    for t in (25, 125):
        b[f"reverse_{t}C"] = bl.HEAD + f"""* Reverse conduction: VGS = 0 V, drain swept below the source
Vd d 0 0
Vg g 0 0
X1 g d 0 EPC2204
.temp {t}
.dc Vd 0 -5 -0.01
.end
"""
    for t in TEMPS_FIG9:
        b[f"rds_on_{t}C"] = bl.HEAD + f"""* RDS(on) against temperature: VGS = 5 V, 16 A
Vg g 0 5
Id 0 d 16
X1 g d 0 EPC2204
.temp {t}
.op
.end
"""
    return b


def main():
    lib, archive_sha = bl.library_path()
    run_root = ROOT / "runs" / ("epc2204-curves-" + uuid.uuid4().hex)
    runs, raws = {}, {}
    for name, text in benches().items():
        text = text.replace("\n.end\n", f"\n.options reltol={bl.RELTOL:g}\n.end\n")
        r = run_ltspice(text, run_root / name, libraries=[lib], timeout_s=600)
        runs[name] = r
        if r.status == "completed":
            raws[name] = parse_raw(r.result_path)
    failed = {n: r.message for n, r in runs.items() if r.status != "completed"}
    curves = {}
    raw = raws.get("rds_vs_vgs_25C")
    if raw:
        curves["rds_vs_vgs_25C"] = {}
        for k, i_d in enumerate(DRAIN_CURRENTS_FIG3):
            s = raw.step(k)
            curves["rds_vs_vgs_25C"][f"id_{i_d}A"] = {"vgs_V": s["vg"], "rds_mohm": [v / i_d * 1e3 for v in s["v(d)"]]}
    if "rds_vs_vgs_125C" in raws:
        s = raws["rds_vs_vgs_125C"].values
        curves["rds_vs_vgs_125C_16A"] = {"vgs_V": s["vg"], "rds_mohm": [v / 16 * 1e3 for v in s["v(d)"]]}
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
            # Current leaves the device at the drain and enters Vd's positive terminal.
            curves[f"reverse_{t}C"] = {"vsd_V": [-v for v in s["v(d)"]], "isd_A": list(s["i(vd)"])}
    rds = {}
    for t in TEMPS_FIG9:
        r = runs[f"rds_on_{t}C"]
        if r.status == "completed":
            rds[t] = r.measurements["v(d)"][0] / 16
    if 25 in rds:
        curves["rds_on_vs_temperature_16A_5V"] = {"tj_C": sorted(rds), "normalized": [rds[t] / rds[25] for t in sorted(rds)],
                                                  "rds_ohm": [rds[t] for t in sorted(rds)]}
    report = {"schema": "epc2204-model-curves-extra/1",
              "run_outcome": "completed" if not failed else "incomplete", "failed_benches": failed,
              "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "model": {"library_sha256": hashlib.sha256(lib.read_bytes()).hexdigest(), "archive_sha256": archive_sha,
                        "subcircuit": "EPC2204", "modified": False},
              "numerics": {"reltol": bl.RELTOL}, "evidence_directory": str(run_root.relative_to(ROOT)),
              "runs": {n: {"status": r.status, "message": r.message, "warnings": r.provenance.get("log_warnings")}
                       for n, r in runs.items()},
              "curves": curves}
    OUTPUT.write_text(json.dumps(report, allow_nan=False) + "\n")
    print(json.dumps({"run_outcome": report["run_outcome"], "failed": failed, "curves": sorted(curves)}, indent=2))
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
