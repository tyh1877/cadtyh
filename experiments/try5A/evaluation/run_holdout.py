"""One-shot holdout orchestration for frozen RobotCAD candidates."""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/try5A"
sys.path.insert(0, str(HERE / "evaluation"))
sys.path.insert(0, str(HERE / "scripts"))

from experiment_governance import acquire_holdout_lock, canonical_hash, dump_json, file_sha256, load_json  # noqa: E402
from freecad_runtime import python_runtime  # noqa: E402
from kinematics import canonical_q, fk, parse, rpy  # noqa: E402
from run_try5b1 import metric, PILOTS  # noqa: E402


def verify_frozen_candidates(candidate_manifest):
    expected = candidate_manifest.get("candidate_manifest_sha256")
    unsigned = dict(candidate_manifest)
    unsigned.pop("candidate_manifest_sha256", None)
    if not expected or canonical_hash(unsigned) != expected:
        raise RuntimeError("candidate manifest self-hash mismatch")
    checked = 0
    for condition, condition_data in candidate_manifest["conditions"].items():
        for artifact_type in ("pilot_fcstd", "pilot_stl"):
            hashes = condition_data[artifact_type + "_sha256"]
            for link_id, relative_path in condition_data[artifact_type].items():
                path = ROOT / relative_path
                if not path.is_file():
                    raise FileNotFoundError(f"missing frozen candidate: {condition}/{link_id}/{artifact_type}")
                if file_sha256(path) != hashes[link_id]:
                    raise RuntimeError(f"frozen candidate hash mismatch: {condition}/{link_id}/{artifact_type}")
                checked += 1
    return checked


def per_joint_configurations(fractions):
    links, joints = parse(HERE / "inputs/sanitized_urdf/px100_sanitized.urdf")
    result = {}
    for joint in [item for item in joints if item["joint_type"] in ("revolute", "continuous", "prismatic")]:
        source = next(item for item in joints if item["joint_id"] == joint["mimic"]["joint"]) if joint["mimic"] else joint
        lo, hi = (-math.pi, math.pi) if source["joint_type"] == "continuous" else (source["limits"]["lower"], source["limits"]["upper"])
        rows = []
        for fraction in fractions:
            q = canonical_q(joints)
            q[source["joint_id"]] = lo + fraction * (hi - lo)
            for mimic in [item for item in joints if item.get("mimic")]:
                q[mimic["joint_id"]] = q[mimic["mimic"]["joint"]] * mimic["mimic"].get("multiplier", 1) + mimic["mimic"].get("offset", 0)
            _, world, _ = fk(links, joints, q)
            rows.append({"config_id": f"{joint['joint_id']}_holdout_{fraction:.2f}", "q": q, "world_transforms": {key: value.tolist() for key, value in world.items()}, "ee_world": world["L11"].tolist(), "active_joint": joint["joint_id"], "active_fraction": fraction})
        result[joint["joint_id"]] = rows
    return result


