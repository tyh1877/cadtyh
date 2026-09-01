from __future__ import annotations

import csv
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "experiments" / "freecad_robot_link_reconstruction_pilot_v2"
RESULTS = EXP / "results"
RUNS = EXP / "runs"
ARTIFACTS = EXP / "artifacts"
INPUTS = EXP / "inputs"

FRAME = {
    "origin": [0, 0, 0],
    "x_axis": [1, 0, 0],
    "y_axis": [0, 1, 0],
    "z_axis": [0, 0, 1],
}

VERSIONS = ["R0", "R1", "R2"]

ROLE_EXPECTATIONS = {
    "base_or_shoulder": {
        "expected": ["main_housing", "flange", "proximal_joint_housing", "mounting_boss", "fillet_group", "chamfer_group"],
        "optional": ["recess", "cutout"],
    },
    "upper_arm": {
        "expected": ["elongated_main_body", "proximal_joint_housing", "distal_joint_housing", "tapered_transition", "lightening_cut", "fillet_group"],
        "optional": ["chamfer_group", "recess", "cover_region"],
    },
    "main_link": {
        "expected": ["elongated_main_body", "proximal_joint_housing", "distal_joint_housing", "tapered_transition", "recess", "fillet_group"],
        "optional": ["shell_housing", "chamfer_group"],
    },
    "elbow_housing": {
        "expected": ["main_housing", "proximal_joint_housing", "distal_joint_housing", "web", "recess", "fillet_group"],
        "optional": ["flange", "chamfer_group"],
    },
    "forearm": {
        "expected": ["elongated_main_body", "proximal_joint_housing", "distal_joint_housing", "tapered_transition", "lightening_cut", "fillet_group"],
        "optional": ["chamfer_group", "cover_region"],
    },
    "wrist_or_tool_side_link": {
        "expected": ["palm_plate", "tool_flange", "mounting_face", "gap", "mounting_boss", "fillet_group"],
        "optional": ["chamfer_group", "recess"],
    },
}

FEATURE_FAMILY = {
    "main_link_body": "primary",
    "elongated_main_body": "primary",
    "main_housing": "primary",
    "support_frame": "primary",
    "palm_plate": "primary",
    "proximal_joint_housing": "functional",
    "distal_joint_housing": "functional",
    "flange": "functional",
    "bearing_boss": "functional",
    "mounting_face": "functional",
    "mounting_boss": "functional",
    "tool_flange": "functional",
    "connector_housing": "functional",
    "recess": "structural",
    "cutout": "structural",
    "hollow_region": "structural",
    "rib": "structural",
    "web": "structural",
    "cover_region": "structural",
    "strengthening_boss": "structural",
    "slot": "structural",
    "gap": "structural",
    "lightening_cut": "structural",
    "shell_housing": "structural",
    "tapered_transition": "surface",
    "lofted_transition": "surface",
    "rounded_section": "surface",
    "fillet_group": "surface",
    "chamfer_group": "surface",
    "blended_joint_transition": "surface",
}


def ensure_dirs() -> None:
    for path in [RESULTS, RUNS, ARTIFACTS, INPUTS, EXP / "docs", EXP / "schemas"]:
        path.mkdir(parents=True, exist_ok=True)
    for version in VERSIONS:
        (RUNS / version).mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(rows)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def frozen_rows() -> list[dict[str, str]]:
    return read_csv(INPUTS / "frozen_links.csv")


def normalize_case_for_render(case_id: str) -> str:
    return case_id.replace("dev_", "")


def urdf_link_joint_context(case_id: str, link_id: str) -> dict[str, Any]:
    path = ROOT / "try2" / "inputs" / "sanitized_urdf" / f"{case_id}.urdf"
    if not path.exists():
        return {"proximal_joint": None, "distal_joint": None, "joints": []}
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    joints = []
    for joint in root.findall("joint"):
        name = joint.attrib.get("name")
        parent = joint.find("parent")
        child = joint.find("child")
        origin = joint.find("origin")
        axis = joint.find("axis")
        parent_link = parent.attrib.get("link") if parent is not None else None
        child_link = child.attrib.get("link") if child is not None else None
        item = {
            "name": name,
            "type": joint.attrib.get("type"),
            "parent": parent_link,
            "child": child_link,
            "origin_xyz": [float(x) for x in origin.attrib.get("xyz", "0 0 0").split()] if origin is not None else [0.0, 0.0, 0.0],
            "axis": [float(x) for x in axis.attrib.get("xyz", "0 0 1").split()] if axis is not None else [0.0, 0.0, 1.0],
        }
        joints.append(item)
    proximal = next((j for j in joints if j.get("child") == link_id), None)
    distal = next((j for j in joints if j.get("parent") == link_id), None)
    return {
        "proximal_joint": proximal["name"] if proximal else None,
        "distal_joint": distal["name"] if distal else None,
        "proximal": proximal,
        "distal": distal,
        "joints": joints,
    }


def feature_rows_from_graph(graph: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for section in ["primary_features", "functional_features", "structural_features", "surface_features"]:
        for feature in graph.get(section, []):
            item = dict(feature)
            item["section"] = section
            rows.append(item)
    return rows


def extract_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object found")
    return json.loads(text[start : end + 1])
