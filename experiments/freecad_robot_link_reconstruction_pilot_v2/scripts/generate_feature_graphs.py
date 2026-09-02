from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import sys
import time
from pathlib import Path
from typing import Any

import jsonschema
from PIL import Image

from pilot_common import (
    ARTIFACTS,
    EXP,
    FRAME,
    INPUTS,
    ROOT,
    RUNS,
    ROLE_EXPECTATIONS,
    dump_json,
    ensure_dirs,
    extract_json,
    feature_rows_from_graph,
    frozen_rows,
    load_json,
    urdf_link_joint_context,
    write_csv,
    write_text,
)

sys.path.insert(0, str(ROOT / "go_nogo2" / "scripts"))
from glm_config import load_glm  # noqa: E402


VIEWS = ("front", "rear", "left", "right", "top", "isometric")
SCHEMA = load_json(EXP / "schemas" / "mechanical_feature_graph_v2.schema.json")
ALLOWED_FEATURE_TYPES = {
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
    "recess",
    "cutout",
    "hollow_region",
    "rib",
    "web",
    "cover_region",
    "strengthening_boss",
    "slot",
    "gap",
    "lightening_cut",
    "shell_housing",
    "tapered_transition",
    "lofted_transition",
    "rounded_section",
    "fillet_group",
    "chamfer_group",
    "blended_joint_transition",
}
CAD_OPS = {"extrude", "pad", "pocket", "cut", "revolve", "loft", "sweep", "pipe", "shell", "thickness", "boolean_union", "boolean_cut", "fillet", "chamfer", "pattern", "mirror", "none"}


def compressed_image(path: Path, max_side: int = 384) -> Path:
    rel_name = str(path.resolve()).replace(":", "").replace("\\", "_").replace("/", "_")
    out = ARTIFACTS / "vlm_images" / f"{max_side}px_{rel_name}.jpg"
    if out.exists():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(path) as image:
        image = image.convert("RGB")
        image.thumbnail((max_side, max_side))
        image.save(out, quality=76, optimize=True)
    return out


def image_item(path: Path) -> dict[str, Any]:
    packed = compressed_image(path)
    mime = mimetypes.guess_type(packed.name)[0] or "image/jpeg"
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(packed.read_bytes()).decode()}"}}


def text_item(value: Any) -> dict[str, str]:
    return {"type": "text", "text": value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)}


def image_packet(row: dict[str, str]) -> dict[str, Any]:
    path = ROOT / "try1" / "inputs" / "image_text_v1" / f"{row['case_id']}.json"
    return load_json(path)


def global_image_content(row: dict[str, str]) -> tuple[list[dict[str, Any]], int]:
    packet = image_packet(row)
    content: list[dict[str, Any]] = []
    count = 0
    for view in VIEWS:
        image_path = ROOT / packet["images"][view]
        if image_path.exists():
            content.append(text_item(f"global_view:{view}"))
            content.append(image_item(image_path))
            count += 1
    return content, count


def crop_records(row: dict[str, str]) -> list[dict[str, Any]]:
    manifest = load_json(INPUTS / "local_evidence_manifest.json")
    return [
        rec
        for rec in manifest.get("records", [])
        if rec.get("case_id") == row["case_id"] and rec.get("link_id") == row["link_id"] and rec.get("crop_path")
    ]


def crop_image_content(row: dict[str, str]) -> tuple[list[dict[str, Any]], int]:
    content: list[dict[str, Any]] = []
    count = 0
    for rec in crop_records(row):
        path = Path(str(rec["crop_path"]))
        if not path.exists():
            continue
        content.append(text_item({"local_crop": {k: v for k, v in rec.items() if k != "crop_path"}, "crop_ref": f"crop:{rec['crop_id']}"}))
        content.append(image_item(path))
        count += 1
    return content, count


def invoke(client, cfg, content: list[dict[str, Any]], system: str) -> tuple[str, dict[str, Any]]:
    start = time.time()
    pieces: list[str] = []
    reasoning: list[str] = []
    usage = None
    request_id = None
    for chunk in client.chat.completions.create(
        model=cfg.model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": content},
        ],
        temperature=cfg.temperature,
        top_p=cfg.top_p,
        max_tokens=min(cfg.max_output_tokens, 8192),
        timeout=cfg.timeout_seconds,
        stream=True,
        extra_body={"reasoning_effort": "low"},
    ):
        request_id = getattr(chunk, "id", request_id)
        usage = getattr(chunk, "usage", None) or usage
        if not getattr(chunk, "choices", None):
            continue
        delta = chunk.choices[0].delta
        pieces.append(getattr(delta, "content", None) or "")
        reasoning.append(getattr(delta, "reasoning_content", None) or "")
    return "".join(pieces), {
        "input_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
        "elapsed_seconds": time.time() - start,
        "request_id": request_id,
        "content_characters": len("".join(pieces)),
        "reasoning_characters": len("".join(reasoning)),
    }


