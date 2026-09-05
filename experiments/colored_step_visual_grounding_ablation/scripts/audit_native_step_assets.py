"""Audit geometry/view parity for the native STEP A0/A1/A2 assets."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parents[1]
MANIFEST = EXP / "native_step5_v1.csv"
ARTIFACTS = EXP / "artifacts" / "native_step5"
RESULTS = EXP / "results"
VIEWS = ["front", "rear", "left", "right", "top", "isometric"]


def foreground(path: Path) -> np.ndarray:
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)
    return np.any(rgb < 248, axis=2)


def iou(a: np.ndarray, b: np.ndarray) -> float:
    union = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum() / union) if union else 1.0


def main() -> int:
    rows = list(csv.DictReader(MANIFEST.open("r", encoding="utf-8")))
    detail = []
    cases = []
    for row in rows:
        root = ARTIFACTS / row["case_id"]
        asset = json.loads((root / "asset_result.json").read_text(encoding="utf-8"))
        manifest = json.loads((root / "component_manifest.json").read_text(encoding="utf-8"))
        minimum = 1.0
        identical_a1_a2 = True
        complete = True
        for view in VIEWS:
            a0 = root / "A0_controlled" / "renders" / f"{view}.png"
            a1 = root / "A1_color_only" / "renders" / f"{view}.png"
            a2 = root / "A2_color_legend" / "renders" / f"{view}.png"
            complete = complete and a0.is_file() and a1.is_file() and a2.is_file()
            value = iou(foreground(a0), foreground(a1)) if complete else 0.0
            minimum = min(minimum, value)
            byte_equal = a1.read_bytes() == a2.read_bytes() if complete else False
            identical_a1_a2 = identical_a1_a2 and byte_equal
            detail.append({"case_id": row["case_id"], "view": view, "a0_a1_silhouette_iou": value, "a1_a2_byte_equal": byte_equal})
        pass_case = (
            asset.get("status") == "SUCCESS"
            and asset.get("source_solids") == int(row["expected_solids"])
            and asset.get("reopened_solids") == int(row["expected_solids"])
            and asset.get("step_color_entities", 0) > 0
            and complete and identical_a1_a2 and minimum >= 0.995
            and len(manifest["components"]) == asset.get("leaf_components")
        )
        cases.append({
            "case_id": row["case_id"], "status": "PASS" if pass_case else "FAIL",
            "leaf_components": asset.get("leaf_components", 0),
            "source_solids": asset.get("source_solids", 0),
            "reopened_solids": asset.get("reopened_solids", 0),
            "step_color_entities": asset.get("step_color_entities", 0),
            "minimum_a0_a1_silhouette_iou": minimum,
            "a1_a2_byte_equal": identical_a1_a2,
        })
    RESULTS.mkdir(parents=True, exist_ok=True)
    for path, data in ((RESULTS / "asset_parity_by_view.csv", detail), (RESULTS / "asset_parity_summary.csv", cases)):
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(data[0]))
            writer.writeheader(); writer.writerows(data)
    print(json.dumps({"cases": len(cases), "passes": sum(row["status"] == "PASS" for row in cases), "min_silhouette_iou": min(row["minimum_a0_a1_silhouette_iou"] for row in cases)}, indent=2))
    return 0 if all(row["status"] == "PASS" for row in cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())

