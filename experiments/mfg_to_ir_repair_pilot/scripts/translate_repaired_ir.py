from __future__ import annotations

from typing import Any

import jsonschema

from common import (
    EXP,
    FRAME,
    RUNS,
    SCHEMAS,
    VERSIONS,
    dump_json,
    ensure_dirs,
    feature_rows_from_graph,
    frozen_rows,
    load_json,
    role_scale,
    write_csv,
)


SCHEMA = load_json(SCHEMAS / "executable_cad_ir_v1_2.schema.json")


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


def numeric(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip().replace("mm", "").strip()
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def dims(feature: dict[str, Any]) -> dict[str, Any]:
    value = feature.get("dimensions")
    if not isinstance(value, dict):
        raise IRIncomplete(f"{feature.get('feature_id')}: missing dimensions object")
    return value


def dim(feature: dict[str, Any], *names: str, minimum: float = 0.1) -> float:
    data = dims(feature)
    for name in names:
        value = numeric(data.get(name))
        if value is None:
            continue
        if value < minimum:
            raise IRIncomplete(f"{feature.get('feature_id')}: dimension {name} below minimum")
        return value
    raise IRIncomplete(f"{feature.get('feature_id')}: missing dimension among {names}")


def maybe_dim(feature: dict[str, Any], *names: str) -> float | None:
    data = dims(feature)
    for name in names:
        value = numeric(data.get(name))
        if value is not None and value > 0:
            return value
    return None


def optional_dim(feature: dict[str, Any], names: tuple[str, ...], fallback: float) -> float:
    value = maybe_dim(feature, *names)
    return value if value is not None else fallback


def radius_dim(feature: dict[str, Any]) -> float:
    value = maybe_dim(feature, "radius_mm", "outer_radius_mm", "radius")
    if value is not None:
        return value
    diameter = maybe_dim(feature, "diameter_mm", "diameter")
    if diameter is not None:
        return diameter / 2.0
    wh = [maybe_dim(feature, name) for name in ["width_mm", "height_mm", "thickness_mm", "depth_mm"]]
    wh = [x for x in wh if x is not None]
    if wh:
        return min(wh) / 2.0
    raise IRIncomplete(f"{feature.get('feature_id')}: missing radius/diameter/section size for revolved feature")


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
    cad_op = feature.get("intended_cad_operation")
    if cad_op == "loft" or feature.get("feature_type") in {"tapered_transition", "lofted_transition"}:
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


def sweep_ops(feature: dict[str, Any], scale: tuple[float, float, float], oid: str) -> tuple[list[dict[str, Any]], str]:
    center = anchor(feature, scale)
    radius = radius_dim(feature)
    length = optional_dim(feature, ("length_mm", "width_mm"), scale[0] * 0.25)
    path = {
        "control_points": [
            [center[0] - length / 2, center[1], center[2]],
            [center[0], center[1] + radius * 2.0, center[2] + radius],
            [center[0] + length / 2, center[1], center[2]],
        ]
    }
    return [op(oid, "sweep", oid, [], feature, profile=profile_circle(center, radius), profile_frame=FRAME, path=path, orientation_mode="frenet_false", transition_mode="round", solid=True, operation_mode="new_body")], oid


def additive_ops(feature: dict[str, Any], scale: tuple[float, float, float], oid: str) -> tuple[list[dict[str, Any]], str]:
    ftype = feature.get("feature_type")
    cad_op = feature.get("intended_cad_operation")
    if cad_op in {"sweep", "pipe"}:
        return sweep_ops(feature, scale, oid)
    if cad_op == "revolve" or ftype in {"proximal_joint_housing", "distal_joint_housing", "bearing_boss", "mounting_boss", "flange", "tool_flange", "connector_housing", "rounded_section", "blended_joint_transition"}:
        return revolve_ops(feature, scale, oid)
    if ftype in {"main_link_body", "elongated_main_body", "main_housing", "support_frame", "palm_plate", "tapered_transition", "lofted_transition", "rib", "web", "cover_region", "strengthening_boss"} or cad_op in {"extrude", "pad", "loft"}:
        return main_body_ops(feature, scale, oid)
    return [], ""


def cutter_ops(feature: dict[str, Any], scale: tuple[float, float, float], oid: str, final_body: str) -> tuple[list[dict[str, Any]], str]:
    center = anchor(feature, scale)
    ftype = feature.get("feature_type")
    if ftype in {"hole", "circular_hole"} or maybe_dim(feature, "diameter_mm", "radius_mm") is not None:
        radius = radius_dim(feature)
        depth = dim(feature, "depth_mm", "height_mm", "thickness_mm", "length_mm")
        cutter = op(oid, "extrude", oid, [], feature, profile=profile_circle(center, radius), distance_mm=depth, operation_mode="new_body")
    else:
        length = dim(feature, "length_mm", "diameter_mm", "width_mm")
        width = optional_dim(feature, ("width_mm", "diameter_mm"), length)
        depth = dim(feature, "depth_mm", "height_mm", "thickness_mm", "length_mm")
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
                edge_selectors=[{"selector_type": "outer_short_edges", "target_feature": final_body, "location_hint": "safe_visible_outer_edges", "radius_mm": radius, "max_edges": 1}],
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
                edge_selectors=[{"selector_type": "outer_short_edges", "target_feature": final_body, "location_hint": "safe_visible_outer_edges", "distance_mm": distance, "max_edges": 1}],
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
    cutter_types = {"recess", "cutout", "hollow_region", "slot", "gap", "lightening_cut", "hole", "circular_hole"}
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
        "metadata": {
            "source_schema": "mechanical_feature_graph_v2",
            "translator": "mfg_to_ir_repair_pilot",
            "strict_missing_geometry_policy": "IR_INCOMPLETE",
            "no_llm_calls": True,
        },
    }


def write_ir(out_dir, ir: dict[str, Any]) -> list[str]:
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
    rows: list[dict[str, Any]] = []
    for version in VERSIONS:
        for row in frozen_rows():
            out_dir = RUNS / version / row["case_id"] / row["link_id"]
            out_dir.mkdir(parents=True, exist_ok=True)
            status = "SUCCESS"
            errors: list[str] = []
            try:
                graph_path = out_dir / "mechanical_feature_graph_repaired.json"
                mfg_validation = load_json(out_dir / "schema_validation_mfg.json") if (out_dir / "schema_validation_mfg.json").exists() else {"valid": False}
                if not graph_path.exists() or not mfg_validation.get("valid"):
                    raise IRIncomplete("repaired MFG missing or invalid")
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


if __name__ == "__main__":
    main()
