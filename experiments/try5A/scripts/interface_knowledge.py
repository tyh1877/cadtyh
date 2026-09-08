"""Generic Try-5A.3 interface knowledge retrieval; no robot-specific geometry."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
KNOWLEDGE_PATH = ROOT / "try5/knowledge/robot_interfaces/families.json"


def load_knowledge():
    data = json.loads(KNOWLEDGE_PATH.read_text(encoding="utf-8"))
    return {entry["interface_family"]: entry for entry in data["families"]}


def legacy_family(joint_type, parent, child):
    if joint_type == "prismatic":
        return "linear_slider_interface"
    if joint_type == "fixed":
        return "planar_mount_interface"
    if parent["body_family"] in ("dual_side_plate", "fork_body") or child["body_family"] in ("dual_side_plate", "fork_body"):
        return "fork_pin_interface"
    return "coaxial_rotary_interface"


def rank_candidates(joint, parent, child, knowledge=None):
    """Return deterministic, explainable rankings; expected scope/GT is never read."""
    knowledge = knowledge or load_knowledge()
    jt = joint["joint_type"]
    parent_role, child_role = parent["role"], child["role"]
    candidates = []

    def add(family, score, evidence):
        if family in knowledge:
            candidates.append({
                "family": family,
                "score": score,
                "evidence": evidence,
                "knowledge_match": knowledge[family]["applicability"],
            })

    if child["body_family"] == "interface_marker" or "tool_center_frame" in child_role:
        add("end_tool_interface", 1.0, ["child is a virtual/tool reference frame", "knowledge forbids child solid generation"])
    elif jt == "prismatic":
        add("rail_slider_interface", 0.98, ["URDF joint is prismatic", "translation axis and travel limits require guided clearance"])
    elif jt == "fixed":
        add("planar_mount_interface", 0.92, ["URDF joint is fixed", "roles form a structural mount"])
        if any(token in (parent_role + child_role) for token in ("tool", "actuator")):
            add("flange_interface", 0.66, ["fixed tool/actuator-adjacent mount", "fastener detail remains unsupported"])
    else:
        fork_evidence = parent["body_family"] in ("dual_side_plate", "fork_body") or child["body_family"] in ("dual_side_plate", "fork_body")
        nested_evidence = parent["body_family"] in ("base_housing", "rotary_housing") and child["body_family"] in ("rotary_housing", "wrist_block")
        if fork_evidence:
            add("fork_pin_interface", 0.95, ["revolute/continuous joint", "dual-side/fork body family in planned link"])
        if nested_evidence:
            add("nested_rotary_housing", 0.94, ["revolute joint", "concentric housing roles on both sides"])
        add("coaxial_rotary_interface", 0.74, ["revolute/continuous joint", "URDF axis supports coaxial carrier"])

    candidates.sort(key=lambda item: (-item["score"], item["family"]))
    if not candidates:
        return [{"family": "CUSTOM_INTERFACE", "score": 0.0, "evidence": ["no generic knowledge family applies"], "knowledge_match": "none"}]
    return candidates


def selection_record(joint, parent, child, knowledge=None):
    ranked = rank_candidates(joint, parent, child, knowledge)
    selected = ranked[0]
    return {
        "joint_id": joint["joint_id"],
        "candidate_interfaces": [{k: value for k, value in entry.items() if k != "score"} | {"confidence": entry["score"]} for entry in ranked],
        "selected_family": selected["family"],
        "selection_reason": "; ".join(selected["evidence"]),
        "uncertainty": "coarse visual/role evidence; no GT geometry or dimensions consumed",
        "knowledge_source": str(KNOWLEDGE_PATH.relative_to(ROOT)).replace("\\", "/"),
    }
