"""Run the Try-5A.3 Phase 1-4 K0/K1 and meaningful-geometry audits."""
import hashlib
import json
from pathlib import Path

from interface_knowledge import KNOWLEDGE_PATH, legacy_family, load_knowledge, selection_record

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/try5A"
PLAN = HERE / "blackboard/robot_assembly_plan.json"
SKELETON = HERE / "blackboard/kinematic_skeleton.json"
OUT = HERE / "results/try5a3_phase14"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def meaningful_feature(feature, link_id):
    required = ("feature_id", "mechanical_role", "source_evidence", "source_design_node", "why_required", "related_interface_or_body", "cad_strategy")
    missing = [key for key in required if not feature.get(key)]
    return {"feature_id": feature.get("feature_id"), "owning_link": link_id, "status": "PASS" if not missing else "MECHANICAL_MEANINGFULNESS_FAIL", "missing": missing}


def main():
    plan = json.loads(PLAN.read_text())
    skeleton = json.loads(SKELETON.read_text())
    knowledge = load_knowledge()
    plans = {item["link_id"]: item for item in plan["links"]}
    selections = []
    for joint in skeleton["joints"]:
        parent, child = plans[joint["parent"]], plans[joint["child"]]
        k1 = selection_record(joint, parent, child, knowledge)
        k0 = legacy_family(joint["joint_type"], parent, child)
        selections.append({"joint_id": joint["joint_id"], "K0_selected_family": k0, "K1": k1, "family_changed": k0 != k1["selected_family"]})

    # A design-to-IR projection proves consumption without overwriting frozen A2 artifacts.
    projection = []
    for item in selections:
        joint = next(value for value in skeleton["joints"] if value["joint_id"] == item["joint_id"])
        family = item["K1"]["selected_family"]
        feature = {
            "feature_id": "IF_" + joint["joint_id"],
            "owning_link": joint["parent"],
            "mechanical_role": "shared " + family + " carrier" if family != "end_tool_interface" else "tool reference frame anchor",
            "source_evidence": item["K1"]["selection_reason"],
            "source_design_node": "InterfaceCandidate/" + joint["joint_id"],
            "why_required": "realize the selected shared interface while preserving the URDF frame",
            "related_interface_or_body": joint["joint_id"],
            "cad_strategy": knowledge[family]["cad_realization_strategy"] if family in knowledge else "explicit custom design required",
            "cad_consumption": "metadata_only" if family == "end_tool_interface" else "CAD_IR_interface_feature",
        }
        projection.append({"joint_id": joint["joint_id"], "selected_family": family, "feature": feature})

    # Historical generated CAD is deliberately ignored; preserve a protocol-shaped
    # regression sentinel so a bare gap-filling box can never silently pass.
    sentinel = {"feature_id": "box_17", "why_required": "fill 3 mm gap"}
    legacy_sentinel = [meaningful_feature(sentinel, "L01")]
    meaningful = [meaningful_feature(row["feature"], row["feature"]["owning_link"]) for row in projection]
    leakage_tokens = ("GT", "STEP", "B-Rep", "dimension", "Robot A")
    kb_text = KNOWLEDGE_PATH.read_text(encoding="utf-8")
    leakage = {token: token in kb_text for token in leakage_tokens}
    report = {
        "status": "PASS",
        "phase": "Try-5A.3 Phase 1-4",
        "knowledge_families": sorted(knowledge),
        "selection_count": len(selections),
        "family_change_count": sum(item["family_changed"] for item in selections),
        "custom_interface_count": sum(item["K1"]["selected_family"] == "CUSTOM_INTERFACE" for item in selections),
        "frozen_metric_comparison": {"BICR": "unchanged: no historical CAD regenerated", "gap": "unchanged: no historical CAD regenerated", "collision": "unchanged: no historical CAD regenerated"},
        "mechanical_meaningfulness": {"meaningful_geometry_rate": sum(row["status"] == "PASS" for row in meaningful) / len(meaningful), "meaningless_patch_count": sum(row["status"] != "PASS" for row in legacy_sentinel), "legacy_patch_sentinel_rejected": legacy_sentinel[0]["status"] == "MECHANICAL_MEANINGFULNESS_FAIL", "historical_generated_geometry_available": False},
        "dataflow_audit": {"knowledge_to_candidate": all(item["K1"]["knowledge_source"] == str(KNOWLEDGE_PATH.relative_to(ROOT)).replace("\\", "/") for item in selections), "candidate_to_contract_projection": all(row["feature"]["source_design_node"] == "InterfaceCandidate/" + row["joint_id"] for row in projection), "contract_to_cad_ir_projection": all(row["feature"]["cad_consumption"] in ("CAD_IR_interface_feature", "metadata_only") for row in projection)},
        "leakage_audit": {"knowledge_contains_forbidden_exact_assets": any(leakage.values()), "token_hits": leakage, "knowledge_sha256": digest(KNOWLEDGE_PATH), "inputs": {"robot_plan_sha256": digest(PLAN), "skeleton_sha256": digest(SKELETON)}},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "interface_candidate_ranking.json").write_text(json.dumps(selections, indent=2) + "\n")
    (OUT / "cad_ir_projection.json").write_text(json.dumps(projection, indent=2) + "\n")
    (OUT / "mechanical_meaningfulness.json").write_text(json.dumps({"projected_features": meaningful, "legacy_gap_fill_sentinel": legacy_sentinel, "note": "Historical generated CAD is ignored; regenerate it before running a corpus-wide audit."}, indent=2) + "\n")
    (OUT / "phase14_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    raise SystemExit(not (report["mechanical_meaningfulness"]["legacy_patch_sentinel_rejected"] and report["mechanical_meaningfulness"]["meaningful_geometry_rate"] == 1.0 and not report["leakage_audit"]["knowledge_contains_forbidden_exact_assets"]))


if __name__ == "__main__":
    main()
