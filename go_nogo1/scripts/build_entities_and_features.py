"""Collapse URDF variants to robot entities and compute preliminary mesh features."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import trimesh


MANUAL_EXCLUSIONS = {
    ("Adept Mobile Robots", "Pioneer 3-AT"): "metadata type error: mobile base, not an arm",
    ("Adept Mobile Robots", "Pioneer 3-DX"): "metadata type error: mobile base, not an arm",
    ("Adept Mobile Robots", "Pioneer LX"): "metadata type error: mobile base/compound variant",
}


def stable_entity_id(manufacturer: str, name: str) -> str:
    raw = f"{manufacturer}|{name}".encode("utf-8")
    return "arm-" + hashlib.sha1(raw).hexdigest()[:10]


def choose_representative(group: pd.DataFrame) -> pd.Series:
    """Frozen deterministic preference; never uses geometric-complexity features."""
    work = group.copy()
    work["grade_rank"] = work.qc_grade.map({"A": 2, "B": 1, "C": 0}).fillna(0)
    work["original_rank"] = work.variant.fillna("original").eq("original").astype(int)
    work["native_rank"] = (~work.xacro_generated.astype(str).str.lower().eq("true")).astype(int)
    work = work.sort_values(
        ["grade_rank", "visual_mesh_resolution_rate", "nonfixed_visual_coverage",
         "original_rank", "native_rank", "source", "relative_path"],
        ascending=[False, False, False, False, False, True, True],
        kind="stable",
    )
    return work.iloc[0]


def load_as_mesh(path: Path):
    loaded = trimesh.load(path, force="scene", process=True)
    if isinstance(loaded, trimesh.Scene):
        meshes = [g for g in loaded.geometry.values() if isinstance(g, trimesh.Trimesh)]
        if not meshes:
            raise ValueError("scene has no triangle geometry")
        mesh = trimesh.util.concatenate(meshes)
        mesh.process(validate=True)
        return mesh
    if isinstance(loaded, trimesh.Trimesh):
        loaded.process(validate=True)
        return loaded
    raise ValueError(f"unsupported mesh object {type(loaded).__name__}")


def normal_entropy(mesh: trimesh.Trimesh) -> float:
    normals = np.asarray(mesh.face_normals)
    areas = np.asarray(mesh.area_faces)
    good = np.isfinite(normals).all(axis=1) & np.isfinite(areas) & (areas > 0)
    if not np.any(good):
        return math.nan
    normals, areas = normals[good], areas[good]
    azimuth = (np.arctan2(normals[:, 1], normals[:, 0]) + np.pi) / (2 * np.pi)
    elevation = (normals[:, 2] + 1) / 2
    bins = np.zeros((12, 6), dtype=float)
    ai = np.minimum((azimuth * 12).astype(int), 11)
    ei = np.minimum((elevation * 6).astype(int), 5)
    np.add.at(bins, (ai, ei), areas)
    p = bins.ravel()
    p = p[p > 0] / p.sum()
    return float(-(p * np.log(p)).sum() / np.log(72))


def measure_mesh(path: Path) -> dict:
    mesh = load_as_mesh(path)
    faces = len(mesh.faces)
    vertices = len(mesh.vertices)
    angles = np.asarray(mesh.face_adjacency_angles)
    finite_angles = angles[np.isfinite(angles)]
    area = float(mesh.area) if np.isfinite(mesh.area) else math.nan
    bounds = np.asarray(mesh.bounds)
    diagonal = float(np.linalg.norm(bounds[1] - bounds[0])) if bounds.shape == (2, 3) else math.nan
    return {
        "mesh_faces": faces,
        "mesh_vertices": vertices,
        "mesh_area": area,
        "mesh_bbox_diagonal": diagonal,
        "mesh_watertight": bool(mesh.is_watertight),
        "mesh_body_count": int(mesh.body_count),
        "normal_entropy": normal_entropy(mesh),
        "dihedral_q90_deg": float(np.degrees(np.quantile(finite_angles, .9))) if finite_angles.size else 0.0,
        "sharp_edge_rate_15deg": float(np.mean(finite_angles > np.radians(15))) if finite_angles.size else 0.0,
        "sharp_edge_rate_30deg": float(np.mean(finite_angles > np.radians(30))) if finite_angles.size else 0.0,
    }


def aggregate_entity(paths, cache):
    measurements, errors = [], []
    for value in paths:
        path = Path(value)
        key = str(path)
        if key not in cache:
            try:
                cache[key] = measure_mesh(path)
            except Exception as exc:  # retained as auditable per-file evidence
                cache[key] = {"error": f"{type(exc).__name__}: {exc}"}
        if "error" in cache[key]:
            errors.append(f"{path.name}: {cache[key]['error']}")
        else:
            measurements.append(cache[key])
    if not measurements:
        return {"loaded_meshes": 0, "mesh_load_errors": json.dumps(errors), "feature_ok": False}
    weights = np.array([max(0.0, m["mesh_area"]) for m in measurements], dtype=float)
    if not np.isfinite(weights).all() or weights.sum() <= 0:
        weights = np.ones(len(measurements))
    weights /= weights.sum()
    result = {
        "loaded_meshes": len(measurements), "failed_meshes": len(errors),
        "mesh_load_errors": json.dumps(errors), "feature_ok": True,
        "total_faces": int(sum(m["mesh_faces"] for m in measurements)),
        "total_vertices": int(sum(m["mesh_vertices"] for m in measurements)),
        "total_surface_area": float(sum(m["mesh_area"] for m in measurements)),
        "watertight_mesh_fraction": float(np.mean([m["mesh_watertight"] for m in measurements])),
        "total_mesh_bodies": int(sum(m["mesh_body_count"] for m in measurements)),
    }
    for field in ["normal_entropy", "dihedral_q90_deg", "sharp_edge_rate_15deg", "sharp_edge_rate_30deg"]:
        result[field] = float(np.average([m[field] for m in measurements], weights=weights))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    df = pd.read_csv(args.inventory)
    arms = df[df.type.eq("robotic arm")].copy()
    records = []
    for (manufacturer, name), group in arms.groupby(["manufacturer", "name"], sort=True):
        representative = choose_representative(group).copy()
        excluded_reason = MANUAL_EXCLUSIONS.get((manufacturer, name), "")
        representative["entity_id"] = stable_entity_id(manufacturer, name)
        representative["n_available_records"] = len(group)
        representative["available_sources"] = json.dumps(sorted(group.source.unique().tolist()))
        representative["eligible_entity"] = representative.qc_grade in {"A", "B"} and not excluded_reason
        representative["manual_exclusion_reason"] = excluded_reason
        records.append(representative)
    entities = pd.DataFrame(records)
    cache = {}
    feature_rows = []
    for _, row in entities.iterrows():
        paths = json.loads(row.resolved_visual_meshes) if isinstance(row.resolved_visual_meshes, str) else []
        features = aggregate_entity(paths, cache) if row.eligible_entity else {"feature_ok": False}
        features["entity_id"] = row.entity_id
        feature_rows.append(features)
    features = pd.DataFrame(feature_rows)
    result = entities.merge(features, on="entity_id", how="left")
    eligible = result.eligible_entity & result.feature_ok.fillna(False)
    # Preliminary stratification score only; it is not the final validity-tested metric.
    # Disconnected-body count is retained as QC only: triangle-soup exporters can
    # inflate it without changing shape. It must not influence sampling strata.
    components = ["normal_entropy", "sharp_edge_rate_15deg", "dihedral_q90_deg"]
    z = []
    for field in components:
        values = result.loc[eligible, field].astype(float)
        median = values.median()
        mad = np.median(np.abs(values - median))
        scale = 1.4826 * mad if mad > 0 else values.std(ddof=0)
        z.append(((result[field].astype(float) - median) / (scale if scale > 0 else 1)).clip(-3, 3))
    result["preliminary_complexity_score"] = pd.concat(z, axis=1).mean(axis=1)
    result["complexity_stratum"] = "ineligible"
    result.loc[eligible, "complexity_stratum"] = pd.qcut(
        result.loc[eligible, "preliminary_complexity_score"], 3,
        labels=["low", "medium", "high"], duplicates="drop"
    ).astype(str)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False, encoding="utf-8-sig")
    pd.DataFrame([{"mesh_path": k, **v} for k, v in cache.items()]).to_csv(
        args.output.with_name("mesh_file_features.csv"), index=False, encoding="utf-8-sig"
    )
    summary = {
        "robotic_arm_urdf_records": int(len(arms)),
        "distinct_name_manufacturer_entities": int(len(result)),
        "eligible_entities": int(eligible.sum()),
        "feature_failures": int((result.eligible_entity & ~result.feature_ok.fillna(False)).sum()),
        "selected_source_distribution": result.loc[eligible, "source"].value_counts().to_dict(),
        "manufacturer_count": int(result.loc[eligible, "manufacturer"].nunique()),
        "strata": result.loc[eligible, "complexity_stratum"].value_counts().to_dict(),
    }
    args.output.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
