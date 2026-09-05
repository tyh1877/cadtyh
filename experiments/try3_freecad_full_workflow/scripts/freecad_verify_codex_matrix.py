"""Reopen every formal FCStd/STEP/STL artifact inside FreeCAD."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import FreeCAD  # type: ignore
import Mesh  # type: ignore
import Part  # type: ignore


def main(job_path: Path) -> int:
    job = json.loads(job_path.read_text(encoding="utf-8"))
    rows = []
    for item in job["items"]:
        doc = None
        row = {"case_id": item["case_id"], "version": item["version"], "status": "FAILURE", "expected_components": item["expected_components"], "reopened_components": 0, "valid_components": 0, "step_shape_valid": False, "stl_facets": 0, "error": ""}
        try:
            doc = FreeCAD.openDocument(item["fcstd"])
            components = [obj for obj in doc.Objects if hasattr(obj, "RobotCADLinkId")]
            row["reopened_components"] = len(components)
            row["valid_components"] = sum(hasattr(obj, "Shape") and not obj.Shape.isNull() and obj.Shape.isValid() for obj in components)
            step_shape = Part.read(item["step"])
            row["step_shape_valid"] = not step_shape.isNull() and step_shape.isValid()
            mesh = Mesh.Mesh(item["stl"])
            row["stl_facets"] = int(mesh.CountFacets)
            if row["reopened_components"] != item["expected_components"] or row["valid_components"] != item["expected_components"] or not row["step_shape_valid"] or row["stl_facets"] <= 0:
                raise RuntimeError("reopen validation mismatch")
            row["status"] = "PASS"
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            if doc is not None:
                FreeCAD.closeDocument(doc.Name)
        rows.append(row)
    output = Path(job["result_path"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(rows), "passes": sum(row["status"] == "PASS" for row in rows)}, indent=2))
    return 0 if all(row["status"] == "PASS" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[-1]).resolve()))

