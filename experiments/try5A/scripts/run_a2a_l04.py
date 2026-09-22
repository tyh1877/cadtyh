"""Prepare and execute the one-shot A2a L04 same-model dry run."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/try5A"
GO2 = ROOT / "go_nogo2/scripts"
sys.path.insert(0, str(HERE / "scripts"))
sys.path.insert(0, str(HERE / "evaluation"))
sys.path.insert(0, str(GO2))

from experiment_governance import canonical_hash  # noqa: E402
from freecad_runtime import python_runtime  # noqa: E402
from llm_config import load_shared_llm  # noqa: E402
from run_try5b1 import render_whole_views  # noqa: E402


CONDITIONS = ("STRUCTURED_QWEN", "DIRECT_QWEN")
SUPPORTED_SCHEMAS = {
    "central_web": {"required": {"span_mm", "thickness_mm", "proximal_height_mm", "mid_height_mm"}, "optional": {"lateral_offset_mm", "major_recess"}},
    "compound_profile_housing": {"required": {"span_mm", "width_mm", "height_mm", "major_recess"}, "optional": set()},
    "gripper_support": {"required": {"span_mm", "bar_width_mm", "thickness_mm", "working_gap"}, "optional": set()},
}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    return str(Path(path).resolve().relative_to(ROOT)).replace("\\", "/")


def now():
    return datetime.now(timezone.utc).isoformat()


def data_url(path):
    path = Path(path); mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def extract_json(text):
    value = text.strip()
    if value.startswith("```"):
        value = value.split("\n", 1)[1].rsplit("```", 1)[0]
    first = value.find("{"); last = value.rfind("}")
    if first < 0 or last < first: raise ValueError("MODEL_RESPONSE_HAS_NO_JSON_OBJECT")
    return json.loads(value[first:last + 1])


def neutral_interfaces(config):
    contracts = load(ROOT / config["shared_inputs"]["interface_contracts_source"]); rows = []
    for item in contracts:
        if "L04" not in (item["parent"], item["child"]): continue
        side = "parent" if item["parent"] == "L04" else "child"
        rows.append({"joint_id": item["joint_id"], "joint_type": item["joint_type"], "L04_side": side, "origin_xyz_mm": item["origin_xyz_mm"], "origin_rpy_rad": item["origin_rpy_rad"], "axis_in_L04_frame": item["axis_parent"] if side == "parent" else item["axis_child"], "clearance_mm": item["clearance_mm"], "motion_range": item["motion_range"], "allowed_dof": item["allowed_dof"], "constrained_dof": item["constrained_dof"]})
    return {"link_id": "L04", "interfaces": rows, "labels_removed": ["interface_family", "selection_reason", "knowledge_source", "swept_clearance_policy", "motion_clearance_spec"]}


def prepare(config_path):
    config_path = Path(config_path).resolve(); config = load(config_path); result_root = HERE / "results/try5b1_a2a_l04"; artifact_root = HERE / "artifacts/try5b1_a2a_l04"; result_root.mkdir(parents=True, exist_ok=True); bundle = artifact_root / "shared_input_bundle"; bundle.mkdir(parents=True, exist_ok=True)
    if (result_root / "call_started.json").exists(): raise FileExistsError("A2a call already attempted")
    llm = load_shared_llm(ROOT / config["model"]["config_path"])
    if llm.model != config["model"]["requested_identifier"] or llm.temperature != config["model"]["temperature"] or llm.top_p != config["model"]["top_p"] or llm.max_output_tokens != config["model"]["max_output_tokens"] or llm.timeout_seconds != config["model"]["timeout_seconds"] or llm.max_retries != 0: raise RuntimeError("LLM config parity failed")
    holdout = load(HERE / "results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if holdout["accessed"] or holdout["evaluation_count"]: raise RuntimeError("formal holdout already accessed")
    f0_job = {"mode": "export_f0", "f0_fcstd": str(ROOT / config["shared_inputs"]["f0_fcstd"]), "output_brep": str(bundle / "f0_l04.brep"), "output_step": str(bundle / "f0_l04.step"), "output_stl": str(bundle / "f0_l04.stl"), "output_json": str(bundle / "f0_shape.json")}; f0_job_path = bundle / "f0_export_job.json"; dump(f0_job_path, f0_job)
    process = subprocess.run([python_runtime(), str(HERE / "evaluation/mechanical/freecad_a2a_direct_body.py"), str(f0_job_path)], cwd=ROOT, capture_output=True, text=True, timeout=300)
    (bundle / "f0_export_stdout.txt").write_text(process.stdout, encoding="utf-8"); (bundle / "f0_export_stderr.txt").write_text(process.stderr, encoding="utf-8")
    if process.returncode: raise RuntimeError(process.stderr or process.stdout)
    render_whole_views(bundle / "f0_l04.stl", bundle / "f0_renders")
    interfaces = neutral_interfaces(config); dump(result_root / "neutral_interface_context.json", interfaces)
    shared_template = (HERE / "prompts/a2a_shared_l04_evidence.md").read_text(encoding="utf-8"); engineering = (ROOT / config["shared_inputs"]["engineering_text"]).read_text(encoding="utf-8"); urdf = (ROOT / config["shared_inputs"]["sanitized_urdf"]).read_text(encoding="utf-8"); f0_record = load(bundle / "f0_shape.json")
    user_text = shared_template + "\n\n## Engineering text\n\n" + engineering + "\n\n## Sanitized URDF\n\n```xml\n" + urdf + "\n```\n\n## Neutral interface context\n\n```json\n" + json.dumps(interfaces, indent=2) + "\n```\n\n## Starting F0 shape record\n\n```json\n" + json.dumps(f0_record, indent=2) + "\n```\n"
    raw_images = [ROOT / config["shared_inputs"]["raw_image_root"] / (view + ".png") for view in config["shared_inputs"]["raw_image_views"]]; f0_images = [bundle / "f0_renders" / (view + ".png") for view in config["shared_inputs"]["raw_image_views"]]; attachments = raw_images + f0_images
    requests = {}
    common_system = "You are participating in a controlled one-shot CAD refinement experiment. Use only supplied evidence. Return JSON only. Do not access evaluator data or historical Try-5 refinement artifacts."
    for condition in CONDITIONS:
        method_prompt = (ROOT / config["conditions"][condition]["method_prompt"]).read_text(encoding="utf-8"); requests[condition] = {"system": common_system + "\n\n" + method_prompt, "user_text": user_text, "attachments": [{"path": rel(path), "sha256": sha(path)} for path in attachments]}; dump(result_root / condition / "request_manifest.json", requests[condition])
    shared_hash = canonical_hash({"user_text": user_text, "attachments": requests[CONDITIONS[0]]["attachments"]}); input_manifest = {"schema_version": "robotcad_a2a_shared_input_manifest_v1", "status": "PASS", "shared_user_evidence_sha256": shared_hash, "raw_images": {view: sha(ROOT / config["shared_inputs"]["raw_image_root"] / (view + ".png")) for view in config["shared_inputs"]["raw_image_views"]}, "f0_fcstd": {"path": config["shared_inputs"]["f0_fcstd"], "sha256": sha(ROOT / config["shared_inputs"]["f0_fcstd"])}, "f0_brep_sha256": sha(bundle / "f0_l04.brep"), "f0_render_sha256": {view: sha(bundle / "f0_renders" / (view + ".png")) for view in config["shared_inputs"]["raw_image_views"]}, "engineering_text_sha256": sha(ROOT / config["shared_inputs"]["engineering_text"]), "sanitized_urdf_sha256": sha(ROOT / config["shared_inputs"]["sanitized_urdf"]), "neutral_interface_sha256": sha(result_root / "neutral_interface_context.json"), "freecad_runtime_locator": config["shared_inputs"]["freecad_runtime"], "scaffold_policy": config["shared_inputs"]["mechanical_policy"], "structured_information_supplied_to_shared_block": False, "gt_supplied": False, "formal_holdout_accessed": False}; dump(result_root / "shared_input_manifest.json", input_manifest)
    readiness = {"schema_version": "robotcad_a2a_readiness_v1", "status": "PASS", "model_config": llm.redacted_dict(), "seed": config["model"]["seed"], "budget": {key: config["model"][key] for key in ("max_vlm_calls_per_condition", "max_refinement_rounds", "max_output_tokens", "timeout_seconds", "max_retries", "manual_intervention")}, "same_shared_user_evidence": requests[CONDITIONS[0]]["user_text"] == requests[CONDITIONS[1]]["user_text"] and requests[CONDITIONS[0]]["attachments"] == requests[CONDITIONS[1]]["attachments"], "method_prompt_is_only_prompt_difference": True, "formal_holdout_accessed": False, "api_calls": 0, "config_sha256": sha(config_path), "input_manifest_sha256": sha(result_root / "shared_input_manifest.json")}; dump(result_root / "readiness.json", readiness)
    print(json.dumps({"status": "READY", "shared_input_sha256": shared_hash, "model": llm.model, "api_calls": 0}, indent=2)); return 0


def call_once(condition, request, config):
    llm = load_shared_llm(ROOT / config["model"]["config_path"]); client = llm.create_client(); content = [{"type": "text", "text": request["user_text"]}]
    for item in request["attachments"]:
        content.extend([{"type": "text", "text": "Attached evidence: " + item["path"]}, {"type": "image_url", "image_url": {"url": data_url(ROOT / item["path"])}}])
    messages = [{"role": "system", "content": request["system"]}, {"role": "user", "content": content}]; started = time.perf_counter(); started_at = now()
    try:
        response = client.chat.completions.create(model=llm.model, messages=messages, response_format={"type": "json_object"}, temperature=llm.temperature, top_p=llm.top_p, max_tokens=llm.max_output_tokens, seed=config["model"]["seed"]); latency = time.perf_counter() - started; payload = response.model_dump(mode="json"); usage = getattr(response, "usage", None)
        return {"condition": condition, "status": "SUCCESS", "started_utc": started_at, "latency_seconds": latency, "request_id": response.id, "requested_model": llm.model, "returned_model": response.model, "system_fingerprint": getattr(response, "system_fingerprint", None), "seed": config["model"]["seed"], "max_output_tokens": llm.max_output_tokens, "timeout_seconds": llm.timeout_seconds, "usage": {"input_tokens": int(getattr(usage, "prompt_tokens", 0) or 0), "output_tokens": int(getattr(usage, "completion_tokens", 0) or 0), "total_tokens": int(getattr(usage, "total_tokens", 0) or 0)}, "content": response.choices[0].message.content or "", "full_response": payload, "error": None}
    except Exception as error:
        return {"condition": condition, "status": "FAILURE", "started_utc": started_at, "latency_seconds": time.perf_counter() - started, "request_id": None, "requested_model": llm.model, "returned_model": None, "system_fingerprint": None, "seed": config["model"]["seed"], "max_output_tokens": llm.max_output_tokens, "timeout_seconds": llm.timeout_seconds, "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}, "content": "", "full_response": None, "error": f"{type(error).__name__}: {error}"}


def validate_structured(payload):
    required = {"visual_structural_analysis", "body_family", "semantic_inventory", "mechanical_topology", "executable_geometry_schema", "assumptions"}
    if not required <= set(payload): raise ValueError("STRUCTURED_IR_FIELDS_MISSING")
    family = payload["body_family"]; schema = payload["executable_geometry_schema"]
    if family not in SUPPORTED_SCHEMAS or not isinstance(schema, dict): raise ValueError("STRUCTURED_FAMILY_UNSUPPORTED")
    contract = SUPPORTED_SCHEMAS[family]; keys = set(schema)
    if not contract["required"] <= keys or not keys <= contract["required"] | contract["optional"]: raise ValueError("STRUCTURED_SCHEMA_INVALID")
    for key, value in schema.items():
        if isinstance(value, bool): continue
        if not isinstance(value, (int, float)): raise ValueError("STRUCTURED_SCHEMA_VALUE_INVALID: " + key)
        if key == "lateral_offset_mm":
            if abs(float(value)) > 300: raise ValueError("STRUCTURED_SCHEMA_VALUE_INVALID: " + key)
        elif not 0.1 <= float(value) <= 300:
            raise ValueError("STRUCTURED_SCHEMA_VALUE_INVALID: " + key)
    return {"body_family": family, "schema": schema, "semantic_inventory": payload["semantic_inventory"], "mechanical_topology": payload["mechanical_topology"], "visual_structural_analysis": payload["visual_structural_analysis"], "assumptions": payload["assumptions"]}


def run(config_path):
    config_path = Path(config_path).resolve(); config = load(config_path); result_root = HERE / "results/try5b1_a2a_l04"; artifact_root = HERE / "artifacts/try5b1_a2a_l04"; readiness = load(result_root / "readiness.json")
    if readiness["status"] != "PASS" or readiness["api_calls"] != 0: raise RuntimeError("A2a readiness failed")
    started_path = result_root / "call_started.json"
    if started_path.exists(): raise FileExistsError("A2a one-shot calls already attempted")
    holdout = load(HERE / "results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if holdout["accessed"] or holdout["evaluation_count"]: raise RuntimeError("formal holdout accessed")
    dump(started_path, {"status": "STARTED_NO_RETRY", "timestamp_utc": now(), "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip(), "config_sha256": sha(config_path), "formal_holdout_accessed": False})
    requests = {condition: load(result_root / condition / "request_manifest.json") for condition in CONDITIONS}; call_results = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(call_once, condition, requests[condition], config): condition for condition in CONDITIONS}
        for future in as_completed(futures): call_results[futures[future]] = future.result()
    for condition, record in call_results.items():
        folder = result_root / condition; dump(folder / "call_record.json", {key: value for key, value in record.items() if key not in ("content", "full_response")}); (folder / "raw_response.txt").write_text(record["content"], encoding="utf-8"); dump(folder / "full_response.json", record["full_response"] if record["full_response"] is not None else {"error": record["error"]})
    process_summary = {"model_calls": {condition: {key: call_results[condition][key] for key in ("status", "latency_seconds", "request_id", "requested_model", "returned_model", "system_fingerprint", "seed", "max_output_tokens", "timeout_seconds", "usage", "error")} for condition in CONDITIONS}, "same_requested_model": len({call_results[c]["requested_model"] for c in CONDITIONS}) == 1, "same_returned_model": len({call_results[c]["returned_model"] for c in CONDITIONS}) == 1 and all(call_results[c]["returned_model"] for c in CONDITIONS), "api_calls_per_condition": 1, "manual_intervention_count": 0, "repair_calls": 0}; dump(result_root / "process_metrics.json", process_summary)
    if any(call_results[c]["status"] != "SUCCESS" for c in CONDITIONS):
        dump(result_root / "failure_accounting.json", {"status": "MODEL_CALL_FAILURE_RETAINED", "conditions": call_results, "retry_count": 0}); raise RuntimeError("one-shot model call failed; result retained without retry")
    return continue_after_calls(config_path, config, result_root, artifact_root, call_results, process_summary)


def continue_after_calls(config_path, config, result_root, artifact_root, call_results, process_summary):
    structured_raw = extract_json(call_results["STRUCTURED_QWEN"]["content"]); direct_raw = extract_json(call_results["DIRECT_QWEN"]["content"]); structured_ir = validate_structured(structured_raw); dump(result_root / "STRUCTURED_QWEN/structured_ir.json", structured_ir); dump(result_root / "DIRECT_QWEN/direct_response.json", direct_raw)
    direct_code = direct_raw.get("freecad_python")
    if not isinstance(direct_code, str) or not direct_code.strip(): raise ValueError("DIRECT_CODE_MISSING")
    direct_code_path = artifact_root / "DIRECT_QWEN/direct_body.py"; direct_code_path.parent.mkdir(parents=True, exist_ok=True); direct_code_path.write_text(direct_code, encoding="utf-8"); direct_brep = artifact_root / "DIRECT_QWEN/direct_body.brep"; direct_job = {"mode": "execute_direct_body", "f0_fcstd": str(ROOT / config["shared_inputs"]["f0_fcstd"]), "code_path": str(direct_code_path), "output_brep": str(direct_brep), "output_json": str(artifact_root / "DIRECT_QWEN/direct_body_result.json")}; direct_job_path = artifact_root / "DIRECT_QWEN/direct_body_job.json"; dump(direct_job_path, direct_job); direct_started = time.perf_counter(); direct_process = subprocess.run([python_runtime(), str(HERE / "evaluation/mechanical/freecad_a2a_direct_body.py"), str(direct_job_path)], cwd=ROOT, capture_output=True, text=True, timeout=300); direct_runtime = time.perf_counter() - direct_started; (artifact_root / "DIRECT_QWEN/stdout.txt").write_text(direct_process.stdout, encoding="utf-8"); (artifact_root / "DIRECT_QWEN/stderr.txt").write_text(direct_process.stderr, encoding="utf-8")
    if direct_process.returncode: dump(result_root / "failure_accounting.json", {"status": "DIRECT_CAD_INVALID_RETAINED", "returncode": direct_process.returncode, "error": (direct_process.stderr or direct_process.stdout)[-4000:], "retry_count": 0}); raise RuntimeError("Direct CAD failed; no retry")
    development = load(ROOT / config["shared_inputs"]["development_input"]); workers = {}; builds = {}; cad_runtimes = {"DIRECT_QWEN_BODY_CODE": direct_runtime}
    for condition in CONDITIONS:
        run_root = artifact_root / condition / "canonical_build"; output = run_root / "generation_result.json"; policy = config["shared_inputs"]["mechanical_policy"]
        spec = structured_ir if condition == "STRUCTURED_QWEN" else {"prebuilt_body_brep": str(direct_brep)}
        job = {"experiment_id": config["experiment_id"], "phase": "A2A_L04_ONE_SHOT", "policy_condition": condition, "mechanical_geometry_policy": policy, "conditions": ["F2"], "pilots": {"L04": {"F2": spec}}, "coupled": development["coupled_configurations"], "per_joint": {"J03": development["per_joint"]["J03"]}, "relevant_joints": ["J03"], "canonical_config": development["canonical_config"], "cad_root": str(run_root / "cad"), "assembly_root": str(run_root / "assemblies"), "output": str(output), "evaluation_enabled": False, "reuse_exact": False, "repair_enabled": False, "gt_access": False, "formal_holdout_access": False}; job_path = run_root / "generation_job.json"; dump(job_path, job); started = time.perf_counter(); process = subprocess.run([python_runtime(), str(HERE / "evaluation/mechanical/freecad_link_refinement.py"), str(job_path)], cwd=ROOT, capture_output=True, text=True, timeout=300); cad_runtimes[condition] = time.perf_counter() - started; (run_root / "stdout.txt").write_text(process.stdout, encoding="utf-8"); (run_root / "stderr.txt").write_text(process.stderr, encoding="utf-8")
        if process.returncode: dump(result_root / "failure_accounting.json", {"status": "CANONICAL_BUILD_FAILURE_RETAINED", "condition": condition, "returncode": process.returncode, "error": (process.stderr or process.stdout)[-4000:], "retry_count": 0}); raise RuntimeError(condition + " canonical build failed; no retry")
        workers[condition] = load(output); builds[condition] = next(item for item in workers[condition]["builds"] if item["condition"] == "F2" and item["link_id"] == "L04")
    candidate = {"schema_version": "robotcad_a2a_l04_candidates_v1", "frozen_nonpilot_root": "experiments/try5A/artifacts/try5a5/round3_verified/links", "interface_contracts": config["shared_inputs"]["interface_contracts_source"], "conditions": {condition: {"selected_candidate": "ONE_SHOT", "pilot_fcstd": {"L04": rel(builds[condition]["artifact"]["fcstd"])}, "mechanical_policy": config["shared_inputs"]["mechanical_policy"]} for condition in CONDITIONS}}; candidate_path = result_root / "candidate_manifest.json"; dump(candidate_path, candidate)
    mechanical_output = artifact_root / "evaluation/mechanical_raw.json"; mechanical_job = {"mode": "A2A_L04_DEVELOPMENT_EXACT", "candidate_manifest": str(candidate_path), "configurations": development["coupled_configurations"], "per_joint": {"J03": development["per_joint"]["J03"]}, "output": str(mechanical_output)}; mechanical_job_path = artifact_root / "evaluation/mechanical_job.json"; dump(mechanical_job_path, mechanical_job); started = time.perf_counter(); mechanical_process = subprocess.run([python_runtime(), str(HERE / "evaluation/mechanical/freecad_holdout_evaluator.py"), str(mechanical_job_path)], cwd=ROOT, capture_output=True, text=True, timeout=1800); mechanical_runtime = time.perf_counter() - started
    if mechanical_process.returncode: raise RuntimeError(mechanical_process.stderr or mechanical_process.stdout)
    mechanical = {item["condition"]: item for item in load(mechanical_output)["conditions"]}
    geometry_job = {"gt_urdf": "go_nogo1/sources/urdf_files_dataset/urdf_files/robotics-toolbox/xacro_generated/interbotix_descriptions/urdf/px100.urdf", "seed": config["model"]["seed"], "candidates": [{"condition": condition, "link_id": "L04", "body_stl": rel(builds[condition]["artifact"]["body_stl"]), "final_stl": rel(builds[condition]["artifact"]["stl"])} for condition in CONDITIONS], "output": str(result_root / "geometry_raw.json")}; geometry_job_path = artifact_root / "evaluation/geometry_job.json"; dump(geometry_job_path, geometry_job); started = time.perf_counter(); geometry_process = subprocess.run([sys.executable, str(HERE / "evaluation/geometry_pair_evaluator.py"), str(geometry_job_path)], cwd=ROOT, capture_output=True, text=True, timeout=300); geometry_runtime = time.perf_counter() - started
    if geometry_process.returncode: raise RuntimeError(geometry_process.stderr or geometry_process.stdout)
    geometry = {(item["condition"], item["scope"]): item for item in load(geometry_job["output"])["rows"]}; rows = []
    for condition in CONDITIONS:
        exact = mechanical[condition]; final = geometry[(condition, "final_assembled_link")]; jr3 = min([item["jr3"] for item in exact["per_joint"]]); rows.append({"condition": condition, "cad_build_success": True, "invalid_cad_attempts": 0, "freecad_failures": 0, "bicr": 1.0 if builds[condition]["attachment_valid"] else 0.0, "connected_solid_count": builds[condition]["solid_count"], "jr3": jr3, "gcfr": exact["gcfr"], "collision_events": exact["collision_events"], "intersection_volume_mm3": exact["intersection_volume_mm3"], "failed_configuration_ids": exact["failed_configuration_ids"], "final_voxel_iou": final["voxel_iou"], "final_silhouette_iou": final["silhouette_iou_mean"], "final_normalized_chamfer": final["normalized_chamfer"], "final_normalized_hd95": final["normalized_hd95"], "body_only_diagnostic": geometry[(condition, "refined_body_only")], "vlm_calls": 1, "input_tokens": call_results[condition]["usage"]["input_tokens"], "output_tokens": call_results[condition]["usage"]["output_tokens"], "model_latency_seconds": call_results[condition]["latency_seconds"], "cad_runtime_seconds": cad_runtimes[condition], "manual_intervention_count": 0})
    dump(result_root / "paired_results.json", {"rows": rows}); process_summary.update({"cad_runtimes_seconds": cad_runtimes, "mechanical_evaluator_runtime_seconds": mechanical_runtime, "geometry_evaluator_runtime_seconds": geometry_runtime}); dump(result_root / "process_metrics.json", process_summary); dump(result_root / "failure_accounting.json", {"status": "COMPLETE", "requested_conditions": 2, "completed_conditions": 2, "failed_conditions": 0, "invalid_cad_attempts": 0, "retry_count": 0, "manual_intervention_count": 0, "cases_per_condition": 96, "formal_holdout_accessed": False})
    manifest = {"experiment_id": config["experiment_id"], "status": "L04_DRY_RUN_COMPLETE_FORMAL_NOT_RUN", "config_sha256": sha(config_path), "shared_input_manifest_sha256": sha(result_root / "shared_input_manifest.json"), "requested_model": config["model"]["requested_identifier"], "returned_models": {condition: call_results[condition]["returned_model"] for condition in CONDITIONS}, "runner_sha256": sha(Path(__file__)), "worker_sha256": sha(HERE / "evaluation/mechanical/freecad_link_refinement.py"), "direct_executor_sha256": sha(HERE / "evaluation/mechanical/freecad_a2a_direct_body.py"), "mechanical_evaluator_sha256": sha(HERE / "evaluation/mechanical/freecad_holdout_evaluator.py"), "geometry_evaluator_sha256": sha(HERE / "evaluation/geometry_pair_evaluator.py"), "formal_holdout_accessed": False, "formal_holdout_evaluation_count": 0}; dump(result_root / "manifest.json", manifest)
    print(json.dumps({"status": manifest["status"], "models": manifest["returned_models"], "rows": len(rows), "holdout_accessed": False}, indent=2)); return 0


def resume(config_path):
    config_path = Path(config_path).resolve(); config = load(config_path); result_root = HERE / "results/try5b1_a2a_l04"; artifact_root = HERE / "artifacts/try5b1_a2a_l04"
    if not (result_root / "call_started.json").is_file(): raise RuntimeError("no completed one-shot call to resume")
    if (result_root / "manifest.json").exists(): raise FileExistsError("A2a result already complete")
    resume_marker = result_root / "executor_resume_started.json"
    if resume_marker.exists(): raise FileExistsError("executor resume already attempted")
    call_results = {}
    for condition in CONDITIONS:
        record = load(result_root / condition / "call_record.json"); record["content"] = (result_root / condition / "raw_response.txt").read_text(encoding="utf-8"); record["full_response"] = load(result_root / condition / "full_response.json"); call_results[condition] = record
    if any(record["status"] != "SUCCESS" for record in call_results.values()): raise RuntimeError("cannot resume failed model call")
    dump(resume_marker, {"status": "RESUME_FROZEN_RESPONSES_ONLY", "timestamp_utc": now(), "reason": "local validator incorrectly rejected legal lateral_offset_mm=0", "new_model_calls": 0, "response_edits": 0, "manual_cad_edits": 0})
    dump(result_root / "execution_incident.json", {"incident_id": "A2A-EXEC-001", "stage": "post_response_structured_validation", "model_calls_completed": 2, "symptom": "local validator rejected legal optional lateral_offset_mm=0", "resolution": "allow zero only for lateral_offset_mm and resume from immutable saved responses", "new_model_calls": 0, "response_edits": 0, "cad_repairs": 0, "fairness_impact": "NONE"})
    return continue_after_calls(config_path, config, result_root, artifact_root, call_results, load(result_root / "process_metrics.json"))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--config", required=True); group = parser.add_mutually_exclusive_group(required=True); group.add_argument("--prepare", action="store_true"); group.add_argument("--run", action="store_true"); group.add_argument("--resume", action="store_true"); args = parser.parse_args(); return prepare(args.config) if args.prepare else (run(args.config) if args.run else resume(args.config))


if __name__ == "__main__":
    raise SystemExit(main())
