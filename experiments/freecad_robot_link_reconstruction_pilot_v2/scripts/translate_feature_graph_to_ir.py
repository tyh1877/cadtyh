from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import jsonschema

from pilot_common import EXP, FRAME, RUNS, dump_json, ensure_dirs, feature_rows_from_graph, frozen_rows, load_json, write_csv


SCHEMA = load_json(EXP / "schemas" / "executable_cad_ir_v1_2.schema.json")


class IRIncomplete(ValueError):
    pass


def profile_rect(center: list[float], size: list[float]) -> dict[str, Any]:
    return {"profile_type": "rectangle", "closed": True, "parameters": {"center": center, "size_mm": size}}


def profile_circle(center: list[float], radius: float) -> dict[str, Any]:
    return {"profile_type": "circle", "closed": True, "parameters": {"center": center, "radius_mm": radius}}


def op(op_id: str, op_type: str, target: str, deps: list[str], feature: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return {
        "op_id": op_id,
        "op_type": op_type,
        "target_body": target,
        "dependencies": deps,
        "reference_frame": FRAME,
        "feature_ref": feature.get("feature_id", ""),
        "semantic_feature_type": feature.get("feature_type", ""),
        **kwargs,
    }


def role_scale(role: str) -> tuple[float, float, float]:
    if role == "base_or_shoulder":
        return 120.0, 90.0, 42.0
    if role in {"upper_arm", "main_link", "forearm"}:
        return 160.0, 42.0, 28.0
    if role == "elbow_housing":
        return 90.0, 75.0, 50.0
    if role == "wrist_or_tool_side_link":
        return 95.0, 55.0, 24.0
    return 100.0, 50.0, 30.0


def dim(feature: dict[str, Any], *names: str, minimum: float = 0.1) -> float:
    dims = feature.get("dimensions")
    if not isinstance(dims, dict):
        raise IRIncomplete(f"{feature.get('feature_id')}: missing dimensions object")
    for name in names:
        value = dims.get(name)
        if value is None:
            continue
        try:
            value = float(value)
        except Exception as exc:
            raise IRIncomplete(f"{feature.get('feature_id')}: non-numeric dimension {name}") from exc
        if value < minimum:
            raise IRIncomplete(f"{feature.get('feature_id')}: dimension {name} below minimum")
        return value
    raise IRIncomplete(f"{feature.get('feature_id')}: missing dimension among {names}")


def optional_dim(feature: dict[str, Any], names: tuple[str, ...], fallback: float) -> float:
    try:
        return dim(feature, *names)
    except IRIncomplete:
        return fallback


def radius_dim(feature: dict[str, Any]) -> float:
    try:
        return dim(feature, "radius_mm", "outer_radius_mm", "radius")
    except IRIncomplete:
        dims = feature.get("dimensions") if isinstance(feature.get("dimensions"), dict) else {}
        for name in ("diameter_mm", "diameter"):
            if name in dims:
                return float(dims[name]) / 2.0
        values = []
        for name in ("width_mm", "height_mm", "length_mm", "thickness_mm", "depth_mm"):
            if name in dims:
                try:
                    values.append(float(dims[name]))
                except Exception:
                    pass
        if values:
            return min(values) / 2.0
        raise


def anchor(feature: dict[str, Any], scale: tuple[float, float, float]) -> list[float]:
    data = feature.get("anchor")
    if not isinstance(data, dict) or "position" not in data:
        raise IRIncomplete(f"{feature.get('feature_id')}: missing anchor.position")
    pos = data["position"]
    if not isinstance(pos, list) or len(pos) != 3:
        raise IRIncomplete(f"{feature.get('feature_id')}: invalid anchor.position")
    values = [float(pos[0]), float(pos[1]), float(pos[2])]
    if data.get("type") == "link_local_normalized":
        return [values[0] * scale[0] / 2, values[1] * scale[1] / 2, values[2] * scale[2] / 2]
    if data.get("type") == "link_local_mm":
        return values
    raise IRIncomplete(f"{feature.get('feature_id')}: unsupported anchor.type")


def main_body_ops(feature: dict[str, Any], scale: tuple[float, float, float], oid: str) -> tuple[list[dict[str, Any]], str]:
    center = anchor(feature, scale)
    length = dim(feature, "length_mm", "length")
    width = dim(feature, "width_mm", "width")
    height = dim(feature, "height_mm", "height", "thickness_mm", "thickness")
    if feature.get("intended_cad_operation") == "loft" or feature.get("feature_type") in {"elongated_main_body", "tapered_transition", "lofted_transition"}:
        profiles = [
            profile_rect([center[0] - length / 2, center[1], center[2]], [width, height]),
            profile_rect([center[0] + length / 2, center[1], center[2] + height * 0.05], [max(width * 0.72, 1.0), max(height * 0.85, 1.0)]),
        ]
        return [op(oid, "loft", oid, [], feature, profiles=profiles, solid=True, operation_mode="new_body")], oid
    return [op(oid, "extrude", oid, [], feature, profile=profile_rect(center, [length, width]), distance_mm=height, operation_mode="new_body")], oid


def revolve_ops(feature: dict[str, Any], scale: tuple[float, float, float], oid: str) -> tuple[list[dict[str, Any]], str]:
    center = anchor(feature, scale)
    radius = radius_dim(feature)
    depth = optional_dim(feature, ("depth_mm", "thickness_mm", "length_mm", "width_mm"), max(radius * 0.65, 1.0))
    profile = profile_rect([center[0] + radius * 0.55, center[1], center[2]], [max(radius * 0.55, 1.0), max(depth, 1.0)])
    axis_dir = feature.get("local_frame", {}).get("y_axis", [0, 1, 0])
    return [op(oid, "revolve", oid, [], feature, profile=profile, axis={"point": center, "direction": axis_dir}, angle_deg=360, operation_mode="new_body")], oid


def additive_ops(feature: dict[str, Any], scale: tuple[float, float, float], oid: str) -> tuple[list[dict[str, Any]], str]:
    ftype = feature.get("feature_type")
    cad_op = feature.get("intended_cad_operation")
    if cad_op == "revolve":
        return revolve_ops(feature, scale, oid)
    if ftype in {"main_link_body", "elongated_main_body", "main_housing", "support_frame", "palm_plate", "tapered_transition", "lofted_transition"} or cad_op in {"extrude", "pad", "loft"}:
        return main_body_ops(feature, scale, oid)
    if ftype in {"proximal_joint_housing", "distal_joint_housing", "bearing_boss", "mounting_boss", "flange", "tool_flange", "connector_housing", "rounded_section", "blended_joint_transition"}:
        return revolve_ops(feature, scale, oid)
    if ftype in {"rib", "web", "cover_region", "strengthening_boss"}:
        center = anchor(feature, scale)
        length = dim(feature, "length_mm", "length")
        width = dim(feature, "width_mm", "width")
        height = dim(feature, "height_mm", "height", "thickness_mm")
        return [op(oid, "extrude", oid, [], feature, profile=profile_rect(center, [length, width]), distance_mm=height, operation_mode="new_body")], oid
    if cad_op in {"sweep", "pipe"}:
        center = anchor(feature, scale)
        radius = dim(feature, "radius_mm", "diameter_mm")
        length = optional_dim(feature, ("length_mm",), scale[0] * 0.25)
        path = {"control_points": [[center[0] - length / 2, center[1], center[2]], [center[0], center[1] + radius * 2, center[2]], [center[0] + length / 2, center[1], center[2]]]}
        return [op(oid, "sweep", oid, [], feature, profile=profile_circle(center, radius), profile_frame=FRAME, path=path, orientation_mode="frenet_false", transition_mode="round", solid=True, operation_mode="new_body")], oid
    return [], ""


def cutter_ops(feature: dict[str, Any], scale: tuple[float, float, float], oid: str, final_body: str) -> tuple[list[dict[str, Any]], str]:
    center = anchor(feature, scale)
    length = dim(feature, "length_mm", "diameter_mm", "width_mm")
    width = optional_dim(feature, ("width_mm", "diameter_mm"), length)
    depth = dim(feature, "depth_mm", "height_mm", "thickness_mm")
    cutter = op(oid, "extrude", oid, [], feature, profile=profile_rect(center, [length, width]), distance_mm=depth, operation_mode="new_body")
    cut_id = f"{oid}_cut"
    cut = op(cut_id, "boolean_cut", final_body, [final_body, oid], feature, tool_bodies=[oid])
    return [cutter, cut], cut_id


def modifier_ops(feature: dict[str, Any], oid: str, final_body: str) -> tuple[list[dict[str, Any]], str]:
    ftype = feature.get("feature_type")
    if ftype == "fillet_group" or feature.get("intended_cad_operation") == "fillet":
        radius = dim(feature, "radius_mm", "fillet_radius_mm")
        return [
            op(
                oid,
                "fillet",
                final_body,
                [final_body],
                feature,
                radius_mm=radius,
                edge_selectors=[{"selector_type": "outer_long_edges", "target_feature": final_body, "location_hint": "side_edges", "radius_mm": radius, "max_edges": 1}],
            )
        ], oid
    if ftype == "chamfer_group" or feature.get("intended_cad_operation") == "chamfer":
        distance = dim(feature, "distance_mm", "chamfer_distance_mm", "radius_mm", "depth_mm")
        return [
            op(
                oid,
                "chamfer",
                final_body,
                [final_body],
                feature,
                distance_mm=distance,
                edge_selectors=[{"selector_type": "outer_long_edges", "target_feature": final_body, "location_hint": "side_edges", "distance_mm": distance, "max_edges": 1}],
            )
        ], oid
    return [], final_body


def graph_to_ir(graph: dict[str, Any], role: str) -> dict[str, Any]:
    scale = role_scale(role)
    features = feature_rows_from_graph(graph)
    additive_types = {
        "main_link_body",
        "elongated_main_body",
        "main_housing",
        "support_frame",
        "palm_plate",
        "proximal_joint_housing",
        "distal_joint_housing",
        "flange",
        "bearing_boss",
        "mounting_face",
        "mounting_boss",
        "tool_flange",
        "connector_housing",
        "rib",
        "web",
        "cover_region",
        "strengthening_boss",
        "tapered_transition",
        "lofted_transition",
        "rounded_section",
        "blended_joint_transition",
    }
    cutter_types = {"recess", "cutout", "hollow_region", "slot", "gap", "lightening_cut"}
    modifier_types = {"fillet_group", "chamfer_group"}
    ops: list[dict[str, Any]] = []
    solids: list[str] = []
    idx = 1
    for feature in [f for f in features if f.get("feature_type") in additive_types]:
        new_ops, solid_id = additive_ops(feature, scale, f"op_{idx:03d}")
        idx += 1
        if new_ops and solid_id:
            ops.extend(new_ops)
            solids.append(solid_id)
    if not solids:
        raise IRIncomplete("no additive IR operations generated")
    final_body = solids[0]
    if len(solids) > 1:
        union_id = f"op_{idx:03d}"
        idx += 1
        ops.append(op(union_id, "boolean_union", solids[0], solids, {"feature_id": "AUTO_UNION", "feature_type": "assembly_union"}, tool_bodies=solids[1:]))
        final_body = union_id
    for feature in [f for f in features if f.get("feature_type") in cutter_types]:
        new_ops, final_body = cutter_ops(feature, scale, f"op_{idx:03d}", final_body)
        idx += 1
        ops.extend(new_ops)
    for feature in [f for f in features if f.get("feature_type") in modifier_types]:
        new_ops, final_body = modifier_ops(feature, f"op_{idx:03d}", final_body)
        idx += 1
        ops.extend(new_ops)
    return {
        "ir_version": "executable_cad_ir_v1_2",
        "case_id": graph["case_id"],
        "link_id": graph["link_id"],
        "bodies": [{"body_id": "body", "role": role}],
        "operations": ops,
        "final_object": final_body,
        "metadata": {"source_schema": "mechanical_feature_graph_v2", "translator": "mfg_v2_to_executable_cad_ir_v1_2", "strict_missing_geometry_policy": "IR_INCOMPLETE"},
    }


def r0_ir(row: dict[str, str]) -> dict[str, Any]:
    length, width, height = role_scale(row["role"])
    main = {"feature_id": "R0_main_proxy", "feature_type": "main_link_body", "dimensions": {"length_mm": length, "width_mm": width, "height_mm": height}, "anchor": {"type": "link_local_mm", "position": [0, 0, 0]}, "local_frame": FRAME, "intended_cad_operation": "extrude"}
    ops = [op("op_001", "extrude", "op_001", [], main, profile=profile_rect([0, 0, 0], [length, width]), distance_mm=height, operation_mode="new_body")]
    final = "op_001"
    if row["role"] in {"upper_arm", "main_link", "forearm", "elbow_housing", "wrist_or_tool_side_link", "base_or_shoulder"}:
        boss = {"feature_id": "R0_joint_proxy", "feature_type": "proximal_joint_housing", "dimensions": {"radius_mm": min(width, height) * 0.45, "depth_mm": width * 0.6}, "anchor": {"type": "link_local_mm", "position": [-length / 2, 0, height / 2]}, "local_frame": FRAME, "intended_cad_operation": "revolve"}
        new_ops, solid = revolve_ops(boss, (length, width, height), "op_002")
        ops.extend(new_ops)
        ops.append(op("op_003", "boolean_union", "op_001", ["op_001", solid], {"feature_id": "R0_union", "feature_type": "assembly_union"}, tool_bodies=[solid]))
        final = "op_003"
    return {"ir_version": "executable_cad_ir_v1_2", "case_id": row["case_id"], "link_id": row["link_id"], "bodies": [{"body_id": "body", "role": row["role"]}], "operations": ops, "final_object": final, "metadata": {"source": "R0 deterministic FreeCAD baseline"}}


def write_ir(out_dir: Path, ir: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        jsonschema.validate(ir, SCHEMA)
    except jsonschema.ValidationError as exc:
        errors.append(f"schema: {exc.message}")
    dump_json(out_dir / "schema_validation_ir.json", {"schema": "executable_cad_ir_v1_2", "valid": not errors, "errors": errors})
    if not errors:
        dump_json(out_dir / "executable_cad_ir_v1_2.json", ir)
        dump_json(out_dir / "executable_cad_ir.json", ir)
    return errors


def main() -> None:
    ensure_dirs()
    rows = []
    for version in ["R0", "R1", "R2"]:
        for row in frozen_rows():
            out_dir = RUNS / version / row["case_id"] / row["link_id"]
            out_dir.mkdir(parents=True, exist_ok=True)
            status = "SUCCESS"
            errors: list[str] = []
            try:
                if version == "R0":
                    ir = r0_ir(row)
                else:
                    graph_path = out_dir / "mechanical_feature_graph_v2.json"
                    if not graph_path.exists():
                        raise IRIncomplete("mechanical_feature_graph_v2.json missing")
                    ir = graph_to_ir(load_json(graph_path), row["role"])
                errors = write_ir(out_dir, ir)
                if errors:
                    status = "IR_INVALID"
            except Exception as exc:
                status = "IR_INCOMPLETE" if isinstance(exc, IRIncomplete) else "FAILURE"
                errors = [f"{type(exc).__name__}: {exc}"]
                dump_json(out_dir / "schema_validation_ir.json", {"schema": "executable_cad_ir_v1_2", "valid": False, "errors": errors})
            dump_json(out_dir / "ir_manifest.json", {"version": version, "case_id": row["case_id"], "link_id": row["link_id"], "status": status, "errors": errors})
            rows.append({"version": version, "case_id": row["case_id"], "link_id": row["link_id"], "role": row["role"], "status": status, "errors": "; ".join(errors)})
            print(version, row["case_id"], row["link_id"], status)
    write_csv(EXP / "results" / "ir_translation.csv", rows)
    stale = EXP / "results" / "freecad_robot_link_reconstruction_pilot_report.md"
    if stale.exists():
        stale.unlink()


if __name__ == "__main__":
    main()
