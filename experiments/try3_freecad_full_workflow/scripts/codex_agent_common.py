from __future__ import annotations

import csv
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parents[1]
RUN_ID = "codex_agent_v1"
RUNS = EXP / "runs" / RUN_ID
RESULTS = EXP / "results"
VIEWS = ("front", "rear", "left", "right", "top", "isometric")


@dataclass(frozen=True)
class Joint:
    joint_id: str
    joint_type: str
    parent: str
    child: str
    xyz_mm: tuple[float, float, float]
    rpy: tuple[float, float, float]
    axis: tuple[float, float, float]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def manifest(stage: str, status: str, schema_version: str, producer: str, inputs: list[Path], **extra: Any) -> dict[str, Any]:
    return {
        "stage": stage,
        "status": status,
        "input_hashes": {path.relative_to(ROOT).as_posix(): sha256(path) for path in inputs if path.is_file()},
        "schema_version": schema_version,
        "created_at": utc_now(),
        "producer": producer,
        "stale_downstream_artifacts_allowed": False,
        **extra,
    }


def parse_urdf(path: Path) -> tuple[list[str], list[Joint]]:
    root = ET.parse(path).getroot()
    links = [node.attrib["name"] for node in root.findall("link")]
    joints = []
    for index, node in enumerate(root.findall("joint")):
        origin = node.find("origin")
        axis = node.find("axis")
        # URDF permits origin elements with either attribute omitted; omission
        # means the identity value, not an invalid record.
        xyz_text = origin.get("xyz", "0 0 0") if origin is not None else "0 0 0"
        rpy_text = origin.get("rpy", "0 0 0") if origin is not None else "0 0 0"
        xyz = tuple(float(x) * 1000.0 for x in xyz_text.split())
        rpy = tuple(float(x) for x in rpy_text.split())
        axis_values = tuple(float(x) for x in ((axis.get("xyz") if axis is not None else "0 0 1").split()))
        joints.append(Joint(
            joint_id=node.get("name") or f"J{index}", joint_type=node.get("type", "fixed"),
            parent=node.find("parent").get("link"), child=node.find("child").get("link"),
            xyz_mm=xyz, rpy=rpy, axis=axis_values,
        ))
    return links, joints


def rotation_rpy(rpy: tuple[float, float, float]) -> np.ndarray:
    roll, pitch, yaw = rpy
    cr, sr, cp, sp, cy, sy = math.cos(roll), math.sin(roll), math.cos(pitch), math.sin(pitch), math.cos(yaw), math.sin(yaw)
    rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]], dtype=float)
    ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]], dtype=float)
    rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]], dtype=float)
    return rz @ ry @ rx


def transform(xyz_mm: tuple[float, float, float], rpy: tuple[float, float, float]) -> np.ndarray:
    value = np.eye(4)
    value[:3, :3] = rotation_rpy(rpy)
    value[:3, 3] = np.asarray(xyz_mm, dtype=float)
    return value


def world_transforms(links: list[str], joints: list[Joint]) -> dict[str, np.ndarray]:
    children = {joint.child: joint for joint in joints}
    roots = [link for link in links if link not in children]
    if len(roots) != 1:
        raise ValueError(f"expected one URDF root, got {roots}")
    worlds = {roots[0]: np.eye(4)}
    unresolved = list(joints)
    while unresolved:
        progressed = False
        for joint in list(unresolved):
            if joint.parent in worlds:
                worlds[joint.child] = worlds[joint.parent] @ transform(joint.xyz_mm, joint.rpy)
                unresolved.remove(joint)
                progressed = True
        if not progressed:
            raise ValueError("URDF graph is disconnected or cyclic")
    return worlds


def tryset_rows() -> list[dict[str, str]]:
    with (EXP / "tryset5_v1.csv").open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def role_for(link: str, links: list[str], joints: list[Joint]) -> str:
    incoming = [j for j in joints if j.child == link]
    outgoing = [j for j in joints if j.parent == link]
    if not incoming:
        return "base"
    if not outgoing:
        return "terminal_or_fixed_accessory" if incoming[0].joint_type == "fixed" else "end_effector"
    movable_before = sum(j.joint_type != "fixed" for j in joints if links.index(j.child) <= links.index(link))
    movable_total = max(1, sum(j.joint_type != "fixed" for j in joints))
    fraction = movable_before / movable_total
    if fraction <= 0.25:
        return "shoulder_or_upper_arm"
    if fraction <= 0.55:
        return "upper_arm_or_elbow"
    if fraction <= 0.8:
        return "forearm"
    return "wrist"


def link_geometry(link: str, links: list[str], joints: list[Joint], scale_mm: float, version: str) -> dict[str, Any]:
    outgoing = [joint for joint in joints if joint.parent == link]
    incoming = [joint for joint in joints if joint.child == link]
    candidates = [np.asarray(joint.xyz_mm, dtype=float) for joint in outgoing if np.linalg.norm(joint.xyz_mm) > 1e-3]
    base_width = max(14.0, min(85.0, scale_mm * 0.045))
    if candidates:
        endpoint = max(candidates, key=np.linalg.norm)
    else:
        endpoint = np.array([0.0, 0.0, base_width * (0.8 if incoming else 1.2)])
    length = float(np.linalg.norm(endpoint))
    if length < base_width * 0.65:
        direction = endpoint / length if length > 1e-6 else np.array([0.0, 0.0, 1.0])
        endpoint = direction * base_width * 0.65
        length = float(np.linalg.norm(endpoint))
    complexity = {"V0": 0.82, "V1": 1.0, "V2": 1.08}[version]
    width = max(base_width * complexity, min(length * 0.32, base_width * 1.5))
    if role_for(link, links, joints) == "base":
        width *= 1.6
    axes = [list(j.axis) for j in incoming if j.joint_type != "fixed"]
    axes += [(rotation_rpy(j.rpy) @ np.asarray(j.axis, dtype=float)).tolist() for j in outgoing if j.joint_type != "fixed"]
    return {
        "start_mm": [0.0, 0.0, 0.0], "end_mm": endpoint.tolist(), "length_mm": length,
        "width_mm": width, "depth_mm": width * (0.86 if version != "V0" else 1.0),
        "distal_width_mm": width * ({"V0": 1.0, "V1": 0.9, "V2": 0.72}[version]),
        "joint_axes": axes or [[0.0, 0.0, 1.0]],
        "dimension_source": "sanitized_urdf_offsets_plus_global_engineering_scale",
    }
