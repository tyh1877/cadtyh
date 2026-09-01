from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import jsonschema

from common import (
    EXP,
    RESULTS,
    RUNS,
    SCHEMAS,
    SOURCE_EXP,
    VERSIONS,
    dump_json,
    ensure_dirs,
    extract_json,
    frozen_rows,
    load_json,
    write_csv,
)


SCHEMA = load_json(SCHEMAS / "mechanical_feature_graph_v2.schema.json")
SECTIONS = ["primary_features", "functional_features", "structural_features", "surface_features"]
PRIORITY_BY_SECTION = {
    "primary_features": "primary",
    "functional_features": "functional",
    "structural_features": "structural",
    "surface_features": "surface",
}
ALLOWED_OPS = {
    "extrude",
    "pad",
    "pocket",
    "cut",
    "revolve",
    "loft",
    "sweep",
    "pipe",
    "shell",
    "thickness",
    "boolean_union",
    "boolean_cut",
    "fillet",
    "chamfer",
    "pattern",
    "mirror",
    "none",
}


def log_action(actions: list[dict[str, str]], path: str, action: str, detail: str) -> None:
    actions.append({"path": path, "action": action, "detail": detail})


def as_number(value: Any) -> float | None:
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


def vec3(value: Any) -> list[float] | None:
    if isinstance(value, list) and len(value) >= 3:
        out = [as_number(value[0]), as_number(value[1]), as_number(value[2])]
        if all(v is not None for v in out):
            return [float(out[0]), float(out[1]), float(out[2])]  # type: ignore[arg-type]
    if isinstance(value, dict):
        for keys in [("x", "y", "z"), ("X", "Y", "Z")]:
            if all(k in value for k in keys):
                out = [as_number(value[k]) for k in keys]
                if all(v is not None for v in out):
                    return [float(out[0]), float(out[1]), float(out[2])]  # type: ignore[arg-type]
    return None


def normalize_anchor(anchor: Any, actions: list[dict[str, str]], path: str) -> dict[str, Any]:
    if not isinstance(anchor, dict):
        log_action(actions, path, "default_missing_anchor", "anchor was not an object; marked at link origin")
        return {"type": "link_local_normalized", "position": [0.0, 0.0, 0.0], "reason": "repair: missing anchor object"}
    candidate = None
    for key in ["position", "center", "point", "xyz", "origin", "anchor_point", "location"]:
        if key in anchor:
            candidate = vec3(anchor[key])
            if candidate is not None and key != "position":
                log_action(actions, f"{path}.{key}", "canonicalize_anchor_position", f"{key} -> position")
                break
    if candidate is None and "start" in anchor and "end" in anchor:
        start = vec3(anchor["start"])
        end = vec3(anchor["end"])
        if start and end:
            candidate = [(start[i] + end[i]) / 2.0 for i in range(3)]
            log_action(actions, path, "canonicalize_anchor_midpoint", "start/end -> midpoint position")
    if candidate is None and "span" in anchor and isinstance(anchor["span"], dict):
        span = anchor["span"]
        keys = [("x_min", "x_max"), ("y_min", "y_max"), ("z_min", "z_max")]
        if all(a in span and b in span for a, b in keys):
            values = []
            for a, b in keys:
                lo, hi = as_number(span[a]), as_number(span[b])
                if lo is None or hi is None:
                    values = []
                    break
                values.append((lo + hi) / 2.0)
            if len(values) == 3:
                candidate = values
                log_action(actions, f"{path}.span", "canonicalize_anchor_span_midpoint", "span bbox -> midpoint position")
    if candidate is None:
        candidate = [0.0, 0.0, 0.0]
        log_action(actions, path, "default_missing_anchor_position", "position unavailable; marked at link origin")
    typ = str(anchor.get("type") or anchor.get("frame") or anchor.get("coordinate_system") or "").lower()
    if "mm" in typ or "millimeter" in typ:
        out_type = "link_local_mm"
    elif "normal" in typ:
        out_type = "link_local_normalized"
    else:
        out_type = "link_local_normalized" if all(-1.5 <= x <= 1.5 for x in candidate) else "link_local_mm"
        log_action(actions, path, "infer_anchor_type", f"inferred {out_type} from coordinate magnitude")
    return {"type": out_type, "position": candidate, "reason": str(anchor.get("reason") or "repair-canonicalized")}


