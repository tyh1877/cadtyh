from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import jsonschema

from pilot_common import EXP, INPUTS, ROOT, RUNS, ROLE_EXPECTATIONS, dump_json, ensure_dirs, extract_json, feature_rows_from_graph, frozen_rows, load_json, urdf_link_joint_context, write_csv

sys.path.insert(0, str(ROOT / "go_nogo2" / "scripts"))
from llm_config import load_shared_llm  # noqa: E402


SCHEMA = load_json(EXP / "schemas" / "mechanical_feature_graph_v1.schema.json")


def evidence_for(row: dict[str, str], version: str) -> list[str]:
    refs = [
        row["source_plan"],
        row["urdf_path"],
        f"role:{row['role']}",
        f"proximal_joint:{row.get('proximal_joint','') or 'none'}",
        f"distal_joint:{row.get('distal_joint','') or 'none'}",
    ]
    if version == "R2":
        manifest = load_json(INPUTS / "local_evidence_manifest.json")
        for rec in manifest["records"]:
            if rec["case_id"] == row["case_id"] and rec["link_id"] == row["link_id"]:
                refs.append(f"crop:{rec['crop_id']}:{rec.get('crop_path','')}")
    return refs


def prompt_for(row: dict[str, str], version: str) -> str:
    plan = load_json(ROOT / row["source_plan"])
    context = urdf_link_joint_context(row["case_id"], row["link_id"])
    role_req = ROLE_EXPECTATIONS.get(row["role"], {"expected": [], "optional": []})
    evidence_refs = evidence_for(row, version)
    local_instruction = ""
    if version == "R2":
        local_instruction = (
            "Use the provided crop references as local visual evidence. "
            "If a crop is marked LOCAL_EVIDENCE_UNAVAILABLE, state that limitation in visual_evidence_refs and do not invent crop-specific evidence."
        )
    return f"""
Return Mechanical Feature Graph v1 JSON only. No markdown, no prose.

Version: {version}
Case/link: {row['case_id']} / {row['link_id']}
Functional role label: {row['role']}

Core task:
Infer visible or externally reasonable mechanical features for this robot-arm link.
Do not output CAD operations as features. Feature nodes must be mechanical semantics.

Forbidden planner inputs:
- GT mesh, GT CAD, GT STEP, GT segmentation, GT feature tree.
- Case-specific hidden dimensions not present in text/URDF.

Allowed evidence refs:
{json.dumps(evidence_refs, ensure_ascii=False)}

Kinematic context:
{json.dumps(context, ensure_ascii=False)[:3000]}

Frozen operation-plan semantic text:
{json.dumps(plan.get('mechanical_intent', {}), ensure_ascii=False)}

Operation families from previous vague plan:
{json.dumps([op.get('operation') or op.get('op') for op in plan.get('operations', [])], ensure_ascii=False)}

Generic link-role grammar requirements for this role:
{json.dumps(role_req, ensure_ascii=False)}

{local_instruction}

Use only these broad feature families unless there is a clear generic reason to add a feature type:
main_link_body, elongated_main_body, main_housing, support_frame, palm_plate,
proximal_joint_housing, distal_joint_housing, flange, bearing_boss, mounting_face,
mounting_boss, tool_flange, connector_housing, recess, cutout, hollow_region,
rib, web, cover_region, strengthening_boss, slot, gap, lightening_cut,
shell_housing, tapered_transition, lofted_transition, rounded_section,
fillet_group, chamfer_group, blended_joint_transition.

Each feature must contain feature_id, feature_type, priority, role, evidence,
reference_frame, approx_dimensions, shape_family, cad_strategy, dependencies,
confidence.

Return exactly one object with:
case_id, link_id, functional_role, kinematic_context, primary_features,
functional_features, structural_features, surface_features,
feature_dependencies, visual_evidence_refs, interface_refs.
"""


def invoke(client, model: str, text: str, max_tokens: int) -> tuple[str, dict[str, Any]]:
    start = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You produce strict JSON only. No chain-of-thought."},
            {"role": "user", "content": text},
        ],
        temperature=0,
        top_p=1,
        max_tokens=min(max_tokens, 8192),
        timeout=300,
    )
    content = response.choices[0].message.content or ""
    usage = getattr(response, "usage", None)
    return content, {
        "input_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
        "elapsed_seconds": time.time() - start,
        "request_id": getattr(response, "id", None),
    }


