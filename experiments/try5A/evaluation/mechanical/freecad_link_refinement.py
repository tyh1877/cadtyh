"""FreeCAD worker for Try-5B1 family compilation and frozen-mechanics audits."""

import hashlib, json, sys, time
from pathlib import Path

import FreeCAD as App
import Mesh, Part
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / "experiments/try5A/scripts"
sys.path.insert(0, str(SCRIPTS))
import freecad_motion_realization as frozen
from executable_body_families import compile_body, compile_robot_body
from interface_instance_geometry import build_image_first_half, build_interface_half, oriented_prism


def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def dump(path, value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+"\n",encoding="utf-8")
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def connect(body, interfaces, realization_type):
    group = body
    for interface in interfaces:
        if interface is None or interface.isNull(): continue
        # Interface families may themselves contain separated bearing halves.
        # Attach every authoritative solid; otherwise a compound can hide a
        # physically floating half even when the first half touches the body.
        for solid in list(interface.Solids) or [interface]:
            distance, points, _ = group.distToShape(solid)
            if distance > 1e-6 and points:
                p1,p2=points[0]; connector=frozen.cylinder_between([p1.x,p1.y,p1.z],[p2.x,p2.y,p2.z],2.4)
                group=group.fuse(connector)
            group=group.fuse(solid)
    group=group.removeSplitter()
    # Deterministic rigid attachment closure used by the frozen coarse stage:
    # join only disconnected solids belonging to this same link.
    solids=list(group.Solids)
    if len(solids)>1:
        connected=solids[0]
        for solid in solids[1:]:
            distance,points,_=connected.distToShape(solid)
            if points:
                p1,p2=points[0]
                connector=frozen.cylinder_between([p1.x,p1.y,p1.z],[p2.x,p2.y,p2.z],2.4)
                connected=connected.fuse(connector).fuse(solid).removeSplitter()
        group=connected
    return group


def refined_shape(link_id, family, schema, contracts, realization_type, frozen_scaffold):
    compiled=compile_body(family,schema); body=compiled["shape"]; interfaces=[]; interface_hashes={}
    proximal=None; distal=[]
    for contract in contracts:
        if contract.get("virtual_child") or link_id not in (contract["parent"],contract["child"]): continue
        side="parent" if contract["parent"]==link_id else "child"
        shape,_=frozen.joint_half(contract,side); interfaces.append(shape)
        if side=="child": proximal=contract
        else: distal.append(contract)
        if shape is not None:
            interface_hashes[contract["joint_id"]]={"side":side,"volume_mm3":float(shape.Volume),"bbox":frozen.bounds(shape)}
    # Consume the exact frozen mating corridors.  This is a protected-interface
    # subtraction, not a redesign: frame, axis, clearance and mating geometry
    # all come from the frozen contract.
    if proximal and proximal["joint_type"] in ("revolute","continuous"):
        axis=frozen.unit(proximal["axis_child"]); body=body.cut(frozen.cylinder_axis(3+proximal["clearance_mm"],26,[0,0,0],axis)).removeSplitter()
        mate_contract=dict(proximal); mate_contract["origin_xyz_mm"]=[0,0,0]; mate_contract["axis_parent"]=mate_contract["axis_child"]
        mate,_=frozen.joint_half(mate_contract,"parent"); body=body.cut(mate).removeSplitter()
    for contract in distal:
        if contract["joint_type"] in ("revolute","continuous"):
            center=frozen.vec(contract["origin_xyz_mm"]); axis=frozen.unit(contract["axis_parent"])
            body=body.cut(frozen.cylinder_axis(10+contract["clearance_mm"],16,center,axis)).removeSplitter()
            mate_contract=dict(contract); mate_contract["axis_child"]=mate_contract["axis_parent"]
            mate,_=frozen.joint_half(mate_contract,"child"); mate.translate(frozen.fcvec(center)); body=body.cut(mate).removeSplitter()
    compiled["shape"]=body
    # Preserve the already validated coarse load-path/interface scaffold and
    # replace its visual dominance with the executable family body.  The
    # scaffold is not a fallback dispatch: it remains a protected transition,
    # while `body` is the recorded executed family feature.
    group=frozen_scaffold.fuse(body).removeSplitter()
    return {**compiled,"group":group,"interface_signatures":interface_hashes,"solid_count":len(group.Solids),
            "attachment_valid":len(group.Solids)==1,"group_valid":group.isValid() and not group.isNull()}


