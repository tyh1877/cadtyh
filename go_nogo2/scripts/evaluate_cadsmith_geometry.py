"""Deterministically score CADSmith-Qwen's native single-part geometry output.

It intentionally does not synthesize an articulated representation.  The
reference is the canonical-pose union of all GT link meshes; results are only
geometry and CAD-validity evidence, never assembly or kinematic scores.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh

from evaluate_prediction import (
    SAMPLE_COUNT, VOXEL_PITCH, deterministic_surface_points, load_robot,
    point_metrics, voxel_iou,
)


def as_mesh(path: Path) -> trimesh.Trimesh:
    loaded = trimesh.load(path, force="mesh")
    if isinstance(loaded, trimesh.Scene):
        loaded = trimesh.util.concatenate(tuple(loaded.geometry.values()))
    if not isinstance(loaded, trimesh.Trimesh) or len(loaded.vertices) == 0 or len(loaded.faces) == 0:
        raise ValueError("CADSmith STL is empty or not a triangle mesh")
    return loaded


def normalize(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    copy = mesh.copy()
    diagonal = float(np.linalg.norm(np.ptp(copy.vertices, axis=0)))
    if not np.isfinite(diagonal) or diagonal <= 0:
        raise ValueError("invalid mesh scale")
    copy.vertices = (copy.vertices - copy.bounds.mean(axis=0)) / diagonal
    return copy


def evaluate(gt_mesh: trimesh.Trimesh, prediction: trimesh.Trimesh, seed: int) -> dict:
    gt, pred = normalize(gt_mesh), normalize(prediction)
    gt_points = deterministic_surface_points(gt, SAMPLE_COUNT, seed)
    pred_points = deterministic_surface_points(pred, SAMPLE_COUNT, seed)
    transform, transformed, _ = trimesh.registration.icp(pred_points, gt_points, max_iterations=50, reflection=False, scale=False)
    pred.apply_transform(transform)
    return {
        "geometry": {**point_metrics(gt_points, np.asarray(transformed)), "voxel_iou": voxel_iou(gt, pred)},
        "cad_validity": {"stl_loaded": True, "watertight": bool(prediction.is_watertight),
                         "vertices": int(len(prediction.vertices)), "faces": int(len(prediction.faces))},
        "unsupported": ["assembly", "kinematics", "motion", "multi_pose", "self_collision"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260808)
    args = parser.parse_args()
    manifest = json.loads((args.run_dir / "cadsmith_manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != "SUCCESS" or not manifest.get("stl"):
        result = {"status": manifest["status"], "geometry": None, "cad_validity": {"stl_loaded": False},
                  "unsupported": ["assembly", "kinematics", "motion", "multi_pose", "self_collision"]}
    else:
        gt = load_robot(args.case_dir / "urdf" / "model.urdf")
        result = {"status": "SUCCESS", **evaluate(gt.combined, as_mesh(Path(manifest["stl"])), args.seed)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
