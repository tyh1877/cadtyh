"""Freeze C1 parity, URDF neighbor sources, KFDE protocol and holdout guard."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime,timezone

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try6.scripts.run_r1_reliability import save

RESULT=HERE/"results/try6_0_c2"


def main():
    cfg=load(HERE/"protocol/try6_0_c2.json")
    if (RESULT/"pre_run_manifest.json").exists():raise FileExistsError("C2 already prepared")
    c1=ROOT/cfg["c1_result_root"]
    c1_manifest=load(c1/"manifest.json")
    if c1_manifest["decision"]!="GO_C2":raise RuntimeError("frozen C1 not GO_C2")
    if not all(sha(c1/name)==digest for name,digest in c1_manifest["result_file_sha256"].items()):
        raise RuntimeError("frozen C1 result drift")
    c1_lock=load(ROOT/cfg["c1_final_lock"])
    for item in c1_lock["final_cad_artifacts"].values():
        if sha(ROOT/item["path"])!=item["sha256"]:raise RuntimeError("frozen C1 final CAD drift")
    slot=load(c1/"slot/validated_slots.json")
    statuses={x["slot_id"]:x["status"] for x in slot["slots"]}
    if statuses!={"main_housing":"PRESENT","visible_pocket":"ABSENT","profile_transition":"PRESENT"}:
        raise RuntimeError("frozen C1 slot state changed")
    c1_cfg=load(ROOT/cfg["c1_protocol"])
    c1_pre=load(c1/"pre_run_manifest.json")
    if c1_pre["protocol_sha256"]!=sha(ROOT/cfg["c1_protocol"]):raise RuntimeError("C1 protocol drift")
    c1_active=load(c1/"kfdg/active_parameters.json")
    c1_objective=load(c1/"solver/objective_definition.json")
    c1_solver=load(c1/"solver/config.json")
    if c1_solver!=c1_cfg["solver"] or c1_objective["weights"]!=c1_cfg["visual_objective"]["weights"] or c1_objective["selected_views"]!=c1_cfg["view_registration"]["views"]:
        raise RuntimeError("frozen C1 solver/objective snapshot parity failed")
    if cfg["c2_max_proposals_if_active"]!=c1_solver["max_candidate_evaluations"]:
        raise RuntimeError("C2 proposal budget differs from C1")
    if cfg["numerical_forbidden_volume_tolerance_mm3"]!=1e-6 or cfg["engineering_clearance_margin_mm"]!=0.0:
        raise RuntimeError("frozen tolerance policy drift")
    if sha(HERE/"scripts/freecad_c1_builder.py")!=c1_pre["method_hashes"]["freecad_builder_source"]:
        raise RuntimeError("CAD compiler differs from frozen C1")
    if sha(HERE/"scripts/c1_v2_visual_objective.py")!=c1_pre["method_hashes"]["visual_objective_source"]:
        raise RuntimeError("visual objective differs from frozen C1")
    if sha(ROOT/c1_cfg["evaluation"]["geometry_evaluator"])!=c1_pre["evaluator_hashes"]["geometry_evaluator"] or sha(ROOT/c1_cfg["evaluation"]["mechanical_evaluator"])!=c1_pre["evaluator_hashes"]["mechanical_evaluator"]:
        raise RuntimeError("evaluator version drift")
    lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"]!=0:raise RuntimeError("formal holdout lock violated")
    neighbor_hashes={item["link_id"]:sha(ROOT/cfg["frozen_neighbor_root"]/item["link_id"]/"model.FCStd") for item in cfg["neighbor_scope"]}
    source_hashes={"sanitized_urdf":sha(ROOT/cfg["sanitized_urdf"]),
        "interface_contracts":sha(ROOT/cfg["frozen_interface_contracts"]),
        "l04_scaffold":sha(ROOT/cfg["frozen_l04_scaffold"]),
        "neighbors":neighbor_hashes}
    c1_reference={"schema_version":"robotcad_try6_c2_frozen_c1_reference_v1",
        "c1_result_root":cfg["c1_result_root"],"c1_result_manifest_sha256":sha(c1/"manifest.json"),
        "c1_final_lock_sha256":sha(ROOT/cfg["c1_final_lock"]),
        "selected_candidate_id":c1_lock["selected_candidate_id"],
        "slot_statuses":statuses,
        "geometry_metrics":load(c1/"evaluation/geometry_metrics.json")["final"],
        "mechanical_metrics":load(c1/"evaluation/mechanical_metrics.json"),
        "reference_only_not_KFDE_input":True}
    save(RESULT/"frozen_c1/c1_reference.json",c1_reference)
    parity={"schema_version":"robotcad_try6_c2_parity_v1","status":"PASS",
        "no_new_vlm_call":True,"slot_state_reused":True,"kfdg_sha256":sha(c1/"kfdg/canonical_kfdg.json"),
        "slot_state_sha256":sha(c1/"slot/validated_slots.json"),
        "active_parameters_sha256":sha(c1/"kfdg/active_parameters.json"),
        "active_ids":c1_active["active_ids"],"parameter_bounds":c1_active["active_bounds"],
        "parameter_initial_values":c1_active["initial_theta"],
        "raw_image_hashes":c1_pre["input_hashes"]["images"],
        "engineering_text_sha256":c1_pre["input_hashes"]["engineering_text"]["sha256"],
        "sanitized_urdf_sha256":c1_pre["input_hashes"]["sanitized_urdf"]["sha256"],
        "view_registration_sha256":sha(c1/"visual_metric_evidence/view_registration_report.json"),
        "visual_evidence_sha256":sha(c1/"visual_metric_evidence/visual_metric_evidence.json"),
        "visual_objective_definition_sha256":sha(c1/"solver/objective_definition.json"),
        "visual_objective_weights":c1_objective["weights"],
        "optimizer_config_sha256":sha(c1/"solver/config.json"),
        "optimizer_config":c1_solver,
        "cad_compiler_sha256":sha(HERE/"scripts/freecad_c1_builder.py"),
        "geometry_evaluator_sha256":c1_pre["evaluator_hashes"]["geometry_evaluator"],
        "mechanical_evaluator_sha256":c1_pre["evaluator_hashes"]["mechanical_evaluator"],
        "only_method_increment":"hard KFDE feasibility before visual ranking"}
    save(RESULT/"frozen_c1/parity_audit.json",parity)
    save(RESULT/"protocol.json",cfg)
    save(RESULT/"case_split.json",{"development_subjects":["L04"],
        "final_development_configurations":96,"kfde_construction_sweep_source":"URDF only, separate from final development cases",
        "formal_holdout_case_count":32,"formal_holdout_ids_not_read":True,
        "formal_holdout_lock_sha256":sha(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json"),
        "accessed":False,"evaluation_count":0})
    save(RESULT/"holdout_evaluation_log.json",{"events":[],"accessed":False,"evaluation_count":0,"followed_by_tuning":False})
    head=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    sys.path.insert(0,str(ROOT/"experiments/try5A/scripts"))
    from freecad_runtime import python_runtime
    freecad=subprocess.run([python_runtime(),"-c","import FreeCAD,json;print(json.dumps(FreeCAD.Version()))"],
        cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    pre={"schema_version":"robotcad_try6_c2_pre_run_v1","status":"READY_FOR_KFDE_CONSTRUCTION",
        "timestamp_utc":datetime.now(timezone.utc).isoformat(),"starting_commit":cfg["starting_commit"],
        "implementation_commit_before_construction":head,"protocol_sha256":sha(HERE/"protocol/try6_0_c2.json"),
        "c1_manifest_sha256":sha(c1/"manifest.json"),"c1_final_lock_sha256":sha(ROOT/cfg["c1_final_lock"]),
        "c1_parity_sha256":sha(RESULT/"frozen_c1/parity_audit.json"),
        "source_hashes":source_hashes,
        "kfde_constructor_sha256":sha(HERE/"scripts/freecad_c2_kfde.py"),
        "model_calls_planned":0,"gt_access_before_final_c2_lock":False,
        "c1_failure_diagnostics_not_in_kfde_inputs":True,
        "holdout_lock":{"accessed":False,"evaluation_count":0},
        "python_environment":".venv/Scripts/python.exe","freecad_version":freecad}
    save(RESULT/"pre_run_manifest.json",pre)
    print(json.dumps({"status":pre["status"],"neighbors":list(neighbor_hashes),"c1_candidates":32,
        "c2_vlm_calls":0,"gt_access":False,"holdout_accessed":False}))


if __name__=="__main__":main()