def observation_prompt(row: dict[str, str]) -> dict[str, Any]:
    return {
        "task": "Inspect real robot-link images and local crops. Return local visual observations JSON only.",
        "case_id": row["case_id"],
        "link_id": row["link_id"],
        "role": row["role"],
        "urdf_context": urdf_link_joint_context(row["case_id"], row["link_id"]),
        "rules": [
            "Use actual visible evidence from attached image_url items.",
            "Do not use GT mesh, STEP, CAD, product identity, segmentation, or evaluator output.",
            "Every observation must cite one of global_view:* or crop:* evidence refs.",
        ],
        "output_shape": {
            "case_id": row["case_id"],
            "link_id": row["link_id"],
            "observations": [
                {
                    "observation_id": "obs_001",
                    "evidence_ref": "global_view:isometric or crop:link_level_crop",
                    "mechanical_semantic": "joint housing / flange / recess / taper / bolt pattern / shell / fillet / chamfer",
                    "location": "proximal/distal/center/top/side",
                    "estimated_anchor": {"type": "link_local_normalized", "position": [0.0, 0.0, 0.0]},
                    "estimated_dimensions": {"length_mm": 80, "width_mm": 30, "height_mm": 20},
                    "confidence": 0.0,
                }
            ],
        },
    }


def graph_prompt(row: dict[str, str], version: str, observations: dict[str, Any] | None) -> dict[str, Any]:
    plan = load_json(ROOT / row["source_plan"])
    context = urdf_link_joint_context(row["case_id"], row["link_id"])
    role_req = ROLE_EXPECTATIONS.get(row["role"], {"expected": [], "optional": []})
    return {
        "task": "Return RobotCAD Mechanical Feature Graph v2 JSON only for one robot-arm link.",
        "version": f"{version}-v2",
        "case_id": row["case_id"],
        "link_id": row["link_id"],
        "functional_role": row["role"],
        "urdf_context": context,
        "engineering_text": image_packet(row).get("text_fields", {}),
        "frozen_semantic_text": plan.get("mechanical_intent", {}),
        "generic_role_expectations": role_req,
        "local_visual_observations": observations or {},
        "forbidden_inputs": ["GT mesh", "GT STEP", "GT CAD", "segmentation", "feature tree", "product identity"],
        "required_feature_fields": [
            "feature_id",
            "feature_type",
            "priority",
            "role",
            "evidence",
            "anchor",
            "local_frame",
            "dimensions",
            "attachment",
            "visible_evidence_refs",
            "intended_cad_operation",
            "confidence",
        ],
        "anchor_contract": "Use link_local_normalized coordinates in [-1,1] unless visible/URDF text justifies millimeters.",
        "dimension_contract": "Use explicit numeric length_mm/width_mm/height_mm/radius_mm/thickness_mm/depth_mm as applicable. Do not write unknown.",
        "modifier_contract": {
            "hard_rule": "For fillet_group and chamfer_group, do not invent absolute radius_mm/distance_mm unless a dimension is explicitly visible or stated. Prefer modifier_intent.",
            "required_when_feature_type_is_fillet_or_chamfer": {
                "modifier_intent": {
                    "modifier_type": "fillet or chamfer",
                    "parameter_mode": "relative unless explicit measured size is available",
                    "strength": "small_finishing, medium_structural, or unknown",
                    "safe_ratio_to_local_thickness": "0.03-0.08 for small_finishing; 0.08-0.14 only when structural blend is clearly visible",
                    "max_ratio_to_edge_length": "0.08-0.12",
                    "requires_translator_resolution": True,
                    "evidence_notes": "why this is a small finishing edge or structural blend",
                }
            },
            "dimensions_rule": "If unsure, put only a small qualitative modifier_intent and omit radius_mm/distance_mm. The translator will resolve executable CAD parameters.",
        },
        "allowed_feature_types": sorted(ALLOWED_FEATURE_TYPES),
        "allowed_cad_operations": sorted(CAD_OPS),
        "operation_mapping_expectations": {
            "joint housing / boss / flange": "revolve",
            "tapered body / transition": "loft",
            "recess / hole / lightening cut": "boolean_cut",
            "curved visible channel": "sweep",
            "hollow housing": "shell",
            "symmetric bolt or boss": "pattern or mirror",
            "rounded / beveled finishing": "fillet or chamfer",
        },
        "output_shape": {
            "case_id": row["case_id"],
            "link_id": row["link_id"],
            "functional_role": row["role"],
            "kinematic_context": {"proximal_joint": context.get("proximal_joint"), "distal_joint": context.get("distal_joint")},
            "primary_features": [],
            "functional_features": [],
            "structural_features": [],
            "surface_features": [],
            "feature_dependencies": [],
            "visual_evidence_refs": ["global_view:isometric"],
            "interface_refs": [],
        },
    }


