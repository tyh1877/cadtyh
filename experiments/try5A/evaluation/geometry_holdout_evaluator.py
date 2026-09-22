"""Evaluator-only GT geometry metrics for frozen A1 holdout candidates."""

from __future__ import annotations

import csv
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/try5A"
sys.path.insert(0, str(HERE / "scripts"))

from kinematics import rpy  # noqa: E402

PILOT_IDS = ("L03", "L04", "L07")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def metric(reference, prediction, seed):
    def sample(mesh, count, sample_seed):
        state = np.random.get_state()
        np.random.seed(sample_seed)
        points, _ = trimesh.sample.sample_surface(mesh, count)
        np.random.set_state(state)
        return points

    reference_points = sample(reference, 10000, seed)
    prediction_points = sample(prediction, 10000, seed + 1)
    reference_distances = cKDTree(prediction_points).query(reference_points)[0]
    prediction_distances = cKDTree(reference_points).query(prediction_points)[0]
    diagonal = float(np.linalg.norm(reference.bounds[1] - reference.bounds[0]))
    pitch = max(diagonal / 48, 0.3)
    origin = np.minimum(reference.bounds[0], prediction.bounds[0]) - pitch

    def voxels(mesh):
        return {tuple(value) for value in np.rint((mesh.voxelized(pitch).fill().points - origin) / pitch).astype(int)}

    reference_voxels = voxels(reference)
    prediction_voxels = voxels(prediction)
    silhouettes = []
    for axes in ((0, 1), (1, 2), (0, 2)):
        reference_projection = {(value[axes[0]], value[axes[1]]) for value in reference_voxels}
        prediction_projection = {(value[axes[0]], value[axes[1]]) for value in prediction_voxels}
        silhouettes.append(len(reference_projection & prediction_projection) / max(1, len(reference_projection | prediction_projection)))
    reference_dimensions = reference.bounds[1] - reference.bounds[0]
    prediction_dimensions = prediction.bounds[1] - prediction.bounds[0]
    return {
        "voxel_iou": len(reference_voxels & prediction_voxels) / max(1, len(reference_voxels | prediction_voxels)),
        "normalized_chamfer": float((reference_distances.mean() + prediction_distances.mean()) / 2 / diagonal),
        "normalized_hd95": float(max(np.percentile(reference_distances, 95), np.percentile(prediction_distances, 95)) / diagonal),
        "silhouette_iou_mean": float(np.mean(silhouettes)),
        "bbox_error_mm": float(np.linalg.norm(prediction_dimensions - reference_dimensions)),
        "major_dimension_error_mm": float(abs(max(prediction_dimensions) - max(reference_dimensions))),
    }


def main():
    job = load(sys.argv[1])
    candidate = load(job["candidate_manifest"])
    source = ROOT / "go_nogo1/sources/urdf_files_dataset/urdf_files/robotics-toolbox/xacro_generated/interbotix_descriptions/urdf/px100.urdf"
    xml = ET.parse(source).getroot()
    mapping = load(HERE / "protocol/source_id_mapping.json")["links"]
    stable = {value: key for key, value in mapping.items()}
    mesh_root = source.parent.parent / "meshes/meshes_px100"
    rows = []
    for condition, condition_data in candidate["conditions"].items():
        for index, link_id in enumerate(PILOT_IDS):
            source_name = stable[link_id]
            link = next(item for item in xml.findall("link") if item.attrib["name"] == source_name)
            visual = link.find("visual")
            origin = visual.find("origin")
            xyz = np.asarray([float(value) for value in origin.attrib.get("xyz", "0 0 0").split()]) * 1000
            rotation = np.asarray([float(value) for value in origin.attrib.get("rpy", "0 0 0").split()])
            mesh_path = mesh_root / Path(visual.find("geometry/mesh").attrib["filename"]).name
            reference = trimesh.load(mesh_path, force="mesh", process=False)
            transform = np.eye(4)
            transform[:3, :3] = rpy(rotation)
            transform[:3, 3] = xyz
            reference.apply_transform(transform)
            prediction = trimesh.load(ROOT / condition_data["pilot_stl"][link_id], force="mesh", process=False)
            rows.append({"condition": condition, "link_id": link_id, **metric(reference, prediction, 12000 + index)})
    output = Path(job["geometry_output"])
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"status": "PASS", "evaluator_only": True, "row_count": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
