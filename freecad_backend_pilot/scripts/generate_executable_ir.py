"""Generate Executable CAD IR v1 for the frozen six-link FreeCAD pilot."""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "go_nogo2" / "scripts"))

from glm_config import load_glm  # noqa: E402
from llm_config import load_shared_llm  # noqa: E402
from robot_blueprint import extract_json  # noqa: E402

PILOT = ROOT / "freecad_backend_pilot"
RUNS = PILOT / "runs"
SCHEMA_PATH = PILOT / "schemas" / "executable_cad_ir_v1.schema.json"
MANIFEST = PILOT / "input_manifest.csv"


FRAME = {
    "origin": [0, 0, 0],
    "x_axis": [1, 0, 0],
    "y_axis": [0, 1, 0],
    "z_axis": [0, 0, 1],
}

REQUIRED_FIELDS = {
    "extrude": {"profile", "distance_mm", "operation_mode", "reference_frame"},
    "pad": {"profile", "distance_mm", "operation_mode", "reference_frame"},
    "revolve": {"profile", "axis", "angle_deg", "operation_mode", "reference_frame"},
    "loft": {"profiles", "solid", "operation_mode", "reference_frame"},
    "sweep": {"profile", "profile_frame", "path", "orientation_mode", "transition_mode", "solid", "operation_mode", "reference_frame"},
    "pipe": {"profile", "profile_frame", "path", "orientation_mode", "transition_mode", "solid", "operation_mode", "reference_frame"},
    "shell": {"faces_to_remove", "thickness_mm", "direction", "join_mode", "reference_frame"},
    "thickness": {"faces_to_remove", "thickness_mm", "direction", "join_mode", "reference_frame"},
    "boolean_union": {"tool_bodies", "reference_frame"},
    "boolean_cut": {"tool_bodies", "reference_frame"},
    "cut": {"tool_bodies", "reference_frame"},
    "pocket": {"tool_bodies", "reference_frame"},
    "fillet": {"edge_selectors", "radius_mm", "reference_frame"},
    "chamfer": {"edge_selectors", "distance_mm", "reference_frame"},
    "pattern": {"target_features", "pattern_type", "axis_or_direction", "count", "spacing_or_angle", "reference_frame"},
    "mirror": {"target_features", "mirror_plane", "reference_frame"},
}