def canonicalize_feature(feature: dict[str, Any], priority: str) -> dict[str, Any]:
    feature = dict(feature)
    feature["priority"] = priority
    if isinstance(feature.get("evidence"), str):
        feature["evidence"] = [feature["evidence"]]
    if "dimensions" not in feature and isinstance(feature.get("approx_dimensions"), dict):
        feature["dimensions"] = feature.pop("approx_dimensions")
    if "intended_cad_operation" not in feature and feature.get("cad_strategy") in CAD_OPS:
        feature["intended_cad_operation"] = feature.pop("cad_strategy")
    if "visible_evidence_refs" not in feature and isinstance(feature.get("evidence"), list):
        feature["visible_evidence_refs"] = [str(x) for x in feature["evidence"] if str(x).startswith(("global_view:", "crop:", "obs_"))]
    if feature.get("feature_type") in {"fillet_group", "chamfer_group"} or feature.get("intended_cad_operation") in {"fillet", "chamfer"}:
        intent = feature.get("modifier_intent")
        if not isinstance(intent, dict):
            dims = feature.get("dimensions") if isinstance(feature.get("dimensions"), dict) else {}
            modifier_type = "chamfer" if feature.get("feature_type") == "chamfer_group" or feature.get("intended_cad_operation") == "chamfer" else "fillet"
            intent = {
                "modifier_type": modifier_type,
                "parameter_mode": "relative",
                "strength": str(feature.get("radius_intent") or feature.get("strength") or "small_finishing"),
                "safe_ratio_to_local_thickness": 0.05,
                "max_ratio_to_edge_length": 0.1,
                "requires_translator_resolution": True,
                "evidence_notes": "canonicalized missing modifier_intent; absolute dimensions are treated as requested but non-authoritative",
            }
            if modifier_type == "fillet" and dims.get("radius_mm") is not None:
                intent["requested_radius_mm"] = dims.get("radius_mm")
            if modifier_type == "chamfer":
                value = dims.get("distance_mm", dims.get("chamfer_distance_mm", dims.get("radius_mm", dims.get("depth_mm"))))
                if value is not None:
                    intent["requested_distance_mm"] = value
        strength = intent.get("strength")
        if strength not in {"small_finishing", "medium_structural", "unknown"}:
            intent["strength"] = "small_finishing"
        if intent.get("parameter_mode") not in {"relative", "absolute", "unknown"}:
            intent["parameter_mode"] = "relative"
        intent.setdefault("requires_translator_resolution", True)
        for ratio_key, default_ratio in {"safe_ratio_to_local_thickness": 0.05, "max_ratio_to_edge_length": 0.1}.items():
            value = intent.get(ratio_key, default_ratio)
            if isinstance(value, str) and "-" in value:
                try:
                    parts = [float(x.strip()) for x in value.split("-", 1)]
                    value = sum(parts) / len(parts)
                except Exception:
                    value = default_ratio
            try:
                value = float(value)
            except Exception:
                value = default_ratio
            intent[ratio_key] = max(0.0, min(value, 0.25))
        feature["modifier_intent"] = intent
    anchor = feature.get("anchor")
    if isinstance(anchor, dict) and "position" not in anchor:
        if "type" not in anchor and "frame" in anchor:
            anchor["type"] = anchor.get("frame")
        if isinstance(anchor.get("type"), str) and "millimeter" in str(anchor.get("type")).lower():
            anchor["type"] = "link_local_mm"
        if isinstance(anchor.get("center"), list):
            anchor["position"] = anchor.pop("center")
        elif isinstance(anchor.get("point"), list):
            anchor["position"] = anchor.pop("point")
        elif isinstance(anchor.get("xyz"), list):
            anchor["position"] = anchor.pop("xyz")
        elif isinstance(anchor.get("origin"), list):
            anchor["position"] = anchor.pop("origin")
        elif isinstance(anchor.get("centers"), list) and anchor["centers"]:
            centers = anchor.pop("centers")
            anchor["position"] = [sum(float(c[i]) for c in centers) / len(centers) for i in range(3)]
        elif isinstance(anchor.get("points"), list) and anchor["points"]:
            points = anchor.pop("points")
            anchor["position"] = [sum(float(c[i]) for c in points) / len(points) for i in range(3)]
        elif isinstance(anchor.get("start"), list) and isinstance(anchor.get("end"), list):
            start, end = anchor.pop("start"), anchor.pop("end")
            anchor["position"] = [(float(start[i]) + float(end[i])) / 2.0 for i in range(3)]
    if isinstance(anchor, dict):
        if "type" not in anchor and "frame" in anchor:
            anchor["type"] = anchor.get("frame")
        if isinstance(anchor.get("type"), str) and "millimeter" in str(anchor.get("type")).lower():
            anchor["type"] = "link_local_mm"
        if "type" not in anchor and "position" in anchor:
            values = [abs(float(v)) for v in anchor["position"]]
            anchor["type"] = "link_local_normalized" if max(values) <= 1.5 else "link_local_mm"
        feature["anchor"] = {k: v for k, v in anchor.items() if k in {"type", "position", "reason"}}
    frame = feature.get("local_frame")
    if isinstance(frame, dict):
        fixed_frame = {}
        for key, default in {"x_axis": [1, 0, 0], "y_axis": [0, 1, 0], "z_axis": [0, 0, 1]}.items():
            value = frame.get(key, default)
            fixed_frame[key] = value if isinstance(value, list) and len(value) == 3 else default
        feature["local_frame"] = fixed_frame
    else:
        feature["local_frame"] = {k: v for k, v in FRAME.items() if k.endswith("_axis")}
    attachment = feature.get("attachment")
    if attachment is not None and not isinstance(attachment, dict):
        attachment = {"attached_to": str(attachment), "attachment_face": None, "relation": "attached"}
        feature["attachment"] = attachment
    if isinstance(attachment, dict) and ("attached_to" not in attachment or "attachment_face" not in attachment):
        attached_to = attachment.get("attached_to") or attachment.get("to") or attachment.get("from") or attachment.get("through") or attachment.get("around") or attachment.get("parent_feature") or attachment.get("parent_features") or attachment.get("joint") or attachment.get("proximal") or attachment.get("distal")
        if isinstance(attached_to, list):
            attached_to = ",".join(str(x) for x in attached_to)
        attachment_face = attachment.get("attachment_face") or attachment.get("face") or attachment.get("location") or None
        feature["attachment"] = {"attached_to": str(attached_to) if attached_to is not None else None, "attachment_face": str(attachment_face) if attachment_face is not None else None, "relation": str(attachment.get("relation") or "attached")}
    feature.pop("reference_frame", None)
    feature.pop("approx_dimensions", None)
    feature.pop("cad_strategy", None)
    allowed = set(SCHEMA["$defs"]["feature"]["properties"].keys())
    return {k: v for k, v in feature.items() if k in allowed}


