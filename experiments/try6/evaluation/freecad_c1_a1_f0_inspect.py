"""Read-only shape check; never builds or evaluates a new CAD candidate."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import FreeCAD as App

ROOT = Path(__file__).resolve().parents[3]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(job):
    path = ROOT / job["f0_fcstd"]
    doc = App.openDocument(str(path))
    obj = doc.getObject("RigidGroup")
    if obj is None or obj.Shape.isNull():
        raise RuntimeError("frozen F0 RigidGroup missing")
    shape = obj.Shape.copy()
    b = shape.BoundBox
    result = {"f0_fcstd": job["f0_fcstd"], "f0_fcstd_sha256": sha(path),
        "BREP_valid": shape.isValid(), "solid_count": len(shape.Solids),
        "volume_mm3": float(shape.Volume),
        "bbox_mm": [b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax],
        "bbox_x_span_mm": b.XLength, "FreeCAD_version": App.Version(),
        "GT_accessed": False}
    App.closeDocument(doc.Name)
    output = ROOT / job["output"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"valid": result["BREP_valid"], "x_span_mm": result["bbox_x_span_mm"]}))


if __name__ == "__main__":
    main(read(sys.argv[1]))
