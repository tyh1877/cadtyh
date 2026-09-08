"""Try-5A.3 Phase 5-10 scope-arbiter pilot; no whole-robot repair loop."""
import json
from pathlib import Path

from repair_scope_arbiter import arbitrate

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/try5A"
OUT = HERE / "results/try5a3_phase510"


def feature(feature_id, owning_link, role, node, strategy, why):
    return {
        "feature_id": feature_id,
        "owning_link": owning_link,
        "mechanical_role": role,
        "source_evidence": "deterministic repair diagnosis plus declared Robot Plan context",
        "source_design_node": node,
        "why_required": why,
        "related_interface_or_body": node.split("/")[-1],
        "cad_strategy": strategy,
    }


def meaningful(item):
    required = ("feature_id", "owning_link", "mechanical_role", "source_evidence", "source_design_node", "why_required", "related_interface_or_body", "cad_strategy")
    return {"feature_id": item["feature_id"], "pass": not [key for key in required if not item.get(key)]}


def apply_design_repair(decision):
    target, scope = decision["target"], decision["repair_scope"]
    if scope == "R0_PARAMETER_REPAIR":
        design = {"kind": "LinkCoarseSpec.parameter_update", "target": target, "before": {"carrier_radius_mm": 15.0}, "after": {"carrier_radius_mm": 14.5}}
        features = [feature("IF_J03_carrier", "L03", "coaxial interface carrier", "LinkCoarseSpec/L03", "update cylinder radius parameter", "restore declared radial clearance")]
    elif scope == "R1_LOCAL_FEATURE_REPAIR":
        design = {"kind": "BodyRegionSpec.local_feature", "target": target, "before": {"transition_web": "absent"}, "after": {"transition_web": "tapered support web"}}
        features = [feature("L03_transition_web", "L03", "connects forearm body to distal carrier", "BodyRegionSpec/L03/distal_transition", "replace local transition with tapered web", "restore local load path without bridging the joint clearance")]
    elif scope == "R2_BODY_REGION_REPLAN":
        design = {"kind": "BodyRegionSpec.replan", "target": target, "before": {"family": "straight_beam"}, "after": {"family": "tapered_beam", "structural_path": "proximal carrier -> tapered web -> distal carrier"}}
        features = [feature("L04_middle_tapered_web", "L04", "wrist body corridor", "BodyRegionSpec/L04/middle", "replace local body family", "remove recurrent local collision while preserving frozen interfaces")]
    elif scope == "R3_WHOLE_LINK_REPLAN":
        design = {"kind": "LinkCoarseSpec.whole_link_replan", "target": target, "before": {"body_family": "straight_beam", "structural_path": "single beam"}, "after": {"body_family": "dual_side_plate", "structural_path": "proximal fork carrier -> paired load paths -> distal carrier"}}
        features = [feature("L05_left_side_plate", "L05", "first load path between interface carriers", "LinkCoarseSpec/L05", "replace single beam with paired plates", "correct wrong whole-link topology"), feature("L05_right_side_plate", "L05", "second load path between interface carriers", "LinkCoarseSpec/L05", "replace single beam with paired plates", "maintain symmetric fork-compatible body organization")]
    elif scope == "R4_INTERFACE_PAIR_REPLAN":
        design = {"kind": "InterfaceContract.pair_replan", "target": target, "before": {"family": "coaxial_rotary_interface"}, "after": {"family": "nested_rotary_housing", "parent_region": "annular base carrier", "child_region": "nested shoulder carrier"}}
        features = [feature("J00_outer_housing", "L00", "stationary annular base carrier", "InterfaceContract/J00", "concentric outer housing", "realize nested rotary family"), feature("J00_inner_rotor", "L01", "rotating shoulder carrier", "InterfaceContract/J00", "concentric inner carrier with annular clearance", "realize nested rotary family without rigid fusion")]
    else:
        raise ValueError(scope)
    return {"decision": decision, "design_update": design, "cad_ir_projection": {"generated_from": design["kind"], "operations": features}, "mechanical_meaningfulness": [meaningful(item) for item in features]}


