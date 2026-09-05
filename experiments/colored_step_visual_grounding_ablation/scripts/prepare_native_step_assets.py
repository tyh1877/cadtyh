"""Orchestrate native STEP coloring and matched FreeCAD rendering."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parents[1]
MANIFEST = EXP / "native_step5_v1.csv"
ARTIFACTS = EXP / "artifacts" / "native_step5"
RESULTS = EXP / "results"
FREECAD_PYTHON = Path(r"D:\software\freeCAD\install\bin\python.exe")
HELPER = Path(__file__).with_name("freecad_native_step_assets.py")
VIEWS = ["front", "rear", "left", "right", "top", "isometric"]


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run_case(row: dict[str, str]) -> dict:
    output = ARTIFACTS / row["case_id"]
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    job = {
        "case_id": row["case_id"],
        "step_path": str((ROOT / row["step_path"]).resolve()),
        "expected_solids": int(row["expected_solids"]),
        "views": VIEWS,
        "output_dir": str(output),
        "result_path": str(output / "asset_result.json"),
    }
    job_path = output / "asset_job.json"
    write_json(job_path, job)
    try:
        completed = subprocess.run(
            [str(FREECAD_PYTHON), str(HELPER), str(job_path)],
            cwd=str(ROOT), capture_output=True, text=True, timeout=900, check=False,
        )
        (output / "freecad_stdout.txt").write_text(completed.stdout or "", encoding="utf-8")
        (output / "freecad_stderr.txt").write_text(completed.stderr or "", encoding="utf-8")
        payload = json.loads((output / "asset_result.json").read_text(encoding="utf-8")) if (output / "asset_result.json").exists() else {}
        return {
            "case_id": row["case_id"], "dataset_name": row["dataset_name"],
            "status": payload.get("status", "FAILURE"),
            "leaf_components": payload.get("leaf_components", 0),
            "source_solids": payload.get("source_solids", 0),
            "expected_solids": int(row["expected_solids"]),
            "reopened_leaf_components": payload.get("reopened_leaf_components", 0),
            "reopened_solids": payload.get("reopened_solids", 0),
            "step_color_entities": payload.get("step_color_entities", 0),
            "views_per_condition": payload.get("views", 0),
            "returncode": completed.returncode,
            "error_type": payload.get("error_type", "MISSING_RESULT"),
            "error": payload.get("error", "")[-500:],
        }
    except Exception as exc:
        return {
            "case_id": row["case_id"], "dataset_name": row["dataset_name"],
            "status": "FAILURE", "leaf_components": 0, "source_solids": 0,
            "expected_solids": int(row["expected_solids"]),
            "reopened_leaf_components": 0, "reopened_solids": 0,
            "step_color_entities": 0, "views_per_condition": 0,
            "returncode": -1, "error_type": type(exc).__name__, "error": str(exc),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case")
    args = parser.parse_args()
    rows = list(csv.DictReader(MANIFEST.open("r", encoding="utf-8")))
    if args.case:
        rows = [row for row in rows if row["case_id"] == args.case]
    results = [run_case(row) for row in rows]
    write_csv(RESULTS / "native_step_asset_summary.csv", results)
    print(json.dumps({"cases": len(results), "successes": sum(row["status"] == "SUCCESS" for row in results)}, indent=2))
    return 0 if all(row["status"] == "SUCCESS" for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

