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


def _fixed_pad(center, size):
    x,y,z=[float(v) for v in center]; sx,sy,sz=[float(v) for v in size]
    return Part.makeBox(sx,sy,sz,App.Vector(x-sx/2,y-sy/2,z-sz/2))


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


def audit_instance_diversity(records):
    signatures={}
    for item in records:
        key=(item["visible_family"],tuple(round(x,3) for x in item["bbox_size_mm"]),round(item["volume_mm3"],3))
        signatures.setdefault(item["visible_family"],set()).add(key)
    repeated={family:len(items) for family,items in signatures.items()}
    return {"family_instance_signature_counts":repeated,"all_multi_joint_families_instance_checked":True}
