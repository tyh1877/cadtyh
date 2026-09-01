"""Execute generated Executable CAD IR links through FreeCADBackend."""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path


ROOT = Path(os.environ.get("ROBOTCAD_REPO_ROOT", os.getcwd())).resolve()
PILOT = ROOT / "freecad_backend_pilot"
RUNS = PILOT / "runs"
RESULTS = PILOT / "results"

sys.path.insert(0, str(ROOT / "robotcad" / "backends" / "freecad_api"))
from FreeCADBackend import execute_ir  # type: ignore  # noqa: E402


def main() -> None:
    manifest_rows = list(csv.DictReader((PILOT / "input_manifest.csv").open(encoding="utf-8", newline="")))
    rows = []
    RESULTS.mkdir(parents=True, exist_ok=True)
    for item in manifest_rows:
        run_dir = RUNS / item["case_id"] / item["link_id"]
        ir_path = run_dir / "executable_cad_ir.json"
        if not ir_path.exists():
            manifest_path = run_dir / "manifest.json"
            status = "IR_INCOMPLETE"
            reason = "executable_cad_ir.json missing"
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                status = manifest.get("status", status)
                reason = "; ".join(manifest.get("errors", [])) or reason
            rows.append(
                {
                    "case_id": item["case_id"],
                    "link_id": item["link_id"],
                    "source_plan": item["source_plan"],
                    "status": status,
                    "operation_count": 0,
                    "native_success_count": 0,
                    "semantic_match_count": 0,
                    "fallback_count": 0,
                    "recompute_success": False,
                    "fcstd_success": False,
                    "reopen_success": False,
                    "step_success": False,
                    "stl_success": False,
                    "failure_stage": "IR_VALIDATION",
                    "failure_reason": reason,
                }
            )
            continue
        ir = json.loads(ir_path.read_text(encoding="utf-8"))
        out_dir = run_dir / "freecad"
        out_dir.mkdir(parents=True, exist_ok=True)
        result = execute_ir(ir, out_dir)
        (out_dir / "execution_log.json").write_text(json.dumps(result["execution_log"], indent=2), encoding="utf-8")
        (out_dir / "feature_manifest.json").write_text(json.dumps(result["feature_manifest"], indent=2), encoding="utf-8")
        (out_dir / "object_tree.json").write_text(json.dumps(result["object_tree"], indent=2), encoding="utf-8")
        (out_dir / "execution_result.json").write_text(json.dumps({k: v for k, v in result.items() if k not in {"execution_log", "feature_manifest", "object_tree"}}, indent=2), encoding="utf-8")
        log = result["execution_log"]
        exports = result["exports"]
        rows.append(
            {
                "case_id": item["case_id"],
                "link_id": item["link_id"],
                "source_plan": item["source_plan"],
                "status": result["status"],
                "operation_count": len(ir.get("operations", [])),
                "native_success_count": sum(bool(x.get("success")) for x in log),
                "semantic_match_count": sum(bool(x.get("semantic_match")) for x in log),
                "fallback_count": sum(bool(x.get("fallback_used")) for x in log),
                "recompute_success": result["status"] == "SUCCESS",
                "fcstd_success": Path(exports.get("fcstd", "")).exists() if exports else False,
                "reopen_success": result["status"] == "SUCCESS",
                "step_success": Path(exports.get("step", "")).exists() if exports else False,
                "stl_success": Path(exports.get("stl", "")).exists() if exports else False,
                "failure_stage": "" if result["status"] == "SUCCESS" else "FREECAD_EXECUTION",
                "failure_reason": result.get("error") or "",
            }
        )
        print(item["case_id"], item["link_id"], result["status"])
    fields = list(rows[0])
    with (RESULTS / "link_execution_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "links_total": len(rows),
        "success_links": sum(r["status"] == "SUCCESS" for r in rows),
        "failed_or_incomplete_links": sum(r["status"] != "SUCCESS" for r in rows),
        "operations_total": sum(int(r["operation_count"]) for r in rows),
        "native_success_count": sum(int(r["native_success_count"]) for r in rows),
        "semantic_match_count": sum(int(r["semantic_match_count"]) for r in rows),
        "fallback_count": sum(int(r["fallback_count"]) for r in rows),
    }
    (RESULTS / "link_execution_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
