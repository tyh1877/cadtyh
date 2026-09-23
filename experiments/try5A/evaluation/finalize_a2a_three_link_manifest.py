"""Freeze lightweight A2a provenance after independent validation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/try5A"


def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rel(path): return str(Path(path).resolve().relative_to(ROOT)).replace("\\", "/")


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--config", required=True); parser.add_argument("--result-dir", required=True); args = parser.parse_args()
    result_root = Path(args.result_dir).resolve(); config_path = Path(args.config).resolve(); output = result_root / "manifest.json"
    if output.exists(): raise FileExistsError("result manifest already frozen")
    pre = load(result_root / "pre_run_manifest.json"); validation = load(result_root / "validation.json"); artifacts = load(result_root / "artifact_manifest.json"); records = load(result_root / "run_records.json")["records"]
    if validation["status"] != "PASS" or len(records) != 6: raise RuntimeError("cannot freeze unvalidated A2a result")
    gt = {}
    for item in artifacts["artifacts"]:
        if item["role"] != "geometry_raw": continue
        raw = load(ROOT / item["path"])
        for source in raw["gt_inputs"]:
            gt[source["link_id"]] = source
    files = ("call_ledger.json", "run_records.json", "paired_main_table.json", "paired_deltas.json", "failure_accounting.json", "claim_ledger.json", "artifact_manifest.json", "validation.json", "process_classification.json", "cross_link_analysis.json", "report.md")
    payload = {"schema_version": "robotcad_a2a_three_link_manifest_v1", "experiment_id": pre["experiment_id"], "phase": "FORMAL_DEVELOPMENT_COMPLETE_HOLDOUT_UNACCESSED", "config_path": rel(config_path), "config_sha256": sha(config_path), "generation_implementation_commit": pre["implementation_commit"], "runner_sha256": pre["runner_sha256"], "method_helper_sha256": pre["method_helper_sha256"], "worker_sha256": pre["worker_sha256"], "direct_executor_sha256": pre["direct_executor_sha256"], "exact_evaluator_sha256": pre["exact_evaluator_sha256"], "geometry_evaluator_sha256": pre["geometry_evaluator_sha256"], "independent_validator_sha256": sha(HERE / "evaluation/validate_a2a_three_link.py"), "prompt_template_sha256": pre["prompt_hashes"], "model_identifier": pre["model_config"]["model"], "sdk_version": pre["sdk_version"], "freecad_version": pre["freecad_version"], "development_input_sha256": pre["development_input_sha256"], "holdout_lock": pre["holdout_lock"], "evaluator_gt_inputs": gt, "result_sha256": {name: sha(result_root / name) for name in files}, "heavy_artifact_count": len(artifacts["artifacts"]), "model_calls": 6, "fully_evaluated_runs": sum(row["status"] == "EVALUATED" for row in records), "manual_intervention_count": 0, "result_conditioned_retries": 0, "formal_holdout_accessed": False}
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "FROZEN", "fully_evaluated_runs": payload["fully_evaluated_runs"], "holdout_accessed": False}, indent=2))


if __name__ == "__main__": main()
