"""Build a blinded 15-case development set from Go/No-Go 1 audited robots."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
GO1_SCRIPTS = REPO_ROOT / "go_nogo1" / "scripts"
sys.path.insert(0, str(GO1_SCRIPTS))

from build_inventory import mesh_index, resolve_mesh  # noqa: E402
from prototype_feasibility import forward_kinematics, parse_model, pose_values  # noqa: E402

VIEWS = ("front", "rear", "left", "right", "top", "iso")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def blind_prompt() -> str:
    return (
        "Reconstruct the articulated robot shown in the supplied six reference views. "
        "Return an editable parametric CAD assembly and an explicit kinematic model. "
        "Infer all parts, assembly relations, joint types, joint axes, joint origins, "
        "and motion limits from visible evidence only. Do not assume access to hidden "
        "robot files, an identifier, a known model, or any declared part/DOF counts."
    )


def copy_case(row: dict[str, str], root: Path, dataset_root: Path, by_name: dict) -> dict[str, object]:
    entity_id = row["entity_id"]
    case_dir = root / f"dev_{entity_id}"
    for name in ("urdf", "meshes", "renders"):
        (case_dir / name).mkdir(parents=True, exist_ok=True)
    source_urdf = Path(row["urdf_path"]).resolve()
    tree = ET.parse(source_urdf)
    copied: dict[Path, Path] = {}
    mesh_records = []
    for index, node in enumerate(tree.getroot().iter("mesh"), start=1):
        source, method = resolve_mesh(node.get("filename", ""), source_urdf, dataset_root, by_name)
        if source is None:
            raise FileNotFoundError(f"{entity_id}: unresolved visual mesh")
        source = source.resolve()
        if source not in copied:
            target = case_dir / "meshes" / f"{len(copied)+1:03d}_{digest(source)[:10]}{source.suffix.lower()}"
            shutil.copy2(source, target)
            copied[source] = target
        target = copied[source]
        node.set("filename", f"../meshes/{target.name}")
        mesh_records.append({"source_sha256": digest(source), "local_file": target.name, "resolution": method, "index": index})
    local_urdf = case_dir / "urdf" / "model.urdf"
    tree.write(local_urdf, encoding="utf-8", xml_declaration=True)
    _, links, joints = parse_model(source_urdf)
    poses = []
    for label, values in (("canonical", {}), ("lower_quarter", pose_values(joints, -1)), ("upper_quarter", pose_values(joints, 1))):
        transforms = forward_kinematics(links, joints, values)
        poses.append({"name": label, "joint_values": values, "link_transforms": {key: value.tolist() for key, value in transforms.items()}})
    gt = {
        "case_id": case_dir.name, "source_entity_id": entity_id, "source_urdf_sha256": digest(source_urdf),
        "links": links,
        "joints": [{"name": j["name"], "type": j["type"], "parent": j["parent"], "child": j["child"],
                    "axis": np.asarray(j["axis"], dtype=float).tolist(), "origin_xyz": np.asarray(j["origin"][:3, 3], dtype=float).tolist(),
                    "origin_rpy": [0.0, 0.0, 0.0], "lower": j["lower"], "upper": j["upper"]} for j in joints],
        "poses": poses, "mesh_provenance": mesh_records,
    }
    (case_dir / "kinematic_gt.json").write_text(json.dumps(gt, indent=2), encoding="utf-8")
    prompt = blind_prompt()
    (case_dir / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
    render_dir = REPO_ROOT / "go_nogo1" / "results" / "prototype_feasibility" / "renders" / entity_id
    hashes = {}
    for view in VIEWS:
        choices = list(render_dir.glob(f"*_{view}.png"))
        if len(choices) != 1:
            raise ValueError(f"{entity_id}: expected one {view} render")
        target = case_dir / "renders" / f"{view}.png"
        shutil.copy2(choices[0], target)
        hashes[view] = digest(target)
    return {"case_id": case_dir.name, "entity_id": entity_id, "manufacturer": row["manufacturer"], "name": row["name"],
            "links": len(links), "joints": len(joints), "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "render_hashes": json.dumps(hashes, sort_keys=True), "gt_urdf_sha256": digest(local_urdf)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, default=REPO_ROOT / "go_nogo1/results/prototype_feasibility/case_audit.csv")
    parser.add_argument("--dataset-root", type=Path, default=REPO_ROOT / "go_nogo1/sources/urdf_files_dataset")
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT / "go_nogo3/data/dev15")
    parser.add_argument("--manifest", type=Path, default=REPO_ROOT / "go_nogo3/results/dev15_manifest.csv")
    parser.add_argument("--size", type=int, default=15)
    args = parser.parse_args()
    if not 15 <= args.size <= 20:
        raise SystemExit("development set size must be 15--20")
    with args.audit.open(encoding="utf-8-sig") as handle:
        audited = list(csv.DictReader(handle))
    selected = [row for row in audited if row["complete_case"].casefold() == "true"][:args.size]
    if len(selected) != args.size:
        raise SystemExit(f"only {len(selected)} complete audited robots available")
    args.output_root.mkdir(parents=True, exist_ok=True)
    _, by_name = mesh_index(args.dataset_root)
    records = [copy_case(row, args.output_root, args.dataset_root, by_name) for row in selected]
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with args.manifest.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader(); writer.writerows(records)
    print(json.dumps({"cases": len(records), "output_root": str(args.output_root.resolve())}, indent=2))


if __name__ == "__main__":
    main()
