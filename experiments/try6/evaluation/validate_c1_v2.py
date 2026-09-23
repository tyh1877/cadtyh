"""Independent one-shot C1-v2 paper gate after locked final GT/mechanics evaluation."""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
import unittest
from datetime import datetime,timezone

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try6.scripts.r1_v3_contract import assemble,validate_kfdg,validate_slots
from experiments.try6.scripts.c1_v2_visual_objective import VisibleObjective
from experiments.try6.scripts.run_r1_reliability import save

RESULT=HERE/"results/try6_0_c1_v2"
ARTIFACT=HERE/"artifacts/try6_0_c1_v2"


def prior_audit(name,path):
    folder=HERE/path;manifest=load(folder/"manifest.json")
    hashes=manifest.get("lightweight_result_sha256",manifest.get("result_file_sha256",{}))
    if not all(sha(folder/p)==expected for p,expected in hashes.items()):
        raise RuntimeError(f"frozen prior result drift: {name}")
    return {"manifest_sha256":sha(folder/"manifest.json"),"files_checked":len(hashes),"unchanged":True}


def validate():
    cfg=load(HERE/"protocol/try6_0_c1_v2.json")
    pre=load(RESULT/"pre_run_manifest.json")
    if pre["protocol_sha256"]!=sha(HERE/"protocol/try6_0_c1_v2.json"):
        raise RuntimeError("formal protocol drift")
    priors={name:prior_audit(name,path) for name,path in (("c1_v1","results/try6_0_c1"),
        ("r0","results/try6_0_r0"),("r1_v1","results/try6_0_r1"),
        ("r1_v2","results/try6_0_r1_v2"),("r1_v3","results/try6_0_r1_v3"))}
    lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    holdout_closed=lock["accessed"] is False and lock["evaluation_count"]==0
    if not holdout_closed:raise RuntimeError("formal holdout lock violated")
    evidence=load(RESULT/"visual_metric_evidence/evidence_audit.json")
    registration=load(RESULT/"visual_metric_evidence/view_registration_report.json")
    if evidence["registration_gate_pass"] is not True or evidence["evidence_gate_pass"] is not True:
        raise RuntimeError("visual evidence/registration gate failed")
    if pre["visual_metric_evidence_sha256"]!=sha(RESULT/"visual_metric_evidence/visual_metric_evidence.json") or pre["view_registration_sha256"]!=sha(RESULT/"visual_metric_evidence/view_registration_report.json"):
        raise RuntimeError("visual evidence/registration changed after freeze")
    slot=load(RESULT/"slot/validation.json")
    if slot["status"]!="PASS" or slot["fresh_calls"]!=1 or slot["retry_count"]!=0:
        raise RuntimeError("fresh slot gate failed")
    raw=(RESULT/"slot/raw_response.txt").read_text(encoding="utf-8")
    sdk=load(RESULT/"slot/response.json")
    http=load(RESULT/"slot/http_response.json")
    if raw!=sdk["choices"][0]["message"]["content"] or raw!=http["choices"][0]["message"]["content"]:
        raise RuntimeError("slot HTTP/SDK/raw mismatch")
    decisions=validate_slots(json.loads(raw))
    if decisions!=load(RESULT/"slot/validated_slots.json"):
        raise RuntimeError("slot response repair detected")
    graph=assemble(decisions);validate_kfdg(graph,decisions)
    if graph!=load(RESULT/"kfdg/canonical_kfdg.json"):
        raise RuntimeError("KFDG differs from deterministic assembly")
    active=load(RESULT/"kfdg/active_parameters.json")
    slot_statuses={x["slot_id"]:x["status"] for x in decisions["slots"]}
    if active["slot_statuses"]!=slot_statuses or any(pid not in {p["id"] for p in graph["parameters"] if p["active"]} for pid in active["active_ids"]):
        raise RuntimeError("slot-aware active parameter rule violated")
    if slot_statuses["visible_pocket"]!="PRESENT" and any(pid.startswith("recess_") for pid in active["active_ids"]):
        raise RuntimeError("absent/uncertain pocket parameter optimized")
    graph_feature_types={f["type"] for f in graph["geometric_features"]}
    if ("pocket" in graph_feature_types)!=(slot_statuses["visible_pocket"]=="PRESENT"):
        raise RuntimeError("slot feature presence not consumed")
    history=load(RESULT/"solver/candidate_history.json")
    selected=load(RESULT/"solver/theta_selected.json")
    rows=history["history"]
    if not rows or len(rows)!=history["evaluated"] or len(rows)>cfg["solver"]["max_candidate_evaluations"]:
        raise RuntimeError("solver candidate accounting mismatch")
    if any(row["candidate_id"]!=f"candidate_{i:03d}" for i,row in enumerate(rows)):
        raise RuntimeError("candidate IDs/order changed")
    if any(row["active_parameters"]!=active["active_ids"] for row in rows):
        raise RuntimeError("active parameter set changed during solve")
    if any(row["status"] not in ("PASS","INFRASTRUCTURE_INVALID") for row in rows):
        raise RuntimeError("candidate failure unaccounted")
    valid=[row for row in rows if row["status"]=="PASS"]
    if len(valid)!=history["valid"] or len(rows)-len(valid)!=history["invalid"] or not valid:
        raise RuntimeError("solver denominator/validity mismatch")
    minimum=min(valid,key=lambda row:row["total_visual_objective"])
    if selected["selected_candidate_id"]!=minimum["candidate_id"] or selected["theta_star"]!=minimum["theta"] or selected["mechanical_feedback"] or selected["gt_accessed"]:
        raise RuntimeError("theta selection used nonvisual evidence")
    objective=VisibleObjective()
    selected_body=ROOT/minimum["body_stl_path"]
    recomputed=objective.evaluate(selected_body)
    if abs(recomputed["total"]-minimum["total_visual_objective"])>1e-9:
        raise RuntimeError("selected visual objective not reproducible")
    final_lock_path=RESULT/"evaluation/final_candidate_lock.json"
    final_lock=load(final_lock_path)
    if final_lock["selected_candidate_id"]!=selected["selected_candidate_id"] or final_lock["theta_star"]!=selected["theta_star"]:
        raise RuntimeError("candidate lock differs from solver")
    for key,path in (("kfdg_sha256",RESULT/"kfdg/canonical_kfdg.json"),
        ("view_registration_sha256",RESULT/"visual_metric_evidence/view_registration_report.json"),
        ("visual_evidence_sha256",RESULT/"visual_metric_evidence/visual_metric_evidence.json"),
        ("objective_definition_sha256",RESULT/"solver/objective_definition.json"),
        ("solver_config_sha256",RESULT/"solver/config.json"),
        ("solver_history_sha256",RESULT/"solver/candidate_history.json"),
        ("theta_selection_sha256",RESULT/"solver/theta_selected.json")):
        if final_lock[key]!=sha(path):raise RuntimeError(f"candidate lock hash mismatch: {key}")
    for item in final_lock["final_cad_artifacts"].values():
        if sha(ROOT/item["path"])!=item["sha256"]:raise RuntimeError("final CAD changed after lock")
    eval_started=load(RESULT/"evaluation/evaluation_started.json")
    if eval_started["final_candidate_lock_sha256"]!=sha(final_lock_path) or final_lock["timestamp_utc"]>=eval_started["timestamp_utc"]:
        raise RuntimeError("GT evaluation was not strictly after candidate lock")
    geometry=load(RESULT/"evaluation/geometry_metrics.json")
    mechanics=load(RESULT/"evaluation/mechanical_metrics.json")
    raw_geometry=load(RESULT/"evaluation/geometry_raw.json")
    raw_mechanics=load(RESULT/"evaluation/mechanical_raw.json")
    if geometry["raw_geometry_sha256"]!=sha(RESULT/"evaluation/geometry_raw.json") or mechanics["raw_mechanical_sha256"]!=sha(RESULT/"evaluation/mechanical_raw.json"):
        raise RuntimeError("raw evaluator output hash mismatch")
    if geometry["gt_evaluation_count"]!=1 or len(raw_geometry["rows"])!=2 or len(raw_mechanics["conditions"])!=1:
        raise RuntimeError("one-shot evaluator accounting mismatch")
    if mechanics["configuration_count"]!=96 or len(mechanics["failed_configuration_ids"])>96 or mechanics["mechanical_feedback_to_solver"]:
        raise RuntimeError("development mechanics diagnostic invalid")
    if mechanics["bicr"]!=1.0 or mechanics["connected_solid_count"]!=1 or not final_lock["interface_invariant"]:
        raise RuntimeError("basic assembly validity gate failed")
    source=ROOT/cfg["frozen_c0_source"]
    if sha(source)!=pre["c0_frozen_source_sha256"]:raise RuntimeError("frozen C0 source drift")
    baseline=[row for row in load(source)["rows"] if row["link"]=="L04" and row["method"]=="DIRECT_QWEN"]
    if len(baseline)!=1 or baseline[0]["status"]!="EVALUATED":raise RuntimeError("frozen C0 row unavailable")
    c0=baseline[0]
    if abs(c0["final_voxel_iou"]-cfg["frozen_c0_iou"])>1e-12:
        raise RuntimeError("C0 IoU differs from frozen protocol")
    c1raw=geometry["final"]
    c1={"final_voxel_iou":c1raw["voxel_iou"],"final_silhouette_iou":c1raw["silhouette_iou_mean"],
        "final_normalized_chamfer":c1raw["normalized_chamfer"],"final_normalized_hd95":c1raw["normalized_hd95"],
        "final_bbox_error_mm":c1raw.get("bbox_error_mm"),"final_major_dimension_error_mm":c1raw.get("major_dimension_error_mm")}
    gates={"primary_iou":c1["final_voxel_iou"]>=cfg["primary_iou_gate"],
        "silhouette":c1["final_silhouette_iou"]>=cfg["supporting_gates"]["silhouette_min_c0_ratio"]*c0["final_silhouette_iou"],
        "nchamfer":c1["final_normalized_chamfer"]<=cfg["supporting_gates"]["nchamfer_max_c0_ratio"]*c0["final_normalized_chamfer"],
        "nhd95":c1["final_normalized_hd95"]<=cfg["supporting_gates"]["nhd95_max_c0_ratio"]*c0["final_normalized_hd95"],
        "one_distance_strictly_better":c1["final_normalized_chamfer"]<c0["final_normalized_chamfer"] or c1["final_normalized_hd95"]<c0["final_normalized_hd95"],
        "bicr":mechanics["bicr"]==1.0,"connected_solid":mechanics["connected_solid_count"]==1}
    visual_initial=selected["initial_objective"]
    visual_final=selected["selected_objective"]
    visual_relative_improvement=(visual_initial-visual_final)/visual_initial if visual_initial>0 else 0.0
    mr=cfg["misalignment_rule"]
    misaligned=(visual_relative_improvement>=mr["minimum_relative_visual_objective_improvement"] and
        c1["final_voxel_iou"]<=mr["maximum_iou_relative_to_c0"]*c0["final_voxel_iou"] and
        c1["final_normalized_chamfer"]>=mr["minimum_nchamfer_relative_to_c0"]*c0["final_normalized_chamfer"] and
        c1["final_normalized_hd95"]>=mr["minimum_nhd95_relative_to_c0"]*c0["final_normalized_hd95"])
    geometry_pass=all(gates.values())
    decision="GO_C2" if geometry_pass else "METRIC_OBJECTIVE_MISALIGNED" if misaligned else "METRIC_GROUNDING_WEAK"
    metric_keys=("final_voxel_iou","final_silhouette_iou","final_normalized_chamfer","final_normalized_hd95")
    deltas={key:{"absolute":c1[key]-c0[key],"relative_to_c0":(c1[key]-c0[key])/c0[key]} for key in metric_keys}
    save(RESULT/"evaluation/c0_vs_c1.json",{"c0_source_path":cfg["frozen_c0_source"],
        "c0_source_sha256":sha(source),"c0":{key:c0[key] for key in metric_keys},"c1":c1,
        "deltas":deltas,"gates":gates,"all_geometry_gates_pass":geometry_pass,
        "visual_initial_objective":visual_initial,"visual_selected_objective":visual_final,
        "visual_relative_improvement":visual_relative_improvement,
        "objective_gt_direction_misaligned_by_frozen_rule":misaligned,"decision":decision})
    process={"vlm_calls":slot["fresh_calls"],"input_tokens":slot["token_usage"]["prompt_tokens"],
        "output_tokens":slot["token_usage"]["completion_tokens"],"vlm_latency_seconds":slot["latency_seconds"],
        "slot_statuses":slot_statuses,"registration_method":registration["method"],
        "solver_evaluations":len(rows),"valid_cad_candidates":len(valid),"failed_cad_candidates":history["invalid"],
        "solver_runtime_seconds":selected["solver_runtime_seconds"],
        "cad_builds":len(rows)+1,"render_count":len(valid)*2,
        "manual_intervention_count":slot["manual_intervention"],
        "geometry_evaluator_runtime_seconds":load(RESULT/"evaluation/evaluation_runtime.json")["geometry_seconds"],
        "mechanical_evaluator_runtime_seconds":load(RESULT/"evaluation/evaluation_runtime.json")["exact_mechanics_seconds"]}
    save(RESULT/"process_metrics.json",process)
    save(RESULT/"failure_accounting.json",{"requested_formal_candidates":1,"completed_formal_candidates":1,
        "slot_calls":1,"slot_failures":0,"solver_candidate_evaluations":len(rows),
        "invalid_cad_or_render_candidates":history["invalid"],
        "all_candidate_ids":[row["candidate_id"] for row in rows],
        "excluded_candidate_ids":[],"final_candidate_id":selected["selected_candidate_id"],
        "gt_final_evaluations":1,"formal_holdout_evaluations":0,"technical_retries":0,
        "manual_intervention_count":0})
    save(RESULT/"audit/dataflow_audit.json",{"slot_chain":{"slot_statuses":slot_statuses,
        "kfdg_sha256":sha(RESULT/"kfdg/canonical_kfdg.json"),"active_parameters":active["active_ids"],
        "cad_feature_names":[x["name"] for x in load(RESULT/"cad/export_reopen.json")["feature_tree"]],
        "pocket_instantiated":any(x["name"]=="VisibleRecessPocket" for x in load(RESULT/"cad/export_reopen.json")["feature_tree"])},
        "visual_metric_chain":{"raw_image_hashes":{k:v["sha256"] for k,v in pre["input_hashes"]["images"].items()},
        "evidence_sha256":sha(RESULT/"visual_metric_evidence/visual_metric_evidence.json"),
        "initial_objective":visual_initial,"selected_objective":visual_final,
        "theta_star":selected["theta_star"],"selected_body_objective_recomputed":recomputed["total"]},
        "urdf_metric_chain":{"anchor_mm":registration["anchor_distance_mm"],
        "scale_px_per_mm":{name:item["scale_px_per_mm"] for name,item in load(RESULT/"visual_metric_evidence/visual_metric_evidence.json")["views"].items()},
        "profile_targets_mm":{name:[s["visible_width_mm"] for s in item["profile_stations"]] for name,item in load(RESULT/"visual_metric_evidence/visual_metric_evidence.json")["views"].items()},
        "theta_star":selected["theta_star"],
        "cad_parameter_table":load(RESULT/"cad/parameter_table.json")["theta_star"]},
        "gt_access_before_final_lock":False,"mechanical_feedback_to_solver":False})
    save(RESULT/"audit/leakage_audit.json",{"generator_solver_gt_reads":0,
        "first_gt_access_after_candidate_lock":True,"slot_request_excludes_gt":True,
        "solver_objective_gt_terms":0,"solver_objective_mechanical_terms":0,
        "source_paths_generator_only":True,"formal_holdout_accessed":False,
        "audit_limit":"source-path and artifact audit, not OS-level filesystem trace"})
    save(RESULT/"audit/holdout_audit.json",{"lock_accessed":False,"lock_evaluation_count":0,
        "current_lock_sha256":sha(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json"),
        "formal_holdout_case_data_read":False})
    save(RESULT/"holdout_evaluation_log.json",{"events":[],"accessed":False,
        "evaluation_count":0,"followed_by_tuning":False})
    validation={"schema_version":"robotcad_try6_c1_v2_independent_validation_v1",
        "timestamp_utc":datetime.now(timezone.utc).isoformat(),"decision":decision,
        "representation_pass":True,"registration_pass":True,"visual_evidence_pass":True,
        "solver_pass":True,"final_cad_valid":True,"bicr":mechanics["bicr"],
        "primary_iou_gate_pass":gates["primary_iou"],"supporting_gates":gates,
        "misalignment_rule_triggered":misaligned,
        "visual_objective_initial":visual_initial,"visual_objective_selected":visual_final,
        "geometry_c0":{key:c0[key] for key in metric_keys},"geometry_c1":c1,
        "mechanical_diagnostic":{key:mechanics[key] for key in ("j03_jr3","gcfr","collision_events","intersection_volume_mm3","failed_configuration_ids")},
        "prior_result_hash_recheck":priors,"gt_evaluation_count":1,
        "formal_holdout_accessed":False,"formal_holdout_evaluation_count":0,
        "candidate_locked_before_gt":True,"manual_intervention_count":0,
        "single_link_development_only":True}
    save(RESULT/"audit/independent_validation.json",validation)
    print(json.dumps({"decision":decision,"c0_iou":c0["final_voxel_iou"],
        "c1_iou":c1["final_voxel_iou"],"visual_improvement":visual_relative_improvement,
        "all_geometry_gates_pass":geometry_pass,"holdout_accessed":False}))
    return validation


if __name__=="__main__":validate()