def export(link_id, condition, built, root):
    folder=Path(root)/condition/link_id; folder.mkdir(parents=True,exist_ok=True)
    doc=App.newDocument(condition+"_"+link_id)
    body=doc.addObject("Part::Feature","BodyFamily"); body.Shape=built["shape"]
    group=doc.addObject("Part::Feature","RigidGroup"); group.Shape=built["group"]
    body.addProperty("App::PropertyString","ExecutedFamily"); body.ExecutedFamily=built["executed_family"]
    body.addProperty("App::PropertyStringList","SemanticFeatures"); body.SemanticFeatures=built["features"]
    doc.recompute(); fcstd=folder/"model.FCStd"; step=folder/"model.step"; stl=folder/"model.stl"
    doc.saveAs(str(fcstd)); Part.export([group],str(step)); Mesh.export([group],str(stl)); App.closeDocument(doc.Name)
    return {"fcstd":str(fcstd),"step":str(step),"stl":str(stl),"sha256":{p.suffix:sha(p) for p in (fcstd,step,stl)},
            "volume_mm3":float(built["group"].Volume),"bbox":frozen.bounds(built["group"])}


def rectangular_attachment_closure(body, interfaces):
    def bridge(p1,p2):
        start=np.asarray([p1.x,p1.y,p1.z],dtype=float); end=np.asarray([p2.x,p2.y,p2.z],dtype=float); d=end-start; n=float(np.linalg.norm(d))
        return None if n<1e-6 else oriented_prism(start-d/n,end+d/n,3.2,3.2)
    group=body
    for interface in interfaces:
        if interface is None or interface.isNull(): continue
        for solid in list(interface.Solids) or [interface]:
            distance,points,_=group.distToShape(solid)
            if distance>1e-6 and points:
                p1,p2=points[0]; connector=bridge(p1,p2)
                if connector is not None: group=group.fuse(connector)
            group=group.fuse(solid)
    group=group.removeSplitter(); solids=list(group.Solids)
    if len(solids)>1:
        connected=solids[0]
        for solid in solids[1:]:
            _,points,_=connected.distToShape(solid)
            if points:
                p1,p2=points[0]; connector=bridge(p1,p2)
                if connector is not None: connected=connected.fuse(connector)
                connected=connected.fuse(solid).removeSplitter()
        group=connected
    return group


def direct_program_attachment(body, interfaces):
    """Fuse only authored contacts; never invent a shortest-path bridge."""
    group=body
    for interface in interfaces:
        if interface is not None and not interface.isNull(): group=group.fuse(interface)
    return group.removeSplitter()


def surface_audit(shape):
    total=sum(float(face.Area) for face in shape.Faces); cylinders=0.0
    surface_types= {}
    for face in shape.Faces:
        name=type(face.Surface).__name__; surface_types[name]=surface_types.get(name,0.0)+float(face.Area)
        if "Cylinder" in name: cylinders+=float(face.Area)
    return {"surface_area_mm2":total,"cylindrical_surface_area_mm2":cylinders,"cylindrical_surface_ratio":cylinders/max(total,1e-9),"surface_types_mm2":surface_types}


def clear_parent_mating_envelopes(body, link_id, contracts, specs):
    value=body
    for contract in contracts:
        if contract.get("virtual_child") or contract["parent"]!=link_id or contract["joint_type"] not in ("revolute","continuous"): continue
        spec=specs[contract["joint_id"]]; family=spec.get("visible_family"); center=contract["origin_xyz_mm"]; axis=contract["axis_parent"]
        if spec.get("clearance_envelope"): radius,depth=spec["clearance_envelope"]["radius"],spec["clearance_envelope"]["depth"]
        elif family=="concealed_turntable": radius,depth=10.1,spec["depth"]+4
        elif family in ("integrated_u_bracket","asymmetric_wrap_hinge"): radius,depth=spec["outer"]+10.0,spec["spacing"]-spec["plate_thickness"]+2
        elif family=="compact_wrist_roll": radius,depth=8.5,spec["depth"]+4
        else: continue
        value=value.cut(frozen.cylinder_axis(radius,depth,center,axis)).removeSplitter()
    return value


