from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "experiments" / "modifier_parameter_repair_pilot"
SOURCE_EXP = ROOT / "experiments" / "mfg_to_ir_repair_pilot"
ROBUSTNESS_EXP = ROOT / "experiments" / "freecad_operation_robustness_pilot"
FROZEN_LINKS = ROOT / "experiments" / "freecad_robot_link_reconstruction_pilot_v2" / "inputs" / "frozen_links.csv"
SCHEMA_PATH = ROOT / "experiments" / "freecad_robot_link_reconstruction_pilot_v2" / "schemas" / "executable_cad_ir_v1_2.schema.json"
RESULTS = EXP / "results"
RUNS = EXP / "runs"
VERSIONS = ["R1", "R2"]


def ensure_dirs() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    RUNS.mkdir(parents=True, exist_ok=True)


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
    return read_csv(FROZEN_LINKS)


def source_case_dir(version: str, case_id: str, link_id: str) -> Path:
    return SOURCE_EXP / "runs" / version / case_id / link_id


def output_case_dir(version: str, case_id: str, link_id: str) -> Path:
    return RUNS / version / case_id / link_id


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


def positive_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value > 0:
        return float(value)
    if isinstance(value, str):
        stripped = value.strip().replace("mm", "").strip()
        try:
            parsed = float(stripped)
        except ValueError:
            return None
        return parsed if parsed > 0 else None
    return None
