#!/usr/bin/env python3
"""Cross-check the EPC90133 BOM, Gerber package, stackup, schematic and quick-start guide.

Reads the git-ignored downloads in vendor/epc/epc90133, verifies them against the
checksums in devices/epc/epc90133-sources.json, and reports:

* copper layer count in the Gerber extension report against the stackup;
* reference designators in the layout PDF (Altium "CO<refdes>" component
  tokens) against the fitted and optional BOM lines;
* part labels in the schematic for the parts that set switching behaviour;
* board numbers named by the Gerber files and the quick-start guide.

Findings are document consistency only; they do not identify the physical
board we will test. Requires PyMuPDF, openpyxl and xlrd.
"""
import hashlib
import json
from pathlib import Path
import re
import zipfile

import openpyxl
import pymupdf
import xlrd

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "devices/epc/epc90133-sources.json"
DIR = ROOT / "vendor/epc/epc90133"
OUTPUT = ROOT / "results/gan/epc90133-board-audit.json"
PREFIX = "Gerbers/EPC90133_B5253_Rev2_0_"
SWITCHING_PARTS = ("Q1", "Q2", "U80", "Q60", "R80", "R81", "R82", "R83", "R70", "R75")


def verified(name):
    rec = json.loads(SOURCES.read_text(encoding="utf-8"))
    entry = next(f for f in rec["files"] if f["name"] == name)
    path = ROOT / entry["local_path"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != entry["sha256"]:
        raise SystemExit(f"{path} sha256 {digest} does not match the recorded {entry['sha256']}")
    return path


def read_bom(path):
    ws = openpyxl.load_workbook(path, data_only=True).active
    fitted, optional, section = {}, {}, None
    for row in ws.iter_rows(values_only=True):
        if row[0] == "Item":
            section = fitted if section is None else section
            continue
        if row[0] == "Optional Components":
            section = optional
            continue
        if section is not None and isinstance(row[0], int) and row[2]:
            for ref in str(row[2]).split(","):
                section[ref.strip()] = {"description": row[3], "manufacturer": row[4], "part_number": str(row[5])}
    return fitted, optional


def main():
    bom_path = verified("EPC90133BOM.xlsx")
    gerber_zip = verified("EPC90133 Development Board Gerbers.zip")
    schematic = verified("EPC90133_Schematic.pdf")
    qsg = verified("EPC90133_qsg.pdf")
    fitted, optional = read_bom(bom_path)

    with zipfile.ZipFile(gerber_zip) as z:
        names = z.namelist()
        extrep = z.read(PREFIX + "Gerbers.EXTREP").decode("latin-1")
        layout = pymupdf.open(stream=z.read(PREFIX + "Layout.PDF"), filetype="pdf")
        stack = xlrd.open_workbook(file_contents=z.read(PREFIX + "Stackup.xls")).sheet_by_index(0)
    copper_files = re.findall(r"^\.(GTL|G\d+|GBL)\s+(.+?)\s*$", extrep, re.M)
    stack_rows = [[str(v).strip() for v in stack.row_values(r)] for r in range(stack.nrows)]
    layers = []
    for row in stack_rows:
        cells = [c for c in row if c]
        if len(cells) >= 4 and cells[2] in ("Copper", "FR370-HR", "Solder Resist"):
            layers.append({"name": cells[1], "material": cells[2], "thickness": cells[3],
                           "dielectric_constant": cells[4] if len(cells) > 4 else None})
    height = next((c for row in stack_rows for c in row if c.startswith("Height")), None)
    stack_copper = [l for l in layers if l["material"] == "Copper"]

    layout_refs = set(re.findall(r"\bCO([A-Za-z]+\d+)\b", layout[0].get_text()))
    bom_refs = set(fitted) | set(optional)

    sch_text = " ".join(p.get_text() for p in pymupdf.open(str(schematic)))
    sch_labels = {}
    for ref in SWITCHING_PARTS:
        m = re.search(r"([^\s].{0,40}?)\s" + re.escape(ref) + r"\b", sch_text)
        sch_labels[ref] = m.group(1) if m else None
    qsg_text = " ".join(p.get_text() for p in pymupdf.open(str(qsg)))

    report = {
        "schema": "epc90133-board-audit/1",
        "scope": "Consistency of EPC's published EPC90133 files with each other; not the identity of a physical board.",
        "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "board_numbers": {"gerber_files": sorted({m for n in names for m in re.findall(r"B\d{4}_Rev\d+_\d+", n)}),
                          "quick_start_guide": sorted(set(re.findall(r"PCB#:\s*(B\d{4})", qsg_text)))},
        "copper": {"gerber_copper_layers": [{"extension": e, "description": d} for e, d in copper_files],
                   "stackup_copper_layers": len(stack_copper), "stackup": layers, "stackup_height": height,
                   "consistent": len(copper_files) == len(stack_copper)},
        "reference_designators": {
            "bom_fitted": len(fitted), "bom_optional": len(optional), "layout_components": len(layout_refs),
            "bom_not_in_layout": sorted(bom_refs - layout_refs),
            "layout_not_in_bom": sorted(layout_refs - bom_refs)},
        "switching_parts": {ref: {"bom": fitted.get(ref) or optional.get(ref), "schematic_text_before_ref": sch_labels[ref]}
                            for ref in SWITCHING_PARTS},
        "driver_labels": {"bom": fitted.get("U80", {}).get("part_number"),
                          "schematic": sorted(set(re.findall(r"uP1966\w", sch_text))),
                          "quick_start_guide": sorted(set(re.findall(r"uP1966\w", qsg_text)))},
    }
    OUTPUT.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("board_numbers", "reference_designators", "driver_labels")},
                     indent=1, ensure_ascii=False))
    print("copper consistent:", report["copper"]["consistent"], len(copper_files), "Gerber /",
          len(stack_copper), "stackup;", height)
    for ref, v in report["switching_parts"].items():
        print(f"  {ref}: BOM {v['bom'] and v['bom']['part_number']} | schematic '{v['schematic_text_before_ref']}'")


if __name__ == "__main__":
    main()
