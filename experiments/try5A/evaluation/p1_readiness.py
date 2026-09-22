"""Non-evaluating P1 readiness gate for the Try-5B.1-A1 formal holdout."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/try5A"
sys.path.insert(0, str(HERE / "evaluation"))
sys.path.insert(0, str(HERE / "scripts"))

from experiment_governance import audit_condition_parity, canonical_hash, dump_json, file_sha256, load_json  # noqa: E402
from freecad_runtime import python_runtime  # noqa: E402
from validate_experiment import validate_bundle  # noqa: E402


FORMAL_OUTPUTS = (
    "holdout_evaluated.lock",
    "holdout_evaluator_job.json",
    "holdout_mechanical_metrics.json",
    "holdout_geometry_metrics.csv",
    "holdout_stdout.txt",
    "holdout_stderr.txt",
    "holdout_geometry_stdout.txt",
    "holdout_geometry_stderr.txt",
)


def git(*arguments):
    process = subprocess.run(["git", *arguments], cwd=ROOT, capture_output=True, text=True, check=True)
    return process.stdout.strip()


def verify_candidate_manifest(candidate):
    expected = candidate.get("candidate_manifest_sha256")
    unsigned = dict(candidate)
    unsigned.pop("candidate_manifest_sha256", None)
    records = []
    hashes_ok = bool(expected) and canonical_hash(unsigned) == expected
    for condition, condition_data in candidate["conditions"].items():
        for artifact_type in ("pilot_fcstd", "pilot_stl"):
            expected_hashes = condition_data[artifact_type + "_sha256"]
            for link_id, relative_path in condition_data[artifact_type].items():
                path = ROOT / relative_path
                actual = file_sha256(path) if path.is_file() else None
                records.append({
                    "condition": condition,
                    "link_id": link_id,
                    "artifact_type": artifact_type,
                    "path": relative_path,
                    "sha256": actual,
                    "matches_manifest": actual == expected_hashes.get(link_id),
                })
    return hashes_ok and all(item["matches_manifest"] for item in records), records


def evaluator_gt_inputs():
    source = ROOT / "go_nogo1/sources/urdf_files_dataset/urdf_files/robotics-toolbox/xacro_generated/interbotix_descriptions/urdf/px100.urdf"
    mapping = load_json(HERE / "protocol/source_id_mapping.json")["links"]
    stable = {value: key for key, value in mapping.items()}
    xml = ET.parse(source).getroot()
    mesh_root = source.parent.parent / "meshes/meshes_px100"
    paths = [source]
    for link_id in ("L03", "L04", "L07"):
        link = next(item for item in xml.findall("link") if item.attrib["name"] == stable[link_id])
        paths.append(mesh_root / Path(link.find("visual/geometry/mesh").attrib["filename"]).name)
    return [{"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": file_sha256(path)} for path in paths]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--analysis-plan", required=True)
    args = parser.parse_args()

    result_root = Path(args.result_dir).resolve()
    config_path = Path(args.config).resolve()
    analysis_path = Path(args.analysis_plan).resolve()
    config = load_json(config_path)
    analysis = load_json(analysis_path)
    manifest = load_json(result_root / "manifest.json")
    split = load_json(result_root / "case_split.json")
    candidate = load_json(result_root / "candidate_manifest.json")
    validation = load_json(result_root / "validation.json")
    holdout_log = load_json(result_root / "holdout_evaluation_log.json")
    classification = load_json(HERE / "results/try5a5/link_realization_classification.json")

    candidate_ok, candidate_records = verify_candidate_manifest(candidate)
    pilot_ids = set(config["shared"]["pilot_links"])
    physical = [item["link_id"] for item in classification if item["realization_type"] != "virtual_frame"]
    frozen_root = ROOT / candidate["frozen_nonpilot_root"]
    nonpilot_records = []
    for link_id in physical:
        if link_id in pilot_ids:
            continue
        path = frozen_root / link_id / "model.FCStd"
        nonpilot_records.append({
            "link_id": link_id,
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": file_sha256(path) if path.is_file() else None,
        })

    freecad_python = Path(python_runtime())
    freecad_probe = subprocess.run(
        [str(freecad_python), "-c", "import FreeCAD, json; print(json.dumps(FreeCAD.Version()))"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    script_paths = {
        "development_runner": HERE / "scripts/run_try5b1.py",
        "development_worker": HERE / "evaluation/mechanical/freecad_link_refinement.py",
        "holdout_orchestrator": HERE / "evaluation/run_holdout.py",
        "holdout_mechanical_evaluator": HERE / "evaluation/mechanical/freecad_holdout_evaluator.py",
        "holdout_geometry_evaluator": HERE / "evaluation/geometry_holdout_evaluator.py",
        "exact_evaluator": HERE / "scripts/freecad_motion_realization.py",
        "independent_validator": HERE / "evaluation/validate_experiment.py",
        "governance": HERE / "evaluation/experiment_governance.py",
        "readiness_gate": Path(__file__).resolve(),
    }
    inputs = {
        "experiment_config": config_path,
        "analysis_plan": analysis_path,
        "case_split": result_root / "case_split.json",
        "candidate_manifest": result_root / "candidate_manifest.json",
        "interface_contracts": ROOT / config["shared"]["frozen_interface_contracts"],
        "frozen_configuration_source": ROOT / config["shared"]["frozen_configuration_source"],
        "sanitized_urdf": ROOT / config["shared"]["sanitized_urdf"],
        "link_classification": HERE / "results/try5a5/link_realization_classification.json",
    }
    environment = {
        "schema_version": "robotcad_p1_environment_manifest_v1",
        "implementation_commit": git("rev-parse", "HEAD"),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "origin_commit": git("rev-parse", "origin/main"),
        "platform": platform.platform(),
        "python": {"executable": str(Path(sys.executable).resolve()), "version": platform.python_version()},
        "packages": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "trimesh")},
        "freecad": {
            "executable": str(freecad_python),
            "probe_returncode": freecad_probe.returncode,
            "version": freecad_probe.stdout.strip(),
            "stderr": freecad_probe.stderr.strip(),
        },
        "disk_free_at_least_1_gib": shutil.disk_usage(result_root).free >= 1024 ** 3,
        "scripts": {name: {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": file_sha256(path)} for name, path in script_paths.items()},
        "inputs": {name: {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": file_sha256(path)} for name, path in inputs.items()},
        "pilot_candidates": candidate_records,
        "frozen_nonpilot_fcstd": nonpilot_records,
        "evaluator_only_gt_inputs": evaluator_gt_inputs(),
    }
    dump_json(result_root / "p1_environment_manifest.json", environment)

    mechanical_source = script_paths["holdout_mechanical_evaluator"].read_text(encoding="utf-8")
    geometry_source = script_paths["holdout_geometry_evaluator"].read_text(encoding="utf-8")
    orchestrator_source = script_paths["holdout_orchestrator"].read_text(encoding="utf-8")
    relevant_paths = [str(path.relative_to(ROOT)) for path in (*script_paths.values(), *inputs.values())]
    relevant_diff = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *relevant_paths], cwd=ROOT).returncode
    formal_outputs_absent = all(not (result_root / name).exists() for name in FORMAL_OUTPUTS)
    checks = {
        "development_validation_pass": validation.get("status") == "PASS" and validation.get("phase") == "development",
        "holdout_event_count_zero": holdout_log.get("events") == [] and all(value == 0 for value in validation.get("holdout_evaluation_counts", {}).values()),
        "formal_outputs_absent": formal_outputs_absent,
        "config_matches_snapshot": config == load_json(result_root / "experiment_config_snapshot.json"),
        "config_hash_matches_manifest": file_sha256(config_path) == manifest["config_file_sha256"] and canonical_hash(config) == manifest["config_canonical_sha256"],
        "split_hash_matches_manifest": split["split_sha256"] == manifest["case_split_sha256"],
        "split_counts_and_lock_policy": split["development"]["count"] == 96 and split["holdout"]["count"] == 32 and split["holdout"]["locked"] and split["holdout"]["evaluation_limit_per_condition"] == 1,
        "condition_parity_pass": audit_condition_parity(config).get("status") == "PASS",
        "development_implementation_unchanged": file_sha256(script_paths["development_runner"]) == manifest["runner_sha256"] and file_sha256(script_paths["development_worker"]) == manifest["worker_sha256"],
        "candidate_manifest_and_pilot_hashes_pass": candidate_ok,
        "all_nonpilot_fcstd_present": len(nonpilot_records) == len(physical) - len(pilot_ids) and all(item["sha256"] for item in nonpilot_records),
        "analysis_plan_matches_experiment": analysis.get("experiment_id") == config["experiment_id"] and analysis.get("comparison", {}).get("paired_holdout_configuration_count") == split["holdout"]["count"],
        "analysis_forbids_case_drop_and_post_holdout_tuning": analysis.get("analysis_rules", {}).get("drop_failed_cases") is False and analysis.get("analysis_rules", {}).get("post_holdout_candidate_change") is False and analysis.get("analysis_rules", {}).get("post_holdout_code_or_metric_change") is False,
        "one_shot_failure_policy_frozen": analysis.get("failure_policy", {}).get("crash_or_interrupt_consumes_attempt") is True and analysis.get("failure_policy", {}).get("delete_lock_to_retry") is False,
        "venv_runtime_active": Path(sys.executable).resolve() == (ROOT / ".venv/Scripts/python.exe").resolve(),
        "freecad_runtime_available": freecad_probe.returncode == 0,
        "runtime_capacity_available": environment["disk_free_at_least_1_gib"],
        "git_head_matches_origin": environment["implementation_commit"] == environment["origin_commit"],
        "formal_inputs_have_no_uncommitted_diff": relevant_diff == 0,
        "mechanical_evaluator_has_no_generator_or_candidate_controller_import": "freecad_link_refinement" not in mechanical_source and "CandidateController" not in mechanical_source,
        "geometry_evaluator_has_no_generator_import": "run_try5b1" not in geometry_source and "freecad_link_refinement" not in geometry_source,
        "orchestrator_has_no_generator_import": "run_try5b1" not in orchestrator_source and "freecad_link_refinement" not in orchestrator_source,
        "explicit_one_shot_confirmation_enforced": "--confirm-one-shot" in orchestrator_source,
    }
    readiness = {
        "schema_version": "robotcad_p1_readiness_v1",
        "experiment_id": config["experiment_id"],
        "status": "PASS" if all(checks.values()) else "FAIL",
        "holdout_evaluated": False,
        "holdout_metrics_read": False,
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "environment_manifest_sha256": file_sha256(result_root / "p1_environment_manifest.json"),
        "analysis_plan_sha256": file_sha256(analysis_path),
    }
    dump_json(result_root / "p1_readiness.json", readiness)
    governance = {
        "schema_version": "robotcad_p1_governance_record_v1",
        "experiment_id": config["experiment_id"],
        "status": readiness["status"],
        "formal_holdout_ready": readiness["status"] == "PASS",
        "formal_holdout_executed": False,
        "implementation_commit": environment["implementation_commit"],
        "readiness_sha256": file_sha256(result_root / "p1_readiness.json"),
        "environment_manifest_sha256": readiness["environment_manifest_sha256"],
        "analysis_plan_sha256": readiness["analysis_plan_sha256"],
        "required_execution_flag": "--confirm-one-shot",
        "next_action": "Run the formal holdout exactly once only after explicit user authorization.",
    }
    dump_json(result_root / "p1_governance_record.json", governance)
    print(json.dumps(governance, indent=2))
    return 0 if readiness["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
