"""Test 10: local small-signal ring check after Q1's turn-on (ring dynamics, separated from excitation).

First-principles review (1 October 2026): separate how strongly the edge excites the ring, what sets the
ring's frequency and decay, and what the probe records. This test addresses only the second, and only LOCALLY:
the circuit is linearized about one specified operating state and its driving-point impedance is computed.
The vendor model is unchanged; LTspice linearizes it at the operating point.

Operating state (declared): the double-pulse bench of scripts/epc90133_switching.py for the named case, with
every time-varying source frozen at T_STATE = 60 ns after Q1's second turn-on command (event B), i.e. Q1 on
(high-side stage static in its on state, through the extracted gate path where the case has one), Q2 off (low-
side stage static, off), bus 48 V. The load (2.2 uH to an ideal 13.8 V source) is replaced by a DC current
source of I_VALLEY = 11.06 A out of the switch node: the operating point carries the event-B current, and the
load branch is open in AC (an ideal 2.2 uH is about 4 kohm at 300 MHz; the real load's high-frequency impedance
is unknown, as the review notes).

Finding the state: LTspice's direct Newton solve fails on this operating point (smoke test on B, 1 October 2026:
Gmin and source stepping fail, pseudo-transient succeeds), and the adapter rightly reports a fallback as a failed
run. So each case first runs an .op-only netlist that saves every node (status recorded, fallback expected), its
state is checked (declared now: switch node at least VIN - 1 V; Q1 internal VGS within 0.1 V of 5 V; Q2 internal
VGS within 0.1 V of 0 V), and the AC run then starts from .nodeset values of every node of that state; the AC run
must converge without fallback (adapter status completed) to be used.

Drive: 1 A AC between Q2's drain pad (q2_d) and circuit ground (Q2's source); Z(f) = V(q2_d). The ring after
event B is the resonance of this port. Read from Z: the dominant peak frequency; a one-pole-pair fit (Levy's
linear least squares, Z = (b0 + b1 s) / (1 + a1 s + a2 s^2) within +-15 % of the peak) giving alpha and omega_d,
reported as zeta = alpha / omega_0 (the transient's definition, delta / sqrt(4 pi^2 + delta^2)) and r = alpha /
omega_d; a half-power bandwidth zeta as a cross-check; and the AC magnitudes of Q1's and Q2's internal VGS
(V(x*:gate, x*:source)) per volt at the switch node at the peak, as gate-feedback participation.

Cases: networks B-m1-mid, B-m1-mid fullR, G-m1-mid, G-m1-mid fullR, G-m1-mid + 50 pH package source,
G-m1-mid + 50 pH fullR, each in two forms kept separate:
  active  - driver stages static at their states, as above (the active driver at rest, linearized);
  clamped - additionally ideal sources hold each vendor-model terminal VGS (Q1 5 V, Q2 0 V): a CONTROL that
            removes gate-loop feedback outside the model's internal rg; not the same circuit.
Declared reading (1 October 2026, before the first run): the local active mode is called consistent with the
transient ring of the same case (tests 7 and 9 reports) if its frequency is within 3 % and its zeta within 25 %.
Consistent means the transient's decay is that of this local linear mode; it does not say the mode or its
damping is the real board's. The half-power zeta is a cross-check only where the half-power band spans at least 10
frequency steps ("half_power_resolved"). Inconsistent means the transient ring involves effects this linearization lacks
(state change during the decay, nonlinear capacitance, other modes). Reported, no further verdicts.

Disclosure: one smoke run (B, active form) was made after this docstring's criteria were written and before
its commit, to debug the state finding: 290.4 MHz, fit zeta 0.0035 (residual 2e-4), against the transient's
282.5 MHz and 0.010; half-power band about 4 steps wide (hence the resolution rule above). No criterion changed.

    PYTHONPATH=src python scripts/epc90133_ringdown.py
"""
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import uuid

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from circuit_tools.ltspice import parse_raw, run_ltspice  # noqa: E402
import epc2302_baseline as bl  # noqa: E402
import epc90133_switching as sw  # noqa: E402

T_STATE = 60e-9
F_LO, F_HI, N_PTS = 50e6, 3e9, 6001
FIT_SPAN = 0.15
OUTPUT = ROOT / "results/gan/epc90133-ringdown.json"
CASES = {"B-m1-mid": dict(ext="B-m1-mid"), "B-m1-mid-fullR": dict(ext="B-m1-mid", full_r=True),
         "G-m1-mid": dict(ext="G-m1-mid"), "G-m1-mid-fullR": dict(ext="G-m1-mid", full_r=True),
         "G-m1-mid-Ls50": dict(ext="G-m1-mid", l_s=50e-12), "G-m1-mid-Ls50-fullR": dict(ext="G-m1-mid", l_s=50e-12, full_r=True)}