def validate_graph(graph: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        jsonschema.validate(graph, SCHEMA)
    except jsonschema.ValidationError as exc:
        return [f"schema: {exc.message}"]
    features = feature_rows_from_graph(graph)
    if not features:
        errors.append("no feature nodes")
    for feature in features:
        if feature["feature_type"] in {"extrude", "revolve", "fillet", "loft"}:
            errors.append(f"{feature['feature_id']}: CAD operation used as feature_type")
    return errors


def canonicalize_graph(graph: dict[str, Any], row: dict[str, str]) -> dict[str, Any]:
    """Canonicalize wire-format issues without adding geometry decisions."""
    graph = dict(graph)
    flat_features = graph.pop("features", None)
    flat_by_id = {}
    if isinstance(flat_features, list):
        flat_by_id = {str(f.get("feature_id")): f for f in flat_features if isinstance(f, dict) and f.get("feature_id")}
    graph["case_id"] = row["case_id"]
    graph["link_id"] = row["link_id"]
    graph.setdefault("functional_role", row["role"])
    if flat_features is not None:
        # Some models emit a flat feature list. Keep it only if the required
        # sections are missing; otherwise use it to resolve section lists of
        # feature IDs into full feature objects.
        flat = flat_features
        if not any(graph.get(section) for section in ["primary_features", "functional_features", "structural_features", "surface_features"]):
            graph["primary_features"] = [f for f in flat if f.get("priority") == "primary"]
            graph["functional_features"] = [f for f in flat if f.get("priority") == "functional"]
            graph["structural_features"] = [f for f in flat if f.get("priority") == "structural"]
            graph["surface_features"] = [f for f in flat if f.get("priority") == "surface"]
    for key in ["primary_features", "functional_features", "structural_features", "surface_features", "feature_dependencies", "visual_evidence_refs", "interface_refs"]:
        graph.setdefault(key, [])
    section_priority = {
        "primary_features": "primary",
        "functional_features": "functional",
        "structural_features": "structural",
        "surface_features": "surface",
    }
    for section, priority in section_priority.items():
        fixed = []
        for feature in graph.get(section, []):
            if isinstance(feature, str) and feature in flat_by_id:
                feature = flat_by_id[feature]
            if not isinstance(feature, dict):
                continue
            feature = dict(feature)
            feature["priority"] = priority
            if isinstance(feature.get("evidence"), str):
                feature["evidence"] = [feature["evidence"]]
            feature.setdefault("evidence", [])
            feature.setdefault("reference_frame", "link_local")
            feature.setdefault("approx_dimensions", {})
            if not isinstance(feature.get("approx_dimensions"), dict):
                feature["approx_dimensions"] = {"raw": feature.get("approx_dimensions")}
            feature.setdefault("shape_family", "unspecified")
            feature.setdefault("cad_strategy", "unspecified")
            feature.setdefault("dependencies", [])
            feature.setdefault("confidence", 0.5)
            fixed.append(feature)
        graph[section] = fixed
    deps = graph.get("feature_dependencies", [])
    if isinstance(deps, dict):
        converted = []
        for target, sources in deps.items():
            if isinstance(sources, str):
                sources = [sources]
            for source in sources or []:
                converted.append({"source": str(source), "target": str(target), "relation": "supports"})
        graph["feature_dependencies"] = converted
    else:
        converted = []
        for item in deps:
            if isinstance(item, dict):
                converted.append(
                    {
                        "source": str(item.get("source") or item.get("from") or ""),
                        "target": str(item.get("target") or item.get("to") or ""),
                        "relation": str(item.get("relation") or "supports"),
                    }
                )
        graph["feature_dependencies"] = [d for d in converted if d["source"] and d["target"]]
    refs = graph.get("visual_evidence_refs", [])
    if isinstance(refs, str):
        refs = [refs]
    graph["visual_evidence_refs"] = [str(x) for x in refs]
    interfaces = graph.get("interface_refs", [])
    if isinstance(interfaces, str):
        interfaces = [interfaces]
    graph["interface_refs"] = [str(x) for x in interfaces]
    kc = graph.get("kinematic_context") or {}
    graph["kinematic_context"] = {
        "proximal_joint": kc.get("proximal_joint"),
        "distal_joint": kc.get("distal_joint"),
    }
    return graph


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--version", choices=["R1", "R2"])
    args = parser.parse_args()
    ensure_dirs()
    cfg = load_shared_llm()
    client = cfg.create_client()
    rows = []
    for version in ["R1", "R2"]:
        if args.version and version != args.version:
            continue
        for row in frozen_rows():
            out_dir = RUNS / version / row["case_id"] / row["link_id"]
            graph_path = out_dir / "mechanical_feature_graph.json"
            manifest_path = out_dir / "manifest.json"
            if graph_path.exists() and not args.overwrite:
                print(version, row["case_id"], row["link_id"], "SKIP")
                continue
            out_dir.mkdir(parents=True, exist_ok=True)
            status = "FAILURE"
            errors: list[str] = []
            usage: dict[str, Any] = {}
            raw = ""
            try:
                raw, usage = invoke(client, cfg.model, prompt_for(row, version), cfg.max_output_tokens)
                (out_dir / "raw_feature_graph_response.txt").write_text(raw, encoding="utf-8")
                graph = canonicalize_graph(extract_json(raw), row)
                validation_errors = validate_graph(graph)
                if validation_errors:
                    status = "MFG_INVALID"
                    errors = validation_errors
                else:
                    status = "SUCCESS"
                    dump_json(graph_path, graph)
            except Exception as exc:
                errors = [f"{type(exc).__name__}: {exc}"]
            manifest = {
                "version": version,
                "case_id": row["case_id"],
                "link_id": row["link_id"],
                "status": status,
                "model": cfg.model,
                "usage": usage,
                "errors": errors,
            }
            dump_json(manifest_path, manifest)
            rows.append({k: v for k, v in manifest.items() if k != "usage"} | usage)
            print(version, row["case_id"], row["link_id"], status)
    if rows:
        write_csv(EXP / "results" / "feature_graph_generation.csv", rows)


if __name__ == "__main__":
    main()
