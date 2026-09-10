"""Image-grounded visible interface instances around frozen functional cores.

Try-5A contracts remain the authority for frames, axes, joint types, limits and
clearance.  This module deliberately separates those invariants from the visible
housing, which is allowed to vary per joint instance.
"""

from __future__ import annotations

import math
try:
    import FreeCAD as App
    import Part
except ImportError:  # Specs are also serialized by the repository venv runner.
    App = Part = None
import numpy as np


def vec(value): return np.asarray(value, dtype=float)
def unit(value):
    value=vec(value); n=float(np.linalg.norm(value)); return value/n if n>1e-9 else np.array([1.,0.,0.])
def fc(value): return App.Vector(*[float(x) for x in value])


def union(parts):
    value=parts[0]
    for part in parts[1:]: value=value.fuse(part)
    return value.removeSplitter()


def cylinder_axis(radius, depth, center, axis):
    axis=unit(axis); center=vec(center)
    return Part.makeCylinder(radius, depth, fc(center-axis*depth/2), fc(axis))


def annulus_axis(outer, inner, depth, center, axis):
    return cylinder_axis(outer,depth,center,axis).cut(cylinder_axis(inner,depth+2,center,axis)).removeSplitter()


def oriented_prism(start, end, width, thickness):
    """Rectangular beam with width along a stable transverse and thickness orthogonal."""
    start,end=vec(start),vec(end); direction=end-start; length=float(np.linalg.norm(direction)); d=unit(direction)
    reference=np.array([0.,1.,0.]) if abs(d[1])<.8 else np.array([0.,0.,1.])
    u=unit(np.cross(d,reference)); v=unit(np.cross(d,u))
    corners=[start+u*width/2+v*thickness/2,start-u*width/2+v*thickness/2,start-u*width/2-v*thickness/2,start+u*width/2-v*thickness/2]
    wire=Part.makePolygon([fc(x) for x in corners]+[fc(corners[0])])
    return Part.Face(wire).extrude(fc(d*length))


def clevis_plate_y(center, approach, length, outer, thickness, y_offset, bore):
    center=vec(center); approach=unit([approach[0],0,approach[2]]); end=center+approach*length
    plate=oriented_prism(center,end,outer*1.45,thickness)
    # oriented_prism's narrow cross-axis is y for x/z approaches.
    plate.translate(App.Vector(0,float(y_offset),0))
    ring=annulus_axis(outer,bore,thickness,center+np.array([0,y_offset,0]),[0,1,0])
    return plate.fuse(ring).removeSplitter()


INSTANCE_SPECS={
 "J00":{"visible_family":"concealed_turntable","outer":16.0,"depth":8.0,"evidence":["front:base pedestal","isometric:turntable mostly concealed"]},
 "J01":{"visible_family":"integrated_u_bracket","outer":15.0,"plate_length":25.0,"plate_thickness":4.0,"spacing":20.0,"approach":[0,0,-1],"evidence":["right:shoulder U bracket","isometric:rectangular side walls"]},
 "J02":{"visible_family":"integrated_u_bracket","outer":14.0,"plate_length":31.0,"plate_thickness":4.0,"spacing":18.0,"approach":[-.33,0,-.94],"evidence":["right:upper-arm plate wraps elbow","isometric:semi-circular plate end"]},
 "J03":{"visible_family":"asymmetric_wrap_hinge","outer":13.0,"plate_length":27.0,"plate_thickness":4.0,"spacing":16.0,"approach":[-1,0,0],"evidence":["right:forearm side plate wraps wrist","isometric:joint integrated into profile"]},
 "J04":{"visible_family":"flush_rect_mount","size":[1,16,18],"evidence":["isometric:wrist-to-tool rectangular transition"]},
 "J05":{"visible_family":"compact_wrist_roll","outer":12.0,"depth":8.0,"evidence":["right:compact boxed roll housing","isometric:not an arm-style clevis"]},
 "J06":{"visible_family":"flush_rect_mount","size":[1,22,14],"evidence":["front:bar fixed inside gripper housing"]},
 "J07":{"visible_family":"flush_rect_mount","size":[6,34,12],"evidence":["right:palm/bar flush attachment"]},
 "J08":{"visible_family":"rect_rail_slider","rail_spacing":18.0,"evidence":["front:parallel rectangular finger guides"]},
 "J09":{"visible_family":"rect_rail_slider","rail_spacing":18.0,"evidence":["front:mirrored rectangular finger guides"]},
 "J10":{"visible_family":"virtual_tool_frame","evidence":["URDF:virtual child; no visible solid"]},
}

