"""Test 12: energy and charge budget of the turn-on ring (where does the ring's energy go, within the model).

Approved after the first-principles review and asked for by the external audit (2 October 2026): test 10's
gate-clamp control cannot partition the losses, so account for the energy element by element instead. No
element, model or network is changed; the vendor model is unmodified. Declared here, 2 October 2026, before the
first run.

Cases: B-m1-mid-ms100, G-m1-mid and G-m1-mid-Ls50 (baseline network, ramp driver, test 7/9 settings) with the
corrected edge timing recorded for the same case in results/gan/epc90133-switching-fullr.json (so one run per
case), and G-m1-mid-Ls50 at 50 ps as the step check. Every node voltage and element current is saved (top level
and both FETs' internals) from 10 ns before Q1's turn-on command (event B) to the end.

Element powers: p = v(n+, n-) * i for every two-terminal element (resistors, inductors including the coupled
network branches, capacitors, voltage sources, switches, LTspice behavioural and charge elements inside the
vendor model). Sign conventions were checked on a small circuit (2 October 2026): LTspice reports switch
currents opposite to every other element type, so switch powers are negated; the absorbed powers then sum to
zero within 1.4e-7 of the largest. Check E1 (bookkeeping, Tellegen): max |sum of absorbed powers| over the saved
window <= 1e-4 of the largest element power. Element groups are assigned by name (sources: bus, output, driver;
storage: magnetic, electric including the FETs' charge elements; losses: network copper, package damping
resistors (the numerical 10 GHz parallel resistors of test 5), capacitor ESR, bus, driver output (resistors and
switches), gate resistors R80-R83, and per FET its rg, rd + rs, channel (bswitch), gate diodes and leakage
resistors).

Ring share: the ring rides on large steady flows (11 A through Q1, the bus charging L1), so its losses are taken
from the deviations of each element's voltage and current from their one-ring-period centred moving averages:
E_ring = integral of v~ i~ dt over [first switch-node peak after the turn-on, command + 60 ns - half a period],
on a 5 ps grid. For a linear resistor this is integral R i~^2 dt. The deviations also satisfy KVL and KCL, so
their powers sum to zero too (check E2, same tolerance on the ring window integrals: |sum| <= 1e-3 of the total
ring loss). Reported per group: ring loss in nJ and as a share of the total ring loss; the ring energy supplied
by sources (their v~ i~); and the whole-window energies. Check E3 (step): every group's ring-loss share changes
by less than 2 percentage points between 100 and 50 ps on G-m1-mid-Ls50.
Reading: shares attribute the simulated ring's dissipation within this model; voltage-envelope decay (tests 10
and the cycle analysis) is a different quantity. Nothing here is a statement about the board.

    PYTHONPATH=src python scripts/epc90133_energy_budget.py
"""
import hashlib
import json
from pathlib import Path
import re
import sys
import uuid

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from circuit_tools.ltspice import run_ltspice  # noqa: E402
import epc2302_baseline as bl  # noqa: E402
import epc90133_switching as sw  # noqa: E402
from epc90133_phase_partial import read_raw  # noqa: E402

TRANSIENT = ROOT / "results/gan/epc90133-switching-fullr.json"
OUTPUT = ROOT / "results/gan/epc90133-energy-budget.json"
CASES = {"B-m1-mid-ms100": dict(ext="B-m1-mid"), "G-m1-mid": dict(ext="G-m1-mid"),
         "G-m1-mid-Ls50": dict(ext="G-m1-mid", l_s=50e-12),
         "G-m1-mid-Ls50-ms50": dict(ext="G-m1-mid", l_s=50e-12, maxstep=sw.MAXSTEP_PKG / 2, timing_of="G-m1-mid-Ls50")}
SAVE_FROM = 10e-9
GRID = 5e-12
TOL_E1, TOL_E2, TOL_E3 = 1e-4, 1e-3, 0.02


def vendor_elements():
    lib, _ = bl.library_path()
    text = Path(lib).read_text(encoding="latin-1")
    m = re.search(r"^\.subckt\s+EPC2302\s+(.*?)^\.ends", text, re.M | re.S | re.I)
    out = []
    for line in m.group(1).splitlines()[1:]:
        tok = line.split()
        if tok and tok[0][0].lower() in "rcb":
            out.append((tok[0].lower(), tok[1].lower(), tok[2].lower()))
    return out


