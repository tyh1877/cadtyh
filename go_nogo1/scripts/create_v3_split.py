"""Create a deterministic product-family-disjoint 80/32/30 v3 split."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


TARGETS = {"development": 80, "validation": 32, "final_holdout": 30}


def family_name(manufacturer: str, name: str) -> str:
    """Conservative family grouping; variants must never cross splits."""
    rules = {
        "ABB": [r"^(CRB\s+\d+)", r"^(IRB\s+1200)", r"^(IRB\s+120T?)", r"^(IRB\s+1600)",
                r"^(IRB\s+4600)", r"^(IRB\s+52)", r"^(IRB\s+6640)", r"^(IRB\s+6650S)",
                r"^(IRB\s+6700)", r"^(IRB\s+\d+)"],
        "Fanuc": [r"^(LR Mate 200i[D]?)", r"^(LR Mate 200iC)", r"^(LR Mate 200iB)",
                  r"^(CR-7iA)", r"^(CR-35iA)", r"^(CRX-10iA)",
                  r"^([MR]-\d+i[A-Z])"],
        "KUKA": [r"^(LBR iiwa)", r"^(KR\s+\d+)"],
        "Kinova Robotics": [r"^(Gen3)", r"^(Jaco)", r"^(Mico)"],
        "Staubli": [r"^(RX\s+160)", r"^(TX2-60)", r"^(TX2-90)", r"^(TX-60)", r"^(TX-90)"],
        "Trossen Robotics": [r"^(PincherX)", r"^(ReactorX)", r"^(ViperX)", r"^(WidowX)"],
        "Universal Robots": [r"^(UR\d+)"],
        "Yaskawa Motoman": [r"^(Motoman SIA)", r"^(Motoman MH)"],
        "Schunk": [r"^(LWA)"],
        "Franka Emika": [r"^(FR3|Panda)"],
    }
    for pattern in rules.get(manufacturer, []):
        match = re.search(pattern, name, flags=re.I)
        if match:
            return f"{manufacturer}|{match.group(1).casefold()}"
    normalized = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
    return f"{manufacturer}|{normalized}"


def assignment_score(frame: pd.DataFrame) -> float:
    score = 0.0
    total = len(frame)
    overall_source = frame.source.value_counts(normalize=True)
    overall_stratum = frame.complexity_stratum.value_counts(normalize=True)
    for split, target in TARGETS.items():
        part = frame[frame.v3_split == split]
        score += 20 * (len(part) - target) ** 2
        for column, overall in [("source", overall_source), ("complexity_stratum", overall_stratum)]:
            observed = part[column].value_counts(normalize=True)
            score += total * float((observed.reindex(overall.index, fill_value=0) - overall).abs().sum())
        # Penalize a split containing too few manufacturers without forcing singleton leakage.
        score += max(0, 8 - part.manufacturer.nunique()) * 5
    return score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entities", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260807)
    parser.add_argument("--trials", type=int, default=2000)
    args = parser.parse_args()

    entities = pd.read_csv(args.entities)
    entities = entities[entities.eligible_entity & entities.feature_ok].copy()
    entities["product_family"] = [family_name(m, n) for m, n in zip(entities.manufacturer, entities.name)]
    families = entities.groupby("product_family").size().sort_values(ascending=False)
    rng = np.random.default_rng(args.seed)
    best_score, best_assignment = float("inf"), None
    split_names = list(TARGETS)

    for _ in range(args.trials):
        # Large families first with randomized tie-breaking and stochastic placement.
        noise = pd.Series(rng.random(len(families)), index=families.index)
        order = sorted(families.index, key=lambda x: (-families[x], noise[x]))
        counts = {name: 0 for name in split_names}
        assignment = {}
        for family in order:
            size = int(families[family])
            costs = []
            for split in split_names:
                projected = counts[split] + size
                fill = projected / TARGETS[split]
                overflow = max(0, projected - TARGETS[split])
                costs.append((fill + overflow * 10 + rng.random() * .08, split))
            chosen = min(costs)[1]
            assignment[family] = chosen
            counts[chosen] += size
        candidate = entities.copy()
        candidate["v3_split"] = candidate.product_family.map(assignment)
        score = assignment_score(candidate)
        if score < best_score:
            best_score, best_assignment = score, assignment

    entities["v3_split"] = entities.product_family.map(best_assignment)
    entities["split_seed"] = args.seed
    entities["split_manifest_hash"] = hashlib.sha256(
        "\n".join(f"{row.entity_id},{row.product_family},{row.v3_split}"
                  for row in entities.sort_values("entity_id").itertuples()).encode()
    ).hexdigest()
    overlap = entities.groupby("product_family").v3_split.nunique().max()
    if overlap != 1:
        raise AssertionError("A product family appears in multiple splits")

    summary = {
        "seed": args.seed, "trials": args.trials, "assignment_score": best_score,
        "counts": entities.v3_split.value_counts().to_dict(),
        "family_counts": entities.groupby("v3_split").product_family.nunique().to_dict(),
        "manufacturer_counts": entities.groupby("v3_split").manufacturer.nunique().to_dict(),
        "source_distributions": {
            split: entities[entities.v3_split == split].source.value_counts().to_dict()
            for split in split_names
        },
        "stratum_distributions": {
            split: entities[entities.v3_split == split].complexity_stratum.value_counts().to_dict()
            for split in split_names
        },
        "max_family_split_count": int(overlap),
        "manifest_hash": entities.split_manifest_hash.iloc[0],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    columns = ["entity_id", "manufacturer", "name", "product_family", "source",
               "complexity_stratum", "v3_split", "split_seed", "split_manifest_hash"]
    entities[columns].sort_values(["v3_split", "manufacturer", "name"]).to_csv(
        args.output_dir / "split_manifest.csv", index=False, encoding="utf-8-sig"
    )
    (args.output_dir / "split_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
