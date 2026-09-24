"""Inspect existing decomposition BREPs without another Boolean operation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "experiments/try6/results/try6_0_d1_v3"
ARTIFACT = ROOT / "experiments/try6/artifacts/try6_0_d1_v3"
sys.path.insert(0, str(ROOT / "experiments/try5A/scripts"))
from freecad_runtime import python_runtime


def main():
    if Path(sys.executable).resolve() != (ROOT / ".venv/Scripts/python.exe").resolve():
        raise RuntimeError("repository .venv required")
    output = RESULT / "semantic_decomposition/existing_brep_inspection.json"
    if output.exists():
        raise FileExistsError("existing BREP inspection already performed")
    if not (ARTIFACT / "geometry_raw.json").exists():
        raise RuntimeError("frozen decomposition unavailable")
    job = {"geometry_raw": "experiments/try6/artifacts/try6_0_d1_v3/geometry_raw.json",
           "output": "experiments/try6/results/try6_0_d1_v3/semantic_decomposition/existing_brep_inspection.json"}
    job_path = ARTIFACT / "inspection_job.json"
    job_path.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")
    worker = ROOT / "experiments/try6/evaluation/freecad_d1_v3_inspect_existing.py"
    proc = subprocess.run([python_runtime(), str(worker), str(job_path)], cwd=ROOT,
        capture_output=True, text=True, timeout=120)
    (ARTIFACT / "inspection_stdout.txt").write_text(proc.stdout, encoding="utf-8")
    (ARTIFACT / "inspection_stderr.txt").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode:
        raise RuntimeError("existing-BREP read-only inspection failed: " + proc.stderr[-1200:])
    print(proc.stdout.strip())


if __name__ == "__main__":
    main()
