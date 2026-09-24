"""Single fail-closed W0 real-subset technical run after frozen calibration."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "experiments/try6/results/try6_0_d1_w0"
ARTIFACT = ROOT / "experiments/try6/artifacts/try6_0_d1_w0"
sys.path.insert(0, str(ROOT / "experiments/try5A/scripts"))
from freecad_runtime import python_runtime


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if Path(sys.executable).resolve() != (ROOT / ".venv/Scripts/python.exe").resolve():
        raise RuntimeError("repository .venv required")
    output = ARTIFACT / "real_raw.json"
    if output.exists() or (RESULT / "witness_technical/attempt_started.json").exists():
        raise FileExistsError("W0 real subsets already attempted; no silent rerun")
    pre = read(RESULT / "pre_real_manifest.json")
    calibration = RESULT / "calibration/tolerance_calibration.json"
    canonical = RESULT / "construction_paths/canonical_path_decision.json"
    if sha(calibration) != pre["calibration_sha256"] or sha(canonical) != pre["canonical_path_sha256"]:
        raise RuntimeError("calibration/canonical path drift")
    if read(calibration)["status"] != "PASS" or read(canonical)["status"] != "FROZEN":
        raise RuntimeError("synthetic technical gate not passed")
    lock = read(ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"] != 0:
        raise RuntimeError("holdout lock violated")
    job = {"protocol": "experiments/try6/protocol/try6_0_d1_w0.json",
           "calibration": "experiments/try6/results/try6_0_d1_w0/calibration/tolerance_calibration.json",
           "pre_real_manifest": "experiments/try6/results/try6_0_d1_w0/pre_real_manifest.json",
           "artifact_root": "experiments/try6/artifacts/try6_0_d1_w0/real_subsets",
           "output": "experiments/try6/artifacts/try6_0_d1_w0/real_raw.json"}
    job_path = ARTIFACT / "real_job.json"
    job_path.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")
    start = RESULT / "witness_technical/attempt_started.json"
    start.parent.mkdir(parents=True, exist_ok=True)
    start.write_text(json.dumps({"planned_subsets": 9, "canonical_path": "UNION_THEN_SINGLE_CUT",
        "calibration_sha256": sha(calibration), "one_run_only": True}, indent=2) + "\n", encoding="utf-8")
    worker = ROOT / "experiments/try6/evaluation/freecad_d1_w0_real.py"
    proc = subprocess.run([python_runtime(), str(worker), str(job_path)], cwd=ROOT,
                          capture_output=True, text=True, timeout=1200)
    (ARTIFACT / "real_stdout.txt").write_text(proc.stdout, encoding="utf-8")
    (ARTIFACT / "real_stderr.txt").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode:
        raise RuntimeError("W0 worker infrastructure failure: " + proc.stderr[-1500:])
    raw = read(output)
    print(json.dumps({"status": raw["status"], "completed_subsets": len(raw["technical_summary"]),
                      "expected_subsets": len(raw["expected_subsets"]), "failure": raw["failure"]}))


if __name__ == "__main__":
    main()
