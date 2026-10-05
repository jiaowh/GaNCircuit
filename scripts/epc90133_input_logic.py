#!/usr/bin/env python3
"""Can any EPC90133 input state command both gates on? (hardware plan open item 5)

The uP1966E has no lockout between HI and LI (datasheet p. 5), so shoot-through
protection rests on the board's input logic (QSG Fig. 16), its jumpers and the PWM
source. devices/epc/epc90133-input-logic.json transcribes that logic; this script
evaluates it as recorded and does not hard-code the board's behaviour.

Checks, declared before the first run (5 October 2026):

L1  Every part in the transcription's bom_parts matches the recorded BOM file.
L2  The gate function used here, Y = (C ? B : A) XOR D with OE active low, reproduces
    every row of the 74LVC1G99 datasheet's Table 4 parsed from the recorded PDF
    (at least 16 OE-low rows, and Z for OE high).
L3  Static evaluation reproduces what the QSG says about its documented settings
    (PWM2 open where the setting is single-input):
      J630 1-2 + J640 5-6 (single buck, no bypass): HIN = PWM1, LIN = not PWM1,
          both turn-ons through the RC delay;
      J630 3-4 + J640 5-6 (single boost, no bypass): HIN = not PWM1, LIN = PWM1,
          both turn-ons through the RC delay;
      J630 5-6 + any J640 setting (dual): HIN = PWM1, LIN = PWM2;
      J640 1-2 (full bypass): HIN = PWM1, LIN = PWM2 whatever J630 holds.
    L3 passes only if all four hold; it tests the transcription, not the board.
L4  Dead time from datasheet limits (arithmetic, no simulation), declared formula:
      t_RC = R C ln((VOH - V0) / (VOH - VT+)), VT+ interpolated linearly to 5.0 V
      between the datasheet's 4.5 V and 5.5 V rows (-40..85 C), R +/-1 %,
      C +/-10 % (room) and additionally +/-15 % (X7R over temperature, reported
      separately), VOH in [VCC - 0.1, VCC], V0 (capacitor voltage left by the diode
      discharge) in [0, 0.3] V (assumed, not from a datasheet);
      logic skew = difference of the two channels' A->Y + B->Y delays, each in
      [1.8, 5.5] + [1.8, 5.4] ns (4.5-5.5 V, -40..85 C);
      driver delay matching 6 ns max (uP1966E TMON/TMOFF).
    Reported: t_RC range, and the worst-case gate-command dead time
    t_RC,min - skew_max - driver_match_max. The diode-discharge (turn-off) delay is
    not bounded by any datasheet here and is reported as an unbounded reduction.
    L4 is informational: it states whether datasheet limits guarantee a positive
    dead time; it has no pass threshold.
L5  Power-up: U80 enables its outputs only above its POR threshold (3.8 V min), at
    which the shared VCC is above the logic's 1.65 V minimum supply, so the gate
    commands at enable are the static idle state (PWM inputs open = low via
    R601/R602). Reported per configuration.

Findings, reported without a pass threshold: for all 64 combinations of horizontal
jumper positions on J630 and J640 (no jumper, one, two or three per header; a
vertical placement shorts two pulled-down signals or two VCC pins and reduces to a
listed case), which input states command both gates on, and whether the
complementary settings have an RC delay on each turn-on.

Static logic only: no timing simulation, no PWM-source behaviour, no noise.
"""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_epc90133_board_files import read_bom, verified

LOGIC = ROOT / "devices/epc/epc90133-input-logic.json"
POSITIONS = ("1-2", "3-4", "5-6")
VCC = 5.0
LOGIC_VCC_MIN, DRIVER_POR_MIN = 1.65, 3.8
VT_PLUS = {4.5: (2.16, 2.52, 2.74), 5.5: (2.61, 2.99, 3.33)}  # 74LVC1G99 Table 24 (min, typ, max), -40..85 C
T_AY, T_BY = (1.8, 3.8, 5.5), (1.8, 3.8, 5.4)  # ns, 4.5-5.5 V, -40..85 C (Table 25)
DRIVER_MATCH_MAX, DRIVER_MATCH_TYP = 6.0, 1.5  # ns, uP1966E TMON/TMOFF
V0_RANGE = (0.0, 0.3)  # V, assumed residual capacitor voltage after diode discharge


