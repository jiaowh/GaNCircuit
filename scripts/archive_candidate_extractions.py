#!/usr/bin/env python3
"""Copy the per-candidate extraction reports from the git-ignored reconstruction export into tracked results.

The reports (numbers only: inductance/resistance matrices, checks, summaries; no geometry) took hours of FastHenry
each and are inputs of the goals switching runs, but lived only on the local disk. Each copy is the original JSON
with absolute local paths made relative to the repository; INDEX records the original's path and SHA-256 (the
identity the switching manifests recorded), so a copy can be traced to the run that used it. Originals are not
changed. Rerun after any new candidate extraction.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / "vendor/epc/epc90133/reconstruction/export"
OUT = ROOT / "results/gan/epc90133-extraction-candidates"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    prefixes = [str(ROOT) + "\\", str(ROOT).replace("\\", "\\\\") + "\\\\", str(ROOT).replace("\\", "/") + "/"]
    index = {}
    for src in sorted(EXPORT.glob("*/extraction/*.json")):
        raw = src.read_bytes()
        text = raw.decode("utf-8")
        for p in prefixes:
            text = text.replace(p, "")
        json.loads(text)  # still valid JSON
        dst = OUT / src.parent.parent.name / src.name
        dst.parent.mkdir(exist_ok=True)
        dst.write_text(text, encoding="utf-8")
        index[dst.relative_to(ROOT).as_posix()] = {"original": src.relative_to(ROOT).as_posix(),
                                                   "original_sha256": hashlib.sha256(raw).hexdigest()}
    (OUT / "INDEX.json").write_text(json.dumps({"note": __doc__.strip().splitlines()[0], "files": index}, indent=1) + "\n",
                                    encoding="utf-8")
    print(len(index), "reports archived")


if __name__ == "__main__":
    main()