def elements(netlist):
    """(current name, node+, node-, kind) for every two-terminal element; FET internals expanded."""
    vend = vendor_elements()
    out = []
    for line in netlist.splitlines():
        tok = line.split()
        if not tok or tok[0][0] in "*.+" or tok[0][0].upper() in "K":
            continue
        name, kind = tok[0].lower(), tok[0][0].upper()
        if kind == "X":
            pins = dict(zip(("gatein", "drainin", "sourcein"), [t.lower() for t in tok[1:4]]))
            for ename, a, b in vend:
                node = lambda n: pins.get(n, f"{name}:{n}")
                out.append((f"{name}:{ename}", node(a), node(b), "X" + ename[0].upper()))
        elif kind in "RLCVBS":
            out.append((name, tok[1].lower(), tok[2].lower(), kind))
    return out


def group(name, kind):
    if ":" in name:
        fet, e = name.split(":")
        q = {"x1": "Q1", "x2": "Q2"}[fet]
        if e.startswith("c_"):
            return "storage_electric"
        if e == "rg":
            return f"{q}_rg"
        if e in ("rd", "rs"):
            return f"{q}_rd_rs"
        if e == "bswitch":
            return f"{q}_channel"
        if e in ("bgsdiode", "bgddiode"):
            return f"{q}_gate_diodes"
        return f"{q}_leakage_R"
    if kind == "L":
        return "storage_magnetic"
    if kind == "C":
        return "storage_electric"
    if kind == "S":
        return "loss_driver_output"
    if kind == "V":
        if name == "vin":
            return "source_bus"
        if name == "vout":
            return "source_output"
        if name in ("vupu", "vupd", "vlpu", "vlpd"):
            return "source_driver"
        return "source_other"  # 0 V sense sources, switch controls
    if kind == "B":
        return "loss_network_offdiag_R"
    if name.startswith("rb") and name[2:].isdigit():
        return "loss_network_copper"
    if re.fullmatch(r"rp\ds", name):
        return "loss_package_damping_R"
    if name.startswith(("rci", "rcm")) or name == "rcm":
        return "loss_capacitor_ESR"
    if name in ("rsup", "rbus", "rbret"):
        return "loss_bus"
    if name in ("ruu", "rud", "rlu", "rld"):
        return "loss_driver_output"
    if name in ("r80", "r81", "r82", "r83"):
        return "loss_gate_resistors"
    return "loss_other"


def budget(raw, els, t_cmd, f_ring):
    t, v = read_raw(raw)
    V = lambda n: np.zeros_like(t) if n == "0" else v[f"v({n})"]
    p = {}
    for name, a, b, kind in els:
        i = v.get(f"i({name})")
        if i is None:
            continue
        p[name] = (V(a) - V(b)) * i * (-1.0 if kind == "S" else 1.0)
    missing = [e[0] for e in els if e[0] not in p]
    tot = sum(p.values())
    e1 = float(np.abs(tot).max() / max(np.abs(x).max() for x in p.values()))
    # ring window
    g = np.arange(t[0], t[-1], GRID)
    sw_v = np.interp(g, t, V("q2_d"))
    rise = np.argmax((g > t_cmd) & (sw_v > 0.5 * sw.VIN))
    peak = rise + int(np.argmax(sw_v[rise:rise + int(5e-9 / GRID)]))
    T = 1.0 / f_ring
    n_avg = int(round(T / GRID))
    kernel = np.ones(n_avg) / n_avg
    lo, hi = peak, int(np.searchsorted(g, t_cmd + 60e-9 - T / 2))
    ring = {}
    for name, a, b, kind in els:
        if name not in p:
            continue
        sgn = -1.0 if kind == "S" else 1.0
        vv = np.interp(g, t, V(a) - V(b))
        ii = np.interp(g, t, v[f"i({name})"]) * sgn
        dv = vv - np.convolve(vv, kernel, mode="same")
        di = ii - np.convolve(ii, kernel, mode="same")
        ring[name] = float(np.sum((dv * di)[lo:hi]) * GRID)
    whole = {name: float(np.sum(0.5 * (x[1:] + x[:-1]) * np.diff(t))) for name, x in p.items()}
    groups, rgroups = {}, {}
    for name, a, b, kind in els:
        if name in p:
            gname = group(name, kind)
            groups[gname] = groups.get(gname, 0.0) + whole[name]
            rgroups[gname] = rgroups.get(gname, 0.0) + ring[name]
    loss = {k: x for k, x in rgroups.items() if not k.startswith(("source", "storage"))}
    total_loss = sum(loss.values())
    e2 = abs(sum(rgroups.values())) / abs(total_loss) if total_loss else None
    return {"elements": len(p), "missing_currents": missing, "E1_tellegen_rel": e1, "E1_pass": e1 <= TOL_E1,
            "ring_window_s": [float(g[lo]), float(g[hi])], "ring_period_s": T,
            "whole_window_energy_J": groups, "ring_energy_J": rgroups,
            "ring_loss_total_J": total_loss, "ring_loss_share": {k: x / total_loss for k, x in loss.items()},
            "E2_ring_balance_rel": e2, "E2_pass": e2 is not None and e2 <= TOL_E2}


