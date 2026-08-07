"""Validate evaluator identity and corruption directions on a fixed pilot case."""

from __future__ import annotations

import json
import hashlib
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

from evaluate_prediction import evaluate, load_robot

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_CASE = REPO_ROOT / "go_nogo2" / "data" / "pilot10" / "case_01_arm-fdadfa8bdd"
OUTPUT_ROOT = REPO_ROOT / "go_nogo2" / "runs" / "evaluator_validation"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def perpendicular(axis: np.ndarray) -> np.ndarray:
    axis = axis / np.linalg.norm(axis)
    basis = np.array([1.0, 0.0, 0.0]) if abs(axis[0]) < 0.8 else np.array([0.0, 1.0, 0.0])
    value = np.cross(axis, basis)
    return value / np.linalg.norm(value)


def corrupt_fixture() -> Path:
    target = OUTPUT_ROOT / "corrupt_case01"
    if target.exists():
        resolved = target.resolve()
        if resolved.parent != OUTPUT_ROOT.resolve():
            raise ValueError(f"unsafe validation fixture path: {resolved}")
        shutil.rmtree(resolved)
    shutil.copytree(SOURCE_CASE, target)
    urdf = target / "urdf" / "model.urdf"
    tree = ET.parse(urdf)
    root = tree.getroot()

    joints = root.findall("joint")
    removed = joints[-1]
    removed_child = removed.find("child").get("link")
    root.remove(removed)
    removed_link = next(link for link in root.findall("link") if link.get("name") == removed_child)
    root.remove(removed_link)

    for index, joint in enumerate(root.findall("joint")):
        if joint.get("type") not in {"fixed", "floating", "planar"}:
            axis_node = joint.find("axis")
            source = np.fromstring(axis_node.get("xyz", "1 0 0"), sep=" ")
            axis_node.set("xyz", " ".join(f"{x:.8f}" for x in perpendicular(source)))
            joint.set("type", "prismatic" if joint.get("type") != "prismatic" else "revolute")
            origin = joint.find("origin")
            xyz = np.fromstring(origin.get("xyz", "0 0 0"), sep=" ")
            xyz += np.array([0.20, -0.15, 0.10])
            origin.set("xyz", " ".join(f"{x:.8f}" for x in xyz))
        if index % 2 == 0:
            for mesh in joint.iter("mesh"):
                mesh.set("scale", "0.4 1.8 0.6")
    # Distort link visuals directly; joints normally do not contain meshes.
    for index, mesh in enumerate(root.iter("mesh")):
        mesh.set("scale", "0.45 1.65 0.70" if index % 2 == 0 else "1.40 0.55 1.25")
    tree.write(urdf, encoding="utf-8", xml_declaration=True)
    return urdf


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    gt_urdf = SOURCE_CASE / "urdf" / "model.urdf"
    gt = load_robot(gt_urdf)
    oracle = evaluate(gt, gt, 20260808)
    corrupted = evaluate(gt, load_robot(corrupt_fixture()), 20260808)
    g0, a0, k0, m0, o0 = oracle
    g1, a1, k1, m1, o1 = corrupted

    assert g0["chamfer"] == 0 and g0["hd95"] == 0 and g0["voxel_iou"] == 1
    assert g0["per_link_count"] > 0
    assert all(row["chamfer"] == 0 and row["hd95"] == 0 and row["voxel_iou"] == 1
               for row in g0["per_link"])
    assert a0["part_f1"] == a0["assembly_graph_f1"] == 1
    assert k0["joint_type_accuracy"] == 1 and k0["axis_error_degrees_median"] == 0
    assert m0["link_translation_error_normalized_median"] == 0
    assert o0["simultaneous_success"] is True

    assert g1["chamfer"] > g0["chamfer"] and g1["hd95"] > g0["hd95"]
    assert g1["voxel_iou"] < g0["voxel_iou"]
    assert "poor_curved_geometry" in o1["failure_patterns"]
    assert a1["part_recall"] < 1 and a1["assembly_graph_f1"] < 1
    assert k1["joint_type_accuracy"] < 1
    assert k1["axis_error_degrees_median"] > 0
    assert k1["joint_origin_error_normalized_median"] > 0
    assert m1["link_translation_error_normalized_median"] > 0
    assert o1["simultaneous_success"] is False

    report = {
        "oracle": {"geometry": g0, "assembly": a0, "kinematic": k0, "motion": m0, "outcome": o0},
        "corrupted": {"geometry": g1, "assembly": a1, "kinematic": k1, "motion": m1, "outcome": o1},
    }
    (OUTPUT_ROOT / "validation_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    contract_run = OUTPUT_ROOT / "oracle_contract_case01"
    if contract_run.exists():
        resolved = contract_run.resolve()
        if resolved.parent != OUTPUT_ROOT.resolve():
            raise ValueError(f"unsafe contract fixture path: {resolved}")
        shutil.rmtree(resolved)
    shutil.copytree(SOURCE_CASE / "urdf", contract_run / "urdf")
    shutil.copytree(SOURCE_CASE / "meshes", contract_run / "meshes")
    (contract_run / "raw_response.json").write_text("{}\n", encoding="utf-8")
    prediction_urdf = contract_run / "urdf" / "model.urdf"
    contract = {
        "schema_version": "1.0",
        "method": "evaluator_oracle",
        "case_id": SOURCE_CASE.name,
        "status": "SUCCESS",
        "prompt_sha256": sha256(SOURCE_CASE / "prompt.txt"),
        "image_sha256": {
            view: sha256(SOURCE_CASE / "renders" / f"{view}.png")
            for view in ("front", "rear", "left", "right", "top", "iso")
        },
        "attempts": 1,
        "latency_seconds": 0.0,
        "artifacts": {
            "raw_response": "raw_response.json",
            "prediction_urdf": "urdf/model.urdf",
            "link_mesh_directory": "meshes",
            "editable_cad": None,
        },
        "provenance": {
            "implementation_version": "oracle-validation",
            "model": None,
            "request_id": None,
            "output_sha256": sha256(prediction_urdf),
        },
        "error": None,
    }
    (contract_run / "prediction_manifest.json").write_text(
        json.dumps(contract, indent=2), encoding="utf-8"
    )
    subprocess.run([
        sys.executable, str(REPO_ROOT / "go_nogo2" / "scripts" / "evaluate_run.py"),
        "--case-dir", str(SOURCE_CASE), "--run-dir", str(contract_run),
        "--schema", str(REPO_ROOT / "go_nogo2" / "prediction_contract.schema.json"),
    ], check=True, capture_output=True, text=True)
    contract_outcome = json.loads(
        (contract_run / "evaluation" / "outcome.json").read_text(encoding="utf-8")
    )
    assert contract_outcome["simultaneous_success"] is True
    print("PASS: oracle exactness, corruption directions, and common run contract")


if __name__ == "__main__":
    main()
