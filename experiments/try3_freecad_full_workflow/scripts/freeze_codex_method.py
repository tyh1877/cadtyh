"""Freeze inputs, method files, and evaluator before formal holdout execution."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from codex_agent_common import EXP, ROOT, RUNS, RESULTS, load_json, sha256, tryset_rows, utc_now, write_csv, write_json


METHOD_FILES = [
    "AMENDMENT_CODEX_AGENT_SUBSTITUTION.md", "codex_agent_v1_config.json",
    "codex_authored/global_visual_observations_v1.json",
    "prompts/mechanical_embodiment_architect.md", "prompts/interface_engineer.md",
    "prompts/part_cad_engineer.md", "prompts/assembly_integrator.md", "prompts/verification_agent.md",
    "schemas/codex_visual_evidence_v1.schema.json", "schemas/codex_mechanical_embodiment_v1.schema.json",
    "schemas/codex_interface_graph_v1.schema.json", "schemas/mechanical_feature_graph_v1.schema.json",
    "schemas/codex_skill_calls_v1.schema.json", "schemas/codex_link_ir_v1.schema.json",
    "scripts/codex_agent_common.py", "scripts/generate_codex_agent_plans.py",
    "scripts/freecad_codex_case_job.py", "scripts/run_codex_freecad_matrix.py",
    "scripts/evaluate_codex_try3.py", "scripts/freecad_codex_backend_smoke.py",
    "scripts/run_codex_backend_smoke.py",
]


def flatten(value: Any):
    if isinstance(value, dict):
        for item in value.values():
            yield from flatten(item)
    elif isinstance(value, list):
        for item in value:
            yield from flatten(item)
    elif isinstance(value, str):
        yield value


def main() -> int:
    input_rows = []
    audit_rows = []
    for row in tryset_rows():
        case_id = row["case_id"]
        packet = ROOT / row["image_text_json"]
        urdf = ROOT / row["sanitized_urdf"]
        image_text = load_json(packet)
        input_rows.extend([
            {"case_id": case_id, "kind": "engineering_text_packet", "name": "image_text_v1", "path": packet.relative_to(ROOT).as_posix(), "bytes": packet.stat().st_size, "sha256": sha256(packet)},
            {"case_id": case_id, "kind": "sanitized_urdf", "name": "kinematic_only", "path": urdf.relative_to(ROOT).as_posix(), "bytes": urdf.stat().st_size, "sha256": sha256(urdf)},
        ])
        for view, path_value in image_text["images"].items():
            path = ROOT / path_value
            input_rows.append({"case_id": case_id, "kind": "image", "name": view, "path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})
        for version in ["V0", "V1", "V2"]:
            plan_root = RUNS / version / case_id
            if not plan_root.exists():
                continue
            violations = []
            for path in plan_root.rglob("*.json"):
                if any(part in {"freecad", "assembly"} for part in path.parts):
                    continue
                for text in flatten(load_json(path)):
                    normalized = text.lower().replace("\\", "/")
                    if any(marker in normalized for marker in ["/meshes/", "kinematic_gt.json", "/urdf/model.urdf", "colored_step_visual_grounding_ablation", "evaluator_masks"]):
                        violations.append(f"{path.relative_to(ROOT).as_posix()}:{text[:100]}")
            audit_rows.append({"case_id": case_id, "version": version, "status": "PASS" if not violations else "FAIL", "forbidden_reference_count": len(violations), "details": " | ".join(violations)})
    method_rows = []
    for relative in METHOD_FILES:
        path = EXP / relative
        method_rows.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path), "role": "evaluator" if relative == "scripts/evaluate_codex_try3.py" else "generation_method"})
    backend = ROOT / "robotcad/backends/freecad_api/FreeCADBackend.py"
    method_rows.append({"path": backend.relative_to(ROOT).as_posix(), "bytes": backend.stat().st_size, "sha256": sha256(backend), "role": "generation_method"})
    write_csv(RESULTS / "codex_agent_v1_input_snapshot.csv", input_rows)
    write_csv(RESULTS / "codex_agent_v1_method_snapshot.csv", method_rows)
    write_csv(RESULTS / "codex_agent_v1_planner_input_audit.csv", audit_rows)
    config = load_json(EXP / "codex_agent_v1_config.json")
    freeze = {"status": "FROZEN" if all(row["status"] == "PASS" for row in audit_rows) else "FAILED", "created_at": utc_now(), "run_id": "codex_agent_v1", "input_records": len(input_rows), "method_records": len(method_rows), "planner_audit_rows": len(audit_rows), "development_cases": config["development_cases"], "holdout_cases": config["holdout_cases"], "method_snapshot_sha256": sha256(RESULTS / "codex_agent_v1_method_snapshot.csv"), "evaluator_sha256": sha256(EXP / "scripts/evaluate_codex_try3.py"), "formal_holdout_started": False}
    write_json(RESULTS / "codex_agent_v1_freeze.json", freeze)
    print(json.dumps(freeze, indent=2))
    return 0 if freeze["status"] == "FROZEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())