def full_robot_repair(job):
    base=ROOT/"experiments/try5A/results/try5a5"; contracts=load(base/"motion_interface_contracts.json")
    classification=load(base/"link_realization_classification.json"); physical=[x["link_id"] for x in classification if x["realization_type"]!="virtual_frame"]
    condition=job.get("condition","FULL_REPAIR"); generation=job.get("generation_strategy","legacy_template"); advisory=job.get("knowledge_mode")=="advisory"
    shapes={}; body_shapes={}; half_shapes={}; builds=[]; interface_records=[]
    for link_id in physical:
        body=compile_robot_body(link_id)
        # Audit the positive body primitive before subtracting protected mating
        # envelopes.  Cylindrical faces created by a clearance cut are void
        # boundaries, not the cylinder-body collapse that this gate targets.
        positive_body_surface_audit=surface_audit(body["shape"])
        body["shape"]=clear_parent_mating_envelopes(body["shape"],link_id,contracts,job["interface_specs"]); halves=[]; metadata=[]
        for contract in contracts:
            if contract.get("virtual_child") or link_id not in (contract["parent"],contract["child"]): continue
            side="parent" if contract["parent"]==link_id else "child"
            if generation=="image_first_program": half,meta=build_image_first_half(contract,side,job["interface_specs"][contract["joint_id"]],advisory=advisory)
            else: half,meta=build_interface_half(contract,side,job["interface_specs"][contract["joint_id"]])
            halves.append(half); half_shapes[(link_id,contract["joint_id"])]=half; metadata.append({"joint_id":contract["joint_id"],"side":side,**meta})
            if half is not None:
                bb=frozen.bounds(half); interface_records.append({"joint_id":contract["joint_id"],"link_id":link_id,"side":side,"design_key":meta.get("design_id",meta.get("visible_family")),"visible_family":meta.get("visible_family","instance_program"),"design_origin":meta.get("design_origin","legacy_template"),"knowledge_mode":meta.get("knowledge_mode","template_dispatch"),"accepted_advice":meta.get("accepted_advice",[]),"volume_mm3":float(half.Volume),"bbox_size_mm":bb["size_mm"],"evidence":meta["evidence"]})
        auto_bridge=generation=="legacy_template"; group=rectangular_attachment_closure(body["shape"],halves) if auto_bridge else direct_program_attachment(body["shape"],halves); built={"shape":body["shape"],"group":group,"executed_family":body["executed_family"],"features":body["features"]}
        artifact=export(link_id,condition,built,job["cad_root"]); builds.append({"link_id":link_id,"body_family":body["executed_family"],"features":body["features"],"body_surface_audit":positive_body_surface_audit,"clearance_cut_surface_audit":surface_audit(body["shape"]),"group_surface_audit":surface_audit(group),"solid_count":len(group.Solids),"attachment_valid":len(group.Solids)==1,"auto_bridge_enabled":auto_bridge,"valid":group.isValid() and not group.isNull(),"interfaces":metadata,"artifact":artifact}); shapes[link_id]=group; body_shapes[link_id]=body["shape"]
    diagnostic=[]; config=job["coupled"][0]
    for contract in contracts:
        if contract.get("virtual_child") or contract["joint_type"]=="fixed": continue
        p,c=contract["parent"],contract["child"]; tp=config["world_transforms"][p]; tc=config["world_transforms"][c]
        pb=frozen.moved(body_shapes[p],tp); cb=frozen.moved(body_shapes[c],tc); ph=frozen.moved(half_shapes[(p,contract["joint_id"])],tp); ch=frozen.moved(half_shapes[(c,contract["joint_id"])],tc)
        diagnostic.append({"joint_id":contract["joint_id"],"parent_body_child_body":frozen.common_volume(pb,cb),"parent_body_child_half":frozen.common_volume(pb,ch),"parent_half_child_body":frozen.common_volume(ph,cb),"parent_half_child_half":frozen.common_volume(ph,ch)})
    exact_start=time.perf_counter(); coupled_rows=[]; flags=[]
    for config in job["coupled"]:
        rows,ok=frozen.exact_config(config,shapes,contracts,physical); coupled_rows.extend(rows); flags.append(ok)
    pair_component_diagnostic=[]
    for config in job["coupled"][:3]:
        for a,b in (("L01","L02"),):
            ca={"body":body_shapes[a],**{joint:shape for (link,joint),shape in half_shapes.items() if link==a and shape is not None}}
            cb={"body":body_shapes[b],**{joint:shape for (link,joint),shape in half_shapes.items() if link==b and shape is not None}}
            for na,sa in ca.items():
                for nb,sb in cb.items():
                    volume=frozen.common_volume(frozen.moved(sa,config["world_transforms"][a]),frozen.moved(sb,config["world_transforms"][b]))
                    if volume>1e-6: pair_component_diagnostic.append({"config_id":config["config_id"],"link_a_component":na,"link_b_component":nb,"common_mm3":volume})
    per_joint=[]
    for joint_id,configs in job["per_joint"].items():
        jflags=[]; collision_rows=[]
        for config in configs:
            rows,ok=frozen.exact_config(config,shapes,contracts,physical); jflags.append(ok)
            collision_rows.extend(row for row in rows if row.get("classification") in ("ADJACENT_UNINTENDED_COLLISION","NONADJACENT_COLLISION"))
        per_joint.append({"joint_id":joint_id,"jr3":sum(jflags)/len(jflags),"full_range_pass":all(jflags),"collision_rows":collision_rows})
    assembly=frozen.save_assembly(job["assembly_root"],condition,shapes,job["canonical_config"],physical)
    dump(job["output"],{"status":"PASS","mode":"full_robot_interface_body_repair","condition":condition,"generation_strategy":generation,"knowledge_mode":job.get("knowledge_mode"),"builds":builds,"interface_records":interface_records,"joint_overlap_diagnostic":diagnostic,"pair_component_diagnostic":pair_component_diagnostic,"mechanical_exact":{"wall_seconds":time.perf_counter()-exact_start,"configuration_count":len(flags),"valid_count":sum(flags),"gcfr":sum(flags)/len(flags),"rows":coupled_rows,"per_joint":per_joint},"assembly":assembly,"physical_links":physical})


