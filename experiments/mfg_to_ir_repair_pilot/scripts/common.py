from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "experiments" / "mfg_to_ir_repair_pilot"
SOURCE_EXP = ROOT / "experiments" / "freecad_robot_link_reconstruction_pilot_v2"
RESULTS = EXP / "results"
RUNS = EXP / "runs"
SCHEMAS = SOURCE_EXP / "schemas"
INPUTS = SOURCE_EXP / "inputs"

FRAME = {
    "origin": [0, 0, 0],
    "x_axis": [1, 0, 0],
    "y_axis": [0, 1, 0],
    "z_axis": [0, 0, 1],
}

VERSIONS = ["R1", "R2"]


def ensure_dirs() -> None:
    for path in [RESULTS, RUNS]:
        path.mkdir(parents=True, exist_ok=True)


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


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def frozen_rows() -> list[dict[str, str]]:
    return read_csv(INPUTS / "frozen_links.csv")


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


def feature_rows_from_graph(graph: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for section in ["primary_features", "functional_features", "structural_features", "surface_features"]:
        for feature in graph.get(section, []):
            if isinstance(feature, dict):
                item = dict(feature)
                item["section"] = section
                rows.append(item)
    return rows


def role_scale(role: str) -> tuple[float, float, float]:
    if role == "base_or_shoulder":
        return 120.0, 90.0, 42.0
    if role in {"upper_arm", "main_link", "forearm"}:
        return 160.0, 42.0, 28.0
    if role == "elbow_housing":
        return 90.0, 75.0, 50.0
    if role == "wrist_or_tool_side_link":
        return 95.0, 55.0, 24.0
    return 100.0, 50.0, 30.0
