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
    def __init__(self, message: str, code: str = "FREECAD_BACKEND_ERROR", context: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.context = context or {}


class IRIncomplete(FreeCADBackendError):
    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message, code="IR_INCOMPLETE", context=context)


def vec(values: list[float] | tuple[float, float, float]):
    if len(values) != 3:
        raise IRIncomplete(f"expected vec3, got {values!r}")
    return FreeCAD.Vector(float(values[0]), float(values[1]), float(values[2]))


def unit_vec(values: list[float] | tuple[float, float, float]):
    value = vec(values)
    if value.Length <= 1e-9:
        raise IRIncomplete(f"direction must be non-zero, got {values!r}")
    value.normalize()
    return value


def rotation_from_z(direction):
    return FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), direction)


def rectangle_wire(center, normal, width: float, depth: float):
    """Create a closed rectangular wire centered in a plane normal to normal."""
    z_axis = unit_vec((normal.x, normal.y, normal.z))
    reference = FreeCAD.Vector(1, 0, 0) if abs(z_axis.x) < 0.8 else FreeCAD.Vector(0, 1, 0)
    x_axis = reference.cross(z_axis)
    x_axis.normalize()
    y_axis = z_axis.cross(x_axis)
    y_axis.normalize()
    points = [
        center + x_axis * sx * width / 2.0 + y_axis * sy * depth / 2.0
        for sx, sy in [(-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1)]
    ]
    return Part.makePolygon(points)


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
        self.current_preflight: dict[str, Any] | None = None

    def _shape_stats(self, obj) -> dict[str, Any]:
        shape = getattr(obj, "Shape", None)
        if shape is None or shape.isNull():
            return {"shape_null": True}
        bbox = shape.BoundBox
        return {
            "shape_null": False,
            "shape_valid": bool(shape.isValid()),
            "volume": float(shape.Volume),
            "bbox": {
                "xmin": float(bbox.XMin),
                "xmax": float(bbox.XMax),
                "ymin": float(bbox.YMin),
                "ymax": float(bbox.YMax),
                "zmin": float(bbox.ZMin),
                "zmax": float(bbox.ZMax),
                "xlength": float(bbox.XLength),
                "ylength": float(bbox.YLength),
                "zlength": float(bbox.ZLength),
            },
            "faces": len(shape.Faces),
            "edges": len(shape.Edges),
            "solids": len(shape.Solids),
        }

    def _bbox_intersects(self, a, b, tolerance: float = 1e-6) -> bool:
        abox = a.Shape.BoundBox
        bbox = b.Shape.BoundBox
        return not (
            abox.XMax < bbox.XMin - tolerance
            or bbox.XMax < abox.XMin - tolerance
            or abox.YMax < bbox.YMin - tolerance
            or bbox.YMax < abox.YMin - tolerance
            or abox.ZMax < bbox.ZMin - tolerance
            or bbox.ZMax < abox.ZMin - tolerance
        )

    def _check_native_shape(self, obj, code: str, context: dict[str, Any]) -> None:
        shape = getattr(obj, "Shape", None)
        if shape is None or shape.isNull():
            raise FreeCADBackendError("native shape is null", code=code, context=context)
        if not shape.isValid():
            raise FreeCADBackendError("native shape is invalid", code=code, context=context)

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
        self.current_preflight = None
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
            "failure_code": None,
            "failure_reason": None,
            "failure_context": None,
            "preflight": None,
        }
        try:
            handler = getattr(self, f"op_{op.get('op_type')}", None)
            if handler is None:
                raise IRIncomplete(f"unsupported op_type: {op.get('op_type')}")
            obj, native_type = handler(op)
            self.doc.recompute()
            self._check_native_shape(obj, "NATIVE_INVALID_SHAPE", {"op_id": op.get("op_id"), "op_type": op.get("op_type"), "object": getattr(obj, "Name", None)})
            record.update(
                {
                    "executed_native_operation": native_type,
                    "native_object_name": obj.Name,
                    "native_object_type": obj.TypeId,
                    "success": True,
                    "semantic_match": True,
                    "preflight": self.current_preflight,
                }
            )
        except Exception as exc:
            record["preflight"] = self.current_preflight
            record["failure_code"] = getattr(exc, "code", type(exc).__name__)
            record["failure_context"] = getattr(exc, "context", None)
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

    def op_oriented_box(self, op):
        op_required(op, ["op_id", "target_body", "start", "end", "width_mm", "depth_mm", "reference_frame"])
        start = vec(op["start"])
        end = vec(op["end"])
        direction = end - start
        length = float(direction.Length)
        if length <= 1e-6:
            raise IRIncomplete("oriented_box start and end must differ")
        direction.normalize()
        width = float(op["width_mm"])
        depth = float(op["depth_mm"])
        if min(width, depth) <= 0:
            raise IRIncomplete("oriented_box dimensions must be positive")
        rotation = rotation_from_z(direction)
        obj = self.doc.addObject("Part::Box", op["op_id"])
        obj.Length = width
        obj.Width = depth
        obj.Height = length
        offset = rotation.multVec(FreeCAD.Vector(-width / 2.0, -depth / 2.0, 0))
        obj.Placement = FreeCAD.Placement(start + offset, rotation)
        return self.register(op, obj), "Part::Box"

    def op_cylinder_primitive(self, op):
        op_required(op, ["op_id", "target_body", "center", "axis", "radius_mm", "height_mm", "reference_frame"])
        center = vec(op["center"])
        axis = unit_vec(op["axis"])
        radius = float(op["radius_mm"])
        height = float(op["height_mm"])
        if min(radius, height) <= 0:
            raise IRIncomplete("cylinder dimensions must be positive")
        obj = self.doc.addObject("Part::Cylinder", op["op_id"])
        obj.Radius = radius
        obj.Height = height
        obj.Angle = 360.0
        obj.Placement = FreeCAD.Placement(center - axis * (height / 2.0), rotation_from_z(axis))
        return self.register(op, obj), "Part::Cylinder"

    def op_lofted_prism(self, op):
        op_required(op, ["op_id", "target_body", "start", "end", "start_size_mm", "end_size_mm", "reference_frame"])
        start = vec(op["start"])
        end = vec(op["end"])
        direction = end - start
        if direction.Length <= 1e-6:
            raise IRIncomplete("lofted_prism start and end must differ")
        start_size = [float(value) for value in op["start_size_mm"]]
        end_size = [float(value) for value in op["end_size_mm"]]
        if len(start_size) != 2 or len(end_size) != 2 or min([*start_size, *end_size]) <= 0:
            raise IRIncomplete("lofted_prism requires two positive 2D sizes")
        sections = []
        for index, (center, size) in enumerate(((start, start_size), (end, end_size))):
            item = self.doc.addObject("Part::Feature", f"{op['op_id']}_section_{index}")
            item.Shape = rectangle_wire(center, direction, float(size[0]), float(size[1]))
            sections.append(item)
        obj = self.doc.addObject("Part::Loft", op["op_id"])
        obj.Sections = sections
        obj.Solid = True
        obj.Ruled = False
        return self.register(op, obj), "Part::Loft"

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
        base = self.resolve(op["target_body"])
        tools = [self.resolve(name) for name in op["tool_bodies"]]
        if not tools:
            raise IRIncomplete("boolean_union requires tool_bodies")
        steps = []
        current = base
        for idx, tool in enumerate(tools, start=1):
            step_name = op["op_id"] if idx == len(tools) else f"{op['op_id']}_seq_{idx:02d}"
            obj = self.doc.addObject("Part::Fuse", step_name)
            obj.Base = current
            obj.Tool = tool
            self.doc.recompute()
            context = {
                "step": idx,
                "tool_body": op["tool_bodies"][idx - 1],
                "base": self._shape_stats(current),
                "tool": self._shape_stats(tool),
                "result": self._shape_stats(obj),
            }
            steps.append(context)
            try:
                self._check_native_shape(obj, "BOOLEAN_UNION_STEP_INVALID", context)
            except FreeCADBackendError:
                self.current_preflight = {"operation": "boolean_union", "strategy": "sequential_fuse", "steps": steps}
                raise
            current = obj
        self.current_preflight = {"operation": "boolean_union", "strategy": "sequential_fuse", "steps": steps}
        return self.register(op, current), "Part::FuseSequential"

    def op_boolean_cut(self, op):
        op_required(op, ["op_id", "target_body", "tool_bodies", "reference_frame"])
        base = self.resolve(op["target_body"])
        tools = [self.resolve(name) for name in op["tool_bodies"]]
        if not tools:
            raise IRIncomplete("boolean_cut requires tool_bodies")
        tool = tools[0]
        intersects = self._bbox_intersects(base, tool, tolerance=float(op.get("intersection_tolerance_mm", 1e-4)))
        self.current_preflight = {
            "operation": "boolean_cut",
            "target": self._shape_stats(base),
            "tool": self._shape_stats(tool),
            "bbox_intersects": intersects,
        }
        if not intersects:
            raise FreeCADBackendError("boolean_cut cutter bbox does not intersect target bbox", code="CUTTER_NO_INTERSECTION", context=self.current_preflight)
        obj = self.doc.addObject("Part::Cut", op["op_id"])
        obj.Base = base
        obj.Tool = tool
        self.doc.recompute()
        result_stats = self._shape_stats(obj)
        self.current_preflight["result"] = result_stats
        self._check_native_shape(obj, "BOOLEAN_CUT_RESULT_INVALID", self.current_preflight)
        return self.register(op, obj), "Part::Cut"

    op_cut = op_boolean_cut
    op_pocket = op_boolean_cut

    def _edge_length(self, edge) -> float:
        try:
            return float(edge.Length)
        except Exception:
            return 0.0

    def _is_circular_edge(self, edge) -> bool:
        curve = getattr(edge, "Curve", None)
        type_id = str(getattr(curve, "TypeId", "") or type(curve).__name__)
        return "Circle" in type_id or "Ellipse" in type_id

    def _is_linear_edge(self, edge) -> bool:
        curve = getattr(edge, "Curve", None)
        type_id = str(getattr(curve, "TypeId", "") or type(curve).__name__)
        return "Line" in type_id

    def _edge_midpoint(self, edge) -> list[float]:
        try:
            p = edge.valueAt((edge.FirstParameter + edge.LastParameter) / 2.0)
            return [float(p.x), float(p.y), float(p.z)]
        except Exception:
            return [0.0, 0.0, 0.0]

    def _edge_candidate_rows(self, base, clearance: float) -> list[dict[str, Any]]:
        bbox = base.Shape.BoundBox
        diag = max((bbox.XLength**2 + bbox.YLength**2 + bbox.ZLength**2) ** 0.5, 1e-6)
        rows = []
        for idx, edge in enumerate(base.Shape.Edges, start=1):
            length = self._edge_length(edge)
            midpoint = self._edge_midpoint(edge)
            on_outer = (
                abs(midpoint[0] - bbox.XMin) <= diag * 0.02
                or abs(midpoint[0] - bbox.XMax) <= diag * 0.02
                or abs(midpoint[1] - bbox.YMin) <= diag * 0.02
                or abs(midpoint[1] - bbox.YMax) <= diag * 0.02
                or abs(midpoint[2] - bbox.ZMin) <= diag * 0.02
                or abs(midpoint[2] - bbox.ZMax) <= diag * 0.02
            )
            rows.append(
                {
                    "index": idx,
                    "length": length,
                    "is_linear": self._is_linear_edge(edge),
                    "is_circular": self._is_circular_edge(edge),
                    "midpoint": midpoint,
                    "on_outer_bbox": on_outer,
                    "safe_by_length": length > max(float(clearance) * 6.0, 1e-6),
                }
            )
        return rows

    def select_edges(self, base, selectors: list[dict[str, Any]], clearance: float) -> list[int]:
        """Resolve typed edge selectors against the current native shape.

        IR v1.2 intentionally avoids raw edge indices in planner output because
        FreeCAD topology numbering is unstable after boolean/modifier features.
        This resolver derives indices from simple native topology properties and
        fails explicitly when no edge satisfies the selector.
        """
        candidates = [(idx, edge, self._edge_length(edge)) for idx, edge in enumerate(base.Shape.Edges, start=1)]
        if not candidates:
            raise IRIncomplete("target body has no selectable edges")
        selected: list[int] = []
        min_length = max(float(clearance) * 6.0, 1e-6)
        for selector in selectors:
            selector_type = selector.get("selector_type")
            if selector_type == "edge_index":
                selected.append(int(selector.get("edge_index", 1)))
                continue
            max_edges = int(selector.get("max_edges", 8) or 8)
            pool = candidates
            if selector_type == "circular_edges":
                pool = [item for item in candidates if self._is_circular_edge(item[1])]
            elif selector_type == "outer_short_edges":
                pool = [item for item in candidates if item[2] > min_length and self._is_linear_edge(item[1])]
                pool = sorted(pool, key=lambda item: item[2])
            elif selector_type in {"outer_long_edges", "feature_edges", "all_safe_edges"}:
                pool = [item for item in candidates if item[2] > min_length and self._is_linear_edge(item[1])]
                pool = sorted(pool, key=lambda item: item[2], reverse=True)
            else:
                raise IRIncomplete(f"unsupported edge selector_type: {selector_type!r}")
            selected.extend(idx for idx, _edge, _length in pool[:max_edges])
        ordered: list[int] = []
        for idx in selected:
            if 1 <= idx <= len(base.Shape.Edges) and idx not in ordered:
                ordered.append(idx)
        if not ordered:
            raise FreeCADBackendError(
                "no suitable edges found for chamfer/fillet selectors",
                code="NO_SAFE_EDGE",
                context={"selectors": selectors, "clearance": clearance, "edge_candidates": self._edge_candidate_rows(base, clearance)},
            )
        return ordered

    def _trial_modifier_edges(self, base, selectors: list[dict[str, Any]], clearance: float, mode: str) -> list[int]:
        rows = self._edge_candidate_rows(base, clearance)
        broad_selectors = []
        for selector in selectors:
            item = dict(selector)
            item["max_edges"] = max(int(item.get("max_edges", 8) or 8), 64)
            broad_selectors.append(item)
        candidate_indices = self.select_edges(base, broad_selectors, clearance)
        accepted: list[int] = []
        rejected: list[dict[str, Any]] = []
        for idx in candidate_indices:
            trial = self.doc.addObject("Part::Fillet" if mode == "fillet" else "Part::Chamfer", f"trial_{mode}_{idx}")
            trial_name = trial.Name
            trial.Base = base
            trial.Edges = [(idx, clearance, clearance)]
            try:
                self.doc.recompute()
                shape = getattr(trial, "Shape", None)
                if shape is not None and not shape.isNull() and shape.isValid():
                    accepted.append(idx)
                    rejected.append({"edge": idx, "trial": "accepted"})
                    self.doc.removeObject(trial.Name)
                    break
                rejected.append({"edge": idx, "trial": "invalid_shape"})
            except Exception as exc:
                rejected.append({"edge": idx, "trial": f"{type(exc).__name__}: {exc}"})
            finally:
                if self.doc.getObject(trial_name):
                    self.doc.removeObject(trial_name)
                self.doc.recompute()
        self.current_preflight = {
            "operation": mode,
            "clearance": clearance,
            "selectors": selectors,
            "edge_candidates": rows,
            "trial_results": rejected,
            "selected_edges": accepted,
        }
        if not accepted:
            raise FreeCADBackendError(
                f"no safe edge accepted by {mode} trial",
                code="NO_SAFE_EDGE",
                context=self.current_preflight,
            )
        return accepted

    def op_fillet(self, op):
        op_required(op, ["op_id", "target_body", "edge_selectors", "radius_mm", "reference_frame"])
        base = self.resolve(op["target_body"])
        radius = float(op["radius_mm"])
        edges = [(idx, radius, radius) for idx in self._trial_modifier_edges(base, op["edge_selectors"], radius, "fillet")]
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
        edges = [(idx, distance, distance) for idx in self._trial_modifier_edges(base, op["edge_selectors"], distance, "chamfer")]
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
