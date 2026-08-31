"""Compile operation-plan pilot outputs into Fusion-executable SkillCalls."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "operation_plan_pilot"


def call(call_id: str, skill: str, target: str, params: dict) -> dict:
    return {
        "call_id": call_id,
        "skill": skill,
        "version": "v1",
        "target_component": target,
        "parameters": params,
        "calling_agent": "SkillCallProjection",
    }


def dimensions(role: str) -> dict:
    role = role.lower()
    if "upper" in role or "main" in role:
        return {"length": 110, "width": 22, "height": 18, "radius": 13}
    if "forearm" in role or "wrist" in role:
        return {"length": 85, "width": 18, "height": 16, "radius": 10}
    if "elbow" in role or "base" in role or "shoulder" in role:
        return {"length": 55, "width": 38, "height": 28, "radius": 18}
    return {"length": 70, "width": 24, "height": 18, "radius": 10}


def compile_plan(case_id: str, link_id: str, role: str, plan: dict) -> list[dict]:
    target = f"{case_id}_{link_id}".replace("-", "_")
    d = dimensions(role)
    calls = []
    idx = 1
    base_profile = "base_profile"
    calls.append(
        call(
            f"{target}-{idx:03d}",
            "CreateSketchProfile",
            target,
            {
                "profile_id": base_profile,
                "shape": "rectangle",
                "center": [0, 0, 0],
                "axis": [0, 0, 1],
                "plane_offset_mm": -d["height"] / 2,
                "size_mm": [d["length"], d["width"]],
                "source_op": "compiler_base",
            },
        )
    )
    idx += 1
    calls.append(
        call(
            f"{target}-{idx:03d}",
            "Extrude",
            target,
            {"profile_id": base_profile, "distance_mm": d["height"], "operation": "new_body", "source_op": "compiler_base"},
        )
    )
    idx += 1

    for op_index, op in enumerate(plan.get("operations", []), 1):
        source = op.get("op", "")
        purpose = str(op.get("purpose", "")).lower()
        x = -d["length"] * 0.35 + (op_index % 5) * d["length"] * 0.18
        if source == "CreateSketchProfile":
            profile_id = f"p{op_index:02d}"
            shape = "circle" if any(k in purpose for k in ("boss", "bearing", "flange", "hole")) else "rectangle"
            params = {"profile_id": profile_id, "shape": shape, "center": [x, 0, 0], "axis": [0, 0, 1], "plane_offset_mm": d["height"] / 2, "source_op": source}
            if shape == "circle":
                params["radius_mm"] = max(3, d["radius"] * 0.35)
            else:
                params["size_mm"] = [max(8, d["width"] * 0.9), max(5, d["width"] * 0.35)]
            calls.append(call(f"{target}-{idx:03d}", "CreateSketchProfile", target, params))
            idx += 1
        elif source == "Extrude":
            profile_id = f"auto_ext_{op_index:02d}"
            calls.append(call(f"{target}-{idx:03d}", "CreateSketchProfile", target, {"profile_id": profile_id, "shape": "rectangle", "center": [x, 0, 0], "axis": [0, 0, 1], "plane_offset_mm": d["height"] / 2, "size_mm": [max(8, d["width"]), max(5, d["width"] * 0.35)], "source_op": source}))
            idx += 1
            calls.append(call(f"{target}-{idx:03d}", "Extrude", target, {"profile_id": profile_id, "distance_mm": max(4, d["height"] * 0.35), "operation": "new_body", "source_op": source}))
            idx += 1
        elif source in {"Loft", "Revolve"}:
            calls.append(call(f"{target}-{idx:03d}", "Loft", target, {"profile_id": f"loft_{op_index:02d}", "center": [x, 0, d["height"] * 0.65], "axis": [0, 0, 1], "height_mm": max(8, d["height"] * 0.8), "bottom_radius_mm": max(4, d["radius"] * 0.55), "top_radius_mm": max(2, d["radius"] * 0.3), "operation": "new_body", "source_op": source}))
            idx += 1
        elif source in {"Sweep", "BooleanUnion"}:
            profile_id = f"union_{op_index:02d}"
            calls.append(call(f"{target}-{idx:03d}", "CreateSketchProfile", target, {"profile_id": profile_id, "shape": "circle", "center": [x, 0, d["height"] / 2], "axis": [1, 0, 0], "plane_offset_mm": x - d["width"] / 2, "radius_mm": max(3, d["width"] * 0.25), "source_op": source}))
            idx += 1
            calls.append(call(f"{target}-{idx:03d}", "Extrude", target, {"profile_id": profile_id, "distance_mm": max(10, d["width"]), "operation": "new_body", "source_op": source}))
            idx += 1
        elif source in {"Shell", "BooleanCut"}:
            calls.append(call(f"{target}-{idx:03d}", "BooleanCut", target, {"center": [x, 0, 0], "axis": [0, 0, 1], "shape": "rectangle", "size_mm": [max(8, d["width"] * 0.9), max(3, d["width"] * 0.25), d["height"] * 1.4], "source_op": source}))
            idx += 1
        elif source == "CreateHole":
            calls.append(call(f"{target}-{idx:03d}", "CreateHole", target, {"center": [x, 0, 0], "axis": [0, 0, 1], "radius_mm": max(2, d["width"] * 0.12), "depth_mm": d["height"] * 1.4, "source_op": source}))
            idx += 1
        elif source == "CircularPattern":
            calls.append(call(f"{target}-{idx:03d}", "CircularPattern", target, {"center": [0, 0, d["height"] / 2], "axis": [0, 0, 1], "radius_mm": max(8, d["radius"] * 0.9), "boss_radius_mm": max(1.5, d["radius"] * 0.14), "boss_height_mm": max(3, d["height"] * 0.2), "count": 4, "source_op": source}))
            idx += 1
        elif source == "ApplyFillet":
            calls.append(call(f"{target}-{idx:03d}", "ApplyFillet", target, {"radius_mm": 1.0, "source_op": source}))
            idx += 1
        elif source == "ApplyChamfer":
            calls.append(call(f"{target}-{idx:03d}", "ApplyChamfer", target, {"distance_mm": 0.8, "source_op": source}))
            idx += 1
    return calls


def main() -> None:
    jobs = []
    for row in csv.DictReader((PILOT / "cases.csv").open(encoding="utf-8-sig")):
        run = PILOT / "runs" / row["case_id"] / row["link_id"]
        target = f"{row['case_id']}_{row['link_id']}".replace("-", "_")
        try:
            plan = json.loads((run / "operation_plan.json").read_text(encoding="utf-8"))
            jobs.append({"case_id": row["case_id"], "link_id": row["link_id"], "target_component": target, "status": "READY", "calls": compile_plan(row["case_id"], row["link_id"], row["role"], plan)})
        except Exception as exc:
            jobs.append({"case_id": row["case_id"], "link_id": row["link_id"], "target_component": target, "status": "PLAN_FAILURE", "error": f"{type(exc).__name__}: {exc}"})
    out = PILOT / "fusion_jobs.json"
    out.write_text(json.dumps({"backend": "FusionAPIBackend.v1.execution_compiler", "jobs": jobs}, indent=2), encoding="utf-8")
    print(json.dumps({"jobs": len(jobs), "ready": sum(j["status"] == "READY" for j in jobs), "calls": sum(len(j.get("calls", [])) for j in jobs)}, indent=2))


if __name__ == "__main__":
    main()
