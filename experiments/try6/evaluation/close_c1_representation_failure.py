"""Close the one-shot C1 attempt after an invalid KFDG response envelope."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/"experiments/try6"
sys.path.insert(0,str(HERE/"scripts"))
from kfdg_contract import validate_vlm  # noqa: E402


def load(path):return json.loads(Path(path).read_text(encoding="utf-8"))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,value):Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--config",required=True);args=parser.parse_args()
    root=HERE/"results/try6_0_c1"
    if (root/"decision.json").exists():raise FileExistsError("C1 attempt already closed")
    config=load(args.config);call=load(root/"vlm_call_record.json");failure=load(root/"vlm_failure.json");raw_path=root/"vlm_raw_response.txt";raw=load(raw_path)
    if call["status"]!="SUCCESS" or failure["status"]!="REPRESENTATION_FAILURE" or not isinstance(raw,list):raise RuntimeError("failure evidence mismatch")
    if (root/"kfdg.json").exists() or (root/"solver_invocation.json").exists() or (root/"geometry_metrics.json").exists():raise RuntimeError("fail-closed boundary violated")
    inner_valid=False
    if len(raw)==1 and isinstance(raw[0],dict):
        try:
            validate_vlm(raw[0]);inner_valid=True
        except Exception:
            inner_valid=False
    source=ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json";lock=load(source)
    if lock["accessed"] is not False or lock["evaluation_count"]!=0:raise RuntimeError("formal holdout accessed")
    dump(root/"representation_failure_audit.json",{"schema_version":"robotcad_try6_c1_representation_failure_v1","response_root_type":type(raw).__name__,"response_array_length":len(raw),"inner_object_schema_valid_read_only":inner_valid,"inner_object_used_for_generation":False,"requested_json_schema_sha256":sha(ROOT/config["vlm_response_schema"]),"raw_response_sha256":sha(raw_path),"failure_stage":"KFDG_TOP_LEVEL_TYPED_CONTRACT","model_returned":call["returned_model"],"finish_reason":load(root/"vlm_full_response.json")["choices"][0]["finish_reason"],"provider_system_fingerprint":call["system_fingerprint"],"retry_count":0})
    dump(root/"decision.json",{"decision":"REPRESENTATION_FAILURE","reason":"Constrained JSON Schema request returned a one-element array rather than the required top-level object; fail-closed validator rejected the unmodified response.","kfdg_schema_valid":False,"formal_solver_executed":False,"c1_cad_generated":False,"geometry_gate_evaluated":False,"motion_metrics_evaluated":False,"c0_exact_iou":load(root/"c0_baseline.json")["metrics"]["final_voxel_iou"],"formal_holdout_accessed":False})
    dump(root/"failure_accounting.json",{"requested_formal_runs":1,"attempted_formal_runs":1,"completed_c1_cad_runs":0,"vlm_calls":1,"vlm_transport_failures":0,"schema_failures":1,"solver_requested_budget":config["solver"]["max_solver_evaluations"],"solver_evaluations":0,"cad_rebuilds":0,"mechanical_requested_development_cases":96,"mechanical_completed_development_cases":0,"mechanical_uncomputed_due_to_schema_failure":96,"gt_evaluations":0,"manual_interventions":0,"retries":0,"formal_holdout_accessed":False})
    dump(root/"process_metrics.json",{"vlm_calls":1,"requested_model":call["requested_model"],"returned_model":call["returned_model"],"request_id":call["request_id"],"input_tokens":call["input_tokens"],"output_tokens":call["output_tokens"],"vlm_latency_seconds":call["latency_seconds"],"solver_evaluations":0,"solver_runtime_seconds":0,"cad_rebuild_count":0,"failed_cad_candidates":0,"final_freecad_build_success":False,"manual_intervention_count":0,"retry_count":0})
    dump(root/"leakage_audit.json",{"vlm_request_sha256":sha(root/"vlm_request_manifest.json"),"allowed_generator_inputs":["raw_images","engineering_text","sanitized_urdf","f0_fcstd","neutral_interface_context"],"gt_generator_access":False,"gt_solver_access":False,"gt_evaluator_access":False,"motion_solver_feedback":False,"formal_holdout_accessed":False})
    dump(root/"dataflow_audit.json",{"vlm_response_sha256":sha(raw_path),"schema_rejected_top_level":True,"kfdg_materialized":False,"metric_solver_invoked":False,"cad_feature_history_built_formally":False,"urdf_anchor_mutation_smoke_pass":load(root/"infrastructure_smoke.json")["anchor_mutation"]["solver_metric_result_changed"],"no_gt_leakage":True})
    dump(root/"claim_ledger.json",{"claims":[{"claim_id":"one_model_call","hard":True,"evidence_type":"computed","artifact":"failure_accounting.json","field":"vlm_calls","operator":"eq","expected":1},{"claim_id":"schema_failure","hard":True,"evidence_type":"computed","artifact":"failure_accounting.json","field":"schema_failures","operator":"eq","expected":1},{"claim_id":"no_solver_invocation","hard":True,"evidence_type":"computed","artifact":"failure_accounting.json","field":"solver_evaluations","operator":"eq","expected":0},{"claim_id":"holdout_unaccessed","hard":True,"evidence_type":"computed","artifact":"failure_accounting.json","field":"formal_holdout_accessed","operator":"eq","expected":False}]})
    print(json.dumps({"status":"FORMAL_C1_STOPPED","decision":"REPRESENTATION_FAILURE","model_calls":1,"solver_evaluations":0,"holdout_accessed":False},indent=2))


if __name__=="__main__":main()
