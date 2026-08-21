"""Evaluate Mesh Oracle Diagnostic predictions with the existing deterministic evaluator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "go_nogo2" / "scripts"))
from evaluate_prediction import evaluate, load_robot, write_json  # noqa: E402


def one(case: Path, run: Path) -> dict:
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8")); output = run / "evaluation"; output.mkdir(exist_ok=True)
    if manifest["status"] != "SUCCESS": result = {"status": manifest["status"], "outcome": {"simultaneous_success": False, "failure_patterns": ["invalid_cad"]}}
    else:
        source = json.loads((case / "metadata.json").read_text(encoding="utf-8"))["source_case"]
        gt, pred = load_robot(Path(source) / "urdf" / "model.urdf"), load_robot(run / "urdf" / "model.urdf")
        geometry, assembly, kinematic, motion, outcome = evaluate(gt, pred, 20260821)
        result = {"status": "SUCCESS", "geometry": geometry, "assembly": assembly, "kinematic": kinematic, "motion": motion, "outcome": outcome}
    write_json(output / "results.json", result); return result


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--condition", required=True); parser.add_argument("--data-root", type=Path, default=ROOT / "mesh_oracle_diagnostic/data/cases"); parser.add_argument("--runs-root", type=Path, default=ROOT / "mesh_oracle_diagnostic/runs"); args = parser.parse_args()
    rows=[]
    for case in sorted(args.data_root.glob("dev_arm-*")):
        run=args.runs_root / args.condition / case.name
        if (run / "manifest.json").is_file(): rows.append({"case":case.name,"status":one(case,run)["status"]})
    print(json.dumps(rows,indent=2))


if __name__ == "__main__": main()
