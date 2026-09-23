"""Independent Try-6.0-C1 result audit. Does not run generation or evaluators."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/"experiments/try6"
sys.path.insert(0,str(HERE/"scripts"))
sys.path.insert(0,str(ROOT/"experiments/try5A/evaluation"))
from kfdg_contract import validate_kfdg  # noqa: E402
from experiment_governance import validate_claim_ledger  # noqa: E402


def load(path):return json.loads(Path(path).read_text(encoding="utf-8"))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,value):Path(path).write_text(json.dumps(value,indent=2)+"\n",encoding="utf-8")


def validate_representation_failure(config_path,root,config):
    required=("protocol.json","input_hashes.json","c0_baseline.json","camera_or_view_registration.json","infrastructure_smoke.json","pre_run_manifest.json","vlm_request_manifest.json","vlm_call_started.json","vlm_call_record.json","vlm_raw_response.txt","vlm_full_response.json","vlm_failure.json","representation_failure_audit.json","decision.json","failure_accounting.json","process_metrics.json","leakage_audit.json","dataflow_audit.json","claim_ledger.json","holdout_evaluation_log.json")
    missing=[name for name in required if not (root/name).is_file()]
    if missing:return {"status":"FAIL","missing_required_files":missing,"checks":{}}
    pre=load(root/"pre_run_manifest.json");call=load(root/"vlm_call_record.json");raw=load(root/"vlm_raw_response.txt");audit=load(root/"representation_failure_audit.json");decision=load(root/"decision.json");failure=load(root/"failure_accounting.json");leak=load(root/"leakage_audit.json");camera=load(root/"camera_or_view_registration.json");c0=load(root/"c0_baseline.json");lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json");claim=validate_claim_ledger(root,load(root/"claim_ledger.json")["claims"])
    forbidden=("kfdg.json","solver_invocation.json","solver_result.json","solver_history.csv","objective_breakdown.csv","final.FCStd","final.step","final.stl","geometry_metrics.json","mechanical_metrics.json")
    checks={
        "frozen_protocol_and_inputs":load(root/"protocol.json")==config and pre["protocol_sha256"]==sha(config_path) and pre["input_hashes_sha256"]==sha(root/"input_hashes.json"),
        "exact_c0_source":c0["source_sha256"]==sha(ROOT/c0["source"]) and c0["metrics"]["link"]=="L04" and c0["metrics"]["method"]=="DIRECT_QWEN",
        "schema_first_infrastructure_smoke":load(root/"infrastructure_smoke.json")["status"]=="PASS" and camera["available"]["freecad_miba_view_matrices"] and not camera["available"]["camera_intrinsics"],
        "one_qwen_response_saved":call["status"]=="SUCCESS" and call["returned_model"]==config["model"]["requested_identifier"] and call["retry_count"]==0 and call["input_tokens"]>0 and call["output_tokens"]>0,
        "schema_root_rejected_without_rewrite":isinstance(raw,list) and len(raw)==1 and audit["response_root_type"]=="list" and audit["inner_object_used_for_generation"] is False and audit["raw_response_sha256"]==sha(root/"vlm_raw_response.txt"),
        "formal_c1_stopped_before_solver_cad_gt":all(not (root/name).exists() for name in forbidden) and failure["solver_evaluations"]==failure["cad_rebuilds"]==failure["gt_evaluations"]==0,
        "decision_matches_representation_failure":decision["decision"]=="REPRESENTATION_FAILURE" and decision["geometry_gate_evaluated"] is False,
        "no_gt_or_motion_feedback":leak["gt_generator_access"] is False and leak["gt_solver_access"] is False and leak["motion_solver_feedback"] is False,
        "holdout_unaccessed":lock["accessed"] is False and lock["evaluation_count"]==0 and load(root/"holdout_evaluation_log.json")["events"]==[] and failure["formal_holdout_accessed"] is False,
        "failure_denominator_and_no_retry":failure["mechanical_requested_development_cases"]==96 and failure["mechanical_uncomputed_due_to_schema_failure"]==96 and failure["retries"]==failure["manual_interventions"]==0,
        "claim_ledger_pass":claim["status"]=="PASS" and not claim["hard_claims_with_noncomputed_evidence"],
        "runner_did_not_self_validate":not (root/"validation.json").exists()
    }
    return {"schema_version":"robotcad_try6_c1_independent_validation_v1","status":"PASS" if all(checks.values()) else "FAIL","checks":checks,"failed_checks":[key for key,value in checks.items() if not value],"decision":"REPRESENTATION_FAILURE","formal_holdout_accessed":False,"missing_required_files":[]}


def validate(config_path,result_root):
    config=load(config_path);root=Path(result_root).resolve()
    if (root/"decision.json").is_file() and load(root/"decision.json").get("decision")=="REPRESENTATION_FAILURE" and (root/"vlm_failure.json").is_file():
        return validate_representation_failure(config_path,root,config)
    required=("protocol.json","input_hashes.json","c0_baseline.json","camera_or_view_registration.json","pre_run_manifest.json","vlm_call_record.json","vlm_raw_response.txt","vlm_full_response.json","vlm_response.json","kfdg.json","solver_config.json","solver_result.json","solver_history.csv","objective_breakdown.csv","parameter_table.json","feature_mapping.json","geometry_metrics.json","mechanical_metrics.json","process_metrics.json","leakage_audit.json","dataflow_audit.json","decision.json","failure_accounting.json","claim_ledger.json","editability_smoke.json","final.FCStd","final.step","final.stl")
    missing=[name for name in required if not (root/name).is_file()]
    if missing:return {"status":"FAIL","missing_required_files":missing,"checks":{}}
    pre=load(root/"pre_run_manifest.json");graph=load(root/"kfdg.json");solver=load(root/"solver_result.json");params=load(root/"parameter_table.json");features=load(root/"feature_mapping.json");geom=load(root/"geometry_metrics.json");mech=load(root/"mechanical_metrics.json");process=load(root/"process_metrics.json");leak=load(root/"leakage_audit.json");dataflow=load(root/"dataflow_audit.json");decision=load(root/"decision.json");failures=load(root/"failure_accounting.json");call=load(root/"vlm_call_record.json");camera=load(root/"camera_or_view_registration.json");c0=load(root/"c0_baseline.json");edit=load(root/"editability_smoke.json")
    lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    claim=validate_claim_ledger(root,load(root/"claim_ledger.json")["claims"])
    nodes={node["id"] for node in graph["functional_nodes"]+graph["geometric_features"]}
    mapped=set(features["kfdg_to_cad"])
    geometry=geom["metrics"];baseline=c0["metrics"];gates=config["success_gates"]
    geometric_gate=geometry["voxel_iou"]>=gates["final_iou_ratio_min"]*baseline["final_voxel_iou"] and geometry["silhouette_iou_mean"]>=gates["silhouette_ratio_min"]*baseline["final_silhouette_iou"] and geometry["normalized_chamfer"]<=gates["normalized_chamfer_ratio_max"]*baseline["final_normalized_chamfer"] and geometry["normalized_hd95"]<=gates["normalized_hd95_ratio_max"]*baseline["final_normalized_hd95"] and (geometry["normalized_chamfer"]<baseline["final_normalized_chamfer"] or geometry["normalized_hd95"]<baseline["final_normalized_hd95"])
    representation=mech["bicr"]==1 and mech["connected_solid_count"]==1 and edit["status"]=="PASS" and process["final_freecad_build_success"] and validate_kfdg(graph)
    expected_decision="GO_C2" if representation and geometric_gate else ("METRIC_GROUNDING_WEAK" if representation else "REPRESENTATION_FAILURE")
    checks={
      "protocol_snapshot":load(root/"protocol.json")==config and pre["protocol_sha256"]==sha(config_path),
      "frozen_c0_exact":c0["source_sha256"]==sha(ROOT/c0["source"]) and baseline["method"]=="DIRECT_QWEN" and baseline["link"]=="L04",
      "schema_and_parameters":validate_kfdg(graph) and len(params["parameters"])==9 and all(item["unit"]=="mm" for item in params["parameters"]),
      "same_frozen_evaluators":pre["geometry_evaluator_sha256"]==sha(ROOT/config["evaluation"]["geometry_evaluator"]) and pre["exact_evaluator_sha256"]==sha(ROOT/config["evaluation"]["exact_mechanical_evaluator"]),
      "camera_audit_honest":camera["available"]["freecad_miba_view_matrices"] and not camera["available"]["camera_intrinsics"] and camera["selected_solver_views"]==["right","top"],
      "urdf_anchor_consumed":dataflow["urdf_anchor_mutation_effect"] and graph["metric_anchor"]["distance_mm"]==63,
      "vlm_one_call":call["status"]=="SUCCESS" and call["returned_model"]==config["model"]["requested_identifier"] and call["retry_count"]==0 and process["vlm_calls"]==1,
      "solver_budget_and_integrity":solver["status"]=="PASS" and 1<=solver["actual_evaluations"]<=config["solver"]["max_solver_evaluations"] and solver["gt_accessed"] is False and solver["motion_feedback"] is False and solver["solver_runtime_seconds"]<=config["solver"]["max_runtime_seconds"]+5,
      "feature_history_mapping":nodes<=mapped and features["final_reopen"]["valid"] and edit["status"]=="PASS" and dataflow["all_nine_parameters_sheet_bound"],
      "cad_artifacts_nonempty":all((root/name).stat().st_size>100 for name in ("final.FCStd","final.step","final.stl")),
      "mechanical_denominator":mech["configuration_count"]==96 and failures["mechanical_completed_cases"]==96 and len(mech["failed_configuration_ids"])==failures["mechanical_failed_configurations"],
      "no_gt_or_motion_feedback_to_solver":leak["gt_generator_access"] is False and leak["gt_solver_access"] is False and leak["motion_solver_feedback"] is False,
      "formal_holdout_unused":lock["accessed"] is False and lock["evaluation_count"]==0 and leak["formal_holdout_accessed"] is False,
      "success_gate_recomputed":decision["decision"]==expected_decision and decision["geometry_gate_pass"]==geometric_gate and decision["representation_gate_pass"]==representation,
      "claim_ledger_pass":claim["status"]=="PASS" and not claim["hard_claims_with_noncomputed_evidence"],
      "runner_did_not_self_validate":not (root/"validation.json").exists()
    }
    return {"schema_version":"robotcad_try6_c1_independent_validation_v1","status":"PASS" if all(checks.values()) else "FAIL","checks":checks,"failed_checks":[key for key,value in checks.items() if not value],"decision":expected_decision,"formal_holdout_accessed":False,"missing_required_files":[]}


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--config",required=True);parser.add_argument("--result-dir",required=True);args=parser.parse_args()
    result=validate(args.config,args.result_dir);dump(Path(args.result_dir)/"validation.json",result);print(json.dumps(result,indent=2));return 0 if result["status"]=="PASS" else 1


if __name__=="__main__":raise SystemExit(main())