def normalize_frame(frame: Any, actions: list[dict[str, str]], path: str) -> dict[str, list[float]]:
    if not isinstance(frame, dict):
        log_action(actions, path, "default_local_frame", "local_frame was not an object")
        return {"x_axis": [1, 0, 0], "y_axis": [0, 1, 0], "z_axis": [0, 0, 1]}
    aliases = {
        "x_axis": ["x_axis", "x", "axis_x", "length_axis"],
        "y_axis": ["y_axis", "y", "axis_y", "width_axis"],
        "z_axis": ["z_axis", "z", "axis_z", "height_axis"],
    }
    defaults = {"x_axis": [1, 0, 0], "y_axis": [0, 1, 0], "z_axis": [0, 0, 1]}
    output: dict[str, list[float]] = {}
    for dst, keys in aliases.items():
        value = None
        for key in keys:
            if key in frame:
                value = vec3(frame[key])
                if value is not None and key != dst:
                    log_action(actions, f"{path}.{key}", "canonicalize_axis", f"{key} -> {dst}")
                break
        if value is None:
            value = defaults[dst]
            log_action(actions, f"{path}.{dst}", "default_axis_convention", f"{dst} missing; used link coordinate convention")
        output[dst] = value
    return output


def normalize_dimensions(dims: Any, actions: list[dict[str, str]], path: str) -> dict[str, Any]:
    if isinstance(dims, list) and len(dims) >= 3:
        out = {"length_mm": dims[0], "width_mm": dims[1], "height_mm": dims[2]}
        log_action(actions, path, "canonicalize_dimensions_array", "array[3] -> length/width/height")
        return out
    if not isinstance(dims, dict):
        log_action(actions, path, "empty_dimensions", "dimensions missing or non-object")
        return {}
    out = dict(dims)
    array_aliases = ["bbox_mm", "bounding_box_mm", "size_mm", "overall_size_mm", "extent_mm", "dims_mm"]
    for key in array_aliases:
        if key in out and isinstance(out[key], list) and len(out[key]) >= 3:
            out.setdefault("length_mm", out[key][0])
            out.setdefault("width_mm", out[key][1])
            out.setdefault("height_mm", out[key][2])
            log_action(actions, f"{path}.{key}", "expand_dimension_array_alias", f"{key} -> length/width/height")
    scalar_aliases = {
        "length": "length_mm",
        "width": "width_mm",
        "height": "height_mm",
        "radius": "radius_mm",
        "diameter": "diameter_mm",
        "depth": "depth_mm",
        "thickness": "thickness_mm",
        "fillet_radius": "fillet_radius_mm",
        "chamfer_distance": "chamfer_distance_mm",
    }
    for src, dst in scalar_aliases.items():
        if src in out and dst not in out:
            out[dst] = out[src]
            log_action(actions, f"{path}.{src}", "canonicalize_dimension_alias", f"{src} -> {dst}")
    return out


def normalize_attachment(value: Any, actions: list[dict[str, str]], path: str) -> dict[str, Any]:
    if isinstance(value, str):
        log_action(actions, path, "string_attachment_to_object", "attachment string -> contract object")
        return {"attached_to": value, "attachment_face": None, "relation": "attached"}
    if not isinstance(value, dict):
        log_action(actions, path, "default_attachment", "attachment missing")
        return {"attached_to": None, "attachment_face": None, "relation": "unspecified"}
    attached_to = value.get("attached_to")
    if attached_to is None:
        for key in ["on", "parent", "parent_feature", "parent_body", "target", "feature_id", "base_feature"]:
            if key in value:
                attached_to = value[key]
                log_action(actions, f"{path}.{key}", "canonicalize_attachment_target", f"{key} -> attached_to")
                break
    face = value.get("attachment_face")
    if face is None:
        for key in ["face", "side", "surface", "location_hint"]:
            if key in value:
                face = value[key]
                log_action(actions, f"{path}.{key}", "canonicalize_attachment_face", f"{key} -> attachment_face")
                break
    return {
        "attached_to": str(attached_to) if attached_to is not None else None,
        "attachment_face": str(face) if face is not None else None,
        "relation": str(value.get("relation") or value.get("type") or "attached"),
    }


