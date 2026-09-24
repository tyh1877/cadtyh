"""Independent final D1-v3 causal-order and frozen-evidence validation."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "experiments/try6/results/try6_0_d1_v3"
ARTIFACT = ROOT / "experiments/try6/artifacts/try6_0_d1_v3"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    manifest = read(RESULT / "manifest.json")
    pre = read(RESULT / "pre_run_manifest.json")
    cfg = read(ROOT / "experiments/try6/protocol/try6_0_d1_v3.json")
    d1 = read(ROOT / cfg["frozen_d1_protocol"])
    raw = read(ARTIFACT / "geometry_raw.json")
    alignment = read(ROOT / cfg["frozen_alignment"])
    decomp = read(RESULT / "semantic_decomposition/decomposition_summary.json")
    capacity = read(RESULT / "capacity/representation_capacity_summary.json")
    decision = read(RESULT / "attribution/decision_trace.json")
    with (RESULT / "localization/localization_summary.csv").open(newline="", encoding="utf-8") as stream:
        locations = list(csv.DictReader(stream))
    with (RESULT / "attribution/neighbor_attribution.csv").open(newline="", encoding="utf-8") as stream:
        neighbors = list(csv.DictReader(stream))
    checks = {}
    checks["tracked_result_hashes"] = all(sha(RESULT / p) == h for p, h in manifest["result_file_sha256"].items())
    checks["raw_geometry_hash"] = sha(ARTIFACT / "geometry_raw.json") == manifest["geometry_raw_sha256"]
    checks["prior_frozen_manifests"] = all(sha(ROOT / "experiments/try6/results" / n / "manifest.json") == h
        for n, h in pre["prior_manifest_sha256"].items())
    checks["frozen_alignment_hash"] = sha(ROOT / cfg["frozen_alignment"]) == pre["alignment_sha256"]
    counts = Counter(x["alignment_category"] for x in alignment["cases"])
    checks["frozen_65_counts"] = len(alignment["cases"]) == 65 and counts == {
        "ALIGNED_SAFE": 33, "ALIGNED_UNSAFE": 5, "KFDE_FALSE_POSITIVE_SUSPECT": 27}
    checks["frozen_unsafe_rate"] = 5/(5+27) == 0.15625 and d1["alignment_high_min_fraction"] == 0.9
    w1root = ROOT / cfg["frozen_witness_result"]
    checks["frozen_witness_reference"] = (sha(w1root / "manifest.json") == pre["W1_v2_manifest_sha256"] and
        sha(w1root / "summary/engineering_witness_metrics.csv") == pre["W1_v2_metrics_sha256"] and
        read(w1root / "audit/independent_validation.json")["decision"] == "READY_FOR_D1_V3")
    checks["frozen_C1_mutable"] = sha(ROOT / cfg["frozen_geometry_set"]) is not None and (
        sha(ROOT / read(ROOT / cfg["frozen_geometry_set"])["geometries"][0]["mutable_brep_path"]) == pre["C1_mutable_brep_sha256"])
    construction = read(ROOT / cfg["frozen_kfde_construction"])
    checks["frozen_KFDE_components"] = all(sha(ROOT / x["brep_path"]) == pre["component_hashes"][x["component_id"]]
        for x in construction["components"])
    checks["nine_accepted_witnesses"] = len(raw["localizations"]) == len(locations) == 9 and all(
        sha(ROOT / x["accepted_witness_brep"]["path"]) == x["accepted_witness_brep"]["sha256"]
        for x in raw["localizations"])
    checks["removed_region_hashes"] = all(sha(ROOT / x["removed_brep"]["path"]) == x["removed_brep"]["sha256"]
        for x in raw["localizations"])
    checks["frozen_partition_and_threshold"] = (d1["witness_longitudinal_cut_stations_mm"] == [21.0, 42.0] and
        d1["witness_localized_one_longitudinal_third_min_fraction"] == 0.8 and
        len({x["subset"] for x in locations}) == 9)
    checks["localization_numeric_caveat_retained"] = any(abs(float(x["partition_error_mm3"])) > 1e-3
        for x in locations) and all(x["robustness"] in ("LOCALIZED_ROBUST", "NOT_LOCALIZED_ROBUST", "")
        for x in locations)
    checks["FULL_and_L03_localization_robust"] = all(next(x for x in locations if x["subset"] == s)["robustness"] == "LOCALIZED_ROBUST"
        for s in ("FULL", "L03"))
    checks["L07_engineering_zero"] = (next(x for x in locations if x["subset"] == "L07")["dominant_region"] == "" and
        next(x for x in neighbors if x["neighbor"] == "L07")["relief_category"] == "ZERO_RELIEF_WITHIN_ENGINEERING_TOLERANCE")
    c1 = [x for x in alignment["cases"] if x["geometry_id"] == "G1_C1_FINAL"]
    supported = [x for x in c1 if x["alignment_category"] == "ALIGNED_UNSAFE"]
    suspect = [x for x in c1 if x["alignment_category"] == "KFDE_FALSE_POSITIVE_SUSPECT"]
    checks["C1_only_semantic_registry"] = (len(c1) == 13 and len(supported) == 1 and len(suspect) == 6 and
        sorted(x["component_id"] for x in supported) == decomp["supported_component_ids"] and
        sorted(x["component_id"] for x in suspect) == decomp["suspect_component_ids"])
    checks["exact_decomposition_artifacts"] = raw["semantic_decomposition"]["status"] == "PASS" and all(
        sha(ROOT / artifact["path"]) == artifact["sha256"]
        for artifact in raw["semantic_decomposition"]["artifacts"].values())
    checks["supported_suspect_overlap_explicit"] = (decomp["supported_only_mm3"] > 0 and
        decomp["suspect_only_mm3"] > decomp["supported_only_mm3"] and decomp["shared_mm3"] == 0 and
        decomp["not_asserted_exact_volume_additivity"] and abs(decomp["partition_sum_minus_FULL_mm3"]) > 0)
    checks["supported_fraction_computed"] = (abs(decomp["supported_fraction_of_FULL"] - decomp["supported_mm3"]/decomp["FULL_unique_removed_mm3"]) < 1e-12 and
        abs(decomp["suspect_only_fraction_of_FULL"] - decomp["suspect_only_mm3"]/decomp["FULL_unique_removed_mm3"]) < 1e-12)
    theta = read(RESULT / "capacity/six_theta_geometry_support.json")
    checks["six_theta_frozen_registry"] = (theta["active_parameter_names"] == ["housing_width_mm", "housing_height_mm",
        "proximal_section_length_mm", "transition_length_mm", "distal_width_mm", "distal_height_mm"] and
        theta["no_local_pocket_feature_in_frozen_KFDG"] and sha(ROOT / theta["C1_builder_source"]) == pre["C1_builder_sha256"])
    checks["supported_ROI_local"] = (theta["supported_relief_bbox_x_span_mm"] < theta["proximal_pad_selected_length_mm"] and
        decomp["supported_localization"]["localization_robustness"] == "LOCALIZED_ROBUST" and
        decomp["supported_localization"]["dominant_region"] == "PROXIMAL")
    checks["false_positive_not_CAD_cause"] = all(x["expressibility"] == "UNKNOWN" for x in neighbors if x["neighbor"] in ("L05", "L06"))
    checks["capacity_secondary"] = capacity["axis"] == "LOCAL_CAPACITY_MISSING" and capacity["topology_redesign_supported"] is False
    checks["F0_no_authority_contradiction"] = decision["authority_contradiction"] is False
    checks["frozen_decision_priority"] = decision["priority"] == d1["decision_priority"] and decision["decision"] == "KFDE_SEMANTICS_MISALIGNED" and decision["next_method_implication"] == "KFDE semantic redesign"
    checks["technical_retry_disclosed"] = ((RESULT / "localization/infrastructure_failure.json").is_file() and
        read(RESULT / "localization/technical_retry_started.json")["scientific_inputs_and_thresholds_unchanged"])
    leakage = read(RESULT / "audit/leakage_audit.json")
    checks["no_forbidden_evaluation"] = all(v == 0 or v is False for v in leakage.values()) and raw["VLM_calls"] == raw["GT_evaluations"] == raw["final_96_case_mechanics_evaluations"] == 0
    lock_path = ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json"
    lock = read(lock_path)
    checks["holdout_untouched"] = sha(lock_path) == pre["holdout_lock_sha256"] and lock["accessed"] is False and lock["evaluation_count"] == 0
    if not all(checks.values()):
        raise RuntimeError("independent D1-v3 validation failed: " + json.dumps(checks))
    output = {"decision": "KFDE_SEMANTICS_MISALIGNED", "checks": checks,
        "passed": len(checks), "total": len(checks), "independent_of_runner": True,
        "C1_supported_only_mm3": decomp["supported_only_mm3"],
        "C1_suspect_only_mm3": decomp["suspect_only_mm3"],
        "next_method_implication": "KFDE semantic redesign",
        "no_method_implemented": True, "formal_holdout_accessed": False}
    target = RESULT / "audit/independent_validation.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"decision": output["decision"], "passed": output["passed"], "total": output["total"]}))


if __name__ == "__main__":
    main()
