"""Read-only bbox/topology inspection of already frozen D1-v3 BREPs."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parents[3]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(job):
    raw = read(ROOT / job["geometry_raw"])
    decomposition = raw["semantic_decomposition"]
    if decomposition["status"] != "PASS":
        raise RuntimeError("no exact semantic decomposition to inspect")
    rows = {}
    for name in ("R_supported", "R_suspect", "R_supported_only", "R_suspect_only", "R_shared"):
        item = decomposition["artifacts"][name]
        path = ROOT / item["path"]
        if sha(path) != item["sha256"]:
            raise RuntimeError("frozen decomposition BREP drift: " + name)
        shape = Part.read(str(path))
        if shape.isNull() or not shape.Solids:
            bounds = None
        else:
            b = shape.BoundBox
            bounds = {"min_mm": [b.XMin, b.YMin, b.ZMin],
                      "max_mm": [b.XMax, b.YMax, b.ZMax],
                      "size_mm": [b.XLength, b.YLength, b.ZLength]}
        rows[name] = {"brep_sha256": item["sha256"], "valid": shape.isValid(),
                      "solid_count": len(shape.Solids), "volume_mm3": float(shape.Volume),
                      "bbox": bounds}
    output = ROOT / job["output"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"FreeCAD_version": App.Version(), "BREP_records": rows},
                                 indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"inspected": len(rows), "supported_bbox": rows["R_supported"]["bbox"]}))


if __name__ == "__main__":
    main(read(sys.argv[1]))
