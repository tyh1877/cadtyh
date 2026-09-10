"""Executable, fail-closed body-family compiler used by Try-5B refinement.

The compiler owns body geometry only.  Frozen Try-5A interface halves are supplied
by the caller and are never inferred or modified here.
"""

from __future__ import annotations

import FreeCAD as App
import Part


SUPPORTED = {"central_web", "compound_profile_housing", "gripper_support"}


def _box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, App.Vector(x0, y0, z0))


def _union(parts):
    shape = parts[0]
    for part in parts[1:]:
        shape = shape.fuse(part)
    return shape.removeSplitter()


def _prism_x(points_yz, x0, length):
    wire = Part.makePolygon([App.Vector(x0, y, z) for y, z in points_yz] +
                            [App.Vector(x0, *points_yz[0])])
    return Part.Face(wire).extrude(App.Vector(length, 0, 0))


def central_web(schema):
    """Flattened load-carrying web with explicit joint transitions."""
    span = float(schema["span_mm"]); t = float(schema["thickness_mm"])
    h0 = float(schema["proximal_height_mm"]); h1 = float(schema["mid_height_mm"])
    core = _prism_x([(-t/2, -h1/2), (t/2, -h1/2), (t/2, h1/2), (-t/2, h1/2)], 12, span-24)
    proximal = _prism_x([(-t/2, -h0/2), (t/2, -h0/2), (t/2, h0/2), (-t/2, h0/2)], 2, 18)
    distal = _prism_x([(-t/2, -h0*.42), (t/2, -h0*.42), (t/2, h0*.42), (-t/2, h0*.42)], span-18, 16)
    shape = _union([core, proximal, distal])
    features = ["proximal_joint_housing", "central_web", "distal_joint_region"]
    if schema.get("major_recess"):
        # A bounded side recess changes the profile without severing the load path.
        recess = _box(span*.35, span*.72, -t, t, -h1*.22, h1*.22)
        shape = shape.cut(recess).removeSplitter(); features.append("major_recess")
    offset = float(schema.get("lateral_offset_mm", 0.0))
    if offset:
        shape.translate(App.Vector(0, offset, 0))
    return shape, features


def compound_profile_housing(schema):
    """Wrist-local housing with distinct sections and an optional service recess."""
    span = float(schema["span_mm"]); width = float(schema["width_mm"]); height = float(schema["height_mm"])
    # Start beyond the frozen rotary mating envelope (radius 11.5 mm).
    main = _box(12, span-9, -width/2, width/2, -height/2, height/2)
    shoulder = _box(11.8, min(24, span*.42), -width*.62, width*.62, -height*.58, height*.58)
    nose = _box(span-16, span, -width*.38, width*.38, -height*.36, height*.36)
    shape = _union([main, shoulder, nose]); features = ["proximal_housing", "stepped_housing", "distal_mount_transition"]
    if schema.get("major_recess"):
        recess = _box(span*.35, span*.7, -width, width, height*.12, height)
        shape = shape.cut(recess).removeSplitter(); features.append("major_recess")
    return shape, features


def gripper_support(schema):
    """End-side carriage and transverse support, optionally split by a working gap."""
    span = float(schema["span_mm"]); bar = float(schema["bar_width_mm"]); thick = float(schema["thickness_mm"])
    carriage = _box(0, span, -8, 8, -thick/2, thick/2)
    crossbar = _box(span*.38, span*.78, -bar/2, bar/2, -thick/2, thick/2)
    transitions = [_box(span*.18, span*.5, -bar/2, -6, -thick*.38, thick*.38),
                   _box(span*.18, span*.5, 6, bar/2, -thick*.38, thick*.38)]
    shape = _union([carriage, crossbar, *transitions])
    features = ["carriage", "transverse_support", "left_support", "right_support"]
    if schema.get("working_gap"):
        gap = _box(span*.48, span+1, -4, 4, -thick, thick)
        shape = shape.cut(gap).removeSplitter(); features.append("working_gap")
    return shape, features


def compile_body(family, schema):
    """Fail closed: an unimplemented planner family is never downgraded."""
    if family not in SUPPORTED:
        raise RuntimeError("EXECUTABLE_FAMILY_MISSING: " + str(family))
    body, features = globals()[family](schema)
    return {"shape": body, "executed_family": family, "features": features,
            "schema_consumed": dict(schema), "valid": body.isValid() and not body.isNull()}