def canonicalize_graph(graph: dict[str, Any], row: dict[str, str]) -> dict[str, Any]:
    graph = dict(graph)
    graph.pop("output_shape", None)
    flat = graph.pop("features", None)
    if isinstance(flat, list) and not any(graph.get(k) for k in ["primary_features", "functional_features", "structural_features", "surface_features"]):
        buckets = {"primary_features": [], "functional_features": [], "structural_features": [], "surface_features": []}
        for feature in flat:
            if not isinstance(feature, dict):
                continue
            priority = str(feature.get("priority") or "structural")
            section = f"{priority}_features" if priority in {"primary", "functional", "structural", "surface"} else "structural_features"
            buckets[section].append(feature)
        graph.update(buckets)
    graph["case_id"] = row["case_id"]
    graph["link_id"] = row["link_id"]
    graph.setdefault("functional_role", row["role"])
    kc = graph.get("kinematic_context") or {}
    graph["kinematic_context"] = {"proximal_joint": kc.get("proximal_joint") or row.get("proximal_joint") or None, "distal_joint": kc.get("distal_joint") or row.get("distal_joint") or None}
    for section, priority in {
        "primary_features": "primary",
        "functional_features": "functional",
        "structural_features": "structural",
        "surface_features": "surface",
    }.items():
        graph[section] = [canonicalize_feature(f, priority) for f in graph.get(section, []) if isinstance(f, dict)]
    for key in ["feature_dependencies", "visual_evidence_refs", "interface_refs"]:
        graph.setdefault(key, [])
    if isinstance(graph["visual_evidence_refs"], str):
        graph["visual_evidence_refs"] = [graph["visual_evidence_refs"]]
    graph["visual_evidence_refs"] = [x if isinstance(x, str) else json.dumps(x, ensure_ascii=False) for x in graph["visual_evidence_refs"]]
    if isinstance(graph["interface_refs"], str):
        graph["interface_refs"] = [graph["interface_refs"]]
    graph["interface_refs"] = [x if isinstance(x, str) else json.dumps(x, ensure_ascii=False) for x in graph["interface_refs"]]
    deps = []
    for item in graph.get("feature_dependencies", []):
        if isinstance(item, dict):
            source = str(item.get("source") or item.get("from") or "")
            target = str(item.get("target") or item.get("to") or "")
            if source and target:
                deps.append({"source": source, "target": target, "relation": str(item.get("relation") or "supports")})
    graph["feature_dependencies"] = deps
    return graph


