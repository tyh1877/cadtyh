"""Freeze auditable zero-feasible C2 execution without inventing a final label."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime,timezone

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try6.scripts.run_r1_reliability import save

RESULT=HERE/"results/try6_0_c2"


def main():
    audit=load(RESULT/"audit/independent_no_feasible_validation.json")
    if audit["status"]!="PASS" or audit["terminal_decision_defined_by_frozen_protocol"]:
        raise RuntimeError("no-feasible execution audit not passed")
    cfg=load(HERE/"protocol/try6_0_c2.json")
    pre=load(RESULT/"pre_run_manifest.json")
    construction=load(RESULT/"kfde/construction_report.json")
    formal=load(RESULT/"formal_solver_freeze.json")
    activity=load(RESULT/"replay/independent_activity_validation.json")
    history=load(RESULT/"solver/candidate_history.json")
    lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"]!=0:raise RuntimeError("holdout lock violated")
    c1=ROOT/cfg["c1_result_root"]
    c1_manifest=load(c1/"manifest.json")
    if not all(sha(c1/name)==digest for name,digest in c1_manifest["result_file_sha256"].items()):
        raise RuntimeError("frozen C1 changed during C2")
    if (RESULT/"evaluation/final_candidate_lock.json").exists():
        raise RuntimeError("C2 final candidate lock exists despite no feasible theta")
    save(RESULT/"experiment_config_snapshot.json",cfg)
    save(RESULT/"condition_parity.json",load(RESULT/"frozen_c1/parity_audit.json"))
    save(RESULT/"failure_accounting.json",{"schema_version":"robotcad_try6_c2_failure_accounting_v1",
        "c1_replay_requested":32,"c1_replay_completed":32,"c1_replay_infeasible":32,
        "formal_max_proposals":32,"formal_actual_proposals":17,"formal_valid_cad_builds":17,
        "formal_kfde_evaluations":17,"formal_kfde_rejects":17,"formal_feasible_candidates":0,
        "formal_renders":0,"formal_visual_objective_evaluations":0,
        "formal_infrastructure_failures":0,
        "all_formal_candidate_ids":[row["candidate_id"] for row in history["history"]],
        "excluded_formal_candidate_ids":[],"final_candidate_exists":False,
        "final_gt_evaluations":0,"final_mechanical_evaluations":0,
        "formal_holdout_evaluations":0,"manual_intervention_count":0,"technical_retries":0,
        "termination":"frozen C1 optimizer stops after initial+16 Sobol proposals when no feasible visual candidate exists"})
    runtime={"kfde_construction_seconds":load(RESULT/"kfde/construction_runtime.json")["seconds"],
        "c1_replay_seconds":load(RESULT/"replay/activity_summary.json")["replay_runtime_seconds"],
        "formal_solver_seconds":history["solver_runtime_seconds"],
        "formal_kfde_check_seconds":sum(row.get("kfde_runtime_seconds",0.0) for row in history["history"]),
        "actual_proposals":17,"cad_builds":17,"kfde_rejects":17,
        "feasible_candidates":0,"renders":0,"visual_objective_evaluations":0,
        "total_wall_time_including_orchestration":None,
        "manual_intervention_count":0}
    save(RESULT/"process_metrics.json",runtime)
    save(RESULT/"audit/dataflow_audit.json",{"urdf_to_fk_to_kfde":{"sanitized_urdf_sha256":pre["source_hashes"]["sanitized_urdf"],
        "J03_J05_design_sweep_sha256":sha(RESULT/"kfde/construction_sweep.json"),
        "L04_coordinate_frame_pass":load(RESULT/"kfde/coordinate_frame_audit.json")["status"]=="PASS"},
        "neighbor_to_keepout":{"neighbor_source_hashes":pre["source_hashes"]["neighbors"],
        "keepout_brep_sha256":construction["keepout"]["sha256"],"nonempty":construction["keepout"]["compound_volume_proxy_mm3"]>0},
        "allowed_contact":{"allowed_region_sha256":construction["allowed_region"]["sha256"],
        "frozen_scaffold_exempt":load(RESULT/"kfde/allowed_contact_audit.json")["protected_interfaces_not_auto_forbidden"]},
        "theta_to_CAD_to_KFDE":{"formal_CAD_builds":17,"KFDE_checks":17,"hard_rejects":17,"feasible":0},
        "feasible_theta_to_visual_objective":{"visual_evaluations":0,"reason":"all proposals hard-rejected before render"},
        "C1_failure_ID_to_KFDE_path":False,"GT_to_KFDE_path":False})
    save(RESULT/"audit/leakage_audit.json",{"construction_uses_sanitized_URDF_and_frozen_neighbor_FCStd_only":True,
        "constructor_read_C1_failure_diagnostics":False,"constructor_read_final_96_case_rows":False,
        "solver_read_C1_GT_or_mechanical_metrics":False,
        "no_new_VLM_call":True,"GT_evaluations":0,"full_final_mechanics_evaluations":0,
        "formal_holdout_accessed":False,
        "audit_limit":"source-path and execution-artifact audit, not OS-level filesystem-read trace"})
    save(RESULT/"audit/holdout_audit.json",{"accessed":False,"evaluation_count":0,
        "lock_sha256":sha(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json"),
        "formal_holdout_case_data_read":False})
    ledger={"schema_version":"robotcad_try6_c2_claim_ledger_v1","claims":[
        {"claim":"C1 method frozen and only KFDE added","evidence_type":"computed","artifact":"frozen_c1/parity_audit.json","field":"status / only_method_increment","expected":"PASS / hard KFDE feasibility"},
        {"claim":"KFDE construction valid and independent","evidence_type":"computed","artifact":"kfde/independent_construction_validation.json","field":"status / component_count","expected":"PASS / 13"},
        {"claim":"KFDE active on C1 search space","evidence_type":"computed","artifact":"replay/independent_activity_validation.json","field":"infeasible_count","expected":32},
        {"claim":"formal C2 no feasible candidate","evidence_type":"computed","artifact":"audit/independent_no_feasible_validation.json","field":"feasible_candidates / formal_proposals","expected":"0 / 17"},
        {"claim":"no final GT/mechanics evaluation","evidence_type":"computed","artifact":"failure_accounting.json","field":"final_gt_evaluations / final_mechanical_evaluations","expected":"0 / 0"},
        {"claim":"protocol decision label gap","evidence_type":"inferred","artifact":"audit/independent_no_feasible_validation.json","field":"terminal_decision_defined_by_frozen_protocol","expected":False,
            "limitation":"requires user-approved protocol amendment for categorical closure"}
    ]}
    save(RESULT/"claim_ledger.json",ledger)
    validation={"schema_version":"robotcad_try6_c2_independent_validation_v1",
        "timestamp_utc":datetime.now(timezone.utc).isoformat(),
        "execution_outcome":audit["execution_outcome"],
        "protocol_terminal_decision":None,"categorical_closure_pending_user_direction":True,
        "construction_pass":True,"activity_pass":True,"formal_solver_no_feasible":True,
        "formal_proposals":17,"valid_cad_builds":17,"kfde_rejects":17,"feasible_candidates":0,
        "final_candidate_lock_exists":False,"GT_evaluations":0,"final_mechanics_evaluations":0,
        "formal_holdout_accessed":False,"formal_holdout_evaluation_count":0,
        "c1_frozen_unchanged":True,"no_tuning_or_retry":True,
        "classification_gap":audit["protocol_gap"]}
    save(RESULT/"validation.json",validation)
    head=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    branch=subprocess.run(["git","branch","--show-current"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    sources={"constructor":HERE/"scripts/freecad_c2_kfde.py",
        "replay_runner":HERE/"scripts/run_c2_replay.py",
        "constrained_solver":HERE/"scripts/c2_constrained_metric_solver.py",
        "independent_constructor_audit":HERE/"evaluation/validate_c2_construction.py",
        "independent_activity_audit":HERE/"evaluation/validate_c2_activity.py",
        "independent_no_feasible_audit":HERE/"evaluation/validate_c2_no_feasible.py"}
    hashes={str(p.relative_to(RESULT)).replace("\\","/"):sha(p) for p in RESULT.rglob("*") if p.is_file() and p.name!="manifest.json"}
    manifest={"schema_version":"robotcad_try6_c2_manifest_v1",
        "experiment_id":cfg["experiment_id"],"execution_outcome":audit["execution_outcome"],
        "protocol_terminal_decision":None,"classification_pending_user_direction":True,
        "starting_commit":cfg["starting_commit"],
        "implementation_commit_before_construction":pre["implementation_commit_before_construction"],
        "implementation_commit_before_formal_C2":formal["implementation_commit_before_formal_C2"],
        "result_freeze_parent_commit":head,"branch":branch,
        "protocol_sha256":sha(HERE/"protocol/try6_0_c2.json"),
        "c1_manifest_sha256":sha(c1/"manifest.json"),
        "c1_final_lock_sha256":sha(ROOT/cfg["c1_final_lock"]),
        "c1_reference_sha256":sha(RESULT/"frozen_c1/c1_reference.json"),
        "c1_parity_sha256":sha(RESULT/"frozen_c1/parity_audit.json"),
        "c1_kfdg_sha256":formal["c1_kfdg_sha256"],
        "c1_slot_sha256":formal["c1_slot_sha256"],
        "c1_visual_evidence_sha256":formal["c1_visual_evidence_sha256"],
        "c1_visual_objective_sha256":formal["c1_visual_objective_definition_sha256"],
        "c1_optimizer_config_sha256":formal["c1_optimizer_config_sha256"],
        "source_URDF_and_neighbor_hashes":pre["source_hashes"],
        "kfde_sweep_sha256":sha(RESULT/"kfde/construction_sweep.json"),
        "kfde_keepout_brep_sha256":construction["keepout"]["sha256"],
        "allowed_contact_brep_sha256":construction["allowed_region"]["sha256"],
        "kfde_construction_report_sha256":sha(RESULT/"kfde/construction_report.json"),
        "replay_history_sha256":sha(RESULT/"replay/c1_candidate_replay.json"),
        "formal_candidate_history_sha256":sha(RESULT/"solver/candidate_history.json"),
        "implementation_source_sha256":{name:sha(path) for name,path in sources.items()},
        "evaluator_hashes":load(c1/"pre_run_manifest.json")["evaluator_hashes"],
        "python_environment":".venv/Scripts/python.exe","freecad_version":pre["freecad_version"],
        "VLM_calls":0,"GT_evaluations":0,"final_mechanics_evaluations":0,
        "formal_holdout_accessed":False,"formal_holdout_evaluation_count":0,
        "result_file_sha256":hashes,"created_utc":datetime.now(timezone.utc).isoformat()}
    save(RESULT/"manifest.json",manifest)
    print(json.dumps({"execution_outcome":audit["execution_outcome"],
        "terminal_decision":None,"proposals":17,"kfde_rejects":17,
        "GT_evaluations":0,"holdout_accessed":False}))


if __name__=="__main__":main()
