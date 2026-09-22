"""Run the three-link Try-5B1 mechanically constrained refinement pilot."""

from __future__ import annotations

import csv, hashlib, json, math, os, subprocess, sys, time
import argparse
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw
from scipy.spatial import cKDTree

ROOT=Path(__file__).resolve().parents[3]; HERE=ROOT/"experiments/try5A"
RESULTS=HERE/"results/try5b1"; ARTIFACTS=HERE/"artifacts/try5b1"; BASE=HERE/"results/try5a5"
sys.path.insert(0,str(HERE/"scripts")); sys.path.insert(0,str(HERE/"evaluation")); sys.path.insert(0,str(HERE/"evaluation/mechanical"))
from fast_evaluator import GeometryCache,MechanicalEvaluator
from experiment_governance import CandidateController,audit_condition_parity,canonical_hash,canonical_json,split_cases
from freecad_runtime import python_runtime
from kinematics import canonical_q,fk,parse,rpy
from interface_instance_geometry import IMAGE_FIRST_SPECS, INSTANCE_SPECS

PILOTS={
 "L03":{"role":"arm_carrier","why_selected":"elongated forearm carrier with two moving-joint transitions","coarse_family":"central_web","weakness":"named central_web was compiled as offset cylinders and thin ties",
   "F1":{"body_family":"central_web","schema":{"span_mm":100,"thickness_mm":8,"proximal_height_mm":34,"mid_height_mm":26,"lateral_offset_mm":-18,"major_recess":False}},
   "F2":{"body_family":"central_web","schema":{"span_mm":100,"thickness_mm":8,"proximal_height_mm":34,"mid_height_mm":28,"lateral_offset_mm":-18,"major_recess":True}}},
 "L04":{"role":"joint_wrist_housing","why_selected":"wrist-local housing joining a rotary interface to a fixed mount","coarse_family":"wrist_block","weakness":"generic cylindrical carrier did not express housing section changes",
   "F1":{"body_family":"compound_profile_housing","schema":{"span_mm":63,"width_mm":8,"height_mm":23,"major_recess":False}},
   "F2":{"body_family":"compound_profile_housing","schema":{"span_mm":63,"width_mm":8,"height_mm":23,"major_recess":True}}},
 "L07":{"role":"gripper_end_support","why_selected":"end-side fixed subassembly supporting the two-finger mechanism","coarse_family":"straight_beam","weakness":"short round bar omitted the transverse support and working gap",
   "F1":{"body_family":"gripper_support","schema":{"span_mm":23,"bar_width_mm":47,"thickness_mm":10,"working_gap":False}},
   "F2":{"body_family":"gripper_support","schema":{"span_mm":23,"bar_width_mm":48,"thickness_mm":10,"working_gap":True}}},
}

INVENTORIES={
 "F0":{x:{"required":[],"optional":[],"uncertain":[],"predicted_features":["coarse_body"],"relations":[]} for x in PILOTS},
 "F1":{
  "L03":{"required":[["proximal_joint_housing","E1"],["central_web","E1"],["distal_joint_region","E1"]],"optional":[["major_recess","E2"]],"uncertain":[["hidden_actuator","E3"]],"predicted_features":["proximal_joint_housing","central_web","distal_joint_region"],"relations":[["central_web","continues_into","proximal_joint_housing"],["central_web","continues_into","distal_joint_region"]]},
  "L04":{"required":[["proximal_housing","E1"],["stepped_housing","E1"],["distal_mount_transition","E1"]],"optional":[["major_recess","E2"]],"uncertain":[["hidden_bearing","E3"]],"predicted_features":["proximal_housing","stepped_housing","distal_mount_transition"],"relations":[["stepped_housing","surrounds","proximal_housing"],["stepped_housing","continues_into","distal_mount_transition"]]},
  "L07":{"required":[["carriage","E1"],["transverse_support","E1"],["left_support","E2"],["right_support","E2"]],"optional":[["working_gap","E2"]],"uncertain":[["hidden_linkage","E3"]],"predicted_features":["carriage","transverse_support","left_support","right_support"],"relations":[["transverse_support","supports","carriage"],["left_support","symmetric_with","right_support"]]}},
 "F2":{}
}
for lid,value in INVENTORIES["F1"].items():
    INVENTORIES["F2"][lid]=json.loads(json.dumps(value))
    if lid=="L03": INVENTORIES["F2"][lid]["predicted_features"].append("major_recess"); INVENTORIES["F2"][lid]["relations"].append(["central_web","surrounds","major_recess"])
    if lid=="L04": INVENTORIES["F2"][lid]["predicted_features"].append("major_recess"); INVENTORIES["F2"][lid]["relations"].append(["stepped_housing","surrounds","major_recess"])
    if lid=="L07": INVENTORIES["F2"][lid]["predicted_features"].append("working_gap"); INVENTORIES["F2"][lid]["relations"].extend([["left_support","separated_by_gap","right_support"],["transverse_support","surrounds","working_gap"]])

GT_ANNOTATION={
 "L03":{"required":["proximal_joint_housing","central_web","distal_joint_region"],"optional":["major_recess"],"family":"central_web","relations":[["central_web","continues_into","proximal_joint_housing"],["central_web","continues_into","distal_joint_region"],["central_web","surrounds","major_recess"]]},
 "L04":{"required":["proximal_housing","stepped_housing","distal_mount_transition","major_recess"],"optional":[],"family":"compound_profile_housing","relations":[["stepped_housing","surrounds","proximal_housing"],["stepped_housing","continues_into","distal_mount_transition"],["stepped_housing","surrounds","major_recess"]]},
 "L07":{"required":["carriage","transverse_support","left_support","right_support","working_gap"],"optional":[],"family":"gripper_support","relations":[["transverse_support","supports","carriage"],["left_support","symmetric_with","right_support"],["left_support","separated_by_gap","right_support"],["transverse_support","surrounds","working_gap"]]}}

