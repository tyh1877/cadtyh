"""Independent visual-only solver audit before final candidate build/GT."""

from __future__ import annotations

import json
import math

from experiments.try6.scripts.r1_contract import HERE,load,sha
from experiments.try6.scripts.c1_v2_visual_objective import VisibleObjective
from experiments.try6.scripts.run_r1_reliability import save
from experiments.try6.scripts.r1_contract import ROOT

RESULT=HERE/"results/try6_0_c1_v2"


def validate():
    cfg=load(HERE/"protocol/try6_0_c1_v2.json")
    if (RESULT/"evaluation/final_candidate_lock.json").exists():
        raise RuntimeError("solver validation must precede final candidate lock")
    slot=load(RESULT/"slot/independent_validation.json")
    if slot["status"]!="PASS":raise RuntimeError("independent representation gate failed")
    active=load(RESULT/"kfdg/active_parameters.json")
    hist=load(RESULT/"solver/candidate_history.json")
    theta=load(RESULT/"solver/theta_selected.json")
    rows=hist["history"]
    if len(rows)!=hist["evaluated"] or len(rows)>cfg["solver"]["max_candidate_evaluations"]:
        raise RuntimeError("solver denominator mismatch")
    if any(row["candidate_id"]!=f"candidate_{i:03d}" for i,row in enumerate(rows)):
        raise RuntimeError("candidate ID sequence incomplete")
    if any(row["active_parameters"]!=active["active_ids"] for row in rows):
        raise RuntimeError("active parameter set changed")
    valid=[row for row in rows if row["status"]=="PASS"]
    if len(valid)!=hist["valid"] or len(rows)-len(valid)!=hist["invalid"] or not valid:
        raise RuntimeError("candidate validity denominator mismatch")
    best=min(valid,key=lambda row:row["total_visual_objective"])
    if theta["selected_candidate_id"]!=best["candidate_id"] or theta["theta_star"]!=best["theta"]:
        raise RuntimeError("selected candidate not visual minimum")
    if theta["gt_accessed"] or theta["mechanical_feedback"]:
        raise RuntimeError("GT/mechanics entered solver")
    if any(not math.isfinite(row["total_visual_objective"]) for row in valid):
        raise RuntimeError("non-finite objective")
    objective=VisibleObjective()
    recalculated=objective.evaluate(ROOT/best["body_stl_path"])
    if abs(recalculated["total"]-best["total_visual_objective"])>1e-9:
        raise RuntimeError("selected objective not reproducible from raw evidence")
    evidence=load(RESULT/"visual_metric_evidence/evidence_audit.json")
    if not evidence["registration_gate_pass"] or not evidence["evidence_gate_pass"]:
        raise RuntimeError("visual evidence gate failed")
    report={"status":"PASS","candidate_count":len(rows),"valid_count":len(valid),
        "invalid_count":hist["invalid"],"selected_candidate_id":best["candidate_id"],
        "selected_visual_objective":best["total_visual_objective"],
        "independent_recomputed_objective":recalculated["total"],
        "selection_by_visual_only":True,"registration_frozen":True,
        "gt_evaluations":0,"mechanical_evaluations":0,"formal_holdout_evaluations":0,
        "history_sha256":sha(RESULT/"solver/candidate_history.json")}
    save(RESULT/"solver/independent_validation.json",report)
    print(json.dumps({"status":"PASS","candidate_count":len(rows),
        "selected_candidate_id":best["candidate_id"],"gt_evaluations":0}))
    return report


if __name__=="__main__":validate()
