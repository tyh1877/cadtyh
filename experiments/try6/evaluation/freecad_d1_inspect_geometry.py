"""Read-only geometry-set object/mutable-scope audit without GT."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import FreeCAD as App
import Part

ROOT=Path(__file__).resolve().parents[3]


def load(path):return json.loads(Path(path).read_text(encoding="utf-8"))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(job):
    cfg=load(ROOT/job["protocol"])
    construction=load(ROOT/cfg["kfde_construction"])
    allowed=Part.read(str(ROOT/construction["allowed_region"]["path"]))
    artifact=ROOT/job["artifact_root"];artifact.mkdir(parents=True,exist_ok=True)
    rows=[]
    for item in cfg["geometry_set"]:
        path=ROOT/item["path"]
        doc=App.openDocument(str(path))
        full_obj=doc.getObject("RigidGroup")
        mutable_obj=doc.getObject(item["mutable_object"]) if item["mutable_object"]!="RigidGroup_minus_frozen_allowed_region" else None
        if full_obj is None or full_obj.Shape.isNull():raise RuntimeError(f"missing full RigidGroup {item['geometry_id']}")
        full=full_obj.Shape.copy()
        if mutable_obj is None:
            if item["mutable_object"]!="RigidGroup_minus_frozen_allowed_region":raise RuntimeError(f"missing mutable object {item['geometry_id']}")
            mutable=full.cut(allowed)
            extraction="full_link_minus_frozen_allowed_region"
        else:
            mutable=mutable_obj.Shape.copy()
            extraction="exact_FrozenMatingEnvelopeCut_object"
        object_names=[obj.Name for obj in doc.Objects]
        App.closeDocument(doc.Name)
        folder=artifact/item["geometry_id"];folder.mkdir(parents=True,exist_ok=True)
        full_path=folder/"full.brep";mutable_path=folder/"mutable.brep"
        full.exportBrep(str(full_path));mutable.exportBrep(str(mutable_path))
        rows.append({"geometry_id":item["geometry_id"],"source_path":item["path"],
            "source_sha256":sha(path),"full_valid":not full.isNull() and full.isValid(),
            "full_volume_mm3":float(full.Volume),"full_solids":len(full.Solids),
            "mutable_valid":mutable.isNull() or mutable.isValid(),
            "mutable_volume_mm3":float(mutable.Volume) if not mutable.isNull() else 0.0,
            "mutable_solids":len(mutable.Solids) if not mutable.isNull() else 0,
            "extraction":extraction,"full_brep_path":str(full_path.relative_to(ROOT)).replace("\\","/"),
            "full_brep_sha256":sha(full_path),"mutable_brep_path":str(mutable_path.relative_to(ROOT)).replace("\\","/"),
            "mutable_brep_sha256":sha(mutable_path),"object_names":object_names,
            "baseline_exemption_scope_ambiguous":item["geometry_id"] in ("G4_C0_DIRECT","G5_F0_COARSE")})
    result={"status":"PASS" if len(rows)==5 and all(x["full_valid"] and x["mutable_valid"] for x in rows) else "FAIL",
        "geometries":rows,"frozen_allowed_region_sha256":construction["allowed_region"]["sha256"],
        "GT_accessed":False}
    out=ROOT/job["output"];out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"geometries":len(rows),
        "f0_mutable_volume_mm3":next(x["mutable_volume_mm3"] for x in rows if x["geometry_id"]=="G5_F0_COARSE")}))
    if result["status"]!="PASS":raise SystemExit(2)


if __name__=="__main__":main(load(sys.argv[1]))
