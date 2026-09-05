"""Prepare matched gray/colored assemblies and evaluator masks for TrySet-5."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import trimesh


ROOT = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parents[1]
TRYSET = ROOT / "experiments" / "try3_freecad_full_workflow" / "tryset5_v1.csv"
OLD_SCRIPT_DIR = ROOT / "experiments" / "visual_evidence_input_ablation" / "scripts"
ARTIFACTS = EXP / "artifacts" / "controlled_assets"
RESULTS = EXP / "results"
FREECAD_PYTHON = Path(r"D:\software\freeCAD\install\bin\python.exe")
FREECAD_HELPER = Path(__file__).with_name("freecad_colored_step_job.py")

sys.path.insert(0, str(OLD_SCRIPT_DIR))
from run_colored_link_ablation import (  # noqa: E402
    PALETTE,
    RenderMesh,
    VIEWS,
    load_colored_meshes,
    render_view,
    write_csv,
    write_json,
)


GRAY = (166, 171, 176)


@dataclass(frozen=True)
class PreparedCase:
    case_id: str
    meshes: list[RenderMesh]
    manifest: dict[str, Any]


def mask_render_mesh(item: RenderMesh, index: int) -> RenderMesh:
    # Stable non-black ID colors. These masks are evaluator-only.
    color = ((37 * (index + 1)) % 251 + 1, (83 * (index + 1)) % 251 + 1, (149 * (index + 1)) % 251 + 1)
    return RenderMesh(item.link_id, item.source_link, item.mesh, color)


def export_link_meshes(case: PreparedCase, output: Path) -> list[dict[str, Any]]:
    output.mkdir(parents=True, exist_ok=True)
    by_link = {item.link_id: item for item in case.meshes}
    links = []
    for manifest_item in case.manifest["links"]:
        link_id = manifest_item["link_id"]
        if link_id not in by_link:
            continue
        path = output / f"{link_id}.stl"
        by_link[link_id].mesh.export(path)
        links.append({"link_id": link_id, "mesh_path": str(path), "color_rgb": manifest_item["color_rgb"]})
    return links


def prepare_case(row: dict[str, str], views: list[str], run_freecad: bool) -> dict[str, Any]:
    case_id = row["case_id"]
    case_root = ARTIFACTS / case_id
    if case_root.exists():
        shutil.rmtree(case_root)
    case_root.mkdir(parents=True, exist_ok=True)
    try:
        meshes, manifest = load_colored_meshes(row)
        case = PreparedCase(case_id, meshes, manifest)
        write_json(case_root / "colored_link_manifest.json", manifest)
        conditions = {
            "A0_controlled": [RenderMesh(x.link_id, x.source_link, x.mesh, GRAY) for x in meshes],
            "A1_color_only": meshes,
            "A2_color_legend": meshes,
        }
        for condition, condition_meshes in conditions.items():
            image_dir = case_root / condition / "renders"
            for view in views:
                render_view(condition_meshes, view, image_dir / f"{view}.png")
        mask_meshes = [mask_render_mesh(item, index) for index, item in enumerate(meshes)]
        for view in views:
            render_view(mask_meshes, view, case_root / "evaluator_masks" / f"{view}.png")

        # Export transformed per-link meshes once, then let FreeCAD create an
        # inspectable colored assembly and colored faceted STEP.
        link_jobs = export_link_meshes(case, case_root / "link_meshes")
        freecad_status = "SKIPPED"
        freecad_error = ""
        if run_freecad:
            job = {
                "case_id": case_id,
                "links": link_jobs,
                "fcstd_path": str(case_root / "colored_assembly.FCStd"),
                "step_path": str(case_root / "colored_assembly.step"),
                "result_path": str(case_root / "freecad_roundtrip.json"),
                "step_preview_path": str(case_root / "colored_step_reopen_preview.png"),
                "mesh_tolerance": 0.05,
            }
            job_path = case_root / "freecad_job.json"
            write_json(job_path, job)
            completed = subprocess.run(
                [str(FREECAD_PYTHON), str(FREECAD_HELPER), str(job_path)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            freecad_status = "SUCCESS" if completed.returncode == 0 else "FAILURE"
            freecad_error = (completed.stderr or completed.stdout)[-2000:]
            (case_root / "freecad_stdout.txt").write_text(completed.stdout or "", encoding="utf-8")
            (case_root / "freecad_stderr.txt").write_text(completed.stderr or "", encoding="utf-8")
        return {
            "case_id": case_id,
            "status": "SUCCESS",
            "expected_links": int(row["links"]),
            "visual_mesh_links": len(meshes),
            "views": len(views),
            "condition_images": len(conditions) * len(views),
            "freecad_status": freecad_status,
            "error_type": "",
            "error": freecad_error,
        }
    except Exception as exc:
        return {
            "case_id": case_id,
            "status": "FAILURE",
            "expected_links": int(row["links"]),
            "visual_mesh_links": 0,
            "views": len(views),
            "condition_images": 0,
            "freecad_status": "NOT_RUN",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case")
    parser.add_argument("--views", default=",".join(VIEWS))
    parser.add_argument("--skip-freecad", action="store_true")
    args = parser.parse_args()
    views = [item.strip() for item in args.views.split(",") if item.strip()]
    unknown = [item for item in views if item not in VIEWS]
    if unknown:
        raise SystemExit(f"unsupported views: {unknown}")
    rows = list(csv.DictReader(TRYSET.open("r", encoding="utf-8")))
    if args.case:
        rows = [row for row in rows if row["case_id"] == args.case]
    results = [prepare_case(row, views, not args.skip_freecad) for row in rows]
    RESULTS.mkdir(parents=True, exist_ok=True)
    write_csv(RESULTS / "asset_preparation_summary.csv", results)
    print(json.dumps({"cases": len(results), "successes": sum(row["status"] == "SUCCESS" for row in results), "freecad_successes": sum(row["freecad_status"] == "SUCCESS" for row in results)}, indent=2))
    return 0 if all(row["status"] == "SUCCESS" for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
