"""Correct descriptive process aggregation from frozen six-run A2a deltas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, median

PROCESS = {"input_tokens", "output_tokens", "total_tokens", "model_latency_seconds", "end_to_end_runtime_seconds"}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--result-dir", required=True); args = parser.parse_args()
    root = Path(args.result_dir).resolve(); path = root / "paired_deltas.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if (root / "process_aggregate_correction.json").exists(): raise FileExistsError("process aggregation correction already recorded")
    before = {key: payload["aggregate"][key] for key in PROCESS}
    for metric in PROCESS:
        values = [row[metric] for row in payload["per_link"] if row[metric] is not None]
        payload["aggregate"][metric] = {"mean_delta": mean(values), "median_delta": median(values), "paired_link_count": len(values), "requested_link_count": 3}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (root / "process_aggregate_correction.json").write_text(json.dumps({"incident": "A2A-ANALYSIS-001", "reason": "process metrics are observed for all three pairs even when CAD validation fails; initial aggregate applied the geometry-evaluable mask", "raw_runs_changed": False, "model_calls_added": 0, "cad_runs_added": 0, "evaluator_runs_added": 0, "before": before, "after": {key: payload["aggregate"][key] for key in PROCESS}}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PROCESS_AGGREGATE_CORRECTED", "process_pairs": 3, "geometry_pairs": payload["aggregate"]["final_voxel_iou"]["paired_link_count"]}, indent=2))


if __name__ == "__main__": main()