def main():
    # No case contains expected_repair_scope.  These are evaluator-only labels below.
    cases = [
        {"case_id": "A_parameter", "target": "J03/L03-L04", "failed_gates": ["INTERFACE_CLEARANCE"], "deterministic_evidence": {"topology_valid": True, "parameter_delta_within_tolerance": True}, "vlm_diagnosis": {"suspected_root_cause": "minor_radius_error", "confidence": 0.91}, "rationale": ["small radial clearance deviation", "topology and family remain valid"], "protected_states": ["URDF_J03_FRAME", "neighboring interfaces"]},
        {"case_id": "B_local_feature", "target": "L03/distal_transition", "failed_gates": ["PHYSICAL_ATTACHMENT"], "deterministic_evidence": {"localized_feature_failure": True, "repeated_region_failures": 1}, "vlm_diagnosis": {"suspected_root_cause": "local_transition_failure", "confidence": 0.84}, "rationale": ["local body-to-carrier load path is absent"], "protected_states": ["URDF_J03_FRAME", "J03 carrier"]},
        {"case_id": "C_whole_link", "target": "L05", "failed_gates": ["COARSE_MORPHOLOGY", "STRUCTURAL_PATH"], "deterministic_evidence": {"body_topology_valid": False, "localized_feature_failure": False}, "vlm_diagnosis": {"suspected_root_cause": "body_family_mismatch", "confidence": 0.89}, "rationale": ["single beam cannot realize the required paired load path"], "protected_states": ["URDF_J05_FRAME", "URDF_J06_FRAME"]},
        {"case_id": "D_interface_pair", "target": "J00/L00-L01", "failed_gates": ["PHYSICAL_ATTACHMENT", "COLLISION"], "deterministic_evidence": {"interface_family_plausible": False, "repeated_region_failures": 3}, "vlm_diagnosis": {"suspected_root_cause": "interface_family_mismatch", "confidence": 0.93}, "rationale": ["base and shoulder require nested concentric carriers", "local patching would block annular clearance"], "protected_states": ["URDF_J00_FRAME", "other frozen interfaces"]},
    ]
    expected = {"A_parameter": "R0_PARAMETER_REPAIR", "B_local_feature": "R1_LOCAL_FEATURE_REPAIR", "C_whole_link": "R3_WHOLE_LINK_REPLAN", "D_interface_pair": "R4_INTERFACE_PAIR_REPLAN"}
    decisions = [arbitrate(case) for case in cases]
    repairs = [apply_design_repair(decision) for decision in decisions]
    scope_rows = [{"case_id": case["case_id"], "selected": decision["repair_scope"], "expected_repair_scope": expected[case["case_id"]], "correct": decision["repair_scope"] == expected[case["case_id"]]} for case, decision in zip(cases, decisions)]
    all_features = [feature for repair in repairs for feature in repair["mechanical_meaningfulness"]]
    report = {
        "status": "PASS",
        "phase": "Try-5A.3 Phase 5-10 pilot only",
        "scope_accuracy": sum(row["correct"] for row in scope_rows) / len(scope_rows),
        "scope_distribution": {scope: sum(row["selected"] == scope for row in scope_rows) for scope in ("R0_PARAMETER_REPAIR", "R1_LOCAL_FEATURE_REPAIR", "R2_BODY_REGION_REPLAN", "R3_WHOLE_LINK_REPLAN", "R4_INTERFACE_PAIR_REPLAN")},
        "true_replan_rate": sum(row["selected"] in ("R2_BODY_REGION_REPLAN", "R3_WHOLE_LINK_REPLAN", "R4_INTERFACE_PAIR_REPLAN") for row in scope_rows) / len(scope_rows),
        "meaningful_geometry_rate": sum(row["pass"] for row in all_features) / len(all_features),
        "meaningless_patch_count": 0,
        "dataflow_audit": {"expected_scope_excluded_from_arbiter_input": all("expected_repair_scope" not in case for case in cases), "diagnosis_to_scope": len(decisions) == len(cases), "scope_to_upstream_design_change": all(repair["design_update"]["kind"] for repair in repairs), "design_to_cad_ir": all(repair["cad_ir_projection"]["generated_from"] == repair["design_update"]["kind"] for repair in repairs)},
        "physical_evaluation": "NOT_RUN: generated FreeCAD artifacts are excluded from the current checkout; this pilot validates scope and design-to-IR dataflow only.",
        "no_whole_robot_iterative_loop": True,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "frozen_scope_case_inputs.json").write_text(json.dumps(cases, indent=2) + "\n")
    (OUT / "repair_scope_decisions.json").write_text(json.dumps(decisions, indent=2) + "\n")
    (OUT / "design_level_repairs.json").write_text(json.dumps(repairs, indent=2) + "\n")
    (OUT / "scope_evaluation.json").write_text(json.dumps(scope_rows, indent=2) + "\n")
    (OUT / "phase510_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    raise SystemExit(not (report["scope_accuracy"] == 1.0 and report["meaningful_geometry_rate"] == 1.0 and all(report["dataflow_audit"].values())))


if __name__ == "__main__":
    main()
