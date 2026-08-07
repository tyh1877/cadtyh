"""Test whether an invariant mesh-complexity score survives tessellation changes."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import trimesh
from scipy.stats import spearmanr


def load_mesh(path: Path):
    loaded = trimesh.load(path, force="scene", process=True)
    if isinstance(loaded, trimesh.Scene):
        parts = [g for g in loaded.geometry.values() if isinstance(g, trimesh.Trimesh)]
        if not parts:
            raise ValueError("no triangle geometry")
        mesh = trimesh.util.concatenate(parts)
    else:
        mesh = loaded
    mesh.process(validate=True)
    return mesh


def spectral_normal_entropy(mesh) -> float:
    normals = np.asarray(mesh.face_normals)
    areas = np.asarray(mesh.area_faces)
    good = np.isfinite(normals).all(axis=1) & np.isfinite(areas) & (areas > 0)
    normals, areas = normals[good], areas[good]
    if len(normals) < 3:
        return 0.0
    weights = areas / areas.sum()
    mean = np.average(normals, axis=0, weights=weights)
    centered = normals - mean
    cov = (centered * weights[:, None]).T @ centered
    eig = np.clip(np.linalg.eigvalsh(cov), 0, None)
    if eig.sum() <= 0:
        return 0.0
    p = eig[eig > 0] / eig.sum()
    return float(-(p * np.log(p)).sum() / np.log(3))


def curvature_entropy(angles) -> float:
    angles = angles[np.isfinite(angles)]
    if not len(angles):
        return 0.0
    hist, _ = np.histogram(angles, bins=np.linspace(0, np.pi, 19))
    p = hist[hist > 0] / hist.sum()
    return float(-(p * np.log(p)).sum() / np.log(18))


def measure(mesh) -> dict:
    angles = np.asarray(mesh.face_adjacency_angles)
    finite = angles[np.isfinite(angles)]
    return {
        "faces": int(len(mesh.faces)),
        "area": float(mesh.area),
        "normal_spectral_entropy": spectral_normal_entropy(mesh),
        "curvature_entropy": curvature_entropy(finite),
        "dihedral_q90_deg": float(np.degrees(np.quantile(finite, .9))) if len(finite) else 0.0,
        "sharp_rate_30deg": float(np.mean(finite > np.radians(30))) if len(finite) else 0.0,
    }


def simplified(mesh, ratio):
    if ratio >= .999 or len(mesh.faces) < 200:
        return mesh.copy()
    target = max(100, int(len(mesh.faces) * ratio))
    return mesh.simplify_quadric_decimation(face_count=target, aggression=5)


def aggregate(paths, ratio, mesh_cache, measure_cache):
    values, failures = [], []
    for path_text in paths:
        key = (path_text, ratio)
        try:
            if path_text not in mesh_cache:
                mesh_cache[path_text] = load_mesh(Path(path_text))
            if key not in measure_cache:
                measure_cache[key] = measure(simplified(mesh_cache[path_text], ratio))
            values.append(measure_cache[key])
        except Exception as exc:
            failures.append(f"{Path(path_text).name}: {type(exc).__name__}: {exc}")
    if not values:
        return {"feature_ok": False, "failures": json.dumps(failures)}
    area = np.array([max(v["area"], 0) for v in values])
    if area.sum() <= 0 or not np.isfinite(area).all():
        area = np.ones(len(values))
    area /= area.sum()
    out = {
        "feature_ok": True, "failures": json.dumps(failures),
        "n_meshes": len(values), "n_failed": len(failures),
        "faces": int(sum(v["faces"] for v in values)),
    }
    for field in ["normal_spectral_entropy", "curvature_entropy", "dihedral_q90_deg", "sharp_rate_30deg"]:
        out[field] = float(np.average([v[field] for v in values], weights=area))
    return out


def robust_parameters(frame, fields):
    params = {}
    for field in fields:
        values = frame[field]
        median = float(values.median())
        mad = float(np.median(np.abs(values - median)))
        scale = 1.4826 * mad if mad > 0 else float(values.std(ddof=0))
        params[field] = (median, scale if scale > 0 else 1.0)
    return params


def score(frame, params):
    values = []
    for field, (median, scale) in params.items():
        values.append(((frame[field] - median) / scale).clip(-3, 3))
    return pd.concat(values, axis=1).mean(axis=1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entities", type=Path, required=True)
    parser.add_argument("--audit-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    entities = pd.read_csv(args.entities)
    entities = entities[entities.eligible_entity & entities.feature_ok].copy()
    audit_ids = set(pd.read_csv(args.audit_manifest).entity_id)
    mesh_cache, measure_cache = {}, {}
    rows = []
    ratios = [1.0, .5, .25]
    for number, (_, entity) in enumerate(entities.iterrows(), start=1):
        paths = json.loads(entity.resolved_visual_meshes)
        for ratio in ratios:
            result = aggregate(paths, ratio, mesh_cache, measure_cache)
            rows.append({"entity_id": entity.entity_id, "manufacturer": entity.manufacturer,
                         "name": entity["name"], "source": entity.source,
                         "is_audit30": entity.entity_id in audit_ids, "ratio": ratio, **result})
        if number % 20 == 0:
            print(f"processed {number}/{len(entities)} entities", flush=True)
    long = pd.DataFrame(rows)
    fields = ["normal_spectral_entropy", "curvature_entropy", "dihedral_q90_deg", "sharp_rate_30deg"]
    original = long[(long.ratio == 1.0) & long.feature_ok].copy()
    params = robust_parameters(original, fields)
    long["complexity_score"] = score(long, params)
    original = long[(long.ratio == 1.0) & long.feature_ok].copy()
    wide = long.pivot(index="entity_id", columns="ratio", values=["complexity_score", "faces", "feature_ok"])
    valid = wide[(wide["feature_ok"] == True).all(axis=1)]  # noqa: E712
    rho50 = spearmanr(valid["complexity_score"][1.0].astype(float), valid["complexity_score"][.5].astype(float)).statistic
    rho25 = spearmanr(valid["complexity_score"][1.0].astype(float), valid["complexity_score"][.25].astype(float)).statistic
    triangle_rho = spearmanr(original.complexity_score, original.faces).statistic
    audit = long[(long.is_audit30) & (long.feature_ok)]
    audit_wide = audit.pivot(index="entity_id", columns="ratio", values="complexity_score").dropna()
    summary = {
        "n_entities": int(len(entities)), "n_complete_all_ratios": int(len(valid)),
        "rank_rho_original_vs_50pct": float(rho50),
        "rank_rho_original_vs_25pct": float(rho25),
        "triangle_count_rho_full_pool": float(triangle_rho),
        "audit30_rank_rho_original_vs_50pct": float(spearmanr(audit_wide[1.0].astype(float), audit_wide[.5].astype(float)).statistic),
        "audit30_rank_rho_original_vs_25pct": float(spearmanr(audit_wide[1.0].astype(float), audit_wide[.25].astype(float)).statistic),
        "passes_remesh_threshold_0_85": bool(min(rho50, rho25) >= .85),
        "passes_triangle_confound_threshold_abs_0_30": bool(abs(triangle_rho) < .30),
        "score_scaling": {k: {"median": v[0], "robust_scale": v[1]} for k, v in params.items()},
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    long.to_csv(args.output_dir / "remesh_features_long.csv", index=False, encoding="utf-8-sig")
    (args.output_dir / "remesh_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
