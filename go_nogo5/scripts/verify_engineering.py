"""Deterministic engineering verification for articulated CAD reconstructions.

`collision_rate_proxy` is deliberately a sampled non-adjacent surface-clearance
proxy because python-fcl is unavailable in the fixed environment. It is not a
claim of exact volumetric penetration testing.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
from scipy.stats import qmc

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "go_nogo2" / "scripts"))
from evaluate_prediction import edge_set, evaluate, load_robot, write_json  # noqa: E402
from prototype_feasibility import forward_kinematics  # noqa: E402

SAMPLES, CLEARANCE_RATIO, VOXEL_RATIO = 64, 0.01, 0.05


def joint_samples(robot, count: int = SAMPLES) -> list[dict[str, float]]:
    active = [joint for joint in robot.joints if joint["type"] in {"revolute", "continuous", "prismatic"}]
    sobol = qmc.Sobol(d=max(1, len(active)), scramble=False, seed=20260821).random_base2(int(math.ceil(math.log2(count))))[:count]
    values = []
    for row in sobol:
        q = {}
        for index, joint in enumerate(active):
            if joint["type"] == "continuous": q[joint["name"]] = (float(row[index]) * 2 - 1) * math.pi
            else: q[joint["name"]] = joint["lower"] + float(row[index]) * (joint["upper"] - joint["lower"])
        values.append(q)
    return values


def link_points(robot, transforms: dict[str, np.ndarray], link: str, count: int = 160) -> np.ndarray:
    meshes = robot.local_meshes.get(link, [])
    if not meshes: return np.empty((0, 3))
    vertices = np.vstack([mesh.vertices for mesh in meshes if len(mesh.vertices)])
    if len(vertices) > count:
        indices = np.linspace(0, len(vertices) - 1, count, dtype=int); vertices = vertices[indices]
    homo = np.column_stack([vertices, np.ones(len(vertices))])
    return (transforms[link] @ homo.T).T[:, :3]


def nonadjacent_pairs(robot) -> list[tuple[str, str]]:
    adjacent = {frozenset(edge) for edge in edge_set(robot)}
    links = robot.links
    return [(links[i], links[j]) for i in range(len(links)) for j in range(i + 1, len(links)) if frozenset((links[i], links[j])) not in adjacent]


def intrinsic(robot) -> dict:
    pairs, samples = nonadjacent_pairs(robot), joint_samples(robot)
    minimum, collisions, witnesses = float("inf"), 0, []
    threshold = robot.diagonal * CLEARANCE_RATIO
    for sample_index, q in enumerate(samples):
        transforms = forward_kinematics(robot.links, robot.joints, q)
        points = {link: link_points(robot, transforms, link) for link in robot.links}
        pose_min, pose_pair = float("inf"), None
        for a, b in pairs:
            if not len(points[a]) or not len(points[b]): continue
            distance = float(cKDTree(points[a]).query(points[b], workers=1)[0].min())
            if distance < pose_min: pose_min, pose_pair = distance, (a, b)
        minimum = min(minimum, pose_min)
        if pose_min < threshold:
            collisions += 1
            witnesses.append({"sample_index": sample_index, "q": q, "links": list(pose_pair or ()), "clearance": pose_min})
    # Interface proxy: both incident bodies should lie close to the declared joint origin.
    interfaces = []
    canonical = forward_kinematics(robot.links, robot.joints, {})
    for joint in robot.joints:
        parent_tf = canonical[joint["parent"]]
        origin = parent_tf @ joint["origin"]
        joint_point = origin[:3, 3]
        distances = {}
        for link in (joint["parent"], joint["child"]):
            points = link_points(robot, canonical, link)
            distances[link] = float(cKDTree(points).query(joint_point, workers=1)[0]) if len(points) else float("inf")
        interfaces.append({"joint": joint["name"], "parent_distance": distances[joint["parent"]], "child_distance": distances[joint["child"]]})
    return {"collision_rate_proxy": collisions / len(samples), "minimum_clearance": minimum,
            "clearance_threshold": threshold, "collision_witnesses": witnesses[:5], "interface_proximity": interfaces,
            "sampling": {"method": "Sobol", "configurations": len(samples), "nonadjacent_pairs": len(pairs)}}


def workspace(robot) -> tuple[set[tuple[int, int, int]], dict]:
    samples = joint_samples(robot); ee = max(robot.links, key=lambda link: robot.depth.get(link, -1)); points = []
    for q in samples:
        tf = forward_kinematics(robot.links, robot.joints, q)
        point = (np.linalg.inv(tf[robot.root]) @ tf[ee])[:3, 3] / robot.diagonal
        points.append(point)
    points = np.asarray(points); pitch = VOXEL_RATIO
    keys = {tuple(row) for row in np.floor((points + 2) / pitch).astype(int)}
    return keys, {"end_effector": ee, "samples": len(samples), "radius_normalized_median": float(np.median(np.linalg.norm(points, axis=1))), "workspace_voxels": len(keys)}


def failure_report(intrinsic_result: dict) -> list[dict]:
    failures = []
    for witness in intrinsic_result["collision_witnesses"]:
        failures.append({"type": "clearance_proxy", "location": "-".join(witness["links"]), "severity": max(0.0, intrinsic_result["clearance_threshold"] - witness["clearance"]), "suggestion": "Increase clearance by changing only local body primitive placement/size; preserve link and joint identity.", "details": witness})
    for item in intrinsic_result["interface_proximity"]:
        severity = max(item["parent_distance"], item["child_distance"])
        if severity > intrinsic_result["clearance_threshold"] * 5:
            failures.append({"type": "joint_interface_proximity", "location": item["joint"], "severity": severity, "suggestion": "Move local body material toward the existing joint origin; do not alter graph, joint type, axis, or limits.", "details": item})
    return failures


def verify(case_dir: Path, prediction_dir: Path, output_dir: Path) -> dict:
    manifest = json.loads((prediction_dir / "manifest.json").read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    if manifest["status"] != "SUCCESS":
        result = {"status": manifest["status"], "failure_report": [{"type": "invalid_cad", "location": None, "severity": 1.0, "suggestion": "No repair attempted without an executable source artifact."}]}
    else:
        source_case = json.loads((case_dir / "metadata.json").read_text(encoding="utf-8"))["source_case"]
        gt, pred = load_robot(Path(source_case) / "urdf" / "model.urdf"), load_robot(prediction_dir / "urdf" / "model.urdf")
        geometry, assembly, kinematic, motion, outcome = evaluate(gt, pred, 20260821)
        own = intrinsic(pred); gt_workspace, gt_workspace_meta = workspace(gt); pred_workspace, pred_workspace_meta = workspace(pred)
        workspace_iou = len(gt_workspace & pred_workspace) / len(gt_workspace | pred_workspace) if gt_workspace | pred_workspace else 0.0
        result = {"status": "SUCCESS", "geometry": geometry, "assembly": assembly, "kinematic": kinematic, "motion": motion, "outcome": outcome,
                  "engineering": {"collision": own, "workspace": {"workspace_iou": workspace_iou, "gt": gt_workspace_meta, "prediction": pred_workspace_meta}},
                  "failure_report": failure_report(own)}
    write_json(output_dir / "verification.json", result)
    write_json(output_dir / "failure.json", {"failures": result["failure_report"]})
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--prediction-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(); print(json.dumps(verify(args.case_dir, args.prediction_dir, args.output_dir), indent=2))


if __name__ == "__main__": main()
