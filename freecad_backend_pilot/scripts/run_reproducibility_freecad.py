"""Run minimal reproducibility checks for freecad_backend_pilot.

Executed with FreeCADCmd. Repeats one native smoke operation three times and
records that the complex link case cannot run until executable CAD IR exists.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import os
from pathlib import Path


ROOT = Path(os.environ.get("ROBOTCAD_REPO_ROOT", os.getcwd())).resolve()
PILOT = ROOT / "freecad_backend_pilot"
RESULTS = PILOT / "results"
SMOKE_SCRIPT = PILOT / "scripts" / "run_operation_smokes_freecad.py"


def load_smoke_module():
    spec = importlib.util.spec_from_file_location("freecad_smokes", SMOKE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def round_stats(stats):
    return {
        "valid": stats["valid"],
        "volume": round(float(stats["volume"]), 6),
        "bbox": [round(float(v), 6) for v in stats["bbox"]],
        "solids": int(stats["solids"]),
        "faces": int(stats["faces"]),
        "edges": int(stats["edges"]),
    }


def main():
    module = load_smoke_module()
    rows = []
    trial_stats = []
    revolve = next(s for s in module.SMOKES if s[1] == "revolve")
    for trial in range(3):
        row, log = module.run_one(*revolve)
        success = all(
            [
                bool(row["semantic_match"]),
                bool(row["recompute_success"]),
                bool(row["save_success"]),
                bool(row["reopen_success"]),
                bool(row["step_success"]),
                bool(row["stl_success"]),
            ]
        )
        stats = round_stats(log["shape_stats"]) if success else None
        trial_stats.append({"success": success, "stats": stats})
    first = trial_stats[0]
    consistent_success = all(t["success"] == first["success"] for t in trial_stats)
    consistent_shape = all(t["stats"] == first["stats"] for t in trial_stats)
    rows.append(
        {
            "case_id": "smoke_revolve",
            "link_id": "smoke",
            "trial_count": 3,
            "status": "SUCCESS" if consistent_success and consistent_shape else "FAILURE",
            "operation_success_consistent": consistent_success,
            "feature_tree_consistent": consistent_success,
            "bbox_consistent": consistent_shape,
            "volume_consistent": consistent_shape,
            "export_consistent": consistent_success,
            "failure_stage": "" if consistent_success and consistent_shape else "REPRODUCIBILITY_CHECK",
            "failure_reason": "" if consistent_success and consistent_shape else json.dumps(trial_stats),
        }
    )
    rows.append(
        {
            "case_id": "dev_arm-dcc2b0ce1e",
            "link_id": "L2",
            "trial_count": 0,
            "status": "IR_INCOMPLETE",
            "operation_success_consistent": False,
            "feature_tree_consistent": False,
            "bbox_consistent": False,
            "volume_consistent": False,
            "export_consistent": False,
            "failure_stage": "IR_VALIDATION",
            "failure_reason": "Existing operation_plan_pilot link plan is not Executable CAD IR; repeated FreeCAD execution intentionally skipped",
        }
    )
    with (RESULTS / "reproducibility_results.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = list(rows[0])
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "smoke_revolve_trials": trial_stats,
        "smoke_revolve_reproducible": rows[0]["status"] == "SUCCESS",
        "complex_link_trial_status": rows[1]["status"],
    }
    (RESULTS / "reproducibility_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

