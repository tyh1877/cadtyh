"""Two development-only CAD/objective points and an URDF-anchor mutation."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import trimesh

from metric_grounding import HERE, Objective, load, dump


def main():
    config=load(HERE/"protocol/solver_smoke_config.json")
    registration=load(HERE/"results/try6_0_c1/camera_or_view_registration.json")
    parameters=load(HERE/"protocol/parameter_bounds.json")
    root=HERE/"artifacts/try6_0_c1/smoke/metric_grounding"
    objective=Objective(config,registration,parameters,root,HERE/"artifacts/try6_0_c1/smoke/point_0/synthetic_kfdg.json")
    initial=objective.initial
    second=initial.copy();second[0]=min(second[0]+1.0,objective.bounds[0,1]);second[7]=min(second[7]+.5,objective.bounds[7,1])
    rows=[objective.build_and_score(0,initial,63.0),objective.build_and_score(1,second,63.0)]
    if not all(row["status"]=="PASS" and np.isfinite(row["total"]) for row in rows): raise RuntimeError("CAD/render/objective smoke failed")
    mesh=trimesh.load(root/"candidates/candidate_000/final.stl",force="mesh",process=False)
    mutated=objective.evaluate_mesh(mesh,initial,60.0)
    if abs(rows[0]["total"]-mutated["total"])<1e-6: raise RuntimeError("URDF anchor is not consumed by the metric objective")
    right=registration["views"]["right"]["teal_bbox_px"]
    derived_width_63=(right[3]-right[1])*63/(right[2]-right[0])
    derived_width_60=(right[3]-right[1])*60/(right[2]-right[0])
    output={"schema_version":"robotcad_try6_c1_metric_smoke_v1","status":"PASS","nonformal":True,"candidate_count":2,"candidates":[{"index":row["index"],"objective":row["total"],"cad_seconds":row["seconds"]} for row in rows],"anchor_mutation":{"original_mm":63.0,"mutated_mm":60.0,"fixed_cad_objective_original":rows[0]["total"],"fixed_cad_objective_mutated":mutated["total"],"right_view_metric_height_estimate_original_mm":derived_width_63,"right_view_metric_height_estimate_mutated_mm":derived_width_60,"solver_metric_result_changed":abs(derived_width_63-derived_width_60)>1e-6},"gt_accessed":False,"motion_feedback":False}
    dump(HERE/"results/try6_0_c1/infrastructure_smoke.json",output)
    print(json.dumps(output,indent=2))


if __name__=="__main__":main()
