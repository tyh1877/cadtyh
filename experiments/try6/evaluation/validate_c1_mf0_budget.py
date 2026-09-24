"""Independent MF0 anti-sunk-cost validation; no CAD build is executed."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "experiments/try6/results/try6_0_c1_mf0"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    manifest = read(RESULT / "manifest.json")
    config = read(ROOT / "experiments/try6/protocol/try6_0_c1_mf0.json")
    pre = read(RESULT / "pre_run_manifest.json")
    scope = read(RESULT / "refactor_budget/scope.json")
    changed = read(RESULT / "refactor_budget/changed_modules.json")
    budget = read(RESULT / "refactor_budget/budget_decision.json")
    tests = read(RESULT / "tests/test_report.json")
    checks = {}
    checks["tracked_result_hashes"] = all(sha(RESULT / p) == h for p, h in manifest["result_file_sha256"].items())
    checks["protocol_hash"] = sha(ROOT / "experiments/try6/protocol/try6_0_c1_mf0.json") == manifest["protocol_sha256"]
    checks["frozen_prior_manifests"] = all(sha(ROOT / path / "manifest.json") == h for name, path, h in (
        ("C1_v2", config["frozen_c1_v2_result"], pre["prior_manifest_sha256"]["C1_v2"]),
        ("D1_v3", config["frozen_d1_v3_result"], pre["prior_manifest_sha256"]["D1_v3"]),
        ("C1_A1", config["frozen_c1_a1_result"], pre["prior_manifest_sha256"]["C1_A1"])))
    checks["source_hashes_unchanged"] = all(sha(ROOT / x["path"]) == x["sha256"] == pre["source_sha256"][name]
        for name, x in scope["source_snapshots"].items())
    checks["seven_core_layers"] = [x["layer"] for x in scope["core_layers"]] == config["refactor_budget_rule"]["core_layers"] and len(scope["core_layers"]) == 7
    checks["seven_semantic_replacements_evidenced"] = all(x["semantic_replacement"] and not x["legacy_wrapper_sufficient"] and
        x["existing_metric_dependency"] and x["required_change"] for x in scope["core_layers"])
    checks["observed_code_dependencies"] = all(scope["observed_dependency_checks"].values())
    builder = (ROOT / scope["source_snapshots"]["FreeCAD_compiler"]["path"]).read_text(encoding="utf-8")
    checks["non63_compiler_block"] = "abs(anchor-63.0)>1e-9" in builder and 'job["f0_fcstd"]' in builder
    f0 = (ROOT / scope["source_snapshots"]["F0_scaffold_generator"]["path"]).read_text(encoding="utf-8")
    checks["F0_metric_interface_dependency"] = "origin_xyz_mm" in f0 and "interface_span_mm" in f0 and "cylinder_axis(3+" in f0
    objective = (ROOT / scope["source_snapshots"]["visual_objective"]["path"]).read_text(encoding="utf-8")
    registration = (ROOT / scope["source_snapshots"]["view_registration_evidence"]["path"]).read_text(encoding="utf-8")
    checks["objective_registration_metric_dependency"] = "scale_px_per_mm" in objective and "/self.anchor" in objective and "scale=axis_span/anchor" in registration
    checks["budget_rule_applied"] = scope["semantic_replacements_required"] == 7 and budget["observed_semantic_replacements"] == 7 and budget["total_core_layers"] == 7 and budget["major_method_rewrite"]
    checks["changed_LOC_estimate_honest"] = changed["estimate_type"].startswith("preimplementation") and changed["estimated_changed_LOC_range_total"] == manifest["changed_LOC_estimate"] and changed["estimated_changed_LOC_range_total"][0] > 0
    checks["no_posthoc_scaling_shortcut"] = "global rescale" in read(RESULT / "provenance/hidden_scale_search.json")["forbidden_shortcut"]
    checks["no_false_factorized_artifacts"] = all(read(RESULT / "representation" / (name + ".json"))["status"] == "DESIGN_ONLY_NOT_IMPLEMENTED"
        for name in ("canonical_coordinate_spec", "shape_parameter_registry", "scale_boundary_spec", "interface_spec", "scaffold_spec"))
    checks["after_provenance_unavailable"] = read(RESULT / "provenance/metric_provenance_after.json")["status"] == "NOT_AVAILABLE_REFACTOR_BUDGET_GATE"
    split = read(RESULT / "case_split.json")
    failure = read(RESULT / "failure_accounting.json")
    checks["no_scale_builds"] = split["technical_scales_requested"] == [1, 60, 63, 70] and split["technical_scales_built"] == failure["attempted_build_scales"] == failure["completed_build_scales"] == [] and not (RESULT / "builds").exists()
    checks["twenty_four_tests_honest"] = tests["count"] == 24 and tests["technical_build_tests_run"] == 0 and tests["guard_checks_passed"] == 5 and sum(x == "NOT_RUN_BUDGET_GATE" for x in tests["tests"].values()) == 19
    checks["no_forbidden_evaluations"] = all(read(RESULT / "audit" / (name + ".json"))["count"] == 0
        for name in ("no_gt", "no_vlm", "no_optimizer", "no_kfde"))
    lock_path = ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json"
    lock = read(lock_path)
    checks["holdout_untouched"] = sha(lock_path) == pre["holdout_lock_sha256"] and lock["accessed"] is False and lock["evaluation_count"] == 0
    checks["decision_follows_budget_gate"] = manifest["decision"] == budget["decision"] == "FACTOR_REFACTOR_TOO_LARGE" and budget["implementation_stopped_before_any_scientific_module_edit"]
    if not all(checks.values()):
        raise RuntimeError("independent MF0 validation failed: " + json.dumps(checks))
    output = {"decision": "FACTOR_REFACTOR_TOO_LARGE", "checks": checks,
        "passed": len(checks), "total": len(checks), "independent_of_runner": True,
        "core_layers_requiring_semantic_replacement": 7, "metric_scale_instantiations": 0,
        "anchor_benefit_estimated": False, "GT_evaluations": 0}
    target = RESULT / "audit/independent_validation.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"decision": output["decision"], "passed": output["passed"], "total": output["total"]}))


if __name__ == "__main__":
    main()
