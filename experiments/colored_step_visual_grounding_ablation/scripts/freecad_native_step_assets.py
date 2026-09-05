"""Create matched renders and a colored STEP directly from one native STEP."""

from __future__ import annotations

import hashlib
import json
import sys
import traceback
from pathlib import Path

import FreeCAD
import FreeCADGui

FreeCADGui.showMainWindow()
import ImportGui  # noqa: E402


PALETTE = [
    (230, 57, 70), (29, 53, 87), (69, 123, 157), (42, 157, 143),
    (233, 196, 106), (244, 162, 97), (231, 111, 81), (131, 56, 236),
    (255, 0, 110), (58, 134, 255), (6, 214, 160), (255, 209, 102),
    (17, 138, 178), (7, 59, 76), (239, 71, 111), (118, 200, 147),
    (255, 183, 3), (33, 158, 188), (142, 202, 230), (251, 133, 0),
    (80, 81, 79), (166, 97, 26), (106, 76, 147), (27, 158, 119),
]
GRAY = (166, 171, 176)
VIEW_METHODS = {
    "front": "viewFront", "rear": "viewRear", "left": "viewLeft",
    "right": "viewRight", "top": "viewTop", "isometric": "viewAxonometric",
}


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def rgb01(rgb):
    return tuple(float(v) / 255.0 for v in rgb)


def set_color(obj, rgb) -> None:
    color = rgb01(rgb)
    view = obj.ViewObject
    view.ShapeColor = color
    material = FreeCAD.Material()
    material.DiffuseColor = (*color, 1.0)
    material.AmbientColor = (*tuple(value * 0.3 for value in color), 1.0)
    material.SpecularColor = (0.18, 0.18, 0.18, 1.0)
    material.Shininess = 30.0
    view.ShapeAppearance = (material,) * max(1, len(obj.Shape.Faces))
    view.setElementColors({"Face": (*color, 1.0)})


def leaf_shapes(doc):
    return [
        obj for obj in doc.Objects
        if obj.TypeId == "Part::Feature"
        and hasattr(obj, "Shape")
        and not obj.Shape.isNull()
        and len(obj.Shape.Faces) > 0
    ]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_view(view, name: str, path: Path) -> None:
    getattr(view, VIEW_METHODS[name])()
    view.fitAll()
    FreeCADGui.updateGui()
    path.parent.mkdir(parents=True, exist_ok=True)
    view.saveImage(str(path), 1400, 1400, "White")


def render_condition(doc, leaves, views, output: Path, colored: bool) -> None:
    for index, obj in enumerate(leaves):
        set_color(obj, PALETTE[index % len(PALETTE)] if colored else GRAY)
        obj.ViewObject.Visibility = True
    doc.recompute()
    view = FreeCADGui.activeDocument().activeView()
    view.setAnimationEnabled(False)
    view.setCameraType("Orthographic")
    for name in views:
        save_view(view, name, output / f"{name}.png")


def render_component_masks(doc, leaves, views, output: Path) -> None:
    view = FreeCADGui.activeDocument().activeView()
    for view_name in views:
        # Freeze full-assembly framing before hiding objects.
        for obj in leaves:
            obj.ViewObject.Visibility = True
        getattr(view, VIEW_METHODS[view_name])()
        view.fitAll()
        FreeCADGui.updateGui()
        for index, target in enumerate(leaves):
            for obj in leaves:
                obj.ViewObject.Visibility = obj is target
            set_color(target, (25, 25, 25))
            FreeCADGui.updateGui()
            path = output / view_name / f"C{index:02d}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            view.saveImage(str(path), 1400, 1400, "White")
    for obj in leaves:
        obj.ViewObject.Visibility = True


def color_entities(path: Path) -> int:
    text = path.read_text(encoding="latin-1", errors="ignore")
    return text.count("COLOUR_RGB")


