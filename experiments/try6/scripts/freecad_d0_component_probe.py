"""No-GT CAD build plus exact frozen KFDE component-vector diagnosis."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import FreeCAD as App
import Part

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"experiments/try5A/scripts"))
import freecad_motion_realization as motion
import freecad_c1_builder as builder


def load(path):return json.loads(Path(path).read_text(encoding="utf-8"))
def save(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8")


def main(job):
    cfg=load(ROOT/job["d0_protocol"])
    c2=load(ROOT/job["c2_protocol"])
    construction=load(ROOT/job["construction_report"])
    if construction["status"]!="PASS" or len(construction["components"])!=13:
        raise RuntimeError("frozen KFDE construction unavailable")
    if cfg["strict_feasibility_epsilon_mm3"]!=c2["numerical_forbidden_volume_tolerance_mm3"]:
        raise RuntimeError("D0 feasibility epsilon differs from frozen C2")
    out=ROOT/job["output_root"];out.mkdir(parents=True,exist_ok=True)
    cad_job={"mode":"D0_FEASIBILITY_DIAGNOSTIC_NON_GT","parameters":job["theta"],
        "anchor_distance_mm":63.0,"kfdg_path":str(ROOT/job["kfdg_source"]),
        "frozen_interface_contracts":str(ROOT/c2["frozen_interface_contracts"]),
        "f0_fcstd":str(ROOT/c2["frozen_l04_scaffold"]),"output_root":str(out/"cad")}
    builder.build(cad_job)
    built=load(out/"cad/build_result.json")
    if built["final_solid_count"]!=1 or not built["reopen"]["valid"]:
        raise RuntimeError("D0 CAD not one valid connected solid")
    doc=App.openDocument(str(out/"cad/final.FCStd"))
    body=doc.getObject("FrozenMatingEnvelopeCut").Shape.copy()
    App.closeDocument(doc.Name)
    allowed=Part.read(str(ROOT/construction["allowed_region"]["path"]))
    mutable=body.cut(allowed)
    if not mutable.isNull() and not mutable.isValid():raise RuntimeError("mutable addition BREP invalid")
    volumes=[]
    epsilon=cfg["strict_feasibility_epsilon_mm3"]
    for component in construction["components"]:
        neighbor=Part.read(str(ROOT/component["brep_path"]))
        if mutable.isNull() or mutable.Volume<=0 or not motion.aabb_overlap(mutable,neighbor):
            overlap=0.0
        else:overlap=motion.common_volume(mutable,neighbor)
        if not math.isfinite(overlap) or overlap<0:raise RuntimeError("invalid exact BREP overlap")
        volumes.append({"component_id":component["component_id"],"neighbor_id":component["link_id"],
            "joint_id":component["joint_id"],"pose_q_rad":component["q_rad"],
            "intersection_volume_mm3":float(overlap),"violation":bool(overlap>epsilon)})
    g_sum=sum(row["intersection_volume_mm3"] for row in volumes)
    dominant=max(volumes,key=lambda row:row["intersection_volume_mm3"])
    g_max=dominant["intersection_volume_mm3"]
    payload={"candidate_id":job["candidate_id"],"theta":job["theta"],
        "cad_build_valid":True,"connected_solid_count":built["final_solid_count"],
        "mutable_added_volume_mm3":float(mutable.Volume) if not mutable.isNull() else 0.0,
        "g_sum_mm3":g_sum,"g_max_mm3":g_max,"strict_feasible":bool(g_max<=epsilon),
        "violating_component_count":sum(row["violation"] for row in volumes),
        "dominant_component":dominant["component_id"],"dominant_neighbor":dominant["neighbor_id"],
        "components":volumes,"GT_accessed":False,"final_mechanics_invoked":False,
        "VLM_calls":0,"frozen_kfde_keepout_sha256":construction["keepout"]["sha256"],
        "frozen_allowed_contact_sha256":construction["allowed_region"]["sha256"]}
    save(out/"component_result.json",payload)
    print(json.dumps({"candidate_id":job["candidate_id"],"g_max_mm3":g_max,
        "g_sum_mm3":g_sum,"strict_feasible":payload["strict_feasible"]}))


if __name__=="__main__":main(load(sys.argv[1]))
