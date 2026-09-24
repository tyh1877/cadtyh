"""Independent W1-v2 rule/occupancy/category audit, after the runner exits."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "experiments/try6/results/try6_0_d1_w1_v2"
ARTIFACT = ROOT / "experiments/try6/artifacts/try6_0_d1_w1_v2"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def category(r):
    return "SMALL_RELIEF" if r <= 0.05 else "MODERATE_RELIEF" if r <= 0.15 else "LARGE_RELIEF"


def main():
    manifest = read(RESULT / "manifest.json")
    pre = read(RESULT / "pre_run_manifest.json")
    cfg = read(ROOT / "experiments/try6/protocol/try6_0_d1_w1_v2.json")
    d1 = read(ROOT / cfg["frozen_d1_protocol"])
    rule = read(RESULT / "zero_rule/rule.json")
    synthetic = read(RESULT / "zero_rule/synthetic_tests.json")
    raw = read(ARTIFACT / "raw.json")
    with (RESULT / "summary/engineering_witness_metrics.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    with (RESULT / "summary/raw_vs_normalized_relief.csv").open(newline="", encoding="utf-8") as stream:
        measurements = list(csv.DictReader(stream))
    comparison = read(RESULT / "summary/w1_comparison.json")
    fail = read(RESULT / "failure_accounting.json")
    checks = {}
    checks["tracked_result_hashes"] = all(sha(RESULT / p) == h for p, h in manifest["result_file_sha256"].items())
    checks["raw_artifact_hash"] = sha(ARTIFACT / "raw.json") == manifest["raw_artifact_sha256"]
    checks["frozen_prior_manifests"] = all(sha(ROOT / "experiments/try6/results" / n / "manifest.json") == h
        for n, h in pre["prior_manifest_sha256"].items())
    d1v2 = ROOT / "experiments/try6/results/try6_0_d1_v2"
    checks["frozen_65_rows"] = sha(d1v2 / "alignment/raw_alignment.json") == read(d1v2 / "manifest.json")["result_file_sha256"]["alignment/raw_alignment.json"]
    checks["protocol_rule_hashes"] = sha(ROOT / "experiments/try6/protocol/try6_0_d1_w1_v2.json") == pre["protocol_sha256"] and sha(RESULT / "zero_rule/rule.json") == pre["zero_rule_sha256"]
    checks["frozen_worker_paths"] = (sha(ROOT / "experiments/try6/evaluation/freecad_d1_w1_real.py") == pre["W1_worker_sha256"] and
        sha(ROOT / "experiments/try6/scripts/witness_boolean.py") == pre["W0_Boolean_helper_sha256"] and
        cfg["frozen_paths"] == ["UNION_THEN_SINGLE_CUT", "ORDERED_SEQUENTIAL_CUT"])
    cal_path = ROOT / cfg["frozen_w0_calibration"]
    cal = read(cal_path)
    checks["epsilon_abs_provenance"] = (sha(cal_path) == pre["epsilon_abs_source_sha256"] and
        rule["epsilon_abs_mm3"] == cal["BOOLEAN_ACCOUNTING_TOLERANCE"]["absolute_mm3"] == 1e-8)
    checks["epsilon_rel_preregistered"] = rule["epsilon_rel"] == pre["epsilon_rel"] == 1e-6 and rule["inclusive_negative_boundary"] and not rule["subset_specific_exceptions"]
    checks["synthetic_boundary_tests"] = (synthetic["status"] == "PASS" and synthetic["unittest_count"] == 9 and
        synthetic["cases"]["negative_exact_boundary"]["normalized_removed_volume_mm3"] == 0 and
        synthetic["cases"]["negative_outside"]["status"] == "WITNESS_NUMERICALLY_UNSTABLE" and
        synthetic["cases"]["tiny_positive"]["normalized_removed_volume_mm3"] > 0 and
        synthetic["cases"]["cross_five"]["category_status"] == "RELIEF_CATEGORY_NUMERICALLY_AMBIGUOUS" and
        synthetic["cases"]["cross_fifteen"]["category_status"] == "RELIEF_CATEGORY_NUMERICALLY_AMBIGUOUS")
    checks["nine_fresh_subsets"] = [x["subset"] for x in raw["rows"]] == d1["witness_subsets"] == [x["subset"] for x in rows] and len(raw["rows"]) == 9
    checks["all_paths_repeats_reopen"] = all(len(x["paths"]) == 4 and
        {(s["path"], s["repeat"]) for s in x["paths"]} == {(p, r) for p in cfg["frozen_paths"] for r in (0, 1)} and
        all(s["BREP_parity"] and s["FCStd_parity"] and
            "try6_0_d1_w1_v2" in s["witness_brep_path"] for s in x["paths"])
        for x in raw["rows"])
    construction = read(ROOT / cfg["frozen_kfde_construction"])
    checks["source_keepout_hashes"] = (sha(ROOT / read(ROOT / cfg["frozen_geometry_set"])["geometries"][0]["source_path"]) == pre["C1_source_sha256"] and
        sha(ROOT / construction["allowed_region"]["path"]) == pre["allowed_sha256"] and
        all(sha(ROOT / x["brep_path"]) == pre["component_hashes"][x["component_id"]] for x in construction["components"]))
    checks["measurement_coverage"] = len(measurements) == 9*2*2*3 and all(sum(x["subset"] == s for x in measurements) == 12 for s in d1["witness_subsets"])
    def records(item):
        return [sample[place] for sample in item["paths"] for place in ("memory", "BREP_reopen", "FCStd_reopen")]
    policy = cal["BOOLEAN_ACCOUNTING_TOLERANCE"]
    checks["source_containment"] = all(r["outside_source_mm3"] <= policy["absolute_mm3"] + policy["relative"]*max(1.0, item["source_volume_mm3"])
        for item in raw["rows"] for r in records(item))
    checks["keepout_removed"] = all(r["keepout_residual_mm3"] <= d1["kfde_numerical_epsilon_mm3"] for item in raw["rows"] for r in records(item))
    checks["topology_stable"] = all(len({(r["state"], r["solid_count"]) for r in records(item)}) == 1 for item in raw["rows"])
    checks["interface_invariant"] = raw["interface_invariant"] and read(RESULT / "audit/interface_invariance.json")["invariant"]
    normalization_valid = True
    for item in raw["rows"]:
        source = item["source_volume_mm3"]
        eps = max(rule["epsilon_abs_mm3"], rule["epsilon_rel"]*source)
        expected = []
        for sample in item["paths"]:
            for place in ("memory", "BREP_reopen", "FCStd_reopen"):
                volume = sample[place]["volume_mm3"]
                delta = source-volume
                normal = delta if delta >= 0 else 0.0 if delta >= -eps else None
                expected.append((sample["path"], sample["repeat"], place, delta, normal))
        actual = [(x["path"], int(x["repeat"]), x["location"], float(x["raw_removed_mm3"]),
                   float(x["normalized_removed_mm3"]) if x["normalized_removed_mm3"] else None)
                  for x in measurements if x["subset"] == item["subset"]]
        # CSV encodes a normalized zero as "0.0", not an empty field.
        normalization_valid &= len(expected) == len(actual) and all(
            e[:3] == a[:3] and abs(e[3]-a[3]) <= 1e-9 and
            (e[4] is None and a[4] is None or e[4] is not None and a[4] is not None and abs(e[4]-a[4]) <= 1e-9)
            for e, a in zip(expected, actual))
    checks["general_normalization_formula"] = normalization_valid
    normalized_counts = {s: sum(x["subset"] == s and x["normalization_applied"] == "True" for x in measurements) for s in d1["witness_subsets"]}
    checks["only_L07_normalized"] = normalized_counts["L07"] == 12 and all(v == 0 for k, v in normalized_counts.items() if k != "L07")
    checks["positive_measurements_preserved"] = all(float(x["normalized_removed_mm3"]) == float(x["raw_removed_mm3"])
        for x in measurements if float(x["raw_removed_mm3"]) >= 0)
    checks["category_intervals"] = all(
        (r["relief_category"] == category(float(r["relief_R_min"])) == category(float(r["relief_R_max"])) and
         r["category_status"] == "ROBUST" and float(r["relief_R_max"])-float(r["relief_R_min"]) <= 0.001)
        for r in rows)
    checks["L07_zero_small"] = next(r for r in rows if r["subset"] == "L07")["relief_category"] == "SMALL_RELIEF" and all(float(x["normalized_relief_ratio"]) == 0 for x in measurements if x["subset"] == "L07")
    checks["eight_W1_categories_unchanged"] = all(comparison[s]["raw_geometry_consistent"] and
        comparison[s]["previous_category"] == comparison[s]["new_category"] for s in d1["witness_subsets"] if s != "L07")
    checks["failure_accounting_complete"] = len(fail["attempted"]) == len(fail["passed"]) == 9 and fail["failed"] == {} and fail["dropped"] == []
    leakage = read(RESULT / "audit/leakage_audit.json")
    checks["no_forbidden_evaluation"] = all(v == 0 or v is False for v in leakage.values()) and raw["GT_evaluations"] == raw["VLM_calls"] == raw["final_96_case_mechanics_evaluations"] == 0
    lock_path = ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json"
    lock = read(lock_path)
    checks["holdout_untouched"] = sha(lock_path) == pre["holdout_lock_sha256"] and lock["accessed"] is False and lock["evaluation_count"] == 0
    checks["readiness_not_science"] = manifest["decision"] == "READY_FOR_D1_V3" and read(RESULT / "claim_ledger.json")["D1_scientific_mechanism"]["evidence_type"] == "not_evaluated"
    if not all(checks.values()):
        raise RuntimeError("independent W1-v2 validation failed: " + json.dumps(checks))
    output = {"decision": "READY_FOR_D1_V3", "checks": checks, "passed": len(checks),
        "total": len(checks), "independent_of_runner": True,
        "subsets_attempted": 9, "subsets_usable": 9, "normalization_counts": normalized_counts,
        "D1_v3_not_run": True, "scientific_mechanism_verdict": None}
    target = RESULT / "audit/independent_validation.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"decision": output["decision"], "passed": output["passed"], "total": output["total"]}))


if __name__ == "__main__":
    main()
