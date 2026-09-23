"""Freeze claim ledger and provenance after independent one-shot validation."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime,timezone

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try6.scripts.run_r1_reliability import save

RESULT=HERE/"results/try6_0_c1_v2"


def main():
    validation=load(RESULT/"audit/independent_validation.json")
    if validation["decision"] not in {"GO_C2","METRIC_GROUNDING_WEAK","METRIC_OBJECTIVE_MISALIGNED"}:
        raise RuntimeError("final development evaluation not independently closed")
    if (RESULT/"manifest.json").exists():raise FileExistsError("C1-v2 result already frozen")
    cfg=load(HERE/"protocol/try6_0_c1_v2.json")
    pre=load(RESULT/"pre_run_manifest.json")
    lock=load(RESULT/"evaluation/final_candidate_lock.json")
    metrics=load(RESULT/"evaluation/c0_vs_c1.json")
    mechanics=load(RESULT/"evaluation/mechanical_metrics.json")
    process=load(RESULT/"process_metrics.json")
    holdout=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if holdout["accessed"] is not False or holdout["evaluation_count"]!=0:
        raise RuntimeError("formal holdout lock violated")
    save(RESULT/"experiment_config_snapshot.json",cfg)
    save(RESULT/"validation.json",validation)
    ledger={"schema_version":"robotcad_try6_c1_v2_claim_ledger_v1","claims":[
        {"claim":"fresh single slot call valid","evidence_type":"computed","artifact":"slot/independent_validation.json","field":"status","expected":"PASS"},
        {"claim":"raw-image registration and evidence gate valid","evidence_type":"computed","artifact":"visual_metric_evidence/evidence_audit.json","field":"registration_gate_pass / evidence_gate_pass","expected":"true / true"},
        {"claim":"theta selected by visual objective only","evidence_type":"computed","artifact":"solver/independent_validation.json","field":"selection_by_visual_only","expected":True},
        {"claim":"final CAD locked before GT","evidence_type":"computed","artifact":"evaluation/evaluation_started.json","field":"final_candidate_lock_sha256","expected":sha(RESULT/"evaluation/final_candidate_lock.json")},
        {"claim":"final BICR and one-solid gate","evidence_type":"computed","artifact":"evaluation/mechanical_metrics.json","field":"bicr / connected_solid_count","expected":"1.0 / 1"},
        {"claim":"primary IoU >= frozen threshold","evidence_type":"computed","artifact":"evaluation/c0_vs_c1.json","field":"gates.primary_iou","expected":True},
        {"claim":"supporting geometry gates all pass","evidence_type":"computed","artifact":"evaluation/c0_vs_c1.json","field":"all_geometry_gates_pass","expected":True},
        {"claim":"exact development mechanics diagnostic only","evidence_type":"computed","artifact":"evaluation/mechanical_metrics.json","field":"mechanical_feedback_to_solver / configuration_count","expected":"false / 96"},
        {"claim":"formal holdout lock closed","evidence_type":"computed","artifact":"audit/holdout_audit.json","field":"lock_accessed / lock_evaluation_count","expected":"false / 0"},
        {"claim":"no GT path supplied to generator/solver","evidence_type":"inferred","artifact":"audit/leakage_audit.json","field":"source_paths_generator_only","expected":True,"limitation":"No OS-level filesystem-read trace; not independently sufficient for a stronger no-read claim"}
    ]}
    save(RESULT/"claim_ledger.json",ledger)
    head=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    branch=subprocess.run(["git","branch","--show-current"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    method_sources={"slot_runner":HERE/"scripts/run_c1_v2_slot.py",
        "objective":HERE/"scripts/c1_v2_visual_objective.py",
        "solver":HERE/"scripts/c1_v2_metric_solver.py",
        "freecad_builder":HERE/"scripts/freecad_c1_builder.py",
        "geometry_evaluator":ROOT/cfg["evaluation"]["geometry_evaluator"],
        "mechanical_evaluator":ROOT/cfg["evaluation"]["mechanical_evaluator"],
        "independent_validator":HERE/"evaluation/validate_c1_v2.py"}
    artifact_hashes={str(p.relative_to(RESULT)).replace("\\","/"):sha(p)
        for p in RESULT.rglob("*") if p.is_file() and p.name!="manifest.json"}
    manifest={"schema_version":"robotcad_try6_c1_v2_manifest_v1",
        "experiment_id":cfg["experiment_id"],"decision":validation["decision"],
        "starting_commit":cfg["starting_commit"],
        "implementation_commit_before_formal_call":pre["implementation_commit_before_call"],
        "result_freeze_parent_commit":head,"branch":branch,
        "protocol_path":"experiments/try6/protocol/try6_0_c1_v2.json",
        "protocol_sha256":sha(HERE/"protocol/try6_0_c1_v2.json"),
        "method_source_sha256":{name:sha(path) for name,path in method_sources.items()},
        "slot_schema_sha256":pre["method_hashes"]["slot_canonical_schema"],
        "slot_registry_sha256":pre["method_hashes"]["slot_registry"],
        "parameter_registry_sha256":pre["method_hashes"]["parameter_registry"],
        "functional_backbone_sha256":pre["method_hashes"]["functional_backbone"],
        "kfdg_sha256":lock["kfdg_sha256"],
        "raw_image_hashes":{view:item["sha256"] for view,item in pre["input_hashes"]["images"].items()},
        "sanitized_urdf_sha256":pre["input_hashes"]["sanitized_urdf"]["sha256"],
        "view_registration_sha256":lock["view_registration_sha256"],
        "visual_evidence_sha256":lock["visual_evidence_sha256"],
        "visual_objective_sha256":lock["objective_definition_sha256"],
        "solver_config_sha256":lock["solver_config_sha256"],
        "evaluator_source_sha256":pre["evaluator_hashes"],
        "frozen_c0_source_sha256":pre["c0_frozen_source_sha256"],
        "model_requested":cfg["model"]["identifier"],"model_returned":load(RESULT/"slot/validation.json")["model_returned"],
        "sdk_version":pre["sdk_version"],"api_base_url":pre["api_base_url"],
        "api_key_recorded":False,"python_environment":".venv/Scripts/python.exe",
        "freecad_version":pre["freecad_version"],
        "final_candidate_lock_sha256":sha(RESULT/"evaluation/final_candidate_lock.json"),
        "final_cad_artifacts":lock["final_cad_artifacts"],
        "geometry_raw_sha256":sha(RESULT/"evaluation/geometry_raw.json"),
        "mechanical_raw_sha256":sha(RESULT/"evaluation/mechanical_raw.json"),
        "gt_final_evaluation_count":1,"formal_holdout_accessed":False,
        "formal_holdout_evaluation_count":0,
        "process_runtime_accounting":"measured components only; full wall time unavailable",
        "prior_result_hash_recheck":validation["prior_result_hash_recheck"],
        "result_file_sha256":artifact_hashes,
        "created_utc":datetime.now(timezone.utc).isoformat()}
    save(RESULT/"manifest.json",manifest)
    print(json.dumps({"decision":validation["decision"],"iou_c0":metrics["c0"]["final_voxel_iou"],
        "iou_c1":metrics["c1"]["final_voxel_iou"],
        "mechanical_gcfr":mechanics["gcfr"],"solver_evaluations":process["solver_evaluations"],
        "holdout_accessed":False}))


if __name__=="__main__":main()