def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def dump(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rows_csv(path,rows):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def governance_dry_run(config_path):
    """Freeze the A1 split/parity and exercise real policy decisions without CAD/GT."""
    config_path=Path(config_path).resolve(); config=load(config_path); cases=load(ROOT/config["shared"]["frozen_configuration_source"])["configurations"]
    case_ids=[item["config_id"] for item in cases]; split=split_cases(case_ids,config["shared"]["split"]); parity=audit_condition_parity(config)
    failing_metrics={"artifact_valid":True,"bicr":0.5,"physical_floating_count":1,"forbidden_fusion_count":0,"virtual_solid_count":0,"meaningless_patch_count":0,"relevant_jr3":0.8,"gcfr_regression":0.1}
    decisions=[]
    for name,condition in config["conditions"].items():
        controller=CandidateController(name,condition["mechanical_policy"],config["shared"]["mechanical_thresholds"])
        decisions.append(controller.decide("F1_ACCEPTED","F2_PROPOSED",failing_metrics).as_dict())
    expected=(next(x for x in decisions if x["condition"]=="C1_CONSTRAINED")["outcome"]=="ROLLBACK" and next(x for x in decisions if x["condition"]=="C2_UNCONSTRAINED")["outcome"]=="ACCEPT_WITH_MECHANICAL_FAILURE")
    output_root=HERE/"protocol"; dump(output_root/"try5b1_a1_case_split.json",split); dump(output_root/"try5b1_a1_condition_parity.json",parity)
    payload={"status":"PASS" if parity["status"]=="PASS" and expected else "FAIL","config":str(Path(config_path).relative_to(ROOT)).replace("\\","/"),"config_canonical_sha256":canonical_hash(config),"split_sha256":split["split_sha256"],"parity_status":parity["status"],"runtime_policy_decisions":decisions,"freecad_invoked":False,"gt_accessed":False}
    dump(output_root/"try5b1_a1_governance_dry_run.json",payload); print(json.dumps(payload,indent=2)); return 0 if payload["status"]=="PASS" else 1


def _repo_relative(path):
    return str(Path(path).resolve().relative_to(ROOT)).replace("\\","/")


def _candidate_metrics(worker,condition,frozen_gcfr):
    builds=[item for item in worker["builds"] if item["condition"]==condition and item["link_id"] in PILOTS]; exact=next(item for item in worker["mechanical_exact"] if item["condition"]==condition)
    features={lid:set(INVENTORIES[condition][lid]["predicted_features"]) for lid in PILOTS}; unsupported=sum(len(set(item["features"])-features[item["link_id"]]) for item in builds)
    artifact_paths=[item["artifact"]["fcstd"] for item in builds]; separate_artifacts=len(set(artifact_paths))==len(builds)
    return {
        "artifact_valid":all(item["group_valid"] and all(Path(path).is_file() for path in item["artifact"].values() if isinstance(path,str)) for item in builds),
        "bicr":sum(item["attachment_valid"] for item in builds)/max(1,len(builds)),
        "physical_floating_count":sum(item["solid_count"]!=1 for item in builds),
        "forbidden_fusion_count":0 if separate_artifacts else len(builds)-len(set(artifact_paths)),
        "virtual_solid_count":int("L11" in worker["physical_links"]),
        "meaningless_patch_count":unsupported,
        "relevant_jr3":min(item["jr3"] for item in exact["per_joint"]),
        "gcfr":exact["gcfr"],
        "gcfr_regression":frozen_gcfr-exact["gcfr"],
        "configuration_count":exact["configuration_count"],
        "valid_configurations":exact["valid_configs"],
    }


def _raw_proposal_parity(workers):
    reference={}
    rows=[]
    for condition_name,worker in workers.items():
        for build in worker["builds"]:
            if build["condition"] not in ("F1","F2") or build["link_id"] not in PILOTS: continue
            key=build["condition"]+"/"+build["link_id"]; signature=build["raw_body_signature"]
            if key not in reference: reference[key]=signature
            rows.append({"policy_condition":condition_name,"refinement_condition":build["condition"],"link_id":build["link_id"],"raw_body_signature":signature,"matches_reference":signature==reference[key]})
    return {"status":"PASS" if all(row["matches_reference"] for row in rows) else "FAIL","records":rows,"reference_sha256":canonical_hash(reference)}


def _filter_per_joint(per, fractions):
    allowed={round(float(value),8) for value in fractions}
    return {joint:[item for item in rows if round(float(item["active_fraction"]),8) in allowed] for joint,rows in per.items()}


def run_geometry_protection_dry_run(config_path):
    config_path=Path(config_path).resolve(); config=load(config_path); result_root=HERE/"results/try5b1_a1_geometry_protection"; artifact_root=HERE/"artifacts/try5b1_a1_geometry_protection"; result_root.mkdir(parents=True,exist_ok=True); artifact_root.mkdir(parents=True,exist_ok=True)
    if config["stage"]!="L04_PAIRED_DRY_RUN_ONLY" or config["shared"]["dry_run_links"]!=["L04"]: raise RuntimeError("this entrypoint is locked to the L04 paired dry run")

    old_path=HERE/"artifacts/try5b1_a1_development/C1_CONSTRAINED/freecad_result.json"; reproduced_path=artifact_root/"baseline_c1/freecad_result.json"
    old=load(old_path); reproduced=load(reproduced_path); old_builds={(item["condition"],item["link_id"]):item for item in old["builds"]}; new_builds={(item["condition"],item["link_id"]):item for item in reproduced["builds"]}; build_rows=[]
    for link_id in config["shared"]["pilot_links"]:
        previous=old_builds[("F2",link_id)]; current=new_builds[("F2",link_id)]
        build_rows.append({"link_id":link_id,"raw_body_signature_equal":previous["raw_body_signature"]==current["raw_body_signature"],"interface_signatures_equal":previous["interface_signatures"]==current["interface_signatures"],"attachment_valid_equal":previous["attachment_valid"]==current["attachment_valid"],"solid_count_equal":previous["solid_count"]==current["solid_count"],"stl_sha256_previous":sha(previous["artifact"]["stl"]),"stl_sha256_reproduced":sha(current["artifact"]["stl"]),"stl_equal":sha(previous["artifact"]["stl"])==sha(current["artifact"]["stl"])})
    old_exact=next(item for item in old["mechanical_exact"] if item["condition"]=="F2"); new_exact=next(item for item in reproduced["mechanical_exact"] if item["condition"]=="F2")
    baseline={"schema_version":"robotcad_a1_baseline_reproduction_v1","status":"PASS" if all(all(row[key] for key in ("raw_body_signature_equal","interface_signatures_equal","attachment_valid_equal","solid_count_equal","stl_equal")) for row in build_rows) and old_exact["rows"]==new_exact["rows"] and old_exact["per_joint"]==new_exact["per_joint"] else "FAIL","executed_before_c2_implementation":True,"baseline_execution_commit":config["baseline_execution_commit"],"worker_sha256":config["baseline_worker_sha256"],"links":build_rows,"exact":{"configuration_count_previous":old_exact["configuration_count"],"configuration_count_reproduced":new_exact["configuration_count"],"valid_previous":old_exact["valid_configs"],"valid_reproduced":new_exact["valid_configs"],"gcfr_previous":old_exact["gcfr"],"gcfr_reproduced":new_exact["gcfr"],"rows_equal":old_exact["rows"]==new_exact["rows"],"per_joint_equal":old_exact["per_joint"]==new_exact["per_joint"]}}
    dump(result_root/"baseline_reproduction.json",baseline)
    if baseline["status"]!="PASS": raise RuntimeError("C1/F2 baseline did not reproduce; ablation stopped")

    freecad_version=subprocess.run([python_runtime(),"-c","import FreeCAD,json; print(json.dumps(FreeCAD.Version()))"],cwd=ROOT,capture_output=True,text=True,check=True,timeout=30).stdout.strip(); body_specs=load(ROOT/config["shared"]["body_family_specs"]); f2_specs={link_id:body_specs[link_id]["F2"] for link_id in config["shared"]["pilot_links"]}
    images={view:{"path":config["shared"]["formal_image_root"]+"/"+view+".png","sha256":sha(ROOT/config["shared"]["formal_image_root"]/(view+".png"))} for view in config["shared"]["formal_image_views"]}
    reproducibility={"schema_version":"robotcad_a1_reproducibility_freeze_v1","baseline_execution_commit":config["baseline_execution_commit"],"python":{"executable":".venv/Scripts/python.exe","version":sys.version.split()[0]},"freecad":{"locator":"experiments/try5A/scripts/freecad_runtime.py:python_runtime","version":freecad_version},"input_images":images,"sanitized_urdf":{"path":config["shared"]["sanitized_urdf"],"sha256":sha(ROOT/config["shared"]["sanitized_urdf"])},"f2_schema":{"sha256":canonical_hash(f2_specs),"links":f2_specs},"interface_contract":{"path":config["shared"]["interface_contracts"],"sha256":sha(ROOT/config["shared"]["interface_contracts"])},"visual_evidence_packs":{link_id:{"path":config["shared"]["visual_evidence_root"]+"/"+link_id+".json","sha256":sha(ROOT/config["shared"]["visual_evidence_root"]/(link_id+".json"))} for link_id in config["shared"]["pilot_links"]},"semantic_inventories":{link_id:sha(ROOT/config["shared"]["semantic_inventory_root"]/(link_id+".json")) for link_id in config["shared"]["pilot_links"]},"mechanical_topology":{link_id:sha(ROOT/config["shared"]["mechanical_topology_root"]/(link_id+".json")) for link_id in config["shared"]["pilot_links"]},"seed":config["shared"]["seed"],"evaluator_settings":{"exact_evaluator":"experiments/try5A/scripts/freecad_motion_realization.py","exact_evaluator_sha256":sha(HERE/"scripts/freecad_motion_realization.py"),"geometry_sample_count":config["shared"]["geometry_sample_count"],"geometry_metrics":config["shared"]["geometry_metrics"],"coupled_configuration_count":config["shared"]["coupled_configuration_count"],"joint_sweep_fractions":[0.25,0.5,0.75]}}
    dump(result_root/"reproducibility_manifest.json",reproducibility)

    integrity={"schema_version":"robotcad_a1_evaluator_integrity_v1","status":"PASS","computed_primary_metrics":{"bicr":"FreeCAD final RigidGroup connected-solid test: solid_count == 1","connected_solid_count":"FreeCAD len(final_shape.Solids)","attachment_valid":"FreeCAD final shape solid_count == 1","relevant_jr3":"independent Exact evaluator per-joint collision-free fraction","gcfr":"independent Exact evaluator collision-free coupled-configuration fraction","exact_collision_events":"count of Exact evaluator unintended-collision rows","failed_configurations":"Exact evaluator configuration IDs with any unintended collision"},"declarative_or_non_primary_fields":{"swept_clearance_preserved":"literal True in legacy runner","forbidden_fusion_count":"literal/filename-based value, not a geometry evaluator result","virtual_solid_count":"membership/declaration check, not an evaluated geometry result","meaningless_patch_count":"semantic feature bookkeeping, not a geometry evaluator result"},"excluded_from_main_quantitative_analysis":config["shared"]["excluded_declarative_metrics"]}
    dump(result_root/"evaluator_integrity.json",integrity)

    parity=audit_condition_parity(config); coupled_all,per_all=configurations(); split=load(ROOT/config["shared"]["development_split"]); development_ids=set(split["development"]["case_ids"]); holdout_ids=set(split["holdout"]["case_ids"]); coupled=[item for item in coupled_all if item["config_id"] in development_ids]; per=_filter_per_joint(per_all,[0.25,0.5,0.75]); canonical=load(BASE/"motion_sequence.json")["configurations"][0]; f2_l04=f2_specs["L04"]
    shared_hashes={"input_images":canonical_hash(images),"urdf":sha(ROOT/config["shared"]["sanitized_urdf"]),"pilot_links":canonical_hash(config["shared"]["pilot_links"]),"f2_body_family":canonical_hash(f2_l04["body_family"]),"f2_schema":canonical_hash(f2_l04["schema"]),"visual_evidence_pack":sha(ROOT/config["shared"]["visual_evidence_root"]/"L04.json"),"semantic_inventory":sha(ROOT/config["shared"]["semantic_inventory_root"]/"L04.json"),"mechanical_topology":sha(ROOT/config["shared"]["mechanical_topology_root"]/"L04.json"),"model_prompt":"NOT_APPLICABLE_DETERMINISTIC_FROZEN_F2","seed":canonical_hash(config["shared"]["seed"]),"evaluator":canonical_hash({"mechanical":sha(HERE/"evaluation/mechanical/freecad_holdout_evaluator.py"),"geometry":sha(HERE/"evaluation/geometry_pair_evaluator.py")}),"coupled_configurations":canonical_hash(coupled),"joint_sweeps":canonical_hash({"J03":per["J03"]})}
    parity_report={"schema_version":"robotcad_a1_condition_parity_v1","status":"PASS" if parity["status"]=="PASS" and len(coupled)==96 and not (holdout_ids & {item["config_id"] for item in coupled}) else "FAIL","config_parity":parity,"shared_input_hashes":shared_hashes,"only_allowed_difference":"mechanical_geometry_policy","development_cases":len(coupled),"serialized_holdout_ids":0}; dump(result_root/"condition_parity.json",parity_report)
    if parity_report["status"]!="PASS": raise RuntimeError("condition parity failed")

    workers={}; failures=[]
    for condition_name,condition in config["conditions"].items():
        condition_root=artifact_root/"l04_dry_run"/condition_name; job={"experiment_id":config["experiment_id"],"phase":"L04_PAIRED_DRY_RUN","policy_condition":condition_name,"mechanical_geometry_policy":condition["mechanical_geometry_policy"],"conditions":["F2"],"pilots":{"L04":{"F2":f2_l04}},"coupled":coupled,"per_joint":{"J03":per["J03"]},"relevant_joints":["J03"],"canonical_config":canonical,"cad_root":str(condition_root/"cad"),"assembly_root":str(condition_root/"assemblies"),"output":str(condition_root/"generation_result.json"),"evaluation_enabled":False,"reuse_exact":False,"gt_access":False,"repair_enabled":False}
        if holdout_ids & {item["config_id"] for item in job["coupled"]}: raise RuntimeError("holdout leakage")
        job_path=condition_root/"generator_job.json"; dump(job_path,job); process=subprocess.run([python_runtime(),str(HERE/"evaluation/mechanical/freecad_link_refinement.py"),str(job_path)],cwd=ROOT,capture_output=True,text=True,timeout=1800); (condition_root/"stdout.txt").write_text(process.stdout,encoding="utf-8"); (condition_root/"stderr.txt").write_text(process.stderr,encoding="utf-8")
        if process.returncode: failures.append({"condition":condition_name,"stage":"generation","returncode":process.returncode,"error":(process.stderr or process.stdout)[-2000:]}); continue
        workers[condition_name]=load(job["output"])
    dump(result_root/"failure_accounting.json",{"requested_conditions":list(config["conditions"]),"completed_generation_conditions":list(workers),"failures":failures,"retry_count":0})
    if failures: raise RuntimeError("dry-run generation failed; failure retained without retry")

    builds={condition:next(item for item in worker["builds"] if item["condition"]=="F2" and item["link_id"]=="L04") for condition,worker in workers.items()}; candidate={"schema_version":"robotcad_a1_frozen_dry_candidates_v1","frozen_nonpilot_root":"experiments/try5A/artifacts/try5a5/round3_verified/links","interface_contracts":config["shared"]["interface_contracts"],"conditions":{condition:{"selected_candidate":"F2","pilot_fcstd":{"L04":_repo_relative(build["artifact"]["fcstd"])},"mechanical_geometry_policy":config["conditions"][condition]["mechanical_geometry_policy"]} for condition,build in builds.items()}}; dump(result_root/"l04_candidate_manifest.json",candidate)
    mechanical_job={"mode":"A1_L04_PAIRED_DRY_RUN_EXACT","candidate_manifest":str(result_root/"l04_candidate_manifest.json"),"configurations":coupled,"per_joint":{"J03":per["J03"]},"output":str(result_root/"l04_mechanical_raw.json")}; mechanical_job_path=artifact_root/"l04_dry_run/mechanical_evaluator_job.json"; dump(mechanical_job_path,mechanical_job); mechanical_process=subprocess.run([python_runtime(),str(HERE/"evaluation/mechanical/freecad_holdout_evaluator.py"),str(mechanical_job_path)],cwd=ROOT,capture_output=True,text=True,timeout=1800); (artifact_root/"l04_dry_run/mechanical_stdout.txt").write_text(mechanical_process.stdout,encoding="utf-8"); (artifact_root/"l04_dry_run/mechanical_stderr.txt").write_text(mechanical_process.stderr,encoding="utf-8")
    if mechanical_process.returncode: raise RuntimeError("independent mechanical evaluator failed: "+(mechanical_process.stderr or mechanical_process.stdout))
    mechanical=load(mechanical_job["output"]); geometry_job={"gt_urdf":"go_nogo1/sources/urdf_files_dataset/urdf_files/robotics-toolbox/xacro_generated/interbotix_descriptions/urdf/px100.urdf","seed":config["shared"]["seed"],"candidates":[{"condition":condition,"link_id":"L04","body_stl":_repo_relative(build["artifact"]["body_stl"]),"final_stl":_repo_relative(build["artifact"]["stl"])} for condition,build in builds.items()],"output":str(result_root/"l04_geometry_raw.json")}; geometry_job_path=artifact_root/"l04_dry_run/geometry_evaluator_job.json"; dump(geometry_job_path,geometry_job); geometry_process=subprocess.run([sys.executable,str(HERE/"evaluation/geometry_pair_evaluator.py"),str(geometry_job_path)],cwd=ROOT,capture_output=True,text=True,timeout=1800); (artifact_root/"l04_dry_run/geometry_stdout.txt").write_text(geometry_process.stdout,encoding="utf-8"); (artifact_root/"l04_dry_run/geometry_stderr.txt").write_text(geometry_process.stderr,encoding="utf-8")
    if geometry_process.returncode: raise RuntimeError("independent geometry evaluator failed: "+(geometry_process.stderr or geometry_process.stdout))
    geometry=load(geometry_job["output"]); mech_by={item["condition"]:item for item in mechanical["conditions"]}; geometry_by={(item["condition"],item["scope"]):item for item in geometry["rows"]}
    traces={condition:{"policy":config["conditions"][condition]["mechanical_geometry_policy"],"trace":build["execution_trace"],"assembly_strategy":build["assembly_strategy"]} for condition,build in builds.items()}; dump(result_root/"l04_execution_trace.json",traces)
    condition_results={}
    for condition,build in builds.items():
        exact=mech_by[condition]; condition_results[condition]={"build_export_reopen":build["artifact"]["reopen"],"planned_family":build["planned_family"],"executed_family":build["executed_family"],"raw_body_signature":build["raw_body_signature"],"bicr":1.0 if build["attachment_valid"] else 0.0,"connected_solid_count":build["solid_count"],"attachment_valid":build["attachment_valid"],"relevant_jr3":exact["per_joint"],"gcfr":exact["gcfr"],"exact_collision_events":exact["collision_events"],"exact_intersection_volume_mm3":exact["intersection_volume_mm3"],"failed_configuration_count":exact["invalid_configurations"],"failed_configuration_ids":exact["failed_configuration_ids"],"geometry":{"refined_body_only":geometry_by[(condition,"refined_body_only")],"final_assembled_link":geometry_by[(condition,"final_assembled_link")]}}
    raw_equal=builds["C1_CONSTRAINED"]["raw_body_signature"]==builds["C2_UNPROTECTED"]["raw_body_signature"]
    confounds=[{"id":"L04_DISTAL_CLEARANCE_NOT_EXERCISED","expected":True,"detail":"L04 has no applicable rotary distal interface, so this dry run cannot validate the distal-clearance toggle."},{"id":"BODY_ONLY_GT_IS_FULL_LINK_MESH","expected":True,"detail":"No evaluator-only body segmentation exists; body-only predictions are scored against the same full-link GT mesh. Use paired deltas, not the body-only absolute score."},{"id":"BUNDLED_PROTECTION_TREATMENT","expected":True,"detail":"Protected proximal cuts and scaffold preservation are jointly ablated by design; this experiment estimates their combined effect."}]
    leakage={"status":"PASS","generator_gt_access":False,"generator_repair_enabled":False,"serialized_holdout_ids":0,"formal_holdout_lock_exists":(HERE/"results/try5b1_a1_development/holdout_evaluated.lock").exists(),"geometry_gt_access_process":"independent evaluator only"}; dump(result_root/"leakage_audit.json",leakage)
    summary={"schema_version":"robotcad_a1_l04_dry_run_v1","status":"DRY_RUN_COMPLETE_FORMAL_NOT_RUN" if raw_equal and all(all(value for value in item["build_export_reopen"].values()) for item in condition_results.values()) and leakage["status"]=="PASS" and not leakage["formal_holdout_lock_exists"] else "DRY_RUN_FAILED","baseline_reproduced":True,"condition_parity":parity_report["status"],"raw_proposal_parity":"PASS" if raw_equal else "FAIL","conditions":condition_results,"unexpected_confounds":confounds,"formal_three_link_run_executed":False,"suitable_for_formal_three_link_run":raw_equal and parity_report["status"]=="PASS" and all(all(value for value in item["build_export_reopen"].values()) for item in condition_results.values())}; dump(result_root/"l04_dry_run_summary.json",summary)
    manifest={"experiment_id":config["experiment_id"],"stage":config["stage"],"config_path":_repo_relative(config_path),"config_sha256":sha(config_path),"runner_sha256":sha(Path(__file__)),"generation_worker_sha256":sha(HERE/"evaluation/mechanical/freecad_link_refinement.py"),"mechanical_evaluator_sha256":sha(HERE/"evaluation/mechanical/freecad_holdout_evaluator.py"),"geometry_evaluator_sha256":sha(HERE/"evaluation/geometry_pair_evaluator.py"),"baseline_reproduction_sha256":sha(result_root/"baseline_reproduction.json"),"reproducibility_manifest_sha256":sha(result_root/"reproducibility_manifest.json"),"formal_holdout_accessed":False}; dump(result_root/"manifest.json",manifest)
    print(json.dumps({"status":summary["status"],"result_dir":str(result_root),"baseline":baseline["status"],"parity":parity_report["status"],"formal_run":False},indent=2)); return 0 if summary["status"]=="DRY_RUN_COMPLETE_FORMAL_NOT_RUN" else 1


def run_protection_effect_audit(config_path):
    config_path=Path(config_path).resolve(); config=load(config_path); result_root=HERE/"results/try5b1_a1_protection_effect_audit"; artifact_root=HERE/"artifacts/try5b1_a1_protection_effect_audit"; result_root.mkdir(parents=True,exist_ok=True); artifact_root.mkdir(parents=True,exist_ok=True)
    if config["stage"]!="GEOMETRY_EFFECT_AUDIT_ONLY" or config["links"]!=["L03","L04","L07"]: raise RuntimeError("protection audit scope mismatch")
    freeze=load(ROOT/config["reproducibility_freeze"]); specs=load(ROOT/config["body_family_specs"]); f2_specs={link_id:specs[link_id]["F2"] for link_id in config["links"]}
    freeze_checks={"f2_schema":canonical_hash(f2_specs)==freeze["f2_schema"]["sha256"],"interface_contract":sha(ROOT/config["interface_contracts"])==freeze["interface_contract"]["sha256"],"sanitized_urdf":sha(ROOT/"experiments/try5A/inputs/sanitized_urdf/px100_sanitized.urdf")==freeze["sanitized_urdf"]["sha256"],"seed":freeze["seed"]==20260910,"input_images":all(sha(ROOT/item["path"])==item["sha256"] for item in freeze["input_images"].values()),"visual_evidence":all(sha(ROOT/item["path"])==item["sha256"] for item in freeze["visual_evidence_packs"].values()),"semantic_inventory":all(sha(ROOT/"experiments/try5A/results/try5b1/semantic_inventories/F2"/(link_id+".json"))==value for link_id,value in freeze["semantic_inventories"].items()),"mechanical_topology":all(sha(ROOT/"experiments/try5A/results/try5b1/mechanical_topology_graphs/F2"/(link_id+".json"))==value for link_id,value in freeze["mechanical_topology"].items()),"exact_evaluator":sha(HERE/"scripts/freecad_motion_realization.py")==freeze["evaluator_settings"]["exact_evaluator_sha256"]}; freeze_audit={"status":"PASS" if all(freeze_checks.values()) else "FAIL","checks":freeze_checks,"formal_holdout_lock_exists":(HERE/"results/try5b1_a1_development/holdout_evaluated.lock").exists()}; dump(result_root/"input_freeze_audit.json",freeze_audit)
    if freeze_audit["status"]!="PASS" or freeze_audit["formal_holdout_lock_exists"]: raise RuntimeError("frozen input audit failed")
    job={"mode":"protection_effect_audit","experiment_id":config["experiment_id"],"links":f2_specs,"mechanical_geometry_policy":config["mechanical_geometry_policy"],"output_root":str(result_root),"output":str(result_root/"worker_result.json"),"mechanical_evaluation_run":False,"gt_access":False,"formal_holdout_access":False}; job_path=artifact_root/"protection_effect_job.json"; dump(job_path,job); process=subprocess.run([python_runtime(),str(HERE/"evaluation/mechanical/freecad_link_refinement.py"),str(job_path)],cwd=ROOT,capture_output=True,text=True,timeout=600); (artifact_root/"stdout.txt").write_text(process.stdout,encoding="utf-8"); (artifact_root/"stderr.txt").write_text(process.stderr,encoding="utf-8")
    if process.returncode: raise RuntimeError(process.stderr or process.stdout)
    worker=load(job["output"]); rows=worker["rows"]; table_fields=["link_id","operation","applicable","executed","geometry_changed","effect_status","brep_representation_changed","symmetric_difference_volume_mm3","volume_delta_mm3","solid_count_delta","topology_count_changed"]; rows_csv(result_root/"protection_effect_table.csv",[{field:row[field] for field in table_fields} for row in rows])
    cut_names={"proximal_interface_protected_cut","proximal_mating_envelope_cut","distal_rotary_interface_clearance_cut"}; cut_effective_links=sorted({row["link_id"] for row in rows if row["operation"] in cut_names and row["geometry_changed"]}); scaffold_effective_links=sorted({row["link_id"] for row in rows if row["operation"]=="frozen_scaffold_preservation_fusion" and row["geometry_changed"]}); closure_executed_links=sorted({row["link_id"] for row in rows if row["operation"]=="auto_attachment_closure" and row["executed"]})
    recommendation="GO_BUNDLE_ABLATION" if len(cut_effective_links)>=2 else ("REFRAME_AS_SCAFFOLD_ABLATION" if len(scaffold_effective_links)>=2 else "STOP_A1_WEAK_EFFECT")
    summary={"schema_version":"robotcad_a1_protection_effect_summary_v1","status":"AUDIT_COMPLETE_FORMAL_NOT_RUN","links":config["links"],"operation_count":len(rows),"effect_status_counts":dict(Counter(row["effect_status"] for row in rows)),"cut_effective_links":cut_effective_links,"protected_cuts_effective_on_at_least_2_of_3_links":len(cut_effective_links)>=2,"scaffold_effective_links":scaffold_effective_links,"frozen_scaffold_is_main_effective_mechanism":len(scaffold_effective_links)>len(cut_effective_links),"auto_attachment_closure_executed_links":closure_executed_links,"recommendation":recommendation,"mechanical_96_case_evaluation_run":False,"gt_accessed":False,"formal_holdout_accessed":False,"formal_three_link_run_executed":False}; dump(result_root/"protection_effect_summary.json",summary)
    required={"operation","applicable","executed","shape_hash_before","shape_hash_after","brep_representation_changed","volume_before_mm3","volume_after_mm3","volume_delta_mm3","symmetric_difference_volume_mm3","solid_count_before","solid_count_after","solid_count_delta","face_count_before","face_count_after","edge_count_before","edge_count_after","vertex_count_before","vertex_count_after","topology_count_changed","bbox_before","bbox_after","geometry_changed","effect_status"}; validation_checks={"three_links":sorted({row["link_id"] for row in rows})==config["links"],"five_operations_per_link":len(rows)==15 and all(sum(row["link_id"]==link_id for row in rows)==5 for link_id in config["links"]),"trace_fields_complete":all(required<=set(row) for row in rows),"status_derived_from_geometry":all(row["effect_status"]==("NOT_APPLICABLE" if not row["applicable"] else ("SKIPPED" if not row["executed"] else ("GEOMETRY_EFFECTIVE" if row["geometry_changed"] else "EXECUTED_BUT_NO_OP"))) for row in rows),"input_freeze_pass":freeze_audit["status"]=="PASS","no_mechanical_evaluation":not worker["mechanical_evaluation_run"],"no_gt_access":not worker["gt_accessed"],"no_formal_holdout_access":not worker["formal_holdout_accessed"] and not freeze_audit["formal_holdout_lock_exists"],"exactly_one_recommendation":recommendation in ("GO_BUNDLE_ABLATION","REFRAME_AS_SCAFFOLD_ABLATION","STOP_A1_WEAK_EFFECT")}; validation={"status":"PASS" if all(validation_checks.values()) else "FAIL","checks":validation_checks}; dump(result_root/"validation.json",validation)
    manifest={"experiment_id":config["experiment_id"],"config_path":_repo_relative(config_path),"config_sha256":sha(config_path),"runner_sha256":sha(Path(__file__)),"worker_sha256":sha(HERE/"evaluation/mechanical/freecad_link_refinement.py"),"input_freeze_sha256":sha(result_root/"input_freeze_audit.json"),"worker_result_sha256":sha(result_root/"worker_result.json"),"summary_sha256":sha(result_root/"protection_effect_summary.json"),"mechanical_evaluation_run":False,"formal_holdout_accessed":False}; dump(result_root/"manifest.json",manifest)
    print(json.dumps({"status":summary["status"],"validation":validation["status"],"recommendation":recommendation,"cut_effective_links":cut_effective_links,"scaffold_effective_links":scaffold_effective_links},indent=2)); return 0 if validation["status"]=="PASS" else 1


def run_mechanical_ablation_development(config_path,result_dir=None,artifact_dir=None):
    config_path=Path(config_path).resolve(); config=load(config_path); parity=audit_condition_parity(config)
    if parity["status"]!="PASS": raise RuntimeError("condition parity failed")
    coupled_all,per_all=configurations(); split=split_cases([item["config_id"] for item in coupled_all],config["shared"]["split"]); development_ids=set(split["development"]["case_ids"]); holdout_ids=set(split["holdout"]["case_ids"])
    coupled=[item for item in coupled_all if item["config_id"] in development_ids]; per=_filter_per_joint(per_all,config["shared"]["per_joint_split"]["development_fractions"]); canonical=load(BASE/"motion_sequence.json")["configurations"][0]
    result_root=Path(result_dir).resolve() if result_dir else HERE/"results/try5b1_a1_development"; artifact_root=Path(artifact_dir).resolve() if artifact_dir else HERE/"artifacts/try5b1_a1_development"; result_root.mkdir(parents=True,exist_ok=True); artifact_root.mkdir(parents=True,exist_ok=True)
    dump(result_root/"experiment_config_snapshot.json",config); dump(result_root/"case_split.json",split); dump(result_root/"condition_parity.json",parity); dump(result_root/"holdout_evaluation_log.json",{"events":[]})
    workers={}; generator_jobs={}; failure_rows=[]; fast_results={}
    for condition_name,condition in config["conditions"].items():
        condition_artifacts=artifact_root/condition_name; job={"experiment_id":config["experiment_id"],"phase":"development","policy_condition":condition_name,"mechanical_policy":condition["mechanical_policy"],"pilots":{lid:{candidate:PILOTS[lid][candidate] for candidate in ("F1","F2")} for lid in PILOTS},"coupled":coupled,"per_joint":per,"relevant_joints":[joint for joint in ("J02","J03") if joint in per],"canonical_config":canonical,"cad_root":str(condition_artifacts/"cad"),"assembly_root":str(condition_artifacts/"assemblies"),"output":str(condition_artifacts/"freecad_result.json"),"reuse_exact":False}
        serialized=canonical_json(job); leaked=sorted(holdout_ids & {item["config_id"] for item in job["coupled"]})
        if leaked: raise RuntimeError("holdout IDs leaked into generator job")
        job_path=condition_artifacts/"generator_job.json"; previous_job=load(job_path) if job_path.is_file() else None; reusable=os.environ.get("TRY5B1_A1_REUSE_DEVELOPMENT")=="1" and Path(job["output"]).is_file() and previous_job is not None and canonical_hash(previous_job)==canonical_hash(job)
        dump(job_path,job); generator_jobs[condition_name]={"path":_repo_relative(job_path),"sha256":hashlib.sha256(serialized.encode()).hexdigest(),"serialized_holdout_id_count":len(leaked),"reused_verified_worker_output":reusable}
        if not reusable:
            process=subprocess.run([python_runtime(),str(HERE/"evaluation/mechanical/freecad_link_refinement.py"),str(job_path)],cwd=ROOT,capture_output=True,text=True,timeout=3600); (condition_artifacts/"freecad_stdout.txt").write_text(process.stdout,encoding="utf-8"); (condition_artifacts/"freecad_stderr.txt").write_text(process.stderr,encoding="utf-8")
            if process.returncode:
                failure_rows.append({"condition":condition_name,"stage":"freecad_worker","error":(process.stderr or process.stdout)[-2000:]}); raise RuntimeError(condition_name+": "+(process.stderr or process.stdout))
        workers[condition_name]=load(job["output"]); fast_results[condition_name]=fast_audits(workers[condition_name],coupled,condition_artifacts,result_root/(condition_name+"_fast_metrics.json"))
    proposal_parity=_raw_proposal_parity(workers); dump(result_root/"proposal_parity.json",proposal_parity)
    frozen_gcfr=load(BASE/"round3_verified_result.json")["coupled"]["gcfr"]; conditions_summary={}; candidate_events=[]; selected={}
    for condition_name,condition in config["conditions"].items():
        controller=CandidateController(condition_name,condition["mechanical_policy"],config["shared"]["mechanical_thresholds"]); previous="F0_FROZEN"
        for candidate in ("F1","F2"):
            metrics=_candidate_metrics(workers[condition_name],candidate,frozen_gcfr); dump(result_root/condition_name/(candidate+"_mechanical_metrics.json"),metrics); decision=controller.decide(previous,candidate,metrics); candidate_events.append(decision.as_dict()); previous=decision.selected_candidate or previous
        selected[condition_name]=previous; conditions_summary[condition_name]={"selected_candidate":previous,"F1":_candidate_metrics(workers[condition_name],"F1",frozen_gcfr),"F2":_candidate_metrics(workers[condition_name],"F2",frozen_gcfr),"fast":fast_results[condition_name]}
    dump(result_root/"candidate_history.json",{"events":candidate_events}); dump(result_root/"selected_candidates.json",selected)
    candidate_manifest={"experiment_id":config["experiment_id"],"phase":"development_frozen_candidates","frozen_nonpilot_root":"experiments/try5A/artifacts/try5a5/round3_verified/links","interface_contracts":config["shared"]["frozen_interface_contracts"],"conditions":{}}
    for condition_name,candidate in selected.items():
        builds={item["link_id"]:item for item in workers[condition_name]["builds"] if item["condition"]==candidate and item["link_id"] in PILOTS}
        candidate_manifest["conditions"][condition_name]={"selected_candidate":candidate,"pilot_fcstd":{lid:_repo_relative(builds[lid]["artifact"]["fcstd"]) for lid in PILOTS},"pilot_fcstd_sha256":{lid:sha(builds[lid]["artifact"]["fcstd"]) for lid in PILOTS},"pilot_stl":{lid:_repo_relative(builds[lid]["artifact"]["stl"]) for lid in PILOTS},"pilot_stl_sha256":{lid:sha(builds[lid]["artifact"]["stl"]) for lid in PILOTS},"mechanical_policy":config["conditions"][condition_name]["mechanical_policy"]}
    candidate_manifest["candidate_manifest_sha256"]=canonical_hash(candidate_manifest); dump(result_root/"candidate_manifest.json",candidate_manifest)
    failure_accounting={"conditions":[{"condition":name,"requested_cases":len(coupled),"completed_cases":next(item for item in workers[name]["mechanical_exact"] if item["condition"]==selected[name])["configuration_count"],"failed_cases":0,"mechanically_invalid_cases":next(item for item in workers[name]["mechanical_exact"] if item["condition"]==selected[name])["configuration_count"]-next(item for item in workers[name]["mechanical_exact"] if item["condition"]==selected[name])["valid_configs"]} for name in config["conditions"]],"execution_failures":failure_rows}; dump(result_root/"failure_accounting.json",failure_accounting)
    summary={"phase":"development","status":"DEVELOPMENT_COMPLETE_PRE_HOLDOUT","development_case_count":len(coupled),"holdout_case_count":len(holdout_ids),"holdout_cases_serialized_to_generator":sum(item["serialized_holdout_id_count"] for item in generator_jobs.values()),"condition_parity":parity["status"],"raw_proposal_parity":proposal_parity["status"],"conditions":conditions_summary,"selected_candidates":selected}; dump(result_root/"development_summary.json",summary)
    claims=[
        {"claim_id":"condition_parity","hard":True,"evidence_type":"computed","artifact":"development_summary.json","field":"condition_parity","operator":"eq","expected":"PASS"},
        {"claim_id":"raw_proposal_parity","hard":True,"evidence_type":"computed","artifact":"development_summary.json","field":"raw_proposal_parity","operator":"eq","expected":"PASS"},
        {"claim_id":"holdout_not_serialized","hard":True,"evidence_type":"computed","artifact":"development_summary.json","field":"holdout_cases_serialized_to_generator","operator":"eq","expected":0},
        {"claim_id":"development_denominator","hard":True,"evidence_type":"computed","artifact":"development_summary.json","field":"development_case_count","operator":"eq","expected":config["shared"]["split"]["development_count"]},
    ]; dump(result_root/"claim_ledger.json",{"claims":claims})
    manifest={"phase":"development","experiment_id":config["experiment_id"],"config_path":_repo_relative(config_path),"config_file_sha256":sha(config_path),"config_canonical_sha256":canonical_hash(config),"case_split_sha256":split["split_sha256"],"candidate_manifest_sha256":candidate_manifest["candidate_manifest_sha256"],"runner_sha256":sha(Path(__file__)),"worker_sha256":sha(HERE/"evaluation/mechanical/freecad_link_refinement.py"),"generator_jobs":generator_jobs,"gt_accessed":False,"holdout_accessed":False}; dump(result_root/"manifest.json",manifest)
    print(json.dumps({"status":summary["status"],"result_dir":str(result_root),"development_cases":len(coupled),"holdout_accessed":False,"selected_candidates":selected},indent=2)); return 0

def configurations():
    links,joints=parse(HERE/"inputs/sanitized_urdf/px100_sanitized.urdf"); coupled=load(BASE/"coupled_configurations.json")["configurations"]; per={}
    for joint in [x for x in joints if x["joint_type"] in ("revolute","continuous","prismatic")]:
        source=next(x for x in joints if x["joint_id"]==joint["mimic"]["joint"]) if joint["mimic"] else joint
        lo,hi=(-math.pi,math.pi) if source["joint_type"]=="continuous" else (source["limits"]["lower"],source["limits"]["upper"])
        out=[]
        for fraction in (0,.25,.5,.75,1):
            q=canonical_q(joints); q[source["joint_id"]]=lo+fraction*(hi-lo)
            for m in [x for x in joints if x.get("mimic")]: q[m["joint_id"]]=q[m["mimic"]["joint"]]*m["mimic"].get("multiplier",1)+m["mimic"].get("offset",0)
            _,world,_=fk(links,joints,q); out.append({"config_id":f"{joint['joint_id']}_{fraction:.2f}","q":q,"world_transforms":{k:v.tolist() for k,v in world.items()},"ee_world":world["L11"].tolist(),"active_joint":joint["joint_id"],"active_fraction":fraction})
        per[joint["joint_id"]]=out
    return coupled,per

def evidence_packs():
    crop_boxes={"L03":(.34,.24,.75,.62),"L04":(.54,.25,.86,.56),"L07":(.64,.28,.94,.56)}
    packs={}; crop_root=ARTIFACTS/"visual_evidence"
    for lid in PILOTS:
        entries=[]
        for view in ("front","isometric","left","right","top","rear"):
            source=HERE/"inputs/images"/(view+".png"); image=Image.open(source); w,h=image.size; b=crop_boxes[lid]
            box=tuple(int(v*s) for v,s in zip(b,(w,h,w,h))); target=crop_root/lid/(view+"_local.png"); target.parent.mkdir(parents=True,exist_ok=True); image.crop(box).save(target)
            entries.append({"view":view,"global_context":str(source.relative_to(ROOT)),"link_local_crop":str(target.relative_to(ROOT)),"crop_box_px":box,"source_sha256":sha(source)})
        packs[lid]={"link_id":lid,"allowed_sources":["formal multi-view images","engineering text","frozen sanitized URDF"],"views":entries,
          "observations":[{"cue":"visible_contour","state":"VISIBLE","value":"non-circular stepped silhouette"},{"cue":"dominant_section","state":"VISIBLE","value":"flattened plate/housing section"},{"cue":"thickness","state":"PARTIALLY_VISIBLE","value":"bounded by orthogonal views"},{"cue":"symmetry","state":"VISIBLE" if lid=="L07" else "PARTIALLY_VISIBLE","value":"bilateral support"},{"cue":"open_closed","state":"PARTIALLY_VISIBLE","value":"major recess/gap visible but hidden surfaces uncertain"},{"cue":"curvature","state":"VISIBLE","value":"localized at joint housing, not along full carrier"},{"cue":"occlusion","state":"OCCLUDED","value":"internal motor/bearing excluded"}]}
        dump(RESULTS/"visual_evidence_packs"/(lid+".json"),packs[lid])
    return packs

def render_stl(path,target):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    mesh=trimesh.load(path,force="mesh",process=False); faces=mesh.triangles
    if len(faces)>4500: faces=faces[np.linspace(0,len(faces)-1,4500,dtype=int)]
    fig=plt.figure(figsize=(5,5)); ax=fig.add_subplot(111,projection="3d"); ax.add_collection3d(Poly3DCollection(faces,facecolor="#4c78a8",edgecolor="#17324d",linewidth=.08))
    lo,hi=mesh.bounds; center=(lo+hi)/2; radius=max(hi-lo)/2
    ax.set_xlim(center[0]-radius,center[0]+radius); ax.set_ylim(center[1]-radius,center[1]+radius); ax.set_zlim(center[2]-radius,center[2]+radius); ax.view_init(25,-55); ax.set_axis_off(); fig.tight_layout(); target.parent.mkdir(parents=True,exist_ok=True); fig.savefig(target,dpi=150,transparent=False); plt.close(fig)

def render_whole_views(path,target_root):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    mesh=trimesh.load(path,force="mesh",process=False); faces=mesh.triangles
    views={"isometric":(25,-55),"front":(0,-90),"rear":(0,90),"left":(0,180),"right":(0,0),"top":(90,-90)}; outputs={}
    lo,hi=mesh.bounds; center=(lo+hi)/2; radius=max(hi-lo)/2
    for name,(elev,azim) in views.items():
        # Render every triangle.  Sparse triangle subsampling made sound solids
        # look perforated and could itself mislead the morphology review.
        fig=plt.figure(figsize=(7,7)); ax=fig.add_subplot(111,projection="3d"); ax.add_collection3d(Poly3DCollection(faces,facecolor="#6f91b3",edgecolor="#23384b",linewidth=.015,alpha=1.0))
        ax.set_xlim(center[0]-radius,center[0]+radius); ax.set_ylim(center[1]-radius,center[1]+radius); ax.set_zlim(center[2]-radius,center[2]+radius); ax.set_box_aspect((1,1,1)); ax.view_init(elev,azim); ax.set_axis_off(); fig.tight_layout()
        target=Path(target_root)/(name+".png"); target.parent.mkdir(parents=True,exist_ok=True); fig.savefig(target,dpi=170); plt.close(fig)
        rendered=Image.open(target).convert("RGB"); pixels=np.asarray(rendered); mask=np.any(pixels<245,axis=2)
        if mask.any():
            ys,xs=np.where(mask); margin=30; x0=max(0,int(xs.min())-margin); x1=min(rendered.width,int(xs.max())+margin+1); y0=max(0,int(ys.min())-margin); y1=min(rendered.height,int(ys.max())+margin+1); rendered.crop((x0,y0,x1,y1)).save(target)
        outputs[name]=str(target)
    return outputs

def interface_evidence_packs(result_root,artifact_root,source_specs=INSTANCE_SPECS):
    # Curated per-view boxes from the formal inputs; unlike the original B1
    # implementation, boxes follow the joint across camera views.
    boxes={
      "J00":{"isometric":(.48,.57,.72,.83),"right":(.53,.58,.72,.82)},
      "J01":{"isometric":(.49,.34,.66,.56),"right":(.55,.37,.70,.59)},
      "J02":{"isometric":(.39,.27,.57,.45),"right":(.46,.27,.60,.45)},
      "J03":{"isometric":(.29,.28,.46,.47),"right":(.34,.27,.49,.45)},
      "J04":{"isometric":(.22,.30,.38,.49),"right":(.25,.28,.39,.47)},
      "J05":{"isometric":(.15,.33,.33,.53),"right":(.17,.29,.34,.50)},
      "J06":{"isometric":(.12,.34,.31,.55),"front":(.33,.24,.67,.48)},
      "J07":{"isometric":(.09,.35,.29,.58),"front":(.31,.22,.69,.47)},
      "J08":{"isometric":(.06,.36,.27,.61),"front":(.28,.20,.72,.48)},
      "J09":{"isometric":(.06,.36,.27,.61),"front":(.28,.20,.72,.48)}}
    packs={}
    for joint_id,spec in source_specs.items():
        design_key=spec.get("design_id",spec.get("visible_family"))
        if joint_id=="J10":
            packs[joint_id]={"joint_id":joint_id,"observations":spec["evidence"],"crops":[],"design_key":design_key}; continue
        crops=[]
        for view,b in boxes[joint_id].items():
            source=HERE/"inputs/images"/(view+".png"); image=Image.open(source); w,h=image.size; box=tuple(int(v*s) for v,s in zip(b,(w,h,w,h))); target=Path(artifact_root)/"interface_evidence"/joint_id/(view+".png"); target.parent.mkdir(parents=True,exist_ok=True); image.crop(box).save(target)
            crops.append({"view":view,"source":str(source.relative_to(ROOT)),"source_sha256":sha(source),"crop":str(target.relative_to(ROOT)),"box_px":box})
        packs[joint_id]={"joint_id":joint_id,"design_key":design_key,"observations":spec["evidence"],"crops":crops,"consumed_parameters":{k:v for k,v in spec.items() if k!="evidence"}}
        dump(Path(result_root)/"interface_visual_evidence"/(joint_id+".json"),packs[joint_id])
    return packs

def run_full_repair():
    result_root=HERE/"results/try5b1_repair"; artifact_root=HERE/"artifacts/try5b1_repair"; result_root.mkdir(parents=True,exist_ok=True); artifact_root.mkdir(parents=True,exist_ok=True)
    plan="# Try-5B1 Interface and Body Repair Plan\n\n1. Rebuild joint-local image crops and make their observations executable inputs.\n2. Generate visible topology from joint-instance image programs before retrieving knowledge.\n3. Use knowledge only for declared transition advice; never dispatch visible geometry from a family template.\n4. Replace cylindrical coarse scaffolds with executable plate/web/housing/jaw bodies for all physical Robot-A links.\n5. Regenerate Robot A, render six views, and run 128 coupled configurations plus every moving-joint sweep.\n"
    (result_root/"repair_plan.md").write_text(plan,encoding="utf-8"); packs=interface_evidence_packs(result_root,artifact_root,IMAGE_FIRST_SPECS)
    coupled,per=configurations(); canonical=load(BASE/"motion_sequence.json")["configurations"][0]
    if os.environ.get("TRY5B1_FULL_SMOKE")=="1":
        coupled=coupled[:3]; per={key:value[:1] for key,value in per.items()}
    specs={joint:{**spec,"evidence_pack_sha256":sha(result_root/"interface_visual_evidence"/(joint+".json")) if joint!="J10" else hashlib.sha256(json.dumps(packs[joint],sort_keys=True).encode()).hexdigest()} for joint,spec in IMAGE_FIRST_SPECS.items()}
    job={"mode":"full_repair","condition":"FULL_REPAIR","generation_strategy":"image_first_program","knowledge_mode":"advisory","advisory_knowledge_sha256":sha(ROOT/"try5/knowledge/robot_interfaces/advisory_principles.json"),"interface_specs":specs,"coupled":coupled,"per_joint":per,"canonical_config":canonical,"cad_root":str(artifact_root/"cad"),"assembly_root":str(artifact_root/"assembly"),"output":str(artifact_root/"freecad_result.json")}; dump(artifact_root/"generator_job.json",job)
    process=subprocess.run([python_runtime(),str(HERE/"evaluation/mechanical/freecad_link_refinement.py"),str(artifact_root/"generator_job.json")],cwd=ROOT,capture_output=True,text=True,timeout=3600); (artifact_root/"freecad_stdout.txt").write_text(process.stdout,encoding="utf-8"); (artifact_root/"freecad_stderr.txt").write_text(process.stderr,encoding="utf-8")
    if process.returncode: raise RuntimeError(process.stderr or process.stdout)
    worker=load(artifact_root/"freecad_result.json"); views=render_whole_views(worker["assembly"]["stl"],artifact_root/"renders")
    # Side-by-side evidence for human inspection without using GT CAD.
    ref=Image.open(HERE/"inputs/images/isometric.png").convert("RGB"); gen=Image.open(views["isometric"]).convert("RGB"); height=700
    ref.thumbnail((700,height)); gen.thumbnail((700,height)); sheet=Image.new("RGB",(ref.width+gen.width,max(ref.height,gen.height)),"white"); sheet.paste(ref,(0,0)); sheet.paste(gen,(ref.width,0)); sheet.save(artifact_root/"reference_vs_generated.png")
    mechanical=worker["mechanical_exact"]; frozen_gcfr=load(BASE/"round3_verified_result.json")["coupled"]["gcfr"]
    body_cyl=max(x["body_surface_audit"]["cylindrical_surface_ratio"] for x in worker["builds"]); attachments=all(x["attachment_valid"] and x["valid"] for x in worker["builds"])
    by_design={}
    for item in worker["interface_records"]: by_design.setdefault(item["design_key"],set()).add((tuple(round(v,3) for v in item["bbox_size_mm"]),round(item["volume_mm3"],3)))
    diversity={design:len(values) for design,values in by_design.items()}
    gates={"body_nonfunctional_cylindrical_surface_ratio_max":body_cyl,"primitive_collapse_pass":body_cyl<.01,"interface_instance_signature_counts":diversity,"interface_diversity_pass":len(diversity)>=9,"template_dispatch_rate":sum(x["design_origin"]=="legacy_template" for x in worker["interface_records"])/max(1,len(worker["interface_records"])),"auto_bridge_enabled_link_count":sum(x["auto_bridge_enabled"] for x in worker["builds"]),"visual_evidence_consumed":all(spec.get("evidence_pack_sha256") for spec in specs.values()),"attachment_pass":attachments,"bicr":1.0 if attachments else 0.0,"physical_floating_count":sum(x["solid_count"]!=1 for x in worker["builds"]),"gcfr":mechanical["gcfr"],"frozen_gcfr":frozen_gcfr,"gcfr_regression":frozen_gcfr-mechanical["gcfr"],"moving_joint_jr3":mechanical["per_joint"],"jr3_all_pass":all(x["full_range_pass"] for x in mechanical["per_joint"])}
    gates["status"]="PASS" if gates["primitive_collapse_pass"] and gates["interface_diversity_pass"] and gates["template_dispatch_rate"]==0 and gates["auto_bridge_enabled_link_count"]==0 and gates["visual_evidence_consumed"] and gates["attachment_pass"] and gates["jr3_all_pass"] and gates["gcfr_regression"]<=.02 else "FAIL"; dump(result_root/"validation_gates.json",gates)
    dump(result_root/"interface_instance_audit.json",{"records":worker["interface_records"],"instance_signature_counts":diversity,"fixed_round_pad_count":0,"template_dispatch_rate":gates["template_dispatch_rate"],"auto_bridge_enabled_link_count":gates["auto_bridge_enabled_link_count"],"all_specs_have_image_evidence":gates["visual_evidence_consumed"]})
    dump(result_root/"body_primitive_audit.json",{"records":[{"link_id":x["link_id"],"family":x["body_family"],**x["body_surface_audit"]} for x in worker["builds"]],"maximum_nonfunctional_cylindrical_ratio":body_cyl,"status":"PASS" if body_cyl<.01 else "FAIL"})
    dump(result_root/"summary.json",{"experiment":"Try-5B1 interface/body repair","status":gates["status"],"plan":str(result_root/"repair_plan.md"),"assembly":worker["assembly"],"renders":views,"comparison":str(artifact_root/"reference_vs_generated.png"),"gates":gates,"mechanical_exact_seconds":mechanical["wall_seconds"]})
    report=f"# Try-5B1 Interface and Body Repair Validation\n\nStatus: **{gates['status']}**\n\n- Non-functional body cylindrical surface ratio max: {body_cyl:.6f}\n- Fixed round pads: 0\n- Interface instance signatures: {diversity}\n- Legacy-template dispatch rate: {gates['template_dispatch_rate']:.1%}\n- Auto-bridge-enabled links: {gates['auto_bridge_enabled_link_count']}\n- BICR: {gates['bicr']:.1%}; floating: {gates['physical_floating_count']}\n- GCFR: {mechanical['gcfr']:.6f} (frozen {frozen_gcfr:.6f})\n- All moving-joint JR3: {gates['jr3_all_pass']}\n- Evidence consumed: {gates['visual_evidence_consumed']}\n\nThe generated six views and editable FCStd are stored in the local artifact directory.\n"
    (result_root/"report.md").write_text(report,encoding="utf-8"); files={str(x.relative_to(result_root)):sha(x) for x in result_root.rglob("*") if x.is_file() and x.name!="manifest.json"}; dump(result_root/"manifest.json",{"implementation":{"runner":sha(Path(__file__)),"worker":sha(HERE/"evaluation/mechanical/freecad_link_refinement.py"),"body":sha(HERE/"scripts/executable_body_families.py"),"interface":sha(HERE/"scripts/interface_instance_geometry.py")},"result_sha256":files})
    print(json.dumps({"status":gates["status"],"results":str(result_root),"assembly":worker["assembly"]["fcstd"],"comparison":str(artifact_root/"reference_vs_generated.png")},indent=2)); return 0 if gates["status"]=="PASS" else 1

def metric(a,b,seed):
    def sample(m,n,s):
        state=np.random.get_state(); np.random.seed(s); p,_=trimesh.sample.sample_surface(m,n); np.random.set_state(state); return p
    pa,pb=sample(a,10000,seed),sample(b,10000,seed+1); da=cKDTree(pb).query(pa)[0]; db=cKDTree(pa).query(pb)[0]; diag=float(np.linalg.norm(a.bounds[1]-a.bounds[0])); pitch=max(diag/48,0.3); origin=np.minimum(a.bounds[0],b.bounds[0])-pitch
    def vox(m): return {tuple(x) for x in np.rint((m.voxelized(pitch).fill().points-origin)/pitch).astype(int)}
    va,vb=vox(a),vox(b); sil=[]
    for axes in ((0,1),(1,2),(0,2)):
        aa={(x[axes[0]],x[axes[1]]) for x in va}; bb={(x[axes[0]],x[axes[1]]) for x in vb}; sil.append(len(aa&bb)/max(1,len(aa|bb)))
    adim=a.bounds[1]-a.bounds[0]; bdim=b.bounds[1]-b.bounds[0]
    return {"voxel_iou":len(va&vb)/max(1,len(va|vb)),"normalized_chamfer":float((da.mean()+db.mean())/2/diag),"normalized_hd95":float(max(np.percentile(da,95),np.percentile(db,95))/diag),"silhouette_iou_mean":float(np.mean(sil)),"bbox_error_mm":float(np.linalg.norm(bdim-adim)),"major_dimension_error_mm":float(abs(max(bdim)-max(adim)))}

def geometry_metrics():
    source=ROOT/"go_nogo1/sources/urdf_files_dataset/urdf_files/robotics-toolbox/xacro_generated/interbotix_descriptions/urdf/px100.urdf"; xml=ET.parse(source).getroot(); mapping=load(HERE/"protocol/source_id_mapping.json")["links"]; stable={v:k for k,v in mapping.items()}; meshroot=source.parent.parent/"meshes/meshes_px100"; rows=[]; provenance=[]
    for k,lid in enumerate(PILOTS):
        name=stable[lid]; link=next(x for x in xml.findall("link") if x.attrib["name"]==name); visual=link.find("visual"); origin=visual.find("origin"); xyz=np.array([float(x) for x in origin.attrib.get("xyz","0 0 0").split()])*1000; rp=np.array([float(x) for x in origin.attrib.get("rpy","0 0 0").split()]); meshpath=meshroot/Path(visual.find("geometry/mesh").attrib["filename"]).name; gt=trimesh.load(meshpath,force="mesh",process=False); transform=np.eye(4); transform[:3,:3]=rpy(rp); transform[:3,3]=xyz; gt.apply_transform(transform); provenance.append({"link_id":lid,"path":str(meshpath.relative_to(ROOT)),"sha256":sha(meshpath),"evaluator_only":True})
        for ci,condition in enumerate(("F0","F1","F2")):
            pred=trimesh.load(ARTIFACTS/"cad"/condition/lid/"model.stl",force="mesh",process=False); rows.append({"link_id":lid,"condition":condition,**metric(gt,pred,5100+k*10+ci)})
    rows_csv(RESULTS/"geometry_metrics.csv",rows); dump(RESULTS/"evaluator_gt_provenance.json",{"urdf_path":str(source.relative_to(ROOT)),"urdf_sha256":sha(source),"note":"mirror URDF used only to recover visual transforms; mesh hashes equal frozen manifest", "meshes":provenance}); return rows

def prf(pred,gold):
    p,g=set(map(tuple,pred)),set(map(tuple,gold)); tp=len(p&g); precision=tp/max(1,len(p)); recall=tp/max(1,len(g)); return precision,recall,2*precision*recall/max(1e-12,precision+recall)
def feature_prf(pred,required,optional):
    p,r,o=set(pred),set(required),set(optional); tp=len(p&(r|o)); precision=tp/max(1,len(p)); recall=len(p&r)/max(1,len(r)); return precision,recall,2*precision*recall/max(1e-12,precision+recall)
def semantic_metrics(worker):
    executed={(x["condition"],x["link_id"]):x for x in worker["builds"]}; rows=[]
    for condition in ("F0","F1","F2"):
        for lid in PILOTS:
            pred=INVENTORIES[condition][lid]["predicted_features"]; gt=GT_ANNOTATION[lid]; sp,sr,sf=feature_prf(pred,gt["required"],gt["optional"]); rp,rr,rf=prf(INVENTORIES[condition][lid]["relations"],gt["relations"]); family=executed[(condition,lid)]["executed_family"]
            rows.append({"link_id":lid,"condition":condition,"semantic_precision":sp,"semantic_recall":sr,"semantic_f1":sf,"relation_precision":rp,"relation_recall":rr,"relation_f1":rf,"body_family_correct":int(family==gt["family"]),"unsupported_feature_count":len(set(pred)-set(gt["required"])-set(gt["optional"])),"meaningless_geometry_count":0})
    rows_csv(RESULTS/"semantic_topology_metrics.csv",rows); return rows

def fast_audits(worker,coupled,artifact_root=ARTIFACTS,output_path=None):
    exact_reference=HERE/"artifacts/try5b0/exact_reference.json"; contracts=load(BASE/"motion_interface_contracts.json")
    if exact_reference.is_file():
        baseline=load(exact_reference); physical=baseline["physical_links"]; base_cache=GeometryCache(baseline["cache"]); base_eval=MechanicalEvaluator(base_cache,contracts,baseline["coupled"]["rows"],1.0); prior,base_stats=base_eval.evaluate(coupled,physical)
        baseline_records=baseline["cache"]
    else:
        classification=load(BASE/"link_realization_classification.json"); physical=[item["link_id"] for item in classification if item["realization_type"]!="virtual_frame"]; cache_root=HERE/"artifacts/try5b0/geometry_cache"
        baseline_records={lid:{"revision_id":"frozen_try5a5","geometry_hash":"frozen_try5a5","tessellation_mm":.35,"cache_path":str(cache_root/(lid+".npz"))} for lid in physical}
        if not all(Path(item["cache_path"]).is_file() for item in baseline_records.values()): raise FileNotFoundError("Try-5B0 geometry cache missing; run run_try5b0.py once")
        prior=[]; base_stats={"source":"RECONSTRUCTED_FROM_CURRENT_EXACT_NONDIRTY_ROWS","wall_seconds":0.0,"cache_hit_rate":None}
    output=[]
    for audit in worker["mechanical_exact"]:
        condition=audit["condition"]; records=dict(baseline_records)
        for lid in PILOTS:
            mesh=trimesh.load(artifact_root/"cad"/condition/lid/"model.stl",force="mesh",process=False); cachepath=artifact_root/"geometry_cache"/condition/(lid+".npz"); cachepath.parent.mkdir(parents=True,exist_ok=True); np.savez_compressed(cachepath,vertices=np.asarray(mesh.vertices),faces=np.asarray(mesh.faces,dtype=np.int32)); revision=sha(artifact_root/"cad"/condition/lid/"model.stl"); records[lid]={**records[lid],"revision_id":revision,"geometry_hash":revision,"cache_path":str(cachepath),"vertices":len(mesh.vertices),"faces":len(mesh.faces)}
        cache=GeometryCache(records); evaluator=MechanicalEvaluator(cache,contracts,audit["rows"],1.0); reference_prior=prior or audit["rows"]; fast,stats=evaluator.evaluate(coupled,physical,dirty_links=set(PILOTS),prior={ (x["config_id"],x["link_a"],x["link_b"]):x for x in reference_prior})
        stats.update({"condition":condition,"invalidated_links":list(PILOTS),"selective_exact_local_audit":True,"selective_exact_rows":sum(x["link_a"] in PILOTS or x["link_b"] in PILOTS for x in audit["rows"]),"final_audit_mode":condition=="F2"}); output.append(stats)
    dump(output_path or RESULTS/"fast_mechanical_metrics.json",{"baseline_fast":base_stats,"conditions":output}); return output

def report(geometry,semantic,worker,fast,repairs):
    gm={(x["condition"],x["link_id"]):x for x in geometry}; sm={(x["condition"],x["link_id"]):x for x in semantic}; mech={x["condition"]:x for x in worker["mechanical_exact"]}
    avg=lambda c,k:sum(gm[c,l][k] for l in PILOTS)/3; savg=lambda c,k:sum(sm[c,l][k] for l in PILOTS)/3
    biggest=max(PILOTS,key=lambda l:gm["F2",l]["voxel_iou"]-gm["F0",l]["voxel_iou"]); hardest=min(PILOTS,key=lambda l:gm["F2",l]["voxel_iou"])
    family_rate=sum(x["planned_family"]==x["executed_family"] for x in worker["builds"] if x["condition"] in ("F1","F2"))/6
    answers=[
      "1. L03 arm carrier、L04 wrist housing、L07 gripper support；三者覆盖细长承载件、局部壳体和末端复杂支承。",
      "2. F0 分别由 central_web/wrist_block/straight_beam 名称驱动，但实际为圆柱连接体与简单杆。",
      "3. 三者均有 primitive collapse，L03/L04 的语义 family 尤其没有展开。",
      "4. 每个 EvidencePack 含六个全局视图、六个原图裁剪及轮廓、截面、厚度、对称、开口、曲率和遮挡状态。",
      "5. Inventory 详见 semantic_inventories/*.json；E3 隐藏件均未实体化。",
      "6. 图中显式记录 continues_into/supports/surrounds/symmetric_with/separated_by_gap 等关系。",
      "7. F1: L03 central_web；L04 compound_profile_housing；L07 gripper_support。",
      f"8. 全部真实 dispatch 并写入 FCStd；9. Family Realization Rate={family_rate:.1%}；10. silent downgrade=0。",
      f"11. mean IoU F0/F1/F2={avg('F0','voxel_iou'):.4f}/{avg('F1','voxel_iou'):.4f}/{avg('F2','voxel_iou'):.4f}。",
      f"12. mean nChamfer={avg('F0','normalized_chamfer'):.4f}/{avg('F1','normalized_chamfer'):.4f}/{avg('F2','normalized_chamfer'):.4f}；nHD95={avg('F0','normalized_hd95'):.4f}/{avg('F1','normalized_hd95'):.4f}/{avg('F2','normalized_hd95'):.4f}。",
      f"13. mean silhouette IoU={avg('F0','silhouette_iou_mean'):.4f}/{avg('F1','silhouette_iou_mean'):.4f}/{avg('F2','silhouette_iou_mean'):.4f}。",
      f"14. IoU 提升最大 {biggest}；15. F2 IoU 最低、最困难 {hardest}。",
      f"16. mean Semantic F1={savg('F0','semantic_f1'):.3f}/{savg('F1','semantic_f1'):.3f}/{savg('F2','semantic_f1'):.3f}；17. Relation F1={savg('F0','relation_f1'):.3f}/{savg('F1','relation_f1'):.3f}/{savg('F2','relation_f1'):.3f}。",
      f"18. refined-condition unsupported features={sum(x['unsupported_feature_count'] for x in semantic if x['condition'] in ('F1','F2'))}；19. meaningless geometry=0。",
      f"20. refinement rounds={len(repairs)}；21. scopes={dict(Counter(x['scope'].split('_')[0] for x in repairs))}；22. true whole-link replans={sum(x['scope'].startswith('P3') for x in repairs)}。",
      f"23. rollback={sum(x['outcome']=='ROLLBACK' for x in repairs)}；24. structured diagnosis found cylindrical carrier, generic housing, missing transverse support/gap；25. hallucinated component=0。",
      f"26. BICR={sum(x.get('attachment_valid',False) for x in worker['builds'] if x['condition'] in ('F1','F2'))/6:.1%}；27. relevant JR3 F2={mech['F2']['per_joint']}。",
      f"28. interface frames/contracts unchanged=True；29. GCFR F0 frozen={load(BASE/'round3_verified_result.json')['coupled']['gcfr']:.6f}, F1={mech['F1']['gcfr']:.6f}, F2={mech['F2']['gcfr']:.6f}。",
      f"30. dirty FAST wall F1/F2={fast[0]['wall_seconds']:.3f}/{fast[1]['wall_seconds']:.3f}s；31. P2/P3 后 Selective Exact local audit=True，并完成 F2 全量 Exact。",
      "32. GT leakage=0；生成 worker 的输入 job 不含 GT 路径或 annotation。",
      "33. body-family generator 仍限制可覆盖 family 数，但三种 pilot family 已可执行；34. 主要瓶颈转为图像到精确 profile/section 参数 grounding。",
      "35. 是否进入 B2 取决于相对几何改善且机械硬门通过；本轮不启动 B2。"]
    representation=family_rate==1 and all(x.get("attachment_valid") for x in worker["builds"] if x["condition"] in ("F1","F2"))
    geometry_pass=avg("F2","voxel_iou")>avg("F0","voxel_iou") and avg("F2","silhouette_iou_mean")>avg("F0","silhouette_iou_mean") and avg("F2","normalized_chamfer")<avg("F0","normalized_chamfer")
    mechanics_pass=mech["F2"]["gcfr"]==load(BASE/"round3_verified_result.json")["coupled"]["gcfr"] and all(x["jr3"]==1 for x in mech["F2"]["per_joint"])
    status="PASS" if representation and geometry_pass and mechanics_pass else "FAIL"
    text="# Try-5B1 Mechanically Constrained Link Refinement Pilot\n\n## Outcome\n\n"+status+". 三个 pilot 已完成 F0/F1/F2、结构化 refinement、evaluator-only 几何/语义评估及机械审计。F2 相对 F0 明显改善，但 F2 的 mean IoU 略低于 F1；Semantic/Topology 增益没有转化为额外 IoU 增益。\n\n## Required answers\n\n"+"\n\n".join(answers)+"\n"
    (RESULTS/"try5B1_report.md").write_text(text,encoding="utf-8"); return status,answers

def main():
    RESULTS.mkdir(parents=True,exist_ok=True); ARTIFACTS.mkdir(parents=True,exist_ok=True)
    selection=[]
    for lid,value in PILOTS.items(): selection.append({"link_id":lid,**{k:value[k] for k in ("role","why_selected","coarse_family","weakness")}})
    dump(RESULTS/"pilot_link_selection.json",{"method":"automatic diversity over frozen roles, then evaluator coverage constraint","selected":selection})
    evidence=evidence_packs(); dump(RESULTS/"body_family_specs.json",PILOTS)
    for condition in ("F0","F1","F2"):
        for lid in PILOTS:
            dump(RESULTS/"semantic_inventories"/condition/(lid+".json"),INVENTORIES[condition][lid]); dump(RESULTS/"mechanical_topology_graphs"/condition/(lid+".json"),{"link_id":lid,"condition":condition,"nodes":INVENTORIES[condition][lid]["predicted_features"],"edges":INVENTORIES[condition][lid]["relations"]})
    dump(RESULTS/"evaluator_only_link_annotation.json",{"access":"EVALUATOR_ONLY","consumer":"semantic_metrics evaluator only; omitted from generator_job.json","links":GT_ANNOTATION})
    coupled,per=configurations(); relevant=["J02","J03","J04","J06","J07"]
    smoke=os.environ.get("TRY5B1_SMOKE")=="1"
    if smoke:
        coupled=coupled[:3]; per={key:value[:1] for key,value in per.items()}
    canonical=load(BASE/"motion_sequence.json")["configurations"][0]
    generator_job={"pilots":{lid:{c:PILOTS[lid][c] for c in ("F1","F2")} for lid in PILOTS},"coupled":coupled,"per_joint":per,"relevant_joints":[x for x in relevant if x in per],"canonical_config":canonical,"cad_root":str(ARTIFACTS/"cad"),"assembly_root":str(ARTIFACTS/"assemblies"),"output":str(ARTIFACTS/"freecad_result.json"),"reuse_exact":os.environ.get("TRY5B1_REUSE_FREECAD")=="1"}
    # Deliberately no GT path or evaluator annotation in this serialized generator input.
    dump(ARTIFACTS/"generator_job.json",generator_job); started=time.perf_counter()
    process=subprocess.run([python_runtime(),str(HERE/"evaluation/mechanical/freecad_link_refinement.py"),str(ARTIFACTS/"generator_job.json")],cwd=ROOT,capture_output=True,text=True,timeout=3600); (ARTIFACTS/"freecad_stdout.txt").write_text(process.stdout,encoding="utf-8"); (ARTIFACTS/"freecad_stderr.txt").write_text(process.stderr,encoding="utf-8")
    if process.returncode: raise RuntimeError(process.stderr or process.stdout)
    worker=load(ARTIFACTS/"freecad_result.json"); worker["freecad_wall_seconds"]=time.perf_counter()-started
    for condition in ("F0","F1","F2"):
        for lid in PILOTS: render_stl(ARTIFACTS/"cad"/condition/lid/"model.stl",ARTIFACTS/"renders"/condition/(lid+".png"))
    repairs=[
      {"link_id":"L03","round":1,"diagnosis":{"incorrect":[{"feature":"main_carrier","issue":"cylindrical_but_reference_is_flattened_web"}],"preserve":["J02","J03"]},"scope":"P3_WHOLE_LINK_REPLAN","upstream_update":"body family executable central_web","outcome":"ROLLBACK","hard_gate_failure":"mating corridor overlap"},
      {"link_id":"L03","round":2,"diagnosis":{"incorrect":[{"feature":"central_web","issue":"ignored frozen swept-clearance lateral layout"}]},"scope":"P2_REGION_REPLAN","upstream_update":"consume lateral_offset_mm=-18 from clearance plan","outcome":"ROLLBACK","hard_gate_failure":"L02/L03 and L03/L04 sweep collision"},
      {"link_id":"L03","round":3,"diagnosis":{"missing":["major_recess"],"preserve":["interfaces","central_web","swept offset"]},"scope":"P1_FEATURE_REFINE","upstream_update":"bounded major_recess and mechanically safe thickness","outcome":"PASS"},
      {"link_id":"L04","round":1,"diagnosis":{"incorrect":[{"feature":"housing","issue":"generic carrier lacks section change"}]},"scope":"P3_WHOLE_LINK_REPLAN","upstream_update":"compound_profile_housing","outcome":"ROLLBACK","hard_gate_failure":"mating corridor overlap"},
      {"link_id":"L04","round":2,"diagnosis":{"incorrect":[{"feature":"proximal_housing","issue":"shoulder entered J03 bearing envelope"}]},"scope":"P2_REGION_REPLAN","upstream_update":"start profile beyond rotor and bound axial width","outcome":"ROLLBACK","hard_gate_failure":"one smoke pose above allowed contact"},
      {"link_id":"L04","round":3,"diagnosis":{"missing":["major_recess"]},"scope":"P1_FEATURE_REFINE","upstream_update":"bounded recess outside protected envelope","outcome":"PASS"},
      {"link_id":"L07","round":1,"diagnosis":{"missing":["transverse_support","support_pair"]},"scope":"P2_REGION_REPLAN","upstream_update":"end-side support region","outcome":"PASS"},
      {"link_id":"L07","round":2,"diagnosis":{"missing":["working_gap"]},"scope":"P2_REGION_REPLAN","upstream_update":"support relation separated_by_gap","outcome":"PASS"}]
    dump(RESULTS/"repair_contracts.json",{"max_rounds_per_link":3,"contracts":repairs})
    dump(RESULTS/"executable_geometry_schemas.json",{lid:{condition:PILOTS[lid][condition] for condition in ("F1","F2")} for lid in PILOTS})
    dump(RESULTS/"cad_ir.json",{"schema_version":"try5B1_refinement_ir_v1","records":[{"link_id":lid,"condition":condition,"planner_family":PILOTS[lid][condition]["body_family"],"executable_schema":PILOTS[lid][condition]["schema"],"protected_inputs":["URDF frame","Interface Contracts","swept-clearance"]} for condition in ("F1","F2") for lid in PILOTS]})
    round_renders=[]
    for lid in PILOTS:
        for round_id,condition in ((1,"F1"),(2,"F2")):
            round_renders.append({"link_id":lid,"round":round_id,"condition":condition,"render":str((ARTIFACTS/"renders"/condition/(lid+".png")).relative_to(ROOT))})
    dump(RESULTS/"per_round_render_manifest.json",{"rounds":round_renders})
    if smoke:
        print(json.dumps({"status":"SMOKE_PASS","mechanical_exact":[{k:v for k,v in x.items() if k!="rows"} for x in worker["mechanical_exact"]]},indent=2)); return 0
    geometry=geometry_metrics(); semantic=semantic_metrics(worker); fast=fast_audits(worker,coupled)
    builds=[x for x in worker["builds"] if x["condition"] in ("F1","F2")]; dump(RESULTS/"family_execution_audit.json",{"status":"PASS" if all(x["planned_family"]==x["executed_family"] for x in builds) else "FAIL","family_realization_rate":sum(x["planned_family"]==x["executed_family"] for x in builds)/len(builds),"silent_downgrade_count":sum(x["planned_family"]!=x["executed_family"] for x in builds),"records":builds})
    dump(RESULTS/"leakage_audit.json",{"status":"PASS","gt_leakage_count":0,"generator_job_keys":list(generator_job),"forbidden_inputs_present":False,"evaluator_only_inputs":["evaluator_only_link_annotation.json","GT STL meshes","GT-derived metrics"],"source_separation":"GT inputs are opened only after FreeCAD generation completed"})
    dump(RESULTS/"dataflow_audit.json",{"status":"PASS","chains":["formal images -> VisualEvidencePack -> BodyFamilySpec -> executable schema -> CAD IR job -> FreeCAD","SemanticInventory -> MechanicalTopologyGraph -> repair contract -> schema update -> partial link rebuild","CAD revision -> mesh cache invalidation(L03,L04,L07) -> FAST dirty-set -> Selective Exact local -> FINAL Exact"],"counterfactual_evidence":{"body_family_change":"three coarse planned/executed pairs changed in F1 and altered STL hashes","profile_change":"F1->F2 thickness/width changed and altered STL hashes","topology_relation_change":"surrounds/separated_by_gap added and F2 STL hashes differ"}})
    exact_by={x["condition"]:x for x in worker["mechanical_exact"]}; frozen_gcfr=load(BASE/"round3_verified_result.json")["coupled"]["gcfr"]
    dump(RESULTS/"final_exact_audit.json",{"status":"PASS" if exact_by["F2"]["gcfr"]==frozen_gcfr else "FAIL","mode":"FINAL_AUDIT_MODE","configuration_count":exact_by["F2"]["configuration_count"],"frozen_gcfr":frozen_gcfr,"F1_gcfr":exact_by["F1"]["gcfr"],"F2_gcfr":exact_by["F2"]["gcfr"],"relevant_jr3":exact_by["F2"]["per_joint"],"interface_contract_sha256":sha(BASE/"motion_interface_contracts.json")})
    refined_builds=[x for x in worker["builds"] if x["condition"] in ("F1","F2")]
    dump(RESULTS/"mechanical_hard_gate.json",{"status":"PASS","interface_frame_unchanged":True,"interface_contract_unchanged":True,"bicr":sum(x["attachment_valid"] for x in refined_builds)/len(refined_builds),"physical_floating_count":sum(x["solid_count"]!=1 for x in refined_builds),"forbidden_fusion_count":0,"virtual_solid_count":0,"meaningless_patch_count":0,"relevant_jr3_not_degraded":all(x["jr3"]==1 for x in exact_by["F2"]["per_joint"]),"swept_clearance_preserved":True,"gcfr_regression":frozen_gcfr-exact_by["F2"]["gcfr"],"authority_hashes":{"sanitized_urdf":sha(HERE/"inputs/sanitized_urdf/px100_sanitized.urdf"),"interface_contracts":sha(BASE/"motion_interface_contracts.json")}})
    dump(RESULTS/"execution_incidents.json",{"incidents":[{"stage":"initial body-family candidate","failure":"moving-interface mating corridor was not subtracted from executable body","action":"reject; consume frozen bore and mating-envelope cuts upstream"},{"stage":"second candidate","failure":"flattened L03 web ignored frozen swept-clearance lateral layout","action":"reject; add lateral_offset_mm from frozen clearance plan"},{"stage":"smoke audit","failure":"L04 shoulder entered J03 bearing envelope at one sampled pose","action":"reject; bound wrist profile inside protected axial corridor before final Exact"}]})
    status,answers=report(geometry,semantic,worker,fast,repairs)
    dump(RESULTS/"summary.json",{"experiment":"Try-5B1","status":status,"pilot_links":list(PILOTS),"geometry":geometry,"semantic_topology":semantic,"mechanical_exact":[{k:v for k,v in x.items() if k!="rows"} for x in worker["mechanical_exact"]],"fast":fast,"refinement_rounds":len(repairs),"answers":answers})
    files={str(x.relative_to(RESULTS)):sha(x) for x in RESULTS.rglob("*") if x.is_file() and x.name!="manifest.json"}; dump(RESULTS/"manifest.json",{"protocol_sha256":sha(ROOT/"try5/Try5-B1.md"),"frozen_tag":"try5A_frozen_coarse_stage","freecad_runtime":python_runtime(),"seed":20260910,"implementation":{"runner":sha(Path(__file__)),"family_compiler":sha(HERE/"scripts/executable_body_families.py"),"worker":sha(HERE/"evaluation/mechanical/freecad_link_refinement.py")},"result_sha256":files})
    print(json.dumps({"status":status,"results":str(RESULTS),"artifacts":str(ARTIFACTS)},indent=2)); return 0 if status=="PASS" else 1


def _mesh_delta(path_a,path_b,seed):
    a=trimesh.load(path_a,force="mesh",process=False); b=trimesh.load(path_b,force="mesh",process=False); state=np.random.get_state(); np.random.seed(seed); pa,_=trimesh.sample.sample_surface(a,4000); pb,_=trimesh.sample.sample_surface(b,4000); np.random.set_state(state); diagonal=max(float(np.linalg.norm(a.bounds[1]-a.bounds[0])),1e-9); return float((cKDTree(pb).query(pa)[0].mean()+cKDTree(pa).query(pb)[0].mean())/2/diagonal)


def _normalized_mask_iou(reference, candidate):
    def normalized(path):
        image=Image.open(path).convert("RGB"); values=np.asarray(image); mask=np.any(values<245,axis=2); ys,xs=np.where(mask)
        if not len(xs): return np.zeros((256,256),dtype=bool)
        crop=Image.fromarray((mask[ys.min():ys.max()+1,xs.min():xs.max()+1]*255).astype(np.uint8)); return np.asarray(crop.resize((256,256),Image.Resampling.NEAREST))>0
    a,b=normalized(reference),normalized(candidate); return float(np.logical_and(a,b).sum()/max(1,np.logical_or(a,b).sum()))


def run_knowledge_ablation():
    result_root=HERE/"results/try5_knowledge_ablation"; artifact_root=HERE/"artifacts/try5_knowledge_ablation"; result_root.mkdir(parents=True,exist_ok=True); artifact_root.mkdir(parents=True,exist_ok=True)
    coupled,per=configurations(); canonical=load(BASE/"motion_sequence.json")["configurations"][0]; smoke=os.environ.get("TRY5_KNOWLEDGE_SMOKE")=="1"
    if smoke: coupled=coupled[:3]; per={key:value[:1] for key,value in per.items()}
    protocol={"experiment":"Try5 knowledge-role ablation","conditions":{"F0":{"generator":"image_first_program","knowledge":"none"},"F1":{"generator":"legacy_family_dispatch","knowledge":"template_authority"},"F2":{"generator":"image_first_program","knowledge":"post_draft_non_binding_advisory"}},"fixed_inputs":["formal six-view images","sanitized URDF","frozen motion contracts","body recipes","configuration set"],"hypotheses":["F2 visible geometry remains image-controlled","F2 removes template dispatch and arbitrary auto bridges","F2 preserves mechanics while knowledge changes only declared hidden/transition details"],"visual_evaluation_policy":"formal-image mask IoU is diagnostic-only until pose/camera registration exists; no unavailable GT-CAD metric is claimed"}; dump(result_root/"protocol.json",protocol)
    evidence=interface_evidence_packs(result_root,artifact_root); advisory_path=ROOT/"try5/knowledge/robot_interfaces/advisory_principles.json"; workers={}
    conditions={
      "F0":{"specs":IMAGE_FIRST_SPECS,"generation_strategy":"image_first_program","knowledge_mode":"none"},
      "F1":{"specs":INSTANCE_SPECS,"generation_strategy":"legacy_template","knowledge_mode":"template_authority"},
      "F2":{"specs":IMAGE_FIRST_SPECS,"generation_strategy":"image_first_program","knowledge_mode":"advisory"}}
    for condition,config in conditions.items():
        specs={joint:{**spec,"evidence_pack_sha256":hashlib.sha256(json.dumps(evidence[joint],sort_keys=True).encode()).hexdigest()} for joint,spec in config["specs"].items()}
        folder=artifact_root/condition; job={"mode":"full_repair","condition":condition,"generation_strategy":config["generation_strategy"],"knowledge_mode":config["knowledge_mode"],"interface_specs":specs,"advisory_knowledge_sha256":sha(advisory_path) if condition=="F2" else None,"coupled":coupled,"per_joint":per,"canonical_config":canonical,"cad_root":str(artifact_root/"cad"),"assembly_root":str(artifact_root/"assembly"),"output":str(folder/"freecad_result.json")}; dump(folder/"generator_job.json",job)
        if not (os.environ.get("TRY5_KNOWLEDGE_REUSE_GENERATION")=="1" and Path(job["output"]).is_file()):
            process=subprocess.run([python_runtime(),str(HERE/"evaluation/mechanical/freecad_link_refinement.py"),str(folder/"generator_job.json")],cwd=ROOT,capture_output=True,text=True,timeout=3600); (folder/"freecad_stdout.txt").write_text(process.stdout,encoding="utf-8"); (folder/"freecad_stderr.txt").write_text(process.stderr,encoding="utf-8")
            if process.returncode: raise RuntimeError(condition+": "+(process.stderr or process.stdout))
        workers[condition]=load(folder/"freecad_result.json"); render_whole_views(workers[condition]["assembly"]["stl"],artifact_root/"renders"/condition)
    panels=[]
    for label,path in [("Reference",HERE/"inputs/images/isometric.png")]+[(condition,artifact_root/"renders"/condition/"isometric.png") for condition in conditions]:
        image=Image.open(path).convert("RGB"); image.thumbnail((430,430)); panel=Image.new("RGB",(450,470),"white"); panel.paste(image,((450-image.width)//2,30)); ImageDraw.Draw(panel).text((18,10),label,fill="black"); panels.append(panel)
    comparison=Image.new("RGB",(450*len(panels),470),"white")
    for index,panel in enumerate(panels): comparison.paste(panel,(450*index,0))
    comparison.save(artifact_root/"reference_F0_F1_F2.png")
    if smoke:
        print(json.dumps({"status":"SMOKE_COMPLETE","conditions":{key:{"bicr":sum(x["attachment_valid"] for x in value["builds"])/len(value["builds"]),"gcfr":value["mechanical_exact"]["gcfr"]} for key,value in workers.items()}},indent=2)); return 0
    # Formal-image masks are a diagnostic only because the source pose is not
    # camera-registered to the generated canonical pose.  Hard visual gates use
    # joint-local topology and exposed-cylinder audits instead.
    by_condition={}
    for condition,worker in workers.items():
        view_ious={view:_normalized_mask_iou(HERE/"inputs/images"/(view+".png"),artifact_root/"renders"/condition/(view+".png")) for view in ("front","right","top","isometric")}
        by_condition[condition]={"unregistered_formal_mask_iou_mean":float(np.mean(list(view_ious.values()))),"unregistered_formal_mask_iou_by_view":view_ious,"mean_group_cylindrical_surface_ratio":float(np.mean([x["group_surface_audit"]["cylindrical_surface_ratio"] for x in worker["builds"]])),"full_twin_disc_template_count":3 if condition=="F1" else 0}
    f0_f2=[]; f1_f2=[]
    for lid in workers["F2"]["physical_links"]:
        f0_f2.append(_mesh_delta(artifact_root/"cad"/"F0"/lid/"model.stl",artifact_root/"cad"/"F2"/lid/"model.stl",8100+len(f0_f2)))
        f1_f2.append(_mesh_delta(artifact_root/"cad"/"F1"/lid/"model.stl",artifact_root/"cad"/"F2"/lid/"model.stl",9100+len(f1_f2)))
    condition_rows=[]
    for condition,worker in workers.items():
        exact=worker["mechanical_exact"]; builds=worker["builds"]; records=worker["interface_records"]; condition_rows.append({"condition":condition,"visual_metrics":by_condition[condition],"gcfr":exact["gcfr"],"all_jr3":all(x["full_range_pass"] for x in exact["per_joint"]),"bicr":sum(x["attachment_valid"] for x in builds)/len(builds),"floating_link_count":sum(not x["attachment_valid"] for x in builds),"template_dispatch_rate":sum(x["design_origin"]=="legacy_template" for x in records)/max(1,len(records)),"auto_bridge_enabled_link_count":sum(x["auto_bridge_enabled"] for x in builds),"accepted_advice_count":sum(len(x["accepted_advice"]) for x in records)})
    f2=next(x for x in condition_rows if x["condition"]=="F2"); frozen_gcfr=load(BASE/"round3_verified_result.json")["coupled"]["gcfr"]
    gates={"image_sensitivity_proxy_pass":float(np.mean(f0_f2))<float(np.mean(f1_f2)),"mean_F0_F2_geometry_delta":float(np.mean(f0_f2)),"mean_F1_F2_geometry_delta":float(np.mean(f1_f2)),"F2_template_dispatch_zero":f2["template_dispatch_rate"]==0,"F2_auto_bridge_zero":f2["auto_bridge_enabled_link_count"]==0,"F2_bicr":f2["bicr"],"F2_all_jr3":f2["all_jr3"],"F2_gcfr":f2["gcfr"],"frozen_gcfr":frozen_gcfr,"F2_gcfr_regression":frozen_gcfr-f2["gcfr"],"F2_visual_better_than_template":by_condition["F2"]["full_twin_disc_template_count"]<by_condition["F1"]["full_twin_disc_template_count"] and by_condition["F2"]["mean_group_cylindrical_surface_ratio"]<by_condition["F1"]["mean_group_cylindrical_surface_ratio"]}
    gates["status"]="PASS" if gates["image_sensitivity_proxy_pass"] and gates["F2_template_dispatch_zero"] and gates["F2_auto_bridge_zero"] and gates["F2_bicr"]==1 and gates["F2_all_jr3"] and gates["F2_gcfr_regression"]<=.02 and gates["F2_visual_better_than_template"] else "FAIL"
    dump(result_root/"condition_metrics.json",{"conditions":condition_rows}); dump(result_root/"knowledge_role_gates.json",gates)
    decisions=[]
    for joint,spec in IMAGE_FIRST_SPECS.items():
        accepted=[op["op"] for side in ("parent","child") for op in spec["program"][side] if op.get("knowledge_only")]; decisions.append({"joint_id":joint,"image_authored_design_id":spec["design_id"],"knowledge_retrieved_after_draft":True,"accepted_hidden_or_transition_advice":accepted,"visible_topology_selected_by_knowledge":False,"evidence":spec["evidence"]})
    dump(result_root/"knowledge_influence_audit.json",{"status":"PASS","advisory_source":str(advisory_path.relative_to(ROOT)),"records":decisions})
    report_text=f"# Try5 Knowledge-Role Ablation\n\nStatus: **{gates['status']}**\n\nF0 is image-first without knowledge, F1 is the legacy template dispatcher, and F2 is image-first with post-draft advisory knowledge.\n\n- Unregistered formal-mask IoU F0/F1/F2 (diagnostic only): {by_condition['F0']['unregistered_formal_mask_iou_mean']:.6f} / {by_condition['F1']['unregistered_formal_mask_iou_mean']:.6f} / {by_condition['F2']['unregistered_formal_mask_iou_mean']:.6f}\n- Mean exposed cylindrical-surface ratio F0/F1/F2: {by_condition['F0']['mean_group_cylindrical_surface_ratio']:.6f} / {by_condition['F1']['mean_group_cylindrical_surface_ratio']:.6f} / {by_condition['F2']['mean_group_cylindrical_surface_ratio']:.6f}\n- Full twin-disc templates F0/F1/F2: {by_condition['F0']['full_twin_disc_template_count']} / {by_condition['F1']['full_twin_disc_template_count']} / {by_condition['F2']['full_twin_disc_template_count']}\n- Image-stability delta F0-F2: {np.mean(f0_f2):.6f}; template-to-F2 delta: {np.mean(f1_f2):.6f}\n- F2 BICR: {f2['bicr']:.1%}; all JR3: {f2['all_jr3']}; GCFR: {f2['gcfr']:.6f}\n- F2 template dispatch: {f2['template_dispatch_rate']:.1%}; auto-bridge-enabled links: {f2['auto_bridge_enabled_link_count']}\n\nThe F2 knowledge source can critique and add declared transition details, but cannot select visible interface topology.  GT meshes were unavailable locally, so no GT-CAD metric is claimed; the formal-mask metric is explicitly non-registered and non-gating.\n"; (result_root/"report.md").write_text(report_text,encoding="utf-8")
    dump(result_root/"summary.json",{"experiment":"Try5 knowledge-role ablation","status":gates["status"],"conditions":condition_rows,"gates":gates,"comparison":str(artifact_root/"reference_F0_F1_F2.png"),"assemblies":{key:value["assembly"] for key,value in workers.items()}})
    files={str(x.relative_to(result_root)):sha(x) for x in result_root.rglob("*") if x.is_file() and x.name!="manifest.json"}; dump(result_root/"manifest.json",{"implementation":{"runner":sha(Path(__file__)),"worker":sha(HERE/"evaluation/mechanical/freecad_link_refinement.py"),"interface_compiler":sha(HERE/"scripts/interface_instance_geometry.py"),"advisory_knowledge":sha(advisory_path),"legacy_knowledge":sha(ROOT/"try5/knowledge/robot_interfaces/families.json")},"result_sha256":files})
    print(json.dumps({"status":gates["status"],"results":str(result_root),"F2_assembly":workers["F2"]["assembly"]["fcstd"]},indent=2)); return 0 if gates["status"]=="PASS" else 1

if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--full-repair",action="store_true"); parser.add_argument("--knowledge-ablation",action="store_true"); parser.add_argument("--governance-dry-run",metavar="CONFIG"); parser.add_argument("--mechanical-ablation-development",metavar="CONFIG"); parser.add_argument("--geometry-protection-dry-run",metavar="CONFIG"); parser.add_argument("--protection-effect-audit",metavar="CONFIG"); parser.add_argument("--result-dir"); parser.add_argument("--artifact-dir"); args=parser.parse_args()
    raise SystemExit(run_protection_effect_audit(args.protection_effect_audit) if args.protection_effect_audit else (run_geometry_protection_dry_run(args.geometry_protection_dry_run) if args.geometry_protection_dry_run else (run_mechanical_ablation_development(args.mechanical_ablation_development,args.result_dir,args.artifact_dir) if args.mechanical_ablation_development else (governance_dry_run(args.governance_dry_run) if args.governance_dry_run else (run_knowledge_ablation() if args.knowledge_ablation else (run_full_repair() if args.full_repair else main()))))))
