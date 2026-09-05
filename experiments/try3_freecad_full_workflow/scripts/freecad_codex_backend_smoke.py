"""Synthetic smoke for the exact FreeCAD operations used by Codex Try-3."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def frame():
    return {"origin": [0, 0, 0], "x_axis": [1, 0, 0], "y_axis": [0, 1, 0], "z_axis": [0, 0, 1]}


def main(repo: Path, output: Path) -> int:
    sys.path.insert(0, str(repo))
    from robotcad.backends.freecad_api.FreeCADBackend import execute_ir
    cases = [
        {"ir_version": "codex_link_ir_v1", "case_id": "SMOKE", "link_id": "L0", "bodies": [], "operations": [{"op_id": "box", "op_type": "oriented_box", "target_body": "box", "dependencies": [], "reference_frame": frame(), "start": [0, 0, 0], "end": [20, 10, 30], "width_mm": 12, "depth_mm": 10}], "final_object": "box"},
        {"ir_version": "codex_link_ir_v1", "case_id": "SMOKE", "link_id": "L1", "bodies": [], "operations": [
            {"op_id": "loft", "op_type": "lofted_prism", "target_body": "loft", "dependencies": [], "reference_frame": frame(), "start": [0, 0, 0], "end": [40, 5, 15], "start_size_mm": [18, 14], "end_size_mm": [11, 9]},
            {"op_id": "joint", "op_type": "cylinder_primitive", "target_body": "joint", "dependencies": [], "reference_frame": frame(), "center": [0, 0, 0], "axis": [0, 1, 0], "radius_mm": 11, "height_mm": 16},
            {"op_id": "union", "op_type": "boolean_union", "target_body": "loft", "dependencies": ["loft", "joint"], "reference_frame": frame(), "tool_bodies": ["joint"]}
        ], "final_object": "union"},
    ]
    rows = []
    for index, ir in enumerate(cases):
        result = execute_ir(ir, output / f"case_{index}" / "model")
        rows.append({"case": index, "status": result["status"], "error": result.get("error"), "fallbacks": sum(bool(item.get("fallback_used")) for item in result["execution_log"]), "native_operations": [item.get("executed_native_operation") for item in result["execution_log"]]})
    payload = {"status": "PASS" if all(row["status"] == "SUCCESS" and row["fallbacks"] == 0 for row in rows) else "FAIL", "cases": rows}
    output.mkdir(parents=True, exist_ok=True)
    (output / "smoke_result.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[-2]).resolve(), Path(sys.argv[-1]).resolve()))

