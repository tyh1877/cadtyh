"""Build the frozen ten-case Go/No-Go 2 pilot dataset from Go/No-Go 1."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
GO1_SCRIPTS = REPO_ROOT / "go_nogo1" / "scripts"
sys.path.insert(0, str(GO1_SCRIPTS))

from build_inventory import mesh_index, resolve_mesh  # noqa: E402
from prototype_feasibility import (  # noqa: E402
    forward_kinematics,
    parse_model,
    pose_values,
)

PILOT_SIZE = 10
VIEWS = ("front", "rear", "left", "right", "top", "iso")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def select_cases(audit: pd.DataFrame) -> pd.DataFrame:
    passed = audit.loc[audit["complete_case"].astype(str).str.casefold() == "true"].copy()
    passed = passed.sort_values("prototype_index", kind="stable")
    selected = passed.drop_duplicates("manufacturer", keep="first").head(PILOT_SIZE).copy()
    if len(selected) != PILOT_SIZE:
        raise ValueError(f"need {PILOT_SIZE} complete manufacturers, found {len(selected)}")
    selected.insert(0, "pilot_index", range(1, PILOT_SIZE + 1))
    return selected


def jsonable_joint(joint: dict) -> dict:
    return {
        "name": joint["name"],
        "type": joint["type"],
        "parent": joint["parent"],
        "child": joint["child"],
        "axis": np.asarray(joint["axis"], dtype=float).tolist(),
        "origin_xyz": np.asarray(joint["origin"][:3, 3], dtype=float).tolist(),
        "origin_matrix": np.asarray(joint["origin"], dtype=float).tolist(),
        "lower": joint["lower"],
        "upper": joint["upper"],
    }


def write_local_urdf(source_urdf: Path, destination: Path, meshes_dir: Path,
                     dataset_root: Path, by_name: dict) -> list[dict]:
    tree = ET.parse(source_urdf)
    records = []
    copied_by_source = {}
    for index, mesh_node in enumerate(tree.getroot().iter("mesh"), start=1):
        uri = mesh_node.get("filename", "")
        source, method = resolve_mesh(uri, source_urdf, dataset_root, by_name)
        if source is None:
            raise FileNotFoundError(f"unresolved mesh reference: {uri}")
        source = source.resolve()
        if source not in copied_by_source:
            token = hashlib.sha256(str(source).encode("utf-8")).hexdigest()[:10]
            local_name = f"{len(copied_by_source) + 1:03d}_{token}{source.suffix.lower()}"
            local_path = meshes_dir / local_name
            shutil.copy2(source, local_path)
            copied_by_source[source] = local_path
        local_path = copied_by_source[source]
        mesh_node.set("filename", f"../meshes/{local_path.name}")
        records.append({
            "reference_index": index,
            "original_uri": uri,
            "source_path": str(source),
            "source_sha256": sha256(source),
            "local_file": local_path.name,
            "resolution_method": method,
        })
    destination.parent.mkdir(parents=True, exist_ok=True)
    tree.write(destination, encoding="utf-8", xml_declaration=True)
    return records


def build_prompt(row, links: list[str], joints: list[dict]) -> str:
    actuated = [j for j in joints if j["type"] in {"revolute", "continuous", "prismatic"}]
    return (
        f"Generate an editable articulated CAD model of a {row.manufacturer} {row.name} robot arm. "
        f"The assembly has {len(links)} links, {len(joints)} total joints, and {len(actuated)} actuated DOF. "
        "Use the six supplied reference views to recover link geometry and proportions. "
        "Return separate link geometry plus a rooted assembly tree. For every joint return parent, child, "
        "joint type, local axis, origin transform, and motion limits. Preserve the complete raw generation "
        "and export the common prediction contract; do not copy or infer from any hidden URDF."
    )


def build_case(row, output_root: Path, go1_results: Path, dataset_root: Path,
               by_name: dict) -> dict:
    case_id = f"case_{int(row.pilot_index):02d}_{row.entity_id}"
    case_dir = output_root / case_id
    for child in ("urdf", "meshes", "renders"):
        (case_dir / child).mkdir(parents=True, exist_ok=True)

    source_urdf = Path(row.urdf_path).resolve()
    local_urdf = case_dir / "urdf" / "model.urdf"
    mesh_records = write_local_urdf(
        source_urdf, local_urdf, case_dir / "meshes", dataset_root, by_name
    )
    _, links, joints = parse_model(source_urdf)
    q_negative, q_positive = pose_values(joints, -1), pose_values(joints, 1)
    pose_specs = [
        ("neutral", {}),
        ("lower_quarter", q_negative),
        ("upper_quarter", q_positive),
    ]
    poses = []
    for pose_name, q in pose_specs:
        transforms = forward_kinematics(links, joints, q)
        poses.append({
            "name": pose_name,
            "joint_values": q,
            "link_transforms": {name: matrix.tolist() for name, matrix in transforms.items()},
        })
    gt = {
        "case_id": case_id,
        "entity_id": row.entity_id,
        "manufacturer": row.manufacturer,
        "name": row.name,
        "source_urdf": str(source_urdf),
        "source_urdf_sha256": sha256(source_urdf),
        "links": links,
        "joints": [jsonable_joint(joint) for joint in joints],
        "poses": poses,
        "mesh_provenance": mesh_records,
    }
    (case_dir / "kinematic_gt.json").write_text(
        json.dumps(gt, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    prompt = build_prompt(row, links, joints)
    (case_dir / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")

    source_render_dir = go1_results / "renders" / row.entity_id
    render_hashes = {}
    for view in VIEWS:
        matches = sorted(source_render_dir.glob(f"*_{view}.png"))
        if len(matches) != 1:
            raise ValueError(f"expected one {view} render for {row.entity_id}, found {len(matches)}")
        target = case_dir / "renders" / f"{view}.png"
        shutil.copy2(matches[0], target)
        render_hashes[view] = sha256(target)

    return {
        "pilot_index": int(row.pilot_index),
        "case_id": case_id,
        "entity_id": row.entity_id,
        "manufacturer": row.manufacturer,
        "name": row.name,
        "links": len(links),
        "joints": len(joints),
        "actuated_dof": sum(j["type"] in {"revolute", "continuous", "prismatic"} for j in joints),
        "local_urdf": str(local_urdf.resolve()),
        "local_urdf_sha256": sha256(local_urdf),
        "mesh_files": len({record["local_file"] for record in mesh_records}),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "render_hashes": json.dumps(render_hashes, sort_keys=True),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--go1-results", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    audit = pd.read_csv(args.audit)
    selected = select_cases(audit)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    expected = {f"case_{int(row.pilot_index):02d}_{row.entity_id}" for row in selected.itertuples()}
    for child in args.output_dir.iterdir():
        if child.is_dir() and child.name not in expected:
            resolved = child.resolve()
            if resolved.parent != args.output_dir.resolve():
                raise ValueError(f"unsafe stale case path: {resolved}")
            shutil.rmtree(resolved)

    _, by_name = mesh_index(args.dataset_root)
    records = [
        build_case(row, args.output_dir, args.go1_results, args.dataset_root.resolve(), by_name)
        for row in selected.itertuples()
    ]
    manifest = pd.DataFrame(records)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(args.manifest, index=False, encoding="utf-8-sig")
    print(manifest[["pilot_index", "manufacturer", "name", "links", "joints", "actuated_dof"]].to_string(index=False))
    print(f"built {len(manifest)} cases at {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
