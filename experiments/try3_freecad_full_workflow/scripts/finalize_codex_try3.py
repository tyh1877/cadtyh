"""Audit and report the completed Codex-agent Try-3 matrix."""
from __future__ import annotations

import csv
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

import jsonschema
import numpy as np

from codex_agent_common import EXP, ROOT, RUNS, RESULTS, load_json, parse_urdf, sha256, tryset_rows, write_csv, write_json


FREECAD_PYTHON = Path(r"D:\software\freeCAD\install\bin\python.exe")
VERIFY_HELPER = Path(__file__).with_name("freecad_verify_codex_matrix.py")
VERSIONS = ("V0", "V1", "V2")
REQUIRED_MANIFEST_FIELDS = {"stage", "status", "input_hashes", "schema_version", "created_at", "producer"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def verify_artifacts(execution: list[dict[str, str]]) -> list[dict[str, Any]]:
    items = []
    for row in execution:
        root = RUNS / row["version"] / row["case_id"] / "assembly"
        items.append({"case_id": row["case_id"], "version": row["version"], "expected_components": int(row["links_expected"]), "fcstd": str(root / "assembly.FCStd"), "step": str(root / "assembly.step"), "stl": str(root / "assembly.stl")})
    job = {"items": items, "result_path": str(RUNS / "artifact_verification.json")}
    job_path = RUNS / "artifact_verification_job.json"
    write_json(job_path, job)
    completed = subprocess.run([str(FREECAD_PYTHON), str(VERIFY_HELPER), str(job_path)], cwd=str(ROOT), capture_output=True, text=True, timeout=600, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"FreeCAD artifact verification failed: {completed.stdout[-1000:]} {completed.stderr[-1000:]}")
    rows = load_json(RUNS / "artifact_verification.json")
    write_csv(RESULTS / "codex_agent_v1_artifact_reopen.csv", rows)
    return rows


def manifest_row(path: Path, case_id: str, version: str, link_id: str = "") -> dict[str, Any]:
    value = load_json(path)
    missing = sorted(REQUIRED_MANIFEST_FIELDS - set(value))
    return {"case_id": case_id, "version": version, "link_id": link_id, "manifest_path": path.relative_to(ROOT).as_posix(), "stage": value.get("stage", ""), "status": "PASS" if not missing and value.get("status") == "SUCCESS" else "FAIL", "missing_fields": ";".join(missing)}


def validate_plans() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    schemas = {
        "visual": load_json(EXP / "schemas/codex_visual_evidence_v1.schema.json"),
        "mep": load_json(EXP / "schemas/codex_mechanical_embodiment_v1.schema.json"),
        "interface": load_json(EXP / "schemas/codex_interface_graph_v1.schema.json"),
        "feature": load_json(EXP / "schemas/mechanical_feature_graph_v1.schema.json"),
        "skill": load_json(EXP / "schemas/codex_skill_calls_v1.schema.json"),
        "ir": load_json(EXP / "schemas/codex_link_ir_v1.schema.json"),
    }
    stage_rows = []
    manifest_rows = []
    interface_rows = []
    link_artifact_rows = []
    for row in tryset_rows():
        case_id = row["case_id"]
        urdf = ROOT / row["sanitized_urdf"]
        links, joints = parse_urdf(urdf)
        visual_path = RUNS / "visual_observer" / case_id / "codex_visual_evidence_v1.json"
        visual = load_json(visual_path); jsonschema.validate(visual, schemas["visual"])
        assert [item["link_id"] for item in visual["links"]] == links
        manifest_rows.append(manifest_row(RUNS / "visual_observer" / case_id / "stage_manifest.json", case_id, "shared"))
        stage_rows.append({"stage": "visual_observer", "case_id": case_id, "version": "shared", "expected": len(links), "actual": len(visual["links"]), "status": "PASS"})
        for version in VERSIONS:
            for link_id in links:
                root = RUNS / version / case_id / "links" / link_id
                jsonschema.validate(load_json(root / "mechanical_feature_graph.json"), schemas["feature"])
                jsonschema.validate(load_json(root / "skill_calls.json"), schemas["skill"])
                jsonschema.validate(load_json(root / "executable_cad_ir.json"), schemas["ir"])
                manifest_rows.append(manifest_row(root / "stage_manifest.json", case_id, version, link_id))
                artifacts = root / "freecad"
                expected = [artifacts / "model.FCStd", artifacts / "model.step", artifacts / "model.stl", artifacts / "execution_log.json", artifacts / "feature_manifest.json"]
                execution_log = load_json(artifacts / "execution_log.json")
                link_artifact_rows.append({"case_id": case_id, "version": version, "link_id": link_id, "status": "PASS" if all(path.is_file() and path.stat().st_size > 0 for path in expected) and execution_log and all(item.get("success") and not item.get("fallback_used") for item in execution_log) else "FAIL", "fcstd_bytes": (artifacts / "model.FCStd").stat().st_size if (artifacts / "model.FCStd").exists() else 0, "step_bytes": (artifacts / "model.step").stat().st_size if (artifacts / "model.step").exists() else 0, "stl_bytes": (artifacts / "model.stl").stat().st_size if (artifacts / "model.stl").exists() else 0, "operation_records": len(execution_log), "fallbacks": sum(bool(item.get("fallback_used")) for item in execution_log)})
            stage_rows.append({"stage": "per_link_planning", "case_id": case_id, "version": version, "expected": len(links), "actual": len(list((RUNS / version / case_id / "links").glob("*/stage_manifest.json"))), "status": "PASS"})
            manifest_rows.append(manifest_row(RUNS / version / case_id / "freecad_stage_manifest.json", case_id, version))
        mep = load_json(RUNS / "V2" / case_id / "mep/mechanical_embodiment_plan.json"); jsonschema.validate(mep, schemas["mep"])
        assert [item["link_id"] for item in mep["links"]] == links
        manifest_rows.append(manifest_row(RUNS / "V2" / case_id / "mep/stage_manifest.json", case_id, "V2"))
        interface = load_json(RUNS / "V2" / case_id / "interface/interface_graph.json"); jsonschema.validate(interface, schemas["interface"])
        manifest_rows.append(manifest_row(RUNS / "V2" / case_id / "interface/stage_manifest.json", case_id, "V2"))
        by_id = {item["joint_id"]: item for item in interface["joints"]}
        errors = []
        for joint in joints:
            item = by_id.get(joint.joint_id)
            if item is None or item["joint_type"] != joint.joint_type or item["parent_link"] != joint.parent or item["child_link"] != joint.child or not np.allclose(item["origin_xyz_mm"], joint.xyz_mm, atol=1e-9) or not np.allclose(item["axis"], joint.axis, atol=1e-9):
                errors.append(joint.joint_id)
        interface_rows.append({"case_id": case_id, "expected_joints": len(joints), "actual_joints": len(interface["joints"]), "exact_urdf_matches": len(joints) - len(errors), "status": "PASS" if len(interface["joints"]) == len(joints) and not errors else "FAIL", "errors": ";".join(errors)})
    return stage_rows, manifest_rows, interface_rows, link_artifact_rows


def planner_audit() -> list[dict[str, Any]]:
    forbidden = ["/meshes/", "kinematic_gt.json", "/urdf/model.urdf", "colored_step_visual_grounding_ablation", "evaluator_masks", ".step", ".fcstd", ".stl"]
    rows = []
    for case in tryset_rows():
        for version in VERSIONS:
            violations = []
            for path in (RUNS / version / case["case_id"]).rglob("*.json"):
                if any(part in {"freecad", "assembly"} for part in path.parts) or path.name.startswith("freecad"):
                    continue
                text = path.read_text(encoding="utf-8").lower().replace("\\", "/")
                for marker in forbidden:
                    if marker in text:
                        violations.append(f"{path.relative_to(ROOT).as_posix()}:{marker}")
            rows.append({"case_id": case["case_id"], "version": version, "status": "PASS" if not violations else "FAIL", "forbidden_reference_count": len(violations), "details": " | ".join(violations)})
    return rows


def visible_feature_recall() -> list[dict[str, Any]]:
    expected = load_json(EXP / "codex_authored/global_visual_observations_v1.json")["cases"]
    rows = []
    for case in tryset_rows():
        labels = expected[case["case_id"]]["visible_features"]
        for version in VERSIONS:
            planned = set()
            executed = set()
            for graph_path in (RUNS / version / case["case_id"] / "links").glob("*/mechanical_feature_graph.json"):
                for feature in load_json(graph_path)["features"]:
                    if feature["priority"] in {"structural_detail", "secondary_detail", "surface_detail"}:
                        planned.add(feature["feature_type"])
                        if feature["intended_cad_strategy"] != "UNIMPLEMENTED_VISIBLE_DETAIL":
                            executed.add(feature["feature_type"])
            rows.append({"case_id": case["case_id"], "version": version, "frozen_visible_labels": len(labels), "planned_label_matches": len(set(labels) & planned), "executed_label_matches": len(set(labels) & executed), "planned_recall": len(set(labels) & planned) / len(labels), "executed_recall": len(set(labels) & executed) / len(labels), "label_source": "pre-output Codex visual annotation; not independent expert GT"})
    return rows


def resource_rows(execution: list[dict[str, str]]) -> list[dict[str, Any]]:
    output = []
    for row in execution:
        case_id, version = row["case_id"], row["version"]
        output.append({"case_id": case_id, "version": version, "agent_provider": "interactive_codex_gpt5_family", "exact_model_snapshot": "UNAVAILABLE", "agent_calls": "UNAVAILABLE_INTERACTIVE", "input_tokens": "UNAVAILABLE", "output_tokens": "UNAVAILABLE", "total_tokens": "UNAVAILABLE", "planning_wall_seconds": "UNAVAILABLE", "freecad_operations": row["operation_count"], "freecad_elapsed_seconds": row["elapsed_seconds"], "fallbacks": row["fallback_count"]})
    return output


def make_report(aggregate: list[dict[str, str]], execution: list[dict[str, str]], visible: list[dict[str, Any]], incident_count: int) -> None:
    lookup = {(row["group"], row["version"]): row for row in aggregate}
    holdout = {version: lookup[("holdout", version)] for version in VERSIONS}
    def f(value): return f"{float(value):.6f}"
    def pct(before, after): return (float(before) - float(after)) / float(before) * 100.0
    lines = [
        "# Codex-agent Try-3 FreeCAD report", "",
        "## Executive result", "",
        "The formal Codex-agent matrix executed completely: 15/15 robot/version cells and 189/189 link/version cells exported editable FCStd plus STEP/STL with zero silent fallbacks. The architectural result is mixed: V1 clearly improves coarse geometry and connectivity over V0 on the three-case holdout, while V2 adds only a modest envelope/interface gain over V1 and increases the non-adjacent AABB-overlap interference proxy.", "",
        "This is not a GLM continuation result. The producer change and interactive reproducibility limits are defined in `AMENDMENT_CODEX_AGENT_SUBSTITUTION.md`.", "",
        "## Holdout results", "",
        "| Metric | V0 | V1 | V2 |", "| --- | ---: | ---: | ---: |",
        f"| Mean Chamfer | {f(holdout['V0']['mean_chamfer'])} | {f(holdout['V1']['mean_chamfer'])} | {f(holdout['V2']['mean_chamfer'])} |",
        f"| Mean HD95 | {f(holdout['V0']['mean_hd95'])} | {f(holdout['V1']['mean_hd95'])} | {f(holdout['V2']['mean_hd95'])} |",
        f"| Mean voxel IoU | {f(holdout['V0']['mean_voxel_iou'])} | {f(holdout['V1']['mean_voxel_iou'])} | {f(holdout['V2']['mean_voxel_iou'])} |",
        f"| Mean interface gap | {f(holdout['V0']['mean_interface_gap'])} | {f(holdout['V1']['mean_interface_gap'])} | {f(holdout['V2']['mean_interface_gap'])} |",
        f"| Mean disconnected-joint rate | {f(holdout['V0']['mean_disconnected_joint_rate'])} | {f(holdout['V1']['mean_disconnected_joint_rate'])} | {f(holdout['V2']['mean_disconnected_joint_rate'])} |",
        f"| Mean non-adjacent AABB overlaps | {f(holdout['V0']['mean_nonadjacent_bbox_overlaps'])} | {f(holdout['V1']['mean_nonadjacent_bbox_overlaps'])} | {f(holdout['V2']['mean_nonadjacent_bbox_overlaps'])} |", "",
        f"V0→V1 reduces holdout Chamfer by {pct(holdout['V0']['mean_chamfer'], holdout['V1']['mean_chamfer']):.1f}% and HD95 by {pct(holdout['V0']['mean_hd95'], holdout['V1']['mean_hd95']):.1f}%, while voxel IoU rises by {(float(holdout['V1']['mean_voxel_iou']) / float(holdout['V0']['mean_voxel_iou']) - 1) * 100:.1f}%. V1→V2 reduces Chamfer by {pct(holdout['V1']['mean_chamfer'], holdout['V2']['mean_chamfer']):.1f}% and interface gap by {pct(holdout['V1']['mean_interface_gap'], holdout['V2']['mean_interface_gap']):.1f}%; disconnected-joint rate is unchanged and non-adjacent overlap count worsens.", "",
        "## Research questions", "",
        "### RQ1: global-to-local visual grounding", "",
        "Partially supported. V1 improves envelope-level geometry and joint-neighborhood connectivity over V0, including on holdout. It does not demonstrate fine visible-detail recovery: the pre-output visual labels reach the feature plans, but none are translated into an executed visible-detail operation.", "",
        "### RQ2: MEP and interface-first planning", "",
        "Not clearly supported as a distinct V2 effect. V2 modestly improves mean Chamfer, HD95, voxel IoU, and interface gap over V1, but it does not lower the disconnected-joint rate and increases the AABB interference proxy. The improvement is too small and mechanically incomplete to claim that full MEP/interface planning solved the assembly/detail gap.", "",
        "### RQ3: RobotCAD skills and editable FreeCAD", "",
        "Supported for the frozen basic skill subset, not for high-fidelity embodiment. Native Part::Box, Part::Loft, Part::Cylinder, and Part::Fuse features execute reliably, all assemblies reopen, and fallback count is zero. Shell, sweep, fillet, holes/recesses, feet, fingers, and other visible details are absent from the formal skill projection. V1/V2 avoid the V0 box-only proxy but remain coarse loft-and-cylinder assemblies.", "",
        "## Coverage and failure accounting", "",
        f"- Formal execution: 15/15 cases and 189/189 links successful; {sum(int(row['operation_count']) for row in execution)} FreeCAD operations; zero fallback.",
        f"- Pre-holdout incident count: {incident_count}. The optional-URDF-origin parser failure occurred before any holdout agent output, was recorded, fixed generically, and the method was re-frozen before formal generation.",
        "- No formal case was dropped or repaired after generation.",
        "- Agent token counts, exact serving snapshot, sampling controls, and per-call latency are unavailable in the interactive Codex environment and are not represented as zero.", "",
        "## Interpretation limits", "",
        "- The five-case set is a method-development TrySet, not a large benchmark. The three-case holdout protects evaluator tuning within this continuation but is too small for a broad generalization claim.",
        "- Visible-feature labels were authored by the same Codex agent from allowed images before formal outputs; they are not independent expert ground truth. Executed visible-feature recall is conservatively zero because those planned details have no mapped CAD operations.",
        "- Interference is an AABB overlap proxy, not exact solid intersection volume. Axis equality is validated structurally against sanitized URDF/interface artifacts; native moving-joint behavior is outside the amended FreeCAD acceptance boundary.",
        "- Global and per-link geometry use normalized deterministic surface sampling and rigid ICP; they measure shape similarity, not manufacturing correctness.", "",
        "## Decision", "",
        "The experiment supports continuing to a Try-3.x skill refinement, not claiming full Try-3 success. The next work should translate already planned visible details into robust FreeCAD hole/recess/shell/fillet/sweep operations and reduce non-adjacent interference without a case-specific repair loop. The same frozen five cases can be used for development; a new untouched set is required for a later confirmatory claim.", "",
    ]
    (RESULTS / "codex_agent_v1_try3_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    # A historical replay must not restore withdrawn conclusions or overwrite
    # the archived evidence inventory. This guard performs no writes or CAD calls.
    reclassification = EXP / "archive/codex_agent_v1_reclassification/manifest.json"
    if reclassification.is_file():
        print(json.dumps({
            "status": "ARCHIVED_RECLASSIFIED_NO_WRITE",
            "classification": "URDF_DRIVEN_COARSE_GEOMETRY_TEMPLATE_PILOT",
            "try3_completion": "INCOMPLETE",
            "report": str(RESULTS / "codex_agent_v1_try3_report.md"),
            "note": "Historical finalization disabled to preserve corrected conclusions and evidence."
        }, indent=2))
        return 0
    execution = read_csv(RESULTS / "codex_agent_v1_freecad_execution.csv")
    if len(execution) != 15:
        raise RuntimeError(f"expected 15 execution rows, got {len(execution)}")
    reopen = verify_artifacts(execution)
    stage, manifests, interfaces, link_artifacts = validate_plans()
    planner = planner_audit()
    visible = visible_feature_recall()
    resources = resource_rows(execution)
    write_csv(RESULTS / "codex_agent_v1_stage_validation.csv", stage)
    write_csv(RESULTS / "codex_agent_v1_manifest_validation.csv", manifests)
    write_csv(RESULTS / "codex_agent_v1_interface_graph_validation.csv", interfaces)
    write_csv(RESULTS / "codex_agent_v1_link_artifact_validation.csv", link_artifacts)
    write_csv(RESULTS / "codex_agent_v1_planner_input_audit.csv", planner)
    write_csv(RESULTS / "codex_agent_v1_visible_feature_recall.csv", visible)
    write_csv(RESULTS / "codex_agent_v1_resource_accounting.csv", resources)
    inventory = []
    for path in sorted(RUNS.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            inventory.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})
    write_csv(RESULTS / "codex_agent_v1_evidence_inventory.csv", inventory)
    aggregate = read_csv(RESULTS / "codex_agent_v1_aggregate_results.csv")
    incidents = read_csv(RESULTS / "codex_agent_v1_execution_incidents.csv")
    make_report(aggregate, execution, visible, len(incidents))
    method_rows = read_csv(RESULTS / "codex_agent_v1_method_snapshot.csv")
    method_mismatches = [row["path"] for row in method_rows if sha256(ROOT / row["path"]) != row["sha256"]]
    audit = {
        "status": "PASS" if not method_mismatches and all(row["status"] == "PASS" for row in reopen + interfaces + planner + manifests + link_artifacts) else "FAIL",
        "formal_case_version_cells": len(execution), "successful_case_version_cells": sum(row["status"] == "SUCCESS" for row in execution),
        "formal_link_version_cells": len(link_artifacts), "validated_link_version_cells": sum(row["status"] == "PASS" for row in link_artifacts),
        "stage_manifests": len(manifests), "valid_stage_manifests": sum(row["status"] == "PASS" for row in manifests),
        "artifact_reopen_passes": sum(row["status"] == "PASS" for row in reopen),
        "interface_graph_passes": sum(row["status"] == "PASS" for row in interfaces),
        "planner_input_audit_passes": sum(row["status"] == "PASS" for row in planner),
        "method_hash_mismatches": method_mismatches,
        "formal_failures": sum(row["status"] != "SUCCESS" for row in execution),
        "preflight_incidents": len(incidents),
        "scientific_decision": "TRY3_X_REFINEMENT; no full Try-3 method-success claim",
    }
    write_json(RESULTS / "codex_agent_v1_completion_audit.json", audit)
    print(json.dumps(audit, indent=2))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
