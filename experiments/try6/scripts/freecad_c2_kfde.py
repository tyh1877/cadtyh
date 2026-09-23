"""Exact FreeCAD KFDE construction/check from URDF FK and frozen neighbors only."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import FreeCAD as App
import Part
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"experiments/try5A/scripts"))
import freecad_motion_realization as motion
import kinematics


def load(path):return json.loads(Path(path).read_text(encoding="utf-8"))
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rel(path):return str(Path(path).resolve().relative_to(ROOT)).replace("\\","/")


def load_shape(path,name="RigidGroup"):
    doc=App.openDocument(str(path))
    obj=doc.getObject(name)
    if obj is None or obj.Shape.isNull():
        App.closeDocument(doc.Name);raise RuntimeError(f"missing FreeCAD object {name}: {path}")
    shape=obj.Shape.copy();App.closeDocument(doc.Name)
    return shape


def brp(path):
    shape=Part.read(str(path))
    if shape.isNull() or not shape.isValid():raise RuntimeError(f"invalid BREP: {path}")
    return shape


def construct(job):
    cfg=load(ROOT/job["protocol"])
    out=ROOT/job["artifact_root"];out.mkdir(parents=True,exist_ok=True)
    result=ROOT/job["result_root"];result.mkdir(parents=True,exist_ok=True)
    urdf=ROOT/cfg["sanitized_urdf"]
    links,joints=kinematics.parse(urdf)
    q0=kinematics.canonical_q(joints)
    by_joint={j["joint_id"]:j for j in joints}
    j03=by_joint["J03"];j05=by_joint["J05"]
    if j03["joint_type"]!="revolute" or j05["joint_type"]!="continuous":
        raise RuntimeError("frozen L04 relative joint types changed")
    n=cfg["construction_sweep"]["J03"]["sample_count"]
    j03_samples=np.linspace(j03["limits"]["lower"],j03["limits"]["upper"],n).tolist()
    j05_samples=cfg["construction_sweep"]["J05"]["angles_radians"]
    samples={"L03":[("J03",float(q)) for q in j03_samples],
        "L05":[("FIXED_J04",0.0)],
        "L06":[("J05",float(q)) for q in j05_samples],
        "L07":[("FIXED_J06",0.0)]}
    components=[];shapes=[]
    for neighbor in cfg["neighbor_scope"]:
        link=neighbor["link_id"]
        source=ROOT/cfg["frozen_neighbor_root"]/link/"model.FCStd"
        base=load_shape(source)
        for index,(joint_id,value) in enumerate(samples[link]):
            q=dict(q0)
            if joint_id in ("J03","J05"):q[joint_id]=value
            _,world,joint_world=kinematics.fk(links,joints,q)
            transform=np.linalg.inv(world["L04"])@world[link]
            moved=motion.moved(base,transform)
            if moved.isNull() or not moved.isValid() or moved.Volume<=0:
                raise RuntimeError(f"invalid transformed neighbor {link}:{index}")
            name=f"{link}_{joint_id}_{index:02d}"
            path=out/"components"/(name+".brep");path.parent.mkdir(parents=True,exist_ok=True)
            moved.exportBrep(str(path))
            components.append({"component_id":name,"link_id":link,"joint_id":joint_id,"q_rad":value,
                "source_fcstd":rel(source),"source_sha256":sha(source),
                "relative_transform_L04":transform.tolist(),"brep_path":rel(path),"brep_sha256":sha(path),
                "volume_mm3":float(moved.Volume),"bbox":motion.bounds(moved)})
            shapes.append(moved)
    keepout=Part.makeCompound(shapes)
    keepout_path=out/"kfde_keepout.brep";keepout.exportBrep(str(keepout_path))
    if keepout.isNull() or not keepout.isValid() or keepout.Volume<=0:
        raise RuntimeError("KFDE keepout empty/invalid")
    scaffold=load_shape(ROOT/cfg["frozen_l04_scaffold"])
    final_c1=ROOT/cfg["c1_artifact_root"]/"cad/final.FCStd"
    bore=load_shape(final_c1,"FrozenProximalBoreTool")
    mate=load_shape(final_c1,"FrozenMatingEnvelopeTool")
    allowed=motion.union([scaffold,bore,mate])
    allowed_path=out/"allowed_contact_and_scaffold.brep";allowed.exportBrep(str(allowed_path))
    baseline_residue=float(scaffold.cut(allowed).Volume)
    if baseline_residue>cfg["numerical_forbidden_volume_tolerance_mm3"]:
        raise RuntimeError("frozen scaffold not fully allowed")
    # Check the kinematic frame without relying on any final evaluator row.
    _,world0,joints0=kinematics.fk(links,joints,q0)
    l04_inv=np.linalg.inv(world0["L04"])
    j03_local=(l04_inv@joints0["J03"])[:3,3]*1000
    j04_local=(l04_inv@joints0["J04"])[:3,3]*1000
    if np.linalg.norm(j03_local)>1e-6 or np.linalg.norm(j04_local-np.array([63.0,0.0,0.0]))>1e-6:
        raise RuntimeError("KFDE coordinate frame/URDF anchor incorrect")
    l03=[x for x in components if x["link_id"]=="L03"]
    l06=[x for x in components if x["link_id"]=="L06"]
    pose_sensitive=(l03[0]["brep_sha256"]!=l03[-1]["brep_sha256"] and
        l06[0]["brep_sha256"]!=l06[2]["brep_sha256"])
    if not pose_sensitive:raise RuntimeError("design sweep does not change neighbor geometry")
    construction={"schema_version":"robotcad_try6_c2_kfde_construction_v1","status":"PASS",
        "coordinate_frame":"L04 local mm","sanitized_urdf_path":cfg["sanitized_urdf"],
        "sanitized_urdf_sha256":sha(urdf),"design_pose_policy":cfg["construction_sweep"],
        "design_pose_count":len(components),"j03_samples_rad":j03_samples,"j05_samples_rad":j05_samples,
        "components":components,"keepout":{"path":rel(keepout_path),"sha256":sha(keepout_path),
            "compound_volume_proxy_mm3":float(keepout.Volume),"bbox":motion.bounds(keepout)},
        "allowed_region":{"path":rel(allowed_path),"sha256":sha(allowed_path),
            "volume_mm3":float(allowed.Volume),"scaffold_path":cfg["frozen_l04_scaffold"],
            "scaffold_sha256":sha(ROOT/cfg["frozen_l04_scaffold"]),
            "proximal_bore_source":"C1-v2 final.FCStd:FrozenProximalBoreTool",
            "mating_envelope_source":"C1-v2 final.FCStd:FrozenMatingEnvelopeTool"},
        "numerical_tolerance_mm3":cfg["numerical_forbidden_volume_tolerance_mm3"],
        "engineering_margin_mm":cfg["engineering_clearance_margin_mm"],
        "gt_accessed":False,"final_development_configurations_consumed":False,
        "c1_failure_ids_consumed":False}
    save(result/"construction_report.json",construction)
    save(result/"construction_sweep.json",{"J03":{"range_rad":[j03["limits"]["lower"],j03["limits"]["upper"]],"samples_rad":j03_samples},
        "J05":{"type":"continuous","samples_rad":j05_samples},
        "fixed_neighbors":["L05","L07"],"derived_from":"sanitized URDF, not final 96-case development configurations"})
    save(result/"coordinate_frame_audit.json",{"status":"PASS","L04_design_frame":"local mm",
        "J03_origin_L04_mm":j03_local.tolist(),"J04_origin_L04_mm":j04_local.tolist(),
        "pose_transform_changes_geometry":pose_sensitive,"j03_first_transform":l03[0]["relative_transform_L04"],
        "j03_last_transform":l03[-1]["relative_transform_L04"],
        "j05_first_transform":l06[0]["relative_transform_L04"],
        "j05_opposite_transform":l06[2]["relative_transform_L04"]})
    save(result/"allowed_contact_audit.json",{"status":"PASS","policy":cfg["allowed_contact_policy"],
        "allowed_region_path":rel(allowed_path),"allowed_region_sha256":sha(allowed_path),
        "frozen_scaffold_residual_after_exemption_mm3":baseline_residue,
        "protected_interfaces_not_auto_forbidden":baseline_residue<=cfg["numerical_forbidden_volume_tolerance_mm3"]})
    print(json.dumps({"status":"PASS","components":len(components),"keepout_volume_proxy_mm3":float(keepout.Volume),
        "pose_sensitive":pose_sensitive,"scaffold_exempt":True}))


def check(job):
    cfg=load(ROOT/job["protocol"])
    construction=load(ROOT/job["construction_report"])
    if construction["status"]!="PASS":raise RuntimeError("KFDE construction not passed")
    body=load_shape(ROOT/job["candidate_fcstd"],"FrozenMatingEnvelopeCut")
    allowed=brp(ROOT/construction["allowed_region"]["path"])
    mutable=body.cut(allowed)
    if mutable.isNull():
        mutable_volume=0.0
    else:
        if not mutable.isValid():raise RuntimeError("candidate mutable addition BREP invalid")
        mutable_volume=float(mutable.Volume)
    violations=[]
    max_volume=0.0
    for item in construction["components"]:
        neighbor=brp(ROOT/item["brep_path"])
        if mutable_volume<=0 or not motion.aabb_overlap(mutable,neighbor):continue
        volume=motion.common_volume(mutable,neighbor)
        if not math.isfinite(volume):raise RuntimeError("non-finite exact overlap")
        if volume>max_volume:max_volume=volume
        if volume>cfg["numerical_forbidden_volume_tolerance_mm3"]:
            violations.append({"component_id":item["component_id"],"link_id":item["link_id"],
                "joint_id":item["joint_id"],"q_rad":item["q_rad"],
                "forbidden_intersection_mm3":volume})
    feasible=max_volume<=cfg["numerical_forbidden_volume_tolerance_mm3"]
    output={"candidate_id":job["candidate_id"],"candidate_fcstd":job["candidate_fcstd"],
        "candidate_fcstd_sha256":sha(ROOT/job["candidate_fcstd"]),
        "mutable_added_volume_mm3":mutable_volume,
        "maximum_forbidden_intersection_mm3":max_volume,
        "feasible":feasible,"violating_components":violations,
        "violating_component_count":len(violations),
        "engineering_margin_mm":cfg["engineering_clearance_margin_mm"],
        "numerical_tolerance_mm3":cfg["numerical_forbidden_volume_tolerance_mm3"],
        "keepout_sha256":construction["keepout"]["sha256"],
        "allowed_region_sha256":construction["allowed_region"]["sha256"],
        "gt_accessed":False,"final_mechanics_evaluator_invoked":False}
    save(ROOT/job["output"],output)
    print(json.dumps({"candidate_id":job["candidate_id"],"feasible":feasible,
        "maximum_forbidden_intersection_mm3":max_volume,"violating_components":len(violations)}))


if __name__=="__main__":
    job=load(sys.argv[1])
    if job["mode"]=="construct":construct(job)
    elif job["mode"]=="check":check(job)
    else:raise ValueError("unknown KFDE mode")