# Transient counterparts (same network and options, 100 ps): report, case name.
TRANSIENT = {"B-m1-mid": ("epc90133-switching-fullr.json", "B-m1-mid-ms100"),
             "B-m1-mid-fullR": ("epc90133-switching-fullr.json", "B-m1-mid-ms100-fullR"),
             "G-m1-mid": ("epc90133-switching-fullr.json", "G-m1-mid"),
             "G-m1-mid-fullR": ("epc90133-switching-fullr.json", "G-m1-mid-fullR"),
             "G-m1-mid-Ls50": ("epc90133-switching-fullr.json", "G-m1-mid-Ls50"),
             "G-m1-mid-Ls50-fullR": ("epc90133-switching-fullr.json", "G-m1-mid-Ls50-fullR")}


def pwl_value(args, t):
    v = [float(x) for x in args.split()]
    ts, ys = v[0::2], v[1::2]
    return float(np.interp(t, ts, ys))


def small_signal_netlist(text, t_state, clamp, die, op_only=False, nodeset=None):
    out = []
    for line in text.splitlines():
        m = re.match(r"^(\S+)\s+(\S+)\s+(\S+)\s+PWL\((.*)\)\s*$", line)
        if m:
            out.append(f"{m.group(1)} {m.group(2)} {m.group(3)} {pwl_value(m.group(4), t_state):.9g}")
            continue
        if line.startswith("L1 "):
            out.append(f"Iload q2_d 0 {sw.I_VALLEY:.9g}")
            continue
        if line.startswith(("Vout ", ".tran", ".save", ".end")) or line == "":
            continue
        out.append(line)
    if clamp:
        out += [f"Vclamp1 {die['g1']} {die['s1']} {sw.VBOOT:g}",
                f"Vclamp2 {die['g2']} {die['s2']} 0"]
    if op_only:
        return "\n".join(out + [".save V(*) V(x1:*) V(x2:*)", ".op", ".end", ""])
    if nodeset:
        out += [f".nodeset {k.upper()}={v:.12g}" for k, v in nodeset.items()]
    out += ["Iac 0 q2_d AC 1",
            ".save V(q2_d) V(x1:gate) V(x1:source) V(x2:gate) V(x2:source)",
            f".ac lin {N_PTS} {F_LO:g} {F_HI:g}", ".end", ""]
    return "\n".join(out)


def levy_fit(f, z):
    s = 2j * math.pi * f
    # z (1 + a1 s + a2 s^2) = b0 + b1 s  ->  linear in (b0, b1, a1, a2)
    A = np.column_stack([np.ones_like(s), s, -z * s, -z * s ** 2])
    A2 = np.vstack([A.real, A.imag])
    y = np.concatenate([z.real, z.imag])
    scale = np.abs(A2).max(axis=0)
    x = np.linalg.lstsq(A2 / scale, y, rcond=None)[0] / scale
    b0, b1, a1, a2 = x
    poles = np.roots([a2, a1, 1.0])
    p = poles[np.argmax(poles.imag)]
    alpha, wd = -p.real, abs(p.imag)
    resid = np.abs((b0 + b1 * s) / (1 + a1 * s + a2 * s ** 2) - z).max() / np.abs(z).max()
    return alpha, wd, float(resid)


def analyse(raw):
    s = raw.step(0)
    f = np.array([abs(x) for x in s["frequency"]])
    z = np.array(s["v(q2_d)"])
    mag = np.abs(z)
    # local maxima above 20 % of the largest
    idx = [i for i in range(1, len(mag) - 1) if mag[i] >= mag[i - 1] and mag[i] >= mag[i + 1] and mag[i] > 0.2 * mag.max()]
    k = int(np.argmax(mag))
    f0 = f[k]
    w = (f > f0 * (1 - FIT_SPAN)) & (f < f0 * (1 + FIT_SPAN))
    alpha, wd, resid = levy_fit(f[w], z[w])
    w0 = math.hypot(alpha, wd)
    half = mag >= mag[k] / math.sqrt(2)
    lo = k
    while lo > 0 and half[lo - 1]:
        lo -= 1
    hi = k
    while hi < len(mag) - 1 and half[hi + 1]:
        hi += 1
    vsw = z[k]
    part = {}
    for q in ("1", "2"):
        vi = np.array(s[f"v(x{q}:gate)"])[k] - np.array(s[f"v(x{q}:source)"])[k]
        part[f"q{q}_internal_vgs_per_V_sw"] = float(abs(vi / vsw))
    return {"peak_frequency_Hz": float(f0), "peak_impedance_ohm": float(mag[k]),
            "other_peaks_Hz": [float(f[i]) for i in idx if i != k],
            "fit": {"alpha_per_s": float(alpha), "f_damped_Hz": float(wd / (2 * math.pi)), "zeta": float(alpha / w0),
                    "r_alpha_over_omega_d": float(alpha / wd), "max_rel_residual": resid},
            "half_power_zeta": float((f[hi] - f[lo]) / (2 * f0)),
            "half_power_resolved": bool(hi - lo >= 10),
            "participation_at_peak": part}


