#!/usr/bin/env python3
"""Post-hoc validity assessment of the stored FasterCap case H report (audit at 75d6f35, 2 October 2026).

The stored report (results/gan/fastercap-board3d-check.json, schema /1) predates the matrix-validity gate now in
scripts/fastercap_board3d_check.py. Its declared verdict (all_pass false: H1/H2 not evaluated, H3 15.8 %) stands and
the report is not rewritten. This assessment, bound to the report's sha256, applies the gate to every stored matrix
and records the disposition that the prose already gave: the 3D Maxwell matrices are unphysical, so the derived
C' values (about 178 pF/m) are not accuracy results. It reruns no solver. Besides itself and the report, it binds
by sha256 the gate it imports (scripts/fastercap_board3d_check.py) and that module's own imported helpers
(scripts/fastercap_known_answer.py).

    python scripts/assess_fastercap_board3d.py   # results/gan/fastercap-board3d-assessment.json
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from fastercap_board3d_check import DEPENDENCIES, REL_TOL, dependency_hashes, matrix_validity  # noqa: E402

REPORT = ROOT / "results/gan/fastercap-board3d-check.json"
OUTPUT = ROOT / "results/gan/fastercap-board3d-assessment.json"


def assess(rep):
    matrices = {f"2D -a{a}": r["matrix"] for a, r in rep["two_d"].items()}
    matrices.update({f"3D L={k} -a{a}": v["matrix"] for a, r in rep["three_d"].items() for k, v in r.items()
                     if isinstance(v, dict) and "matrix" in v})
    validity = {k: matrix_validity(m) for k, m in matrices.items()}
    invalid_3d = [k for k, v in validity.items() if v and k.startswith("3D")]
    all_3d = [k for k in validity if k.startswith("3D")]
    return {"matrix_validity": validity,
            "invalid_matrices": [k for k, v in validity.items() if v],
            "disposition": {
                "declared_verdict": "failed (unchanged)" if rep.get("all_pass") is False else rep.get("all_pass"),
                "three_d": "invalid" if all_3d and invalid_3d == all_3d else
                           ("partly invalid" if invalid_3d else "valid"),
                "derived_C_per_m_usable": not invalid_3d,
                "two_d": "valid" if not any(v for k, v in validity.items() if k.startswith("2D")) else "invalid"}}


def main():
    raw = REPORT.read_bytes()
    rep = json.loads(raw)
    out = {"schema": "fastercap-board3d-assessment/1", "date": "2026-10-02",
           "basis": "audit at 75d6f35; post-hoc, not a declared check; the report is not rewritten",
           "report": REPORT.relative_to(ROOT).as_posix(), "report_sha256": hashlib.sha256(raw).hexdigest(),
           "report_schema": rep.get("schema"), "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "dependencies_sha256": dependency_hashes(("scripts/fastercap_board3d_check.py", *DEPENDENCIES)),
           "gate_rel_tol": REL_TOL, **assess(rep)}
    OUTPUT.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out["disposition"], indent=1))


if __name__ == "__main__":
    main()
