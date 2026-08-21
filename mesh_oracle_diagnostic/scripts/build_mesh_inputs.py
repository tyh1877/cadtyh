"""Create pre-registered point-cloud mesh inputs for the Mesh Oracle Diagnostic."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "go_nogo2" / "scripts"))
from evaluate_prediction import deterministic_surface_points, load_robot, normalized_mesh  # noqa: E402

# Selected before any Mesh Oracle model result: compact, medium, high-link-count
# robots from the pre-existing audited development set.
SELECTED = (
    "dev_arm-0573e1e127", "dev_arm-10f5f05385", "dev_arm-21b8992ec4",
    "dev_arm-42e898b1a2", "dev_arm-43fa322555", "dev_arm-551a9c392e",
    "dev_arm-d55f01b988",
)


def quantized(points: np.ndarray) -> list[list[float]]:
    return np.round(points, 4).astype(float).tolist()


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=ROOT / "go_nogo3/data/dev15")
    parser.add_argument("--output-root", type=Path, default=ROOT / "mesh_oracle_diagnostic/data/cases")
    parser.add_argument("--manifest", type=Path, default=ROOT / "mesh_oracle_diagnostic/results/input_manifest.csv")
    args = parser.parse_args(); records = []
    for case_id in SELECTED:
        source = args.source_root / case_id
        output = args.output_root / case_id; (output / "oracle_parts").mkdir(parents=True, exist_ok=True)
        robot = load_robot(source / "urdf" / "model.urdf")
        monolithic = deterministic_surface_points(normalized_mesh(robot), 384, 20260821)
        coordinate = {"representation": "normalized canonical mesh surface points", "normalization": "point_normalized=(point-center)/diagonal", "meters_per_normalized_unit": robot.diagonal, "millimeters_per_normalized_unit": robot.diagonal * 1000.0}
        (output / "monolithic_surface_points.json").write_text(json.dumps({**coordinate, "points": quantized(monolithic)}, separators=(",", ":")), encoding="utf-8")
        part_records, hidden_mapping = [], {}
        for index, link in enumerate(robot.links):
            name = f"part_{index:02d}"
            meshes = robot.local_meshes.get(link, [])
            # URDFs can contain a structural root/tool link without a visual.
            # Preserve the link for graph recovery with a negligible, documented
            # placeholder rather than creating an empty STL that invalidates URDF parsing.
            mesh = trimesh.util.concatenate(meshes) if meshes else trimesh.creation.icosphere(subdivisions=1, radius=robot.diagonal * 1e-6)
            mesh.export(output / "oracle_parts" / f"{name}.stl")
            world = robot.world_meshes.get(link)
            points = deterministic_surface_points(world, min(96, max(24, len(world.faces))), 20260821 + index) if world is not None else np.empty((0, 3))
            points = (points - robot.center) / robot.diagonal
            part_records.append({"part": name, "surface_points": quantized(points)})
            hidden_mapping[name] = link
        (output / "per_link_surface_points.json").write_text(json.dumps({**coordinate, "representation": "anonymous per-link canonical mesh surface points", "parts": part_records}, separators=(",", ":")), encoding="utf-8")
        (output / "hidden_part_mapping.json").write_text(json.dumps(hidden_mapping, indent=2), encoding="utf-8")
        (output / "metadata.json").write_text(json.dumps({"source_case": str(source.resolve()), "part_count": len(part_records), "monolithic_points": len(monolithic), "per_link_points_per_part": 96}, indent=2), encoding="utf-8")
        records.append({"case_id": case_id, "links": len(robot.links), "joints": len(robot.joints), "monolithic_points": len(monolithic), "anonymous_parts": len(part_records)})
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with args.manifest.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
    print(json.dumps({"cases": len(records), "selected": list(SELECTED)}, indent=2))


if __name__ == "__main__": main()