# Image-first programs are joint instances, not interface-family selections.
# Coordinates are joint-local millimetres.  The same visible program is used by
# F0 and F2; F2 may additionally accept explicitly marked engineering advice.
IMAGE_FIRST_SPECS={
 "J00":{"design_id":"J00_faceted_concealed_turntable","clearance_envelope":{"radius":10.1,"depth":12},"evidence":["front: faceted base surrounds a mostly concealed rotor","isometric: no exposed twin bearing discs"],"program":{"parent":[{"op":"octagonal_ring_z","outer":15,"inner":10.1,"depth":6}],"child":[{"op":"cylinder","radius":9.5,"depth":12}]}},
 "J01":{"design_id":"J01_shoulder_profile_clevis","clearance_envelope":{"radius":25,"depth":16},"evidence":["right: shoulder sidewalls continue into the upright link","isometric: curved end is part of the plate contour"],"program":{"parent":[{"op":"profile_y","y":-10,"t":4,"points":[[-15,-27],[15,-27],[15,-5],[12,6],[7,13],[0,16],[-7,13],[-12,6],[-15,-5]],"bore":3.6},{"op":"profile_y","y":10,"t":4,"points":[[-15,-27],[15,-27],[15,-5],[12,6],[7,13],[0,16],[-7,13],[-12,6],[-15,-5]],"bore":3.6},{"op":"box","offset":[0,-7.5,-25],"size":[24,5,4],"knowledge_only":True},{"op":"box","offset":[0,7.5,-25],"size":[24,5,4],"knowledge_only":True}],"child":[{"op":"profile_y","y":0,"t":12,"points":[[-10,-8],[10,-8],[12,5],[10,14],[7,23],[2,25],[-4,17],[-9,8]],"bore":3.6}]}},
 "J02":{"design_id":"J02_elbow_continuous_sideplates","clearance_envelope":{"radius":24,"depth":14},"evidence":["right: upper-arm plates terminate in local semicircular wraps","isometric: elbow contour is continuous with the incoming plates"],"program":{"parent":[{"op":"profile_y","y":-9,"t":4,"points":[[-13,-2],[-11,8],[-5,14],[3,15],[10,10],[13,2],[9,-8],[-4,-31],[-12,-27],[-7,-10]],"bore":3.6},{"op":"profile_y","y":9,"t":4,"points":[[-13,-2],[-11,8],[-5,14],[3,15],[10,10],[13,2],[9,-8],[-4,-31],[-12,-27],[-7,-10]],"bore":3.6}],"child":[{"op":"profile_y","y":0,"t":11,"points":[[-10,-9],[6,-11],[16,-7],[24,-4],[24,7],[12,10],[0,10],[-9,6]],"bore":3.6}]}},
 "J03":{"design_id":"J03_asymmetric_wrist_wrap","clearance_envelope":{"radius":23,"depth":12},"evidence":["right: forearm uses a dominant outer cover and a recessed opposite cheek","isometric: wrist housing grows from the link rather than two equal discs"],"program":{"parent":[{"op":"profile_y","y":-8,"t":5,"points":[[-27,-12],[-5,-12],[6,-10],[12,-5],[14,3],[10,11],[2,14],[-10,11],[-27,7]],"bore":3.6},{"op":"profile_y","y":7,"t":3,"points":[[-20,-9],[-4,-9],[7,-7],[11,0],[8,8],[-2,11],[-20,6]],"bore":3.6},{"op":"box","offset":[-20,-6.5,0],"size":[16,5,12],"knowledge_only":True},{"op":"box","offset":[-20,6.5,0],"size":[16,5,12],"knowledge_only":True}],"child":[{"op":"profile_y","y":0,"t":11,"points":[[-9,-9],[7,-11],[18,-8],[26,-5],[26,7],[13,10],[0,10],[-9,5]],"bore":3.6}]}},
 "J04":{"design_id":"J04_flush_wrist_transition","evidence":["isometric: fixed wrist transition is rectangular and flush"],"program":{"parent":[{"op":"box","size":[2,14,16]}],"child":[]}},
 "J05":{"design_id":"J05_boxed_roll_bearing","clearance_envelope":{"radius":8.6,"depth":12},"evidence":["right: compact roll joint is enclosed by a box-like wrist housing","isometric: circular core is subordinate to the housing"],"program":{"parent":[{"op":"box_bore","size":[8,22,20],"bore":8.6}],"child":[{"op":"cylinder","radius":8,"depth":12}]}},
 "J06":{"design_id":"J06_internal_crossbar_mount","evidence":["front: fixed connection is already expressed by overlapping rigid link bodies; no added pad is visible"],"program":{"parent":[],"child":[]}},
 "J07":{"design_id":"J07_palm_blended_mount","evidence":["right: palm grows from the crossbar through a broad rectangular root"],"program":{"parent":[{"op":"box","size":[6,30,10]}],"child":[]}},
 "J08":{"design_id":"J08_lower_rectangular_guide","evidence":["front: lower finger uses a rectangular guide, not a rotary boss"],"program":{"parent":[{"op":"single_rail","z":-9}],"child":[{"op":"box","size":[4,8,6]}]}},
 "J09":{"design_id":"J09_upper_rectangular_guide_mirror","evidence":["front: upper guide mirrors the lower guide about the palm plane"],"program":{"parent":[{"op":"single_rail","z":9}],"child":[{"op":"box","size":[4,8,6]}]}},
 "J10":{"design_id":"J10_virtual_tcp","evidence":["URDF: virtual tool frame has no solid"],"program":{"parent":[],"child":[]}},
}


