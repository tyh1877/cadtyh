"""Independent validator for the A1 frozen-scaffold development matrix."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/try5A"
sys.path.insert(0, str(HERE / "evaluation"))

from experiment_governance import audit_condition_parity, canonical_hash, dump_json, file_sha256, load_json, validate_claim_ledger  # noqa: E402


REQUIRED = (
    "experiment_config_snapshot.json",
    "case_split.json",
    "condition_parity.json",
    "formal_holdout_lock.json",
    "pre_run_manifest.json",
    "formal_development_started.json",
    "generation_failure_accounting.json",
    "failure_accounting.json",
    "paired_main_table.json",
    "paired_main_table.csv",
    "paired_deltas.json",
    "protection_trace.json",
    "geometry_raw.json",
    "claim_ledger.json",
    "holdout_evaluation_log.json",
    "manifest.json",
)


def validate(result_dir, config_path):
    root = Path(result_dir).resolve(); config_path = Path(config_path).resolve(); missing=[name for name in REQUIRED if not (root/name).is_file()]
    if missing: return {"status":"FAIL","missing_required_files":missing,"checks":{}}
    config=load_json(config_path); snapshot=load_json(root/"experiment_config_snapshot.json"); split=load_json(root/"case_split.json"); parity=load_json(root/"condition_parity.json"); lock=load_json(root/"formal_holdout_lock.json"); pre=load_json(root/"pre_run_manifest.json"); generation=load_json(root/"generation_failure_accounting.json"); accounting=load_json(root/"failure_accounting.json"); table=load_json(root/"paired_main_table.json")["rows"]; traces=load_json(root/"protection_trace.json")["links"]; manifest=load_json(root/"manifest.json"); holdout_log=load_json(root/"holdout_evaluation_log.json"); claims=load_json(root/"claim_ledger.json")["claims"]
    recomputed_parity=audit_condition_parity(config); expected_pairs={(link,condition) for link in config["shared"]["pilot_links"] for condition in config["conditions"]}; actual_pairs={(row["link"],row["condition"]) for row in table}; claim_audit=validate_claim_ledger(root,claims)
    primary_fields=("bicr","attachment_valid","connected_solid_count"); motion_fields=("gcfr","collision_events","intersection_volume_mm3","failed_configuration_ids"); geometry_fields=("final_voxel_iou","final_silhouette_iou","final_normalized_chamfer","final_normalized_hd95","final_bbox_error_mm","final_major_dimension_error_mm")
    checks={
        "config_snapshot_matches":snapshot==config,
        "config_hash_matches_manifest":file_sha256(config_path)==manifest["config_file_sha256"] and canonical_hash(config)==manifest["config_canonical_sha256"],
        "single_variable_parity":parity==recomputed_parity and parity["status"]=="PASS" and parity["observed_differences"]==["mechanical_geometry_policy.preserve_frozen_scaffold"],
        "holdout_lock_matches_protocol":lock["protocol_sha256"]==file_sha256(config_path) and lock["case_ids"]==split["holdout"]["case_ids"] and lock["case_ids_sha256"]==split["holdout"]["case_ids_sha256"] and lock["case_count"]==32,
        "holdout_locked_and_unaccessed":lock["accessed"] is False and lock["evaluation_count"]==0 and holdout_log["events"]==[] and manifest["formal_holdout_accessed"] is False and manifest["formal_holdout_evaluation_count"]==0,
        "development_input_only":pre["development_input"]["configuration_count"]==96 and accounting["formal_holdout"]["accessed"] is False,
        "six_generation_runs_once":generation["requested_runs"]==6 and generation["completed_runs"]==6 and generation["failed_runs"]==0 and generation["retry_count"]==0,
        "six_paired_rows":len(table)==6 and actual_pairs==expected_pairs,
        "primary_metrics_complete":all(all(field in row and row[field] is not None for field in primary_fields) for row in table),
        "motion_metrics_complete":all(all(field in row and row[field] is not None for field in motion_fields) for row in table),
        "geometry_metrics_complete":all(all(field in row and row[field] is not None for field in geometry_fields) for row in table),
        "denominator_preserved":accounting["evaluation"]["denominator_preserved"] and len(accounting["evaluation"]["rows"])==6 and all(row["requested_cases"]==96 and row["completed_cases"]==96 for row in accounting["evaluation"]["rows"]),
        "protection_trace_complete":len(traces)==3 and all(trace["raw_body_signature_equal"] and trace["body_only_equal"] and not trace["final_equal"] and trace["only_effective_difference"]=="frozen_scaffold_preservation_fusion" for trace in traces),
        "declarative_metrics_absent":all(not ({"swept_clearance_preserved","forbidden_fusion_count","virtual_solid_count","meaningless_patch_count"}&set(row)) for row in table),
        "claim_ledger_pass":claim_audit["status"]=="PASS" and not claim_audit["hard_claims_with_noncomputed_evidence"],
        "runner_did_not_self_validate":not (root/"validation.json").exists(),
    }
    return {"schema_version":"robotcad_scaffold_ablation_validation_v1","status":"PASS" if all(checks.values()) else "FAIL","checks":checks,"failed_checks":[key for key,value in checks.items() if not value],"claim_audit":claim_audit,"formal_holdout_accessed":False,"missing_required_files":[]}


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--result-dir",required=True); parser.add_argument("--config",required=True); args=parser.parse_args(); result=validate(args.result_dir,args.config); dump_json(Path(args.result_dir)/"validation.json",result); print(json.dumps(result,indent=2)); return 0 if result["status"]=="PASS" else 1


if __name__=="__main__":
    raise SystemExit(main())
