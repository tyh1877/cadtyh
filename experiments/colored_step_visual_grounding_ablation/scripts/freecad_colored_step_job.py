"""Run one colored faceted-STEP job inside the FreeCAD GUI Python runtime.

This helper intentionally uses ImportGui because FreeCADCmd cannot load the GUI
STEP exporter and therefore cannot preserve presentation colors reliably.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

import FreeCAD
import FreeCADGui
import Mesh
import Part

# The bundled FreeCAD Python runtime starts without a GUI. Initializing the GUI
# here makes ViewObject colors and the color-aware STEP exporter available while
# still allowing the orchestrator to run the window hidden.
FreeCADGui.showMainWindow()
import ImportGui  # noqa: E402


def rgb01(values):
    return tuple(float(value) / 255.0 for value in values)


def color_summary(obj):
    view = obj.ViewObject
    shape_color = list(getattr(view, "ShapeColor", ()))
    diffuse = getattr(view, "DiffuseColor", [])
    first_diffuse = list(diffuse[0]) if diffuse else []
    appearances = getattr(view, "ShapeAppearance", ())
    first_appearance = list(appearances[0].DiffuseColor) if appearances else []
    element_colors = getattr(view, "getElementColors", lambda: {})()
    return {
        "name": obj.Name,
        "label": obj.Label,
        "type_id": obj.TypeId,
        "shape_color": shape_color,
        "first_diffuse_color": first_diffuse,
        "first_shape_appearance": first_appearance,
        "element_color_count": len(element_colors),
        "first_element_color": list(next(iter(element_colors.values()))) if element_colors else [],
        "face_count": len(getattr(obj.Shape, "Faces", [])) if hasattr(obj, "Shape") else 0,
        "solid_count": len(getattr(obj.Shape, "Solids", [])) if hasattr(obj, "Shape") else 0,
        "shell_count": len(getattr(obj.Shape, "Shells", [])) if hasattr(obj, "Shape") else 0,
    }


def run(job_path: Path) -> int:
    job = json.loads(job_path.read_text(encoding="utf-8"))
    result_path = Path(job["result_path"])
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "case_id": job["case_id"],
        "status": "FAILURE",
        "source_object_count": 0,
        "step_object_count": 0,
        "source_colors": [],
        "reopened_colors": [],
        "error_type": "",
        "error": "",
    }
    source_doc = None
    reopened_doc = None
    try:
        source_doc = FreeCAD.newDocument("ColoredAssemblySource")
        objects = []
        for index, item in enumerate(job["links"]):
            mesh = Mesh.Mesh(str(item["mesh_path"]))
            shape = Part.Shape()
            shape.makeShapeFromMesh(mesh.Topology, float(job.get("mesh_tolerance", 0.05)))
            converted = []
            for shell in shape.Shells:
                converted.append(Part.makeSolid(shell) if shell.isClosed() else shell)
            if converted:
                shape = converted[0] if len(converted) == 1 else Part.makeCompound(converted)
            obj = source_doc.addObject("Part::Feature", f"Link_{index:03d}")
            obj.Label = str(item["link_id"])
            obj.addProperty("App::PropertyString", "RobotCADLinkId", "RobotCAD")
            obj.RobotCADLinkId = str(item["link_id"])
            obj.Shape = shape
            color = rgb01(item["color_rgb"])
            obj.ViewObject.ShapeColor = color
            obj.ViewObject.DiffuseColor = [color] * len(shape.Faces)
            material = FreeCAD.Material()
            material.DiffuseColor = (*color, 1.0) if len(color) == 3 else color
            material.AmbientColor = (*tuple(value * 0.3 for value in color), 1.0)
            material.SpecularColor = (0.2, 0.2, 0.2, 1.0)
            material.Shininess = 35.0
            obj.ViewObject.ShapeAppearance = (material,) * len(shape.Faces)
            obj.ViewObject.setElementColors({"Face": color})
            obj.ViewObject.LineColor = tuple(max(0.0, value * 0.45) for value in color)
            objects.append(obj)
        source_doc.recompute()
        result["source_object_count"] = len(objects)
        result["source_colors"] = [color_summary(obj) for obj in objects]
        source_doc.saveAs(str(job["fcstd_path"]))
        ImportGui.export(objects, str(job["step_path"]))

        reopened_doc = FreeCAD.newDocument("ColoredAssemblyReopened")
        ImportGui.insert(str(job["step_path"]), reopened_doc.Name)
        reopened_doc.recompute()
        FreeCADGui.activeDocument().activeView().viewAxonometric()
        FreeCADGui.activeDocument().activeView().fitAll()
        FreeCADGui.updateGui()
        if job.get("step_preview_path"):
            FreeCADGui.activeDocument().activeView().saveImage(str(job["step_preview_path"]), 1200, 900, "White")
        reopened = [obj for obj in reopened_doc.Objects if hasattr(obj, "Shape") and not obj.Shape.isNull()]
        result["step_object_count"] = len(reopened)
        result["reopened_colors"] = [color_summary(obj) for obj in reopened]
        result["fcstd_exists"] = Path(job["fcstd_path"]).is_file()
        result["step_exists"] = Path(job["step_path"]).is_file()
        result["status"] = "SUCCESS"
    except Exception as exc:
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
        result["traceback"] = traceback.format_exc()
    finally:
        result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        if reopened_doc is not None:
            FreeCAD.closeDocument(reopened_doc.Name)
        if source_doc is not None:
            FreeCAD.closeDocument(source_doc.Name)
    return 0 if result["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: freecad_colored_step_job.py JOB_JSON")
    code = run(Path(sys.argv[-1]).resolve())
    FreeCADGui.getMainWindow().close()
    raise SystemExit(code)
