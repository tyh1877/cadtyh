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


def shape_state(shape):
    return {
        "shape_sha256":hashlib.sha256(shape.exportBrepToString().encode("utf-8")).hexdigest(),
        "volume_mm3":float(shape.Volume),
        "solid_count":len(shape.Solids),
        "face_count":len(shape.Faces),
        "edge_count":len(shape.Edges),
        "vertex_count":len(shape.Vertexes),
        "bbox":frozen.bounds(shape),
    }


def protection_effect(operation,applicable,executed,before_shape,after_shape):
    before=shape_state(before_shape); after=shape_state(after_shape); volume_delta=after["volume_mm3"]-before["volume_mm3"]; solid_delta=after["solid_count"]-before["solid_count"]
    removed_volume=float(before_shape.cut(after_shape).Volume) if executed else 0.0; added_volume=float(after_shape.cut(before_shape).Volume) if executed else 0.0; symmetric_difference=removed_volume+added_volume; topology_changed=any(before[key]!=after[key] for key in ("solid_count","face_count","edge_count","vertex_count")); representation_changed=before["shape_sha256"]!=after["shape_sha256"]
    geometry_changed=bool(executed and (symmetric_difference>1e-7 or abs(volume_delta)>1e-7 or solid_delta!=0 or before["bbox"]!=after["bbox"]))
    status="NOT_APPLICABLE" if not applicable else ("SKIPPED" if not executed else ("GEOMETRY_EFFECTIVE" if geometry_changed else "EXECUTED_BUT_NO_OP"))
    return {"operation":operation,"applicable":bool(applicable),"executed":bool(executed),"shape_hash_before":before["shape_sha256"],"shape_hash_after":after["shape_sha256"],"brep_representation_changed":representation_changed,"volume_before_mm3":before["volume_mm3"],"volume_after_mm3":after["volume_mm3"],"volume_delta_mm3":volume_delta,"removed_volume_mm3":removed_volume,"added_volume_mm3":added_volume,"symmetric_difference_volume_mm3":symmetric_difference,"solid_count_before":before["solid_count"],"solid_count_after":after["solid_count"],"solid_count_delta":solid_delta,"face_count_before":before["face_count"],"face_count_after":after["face_count"],"edge_count_before":before["edge_count"],"edge_count_after":after["edge_count"],"vertex_count_before":before["vertex_count"],"vertex_count_after":after["vertex_count"],"topology_count_changed":topology_changed,"bbox_before":before["bbox"],"bbox_after":after["bbox"],"geometry_changed":geometry_changed,"effect_status":status}


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


DEFAULT_MECHANICAL_POLICY = {
    "protected_interface_cuts": True,
    "distal_clearance_cut": True,
    "preserve_frozen_scaffold": True,
    "auto_attachment_closure": True,
}


def refined_shape(link_id, family, schema, contracts, realization_type, frozen_scaffold, mechanical_policy=None):
    policy = {**DEFAULT_MECHANICAL_POLICY, **(mechanical_policy or {})}
    compiled=compile_body(family,schema); body=compiled["shape"]; interfaces=[]; interface_hashes={}
    raw_body_signature={"volume_mm3":round(float(body.Volume),9),"bbox":frozen.bounds(body),"solids":len(body.Solids),"faces":len(body.Faces),"edges":len(body.Edges),"vertices":len(body.Vertexes)}
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
    proximal_cut_applicable=bool(proximal and proximal["joint_type"] in ("revolute","continuous"))
    proximal_cut_executed=bool(policy["protected_interface_cuts"] and proximal_cut_applicable)
    if proximal_cut_executed:
        axis=frozen.unit(proximal["axis_child"]); body=body.cut(frozen.cylinder_axis(3+proximal["clearance_mm"],26,[0,0,0],axis)).removeSplitter()
        mate_contract=dict(proximal); mate_contract["origin_xyz_mm"]=[0,0,0]; mate_contract["axis_parent"]=mate_contract["axis_child"]
        mate,_=frozen.joint_half(mate_contract,"parent"); body=body.cut(mate).removeSplitter()
    distal_applicable=[contract for contract in distal if contract["joint_type"] in ("revolute","continuous")]
    distal_cut_executed=bool(policy["distal_clearance_cut"] and distal_applicable)
    for contract in (distal_applicable if policy["distal_clearance_cut"] else []):
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
    if policy["preserve_frozen_scaffold"]:
        group=frozen_scaffold.fuse(body).removeSplitter()
        assembly_strategy="FROZEN_SCAFFOLD"
        attachment_trace="NOT_REACHED_SCAFFOLD_SELECTED"
    elif policy["auto_attachment_closure"]:
        group=connect(body,interfaces,realization_type)
        assembly_strategy="AUTO_ATTACHMENT_CLOSURE"
        attachment_trace="EXECUTED"
    else:
        # Keep the exact same interface inputs, but do not add a connector or the
        # validated coarse scaffold.  Disconnected solids remain visible to BICR.
        group=Part.makeCompound([body]+[shape for shape in interfaces if shape is not None and not shape.isNull()])
        assembly_strategy="NATURAL_CONTACT_ONLY"
        attachment_trace="SKIPPED_BY_POLICY"
    execution_trace={
        "protected_interface_cuts":"EXECUTED" if proximal_cut_executed else ("SKIPPED_BY_POLICY" if proximal_cut_applicable else "NOT_APPLICABLE"),
        "distal_clearance_cut":"EXECUTED" if distal_cut_executed else ("SKIPPED_BY_POLICY" if distal_applicable else "NOT_APPLICABLE"),
        "frozen_scaffold_preservation":"EXECUTED" if policy["preserve_frozen_scaffold"] else "SKIPPED_BY_POLICY",
        "auto_attachment_closure":attachment_trace,
    }
    return {**compiled,"group":group,"interface_signatures":interface_hashes,"solid_count":len(group.Solids),
            "attachment_valid":len(group.Solids)==1,"group_valid":group.isValid() and not group.isNull(),
            "mechanical_policy":policy,"assembly_strategy":assembly_strategy,"raw_body_signature":raw_body_signature,
            "execution_trace":execution_trace}


