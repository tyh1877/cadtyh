"""Run the Operation-plan Pilot LLM diagnostic.

This script asks the configured project LLM for explicit CAD operation plans
for a small frozen set of robot links. It does not send GT mesh, original CAD,
product names, or evaluator outputs to the model.
"""
from __future__ import annotations

import base64
import csv
import json
import mimetypes
import argparse
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "operation_plan_pilot"
sys.path[:0] = [str(ROOT / "go_nogo2/scripts"), str(ROOT / "go_nogo3/scripts")]

from glm_config import load_glm  # noqa: E402
from robot_blueprint import extract_json  # noqa: E402

VIEWS = ("front", "rear", "left", "right", "top", "isometric")


def image_item(path: Path) -> dict:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"},
    }


def skeleton(path: Path) -> tuple[list[str], list[dict]]:
    root = ET.parse(path).getroot()
    links = [node.get("name") for node in root.findall("link")]
    joints = []
    for node in root.findall("joint"):
        parent = node.find("parent").get("link")
        child = node.find("child").get("link")
        axis = node.find("axis")
        origin = node.find("origin")
        joints.append(
            {
                "joint_id": node.get("name"),
                "type": node.get("type"),
                "parent_link": parent,
                "child_link": child,
                "axis": axis.get("xyz", "0 0 1") if axis is not None else "0 0 1",
                "origin_xyz": origin.get("xyz", "0 0 0") if origin is not None else "0 0 0",
                "origin_rpy": origin.get("rpy", "0 0 0") if origin is not None else "0 0 0",
            }
        )
    return links, joints


def relevant_joints(link_id: str, joints: list[dict]) -> list[dict]:
    return [j for j in joints if j["parent_link"] == link_id or j["child_link"] == link_id]


def canonicalize_plan(value: dict, case_id: str, link_id: str, joints: list[dict]) -> dict:
    """Normalize common LLM field aliases without changing model substance."""
    value["schema_version"] = "robotcad.operation_plan_pilot.v1"
    value["case_id"] = case_id
    value["link_id"] = link_id
    by_joint = {j["joint_id"]: j for j in relevant_joints(link_id, joints)}
    normalized_constraints = []
    for item in value.get("interface_constraints", []):
        if not isinstance(item, dict):
            continue
        joint_id = str(item.get("joint_id", ""))
        joint = by_joint.get(joint_id)
        if joint:
            item.setdefault("parent_link", joint["parent_link"])
            item.setdefault("child_link", joint["child_link"])
        if "constraint" not in item:
            item["constraint"] = item.get("description", item.get("purpose", "preserve listed URDF joint interface"))
        normalized_constraints.append(item)
    value["interface_constraints"] = normalized_constraints
    normalized_ops = []
    for idx, item in enumerate(value.get("operations", []), 1):
        if not isinstance(item, dict):
            continue
        if "op" not in item and "operation" in item:
            item["op"] = item["operation"]
        if "operation_id" not in item:
            item["operation_id"] = str(item.get("op_id", f"OP{idx}"))
        if "purpose" not in item:
            item["purpose"] = str(item.get("description", item.get("op", "cad operation")))
        normalized_ops.append(item)
    value["operations"] = normalized_ops
    value.setdefault("prohibited_input_ack", "No GT mesh, original CAD, product identity, or hidden labels were used.")
    return value


def link_observation(case_id: str, link_id: str) -> dict:
    path = ROOT / "try3/runs/V2" / case_id / "visual_evidence.json"
    if not path.exists():
        return {}
    value = json.loads(path.read_text())
    for item in value.get("links", []):
        if item.get("link_id") == link_id:
            return item
    return {}


