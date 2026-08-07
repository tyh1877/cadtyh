"""Run the screenshot-defined 20-case Go/No-Go 1 feasibility prototype.

The denominator is always the frozen, complexity-blind set of 20 candidates.
Automated checks cover mesh/URDF integrity, Mesh-URDF linkage, multi-pose forward
kinematics, deterministic evaluator smoke tests, and multimodal input generation.
Obvious visual breakage is a separate human review field and cannot be silently
imputed as passing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict, deque
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import trimesh
from PIL import Image, ImageDraw
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

sys.path.insert(0, str(Path(__file__).parent))
from build_inventory import mesh_index, resolve_mesh  # noqa: E402
from render_audit30 import (  # noqa: E402
    origin_transform, prepare_render_meshes, render_view, vector, view_rotation,
)


PROTOTYPE_SIZE = 20
MIN_COMPLETE = 15
SEED = 20260808
VIEWS = (
    (0, 0, "front"), (180, 0, "rear"), (90, 0, "left"),
    (-90, 0, "right"), (0, 90, "top"), (45, 25, "iso"),
)
ALLOWED_JOINT_TYPES = {"fixed", "revolute", "continuous", "prismatic", "floating", "planar"}


def select_prototype(candidate80: pd.DataFrame) -> pd.DataFrame:
    """Take one case per manufacturer, then a second in stable order."""
    ordered = candidate80.sort_values(["manufacturer", "benchmark_index", "entity_id"])
    selected = ordered.groupby("manufacturer", sort=True).head(1).copy()
    remaining = ordered[~ordered.entity_id.isin(selected.entity_id)]
    for row in remaining.itertuples():
        if len(selected) >= PROTOTYPE_SIZE:
            break
        if int((selected.manufacturer == row.manufacturer).sum()) < 2:
            selected = pd.concat([selected, pd.DataFrame([row._asdict()])], ignore_index=True)
    if len(selected) != PROTOTYPE_SIZE:
        raise RuntimeError("could not select exactly 20 manufacturer-balanced cases")
    selected = selected.sort_values(["manufacturer", "name", "entity_id"]).reset_index(drop=True)
    selected.insert(0, "prototype_index", np.arange(1, PROTOTYPE_SIZE + 1))
    return selected


def parse_xyz(node, attribute="xyz", default=(0.0, 0.0, 0.0)):
    if node is None or not node.get(attribute):
        return np.asarray(default, dtype=float)
    values = np.asarray([float(x) for x in node.get(attribute).split()], dtype=float)
    if values.shape != (3,) or not np.isfinite(values).all():
        raise ValueError(f"invalid {attribute} vector")
    return values


def parse_model(path: Path):
    root = ET.parse(path).getroot()
    links = [node.get("name", "") for node in root.findall("link")]
    joints = []
    for node in root.findall("joint"):
        parent_node, child_node = node.find("parent"), node.find("child")
        joint_type = node.get("type", "")
        axis = parse_xyz(node.find("axis"), default=(1.0, 0.0, 0.0))
        if joint_type not in {"fixed", "floating", "planar"}:
            norm = np.linalg.norm(axis)
            if norm <= 0:
                raise ValueError("zero joint axis")
            axis = axis / norm
        limit_node = node.find("limit")
        lower, upper = 0.0, 0.0
        limit_ok = True
        if joint_type in {"revolute", "prismatic"}:
            limit_ok = limit_node is not None and limit_node.get("lower") is not None \
                and limit_node.get("upper") is not None
            if limit_ok:
                lower, upper = float(limit_node.get("lower")), float(limit_node.get("upper"))
                limit_ok = np.isfinite([lower, upper]).all() and lower <= upper
        elif joint_type == "continuous":
            lower, upper = -math.pi, math.pi
        parent = parent_node.get("link", "") if parent_node is not None else ""
        child = child_node.get("link", "") if child_node is not None else ""
        joints.append({
            "name": node.get("name", ""), "type": joint_type,
            "parent": parent, "child": child, "axis": axis,
            "origin": origin_transform(node.find("origin")),
            "lower": lower, "upper": upper, "limit_ok": bool(limit_ok),
        })
    return root, links, joints


def graph_audit(links, joints):
    link_set = set(links)
    edges = [(joint["parent"], joint["child"]) for joint in joints]
    child_counts = Counter(child for _, child in edges)
    children = defaultdict(list)
    for parent, child in edges:
        children[parent].append(child)
    roots = sorted(link_set - set(child_counts))
    visited, queue = set(), deque(roots)
    while queue:
        link = queue.popleft()
        if link in visited:
            continue
        visited.add(link)
        queue.extend(children[link])
    names_ok = bool(links) and all(links) and len(links) == len(link_set)
    joint_names = [joint["name"] for joint in joints]
    joints_named_unique = all(joint_names) and len(joint_names) == len(set(joint_names))
    endpoints_ok = all(parent in link_set and child in link_set and parent != child
                       for parent, child in edges)
    types_ok = all(joint["type"] in ALLOWED_JOINT_TYPES for joint in joints)
    limits_ok = all(joint["limit_ok"] for joint in joints)
    tree_ok = len(roots) == 1 and len(visited) == len(links) and max(child_counts.values(), default=0) <= 1
    return {
        "link_names_valid": names_ok, "joint_names_valid": joints_named_unique,
        "joint_endpoints_valid": endpoints_ok, "joint_types_valid": types_ok,
        "joint_limits_valid": limits_ok, "tree_valid": tree_ok,
        "root_count": len(roots), "root_link": roots[0] if len(roots) == 1 else "",
    }


def motion_transform(joint, value):
    matrix = np.eye(4)
    if joint["type"] in {"revolute", "continuous"}:
        matrix[:3, :3] = Rotation.from_rotvec(joint["axis"] * value).as_matrix()
    elif joint["type"] == "prismatic":
        matrix[:3, 3] = joint["axis"] * value
    return matrix


def pose_values(joints, sign):
    values = {}
    for joint in joints:
        if joint["type"] in {"revolute", "prismatic", "continuous"}:
            if joint["type"] == "continuous":
                value = sign * math.pi / 4
            elif sign < 0:
                value = joint["lower"] + .25 * (joint["upper"] - joint["lower"])
            else:
                value = joint["lower"] + .75 * (joint["upper"] - joint["lower"])
            if joint["type"] == "revolute":
                value = float(np.clip(value, -math.pi / 2, math.pi / 2))
            values[joint["name"]] = float(value)
    return values


def forward_kinematics(links, joints, values):
    children, child_names = defaultdict(list), set()
    for joint in joints:
        children[joint["parent"]].append(joint)
        child_names.add(joint["child"])
    roots = [link for link in links if link not in child_names]
    if len(roots) != 1:
        raise ValueError("kinematic graph is not a rooted tree")
    transforms = {roots[0]: np.eye(4)}
    queue = deque([roots[0]])
    while queue:
        parent = queue.popleft()
        for joint in children[parent]:
            value = values.get(joint["name"], 0.0)
            transforms[joint["child"]] = (
                transforms[parent] @ joint["origin"] @ motion_transform(joint, value)
            )
            queue.append(joint["child"])
    if len(transforms) != len(links):
        raise ValueError("forward kinematics did not reach every link")
    return transforms


def load_link_meshes(root, urdf_path, dataset_root, by_name):
    output, references, resolved, failures = defaultdict(list), 0, 0, []
    for link in root.findall("link"):
        link_name = link.get("name", "")
        for visual in link.findall("visual"):
            mesh_node = visual.find("geometry/mesh")
            if mesh_node is None or not mesh_node.get("filename"):
                continue
            references += 1
            path, method = resolve_mesh(mesh_node.get("filename"), urdf_path, dataset_root, by_name)
            if path is None:
                failures.append(f"unresolved:{mesh_node.get('filename')}")
                continue
            try:
                loaded = trimesh.load(path, force="scene", process=True)
                # Scene.dump applies Collada/OBJ scene-graph transforms. Reading
                # geometry.values() directly can explode multi-node assemblies.
                parts = loaded.dump(concatenate=False) if isinstance(loaded, trimesh.Scene) else [loaded]
                scale = vector(mesh_node.get("scale"), [1, 1, 1])
                visual_tf = origin_transform(visual.find("origin"))
                loaded_any = False
                for part in parts:
                    if not isinstance(part, trimesh.Trimesh) or not len(part.faces):
                        continue
                    mesh = part.copy()
                    mesh.vertices *= scale
                    mesh.apply_transform(visual_tf)
                    mesh.process(validate=True)
                    if np.isfinite(mesh.vertices).all() and len(mesh.faces):
                        output[link_name].append(mesh)
                        loaded_any = True
                if loaded_any:
                    resolved += 1
                else:
                    failures.append(f"empty:{path.name}")
            except Exception as exc:
                failures.append(f"{path.name}:{type(exc).__name__}")
    return output, references, resolved, failures


def world_meshes(link_meshes, transforms):
    output = []
    by_link = {}
    for link, meshes in link_meshes.items():
        transformed = []
        for mesh in meshes:
            item = mesh.copy()
            item.apply_transform(transforms[link])
            transformed.append(item)
            output.append(item)
        if transformed:
            by_link[link] = trimesh.util.concatenate(transformed)
    return output, by_link


def point_aabb_distance(point, bounds):
    delta = np.maximum(np.maximum(bounds[0] - point, point - bounds[1]), 0)
    return float(np.linalg.norm(delta))


def axis_plausibility(joints, transforms, world_by_link, robot_diagonal):
    checked, plausible = 0, 0
    ratios = []
    for joint in joints:
        adjacent = [link for link in (joint["parent"], joint["child"]) if link in world_by_link]
        if not adjacent:
            continue
        joint_world = transforms[joint["parent"]] @ joint["origin"]
        point = joint_world[:3, 3]
        ratio = max(point_aabb_distance(point, world_by_link[link].bounds) for link in adjacent) \
            / max(robot_diagonal, 1e-12)
        ratios.append(ratio)
        checked += 1
        plausible += int(ratio <= .25)
    rate = plausible / checked if checked else 0.0
    return checked, rate, max(ratios, default=float("inf"))


def deterministic_surface_points(mesh, count, seed):
    state = np.random.get_state()
    np.random.seed(seed)
    try:
        points, _ = trimesh.sample.sample_surface(mesh, count)
    finally:
        np.random.set_state(state)
    return points


def point_metrics(reference, prediction, diagonal):
    ref_tree, pred_tree = cKDTree(reference), cKDTree(prediction)
    d_ref = pred_tree.query(reference, k=1)[0]
    d_pred = ref_tree.query(prediction, k=1)[0]
    chamfer = float((d_ref.mean() + d_pred.mean()) / (2 * diagonal))
    hd95 = float(max(np.quantile(d_ref, .95), np.quantile(d_pred, .95)) / diagonal)
    similarity = float(math.exp(-20 * chamfer))
    return chamfer, hd95, similarity


def surface_iou(reference, prediction, pitch):
    ref = {tuple(row) for row in np.floor(reference / pitch + .5).astype(np.int64)}
    pred = {tuple(row) for row in np.floor(prediction / pitch + .5).astype(np.int64)}
    return len(ref & pred) / len(ref | pred) if ref or pred else 1.0


def set_f1(reference, prediction):
    if not reference and not prediction:
        return 1.0
    true_positive = len(reference & prediction)
    precision = true_positive / len(prediction) if prediction else 0.0
    recall = true_positive / len(reference) if reference else 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def evaluator_smoke_test(world_by_link, joints, neutral_tf, positive_tf, seed):
    combined = trimesh.util.concatenate(list(world_by_link.values()))
    diagonal = float(np.linalg.norm(np.ptp(combined.vertices, axis=0)))
    if not np.isfinite(diagonal) or diagonal <= 0:
        raise ValueError("invalid whole-robot scale")
    points = deterministic_surface_points(combined, 768, seed)
    identity = point_metrics(points, points.copy(), diagonal)
    offset = np.array([.01 * diagonal, 0, 0])
    corrupted = point_metrics(points, points + offset, diagonal)

    per_link_identity_cd, per_link_identity_iou = [], []
    per_link_corrupted_cd, per_link_corrupted_iou = [], []
    for index, mesh in enumerate(world_by_link.values()):
        samples = deterministic_surface_points(mesh, 128, seed + index + 1)
        local_diag = max(float(np.linalg.norm(np.ptp(mesh.vertices, axis=0))), diagonal / 100)
        per_link_identity_cd.append(point_metrics(samples, samples.copy(), local_diag)[0])
        per_link_identity_iou.append(surface_iou(samples, samples.copy(), diagonal / 64))
        shifted = samples + offset
        per_link_corrupted_cd.append(point_metrics(samples, shifted, local_diag)[0])
        per_link_corrupted_iou.append(surface_iou(samples, shifted, diagonal / 64))

    link_names = set(world_by_link)
    graph_edges = {(joint["parent"], joint["child"]) for joint in joints}
    joint_types = {joint["name"]: joint["type"] for joint in joints}
    partmatch_identity = set_f1(link_names, set(link_names))
    graph_identity = set_f1(graph_edges, set(graph_edges))
    corrupt_links = set(link_names)
    corrupt_links.discard(sorted(corrupt_links)[-1])
    corrupt_edges = set(graph_edges)
    corrupt_edges.discard(sorted(corrupt_edges)[-1])
    partmatch_corrupt = set_f1(link_names, corrupt_links)
    graph_corrupt = set_f1(graph_edges, corrupt_edges)
    joint_type_identity = float(np.mean([
        joint_types[name] == joint_types[name] for name in joint_types
    ])) if joint_types else 1.0
    corrupt_joint_types = dict(joint_types)
    first_joint = sorted(corrupt_joint_types)[0]
    corrupt_joint_types[first_joint] = "__wrong_type__"
    joint_type_corrupt = float(np.mean([
        joint_types[name] == corrupt_joint_types[name] for name in joint_types
    ]))
    axis_identity = float(np.mean([np.linalg.norm(joint["axis"] - joint["axis"])
                                   for joint in joints])) if joints else 0.0
    origin_identity = float(np.mean([np.linalg.norm(joint["origin"][:3, 3]
                                                        - joint["origin"][:3, 3])
                                     for joint in joints])) if joints else 0.0
    axis_corrupt = float(np.mean([
        np.linalg.norm(joint["axis"] - (joint["axis"] + np.array([.1, 0, 0])))
        if index == 0 else 0.0 for index, joint in enumerate(joints)
    ])) if joints else 0.0
    origin_corrupt = .01 * diagonal / max(len(joints), 1)
    transform_identity = float(np.mean([
        np.linalg.norm(neutral_tf[link][:3, 3] - neutral_tf[link][:3, 3])
        for link in neutral_tf
    ]))
    transform_corrupt = float(np.mean([
        np.linalg.norm(neutral_tf[link][:3, 3] - positive_tf[link][:3, 3])
        for link in neutral_tf
    ]))
    identity_ok = (
        max(identity[:2]) <= 1e-12 and abs(identity[2] - 1) <= 1e-12
        and max(per_link_identity_cd, default=0) <= 1e-12
        and min(per_link_identity_iou, default=1) == 1
        and len(link_names) > 0 and len(graph_edges) > 0 and len(joint_types) > 0
        and partmatch_identity == 1 and graph_identity == 1 and joint_type_identity == 1
        and axis_identity == 0 and origin_identity == 0 and transform_identity == 0
    )
    corruption_detected = (
        corrupted[0] > identity[0] and corrupted[1] > identity[1]
        and corrupted[2] < identity[2]
        and np.mean(per_link_corrupted_cd) > 0
        and np.mean(per_link_corrupted_iou) < 1
        and partmatch_corrupt < 1 and graph_corrupt < 1 and joint_type_corrupt < 1
        and axis_corrupt > 0 and origin_corrupt > 0
        and transform_corrupt > 0
    )
    return {
        "evaluator_identity_ok": bool(identity_ok),
        "evaluator_corruption_detected": bool(corruption_detected),
        "identity_cd": identity[0], "identity_hd95": identity[1],
        "identity_similarity": identity[2],
        "corrupt_cd": corrupted[0], "corrupt_hd95": corrupted[1],
        "corrupt_similarity": corrupted[2],
        "identity_part_cd_max": max(per_link_identity_cd, default=0),
        "identity_part_iou_min": min(per_link_identity_iou, default=1),
        "corrupt_part_cd_mean": float(np.mean(per_link_corrupted_cd)),
        "corrupt_part_iou_mean": float(np.mean(per_link_corrupted_iou)),
        "identity_partmatch_f1": partmatch_identity, "identity_graph_f1": graph_identity,
        "identity_joint_type_accuracy": joint_type_identity,
        "identity_axis_error": axis_identity, "identity_origin_error": origin_identity,
        "identity_multipose_transform_error": transform_identity,
        "corrupt_partmatch_f1": partmatch_corrupt, "corrupt_graph_f1": graph_corrupt,
        "corrupt_joint_type_accuracy": joint_type_corrupt,
        "corrupt_axis_error": axis_corrupt, "corrupt_origin_error": origin_corrupt,
        "corrupt_multipose_transform_error": transform_corrupt,
    }


def render_six_views(meshes, output_dir, prototype_index, entity_id):
    output_dir.mkdir(parents=True, exist_ok=True)
    # The prototype manifest can change after an upstream parser correction.
    # Remove only this entity's previous generated views to avoid stale evidence.
    for stale in output_dir.glob("*.png"):
        stale.unlink()
    render_meshes = prepare_render_meshes(meshes, max_faces=60000)
    paths = []
    for azimuth, elevation, label in VIEWS:
        fig, ax = plt.subplots(figsize=(4, 4), dpi=110, facecolor="white")
        render_view(ax, render_meshes, view_rotation(azimuth, elevation))
        ax.set_title(label, fontsize=10)
        path = output_dir / f"{prototype_index:02d}_{entity_id}_{label}.png"
        fig.savefig(path, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        paths.append(str(path.resolve()))
    return paths


def create_contact_sheets(manifest, output_dir):
    sheets_dir = output_dir / "contact_sheets"
    sheets_dir.mkdir(parents=True, exist_ok=True)
    for chunk_start in range(0, len(manifest), 4):
        chunk = manifest.iloc[chunk_start:chunk_start + 4]
        thumb = 220
        canvas = Image.new("RGB", (thumb * 6, (thumb + 32) * len(chunk)), "white")
        draw = ImageDraw.Draw(canvas)
        for row_number, row in enumerate(chunk.itertuples()):
            paths = json.loads(row.render_paths)
            for column, path in enumerate(paths):
                image = Image.open(path).convert("RGB")
                image.thumbnail((thumb - 8, thumb - 8))
                x = column * thumb + (thumb - image.width) // 2
                y = row_number * (thumb + 32) + 24
                canvas.paste(image, (x, y))
            draw.text((6, row_number * (thumb + 32) + 4),
                      f"{int(row.prototype_index):02d} {row.manufacturer} {row.name}", fill="black")
        canvas.save(sheets_dir / f"cases_{chunk_start + 1:02d}_{chunk_start + len(chunk):02d}.jpg",
                    quality=88)


def prompt_text(row, links, joints):
    joint_types = Counter(joint["type"] for joint in joints)
    actuated = sum(count for kind, count in joint_types.items()
                   if kind not in {"fixed", "floating", "planar"})
    types = ", ".join(f"{count} {kind}" for kind, count in sorted(joint_types.items()))
    return (
        f"Generate a complete articulated robot arm with {len(links)} links and "
        f"{len(joints)} joints ({actuated} actuated; {types}). Produce link-level "
        "mesh geometry plus a consistent URDF containing parent-child relations, "
        "joint types, axes, origins, limits, and a valid canonical pose."
    )


def manual_reviews(path, entity_ids):
    if not path.exists():
        pd.DataFrame({"entity_id": entity_ids, "visual_review_pass": "", "notes": ""}).to_csv(
            path, index=False, encoding="utf-8-sig"
        )
    review = pd.read_csv(path, dtype=str).fillna("")
    if set(review.entity_id) != set(entity_ids) or review.entity_id.duplicated().any():
        raise ValueError("visual review file does not match the frozen prototype denominator")
    mapping = {}
    for row in review.itertuples():
        value = row.visual_review_pass.strip().casefold()
        mapping[row.entity_id] = True if value in {"true", "1", "yes", "pass"} \
            else False if value in {"false", "0", "no", "fail"} else None
    return mapping


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate80", type=Path, required=True)
    parser.add_argument("--entities", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    candidate80 = pd.read_csv(args.candidate80)
    entities = pd.read_csv(args.entities)
    prototype = select_prototype(candidate80).merge(
        entities, on="entity_id", suffixes=("", "_entity"), validate="one_to_one"
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    prototype_ids = prototype.entity_id.tolist()
    # These folders contain only reproducible outputs from this script.  Keep
    # them synchronized with the frozen denominator so an upstream correction
    # cannot leave evidence from a superseded candidate in the audit folder.
    expected_ids = set(prototype_ids)
    for generated_name in ("prompts", "renders"):
        generated_root = (args.output_dir / generated_name).resolve()
        generated_root.mkdir(parents=True, exist_ok=True)
        for child in generated_root.iterdir():
            if not child.is_dir() or child.name in expected_ids:
                continue
            resolved_child = child.resolve()
            if resolved_child.parent != generated_root:
                raise ValueError(f"refusing to remove output outside {generated_root}: {resolved_child}")
            shutil.rmtree(resolved_child)
    review_path = args.output_dir / "visual_review.csv"
    reviews = manual_reviews(review_path, prototype_ids)
    _, by_name = mesh_index(args.dataset_root)
    rows = []

    for row in prototype.itertuples():
        record = {
            "prototype_index": int(row.prototype_index), "entity_id": row.entity_id,
            "manufacturer": row.manufacturer, "name": row.name, "source": row.source,
            "urdf_path": row.urdf_path,
        }
        failures = []
        try:
            root, links, joints = parse_model(Path(row.urdf_path))
            graph = graph_audit(links, joints)
            neutral = forward_kinematics(links, joints, {})
            negative = forward_kinematics(links, joints, pose_values(joints, -1))
            positive = forward_kinematics(links, joints, pose_values(joints, 1))
            link_meshes, references, resolved, mesh_failures = load_link_meshes(
                root, Path(row.urdf_path), args.dataset_root, by_name
            )
            failures.extend(mesh_failures)
            meshes, world_by_link = world_meshes(link_meshes, neutral)
            if not meshes:
                raise ValueError("no linked visual meshes")
            combined = trimesh.util.concatenate(meshes)
            diagonal = float(np.linalg.norm(np.ptp(combined.vertices, axis=0)))
            finite_mesh = bool(np.isfinite(combined.vertices).all() and diagonal > 0)
            face_count = int(len(combined.faces))
            resolution_rate = resolved / references if references else 0.0
            actuated_children = {joint["child"] for joint in joints
                                 if joint["type"] not in {"fixed", "floating", "planar"}}
            moving_visual_rate = len(actuated_children & set(link_meshes)) / max(len(actuated_children), 1)
            checked_axes, plausible_rate, max_axis_ratio = axis_plausibility(
                joints, neutral, world_by_link, diagonal
            )
            pose_finite = all(np.isfinite(matrix).all()
                              for transforms in (neutral, negative, positive)
                              for matrix in transforms.values())
            pose_motion = max(
                np.linalg.norm(positive[link][:3, 3] - negative[link][:3, 3])
                for link in links
            ) / max(diagonal, 1e-12)
            pose_bounded = pose_motion <= 4.0
            seed = int(hashlib.sha256(row.entity_id.encode()).hexdigest()[:8], 16)
            evaluator = evaluator_smoke_test(world_by_link, joints, neutral, positive, seed)
            render_paths = render_six_views(
                meshes, args.output_dir / "renders" / row.entity_id,
                int(row.prototype_index), row.entity_id,
            )
            prompt = prompt_text(row, links, joints)
            prompt_dir = args.output_dir / "prompts" / row.entity_id
            prompt_dir.mkdir(parents=True, exist_ok=True)
            (prompt_dir / "text.txt").write_text(prompt + "\n", encoding="utf-8")
            bundle = {"entity_id": row.entity_id, "text": prompt, "images": render_paths,
                      "modalities": ["text", "image", "text+image"]}
            (prompt_dir / "bundle.json").write_text(json.dumps(bundle, indent=2), encoding="utf-8")

            mesh_pass = finite_mesh and face_count >= 1000 and resolution_rate >= .90 \
                and moving_visual_rate >= .80 and not mesh_failures
            urdf_pass = bool(all([
                graph["link_names_valid"], graph["joint_names_valid"],
                graph["joint_endpoints_valid"], graph["joint_types_valid"],
                graph["joint_limits_valid"], graph["tree_valid"],
            ]))
            consistency_pass = bool(
                checked_axes > 0 and plausible_rate >= .90 and pose_finite
                and pose_motion > 1e-8 and pose_bounded
            )
            evaluator_pass = bool(evaluator["evaluator_identity_ok"]
                                  and evaluator["evaluator_corruption_detected"])
            multimodal_pass = bool(len(render_paths) == 6 and all(Path(x).is_file() for x in render_paths)
                                   and prompt.strip())
            visual_review = reviews[row.entity_id]
            gate_status = {
                "mesh_quality": mesh_pass,
                "urdf_quality": urdf_pass,
                "mesh_urdf_consistency": consistency_pass,
                "evaluator": evaluator_pass,
                "multimodal": multimodal_pass,
                "visual_review": visual_review is True,
            }
            failed_gates = [name for name, passed in gate_status.items() if not passed]
            record.update({
                "n_links_parsed": len(links), "n_joints_parsed": len(joints),
                "mesh_references": references, "mesh_references_resolved": resolved,
                "mesh_resolution_rate": resolution_rate, "loaded_visual_links": len(link_meshes),
                "moving_link_visual_rate": moving_visual_rate, "face_count": face_count,
                "robot_diagonal": diagonal, "axis_checks": checked_axes,
                "axis_plausible_rate": plausible_rate, "max_axis_aabb_distance_ratio": max_axis_ratio,
                "multi_pose_finite": pose_finite, "multi_pose_motion_ratio": pose_motion,
                "multi_pose_bounded": pose_bounded,
                "mesh_quality_pass": mesh_pass, "urdf_quality_pass": urdf_pass,
                "mesh_urdf_consistency_pass": consistency_pass,
                "evaluator_pass": evaluator_pass, "multimodal_pass": multimodal_pass,
                "visual_review_pass": visual_review,
                "automated_complete": bool(mesh_pass and urdf_pass and consistency_pass
                                           and evaluator_pass and multimodal_pass),
                "complete_case": bool(mesh_pass and urdf_pass and consistency_pass
                                      and evaluator_pass and multimodal_pass
                                      and visual_review is True),
                "render_paths": json.dumps(render_paths), "prompt_text": prompt,
                "failures": json.dumps(failures),
                "failed_gates": json.dumps(failed_gates), **graph, **evaluator,
            })
        except Exception as exc:
            failures.append(f"{type(exc).__name__}:{exc}")
            record.update({
                "mesh_quality_pass": False, "urdf_quality_pass": False,
                "mesh_urdf_consistency_pass": False, "evaluator_pass": False,
                "multimodal_pass": False, "visual_review_pass": reviews[row.entity_id],
                "automated_complete": False, "complete_case": False,
                "render_paths": "[]", "prompt_text": "", "failures": json.dumps(failures),
                "failed_gates": json.dumps(["exception"]),
            })
        rows.append(record)
        print(f"audited {len(rows)}/{PROTOTYPE_SIZE}: {row.entity_id}", flush=True)

    result = pd.DataFrame(rows).sort_values("prototype_index")
    result.to_csv(args.output_dir / "case_audit.csv", index=False, encoding="utf-8-sig")
    manifest_columns = ["prototype_index", "entity_id", "manufacturer", "name", "source",
                        "urdf_path", "render_paths", "prompt_text"]
    result[manifest_columns].to_csv(args.output_dir / "prototype20_manifest.csv", index=False,
                                    encoding="utf-8-sig")
    create_contact_sheets(result, args.output_dir)

    complete = int(result.complete_case.sum())
    review_complete = int(result.visual_review_pass.notna().sum())
    complete_mask = result.complete_case.fillna(False)
    criteria = {
        "at_least_15_of_20_complete_cases": bool(complete >= MIN_COMPLETE),
        "link_visual_mesh_readability_at_least_90_percent": bool(
            result.mesh_references_resolved.sum() / result.mesh_references.sum() >= .90
        ),
        "100_percent_complete_cases_urdf_parse_and_graph_valid": bool(
            complete > 0 and result.loc[complete_mask, "urdf_quality_pass"].all()
        ),
        "100_percent_complete_cases_multi_pose_no_clear_gt_error": bool(
            complete > 0 and result.loc[complete_mask, "mesh_urdf_consistency_pass"].all()
        ),
        "100_percent_complete_cases_evaluators_callable": bool(
            complete > 0 and result.loc[complete_mask, "evaluator_pass"].all()
        ),
        "100_percent_complete_cases_multimodal_inputs_constructed": bool(
            complete > 0 and result.loc[complete_mask, "multimodal_pass"].all()
        ),
        "all_20_visual_reviews_completed": bool(review_complete == PROTOTYPE_SIZE),
    }
    summary = {
        "target": "screenshot-defined Go/No-Go 1 prototype feasibility",
        "denominator": PROTOTYPE_SIZE, "minimum_complete_cases": MIN_COMPLETE,
        "prototype_selection": "complexity-blind; one per manufacturer then a second",
        "prototype_manufacturers": int(result.manufacturer.nunique()),
        "automated_complete_cases": int(result.automated_complete.sum()),
        "visual_reviews_completed": review_complete,
        "complete_cases": complete,
        "criterion_results": criteria,
        "decision": "GO" if all(criteria.values()) else "NO-GO",
        "decision_rule": "all global criteria must pass; failures remain in denominator",
        "case_failures": result.loc[
            ~result.complete_case,
            ["entity_id", "manufacturer", "name", "failed_gates", "failures"],
        ].to_dict("records"),
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
