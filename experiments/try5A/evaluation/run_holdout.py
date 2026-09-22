"""One-shot holdout orchestration for frozen RobotCAD candidates."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/try5A"
sys.path.insert(0, str(HERE / "evaluation"))
sys.path.insert(0, str(HERE / "scripts"))

from experiment_governance import acquire_holdout_lock, canonical_hash, dump_json, file_sha256, load_json  # noqa: E402
from freecad_runtime import python_runtime  # noqa: E402
from kinematics import canonical_q, fk, parse  # noqa: E402


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--confirm-one-shot", action="store_true")
    args = parser.parse_args()
    if not args.confirm_one_shot:
        raise RuntimeError("formal holdout requires explicit --confirm-one-shot authorization")
    result_root = Path(args.result_dir).resolve()
    config_path = Path(args.config).resolve()
    config = load_json(config_path)
    split = load_json(result_root / "case_split.json")
    candidate = load_json(result_root / "candidate_manifest.json")
    governance = load_json(result_root / "p1_governance_record.json")
    if governance.get("status") != "PASS" or not governance.get("formal_holdout_ready"):
        raise RuntimeError("P1 governance gate has not passed")
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
        "geometry_output": str(result_root / "holdout_geometry_metrics.csv"),
    }
    job_path = result_root / "holdout_evaluator_job.json"
    dump_json(job_path, job)
    process = subprocess.run([python_runtime(), str(HERE / "evaluation/mechanical/freecad_holdout_evaluator.py"), str(job_path)], cwd=ROOT, capture_output=True, text=True, timeout=3600)
    (result_root / "holdout_stdout.txt").write_text(process.stdout, encoding="utf-8")
    (result_root / "holdout_stderr.txt").write_text(process.stderr, encoding="utf-8")
    if process.returncode:
        raise RuntimeError(process.stderr or process.stdout)
    mechanical = load_json(job["output"])
    geometry_process = subprocess.run([sys.executable, str(HERE / "evaluation/geometry_holdout_evaluator.py"), str(job_path)], cwd=ROOT, capture_output=True, text=True, timeout=3600)
    (result_root / "holdout_geometry_stdout.txt").write_text(geometry_process.stdout, encoding="utf-8")
    (result_root / "holdout_geometry_stderr.txt").write_text(geometry_process.stderr, encoding="utf-8")
    if geometry_process.returncode:
        raise RuntimeError(geometry_process.stderr or geometry_process.stdout)

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
    manifest.update({"phase": "formal", "candidate_manifest_sha256": candidate["candidate_manifest_sha256"], "frozen_candidate_artifacts_verified": checked_artifacts, "holdout_lock_sha256": file_sha256(result_root / "holdout_evaluated.lock"), "holdout_worker_sha256": file_sha256(HERE / "evaluation/mechanical/freecad_holdout_evaluator.py"), "holdout_geometry_evaluator_sha256": file_sha256(HERE / "evaluation/geometry_holdout_evaluator.py"), "holdout_generator_invoked": False, "holdout_repair_invoked": False})
    dump_json(result_root / "manifest.json", manifest)
    print(json.dumps({"status": "HOLDOUT_COMPLETE_PENDING_INDEPENDENT_VALIDATION", "lock": lock, "conditions": [{"condition": item["condition"], "gcfr": item["gcfr"]} for item in mechanical["conditions"]]}, indent=2))


if __name__ == "__main__":
    main()
