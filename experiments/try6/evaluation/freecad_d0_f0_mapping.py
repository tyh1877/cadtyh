"""Read-only audit for an exact six-parameter F0→current-builder mapping."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import FreeCAD as App

ROOT=Path(__file__).resolve().parents[3]


def main(job):
    doc=App.openDocument(str(ROOT/job["f0_fcstd"]))
    names=[obj.Name for obj in doc.Objects]
    sheet=doc.getObject("ParameterTable")
    result={"f0_fcstd":job["f0_fcstd"],"object_names":names,
        "has_frozen_six_parameter_table":sheet is not None,
        "exact_F0_equivalent_current_theta_mapping_available":False,
        "reason":"Coarse F0 FCStd has no verified one-to-one mapping to six current R1-v3 parametric housing variables; do not manually approximate a P5 theta.",
        "GT_accessed":False}
    App.closeDocument(doc.Name)
    path=ROOT/job["output"];path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"exact_mapping_available":False,"has_parameter_table":result["has_frozen_six_parameter_table"]}))


if __name__=="__main__":main(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
