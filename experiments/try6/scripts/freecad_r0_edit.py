"""FreeCAD child process: one independent edit of the R0 baseline FCStd."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import FreeCAD as App
import Mesh
import Part


def shape_signature(obj, output: Path):
    shape = obj.Shape
    output.mkdir(parents=True, exist_ok=True)
    brep = output / f"{obj.Name}.brep"
    shape.exportBrep(str(brep))
    box = shape.BoundBox
    return {"brep_sha256": hashlib.sha256(brep.read_bytes()).hexdigest(), "volume_mm3": float(shape.Volume),
            "bbox_mm": [float(box.XMin), float(box.YMin), float(box.ZMin), float(box.XMax), float(box.YMax), float(box.ZMax)],
            "solids": len(shape.Solids), "valid": not shape.isNull() and shape.isValid()}


def run(job):
    output = Path(job["output"])
    output.mkdir(parents=True, exist_ok=True)
    doc = App.openDocument(job["baseline_fcstd"])
    doc.recompute()
    sheet = doc.getObject("ParameterTable")
    if sheet is None: raise RuntimeError("missing ParameterTable")
    protected_names = ["FrozenProximalBoreTool", "FrozenMatingEnvelopeTool", "FrozenScaffold"]
    before = {name: shape_signature(doc.getObject(name), output / "before") for name in protected_names}
    old = float(job["old_value_mm"])
    new = float(job["new_value_mm"])
    parameter = job["parameter"]
    if abs(float(str(sheet.get(parameter)).split()[0]) - old) > 1e-6:
        raise RuntimeError("baseline parameter value differs from frozen edit protocol")
    cell = next(f"B{i}" for i in range(1, 10) if sheet.get(f"A{i}") == parameter)
    sheet.set(cell, f"{new} mm")
    doc.recompute()
    names = ["MainHousingPad", "VisibleRecessPocket", "ProfileTransitionLoft", "HousingWithTransition", "FrozenProximalBore", "FrozenMatingEnvelopeCut", "RigidGroup"]
    feature_tree = []
    for name in names:
        obj = doc.getObject(name)
        if obj is None: raise RuntimeError(f"missing feature {name}")
        state = {"name": name, "error_state": str(obj.State), "valid": not obj.Shape.isNull() and obj.Shape.isValid(), "solids": len(obj.Shape.Solids)}
        feature_tree.append(state)
    after = {name: shape_signature(doc.getObject(name), output / "after") for name in protected_names}
    invariant = all(before[name] == after[name] for name in protected_names)
    final = doc.getObject("RigidGroup")
    solid_count = len(final.Shape.Solids)
    final_volume = float(final.Shape.Volume)
    cad_valid = all(item["valid"] for item in feature_tree) and solid_count == 1
    doc.saveAs(str(output / "edited.FCStd"))
    Part.export([final], str(output / "edited.step"))
    Mesh.export([final], str(output / "edited.stl"))
    App.closeDocument(doc.Name)
    reopened = App.openDocument(str(output / "edited.FCStd"))
    reopened.recompute()
    reopened_final = reopened.getObject("RigidGroup")
    reopen_valid = reopened_final is not None and not reopened_final.Shape.isNull() and reopened_final.Shape.isValid() and len(reopened_final.Shape.Solids) == 1
    App.closeDocument(reopened.Name)
    result = {"edit_id": job["edit_id"], "parameter": parameter, "old_value_mm": old, "new_value_mm": new,
              "feature_tree": feature_tree, "protected_shape_signatures_before": before, "protected_shape_signatures_after": after,
              "interface_invariant": invariant, "joint_axis_center_invariant": invariant,
              "attachment_anchor_invariant": invariant, "cad_valid": cad_valid, "connected_solid_count": solid_count,
              "final_volume_mm3": final_volume,
              "export_success": all((output / name).is_file() and (output / name).stat().st_size > 0 for name in ("edited.step", "edited.stl")),
              "reopen_valid": reopen_valid}
    result["pass"] = all([invariant, cad_valid, result["export_success"], reopen_valid])
    (output / "edit_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"edit_id": job["edit_id"], "pass": result["pass"], "interface_invariant": invariant, "cad_valid": cad_valid, "reopen_valid": reopen_valid}))
    return result["pass"]


if __name__ == "__main__":
    sys.exit(0 if run(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))) else 2)