def main():
    lib, _ = bl.library_path()
    bl.verify_target_sources(lib)
    rep = json.loads(TRANSIENT.read_text(encoding="utf-8"))
    cal = rep["driver_calibration"]
    run_root = ROOT / "runs" / ("epc90133-energy-" + uuid.uuid4().hex[:12])
    out = {}
    for name, c in CASES.items():
        src = rep["cases"][c.get("timing_of", name)]
        ext = json.loads((ROOT / f"results/gan/epc90133-extraction/{c['ext']}.json").read_text(encoding="utf-8"))
        timing = src["timing_run"]["corrected_timing_s"]
        text, times, _ = sw.bench(ext, cal["pull_up_edge_s"], cal["pull_down_edge_s"], maxstep=c.get("maxstep", sw.MAXSTEP_PKG),
                                  t_after_b=sw.T_AFTER_B, sense_q2=True, l_s=c.get("l_s"), internal=True, timing=timing)
        tb = times["t_on2"]
        lines = []
        for line in text.splitlines():
            if line.startswith(".save"):
                line = ".save V(*) I(*) V(x1:*) V(x2:*) I(x1:*) I(x2:*)"
            elif line.startswith(".tran"):
                tok = line.split()
                line = f".tran 0 {tok[2]} {tb - SAVE_FROM:.9g} {tok[4]}"
            lines.append(line)
        net = "\n".join(lines)
        d = run_root / name
        r = run_ltspice(net, d, libraries=[lib], timeout_s=3600)
        if r.status != "completed":
            out[name] = {"status": r.status, "message": r.message}
            print(name, "failed:", r.message, flush=True)
            continue
        f_ring = src["metrics"]["event_b_turn_on_at_valley"]["ringing_frequency_Hz"]
        res = budget(d / "bench.raw", elements(net), tb, f_ring)
        out[name] = {"status": "completed", "event_b_command_s": tb, **res}
        print(name, {k: round(x, 3) for k, x in sorted(res["ring_loss_share"].items(), key=lambda kv: -kv[1])},
              "loss", f"{res['ring_loss_total_J'] * 1e9:.1f} nJ", "E1", f"{res['E1_tellegen_rel']:.1e}",
              "E2", f"{res['E2_ring_balance_rel']:.1e}", flush=True)
        report = {"schema": "epc90133-energy-budget/1",
                  "scope": "element energy accounting of the simulated turn-on ring within the unmodified vendor model; "
                           "ring loss = integral of deviations from one-period moving averages; not a statement about the board",
                  "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  "inputs": {TRANSIENT.relative_to(ROOT).as_posix(): hashlib.sha256(TRANSIENT.read_bytes()).hexdigest()},
                  "run_directory": run_root.relative_to(ROOT).as_posix(), "cases": out}
        OUTPUT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    a, b = out.get("G-m1-mid-Ls50", {}), out.get("G-m1-mid-Ls50-ms50", {})
    if a.get("status") == b.get("status") == "completed":
        keys = set(a["ring_loss_share"]) | set(b["ring_loss_share"])
        d3 = {k: b["ring_loss_share"].get(k, 0) - a["ring_loss_share"].get(k, 0) for k in keys}
        out["E3_step_check"] = {"share_change": d3, "pass": all(abs(x) < TOL_E3 for x in d3.values())}
        print("E3", out["E3_step_check"]["pass"], {k: round(x, 4) for k, x in d3.items()})
        report["cases"] = out
        OUTPUT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
