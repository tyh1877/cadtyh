"""Strict FreeCAD backend for RobotCAD Executable CAD IR v1.

This module is intended to run inside FreeCADCmd. It maps requested IR
operations to native FreeCAD/Part/Draft objects and records failures explicitly.
It never substitutes one requested operation with another operation type.
"""
from __future__ import annotations

import json
import time
import traceback
from pathlib import Path
from typing import Any

import FreeCAD  # type: ignore
import Import  # type: ignore
import Mesh  # type: ignore
import Part  # type: ignore

try:
    import Draft  # type: ignore
except Exception:
    Draft = None


class FreeCADBackendError(RuntimeError):
    pass


class IRIncomplete(FreeCADBackendError):
    pass


def vec(values: list[float] | tuple[float, float, float]):
    if len(values) != 3:
        raise IRIncomplete(f"expected vec3, got {values!r}")
    return FreeCAD.Vector(float(values[0]), float(values[1]), float(values[2]))


def op_required(op: dict[str, Any], fields: list[str]) -> None:
    missing = [field for field in fields if field not in op]
    if missing:
        raise IRIncomplete("missing required fields: " + ",".join(missing))


def profile_face(profile: dict[str, Any]):
    kind = profile.get("profile_type")
    params = profile.get("parameters") or {}
    if not profile.get("closed", False):
        raise IRIncomplete("profile must be closed for solid operation")
    center = vec(params.get("center", [0, 0, 0]))
    if kind == "rectangle":
        size = params.get("size_mm") or params.get("size")
        if not size or len(size) != 2:
            raise IRIncomplete("rectangle profile requires parameters.size_mm=[x,y]")
        sx, sy = float(size[0]), float(size[1])
        pts = [
            FreeCAD.Vector(center.x - sx / 2, center.y - sy / 2, center.z),
            FreeCAD.Vector(center.x + sx / 2, center.y - sy / 2, center.z),
            FreeCAD.Vector(center.x + sx / 2, center.y + sy / 2, center.z),
            FreeCAD.Vector(center.x - sx / 2, center.y + sy / 2, center.z),
            FreeCAD.Vector(center.x - sx / 2, center.y - sy / 2, center.z),
        ]
        return Part.Face(Part.makePolygon(pts))
    if kind == "circle":
        radius = params.get("radius_mm") or params.get("radius")
        if radius is None:
            raise IRIncomplete("circle profile requires parameters.radius_mm")
        return Part.Face(Part.Wire([Part.makeCircle(float(radius), center, FreeCAD.Vector(0, 0, 1))]))
    if kind == "annulus":
        outer = params.get("outer_radius_mm")
        inner = params.get("inner_radius_mm")
        if outer is None or inner is None:
            raise IRIncomplete("annulus profile requires outer_radius_mm and inner_radius_mm")
        outer_wire = Part.Wire([Part.makeCircle(float(outer), center, FreeCAD.Vector(0, 0, 1))])
        inner_wire = Part.Wire([Part.makeCircle(float(inner), center, FreeCAD.Vector(0, 0, 1))])
        return Part.Face([outer_wire, inner_wire])
    if kind == "polyline":
        points = params.get("points")
        if not points or len(points) < 3:
            raise IRIncomplete("polyline profile requires at least three points")
        vectors = [vec(p) for p in points]
        if vectors[0].distanceToPoint(vectors[-1]) > 1e-7:
            vectors.append(vectors[0])
        return Part.Face(Part.makePolygon(vectors))
    raise IRIncomplete(f"unsupported profile_type: {kind!r}")


def profile_wire(profile: dict[str, Any]):
    return profile_face(profile).OuterWire


