"""Independent exact-config semantics at the same 5×13 frozen KFDE poses."""

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
import freecad_motion_realization as exact
import kinematics


def load(path):return json.loads(Path(path).read_text(encoding="utf-8"))
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_group(path):
    doc=App.openDocument(str(path));obj=doc.getObject("RigidGroup")
    if obj is None or obj.Shape.isNull():raise RuntimeError(f"RigidGroup missing: {path}")
    shape=obj.Shape.copy();App.closeDocument(doc.Name)
    return shape


def main(job):
    cfg=load(ROOT/job["protocol"])
    frozen=load(ROOT/job["geometry_set"])
    construction=load(ROOT/cfg["kfde_construction"])
    if frozen["status"]!="PASS" or len(frozen["geometries"])!=5 or len(construction["components"])!=13:
        raise RuntimeError("frozen geometry/KFDE inputs invalid")
    allowed=Part.read(str(ROOT/construction["allowed_region"]["path"]))
    components={item["component_id"]:Part.read(str(ROOT/item["brep_path"])) for item in construction["components"]}
    contracts=load(ROOT/cfg["interface_contracts"])
    classification=load(ROOT/cfg["physical_link_classification"])
    physical=[x["link_id"] for x in classification if x["realization_type"]!="virtual_frame"]
    shapes={link:load_group(ROOT/cfg["frozen_nonpilot_root"]/link/"model.FCStd") for link in physical if link!="L04"}
    links,joints=kinematics.parse(ROOT/cfg["sanitized_urdf"])
    q0=kinematics.canonical_q(joints)
    tolerance=cfg["kfde_numerical_epsilon_mm3"]
    material=cfg["material_exact_overlap_mm3"]
    records=[]
    for geometry in frozen["geometries"]:
        full=Part.read(str(ROOT/geometry["full_brep_path"]))
        mutable=Part.read(str(ROOT/geometry["mutable_brep_path"]))
        addition=mutable.cut(allowed)
        if not addition.isNull() and not addition.isValid():raise RuntimeError("mutable addition invalid")
        shapes["L04"]=full
        for component in construction["components"]:
            joint=component["joint_id"]
            q=dict(q0)
            if joint in ("J03","J05"):q[joint]=component["q_rad"]
            _,world,_=kinematics.fk(links,joints,q)
            relative=np.linalg.inv(world["L04"])@world[component["link_id"]]
            if not np.allclose(relative,component["relative_transform_L04"],atol=1e-12):
                raise RuntimeError("KFDE/exact coordinate frame parity failed")
            config={"config_id":geometry["geometry_id"]+"_"+component["component_id"],
                "world_transforms":{link:world[link].tolist() for link in physical}}
            exact_rows,_=exact.exact_config(config,shapes,contracts,physical)
            pair=next(row for row in exact_rows if {row["link_a"],row["link_b"]}=={"L04",component["link_id"]})
            frozen_neighbor=components[component["component_id"]]
            kfde_volume=0.0 if addition.isNull() or addition.Volume<=0 or not exact.aabb_overlap(addition,frozen_neighbor) else exact.common_volume(addition,frozen_neighbor)
            addition_world=exact.moved(addition,world["L04"]) if not addition.isNull() else addition
            neighbor_source=shapes[component["link_id"]]
            neighbor_world=exact.moved(neighbor_source,world[component["link_id"]])
            mutable_world_volume=0.0 if addition.isNull() or addition.Volume<=0 or not exact.aabb_overlap(addition_world,neighbor_world) else exact.common_volume(addition_world,neighbor_world)
            coordinate_delta=abs(kfde_volume-mutable_world_volume)
            if coordinate_delta>1e-4:raise RuntimeError(f"KFDE/exact mutable BREP overlap differs: {config['config_id']} {coordinate_delta}")
            full_common=pair["exact_common_mm3"]
            allowed_world=exact.moved(allowed,world["L04"])
            allowed_common=0.0 if not exact.aabb_overlap(allowed_world,neighbor_world) else exact.common_volume(allowed_world,neighbor_world)
            unsafe=pair["classification"] in ("ADJACENT_UNINTENDED_COLLISION","NONADJACENT_COLLISION")
            violation=kfde_volume>tolerance
            scope_ambiguous=geometry["baseline_exemption_scope_ambiguous"]
            if coordinate_delta>tolerance:
                category="AMBIGUOUS_NUMERICAL"
                ambiguity="L04-frame/world-frame mutable overlap differs beyond frozen numerical tolerance"
            elif violation and unsafe:
                category="ALIGNED_UNSAFE";ambiguity=None
            elif violation and not unsafe:
                category="KFDE_FALSE_POSITIVE_SUSPECT" if kfde_volume>=material else "AMBIGUOUS_NUMERICAL"
                ambiguity=None if category=="KFDE_FALSE_POSITIVE_SUSPECT" else "overlap below predeclared material threshold"
            elif not violation and unsafe:
                category="AMBIGUOUS_NUMERICAL" if scope_ambiguous or allowed_common>tolerance else "KFDE_FALSE_NEGATIVE_SUSPECT"
                ambiguity="frozen baseline/full-link occupancy intentionally outside mutable KFDE scope" if category=="AMBIGUOUS_NUMERICAL" else None
            else:category="ALIGNED_SAFE";ambiguity=None
            records.append({"geometry_id":geometry["geometry_id"],"component_id":component["component_id"],
                "neighbor_id":component["link_id"],"joint_id":joint,"pose_q_rad":component["q_rad"],
                "geometry_fcstd_sha256":geometry["source_sha256"],"KFDE_component_brep_sha256":component["brep_sha256"],
                "kfde_mutable_added_intersection_mm3":kfde_volume,"kfde_violation":violation,
                "exact_full_pair_common_mm3":full_common,"exact_mutable_pair_common_mm3":mutable_world_volume,
                "allowed_region_pair_common_mm3":allowed_common,
                "coordinate_volume_delta_mm3":coordinate_delta,
                "exact_taxonomy":pair["classification"],"exact_adjacent":pair["adjacent"],
                "exact_unintended_collision":unsafe,
                "exact_allowed_contact_or_cluster_exception":pair["classification"]=="EXPECTED_INTERFACE_CONTACT" and full_common>tolerance,
                "scope_ambiguity":scope_ambiguous,"alignment_category":category,
                "ambiguity_reason":ambiguity,"GT_accessed":False})
    if len(records)!=65:raise RuntimeError("D1 5×13 alignment denominator incomplete")
    save(ROOT/job["output"],{"schema_version":"robotcad_try6_d1_alignment_raw_v1","status":"PASS",
        "geometry_count":5,"component_count":13,"case_count":len(records),"cases":records,
        "exact_mechanics_source_sha256":sha(ROOT/cfg["exact_mechanics_source"]),
        "GT_accessed":False,"final_96_case_mechanics_run":False,"formal_holdout_accessed":False})
    counts={name:sum(row["alignment_category"]==name for row in records) for name in
        ("ALIGNED_UNSAFE","KFDE_FALSE_POSITIVE_SUSPECT","KFDE_FALSE_NEGATIVE_SUSPECT","AMBIGUOUS_NUMERICAL","ALIGNED_SAFE")}
    print(json.dumps({"status":"PASS","cases":65,"categories":counts,"GT_accessed":False}))


if __name__=="__main__":main(load(sys.argv[1]))
