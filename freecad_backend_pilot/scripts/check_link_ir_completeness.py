"""Check whether existing operation_plan_pilot plans are executable CAD IR.

This does not execute FreeCAD. It enforces the pilot rule that the backend must
not guess missing CAD parameters from vague semantic operation descriptions.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "freecad_backend_pilot"
RESULTS = PILOT / "results"
MANIFEST = PILOT / "input_manifest.csv"


OP_MAP = {
    "Extrude": "extrude",
    "BooleanCut": "boolean_cut",
    "CreateHole": "cut",
    "Revolve": "revolve",
    "Loft": "loft",
    "Sweep": "sweep",
    "Shell": "shell",
    "BooleanUnion": "boolean_union",
    "ApplyFillet": "fillet",
    "ApplyChamfer": "chamfer",
    "CircularPattern": "pattern",
    "LinearPattern": "pattern",
    "Mirror": "mirror",
}


REQUIRED_FIELDS = {
    "extrude": {"sketch_plane", "profile", "distance_mm", "operation_mode", "reference_frame"},
    "cut": {"sketch_plane", "profile", "distance_mm", "operation_mode", "reference_frame"},
    "boolean_cut": {"target_body", "tool_bodies", "reference_frame"},
    "revolve": {"sketch_plane", "profile", "axis", "angle_deg", "operation_mode", "reference_frame"},
    "loft": {"profiles", "solid", "operation_mode", "reference_frame"},
    "sweep": {"profile", "profile_frame", "path", "orientation_mode", "transition_mode", "solid", "operation_mode", "reference_frame"},
    "shell": {"target_body", "faces_to_remove", "thickness_mm", "direction", "join_mode", "reference_frame"},
    "boolean_union": {"target_body", "tool_bodies", "reference_frame"},
    "fillet": {"target_body", "edge_selectors", "radius_mm", "reference_frame"},
    "chamfer": {"target_body", "edge_selectors", "distance_mm", "reference_frame"},
    "pattern": {"target_features", "pattern_type", "axis_or_direction", "count", "spacing_or_angle", "reference_frame"},
    "mirror": {"target_features", "mirror_plane", "reference_frame"},
}


def check_operation(op: dict) -> tuple[str, list[str]]:
    raw_type = op.get("op") or op.get("operation")
    mapped = OP_MAP.get(raw_type, raw_type)
    if mapped == "CreateSketchProfile":
        return "sketch_profile_not_executable_body_feature", ["executable profile schema not supplied"]
    required = REQUIRED_FIELDS.get(mapped)
    if not required:
        return str(mapped), [f"unsupported operation type in executable IR check: {raw_type}"]
    missing = sorted(field for field in required if field not in op)
    return str(mapped), missing


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    rows = []
    detail_rows = []
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        manifest_rows = list(csv.DictReader(handle))
    for item in manifest_rows:
        plan_path = ROOT / item["source_plan"]
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        ops = plan.get("operations", [])
        incomplete = 0
        executable = 0
        for op in ops:
            mapped, missing = check_operation(op)
            status = "IR_COMPLETE" if not missing else "IR_INCOMPLETE"
            if status == "IR_COMPLETE":
                executable += 1
            else:
                incomplete += 1
            detail_rows.append(
                {
                    "case_id": item["case_id"],
                    "link_id": item["link_id"],
                    "op_id": op.get("op_id") or op.get("operation_id", ""),
                    "requested_operation": op.get("op") or op.get("operation", ""),
                    "mapped_ir_operation": mapped,
                    "status": status,
                    "missing_required_fields": ";".join(missing),
                }
            )
        rows.append(
            {
                "case_id": item["case_id"],
                "link_id": item["link_id"],
                "source_plan": item["source_plan"],
                "status": "IR_INCOMPLETE" if incomplete else "READY",
                "operation_count": len(ops),
                "native_success_count": 0,
                "semantic_match_count": 0,
                "fallback_count": 0,
                "recompute_success": False,
                "fcstd_success": False,
                "reopen_success": False,
                "step_success": False,
                "stl_success": False,
                "failure_stage": "IR_VALIDATION",
                "failure_reason": f"{incomplete}/{len(ops)} operations missing required executable CAD IR fields; backend execution intentionally skipped",
            }
        )
    with (RESULTS / "link_execution_results.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = list(rows[0])
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(rows)
    with (RESULTS / "link_ir_completeness_detail.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = list(detail_rows[0])
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(detail_rows)
    summary = {
        "links_total": len(rows),
        "ready_links": sum(r["status"] == "READY" for r in rows),
        "ir_incomplete_links": sum(r["status"] == "IR_INCOMPLETE" for r in rows),
        "operations_total": len(detail_rows),
        "ir_complete_operations": sum(r["status"] == "IR_COMPLETE" for r in detail_rows),
        "ir_incomplete_operations": sum(r["status"] == "IR_INCOMPLETE" for r in detail_rows),
    }
    (RESULTS / "link_ir_completeness_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