def validate_graph(graph: dict[str, Any]) -> list[str]:
    try:
        jsonschema.validate(graph, SCHEMA)
    except jsonschema.ValidationError as exc:
        return [f"schema: {exc.message}"]
    errors = []
    features = feature_rows_from_graph(graph)
    if not features:
        errors.append("no feature nodes")
    for feature in features:
        if feature.get("feature_type") not in ALLOWED_FEATURE_TYPES:
            errors.append(f"{feature.get('feature_id')}: unsupported feature_type {feature.get('feature_type')}")
        if not feature.get("visible_evidence_refs"):
            errors.append(f"{feature.get('feature_id')}: missing visible_evidence_refs")
        if not feature.get("dimensions"):
            errors.append(f"{feature.get('feature_id')}: missing dimensions")
    return errors


def run_one(client, cfg, row: dict[str, str], version: str) -> dict[str, Any]:
    out_dir = RUNS / version / row["case_id"] / row["link_id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    usage_total: dict[str, Any] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "elapsed_seconds": 0.0}
    status = "FAILURE"
    errors: list[str] = []
    global_items, global_count = global_image_content(row)
    crop_items, crop_count = crop_image_content(row) if version == "R2" else ([], 0)
    audit_rows = []
    observations = None
    try:
        if version == "R2":
            obs_content = [text_item(observation_prompt(row)), *global_items, *crop_items]
            raw_obs, obs_usage = invoke(client, cfg, obs_content, "Return strict JSON only. Inspect provided robot-link images and crops.")
            for key in usage_total:
                usage_total[key] += obs_usage.get(key, 0)
            write_text(out_dir / "raw_local_observation_response.txt", raw_obs)
            observations = extract_json(raw_obs)
            dump_json(out_dir / "local_visual_observations.json", observations)
            audit_rows.append({"version": version, "case_id": row["case_id"], "link_id": row["link_id"], "stage": "local_visual_observations", "text_items": 1 + global_count + crop_count, "image_items": global_count + crop_count, "global_images": global_count, "local_crop_images": crop_count, "paths_only_prompt": False, "gt_geometry_used": False})
        graph_content = [text_item(graph_prompt(row, version, observations)), *global_items]
        if version == "R2":
            graph_content.extend(crop_items)
        raw, graph_usage = invoke(client, cfg, graph_content, "Return strict JSON only. Output RobotCAD Mechanical Feature Graph v2.")
        for key in usage_total:
            usage_total[key] += graph_usage.get(key, 0)
        write_text(out_dir / "raw_response.txt", raw)
        graph = canonicalize_graph(extract_json(raw), row)
        validation_errors = validate_graph(graph)
        dump_json(out_dir / "schema_validation.json", {"schema": "mechanical_feature_graph_v2", "valid": not validation_errors, "errors": validation_errors})
        if validation_errors:
            status = "MFG_INVALID"
            errors = validation_errors
        else:
            status = "SUCCESS"
            dump_json(out_dir / "mechanical_feature_graph_v2.json", graph)
            dump_json(out_dir / "mechanical_feature_graph.json", graph)
        audit_rows.append({"version": version, "case_id": row["case_id"], "link_id": row["link_id"], "stage": "mechanical_feature_graph_v2", "text_items": 1 + global_count + (crop_count if version == "R2" else 0), "image_items": global_count + (crop_count if version == "R2" else 0), "global_images": global_count, "local_crop_images": crop_count if version == "R2" else 0, "paths_only_prompt": False, "gt_geometry_used": False})
    except Exception as exc:
        status = "FAILURE" if status == "FAILURE" else status
        errors.append(f"{type(exc).__name__}: {exc}")
        dump_json(out_dir / "schema_validation.json", {"schema": "mechanical_feature_graph_v2", "valid": False, "errors": errors})
    manifest = {"version": version, "case_id": row["case_id"], "link_id": row["link_id"], "status": status, "model": cfg.model, "usage": usage_total, "errors": errors}
    dump_json(out_dir / "manifest.json", manifest)
    return ({k: v for k, v in manifest.items() if k != "usage"} | usage_total), audit_rows


def repair_one(row: dict[str, str], version: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    out_dir = RUNS / version / row["case_id"] / row["link_id"]
    manifest_path = out_dir / "manifest.json"
    manifest = load_json(manifest_path) if manifest_path.exists() else {}
    usage = manifest.get("usage") or {}
    status = manifest.get("status") or "FAILURE"
    errors: list[str] = []
    raw_path = out_dir / "raw_response.txt"
    if raw_path.exists():
        try:
            graph = canonicalize_graph(extract_json(raw_path.read_text(encoding="utf-8")), row)
            validation_errors = validate_graph(graph)
            dump_json(out_dir / "schema_validation.json", {"schema": "mechanical_feature_graph_v2", "valid": not validation_errors, "errors": validation_errors})
            if validation_errors:
                status = "MFG_INVALID"
                errors = validation_errors
            else:
                status = "SUCCESS"
                dump_json(out_dir / "mechanical_feature_graph_v2.json", graph)
                dump_json(out_dir / "mechanical_feature_graph.json", graph)
        except Exception as exc:
            status = "FAILURE"
            errors = [f"{type(exc).__name__}: {exc}"]
            dump_json(out_dir / "schema_validation.json", {"schema": "mechanical_feature_graph_v2", "valid": False, "errors": errors})
    else:
        errors = [f"raw_response.txt missing"]
    manifest.update({"version": version, "case_id": row["case_id"], "link_id": row["link_id"], "status": status, "model": manifest.get("model", "glm-5.3-flash"), "usage": usage, "errors": errors})
    dump_json(manifest_path, manifest)
    global_items, global_count = global_image_content(row)
    crop_count = len(crop_records(row)) if version == "R2" else 0
    audit = [{"version": version, "case_id": row["case_id"], "link_id": row["link_id"], "stage": "mechanical_feature_graph_v2", "text_items": 1 + global_count + (crop_count if version == "R2" else 0), "image_items": global_count + (crop_count if version == "R2" else 0), "global_images": global_count, "local_crop_images": crop_count if version == "R2" else 0, "paths_only_prompt": False, "gt_geometry_used": False}]
    if version == "R2" and (out_dir / "local_visual_observations.json").exists():
        audit.insert(0, {"version": version, "case_id": row["case_id"], "link_id": row["link_id"], "stage": "local_visual_observations", "text_items": 1 + global_count + crop_count, "image_items": global_count + crop_count, "global_images": global_count, "local_crop_images": crop_count, "paths_only_prompt": False, "gt_geometry_used": False})
    return ({k: v for k, v in manifest.items() if k != "usage"} | usage), audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--version", choices=["R1", "R2"])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--repair-existing", action="store_true")
    args = parser.parse_args()
    ensure_dirs()
    cfg = load_glm()
    client = cfg.create_client()
    rows = []
    audit = []
    for version in ["R1", "R2"]:
        if args.version and version != args.version:
            continue
        done = 0
        for row in frozen_rows():
            if args.limit is not None and done >= args.limit:
                break
            out_dir = RUNS / version / row["case_id"] / row["link_id"]
            if (out_dir / "manifest.json").exists() and not args.overwrite:
                print(version, row["case_id"], row["link_id"], "SKIP")
                continue
            record, audit_rows = repair_one(row, version) if args.repair_existing else run_one(client, cfg, row, version)
            rows.append(record)
            audit.extend(audit_rows)
            print(version, row["case_id"], row["link_id"], record["status"])
            done += 1
    if rows:
        write_csv(EXP / "results" / "feature_graph_generation.csv", rows)
    if audit:
        write_csv(EXP / "results" / "vlm_input_audit.csv", audit)


if __name__ == "__main__":
    main()