def invoke(client, model: str, content: list[dict]) -> tuple[str, dict]:
    body = []
    usage = None
    rid = None
    finish = None
    for chunk in client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Return JSON only. Design an editable CAD construction operation plan for exactly one robot link. "
                    "Use only the provided images, sanitized anonymous URDF identifiers, and visual observations. "
                    "Do not use or infer product identity, original CAD, hidden labels, or GT mesh. "
                    "Prefer explicit CAD operations over primitive lists."
                ),
            },
            {"role": "user", "content": content},
        ],
        temperature=0,
        top_p=1,
        max_tokens=8192,
        stream=True,
        extra_body={"reasoning_effort": "low"},
    ):
        rid = getattr(chunk, "id", rid)
        usage = getattr(chunk, "usage", None) or usage
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        body.append(getattr(delta, "content", None) or "")
        finish = chunk.choices[0].finish_reason or finish
    u = usage
    return "".join(body), {
        "input_tokens": int(getattr(u, "prompt_tokens", 0) or 0),
        "output_tokens": int(getattr(u, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(u, "total_tokens", 0) or 0),
        "finish_reason": finish,
        "request_id": rid,
    }


def prompt_content(case_id: str, link_id: str) -> list[dict]:
    packet = json.loads((ROOT / "try1/inputs/image_text_v1" / f"{case_id}.json").read_text())
    _, joints = skeleton(ROOT / "try2/inputs/sanitized_urdf" / f"{case_id}.urdf")
    obs = link_observation(case_id, link_id)
    text = {
        "task": "Create an explicit CAD operation plan for one selected robot link.",
        "case_id": case_id,
        "target_link_id": link_id,
        "known_text_packet": packet["text_fields"],
        "target_visual_observation": obs,
        "relevant_urdf_joints": relevant_joints(link_id, joints),
        "required_schema_version": "robotcad.operation_plan_pilot.v1",
        "allowed_operations": [
            "CreateSketchProfile",
            "Extrude",
            "Loft",
            "Revolve",
            "Sweep",
            "Shell",
            "OffsetFace",
            "BooleanUnion",
            "BooleanCut",
            "ApplyFillet",
            "ApplyChamfer",
            "CreateHole",
            "CircularPattern",
            "LinearPattern",
            "Mirror",
        ],
        "minimum_expectations": [
            "Return at least 5 operations when visual evidence supports it.",
            "Include interface constraints for every listed relevant URDF joint.",
            "Use operation purposes such as base housing, boss, bearing seat, lightening cutout, bolt pattern, rounded transition, shell, flange, or taper.",
            "Avoid describing the geometry only as boxes/cylinders.",
        ],
        "output_shape": {
            "schema_version": "robotcad.operation_plan_pilot.v1",
            "case_id": case_id,
            "link_id": link_id,
            "mechanical_intent": {"role": "", "geometry_intent": "", "surface_features": []},
            "interface_constraints": [],
            "operations": [],
            "prohibited_input_ack": "No GT mesh, original CAD, product identity, or hidden labels were used.",
        },
    }
    content = [{"type": "text", "text": json.dumps(text, ensure_ascii=False)}]
    for view in VIEWS:
        content += [{"type": "text", "text": f"view={view}"}, image_item(ROOT / packet["images"][view])]
    return content


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repair-existing", action="store_true", help="Canonicalize saved raw responses without new LLM calls")
    args = parser.parse_args()
    cfg = load_glm()
    client = cfg.create_client()
    schema = json.loads((PILOT / "schemas/cad_operation_plan_v1.schema.json").read_text())
    rows = list(csv.DictReader((PILOT / "cases.csv").open(encoding="utf-8-sig")))
    for row in rows:
        case_id, link_id = row["case_id"], row["link_id"]
        run = PILOT / "runs" / case_id / link_id
        run.mkdir(parents=True, exist_ok=True)
        manifest = run / "manifest.json"
        if manifest.exists() and not args.repair_existing:
            continue
        _, joints = skeleton(ROOT / "try2/inputs/sanitized_urdf" / f"{case_id}.urdf")
        started = time.time()
        status = "FAILURE"
        error = None
        usage = {}
        raw = ""
        try:
            if args.repair_existing and (run / "raw_response.txt").exists():
                raw = (run / "raw_response.txt").read_text(encoding="utf-8")
                prior = json.loads(manifest.read_text()) if manifest.exists() else {}
                usage = prior.get("usage", {})
            else:
                raw, usage = invoke(client, cfg.model, prompt_content(case_id, link_id))
            value = canonicalize_plan(extract_json(raw), case_id, link_id, joints)
            jsonschema.validate(value, schema)
            (run / "operation_plan.json").write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
            status = "SUCCESS"
        except Exception as exc:  # preserve failure in denominator
            error = f"{type(exc).__name__}: {exc}"
        (run / "raw_response.txt").write_text(raw, encoding="utf-8")
        manifest.write_text(
            json.dumps(
                {
                    "case_id": case_id,
                    "link_id": link_id,
                    "status": status,
                    "model": cfg.model,
                    "usage": usage,
                    "error": error,
                    "elapsed_seconds": time.time() - started,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(case_id, link_id, status, flush=True)


if __name__ == "__main__":
    main()