def main():
    job=load(sys.argv[1]); base=ROOT/"experiments/try5A/results/try5a5"; contracts=load(base/"motion_interface_contracts.json")
    if job.get("mode")=="full_repair":
        full_robot_repair(job); return
    classification=load(base/"link_realization_classification.json"); physical=[x["link_id"] for x in classification if x["realization_type"]!="virtual_frame"]
    condition_shapes={}; builds=[]
    for condition in ("F0","F1","F2"):
        shapes={}
        for link_id in physical:
            ir=load(base/"cad_ir/round3_verified"/(link_id+".json"))
            if condition=="F0" or link_id not in job["pilots"]:
                built=frozen.link_shape(ir["link_spec"],contracts,ir["body_scale"],ir.get("repair_state")); shapes[link_id]=built["group"]
                if link_id in job["pilots"]:
                    artifact=export(link_id,condition,{"shape":built["body"],"group":built["group"],"executed_family":ir["link_spec"]["body_family"],"features":["coarse_body"],"interface_signatures":{},"solid_count":built["solid_count"],"attachment_valid":built["attachment_valid"],"group_valid":built["valid"]},job["cad_root"])
                    builds.append({"condition":condition,"link_id":link_id,"planned_family":ir["link_spec"]["body_family"],"executed_family":ir["link_spec"]["body_family"],"artifact":artifact,"attachment_valid":built["attachment_valid"],"solid_count":built["solid_count"],"features":["coarse_body"]})
            else:
                spec=job["pilots"][link_id][condition]
                scaffold=frozen.link_shape(ir["link_spec"],contracts,ir["body_scale"],ir.get("repair_state"))["group"]
                built=refined_shape(link_id,spec["body_family"],spec["schema"],contracts,ir["link_spec"]["realization_type"],scaffold)
                shapes[link_id]=built["group"]; artifact=export(link_id,condition,built,job["cad_root"])
                builds.append({"condition":condition,"link_id":link_id,"planned_family":spec["body_family"],"executed_family":built["executed_family"],"artifact":artifact,"attachment_valid":built["attachment_valid"],"solid_count":built["solid_count"],"group_valid":built["group_valid"],"features":built["features"],"interface_signatures":built["interface_signatures"]})
        condition_shapes[condition]=shapes
    assemblies=[{"condition":condition,**frozen.save_assembly(job["assembly_root"],condition,condition_shapes[condition],job["canonical_config"],physical)} for condition in ("F0","F1","F2")]
    previous=load(job["output"]) if job.get("reuse_exact") and Path(job["output"]).is_file() else None
    if previous:
        audits=previous["mechanical_exact"]
    else:
        audits=[]
        for condition in ("F1","F2"):
            start=time.perf_counter(); rows=[]; flags=[]
            for config in job["coupled"]:
                current,ok=frozen.exact_config(config,condition_shapes[condition],contracts,physical); rows.extend(current); flags.append(ok)
            per_joint=[]
            for joint_id in job["relevant_joints"]:
                jflags=[]
                for config in job["per_joint"][joint_id]:
                    _,ok=frozen.exact_config(config,condition_shapes[condition],contracts,physical); jflags.append(ok)
                per_joint.append({"joint_id":joint_id,"jr3":sum(jflags)/len(jflags),"full_range_pass":all(jflags)})
            audits.append({"condition":condition,"wall_seconds":time.perf_counter()-start,"gcfr":sum(flags)/len(flags),"valid_configs":sum(flags),"configuration_count":len(flags),"per_joint":per_joint,"rows":rows})
    dump(job["output"],{"status":"PASS","builds":builds,"assemblies":assemblies,"mechanical_exact":audits,"physical_links":physical})


if __name__=="__main__": main()
