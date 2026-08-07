"""Measure objective mesh approximation difficulty at fixed face budgets.

By default this script refuses to touch Final Holdout. Approximation errors are
validation targets, not inputs to the v3 geometry score.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
import trimesh


BUDGETS = (1000, 5000, 10000)


def load_mesh(path: Path):
    loaded = trimesh.load(path, force="scene", process=True)
    parts = list(loaded.geometry.values()) if isinstance(loaded, trimesh.Scene) else [loaded]
    meshes = [part for part in parts if isinstance(part, trimesh.Trimesh) and len(part.faces)]
    if not meshes:
        raise ValueError("no triangle geometry")
    mesh = trimesh.util.concatenate(meshes)
    mesh.process(validate=True)
    return mesh


def simplify(mesh, target_faces):
    if len(mesh.faces) <= target_faces or len(mesh.faces) < 100:
        return mesh.copy()
    return mesh.simplify_quadric_decimation(face_count=max(20, int(target_faces)), aggression=5)


def sample_surface(mesh, count, seed):
    # trimesh uses NumPy's legacy global generator for surface sampling.
    state = np.random.get_state()
    np.random.seed(seed)
    try:
        points, face_index = trimesh.sample.sample_surface(mesh, count)
    finally:
        np.random.set_state(state)
    normals = np.asarray(mesh.face_normals)[face_index]
    return points, normals


def mesh_error(original, reduced, seed, samples=512):
    diagonal = float(np.linalg.norm(np.ptp(original.vertices, axis=0)))
    if not np.isfinite(diagonal) or diagonal <= 0:
        raise ValueError("zero or invalid mesh scale")
    p0, n0 = sample_surface(original, samples, seed)
    p1, n1 = sample_surface(reduced, samples, seed + 1)
    tree0, tree1 = cKDTree(p0), cKDTree(p1)
    d01, i01 = tree1.query(p0, k=1)
    d10, i10 = tree0.query(p1, k=1)
    normal01 = 1 - np.abs(np.einsum("ij,ij->i", n0, n1[i01])).clip(0, 1)
    normal10 = 1 - np.abs(np.einsum("ij,ij->i", n1, n0[i10])).clip(0, 1)
    return {
        "normalized_chamfer": float((np.mean(d01) + np.mean(d10)) / (2 * diagonal)),
        "normalized_hausdorff": float(max(np.max(d01), np.max(d10)) / diagonal),
        "normal_error": float((np.mean(normal01) + np.mean(normal10)) / 2),
    }


def allocate_budget(meshes, budget):
    faces = np.array([len(mesh.faces) for mesh in meshes], dtype=float)
    if faces.sum() <= budget:
        return faces.astype(int)
    targets = np.maximum(20, np.floor(budget * faces / faces.sum())).astype(int)
    return np.minimum(targets, faces.astype(int))


def entity_at_budget(paths, budget, cache, entity_id):
    meshes, failures = [], []
    for path_text in paths:
        try:
            if path_text not in cache:
                cache[path_text] = load_mesh(Path(path_text))
            meshes.append((path_text, cache[path_text]))
        except Exception as exc:
            failures.append(f"{Path(path_text).name}: {type(exc).__name__}: {exc}")
    if not meshes:
        return {"approximation_ok": False, "failures": json.dumps(failures)}
    targets = allocate_budget([mesh for _, mesh in meshes], budget)
    areas = np.array([max(float(mesh.area), 0) for _, mesh in meshes])
    if not np.isfinite(areas).all() or areas.sum() <= 0:
        areas = np.ones(len(meshes))
    weights = areas / areas.sum()
    measurements, achieved_faces = [], 0
    for index, ((path_text, mesh), target) in enumerate(zip(meshes, targets)):
        try:
            reduced = simplify(mesh, int(target))
            if len(reduced.faces) == len(mesh.faces):
                # The fixed budget already contains the complete source mesh.
                # Avoid turning independent surface-sampling noise into error.
                measurements.append({"normalized_chamfer": 0.0,
                                     "normalized_hausdorff": 0.0,
                                     "normal_error": 0.0})
            else:
                seed_text = f"{entity_id}|{budget}|{path_text}|{index}".encode()
                seed = int(hashlib.sha256(seed_text).hexdigest()[:8], 16)
                measurements.append(mesh_error(mesh, reduced, seed))
            achieved_faces += len(reduced.faces)
        except Exception as exc:
            failures.append(f"{Path(path_text).name}: {type(exc).__name__}: {exc}")
            measurements.append({"normalized_chamfer": np.nan, "normalized_hausdorff": np.nan,
                                 "normal_error": np.nan})
    output = {
        "approximation_ok": bool(any(np.isfinite(x["normalized_chamfer"]) for x in measurements)),
        "original_faces": int(sum(len(mesh.faces) for _, mesh in meshes)),
        "target_faces": budget, "achieved_faces": int(achieved_faces),
        "mesh_count": len(meshes), "failure_count": len(failures),
        "failures": json.dumps(failures),
    }
    for field in ["normalized_chamfer", "normalized_hausdorff", "normal_error"]:
        values = np.array([item[field] for item in measurements], dtype=float)
        valid = np.isfinite(values)
        output[field] = float(np.average(values[valid], weights=weights[valid])) if valid.any() else np.nan
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entities", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--include-final-holdout", action="store_true")
    args = parser.parse_args()

    entities = pd.read_csv(args.entities)
    splits = pd.read_csv(args.split_manifest)[["entity_id", "v3_split"]]
    frame = entities.merge(splits, on="entity_id", how="inner", validate="one_to_one")
    allowed = ["development", "validation"]
    if args.include_final_holdout:
        allowed.append("final_holdout")
    frame = frame[frame.v3_split.isin(allowed)].copy()
    if not args.include_final_holdout and (frame.v3_split == "final_holdout").any():
        raise AssertionError("Final Holdout leakage")

    cache, rows = {}, []
    for number, row in enumerate(frame.itertuples(), start=1):
        paths = json.loads(row.resolved_visual_meshes)
        for budget in BUDGETS:
            metrics = entity_at_budget(paths, budget, cache, row.entity_id)
            rows.append({"entity_id": row.entity_id, "manufacturer": row.manufacturer,
                         "name": row.name, "v3_split": row.v3_split, "face_budget": budget, **metrics})
        if number % 10 == 0:
            print(f"processed {number}/{len(frame)} entities", flush=True)

    result = pd.DataFrame(rows)
    summary = {
        "splits_run": allowed, "final_holdout_touched": args.include_final_holdout,
        "n_entities": int(result.entity_id.nunique()), "n_rows": int(len(result)),
        "budgets": list(BUDGETS), "successful_rows": int(result.approximation_ok.sum()),
        "rows_with_failures": int((result.failure_count > 0).sum()),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output_dir / "fixed_budget_errors.csv", index=False, encoding="utf-8-sig")
    (args.output_dir / "fixed_budget_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
