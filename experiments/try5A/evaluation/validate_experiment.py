"""Independent validator for formal RobotCAD experiment result bundles."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from experiment_governance import (  # noqa: E402
    audit_condition_parity,
    canonical_hash,
    dump_json,
    file_sha256,
    load_json,
    validate_claim_ledger,
)


REQUIRED_FILES = (
    "experiment_config_snapshot.json",
    "case_split.json",
    "condition_parity.json",
    "failure_accounting.json",
    "holdout_evaluation_log.json",
    "claim_ledger.json",
    "manifest.json",
)


def validate_bundle(result_root: str | Path, config_path: str | Path) -> dict:
    root = Path(result_root)
    config_file = Path(config_path)
    missing = [name for name in REQUIRED_FILES if not (root / name).is_file()]
    if missing:
        return {"status": "FAIL", "missing_required_files": missing, "checks": {}}

    config = load_json(config_file)
    snapshot = load_json(root / "experiment_config_snapshot.json")
    split = load_json(root / "case_split.json")
    stored_parity = load_json(root / "condition_parity.json")
    recomputed_parity = audit_condition_parity(config)
    accounting = load_json(root / "failure_accounting.json")
    holdout_log = load_json(root / "holdout_evaluation_log.json")
    claims = load_json(root / "claim_ledger.json")["claims"]
    manifest = load_json(root / "manifest.json")

    development = split["development"]["case_ids"]
    holdout = split["holdout"]["case_ids"]
    split_counts_ok = (
        len(development) == config["shared"]["split"]["development_count"]
        and len(holdout) == config["shared"]["split"]["holdout_count"]
        and not (set(development) & set(holdout))
        and len(set(development) | set(holdout)) == split["source_case_count"]
    )

    conditions = set(config["conditions"])
    accounting_rows = {row["condition"]: row for row in accounting["conditions"]}
    denominator_ok = set(accounting_rows) == conditions and all(
        row["requested_cases"] == row["completed_cases"] + row["failed_cases"]
        and row["requested_cases"] == split["source_case_count"]
        for row in accounting_rows.values()
    )

    limit = split["holdout"]["evaluation_limit_per_condition"]
    counts = {condition: 0 for condition in conditions}
    for event in holdout_log["events"]:
        if event["condition"] in counts:
            counts[event["condition"]] += 1
    one_shot_holdout = set(counts) == conditions and all(count == limit for count in counts.values())
    post_holdout_tuning = any(event.get("followed_by_tuning", False) for event in holdout_log["events"])

    claim_audit = validate_claim_ledger(root, claims)
    checks = {
        "config_snapshot_matches": snapshot == config,
        "config_file_sha256_matches_manifest": manifest.get("config_file_sha256") == file_sha256(config_file),
        "config_canonical_sha256_matches_manifest": manifest.get("config_canonical_sha256") == canonical_hash(config),
        "case_split_sha256_matches_manifest": manifest.get("case_split_sha256") == split.get("split_sha256"),
        "case_split_counts_and_disjointness": split_counts_ok,
        "stored_parity_pass": stored_parity.get("status") == "PASS",
        "parity_recomputed_pass": recomputed_parity.get("status") == "PASS",
        "parity_reproducible": stored_parity == recomputed_parity,
        "denominator_preserved": denominator_ok,
        "holdout_evaluated_exactly_once_per_condition": one_shot_holdout,
        "no_post_holdout_tuning": not post_holdout_tuning,
        "hard_claims_have_direct_computed_evidence": not claim_audit["hard_claims_with_noncomputed_evidence"],
        "claim_ledger_pass": claim_audit["status"] == "PASS",
    }
    return {
        "schema_version": "robotcad_independent_validation_v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "validator": str(Path(__file__).relative_to(Path(__file__).resolve().parents[3])).replace("\\", "/"),
        "validator_sha256": file_sha256(__file__),
        "result_root": str(root),
        "checks": checks,
        "holdout_evaluation_counts": counts,
        "claim_audit": claim_audit,
        "missing_required_files": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = validate_bundle(args.result_dir, args.config)
    output = Path(args.output) if args.output else Path(args.result_dir) / "validation.json"
    dump_json(output, result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
