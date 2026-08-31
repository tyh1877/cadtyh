"""Run FreeCAD native operation smoke tests for freecad_backend_pilot.

This script must be executed with FreeCADCmd, not the repository .venv Python:

    D:\software\freeCAD\install\bin\freecadcmd.exe freecad_backend_pilot\scripts\run_operation_smokes_freecad.py

It intentionally does not use silent fallback. If a requested native operation
cannot be created, the row is recorded as a failure.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
import traceback
from pathlib import Path

import FreeCAD  # type: ignore
import Import  # type: ignore
import Mesh  # type: ignore
import Part  # type: ignore

try:
    import Draft  # type: ignore
except Exception:  # pragma: no cover - recorded by smoke test if needed
    Draft = None


if "__file__" in globals():
    ROOT = Path(__file__).resolve().parents[2]
else:
    ROOT = Path(os.environ.get("ROBOTCAD_REPO_ROOT", os.getcwd())).resolve()
PILOT = ROOT / "freecad_backend_pilot"
RESULTS = PILOT / "results"
ARTIFACTS = PILOT / "artifacts" / "smoke"
LOGS = PILOT / "logs" / "smoke"


def vector(values):
    return FreeCAD.Vector(float(values[0]), float(values[1]), float(values[2]))


def add_shape(doc, name, shape):
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    return obj


def rectangle_face(x0, y0, x1, y1, z=0.0):
    pts = [
        FreeCAD.Vector(x0, y0, z),
        FreeCAD.Vector(x1, y0, z),
        FreeCAD.Vector(x1, y1, z),
        FreeCAD.Vector(x0, y1, z),
        FreeCAD.Vector(x0, y0, z),
    ]
    return Part.Face(Part.makePolygon(pts))


def circle_wire(radius, center=(0, 0, 0), normal=(0, 0, 1)):
    edge = Part.makeCircle(float(radius), vector(center), vector(normal))
    return Part.Wire([edge])


def circle_face(radius, center=(0, 0, 0), normal=(0, 0, 1)):
    return Part.Face(circle_wire(radius, center, normal))


def create_revolve(doc):
    profile = add_shape(doc, "revolve_profile", rectangle_face(6, 0, 12, 18))
    obj = doc.addObject("Part::Revolution", "native_revolve")
    obj.Source = profile
    obj.Base = FreeCAD.Vector(0, 0, 0)
    obj.Axis = FreeCAD.Vector(0, 1, 0)
    obj.Angle = 360
    return obj


def create_loft(doc):
    s1 = add_shape(doc, "loft_section_1", circle_wire(5, (0, 0, 0)))
    s2 = add_shape(doc, "loft_section_2", circle_wire(9, (0, 0, 20)))
    s3 = add_shape(doc, "loft_section_3", circle_wire(4, (0, 0, 35)))
    obj = doc.addObject("Part::Loft", "native_loft")
    obj.Sections = [s1, s2, s3]
    obj.Solid = True
    obj.Ruled = False
    return obj


def create_sweep(doc):
    profile = add_shape(doc, "sweep_profile", circle_wire(2.0, (0, 0, 0), (1, 0, 0)))
    path = add_shape(
        doc,
        "sweep_path",
        Part.Wire(
            [
                Part.makeLine(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(20, 0, 0)),
                Part.makeLine(FreeCAD.Vector(20, 0, 0), FreeCAD.Vector(30, 10, 0)),
            ]
        ),
    )
    obj = doc.addObject("Part::Sweep", "native_sweep")
    obj.Sections = [profile]
    obj.Spine = path
    obj.Solid = True
    obj.Frenet = False
    return obj


def create_shell(doc):
    box = doc.addObject("Part::Box", "shell_base_box")
    box.Length = 30
    box.Width = 20
    box.Height = 15
    doc.recompute()
    obj = doc.addObject("Part::Thickness", "native_shell")
    obj.Value = 1.5
    obj.Mode = "Skin"
    obj.Join = "Arc"
    obj.Faces = (box, ["Face6"])
    return obj


def create_boolean_union(doc):
    box = doc.addObject("Part::Box", "union_box")
    box.Length = 20
    box.Width = 12
    box.Height = 10
    cyl = doc.addObject("Part::Cylinder", "union_cylinder")
    cyl.Radius = 5
    cyl.Height = 20
    cyl.Placement.Base = FreeCAD.Vector(10, 6, 0)
    doc.recompute()
    obj = doc.addObject("Part::Fuse", "native_boolean_union")
    obj.Base = box
    obj.Tool = cyl
    return obj


def create_boolean_cut(doc):
    box = doc.addObject("Part::Box", "cut_box")
    box.Length = 25
    box.Width = 18
    box.Height = 12
    cyl = doc.addObject("Part::Cylinder", "cut_cylinder")
    cyl.Radius = 4
    cyl.Height = 30
    cyl.Placement.Base = FreeCAD.Vector(12, 9, -5)
    doc.recompute()
    obj = doc.addObject("Part::Cut", "native_boolean_cut")
    obj.Base = box
    obj.Tool = cyl
    return obj


def create_fillet(doc):
    box = doc.addObject("Part::Box", "fillet_base_box")
    box.Length = 25
    box.Width = 16
    box.Height = 12
    doc.recompute()
    obj = doc.addObject("Part::Fillet", "native_fillet")
    obj.Base = box
    obj.Edges = [(1, 1.5, 1.5), (2, 1.5, 1.5)]
    return obj


def create_chamfer(doc):
    box = doc.addObject("Part::Box", "chamfer_base_box")
    box.Length = 25
    box.Width = 16
    box.Height = 12
    doc.recompute()
    obj = doc.addObject("Part::Chamfer", "native_chamfer")
    obj.Base = box
    obj.Edges = [(1, 1.2, 1.2), (2, 1.2, 1.2)]
    return obj


def create_pattern(doc):
    if Draft is None:
        raise RuntimeError("Draft module unavailable; cannot create native Draft array")
    cyl = doc.addObject("Part::Cylinder", "pattern_seed")
    cyl.Radius = 2
    cyl.Height = 5
    doc.recompute()
    obj = Draft.make_array(cyl, FreeCAD.Vector(8, 0, 0), FreeCAD.Vector(0, 8, 0), 4, 1)
    obj.Label = "native_pattern_array"
    return obj


def create_mirror(doc):
    box = doc.addObject("Part::Box", "mirror_seed")
    box.Length = 10
    box.Width = 6
    box.Height = 5
    box.Placement.Base = FreeCAD.Vector(8, 0, 0)
    doc.recompute()
    obj = doc.addObject("Part::Mirroring", "native_mirror")
    obj.Source = box
    obj.Base = FreeCAD.Vector(0, 0, 0)
    obj.Normal = FreeCAD.Vector(1, 0, 0)
    return obj


SMOKES = [
    ("Revolve", "revolve", create_revolve, "Part::Revolution"),
    ("Loft", "loft", create_loft, "Part::Loft"),
    ("Sweep / Pipe", "sweep", create_sweep, "Part::Sweep"),
    ("Shell / Thickness", "shell", create_shell, "Part::Thickness"),
    ("Boolean Union", "boolean_union", create_boolean_union, "Part::Fuse"),
    ("Boolean Cut", "boolean_cut", create_boolean_cut, "Part::Cut"),
    ("Fillet", "fillet", create_fillet, "Part::Fillet"),
    ("Chamfer", "chamfer", create_chamfer, "Part::Chamfer"),
    ("Pattern", "pattern", create_pattern, "Draft::Array"),
    ("Mirror", "mirror", create_mirror, "Part::Mirroring"),
]


def export_outputs(doc, obj, out_base):
    fcstd = out_base.with_suffix(".FCStd")
    step = out_base.with_suffix(".step")
    stl = out_base.with_suffix(".stl")
    doc.saveAs(str(fcstd))
    Import.export([obj], str(step))
    Mesh.export([obj], str(stl))
    return fcstd, step, stl


def object_type_matches(obj, expected_type):
    if expected_type == "Draft::Array":
        return obj.TypeId == "Part::FeaturePython" and obj.Proxy.__class__.__name__.lower().endswith("array")
    return obj.TypeId == expected_type


def shape_stats(obj):
    shape = obj.Shape
    bbox = shape.BoundBox
    return {
        "valid": bool(shape.isValid()),
        "volume": float(shape.Volume),
        "bbox": [bbox.XLength, bbox.YLength, bbox.ZLength],
        "solids": len(shape.Solids),
        "faces": len(shape.Faces),
        "edges": len(shape.Edges),
    }


def run_one(operation, requested_type, creator, expected_type):
    safe_name = requested_type.replace("/", "_").replace(" ", "_")
    out_dir = ARTIFACTS / safe_name
    log_dir = LOGS / safe_name
    out_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    row = {
        "operation": operation,
        "requested_type": requested_type,
        "executed_type": "",
        "semantic_match": False,
        "recompute_success": False,
        "save_success": False,
        "reopen_success": False,
        "step_success": False,
        "stl_success": False,
        "failure_stage": "",
        "failure_reason": "",
    }
    log = {
        "operation": operation,
        "requested_type": requested_type,
        "expected_native_type": expected_type,
        "fallback_used": False,
        "events": [],
    }
    doc = None
    try:
        start = time.time()
        doc = FreeCAD.newDocument(f"smoke_{requested_type}")
        obj = creator(doc)
        obj_name = obj.Name
        row["executed_type"] = obj.TypeId
        row["semantic_match"] = object_type_matches(obj, expected_type)
        if not row["semantic_match"]:
            row["failure_stage"] = "SEMANTIC_EXECUTION_FAILURE"
            row["failure_reason"] = f"expected {expected_type}, got {obj.TypeId}"
            return row, log
        doc.recompute()
        row["recompute_success"] = True
        stats = shape_stats(obj)
        if not stats["valid"] or stats["faces"] == 0:
            row["failure_stage"] = "GEOMETRY_INVALID"
            row["failure_reason"] = json.dumps(stats)
            return row, log
        fcstd, step, stl = export_outputs(doc, obj, out_dir / "model")
        row["save_success"] = fcstd.exists()
        row["step_success"] = step.exists() and step.stat().st_size > 0
        row["stl_success"] = stl.exists() and stl.stat().st_size > 0
        FreeCAD.closeDocument(doc.Name)
        doc = None
        reopened = FreeCAD.openDocument(str(fcstd))
        reopened_obj = reopened.getObject(obj_name)
        row["reopen_success"] = reopened_obj is not None and object_type_matches(reopened_obj, expected_type)
        reopened_stats = shape_stats(reopened_obj) if reopened_obj is not None else None
        FreeCAD.closeDocument(reopened.Name)
        log.update(
            {
                "native_object_name": obj_name,
                "native_object_type": row["executed_type"],
                "shape_stats": stats,
                "reopened_shape_stats": reopened_stats,
                "elapsed_seconds": time.time() - start,
                "success": all(
                    [
                        row["semantic_match"],
                        row["recompute_success"],
                        row["save_success"],
                        row["reopen_success"],
                        row["step_success"],
                        row["stl_success"],
                    ]
                ),
            }
        )
        if not log["success"] and not row["failure_stage"]:
            row["failure_stage"] = "POSTCHECK_FAILURE"
            row["failure_reason"] = "one or more save/reopen/export checks failed"
        if log["success"]:
            row["failure_stage"] = ""
            row["failure_reason"] = ""
    except Exception:
        if not row["failure_stage"]:
            row["failure_stage"] = "NATIVE_OPERATION_FAILURE"
        row["failure_reason"] = traceback.format_exc()
        log["success"] = False
        log["traceback"] = row["failure_reason"]
    finally:
        if doc is not None:
            try:
                FreeCAD.closeDocument(doc.Name)
            except Exception:
                pass
        (log_dir / "execution_log.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
    return row, log


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    rows = []
    logs = []
    for smoke in SMOKES:
        row, log = run_one(*smoke)
        rows.append(row)
        logs.append(log)
    fields = [
        "operation",
        "requested_type",
        "executed_type",
        "semantic_match",
        "recompute_success",
        "save_success",
        "reopen_success",
        "step_success",
        "stl_success",
        "failure_stage",
        "failure_reason",
    ]
    with (RESULTS / "operation_smoke_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "freecad_version": FreeCAD.Version(),
        "operation_total": len(rows),
        "semantic_match": sum(str(r["semantic_match"]) == "True" for r in rows),
        "recompute_success": sum(str(r["recompute_success"]) == "True" for r in rows),
        "save_success": sum(str(r["save_success"]) == "True" for r in rows),
        "reopen_success": sum(str(r["reopen_success"]) == "True" for r in rows),
        "step_success": sum(str(r["step_success"]) == "True" for r in rows),
        "stl_success": sum(str(r["stl_success"]) == "True" for r in rows),
        "silent_fallback_count": 0,
        "rows": rows,
    }
    (RESULTS / "operation_smoke_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