def main(job_path: Path) -> int:
    job = json.loads(job_path.read_text(encoding="utf-8"))
    result_path = Path(job["result_path"])
    output = Path(job["output_dir"])
    source_step = Path(job["step_path"])
    result = {"case_id": job["case_id"], "status": "FAILURE", "error_type": "", "error": ""}
    source_doc = None
    reopened = None
    try:
        source_doc = FreeCAD.newDocument("NativeStepSource")
        ImportGui.insert(str(source_step), source_doc.Name)
        source_doc.recompute()
        leaves = leaf_shapes(source_doc)
        if not leaves:
            raise RuntimeError("NO_STEP_LEAF_COMPONENTS")
        manifest = []
        for index, obj in enumerate(leaves):
            component_id = f"C{index:02d}"
            obj.addProperty("App::PropertyString", "OracleComponentId", "RobotCAD")
            obj.OracleComponentId = component_id
            manifest.append({
                "component_id": component_id,
                "source_label": obj.Label,
                "color_rgb": list(PALETTE[index % len(PALETTE)]),
                "faces": len(obj.Shape.Faces),
                "solids": len(obj.Shape.Solids),
                "bbox_mm": [obj.Shape.BoundBox.XLength, obj.Shape.BoundBox.YLength, obj.Shape.BoundBox.ZLength],
            })
        write_json(output / "component_manifest.json", {
            "case_id": job["case_id"],
            "source_step": str(source_step),
            "source_step_sha256": sha256(source_step),
            "oracle_input": True,
            "components": manifest,
        })

        views = job["views"]
        render_condition(source_doc, leaves, views, output / "A0_controlled" / "renders", False)
        render_condition(source_doc, leaves, views, output / "A1_color_only" / "renders", True)
        # A2 uses byte-identical images; only the downstream prompt receives a legend.
        a2 = output / "A2_color_legend" / "renders"
        a2.mkdir(parents=True, exist_ok=True)
        for name in views:
            (a2 / f"{name}.png").write_bytes((output / "A1_color_only" / "renders" / f"{name}.png").read_bytes())
        render_component_masks(source_doc, leaves, views, output / "evaluator_masks")

        for index, obj in enumerate(leaves):
            set_color(obj, PALETTE[index % len(PALETTE)])
            obj.ViewObject.Visibility = True
        source_doc.recompute()
        source_doc.saveAs(str(output / "colored_assembly.FCStd"))
        ImportGui.export(leaves, str(output / "colored_assembly.step"))

        reopened = FreeCAD.newDocument("NativeStepReopened")
        ImportGui.insert(str(output / "colored_assembly.step"), reopened.Name)
        reopened.recompute()
        FreeCADGui.activeDocument().activeView().viewAxonometric()
        FreeCADGui.activeDocument().activeView().fitAll()
        FreeCADGui.updateGui()
        FreeCADGui.activeDocument().activeView().saveImage(str(output / "colored_step_reopen_preview.png"), 1400, 1400, "White")
        reopened_leaves = leaf_shapes(reopened)
        result.update({
            "status": "SUCCESS",
            "source_step_sha256": sha256(source_step),
            "leaf_components": len(leaves),
            "source_solids": sum(len(obj.Shape.Solids) for obj in leaves),
            "expected_solids": int(job["expected_solids"]),
            "reopened_leaf_components": len(reopened_leaves),
            "reopened_solids": sum(len(obj.Shape.Solids) for obj in reopened_leaves),
            "step_color_entities": color_entities(output / "colored_assembly.step"),
            "views": len(views),
            "fcstd_exists": (output / "colored_assembly.FCStd").is_file(),
            "colored_step_exists": (output / "colored_assembly.step").is_file(),
        })
    except Exception as exc:
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
        result["traceback"] = traceback.format_exc()
    finally:
        write_json(result_path, result)
        if reopened is not None:
            FreeCAD.closeDocument(reopened.Name)
        if source_doc is not None:
            FreeCAD.closeDocument(source_doc.Name)
        FreeCADGui.getMainWindow().close()
    return 0 if result["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[-1]).resolve()))

