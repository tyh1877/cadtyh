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
SCRIPT_DIR = ROOT / "experiments" / "freecad_operation_robustness_pilot" / "scripts"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPT_DIR))

from common import EXP, FRAME, RESULTS, RUNS, dump_json, ensure_dirs, op, profile_circle, profile_rect, write_csv  # type: ignore  # noqa: E402
from robotcad.backends.freecad_api.FreeCADBackend import execute_ir  # type: ignore  # noqa: E402


def base_ir(case_id: str, link_id: str, operations: list[dict[str, Any]], final_object: str) -> dict[str, Any]:
    return {
        "ir_version": "executable_cad_ir_v1_2",
        "case_id": case_id,
        "link_id": link_id,
        "bodies": [{"body_id": "body", "role": "operation_smoke"}],
        "operations": operations,
        "final_object": final_object,
        "metadata": {"source": "freecad_operation_robustness_pilot_smoke"},
    }


def smoke_cases() -> list[dict[str, Any]]:
    box = op("box", "extrude", "box", [], profile=profile_rect([0, 0, 0], [40, 20]), distance_mm=10, operation_mode="new_body")
    boss = op("boss", "revolve", "boss", [], profile=profile_rect([9, 0, 5], [4, 8]), axis={"point": [5, 0, 5], "direction": [0, 1, 0]}, angle_deg=360, operation_mode="new_body")
    far_boss = op("far_boss", "revolve", "far_boss", [], profile=profile_rect([109, 0, 5], [4, 8]), axis={"point": [105, 0, 5], "direction": [0, 1, 0]}, angle_deg=360, operation_mode="new_body")
    cutter = op("cutter", "extrude", "cutter", [], profile=profile_circle([0, 0, 0], 4), distance_mm=20, operation_mode="new_body")
    far_cutter = op("far_cutter", "extrude", "far_cutter", [], profile=profile_circle([100, 100, 0], 4), distance_mm=20, operation_mode="new_body")
    return [
        {
            "name": "boolean_union_success",
            "expected": "SUCCESS",
            "ir": base_ir("smoke", "boolean_union_success", [box, boss, op("union", "boolean_union", "box", ["box", "boss"], tool_bodies=["boss"])], "union"),
        },
        {
            "name": "boolean_union_expected_failure",
            "expected": "FAILURE",
            "ir": base_ir("smoke", "boolean_union_expected_failure", [box, op("union", "boolean_union", "box", ["box"], tool_bodies=[])], "union"),
        },
        {
            "name": "boolean_cut_success",
            "expected": "SUCCESS",
            "ir": base_ir("smoke", "boolean_cut_success", [box, cutter, op("cut", "boolean_cut", "box", ["box", "cutter"], tool_bodies=["cutter"])], "cut"),
        },
        {
            "name": "boolean_cut_expected_failure",
            "expected": "FAILURE",
            "ir": base_ir("smoke", "boolean_cut_expected_failure", [box, far_cutter, op("cut", "boolean_cut", "box", ["box", "far_cutter"], tool_bodies=["far_cutter"])], "cut"),
        },
        {
            "name": "fillet_success",
            "expected": "SUCCESS",
            "ir": base_ir("smoke", "fillet_success", [box, op("fillet", "fillet", "box", ["box"], radius_mm=1.0, edge_selectors=[{"selector_type": "outer_long_edges", "max_edges": 1}])], "fillet"),
        },
        {
            "name": "fillet_expected_failure",
            "expected": "FAILURE",
            "ir": base_ir("smoke", "fillet_expected_failure", [box, op("fillet", "fillet", "box", ["box"], radius_mm=100.0, edge_selectors=[{"selector_type": "outer_long_edges", "max_edges": 1}])], "fillet"),
        },
        {
            "name": "chamfer_success",
            "expected": "SUCCESS",
            "ir": base_ir("smoke", "chamfer_success", [box, op("chamfer", "chamfer", "box", ["box"], distance_mm=1.0, edge_selectors=[{"selector_type": "outer_long_edges", "max_edges": 1}])], "chamfer"),
        },
        {
            "name": "chamfer_expected_failure",
            "expected": "FAILURE",
            "ir": base_ir("smoke", "chamfer_expected_failure", [box, op("chamfer", "chamfer", "box", ["box"], distance_mm=100.0, edge_selectors=[{"selector_type": "outer_long_edges", "max_edges": 1}])], "chamfer"),
        },
    ]


def main() -> None:
    ensure_dirs()
    rows = []
    for case in smoke_cases():
        out_dir = RUNS / "smoke" / case["name"]
        out_dir.mkdir(parents=True, exist_ok=True)
        dump_json(out_dir / "input_ir.json", case["ir"])
        start = time.time()
        result = execute_ir(case["ir"], out_dir)
        elapsed = time.time() - start
        dump_json(out_dir / "execution_log.json", result["execution_log"])
        dump_json(out_dir / "feature_manifest.json", result["feature_manifest"])
        dump_json(out_dir / "object_tree.json", result["object_tree"])
        dump_json(out_dir / "execution_result.json", {k: v for k, v in result.items() if k not in {"execution_log", "feature_manifest", "object_tree"}})
        failed = [item for item in result["execution_log"] if not item.get("success")]
        failure_code = failed[-1].get("failure_code") if failed else ""
        passed = (case["expected"] == "SUCCESS" and result["status"] == "SUCCESS") or (case["expected"] == "FAILURE" and result["status"] == "FAILURE" and bool(failure_code))
        rows.append(
            {
                "case_name": case["name"],
                "expected": case["expected"],
                "status": result["status"],
                "passed": passed,
                "failure_code": failure_code,
                "fallback_count": sum(bool(item.get("fallback_used")) for item in result["execution_log"]),
                "elapsed_seconds": elapsed,
            }
        )
        print(case["name"], result["status"], failure_code, "PASS" if passed else "FAIL")
    write_csv(RESULTS / "operation_smoke.csv", rows)


if __name__ == "__main__":
    main()
