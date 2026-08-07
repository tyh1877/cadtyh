"""Analyze independent blinded expert ratings and issue the final Go/No-Go result."""

from __future__ import annotations

import argparse
import json
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


def weighted_kappa(a, b, levels=5):
    matrix = np.zeros((levels, levels), dtype=float)
    for x, y in zip(a.astype(int), b.astype(int)):
        matrix[x - 1, y - 1] += 1
    observed = matrix / matrix.sum()
    expected = np.outer(matrix.sum(axis=1), matrix.sum(axis=0)) / matrix.sum() ** 2
    i, j = np.indices((levels, levels))
    weights = ((i - j) / (levels - 1)) ** 2
    denominator = (weights * expected).sum()
    return 1 - (weights * observed).sum() / denominator if denominator else np.nan


def icc_2k(values):
    """Two-way random-effects, absolute-agreement ICC for mean of k raters."""
    x = np.asarray(values, dtype=float)
    n, k = x.shape
    grand = x.mean(); row_mean = x.mean(axis=1); col_mean = x.mean(axis=0)
    ms_rows = k * ((row_mean - grand) ** 2).sum() / (n - 1)
    ms_cols = n * ((col_mean - grand) ** 2).sum() / (k - 1)
    residual = x - row_mean[:, None] - col_mean[None, :] + grand
    ms_error = (residual ** 2).sum() / ((n - 1) * (k - 1))
    return (ms_rows - ms_error) / (ms_rows + (ms_cols - ms_error) / n)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ratings-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mesh-features", type=Path, required=True)
    parser.add_argument("--robustness-summary", type=Path, required=True)
    parser.add_argument("--brep-summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    files = sorted(args.ratings_dir.glob("expert_rating_*.csv"))
    files = [x for x in files if x.name != "expert_rating_blank.csv"]
    if len(files) < 2:
        raise SystemExit("Need at least two completed expert_rating_*.csv files.")
    manifest = pd.read_csv(args.manifest)
    combined = manifest[["blind_id", "entity_id", "manufacturer", "name"]].copy()
    rating_columns = []
    for number, path in enumerate(files, start=1):
        rating = pd.read_csv(path)
        column = f"rater_{number}"
        rating[column] = pd.to_numeric(rating["geometric_complexity_1_to_5"], errors="coerce")
        unusable = rating.get("unusable_or_incomplete", pd.Series(False, index=rating.index)).astype(str).str.lower().isin({"yes", "true", "1"})
        rating.loc[unusable, column] = np.nan
        if rating.blind_id.duplicated().any():
            raise ValueError(f"Duplicate blind_id in {path.name}")
        combined = combined.merge(rating[["blind_id", column]], on="blind_id", how="left", validate="one_to_one")
        rating_columns.append(column)
    complete = combined.dropna(subset=rating_columns).copy()
    if len(complete) < 24:
        raise SystemExit(f"Only {len(complete)} fully rated usable robots; at least 24 required.")
    kappas = [weighted_kappa(complete[a], complete[b]) for a, b in combinations(rating_columns, 2)]
    icc = icc_2k(complete[rating_columns].values)
    complete["expert_median"] = complete[rating_columns].median(axis=1)
    mesh = pd.read_csv(args.mesh_features)
    mesh = mesh[(mesh.ratio == 1.0) & mesh.feature_ok][["entity_id", "complexity_score"]]
    complete = complete.merge(mesh, on="entity_id", how="left", validate="one_to_one")
    rho = spearmanr(complete.expert_median, complete.complexity_score).statistic
    high = complete[complete.expert_median >= 4]
    robustness = json.loads(args.robustness_summary.read_text(encoding="utf-8"))
    brep = json.loads(args.brep_summary.read_text(encoding="utf-8"))
    checks = {
        "valid_n": len(complete) >= 24,
        "high_complexity_diversity": len(high) >= 8 and high.manufacturer.nunique() >= 4,
        "expert_agreement": np.nanmean(kappas) >= .65 or icc >= .75,
        "mesh_human_validity": rho >= .60,
        "remesh_robustness": robustness["passes_remesh_threshold_0_85"],
        "triangle_count_confound": robustness["passes_triangle_confound_threshold_abs_0_30"],
        "mesh_brep_validity": brep["passes_threshold_0_50"],
    }
    decision = "FULL GO" if all(checks.values()) else "NO-GO / REVISE METRIC"
    summary = {
        "decision": decision, "n_raters": len(files), "n_complete_usable": len(complete),
        "mean_pairwise_quadratic_weighted_kappa": float(np.nanmean(kappas)),
        "icc_2k_absolute_agreement": float(icc), "mesh_human_spearman_rho": float(rho),
        "expert_high_complexity_n": len(high), "expert_high_complexity_manufacturers": high.manufacturer.nunique(),
        "checks": checks,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    complete.to_csv(args.output_dir / "expert_mesh_scored.csv", index=False, encoding="utf-8-sig")
    (args.output_dir / "final_decision.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