def validate_ir(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(value, schema)
    except jsonschema.ValidationError as exc:
        errors.append(f"schema: {exc.message}")
        return errors
    seen = {body["body_id"] for body in value.get("bodies", [])}
    for op in value.get("operations", []):
        op_id = op.get("op_id", "<missing>")
        op_type = op.get("op_type")
        required = REQUIRED_FIELDS.get(op_type, set())
        missing = sorted(field for field in required if field not in op)
        if missing:
            errors.append(f"{op_id}: missing {','.join(missing)}")
        if op_type == "revolve" and not missing:
            profile = op.get("profile", {})
            params = profile.get("parameters", {})
            center = params.get("center")
            axis_point = op.get("axis", {}).get("point")
            axis_dir = op.get("axis", {}).get("direction")
            if center and axis_point and axis_dir:
                # The current IR v1 backend constructs profiles in the XY
                # plane. A native FreeCAD revolution must rotate around an
                # axis that lies in that sketch plane. Reject axes parallel to
                # the profile-plane normal rather than letting FreeCAD fail
                # later with an invalid/null BRep.
                if abs(float(axis_dir[2])) > 0.9:
                    errors.append(f"{op_id}: revolve axis is normal to the XY profile plane")
                if abs(float(axis_dir[1])) > 0.9 and abs(float(center[0]) - float(axis_point[0])) < 1e-6:
                    errors.append(f"{op_id}: revolve profile center lies on Y-axis of revolution")
        deps = op.get("dependencies", [])
        for dep in deps:
            if dep not in seen:
                errors.append(f"{op_id}: unknown dependency {dep}")
        target = op.get("target_body")
        if op_type in {"boolean_union", "boolean_cut", "cut", "pocket", "fillet", "chamfer", "shell", "thickness"}:
            if target not in seen:
                errors.append(f"{op_id}: target_body {target!r} does not reference an existing body/op")
        for tool in op.get("tool_bodies", []):
            if tool not in seen:
                errors.append(f"{op_id}: unknown tool_body {tool}")
        for feature in op.get("target_features", []):
            if feature not in seen:
                errors.append(f"{op_id}: unknown target_feature {feature}")
        seen.add(op_id)
    return errors


def canonicalize_aliases(value: dict[str, Any]) -> dict[str, Any]:
    """Canonicalize non-geometric wire-format aliases only."""
    value = dict(value)
    bodies = []
    for body in value.get("bodies", []):
        if isinstance(body, str):
            bodies.append({"body_id": body})
        else:
            bodies.append(body)
    value["bodies"] = bodies
    ops = []
    for op in value.get("operations", []):
        op = dict(op)
        if "edge_selectors" not in op and "edge_ids" in op:
            selectors = []
            for item in op.get("edge_ids", []):
                digits = "".join(ch for ch in str(item) if ch.isdigit())
                if digits:
                    selectors.append({"edge_index": int(digits)})
            op["edge_selectors"] = selectors
            op.pop("edge_ids", None)
        ops.append(op)
    value["operations"] = ops
    return value


def prompt_for(row: dict[str, str], plan: dict[str, Any], urdf_text: str) -> str:
    intent = plan.get("mechanical_intent", {})
    compact_plan = {
        "role": row["role"],
        "geometry_intent": intent.get("geometry_intent", ""),
        "interface_constraints": plan.get("interface_constraints", []),
        "requested_operations": row["requested_operations"].split(";"),
    }
    return f"""
Generate STRICT Executable CAD IR v1 JSON only for one anonymous robot link.

Hard constraints:
- ir_version must be "executable_cad_ir_v1".
- case_id: {row['case_id']}
- link_id: {row['link_id']}
- Do not use GT mesh, STEP, CAD, product names, or hidden labels.
- Do not output natural language outside JSON.
- Do not ask the backend to infer geometry from description.
- Use only millimetres.
- Every operation must include op_id, op_type, target_body, dependencies, reference_frame.
- target_body for modifier operations must reference an existing body_id or previous op_id.
- dependencies must reference only existing body_id or previous op_id.
- bodies must be objects: [{{"body_id":"body"}}], not strings.
- Use simple executable geometry, not visual-perfect geometry.
- Output exactly 5 operations.
- Required structure: op_001 extrude base, op_002 revolve boss, op_003 loft tapered feature, op_004 boolean_union, op_005 fillet.
- For revolve, the closed profile must be offset from the axis. Do not place
  the rectangle center on the axis point. Example: axis point x=45, profile
  center x=55. In this pilot, revolve axis direction must be [0,1,0] so the
  axis lies in the XY profile plane; do not use [0,0,1].
- Use linear pattern, not circular pattern, in this IR v1 pilot.
- Loft must include "solid": true.
- Fillet must use "edge_selectors":[{{"edge_index":1}}], not edge_ids.
- Valid profiles:
  - rectangle: {{"profile_type":"rectangle","closed":true,"parameters":{{"center":[x,y,z],"size_mm":[sx,sy]}}}}
  - circle: {{"profile_type":"circle","closed":true,"parameters":{{"center":[x,y,z],"radius_mm":r}}}}
  - annulus: {{"profile_type":"annulus","closed":true,"parameters":{{"center":[x,y,z],"outer_radius_mm":r1,"inner_radius_mm":r2}}}}
  - polyline: {{"profile_type":"polyline","closed":true,"parameters":{{"points":[[x,y,z],...]}}}}

Reference frame template:
{json.dumps(FRAME)}

Example operation snippets:
{{
  "op_id":"op_001",
  "op_type":"extrude",
  "target_body":"body",
  "dependencies":["body"],
  "reference_frame":{json.dumps(FRAME)},
  "profile":{{"profile_type":"rectangle","closed":true,"parameters":{{"center":[0,0,0],"size_mm":[80,30]}}}},
  "distance_mm":20,
  "operation_mode":"new_body"
}}

{{
  "op_id":"op_002",
  "op_type":"revolve",
  "target_body":"boss",
  "dependencies":["body"],
  "reference_frame":{json.dumps(FRAME)},
  "profile":{{"profile_type":"rectangle","closed":true,"parameters":{{"center":[55,0,0],"size_mm":[8,18]}}}},
  "axis":{{"point":[45,0,0],"direction":[0,1,0]}},
  "angle_deg":360,
  "operation_mode":"new_body"
}}

{{
  "op_id":"op_003",
  "op_type":"boolean_union",
  "target_body":"op_001",
  "dependencies":["op_001","op_002"],
  "reference_frame":{json.dumps(FRAME)},
  "tool_bodies":["op_002"]
}}

Existing non-GT semantic operation plan:
{json.dumps(compact_plan, ensure_ascii=False)}

Return exactly one JSON object with keys:
ir_version, case_id, link_id, bodies, operations, final_object.
"""


def invoke(client, model: str, text: str, max_tokens: int):
    chunks = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You output strict JSON CAD IR only. No markdown. No prose.",
            },
            {"role": "user", "content": text},
        ],
        temperature=0,
        top_p=1,
        max_tokens=min(max_tokens, 4096),
        timeout=90,
        stream=True,
    )
    body: list[str] = []
    usage = None
    request_id = None
    finish_reason = None
    for chunk in chunks:
        request_id = getattr(chunk, "id", request_id)
        usage = getattr(chunk, "usage", None) or usage
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        body.append(getattr(delta, "content", None) or "")
        finish_reason = chunk.choices[0].finish_reason or finish_reason
    return "".join(body), {
        "input_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
        "request_id": request_id,
        "finish_reason": finish_reason,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--case")
    parser.add_argument("--link")
    parser.add_argument("--provider", choices=("qwen", "glm"), default="qwen")
    args = parser.parse_args()
    cfg = load_shared_llm() if args.provider == "qwen" else load_glm()
    client = cfg.create_client()
    RUNS.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(MANIFEST.open(encoding="utf-8", newline="")))
    for row in rows:
        if args.case and row["case_id"] != args.case:
            continue
        if args.link and row["link_id"] != args.link:
            continue
        out_dir = RUNS / row["case_id"] / row["link_id"]
        manifest_path = out_dir / "manifest.json"
        if manifest_path.exists() and not args.overwrite:
            print(row["case_id"], row["link_id"], "SKIP")
            continue
        out_dir.mkdir(parents=True, exist_ok=True)
        start = time.time()
        source_plan = ROOT / row["source_plan"]
        plan = json.loads(source_plan.read_text(encoding="utf-8"))
        urdf_path = ROOT / "try2" / "inputs" / "sanitized_urdf" / f"{row['case_id']}.urdf"
        urdf_text = urdf_path.read_text(encoding="utf-8")
        status = "FAILURE"
        errors: list[str] = []
        usage: dict[str, Any] = {}
        raw = ""
        try:
            raw, usage = invoke(client, cfg.model, prompt_for(row, plan, urdf_text), cfg.max_output_tokens)
            (out_dir / "raw_response.txt").write_text(raw, encoding="utf-8")
            value = canonicalize_aliases(extract_json(raw))
            validation_errors = validate_ir(value)
            if validation_errors:
                status = "IR_INCOMPLETE"
                errors = validation_errors
            else:
                status = "SUCCESS"
                (out_dir / "executable_cad_ir.json").write_text(json.dumps(value, indent=2), encoding="utf-8")
        except Exception as exc:
            errors = [f"{type(exc).__name__}: {exc}"]
        manifest = {
            "case_id": row["case_id"],
            "link_id": row["link_id"],
            "source_plan": row["source_plan"],
            "status": status,
            "model": cfg.model,
            "usage": usage,
            "errors": errors,
            "elapsed_seconds": time.time() - start,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(row["case_id"], row["link_id"], status)


if __name__ == "__main__":
    main()
