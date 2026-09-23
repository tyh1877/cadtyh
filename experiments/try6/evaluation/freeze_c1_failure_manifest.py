"""Freeze provenance for a terminal C1 representation failure."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/"experiments/try6"


def load(path):return json.loads(Path(path).read_text(encoding="utf-8"))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--config",required=True);args=parser.parse_args()
    root=HERE/"results/try6_0_c1";target=root/"manifest.json"
    if target.exists():raise FileExistsError("C1 manifest already frozen")
    pre=load(root/"pre_run_manifest.json");validation=load(root/"validation.json");decision=load(root/"decision.json")
    if validation["status"]!="PASS" or decision["decision"]!="REPRESENTATION_FAILURE":raise RuntimeError("unvalidated C1 result")
    names=("protocol.json","input_hashes.json","c0_baseline.json","camera_or_view_registration.json","infrastructure_smoke.json","pre_run_manifest.json","vlm_request_manifest.json","vlm_call_record.json","vlm_raw_response.txt","vlm_full_response.json","vlm_failure.json","representation_failure_audit.json","decision.json","failure_accounting.json","process_metrics.json","leakage_audit.json","dataflow_audit.json","claim_ledger.json","execution_incidents.json","validation.json","report.md")
    smoke=HERE/"artifacts/try6_0_c1/smoke/point_0"
    payload={"schema_version":"robotcad_try6_c1_manifest_v1","experiment_id":"try6_0_c1_l04_kfdg_metric_grounding","phase":"ONE_FORMAL_ATTEMPT_TERMINATED_AT_KFDG_SCHEMA","generation_implementation_commit":pre["implementation_commit"],"protocol_path":"experiments/try6/protocol/try6_0_c1.json","protocol_sha256":sha(args.config),"schema_sha256":pre["kfdg_schema_sha256"],"response_schema_sha256":pre["vlm_response_schema_sha256"],"prompt_sha256":pre["prompt_sha256"],"model_requested":pre["model_config"]["model"],"model_returned":load(root/"vlm_call_record.json")["returned_model"],"freecad_version":pre["freecad_version"],"python_environment":pre["python_executable"],"solver_config_sha256":pre["solver_config_sha256"],"geometry_evaluator_sha256":pre["geometry_evaluator_sha256"],"exact_evaluator_sha256":pre["exact_evaluator_sha256"],"independent_failure_validator_sha256":sha(HERE/"evaluation/validate_c1.py"),"c0_exact_source_sha256":load(root/"c0_baseline.json")["source_sha256"],"lightweight_result_sha256":{name:sha(root/name) for name in names},"nonformal_smoke_cad":{"path":"experiments/try6/artifacts/try6_0_c1/smoke/point_0/final.FCStd","sha256":sha(smoke/"final.FCStd"),"regeneration":".venv/Scripts/python.exe experiments/try6/scripts/smoke_c1_builder.py"},"formal_c1_cad_generated":False,"solver_evaluations":0,"gt_evaluations":0,"formal_holdout_accessed":False}
    target.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"FROZEN","decision":"REPRESENTATION_FAILURE","formal_holdout_accessed":False},indent=2))


if __name__=="__main__":main()
