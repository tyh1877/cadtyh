"""Run reproducibility checks for freecad_backend_pilot.

Executed with FreeCADCmd. Repeats one native smoke operation and one
IR-complete generated link three times. The check compares stable semantic
signals, not byte-identical FCStd/STEP/STL files.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import os
import sys
from pathlib import Path


ROOT = Path(os.environ.get("ROBOTCAD_REPO_ROOT", os.getcwd())).resolve()
PILOT = ROOT / "freecad_backend_pilot"
RESULTS = PILOT / "results"
SMOKE_SCRIPT = PILOT / "scripts" / "run_operation_smokes_freecad.py"
sys.path.insert(0, str(ROOT))

from robotcad.backends.freecad_api.FreeCADBackend import execute_ir  # noqa: E402


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


def manifest_stats(result):
    final_name = result["execution_log"][-1]["native_object_name"]
    final_items = [item for item in result["feature_manifest"] if item["name"] == final_name]
    final = final_items[0] if final_items else result["feature_manifest"][-1]
    return {
        "status": result["status"],
        "feature_types": [row["native_object_type"] for row in result["execution_log"]],
        "bbox": [round(float(v), 6) for v in final.get("bbox", [])],
        "volume": round(float(final.get("volume", 0)), 6),
        "faces": int(final.get("faces", 0)),
        "edges": int(final.get("edges", 0)),
        "exports": {key: bool(value) for key, value in result.get("exports", {}).items()},
    }


def append_consistency_row(rows, case_id, link_id, trial_stats):
    first = trial_stats[0]
    consistent_success = all(t["status"] == first["status"] for t in trial_stats)
    consistent_feature_tree = all(t["feature_types"] == first["feature_types"] for t in trial_stats)
    consistent_bbox = all(t["bbox"] == first["bbox"] for t in trial_stats)
    consistent_volume = all(t["volume"] == first["volume"] for t in trial_stats)
    consistent_exports = all(t["exports"] == first["exports"] for t in trial_stats)
    success = all(
        [
            first["status"] == "SUCCESS",
            consistent_success,
            consistent_feature_tree,
            consistent_bbox,
            consistent_volume,
            consistent_exports,
        ]
    )
    rows.append(
        {
            "case_id": case_id,
            "link_id": link_id,
            "trial_count": len(trial_stats),
            "status": "SUCCESS" if success else "FAILURE",
            "operation_success_consistent": consistent_success,
            "feature_tree_consistent": consistent_feature_tree,
            "bbox_consistent": consistent_bbox,
            "volume_consistent": consistent_volume,
            "export_consistent": consistent_exports,
            "failure_stage": "" if success else "REPRODUCIBILITY_CHECK",
            "failure_reason": "" if success else json.dumps(trial_stats),
        }
    )


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
    smoke_stats = [
        {
            "status": "SUCCESS" if item["success"] else "FAILURE",
            "feature_types": ["Part::Revolution"],
            "bbox": item["stats"]["bbox"] if item["stats"] else [],
            "volume": item["stats"]["volume"] if item["stats"] else 0,
            "faces": item["stats"]["faces"] if item["stats"] else 0,
            "edges": item["stats"]["edges"] if item["stats"] else 0,
            "exports": {"fcstd": item["success"], "step": item["success"], "stl": item["success"]},
        }
        for item in trial_stats
    ]
    append_consistency_row(rows, "smoke_revolve", "smoke", smoke_stats)

    link_case = "dev_arm-dcc2b0ce1e"
    link_id = "L2"
    ir = json.loads((PILOT / "runs" / link_case / link_id / "executable_cad_ir.json").read_text(encoding="utf-8"))
    link_stats = []
    for trial in range(3):
        result = execute_ir(ir, PILOT / "artifacts" / "reproducibility" / f"{link_case}_{link_id}_trial_{trial}")
        link_stats.append(manifest_stats(result))
    append_consistency_row(rows, link_case, link_id, link_stats)
    with (RESULTS / "reproducibility_results.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = list(rows[0])
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "smoke_revolve_trials": smoke_stats,
        "smoke_revolve_reproducible": rows[0]["status"] == "SUCCESS",
        "complex_link_trials": link_stats,
        "complex_link_reproducible": rows[1]["status"] == "SUCCESS",
    }
    (RESULTS / "reproducibility_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
