"""Freeze C1 domain/C2 KFDE and D0 diagnostic policy before first D0 build."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime,timezone

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try6.scripts.run_r1_reliability import save

sys.path.insert(0,str(ROOT/"experiments/try5A/scripts"))
from freecad_runtime import python_runtime

RESULT=HERE/"results/try6_0_d0"
ARTIFACT=HERE/"artifacts/try6_0_d0"


def prior(root):
    manifest=load(root/"manifest.json")
    hashes=manifest["result_file_sha256"]
    if not all(sha(root/path)==digest for path,digest in hashes.items()):
        raise RuntimeError(f"frozen result changed: {root}")
    return {"manifest_sha256":sha(root/"manifest.json"),"file_count":len(hashes),"unchanged":True}


def main():
    cfg=load(HERE/"protocol/try6_0_d0.json")
    if (RESULT/"pre_run_manifest.json").exists():raise FileExistsError("D0 already prepared")
    c1=ROOT/cfg["c1_result_root"]
    c2=ROOT/cfg["c2_result_root"]
    previous={"c1_v2":prior(c1),"c2":prior(c2)}
    if load(c2/"validation.json")["execution_outcome"]!="NO_FEASIBLE_CANDIDATE_AFTER_FROZEN_C1_PROPOSAL_SCHEDULE":
        raise RuntimeError("frozen C2 historical outcome drift")
    active=load(ROOT/cfg["active_parameter_source"])
    graph=load(ROOT/cfg["kfdg_source"])
    construction=load(ROOT/cfg["kfde_construction_source"])
    if len(active["active_ids"])!=6 or construction["status"]!="PASS" or len(construction["components"])!=13:
        raise RuntimeError("frozen domain/KFDE unavailable")
    c2_protocol=load(ROOT/cfg["c2_protocol_source"])
    if cfg["strict_feasibility_epsilon_mm3"]!=c2_protocol["numerical_forbidden_volume_tolerance_mm3"]:
        raise RuntimeError("strict D0 epsilon differs from C2")
    if sha(ROOT/cfg["cad_compiler"])!=load(c1/"pre_run_manifest.json")["method_hashes"]["freecad_builder_source"]:
        raise RuntimeError("CAD compiler source differs from frozen C1")
    if sha(ROOT/construction["keepout"]["path"])!=construction["keepout"]["sha256"] or sha(ROOT/construction["allowed_region"]["path"])!=construction["allowed_region"]["sha256"]:
        raise RuntimeError("frozen KFDE BREP artifact changed")
    lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"]!=0:raise RuntimeError("holdout lock violated")
    ARTIFACT.mkdir(parents=True,exist_ok=True)
    f0_job={"f0_fcstd":c2_protocol["frozen_l04_scaffold"],
        "output":"experiments/try6/results/try6_0_d0/authority_audit/f0_consistency_audit.json"}
    save(ARTIFACT/"f0_mapping_job.json",f0_job)
    f0=subprocess.run([python_runtime(),str(HERE/"evaluation/freecad_d0_f0_mapping.py"),str(ARTIFACT/"f0_mapping_job.json")],
        cwd=ROOT,capture_output=True,text=True,timeout=90)
    if f0.returncode:raise RuntimeError(f"F0 exact-mapping audit failed: {f0.stderr[-1000:]}")
    f0_audit=load(RESULT/"authority_audit/f0_consistency_audit.json")
    if f0_audit["exact_F0_equivalent_current_theta_mapping_available"]:
        raise RuntimeError("D0 protocol P5 exclusion conflicts with exact F0 mapping audit")
    save(RESULT/"protocol.json",cfg)
    save(RESULT/"frozen_inputs/c1_domain.json",{"active_ids":active["active_ids"],
        "active_bounds":active["active_bounds"],"initial_theta":active["initial_theta"],
        "c1_winner_theta":load(c1/"solver/theta_selected.json")["theta_star"],
        "inactive_ids":active["frozen_ids"],"slot_statuses":active["slot_statuses"],
        "parameter_source_sha256":sha(ROOT/cfg["active_parameter_source"]),
        "kfdg_sha256":sha(ROOT/cfg["kfdg_source"])})
    save(RESULT/"frozen_inputs/kfde_reference.json",{"construction_report_sha256":sha(ROOT/cfg["kfde_construction_source"]),
        "keepout_sha256":construction["keepout"]["sha256"],
        "allowed_contact_sha256":construction["allowed_region"]["sha256"],
        "component_count":len(construction["components"]),
        "numerical_tolerance_mm3":construction["numerical_tolerance_mm3"],
        "c2_protocol_sha256":sha(ROOT/cfg["c2_protocol_source"]),
        "neighbor_source_hashes":{item["link_id"]:item["source_sha256"] for item in construction["components"]}})
    save(RESULT/"frozen_inputs/parity_audit.json",{"status":"PASS","c1_v2":previous["c1_v2"],"c2":previous["c2"],
        "no_VLM":True,"no_GT":True,"no_final_mechanics":True,
        "same_six_bounds":True,"same_KFDG":True,"same_CAD_compiler":True,
        "same_KFDE_artifact_and_epsilon":True,"no_visual_objective_ranking":True,
        "historical_C2_classification_note":cfg["historical_c2_label"]})
    save(RESULT/"frozen_inputs/historical_c2_governance_note.json",{"historical_C2_execution_label":cfg["historical_c2_label"],
        "source_C2_validation_path":cfg["c2_result_root"]+"/validation.json",
        "source_C2_manifest_sha256":sha(c2/"manifest.json"),
        "old_C2_artifacts_modified":False,
        "does_not_expand_KFDE_OVERCONSTRAINED_definition":True})
    save(RESULT/"constraint_decomposition/component_registry.json",{"components":[{
        "component_id":x["component_id"],"neighbor_id":x["link_id"],"joint_id":x["joint_id"],
        "pose_q_rad":x["q_rad"],"brep_path":x["brep_path"],"brep_sha256":x["brep_sha256"]}
        for x in construction["components"]],"component_count":len(construction["components"]),
        "source_construction_sha256":sha(ROOT/cfg["kfde_construction_source"])})
    save(RESULT/"counterfactual/subset_definitions.json",{"subsets":cfg["counterfactual_subsets"],
        "rule":"FULL includes all 13 frozen pose components; MINUS_<LID> removes only components with that neighbor_id; per-component volumes are never recomputed/tuned",
        "diagnostic_only":True,"never_changes_frozen_KFDE":True})
    save(RESULT/"feasible_search/search_config.json",{"stage_a":cfg["stage_a"],"stage_b":cfg["stage_b"],
        "runtime_ceiling_seconds":cfg["maximum_total_runtime_seconds"],
        "strict_epsilon_mm3":cfg["strict_feasibility_epsilon_mm3"],
        "near_thresholds_mm3":cfg["near_feasible_thresholds_mm3"],
        "active_bounds":active["active_bounds"],"active_ids":active["active_ids"],
        "ranking_terms":cfg["ranking_terms"],"visual_objective_used":False})
    save(RESULT/"case_split.json",{"diagnostic_subjects":["L04"],
        "canonical_probes":5,"stage_a_samples":256,"stage_b_proposals":60,
        "formal_holdout_case_count":32,"formal_holdout_ids_not_read":True,
        "holdout_lock_sha256":sha(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json"),
        "holdout_accessed":False,"holdout_evaluation_count":0})
    save(RESULT/"holdout_evaluation_log.json",{"events":[],"accessed":False,"evaluation_count":0,"followed_by_tuning":False})
    head=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    freecad=subprocess.run([python_runtime(),"-c","import FreeCAD,json;print(json.dumps(FreeCAD.Version()))"],
        cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    pre={"schema_version":"robotcad_try6_d0_pre_run_v1","status":"READY_FOR_FROZEN_DIAGNOSTIC",
        "timestamp_utc":datetime.now(timezone.utc).isoformat(),"starting_commit":cfg["starting_commit"],
        "implementation_commit_before_D0":head,"protocol_sha256":sha(HERE/"protocol/try6_0_d0.json"),
        "c1_manifest_sha256":sha(c1/"manifest.json"),"c2_manifest_sha256":sha(c2/"manifest.json"),
        "active_bounds_sha256":sha(ROOT/cfg["active_parameter_source"]),
        "kfdg_sha256":sha(ROOT/cfg["kfdg_source"]),
        "kfde_construction_sha256":sha(ROOT/cfg["kfde_construction_source"]),
        "kfde_keepout_sha256":construction["keepout"]["sha256"],
        "allowed_contact_sha256":construction["allowed_region"]["sha256"],
        "numerical_tolerance_mm3":cfg["strict_feasibility_epsilon_mm3"],
        "diagnostic_worker_sha256":sha(HERE/"scripts/freecad_d0_component_probe.py"),
        "CAD_compiler_sha256":sha(ROOT/cfg["cad_compiler"]),
        "FreeCAD_version":freecad,"python_environment":".venv/Scripts/python.exe",
        "f0_exact_mapping_available":False,"VLM_calls":0,"GT_evaluations":0,
        "final_mechanics_evaluations":0,"formal_holdout_accessed":False}
    save(RESULT/"pre_run_manifest.json",pre)
    print(json.dumps({"status":pre["status"],"stage_a":256,"stage_b":60,
        "canonical_probes":5,"exact_F0_mapping":False,"GT_evaluations":0}))


if __name__=="__main__":main()
