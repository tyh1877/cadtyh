"""Independent 32-case C1 replay/activity gate before any formal C2 proposal."""

from __future__ import annotations

import json

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try6.scripts.run_r1_reliability import save

RESULT=HERE/"results/try6_0_c2"


def validate():
    cfg=load(HERE/"protocol/try6_0_c2.json")
    if (RESULT/"solver").exists():raise RuntimeError("formal C2 began before independent replay gate")
    construction=load(RESULT/"kfde/independent_construction_validation.json")
    if construction["status"]!="PASS":raise RuntimeError("KFDE construction not independently valid")
    history=load(ROOT/cfg["c1_result_root"]/"solver/candidate_history.json")
    replay=load(RESULT/"replay/c1_candidate_replay.json")
    if replay["requested"]!=32 or replay["completed"]!=32 or len(replay["records"])!=32:
        raise RuntimeError("C1 replay denominator incomplete")
    if replay["candidate_regeneration"] or replay["gt_access"] or replay["final_mechanics_access"]:
        raise RuntimeError("C1 replay leakage/regeneration")
    start=load(RESULT/"replay/replay_started.json")
    if start["source_C1_history_sha256"]!=sha(ROOT/cfg["c1_result_root"]/"solver/candidate_history.json"):
        raise RuntimeError("C1 candidate source history drift")
    if start["construction_report_sha256"]!=sha(RESULT/"kfde/construction_report.json"):
        raise RuntimeError("KFDE construction changed after replay")
    tolerance=cfg["numerical_forbidden_volume_tolerance_mm3"]
    results=[]
    for original,record in zip(history["history"],replay["records"]):
        if record["candidate_id"]!=original["candidate_id"] or record["status"]!="EVALUATED":
            raise RuntimeError("C1 replay case dropped/reordered")
        if record["theta"]!=original["theta"] or record["visual_loss_c1"]!=original["total_visual_objective"]:
            raise RuntimeError("C1 frozen visual candidate changed")
        raw=load(ROOT/record["kfde_raw_path"])
        if sha(ROOT/record["kfde_raw_path"])!=record["kfde_raw_sha256"]:
            raise RuntimeError("raw KFDE check altered")
        if raw["candidate_id"]!=record["candidate_id"] or raw["candidate_fcstd"]!=original["cad_artifact_path"]:
            raise RuntimeError("KFDE checked wrong CAD")
        if raw["candidate_fcstd_sha256"]!=sha(ROOT/original["cad_artifact_path"]):
            raise RuntimeError("C1 candidate CAD changed")
        feasible=raw["maximum_forbidden_intersection_mm3"]<=tolerance
        if feasible!=record["feasible"] or raw["feasible"]!=feasible:
            raise RuntimeError("KFDE feasibility decision mismatch")
        if record["maximum_forbidden_intersection_mm3"]!=raw["maximum_forbidden_intersection_mm3"]:
            raise RuntimeError("KFDE violation volume mismatch")
        if any(item["forbidden_intersection_mm3"]<=tolerance for item in raw["violating_components"]):
            raise RuntimeError("nonmeaningful component labeled violating")
        if raw["gt_accessed"] or raw["final_mechanics_evaluator_invoked"]:
            raise RuntimeError("KFDE replay invoked forbidden evaluator")
        results.append(feasible)
    summary=load(RESULT/"replay/activity_summary.json")
    rejects=sum(not x for x in results)
    selected=next(record for record in replay["records"] if record["candidate_id"]=="candidate_031")
    if rejects!=summary["infeasible_count"] or summary["rejection_rate"]!=rejects/32 or summary["c1_selected_feasible"]!=selected["feasible"]:
        raise RuntimeError("activity summary not supported by raw checks")
    if rejects==0 and selected["maximum_forbidden_intersection_mm3"]<=tolerance:
        decision="KFDE_INACTIVE"
    else:
        decision="KFDE_ACTIVE_FORMAL_C2_ALLOWED"
    lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"]!=0:raise RuntimeError("holdout lock violated")
    output={"status":"PASS","activity_decision":decision,"requested":32,"validated":32,
        "feasible_count":32-rejects,"infeasible_count":rejects,"rejection_rate":rejects/32,
        "c1_selected_feasible":selected["feasible"],
        "c1_selected_forbidden_volume_mm3":selected["maximum_forbidden_intersection_mm3"],
        "meaningful_volume_tolerance_mm3":tolerance,
        "all_source_candidate_hashes_verified":True,"no_C1_candidate_regeneration":True,
        "gt_accessed":False,"final_mechanics_accessed":False,"formal_holdout_accessed":False}
    save(RESULT/"replay/independent_activity_validation.json",output)
    print(json.dumps({"activity_decision":decision,"infeasible":rejects,"c1_selected_feasible":selected["feasible"],"gt_accessed":False}))
    return output


if __name__=="__main__":validate()
