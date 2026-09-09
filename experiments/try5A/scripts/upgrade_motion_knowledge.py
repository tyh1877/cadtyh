"""Upgrade and validate the canonical interface knowledge with motion semantics."""

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATH = ROOT / "try5/knowledge/robot_interfaces/families.json"


COMMON_ROTARY = {
    "joint_semantics": {
        "compatible_joint_types": ["revolute", "continuous"],
        "allowed_dof": ["rotation_about_urdf_axis"],
        "constrained_dof": ["translation_x", "translation_y", "translation_z", "rotation_about_two_orthogonal_axes"],
        "motion_axis_source": "sanitized_urdf_joint_axis",
        "motion_range_semantics": "sample the sanitized URDF limits; use [-pi, pi] only as an explicit continuous-joint evaluation proxy",
    },
    "motion_preserving_constraints": {
        "radial_clearance": "positive radial gap around the rotating carrier",
        "axial_clearance": "positive side gap between parent supports and child carrier",
        "swept_clearance": "exclude parent/neighbor body from the generated child swept occupancy",
        "required_clearance_regions": ["rotating_carrier_radial_envelope", "carrier_side_faces", "child_link_swept_corridor"],
    },
}


FAMILY_RULES = {
    "fork_pin_interface": {
        "parent_side": {"members": ["fork_left", "fork_right", "parent_support"], "rigid_attachment": "both fork arms and support are rigidly attached to the parent body"},
        "child_side": {"members": ["central_boss", "child_neck"], "rigid_attachment": "boss connects to the child body through a structural neck"},
        "parent_child_relation": {"allowed_contact_regions": ["optional pin/bore bearing surface"], "clearance_regions": ["boss-to-fork side gaps", "fork opening"], "never_fuse": ["fork_left:central_boss", "fork_right:central_boss", "parent_rigid_group:child_rigid_group"], "relative_motion_rule": "child rotates relative to parent only about the URDF axis"},
        "cad_construction_logic": ["construct symmetric parent fork supports", "construct child boss between supports", "align all carrier axes to the URDF axis", "leave positive axial and radial clearance", "attach each carrier only to its owning body"],
    },
    "coaxial_rotary_interface": {
        "parent_side": {"members": ["paired_bearing_supports", "parent_housing_neck"], "rigid_attachment": "bearing supports and neck belong to the parent rigid group"},
        "child_side": {"members": ["inner_rotor_boss", "child_neck"], "rigid_attachment": "rotor boss is rigidly connected to the child body"},
        "parent_child_relation": {"allowed_contact_regions": ["optional coaxial bearing surface"], "clearance_regions": ["annular_gap", "axial_side_gaps"], "never_fuse": ["bearing_supports:inner_rotor_boss", "parent_rigid_group:child_rigid_group"], "relative_motion_rule": "inner child carrier rotates about the URDF axis inside parent supports"},
        "cad_construction_logic": ["construct parent bearing supports outside the motion corridor", "construct coaxial child rotor", "protect annular and axial gaps", "attach carriers to owning bodies only"],
    },
    "nested_rotary_housing": {
        "parent_side": {"members": ["outer_housing", "parent_support"], "rigid_attachment": "outer housing is continuous with the parent body"},
        "child_side": {"members": ["inner_rotating_carrier", "child_support"], "rigid_attachment": "inner carrier is continuous with the child body"},
        "parent_child_relation": {"allowed_contact_regions": ["optional bearing race"], "clearance_regions": ["annular_shell_gap", "axial_end_gap"], "never_fuse": ["outer_housing:inner_rotating_carrier", "parent_rigid_group:child_rigid_group"], "relative_motion_rule": "nested child carrier rotates about the URDF axis without a radial bridge"},
        "cad_construction_logic": ["construct concentric outer and inner envelopes", "subtract a protected annular gap", "route body supports outside the swept corridor", "keep housings in separate rigid groups"],
    },
    "rail_slider_interface": {
        "joint_semantics": {"compatible_joint_types": ["prismatic"], "allowed_dof": ["translation_along_urdf_axis"], "constrained_dof": ["two_orthogonal_translations", "rotation_x", "rotation_y", "rotation_z"], "motion_axis_source": "sanitized_urdf_joint_axis", "motion_range_semantics": "sample the sanitized URDF lower and upper translation limits"},
        "parent_side": {"members": ["guide_rail", "parent_rail_support"], "rigid_attachment": "rail and support are rigidly attached to the parent body"},
        "child_side": {"members": ["sliding_carriage", "child_mount"], "rigid_attachment": "carriage mount is rigidly attached to the child body"},
        "parent_child_relation": {"allowed_contact_regions": ["guide_bearing_surfaces"], "clearance_regions": ["travel_corridor", "rail_side_clearance"], "never_fuse": ["guide_rail:sliding_carriage", "parent_rigid_group:child_rigid_group"], "relative_motion_rule": "child translates only along the URDF axis"},
        "motion_preserving_constraints": {"radial_clearance": "positive guide side clearance", "axial_clearance": "not applicable to travel direction", "swept_clearance": "keep the complete URDF travel corridor free", "required_clearance_regions": ["carriage_travel_corridor", "finger_neighbor_corridor"]},
        "cad_construction_logic": ["construct parent rail", "construct keyed child carriage", "attach each to its own body", "reserve the full translated swept corridor"],
    },
    "flange_interface": {
        "joint_semantics": {"compatible_joint_types": ["fixed"], "allowed_dof": [], "constrained_dof": ["all_relative_translation", "all_relative_rotation"], "motion_axis_source": "not_applicable", "motion_range_semantics": "fixed transform only"},
        "parent_side": {"members": ["parent_flange"], "rigid_attachment": "flange is integrated into the parent body"},
        "child_side": {"members": ["child_flange"], "rigid_attachment": "flange is integrated into the child body"},
        "parent_child_relation": {"allowed_contact_regions": ["mating_flange_faces"], "clearance_regions": [], "never_fuse": [], "relative_motion_rule": "no relative motion after fixed assembly"},
        "motion_preserving_constraints": {"radial_clearance": "not applicable", "axial_clearance": "zero intended mating-face gap", "swept_clearance": "fixed occupancy only", "required_clearance_regions": []},
        "cad_construction_logic": ["construct aligned mating faces", "attach each face to its owning body", "represent fixed fastening without inventing detailed hardware"],
    },
    "planar_mount_interface": {
        "joint_semantics": {"compatible_joint_types": ["fixed"], "allowed_dof": [], "constrained_dof": ["all_relative_translation", "all_relative_rotation"], "motion_axis_source": "not_applicable", "motion_range_semantics": "fixed transform only"},
        "parent_side": {"members": ["parent_mount_pad", "support_web"], "rigid_attachment": "mount pad and web form a parent-body load path"},
        "child_side": {"members": ["child_mount_pad"], "rigid_attachment": "child pad is continuous with the child body"},
        "parent_child_relation": {"allowed_contact_regions": ["mating_mount_planes"], "clearance_regions": [], "never_fuse": [], "relative_motion_rule": "no relative motion after fixed assembly"},
        "motion_preserving_constraints": {"radial_clearance": "not applicable", "axial_clearance": "zero intended mating-plane gap", "swept_clearance": "fixed occupancy only", "required_clearance_regions": []},
        "cad_construction_logic": ["construct mating pads", "connect pads to owning bodies", "preserve the frozen fixed transform"],
    },
    "end_tool_interface": {
        "joint_semantics": {"compatible_joint_types": ["fixed_virtual"], "allowed_dof": [], "constrained_dof": ["all_relative_translation", "all_relative_rotation"], "motion_axis_source": "not_applicable", "motion_range_semantics": "metadata frame follows the physical parent"},
        "parent_side": {"members": ["physical_tool_carrier", "frame_anchor"], "rigid_attachment": "frame anchor belongs to the physical parent"},
        "child_side": {"members": ["virtual_tool_frame"], "rigid_attachment": "no child solid is generated"},
        "parent_child_relation": {"allowed_contact_regions": [], "clearance_regions": [], "never_fuse": [], "relative_motion_rule": "virtual frame follows the parent rigid transform"},
        "motion_preserving_constraints": {"radial_clearance": "not applicable", "axial_clearance": "not applicable", "swept_clearance": "virtual frame has no occupancy", "required_clearance_regions": []},
        "cad_construction_logic": ["retain the tool frame as metadata", "anchor metadata to the parent rigid group", "generate no virtual-frame solid"],
    },
}


