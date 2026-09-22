"""Independent result audit for the A2a L04 same-model dry run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/try5A"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--config", required=True); parser.add_argument("--result-dir", required=True); args = parser.parse_args(); config = load(args.config); root = Path(args.result_dir).resolve()
    required = ["readiness.json", "shared_input_manifest.json", "call_started.json", "process_metrics.json", "STRUCTURED_QWEN/request_manifest.json", "DIRECT_QWEN/request_manifest.json", "STRUCTURED_QWEN/call_record.json", "DIRECT_QWEN/call_record.json", "STRUCTURED_QWEN/raw_response.txt", "DIRECT_QWEN/raw_response.txt", "STRUCTURED_QWEN/full_response.json", "DIRECT_QWEN/full_response.json", "STRUCTURED_QWEN/structured_ir.json", "DIRECT_QWEN/direct_response.json", "candidate_manifest.json", "geometry_raw.json", "paired_results.json", "failure_accounting.json", "manifest.json"]
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        result = {"status": "FAIL", "missing_required_files": missing, "checks": {}}; dump(root / "validation.json", result); print(json.dumps(result, indent=2)); return 1
    readiness = load(root / "readiness.json"); shared = load(root / "shared_input_manifest.json"); process = load(root / "process_metrics.json"); requests = {condition: load(root / condition / "request_manifest.json") for condition in config["conditions"]}; calls = {condition: load(root / condition / "call_record.json") for condition in config["conditions"]}; paired = load(root / "paired_results.json")["rows"]; failures = load(root / "failure_accounting.json"); manifest = load(root / "manifest.json"); candidate = load(root / "candidate_manifest.json"); direct = load(root / "DIRECT_QWEN/direct_response.json"); holdout = load(HERE / "results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    conditions = set(config["conditions"]); row_conditions = {row["condition"] for row in paired}; returned = {calls[c]["returned_model"] for c in conditions}; requested = {calls[c]["requested_model"] for c in conditions}; budgets = {(calls[c]["seed"], calls[c]["max_output_tokens"], calls[c]["timeout_seconds"]) for c in conditions}; policies = {canonical_json(candidate["conditions"][c]["mechanical_policy"]) for c in conditions}
    metric_fields = {"final_voxel_iou", "final_silhouette_iou", "final_normalized_chamfer", "final_normalized_hd95", "bicr", "connected_solid_count", "jr3", "gcfr", "collision_events", "intersection_volume_mm3", "vlm_calls", "input_tokens", "output_tokens", "model_latency_seconds", "cad_runtime_seconds"}
    direct_forbidden_keys = {"body_family", "semantic_inventory", "mechanical_topology", "executable_geometry_schema"}
    checks = {
        "readiness_passed_before_calls": readiness["status"] == "PASS" and readiness["api_calls"] == 0,
        "shared_user_evidence_identical": requests["STRUCTURED_QWEN"]["user_text"] == requests["DIRECT_QWEN"]["user_text"] and requests["STRUCTURED_QWEN"]["attachments"] == requests["DIRECT_QWEN"]["attachments"],
        "method_prompt_only_difference": requests["STRUCTURED_QWEN"]["system"] != requests["DIRECT_QWEN"]["system"] and readiness["method_prompt_is_only_prompt_difference"],
        "shared_input_manifest_pass": shared["status"] == "PASS" and not shared["structured_information_supplied_to_shared_block"] and not shared["gt_supplied"],
        "one_successful_call_each": all(calls[c]["status"] == "SUCCESS" for c in conditions) and process["api_calls_per_condition"] == 1,
        "same_exact_requested_and_returned_model": requested == {config["model"]["requested_identifier"]} and len(returned) == 1 and None not in returned and process["same_requested_model"] and process["same_returned_model"],
        "same_seed_ceiling_timeout": len(budgets) == 1 and budgets == {(config["model"]["seed"], config["model"]["max_output_tokens"], config["model"]["timeout_seconds"])},
        "token_usage_recorded": all(calls[c]["usage"]["input_tokens"] > 0 and calls[c]["usage"]["output_tokens"] > 0 and calls[c]["usage"]["output_tokens"] <= config["model"]["max_output_tokens"] for c in conditions),
        "full_prompts_and_responses_saved": all((root / c / "raw_response.txt").stat().st_size > 0 and (root / c / "full_response.json").stat().st_size > 0 for c in conditions),
        "structured_ir_fresh_artifact_present": (root / "STRUCTURED_QWEN/structured_ir.json").is_file(),
        "direct_output_has_no_structured_ir_fields": not (direct_forbidden_keys & set(direct)),
        "same_scaffold_policy": len(policies) == 1 and next(iter(candidate["conditions"].values()))["mechanical_policy"]["preserve_frozen_scaffold"] is True,
        "paired_metrics_complete": len(paired) == 2 and row_conditions == conditions and all(metric_fields <= set(row) and all(row[field] is not None for field in metric_fields) for row in paired),
        "process_failures_zero": failures["completed_conditions"] == 2 and failures["failed_conditions"] == 0 and failures["invalid_cad_attempts"] == 0 and failures["retry_count"] == 0 and failures["manual_intervention_count"] == 0,
        "historical_frozen_is_context_only": config["historical_frozen_reference"]["comparison_role"] == "context_only_not_same_model_evidence",
        "holdout_unaccessed": holdout["accessed"] is False and holdout["evaluation_count"] == 0 and manifest["formal_holdout_accessed"] is False,
        "runner_did_not_self_validate": not (root / "validation.json").exists(),
    }
    result = {"schema_version": "robotcad_a2a_l04_validation_v1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "failed_checks": [key for key, value in checks.items() if not value], "returned_model": list(returned), "formal_holdout_accessed": False, "missing_required_files": []}; dump(root / "validation.json", result); print(json.dumps(result, indent=2)); return 0 if result["status"] == "PASS" else 1


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


if __name__ == "__main__":
    raise SystemExit(main())