def gate(oe, a, b, c, d):
    """74LVC1G99: Y = (C ? B : A) XOR D, Z when OE is high."""
    if oe:
        return None
    return (b if c else a) ^ d


def parse_function_table(pdf_path):
    import fitz
    doc = fitz.open(pdf_path)
    for page in doc:
        text = page.get_text()
        if "Table 4. Function table" in text:
            tail = text.split("Table 4. Function table", 1)[1]
            tokens = re.findall(r"^\s*([LHXZ])\s*$", tail, re.M)
            rows = [tokens[i:i + 6] for i in range(0, len(tokens) - 5, 6)]
            return [r for r in rows if len(r) == 6]
    return []


def check_function_table(rows):
    val = {"L": 0, "H": 1}
    oe_low = [r for r in rows if r[0] == "L"]
    bad = []
    for r in rows:
        oe, d, c, b, a, y = r
        if oe == "H":
            if y != "Z":
                bad.append(r)
            continue
        got = gate(0, val[a], val[b], val[c], val[d])
        if "HL"[1 - got] != y:
            bad.append(r)
    return {"rows_parsed": len(rows), "oe_low_rows": len(oe_low), "mismatches": bad,
            "pass": len(oe_low) >= 16 and not bad}


def evaluate(logic, j630, j640, in1, in2):
    """Static gate commands for one jumper set and input state. Returns nets and paths."""
    nets = {"GND": 0, "VCC": 1, "In1": in1, "In2": in2}
    for header, placed in (("J630", j630), ("J640", j640)):
        pins = logic["headers"][header]["pins"]
        for pos in placed:
            p, q = pos.split("-")
            sig = pins[p]
            if sig is not None and pins[q] == "VCC":
                nets[sig] = 1
    for name in ("PolQup", "PolQlow", "Dual", "UseDT", "SWbyp"):
        nets.setdefault(name, 0)  # 10 k pull-downs
    g = logic["gates"]
    for ref in ("U610", "U611"):
        p = g[ref]
        nets[p["Y"]] = gate(nets[p["OE"]], nets[p["A"]], nets[p["B"]], nets[p["C"]], nets[p["D"]])
    for node, dn in logic["delay_networks"].items():
        nets[node] = nets[dn["from"]]  # static: the RC node settles to its source
    out, path = {}, {}
    for ref in ("U612", "U614"):
        p = g[ref]
        y = gate(nets[p["OE"]], nets[p["A"]], nets[p["B"]], nets[p["C"]], nets[p["D"]])
        drivers = []
        if y is not None:
            drivers.append(("gate", y, "rc_delayed" if nets[p["C"]] else "direct"))
        for sref, s in logic["switches"].items():
            if s["b"] == p["Y"] and nets[s["control"]]:
                drivers.append(("switch", nets[s["a"]], "pwm_input_direct"))
        values = {d[1] for d in drivers}
        out[p["Y"]] = None if len(values) != 1 else values.pop()  # None: contention or floating
        if not drivers:
            out[p["Y"]] = 0  # floating, held low by R71/R76 and U80's 200 k
        path[p["Y"]] = [d[2] for d in drivers] or ["pulled_down"]
    hin = out[logic["driver_inputs"]["HIN"]["from"]]
    lin = out[logic["driver_inputs"]["LIN"]["from"]]
    return {"HIN": hin, "LIN": lin, "paths": path, "contention": any(v is None for v in out.values()),
            "selects": {k: nets[k] for k in ("PolQup", "PolQlow", "Dual", "UseDT", "SWbyp")}}


