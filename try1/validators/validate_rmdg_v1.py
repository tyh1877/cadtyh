"""JSON Schema plus deterministic semantic validation for RMDG v1."""
from __future__ import annotations

import json
import math
import sys
from collections import deque
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "rmdg_v1.schema.json"


def validate(graph: dict) -> dict:
    errors: list[dict] = []
    try:
        jsonschema.validate(graph, json.loads(SCHEMA.read_text(encoding="utf-8")))
    except jsonschema.ValidationError as exc:
        return {"syntax_valid": False, "semantic_valid": False, "errors": [{"code": "SCHEMA", "path": list(exc.absolute_path), "message": exc.message}]}
    links, joints, robot = graph["links"], graph["joints"], graph["robot"]
    link_ids, joint_ids = [x["link_id"] for x in links], [x["joint_id"] for x in joints]
    if len(link_ids) != len(set(link_ids)): errors.append({"code": "DUPLICATE_LINK_ID"})
    if len(joint_ids) != len(set(joint_ids)): errors.append({"code": "DUPLICATE_JOINT_ID"})
    known = set(link_ids)
    if robot["base_link_id"] not in known: errors.append({"code": "MISSING_BASE"})
    if robot["end_effector_link_id"] not in known: errors.append({"code": "MISSING_END_EFFECTOR"})
    child_to_joint, outgoing = {}, {link: [] for link in known}
    for joint in joints:
        parent, child = joint["parent_link_id"], joint["child_link_id"]
        if parent not in known or child not in known: errors.append({"code": "UNKNOWN_LINK", "joint_id": joint["joint_id"]}); continue
        if parent == child: errors.append({"code": "SELF_EDGE", "joint_id": joint["joint_id"]})
        if child in child_to_joint: errors.append({"code": "MULTIPLE_PARENTS", "link_id": child})
        child_to_joint[child] = joint["joint_id"]; outgoing[parent].append(child)
        axis, origin = joint["axis_base"], joint["origin_base_mm"]
        if not all(math.isfinite(float(v)) for v in axis + origin): errors.append({"code": "NONFINITE", "joint_id": joint["joint_id"]})
        norm = math.sqrt(sum(float(v) ** 2 for v in axis))
        if joint["joint_type"] not in {"fixed", "unknown"} and not .99 <= norm <= 1.01: errors.append({"code": "AXIS_NORM", "joint_id": joint["joint_id"]})
        limit = joint["limit"]
        if limit["lower_rad"] is not None and limit["upper_rad"] is not None and not limit["lower_rad"] < limit["upper_rad"]: errors.append({"code": "LIMIT_ORDER", "joint_id": joint["joint_id"]})
    for link in links:
        expected_parent = child_to_joint.get(link["link_id"])
        if link["parent_joint_id"] != expected_parent: errors.append({"code": "PARENT_LINK_MISMATCH", "link_id": link["link_id"]})
        listed = set(link["child_joint_ids"]); actual = {j["joint_id"] for j in joints if j["parent_link_id"] == link["link_id"]}
        if listed != actual: errors.append({"code": "CHILD_LINK_MISMATCH", "link_id": link["link_id"]})
    if robot["base_link_id"] in known:
        seen, queue = set(), deque([robot["base_link_id"]])
        while queue:
            node = queue.popleft()
            if node in seen: errors.append({"code": "GRAPH_CYCLE", "link_id": node}); continue
            seen.add(node); queue.extend(outgoing.get(node, []))
        if known and seen != known: errors.append({"code": "DISCONNECTED_OR_CYCLE"})
        if robot["end_effector_link_id"] not in seen: errors.append({"code": "NO_BASE_TO_END_PATH"})
    return {"syntax_valid": True, "semantic_valid": not errors, "errors": errors}


if __name__ == "__main__":
    report = validate(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
    print(json.dumps(report, indent=2)); raise SystemExit(0 if report["semantic_valid"] else 1)
