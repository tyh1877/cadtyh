"""One-shot exact evaluator for frozen A1 candidate artifacts.

This process loads existing FCStd files only.  It contains no generation, repair,
candidate-selection, or rollback path.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import FreeCAD as App

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / "experiments/try5A/scripts"
sys.path.insert(0, str(SCRIPTS))

import freecad_motion_realization as exact  # noqa: E402


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_rigid_group(path):
    document = App.openDocument(str(path))
    obj = document.getObject("RigidGroup")
    if obj is None or obj.Shape.isNull():
        App.closeDocument(document.Name)
        raise RuntimeError(f"RigidGroup missing: {path}")
    shape = obj.Shape.copy()
    App.closeDocument(document.Name)
    return shape


def evaluate_condition(condition, candidate, job, contracts, physical):
    frozen_root = ROOT / candidate["frozen_nonpilot_root"]
    pilot_paths = candidate["conditions"][condition]["pilot_fcstd"]
    shapes = {}
    for link_id in physical:
        path = ROOT / pilot_paths[link_id] if link_id in pilot_paths else frozen_root / link_id / "model.FCStd"
        shapes[link_id] = load_rigid_group(path)
    rows = []
    flags = []
    for config in job["holdout_configurations"]:
        current, ok = exact.exact_config(config, shapes, contracts, physical)
        rows.extend(current)
        flags.append(ok)
    per_joint = []
    for joint_id, configurations in job["holdout_per_joint"].items():
        joint_flags = []
        collision_rows = []
        for config in configurations:
            current, ok = exact.exact_config(config, shapes, contracts, physical)
            joint_flags.append(ok)
            collision_rows.extend(row for row in current if row["classification"] in ("ADJACENT_UNINTENDED_COLLISION", "NONADJACENT_COLLISION"))
        per_joint.append({"joint_id": joint_id, "holdout_samples": len(configurations), "jr3": sum(joint_flags) / len(joint_flags), "all_holdout_samples_pass": all(joint_flags), "collision_rows": collision_rows})
    invalid = len(flags) - sum(flags)
    return {
        "condition": condition,
        "selected_candidate": candidate["conditions"][condition]["selected_candidate"],
        "configuration_count": len(flags),
        "valid_configurations": sum(flags),
        "invalid_configurations": invalid,
        "gcfr": sum(flags) / len(flags),
        "collision_events": sum(row["classification"] in ("ADJACENT_UNINTENDED_COLLISION", "NONADJACENT_COLLISION") for row in rows),
        "intersection_volume_mm3": sum(row["exact_common_mm3"] for row in rows if row["classification"] in ("ADJACENT_UNINTENDED_COLLISION", "NONADJACENT_COLLISION")),
        "per_joint": per_joint,
        "rows": rows,
    }


def main():
    job = load(sys.argv[1])
    candidate = load(job["candidate_manifest"])
    contracts = load(ROOT / candidate["interface_contracts"])
    classification = load(ROOT / "experiments/try5A/results/try5a5/link_realization_classification.json")
    physical = [item["link_id"] for item in classification if item["realization_type"] != "virtual_frame"]
    results = [evaluate_condition(condition, candidate, job, contracts, physical) for condition in candidate["conditions"]]
    payload = {"status": "PASS", "mode": "ONE_SHOT_HOLDOUT_EXACT", "generator_invoked": False, "repair_invoked": False, "conditions": results}
    Path(job["output"]).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "conditions": [{"condition": item["condition"], "gcfr": item["gcfr"]} for item in results]}, indent=2))


if __name__ == "__main__":
    main()
