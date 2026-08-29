"""Export canonical-pose GT articulated robots as assembled STL meshes for Fusion review."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import trimesh

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "go_nogo2" / "scripts"))
from evaluate_prediction import load_robot  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    output_root = ROOT / "try2" / "ground_truth_assembled"
    manifest_rows = []
    for row in csv.DictReader((ROOT / "try1" / "frozen_cases.csv").open(encoding="utf-8-sig")):
        case_id = row["case_id"]
        source_urdf = ROOT / "go_nogo3" / "data" / "dev15" / case_id / "urdf" / "model.urdf"
        robot = load_robot(source_urdf)
        assembled = robot.combined.copy()
        case_output = output_root / case_id
        case_output.mkdir(parents=True, exist_ok=True)
        stl = case_output / "ground_truth_assembled_home.stl"
        assembled.export(stl)
        metadata = {
            "case_id": case_id,
            "source_urdf": str(source_urdf.relative_to(ROOT)).replace("\\", "/"),
            "source_urdf_sha256": sha256(source_urdf),
            "pose": "canonical/home: all joint values = 0",
            "link_count": len(robot.links),
            "visual_link_count": len(robot.world_meshes),
            "vertices": int(len(assembled.vertices)),
            "faces": int(len(assembled.faces)),
            "assembled_stl": stl.name,
            "assembled_stl_sha256": sha256(stl),
        }
        (case_output / "manifest.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        manifest_rows.append(metadata)
        print(f"{case_id}: {len(assembled.vertices)} vertices, {len(assembled.faces)} faces", flush=True)
    tracked_manifest = ROOT / "try2" / "ground_truth_assembled_manifest.csv"
    with tracked_manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest_rows[0]))
        writer.writeheader()
        writer.writerows(manifest_rows)


if __name__ == "__main__":
    main()
