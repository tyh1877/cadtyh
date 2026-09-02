from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "experiments" / "freecad_operation_robustness_pilot"
SOURCE_EXP = ROOT / "experiments" / "mfg_to_ir_repair_pilot"
FROZEN_LINKS = ROOT / "experiments" / "freecad_robot_link_reconstruction_pilot_v2" / "inputs" / "frozen_links.csv"
RESULTS = EXP / "results"
RUNS = EXP / "runs"
VERSIONS = ["R1", "R2"]

FRAME = {"origin": [0, 0, 0], "x_axis": [1, 0, 0], "y_axis": [0, 1, 0], "z_axis": [0, 0, 1]}


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


def input_ir_path(version: str, case_id: str, link_id: str) -> Path:
    return SOURCE_EXP / "runs" / version / case_id / link_id / "executable_cad_ir_v1_2.json"


def profile_rect(center: list[float], size: list[float]) -> dict[str, Any]:
    return {"profile_type": "rectangle", "closed": True, "parameters": {"center": center, "size_mm": size}}


def profile_circle(center: list[float], radius: float) -> dict[str, Any]:
    return {"profile_type": "circle", "closed": True, "parameters": {"center": center, "radius_mm": radius}}


def op(op_id: str, op_type: str, target: str, deps: list[str], **kwargs: Any) -> dict[str, Any]:
    return {"op_id": op_id, "op_type": op_type, "target_body": target, "dependencies": deps, "reference_frame": FRAME, **kwargs}
