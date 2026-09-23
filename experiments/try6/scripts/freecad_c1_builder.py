"""Build editable L04 feature history from a typed KFDG parameter table."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import FreeCAD as App
import Mesh
import Part
import Sketcher

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments/try5A/scripts"))
import freecad_motion_realization as frozen  # noqa: E402


def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def dump(path, value): Path(path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rect(sketch, x0, x1, y0, y1, bindings=None):
    corners = [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
    for a,b in zip(corners,corners[1:]+corners[:1]):
        sketch.addGeometry(Part.LineSegment(App.Vector(a[0],a[1],0),App.Vector(b[0],b[1],0)),False)
    sketch.addConstraint([
        Sketcher.Constraint("Coincident",0,2,1,1),
        Sketcher.Constraint("Coincident",1,2,2,1),
        Sketcher.Constraint("Coincident",2,2,3,1),
        Sketcher.Constraint("Coincident",3,2,0,1),
        Sketcher.Constraint("Horizontal",0),
        Sketcher.Constraint("Vertical",1),
        Sketcher.Constraint("Horizontal",2),
        Sketcher.Constraint("Vertical",3),
        Sketcher.Constraint("DistanceX",0,1,float(x0)),
        Sketcher.Constraint("DistanceY",0,1,float(y0)),
        Sketcher.Constraint("Distance",0,float(x1-x0)),
        Sketcher.Constraint("Distance",1,float(y1-y0))
    ])
    for key,expression in (bindings or {}).items():
        sketch.setExpression(f"Constraints[{dict(start_x=8,start_y=9,length_x=10,length_y=11)[key]}]",expression)


def yz_sketch(doc,name,x,width,height,width_expression=None,height_expression=None,x_expression=None):
    sketch=doc.addObject("Sketcher::SketchObject",name)
    sketch.Placement=App.Placement(App.Vector(x,0,0),App.Rotation(App.Vector(0,0,1),App.Vector(1,0,0)))
    if x_expression: sketch.setExpression("Placement.Base.x",x_expression)
    bindings={}
    if height_expression:
        bindings.update(start_x=f"-({height_expression})/2",length_x=height_expression)
    if width_expression:
        bindings.update(start_y=f"-({width_expression})/2",length_y=width_expression)
    rect(sketch,-height/2,height/2,-width/2,width/2,bindings)
    return sketch


def feature_state(obj):
    shape=obj.Shape
    return {"name":obj.Name,"type_id":obj.TypeId,"valid":not shape.isNull() and shape.isValid(),"volume_mm3":float(shape.Volume),"solids":len(shape.Solids),"faces":len(shape.Faces)}


def build(job):
    params=job["parameters"]; anchor=float(job["anchor_distance_mm"])
    if abs(anchor-63.0)>1e-9: raise ValueError("frozen J03-J04 anchor changed")
    graph=load(job["kfdg_path"])
    if graph["schema_version"]!="robotcad_kfdg_l04_v1" or graph["metric_anchor"]["distance_mm"]!=anchor: raise RuntimeError("KFDG/anchor mismatch")
    if {item["id"] for item in graph["parameter_nodes"]}!={*params}: raise RuntimeError("KFDG parameter identity mismatch")
    nodes={item["type"]:item["id"] for item in graph["geometric_features"]}
    if not {"housing","profile_transition","pocket","fillet"}<=set(nodes): raise RuntimeError("KFDG feature history incomplete")
    out=Path(job["output_root"]); out.mkdir(parents=True,exist_ok=True)
    doc=App.newDocument("Try6_C1_L04")
    sheet=doc.addObject("Spreadsheet::Sheet","ParameterTable")
    for index,(name,value) in enumerate(params.items(),start=1):
        sheet.set(f"A{index}",name)
        sheet.set(f"B{index}",f"{float(value)} mm")
        sheet.setAlias(f"B{index}",name)
    doc.recompute()
    body=doc.addObject("PartDesign::Body","ParametricHousing")
    main=yz_sketch(doc,"MainHousingSketch",0.0,params["housing_width_mm"],params["housing_height_mm"],"ParameterTable.housing_width_mm","ParameterTable.housing_height_mm")
    body.addObject(main)
    pad=body.newObject("PartDesign::Pad","MainHousingPad")
    pad.Profile=main; pad.Length=float(params["proximal_section_length_mm"])
    pad.setExpression("Length","ParameterTable.proximal_section_length_mm")
    doc.recompute()
    if pad.Shape.isNull() or not pad.Shape.isValid(): raise RuntimeError("main Sketch/Pad invalid")
    fillet=body.newObject("PartDesign::Fillet","VisibleEdgeFillet")
    fillet.Base=(pad,["Edge1"]); fillet.Radius=float(params["fillet_radius_mm"])
    fillet.setExpression("Radius","ParameterTable.fillet_radius_mm")
    doc.recompute()
    if fillet.Shape.isNull() or not fillet.Shape.isValid(): raise RuntimeError("PartDesign Fillet invalid")
    pocket_sketch=doc.addObject("Sketcher::SketchObject","VisibleRecessSketch")
    body.addObject(pocket_sketch)
    pocket_sketch.Placement=App.Placement(App.Vector(0,0,params["housing_height_mm"]/2),App.Rotation())
    pocket_sketch.setExpression("Placement.Base.z","ParameterTable.housing_height_mm/2")
    start=params["proximal_section_length_mm"]*.1
    rect(pocket_sketch,start,start+params["recess_length_mm"],-params["housing_width_mm"]*.3,params["housing_width_mm"]*.3,{"start_x":"ParameterTable.proximal_section_length_mm*0.1","start_y":"-ParameterTable.housing_width_mm*0.3","length_x":"ParameterTable.recess_length_mm","length_y":"ParameterTable.housing_width_mm*0.6"})
    pocket=body.newObject("PartDesign::Pocket","VisibleRecessPocket")
    pocket.Profile=pocket_sketch; pocket.Length=float(params["recess_depth_mm"])
    pocket.setExpression("Length","ParameterTable.recess_depth_mm")
    doc.recompute()
    if pocket.Shape.isNull() or not pocket.Shape.isValid(): raise RuntimeError("PartDesign Pocket invalid")
    start_section=yz_sketch(doc,"TransitionStart",params["proximal_section_length_mm"],params["housing_width_mm"],params["housing_height_mm"],"ParameterTable.housing_width_mm","ParameterTable.housing_height_mm","ParameterTable.proximal_section_length_mm")
    middle_section=yz_sketch(doc,"TransitionMiddle",params["proximal_section_length_mm"]+params["transition_length_mm"],(params["housing_width_mm"]+params["distal_width_mm"])/2,(params["housing_height_mm"]+params["distal_height_mm"])/2,"(ParameterTable.housing_width_mm+ParameterTable.distal_width_mm)/2","(ParameterTable.housing_height_mm+ParameterTable.distal_height_mm)/2","ParameterTable.proximal_section_length_mm+ParameterTable.transition_length_mm")
    end_section=yz_sketch(doc,"TransitionEnd",anchor,params["distal_width_mm"],params["distal_height_mm"],"ParameterTable.distal_width_mm","ParameterTable.distal_height_mm")
    loft=doc.addObject("Part::Loft","ProfileTransitionLoft")
    loft.Sections=[start_section,middle_section,end_section]; loft.Solid=True; loft.Ruled=False
    doc.recompute()
    if loft.Shape.isNull() or not loft.Shape.isValid(): raise RuntimeError("profile transition Loft invalid")
    join=doc.addObject("Part::Fuse","HousingWithTransition")
    join.Base=pocket; join.Tool=loft
    doc.recompute()
    if join.Shape.isNull() or not join.Shape.isValid(): raise RuntimeError("housing transition fusion invalid")
    contracts=load(ROOT/job["frozen_interface_contracts"])
    proximal=next(item for item in contracts if item["joint_id"]=="J03")
    axis=frozen.unit(proximal["axis_child"])
    bore_tool=doc.addObject("Part::Feature","FrozenProximalBoreTool")
    bore_tool.Shape=frozen.cylinder_axis(3+proximal["clearance_mm"],26,[0,0,0],axis)
    bore=doc.addObject("Part::Cut","FrozenProximalBore")
    bore.Base=join; bore.Tool=bore_tool
    mate_contract=dict(proximal); mate_contract["origin_xyz_mm"]=[0,0,0]; mate_contract["axis_parent"]=mate_contract["axis_child"]
    mate_shape,_=frozen.joint_half(mate_contract,"parent")
    mate_tool=doc.addObject("Part::Feature","FrozenMatingEnvelopeTool"); mate_tool.Shape=mate_shape
    mate_cut=doc.addObject("Part::Cut","FrozenMatingEnvelopeCut"); mate_cut.Base=bore; mate_cut.Tool=mate_tool
    doc.recompute()
    if mate_cut.Shape.isNull() or not mate_cut.Shape.isValid(): raise RuntimeError("frozen interface opening invalid")
    scaffold_doc=App.openDocument(str(ROOT/job["f0_fcstd"]))
    scaffold_shape=scaffold_doc.getObject("RigidGroup").Shape.copy(); App.closeDocument(scaffold_doc.Name)
    scaffold=doc.addObject("Part::Feature","FrozenScaffold"); scaffold.Shape=scaffold_shape
    final=doc.addObject("Part::Fuse","RigidGroup"); final.Base=mate_cut; final.Tool=scaffold
    doc.recompute()
    if final.Shape.isNull() or not final.Shape.isValid(): raise RuntimeError("final scaffold fusion invalid")
    mapping={"proximal_joint_port":["FrozenProximalBore","FrozenMatingEnvelopeCut"],"distal_mount_port":["ProfileTransitionLoft"],nodes["housing"]:["MainHousingSketch","MainHousingPad"],nodes["profile_transition"]:["TransitionStart","TransitionMiddle","TransitionEnd","ProfileTransitionLoft"],nodes["pocket"]:["VisibleRecessSketch","VisibleRecessPocket"],nodes["fillet"]:["VisibleEdgeFillet"],"scaffold_safeguard":["FrozenScaffold","RigidGroup"]}
    tree=[feature_state(obj) for obj in (pad,fillet,pocket,loft,join,bore,mate_cut,final)]
    for item in tree:
        if not item["valid"]: raise RuntimeError(f"invalid feature: {item['name']}")
    doc.saveAs(str(out/"final.FCStd"))
    Part.export([final],str(out/"final.step"))
    Mesh.export([final],str(out/"final.stl"))
    Mesh.export([mate_cut],str(out/"body_only.stl"))
    volume=float(final.Shape.Volume)
    App.closeDocument(doc.Name)
    reopened=App.openDocument(str(out/"final.FCStd"))
    reopened.recompute()
    obj=reopened.getObject("RigidGroup")
    reopen={"valid":obj is not None and not obj.Shape.isNull() and obj.Shape.isValid(),"volume_mm3":float(obj.Shape.Volume) if obj else None,"tree_nodes":len(reopened.Objects)}
    App.closeDocument(reopened.Name)
    if not reopen["valid"]: raise RuntimeError("saved FCStd did not reopen/recompute")
    dump(out/"feature_mapping.json",{"kfdg_path":str(Path(job["kfdg_path"]).relative_to(ROOT)).replace("\\","/"),"kfdg_to_cad":mapping,"feature_tree":tree,"parameter_binding":{"sheet":"ParameterTable","builder_source":"experiments/try6/scripts/freecad_c1_builder.py","values":params},"final_reopen":reopen})
    payload={"status":"PASS","mode":job["mode"],"feature_tree":tree,"final_volume_mm3":volume,"final_solid_count":tree[-1]["solids"],"reopen":reopen,"artifacts":{key:sha(out/name) for key,name in (("fcstd","final.FCStd"),("step","final.step"),("stl","final.stl"),("body_stl","body_only.stl"))}}
    dump(out/"build_result.json",payload)
    print(json.dumps({"status":"PASS","final_volume_mm3":volume,"final_solid_count":tree[-1]["solids"]},indent=2))


if __name__=="__main__": build(load(sys.argv[1]))
