#!/usr/bin/env python3
"""Track R step 2a: which side each EPC90133 part sits on, and which mask opening each of its pads uses.

Plan: plans/layout-round-2-plan.md, "Parallel track R", step 2. Sources: the layout PDF in the Gerber package
(Gerbers/EPC90133_B5253_Rev2_0_Layout.PDF, Altium export) and the Gerbers. The PDF carries hidden text tags
PA<ref><pin> (pin zero-padded; the bookmark tree's Components lists give the real pin names, which resolves
ambiguous splits such as C61 pin 01 / C610 pin 1) whose boxes approximate each pad's extent (about 0.2-0.5 mm), and
a bookmark netlist (net name -> pads). Page scale: the board outline rectangle 3.861..477.607 pt is 50.8 mm.

Exploration before this declaration (6 October 2026; scripts kept in the git-ignored runs/trackR-step2-exploration/):
tag-box overlap with mask or paste, translation fits, paste containment with a shift and designator silkscreen ink
each misplaced some parts in the stacked power stage (Ci on top, Cm directly below). A pad-size test on the mask
openings placed all 19 anchors correctly but placed R80 on the bottom by 0.003 mm, against the gate-loop
analysis. Netlist consistency on our copper connectivity (read_epc90133_geometry) put R80 and U80 on top.

Side rule (declared 6 October 2026 before the first run), applied per part in this order:
  1. net evidence: with every other part at its rule-2 side, place the part on each side, snap each pad to its
     best mask opening (size and position match within 0.6 mm), read the copper island under it (GTL/GBL, joined
     through vias), and count pads that land on the island holding most of the same net's other pads. If one side
     scores higher, take it;
  2. otherwise the mask-size test (mean over pads of |width diff| + |height diff| + centre distance to the best
     mask opening), if the two sides differ by at least 0.05 mm; for a part with paste openings the paste-size test
     must not disagree, otherwise it is flagged;
  3. otherwise an anchor established by earlier declared scripts: Ci1-7 top and Cm1-10 bottom
     (scripts/epc90133_power_loop.py), Q1, Q2, U80 and R80-R83 top (power-loop and gate-loop scripts);
  4. a plated-through part whose mask openings are identical on both sides (connectors, mounting holes, fiducials
     without paste) gets the side with more silkscreen ink in its designator box, marked side_cosmetic: its side
     changes no copper, mask or paste;
  5. anything left is 'undecided' and fails S2.
Checks:
  S1 every pad in the bookmark Components lists is matched to a PDF tag;
  S2 every part gets a side from rules 1-4, and no part is flagged under rule 2;
  S3 with the final sides, every net with at least two pads on copper has all of them on one copper island;
  S4 every anchor in rule 3 ends on its anchor side, whichever rule decided it;
  S5 every non-cosmetic pad is matched to a mask opening on its part's side, and no opening serves two parts.
Outputs: the per-part sides and per-pad opening centres are EPC-derived, so they go to the git-ignored
vendor/epc/epc90133/reconstruction/parts-sides.json; the committed report holds counts, check results and the list
of parts per rule (designators only).
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import sys

import fitz
import numpy as np
import shapely
from shapely.geometry import box as sbox
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from circuit_tools.gerber import load_layer
from read_epc90133_geometry import GERBERS, PREFIX, load_board
from epc90133_reconstruct import OUT, layer_geometry, polygons

PT_PER_MM = (477.607 - 3.861) / 50.8
X0, Y0 = 3.861, 3.864
SNAP_MM, SIZE_MARGIN_MM = 0.6, 0.05
ANCHORS = {**{f"Ci{i}": "top" for i in range(1, 8)}, **{f"Cm{i}": "bot" for i in range(1, 11)},
           **{r: "top" for r in ("Q1", "Q2", "U80", "R80", "R81", "R82", "R83")}}
COPPER = {"top": "GTL", "bot": "GBL"}


def to_mm(x, y):
    return (x - X0) / PT_PER_MM, 50.8 - (y - Y0) / PT_PER_MM


def read_pdf():
    doc = fitz.open(str(GERBERS / f"{PREFIX}Layout.PDF"))
    cur = sec = net = None
    pins, nets = collections.defaultdict(set), {}
    for lv, title, _page, _dest in doc.get_toc(simple=False):
        if lv == 3:
            cur = title
        elif lv == 4:
            sec = title
        elif cur == "Top Layer" and sec == "Components" and lv == 6:
            ref, _, pin = title.rpartition("-")
            pins[ref].add(pin)
        elif cur == "Top Layer" and sec == "Nets" and lv == 5:
            net = title
            nets[net] = []
        elif cur == "Top Layer" and sec == "Nets" and lv == 6:
            nets[net].append(title)
    lookup = {}
    for ref, ps in pins.items():
        for pin in ps:
            for key in {pin.zfill(2), "0" + pin}:
                lookup.setdefault("PA" + ref + key, (ref, pin))
    pads, designator = collections.defaultdict(dict), {}
    for w in doc[0].get_text("words"):
        (x0, y1), (x1, y0) = to_mm(w[0], w[1]), to_mm(w[2], w[3])
        if w[4] in lookup:
            ref, pin = lookup[w[4]]
            pads[ref][pin] = sbox(x0, y0, x1, y1)
        elif w[4].startswith("CO"):
            designator[w[4][2:]] = sbox(x0, y0, x1, y1)
    return pins, nets, pads, designator


class Openings:
    def __init__(self, ext):
        self.g = polygons(layer_geometry(load_layer(GERBERS / f"{PREFIX}Gerbers.{ext}")))
        self.tree = STRtree(self.g)

    def best(self, tag):
        """(error mm, index) of the opening best matching the tag box in size and position, or None."""
        c = tag.centroid
        bw, bh = tag.bounds[2] - tag.bounds[0], tag.bounds[3] - tag.bounds[1]
        out = None
        for i in self.tree.query(c.buffer(SNAP_MM)):
            x0, y0, x1, y1 = self.g[i].bounds
            e = abs((x1 - x0) - bw) + abs((y1 - y0) - bh) + c.distance(self.g[i].centroid)
            out = (e, int(i)) if out is None or e < out[0] else out
        return out


def size_score(pp, op):
    es = [op.best(b) for b in pp.values()]
    return None if any(e is None for e in es) else float(np.mean([e[0] for e in es]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "results/gan/epc90133-reconstruct-sides.json")
    args = ap.parse_args()
    pins, nets, pads, designator = read_pdf()
    mask = {"top": Openings("GTS"), "bot": Openings("GBS")}
    paste = {"top": Openings("GTP"), "bot": Openings("GBP")}
    silk = {s: shapely.union_all([g for g in polygons(layer_geometry(load_layer(GERBERS / f"{PREFIX}Gerbers.{e}")))])
            for s, e in (("top", "GTO"), ("bot", "GBO"))}
    board = load_board()

    def island(ref, pin, side):
        o = mask[side].best(pads[ref][pin])
        if o is None:
            return None
        p = mask[side].g[o[1]].representative_point()
        e = COPPER[side]
        lab = int(board.labels[e][board.pixel(p.x, p.y)])
        return board.find((e, lab)) if lab else None

    isl = {(r, pin, s): island(r, pin, s) for r in pads for pin in pads[r] for s in ("top", "bot")}
    padnet = {p: n for n, pl in nets.items() for p in pl}

    # rule 2 first, as the background assignment for rule 1
    size = {r: {s: size_score(pp, mask[s]) for s in ("top", "bot")} for r, pp in pads.items()}
    psize = {r: {s: size_score(pp, paste[s]) for s in ("top", "bot")} for r, pp in pads.items()}

    def size_side(r, scores, margin):
        t, b = scores[r]["top"], scores[r]["bot"]
        if t is None and b is None:
            return None
        if b is None or (t is not None and b - t >= margin):
            return "top"
        if t is None or t - b >= margin:
            return "bot"
        return None

    background = {r: size_side(r, size, 0.0) for r in pads}

    def net_score(r, side):
        ok = tot = 0
        for pin in pads[r]:
            n = padnet.get(f"{r}-{pin}")
            mine = isl[(r, pin, side)]
            if not n or mine is None:
                continue
            others = [isl[(rr, pp, background[rr])] for rr, _, pp in (q.rpartition("-") for q in nets[n])
                      if rr != r and rr in pads and background.get(rr) and isl.get((rr, pp, background[rr]))]
            if others:
                tot += 1
                ok += mine == collections.Counter(others).most_common(1)[0][0]
        return ok, tot

    final, rule, flags = {}, {}, []
    for r in sorted(pads):
        nt, nb = net_score(r, "top"), net_score(r, "bot")
        if nt[0] != nb[0]:
            final[r], rule[r] = ("top" if nt[0] > nb[0] else "bot"), 1
            continue
        s = size_side(r, size, SIZE_MARGIN_MM)
        if s:
            ps = size_side(r, psize, 0.0)
            if ps and ps != s:
                flags.append(r)
            final[r], rule[r] = s, 2
            continue
        if r in ANCHORS:
            final[r], rule[r] = ANCHORS[r], 3
            continue
        same = all(mask["top"].best(b) and mask["bot"].best(b) and
                   mask["top"].g[mask["top"].best(b)[1]].symmetric_difference(
                       mask["bot"].g[mask["bot"].best(b)[1]]).area < 1e-3 for b in pads[r].values())
        no_paste = all(psize[r][s] is None or psize[r][s] > SNAP_MM for s in ("top", "bot"))
        if same and no_paste and r in designator:
            at, ab = (silk[s].intersection(designator[r]).area for s in ("top", "bot"))
            final[r], rule[r] = ("top" if at >= ab else "bot"), 4
            continue
        final[r], rule[r] = "undecided", 5

    # checks
    bookmark_pads = {(r, p) for r, ps in pins.items() for p in ps}
    tagged = {(r, p) for r, pp in pads.items() for p in pp}
    s1 = bookmark_pads <= tagged
    s2 = all(v != "undecided" for v in final.values()) and not flags
    per_net = {}
    for n, pl in nets.items():
        roots = [isl.get((rr, pp, final.get(rr))) for rr, _, pp in (q.rpartition("-") for q in pl)
                 if rr in final and final[rr] in ("top", "bot")]
        roots = [x for x in roots if x is not None]
        if len(roots) >= 2:
            per_net[n] = (collections.Counter(roots).most_common(1)[0][1], len(roots))
    s3 = all(a == b for a, b in per_net.values())
    s4 = all(final.get(r) == s for r, s in ANCHORS.items())
    used, clash, unmatched = {}, [], []
    for r, s in final.items():
        if s not in ("top", "bot") or rule[r] == 4:
            continue
        for pin, b in pads[r].items():
            o = mask[s].best(b)
            if o is None:
                unmatched.append(f"{r}-{pin}")
                continue
            if (s, o[1]) in used and used[(s, o[1])] != r:
                clash.append((r, used[(s, o[1])]))
            used[(s, o[1])] = r
    s5 = not unmatched and not clash
    passed = s1 and s2 and s3 and s4 and s5

    detail = {r: {"side": final[r], "rule": rule[r], "pads": {
        pin: (lambda o: None if o is None else list(mask[final[r]].g[o[1]].centroid.coords[0]))(
            mask[final[r]].best(b)) if final[r] in ("top", "bot") else None for pin, b in pads[r].items()}}
        for r in final}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "parts-sides.json").write_text(json.dumps({"nets": nets, "parts": detail}, indent=1) + "\n",
                                          encoding="utf-8")
    report = {"schema": "epc90133-reconstruct-sides/1", "step": "track R step 2a: part sides and pad openings",
              "passed": passed, "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "parts": len(final), "pads": len(tagged), "bookmark_pads": len(bookmark_pads), "nets": len(nets),
              "checks": {"S1_all_pads_tagged": s1, "S2_all_decided_no_flags": s2, "S3_nets_on_one_island": s3,
                         "S4_anchors": s4, "S5_pads_matched_no_clash": s5},
              "flags_rule2_paste_disagrees": flags, "unmatched_pads": unmatched, "opening_clashes": clash,
              "net_consistency": {n: list(v) for n, v in per_net.items()},
              "by_rule": {k: sorted(r for r in final if rule[r] == k) for k in (1, 2, 3, 4, 5)},
              "top": sorted(r for r, s in final.items() if s == "top"),
              "bottom": sorted(r for r, s in final.items() if s == "bot"),
              "detail_file": "vendor/epc/epc90133/reconstruction/parts-sides.json (git-ignored; EPC derivative)"}
    args.output.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("passed", "parts", "pads", "checks", "flags_rule2_paste_disagrees",
                                             "unmatched_pads", "opening_clashes")}, indent=1))
    print("rules:", {k: len(v) for k, v in report["by_rule"].items()}, "undecided:", report["by_rule"][5])
    print("inconsistent nets:", {n: v for n, v in per_net.items() if v[0] != v[1]})
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
