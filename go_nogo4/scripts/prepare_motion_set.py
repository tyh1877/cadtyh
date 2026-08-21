"""Derive blinded multi-pose render inputs from the audited Go/No-Go 3 dev set."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "go_nogo2" / "scripts"))
sys.path.insert(0, str(ROOT / "go_nogo1" / "scripts"))
from evaluate_prediction import load_robot, q_for_fraction  # noqa: E402
from prototype_feasibility import forward_kinematics, world_meshes  # noqa: E402
from render_audit30 import prepare_render_meshes, render_view, view_rotation  # noqa: E402

POSES = (("pose_0", -0.70), ("pose_1", 0.0), ("pose_2", 0.70))
VIEWS = ((0, 0, "front"), (90, 0, "side"), (0, 90, "top"), (45, 25, "iso"))
BLIND_PROMPT = (
    "Reconstruct the articulated robot shown in the supplied rendered observations. "
    "Return editable parametric CAD geometry and an explicit URDF-equivalent kinematic model. "
    "Infer parts, topology, joint types, axes, origins, and limits only from visible evidence. "
    "No hidden file, robot identifier, structural count, or motion parameters are available."
)


def render_case(source_case: Path, output_case: Path) -> dict:
    output_case.mkdir(parents=True, exist_ok=True)
    robot = load_robot(source_case / "urdf" / "model.urdf")
    records = []
    for pose_name, fraction in POSES:
        transforms = forward_kinematics(robot.links, robot.joints, q_for_fraction(robot.joints, fraction))
        meshes, _ = world_meshes(robot.local_meshes, transforms)
        meshes = prepare_render_meshes(meshes, max_faces=60000)
        pose_dir = output_case / "rendered_images" / pose_name
        pose_dir.mkdir(parents=True, exist_ok=True)
        paths = []
        for azimuth, elevation, label in VIEWS:
            fig, axis = plt.subplots(figsize=(4, 4), dpi=110, facecolor="white")
            render_view(axis, meshes, view_rotation(azimuth, elevation))
            path = pose_dir / f"{label}.png"
            fig.savefig(path, bbox_inches="tight", facecolor="white")
            plt.close(fig)
            paths.append(str(path.resolve()))
        records.append({"pose": pose_name, "fraction": fraction, "views": paths})
    (output_case / "prompt.txt").write_text(BLIND_PROMPT + "\n", encoding="utf-8")
    metadata = {"case_id": source_case.name, "source_case": str(source_case.resolve()), "poses": records,
                "source_gt": "kept outside model inputs; used only for deterministic evaluation"}
    (output_case / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (output_case / "joint_parameters.json").write_text(json.dumps({"source": str(source_case / 'kinematic_gt.json')}, indent=2), encoding="utf-8")
    (output_case / "link_mapping.json").write_text(json.dumps({"source": str(source_case / 'kinematic_gt.json')}, indent=2), encoding="utf-8")
    return {"case_id": source_case.name, "source_case": str(source_case.resolve()), "poses": len(POSES), "images": len(POSES) * len(VIEWS)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=ROOT / "go_nogo3/data/dev15")
    parser.add_argument("--output-root", type=Path, default=ROOT / "go_nogo4/data/motion15")
    parser.add_argument("--manifest", type=Path, default=ROOT / "go_nogo4/results/motion15_manifest.csv")
    args = parser.parse_args()
    records = [render_case(case, args.output_root / case.name) for case in sorted(args.source_root.glob("dev_arm-*"))]
    if len(records) != 15:
        raise SystemExit(f"expected 15 source cases, found {len(records)}")
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with args.manifest.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
    print(json.dumps({"cases": len(records), "images_per_case": 12}, indent=2))


if __name__ == "__main__":
    main()
