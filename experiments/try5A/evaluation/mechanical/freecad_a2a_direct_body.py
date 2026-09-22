"""Fail-closed executor for A2a Direct-Qwen body code and F0 export."""

from __future__ import annotations

import ast
import json
import math
import sys
from pathlib import Path

import FreeCAD
import Part
import numpy

ALLOWED_IMPORTS = {"FreeCAD", "Part", "math", "numpy"}
FORBIDDEN_CALLS = {"open", "exec", "eval", "compile", "input", "__import__"}
FORBIDDEN_ATTRIBUTES = {"openDocument", "saveAs", "export", "exportBrep", "exportBrepToString"}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_code(source):
    tree = ast.parse(source)
    uses_f0 = False
    assigns_result = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name.split(".")[0] not in ALLOWED_IMPORTS for alias in node.names):
                raise RuntimeError("DIRECT_CODE_FORBIDDEN_IMPORT")
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] not in ALLOWED_IMPORTS:
            raise RuntimeError("DIRECT_CODE_FORBIDDEN_IMPORT")
        if isinstance(node, ast.Name):
            uses_f0 |= isinstance(node.ctx, ast.Load) and node.id == "f0_shape"
            assigns_result |= isinstance(node.ctx, ast.Store) and node.id == "result_shape"
            if isinstance(node.ctx, ast.Load) and node.id in FORBIDDEN_CALLS:
                raise RuntimeError("DIRECT_CODE_FORBIDDEN_CALL")
        if isinstance(node, ast.Attribute) and (node.attr.startswith("__") or node.attr in FORBIDDEN_ATTRIBUTES):
            raise RuntimeError("DIRECT_CODE_FORBIDDEN_ATTRIBUTE")
    if not uses_f0:
        raise RuntimeError("DIRECT_CODE_MUST_USE_F0_SHAPE")
    if not assigns_result:
        raise RuntimeError("DIRECT_CODE_MUST_ASSIGN_RESULT_SHAPE")
    return tree


def f0_shape(path):
    document = FreeCAD.openDocument(str(path))
    obj = document.getObject("RigidGroup")
    if obj is None or obj.Shape.isNull():
        FreeCAD.closeDocument(document.Name)
        raise RuntimeError("F0_RIGID_GROUP_MISSING")
    shape = obj.Shape.copy()
    FreeCAD.closeDocument(document.Name)
    return shape


def shape_record(shape):
    bounds = shape.BoundBox
    return {
        "valid": shape.isValid() and not shape.isNull(),
        "volume_mm3": float(shape.Volume),
        "solid_count": len(shape.Solids),
        "face_count": len(shape.Faces),
        "bbox_size_mm": [float(bounds.XLength), float(bounds.YLength), float(bounds.ZLength)],
    }


def main():
    job = load(sys.argv[1]); mode = job["mode"]; source_shape = f0_shape(job["f0_fcstd"])
    if mode == "export_f0":
        source_shape.exportBrep(job["output_brep"])
        document = FreeCAD.newDocument("A2A_F0_Export")
        feature = document.addObject("Part::Feature", "RigidGroup")
        feature.Shape = source_shape
        document.recompute()
        Part.export([feature], job["output_step"])
        import Mesh
        Mesh.export([feature], job["output_stl"])
        FreeCAD.closeDocument(document.Name)
        payload = {"status": "PASS", "mode": mode, "shape": shape_record(source_shape)}
    elif mode == "execute_direct_body":
        code = Path(job["code_path"]).read_text(encoding="utf-8")
        tree = validate_code(code)
        namespace = {"FreeCAD": FreeCAD, "App": FreeCAD, "Part": Part, "math": math, "numpy": numpy, "np": numpy, "f0_shape": source_shape.copy(), "__builtins__": {"abs": abs, "bool": bool, "dict": dict, "enumerate": enumerate, "float": float, "int": int, "len": len, "list": list, "max": max, "min": min, "range": range, "round": round, "sum": sum, "tuple": tuple, "zip": zip, "__import__": __import__}}
        exec(compile(tree, str(job["code_path"]), "exec"), namespace, namespace)
        result = namespace.get("result_shape")
        if not isinstance(result, Part.Shape) or result.isNull() or not result.isValid() or result.Volume <= 0:
            raise RuntimeError("DIRECT_RESULT_SHAPE_INVALID")
        bounds = result.BoundBox
        if max(bounds.XLength, bounds.YLength, bounds.ZLength) > 500:
            raise RuntimeError("DIRECT_RESULT_SHAPE_OUT_OF_BOUNDS")
        result.exportBrep(job["output_brep"])
        payload = {"status": "PASS", "mode": mode, "shape": shape_record(result)}
    else:
        raise RuntimeError("UNKNOWN_A2A_BODY_MODE")
    Path(job["output_json"]).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
