"""Run the frozen deterministic evaluator and CAD-URDF frame checks for Go/No-Go 3."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "go_nogo2" / "scripts"))
from evaluate_prediction import angle_error_degrees, evaluate, load_robot, write_json  # noqa: E402


def frame_consistency(run_dir: Path) -> dict:
    draft_path, urdf_path = run_dir / "joint_frame_draft.json", run_dir / "urdf" / "model.urdf"
    if not draft_path.is_file() or not urdf_path.is_file():
        return {"status": "NOT_APPLICABLE", "matched_joints": 0}
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    generated = load_robot(urdf_path)
    by_name = {joint["name"]: joint for joint in generated.joints}
    axis, origin = [], []
    for joint in draft["joints"]:
        generated_joint = by_name.get(joint["name"])
        if generated_joint is None:
            continue
        if joint["type"] != "fixed" and generated_joint["type"] != "fixed":
            axis.append(angle_error_degrees(np.asarray(joint["axis"]), generated_joint["axis"]))
        origin.append(float(np.linalg.norm(np.asarray(joint["origin_xyz"], dtype=float) / 1000 - generated_joint["origin"][:3, 3])))
    return {"status": "OK", "matched_joints": len(axis), "joint_axis_error_degrees_median": float(np.median(axis)) if axis else None,
            "joint_origin_error_median_meters": float(np.median(origin)) if origin else None}


def one(case_dir: Path, run_dir: Path) -> dict:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    output = run_dir / "evaluation"
    output.mkdir(exist_ok=True)
    if manifest["status"] != "SUCCESS":
        result = {"status": manifest["status"], "outcome": {"simultaneous_success": False, "failure_patterns": ["invalid_cad"]},
                  "cad_urdf_consistency": {"status": "NOT_APPLICABLE", "matched_joints": 0}}
    else:
        gt, pred = load_robot(case_dir / "urdf" / "model.urdf"), load_robot(run_dir / "urdf" / "model.urdf")
        geometry, assembly, kinematic, motion, outcome = evaluate(gt, pred, 20260820)
        result = {"status": "SUCCESS", "geometry": geometry, "assembly": assembly, "kinematic": kinematic, "motion": motion,
                  "outcome": outcome, "cad_urdf_consistency": frame_consistency(run_dir)}
    write_json(output / "results.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=ROOT / "go_nogo3/data/dev15")
    parser.add_argument("--runs-root", type=Path, default=ROOT / "go_nogo3/runs")
    parser.add_argument("--variant", required=True)
    args = parser.parse_args()
    rows = []
    for case_dir in sorted(args.data_root.glob("dev_arm-*")):
        run_dir = args.runs_root / args.variant / case_dir.name
        if not (run_dir / "manifest.json").is_file():
            continue
        rows.append({"case": case_dir.name, "status": one(case_dir, run_dir)["status"]})
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