def main():
    lib, _ = bl.library_path()
    bl.verify_target_sources(lib)
    run_root = ROOT / "runs" / ("epc90133-ringdown-" + uuid.uuid4().hex[:12])
    cal = json.loads((ROOT / "results/gan/epc90133-switching-gateloop.json").read_text(encoding="utf-8"))["driver_calibration"]
    te_rise, te_fall = cal["pull_up_edge_s"], cal["pull_down_edge_s"]
    out = {}
    for name, c in CASES.items():
        ext = json.loads((ROOT / f"results/gan/epc90133-extraction/{c['ext']}.json").read_text(encoding="utf-8"))
        text, times, _ = sw.bench(ext, te_rise, te_fall, maxstep=sw.MAXSTEP_PKG, t_after_b=sw.T_AFTER_B, sense_q2=True,
                                  l_s=c.get("l_s"), full_r=c.get("full_r", False), internal=True)
        row = {"extraction": c["ext"], "options": {k: v for k, v in c.items() if k != "ext"},
               "state_time_s": times["t_on2"] + T_STATE}
        for form in ("active", "clamped"):
            ts, clamp, die = times["t_on2"] + T_STATE, form == "clamped", times["die_nodes"]
            dop = run_root / f"{name}-{form}-op"
            rop = run_ltspice(small_signal_netlist(text, ts, clamp, die, op_only=True), dop, libraries=[lib], timeout_s=3600)
            raw_op = dop / "bench.raw"
            if not raw_op.exists():
                row[form] = {"status": "state not found", "op_message": rop.message}
                print(name, form, "state not found:", rop.message)
                continue
            st = parse_raw(raw_op).step(0)
            vals = {k: float(v[0]) for k, v in st.items() if k.startswith("v(")}
            state = {"op_status": rop.status, "op_message": rop.message,
                     "v_sw_V": vals["v(q2_d)"],
                     "q1_internal_vgs_V": vals["v(x1:gate)"] - vals["v(x1:source)"],
                     "q2_internal_vgs_V": vals["v(x2:gate)"] - vals["v(x2:source)"]}
            state["checks_pass"] = (state["v_sw_V"] >= sw.VIN - 1 and abs(state["q1_internal_vgs_V"] - sw.VBOOT) <= 0.1
                                    and abs(state["q2_internal_vgs_V"]) <= 0.1)
            if not state["checks_pass"]:
                row[form] = {"status": "state check failed", "state": state}
                print(name, form, "state check failed", state)
                continue
            net = small_signal_netlist(text, ts, clamp, die, nodeset=vals)
            d = run_root / f"{name}-{form}"
            r = run_ltspice(net, d, libraries=[lib], timeout_s=1800)
            if r.status != "completed":
                row[form] = {"status": r.status, "message": r.message, "state": state}
                print(name, form, "failed:", r.message)
                continue
            row[form] = {"status": "completed", "state": state, **analyse(parse_raw(d / "bench.raw"))}
            a = row[form]
            print(f"{name:22s} {form:7s} f {a['peak_frequency_Hz'] / 1e6:7.1f} MHz zeta {a['fit']['zeta']:.4f} "
                  f"(hp {a['half_power_zeta']:.4f}, resid {a['fit']['max_rel_residual']:.3f}) "
                  f"part Q2 {a['participation_at_peak']['q2_internal_vgs_per_V_sw']:.4f}", flush=True)
        rep, case = TRANSIENT[name]
        p = ROOT / "results/gan" / rep
        tr = json.loads(p.read_text(encoding="utf-8"))["cases"].get(case) if p.exists() else None
        if tr and tr.get("metrics") and row.get("active", {}).get("status") == "completed":
            m = tr["metrics"]["event_b_turn_on_at_valley"]
            a = row["active"]
            df = a["peak_frequency_Hz"] / m["ringing_frequency_Hz"] - 1
            dz = a["fit"]["zeta"] / m["ringing_damping_ratio"] - 1
            row["transient_comparison"] = {"report": rep, "case": case, "transient_f_Hz": m["ringing_frequency_Hz"],
                                           "transient_zeta": m["ringing_damping_ratio"], "rel_f": df, "rel_zeta": dz,
                                           "consistent": abs(df) <= 0.03 and abs(dz) <= 0.25}
        else:
            row["transient_comparison"] = {"report": rep, "case": case, "status": "transient result not available"}
        out[name] = row
    report = {"schema": "epc90133-ringdown/1",
              "scope": "local small-signal impedance at Q2's drain-source port about one operating state after event B; "
                       "ring dynamics only (not excitation, not observation); load branch open in AC",
              "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "generator_sha256": hashlib.sha256((ROOT / "scripts/epc90133_switching.py").read_bytes()).hexdigest(),
              "run_directory": run_root.relative_to(ROOT).as_posix(), "state": {"after_event_b_s": T_STATE,
              "load_dc_current_A": sw.I_VALLEY, "bus_V": sw.VIN}, "cases": out}
    OUTPUT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