def geometry_holdout(candidate_manifest, output_csv):
    source = ROOT / "go_nogo1/sources/urdf_files_dataset/urdf_files/robotics-toolbox/xacro_generated/interbotix_descriptions/urdf/px100.urdf"
    xml = ET.parse(source).getroot()
    mapping = load_json(HERE / "protocol/source_id_mapping.json")["links"]
    stable = {value: key for key, value in mapping.items()}
    mesh_root = source.parent.parent / "meshes/meshes_px100"
    rows = []
    for condition, condition_data in candidate_manifest["conditions"].items():
        for index, link_id in enumerate(PILOTS):
            source_name = stable[link_id]
            link = next(item for item in xml.findall("link") if item.attrib["name"] == source_name)
            visual = link.find("visual")
            origin = visual.find("origin")
            xyz = np.asarray([float(value) for value in origin.attrib.get("xyz", "0 0 0").split()]) * 1000
            rotation = np.asarray([float(value) for value in origin.attrib.get("rpy", "0 0 0").split()])
            mesh_path = mesh_root / Path(visual.find("geometry/mesh").attrib["filename"]).name
            gt = trimesh.load(mesh_path, force="mesh", process=False)
            transform = np.eye(4)
            transform[:3, :3] = rpy(rotation)
            transform[:3, 3] = xyz
            gt.apply_transform(transform)
            prediction = trimesh.load(ROOT / condition_data["pilot_stl"][link_id], force="mesh", process=False)
            rows.append({"condition": condition, "link_id": link_id, **metric(gt, prediction, 12000 + index)})
    with Path(output_csv).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", required=True)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    result_root = Path(args.result_dir).resolve()
    config_path = Path(args.config).resolve()
    config = load_json(config_path)
    split = load_json(result_root / "case_split.json")
    candidate = load_json(result_root / "candidate_manifest.json")
    checked_artifacts = verify_frozen_candidates(candidate)
    manifest = load_json(result_root / "manifest.json")
    if manifest["config_file_sha256"] != file_sha256(config_path):
        raise RuntimeError("tracked config no longer matches the frozen development run")
    if manifest["case_split_sha256"] != split["split_sha256"]:
        raise RuntimeError("case split no longer matches the frozen development run")
    lock = acquire_holdout_lock(result_root / "holdout_evaluated.lock", config["experiment_id"], file_sha256(config_path))

    all_configurations = load_json(ROOT / config["shared"]["frozen_configuration_source"])["configurations"]
    holdout_ids = set(split["holdout"]["case_ids"])
    holdout = [item for item in all_configurations if item["config_id"] in holdout_ids]
    if len(holdout) != split["holdout"]["count"]:
        raise RuntimeError("holdout case count mismatch")
    per_joint = per_joint_configurations(config["shared"]["per_joint_split"]["holdout_fractions"])
    job = {
        "mode": "ONE_SHOT_HOLDOUT_EXACT",
        "candidate_manifest": str(result_root / "candidate_manifest.json"),
        "holdout_configurations": holdout,
        "holdout_per_joint": per_joint,
        "output": str(result_root / "holdout_mechanical_metrics.json"),
    }
    job_path = result_root / "holdout_evaluator_job.json"
    dump_json(job_path, job)
    process = subprocess.run([python_runtime(), str(HERE / "evaluation/mechanical/freecad_holdout_evaluator.py"), str(job_path)], cwd=ROOT, capture_output=True, text=True, timeout=3600)
    (result_root / "holdout_stdout.txt").write_text(process.stdout, encoding="utf-8")
    (result_root / "holdout_stderr.txt").write_text(process.stderr, encoding="utf-8")
    if process.returncode:
        raise RuntimeError(process.stderr or process.stdout)
    mechanical = load_json(job["output"])
    geometry_holdout(candidate, result_root / "holdout_geometry_metrics.csv")

    events = [{"condition": item["condition"], "case_count": item["configuration_count"], "followed_by_tuning": False, "lock_sha256": file_sha256(result_root / "holdout_evaluated.lock")} for item in mechanical["conditions"]]
    dump_json(result_root / "holdout_evaluation_log.json", {"events": events})
    accounting = load_json(result_root / "failure_accounting.json")
    by_condition = {item["condition"]: item for item in mechanical["conditions"]}
    for row in accounting["conditions"]:
        holdout_result = by_condition[row["condition"]]
        row["requested_cases"] += holdout_result["configuration_count"]
        row["completed_cases"] += holdout_result["configuration_count"]
        row["mechanically_invalid_cases"] += holdout_result["invalid_configurations"]
    dump_json(result_root / "failure_accounting.json", accounting)

    claims = load_json(result_root / "claim_ledger.json")
    for index, item in enumerate(mechanical["conditions"]):
        claims["claims"].append({"claim_id": f"holdout_denominator_{item['condition']}", "hard": True, "evidence_type": "computed", "artifact": "holdout_mechanical_metrics.json", "field": f"conditions.{index}.configuration_count", "operator": "eq", "expected": split["holdout"]["count"]})
    dump_json(result_root / "claim_ledger.json", claims)
    manifest.update({"phase": "formal", "candidate_manifest_sha256": candidate["candidate_manifest_sha256"], "frozen_candidate_artifacts_verified": checked_artifacts, "holdout_lock_sha256": file_sha256(result_root / "holdout_evaluated.lock"), "holdout_worker_sha256": file_sha256(HERE / "evaluation/mechanical/freecad_holdout_evaluator.py"), "holdout_generator_invoked": False, "holdout_repair_invoked": False})
    dump_json(result_root / "manifest.json", manifest)
    print(json.dumps({"status": "HOLDOUT_COMPLETE_PENDING_INDEPENDENT_VALIDATION", "lock": lock, "conditions": [{"condition": item["condition"], "gcfr": item["gcfr"]} for item in mechanical["conditions"]]}, indent=2))


if __name__ == "__main__":
    main()
