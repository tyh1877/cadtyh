"""Validate the frozen Try-5A coarse baseline or a Try-5B candidate.

The default invocation is read-only and checks the committed evidence plus every
locally retained CAD artifact.  ``--candidate-results`` additionally applies the
frozen mechanical contract to a refined result directory.  Any hard failure is
reported as ROLLBACK and produces a non-zero exit status.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FREEZE_MANIFEST = ROOT / "experiments/try5A/results/try5a_frozen_coarse_stage/manifest.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def verify_frozen_files(manifest: dict, failures: list[str]) -> None:
    for relative, expected in manifest["frozen_sha256"].items():
        path = ROOT / relative
        check(path.is_file(), f"missing frozen file: {relative}", failures)
        if path.is_file():
            check(sha256(path) == expected, f"frozen file changed: {relative}", failures)


def verify_artifacts(baseline: Path, failures: list[str], require: bool) -> str:
    payload = load(baseline / "artifact_manifest.json")
    heavy = [item for item in payload["artifacts"] if item["path"].startswith("experiments/try5A/artifacts/")]
    heavy_present = sum((ROOT / item["path"]).is_file() for item in heavy)
    skip_missing_heavy = heavy_present == 0 and not require
    if heavy_present not in (0, len(heavy)):
        failures.append(f"partial heavy CAD artifact set: {heavy_present}/{len(heavy)} files present")
    for item in payload["artifacts"]:
        path = ROOT / item["path"]
        if skip_missing_heavy and item in heavy:
            continue
        check(path.is_file(), f"missing CAD artifact: {item['path']}", failures)
        if path.is_file():
            check(path.stat().st_size == item["bytes"], f"CAD size changed: {item['path']}", failures)
            check(sha256(path) == item["sha256"], f"CAD hash changed: {item['path']}", failures)
    return "HASH_VERIFIED" if heavy_present == len(heavy) else "MANIFEST_ONLY"


def semantic_contract(contract: dict) -> dict:
    """Fields that body refinement is forbidden to alter."""
    keys = (
        "joint_id", "joint_type", "parent", "child", "interface_family",
        "origin_xyz_mm", "origin_rpy_rad", "axis_parent", "axis_child",
        "clearance_mm", "allowed_contact_volume_mm3", "allowed_contact_role",
        "motion_range", "motion_range_m", "allowed_dof", "constrained_dof",
        "parent_rigid_group", "child_rigid_group", "forbidden_fusion",
        "fixed_connection_strategy", "mimic", "virtual_child",
        "swept_clearance_policy", "motion_clearance_spec",
    )
    return {key: contract.get(key) for key in keys}


def verify_result(result_dir: Path, baseline: Path, policy: dict, failures: list[str]) -> None:
    required = (
        "summary.json", "validation.json", "kinematic_skeleton.json",
        "link_realization_classification.json", "motion_interface_contracts.json",
        "motion_clearance_specs.json", "round3_verified_result.json",
        "mechanical_meaningfulness_audit.json",
    )
    missing = [name for name in required if not (result_dir / name).is_file()]
    if missing:
        failures.extend(f"missing result evidence: {result_dir / name}" for name in missing)
        return

    summary = load(result_dir / "summary.json")
    validation = load(result_dir / "validation.json")
    verified = load(result_dir / "round3_verified_result.json")
    meaningful = load(result_dir / "mechanical_meaningfulness_audit.json")
    baseline_summary = load(baseline / "summary.json")

    check(summary.get("status") == "COMPLETE", "result status is not COMPLETE", failures)
    check(validation.get("status") == "PASS", "validation status is not PASS", failures)
    for gate in policy["required_hard_gates"]:
        check(summary.get("hard_gates", {}).get(gate) is True, f"hard gate failed: {gate}", failures)

    check(meaningful.get("meaningless_patch_count") == 0, "meaningless patch count is not zero", failures)
    check(all(item.get("valid") and not item.get("floating") for item in verified.get("link_audit", [])),
          "BICR/floating audit failed", failures)
    check(len(verified.get("link_audit", [])) == policy["physical_link_count"],
          "physical link denominator changed", failures)
    check(all(item.get("pass") for item in verified.get("mechanical_dof_audit", [])),
          "exact mechanical DOF validation failed", failures)

    candidate_jr3 = {item["joint_id"]: item.get("jr3", 0.0) for item in summary.get("per_joint", [])}
    baseline_jr3 = {item["joint_id"]: item["jr3"] for item in baseline_summary["per_joint"]}
    for joint_id, expected in baseline_jr3.items():
        check(candidate_jr3.get(joint_id, -1.0) >= expected,
              f"JR3 regression at {joint_id}: {candidate_jr3.get(joint_id)} < {expected}", failures)

    gcfr_floor = max(policy["gcfr_absolute_floor"], baseline_summary["final_gcfr"] - policy["gcfr_max_absolute_drop"])
    check(summary.get("final_gcfr", -1.0) >= gcfr_floor,
          f"severe GCFR regression: {summary.get('final_gcfr')} < {gcfr_floor}", failures)

    check(load(result_dir / "kinematic_skeleton.json") == load(baseline / "kinematic_skeleton.json"),
          "sanitized-URDF frame/FK authority changed", failures)
    check(load(result_dir / "link_realization_classification.json") == load(baseline / "link_realization_classification.json"),
          "physical/virtual classification changed", failures)
    check(load(result_dir / "motion_clearance_specs.json") == load(baseline / "motion_clearance_specs.json"),
          "swept-clearance specification changed", failures)

    baseline_contracts = [semantic_contract(item) for item in load(baseline / "motion_interface_contracts.json")]
    candidate_contracts = [semantic_contract(item) for item in load(result_dir / "motion_interface_contracts.json")]
    check(candidate_contracts == baseline_contracts, "Motion-Aware Interface Contract changed", failures)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-results", type=Path,
                        help="Try-5B result directory to gate against the frozen baseline")
    parser.add_argument("--require-artifacts", action="store_true",
                        help="fail if the ignored heavy CAD artifacts are not retained in this checkout")
    args = parser.parse_args()

    manifest = load(FREEZE_MANIFEST)
    baseline = ROOT / manifest["baseline_results"]
    failures: list[str] = []
    verify_frozen_files(manifest, failures)
    verify_result(baseline, baseline, manifest["try5b_hard_constraint_policy"], failures)
    artifact_status = verify_artifacts(baseline, failures, args.require_artifacts)
    if args.candidate_results:
        candidate = args.candidate_results.resolve()
        verify_result(candidate, baseline, manifest["try5b_hard_constraint_policy"], failures)

    status = "PASS" if not failures else "ROLLBACK"
    print(json.dumps({
        "experiment": "Try-5A frozen coarse-stage revalidation",
        "status": status,
        "baseline": manifest["baseline_results"],
        "candidate": str(args.candidate_results) if args.candidate_results else None,
        "artifact_status": artifact_status,
        "failures": failures,
    }, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
