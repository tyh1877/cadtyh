"""Independent W0 technical gate; never promotes a failed FULL witness."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "experiments/try6/results/try6_0_d1_w0"
ARTIFACT = ROOT / "experiments/try6/artifacts/try6_0_d1_w0"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    manifest = read(RESULT / "manifest.json")
    cfg = read(ROOT / "experiments/try6/protocol/try6_0_d1_w0.json")
    d1 = read(ROOT / cfg["frozen_d1_protocol"])
    pre = read(RESULT / "pre_real_manifest.json")
    synthetic = read(RESULT / "calibration/synthetic_cases.json")
    calibration = read(RESULT / "calibration/tolerance_calibration.json")
    canonical = read(RESULT / "construction_paths/canonical_path_decision.json")
    raw = read(ARTIFACT / "real_raw.json")
    tests = read(RESULT / "tests/test_report.json")
    failure = read(RESULT / "failure_accounting.json")
    holdout = read(RESULT / "audit/holdout_audit.json")
    leakage = read(RESULT / "audit/leakage_audit.json")
    checks = {}
    checks["tracked_result_hashes"] = all(sha(RESULT / p) == digest for p, digest in manifest["result_file_sha256"].items())
    checks["raw_artifact_hash"] = sha(ARTIFACT / "real_raw.json") == manifest["real_raw_sha256"]
    checks["prior_frozen_manifests"] = all(
        sha(ROOT / "experiments/try6/results" / name / "manifest.json") == digest
        for name, digest in manifest["prior_manifest_sha256"].items())
    checks["D1_v2_alignment_untouched"] = (sha(ROOT / "experiments/try6/results/try6_0_d1_v2/alignment/raw_alignment.json") ==
        read(ROOT / "experiments/try6/results/try6_0_d1_v2/manifest.json")["result_file_sha256"]["alignment/raw_alignment.json"])
    checks["protocol_and_implementation_hashes"] = (sha(ROOT / "experiments/try6/protocol/try6_0_d1_w0.json") == manifest["protocol_sha256"] and
        sha(ROOT / "experiments/try6/scripts/witness_boolean.py") == manifest["Boolean_helper_sha256"] and
        sha(ROOT / "experiments/try6/evaluation/freecad_d1_w0_real.py") == manifest["real_worker_sha256"])
    checks["synthetic_coverage"] = (synthetic["case_count"] == 8 and synthetic["row_count"] == 48 and
        {x["case"] for x in synthetic["rows"]} == set(cfg["calibration_cases"]) and
        all(x["state"] == x["reopen_state"] and x["solid_count"] == x["reopen_solid_count"] for x in synthetic["rows"]))
    rule = cfg["accounting_tolerance_rule"]
    max_abs = max(x["max_absolute_error_mm3"] for x in synthetic["rows"])
    max_rel = max(x["max_relative_error"] for x in synthetic["rows"])
    expected_abs = max(rule["absolute_floor_mm3"], rule["calibration_multiplier"] * max_abs)
    expected_rel = max(rule["relative_floor"], rule["calibration_multiplier"] * max_rel)
    checks["tolerance_calibrated_before_real"] = (calibration["status"] == "PASS" and
        calibration["BOOLEAN_ACCOUNTING_TOLERANCE"]["absolute_mm3"] == expected_abs and
        calibration["BOOLEAN_ACCOUNTING_TOLERANCE"]["relative"] == expected_rel and
        sha(RESULT / "calibration/tolerance_calibration.json") == pre["calibration_sha256"] and
        calibration["frozen_before_real_witness"])
    checks["KFDE_epsilon_not_changed"] = d1["kfde_numerical_epsilon_mm3"] == 1e-6 and calibration["KFDE_feasibility_epsilon_mm3_unchanged"] == 1e-6
    checks["canonical_path_preregistered"] = canonical["canonical_path"] == "UNION_THEN_SINGLE_CUT" and canonical["selected_before_real_witness"] and sha(RESULT / "construction_paths/canonical_path_decision.json") == pre["canonical_path_sha256"]
    checks["FULL_union_valid"] = len(raw["union_rows"]) == 1 and raw["union_rows"][0]["subset"] == "FULL" and raw["union_rows"][0]["valid"]
    checks["both_paths_repeated"] = len(raw["path_rows"]) == 4 and {(x["path"], x["repeat"]) for x in raw["path_rows"]} == {(p, r) for p in cfg["candidate_paths"] for r in (0, 1)}
    checks["raw_BREP_and_reopen_valid"] = all(x["metrics"]["witness_state"]["is_valid"] and x["BREP_parity"]["pass"] and x["FCStd_parity"]["pass"] for x in raw["path_rows"])
    checks["occupancy_residuals_zero"] = all(x["metrics"]["outside_source_residual_mm3"] == 0 and x["metrics"]["residual_keepout_intersection_mm3"] == 0 for x in raw["path_rows"])
    checks["stable_accounting_failure"] = all(x["metrics"]["removed_consistency_error_mm3"] > x["metrics"]["accounting_limit_mm3"] for x in raw["path_rows"])
    checks["cleanup_non_authoritative"] = all(x["cleanup_status"].startswith("OPTIONAL_CLEANUP_FAILED") and x["metrics"]["witness_state"]["is_valid"] for x in raw["path_rows"])
    checks["fail_closed_denominator"] = raw["status"] == "BOOLEAN_ACCOUNTING_BLOCKED" and raw["failure"] == "FULL" and failure["attempted"] == ["FULL"] and len(failure["not_run_after_fail_closed"]) == 8 and len(failure["requested_subsets"]) == 9
    checks["interface_scaffold_invariant"] = raw["frozen_signatures_invariant"] and raw["C1_source_sha256_after"] == pre["C1_source_sha256"]
    checks["twenty_named_tests_honest"] = tests["total"] >= 20 and tests["passed"] < tests["total"] and tests["checks"]["removed_volume_consistency"] is False and tests["checks"]["exact_nine_subset_execution"] is False
    checks["no_forbidden_evaluation"] = all(value == 0 or value is False for value in leakage.values()) and raw["GT_evaluations"] == raw["VLM_calls"] == raw["final_96_case_mechanics_evaluations"] == 0
    lock_path = ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json"
    lock = read(lock_path)
    checks["holdout_untouched"] = sha(lock_path) == holdout["lock_sha256"] and lock["accessed"] is False and lock["evaluation_count"] == 0
    if not all(checks.values()):
        raise RuntimeError("independent W0 validation failed: " + json.dumps(checks))
    result = {"decision": "BOOLEAN_ACCOUNTING_BLOCKED", "independent_of_runner": True,
        "checks": checks, "passed": len(checks), "total": len(checks),
        "READY_FOR_D1_V3": False, "real_subsets_tested": 1, "real_subsets_requested": 9,
        "scientific_relief_conclusion": None}
    output = RESULT / "audit/independent_validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "passed": result["passed"], "total": result["total"]}))


if __name__ == "__main__":
    main()
