"""Test 13: does Q1's partly enhanced channel account for the transient ring's damping? (local AC control)

Observation that prompted it (2 October 2026, from saved data, before this test): in the transient, Q1's internal
gate-source voltage is about 2.5 V when the turn-on ring starts and reaches 4.6 V only 20 ns later (test 9
traces), and test 12's energy budget on B puts 64 % of the ring's loss in Q1's channel. Test 10 linearized
with Q1 fully on (5 V), which gave a smaller damping than the transient. Hypothesis, within the model: the ring
is damped mainly by Q1's channel while Q1 is still turning on. Declared here, 2 October 2026, before any run.

Method: test 10's local AC analysis (scripts/epc90133_ringdown.py, same bench, state 60 ns after event B, load as
an 11.06 A DC current source, 1 A AC into Q2's drain-source port) in its clamped form, with Q1's vendor-model
terminal VGS clamped at X = 2.5, 3.0, 3.5, 4.0 and 4.5 V instead of 5 V (Q2 clamped at 0 V). At DC no gate current
flows, so Q1's internal VGS equals X. Networks: B-m1-mid and G-m1-mid + 50 pH (assumed package source inductance).
Operating state: found by an .op-only run (fallbacks expected), then the AC run from .nodeset values; a form
counts if its own solved operating point has Q1 internal VGS within 0.1 V of X, Q2 internal VGS within 0.1 V of 0
and the switch node between 0 and VIN, and its AC sweep is complete (the revision 3/4 rule of test 10; any
operating-point fallback is flagged). The X = 5 V point is test 10's clamped result.

Comparison with the transient: the cycle-by-cycle damping of the same case (scripts/epc90133_ring_decay.py,
results/gan/epc90133-ring-decay.json) and Q1's internal VGS trace (test 9 report). For each X, the transient
cycles whose start time has Q1 internal VGS within 0.15 V of X are averaged. Declared reading: the hypothesis is
supported within the model if the local zeta rises as X falls and, for every X with matching transient cycles,
the local zeta is within 30 % of their mean zeta. Otherwise Q1's channel bias alone does not account for the
transient's damping. Either way a model statement: the real device's channel and gate charging are not
characterized (Fig. 7 gate charge fails its checks).

    PYTHONPATH=src python scripts/epc90133_q1_bias_ring.py
"""
import hashlib
import json
from pathlib import Path
import sys
import uuid

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from circuit_tools.ltspice import parse_raw, run_ltspice  # noqa: E402
import epc2302_baseline as bl  # noqa: E402
import epc90133_ringdown as rd  # noqa: E402
import epc90133_switching as sw  # noqa: E402

X_VALUES = (2.5, 3.0, 3.5, 4.0, 4.5)
CASES = {"B-m1-mid": dict(ext="B-m1-mid", transient="B-m1-mid-ms100"),
         "G-m1-mid-Ls50": dict(ext="G-m1-mid", l_s=50e-12, transient="G-m1-mid-Ls50")}
TRANSIENT = ROOT / "results/gan/epc90133-switching-fullr.json"
DECAY = ROOT / "results/gan/epc90133-ring-decay.json"
RINGDOWN = ROOT / "results/gan/epc90133-ringdown.json"
OUTPUT = ROOT / "results/gan/epc90133-q1-bias-ring.json"
VGS_MATCH, ZETA_TOL = 0.15, 0.30


def solved_state(op_raw, x):
    st = parse_raw(op_raw).step(0)
    vals = {k: float(v[0]) for k, v in st.items() if k.startswith("v(")}
    s = {"v_sw_V": vals["v(q2_d)"], "q1_internal_vgs_V": vals["v(x1:gate)"] - vals["v(x1:source)"],
         "q2_internal_vgs_V": vals["v(x2:gate)"] - vals["v(x2:source)"]}
    s["checks_pass"] = (abs(s["q1_internal_vgs_V"] - x) <= 0.1 and abs(s["q2_internal_vgs_V"]) <= 0.1
                        and 0 < s["v_sw_V"] < sw.VIN)
    return s, vals


def run_form(text, ts, die, x, d, lib):
    def clamp(net):
        lines = net.splitlines()
        k = next(i for i, l in enumerate(lines) if l.startswith("Vclamp1 "))
        tok = lines[k].split()
        lines[k] = f"Vclamp1 {tok[1]} {tok[2]} {x:g}"
        return "\n".join(lines) + "\n"
    rop = run_ltspice(clamp(rd.small_signal_netlist(text, ts, True, die, op_only=True)), d.with_name(d.name + "-op"),
                      libraries=[lib], timeout_s=3600)
    raw_op = d.with_name(d.name + "-op") / "bench.raw"
    if not raw_op.exists():
        return {"status": "state not found", "op_message": rop.message}
    guess, vals = solved_state(raw_op, x)
    r = run_ltspice(clamp(rd.small_signal_netlist(text, ts, True, die, nodeset=vals)), d, libraries=[lib], timeout_s=1800)
    if not (d / "bench.op.raw").exists() or not (d / "bench.raw").exists():
        return {"status": "failed", "message": r.message, "initial_guess_state": guess}
    own, _ = solved_state(d / "bench.op.raw", x)
    reasons = [y.strip() for y in (r.message or "").split(";") if y.strip()]
    only_fallback = all(any(ph in y for ph in rd.FALLBACK_PHRASES) for y in reasons)
    ac = parse_raw(d / "bench.raw").step(0)
    ok = (r.status == "completed" or only_fallback) and own["checks_pass"] and len(ac["frequency"]) == rd.N_PTS
    status = ("completed" if r.status == "completed" else "accepted_with_verified_op_fallback") if ok else "failed"
    out = {"status": status, "adapter_message": r.message, "initial_guess_state": guess, "solved_state": own}
    if ok:
        out.update(rd.analyse(parse_raw(d / "bench.raw")))
    return out