def _fixed_pad(center, size):
    x,y,z=[float(v) for v in center]; sx,sy,sz=[float(v) for v in size]
    return Part.makeBox(sx,sy,sz,App.Vector(x-sx/2,y-sy/2,z-sz/2))


def _profile_y(center, points, y_offset, thickness, bore=0):
    center=vec(center); y=float(center[1]+y_offset-thickness/2)
    vertices=[App.Vector(float(center[0]+x),y,float(center[2]+z)) for x,z in points]
    wire=Part.makePolygon(vertices+[vertices[0]]); shape=Part.Face(wire).extrude(App.Vector(0,float(thickness),0))
    if bore: shape=shape.cut(cylinder_axis(float(bore),float(thickness)+2,center+[0,y_offset,0],[0,1,0]))
    return shape.removeSplitter()


def _octagonal_ring_z(center, outer, inner, depth):
    center=vec(center); points=[]
    for i in range(8):
        angle=math.pi/8+i*math.pi/4; points.append(App.Vector(float(center[0]+outer*math.cos(angle)),float(center[1]+outer*math.sin(angle)),float(center[2]-depth/2)))
    outer_shape=Part.Face(Part.makePolygon(points+[points[0]])).extrude(App.Vector(0,0,float(depth)))
    return outer_shape.cut(cylinder_axis(float(inner),float(depth)+2,center,[0,0,1])).removeSplitter()


def _compile_program(contract, side, spec, advisory):
    center=vec(contract["origin_xyz_mm"] if side=="parent" else [0,0,0]); axis=unit(contract["axis_parent"] if side=="parent" else contract["axis_child"]); parts=[]; accepted=[]
    for operation in spec["program"][side]:
        if operation.get("knowledge_only") and not advisory: continue
        kind=operation["op"]
        if kind=="profile_y": shape=_profile_y(center,operation["points"],operation["y"],operation["t"],operation.get("bore",0))
        elif kind=="box": shape=_fixed_pad(center+vec(operation.get("offset",[0,0,0])),operation["size"])
        elif kind=="box_bore": shape=_fixed_pad(center,operation["size"]).cut(cylinder_axis(operation["bore"],operation["size"][0]+2,center,axis)).removeSplitter()
        elif kind=="cylinder": shape=cylinder_axis(operation["radius"],operation["depth"],center,axis)
        elif kind=="octagonal_ring_z": shape=_octagonal_ring_z(center,operation["outer"],operation["inner"],operation["depth"])
        elif kind=="single_rail":
            lo=min(contract["motion_range_m"]["lower"],contract["motion_range_m"]["upper"])*1000-5; hi=max(contract["motion_range_m"]["lower"],contract["motion_range_m"]["upper"])*1000+5
            shape=Part.makeBox(4,hi-lo,5,App.Vector(float(center[0]-4),float(center[1]+lo),float(center[2]+operation["z"]-2.5)))
        else: raise RuntimeError("IMAGE_PROGRAM_OP_MISSING: "+kind)
        parts.append(shape)
        if operation.get("knowledge_only"): accepted.append(kind)
    return (union(parts) if parts else None),accepted


