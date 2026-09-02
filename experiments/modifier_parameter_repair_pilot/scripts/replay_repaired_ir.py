from __future__ import annotations

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
SCRIPT_DIR = ROOT / "experiments" / "modifier_parameter_repair_pilot" / "scripts"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPT_DIR))

from common import RESULTS, RUNS, VERSIONS, dump_json, ensure_dirs, frozen_rows, output_case_dir, write_csv  # type: ignore  # noqa: E402
from robotcad.backends.freecad_api.FreeCADBackend import execute_ir  # type: ignore  # noqa: E402


def run_one(version: str, row: dict[str, str]) -> dict[str, Any]:
    case_dir = output_case_dir(version, row["case_id"], row["link_id"])
    ir_path = case_dir / "executable_cad_ir_v1_2.json"
    out_dir = RUNS / "execution" / version / row["case_id"] / row["link_id"] / "freecad"
    out_dir.mkdir(parents=True, exist_ok=True)
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
            "failure_code": "IR_INCOMPLETE",
            "failure_stage": "IR_VALIDATION",
            "failure_reason": "modifier repaired executable_cad_ir_v1_2.json missing",
            "execution_time_seconds": 0.0,
        }
    ir = json.loads(ir_path.read_text(encoding="utf-8"))
    dump_json(out_dir / "input_ir.json", ir)
    start = time.time()
    result = execute_ir(ir, out_dir)
    elapsed = time.time() - start
    dump_json(out_dir / "execution_log.json", result["execution_log"])
    dump_json(out_dir / "feature_manifest.json", result["feature_manifest"])
    dump_json(out_dir / "object_tree.json", result["object_tree"])
    dump_json(out_dir / "execution_result.json", {k: v for k, v in result.items() if k not in {"execution_log", "feature_manifest", "object_tree"}})
    failed = [item for item in result["execution_log"] if not item.get("success")]
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
        "failure_code": failed[-1].get("failure_code") if failed else "",
        "failure_stage": "" if result["status"] == "SUCCESS" else "FREECAD_EXECUTION",
        "failure_reason": result.get("error") or "",
        "execution_time_seconds": elapsed,
    }


def main() -> None:
    ensure_dirs()
    rows = []
    for version in VERSIONS:
        for row in frozen_rows():
            result = run_one(version, row)
            rows.append(result)
            print(version, row["case_id"], row["link_id"], result["status"], result["failure_code"])
    write_csv(RESULTS / "execution_metrics.csv", rows)


if __name__ == "__main__":
    main()
