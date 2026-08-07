"""Deterministically evaluate one common-contract robot prediction."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import trimesh
from scipy.optimize import linear_sum_assignment
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

REPO_ROOT = Path(__file__).resolve().parents[2]
GO1_SCRIPTS = REPO_ROOT / "go_nogo1" / "scripts"
sys.path.insert(0, str(GO1_SCRIPTS))

from build_inventory import mesh_index  # noqa: E402
from prototype_feasibility import (  # noqa: E402
    forward_kinematics,
    load_link_meshes,
    parse_model,
    world_meshes,
)

SAMPLE_COUNT = 3000
PER_LINK_SAMPLES = 600
VOXEL_PITCH = 0.05
PART_MATCH_MAX_COST = 0.35


@dataclass
class Robot:
    urdf: Path
    links: list[str]
    joints: list[dict]
    local_meshes: dict[str, list[trimesh.Trimesh]]
    world_meshes: dict[str, trimesh.Trimesh]
    combined: trimesh.Trimesh
    diagonal: float
    center: np.ndarray
    root: str
    depth: dict[str, int]


def load_robot(urdf: Path) -> Robot:
    urdf = urdf.resolve()
    root_node, links, joints = parse_model(urdf)
    transforms = forward_kinematics(links, joints, {})
    data_root = urdf.parent.parent
    _, by_name = mesh_index(data_root)
    local_meshes, references, resolved, failures = load_link_meshes(
        root_node, urdf, data_root, by_name
    )
    if failures or references == 0 or resolved != references:
        raise ValueError(f"mesh loading incomplete: {resolved}/{references}; {failures}")
    mesh_list, by_link = world_meshes(local_meshes, transforms)
    if not mesh_list:
        raise ValueError("no visual meshes")
    combined = trimesh.util.concatenate(mesh_list)
    center = combined.bounds.mean(axis=0)
    diagonal = float(np.linalg.norm(np.ptp(combined.vertices, axis=0)))
    if not np.isfinite(diagonal) or diagonal <= 0:
        raise ValueError("invalid robot diagonal")
    children, child_set = defaultdict(list), set()
    for joint in joints:
        children[joint["parent"]].append(joint["child"])
        child_set.add(joint["child"])
    roots = [link for link in links if link not in child_set]
    if len(roots) != 1:
        raise ValueError("robot must have exactly one root")
    depth = {roots[0]: 0}
    queue = deque([roots[0]])
    while queue:
        parent = queue.popleft()
        for child in children[parent]:
            depth[child] = depth[parent] + 1
            queue.append(child)
    return Robot(urdf, links, joints, local_meshes, by_link, combined,
                 diagonal, center, roots[0], depth)


def deterministic_surface_points(mesh: trimesh.Trimesh, count: int, seed: int) -> np.ndarray:
    triangles = np.asarray(mesh.triangles, dtype=float)
    areas = np.asarray(mesh.area_faces, dtype=float)
    valid = np.isfinite(areas) & (areas > 0)
    triangles, areas = triangles[valid], areas[valid]
    if len(triangles) == 0:
        raise ValueError("mesh has no positive-area triangles")
    rng = np.random.default_rng(seed)
    chosen = rng.choice(len(triangles), size=count, replace=True, p=areas / areas.sum())
    uv = rng.random((count, 2))
    fold = uv.sum(axis=1) > 1
    uv[fold] = 1 - uv[fold]
    tri = triangles[chosen]
    return tri[:, 0] + uv[:, :1] * (tri[:, 1] - tri[:, 0]) + uv[:, 1:] * (tri[:, 2] - tri[:, 0])


def normalized_mesh(robot: Robot) -> trimesh.Trimesh:
    mesh = robot.combined.copy()
    mesh.vertices = (mesh.vertices - robot.center) / robot.diagonal
    return mesh


def align_prediction(gt: Robot, pred: Robot, seed: int):
    gt_mesh, pred_mesh = normalized_mesh(gt), normalized_mesh(pred)
    gt_points = deterministic_surface_points(gt_mesh, SAMPLE_COUNT, seed)
    # Use the same deterministic variates on both surfaces.  This gives an
    # exact zero-distance oracle when prediction and GT are identical while
    # remaining deterministic for non-identical meshes.
    pred_points = deterministic_surface_points(pred_mesh, SAMPLE_COUNT, seed)
    matrix, transformed, _ = trimesh.registration.icp(
        pred_points, gt_points, max_iterations=50, reflection=False, scale=False
    )
    aligned_mesh = pred_mesh.copy()
    aligned_mesh.apply_transform(matrix)
    return gt_mesh, aligned_mesh, gt_points, np.asarray(transformed), np.asarray(matrix)


def point_metrics(a: np.ndarray, b: np.ndarray) -> dict:
    a_to_b = cKDTree(b).query(a, workers=1)[0]
    b_to_a = cKDTree(a).query(b, workers=1)[0]
    distances = np.concatenate([a_to_b, b_to_a])
    return {
        "chamfer": float((np.mean(a_to_b ** 2) + np.mean(b_to_a ** 2)) / 2),
        "hd95": float(np.percentile(distances, 95)),
        "hausdorff_max": float(distances.max()),
    }


def voxel_keys(mesh: trimesh.Trimesh, pitch: float) -> set[tuple[int, int, int]]:
    voxels = mesh.voxelized(pitch=pitch).fill()
    points = np.asarray(voxels.points)
    if len(points) == 0:
        return set()
    indices = np.floor((points + 2.0) / pitch + 0.5).astype(np.int32)
    return {tuple(row) for row in indices}


def voxel_iou(gt_mesh: trimesh.Trimesh, pred_mesh: trimesh.Trimesh) -> float:
    a, b = voxel_keys(gt_mesh, VOXEL_PITCH), voxel_keys(pred_mesh, VOXEL_PITCH)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def link_points(robot: Robot, link: str, seed: int) -> np.ndarray | None:
    mesh = robot.world_meshes.get(link)
    if mesh is None:
        return None
    points = deterministic_surface_points(mesh, PER_LINK_SAMPLES, seed)
    center = points.mean(axis=0)
    scale = max(float(np.linalg.norm(np.ptp(points, axis=0))), 1e-12)
    return (points - center) / scale


def globally_normalized_link_mesh(robot: Robot, link: str) -> trimesh.Trimesh | None:
    source = robot.world_meshes.get(link)
    if source is None:
        return None
    mesh = source.copy()
    mesh.vertices = (mesh.vertices - robot.center) / robot.diagonal
    return mesh


def has_curved_surface(mesh: trimesh.Trimesh) -> bool:
    normals = np.asarray(mesh.face_normals)
    if len(normals) == 0:
        return False
    return len(np.unique(np.round(normals, 1), axis=0)) >= 20


def joint_by_child(robot: Robot) -> dict[str, dict]:
    return {joint["child"]: joint for joint in robot.joints}


def match_parts(gt: Robot, pred: Robot, seed: int):
    matches = {}
    remaining_gt, remaining_pred = set(gt.links), set(pred.links)
    for name in sorted(remaining_gt & remaining_pred):
        matches[name] = name
    remaining_gt -= set(matches.values())
    remaining_pred -= set(matches)
    gt_items = sorted(remaining_gt)
    pred_items = sorted(remaining_pred)
    if gt_items and pred_items:
        gt_child, pred_child = joint_by_child(gt), joint_by_child(pred)
        costs = np.full((len(pred_items), len(gt_items)), 1.0)
        gt_points = {name: link_points(gt, name, seed + i) for i, name in enumerate(gt_items)}
        pred_points = {name: link_points(pred, name, seed + 100 + i) for i, name in enumerate(pred_items)}
        for i, p_name in enumerate(pred_items):
            for j, g_name in enumerate(gt_items):
                p_pts, g_pts = pred_points[p_name], gt_points[g_name]
                if p_pts is None or g_pts is None:
                    continue
                shape = math.sqrt(max(point_metrics(p_pts, g_pts)["chamfer"], 0.0))
                depth = 0.08 * abs(pred.depth.get(p_name, 0) - gt.depth.get(g_name, 0))
                p_type = pred_child.get(p_name, {}).get("type", "root")
                g_type = gt_child.get(g_name, {}).get("type", "root")
                joint_penalty = 0.12 if normalize_joint_type(p_type) != normalize_joint_type(g_type) else 0.0
                costs[i, j] = shape + depth + joint_penalty
        rows, cols = linear_sum_assignment(costs)
        for i, j in zip(rows, cols):
            if costs[i, j] <= PART_MATCH_MAX_COST:
                matches[pred_items[i]] = gt_items[j]
    return matches


def precision_recall_f1(tp: int, predicted: int, actual: int) -> tuple[float, float, float]:
    precision = tp / predicted if predicted else 0.0
    recall = tp / actual if actual else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def edge_set(robot: Robot) -> set[tuple[str, str]]:
    return {(joint["parent"], joint["child"]) for joint in robot.joints}


def normalize_joint_type(value: str) -> str:
    return "revolute" if value == "continuous" else value


def angle_error_degrees(a, b) -> float:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    a, b = a / np.linalg.norm(a), b / np.linalg.norm(b)
    return float(np.degrees(np.arccos(np.clip(abs(float(a @ b)), -1.0, 1.0))))


def rotation_error_degrees(a: np.ndarray, b: np.ndarray) -> float:
    relative = a[:3, :3].T @ b[:3, :3]
    return float(np.degrees(Rotation.from_matrix(relative).magnitude()))


def q_for_fraction(joints: list[dict], fraction: float) -> dict[str, float]:
    values = {}
    for joint in joints:
        kind = joint["type"]
        if kind == "continuous":
            values[joint["name"]] = fraction * math.pi
        elif kind in {"revolute", "prismatic"}:
            lower, upper = joint["lower"], joint["upper"]
            values[joint["name"]] = lower + (fraction + 1) * 0.5 * (upper - lower)
    return values


def evaluate(gt: Robot, pred: Robot, seed: int) -> tuple[dict, dict, dict, dict, dict]:
    gt_mesh, pred_mesh, gt_points, pred_points, alignment = align_prediction(gt, pred, seed)
    geometry = point_metrics(gt_points, pred_points)
    geometry.update({
        "voxel_iou": voxel_iou(gt_mesh, pred_mesh),
        "sample_count_per_robot": SAMPLE_COUNT,
        "voxel_pitch_normalized": VOXEL_PITCH,
        "alignment_pred_normalized_to_gt_normalized": alignment.tolist(),
        "note": "hd95 is robust Hausdorff; hausdorff_max is also reported",
    })

    matches = match_parts(gt, pred, seed)
    per_link = []
    for index, (pred_link, gt_link) in enumerate(sorted(matches.items())):
        gt_link_mesh = globally_normalized_link_mesh(gt, gt_link)
        pred_link_mesh = globally_normalized_link_mesh(pred, pred_link)
        if gt_link_mesh is None or pred_link_mesh is None:
            continue
        pred_link_mesh.apply_transform(alignment)
        gt_link_points = deterministic_surface_points(gt_link_mesh, PER_LINK_SAMPLES, seed + 1000 + index)
        pred_link_points = deterministic_surface_points(pred_link_mesh, PER_LINK_SAMPLES, seed + 1000 + index)
        metrics = point_metrics(gt_link_points, pred_link_points)
        metrics.update({
            "gt_link": gt_link, "pred_link": pred_link,
            "gt_has_curved_surface": has_curved_surface(gt_link_mesh),
            "voxel_iou": voxel_iou(gt_link_mesh, pred_link_mesh),
        })
        per_link.append(metrics)
    geometry["per_link"] = per_link
    geometry["per_link_count"] = len(per_link)
    part_p, part_r, part_f1 = precision_recall_f1(len(matches), len(pred.links), len(gt.links))
    gt_edges = edge_set(gt)
    mapped_pred_edges = {
        (matches[parent], matches[child])
        for parent, child in edge_set(pred)
        if parent in matches and child in matches
    }
    graph_tp = len(mapped_pred_edges & gt_edges)
    graph_p, graph_r, graph_f1 = precision_recall_f1(graph_tp, len(pred.joints), len(gt.joints))
    assembly = {
        "gt_link_count": len(gt.links), "pred_link_count": len(pred.links),
        "matched_parts": len(matches), "part_precision": part_p,
        "part_recall": part_r, "part_f1": part_f1,
        "gt_edge_count": len(gt.joints), "pred_edge_count": len(pred.joints),
        "matched_edges": graph_tp, "assembly_graph_precision": graph_p,
        "assembly_graph_recall": graph_r, "assembly_graph_f1": graph_f1,
        "pred_to_gt_link_mapping": matches,
    }

    pred_joint_by_mapped_edge = {}
    for joint in pred.joints:
        if joint["parent"] in matches and joint["child"] in matches:
            pred_joint_by_mapped_edge[(matches[joint["parent"]], matches[joint["child"]])] = joint
    type_correct, axis_errors, origin_errors = 0, [], []
    gt_to_pred_joint = {}
    for gt_joint in gt.joints:
        edge = (gt_joint["parent"], gt_joint["child"])
        pred_joint = pred_joint_by_mapped_edge.get(edge)
        if pred_joint is None:
            continue
        gt_to_pred_joint[gt_joint["name"]] = pred_joint["name"]
        type_correct += normalize_joint_type(gt_joint["type"]) == normalize_joint_type(pred_joint["type"])
        if gt_joint["type"] not in {"fixed", "floating", "planar"} and pred_joint["type"] not in {"fixed", "floating", "planar"}:
            axis_errors.append(angle_error_degrees(gt_joint["axis"], pred_joint["axis"]))
        origin_errors.append(float(np.linalg.norm(
            gt_joint["origin"][:3, 3] - pred_joint["origin"][:3, 3]
        ) / gt.diagonal))
    kinematic = {
        "matched_joints": len(gt_to_pred_joint),
        "joint_type_accuracy": type_correct / len(gt.joints) if gt.joints else 0.0,
        "axis_error_degrees_median": float(np.median(axis_errors)) if axis_errors else None,
        "axis_error_degrees_mean": float(np.mean(axis_errors)) if axis_errors else None,
        "joint_origin_error_normalized_median": float(np.median(origin_errors)) if origin_errors else None,
        "joint_origin_error_normalized_mean": float(np.mean(origin_errors)) if origin_errors else None,
    }

    inverse_matches = {gt_name: pred_name for pred_name, gt_name in matches.items()}
    translation_errors, rotation_errors = [], []
    ee_translation, ee_rotation = [], []
    mapped_gt_links = [link for link in gt.links if link in inverse_matches]
    ee_gt = max(mapped_gt_links, key=lambda name: gt.depth.get(name, -1)) if mapped_gt_links else None
    fractions = (-0.75, -0.375, 0.0, 0.375, 0.75)
    for fraction in fractions:
        gt_tf = forward_kinematics(gt.links, gt.joints, q_for_fraction(gt.joints, fraction))
        pred_tf = forward_kinematics(pred.links, pred.joints, q_for_fraction(pred.joints, fraction))
        for gt_link in mapped_gt_links:
            pred_link = inverse_matches[gt_link]
            gt_rel = np.linalg.inv(gt_tf[gt.root]) @ gt_tf[gt_link]
            pred_rel = np.linalg.inv(pred_tf[pred.root]) @ pred_tf[pred_link]
            trans = float(np.linalg.norm(
                gt_rel[:3, 3] / gt.diagonal - pred_rel[:3, 3] / pred.diagonal
            ))
            rot = rotation_error_degrees(gt_rel, pred_rel)
            if gt_link != gt.root:
                translation_errors.append(trans)
                rotation_errors.append(rot)
            if gt_link == ee_gt:
                ee_translation.append(trans)
                ee_rotation.append(rot)
    motion = {
        "pose_fractions": list(fractions),
        "mapped_links": len(mapped_gt_links),
        "end_effector_gt_link": ee_gt,
        "link_translation_error_normalized_median": float(np.median(translation_errors)) if translation_errors else None,
        "link_translation_error_normalized_mean": float(np.mean(translation_errors)) if translation_errors else None,
        "link_rotation_error_degrees_median": float(np.median(rotation_errors)) if rotation_errors else None,
        "link_rotation_error_degrees_mean": float(np.mean(rotation_errors)) if rotation_errors else None,
        "end_effector_translation_error_normalized_median": float(np.median(ee_translation)) if ee_translation else None,
        "end_effector_rotation_error_degrees_median": float(np.median(ee_rotation)) if ee_rotation else None,
    }

    failures = []
    if len(pred.links) < len(gt.links): failures.append("missing_parts")
    if len(pred.links) > len(gt.links): failures.append("extra_parts")
    if graph_f1 < 0.90: failures.append("wrong_topology")
    if kinematic["joint_type_accuracy"] < 0.90: failures.append("wrong_joint_type")
    if kinematic["axis_error_degrees_median"] is None or kinematic["axis_error_degrees_median"] > 10: failures.append("wrong_joint_axis")
    if kinematic["joint_origin_error_normalized_median"] is None or kinematic["joint_origin_error_normalized_median"] > 0.05: failures.append("wrong_joint_origin")
    if geometry["chamfer"] > 0.05 or geometry["hd95"] > 0.10 or geometry["voxel_iou"] < 0.50: failures.append("poor_geometry")
    curved = [row for row in geometry["per_link"] if row["gt_has_curved_surface"]]
    if any(row["chamfer"] > 0.05 or row["hd95"] > 0.10 or row["voxel_iou"] < 0.50
           for row in curved):
        failures.append("poor_curved_geometry")
    simultaneous = not failures and motion["link_translation_error_normalized_median"] is not None \
        and motion["link_translation_error_normalized_median"] <= 0.05 \
        and motion["link_rotation_error_degrees_median"] <= 10
    if not simultaneous and (motion["link_translation_error_normalized_median"] is None
                             or motion["link_translation_error_normalized_median"] > 0.05
                             or motion["link_rotation_error_degrees_median"] > 10):
        failures.append("wrong_motion")
    outcome = {"status": "SUCCESS", "simultaneous_success": simultaneous,
               "failure_patterns": sorted(set(failures))}
    return geometry, assembly, kinematic, motion, outcome


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gt-urdf", type=Path, required=True)
    parser.add_argument("--prediction-urdf", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260808)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    try:
        gt, pred = load_robot(args.gt_urdf), load_robot(args.prediction_urdf)
        geometry, assembly, kinematic, motion, outcome = evaluate(gt, pred, args.seed)
    except Exception as exc:
        geometry = assembly = kinematic = motion = {"status": "INVALID"}
        outcome = {"status": "FAILURE", "simultaneous_success": False,
                   "failure_patterns": ["invalid_cad"],
                   "error": f"{type(exc).__name__}: {exc}"}
    for name, payload in (
        ("geometry_metrics.json", geometry), ("assembly_metrics.json", assembly),
        ("kinematic_metrics.json", kinematic), ("motion_metrics.json", motion),
        ("outcome.json", outcome),
    ):
        write_json(args.output_dir / name, payload)
    print(json.dumps(outcome, indent=2))


if __name__ == "__main__":
    main()
