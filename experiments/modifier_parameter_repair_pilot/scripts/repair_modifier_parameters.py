from __future__ import annotations

from copy import deepcopy
from typing import Any

import jsonschema

from common import (
    RESULTS,
    RUNS,
    SCHEMA_PATH,
    VERSIONS,
    dump_json,
    ensure_dirs,
    frozen_rows,
    load_json,
    output_case_dir,
    positive_number,
    role_scale,
    source_case_dir,
    write_csv,
)


SCHEMA = load_json(SCHEMA_PATH)


def feature_rows(graph: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for section in ["primary_features", "functional_features", "structural_features", "surface_features"]:
        for feature in graph.get(section, []):
            if isinstance(feature, dict):
                item = dict(feature)
                item["section"] = section
                rows.append(item)
    return rows


def feature_by_id(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(f.get("feature_id")): f for f in feature_rows(graph) if f.get("feature_id") is not None}


def dimension_values(feature: dict[str, Any]) -> list[float]:
    dims = feature.get("dimensions")
    if not isinstance(dims, dict):
        return []
    values: list[float] = []
    for key, value in dims.items():
        if key in {"radius_mm", "fillet_radius_mm", "chamfer_distance_mm", "distance_mm"}:
            continue
        parsed = positive_number(value)
        if parsed is not None:
            values.append(parsed)
    return values


def safe_cap_mm(feature: dict[str, Any], role: str, op_type: str) -> tuple[float, str]:
    scale = role_scale(role)
    role_cap = min(scale) * (0.025 if op_type == "fillet" else 0.02)
    dims = dimension_values(feature)
    if dims:
        dim_cap = min(dims) * (0.18 if op_type == "fillet" else 0.12)
        cap = min(role_cap, dim_cap)
        reason = "role_scale_and_feature_dimension_cap"
    else:
        cap = role_cap
        reason = "role_scale_cap_no_local_dimension"
    return max(0.5, round(cap, 3)), reason


def requested_value(op: dict[str, Any], feature: dict[str, Any], op_type: str) -> float | None:
    keys = ["radius_mm", "fillet_radius_mm"] if op_type == "fillet" else ["distance_mm", "chamfer_distance_mm", "radius_mm", "depth_mm"]
    for key in keys:
        value = positive_number(op.get(key))
        if value is not None:
            return value
    dims = feature.get("dimensions") if isinstance(feature.get("dimensions"), dict) else {}
    for key in keys:
        value = positive_number(dims.get(key))
        if value is not None:
            return value
    return None


def selector_priority(target_body: str, value: float, op_type: str) -> list[dict[str, Any]]:
    value_key = "radius_mm" if op_type == "fillet" else "distance_mm"
    common = {
        "target_feature": target_body,
        "location_hint": "safe_visible_outer_edges",
        value_key: value,
        "min_edge_length_ratio": 6.0,
        "safe_radius_ratio": 0.16 if op_type == "fillet" else 0.12,
    }
    return [
        {"selector_type": "outer_long_edges", "max_edges": 4, **common},
        {"selector_type": "outer_short_edges", "max_edges": 4, **common},
        {"selector_type": "all_safe_edges", "max_edges": 6, **common},
    ]


def repair_ir(ir: dict[str, Any], graph: dict[str, Any], role: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    repaired = deepcopy(ir)
    features = feature_by_id(graph)
    logs: list[dict[str, Any]] = []
    for op in repaired.get("operations", []):
        op_type = op.get("op_type")
        if op_type not in {"fillet", "chamfer"}:
            continue
        feature = features.get(str(op.get("feature_ref")), {})
        requested = requested_value(op, feature, op_type)
        if requested is None:
            logs.append({
                "op_id": op.get("op_id"),
                "op_type": op_type,
                "feature_ref": op.get("feature_ref"),
                "repair_status": "IR_INCOMPLETE",
                "reason": "missing_requested_modifier_parameter",
            })
            continue
        cap, cap_reason = safe_cap_mm(feature, role, op_type)
        resolved = min(requested, cap)
        resolved = round(max(0.5, resolved), 3)
        status = "PARAMETER_REPAIRED" if resolved < requested else "NO_REPAIR_NEEDED"
        value_key = "radius_mm" if op_type == "fillet" else "distance_mm"
        op[f"requested_{value_key}"] = requested
        op[value_key] = resolved
        op[f"resolved_{value_key}"] = resolved
        op["parameter_repair_used"] = status == "PARAMETER_REPAIRED"
        op["semantic_match"] = "partial" if status == "PARAMETER_REPAIRED" else "true"
        op["modifier_parameter_policy"] = {
            "safe_cap_mm": cap,
            "cap_reason": cap_reason,
            "requested_value_treated_as_non_authoritative": True,
            "backend_silent_fallback_allowed": False,
        }
        op["edge_selectors"] = selector_priority(op["target_body"], resolved, op_type)
        logs.append({
            "op_id": op.get("op_id"),
            "op_type": op_type,
            "feature_ref": op.get("feature_ref"),
            "target_body": op.get("target_body"),
            "requested_value_mm": requested,
            "resolved_value_mm": resolved,
            "safe_cap_mm": cap,
            "repair_status": status,
            "reason": cap_reason if status == "PARAMETER_REPAIRED" else "requested_value_within_safe_cap",
        })
    repaired.setdefault("metadata", {})
    repaired["metadata"].update({
        "modifier_parameter_repair_pilot": True,
        "modifier_repair_policy": "explicit_translator_parameter_repair_no_backend_fallback",
        "no_llm_calls": True,
        "no_gt_mesh_step_cad": True,
    })
    return repaired, logs


def validate_ir(ir: dict[str, Any]) -> list[str]:
    try:
        jsonschema.validate(ir, SCHEMA)
    except jsonschema.ValidationError as exc:
        return [f"schema: {exc.message}"]
    return []


def main() -> None:
    ensure_dirs()
    rows: list[dict[str, Any]] = []
    modifier_rows: list[dict[str, Any]] = []
    for version in VERSIONS:
        for row in frozen_rows():
            src = source_case_dir(version, row["case_id"], row["link_id"])
            out = output_case_dir(version, row["case_id"], row["link_id"])
            out.mkdir(parents=True, exist_ok=True)
            status = "SUCCESS"
            errors: list[str] = []
            logs: list[dict[str, Any]] = []
            try:
                graph_path = src / "mechanical_feature_graph_repaired.json"
                ir_path = src / "executable_cad_ir_v1_2.json"
                if not graph_path.exists():
                    raise FileNotFoundError("mechanical_feature_graph_repaired.json missing")
                if not ir_path.exists():
                    raise FileNotFoundError("source executable_cad_ir_v1_2.json missing")
                graph = load_json(graph_path)
                source_ir = load_json(ir_path)
                repaired_ir, logs = repair_ir(source_ir, graph, row["role"])
                errors = validate_ir(repaired_ir)
                if errors:
                    status = "IR_INVALID"
                else:
                    dump_json(out / "executable_cad_ir_v1_2.json", repaired_ir)
                    dump_json(out / "executable_cad_ir.json", repaired_ir)
            except FileNotFoundError as exc:
                status = "IR_INCOMPLETE"
                errors = [str(exc)]
            except Exception as exc:
                status = "FAILURE"
                errors = [f"{type(exc).__name__}: {exc}"]
            dump_json(out / "modifier_repair_log.json", logs)
            dump_json(out / "schema_validation.json", {"schema": "executable_cad_ir_v1_2", "valid": status == "SUCCESS", "errors": errors})
            dump_json(out / "manifest.json", {"version": version, "case_id": row["case_id"], "link_id": row["link_id"], "role": row["role"], "status": status, "errors": errors})
            rows.append({"version": version, "case_id": row["case_id"], "link_id": row["link_id"], "role": row["role"], "status": status, "errors": "; ".join(errors)})
            for item in logs:
                modifier_rows.append({"version": version, "case_id": row["case_id"], "link_id": row["link_id"], "role": row["role"], **item})
            print(version, row["case_id"], row["link_id"], status)
    write_csv(RESULTS / "ir_repair_metrics.csv", rows)
    write_csv(RESULTS / "modifier_repair_metrics.csv", modifier_rows, fields=[
        "version",
        "case_id",
        "link_id",
        "role",
        "op_id",
        "op_type",
        "feature_ref",
        "target_body",
        "requested_value_mm",
        "resolved_value_mm",
        "safe_cap_mm",
        "repair_status",
        "reason",
    ])


if __name__ == "__main__":
    main()
