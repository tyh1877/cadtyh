"""Hash the ignored CAD, generated code, and Exact outputs after A2a execution."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/try5A"


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rel(path): return str(Path(path).resolve().relative_to(ROOT)).replace("\\", "/")


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--result-dir", required=True); args = parser.parse_args()
    root = Path(args.result_dir).resolve(); output = root / "artifact_manifest.json"
    if output.exists(): raise FileExistsError("artifact manifest already frozen")
    records = json.loads((root / "run_records.json").read_text(encoding="utf-8"))["records"]
    artifacts = []
    for row in records:
        link_id, condition = row["link"], row["method"]
        source = root / link_id / condition / "raw_response.txt"
        artifacts.append({"run": f"{link_id}__{condition}", "role": "frozen_model_response", "path": rel(source), "sha256": sha(source), "bytes": source.stat().st_size})
        folder = HERE / "artifacts/try5b1_a2a_three_link/runs" / link_id / condition
        candidates = {"generated_direct_code": folder / "generated_body.py", "generated_direct_brep": folder / "direct_body.brep", "fcstd": folder / "canonical_build/cad/F2" / link_id / "model.FCStd", "final_stl": folder / "canonical_build/cad/F2" / link_id / "model.stl", "body_only_stl": folder / "canonical_build/cad/F2" / link_id / "body_only.stl", "generation_job": folder / "canonical_build/generation_job.json"}
        for role, path in candidates.items():
            if path.is_file(): artifacts.append({"run": f"{link_id}__{condition}", "role": role, "path": rel(path), "sha256": sha(path), "bytes": path.stat().st_size})
        evaluator = HERE / "artifacts/try5b1_a2a_three_link/evaluation" / link_id / condition
        for role, path in {"exact_raw": evaluator / "mechanical_raw.json", "geometry_raw": evaluator / "geometry_raw.json", "exact_stdout": evaluator / "exact_log/stdout.txt", "exact_stderr": evaluator / "exact_log/stderr.txt"}.items():
            if path.is_file(): artifacts.append({"run": f"{link_id}__{condition}", "role": role, "path": rel(path), "sha256": sha(path), "bytes": path.stat().st_size})
    payload = {"schema_version": "robotcad_a2a_three_link_artifact_manifest_v1", "runs": 6, "artifacts": artifacts, "formal_holdout_accessed": False}
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "FROZEN", "artifacts": len(artifacts)}, indent=2))


if __name__ == "__main__": main()
