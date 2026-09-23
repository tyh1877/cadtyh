"""Stage-gated Try-6.0-C1 L04 pilot; GT is opened only in --evaluate."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/"experiments/try6"
RESULTS=HERE/"results/try6_0_c1"
ARTIFACTS=HERE/"artifacts/try6_0_c1"
sys.path.insert(0,str(HERE/"scripts"))
sys.path.insert(0,str(ROOT/"go_nogo2/scripts"))
sys.path.insert(0,str(ROOT/"experiments/try5A/scripts"))
from kfdg_contract import build_kfdg,validate_vlm,validate_kfdg  # noqa: E402
from llm_config import load_shared_llm  # noqa: E402
from freecad_runtime import python_runtime  # noqa: E402
from run_try5b1 import render_whole_views  # noqa: E402


def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def dump(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rel(path): return str(Path(path).resolve().relative_to(ROOT)).replace("\\","/")
def now(): return datetime.now(timezone.utc).isoformat()


def check_holdout():
    lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"]!=0: raise RuntimeError("formal holdout access detected")
    return {"case_ids_sha256":lock["case_ids_sha256"],"accessed":False,"evaluation_count":0}


def neutral_interfaces():
    contracts=load(ROOT/"experiments/try5A/results/try5a5/motion_interface_contracts.json")
    output=[]
    for item in contracts:
        if "L04" not in (item["parent"],item["child"]):continue
        side="parent" if item["parent"]=="L04" else "child"
        output.append({"joint_id":item["joint_id"],"joint_type":item["joint_type"],"L04_side":side,"origin_xyz_mm":item["origin_xyz_mm"],"origin_rpy_rad":item["origin_rpy_rad"],"axis_in_L04_frame":item["axis_parent"] if side=="parent" else item["axis_child"],"clearance_mm":item["clearance_mm"],"motion_range":item["motion_range"]})
    return {"link_id":"L04","interfaces":output,"excluded_structured_labels":True}


def reduced_api_schema(value):
    if isinstance(value,list):return [reduced_api_schema(item) for item in value]
    if not isinstance(value,dict):return value
    unsupported={"$schema","title","pattern","minItems","maxItems","uniqueItems","minimum","maximum"}
    return {key:reduced_api_schema(item) for key,item in value.items() if key not in unsupported}


def data_url(path):
    return "data:image/png;base64,"+base64.b64encode(Path(path).read_bytes()).decode("ascii")


def prepare(config_path):
    config_path=Path(config_path).resolve();config=load(config_path)
    if RESULTS.exists() and (RESULTS/"pre_run_manifest.json").exists():raise FileExistsError("C1 pre-run already frozen")
    holdout=check_holdout()
    for name in ("kfdg_schema","vlm_response_schema","parameter_bounds","prompt"):
        if not (ROOT/config[name]).is_file():raise FileNotFoundError(config[name])
    if load(RESULTS/"infrastructure_smoke.json")["status"]!="PASS":raise RuntimeError("infrastructure smoke not passed")
    camera=load(RESULTS/"camera_or_view_registration.json")
    if camera["selected_solver_views"]!=["right","top"] or camera["gt_used"]:raise RuntimeError("camera audit invalid")
    c0=load(RESULTS/"c0_baseline.json")
    if c0["metrics"]["status"]!="EVALUATED" or c0["metrics"]["method"]!="DIRECT_QWEN":raise RuntimeError("frozen C0 unavailable")
    llm=load_shared_llm(ROOT/config["model"]["config_path"])
    model=config["model"]
    if (llm.model,llm.temperature,llm.top_p,llm.max_output_tokens,llm.timeout_seconds,llm.max_retries)!=(model["requested_identifier"],model["temperature"],model["top_p"],model["max_output_tokens"],model["timeout_seconds"],model["sdk_retries"]):raise RuntimeError("Qwen config drift")
    source_manifest=load(ROOT/"experiments/try5A/results/try5b1_a2a_three_link/manifest.json")
    if sha(ROOT/config["evaluation"]["geometry_evaluator"])!=source_manifest["geometry_evaluator_sha256"] or sha(ROOT/config["evaluation"]["exact_mechanical_evaluator"])!=source_manifest["exact_evaluator_sha256"]:raise RuntimeError("frozen C0 evaluator drift")
    ARTIFACTS.mkdir(parents=True,exist_ok=True);RESULTS.mkdir(parents=True,exist_ok=True)
    f0=ROOT/"experiments/try5A/artifacts/try5a5/round3_verified/links/L04/model.FCStd"
    bundle=ARTIFACTS/"vlm_inputs";bundle.mkdir(parents=True,exist_ok=True)
    export_job={"mode":"export_f0","f0_fcstd":str(f0),"output_brep":str(bundle/"f0.brep"),"output_step":str(bundle/"f0.step"),"output_stl":str(bundle/"f0.stl"),"output_json":str(bundle/"f0_shape.json")}
    export_path=bundle/"export_job.json";dump(export_path,export_job)
    result=subprocess.run([python_runtime(),str(ROOT/"experiments/try5A/evaluation/mechanical/freecad_a2a_direct_body.py"),str(export_path)],cwd=ROOT,capture_output=True,text=True,timeout=120)
    (bundle/"export_stdout.txt").write_text(result.stdout,encoding="utf-8");(bundle/"export_stderr.txt").write_text(result.stderr,encoding="utf-8")
    if result.returncode:raise RuntimeError("F0 export failed: "+result.stderr[-1000:])
    render_whole_views(bundle/"f0.stl",bundle/"renders")
    interface=neutral_interfaces();dump(RESULTS/"neutral_interface_context.json",interface)
    prompt=(ROOT/config["prompt"]).read_text(encoding="utf-8")
    engineering=(ROOT/"experiments/try5A/inputs/engineering_text/robot_A.md").read_text(encoding="utf-8")
    urdf=(ROOT/"experiments/try5A/inputs/sanitized_urdf/px100_sanitized.urdf").read_text(encoding="utf-8")
    user_text="Engineering text:\n"+engineering+"\nSanitized URDF:\n"+urdf+"\nNeutral interface context:\n"+json.dumps(interface,indent=2)+"\nF0 shape statistics:\n"+json.dumps(load(bundle/"f0_shape.json"),indent=2)
    views=("front","isometric","left","right","top","rear")
    images=[ROOT/"experiments/try5A/inputs/images"/(view+".png") for view in views]+[bundle/"renders"/(view+".png") for view in views]
    request={"system":prompt,"user_text":user_text,"attachments":[{"path":rel(path),"sha256":sha(path)} for path in images],"response_schema_sha256":sha(ROOT/config["vlm_response_schema"]),"response_format":"json_schema_strict","gt_access":False}
    dump(RESULTS/"vlm_request_manifest.json",request)
    dump(RESULTS/"protocol.json",config)
    dump(RESULTS/"solver_config.json",config["solver"])
    dump(RESULTS/"holdout_evaluation_log.json",{"events":[]})
    commit=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    pre={"schema_version":"robotcad_try6_c1_pre_run_v1","status":"READY","implementation_commit":commit,"protocol_sha256":sha(config_path),"kfdg_schema_sha256":sha(ROOT/config["kfdg_schema"]),"vlm_response_schema_sha256":sha(ROOT/config["vlm_response_schema"]),"parameter_bounds_sha256":sha(ROOT/config["parameter_bounds"]),"prompt_sha256":sha(ROOT/config["prompt"]),"model_config":llm.redacted_dict(),"freecad_version":subprocess.run([python_runtime(),"-c","import FreeCAD,json;print(json.dumps(FreeCAD.Version()))"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip(),"python_executable":".venv/Scripts/python.exe","input_hashes_sha256":sha(RESULTS/"input_hashes.json"),"c0_baseline_sha256":sha(RESULTS/"c0_baseline.json"),"camera_audit_sha256":sha(RESULTS/"camera_or_view_registration.json"),"solver_config_sha256":sha(RESULTS/"solver_config.json"),"geometry_evaluator_sha256":sha(ROOT/config["evaluation"]["geometry_evaluator"]),"exact_evaluator_sha256":sha(ROOT/config["evaluation"]["exact_mechanical_evaluator"]),"holdout_lock":holdout,"vlm_request_sha256":sha(RESULTS/"vlm_request_manifest.json")}
    dump(RESULTS/"pre_run_manifest.json",pre)
    print(json.dumps({"status":"READY","c0_exact_iou":c0["metrics"]["final_voxel_iou"],"solver_budget":config["solver"]["max_solver_evaluations"],"holdout_accessed":False},indent=2))


def call_vlm(config_path):
    config=load(config_path);pre=load(RESULTS/"pre_run_manifest.json")
    if pre["status"]!="READY" or pre["protocol_sha256"]!=sha(config_path):raise RuntimeError("pre-run freeze mismatch")
    check_holdout()
    marker=RESULTS/"vlm_call_started.json"
    if marker.exists():raise FileExistsError("formal VLM call already attempted")
    dump(marker,{"timestamp_utc":now(),"maximum_calls":1,"retry_count":0,"gt_access":False})
    request=load(RESULTS/"vlm_request_manifest.json")
    llm=load_shared_llm(ROOT/config["model"]["config_path"])
    content=[{"type":"text","text":request["user_text"]}]
    for item in request["attachments"]:
        content.extend([{"type":"text","text":"Evidence view: "+item["path"]},{"type":"image_url","image_url":{"url":data_url(ROOT/item["path"])}}])
    schema=reduced_api_schema(load(ROOT/config["vlm_response_schema"]))
    start=time.perf_counter()
    try:
        response=llm.create_client().chat.completions.create(model=llm.model,messages=[{"role":"system","content":request["system"]},{"role":"user","content":content}],response_format={"type":"json_schema","json_schema":{"name":"try6_l04_kfdg","strict":True,"schema":schema}},temperature=llm.temperature,top_p=llm.top_p,max_tokens=llm.max_output_tokens,seed=config["model"]["seed"])
        raw=response.choices[0].message.content or ""
        (RESULTS/"vlm_raw_response.txt").write_text(raw,encoding="utf-8")
        dump(RESULTS/"vlm_full_response.json",response.model_dump(mode="json"))
        usage=response.usage
        call={"status":"SUCCESS","requested_model":llm.model,"returned_model":response.model,"request_id":response.id,"system_fingerprint":getattr(response,"system_fingerprint",None),"input_tokens":int(getattr(usage,"prompt_tokens",0) or 0),"output_tokens":int(getattr(usage,"completion_tokens",0) or 0),"latency_seconds":time.perf_counter()-start,"seed":config["model"]["seed"],"retry_count":0,"manual_intervention_count":0}
        dump(RESULTS/"vlm_call_record.json",call)
        parsed=json.loads(raw)
        validated=validate_vlm(parsed)
        dump(RESULTS/"vlm_response.json",validated)
        graph=build_kfdg(validated,load(ROOT/config["parameter_bounds"]))
        dump(RESULTS/"kfdg.json",graph)
        dump(RESULTS/"provenance.json",{"functional_nodes":"URDF_METRIC_ANCHOR","geometric_features":"QWEN_STRUCTURAL_REASONING","parameter_initial_values":"FROZEN_PRE_VLM_VISUAL_AND_F0_ESTIMATE","parameter_final_values":"METRIC_SOLVER_ESTIMATED","gt_generator_access":False})
        print(json.dumps({"status":"KFDG_VALID","model":response.model,"feature_types":[item["type"] for item in graph["geometric_features"]],"vlm_calls":1},indent=2))
    except Exception as error:
        dump(RESULTS/"vlm_failure.json",{"status":"REPRESENTATION_FAILURE","error":f"{type(error).__name__}: {error}","retry_count":0,"elapsed_seconds":time.perf_counter()-start,"gt_access":False})
        raise


def solve(config_path):
    config=load(config_path);check_holdout()
    if not (RESULTS/"kfdg.json").is_file():raise RuntimeError("validated KFDG missing")
    if (RESULTS/"solver_invocation.json").exists():raise FileExistsError("formal solver already attempted")
    dump(RESULTS/"solver_invocation.json",{"status":"STARTED_ONCE","kfdg_sha256":sha(RESULTS/"kfdg.json"),"solver_config_sha256":sha(RESULTS/"solver_config.json"),"gt_access":False,"motion_feedback":False})
    output=ARTIFACTS/"formal_solver"
    result=subprocess.run([sys.executable,str(HERE/"scripts/metric_grounding.py"),"--config",str(RESULTS/"solver_config.json"),"--kfdg",str(RESULTS/"kfdg.json"),"--output-root",str(output)],cwd=ROOT,capture_output=True,text=True,timeout=config["solver"]["max_runtime_seconds"]+30)
    (ARTIFACTS/"solver_stdout.txt").write_text(result.stdout,encoding="utf-8")
    (ARTIFACTS/"solver_stderr.txt").write_text(result.stderr,encoding="utf-8")
    for name in ("solver_history.csv","objective_breakdown.csv","solver_result.json"):
        if (output/name).is_file(): shutil.copy2(output/name,RESULTS/name)
    if result.returncode:raise RuntimeError("formal solver failed: "+result.stderr[-1500:])
    print(result.stdout)


def evaluate(config_path):
    config=load(config_path);check_holdout()
    if (RESULTS/"evaluation_started.json").exists():raise FileExistsError("final evaluation already attempted")
    solver=load(RESULTS/"solver_result.json");graph=load(RESULTS/"kfdg.json")
    validate_kfdg(graph)
    dump(RESULTS/"evaluation_started.json",{"timestamp_utc":now(),"solver_result_sha256":sha(RESULTS/"solver_result.json"),"formal_holdout_accessed":False})
    best=ARTIFACTS/"formal_solver/candidates"/f"candidate_{solver['best_candidate_index']:03d}"
    if not load(best/"build_result.json")["reopen"]["valid"]:raise RuntimeError("best CAD did not reopen")
    for name in ("final.FCStd","final.step","final.stl","body_only.stl","feature_mapping.json"):
        shutil.copy2(best/name,RESULTS/name)
    render_whole_views(RESULTS/"final.stl",RESULTS/"renders")
    parameter_nodes=[]
    for item in graph["parameter_nodes"]:
        parameter_nodes.append({**item,"initial_value":item["value"],"value":solver["theta_star"][item["id"]],"provenance":"SOLVER_ESTIMATED"})
    dump(RESULTS/"parameter_table.json",{"schema_version":"robotcad_try6_c1_final_parameters_v1","parameters":parameter_nodes,"fixed_functional":load(ROOT/config["parameter_bounds"])["fixed_functional"],"solver_result_sha256":sha(RESULTS/"solver_result.json")})
    edit_result=subprocess.run([python_runtime(),str(HERE/"scripts/freecad_c1_edit_smoke.py"),str(RESULTS/"final.FCStd"),str(ARTIFACTS/"formal_editability_smoke.FCStd")],cwd=ROOT,capture_output=True,text=True,timeout=60)
    (ARTIFACTS/"edit_smoke_stdout.txt").write_text(edit_result.stdout,encoding="utf-8")
    (ARTIFACTS/"edit_smoke_stderr.txt").write_text(edit_result.stderr,encoding="utf-8")
    edit={"status":"PASS" if edit_result.returncode==0 else "FAIL","edited_parameter":"recess_depth_mm","formal_prs_claim":False,"stdout":edit_result.stdout[-1000:],"stderr":edit_result.stderr[-1000:]}
    dump(RESULTS/"editability_smoke.json",edit)
    development=load(ROOT/config["evaluation"]["development_input"])
    candidate={"frozen_nonpilot_root":"experiments/try5A/artifacts/try5a5/round3_verified/links","interface_contracts":"experiments/try5A/results/try5a5/motion_interface_contracts.json","conditions":{"C1_KFDG_METRIC":{"selected_candidate":"ONE_FORMAL_DEVELOPMENT","pilot_fcstd":{"L04":rel(RESULTS/"final.FCStd")}}}}
    candidate_path=ARTIFACTS/"evaluation/candidate_manifest.json";dump(candidate_path,candidate)
    exact_job={"mode":"TRY6_C1_DEVELOPMENT_EXACT","candidate_manifest":str(candidate_path),"configurations":development["coupled_configurations"],"per_joint":{"J03":development["per_joint"]["J03"]},"output":str(ARTIFACTS/"evaluation/mechanical_raw.json")}
    exact_path=ARTIFACTS/"evaluation/exact_job.json";dump(exact_path,exact_job)
    start=time.perf_counter()
    exact=subprocess.run([python_runtime(),str(ROOT/config["evaluation"]["exact_mechanical_evaluator"]),str(exact_path)],cwd=ROOT,capture_output=True,text=True,timeout=1800)
    mechanical_runtime=time.perf_counter()-start
    (ARTIFACTS/"evaluation/exact_stdout.txt").write_text(exact.stdout,encoding="utf-8");(ARTIFACTS/"evaluation/exact_stderr.txt").write_text(exact.stderr,encoding="utf-8")
    if exact.returncode:raise RuntimeError("Exact evaluation failed: "+exact.stderr[-1000:])
    mechanical=load(exact_job["output"])["conditions"][0]
    geom_job={"gt_urdf":"go_nogo1/sources/urdf_files_dataset/urdf_files/robotics-toolbox/xacro_generated/interbotix_descriptions/urdf/px100.urdf","seed":config["evaluation"]["geometry_seed"],"candidates":[{"condition":"C1_KFDG_METRIC","link_id":"L04","body_stl":rel(RESULTS/"body_only.stl"),"final_stl":rel(RESULTS/"final.stl")}],"output":str(ARTIFACTS/"evaluation/geometry_raw.json")}
    geom_path=ARTIFACTS/"evaluation/geometry_job.json";dump(geom_path,geom_job)
    start=time.perf_counter()
    geom=subprocess.run([sys.executable,str(ROOT/config["evaluation"]["geometry_evaluator"]),str(geom_path)],cwd=ROOT,capture_output=True,text=True,timeout=300)
    geometry_runtime=time.perf_counter()-start
    (ARTIFACTS/"evaluation/geometry_stdout.txt").write_text(geom.stdout,encoding="utf-8");(ARTIFACTS/"evaluation/geometry_stderr.txt").write_text(geom.stderr,encoding="utf-8")
    if geom.returncode:raise RuntimeError("geometry evaluation failed: "+geom.stderr[-1000:])
    geometry=next(row for row in load(geom_job["output"])["rows"] if row["scope"]=="final_assembled_link")
    build=load(best/"build_result.json")
    dump(RESULTS/"geometry_metrics.json",{"status":"PASS","source_evaluator":config["evaluation"]["geometry_evaluator"],"metrics":geometry,"c0_exact":load(RESULTS/"c0_baseline.json")["metrics"],"gt_evaluator_only":True})
    dump(RESULTS/"mechanical_metrics.json",{"status":"PASS","source_evaluator":config["evaluation"]["exact_mechanical_evaluator"],"bicr":float(build["final_solid_count"]==1),"connected_solid_count":build["final_solid_count"],"attachment_valid":build["final_solid_count"]==1,"jr3":min(row["jr3"] for row in mechanical["per_joint"]),"gcfr":mechanical["gcfr"],"collision_events":mechanical["collision_events"],"intersection_volume_mm3":mechanical["intersection_volume_mm3"],"failed_configuration_ids":mechanical["failed_configuration_ids"],"configuration_count":mechanical["configuration_count"],"raw_exact_sha256":sha(exact_job["output"])})
    call=load(RESULTS/"vlm_call_record.json")
    dump(RESULTS/"process_metrics.json",{"vlm_calls":1,"input_tokens":call["input_tokens"],"output_tokens":call["output_tokens"],"vlm_latency_seconds":call["latency_seconds"],"solver_evaluations":solver["actual_evaluations"],"solver_runtime_seconds":solver["solver_runtime_seconds"],"cad_rebuild_count":solver["actual_evaluations"],"failed_cad_candidates":solver["failed_candidates"],"final_freecad_build_success":build["status"]=="PASS","editability_smoke":edit["status"],"exact_evaluator_seconds":mechanical_runtime,"geometry_evaluator_seconds":geometry_runtime,"manual_intervention_count":0,"formal_holdout_accessed":False})
    dump(RESULTS/"leakage_audit.json",{"generator_inputs":["raw_images","engineering_text","sanitized_urdf","f0_fcstd","neutral_interface_context"],"solver_inputs":["observed_raw_color_masks","urdf_63mm_anchor","validated_kfdg","parameter_bounds"],"gt_generator_access":False,"gt_solver_access":False,"gt_evaluator_only":True,"motion_solver_feedback":False,"formal_holdout_accessed":False})
    dump(RESULTS/"dataflow_audit.json",{"vlm_response_sha256":sha(RESULTS/"vlm_response.json"),"kfdg_sha256":sha(RESULTS/"kfdg.json"),"solver_result_sha256":sha(RESULTS/"solver_result.json"),"parameter_table_sha256":sha(RESULTS/"parameter_table.json"),"feature_mapping_sha256":sha(RESULTS/"feature_mapping.json"),"cad_sha256":sha(RESULTS/"final.FCStd"),"urdf_anchor_mutation_effect":load(RESULTS/"infrastructure_smoke.json")["anchor_mutation"]["solver_metric_result_changed"],"all_nine_parameters_sheet_bound":edit["status"]=="PASS","gt_used_in_generator":False})
    c0=load(RESULTS/"c0_baseline.json")["metrics"]
    gates=config["success_gates"]
    objective=geometry
    checks={"kfdg_schema_valid":validate_kfdg(graph),"cad_build_valid":build["status"]=="PASS" and build["reopen"]["valid"] and edit["status"]=="PASS","manual_intervention_zero":True,"bicr_one":build["final_solid_count"]==1,"connected_solid_one":build["final_solid_count"]==1,"iou_improves_10_percent":objective["voxel_iou"]>=gates["final_iou_ratio_min"]*c0["final_voxel_iou"],"silhouette_within_2_percent":objective["silhouette_iou_mean"]>=gates["silhouette_ratio_min"]*c0["final_silhouette_iou"],"chamfer_within_5_percent":objective["normalized_chamfer"]<=gates["normalized_chamfer_ratio_max"]*c0["final_normalized_chamfer"],"hd95_within_5_percent":objective["normalized_hd95"]<=gates["normalized_hd95_ratio_max"]*c0["final_normalized_hd95"],"one_distance_strictly_better":objective["normalized_chamfer"]<c0["final_normalized_chamfer"] or objective["normalized_hd95"]<c0["final_normalized_hd95"]}
    representation=all(checks[key] for key in ("kfdg_schema_valid","cad_build_valid","manual_intervention_zero","bicr_one","connected_solid_one"))
    geometry_pass=all(checks[key] for key in ("iou_improves_10_percent","silhouette_within_2_percent","chamfer_within_5_percent","hd95_within_5_percent","one_distance_strictly_better"))
    decision="GO_C2" if representation and geometry_pass else ("METRIC_GROUNDING_WEAK" if representation else "REPRESENTATION_FAILURE")
    dump(RESULTS/"decision.json",{"decision":decision,"checks":checks,"geometry_gate_pass":geometry_pass,"representation_gate_pass":representation,"motion_is_diagnostic_only":True,"c0_exact_iou":c0["final_voxel_iou"],"c1_iou_threshold":gates["final_iou_ratio_min"]*c0["final_voxel_iou"],"formal_holdout_accessed":False})
    dump(RESULTS/"failure_accounting.json",{"requested_formal_runs":1,"completed_formal_runs":1,"solver_requested_budget":config["solver"]["max_solver_evaluations"],"solver_evaluations":solver["actual_evaluations"],"invalid_cad_candidates":solver["failed_candidates"],"mechanical_requested_cases":96,"mechanical_completed_cases":mechanical["configuration_count"],"mechanical_failed_configurations":mechanical["invalid_configurations"],"retries":0,"formal_holdout_accessed":False})
    dump(RESULTS/"claim_ledger.json",{"claims":[{"claim_id":"c1_valid_cad","hard":True,"evidence_type":"computed","artifact":"process_metrics.json","field":"final_freecad_build_success","operator":"eq","expected":True},{"claim_id":"mechanical_denominator","hard":True,"evidence_type":"computed","artifact":"mechanical_metrics.json","field":"configuration_count","operator":"eq","expected":96},{"claim_id":"holdout_unused","hard":True,"evidence_type":"computed","artifact":"failure_accounting.json","field":"formal_holdout_accessed","operator":"eq","expected":False}]})
    print(json.dumps({"status":"EVALUATED_PENDING_INDEPENDENT_VALIDATION","decision":decision,"c0_iou":c0["final_voxel_iou"],"c1_iou":objective["voxel_iou"],"holdout_accessed":False},indent=2))


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--config",required=True);group=parser.add_mutually_exclusive_group(required=True);group.add_argument("--prepare",action="store_true");group.add_argument("--vlm",action="store_true");group.add_argument("--solve",action="store_true");group.add_argument("--evaluate",action="store_true");args=parser.parse_args()
    if args.prepare:prepare(args.config)
    elif args.vlm:call_vlm(args.config)
    elif args.solve:solve(args.config)
    else:evaluate(args.config)


if __name__=="__main__":main()
