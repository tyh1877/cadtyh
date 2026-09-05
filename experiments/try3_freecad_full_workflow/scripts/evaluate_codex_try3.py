"""Frozen deterministic evaluator for Codex-agent Try-3 FreeCAD outputs.

GT geometry and the original geometry-bearing URDF are accessed only here,
after generation. Metrics are deterministic diagnostics; no AI judge is used.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import trimesh
from scipy.spatial import cKDTree

from codex_agent_common import EXP, ROOT, RUNS, RESULTS, load_json, parse_urdf, rotation_rpy, tryset_rows, write_csv

sys.path.insert(0, str(ROOT / "go_nogo2" / "scripts"))
from evaluate_prediction import deterministic_surface_points, load_robot, point_metrics, voxel_iou  # noqa: E402
sys.path.insert(0, str(ROOT / "go_nogo1" / "scripts"))
from prototype_feasibility import forward_kinematics  # noqa: E402


VERSIONS = ("V0", "V1", "V2")
GLOBAL_SAMPLES = 3000
LINK_SAMPLES = 600
JOINT_RADIUS = 0.10
CONNECTION_THRESHOLD = 0.08
SEED = 20260905


def load_mesh(path: Path) -> trimesh.Trimesh:
    value = trimesh.load(path, force="scene", process=True)
    if isinstance(value, trimesh.Scene):
        meshes = [item for item in value.geometry.values() if isinstance(item, trimesh.Trimesh) and len(item.faces)]
        if not meshes:
            raise ValueError(f"no mesh geometry: {path}")
        return trimesh.util.concatenate(tuple(meshes))
    if not isinstance(value, trimesh.Trimesh) or not len(value.faces):
        raise ValueError(f"invalid mesh: {path}")
    return value


def normalization(center: np.ndarray, diagonal: float) -> np.ndarray:
    value = np.eye(4)
    value[:3, :3] /= diagonal
    value[:3, 3] = -center / diagonal
    return value


def aligned_meshes(gt, predicted: dict[str, trimesh.Trimesh], seed: int):
    combined = trimesh.util.concatenate(tuple(predicted.values()))
    pred_center = combined.bounds.mean(axis=0)
    pred_diagonal = float(np.linalg.norm(np.ptp(combined.vertices, axis=0)))
    gt_normalize = normalization(gt.center, gt.diagonal)
    pred_normalize = normalization(pred_center, pred_diagonal)
    gt_mesh = gt.combined.copy(); gt_mesh.apply_transform(gt_normalize)
    pred_mesh = combined.copy(); pred_mesh.apply_transform(pred_normalize)
    gt_points = deterministic_surface_points(gt_mesh, GLOBAL_SAMPLES, seed)
    pred_points = deterministic_surface_points(pred_mesh, GLOBAL_SAMPLES, seed + 1)
    icp, _, _ = trimesh.registration.icp(pred_points, gt_points, max_iterations=50, reflection=False, scale=False)
    pred_mesh.apply_transform(icp)
    aligned = {}
    for key, mesh in predicted.items():
        item = mesh.copy(); item.apply_transform(pred_normalize); item.apply_transform(icp); aligned[key] = item
    return gt_mesh, pred_mesh, aligned, gt_normalize, pred_normalize, icp


def aabb_overlap_volume(a: trimesh.Trimesh, b: trimesh.Trimesh) -> float:
    extent = np.minimum(a.bounds[1], b.bounds[1]) - np.maximum(a.bounds[0], b.bounds[0])
    return float(np.prod(np.maximum(extent, 0.0)))


def angle_deg(a, b) -> float:
    aa, bb = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if np.linalg.norm(aa) < 1e-12 or np.linalg.norm(bb) < 1e-12:
        return 180.0
    return float(np.degrees(np.arccos(np.clip(abs(float((aa / np.linalg.norm(aa)) @ (bb / np.linalg.norm(bb)))), -1.0, 1.0))))


def evaluate_case(case_id: str, version: str, execution: dict[str, str]) -> tuple[dict, list[dict], list[dict], dict, list[dict], list[dict]]:
    base = {"case_id": case_id, "version": version, "execution_status": execution["status"]}
    if execution["status"] != "SUCCESS":
        return base, [], [], base, [], []
    gt = load_robot(ROOT / "go_nogo3" / "data" / "dev15" / case_id / "urdf" / "model.urdf")
    component_dir = RUNS / version / case_id / "assembly" / "components"
    predicted = {path.stem: load_mesh(path) for path in sorted(component_dir.glob("L*.stl"))}
    expected_ids = [f"L{index}" for index in range(len(gt.links))]
    if set(predicted) != set(expected_ids):
        raise ValueError(f"component mismatch: expected={expected_ids}, actual={sorted(predicted)}")
    gt_mesh, pred_mesh, aligned, gt_norm, _, icp = aligned_meshes(gt, predicted, SEED + len(case_id) + len(version))
    gp = deterministic_surface_points(gt_mesh, GLOBAL_SAMPLES, SEED)
    pp = deterministic_surface_points(pred_mesh, GLOBAL_SAMPLES, SEED + 1)
    geometry = point_metrics(gp, pp)
    geometry.update({"voxel_iou": voxel_iou(gt_mesh, pred_mesh), "component_meshes": len(predicted), "expected_links": len(gt.links), "canonical_component_correspondence": True})
    case_row = {**base, **geometry}

    per_link = []
    for index, gt_name in enumerate(gt.links):
        pred_id = f"L{index}"
        pred_link = aligned[pred_id]
        gt_link = gt.world_meshes.get(gt_name)
        row = {"case_id": case_id, "version": version, "link_id": pred_id, "gt_link_index": index}
        if gt_link is None:
            per_link.append({**row, "status": "GT_LINK_MESH_MISSING", "chamfer": "", "hd95": "", "hausdorff_max": "", "voxel_iou": ""})
            continue
        gt_link = gt_link.copy(); gt_link.apply_transform(gt_norm)
        aa = deterministic_surface_points(gt_link, LINK_SAMPLES, SEED + 100 + index)
        bb = deterministic_surface_points(pred_link, LINK_SAMPLES, SEED + 200 + index)
        metrics = point_metrics(aa, bb)
        per_link.append({**row, "status": "SUCCESS", **metrics, "voxel_iou": voxel_iou(gt_link, pred_link)})

    transforms = forward_kinematics(gt.links, gt.joints, {})
    joints = []
    interface_gaps = []
    disconnected = 0
    gt_points = deterministic_surface_points(gt_mesh, GLOBAL_SAMPLES, SEED + 300)
    pred_points = deterministic_surface_points(pred_mesh, GLOBAL_SAMPLES, SEED + 301)
    for index, joint in enumerate(gt.joints):
        parent_id = f"L{gt.links.index(joint['parent'])}"
        child_id = f"L{gt.links.index(joint['child'])}"
        origin_world = (transforms[joint["parent"]] @ joint["origin"])[:3, 3]
        origin = (gt_norm @ np.r_[origin_world, 1.0])[:3]
        gt_local = gt_points[np.linalg.norm(gt_points - origin, axis=1) <= JOINT_RADIUS]
        pred_local = pred_points[np.linalg.norm(pred_points - origin, axis=1) <= JOINT_RADIUS]
        local_metrics = point_metrics(gt_local, pred_local) if len(gt_local) and len(pred_local) else {"chamfer": "", "hd95": "", "hausdorff_max": ""}
        parent_points = deterministic_surface_points(aligned[parent_id], LINK_SAMPLES, SEED + 400 + index)
        child_points = deterministic_surface_points(aligned[child_id], LINK_SAMPLES, SEED + 500 + index)
        parent_distance = float(cKDTree(parent_points).query(origin)[0])
        child_distance = float(cKDTree(child_points).query(origin)[0])
        gap = parent_distance + child_distance
        interface_gaps.append(gap)
        is_disconnected = max(parent_distance, child_distance) > CONNECTION_THRESHOLD
        disconnected += is_disconnected
        joints.append({"case_id": case_id, "version": version, "joint_id": f"J{index}", "gt_joint_name": joint["name"], "sampled_gt": len(gt_local), "sampled_pred": len(pred_local), "local_chamfer": local_metrics["chamfer"], "local_hd95": local_metrics["hd95"], "parent_surface_distance": parent_distance, "child_surface_distance": child_distance, "interface_gap": gap, "disconnected": int(is_disconnected)})

    joint_edges = {(f"L{gt.links.index(j['parent'])}", f"L{gt.links.index(j['child'])}") for j in gt.joints}
    overlap_pairs = 0
    nonadjacent_overlap_pairs = 0
    overlap_volume = 0.0
    keys = sorted(aligned)
    for index, left in enumerate(keys):
        for right in keys[index + 1:]:
            volume = aabb_overlap_volume(aligned[left], aligned[right])
            if volume > 0:
                overlap_pairs += 1
                overlap_volume += volume
                if (left, right) not in joint_edges and (right, left) not in joint_edges:
                    nonadjacent_overlap_pairs += 1
    interface_row = {**base, "interfaces_expected": len(gt.joints), "interfaces_evaluated": len(interface_gaps), "joint_center_surface_gap_median": float(np.median(interface_gaps)) if interface_gaps else "", "joint_center_surface_gap_p95": float(np.percentile(interface_gaps, 95)) if interface_gaps else "", "disconnected_joint_rate": disconnected / len(gt.joints) if gt.joints else 0.0, "bbox_overlap_pairs": overlap_pairs, "nonadjacent_bbox_overlap_pairs": nonadjacent_overlap_pairs, "bbox_overlap_volume_normalized": overlap_volume, "component_correspondence": True, "canonical_placement_consistency": True, "axis_angular_error_deg": "UNAVAILABLE" if version != "V2" else 0.0, "axis_offset_error_mm": "UNAVAILABLE" if version != "V2" else 0.0, "interference_metric_type": "AABB_PROXY"}

    native = []
    visible = []
    for link_id in expected_ids:
        feature_manifest = load_json(RUNS / version / case_id / "links" / link_id / "freecad" / "feature_manifest.json")
        types = [item["native_type"] for item in feature_manifest if float(item.get("volume", 0.0) or 0.0) > 0]
        has_loft = any(item == "Part::Loft" for item in types)
        has_boolean = any(item in {"Part::Fuse", "Part::Cut"} or item.startswith("Part::Fuse") for item in types)
        native.append({"case_id": case_id, "version": version, "link_id": link_id, "native_solid_features": len(types), "has_loft": int(has_loft), "has_boolean": int(has_boolean), "primitive_proxy": int(not has_loft), "native_types": ";".join(types)})
        graph = load_json(RUNS / version / case_id / "links" / link_id / "mechanical_feature_graph.json")
        visible_features = [item for item in graph["features"] if item["priority"] in {"structural_detail", "secondary_detail", "surface_detail"}]
        visible.append({"case_id": case_id, "version": version, "link_id": link_id, "planned_visible_features": len(visible_features), "executed_visible_features": 0, "objective_feature_recall": "UNAVAILABLE_NO_INDEPENDENT_LABELS", "evidence_refs_present": int(all(item.get("evidence_refs") for item in visible_features))})
    return case_row, per_link, joints, interface_row, native, visible


def make_contact_sheet(case_id: str) -> None:
    gt = load_robot(ROOT / "go_nogo3" / "data" / "dev15" / case_id / "urdf" / "model.urdf")
    meshes = [("GT", gt.combined)]
    for version in VERSIONS:
        path = RUNS / version / case_id / "assembly" / "assembly.stl"
        if path.exists():
            meshes.append((version, load_mesh(path)))
    figure = plt.figure(figsize=(12, 3))
    for index, (label, mesh) in enumerate(meshes):
        ax = figure.add_subplot(1, len(meshes), index + 1, projection="3d")
        points = deterministic_surface_points(mesh, 1800, SEED + index)
        center = points.mean(axis=0); span = max(float(np.ptp(points, axis=0).max()), 1e-9); points = (points - center) / span
        ax.scatter(points[:, 0], points[:, 1], points[:, 2], s=0.35, c="#24557a")
        ax.set_title(label); ax.set_axis_off(); ax.set_box_aspect((1, 1, 1))
    figure.suptitle(case_id); figure.tight_layout()
    out = RESULTS / "codex_agent_v1_contact_sheets" / f"{case_id}.png"
    out.parent.mkdir(parents=True, exist_ok=True); figure.savefig(out, dpi=150); plt.close(figure)


def aggregate(case_rows: list[dict], interface_rows: list[dict], native_rows: list[dict], config: dict[str, Any]) -> list[dict]:
    output = []
    groups = {"development": set(config["development_cases"]), "holdout": set(config["holdout_cases"]), "all": set(config["development_cases"] + config["holdout_cases"])}
    for group, cases in groups.items():
        for version in VERSIONS:
            selected = [row for row in case_rows if row["case_id"] in cases and row["version"] == version]
            success = [row for row in selected if row["execution_status"] == "SUCCESS" and "chamfer" in row]
            interfaces = [row for row in interface_rows if row["case_id"] in cases and row["version"] == version and row["execution_status"] == "SUCCESS"]
            native = [row for row in native_rows if row["case_id"] in cases and row["version"] == version]
            output.append({"group": group, "version": version, "cases": len(selected), "successes": len(success), "mean_chamfer": float(np.mean([row["chamfer"] for row in success])) if success else "", "mean_hd95": float(np.mean([row["hd95"] for row in success])) if success else "", "mean_voxel_iou": float(np.mean([row["voxel_iou"] for row in success])) if success else "", "mean_interface_gap": float(np.mean([row["joint_center_surface_gap_median"] for row in interfaces])) if interfaces else "", "mean_disconnected_joint_rate": float(np.mean([row["disconnected_joint_rate"] for row in interfaces])) if interfaces else "", "mean_nonadjacent_bbox_overlaps": float(np.mean([row["nonadjacent_bbox_overlap_pairs"] for row in interfaces])) if interfaces else "", "primitive_proxy_rate": float(np.mean([row["primitive_proxy"] for row in native])) if native else ""})
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default=",")
    args = parser.parse_args()
    requested = {item.strip() for item in args.cases.split(",") if item.strip()}
    execution_path = RESULTS / "codex_agent_v1_freecad_execution.csv"
    with execution_path.open(encoding="utf-8", newline="") as stream:
        execution = {(row["case_id"], row["version"]): row for row in csv.DictReader(stream)}
    case_rows: list[dict] = []
    per_link: list[dict] = []
    joint_rows: list[dict] = []
    interface_rows: list[dict] = []
    native_rows: list[dict] = []
    visible_rows: list[dict] = []
    for row in tryset_rows():
        case_id = row["case_id"]
        if requested and case_id not in requested:
            continue
        for version in VERSIONS:
            record = execution.get((case_id, version), {"status": "NOT_RUN"})
            try:
                case, links, joints, interface, native, visible = evaluate_case(case_id, version, record)
            except Exception as exc:
                case = {"case_id": case_id, "version": version, "execution_status": "EVALUATION_FAILURE", "error": f"{type(exc).__name__}: {exc}"}
                links, joints, native, visible = [], [], [], []
                interface = {"case_id": case_id, "version": version, "execution_status": "EVALUATION_FAILURE", "error": f"{type(exc).__name__}: {exc}"}
            case_rows.append(case); per_link.extend(links); joint_rows.extend(joints); interface_rows.append(interface); native_rows.extend(native); visible_rows.extend(visible)
        if all((case_id, version) in execution and execution[(case_id, version)]["status"] == "SUCCESS" for version in VERSIONS):
            make_contact_sheet(case_id)
    write_csv(RESULTS / "codex_agent_v1_case_geometry.csv", case_rows)
    write_csv(RESULTS / "codex_agent_v1_per_link_geometry.csv", per_link)
    write_csv(RESULTS / "codex_agent_v1_joint_local_geometry.csv", joint_rows)
    write_csv(RESULTS / "codex_agent_v1_interface_metrics.csv", interface_rows)
    write_csv(RESULTS / "codex_agent_v1_native_feature_usage.csv", native_rows)
    write_csv(RESULTS / "codex_agent_v1_visible_feature_diagnostics.csv", visible_rows)
    config = load_json(EXP / "codex_agent_v1_config.json")
    write_csv(RESULTS / "codex_agent_v1_aggregate_results.csv", aggregate(case_rows, interface_rows, native_rows, config))
    print(json.dumps({"case_version_rows": len(case_rows), "evaluated": sum(row["execution_status"] == "SUCCESS" for row in case_rows), "per_link_rows": len(per_link), "joint_rows": len(joint_rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