def protection_effect_audit(job):
    base=ROOT/"experiments/try5A/results/try5a5"; contracts=load(base/"motion_interface_contracts.json"); rows=[]; links=[]; policy=job["mechanical_geometry_policy"]
    for link_id,spec in job["links"].items():
        ir=load(base/"cad_ir/round3_verified"/(link_id+".json")); scaffold=frozen.link_shape(ir["link_spec"],contracts,ir["body_scale"],ir.get("repair_state"))["group"]; body=compile_body(spec["body_family"],spec["schema"])["shape"]; interfaces=[]; proximal=None; distal=[]; operations=[]
        for contract in contracts:
            if contract.get("virtual_child") or link_id not in (contract["parent"],contract["child"]): continue
            side="parent" if contract["parent"]==link_id else "child"; shape,_=frozen.joint_half(contract,side); interfaces.append(shape)
            if side=="child": proximal=contract
            else: distal.append(contract)
        applicable=bool(proximal and proximal["joint_type"] in ("revolute","continuous")); before=body
        after=before
        if applicable and policy["protected_interface_cuts"]:
            axis=frozen.unit(proximal["axis_child"]); after=before.cut(frozen.cylinder_axis(3+proximal["clearance_mm"],26,[0,0,0],axis)).removeSplitter()
        operations.append(protection_effect("proximal_interface_protected_cut",applicable,applicable and policy["protected_interface_cuts"],before,after)); body=after
        before=body; after=before
        if applicable and policy["protected_interface_cuts"]:
            mate_contract=dict(proximal); mate_contract["origin_xyz_mm"]=[0,0,0]; mate_contract["axis_parent"]=mate_contract["axis_child"]; mate,_=frozen.joint_half(mate_contract,"parent"); after=before.cut(mate).removeSplitter()
        operations.append(protection_effect("proximal_mating_envelope_cut",applicable,applicable and policy["protected_interface_cuts"],before,after)); body=after
        distal_applicable=[contract for contract in distal if contract["joint_type"] in ("revolute","continuous")]; before=body; after=before
        if distal_applicable and policy["distal_clearance_cut"]:
            for contract in distal_applicable:
                center=frozen.vec(contract["origin_xyz_mm"]); axis=frozen.unit(contract["axis_parent"]); after=after.cut(frozen.cylinder_axis(10+contract["clearance_mm"],16,center,axis)).removeSplitter(); mate_contract=dict(contract); mate_contract["axis_child"]=mate_contract["axis_parent"]; mate,_=frozen.joint_half(mate_contract,"child"); mate.translate(frozen.fcvec(center)); after=after.cut(mate).removeSplitter()
        operations.append(protection_effect("distal_rotary_interface_clearance_cut",bool(distal_applicable),bool(distal_applicable and policy["distal_clearance_cut"]),before,after)); body=after
        before=body; scaffold_executed=bool(policy["preserve_frozen_scaffold"]); after=scaffold.fuse(before).removeSplitter() if scaffold_executed else before
        operations.append(protection_effect("frozen_scaffold_preservation_fusion",True,scaffold_executed,before,after)); group=after
        closure_applicable=bool(not scaffold_executed and policy["auto_attachment_closure"]); before=group; after=connect(before,interfaces,ir["link_spec"]["realization_type"]) if closure_applicable else before
        operations.append(protection_effect("auto_attachment_closure",closure_applicable,closure_applicable,before,after)); group=after
        trace={"schema_version":"robotcad_protection_trace_v1","link_id":link_id,"f2_spec":spec,"policy":policy,"operations":operations,"final_shape":shape_state(group)}; target=Path(job["output_root"])/link_id/"protection_trace.json"; dump(target,trace); links.append({"link_id":link_id,"trace":str(target)}); rows.extend({"link_id":link_id,**operation} for operation in operations)
    dump(job["output"],{"status":"PASS","mode":"PROTECTION_EFFECT_AUDIT","mechanical_evaluation_run":False,"gt_accessed":False,"formal_holdout_accessed":False,"links":links,"rows":rows})