def transient_cycles(case):
    tr = json.loads(TRANSIENT.read_text(encoding="utf-8"))["cases"][case]["traces"]
    t = tr["start_s"] + tr["step_s"] * np.arange(len(tr["rising_V"]))
    vg = np.array(tr["device"]["rising_q1_vgs_internal_V"])
    cyc = json.loads(DECAY.read_text(encoding="utf-8"))["cases"][case]["cycles"]
    # ring-decay cycle times and the trace axis are both relative to the turn-on command
    return [{**c, "q1_internal_vgs_V": float(np.interp(c["t_s"], t, vg))} for c in cyc]


def main():
    lib, _ = bl.library_path()
    bl.verify_target_sources(lib)
    cal = json.loads(TRANSIENT.read_text(encoding="utf-8"))["driver_calibration"]
    run_root = ROOT / "runs" / ("epc90133-q1bias-" + uuid.uuid4().hex[:12])
    ringdown = json.loads(RINGDOWN.read_text(encoding="utf-8"))["cases"]
    out = {}
    for name, c in CASES.items():
        ext = json.loads((ROOT / f"results/gan/epc90133-extraction/{c['ext']}.json").read_text(encoding="utf-8"))
        text, times, _ = sw.bench(ext, cal["pull_up_edge_s"], cal["pull_down_edge_s"], maxstep=sw.MAXSTEP_PKG,
                                  t_after_b=sw.T_AFTER_B, sense_q2=True, l_s=c.get("l_s"), internal=True)
        ts, die = times["t_on2"] + rd.T_STATE, times["die_nodes"]
        forms = {}
        for x in X_VALUES:
            forms[f"{x:g}"] = run_form(text, ts, die, x, run_root / f"{name}-q1vgs{x:g}", lib)
            f = forms[f"{x:g}"]
            print(name, x, f["status"], f"zeta {f['fit']['zeta']:.4f} f {f['peak_frequency_Hz'] / 1e6:.1f} MHz" if "fit" in f else f.get("adapter_message"),
                  flush=True)
        c5 = ringdown[name]["clamped"]
        forms["5"] = {"status": "test 10 clamped", "fit": c5["fit"], "peak_frequency_Hz": c5["peak_frequency_Hz"]}
        cyc = transient_cycles(c["transient"])
        comp = {}
        for x in list(X_VALUES) + [5.0]:
            f = forms[f"{x:g}"]
            m = [cc["zeta"] for cc in cyc if abs(cc["q1_internal_vgs_V"] - x) <= VGS_MATCH]
            comp[f"{x:g}"] = {"local_zeta": f["fit"]["zeta"] if "fit" in f else None, "matching_cycles": len(m),
                              "transient_mean_zeta": float(np.mean(m)) if m else None,
                              "within_tol": (abs(f["fit"]["zeta"] / np.mean(m) - 1) <= ZETA_TOL) if (m and "fit" in f) else None}
        zs = [comp[f"{x:g}"]["local_zeta"] for x in list(X_VALUES) + [5.0]]
        rising = all(a is not None and b is not None and a > b for a, b in zip(zs, zs[1:]))
        matched = [v["within_tol"] for v in comp.values() if v["within_tol"] is not None]
        out[name] = {"forms": forms, "transient_cycles": cyc, "comparison": comp, "local_zeta_rises_as_vgs_falls": rising,
                     "supported": bool(rising and matched and all(matched))}
        print(name, {k: (round(v["local_zeta"], 4) if v["local_zeta"] else None, v["matching_cycles"],
                         round(v["transient_mean_zeta"], 4) if v["transient_mean_zeta"] else None) for k, v in comp.items()},
              "supported", out[name]["supported"], flush=True)
        OUTPUT.write_text(json.dumps({"schema": "epc90133-q1-bias-ring/1",
                                      "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                      "inputs": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                                 for p in (TRANSIENT, DECAY, RINGDOWN)},
                                      "run_directory": run_root.relative_to(ROOT).as_posix(), "cases": out}, indent=1) + "\n",
                          encoding="utf-8")


if __name__ == "__main__":
    main()
