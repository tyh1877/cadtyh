"""One-shot three-link A2a development comparison, using the audited L04 method code."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/try5A"
sys.path.insert(0, str(HERE / "scripts"))
sys.path.insert(0, str(HERE / "evaluation"))

import run_a2a_l04 as audited  # noqa: E402
from experiment_governance import canonical_hash, audit_condition_parity  # noqa: E402
from freecad_runtime import python_runtime  # noqa: E402

CONDITIONS = audited.CONDITIONS
RESULTS = HERE / "results/try5b1_a2a_three_link"
ARTIFACTS = HERE / "artifacts/try5b1_a2a_three_link"
GT_URDF = "go_nogo1/sources/urdf_files_dataset/urdf_files/robotics-toolbox/xacro_generated/interbotix_descriptions/urdf/px100.urdf"


def load(path): return audited.load(path)
def dump(path, value): return audited.dump(path, value)
def sha(path): return audited.sha(path)
def rel(path): return audited.rel(path)


def command(argv, output_root, timeout):
    output_root = Path(output_root); output_root.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    try:
        process = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        code, stdout, stderr = process.returncode, process.stdout, process.stderr
    except subprocess.TimeoutExpired as error:
        code, stdout, stderr = 124, error.stdout or "", error.stderr or ""
    (output_root / "stdout.txt").write_text(stdout if isinstance(stdout, str) else stdout.decode(errors="replace"), encoding="utf-8")
    (output_root / "stderr.txt").write_text(stderr if isinstance(stderr, str) else stderr.decode(errors="replace"), encoding="utf-8")
    return {"exit_code": code, "seconds": time.perf_counter() - start, "stdout": rel(output_root / "stdout.txt"), "stderr": rel(output_root / "stderr.txt")}


def neutral_interfaces(config, link_id):
    contracts = load(ROOT / config["shared_inputs"]["interface_contracts"])
    rows = []
    for item in contracts:
        if link_id not in (item["parent"], item["child"]): continue
        side = "parent" if item["parent"] == link_id else "child"
        rows.append({"joint_id": item["joint_id"], "joint_type": item["joint_type"], "target_side": side, "origin_xyz_mm": item["origin_xyz_mm"], "origin_rpy_rad": item["origin_rpy_rad"], "axis_in_target_frame": item["axis_parent"] if side == "parent" else item["axis_child"], "clearance_mm": item["clearance_mm"], "motion_range": item["motion_range"], "allowed_dof": item["allowed_dof"], "constrained_dof": item["constrained_dof"]})
    return {"link_id": link_id, "interfaces": rows, "excluded_labels": ["interface_family", "selection_reason", "knowledge_source", "motion_clearance_spec"]}


def assert_holdout(config):
    lock = load(ROOT / config["shared_inputs"]["holdout_lock"])
    if lock["accessed"] is not False or lock["evaluation_count"] != 0: raise RuntimeError("formal holdout is not unused")
    return {"case_ids_sha256": lock["case_ids_sha256"], "accessed": False, "evaluation_count": 0}


def freeze_inputs(config_path):
    config_path = Path(config_path).resolve(); config = load(config_path)
    if RESULTS.exists() and any(RESULTS.iterdir()): raise FileExistsError("A2a formal development directory already exists")
    RESULTS.mkdir(parents=True, exist_ok=True); ARTIFACTS.mkdir(parents=True, exist_ok=True)
    holdout = assert_holdout(config)
    llm = audited.load_shared_llm(ROOT / config["model"]["config_path"])
    model = config["model"]
    if (llm.model, llm.temperature, llm.top_p, llm.max_output_tokens, llm.timeout_seconds, llm.max_retries) != (model["requested_identifier"], model["temperature"], model["top_p"], model["max_output_tokens"], model["timeout_seconds"], model["sdk_retries"]): raise RuntimeError("model configuration parity failed")
    if model["max_calls_per_link_condition"] != 1 or model["max_refinement_rounds"] != 0 or model["technical_retries"] != 0 or model["manual_interventions"] != 0: raise RuntimeError("one-shot policy mismatch")
    l04 = load(HERE / "protocol/try5b1_a2a_same_model_l04.json")
    prompt_paths = {key: ROOT / config["prompt_freeze"][key] for key in ("shared", "structured", "direct")}
    l04_paths = {"shared": HERE / "prompts/a2a_shared_l04_evidence.md", "structured": ROOT / l04["conditions"]["STRUCTURED_QWEN"]["method_prompt"], "direct": ROOT / l04["conditions"]["DIRECT_QWEN"]["method_prompt"]}
    if any(sha(prompt_paths[key]) != config["prompt_freeze"]["sha256"][key] or sha(prompt_paths[key]) != sha(l04_paths[key]) for key in prompt_paths): raise RuntimeError("audited L04 prompt changed")
    development = load(ROOT / config["shared_inputs"]["development_input"])
    split = load(HERE / "results/try5b1_a1_development/case_split.json")
    ids = {item["config_id"] for item in development["coupled_configurations"]}
    if len(ids) != 96 or ids != set(split["development"]["case_ids"]) or ids.intersection(split["holdout"]["case_ids"]): raise RuntimeError("development input leakage")
    if config["links"] != ["L03", "L04", "L07"] or config["conditions"] != list(CONDITIONS): raise RuntimeError("matrix scope mismatch")
    if not config["shared_inputs"]["scaffold_policy"]["preserve_frozen_scaffold"]: raise RuntimeError("scaffold safeguard disabled")
    prompt_hashes = {key: sha(path) for key, path in prompt_paths.items()}
    common_system = "You are participating in a controlled one-shot CAD refinement experiment. Use only supplied evidence. Return JSON only. Do not access evaluator data or historical Try-5 refinement artifacts."
    images = [ROOT / config["shared_inputs"]["raw_images"] / (view + ".png") for view in config["shared_inputs"]["image_views"]]
    evidence_hashes = {"raw_images": {path.name: sha(path) for path in images}, "engineering_text": sha(ROOT / config["shared_inputs"]["engineering_text"]), "sanitized_urdf": sha(ROOT / config["shared_inputs"]["sanitized_urdf"]), "interfaces": sha(ROOT / config["shared_inputs"]["interface_contracts"]), "development_input": sha(ROOT / config["shared_inputs"]["development_input"])}
    shared_template = prompt_paths["shared"].read_text(encoding="utf-8")
    engineering = (ROOT / config["shared_inputs"]["engineering_text"]).read_text(encoding="utf-8")
    urdf = (ROOT / config["shared_inputs"]["sanitized_urdf"]).read_text(encoding="utf-8")
    for link_id in config["links"]:
        folder = ARTIFACTS / "shared" / link_id; folder.mkdir(parents=True, exist_ok=True)
        f0 = ROOT / config["shared_inputs"]["f0_fcstd_pattern"].format(link_id=link_id)
        job = {"mode": "export_f0", "f0_fcstd": str(f0), "output_brep": str(folder / "f0.brep"), "output_step": str(folder / "f0.step"), "output_stl": str(folder / "f0.stl"), "output_json": str(folder / "f0_shape.json")}
        job_path = folder / "f0_export_job.json"; dump(job_path, job)
        execution = command([python_runtime(), str(HERE / "evaluation/mechanical/freecad_a2a_direct_body.py"), str(job_path)], folder / "export_log", model["timeout_seconds"])
        if execution["exit_code"]: raise RuntimeError(f"F0 export failed for {link_id}; see {execution['stderr']}")
        audited.render_whole_views(folder / "f0.stl", folder / "renders")
        context = neutral_interfaces(config, link_id); dump(RESULTS / link_id / "neutral_interface_context.json", context)
        shared = shared_template.replace("L04", link_id)
        user_text = shared + "\n\n## Engineering text\n\n" + engineering + "\n\n## Sanitized URDF\n\n```xml\n" + urdf + "\n```\n\n## Neutral interface context\n\n```json\n" + json.dumps(context, indent=2) + "\n```\n\n## Starting F0 shape record\n\n```json\n" + json.dumps(load(folder / "f0_shape.json"), indent=2) + "\n```\n"
        attachments = images + [folder / "renders" / (view + ".png") for view in config["shared_inputs"]["image_views"]]
        attachment_manifest = [{"path": rel(path), "sha256": sha(path)} for path in attachments]
        for condition in CONDITIONS:
            key = "structured" if condition == "STRUCTURED_QWEN" else "direct"
            method = prompt_paths[key].read_text(encoding="utf-8").replace("L04", link_id)
            request = {"system": common_system + "\n\n" + method, "user_text": user_text, "attachments": attachment_manifest, "template_sha256": prompt_hashes[key], "prompt_version": config["prompt_freeze"]["version"]}
            dump(RESULTS / link_id / condition / "request_manifest.json", request)
        dump(RESULTS / link_id / "input_parity.json", {"link_id": link_id, "status": "PASS", "shared_input_sha256": canonical_hash({"user_text": user_text, "attachments": attachment_manifest}), "f0_fcstd_sha256": sha(f0), "f0_brep_sha256": sha(folder / "f0.brep"), "identical_user_text_and_attachments": True, "scaffold_policy": config["shared_inputs"]["scaffold_policy"], "gt_in_generator": False})
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    dump(RESULTS / "experiment_config_snapshot.json", config)
    dump(RESULTS / "case_split.json", split)
    dump(RESULTS / "condition_parity.json", {"status": "PASS", "conditions": list(CONDITIONS), "method_only_difference": True, "prompt_template_sha256": prompt_hashes, "shared_input_hashes": evidence_hashes})
    dump(RESULTS / "holdout_evaluation_log.json", {"events": []})
    dump(RESULTS / "pre_run_manifest.json", {"status": "READY", "experiment_id": config["experiment_id"], "config_sha256": sha(config_path), "implementation_commit": commit, "prompt_hashes": prompt_hashes, "model_config": llm.redacted_dict(), "sdk_version": __import__("importlib.metadata", fromlist=["version"]).version("openai"), "development_input_sha256": evidence_hashes["development_input"], "holdout_lock": holdout, "runner_sha256": sha(Path(__file__)), "method_helper_sha256": sha(HERE / "scripts/run_a2a_l04.py"), "worker_sha256": sha(HERE / "evaluation/mechanical/freecad_link_refinement.py"), "direct_executor_sha256": sha(HERE / "evaluation/mechanical/freecad_a2a_direct_body.py"), "exact_evaluator_sha256": sha(HERE / "evaluation/mechanical/freecad_holdout_evaluator.py"), "geometry_evaluator_sha256": sha(HERE / "evaluation/geometry_pair_evaluator.py")})
    print(json.dumps({"status": "READY", "links": config["links"], "requests": 6, "holdout_accessed": False}, indent=2))


def save_call(link_id, condition, result):
    folder = RESULTS / link_id / condition
    dump(folder / "call_record.json", {key: value for key, value in result.items() if key not in ("content", "full_response")})
    (folder / "raw_response.txt").write_text(result["content"], encoding="utf-8")
    dump(folder / "full_response.json", result["full_response"] if result["full_response"] is not None else {"error": result["error"]})


def run_calls(config_path):
    config_path = Path(config_path).resolve(); config = load(config_path)
    pre = load(RESULTS / "pre_run_manifest.json")
    if pre["status"] != "READY" or pre["config_sha256"] != sha(config_path): raise RuntimeError("pre-run freeze mismatch")
    if (RESULTS / "formal_started.json").exists(): raise FileExistsError("formal development already attempted")
    assert_holdout(config)
    dump(RESULTS / "formal_started.json", {"status": "STARTED_NO_RESULT_RETRIES", "timestamp_utc": audited.now(), "config_sha256": sha(config_path), "model_calls_planned": 6, "formal_holdout_accessed": False})
    calls = {}
    for link_id in config["links"]:
        requests = {condition: load(RESULTS / link_id / condition / "request_manifest.json") for condition in CONDITIONS}
        if requests[CONDITIONS[0]]["user_text"] != requests[CONDITIONS[1]]["user_text"] or requests[CONDITIONS[0]]["attachments"] != requests[CONDITIONS[1]]["attachments"]: raise RuntimeError(f"input parity failure: {link_id}")
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {condition: pool.submit(audited.call_once, condition, requests[condition], config) for condition in CONDITIONS}
            for condition in CONDITIONS:
                result = futures[condition].result(); save_call(link_id, condition, result)
                calls[f"{link_id}__{condition}"] = {key: value for key, value in result.items() if key not in ("content", "full_response")}
        dump(RESULTS / "call_ledger.json", {"calls": calls, "technical_retries": 0, "result_conditioned_retries": 0, "manual_interventions": 0})
    print(json.dumps({"status": "CALLS_FROZEN", "calls": len(calls), "successes": sum(row["status"] == "SUCCESS" for row in calls.values())}, indent=2))


def evaluate_success(link_id, condition, config, development, build):
    folder = ARTIFACTS / "evaluation" / link_id / condition
    candidate = {"frozen_nonpilot_root": config["shared_inputs"]["frozen_nonpilot_root"], "interface_contracts": config["shared_inputs"]["interface_contracts"], "conditions": {condition: {"selected_candidate": "ONE_SHOT", "pilot_fcstd": {link_id: rel(build["artifact"]["fcstd"])}}}}
    candidate_path = folder / "candidate_manifest.json"; dump(candidate_path, candidate)
    relevant = config["shared_inputs"]["joint_sweeps"][link_id]
    exact_job = {"mode": "A2A_THREE_LINK_DEVELOPMENT_EXACT", "candidate_manifest": str(candidate_path), "configurations": development["coupled_configurations"], "per_joint": {joint: development["per_joint"][joint] for joint in relevant}, "output": str(folder / "mechanical_raw.json")}
    exact_job_path = folder / "exact_job.json"; dump(exact_job_path, exact_job)
    exact_run = command([python_runtime(), str(HERE / "evaluation/mechanical/freecad_holdout_evaluator.py"), str(exact_job_path)], folder / "exact_log", 1800)
    if exact_run["exit_code"]: return {"status": "EXACT_EVALUATOR_FAILURE", "exact_run": exact_run}
    exact = load(exact_job["output"])["conditions"][0]
    geometry_job = {"gt_urdf": GT_URDF, "seed": config["model"]["seed"], "candidates": [{"condition": condition, "link_id": link_id, "body_stl": rel(build["artifact"]["body_stl"]), "final_stl": rel(build["artifact"]["stl"])}], "output": str(folder / "geometry_raw.json")}
    geometry_job_path = folder / "geometry_job.json"; dump(geometry_job_path, geometry_job)
    geometry_run = command([sys.executable, str(HERE / "evaluation/geometry_pair_evaluator.py"), str(geometry_job_path)], folder / "geometry_log", 300)
    if geometry_run["exit_code"]: return {"status": "GEOMETRY_EVALUATOR_FAILURE", "exact_run": exact_run, "geometry_run": geometry_run}
    geometry = load(geometry_job["output"])["rows"]
    final = next(row for row in geometry if row["scope"] == "final_assembled_link")
    body = next(row for row in geometry if row["scope"] == "refined_body_only")
    joint_values = [row["jr3"] for row in exact["per_joint"]]
    return {"status": "EVALUATED", "exact_run": exact_run, "geometry_run": geometry_run, "raw_exact_path": rel(exact_job["output"]), "raw_exact_sha256": sha(exact_job["output"]), "raw_geometry_path": rel(geometry_job["output"]), "raw_geometry_sha256": sha(geometry_job["output"]), "metrics": {"bicr": float(build["attachment_valid"]), "attachment_valid": build["attachment_valid"], "connected_solid_count": build["solid_count"], "jr3": min(joint_values) if joint_values else None, "jr3_detail": exact["per_joint"], "gcfr": exact["gcfr"], "collision_events": exact["collision_events"], "intersection_volume_mm3": exact["intersection_volume_mm3"], "failed_configuration_count": exact["invalid_configurations"], "failed_configuration_ids": exact["failed_configuration_ids"], "configuration_count": exact["configuration_count"], "final_voxel_iou": final["voxel_iou"], "final_silhouette_iou": final["silhouette_iou_mean"], "final_normalized_chamfer": final["normalized_chamfer"], "final_normalized_hd95": final["normalized_hd95"], "final_bbox_error_mm": final["bbox_error_mm"], "final_major_dimension_error_mm": final["major_dimension_error_mm"], "body_only_diagnostic": body}}


def run_execution(config_path):
    config_path = Path(config_path).resolve(); config = load(config_path)
    if not (RESULTS / "formal_started.json").is_file(): raise RuntimeError("model calls not started")
    if (RESULTS / "execution_started.json").exists(): raise FileExistsError("execution already attempted")
    assert_holdout(config)
    ledger = load(RESULTS / "call_ledger.json")["calls"]
    if len(ledger) != 6: raise RuntimeError("six calls were not frozen")
    dump(RESULTS / "execution_started.json", {"timestamp_utc": audited.now(), "call_ledger_sha256": sha(RESULTS / "call_ledger.json"), "model_calls_added": 0})
    development = load(ROOT / config["shared_inputs"]["development_input"])
    records = []
    for link_id in config["links"]:
        for condition in CONDITIONS:
            call = ledger[f"{link_id}__{condition}"]; record = {"link": link_id, "method": condition, "model_call_status": call["status"], "requested_model": call["requested_model"], "returned_model": call["returned_model"], "model_request_id": call["request_id"], "system_fingerprint": call["system_fingerprint"], "input_tokens": call["usage"]["input_tokens"], "output_tokens": call["usage"]["output_tokens"], "total_tokens": call["usage"]["total_tokens"], "model_latency_seconds": call["latency_seconds"], "model_calls": 1, "retry_count": 0, "manual_intervention_count": 0, "requested_configuration_count": 96, "status": "PENDING"}
            if call["status"] != "SUCCESS": record["status"] = "MODEL_CALL_FAILURE"; records.append(record); continue
            raw = (RESULTS / link_id / condition / "raw_response.txt").read_text(encoding="utf-8")
            folder = ARTIFACTS / "runs" / link_id / condition
            try:
                parsed = audited.extract_json(raw)
                if condition == "STRUCTURED_QWEN":
                    ir = audited.validate_structured(parsed); dump(RESULTS / link_id / condition / "structured_ir.json", ir)
                    spec = {"body_family": ir["body_family"], "schema": ir["schema"]}
                    record["structured_ir_sha256"] = sha(RESULTS / link_id / condition / "structured_ir.json")
                else:
                    dump(RESULTS / link_id / condition / "direct_response.json", parsed)
                    code = parsed.get("freecad_python")
                    if not isinstance(code, str) or not code.strip(): raise ValueError("DIRECT_CODE_MISSING")
                    code_path = folder / "generated_body.py"; code_path.parent.mkdir(parents=True, exist_ok=True); code_path.write_text(code, encoding="utf-8")
                    record["generated_code_sha256"] = sha(code_path)
                    direct_job = {"mode": "execute_direct_body", "f0_fcstd": str(ROOT / config["shared_inputs"]["f0_fcstd_pattern"].format(link_id=link_id)), "code_path": str(code_path), "output_brep": str(folder / "direct_body.brep"), "output_json": str(folder / "direct_body_result.json")}
                    job_path = folder / "direct_body_job.json"; dump(job_path, direct_job)
                    direct_run = command([python_runtime(), str(HERE / "evaluation/mechanical/freecad_a2a_direct_body.py"), str(job_path)], folder / "direct_log", config["model"]["timeout_seconds"])
                    record["direct_body_runtime_seconds"] = direct_run["seconds"]
                    record["direct_execution_log"] = direct_run
                    if direct_run["exit_code"]: record["status"] = "DIRECT_CODE_FAILURE"; records.append(record); continue
                    record["direct_body_shape"] = load(direct_job["output_json"])["shape"]
                    spec = {"prebuilt_body_brep": str(folder / "direct_body.brep")}
                run_root = folder / "canonical_build"
                job = {"experiment_id": config["experiment_id"], "phase": "A2A_THREE_LINK_FORMAL_DEVELOPMENT", "policy_condition": condition, "mechanical_geometry_policy": config["shared_inputs"]["scaffold_policy"], "conditions": ["F2"], "pilots": {link_id: {"F2": spec}}, "coupled": development["coupled_configurations"], "per_joint": {joint: development["per_joint"][joint] for joint in config["shared_inputs"]["joint_sweeps"][link_id]}, "relevant_joints": config["shared_inputs"]["joint_sweeps"][link_id], "canonical_config": development["canonical_config"], "cad_root": str(run_root / "cad"), "assembly_root": str(run_root / "assemblies"), "output": str(run_root / "generation_result.json"), "evaluation_enabled": False, "reuse_exact": False, "repair_enabled": False, "gt_access": False, "formal_holdout_access": False}
                job_path = run_root / "generation_job.json"; dump(job_path, job)
                build_run = command([python_runtime(), str(HERE / "evaluation/mechanical/freecad_link_refinement.py"), str(job_path)], run_root / "build_log", config["model"]["timeout_seconds"])
                record["freecad_build_runtime_seconds"] = build_run["seconds"]; record["freecad_execution_log"] = build_run
                if build_run["exit_code"]: record["status"] = "FREECAD_BUILD_FAILURE"; records.append(record); continue
                worker = load(job["output"])
                build = next(row for row in worker["builds"] if row["link_id"] == link_id and row["condition"] == "F2")
                record["cad_build_success"] = bool(build["group_valid"] and all(build["artifact"]["reopen"].values()))
                record["compiler_dispatch"] = {"planned_family": build["planned_family"], "executed_family": build["executed_family"], "schema_consumed": build.get("schema_consumed"), "features": build["features"]}
                record["scaffold_trace"] = build["execution_trace"]
                record["fcstd_path"] = rel(build["artifact"]["fcstd"]); record["fcstd_sha256"] = sha(build["artifact"]["fcstd"])
                record["body_stl_sha256"] = sha(build["artifact"]["body_stl"]); record["final_stl_sha256"] = sha(build["artifact"]["stl"])
                if not record["cad_build_success"]: record["status"] = "INVALID_CAD_ATTEMPT"; records.append(record); continue
                result = evaluate_success(link_id, condition, config, development, build)
                record["mechanical_evaluator_runtime_seconds"] = result["exact_run"]["seconds"]
                if "geometry_run" in result: record["geometry_evaluator_runtime_seconds"] = result["geometry_run"]["seconds"]
                record["status"] = result["status"]
                if result["status"] == "EVALUATED": record.update(result["metrics"]); record["raw_exact_sha256"] = result["raw_exact_sha256"]; record["raw_geometry_sha256"] = result["raw_geometry_sha256"]
                else: record["evaluator_failure"] = {key: value for key, value in result.items() if key != "status"}
            except Exception as error:
                record["status"] = "EXECUTION_EXCEPTION"; record["error"] = f"{type(error).__name__}: {error}"
            records.append(record)
            dump(RESULTS / "run_records.json", {"records": records, "requested_runs": 6, "result_conditioned_retries": 0})
    dump(RESULTS / "run_records.json", {"records": records, "requested_runs": 6, "result_conditioned_retries": 0})
    print(json.dumps({"status": "SIX_RUNS_ATTEMPTED", "evaluated": sum(row["status"] == "EVALUATED" for row in records), "failed": sum(row["status"] != "EVALUATED" for row in records)}, indent=2))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--config", required=True); group = parser.add_mutually_exclusive_group(required=True); group.add_argument("--prepare", action="store_true"); group.add_argument("--calls", action="store_true"); group.add_argument("--execute", action="store_true"); args = parser.parse_args()
    if args.prepare: freeze_inputs(args.config)
    elif args.calls: run_calls(args.config)
    else: run_execution(args.config)


if __name__ == "__main__": main()
