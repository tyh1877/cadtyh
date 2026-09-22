"""Independent post-run integrity audit for the A1 L04 paired dry run."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/try5A"
RESULTS = HERE / "results/try5b1_a1_geometry_protection"
ARTIFACTS = HERE / "artifacts/try5b1_a1_geometry_protection/l04_dry_run"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    summary = load(RESULTS / "l04_dry_run_summary.json")
    parity = load(RESULTS / "condition_parity.json")
    integrity = load(RESULTS / "evaluator_integrity.json")
    failures = load(RESULTS / "failure_accounting.json")
    traces = load(RESULTS / "l04_execution_trace.json")
    builds = {}
    jobs = {}
    for condition in ("C1_CONSTRAINED", "C2_UNPROTECTED"):
        worker = load(ARTIFACTS / condition / "generation_result.json")
        builds[condition] = next(item for item in worker["builds"] if item["condition"] == "F2" and item["link_id"] == "L04")
        jobs[condition] = load(ARTIFACTS / condition / "generator_job.json")
    body_hashes = {condition: sha(build["artifact"]["body_stl"]) for condition, build in builds.items()}
    final_hashes = {condition: sha(build["artifact"]["stl"]) for condition, build in builds.items()}
    body_volumes = {condition: build["artifact"]["body_volume_mm3"] for condition, build in builds.items()}
    checks = {
        "baseline_reproduced": load(RESULTS / "baseline_reproduction.json")["status"] == "PASS",
        "condition_parity_pass": parity["status"] == "PASS" and not parity["config_parity"]["unexpected_differences"],
        "raw_proposal_parity_pass": summary["raw_proposal_parity"] == "PASS",
        "both_generation_conditions_completed_once": not failures["failures"] and failures["retry_count"] == 0 and len(failures["completed_generation_conditions"]) == 2,
        "no_runtime_controller_in_jobs": all("mechanical_rejection" not in json.dumps(job) and "rollback_on_failure" not in json.dumps(job) for job in jobs.values()),
        "c1_trace_matches_protocol": traces["C1_CONSTRAINED"]["trace"]["protected_interface_cuts"] == "EXECUTED" and traces["C1_CONSTRAINED"]["trace"]["frozen_scaffold_preservation"] == "EXECUTED",
        "c2_trace_matches_protocol": traces["C2_UNPROTECTED"]["trace"]["protected_interface_cuts"] == "SKIPPED_BY_POLICY" and traces["C2_UNPROTECTED"]["trace"]["frozen_scaffold_preservation"] == "SKIPPED_BY_POLICY",
        "build_export_reopen_pass": all(all(build["artifact"]["reopen"].values()) for build in builds.values()),
        "declarative_metrics_excluded": set(integrity["excluded_from_main_quantitative_analysis"]) == {"swept_clearance_preserved", "forbidden_fusion_count", "virtual_solid_count", "meaningless_patch_count"},
        "formal_holdout_not_accessed": not (HERE / "results/try5b1_a1_development/holdout_evaluated.lock").exists(),
    }
    findings = {
        "l04_protected_cut_effective_geometry_delta": False,
        "evidence": {
            "body_only_sha256": body_hashes,
            "body_only_volume_mm3": body_volumes,
            "body_only_hashes_equal": len(set(body_hashes.values())) == 1,
            "body_only_volumes_equal": len(set(body_volumes.values())) == 1,
            "final_link_sha256": final_hashes,
            "final_link_hashes_differ": len(set(final_hashes.values())) == 2,
        },
        "interpretation": "For L04 the invoked proximal protected cut is a geometric no-op; the observed condition difference is driven primarily by scaffold preservation. This is a disclosed dry-run limitation, not a failed parity check.",
    }
    payload = {
        "schema_version": "robotcad_a1_dry_run_integrity_review_v1",
        "status": "PASS_WITH_DISCLOSED_LIMITATIONS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "findings": findings,
        "formal_three_link_suitability": "CONDITIONAL_GO",
        "conditions_before_formal": [
            "Record per-link pre/post-operation volume or shape-hash deltas so EXECUTED is distinguished from an effective geometry change.",
            "Interpret A1 as the combined mechanical-geometry-protection bundle, not as an estimate of each individual cut.",
            "Use body-only scores as paired diagnostics against full-link GT, not as absolute body-segmentation accuracy.",
            "Rename the reused evaluator field holdout_samples to sample_count before formal execution to avoid a provenance-label ambiguity."
        ],
        "formal_three_link_run_executed": False,
    }
    (RESULTS / "post_run_integrity_review.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if payload["status"] == "PASS_WITH_DISCLOSED_LIMITATIONS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