def classify(logic, j630, j640):
    states = {(a, b): evaluate(logic, j630, j640, a, b) for a in (0, 1) for b in (0, 1)}
    both_on = [f"PWM1={a},PWM2={b}" for (a, b), s in states.items() if s["HIN"] == 1 and s["LIN"] == 1]
    hin1 = [states[(a, 0)]["HIN"] for a in (0, 1)]
    lin1 = [states[(a, 0)]["LIN"] for a in (0, 1)]
    paths = states[(1, 0)]["paths"]
    idle = states[(0, 0)]
    if states[(0, 0)]["HIN"] == 1 and states[(0, 0)]["LIN"] == 1:
        kind = "both on at idle (PWM inputs open or low)"
    elif any(h == 1 and l == 1 for h, l in zip(hin1, lin1)):
        kind = "both follow PWM1: both on whenever PWM1 is high (PWM2 open)"
    elif hin1 == [1 - x for x in lin1]:
        delayed = all(p == ["rc_delayed"] for p in paths.values())
        kind = ("complementary from PWM1, RC delay on each turn-on" if delayed
                else "complementary from PWM1, no added dead time")
    elif both_on:
        kind = "independent inputs: both on only if the PWM source sets PWM1 and PWM2 high together"
    else:
        kind = "no input state commands both on"
    return {"J630": list(j630), "J640": list(j640), "kind": kind, "both_on_states": both_on,
            "idle_gate_commands": {"HIN": idle["HIN"], "LIN": idle["LIN"]},
            "paths_pwm1_high": paths, "contention": any(s["contention"] for s in states.values()),
            "truth": {f"PWM1={a},PWM2={b}": {"HIN": s["HIN"], "LIN": s["LIN"]} for (a, b), s in states.items()}}


def qsg_checks(logic):
    def fn(j630, j640):
        return {(a, b): evaluate(logic, j630, j640, a, b) for a in (0, 1) for b in (0, 1)}

    def follows(st, h, l):
        return all(st[k]["HIN"] == h(*k) and st[k]["LIN"] == l(*k) for k in st)

    out = {}
    st = fn(["1-2"], ["5-6"])
    out["single_buck_no_bypass"] = (all(st[(a, 0)]["HIN"] == a and st[(a, 0)]["LIN"] == 1 - a for a in (0, 1))
                                    and all(p == ["rc_delayed"] for p in st[(1, 0)]["paths"].values()))
    st = fn(["3-4"], ["5-6"])
    out["single_boost_no_bypass"] = (all(st[(a, 0)]["HIN"] == 1 - a and st[(a, 0)]["LIN"] == a for a in (0, 1))
                                     and all(p == ["rc_delayed"] for p in st[(1, 0)]["paths"].values()))
    out["dual_any_bypass"] = all(follows(fn(["5-6"], [j]), lambda a, b: a, lambda a, b: b) for j in POSITIONS)
    out["full_bypass_any_mode"] = all(follows(fn(j, ["1-2"]), lambda a, b: a, lambda a, b: b)
                                      for j in ([], ["1-2"], ["3-4"], ["5-6"]))
    return out


