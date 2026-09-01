from __future__ import annotations

import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

if "ROBOTCAD_REPO_ROOT" in os.environ:
    ROOT = Path(os.environ["ROBOTCAD_REPO_ROOT"]).resolve()
else:
    ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = ROOT / "experiments" / "freecad_robot_link_reconstruction_pilot_v2" / "scripts"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPT_DIR))

from pilot_common import EXP, RESULTS, RUNS, VERSIONS, dump_json, ensure_dirs, frozen_rows, write_csv
from robotcad.backends.freecad_api.FreeCADBackend import execute_ir  # type: ignore  # noqa: E402


def run_one(version: str, row: dict[str, str]) -> dict[str, Any]:
    out_dir = RUNS / version / row["case_id"] / row["link_id"]
    ir_path = out_dir / "executable_cad_ir_v1_2.json"
    if not ir_path.exists():
        ir_path = out_dir / "executable_cad_ir.json"
    result_dir = out_dir / "freecad"
    result_dir.mkdir(parents=True, exist_ok=True)
    if not ir_path.exists():
        return {
            "version": version,
            "case_id": row["case_id"],
            "link_id": row["link_id"],
            "role": row["role"],
            "status": "IR_INCOMPLETE",
            "operation_count": 0,
            "native_success_count": 0,
            "semantic_match_count": 0,
            "fallback_count": 0,
            "fcstd_success": False,
            "step_success": False,
            "stl_success": False,
            "execution_time_seconds": 0.0,
            "failure_stage": "IR_VALIDATION",
            "failure_reason": "executable_cad_ir.json missing",
        }
    ir = json.loads(ir_path.read_text(encoding="utf-8"))
    start = time.time()
    result = execute_ir(ir, result_dir)
    elapsed = time.time() - start
    dump_json(result_dir / "execution_log.json", result["execution_log"])
    dump_json(result_dir / "feature_manifest.json", result["feature_manifest"])
    dump_json(result_dir / "object_tree.json", result["object_tree"])
    dump_json(result_dir / "execution_result.json", {k: v for k, v in result.items() if k not in {"execution_log", "feature_manifest", "object_tree"}})
    exports = result.get("exports") or {}
    log = result.get("execution_log") or []
    return {
        "version": version,
        "case_id": row["case_id"],
        "link_id": row["link_id"],
        "role": row["role"],
        "status": result["status"],
        "operation_count": len(ir.get("operations", [])),
        "native_success_count": sum(bool(x.get("success")) for x in log),
        "semantic_match_count": sum(bool(x.get("semantic_match")) for x in log),
        "fallback_count": sum(bool(x.get("fallback_used")) for x in log),
        "fcstd_success": Path(exports.get("fcstd", "")).exists() if exports else False,
        "step_success": Path(exports.get("step", "")).exists() if exports else False,
        "stl_success": Path(exports.get("stl", "")).exists() if exports else False,
        "execution_time_seconds": elapsed,
        "failure_stage": "" if result["status"] == "SUCCESS" else "FREECAD_EXECUTION",
        "failure_reason": result.get("error") or "",
    }


def main() -> None:
    ensure_dirs()
    rows = []
    for version in VERSIONS:
        for row in frozen_rows():
            result = run_one(version, row)
            rows.append(result)
            print(version, row["case_id"], row["link_id"], result["status"])
    write_csv(RESULTS / "execution_metrics.csv", rows)
    summary = {
        "versions": {},
        "silent_fallback_total": sum(int(r["fallback_count"]) for r in rows),
    }
    for version in VERSIONS:
        subset = [r for r in rows if r["version"] == version]
        summary["versions"][version] = {
            "links_total": len(subset),
            "success_links": sum(r["status"] == "SUCCESS" for r in subset),
            "operation_count": sum(int(r["operation_count"]) for r in subset),
            "native_success_count": sum(int(r["native_success_count"]) for r in subset),
            "fallback_count": sum(int(r["fallback_count"]) for r in subset),
        }
    dump_json(RESULTS / "execution_summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