def upgrade(payload):
    payload["schema_version"] = "try5A4_robot_interface_motion_knowledge_v2"
    payload["motion_realization_scope"] = "generic parametric construction knowledge; no robot-specific dimensions or ground-truth internals"
    for entry in payload["families"]:
        family = entry["interface_family"]
        rules = FAMILY_RULES[family]
        if family in ("fork_pin_interface", "coaxial_rotary_interface", "nested_rotary_housing"):
            entry.update(COMMON_ROTARY)
        entry.update(rules)
        entry["verification"] = {
            "attachment_rules": ["parent carrier attached to parent body", "child carrier attached to child body"],
            "axis_rules": ["axis angular error within evaluator tolerance", "joint center within evaluator tolerance"],
            "separation_rules": ["parent and child remain separate top-level rigid groups", "all forbidden fusion pairs absent"],
            "clearance_rules": entry["motion_preserving_constraints"]["required_clearance_regions"],
            "motion_validation_rule": "apply URDF FK rigid-group transforms at every frozen pose and accept only exact-collision-valid samples",
        }
        extra_forbidden = [
            "Boolean Fuse between parent and child rigid groups",
            "solid bridge crossing an allowed-motion clearance",
            "connector that locks the intended degree of freedom",
        ]
        entry["forbidden_configurations"] = list(dict.fromkeys(entry.get("forbidden_configurations", []) + extra_forbidden))
    return payload


def validate(payload):
    required = ("joint_semantics", "parent_side", "child_side", "parent_child_relation", "motion_preserving_constraints", "cad_construction_logic", "verification")
    errors = []
    for entry in payload["families"]:
        missing = [key for key in required if key not in entry]
        if missing:
            errors.append({"family": entry["interface_family"], "missing": missing})
    return errors


def main():
    payload = json.loads(PATH.read_text(encoding="utf-8"))
    if "--check" not in sys.argv:
        payload = upgrade(payload)
        PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    errors = validate(payload)
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "family_count": len(payload["families"]), "errors": errors}, indent=2))
    raise SystemExit(bool(errors))


if __name__ == "__main__":
    main()