class FreeCADBackend:
    def __init__(self, document_name: str):
        self.doc = FreeCAD.newDocument(document_name)
        self.objects: dict[str, Any] = {}
        self.execution_log: list[dict[str, Any]] = []

    def resolve(self, name: str):
        if name in self.objects:
            return self.objects[name]
        obj = self.doc.getObject(name)
        if obj is not None:
            return obj
        raise IRIncomplete(f"unknown body/object reference: {name}")

    def register(self, op: dict[str, Any], obj):
        self.objects[op["op_id"]] = obj
        self.objects[op["target_body"]] = obj
        return obj

    def execute(self, op: dict[str, Any]) -> None:
        started = time.time()
        record = {
            "op_id": op.get("op_id"),
            "requested_operation": op.get("op_type"),
            "executed_native_operation": None,
            "input_parameters": op,
            "native_object_name": None,
            "native_object_type": None,
            "start_time": started,
            "end_time": None,
            "success": False,
            "semantic_match": False,
            "fallback_used": False,
            "failure_reason": None,
        }
        try:
            handler = getattr(self, f"op_{op.get('op_type')}", None)
            if handler is None:
                raise IRIncomplete(f"unsupported op_type: {op.get('op_type')}")
            obj, native_type = handler(op)
            self.doc.recompute()
            if obj.Shape.isNull() or not obj.Shape.isValid():
                raise FreeCADBackendError("native shape is null or invalid")
            record.update(
                {
                    "executed_native_operation": native_type,
                    "native_object_name": obj.Name,
                    "native_object_type": obj.TypeId,
                    "success": True,
                    "semantic_match": True,
                }
            )
        except Exception:
            record["failure_reason"] = traceback.format_exc()
            raise
        finally:
            record["end_time"] = time.time()
            self.execution_log.append(record)

    def op_extrude(self, op):
        op_required(op, ["op_id", "target_body", "profile", "distance_mm", "operation_mode", "reference_frame"])
        face = self.doc.addObject("Part::Feature", f"{op['op_id']}_profile")
        face.Shape = profile_face(op["profile"])
        obj = self.doc.addObject("Part::Extrusion", op["op_id"])
        obj.Base = face
        direction = vec(op["reference_frame"].get("z_axis", [0, 0, 1]))
        obj.Dir = direction.multiply(float(op["distance_mm"]))
        obj.Solid = True
        return self.register(op, obj), "Part::Extrusion"

    op_pad = op_extrude

    def op_revolve(self, op):
        op_required(op, ["op_id", "target_body", "profile", "axis", "angle_deg", "operation_mode", "reference_frame"])
        face = self.doc.addObject("Part::Feature", f"{op['op_id']}_profile")
        face.Shape = profile_face(op["profile"])
        obj = self.doc.addObject("Part::Revolution", op["op_id"])
        obj.Source = face
        obj.Base = vec(op["axis"]["point"])
        obj.Axis = vec(op["axis"]["direction"])
        obj.Angle = float(op["angle_deg"])
        return self.register(op, obj), "Part::Revolution"

    def op_loft(self, op):
        op_required(op, ["op_id", "target_body", "profiles", "solid", "operation_mode", "reference_frame"])
        sections = []
        for idx, profile in enumerate(op["profiles"]):
            item = self.doc.addObject("Part::Feature", f"{op['op_id']}_section_{idx}")
            item.Shape = profile_wire(profile)
            sections.append(item)
        obj = self.doc.addObject("Part::Loft", op["op_id"])
        obj.Sections = sections
        obj.Solid = bool(op["solid"])
        obj.Ruled = False
        return self.register(op, obj), "Part::Loft"

    def op_sweep(self, op):
        op_required(op, ["op_id", "target_body", "profile", "profile_frame", "path", "orientation_mode", "transition_mode", "solid", "operation_mode", "reference_frame"])
        section = self.doc.addObject("Part::Feature", f"{op['op_id']}_section")
        section.Shape = profile_wire(op["profile"])
        points = op["path"].get("control_points")
        if not points or len(points) < 2:
            raise IRIncomplete("sweep path requires at least two control_points")
        edges = [Part.makeLine(vec(a), vec(b)) for a, b in zip(points, points[1:])]
        spine = self.doc.addObject("Part::Feature", f"{op['op_id']}_spine")
        spine.Shape = Part.Wire(edges)
        obj = self.doc.addObject("Part::Sweep", op["op_id"])
        obj.Sections = [section]
        obj.Spine = spine
        obj.Solid = bool(op["solid"])
        obj.Frenet = False
        return self.register(op, obj), "Part::Sweep"

    op_pipe = op_sweep

    def op_shell(self, op):
        op_required(op, ["op_id", "target_body", "faces_to_remove", "thickness_mm", "direction", "join_mode", "reference_frame"])
        base = self.resolve(op["target_body"])
        faces = list(op["faces_to_remove"])
        if not faces:
            raise IRIncomplete("shell requires at least one face selector")
        obj = self.doc.addObject("Part::Thickness", op["op_id"])
        obj.Faces = (base, faces)
        value = float(op["thickness_mm"])
        obj.Value = -abs(value) if op["direction"] == "inward" else abs(value)
        obj.Join = "Arc" if op.get("join_mode") == "arc" else "Intersection"
        return self.register(op, obj), "Part::Thickness"

    op_thickness = op_shell

    def op_boolean_union(self, op):
        op_required(op, ["op_id", "target_body", "tool_bodies", "reference_frame"])
        tools = [self.resolve(name) for name in op["tool_bodies"]]
        if not tools:
            raise IRIncomplete("boolean_union requires tool_bodies")
        if len(tools) == 1:
            obj = self.doc.addObject("Part::Fuse", op["op_id"])
            obj.Base = self.resolve(op["target_body"])
            obj.Tool = tools[0]
            native_type = "Part::Fuse"
        else:
            obj = self.doc.addObject("Part::MultiFuse", op["op_id"])
            obj.Shapes = [self.resolve(op["target_body"]), *tools]
            native_type = "Part::MultiFuse"
        return self.register(op, obj), native_type

    def op_boolean_cut(self, op):
        op_required(op, ["op_id", "target_body", "tool_bodies", "reference_frame"])
        tools = [self.resolve(name) for name in op["tool_bodies"]]
        if not tools:
            raise IRIncomplete("boolean_cut requires tool_bodies")
        obj = self.doc.addObject("Part::Cut", op["op_id"])
        obj.Base = self.resolve(op["target_body"])
        obj.Tool = tools[0]
        return self.register(op, obj), "Part::Cut"

    op_cut = op_boolean_cut
    op_pocket = op_boolean_cut

    def op_fillet(self, op):
        op_required(op, ["op_id", "target_body", "edge_selectors", "radius_mm", "reference_frame"])
        base = self.resolve(op["target_body"])
        radius = float(op["radius_mm"])
        edges = [(int(item.get("edge_index", 1)), radius, radius) for item in op["edge_selectors"]]
        if not edges:
            raise IRIncomplete("fillet requires edge_selectors")
        obj = self.doc.addObject("Part::Fillet", op["op_id"])
        obj.Base = base
        obj.Edges = edges
        return self.register(op, obj), "Part::Fillet"

    def op_chamfer(self, op):
        op_required(op, ["op_id", "target_body", "edge_selectors", "distance_mm", "reference_frame"])
        base = self.resolve(op["target_body"])
        distance = float(op["distance_mm"])
        edges = [(int(item.get("edge_index", 1)), distance, distance) for item in op["edge_selectors"]]
        if not edges:
            raise IRIncomplete("chamfer requires edge_selectors")
        obj = self.doc.addObject("Part::Chamfer", op["op_id"])
        obj.Base = base
        obj.Edges = edges
        return self.register(op, obj), "Part::Chamfer"

    def op_pattern(self, op):
        if Draft is None:
            raise FreeCADBackendError("Draft module unavailable")
        op_required(op, ["op_id", "target_features", "pattern_type", "axis_or_direction", "count", "spacing_or_angle", "reference_frame"])
        source = self.resolve(op["target_features"][0])
        if op["pattern_type"] != "linear":
            raise IRIncomplete("current strict backend supports only linear pattern in IR v1")
        direction = vec(op["axis_or_direction"].get("direction", [1, 0, 0]))
        spacing = float(op["spacing_or_angle"])
        count = int(op["count"])
        obj = Draft.make_array(source, direction.multiply(spacing), FreeCAD.Vector(0, 0, 0), count, 1)
        obj.Label = op["op_id"]
        self.objects[op["op_id"]] = obj
        self.objects[op["target_body"]] = obj
        return obj, "Draft::Array"

    def op_mirror(self, op):
        op_required(op, ["op_id", "target_features", "mirror_plane", "reference_frame"])
        source = self.resolve(op["target_features"][0])
        obj = self.doc.addObject("Part::Mirroring", op["op_id"])
        obj.Source = source
        obj.Base = vec(op["mirror_plane"]["origin"])
        obj.Normal = vec(op["mirror_plane"]["z_axis"])
        self.objects[op["op_id"]] = obj
        self.objects[op["target_body"]] = obj
        return obj, "Part::Mirroring"

    def export(self, output_base: Path, final_object_name: str | None = None) -> dict[str, str]:
        output_base.parent.mkdir(parents=True, exist_ok=True)
        final = self.resolve(final_object_name) if final_object_name else list(self.objects.values())[-1]
        fcstd = output_base.with_suffix(".FCStd")
        step = output_base.with_suffix(".step")
        stl = output_base.with_suffix(".stl")
        self.doc.saveAs(str(fcstd))
        Import.export([final], str(step))
        Mesh.export([final], str(stl))
        return {"fcstd": str(fcstd), "step": str(step), "stl": str(stl)}

    def feature_manifest(self) -> list[dict[str, Any]]:
        rows = []
        for obj in self.doc.Objects:
            shape = getattr(obj, "Shape", None)
            stats: dict[str, Any] = {}
            if shape is not None and not shape.isNull():
                bbox = shape.BoundBox
                stats = {
                    "shape_valid": bool(shape.isValid()),
                    "volume": float(shape.Volume),
                    "bbox": [bbox.XLength, bbox.YLength, bbox.ZLength],
                    "faces": len(shape.Faces),
                    "edges": len(shape.Edges),
                    "solids": len(shape.Solids),
                }
            rows.append(
                {
                    "name": obj.Name,
                    "label": obj.Label,
                    "native_type": obj.TypeId,
                    "visibility": bool(getattr(obj, "Visibility", False)),
                    "properties": list(getattr(obj, "PropertiesList", [])),
                    **stats,
                }
            )
        return rows

    def close(self) -> None:
        FreeCAD.closeDocument(self.doc.Name)


def execute_ir(ir: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    backend = FreeCADBackend(f"{ir['case_id']}_{ir['link_id']}")
    status = "FAILURE"
    error = None
    exports: dict[str, str] = {}
    try:
        for body in ir.get("bodies", []):
            backend.objects[body["body_id"]] = None
        for op in ir["operations"]:
            backend.execute(op)
        final_object = ir.get("final_object") or ir["operations"][-1]["op_id"]
        exports = backend.export(output_dir / "model", final_object)
        status = "SUCCESS"
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    feature_manifest = backend.feature_manifest()
    object_tree = [{"name": item["name"], "label": item["label"], "native_type": item["native_type"]} for item in feature_manifest]
    result = {
        "case_id": ir.get("case_id"),
        "link_id": ir.get("link_id"),
        "status": status,
        "error": error,
        "exports": exports,
        "execution_log": backend.execution_log,
        "feature_manifest": feature_manifest,
        "object_tree": object_tree,
    }
    backend.close()
    return result
