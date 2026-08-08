"""Validation and fixed prompt contract for blind robot reconstruction."""

from __future__ import annotations

import json
import math
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "robot_blueprint.schema.json"
ALLOWED_PRIMITIVES = ("box", "cylinder", "sphere", "cone")


class BlueprintError(ValueError):
    pass


def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def extract_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        last_fence = text.rfind("```")
        if first_newline >= 0 and last_fence > first_newline:
            text = text[first_newline + 1:last_fence].strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError as error:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise BlueprintError(f"response is not JSON: {error}") from error
        try:
            value = json.loads(text[start:end + 1])
        except json.JSONDecodeError as nested:
            raise BlueprintError(f"response contains invalid JSON: {nested}") from nested
    if not isinstance(value, dict):
        raise BlueprintError("blueprint root must be an object")
    return value


def _normal(vector: list[float], label: str) -> list[float]:
    length = math.sqrt(sum(float(item) ** 2 for item in vector))
    if not math.isfinite(length) or length < 1e-9:
        raise BlueprintError(f"{label} must be non-zero")
    return [float(item) / length for item in vector]


def validate_blueprint(
    blueprint: dict[str, Any], *, expected_links: int, expected_joints: int,
    expected_dof: int,
) -> dict[str, Any]:
    try:
        jsonschema.validate(blueprint, load_schema())
    except jsonschema.ValidationError as error:
        location = "/".join(str(item) for item in error.absolute_path)
        raise BlueprintError(f"schema error at {location or '<root>'}: {error.message}") from error

    links, joints = blueprint["links"], blueprint["joints"]
    if len(links) != expected_links:
        raise BlueprintError(f"expected {expected_links} links, got {len(links)}")
    if len(joints) != expected_joints:
        raise BlueprintError(f"expected {expected_joints} joints, got {len(joints)}")
    link_names = [item["name"] for item in links]
    joint_names = [item["name"] for item in joints]
    if len(set(link_names)) != len(link_names):
        raise BlueprintError("link names must be unique")
    if len(set(joint_names)) != len(joint_names):
        raise BlueprintError("joint names must be unique")
    known = set(link_names)
    children: set[str] = set()
    graph: dict[str, list[str]] = defaultdict(list)
    for index, joint in enumerate(joints):
        parent, child = joint["parent"], joint["child"]
        if parent not in known or child not in known:
            raise BlueprintError(f"joint {joint['name']} references an unknown link")
        if parent == child or child in children:
            raise BlueprintError(f"joint {joint['name']} violates rooted-tree structure")
        children.add(child)
        graph[parent].append(child)
        joint["axis"] = _normal(joint["axis"], f"joints/{index}/axis")
        if joint["type"] in {"revolute", "prismatic"} and joint["lower"] >= joint["upper"]:
            raise BlueprintError(f"joint {joint['name']} requires lower < upper")
    roots = known - children
    if len(roots) != 1:
        raise BlueprintError(f"expected one root link, got {sorted(roots)}")
    visited, queue = set(), deque(roots)
    while queue:
        node = queue.popleft()
        if node in visited:
            raise BlueprintError("joint graph contains a cycle")
        visited.add(node)
        queue.extend(graph[node])
    if visited != known:
        raise BlueprintError("joint graph is disconnected")
    dof = sum(joint["type"] in {"revolute", "continuous", "prismatic"} for joint in joints)
    if dof != expected_dof:
        raise BlueprintError(f"expected {expected_dof} actuated DOF, got {dof}")
    for link_index, link in enumerate(links):
        for primitive_index, primitive in enumerate(link["primitives"]):
            if "axis" in primitive:
                primitive["axis"] = _normal(
                    primitive["axis"],
                    f"links/{link_index}/primitives/{primitive_index}/axis",
                )
    return blueprint


def blueprint_contract() -> str:
    return """
Return exactly one JSON object, without markdown, using this contract:
{
  "schema_version": "1.0", "units": "mm",
  "links": [{"name": "base_link", "primitives": [PRIMITIVE, ...]}, ...],
  "joints": [{
    "name": "joint_1", "parent": "base_link", "child": "link_1",
    "type": "fixed|revolute|continuous|prismatic",
    "origin_xyz": [x,y,z], "origin_rpy": [r,p,y], "axis": [x,y,z],
    "lower": number, "upper": number
  }, ...]
}
PRIMITIVE is one of:
- {"type":"box", "center":[x,y,z], "size":[width,height,depth]}
- {"type":"cylinder", "center":[x,y,z], "radius":r, "height":h, "axis":[x,y,z]}
- {"type":"sphere", "center":[x,y,z], "radius":r}
- {"type":"cone", "center":[x,y,z], "bottom_radius":r1,
   "top_radius":r2, "height":h, "axis":[x,y,z]}

Use millimetres for geometry and joint translations, radians for angles. Each
link is modeled in its own local frame, with its incoming joint near the local
origin. Use 1-8 primitives per link. The joints must form one rooted tree. Fixed
joints have lower=upper=0. Every non-fixed axis must be non-zero. Match the
link count, joint count, and actuated DOF stated in the user prompt exactly.
Infer proportions, geometry, joint placement, and axes only from the supplied
prompt and six views; never assume access to a hidden URDF or hidden meshes.
""".strip()
