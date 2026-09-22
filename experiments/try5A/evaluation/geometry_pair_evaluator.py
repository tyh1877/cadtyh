"""Evaluator-only body/final geometry metrics for A1 frozen candidates."""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/try5A"
sys.path.insert(0, str(HERE / "evaluation"))
sys.path.insert(0, str(HERE / "scripts"))

from geometry_holdout_evaluator import metric  # noqa: E402
from kinematics import rpy  # noqa: E402


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    job = load(sys.argv[1])
    source = ROOT / job["gt_urdf"]
    xml = ET.parse(source).getroot()
    mapping = load(HERE / "protocol/source_id_mapping.json")["links"]
    stable = {value: key for key, value in mapping.items()}
    mesh_root = source.parent.parent / "meshes/meshes_px100"
    rows = []
    gt_records = []
    for candidate in job["candidates"]:
        link_id = candidate["link_id"]
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
        if not any(record["link_id"] == link_id for record in gt_records):
            import hashlib
            gt_records.append({"link_id": link_id, "path": str(mesh_path.relative_to(ROOT)).replace("\\", "/"), "sha256": hashlib.sha256(mesh_path.read_bytes()).hexdigest()})
        for scope, key in (("refined_body_only", "body_stl"), ("final_assembled_link", "final_stl")):
            prediction = trimesh.load(ROOT / candidate[key], force="mesh", process=False)
            rows.append({
                "condition": candidate["condition"],
                "link_id": link_id,
                "scope": scope,
                **metric(reference, prediction, int(job["seed"])),
            })
    payload = {
        "schema_version": "robotcad_a1_dual_scope_geometry_v1",
        "status": "PASS",
        "evaluator_only": True,
        "sample_count": 10000,
        "seed": job["seed"],
        "gt_inputs": gt_records,
        "rows": rows,
    }
    Path(job["output"]).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "rows": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
