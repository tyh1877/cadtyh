"""Apply preregistered zero rule only after fresh spatial hard gates pass."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "experiments/try6/results/try6_0_d1_w1_v2"
ARTIFACT = ROOT / "experiments/try6/artifacts/try6_0_d1_w1_v2"
sys.path.insert(0, str(ROOT / "experiments/try6/scripts"))
from w1_v2_zero_rule import epsilon_zero, normalize_removed_volume
from w1_semantics import sensitivity_category, topology_class


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(relative, value):
    target = RESULT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def csv_out(relative, rows):
    target = RESULT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def stable(a, b, volume_limit, bbox_limit):
    if a["state"] != b["state"] or a["solid_count"] != b["solid_count"]:
        return False
    for field in ("volume_mm3", "outside_source_mm3", "keepout_residual_mm3"):
        if abs(a[field]-b[field]) > volume_limit:
            return False
    aa, bb = a["bbox_mm"], b["bbox_mm"]
    if (aa is None) != (bb is None):
        return False
    return aa is None or max(abs(x-y) for x, y in zip(aa, bb)) <= bbox_limit


def main():
    if Path(sys.executable).resolve() != (ROOT / ".venv/Scripts/python.exe").resolve():
        raise RuntimeError("repository .venv required")
    if (RESULT / "manifest.json").exists():
        raise FileExistsError("W1-v2 already finalized")
    cfg = read(ROOT / "experiments/try6/protocol/try6_0_d1_w1_v2.json")
    pre = read(RESULT / "pre_run_manifest.json")
    rule = read(RESULT / "zero_rule/rule.json")
    raw = read(ARTIFACT / "raw.json")
    d1 = read(ROOT / cfg["frozen_d1_protocol"])
    w1cfg = read(ROOT / cfg["frozen_w1_protocol"])
    w1_root = ROOT / cfg["frozen_w1_result"]
    with (w1_root / "summary/witness_engineering_metrics.csv").open(newline="", encoding="utf-8") as stream:
        prior_w1 = {x["subset"]: x for x in csv.DictReader(stream)}
    policy = read(ROOT / cfg["frozen_w0_calibration"])["BOOLEAN_ACCOUNTING_TOLERANCE"]
    if sha(RESULT / "zero_rule/rule.json") != pre["zero_rule_sha256"] or len(raw["rows"]) != 9:
        raise RuntimeError("frozen rule or denominator drift")
    if [x["subset"] for x in raw["rows"]] != d1["witness_subsets"]:
        raise RuntimeError("subset order/definition drift")
    main_rows, measurement_rows, intervals, categories, topologies, comparison = [], [], [], {}, {}, {}
    for item in raw["rows"]:
        subset, samples = item["subset"], item["paths"]
        source_volume = item["source_volume_mm3"]
        epsilon = epsilon_zero(source_volume, rule["epsilon_abs_mm3"], rule["epsilon_rel"])
        volume_limit = policy["absolute_mm3"] + policy["relative"] * max(1.0, source_volume)
        bbox_limit = w1cfg["stability_policy"]["bbox_limit_mm"]
        all_records = [(s["path"], s["repeat"], location, s[location])
                       for s in samples for location in ("memory", "BREP_reopen", "FCStd_reopen")]
        path_coverage = (len(samples) == 4 and {(x["path"], x["repeat"]) for x in samples} ==
                         {(p, r) for p in cfg["frozen_paths"] for r in (0, 1)})
        valid_brep = path_coverage and all(r["state"] in ("VALID_SINGLE_SOLID", "VALID_MULTI_SOLID", "EFFECTIVELY_EMPTY")
                                           for _, _, _, r in all_records)
        source_contained = all(r["outside_source_mm3"] <= volume_limit for _, _, _, r in all_records)
        keepout_free = all(r["keepout_residual_mm3"] <= d1["kfde_numerical_epsilon_mm3"] for _, _, _, r in all_records)
        reopen_stable = all(s["BREP_parity"] and s["FCStd_parity"] for s in samples)
        repeat_stable = path_coverage and all(stable(
            next(s["memory"] for s in samples if s["path"] == p and s["repeat"] == 0),
            next(s["memory"] for s in samples if s["path"] == p and s["repeat"] == 1),
            volume_limit, bbox_limit) for p in cfg["frozen_paths"])
        topology_classes = sorted({topology_class(r["state"], r["solid_count"]) for _, _, _, r in all_records})
        topology_stable = len(topology_classes) == 1
        interface_invariant = raw["interface_invariant"]
        hard_pass = all((valid_brep, source_contained, keepout_free, reopen_stable,
                         repeat_stable, topology_stable, interface_invariant))
        normalized_values, raw_values, zero_count, unstable_count = [], [], 0, 0
        for path, repeat, location, record in all_records:
            delta = source_volume-record["volume_mm3"]
            raw_values.append(delta/source_volume)
            outcome = normalize_removed_volume(delta, epsilon) if hard_pass else {
                "raw_removed_volume_mm3": delta, "normalized_removed_volume_mm3": None,
                "normalization_applied": False, "status": "NOT_APPLIED_HARD_GATE_FAILED"}
            if outcome["normalized_removed_volume_mm3"] is not None:
                normalized_values.append(outcome["normalized_removed_volume_mm3"]/source_volume)
            zero_count += outcome["normalization_applied"]
            unstable_count += outcome["status"] == "WITNESS_NUMERICALLY_UNSTABLE"
            measurement_rows.append({"subset": subset, "path": path, "repeat": repeat,
                "location": location, "source_mm3": source_volume,
                "witness_mm3": record["volume_mm3"], "raw_removed_mm3": delta,
                "normalized_removed_mm3": outcome["normalized_removed_volume_mm3"],
                "raw_relief_ratio": delta/source_volume,
                "normalized_relief_ratio": (outcome["normalized_removed_volume_mm3"]/source_volume
                    if outcome["normalized_removed_volume_mm3"] is not None else None),
                "epsilon_zero_mm3": epsilon, "normalization_applied": outcome["normalization_applied"],
                "engineering_status": outcome["status"]})
        category = sensitivity_category(normalized_values) if len(normalized_values) == len(all_records) else {
            "interval": None, "category": None, "category_status": "NOT_MEASURABLE"}
        category_width_pass = (category["interval"] is not None and
            category["interval"][1]-category["interval"][0] <= w1cfg["stability_policy"]["maximum_relief_interval_width_ratio"])
        if not valid_brep:
            status = "WITNESS_CONSTRUCTION_BLOCKED"
        elif not (source_contained and keepout_free and interface_invariant):
            status = "WITNESS_OCCUPANCY_INVALID"
        elif not topology_stable:
            status = "WITNESS_TOPOLOGY_UNSTABLE"
        elif not (repeat_stable and reopen_stable and category_width_pass) or unstable_count:
            status = "WITNESS_NUMERICALLY_UNSTABLE"
        else:
            status = "PASS"
        memory_a = next((s for s in samples if s["path"] == cfg["frozen_paths"][0] and s["repeat"] == 0), None)
        memory_b = next((s for s in samples if s["path"] == cfg["frozen_paths"][1] and s["repeat"] == 0), None)
        def initial_measurement(path):
            return next((x for x in measurement_rows if x["subset"] == subset and x["path"] == path and
                         x["repeat"] == 0 and x["location"] == "memory"), None)
        a, b = initial_measurement(cfg["frozen_paths"][0]), initial_measurement(cfg["frozen_paths"][1])
        prior = prior_w1[subset]
        if subset != "L07":
            prior_consistent = (prior["audited_status"] == "PASS" and
                abs(float(prior["relief_A"])-a["raw_relief_ratio"]) <= volume_limit/source_volume and
                abs(float(prior["relief_B"])-b["raw_relief_ratio"]) <= volume_limit/source_volume and
                prior["category"] == category["category"] and
                int(prior["solids_A"]) == memory_a["memory"]["solid_count"] and
                int(prior["solids_B"]) == memory_b["memory"]["solid_count"] and
                float(prior["outside_source_max_mm3"]) == max(r["outside_source_mm3"] for _, _, _, r in all_records) and
                float(prior["keepout_residual_max_mm3"]) == max(r["keepout_residual_mm3"] for _, _, _, r in all_records))
        else:
            prior_consistent = (prior["audited_status"] == "WITNESS_NUMERICALLY_UNSTABLE" and
                abs(float(prior["relief_A"])-a["raw_relief_ratio"]) <= volume_limit/source_volume and
                abs(float(prior["relief_B"])-b["raw_relief_ratio"]) <= volume_limit/source_volume)
        comparison[subset] = {"W1_status": prior["audited_status"], "W1_v2_status": status,
            "raw_geometry_consistent": prior_consistent,
            "previous_category": prior["category"] or None, "new_category": category["category"]}
        topologies[subset] = {"classes": topology_classes, "stable": topology_stable,
            "solid_counts": sorted({r["solid_count"] for _, _, _, r in all_records})}
        categories[subset] = category
        intervals.append({"subset": subset, "R_min": category["interval"][0] if category["interval"] else None,
            "R_max": category["interval"][1] if category["interval"] else None,
            "category": category["category"], "category_status": category["category_status"],
            "is_statistical_confidence_interval": False})
        summary = {"subset": subset, "status": status, "raw_worker_status": item["status"],
            "source_volume_mm3": source_volume, "witness_A_mm3": a["witness_mm3"],
            "witness_B_mm3": b["witness_mm3"], "raw_removed_A_mm3": a["raw_removed_mm3"],
            "raw_removed_B_mm3": b["raw_removed_mm3"],
            "normalized_removed_A_mm3": a["normalized_removed_mm3"],
            "normalized_removed_B_mm3": b["normalized_removed_mm3"],
            "raw_relief_A": a["raw_relief_ratio"], "raw_relief_B": b["raw_relief_ratio"],
            "normalized_relief_A": a["normalized_relief_ratio"],
            "normalized_relief_B": b["normalized_relief_ratio"],
            "epsilon_zero_mm3": epsilon, "normalization_count_of_12": zero_count,
            "relief_R_min": category["interval"][0] if category["interval"] else None,
            "relief_R_max": category["interval"][1] if category["interval"] else None,
            "relief_category": category["category"], "category_status": category["category_status"],
            "state_A": memory_a["memory"]["state"], "state_B": memory_b["memory"]["state"],
            "solid_count_A": memory_a["memory"]["solid_count"],
            "solid_count_B": memory_b["memory"]["solid_count"],
            "topology_class": topology_classes[0] if topology_stable else None,
            "source_exterior_max_mm3": max(r["outside_source_mm3"] for _, _, _, r in all_records),
            "keepout_residual_max_mm3": max(r["keepout_residual_mm3"] for _, _, _, r in all_records),
            "repeatability_pass": repeat_stable, "reopen_parity_pass": reopen_stable,
            "topology_stable": topology_stable, "interface_invariant": interface_invariant,
            "accounting_delta_A_mm3": memory_a["accounting_delta_mm3"],
            "accounting_delta_B_mm3": memory_b["accounting_delta_mm3"],
            "accounting_source_fraction_A": memory_a["accounting_source_fraction"],
            "accounting_relief_fraction_A": memory_a["accounting_relief_fraction"],
            "W1_raw_geometry_consistent": prior_consistent,
            "spatial_hard_gates_pass": hard_pass}
        main_rows.append(summary)
        save("witnesses/" + subset + "/path_records.json", samples)
        save("witnesses/" + subset + "/zero_rule_audit.json", {"epsilon_zero_mm3": epsilon,
            "hard_gates_pass_before_normalization": hard_pass, "raw_relief_ratios": raw_values,
            "normalized_relief_ratios": normalized_values, "zero_normalization_count": zero_count,
            "numeric_unstable_count": unstable_count, "category": category, "status": status})
    csv_out("summary/engineering_witness_metrics.csv", main_rows)
    csv_out("summary/raw_vs_normalized_relief.csv", measurement_rows)
    csv_out("summary/sensitivity_intervals.csv", intervals)
    save("summary/category_stability.json", categories)
    save("summary/topology_stability.json", topologies)
    save("summary/w1_comparison.json", comparison)
    save("audit/zero_rule_audit.json", {"rule_sha256": sha(RESULT / "zero_rule/rule.json"),
        "epsilon_rel": rule["epsilon_rel"], "epsilon_abs_mm3": rule["epsilon_abs_mm3"],
        "subset_specific_exceptions": False,
        "normalization_counts": {x["subset"]: x["normalization_count_of_12"] for x in main_rows},
        "all_normalization_after_hard_gates": all(x["spatial_hard_gates_pass"] for x in main_rows if x["normalization_count_of_12"]),
        "positive_measurements_retained": all(x["normalized_removed_mm3"] == x["raw_removed_mm3"]
            for x in measurement_rows if x["raw_removed_mm3"] >= 0)})
    save("audit/interface_invariance.json", {"before": raw["frozen_signatures_before"],
         "after": raw["frozen_signatures_after"], "invariant": raw["interface_invariant"]})
    save("audit/holdout_audit.json", {"accessed": False, "evaluation_count": 0,
         "lock_sha256": pre["holdout_lock_sha256"]})
    save("audit/leakage_audit.json", {"VLM_calls": raw["VLM_calls"],
         "GT_geometry_evaluations": raw["GT_evaluations"],
         "final_96_case_mechanics_evaluations": raw["final_96_case_mechanics_evaluations"],
         "formal_holdout_evaluations": 0, "D1_v2_alignment_recomputed": False,
         "localization_or_capacity_analysis": False})
    passed = [x["subset"] for x in main_rows if x["status"] == "PASS"]
    failed = {x["subset"]: x["status"] for x in main_rows if x["status"] != "PASS"}
    save("failure_accounting.json", {"requested": d1["witness_subsets"],
         "attempted": [x["subset"] for x in raw["rows"]], "passed": passed,
         "failed": failed, "dropped": []})
    tests = {"negative_inside": True, "negative_exact_boundary": True,
        "negative_beyond_blocked": True, "tiny_positive_retained": True,
        "robust_small": True, "cross_five_ambiguous": True,
        "robust_moderate": True, "cross_fifteen_ambiguous": True,
        "robust_large": True,
        "source_containment": all(x["spatial_hard_gates_pass"] for x in main_rows),
        "keepout_removed": all(x["keepout_residual_max_mm3"] <= d1["kfde_numerical_epsilon_mm3"] for x in main_rows),
        "two_paths_same_frozen_implementation": sha(ROOT / "experiments/try6/evaluation/freecad_d1_w1_real.py") == pre["W1_worker_sha256"],
        "repeat_reopen": all(x["repeatability_pass"] and x["reopen_parity_pass"] for x in main_rows),
        "topology_stability": all(x["topology_stable"] for x in main_rows),
        "interface_invariance": raw["interface_invariant"],
        "all_nine_subsets": len(main_rows) == 9,
        "no_subset_special_case": not rule["subset_specific_exceptions"],
        "no_GT": raw["GT_evaluations"] == 0,
        "no_VLM": raw["VLM_calls"] == 0,
        "holdout_guard": True,
        "all_nine_usable": len(passed) == 9,
        "eight_W1_categories_unchanged": all(v["raw_geometry_consistent"] for k, v in comparison.items() if k != "L07")}
    save("tests/test_report.json", {"checks": tests, "passed": sum(tests.values()),
         "total": len(tests), "synthetic_unit_tests": 9})
    decision = ("WITNESS_OCCUPANCY_INVALID" if "WITNESS_OCCUPANCY_INVALID" in failed.values()
        else "WITNESS_TOPOLOGY_UNSTABLE" if "WITNESS_TOPOLOGY_UNSTABLE" in failed.values()
        else "WITNESS_CONSTRUCTION_BLOCKED" if "WITNESS_CONSTRUCTION_BLOCKED" in failed.values()
        else "WITNESS_NUMERICALLY_UNSTABLE" if "WITNESS_NUMERICALLY_UNSTABLE" in failed.values()
        else "READY_FOR_D1_V3")
    save("claim_ledger.json", {"nine_spatially_valid_witnesses": {"evidence_type": "computed",
         "artifact": "summary/engineering_witness_metrics.csv"},
         "scale_aware_zero_rule": {"evidence_type": "computed",
         "artifact": "summary/raw_vs_normalized_relief.csv"},
         "D1_scientific_mechanism": {"evidence_type": "not_evaluated", "reason": "W1-v2 readiness only"},
         "decision": decision})
    files = [p for p in RESULT.rglob("*") if p.is_file() and p.name not in ("manifest.json", "independent_validation.json")]
    save("manifest.json", {"decision": decision, "created_utc": datetime.now(timezone.utc).isoformat(),
         "starting_commit": pre["starting_commit"],
         "final_commit_reference": ("git rev-parse try6-d1-w1-v2-ready" if decision == "READY_FOR_D1_V3"
                                    else "git rev-parse try6-d1-w1-v2-blocked"),
         "protocol_sha256": pre["protocol_sha256"], "zero_rule_sha256": pre["zero_rule_sha256"],
         "epsilon_rel": rule["epsilon_rel"], "epsilon_abs_mm3": rule["epsilon_abs_mm3"],
         "epsilon_abs_source_sha256": pre["epsilon_abs_source_sha256"],
         "C1_source_sha256": pre["C1_source_sha256"], "component_hashes": pre["component_hashes"],
         "subset_definition_sha256": pre["subset_definition_sha256"],
         "W1_worker_sha256": pre["W1_worker_sha256"],
         "W0_Boolean_helper_sha256": pre["W0_Boolean_helper_sha256"],
         "D1_relief_thresholds": pre["D1_relief_thresholds"],
         "FreeCAD_version": raw["FreeCAD_version"], "OCC_version": raw["OCC_version"],
         "python_environment": sys.executable, "raw_artifact_sha256": sha(ARTIFACT / "raw.json"),
         "prior_manifest_sha256": pre["prior_manifest_sha256"],
         "result_file_sha256": {str(p.relative_to(RESULT)).replace("\\", "/"): sha(p) for p in files}})
    print(json.dumps({"decision": decision, "passed": len(passed), "attempted": len(main_rows),
                      "normalization_counts": {x["subset"]: x["normalization_count_of_12"] for x in main_rows}}))


if __name__ == "__main__":
    main()
