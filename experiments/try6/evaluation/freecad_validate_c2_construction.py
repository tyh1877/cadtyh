"""Independent FreeCAD BREP check of frozen KFDE/allowed-region artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import FreeCAD as App
import Part

ROOT=Path(__file__).resolve().parents[3]


def load(path):return json.loads(Path(path).read_text(encoding="utf-8"))


def main(job):
    report=load(ROOT/job["construction_report"])
    allowed=Part.read(str(ROOT/report["allowed_region"]["path"]))
    keepout=Part.read(str(ROOT/report["keepout"]["path"]))
    doc=App.openDocument(str(ROOT/job["scaffold_fcstd"]))
    scaffold=doc.getObject("RigidGroup").Shape.copy();App.closeDocument(doc.Name)
    residual=float(scaffold.cut(allowed).Volume)
    component_valid=[]
    for item in report["components"]:
        shape=Part.read(str(ROOT/item["brep_path"]))
        component_valid.append(not shape.isNull() and shape.isValid() and shape.Volume>0)
    result={"status":"PASS" if allowed.isValid() and keepout.isValid() and keepout.Volume>0 and all(component_valid) and residual<=1e-6 else "FAIL",
        "allowed_region_valid":allowed.isValid(),"keepout_valid":keepout.isValid(),
        "keepout_compound_volume_proxy_mm3":float(keepout.Volume),
        "component_count":len(component_valid),"valid_component_count":sum(component_valid),
        "frozen_scaffold_residual_mm3":residual,"gt_accessed":False}
    out=ROOT/job["output"]
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result))
    if result["status"]!="PASS":raise SystemExit(2)


if __name__=="__main__":main(load(sys.argv[1]))