def export(link_id, condition, built, root):
    folder=Path(root)/condition/link_id; folder.mkdir(parents=True,exist_ok=True)
    doc=App.newDocument(condition+"_"+link_id)
    body=doc.addObject("Part::Feature","BodyFamily"); body.Shape=built["shape"]
    group=doc.addObject("Part::Feature","RigidGroup"); group.Shape=built["group"]
    body.addProperty("App::PropertyString","ExecutedFamily"); body.ExecutedFamily=built["executed_family"]
    body.addProperty("App::PropertyStringList","SemanticFeatures"); body.SemanticFeatures=built["features"]
    doc.recompute(); fcstd=folder/"model.FCStd"; step=folder/"model.step"; stl=folder/"model.stl"; body_stl=folder/"body_only.stl"
    doc.saveAs(str(fcstd)); Part.export([group],str(step)); Mesh.export([group],str(stl)); Mesh.export([body],str(body_stl)); App.closeDocument(doc.Name)
    reopened=App.openDocument(str(fcstd)); reopened_body=reopened.getObject("BodyFamily"); reopened_group=reopened.getObject("RigidGroup")
    reopen={"body_valid":bool(reopened_body and not reopened_body.Shape.isNull() and reopened_body.Shape.isValid()),"group_valid":bool(reopened_group and not reopened_group.Shape.isNull() and reopened_group.Shape.isValid())}; App.closeDocument(reopened.Name)
    return {"fcstd":str(fcstd),"step":str(step),"stl":str(stl),"body_stl":str(body_stl),"sha256":{p.name:sha(p) for p in (fcstd,step,stl,body_stl)},
            "volume_mm3":float(built["group"].Volume),"bbox":frozen.bounds(built["group"]),"body_volume_mm3":float(built["shape"].Volume),"body_bbox":frozen.bounds(built["shape"]),"reopen":reopen}


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
    if job.get("mode")=="protection_effect_audit":
        protection_effect_audit(job); return
    if job.get("mode")=="full_repair":
        full_robot_repair(job); return
    classification=load(base/"link_realization_classification.json"); physical=[x["link_id"] for x in classification if x["realization_type"]!="virtual_frame"]
    condition_shapes={}; builds=[]; policy=job.get("mechanical_geometry_policy",job.get("mechanical_policy",DEFAULT_MECHANICAL_POLICY)); conditions=job.get("conditions",["F0","F1","F2"])
    if not conditions or any(condition not in ("F0","F1","F2") for condition in conditions): raise ValueError("conditions must be a non-empty subset of F0/F1/F2")
    for condition in conditions:
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
                built=refined_shape(link_id,spec["body_family"],spec["schema"],contracts,ir["link_spec"]["realization_type"],scaffold,policy)
                shapes[link_id]=built["group"]; artifact=export(link_id,condition,built,job["cad_root"])
                builds.append({"condition":condition,"link_id":link_id,"planned_family":spec["body_family"],"executed_family":built["executed_family"],"artifact":artifact,"attachment_valid":built["attachment_valid"],"solid_count":built["solid_count"],"group_valid":built["group_valid"],"features":built["features"],"interface_signatures":built["interface_signatures"],"mechanical_geometry_policy":built["mechanical_policy"],"assembly_strategy":built["assembly_strategy"],"raw_body_signature":built["raw_body_signature"],"execution_trace":built["execution_trace"]})
        condition_shapes[condition]=shapes
    assemblies=[{"condition":condition,**frozen.save_assembly(job["assembly_root"],condition,condition_shapes[condition],job["canonical_config"],physical)} for condition in conditions]
    previous=load(job["output"]) if job.get("reuse_exact") and Path(job["output"]).is_file() else None
    if not job.get("evaluation_enabled",True):
        audits=[]
    elif previous:
        audits=previous["mechanical_exact"]
    else:
        audits=[]
        for condition in [value for value in conditions if value != "F0"]:
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
