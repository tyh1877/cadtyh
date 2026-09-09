"""Hierarchical, deterministic repair-scope arbitration for Try-5A.3."""

SCOPES = ("R0_PARAMETER_REPAIR", "R1_LOCAL_FEATURE_REPAIR", "R2_BODY_REGION_REPLAN", "R3_WHOLE_LINK_REPLAN", "R4_INTERFACE_PAIR_REPLAN", "R5_SUBASSEMBLY_REPLAN")


def arbitrate(case):
    """Classify repair scope from evidence only.  Evaluation labels are excluded."""
    failures = case["failed_gates"]
    evidence = case["deterministic_evidence"]
    diagnosis = case.get("vlm_diagnosis", {})
    cause = diagnosis.get("suspected_root_cause", "")

    if cause == "subassembly_layout_mismatch" or evidence.get("functional_subassembly_valid") is False:
        scope = "R5_SUBASSEMBLY_REPLAN"
        upstream = ["SubassemblyPlan", "member LinkCoarseSpecs", "internal InterfaceContracts"]
    elif cause == "interface_family_mismatch" or evidence.get("interface_family_plausible") is False:
        scope = "R4_INTERFACE_PAIR_REPLAN"
        upstream = ["InterfaceContract", "parent_local_region", "child_local_region"]
    elif evidence.get("body_topology_valid") is False or cause == "body_family_mismatch":
        scope = "R3_WHOLE_LINK_REPLAN"
        upstream = ["LinkCoarseSpec.body_family", "LinkCoarseSpec.structural_path"]
    elif evidence.get("repeated_region_failures", 0) >= 2 or cause == "body_region_family_mismatch":
        scope = "R2_BODY_REGION_REPLAN"
        upstream = ["BodyRegionSpec"]
    elif evidence.get("localized_feature_failure") or cause in ("local_clearance_failure", "local_transition_failure"):
        scope = "R1_LOCAL_FEATURE_REPAIR"
        upstream = ["BodyRegionSpec.local_feature"]
    elif evidence.get("topology_valid") and evidence.get("parameter_delta_within_tolerance"):
        scope = "R0_PARAMETER_REPAIR"
        upstream = ["LinkCoarseSpec.parameters"]
    else:
        raise ValueError("insufficient evidence to choose a safe repair scope")

    return {
        "target": case["target"],
        "failed_gates": failures,
        "deterministic_evidence": evidence,
        "vlm_diagnosis": diagnosis,
        "repair_scope": scope,
        "reason": "; ".join(case["rationale"]) + "; selected from deterministic failure hierarchy",
        "protected_states": case["protected_states"],
        "upstream_objects_to_modify": upstream,
    }
