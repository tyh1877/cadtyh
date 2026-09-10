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


def _oriented_prism(start, end, width, thickness):
    import numpy as np
    start=np.asarray(start,dtype=float); end=np.asarray(end,dtype=float); delta=end-start; length=float(np.linalg.norm(delta)); d=delta/length
    reference=np.array([0.,1.,0.]) if abs(d[1])<.8 else np.array([0.,0.,1.]); u=np.cross(d,reference); u=u/np.linalg.norm(u); v=np.cross(d,u)
    corners=[start+u*width/2+v*thickness/2,start-u*width/2+v*thickness/2,start-u*width/2-v*thickness/2,start+u*width/2-v*thickness/2]
    wire=Part.makePolygon([App.Vector(*x) for x in corners]+[App.Vector(*corners[0])]); return Part.Face(wire).extrude(App.Vector(*delta))


def compile_robot_body(link_id):
    """Full Robot-A body recipes derived from the formal multi-view evidence."""
    features=[]
    if link_id=="L00":
        # Faceted base housing: intentionally no cylindrical placeholder body.
        # Keep the forward folding corridor of J02 clear at its authoritative
        # lower limit.  The raised turntable carries the shoulder; the wider
        # lower plinth does not extend into the folded wrist path.
        pts=[(-18,-8),(-8,-18),(8,-18),(18,-8),(18,8),(8,18),(-8,18),(-18,8)]
        wire=Part.makePolygon([App.Vector(x,y,0) for x,y in pts]+[App.Vector(pts[0][0],pts[0][1],0)])
        lower=Part.Face(wire).extrude(App.Vector(0,0,20)); top=_box(-11,11,-11,11,20,50.8); shape=lower.fuse(top).removeSplitter(); features=["faceted_base_housing","raised_turntable_support","full_azimuth_fold_clearance"]
    elif link_id=="L01":
        shape=_union([_box(-16,16,-7,7,5,36),_box(-20,20,-7,7,28,42.25)]); features=["shoulder_column","upper_clevis_transition"]
    elif link_id=="L02":
        start=[8,0,23]; end=[32,0,90]; left=_oriented_prism(start,end,22,4); left.translate(App.Vector(0,-9,0)); right=_oriented_prism(start,end,22,4); right.translate(App.Vector(0,9,0)); transition=_oriented_prism([3,0,9],[8,0,23],12,6)
        shape=_union([left,right,transition,_oriented_prism([9,-9,25],[9,9,25],5,16),_oriented_prism([31,-9,89],[31,9,89],5,16)]); features=["dual_side_plate","proximal_transition","proximal_cross_support","distal_cross_support","open_center"]
    elif link_id=="L03":
        web=_box(15,88,-5,5,-14,14); opening=_box(35,67,-8,8,-7,7); shape=web.cut(opening).removeSplitter(); features=["central_web","major_opening","proximal_transition","distal_transition"]
    elif link_id=="L04":
        shape=_union([_box(22,48,-7,7,-13,13),_box(24,58,-10,10,-10,10),_box(50,63,-12,12,-8,8)]); features=["stepped_wrist_housing","service_recess","rectangular_tool_transition","proximal_swept_clearance"]
    elif link_id=="L05":
        shape=_box(0,1.5,-12,12,-10,10); features=["wrist_roll_housing"]
    elif link_id=="L06":
        shape=_box(5,20,-8,8,-8,8); features=["roll_rotor_support"]
    elif link_id=="L07":
        shape=_union([_box(0,23,-7,7,-7,7),_box(12,23,-32,32,-6,6)]); features=["gripper_carriage","transverse_support"]
    elif link_id=="L08":
        palm=_box(-5,-2,-31,31,-7,7); gap=_box(-4,-1,-9,9,-9,9); shape=palm.cut(gap).removeSplitter(); features=["palm","rail_pair","working_gap","symmetric_supports"]
    elif link_id in ("L09","L10"):
        main=_prism_x([(-7,-9),(7,-9),(5,8),(-5,8)],8,40); neck=_box(2,10,-3,3,-4,4); recess=_box(25,43,-3,3,-3,7); shape=_union([main.cut(recess).removeSplitter(),neck]); features=["tapered_jaw","gripping_tip","inner_recess"]
    else: raise RuntimeError("EXECUTABLE_ROBOT_BODY_MISSING: "+link_id)
    return {"shape":shape,"executed_family":"robotA_"+link_id,"features":features,"valid":shape.isValid() and not shape.isNull()}


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
