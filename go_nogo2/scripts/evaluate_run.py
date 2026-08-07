"""Validate one baseline run manifest, provenance, and deterministic metrics."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import jsonschema

from evaluate_prediction import evaluate, load_robot, write_json

VIEWS = ("front", "rear", "left", "right", "top", "iso")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def local_artifact(run_dir: Path, value: str | None) -> Path | None:
    if value is None:
        return None
    path = (run_dir / value).resolve()
    if path != run_dir and run_dir not in path.parents:
        raise ValueError(f"artifact escapes run directory: {value}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260808)
    args = parser.parse_args()

    case_dir, run_dir = args.case_dir.resolve(), args.run_dir.resolve()
    manifest_path = run_dir / "prediction_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)
    if manifest["case_id"] != case_dir.name:
        raise ValueError("prediction case_id does not match case directory")

    prompt_hash = sha256(case_dir / "prompt.txt")
    if manifest["prompt_sha256"] != prompt_hash:
        raise ValueError("prompt hash mismatch")
    expected_images = {view: sha256(case_dir / "renders" / f"{view}.png") for view in VIEWS}
    if manifest["image_sha256"] != expected_images:
        raise ValueError("image hash mismatch")

    evaluation_dir = run_dir / "evaluation"
    evaluation_dir.mkdir(parents=True, exist_ok=True)
    if manifest["status"] != "SUCCESS":
        outcome = {
            "status": manifest["status"], "simultaneous_success": False,
            "failure_patterns": ["invalid_cad"] if manifest["status"] == "FAILURE" else [],
            "error": manifest.get("error"),
        }
        write_json(evaluation_dir / "outcome.json", outcome)
        print(json.dumps(outcome, indent=2))
        return

    prediction_urdf = local_artifact(run_dir, manifest["artifacts"]["prediction_urdf"])
    if prediction_urdf is None or not prediction_urdf.is_file():
        raise FileNotFoundError("successful run has no prediction URDF")
    raw_response = local_artifact(run_dir, manifest["artifacts"]["raw_response"])
    if raw_response is None or not raw_response.is_file():
        raise FileNotFoundError("successful run has no preserved raw response")
    if manifest["provenance"]["output_sha256"] != sha256(prediction_urdf):
        raise ValueError("prediction output hash mismatch")

    gt = load_robot(case_dir / "urdf" / "model.urdf")
    pred = load_robot(prediction_urdf)
    geometry, assembly, kinematic, motion, outcome = evaluate(gt, pred, args.seed)
    for filename, payload in (
        ("geometry_metrics.json", geometry), ("assembly_metrics.json", assembly),
        ("kinematic_metrics.json", kinematic), ("motion_metrics.json", motion),
        ("outcome.json", outcome),
    ):
        write_json(evaluation_dir / filename, payload)
    print(json.dumps(outcome, indent=2))


if __name__ == "__main__":
    main()