def dead_time_bounds(logic):
    vals = logic["component_values"]
    r, rt = vals["R620_R625"]["ohm"], vals["R620_R625"]["tolerance"]
    c, ct = vals["C620_C625"]["F"], vals["C620_C625"]["tolerance"]
    frac = (VCC - 4.5) / 1.0
    vt = [VT_PLUS[4.5][i] + frac * (VT_PLUS[5.5][i] - VT_PLUS[4.5][i]) for i in range(3)]

    def t_rc(rr, cc, voh, v0, vtp):
        return rr * cc * math.log((voh - v0) / (voh - vtp)) * 1e9

    typ = t_rc(r, c, VCC, 0.0, vt[1])
    room = (t_rc(r * (1 - rt), c * (1 - ct), VCC, V0_RANGE[1], vt[0]),
            t_rc(r * (1 + rt), c * (1 + ct), VCC - 0.1, V0_RANGE[0], vt[2]))
    temp = (t_rc(r * (1 - rt), c * (1 - ct) * 0.85, VCC, V0_RANGE[1], vt[0]),
            t_rc(r * (1 + rt), c * (1 + ct) * 1.15, VCC - 0.1, V0_RANGE[0], vt[2]))
    skew_max = (T_AY[2] + T_BY[2]) - (T_AY[0] + T_BY[0])
    worst = room[0] - skew_max - DRIVER_MATCH_MAX
    return {"vt_plus_5V_interpolated_V": [round(v, 3) for v in vt],
            "t_rc_typ_ns": round(typ, 2), "t_rc_room_range_ns": [round(v, 2) for v in room],
            "t_rc_with_x7r_temperature_ns": [round(v, 2) for v in temp],
            "qsg_rule_ns": round((r + 14) / 13.5, 2),
            "logic_channel_skew_max_ns": round(skew_max, 2), "driver_match_max_ns": DRIVER_MATCH_MAX,
            "worst_case_gate_command_dead_time_ns": round(worst, 2),
            "typical_gate_command_dead_time_ns": round(typ - DRIVER_MATCH_TYP, 2),
            "unbounded_reduction": "turn-off delay of the diode discharge (InBuf output resistance, SDM03U40 forward behaviour); not bounded here",
            "datasheet_limits_guarantee_positive_dead_time": worst > 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-input-logic.json")
    args = ap.parse_args()
    logic = json.loads(LOGIC.read_text(encoding="utf-8"))
    fitted, _ = read_bom(verified("EPC90133BOM.xlsx"))
    verified("EPC90133_Schematic.pdf")
    verified("EPC90133_qsg.pdf")
    bom = [{"ref": k, "transcribed": v, "bom": fitted.get(k, {}).get("part_number"),
            "match": fitted.get(k, {}).get("part_number") == v} for k, v in logic["bom_parts"].items()]
    table = check_function_table(parse_function_table(verified("74LVC1G99.pdf")))
    verified("sn74lvc1g66.pdf")
    qsg = qsg_checks(logic)
    configs = [classify(logic, j630, j640)
               for n1 in range(4) for j630 in itertools.combinations(POSITIONS, n1)
               for n2 in range(4) for j640 in itertools.combinations(POSITIONS, n2)]
    dt = dead_time_bounds(logic)
    l5 = {"driver_por_min_V": DRIVER_POR_MIN, "logic_vcc_min_V": LOGIC_VCC_MIN,
          "logic_valid_at_driver_enable": DRIVER_POR_MIN > LOGIC_VCC_MIN,
          "both_on_at_enable": [c for c in configs if c["kind"].startswith("both on at idle")]}
    l5["both_on_at_enable"] = [{"J630": c["J630"], "J640": c["J640"]} for c in l5["both_on_at_enable"]]
    kinds = {}
    for c in configs:
        kinds.setdefault(c["kind"], []).append({"J630": c["J630"], "J640": c["J640"]})
    checks = {"L1_bom": all(r["match"] for r in bom), "L2_function_table": table["pass"],
              "L3_qsg_settings": all(qsg.values()), "L5_logic_valid_at_driver_enable": l5["logic_valid_at_driver_enable"]}
    report = {
        "schema": "epc90133-input-logic/1",
        "scope": "Static logic of the transcribed input path and datasheet-limit dead-time arithmetic; no timing simulation, no PWM-source behaviour, not a measurement.",
        "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "transcription_sha256": hashlib.sha256(LOGIC.read_bytes()).hexdigest(),
        "checks": checks, "outcome": "pass" if all(checks.values()) else "fail",
        "L1_bom": bom, "L2_function_table": table, "L3_qsg_settings": qsg, "L4_dead_time": dt, "L5_power_up": l5,
        "configurations_by_kind": kinds, "configurations": configs,
    }
    args.output.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"outcome": report["outcome"], "checks": checks, "L4": dt,
                      "kinds": {k: len(v) for k, v in kinds.items()}}, indent=1))


if __name__ == "__main__":
    main()
