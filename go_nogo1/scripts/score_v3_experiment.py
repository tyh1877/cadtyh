"""Score Go/No-Go 1 v3 without reading the frozen Final Holdout.

The geometry score uses equal-weight modules. Fixed-budget approximation error
is an external validation target and never enters the geometry score.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr


RATIOS = (1.0, 0.5, 0.25)
CURVATURE = ("curvature_entropy", "dihedral_q90_deg", "sharp_rate_30deg")
ERRORS = ("normalized_chamfer", "normalized_hausdorff", "normal_error")


def percentile_from_development(development: pd.Series, values: pd.Series) -> np.ndarray:
    """Empirical CDF using only the development reference distribution."""
    reference = np.sort(development.dropna().to_numpy(dtype=float))
    if len(reference) == 0:
        return np.full(len(values), np.nan)
    raw = values.to_numpy(dtype=float)
    return np.searchsorted(reference, raw, side="right") / len(reference)


def correlation(x, y):
    valid = np.isfinite(x) & np.isfinite(y)
    if valid.sum() < 3:
        return {"rho": None, "n": int(valid.sum())}
    return {"rho": float(spearmanr(np.asarray(x)[valid], np.asarray(y)[valid]).statistic),
            "n": int(valid.sum())}


def normalized_features(long: pd.DataFrame) -> pd.DataFrame:
    output = long.copy()
    features = ("normal_spectral_entropy",) + CURVATURE
    for ratio in RATIOS:
        mask = output.ratio.eq(ratio)
        dev = mask & output.v3_split.eq("development")
        for feature in features:
            output.loc[mask, f"p_{feature}"] = percentile_from_development(
                output.loc[dev, feature], output.loc[mask, feature]
            )
    return output


def geometry_scores(long: pd.DataFrame) -> pd.DataFrame:
    indexed = long.set_index(["entity_id", "ratio"])
    ids = sorted(long.entity_id.unique())
    records = []
    for entity_id in ids:
        block = indexed.loc[entity_id]
        record = {"entity_id": entity_id, "v3_split": block.v3_split.iloc[0],
                  "manufacturer": block.manufacturer.iloc[0], "name": block.name.iloc[0]}
        record["orientation_module"] = float(block["p_normal_spectral_entropy"].mean())
        original = block.loc[1.0]
        record["local_curvature_module"] = float(np.mean(
            [original[f"p_{feature}"] for feature in CURVATURE]))
        record["persistence_module"] = float(np.mean(
            [block[f"p_{feature}"].min() for feature in CURVATURE]))
        modules = [record["orientation_module"], record["local_curvature_module"],
                   record["persistence_module"]]
        record["geometry_score_v3"] = float(np.mean(modules))
        for omitted, column in enumerate(("orientation", "local_curvature", "persistence")):
            record[f"score_without_{column}"] = float(np.mean(
                [value for index, value in enumerate(modules) if index != omitted]))
        for ratio in RATIOS:
            row = block.loc[ratio]
            record[f"single_scale_score_{ratio:g}"] = float(np.mean(
                [row["p_normal_spectral_entropy"]] + [row[f"p_{x}"] for x in CURVATURE]))
            record[f"faces_{ratio:g}"] = float(row.faces)
        records.append(record)
    return pd.DataFrame(records)


def approximation_scores(errors: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = errors.copy()
    for budget in sorted(frame.face_budget.unique()):
        mask = frame.face_budget.eq(budget)
        dev = mask & frame.v3_split.eq("development")
        for metric in ERRORS:
            frame.loc[mask, f"p_{metric}"] = percentile_from_development(
                frame.loc[dev, metric], frame.loc[mask, metric]
            )
    frame["budget_difficulty"] = frame[[f"p_{x}" for x in ERRORS]].mean(axis=1)
    wide = frame.pivot(index="entity_id", columns="face_budget", values="budget_difficulty")
    scores = wide.mean(axis=1).rename("approximation_difficulty").reset_index()
    for budget in wide.columns:
        scores[f"difficulty_{int(budget)}"] = scores.entity_id.map(wide[budget])
    return scores, frame


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--remesh-features", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--fixed-budget-errors", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    split = pd.read_csv(args.split_manifest)[["entity_id", "v3_split"]]
    if set(split.v3_split) != {"development", "validation", "final_holdout"}:
        raise ValueError("unexpected split labels")
    allowed = split[split.v3_split.isin(["development", "validation"])]
    long = pd.read_csv(args.remesh_features).merge(allowed, on="entity_id", validate="many_to_one")
    errors = pd.read_csv(args.fixed_budget_errors)
    if "final_holdout" in set(long.v3_split) or "final_holdout" in set(errors.v3_split):
        raise AssertionError("Final Holdout leakage")
    if set(np.round(long.ratio.unique(), 2)) != set(RATIOS):
        raise ValueError("missing remesh ratio")

    long = normalized_features(long)
    geometry = geometry_scores(long)
    difficulty, normalized_errors = approximation_scores(errors)
    scores = geometry.merge(difficulty, on="entity_id", validate="one_to_one")
    validation = scores[scores.v3_split.eq("validation")]
    development = scores[scores.v3_split.eq("development")]

    primary = correlation(validation.geometry_score_v3.to_numpy(),
                          validation.approximation_difficulty.to_numpy())
    robustness = {
        "original_vs_50": correlation(validation["single_scale_score_1"].to_numpy(),
                                        validation["single_scale_score_0.5"].to_numpy()),
        "original_vs_25": correlation(validation["single_scale_score_1"].to_numpy(),
                                        validation["single_scale_score_0.25"].to_numpy()),
    }
    confound = correlation(validation.geometry_score_v3.to_numpy(),
                           validation["faces_1"].to_numpy())
    sensitivity = {
        name: correlation(validation.geometry_score_v3.to_numpy(), validation[name].to_numpy())
        for name in ("score_without_orientation", "score_without_local_curvature",
                     "score_without_persistence")
    }
    by_budget = {
        str(budget): correlation(validation.geometry_score_v3.to_numpy(),
                                 validation[f"difficulty_{budget}"].to_numpy())
        for budget in sorted(errors.face_budget.unique())
    }
    dev_primary = correlation(development.geometry_score_v3.to_numpy(),
                              development.approximation_difficulty.to_numpy())

    criteria = {
        "validation_objective_rho_gte_0.60": primary["rho"] is not None and primary["rho"] >= 0.60,
        "remesh_rho_gte_0.85": all(x["rho"] is not None and x["rho"] >= 0.85
                                      for x in robustness.values()),
        "triangle_confound_abs_rho_lt_0.30": confound["rho"] is not None and abs(confound["rho"]) < 0.30,
        "leave_one_module_out_rho_gte_0.80": all(x["rho"] is not None and x["rho"] >= 0.80
                                               for x in sensitivity.values()),
        "all_budget_directions_positive": all(x["rho"] is not None and x["rho"] > 0
                                                 for x in by_budget.values()),
    }
    summary = {
        "formula": "equal mean(orientation, local curvature, multiscale persistence)",
        "validation_target": "equal mean of percentile-normalized Chamfer, Hausdorff, and normal error at 1k/5k/10k nominal face budgets",
        "final_holdout_touched": False,
        "development_n": int(len(development)), "validation_n": int(len(validation)),
        "development_primary_diagnostic": dev_primary,
        "validation_primary": primary, "validation_by_budget": by_budget,
        "validation_remesh_stability": robustness, "validation_triangle_confound": confound,
        "validation_leave_one_module_out": sensitivity, "criteria": criteria,
        "decision": "GO" if all(criteria.values()) else "NO-GO",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    scores.to_csv(args.output_dir / "v3_scores.csv", index=False, encoding="utf-8-sig")
    normalized_errors.to_csv(args.output_dir / "fixed_budget_errors_normalized.csv", index=False,
                             encoding="utf-8-sig")
    (args.output_dir / "v3_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
