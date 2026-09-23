"""Independent A2a integrity audit; it never invokes generation or GT evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/try5A"
sys.path.insert(0, str(HERE / "evaluation"))
from experiment_governance import canonical_hash, validate_claim_ledger  # noqa: E402


def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path, value): Path(path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def validate(config_path, result_dir):
    config = load(config_path); root = Path(result_dir).resolve()
    required = ("experiment_config_snapshot.json", "case_split.json", "condition_parity.json", "pre_run_manifest.json", "formal_started.json", "call_ledger.json", "execution_started.json", "run_records.json", "paired_main_table.json", "paired_main_table.csv", "paired_deltas.json", "failure_accounting.json", "claim_ledger.json", "holdout_evaluation_log.json", "artifact_manifest.json")
    missing = [name for name in required if not (root / name).is_file()]
    if missing: return {"status": "FAIL", "missing_required_files": missing, "checks": {}}
    pre = load(root / "pre_run_manifest.json"); calls = load(root / "call_ledger.json"); records = load(root / "run_records.json")["records"]; table = load(root / "paired_main_table.json")["rows"]; deltas = load(root / "paired_deltas.json"); failures = load(root / "failure_accounting.json"); lock = load(ROOT / config["shared_inputs"]["holdout_lock"]); claim_audit = validate_claim_ledger(root, load(root / "claim_ledger.json")["claims"]); artifacts = load(root / "artifact_manifest.json")["artifacts"]
    expected = {(link, condition) for link in config["links"] for condition in config["conditions"]}
    prompt_hashes = {key: sha(ROOT / config["prompt_freeze"][key]) for key in ("shared", "structured", "direct")}
    request_paths = {(link, condition): root / link / condition / "request_manifest.json" for link, condition in expected}
    requests_exist = all(path.is_file() for path in request_paths.values())
    requests = {key: load(path) for key, path in request_paths.items()} if requests_exist else {}
    records_by = {(row["link"], row["method"]): row for row in records}
    calls_by = calls["calls"]
    expected_model = config["model"]["requested_identifier"]
    raw = [root / link / condition / "raw_response.txt" for link, condition in expected]
    response_hashes = all(path.is_file() and sha(path) for path in raw)
    no_gt_text = all("go_nogo1/sources/" not in request["user_text"] and "results/try5b1/" not in json.dumps(request) for request in requests.values()) if requests else False
    same_input = all(requests[(link, "STRUCTURED_QWEN")]["user_text"] == requests[(link, "DIRECT_QWEN")]["user_text"] and requests[(link, "STRUCTURED_QWEN")]["attachments"] == requests[(link, "DIRECT_QWEN")]["attachments"] for link in config["links"]) if requests_exist else False
    prior_validation = load(root / "validation.json") if (root / "validation.json").is_file() else None
    checks = {
        "six_rows_and_calls": len(records) == len(table) == len(calls_by) == 6 and set(records_by) == expected and set((r["link"], r["method"]) for r in table) == expected,
        "one_call_and_no_retry": all(row["model_calls"] == 1 and row["retry_count"] == 0 and row["manual_intervention_count"] == 0 for row in records) and calls["result_conditioned_retries"] == calls["technical_retries"] == 0,
        "same_requested_and_returned_model": all(row["requested_model"] == row["returned_model"] == expected_model for row in records if row["model_call_status"] == "SUCCESS"),
        "same_frozen_budget": pre["model_config"]["model"] == expected_model and config["model"]["max_calls_per_link_condition"] == 1 and config["model"]["max_refinement_rounds"] == 0,
        "prompt_templates_unchanged": prompt_hashes == config["prompt_freeze"]["sha256"] == pre["prompt_hashes"],
        "requests_exist_and_match_shared_inputs": requests_exist and same_input,
        "method_prompt_only_difference": requests_exist and all(requests[(link, "STRUCTURED_QWEN")]["system"] != requests[(link, "DIRECT_QWEN")]["system"] for link in config["links"]),
        "responses_preserved": response_hashes and all((root / link / condition / "call_record.json").is_file() and (root / link / condition / "full_response.json").is_file() for link, condition in expected),
        "generator_gt_isolation": no_gt_text and all(load(root / link / "input_parity.json")["gt_in_generator"] is False for link in config["links"]),
        "scaffold_parity": all(row.get("scaffold_trace", {}).get("frozen_scaffold_preservation") == "EXECUTED" for row in records if row["status"] == "EVALUATED"),
        "development_denominator": all(row["requested_configuration_count"] == 96 and (row["configuration_count"] == 96 if row["status"] == "EVALUATED" else True) for row in records),
        "process_accounting": failures["attempted_runs"] == 6 and len(failures["rows"]) == 6 and failures["result_conditioned_retries"] == 0,
        "structured_dispatch_trace": all(row.get("compiler_dispatch", {}).get("planned_family") == row.get("compiler_dispatch", {}).get("executed_family") and row.get("compiler_dispatch", {}).get("schema_consumed") == load(root / row["link"] / row["method"] / "structured_ir.json")["schema"] for row in records if row["method"] == "STRUCTURED_QWEN" and row["status"] == "EVALUATED"),
        "direct_code_trace": all(row.get("generated_code_sha256") and row.get("compiler_dispatch", {}).get("executed_family") == "direct_vlm_body" for row in records if row["method"] == "DIRECT_QWEN" and row["status"] == "EVALUATED"),
        "no_overall_score": deltas["no_overall_score"] is True and "overall_score" not in deltas and all("overall_score" not in row for row in table),
        "descriptive_denominators_explicit": deltas["aggregate"]["input_tokens"]["paired_link_count"] == 3 and deltas["aggregate"]["final_voxel_iou"]["paired_link_count"] == sum(row["paired_evaluable"] for row in deltas["per_link"]),
        "artifact_hashes_match": all((ROOT / item["path"]).is_file() and sha(ROOT / item["path"]) == item["sha256"] for item in artifacts),
        "claim_ledger_pass": claim_audit["status"] == "PASS" and not claim_audit["hard_claims_with_noncomputed_evidence"],
        "formal_holdout_untouched": lock["accessed"] is False and lock["evaluation_count"] == 0 and load(root / "holdout_evaluation_log.json")["events"] == [],
        "runner_did_not_self_validate": prior_validation is None or prior_validation.get("schema_version") == "robotcad_a2a_three_link_validation_v1",
    }
    return {"schema_version": "robotcad_a2a_three_link_validation_v1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "failed_checks": [key for key, value in checks.items() if not value], "claim_audit": claim_audit, "missing_required_files": [], "formal_holdout_accessed": False}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--config", required=True); parser.add_argument("--result-dir", required=True); args = parser.parse_args(); result = validate(args.config, args.result_dir); dump(Path(args.result_dir) / "validation.json", result); print(json.dumps(result, indent=2)); return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