def normalize_refs(value: Any, actions: list[dict[str, str]], path: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
        log_action(actions, path, "wrap_refs", "non-list refs wrapped in list")
    out = []
    for item in value:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            label = item.get("id") or item.get("view") or item.get("crop") or item.get("ref") or json.dumps(item, ensure_ascii=False, sort_keys=True)
            out.append(str(label))
            log_action(actions, path, "object_ref_to_string", "object evidence ref stringified")
        else:
            out.append(str(item))
            log_action(actions, path, "ref_to_string", "non-string evidence ref stringified")
    return out


def normalize_feature(feature: Any, section: str, idx: int, actions: list[dict[str, str]]) -> dict[str, Any]:
    if not isinstance(feature, dict):
        feature = {"evidence": [str(feature)]}
        log_action(actions, f"{section}[{idx}]", "non_object_feature", "converted non-object feature to minimal object")
    out: dict[str, Any] = {}
    out["feature_id"] = str(feature.get("feature_id") or feature.get("id") or f"{section}_{idx:02d}")
    out["feature_type"] = str(feature.get("feature_type") or feature.get("type") or feature.get("name") or "unknown_feature")
    priority = feature.get("priority") or PRIORITY_BY_SECTION[section]
    if str(priority) not in {"primary", "functional", "structural", "surface"}:
        log_action(actions, f"{section}[{idx}].priority", "canonicalize_priority_from_section", f"{priority!r} -> {PRIORITY_BY_SECTION[section]}")
        priority = PRIORITY_BY_SECTION[section]
    out["priority"] = str(priority)
    out["role"] = str(feature.get("role") or feature.get("function") or out["feature_type"])
    evidence = feature.get("evidence") or feature.get("rationale") or feature.get("visual_evidence") or []
    out["evidence"] = normalize_refs(evidence, actions, f"{section}[{idx}].evidence")
    out["anchor"] = normalize_anchor(feature.get("anchor"), actions, f"{section}[{idx}].anchor")
    out["local_frame"] = normalize_frame(feature.get("local_frame") or feature.get("frame"), actions, f"{section}[{idx}].local_frame")
    out["dimensions"] = normalize_dimensions(feature.get("dimensions") or feature.get("dimension"), actions, f"{section}[{idx}].dimensions")
    out["attachment"] = normalize_attachment(feature.get("attachment") or feature.get("attached_to"), actions, f"{section}[{idx}].attachment")
    out["visible_evidence_refs"] = normalize_refs(feature.get("visible_evidence_refs") or feature.get("visual_evidence_refs"), actions, f"{section}[{idx}].visible_evidence_refs")
    op = str(feature.get("intended_cad_operation") or feature.get("cad_operation") or feature.get("operation") or "none").lower()
    op = {"extrusion": "extrude", "pad/extrude": "extrude", "boolean cut": "boolean_cut", "boolean-cut": "boolean_cut"}.get(op, op)
    out["intended_cad_operation"] = op if op in ALLOWED_OPS else "none"
    if out["intended_cad_operation"] == "none" and op not in ALLOWED_OPS:
        log_action(actions, f"{section}[{idx}].intended_cad_operation", "unknown_operation_to_none", op)
    if "shape_family" in feature:
        out["shape_family"] = str(feature["shape_family"])
    if "dependencies" in feature:
        out["dependencies"] = normalize_refs(feature["dependencies"], actions, f"{section}[{idx}].dependencies")
    confidence = as_number(feature.get("confidence"))
    out["confidence"] = max(0.0, min(1.0, confidence if confidence is not None else 0.5))
    return out


def normalize_graph(graph: dict[str, Any], row: dict[str, str], actions: list[dict[str, str]]) -> dict[str, Any]:
    if isinstance(graph.get("output_shape"), dict):
        graph = graph["output_shape"]
        log_action(actions, "output_shape", "unwrap_output_shape", "raw response wrapped the MFG object in output_shape")
    out: dict[str, Any] = {}
    allowed_top = {
        "case_id",
        "link_id",
        "functional_role",
        "kinematic_context",
        "primary_features",
        "functional_features",
        "structural_features",
        "surface_features",
        "feature_dependencies",
        "visual_evidence_refs",
        "interface_refs",
    }
    for key in graph:
        if key not in allowed_top:
            log_action(actions, key, "drop_top_level_non_contract_field", "not part of MFG v2 schema")
    out["case_id"] = str(graph.get("case_id") or row["case_id"])
    out["link_id"] = str(graph.get("link_id") or row["link_id"])
    out["functional_role"] = str(graph.get("functional_role") or row["role"])
    out["kinematic_context"] = graph.get("kinematic_context") if isinstance(graph.get("kinematic_context"), dict) else {}
    for section in SECTIONS:
        items = graph.get(section)
        if not isinstance(items, list):
            items = []
            log_action(actions, section, "missing_feature_section", "created empty feature list")
        out[section] = [normalize_feature(item, section, idx, actions) for idx, item in enumerate(items)]
    deps = graph.get("feature_dependencies")
    if not isinstance(deps, list):
        deps = []
        log_action(actions, "feature_dependencies", "missing_dependencies", "created empty dependency list")
    clean_deps = []
    for idx, dep in enumerate(deps):
        if isinstance(dep, dict) and {"source", "target", "relation"} <= set(dep):
            clean_deps.append({"source": str(dep["source"]), "target": str(dep["target"]), "relation": str(dep["relation"])})
        else:
            log_action(actions, f"feature_dependencies[{idx}]", "drop_invalid_dependency", "dependency missing source/target/relation")
    out["feature_dependencies"] = clean_deps
    out["visual_evidence_refs"] = normalize_refs(graph.get("visual_evidence_refs"), actions, "visual_evidence_refs")
    out["interface_refs"] = normalize_refs(graph.get("interface_refs"), actions, "interface_refs")
    return out


def candidate_graphs(version: str, row: dict[str, str]) -> list[tuple[str, dict[str, Any]]]:
    case_id, link_id = row["case_id"], row["link_id"]
    source_dir = SOURCE_EXP / "runs" / version / case_id / link_id
    candidates: list[tuple[str, dict[str, Any]]] = []
    raw = source_dir / "raw_response.txt"
    if raw.exists():
        candidates.append(("raw_response.txt", extract_json(raw.read_text(encoding="utf-8"))))
    graph = source_dir / "mechanical_feature_graph_v2.json"
    if graph.exists():
        candidates.append(("mechanical_feature_graph_v2.json", load_json(graph)))
    return candidates


def main() -> None:
    ensure_dirs()
    rows: list[dict[str, Any]] = []
    for version in VERSIONS:
        for row in frozen_rows():
            out_dir = RUNS / version / row["case_id"] / row["link_id"]
            out_dir.mkdir(parents=True, exist_ok=True)
            status = "SUCCESS"
            errors: list[str] = []
            selected_source = ""
            best_graph: dict[str, Any] | None = None
            best_actions: list[dict[str, str]] = []
            try:
                candidates = candidate_graphs(version, row)
                if not candidates:
                    raise FileNotFoundError("no v2 raw_response or graph found")
                candidate_errors = []
                for source_name, graph in candidates:
                    actions: list[dict[str, str]] = []
                    repaired = normalize_graph(copy.deepcopy(graph), row, actions)
                    try:
                        jsonschema.validate(repaired, SCHEMA)
                        selected_source = source_name
                        best_graph = repaired
                        best_actions = actions
                        break
                    except jsonschema.ValidationError as exc:
                        candidate_errors.append(f"{source_name}: {exc.message}")
                        if best_graph is None:
                            best_graph = repaired
                            best_actions = actions
                            selected_source = source_name
                if best_graph is None:
                    raise ValueError("; ".join(candidate_errors))
                try:
                    jsonschema.validate(best_graph, SCHEMA)
                except jsonschema.ValidationError as exc:
                    status = "MFG_INVALID"
                    errors = [f"schema: {exc.message}"]
                dump_json(out_dir / "mechanical_feature_graph_repaired.json", best_graph)
                dump_json(out_dir / "repair_log.json", {"source": str((SOURCE_EXP / "runs" / version / row["case_id"] / row["link_id"] / selected_source).relative_to(EXP.parents[1])), "actions": best_actions})
                dump_json(out_dir / "schema_validation_mfg.json", {"schema": "mechanical_feature_graph_v2", "valid": status == "SUCCESS", "errors": errors})
            except Exception as exc:
                status = "FAILURE"
                errors = [f"{type(exc).__name__}: {exc}"]
                dump_json(out_dir / "repair_log.json", {"source": None, "actions": [], "errors": errors})
                dump_json(out_dir / "schema_validation_mfg.json", {"schema": "mechanical_feature_graph_v2", "valid": False, "errors": errors})
            rows.append(
                {
                    "version": version,
                    "case_id": row["case_id"],
                    "link_id": row["link_id"],
                    "role": row["role"],
                    "status": status,
                    "source": selected_source,
                    "repair_action_count": len(best_actions),
                    "errors": "; ".join(errors),
                }
            )
            print(version, row["case_id"], row["link_id"], status)
    write_csv(RESULTS / "repair_generation.csv", rows)


if __name__ == "__main__":
    main()
