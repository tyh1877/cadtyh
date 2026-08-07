"""Hierarchically equal-weighted Go/No-Go 1 development metric.

This is a post-failure development metric. It must not be presented as an
independent confirmation on Audit-30; a fresh holdout is required for that claim.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr


GEOMETRY_FEATURES = {
    "orientation": ["normal_spectral_entropy"],
    "curvature": ["curvature_entropy", "dihedral_q90_deg", "sharp_rate_30deg"],
}
ASSEMBLY_FEATURES = ["n_links_with_mesh_visual", "n_visual_mesh_refs", "loaded_meshes"]
KINEMATIC_FEATURES = ["n_actuated_joints", "max_chain_depth", "n_joints"]


def percentile(values):
    values = pd.Series(values, dtype=float)
    good = values.notna()
    output = pd.Series(np.nan, index=values.index, dtype=float)
    if good.sum() == 1:
        output.loc[good] = .5
    elif good.sum() > 1:
        output.loc[good] = (rankdata(values[good], method="average") - 1) / (good.sum() - 1)
    return output


def reference_percentile(value, reference):
    ref = np.sort(pd.Series(reference, dtype=float).dropna().to_numpy())
    if not len(ref):
        return np.nan
    return float((np.searchsorted(ref, value, side="right") - .5) / len(ref))


def add_geometry_scores(frame):
    module_columns = []
    for module, fields in GEOMETRY_FEATURES.items():
        normalized = []
        for field in fields:
            column = f"p_{field}"
            frame[column] = percentile(frame[field])
            normalized.append(column)
        module_column = f"module_{module}"
        frame[module_column] = frame[normalized].mean(axis=1)
        module_columns.append(module_column)
    frame["geometry_complexity_v2"] = frame[module_columns].mean(axis=1)
    return frame


def add_entity_scores(entities):
    for field in ASSEMBLY_FEATURES + KINEMATIC_FEATURES:
        entities[f"p_{field}"] = percentile(entities[field])
    entities["assembly_complexity_v2"] = entities[[f"p_{x}" for x in ASSEMBLY_FEATURES]].mean(axis=1)
    entities["kinematic_complexity_v2"] = entities[[f"p_{x}" for x in KINEMATIC_FEATURES]].mean(axis=1)
    return entities


def brep_equal_score(frame):
    frame = frame.copy()
    frame["p_log_faces"] = percentile(np.log1p(frame.n_faces))
    frame["p_edge_face_ratio"] = percentile(frame.edge_face_ratio)
    frame["p_nonplanar"] = percentile(frame.nonplanar_area_fraction)
    frame["p_freeform"] = percentile(frame.freeform_area_fraction)
    frame["brep_topology_module_v2"] = frame[["p_log_faces", "p_edge_face_ratio"]].mean(axis=1)
    frame["brep_surface_module_v2"] = frame[["p_nonplanar", "p_freeform"]].mean(axis=1)
    frame["brep_complexity_v2"] = frame[["brep_topology_module_v2", "brep_surface_module_v2"]].mean(axis=1)
    return frame


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entities", type=Path, required=True)
    parser.add_argument("--remesh-features", type=Path, required=True)
    parser.add_argument("--brep-pairs", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    long = pd.read_csv(args.remesh_features)
    long = long[long.feature_ok].copy()
    scored_ratios = []
    for ratio, group in long.groupby("ratio", sort=True):
        scored_ratios.append(add_geometry_scores(group.copy()))
    scored = pd.concat(scored_ratios, ignore_index=True)
    multiscale = scored.groupby("entity_id", as_index=False).agg(
        geometry_complexity_v2=("geometry_complexity_v2", "mean"),
        orientation_module_v2=("module_orientation", "mean"),
        curvature_module_v2=("module_curvature", "mean"),
    )

    entities = pd.read_csv(args.entities)
    entities = entities[entities.eligible_entity & entities.feature_ok].copy()
    entities = add_entity_scores(entities)
    result = entities.merge(multiscale, on="entity_id", how="left", validate="one_to_one")
    result["overall_complexity_v2"] = result[[
        "geometry_complexity_v2", "assembly_complexity_v2", "kinematic_complexity_v2"
    ]].mean(axis=1)

    wide = scored.pivot(index="entity_id", columns="ratio", values="geometry_complexity_v2").dropna()
    rho50 = spearmanr(wide[1.0], wide[.5]).statistic
    rho25 = spearmanr(wide[1.0], wide[.25]).statistic
    original = scored[scored.ratio == 1.0][["entity_id", "faces", "geometry_complexity_v2"]]
    triangle_rho = spearmanr(original.faces, original.geometry_complexity_v2).statistic

    pairs = brep_equal_score(pd.read_csv(args.brep_pairs))
    pairs = pairs.merge(result[["entity_id", "geometry_complexity_v2"]], on="entity_id", how="left")
    independent = pairs.dropna(subset=["brep_complexity_v2", "geometry_complexity_v2"])
    independent_rho = spearmanr(independent.brep_complexity_v2, independent.geometry_complexity_v2).statistic

    reference = scored[scored.ratio == 1.0]
    stepmesh_modules = []
    for _, row in pairs.iterrows():
        orientation = reference_percentile(row.stepmesh_normal_spectral_entropy,
                                           reference.normal_spectral_entropy)
        curvature_parts = [
            reference_percentile(row[f"stepmesh_{field}"], reference[field])
            for field in GEOMETRY_FEATURES["curvature"]
        ]
        stepmesh_modules.append((orientation + float(np.mean(curvature_parts))) / 2)
    pairs["same_geometry_mesh_v2"] = stepmesh_modules
    same = pairs.dropna(subset=["brep_complexity_v2", "same_geometry_mesh_v2"])
    same_rho = spearmanr(same.brep_complexity_v2, same.same_geometry_mesh_v2).statistic

    summary = {
        "status": "development_only_post_failure_revision",
        "n_entities": int(len(result)),
        "normalization": "within-ratio percentile ranks in [0,1]",
        "weighting": "equal within modules; equal across modules",
        "geometry_modules": GEOMETRY_FEATURES,
        "remesh_rho_original_vs_50pct": float(rho50),
        "remesh_rho_original_vs_25pct": float(rho25),
        "triangle_count_rho": float(triangle_rho),
        "independent_mesh_brep_n": int(len(independent)),
        "independent_mesh_brep_rho": float(independent_rho),
        "same_geometry_mesh_brep_n": int(len(same)),
        "same_geometry_mesh_brep_rho": float(same_rho),
        "checks": {
            "remesh": bool(min(rho50, rho25) >= .85),
            "triangle_confound": bool(abs(triangle_rho) < .30),
            "independent_brep": bool(independent_rho >= .50),
            "same_geometry_brep": bool(same_rho >= .50),
        },
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output_dir / "entity_scores_v2.csv", index=False, encoding="utf-8-sig")
    scored.to_csv(args.output_dir / "ratio_scores_v2.csv", index=False, encoding="utf-8-sig")
    pairs.to_csv(args.output_dir / "brep_pairs_v2.csv", index=False, encoding="utf-8-sig")
    (args.output_dir / "summary_v2.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
