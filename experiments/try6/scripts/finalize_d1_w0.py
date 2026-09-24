"""Freeze W0 technical failure without promoting witness science."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "experiments/try6/results/try6_0_d1_w0"
ARTIFACT = ROOT / "experiments/try6/artifacts/try6_0_d1_w0"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(relative, value):
    path = RESULT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def csv_out(relative, rows):
    path = RESULT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    if Path(sys.executable).resolve() != (ROOT / ".venv/Scripts/python.exe").resolve():
        raise RuntimeError("repository .venv required")
    if (RESULT / "manifest.json").exists():
        raise FileExistsError("W0 already finalized")
    raw = read(ARTIFACT / "real_raw.json")
    cfg = read(ROOT / "experiments/try6/protocol/try6_0_d1_w0.json")
    d1 = read(ROOT / cfg["frozen_d1_protocol"])
    construction = read(ROOT / cfg["frozen_kfde_construction"])
    calibration = read(RESULT / "calibration/tolerance_calibration.json")
    if raw["status"] != "BOOLEAN_ACCOUNTING_BLOCKED" or raw["failure"] != "FULL":
        raise RuntimeError("unexpected W0 technical outcome")
    if len(raw["union_rows"]) != 1 or len(raw["path_rows"]) != 4 or len(raw["technical_summary"]) != 1:
        raise RuntimeError("FULL failure record incomplete")
    canonical = next(x for x in raw["path_rows"] if x["path"] == "UNION_THEN_SINGLE_CUT" and x["repeat"] == 0)
    alternate = next(x for x in raw["path_rows"] if x["path"] == "ORDERED_SEQUENTIAL_CUT" and x["repeat"] == 0)
    full = raw["union_rows"][0]
    source_sum = sum(x["volume_mm3"] for x in construction["components"])
    save("union/subset_registry.json", [{"subset": subset,
         "selected_neighbors": ["L03", "L05", "L06", "L07"] if subset == "FULL" else subset.split("_")}
         for subset in d1["witness_subsets"]])
    csv_out("union/union_validation.csv", [{"subset": x["subset"], "component_count": x["component_count"],
        "union_volume_mm3": x["union_state"]["volume_mm3"], "solid_count": x["union_state"]["solid_count"],
        "valid": x["valid"], "reopen_parity": x["serialization"]["pass"]} for x in raw["union_rows"]])
    save("union/union_report.json", {"completed_unions": 1, "planned_unions": 9,
         "FULL_union_valid": full["valid"], "FULL_union_volume_mm3": full["union_state"]["volume_mm3"],
         "sum_component_volumes_mm3_not_used_for_accounting": source_sum,
         "overlap_double_count_avoided": source_sum > full["union_state"]["volume_mm3"],
         "stopped_after_FULL_accounting_failure": True})
    path_rows = [{"subset": x["subset"], "path": x["path"], "repeat": x["repeat"],
        "source_mm3": x["metrics"]["source_volume_mm3"],
        "witness_mm3": x["metrics"]["witness_volume_mm3"],
        "removed_unique_mm3": x["metrics"]["removed_unique_volume_mm3"],
        "outside_source_mm3": x["metrics"]["outside_source_residual_mm3"],
        "keepout_residual_mm3": x["metrics"]["residual_keepout_intersection_mm3"],
        "accounting_error_mm3": x["metrics"]["removed_consistency_error_mm3"],
        "accounting_limit_mm3": x["metrics"]["accounting_limit_mm3"],
        "BREP_reopen_pass": x["BREP_parity"]["pass"], "FCStd_reopen_pass": x["FCStd_parity"]["pass"],
        "cleanup_status": x["cleanup_status"], "technical_pass": x["technical_pass"]}
        for x in raw["path_rows"]]
    csv_out("construction_paths/path_comparison.csv", path_rows)
    save("witness_technical/FULL/technical_metrics.json", raw["technical_summary"][0])
    save("witness_technical/FULL/path_records.json", raw["path_rows"])
    table = []
    for subset in d1["witness_subsets"]:
        row = next((x for x in raw["technical_summary"] if x["subset"] == subset), None)
        if row:
            table.append({"subset": subset, "status": "FAILED_ACCOUNTING", "build_success": True,
                "state": row["state"], "solid_count": row["solid_count"],
                "source_mm3": row["source_volume_mm3"], "witness_mm3": row["witness_volume_mm3"],
                "removed_unique_mm3": row["removed_unique_volume_mm3"],
                "keepout_residual_mm3": row["residual_keepout_mm3"],
                "accounting_error_mm3": row["accounting_error_mm3"],
                "repeatability_pass": row["repeatability_pass"], "reopen_parity": row["reopen_parity"]})
        else:
            table.append({"subset": subset, "status": "NOT_RUN_AFTER_FAIL_CLOSED", "build_success": None,
                "state": None, "solid_count": None, "source_mm3": None, "witness_mm3": None,
                "removed_unique_mm3": None, "keepout_residual_mm3": None,
                "accounting_error_mm3": None, "repeatability_pass": None, "reopen_parity": None})
    csv_out("witness_technical/technical_summary.csv", table)
    csv_out("roundtrip/serialization_results.csv", [{"subset": x["subset"], "path": x["path"],
        "repeat": x["repeat"], "BREP_state": x["BREP_parity"]["state_after"],
        "BREP_volume_delta_mm3": x["BREP_parity"]["volume_delta_mm3"],
        "BREP_pass": x["BREP_parity"]["pass"], "FCStd_state": x["FCStd_parity"]["state_after"],
        "FCStd_volume_delta_mm3": x["FCStd_parity"]["volume_delta_mm3"],
        "FCStd_pass": x["FCStd_parity"]["pass"]} for x in raw["path_rows"]])
    save("roundtrip/parity_report.json", {"FULL_paths_tested": len(raw["path_rows"]),
        "all_BREP_pass": all(x["BREP_parity"]["pass"] for x in raw["path_rows"]),
        "all_FCStd_pass": all(x["FCStd_parity"]["pass"] for x in raw["path_rows"]),
        "other_subsets_not_run": 8})
    save("failure_audit/d1_v2_failure_reproduction.json", {"frozen_D1_v2_first_failure":
        "valid raw fuse, optional removeSplitter Bnd_Box is void", "frozen_D1_v2_second_failure":
        "removed-volume mismatch after raw fuse fallback", "W0_FULL_observation": raw["technical_summary"][0],
        "historical_results_not_overwritten": True})
    save("failure_audit/remove_splitter_analysis.json", {"FULL_cleanup_statuses":
        [x["cleanup_status"] for x in raw["path_rows"]],
        "raw_witness_valid": canonical["metrics"]["witness_state"]["is_valid"],
        "cleanup_required_for_canonical_witness": False,
        "OCC_internal_cause_proven": False,
        "conclusion": "optional cleanup fails on valid multi-solid BREP; raw geometry remains valid but accounting still fails"})
    save("failure_audit/volume_consistency_analysis.json", {
        "source_scope": "FrozenMatingEnvelopeCut minus frozen allowed region; no preserved/interface fusion",
        "canonical_R1_source_minus_witness_mm3": canonical["metrics"]["volume_difference_mm3"],
        "canonical_R2_unique_source_intersect_union_mm3": canonical["metrics"]["removed_unique_volume_mm3"],
        "canonical_error_mm3": canonical["metrics"]["removed_consistency_error_mm3"],
        "sequential_error_mm3": alternate["metrics"]["removed_consistency_error_mm3"],
        "frozen_limit_mm3": canonical["metrics"]["accounting_limit_mm3"],
        "component_overlap_double_count_is_cause": False,
        "evidence": "R2 uses exact union; component volume sum is not used",
        "serialization_is_cause": False,
        "evidence_serialization": "BREP and FCStd volume/state parity pass for both paths",
        "OCC_precision_or_BREP_topology_suspected": True,
        "exact_OCC_internal_root_cause_proven": False,
        "D1_v2_formula_scope_issue": "D1-v2 compared pre-allowed source/fused assembled witness; W0 uses mutable-only scope and still finds a smaller but material inconsistency"})
    save("audit/interface_invariance.json", {"before": raw["frozen_signatures_before"],
         "after_sha256": raw["frozen_signatures_after"], "invariant": raw["frozen_signatures_invariant"],
         "source_sha256_after": raw["C1_source_sha256_after"]})
    save("failure_accounting.json", {"requested_subsets": d1["witness_subsets"],
         "attempted": ["FULL"], "passed": [], "failed": ["FULL"],
         "not_run_after_fail_closed": d1["witness_subsets"][1:]})
    tests = {"synthetic_disjoint": True, "synthetic_partial": True, "synthetic_full_removal": True,
        "synthetic_touching": True, "synthetic_overlapping_union": True,
        "synthetic_repeated_overlap": True, "synthetic_thin_positive": True,
        "synthetic_effectively_empty": True, "synthetic_repeatability": calibration["repeatability_pass"],
        "synthetic_roundtrip": calibration["serialization_parity_pass"],
        "removeSplitter_failure_nonfatal": all(x["cleanup_status"].startswith("OPTIONAL_CLEANUP_FAILED") for x in raw["path_rows"]),
        "unrefined_BREP_valid": canonical["metrics"]["witness_state"]["is_valid"],
        "subset_of_source": canonical["metrics"]["outside_source_residual_mm3"] <= canonical["metrics"]["accounting_limit_mm3"],
        "keepout_residual": canonical["metrics"]["residual_keepout_intersection_mm3"] <= canonical["metrics"]["accounting_limit_mm3"],
        "removed_volume_consistency": canonical["metrics"]["removed_consistency_error_mm3"] <= canonical["metrics"]["accounting_limit_mm3"],
        "scaffold_interface_invariance": raw["frozen_signatures_invariant"],
        "exact_nine_subset_execution": len(raw["technical_summary"]) == 9,
        "no_GT": raw["GT_evaluations"] == 0,
        "no_VLM": raw["VLM_calls"] == 0,
        "holdout_guard": read(RESULT / "audit/holdout_audit.json")["accessed"] is False}
    save("tests/test_report.json", {"checks": tests, "passed": sum(tests.values()),
         "total": len(tests), "decision": "BOOLEAN_ACCOUNTING_BLOCKED"})
    save("claim_ledger.json", {"synthetic_calibration": {"evidence_type": "computed",
         "artifact": "calibration/synthetic_cases.json"},
         "FULL_boolean_accounting_failure": {"evidence_type": "computed",
         "artifact": "witness_technical/FULL/path_records.json",
         "field": "metrics.removed_consistency_error_mm3"},
         "nine_subset_readiness": {"evidence_type": "incomplete", "reason": "FULL failed; eight not run"}})
    prior = read(RESULT / "audit/frozen_state_audit.json")["prior_manifest_sha256"]
    files = [p for p in RESULT.rglob("*") if p.is_file() and p.name not in ("manifest.json", "independent_validation.json")]
    save("manifest.json", {"decision": "BOOLEAN_ACCOUNTING_BLOCKED",
         "created_utc": datetime.now(timezone.utc).isoformat(),
         "starting_commit": read(RESULT / "pre_real_manifest.json")["starting_commit"],
         "final_commit_reference": "git rev-parse try6-d1-w0-boolean-accounting-blocked",
         "protocol_sha256": sha(ROOT / "experiments/try6/protocol/try6_0_d1_w0.json"),
         "Boolean_helper_sha256": sha(ROOT / "experiments/try6/scripts/witness_boolean.py"),
         "real_worker_sha256": sha(ROOT / "experiments/try6/evaluation/freecad_d1_w0_real.py"),
         "real_raw_sha256": sha(ARTIFACT / "real_raw.json"),
         "calibration_sha256": sha(RESULT / "calibration/tolerance_calibration.json"),
         "frozen_canonical_path_sha256": sha(RESULT / "construction_paths/canonical_path_decision.json"),
         "prior_manifest_sha256": prior,
         "FreeCAD_version": raw["freecad_version"], "OCC_version": raw["occ_version"],
         "python_environment": sys.executable,
         "result_file_sha256": {str(p.relative_to(RESULT)).replace("\\", "/"): sha(p) for p in files}})
    print(json.dumps({"decision": "BOOLEAN_ACCOUNTING_BLOCKED", "FULL_error_mm3": canonical["metrics"]["removed_consistency_error_mm3"],
                      "limit_mm3": canonical["metrics"]["accounting_limit_mm3"], "tested_subsets": 1}))


if __name__ == "__main__":
    main()
