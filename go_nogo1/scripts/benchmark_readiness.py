"""Audit whether a complexity-blind, technically valid Benchmark-80 exists."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


TARGET_SIZE = 80
MIN_MANUFACTURERS = 10
MAX_MANUFACTURER_SHARE = 0.25
MAX_SOURCE_SHARE = 0.50
SEED = 20260807


def eligible(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply only provenance, geometry, and kinematic readiness conditions."""
    required_text = frame.source_link.notna() & frame.urdf_path.notna()
    mask = (
        frame.eligible_entity.fillna(False)
        & frame.parse_ok.fillna(False)
        & frame.graph_valid.fillna(False)
        & frame.feature_ok.fillna(False)
        & (frame.visual_mesh_resolution_rate >= 0.90)
        & (frame.nonfixed_visual_coverage >= 0.80)
        & (frame.n_actuated_joints >= 1)
        & frame.max_chain_depth.notna()
        & (frame.loaded_meshes >= 1)
        & (frame.total_faces > 0)
        & required_text
    )
    return frame.loc[mask].copy()


def candidate_score(sample: pd.DataFrame) -> tuple:
    """Prefer broad, even provenance without reading any complexity field."""
    manufacturer_counts = sample.manufacturer.value_counts()
    source_counts = sample.source.value_counts()
    return (
        sample.manufacturer.nunique(),
        sample.source.nunique(),
        -int(manufacturer_counts.max()),
        -int(source_counts.max()),
        -float((manufacturer_counts / len(sample)).pow(2).sum()),
    )


def select_candidate(pool: pd.DataFrame, trials: int) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    manufacturer_cap = int(TARGET_SIZE * MAX_MANUFACTURER_SHARE)
    source_cap = int(TARGET_SIZE * MAX_SOURCE_SHARE)
    best, best_score = None, None

    # Draw under explicit caps. No geometric, complexity, or method-performance
    # column is consulted by the selection procedure.
    records = pool[["entity_id", "manufacturer", "name", "source", "source_link",
                    "urdf_path", "n_links", "n_joints", "n_actuated_joints",
                    "max_chain_depth", "loaded_meshes", "total_faces"]].copy()
    for _ in range(trials):
        order = rng.permutation(len(records))
        chosen, manufacturer_counts, source_counts = [], {}, {}
        for index in order:
            row = records.iloc[index]
            if manufacturer_counts.get(row.manufacturer, 0) >= manufacturer_cap:
                continue
            if source_counts.get(row.source, 0) >= source_cap:
                continue
            chosen.append(index)
            manufacturer_counts[row.manufacturer] = manufacturer_counts.get(row.manufacturer, 0) + 1
            source_counts[row.source] = source_counts.get(row.source, 0) + 1
            if len(chosen) == TARGET_SIZE:
                break
        if len(chosen) != TARGET_SIZE:
            continue
        sample = records.iloc[chosen].copy()
        if sample.manufacturer.nunique() < MIN_MANUFACTURERS:
            continue
        score = candidate_score(sample)
        if best_score is None or score > best_score:
            best, best_score = sample, score
    if best is None:
        raise RuntimeError("no Benchmark-80 satisfying the declared caps was found")
    return best.sort_values(["manufacturer", "name", "entity_id"]).reset_index(drop=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entities", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--trials", type=int, default=5000)
    args = parser.parse_args()

    entities = pd.read_csv(args.entities)
    pool = eligible(entities)
    candidate = select_candidate(pool, args.trials)
    manifest_text = "\n".join(candidate.entity_id)
    manifest_hash = hashlib.sha256(manifest_text.encode()).hexdigest()
    candidate.insert(0, "benchmark_index", np.arange(1, len(candidate) + 1))
    candidate["selection_seed"] = SEED
    candidate["manifest_hash"] = manifest_hash

    gates = {
        "exactly_80_entities": bool(len(candidate) == TARGET_SIZE),
        "at_least_10_manufacturers": bool(
            candidate.manufacturer.nunique() >= MIN_MANUFACTURERS
        ),
        "manufacturer_share_at_most_25_percent":
            bool(candidate.manufacturer.value_counts(normalize=True).max()
                 <= MAX_MANUFACTURER_SHARE),
        "source_share_at_most_50_percent":
            bool(candidate.source.value_counts(normalize=True).max() <= MAX_SOURCE_SHARE),
        "all_cases_geometry_and_kinematics_ready": bool(
            len(candidate) == len(eligible(
                entities[entities.entity_id.isin(candidate.entity_id)]
            ))
        ),
    }
    summary = {
        "target_version": "v4",
        "primary_question": "Can a unified, fair Mesh+URDF Benchmark-80 be constructed?",
        "complexity_is_gate": False,
        "eligible_pool_size": int(len(pool)),
        "eligible_pool_manufacturers": int(pool.manufacturer.nunique()),
        "candidate_size": int(len(candidate)),
        "candidate_manufacturers": int(candidate.manufacturer.nunique()),
        "manufacturer_counts": candidate.manufacturer.value_counts().to_dict(),
        "source_counts": candidate.source.value_counts().to_dict(),
        "maximum_manufacturer_share": float(candidate.manufacturer.value_counts(normalize=True).max()),
        "maximum_source_share": float(candidate.source.value_counts(normalize=True).max()),
        "selection_seed": SEED,
        "selection_trials": args.trials,
        "manifest_hash": manifest_hash,
        "automated_gates": gates,
        "technical_decision": "GO" if all(gates.values()) else "NO-GO",
        "release_ready": False,
        "release_blockers": [
            "file-level license and redistribution audit",
            "manual review and freeze of final Benchmark-80",
            "canonical units/frames and leakage policy",
            "versioned common evaluator",
            "same-case baseline execution",
        ],
        "manifest_status": "review candidate; not the frozen paper test set",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    candidate.to_csv(args.output_dir / "candidate_benchmark80.csv", index=False,
                     encoding="utf-8-sig")
    (args.output_dir / "readiness_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
