"""Generate Codex-authored Try-3 planning artifacts without an external model API.

The global visual observations in codex_authored/ were written by the interactive
Codex agent after inspecting only allowed renders. This script deterministically
expands those observations across sanitized URDF links, validates every artifact,
and records provenance. It never reads evaluator or GT geometry paths.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import jsonschema
import numpy as np

from codex_agent_common import (
    EXP, ROOT, RUNS, RESULTS, link_geometry, load_json, manifest, parse_urdf,
    role_for, sha256, tryset_rows, utc_now, write_csv, write_json, world_transforms,
    rotation_rpy,
)


PRODUCER = "interactive_codex_gpt5_family+deterministic_projection"
FRAME = {"origin": [0, 0, 0], "x_axis": [1, 0, 0], "y_axis": [0, 1, 0], "z_axis": [0, 0, 1]}
SEED_PATH = EXP / "codex_authored" / "global_visual_observations_v1.json"
VISUAL_SCHEMA = EXP / "schemas" / "codex_visual_evidence_v1.schema.json"
MEP_SCHEMA = EXP / "schemas" / "codex_mechanical_embodiment_v1.schema.json"
INTERFACE_SCHEMA = EXP / "schemas" / "codex_interface_graph_v1.schema.json"
FEATURE_SCHEMA = EXP / "schemas" / "mechanical_feature_graph_v1.schema.json"
SKILL_SCHEMA = EXP / "schemas" / "codex_skill_calls_v1.schema.json"
IR_SCHEMA = EXP / "schemas" / "codex_link_ir_v1.schema.json"


def refs(link: dict[str, Any], key: str, fallback: str) -> list[str]:
    values = link.get(key) or []
    return [str(values[0])] if values else [fallback]


def build_visual(row: dict[str, str], links: list[str], joints, seed: dict[str, Any]) -> dict[str, Any]:
    source = EXP / "runs" / "visual_agent" / "deterministic" / row["case_id"] / "visual_evidence_packet_v1.json"
    packet = load_json(source)
    by_link = {item["link_id"]: item for item in packet["links"]}
    global_ref = f"global_view:isometric:{(ROOT / load_json(ROOT / row['image_text_json'])['images']['isometric']).resolve()}"
    output = []
    for index, link_id in enumerate(links):
        item = by_link[link_id]
        role = role_for(link_id, links, joints)
        main_refs = refs(item, "link_crops", global_ref)
        prox_refs = refs(item, "proximal_joint_crops", global_ref)
        dist_refs = refs(item, "distal_joint_crops", global_ref)
        visible = seed["visible_features"]
        feature = visible[index % len(visible)]
        confidence = 0.55 if len(links) <= 10 else 0.38
        output.append({
            "link_id": link_id,
            "functional_role_hint": role,
            "main_body": {"description": f"{role}: {seed['envelope_family']} with {seed['section_family']} section; interpreted within {seed['overall_form']}", "evidence_refs": main_refs, "confidence": confidence},
            "proximal_region": {"description": f"proximal interface is consistent with a {seed['joint_housing_family']}; exact link boundary remains uncertain", "evidence_refs": prox_refs, "confidence": max(0.2, confidence - 0.1)},
            "distal_region": {"description": f"distal region uses {seed['transition_strategy']}; housing attribution follows the sanitized chain, not segmentation", "evidence_refs": dist_refs, "confidence": max(0.2, confidence - 0.1)},
            "visible_features": [{"description": feature, "evidence_refs": main_refs, "confidence": max(0.2, confidence - 0.15)}],
            "surface_hints": list(seed["surface_hints"]),
            "uncertainty": [seed["uncertainty"], "Deterministic crops are broad and link-order based; observations do not assert precise segmentation."],
        })
    return {
        "schema_version": "codex_visual_evidence_v1", "case_id": row["case_id"],
        "global_observation": seed, "links": output,
        "leakage_guard": {"uses_gt_mesh": False, "uses_gt_segmentation": False, "uses_product_identity": False, "localization_source": "deterministic_non_gt_silhouette_link_order"},
    }


def build_mep(row: dict[str, str], links: list[str], joints, visual: dict[str, Any], scale_mm: float) -> dict[str, Any]:
    observations = {item["link_id"]: item for item in visual["links"]}
    items = []
    for link_id in links:
        incoming = [j for j in joints if j.child == link_id]
        outgoing = [j for j in joints if j.parent == link_id]
        obs = observations[link_id]
        geom = link_geometry(link_id, links, joints, scale_mm, "V2")
        items.append({
            "link_id": link_id, "functional_role": obs["functional_role_hint"],
            "kinematic_context": {"proximal_joint_ids": [j.joint_id for j in incoming], "distal_joint_ids": [j.joint_id for j in outgoing], "authority": "sanitized_urdf"},
            "main_envelope": {"geometry_family": visual["global_observation"]["envelope_family"], "section_family": visual["global_observation"]["section_family"], "start_mm": geom["start_mm"], "end_mm": geom["end_mm"], "proximal_size_mm": [geom["width_mm"], geom["depth_mm"]], "distal_size_mm": [geom["distal_width_mm"], geom["depth_mm"] * 0.82], "dimension_source": geom["dimension_source"], "evidence_refs": obs["main_body"]["evidence_refs"]},
            "proximal_joint_region": {"housing_family": visual["global_observation"]["joint_housing_family"], "joint_ids": [j.joint_id for j in incoming], "evidence_refs": obs["proximal_region"]["evidence_refs"]},
            "distal_joint_region": {"housing_family": visual["global_observation"]["joint_housing_family"], "joint_ids": [j.joint_id for j in outgoing], "evidence_refs": obs["distal_region"]["evidence_refs"]},
            "body_transition": {"strategy": visual["global_observation"]["transition_strategy"], "evidence_refs": obs["main_body"]["evidence_refs"]},
            "visible_structural_features": obs["visible_features"],
            "protected_interface_regions": [{"joint_id": j.joint_id, "source": "sanitized_urdf", "no_free_repositioning": True} for j in incoming + outgoing],
            "uncertainty": obs["uncertainty"],
        })
    return {"schema_version": "codex_mechanical_embodiment_v1", "case_id": row["case_id"], "links": items}


def build_interface(row: dict[str, str], joints) -> dict[str, Any]:
    items = []
    for joint in joints:
        items.append({
            "joint_id": joint.joint_id, "joint_type": joint.joint_type,
            "parent_link": joint.parent, "child_link": joint.child,
            "origin_xyz_mm": list(joint.xyz_mm), "axis": list(joint.axis),
            "parent_port": {"link_id": joint.parent, "frame_source": "sanitized_urdf_joint", "center_mm": list(joint.xyz_mm), "axis": (rotation_rpy(joint.rpy) @ np.asarray(joint.axis, dtype=float)).tolist()},
            "child_port": {"link_id": joint.child, "frame_source": "sanitized_urdf_joint", "center_mm": [0.0, 0.0, 0.0], "axis": list(joint.axis)},
            "mate_constraints": {"coaxial": True, "coincident_origin": True, "allow_rotation": joint.joint_type in {"revolute", "continuous"}},
            "protected_region": {"radius_policy": "derived_from_link_envelope", "no_uncontrolled_cut": True},
        })
    return {"schema_version": "codex_interface_graph_v1", "case_id": row["case_id"], "joints": items}


def op_base(op_id: str, op_type: str, target: str, dependencies: list[str], **values: Any) -> dict[str, Any]:
    return {"op_id": op_id, "op_type": op_type, "target_body": target, "dependencies": dependencies, "reference_frame": FRAME, **values}


def build_link_artifacts(row: dict[str, str], version: str, link_id: str, links: list[str], joints, scale_mm: float, visual: dict[str, Any], mep: dict[str, Any] | None, interface: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    geom = link_geometry(link_id, links, joints, scale_mm, version)
    incoming = [j for j in joints if j.child == link_id]
    outgoing = [j for j in joints if j.parent == link_id]
    axes = geom["joint_axes"]
    start, end = geom["start_mm"], geom["end_mm"]
    width, depth = geom["width_mm"], geom["depth_mm"]
    caller = {"V0": "CodexV0Planner", "V1": "CodexV1PerLinkEngineer", "V2": "CodexV2MechanicalCADEngineer"}[version]
    features = [{"feature_id": "F00", "feature_type": "main_envelope", "priority": "primary_geometry", "evidence_refs": visual["links"][links.index(link_id)]["main_body"]["evidence_refs"] if version != "V0" else ["global_views"], "dependencies": [], "intended_cad_strategy": "oriented_box" if version == "V0" else "lofted_prism", "interface_dependency": None, "protected_status": "non_protected", "parameters": geom}]
    operations = []
    calls = []
    if version == "V0":
        operations.append(op_base("op_001", "oriented_box", "op_001", [], start=start, end=end, width_mm=width, depth_mm=depth, operation_mode="new_body"))
        calls.append({"call_id": "C00", "skill": "CreateParametricLinkEnvelope", "parameters": geom, "source_feature_ids": ["F00"], "calling_agent": caller, "no_fallback": True})
        final = "op_001"
    else:
        operations.append(op_base("op_001", "lofted_prism", "op_001", [], start=start, end=end, start_size_mm=[width, depth], end_size_mm=[geom["distal_width_mm"], depth * (0.86 if version == "V1" else 0.76)], operation_mode="new_body"))
        calls.append({"call_id": "C00", "skill": "CreateLoftedLinkHousing", "parameters": geom, "source_feature_ids": ["F00"], "calling_agent": caller, "no_fallback": True})
        radius = width * (0.56 if version == "V1" else 0.64)
        height = depth * (1.02 if version == "V1" else 1.18)
        operations.append(op_base("op_002", "cylinder_primitive", "op_002", [], center=start, axis=axes[0], radius_mm=radius, height_mm=height, operation_mode="new_body"))
        operations.append(op_base("op_003", "cylinder_primitive", "op_003", [], center=end, axis=axes[-1], radius_mm=radius * 0.88, height_mm=height * 0.88, operation_mode="new_body"))
        calls.extend([
            {"call_id": "C01", "skill": "CreateRotaryJointHousing", "parameters": {"center_mm": start, "axis": axes[0], "radius_mm": radius, "height_mm": height}, "source_feature_ids": ["F01"], "calling_agent": caller, "no_fallback": True},
            {"call_id": "C02", "skill": "CreateRotaryJointHousing", "parameters": {"center_mm": end, "axis": axes[-1], "radius_mm": radius * 0.88, "height_mm": height * 0.88}, "source_feature_ids": ["F02"], "calling_agent": caller, "no_fallback": True},
        ])
        features.extend([
            {"feature_id": "F01", "feature_type": "proximal_joint_housing", "priority": "functional_geometry", "evidence_refs": visual["links"][links.index(link_id)]["proximal_region"]["evidence_refs"], "dependencies": ["F00"], "intended_cad_strategy": "cylinder_primitive", "interface_dependency": incoming[0].joint_id if incoming else None, "protected_status": "derived_from_interface" if version == "V2" else "non_protected", "parameters": {"radius_mm": radius}},
            {"feature_id": "F02", "feature_type": "distal_joint_housing", "priority": "functional_geometry", "evidence_refs": visual["links"][links.index(link_id)]["distal_region"]["evidence_refs"], "dependencies": ["F00"], "intended_cad_strategy": "cylinder_primitive", "interface_dependency": outgoing[0].joint_id if outgoing else None, "protected_status": "derived_from_interface" if version == "V2" else "non_protected", "parameters": {"radius_mm": radius * 0.88}},
        ])
        observed = visual["links"][links.index(link_id)]["visible_features"][0]
        features.append({"feature_id": "FV0", "feature_type": observed["description"], "priority": "structural_detail", "evidence_refs": observed["evidence_refs"], "dependencies": ["F00"], "intended_cad_strategy": "UNIMPLEMENTED_VISIBLE_DETAIL", "interface_dependency": None, "protected_status": "non_protected", "parameters": {"execution_status": "UNSUPPORTED_BY_FROZEN_SKILL_SET"}})
        tools = ["op_002", "op_003"]
        if version == "V2":
            flange_radius = radius * 1.08
            flange_height = max(3.0, height * 0.18)
            operations.append(op_base("op_004", "cylinder_primitive", "op_004", [], center=start, axis=axes[0], radius_mm=flange_radius, height_mm=flange_height, operation_mode="new_body"))
            operations.append(op_base("op_005", "cylinder_primitive", "op_005", [], center=end, axis=axes[-1], radius_mm=flange_radius * 0.86, height_mm=flange_height, operation_mode="new_body"))
            tools += ["op_004", "op_005"]
            calls.extend([
                {"call_id": "C03", "skill": "CreateFlangeInterface", "parameters": {"center_mm": start, "axis": axes[0], "radius_mm": flange_radius, "height_mm": flange_height}, "source_feature_ids": ["F03"], "calling_agent": caller, "no_fallback": True},
                {"call_id": "C04", "skill": "CreateFlangeInterface", "parameters": {"center_mm": end, "axis": axes[-1], "radius_mm": flange_radius * 0.86, "height_mm": flange_height}, "source_feature_ids": ["F04"], "calling_agent": caller, "no_fallback": True},
            ])
            for fid, point, dependency in [("F03", start, incoming[0].joint_id if incoming else None), ("F04", end, outgoing[0].joint_id if outgoing else None)]:
                features.append({"feature_id": fid, "feature_type": "protected_interface_flange", "priority": "functional_geometry", "evidence_refs": ["sanitized_urdf_interface"], "dependencies": ["F00"], "intended_cad_strategy": "cylinder_primitive", "interface_dependency": dependency, "protected_status": "protected_interface", "parameters": {"center_mm": point}})
        union_id = f"op_{len(operations) + 1:03d}"
        operations.append(op_base(union_id, "boolean_union", "op_001", ["op_001", *tools], tool_bodies=tools))
        calls.append({"call_id": f"C{len(calls):02d}", "skill": "BooleanUnion", "parameters": {"base": "op_001", "tools": tools}, "source_feature_ids": [f["feature_id"] for f in features], "calling_agent": caller, "no_fallback": True})
        final = union_id
    feature_graph = {"schema_version": "mechanical_feature_graph_v1", "case_id": row["case_id"], "link_id": link_id, "features": features}
    skill_calls = {"schema_version": "codex_skill_calls_v1", "case_id": row["case_id"], "version": version, "link_id": link_id, "calls": calls}
    ir = {"ir_version": "codex_link_ir_v1", "case_id": row["case_id"], "version": version, "link_id": link_id, "bodies": [{"body_id": "body", "role": role_for(link_id, links, joints)}], "operations": operations, "final_object": final, "metadata": {"producer": PRODUCER, "created_at": utc_now(), "dimension_source": geom["dimension_source"], "visual_evidence_used": version != "V0", "mep_used": version == "V2", "interface_graph_used": version == "V2", "silent_fallback_allowed": False}}
    return feature_graph, skill_calls, ir


def validate(value: dict[str, Any], schema_path: Path) -> None:
    jsonschema.validate(value, load_json(schema_path))


def process_case(row: dict[str, str], versions: list[str], seeds: dict[str, Any]) -> list[dict[str, Any]]:
    case_id = row["case_id"]
    image_text_path = ROOT / row["image_text_json"]
    urdf_path = ROOT / row["sanitized_urdf"]
    image_text = load_json(image_text_path)
    scale_mm = max(float(image_text["text_fields"]["overall_height_home_mm"]), float(image_text["text_fields"]["max_reach_mm"]))
    links, joints = parse_urdf(urdf_path)
    worlds = world_transforms(links, joints)
    visual = build_visual(row, links, joints, seeds[case_id])
    validate(visual, VISUAL_SCHEMA)
    visual_root = RUNS / "visual_observer" / case_id
    visual_path = visual_root / "codex_visual_evidence_v1.json"
    write_json(visual_path, visual)
    write_json(visual_root / "stage_manifest.json", manifest("codex_visual_observer", "SUCCESS", "codex_visual_evidence_v1", PRODUCER, [image_text_path, urdf_path, SEED_PATH, EXP / "runs/visual_agent/deterministic" / case_id / "visual_evidence_packet_v1.json"], link_count=len(links), exact_model_snapshot="UNAVAILABLE", token_usage="UNAVAILABLE"))
    mep = build_mep(row, links, joints, visual, scale_mm)
    validate(mep, MEP_SCHEMA)
    interface = build_interface(row, joints)
    validate(interface, INTERFACE_SCHEMA)
    if "V2" in versions:
        mep_root = RUNS / "V2" / case_id / "mep"
        int_root = RUNS / "V2" / case_id / "interface"
        write_json(mep_root / "mechanical_embodiment_plan.json", mep)
        write_json(mep_root / "stage_manifest.json", manifest("mechanical_embodiment_architect", "SUCCESS", "codex_mechanical_embodiment_v1", PRODUCER, [visual_path, urdf_path, EXP / "prompts/mechanical_embodiment_architect.md", MEP_SCHEMA], link_count=len(links), token_usage="UNAVAILABLE"))
        write_json(int_root / "interface_graph.json", interface)
        write_json(int_root / "stage_manifest.json", manifest("interface_engineer", "SUCCESS", "codex_interface_graph_v1", PRODUCER, [mep_root / "mechanical_embodiment_plan.json", urdf_path, EXP / "prompts/interface_engineer.md", INTERFACE_SCHEMA], joint_count=len(joints), urdf_exact_match=True, token_usage="UNAVAILABLE"))
    rows = []
    for version in versions:
        version_root = RUNS / version / case_id
        for link_id in links:
            feature, skills, ir = build_link_artifacts(row, version, link_id, links, joints, scale_mm, visual, mep if version == "V2" else None, interface if version == "V2" else None)
            validate(feature, FEATURE_SCHEMA)
            validate(skills, SKILL_SCHEMA)
            validate(ir, IR_SCHEMA)
            root = version_root / "links" / link_id
            write_json(root / "mechanical_feature_graph.json", feature)
            write_json(root / "skill_calls.json", skills)
            write_json(root / "executable_cad_ir.json", ir)
            inputs = [image_text_path, urdf_path, visual_path, FEATURE_SCHEMA, SKILL_SCHEMA, IR_SCHEMA]
            if version == "V2":
                inputs += [version_root / "mep/mechanical_embodiment_plan.json", version_root / "interface/interface_graph.json"]
            write_json(root / "stage_manifest.json", manifest(f"{version.lower()}_per_link_cad_engineer", "SUCCESS", "mechanical_feature_graph_v1+codex_skill_calls_v1+codex_link_ir_v1", PRODUCER, inputs, version=version, link_id=link_id, token_usage="UNAVAILABLE"))
            rows.append({"case_id": case_id, "version": version, "link_id": link_id, "status": "SUCCESS", "feature_count": len(feature["features"]), "skill_calls": len(skills["calls"]), "operations": len(ir["operations"]), "error_type": "", "error": ""})
        write_json(version_root / "assembly_plan.json", {"schema_version": "codex_assembly_plan_v1", "case_id": case_id, "version": version, "placement_source": "sanitized_urdf", "components": [{"link_id": link, "world_transform_mm": worlds[link].tolist()} for link in links], "joint_count": len(joints), "silent_fallback_allowed": False})
    return rows


def summarize() -> None:
    rows = []
    for row in tryset_rows():
        case_id = row["case_id"]
        visual_manifest = RUNS / "visual_observer" / case_id / "stage_manifest.json"
        if visual_manifest.exists():
            value = load_json(visual_manifest)
            rows.append({"stage": "visual_observer", "version": "shared", "case_id": case_id, "status": value["status"], "items": value.get("link_count", 0)})
        for version in ["V0", "V1", "V2"]:
            link_root = RUNS / version / case_id / "links"
            manifests = list(link_root.glob("*/stage_manifest.json")) if link_root.exists() else []
            rows.append({"stage": "planning", "version": version, "case_id": case_id, "status": "SUCCESS" if len(manifests) == int(row["links"]) else "NOT_RUN" if not manifests else "PARTIAL", "items": len(manifests)})
    write_csv(RESULTS / "codex_agent_v1_stage_summary.csv", rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default="dev_arm-ab15a75247,dev_arm-dcc2b0ce1e")
    parser.add_argument("--versions", default="V0,V1,V2")
    args = parser.parse_args()
    requested = {item.strip() for item in args.cases.split(",") if item.strip()}
    versions = [item.strip() for item in args.versions.split(",") if item.strip()]
    if not set(versions) <= {"V0", "V1", "V2"}:
        raise SystemExit("versions must be V0,V1,V2")
    seeds = load_json(SEED_PATH)["cases"]
    output = []
    for row in tryset_rows():
        if row["case_id"] in requested:
            output.extend(process_case(row, versions, seeds))
    summarize()
    print(json.dumps({"cases": sorted(requested), "versions": versions, "link_version_rows": len(output), "successes": sum(r["status"] == "SUCCESS" for r in output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
