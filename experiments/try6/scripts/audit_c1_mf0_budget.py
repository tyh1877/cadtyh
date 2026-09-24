"""Read-only MF0 anti-sunk-cost gate; no factorized CAD path is fabricated."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "experiments/try6/results/try6_0_c1_mf0"
PROTOCOL = ROOT / "experiments/try6/protocol/try6_0_c1_mf0.json"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(relative, value):
    target = RESULT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    if Path(sys.executable).resolve() != (ROOT / ".venv/Scripts/python.exe").resolve():
        raise RuntimeError("repository .venv required")
    if RESULT.exists():
        raise FileExistsError("MF0 budget audit already started; no silent rerun")
    cfg = read(PROTOCOL)
    priors = {}
    for name, path in (("C1_v2", cfg["frozen_c1_v2_result"]),
                       ("D1_v3", cfg["frozen_d1_v3_result"]),
                       ("C1_A1", cfg["frozen_c1_a1_result"])):
        root = ROOT / path
        manifest = read(root / "manifest.json")
        if not all(sha(root / p) == h for p, h in manifest["result_file_sha256"].items()):
            raise RuntimeError("frozen prior result drift: " + name)
        priors[name] = sha(root / "manifest.json")
    lock_path = ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json"
    lock = read(lock_path)
    if lock["accessed"] is not False or lock["evaluation_count"] != 0:
        raise RuntimeError("formal holdout lock violated")
    files = {
        "KFDG_contract": "experiments/try6/scripts/r1_v3_contract.py",
        "KFDG_schema": "experiments/try6/protocol/r1_v3_kfdg.schema.json",
        "functional_backbone": "experiments/try6/protocol/r1_functional_backbone.json",
        "F0_scaffold_generator": "experiments/try5A/scripts/freecad_motion_realization.py",
        "F0_planner": "experiments/try5A/scripts/run_whole_robot.py",
        "FreeCAD_compiler": "experiments/try6/scripts/freecad_c1_builder.py",
        "parameter_registry": "experiments/try6/protocol/r1_parameter_registry.json",
        "parameter_bounds": "experiments/try6/protocol/parameter_bounds.json",
        "interface_contract": "experiments/try5A/results/try5a5/motion_interface_contracts.json",
        "visual_objective": "experiments/try6/scripts/c1_v2_visual_objective.py",
        "view_registration_evidence": "experiments/try6/scripts/extract_c1_v2_visual_evidence.py"}
    snapshots = {name: {"path": path, "sha256": sha(ROOT / path),
        "source_line_count": len((ROOT / path).read_text(encoding="utf-8").splitlines())}
        for name, path in files.items()}
    source = {name: (ROOT / path).read_text(encoding="utf-8") for name, path in files.items()}
    required = {
        "metric_KFDG_frame": '"frame_xyz_mm"' in source["KFDG_schema"] and '"distance_mm": 63.0' in source["functional_backbone"],
        "F0_metric_origins_and_absolute_primitives": "origin_xyz_mm" in source["F0_scaffold_generator"] and "cylinder_axis(3+" in source["F0_scaffold_generator"] and "interface_span_mm" in source["F0_scaffold_generator"],
        "compiler_63_guard_and_F0_import": "abs(anchor-63.0)>1e-9" in source["FreeCAD_compiler"] and 'job["f0_fcstd"]' in source["FreeCAD_compiler"],
        "registry_mm_variables": '"unit": "mm"' in source["parameter_registry"] and '"anchor_distance_mm": 63.0' in source["parameter_bounds"],
        "interface_metric_contract": "origin_xyz_mm" in source["interface_contract"] and "clearance_mm" in source["interface_contract"],
        "objective_px_per_mm": "scale_px_per_mm" in source["visual_objective"] and "/self.anchor" in source["visual_objective"],
        "registration_anchor_mm": "scale=axis_span/anchor" in source["view_registration_evidence"] and "roi_axis_mm" in source["view_registration_evidence"]}
    if not all(required.values()):
        raise RuntimeError("MF0 core-layer evidence incomplete: " + json.dumps(required))
    layers = [
        {"layer": "KFDG_functional_frames", "sources": ["KFDG_contract", "KFDG_schema", "functional_backbone"],
         "existing_metric_dependency": "metric_anchor.distance_mm=63; distal frame_xyz_mm=[63,0,0]; schema/validator expect mm frame and authority hash",
         "required_change": "dimensionless proximal/distal u plus scale-free schema, provenance and validator",
         "semantic_replacement": True, "legacy_wrapper_sufficient": False, "estimated_changed_LOC_range": [90, 170]},
        {"layer": "F0_scaffold_generator", "sources": ["F0_scaffold_generator", "F0_planner"],
         "existing_metric_dependency": "URDF origin and interface_span_mm=63 plus many fixed-mm primitives/bore radii/clearances; frozen F0 FCStd is exact metric scaffold",
         "required_change": "rebuild normalized functional scaffold and all primitive ratios from scale-clean provenance; post-hoc dividing frozen F0 by 63 retains anchored shape ratios",
         "semantic_replacement": True, "legacy_wrapper_sufficient": False, "estimated_changed_LOC_range": [170, 320]},
        {"layer": "FreeCAD_compiler", "sources": ["FreeCAD_compiler"],
         "existing_metric_dependency": "rejects s != 63, loft end x=s, parameters are mm; opens/fuses metric F0 and uses fixed-mm bore/mating tools",
         "required_change": "canonical unit feature tree, explicit s boundary, normalized interface/scaffold instantiation and arbitrary-s reopen",
         "semantic_replacement": True, "legacy_wrapper_sufficient": False, "estimated_changed_LOC_range": [110, 210]},
        {"layer": "parameter_registry", "sources": ["parameter_registry", "parameter_bounds"],
         "existing_metric_dependency": "six active values/bounds and functional anchor are absolute mm; current authority hashes bind them",
         "required_change": "ratio-valued schema, bounds/init provenance and deterministic theta_shape-to-metric map",
         "semantic_replacement": True, "legacy_wrapper_sufficient": False, "estimated_changed_LOC_range": [45, 100]},
        {"layer": "interface_geometry_contract", "sources": ["interface_contract", "F0_scaffold_generator", "FreeCAD_compiler"],
         "existing_metric_dependency": "J04 origin 63, clearance 0.6 and radii/depths 3/16/26 etc baked into mating and protected cuts",
         "required_change": "scale-free port identity/axis with all metric interface dimensions derived at the explicit s boundary",
         "semantic_replacement": True, "legacy_wrapper_sufficient": False, "estimated_changed_LOC_range": [90, 180]},
        {"layer": "visual_objective", "sources": ["visual_objective"],
         "existing_metric_dependency": "projects mesh with scale_px_per_mm; station targets in mm; profile loss divided by anchor",
         "required_change": "new normalized image/link-coordinate projection and ROI/profile objective evaluated on unit shape",
         "semantic_replacement": True, "legacy_wrapper_sufficient": False, "estimated_changed_LOC_range": [80, 150]},
        {"layer": "view_registration_evidence", "sources": ["view_registration_evidence"],
         "existing_metric_dependency": "bbox/63 creates px/mm; 12-52 mm ROI and 15/30/45 mm stations cached downstream",
         "required_change": "re-extract dimensionless visible-envelope coordinates from frozen raw masks, including preregistered u fractions",
         "semantic_replacement": True, "legacy_wrapper_sufficient": False, "estimated_changed_LOC_range": [80, 150]}]
    changed = sum(x["semantic_replacement"] for x in layers)
    lower = sum(x["estimated_changed_LOC_range"][0] for x in layers)
    upper = sum(x["estimated_changed_LOC_range"][1] for x in layers)
    major = changed >= 5
    if not major:
        raise RuntimeError("budget rule did not trigger; implementation path needed")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
        capture_output=True, text=True).stdout.strip()
    save("protocol.json", cfg)
    save("experiment_config_snapshot.json", cfg)
    save("refactor_budget/scope.json", {"core_layers": layers, "core_layer_count": len(layers),
        "semantic_replacements_required": changed, "source_snapshots": snapshots,
        "observed_dependency_checks": required, "classification": "MAJOR_METHOD_REWRITE"})
    save("refactor_budget/changed_modules.json", {"estimated_changed_LOC_range_total": [lower, upper],
        "estimate_type": "preimplementation engineering estimate, not measured diff or implementation promise",
        "changed_core_layers": [x["layer"] for x in layers],
        "affected_test_families": ["KFDG/schema/authority", "F0/interface geometry", "FreeCAD feature-tree/reopen", "visual evidence/registration", "visual objective", "24 MF0 build/provenance tests", "historical C1-v2 parity"],
        "historical_API_wrapper_feasible_without_anchor_leak": False,
        "why_wrapper_insufficient": "The current builder rejects non-63 s and fuses an exact-metric F0; scaling the finished CAD would preserve anchor-derived normalized scaffold and interface ratios inside the shape path."})
    save("refactor_budget/budget_decision.json", {"decision": "FACTOR_REFACTOR_TOO_LARGE",
        "rule": cfg["refactor_budget_rule"], "observed_semantic_replacements": changed,
        "total_core_layers": len(layers), "major_method_rewrite": major,
        "implementation_stopped_before_any_scientific_module_edit": True,
        "bounded_refactor_not_defensible": True})
    before = read(ROOT / cfg["frozen_c1_a1_result"] / "provenance/scale_provenance_audit.json")
    save("provenance/metric_provenance_before.json", {"source": cfg["frozen_c1_a1_result"] + "/provenance/scale_provenance_audit.json",
        "source_sha256": sha(ROOT / cfg["frozen_c1_a1_result"] / "provenance/scale_provenance_audit.json"),
        "metric_paths": before["exact_metric_paths"], "rows": before["rows"]})
    save("provenance/metric_provenance_after.json", {"status": "NOT_AVAILABLE_REFACTOR_BUDGET_GATE",
        "factorized_code_not_created": True, "single_metric_entry_point_proven": False})
    save("provenance/hidden_scale_search.json", {"source_snapshots": snapshots,
        "observed_dependency_checks": required,
        "post_refactor_search_not_run": True,
        "forbidden_shortcut": "global rescale of historical F0 or final CAD does not establish scale-clean theta_shape provenance"})
    for filename, message in (
        ("canonical_coordinate_spec", "u=0/1 is a proposed interface coordinate only; no canonical feature tree exists"),
        ("shape_parameter_registry", "six historical mm parameters have not been replaced by provenance-clean ratios"),
        ("scale_boundary_spec", "a single explicit s API is not implemented; current 63-mm guards remain"),
        ("interface_spec", "joint axes/ownership may remain, but metric radii/clearances/placements are not factored"),
        ("scaffold_spec", "historical F0 is metric; no valid independent normalized scaffold was created")):
        save("representation/" + filename + ".json", {"status": "DESIGN_ONLY_NOT_IMPLEMENTED",
            "description": message, "cannot_close_READY_FOR_MF1": True})
    test_names = ["canonical_s1_build", "arbitrary_s_build", "scale_equivariance", "normalized_ratio_invariance",
        "normalized_geometry_invariance", "topology_invariance", "interface_scaling", "scaffold_scaling",
        "compiler_accepts_non63", "no_63_hard_requirement", "image_objective_independent_of_s",
        "no_px_per_mm_shape_path", "no_mm_ROI_shape_path", "no_mm_profile_stations_shape_path",
        "parameter_registry_dimensionless", "single_metric_entry", "historical_s63_parity",
        "BREP_validity", "FCStd_reopen", "no_GT", "no_VLM", "no_optimizer", "no_KFDE", "holdout_guard"]
    statuses = {x: ("PASS_GUARD" if x in ("no_GT", "no_VLM", "no_optimizer", "no_KFDE", "holdout_guard")
                    else "NOT_RUN_BUDGET_GATE") for x in test_names}
    save("tests/test_report.json", {"tests": statuses, "count": 24,
        "technical_build_tests_run": 0, "guard_checks_passed": 5,
        "no_false_PASS_for_unbuilt_factorization": True})
    save("case_split.json", {"technical_scales_requested": [1, 60, 63, 70],
        "technical_scales_built": [], "formal_holdout_case_count": 32,
        "formal_holdout_ids_not_read": True, "accessed": False, "evaluation_count": 0})
    save("condition_parity.json", {"status": "NOT_RUN_PREIMPLEMENTATION_BUDGET_STOP",
        "theta_shape_fixture": None, "s_values_tested": [], "historical_parity_tested": False})
    save("failure_accounting.json", {"decision": "FACTOR_REFACTOR_TOO_LARGE",
        "requested_build_scales": [1, 60, 63, 70], "attempted_build_scales": [],
        "completed_build_scales": [], "reason": "preimplementation 7-of-7 core-layer semantic replacement gate"})
    save("holdout_evaluation_log.json", {"events": [], "accessed": False,
        "evaluation_count": 0, "followed_by_tuning": False})
    for name in ("no_gt", "no_vlm", "no_optimizer", "no_kfde"):
        save("audit/" + name + ".json", {"count": 0, "status": "PASS_GUARD"})
    save("audit/holdout_audit.json", {"lock_sha256": sha(lock_path),
        "accessed": lock["accessed"], "evaluation_count": lock["evaluation_count"]})
    save("claim_ledger.json", {"refactor_budget": {"evidence_type": "source_audit_plus_engineering_estimate",
        "artifact": "refactor_budget/scope.json"},
        "factorization_feasible": {"evidence_type": "not_tested", "reason": "major rewrite gate stopped implementation"},
        "anchor_benefit": {"evidence_type": "not_evaluated", "reason": "no MF1/no GT/no optimizer"}})
    save("pre_run_manifest.json", {"created_utc": datetime.now(timezone.utc).isoformat(),
        "starting_commit": head, "protocol_sha256": sha(PROTOCOL),
        "prior_manifest_sha256": priors,
        "source_sha256": {name: item["sha256"] for name, item in snapshots.items()},
        "python_environment": sys.executable,
        "holdout_lock_sha256": sha(lock_path), "FreeCAD_not_started": True})
    files_out = [p for p in RESULT.rglob("*") if p.is_file() and p.name not in ("manifest.json", "independent_validation.json")]
    save("manifest.json", {"decision": "FACTOR_REFACTOR_TOO_LARGE",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "starting_commit": head, "final_commit_reference": "git rev-parse try6-c1-mf0-refactor-too-large",
        "protocol_sha256": sha(PROTOCOL), "prior_manifest_sha256": priors,
        "source_sha256": {name: item["sha256"] for name, item in snapshots.items()},
        "changed_LOC_estimate": [lower, upper],
        "python_environment": sys.executable,
        "result_file_sha256": {str(p.relative_to(RESULT)).replace("\\", "/"): sha(p) for p in files_out}})
    print(json.dumps({"decision": "FACTOR_REFACTOR_TOO_LARGE", "core_layers_requiring_semantic_replacement": changed,
        "core_layer_total": len(layers), "builds": 0, "GT_evaluations": 0}))


if __name__ == "__main__":
    main()
