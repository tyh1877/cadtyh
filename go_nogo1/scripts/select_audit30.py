"""Deterministically freeze a diverse 30-entity audit sample."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd


def anonymize(entity_id: str) -> str:
    return "G1-" + hashlib.sha256(("go-no-go-1|" + entity_id).encode()).hexdigest()[:6].upper()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entities", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    df = pd.read_csv(args.entities)
    df = df[df.eligible_entity & df.feature_ok].copy()
    selected = []
    source_counts, manufacturer_counts = Counter(), Counter()
    strata = ["low", "medium", "high"]
    targets = {s: np.linspace(.05, .95, 10) for s in strata}
    # Interleave strata so early choices cannot consume the global diversity caps.
    for index in range(10):
        for stratum in strata:
            pool = df[df.complexity_stratum.eq(stratum) & ~df.entity_id.isin(selected)].copy()
            target = pool.preliminary_complexity_score.quantile(targets[stratum][index])
            span = max(pool.preliminary_complexity_score.max() - pool.preliminary_complexity_score.min(), 1e-9)
            pool["distance"] = abs(pool.preliminary_complexity_score - target) / span
            pool["source_load"] = pool.source.map(source_counts)
            pool["manufacturer_load"] = pool.manufacturer.map(manufacturer_counts)
            pool = pool[(pool.source_load < 15) & (pool.manufacturer_load < 4)]
            if pool.empty:
                raise RuntimeError(f"diversity constraints infeasible at {stratum} target {index}")
            # Diversity has priority; target distance breaks ties without using labels.
            pick = pool.sort_values(
                ["source_load", "manufacturer_load", "distance", "source", "manufacturer", "name"],
                kind="stable",
            ).iloc[0]
            selected.append(pick.entity_id)
            source_counts[pick.source] += 1
            manufacturer_counts[pick.manufacturer] += 1
    audit = df.set_index("entity_id").loc[selected].reset_index()
    audit["blind_id"] = audit.entity_id.map(anonymize)
    audit["audit_order"] = audit.blind_id.rank(method="first").astype(int)
    audit = audit.sort_values("audit_order")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = args.output_dir / "audit30_manifest.csv"
    audit.to_csv(manifest, index=False, encoding="utf-8-sig")
    rating = audit[["blind_id", "audit_order"]].copy()
    rating["geometric_complexity_1_to_5"] = ""
    rating["confidence_1_to_3"] = ""
    rating["unusable_or_incomplete"] = ""
    rating["notes"] = ""
    rating.to_csv(args.output_dir / "expert_rating_blank.csv", index=False, encoding="utf-8-sig")
    summary = {
        "n": len(audit), "strata": audit.complexity_stratum.value_counts().to_dict(),
        "sources": audit.source.value_counts().to_dict(),
        "manufacturers": audit.manufacturer.value_counts().to_dict(),
        "max_source_share": float(audit.source.value_counts(normalize=True).max()),
        "max_manufacturer_share": float(audit.manufacturer.value_counts(normalize=True).max()),
    }
    (args.output_dir / "audit30_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