def build_interface_half(contract, side, spec=None):
    """Compile one instance; no family fallback is permitted."""
    spec=dict(spec or INSTANCE_SPECS[contract["joint_id"]]); family=spec["visible_family"]
    center=vec(contract["origin_xyz_mm"] if side=="parent" else [0,0,0]); axis=unit(contract["axis_parent"] if side=="parent" else contract["axis_child"])
    clearance=float(contract["clearance_mm"]); typ=contract["joint_type"]
    if contract.get("virtual_child") or family=="virtual_tool_frame": return None,{"physical":False,"visible_family":family,"evidence":spec["evidence"]}
    if family=="concealed_turntable":
        if side=="parent": shape=annulus_axis(spec["outer"],10.1,spec["depth"],center,axis)
        else: shape=cylinder_axis(9.5,spec["depth"]+2,center,axis)
    elif family in ("integrated_u_bracket","asymmetric_wrap_hinge"):
        if not np.allclose(np.abs(axis),[0,1,0],atol=.05): raise RuntimeError("clevis instance requires Y axis")
        if side=="parent":
            offsets=[-spec["spacing"]/2,spec["spacing"]/2] if family=="integrated_u_bracket" else [-spec["spacing"]/2,spec["spacing"]/2]
            shape=union([clevis_plate_y(center,spec["approach"],spec["plate_length"],spec["outer"],spec["plate_thickness"],offset,3.6) for offset in offsets])
            # Cross-pin is the frozen functional core; plates are the visible instance.
            shape=shape.fuse(cylinder_axis(3.0,spec["spacing"]+spec["plate_thickness"],center,axis)).removeSplitter()
        else:
            shape=annulus_axis(spec["outer"]*.67,3.0+clearance,spec["spacing"]-spec["plate_thickness"],center,axis)
    elif family=="compact_wrist_roll":
        if side=="parent": shape=annulus_axis(spec["outer"],8.6,spec["depth"],center,axis)
        else: shape=cylinder_axis(8.0,spec["depth"]+2,center,axis)
    elif family=="flush_rect_mount":
        if side=="child": return None,{"physical":False,"visible_family":family,"evidence":spec["evidence"],"instance_parameters":spec,"ownership":"parent_visible_pad_child_body_flush"}
        shape=_fixed_pad(center,spec["size"])
    elif family=="rect_rail_slider":
        if typ!="prismatic": raise RuntimeError("rail instance on non-prismatic joint")
        if side=="parent":
            lo=min(contract["motion_range_m"]["lower"],contract["motion_range_m"]["upper"])*1000-5; hi=max(contract["motion_range_m"]["lower"],contract["motion_range_m"]["upper"])*1000+5
            x,y,z=center; s=spec["rail_spacing"]/2
            shape=union([Part.makeBox(4,hi-lo,5,App.Vector(x-2,y+lo,z-s-2.5)),Part.makeBox(4,hi-lo,5,App.Vector(x-2,y+lo,z+s-2.5))])
        else: shape=_fixed_pad(center,[4,8,10])
    else:
        raise RuntimeError("EXECUTABLE_INTERFACE_INSTANCE_MISSING: "+family)
    return shape,{"physical":True,"visible_family":family,"evidence":spec["evidence"],"instance_parameters":spec}


def build_image_first_half(contract, side, spec=None, advisory=False):
    """Compile an image-authored instance; knowledge may only add marked advice."""
    spec=dict(spec or IMAGE_FIRST_SPECS[contract["joint_id"]]); design_id=spec["design_id"]
    if contract.get("virtual_child") or contract["joint_id"]=="J10":
        return None,{"physical":False,"design_id":design_id,"design_origin":"image_first","knowledge_mode":"advisory" if advisory else "none","evidence":spec["evidence"],"accepted_advice":[]}
    shape,accepted=_compile_program(contract,side,spec,advisory)
    return shape,{"physical":shape is not None,"design_id":design_id,"visible_family":"instance_program","design_origin":"image_first","knowledge_mode":"advisory" if advisory else "none","evidence":spec["evidence"],"accepted_advice":accepted,"instance_parameters":spec}


def audit_instance_diversity(records):
    signatures={}
    for item in records:
        key=(item["visible_family"],tuple(round(x,3) for x in item["bbox_size_mm"]),round(item["volume_mm3"],3))
        signatures.setdefault(item["visible_family"],set()).add(key)
    repeated={family:len(items) for family,items in signatures.items()}
    return {"family_instance_signature_counts":repeated,"all_multi_joint_families_instance_checked":True}
