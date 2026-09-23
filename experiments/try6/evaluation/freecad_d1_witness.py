"""Diagnostic exact-BREP clearance witnesses; never a C2 design candidate."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import FreeCAD as App
import Mesh
import Part

ROOT=Path(__file__).resolve().parents[3]


def load(path):return json.loads(Path(path).read_text(encoding="utf-8"))
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bbox(shape):
    if shape.isNull() or not shape.Solids:return None
    b=shape.BoundBox
    return [b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax]


def volume_in_x(shape,x0,x1,y0,y1,z0,z1):
    if shape.isNull() or not shape.Solids or x1<=x0:return 0.0
    box=Part.makeBox(x1-x0,y1-y0,z1-z0,App.Vector(x0,y0,z0))
    return float(shape.common(box).Volume)


def run(job):
    cfg=load(ROOT/job["protocol"])
    construction=load(ROOT/job["construction_report"])
    if len(construction["components"])!=13:raise RuntimeError("frozen KFDE component count drift")
    allowed=Part.read(str(ROOT/construction["allowed_region"]["path"]))
    doc=App.openDocument(str(ROOT/cfg["geometry_set"][0]["path"]))
    source=doc.getObject("FrozenMatingEnvelopeCut").Shape.copy()
    frozen_scaffold=doc.getObject("FrozenScaffold").Shape.copy()
    frozen_names=("FrozenScaffold","FrozenProximalBoreTool","FrozenMatingEnvelopeTool")
    frozen_shapes={name:doc.getObject(name).Shape.copy() for name in frozen_names}
    App.closeDocument(doc.Name)
    original_fcstd_hash=sha(ROOT/cfg["geometry_set"][0]["path"])
    mutable=source.cut(allowed)
    preserved=source.common(allowed)
    if not source.isValid() or (not mutable.isNull() and not mutable.isValid()):
        raise RuntimeError("C1 original/mutable BREP invalid")
    component_shapes={item["component_id"]:Part.read(str(ROOT/item["brep_path"])) for item in construction["components"]}
    out_root=ROOT/job["artifact_root"];out_root.mkdir(parents=True,exist_ok=True)
    result_root=ROOT/job["result_root"];result_root.mkdir(parents=True,exist_ok=True)
    all_rows=[]
    for subset in cfg["witness_subsets"]:
        selected_links={"L03","L05","L06","L07"} if subset=="FULL" else set(subset.split("_"))
        selected=[item for item in construction["components"] if item["link_id"] in selected_links]
        relieved=mutable.copy()
        for item in selected:
            if not relieved.isNull() and relieved.Volume>0:
                relieved=relieved.cut(component_shapes[item["component_id"]])
        if relieved.isNull() or relieved.Volume<=0:
            witness=preserved.copy()
        elif preserved.isNull() or preserved.Volume<=0:
            witness=relieved.copy()
        else:
            witness=preserved.fuse(relieved).removeSplitter()
        if witness.isNull() or not witness.isValid():raise RuntimeError(f"witness BREP invalid: {subset}")
        removed=source.cut(witness)
        v_original=float(source.Volume)
        v_witness=float(witness.Volume)
        v_removed=max(0.0,v_original-v_witness)
        ratio=v_removed/v_original if v_original>0 else 0.0
        if abs(float(removed.Volume)-v_removed)>1e-3:
            raise RuntimeError(f"witness removed-volume Boolean mismatch: {subset}")
        group=frozen_scaffold.fuse(witness).removeSplitter()
        group_solid_count=len(group.Solids)
        body_solid_count=len(witness.Solids)
        bounds_before=bbox(source);bounds_after=bbox(witness)
        shift=float(source.CenterOfMass.distanceToPoint(witness.CenterOfMass)) if v_witness>0 else None
        b=source.BoundBox
        y0,y1=b.YMin-1,b.YMax+1;z0,z1=b.ZMin-1,b.ZMax+1
        c1,c2=cfg["witness_longitudinal_cut_stations_mm"]
        regions={"proximal":volume_in_x(removed,b.XMin-1,c1,y0,y1,z0,z1),
            "middle":volume_in_x(removed,c1,c2,y0,y1,z0,z1),
            "distal":volume_in_x(removed,c2,b.XMax+1,y0,y1,z0,z1)}
        total_regions=sum(regions.values())
        if v_removed>1e-6 and abs(total_regions-v_removed)>1e-3:
            raise RuntimeError(f"regional removed volume mismatch {subset}: {total_regions-v_removed}")
        fractions={key:(value/v_removed if v_removed>1e-6 else 0.0) for key,value in regions.items()}
        dominant=max(fractions,key=fractions.get) if v_removed>1e-6 else "NONE"
        p0,p1=cfg["proximal_carrier_audit_x_mm"];d0,d1=cfg["distal_carrier_audit_x_mm"]
        proximal=volume_in_x(witness,p0,p1,y0,y1,z0,z1)>1e-6
        distal=volume_in_x(witness,d0,d1,y0,y1,z0,z1)>1e-6
        interface_invariant=sha(ROOT/cfg["geometry_set"][0]["path"])==original_fcstd_hash
        interface_safe=interface_invariant and all(not shape.isNull() and shape.isValid() for shape in frozen_shapes.values())
        connected=(body_solid_count==1 and group_solid_count==1 and proximal and distal)
        localized=max(fractions.values())>=cfg["witness_localized_one_longitudinal_third_min_fraction"] if v_removed>1e-6 else True
        if not interface_safe:category="INTERFACE_DESTRUCTIVE"
        elif not connected:category="TOPOLOGY_BREAKING_RELIEF"
        elif ratio<=cfg["witness_moderate_removed_ratio_max"] and localized:category="LOCAL_CONNECTED_RELIEF"
        else:category="GLOBAL_CONNECTED_SHRINKAGE"
        folder=out_root/subset;folder.mkdir(parents=True,exist_ok=True)
        brep=folder/"witness.brep";witness.exportBrep(str(brep))
        removed_brep=folder/"removed_material.brep";removed.exportBrep(str(removed_brep))
        temporary=App.newDocument("D1_Witness_"+subset)
        obj=temporary.addObject("Part::Feature","DiagnosticWitness")
        obj.Shape=witness
        Part.export([obj],str(folder/"witness.step"))
        Mesh.export([obj],str(folder/"witness.stl"))
        App.closeDocument(temporary.Name)
        row={"subset":subset,"selected_neighbors":sorted(selected_links),
            "component_count":len(selected),"original_mutable_body_volume_mm3":v_original,
            "mutable_added_volume_mm3":float(mutable.Volume) if not mutable.isNull() else 0.0,
            "witness_mutable_body_volume_mm3":v_witness,
            "removed_volume_mm3":v_removed,"removed_ratio":ratio,
            "witness_body_valid":witness.isValid(),"witness_body_solid_count":body_solid_count,
            "fragment_count":max(0,body_solid_count-1),
            "scaffold_fused_group_valid":group.isValid(),"scaffold_fused_group_solid_count":group_solid_count,
            "proximal_carrier_present":proximal,"distal_carrier_present":distal,
            "mutable_carrier_connected":connected,"frozen_interface_signature_invariant":interface_invariant,
            "functional_interface_safe":interface_safe,
            "bbox_before_mm":bounds_before,"bbox_after_mm":bounds_after,
            "centroid_shift_mm":shift,
            "removed_volume_by_longitudinal_region_mm3":regions,
            "removed_fraction_by_longitudinal_region":fractions,
            "dominant_removed_region":dominant,"localized_one_third":localized,
            "witness_category":category,
            "witness_brep_path":str(brep.relative_to(ROOT)).replace("\\","/"),
            "witness_brep_sha256":sha(brep),
            "removed_brep_path":str(removed_brep.relative_to(ROOT)).replace("\\","/"),
            "removed_brep_sha256":sha(removed_brep),
            "step_path":str((folder/"witness.step").relative_to(ROOT)).replace("\\","/"),
            "step_sha256":sha(folder/"witness.step"),
            "stl_path":str((folder/"witness.stl").relative_to(ROOT)).replace("\\","/"),
            "stl_sha256":sha(folder/"witness.stl"),
            "diagnostic_only_not_C2_candidate":True,"GT_accessed":False}
        save(result_root/subset/"witness_metrics.json",row)
        save(result_root/subset/"localization.json",{"regions_mm3":regions,"fractions":fractions,
            "dominant_region":dominant,"localized":localized})
        all_rows.append(row)
    save(result_root/"witness_summary.json",{"schema_version":"robotcad_try6_d1_witness_summary_v1",
        "status":"PASS","subsets":all_rows,"GT_accessed":False,
        "final_mechanics_evaluations":0,"not_a_generated_design":True,
        "frozen_C1_fcstd_unchanged":sha(ROOT/cfg["geometry_set"][0]["path"])==original_fcstd_hash})
    print(json.dumps({"status":"PASS","subsets":len(all_rows),
        "full_removed_ratio":next(x["removed_ratio"] for x in all_rows if x["subset"]=="FULL"),
        "full_category":next(x["witness_category"] for x in all_rows if x["subset"]=="FULL")}))


if __name__=="__main__":run(load(sys.argv[1]))
