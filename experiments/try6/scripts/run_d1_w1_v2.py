"""Fresh nine-subset BREP construction with the unchanged frozen W1 worker."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "experiments/try6/results/try6_0_d1_w1_v2"
ARTIFACT = ROOT / "experiments/try6/artifacts/try6_0_d1_w1_v2"
sys.path.insert(0, str(ROOT / "experiments/try5A/scripts"))
from freecad_runtime import python_runtime


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if Path(sys.executable).resolve() != (ROOT / ".venv/Scripts/python.exe").resolve():
        raise RuntimeError("repository .venv required")
    if not (RESULT / "pre_run_manifest.json").exists():
        raise RuntimeError("zero rule not frozen")
    if (RESULT / "witnesses/attempt_started.json").exists() or (ARTIFACT / "raw.json").exists():
        raise FileExistsError("W1-v2 already attempted; no silent rerun")
    cfg = read(ROOT / "experiments/try6/protocol/try6_0_d1_w1_v2.json")
    pre = read(RESULT / "pre_run_manifest.json")
    if (sha(RESULT / "zero_rule/rule.json") != pre["zero_rule_sha256"] or
            sha(RESULT / "zero_rule/synthetic_tests.json") != pre["synthetic_tests_sha256"]):
        raise RuntimeError("zero rule changed after preregistration")
    worker = ROOT / "experiments/try6/evaluation/freecad_d1_w1_real.py"
    if sha(worker) != pre["W1_worker_sha256"]:
        raise RuntimeError("frozen witness construction worker changed")
    lock = read(ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"] != 0:
        raise RuntimeError("holdout lock violated")
    attempt = RESULT / "witnesses/attempt_started.json"
    attempt.parent.mkdir(parents=True, exist_ok=True)
    attempt.write_text(json.dumps({"subsets": 9, "paths": cfg["frozen_paths"],
        "repeats_per_path": cfg["repeats_per_path"], "fresh_run": True,
        "rule_sha256": pre["zero_rule_sha256"]}, indent=2) + "\n", encoding="utf-8")
    ARTIFACT.mkdir(parents=True, exist_ok=True)
    job = {"protocol": cfg["frozen_w1_protocol"],
           "pre_run_manifest": "experiments/try6/results/try6_0_d1_w1_v2/pre_run_manifest.json",
           "artifact_root": "experiments/try6/artifacts/try6_0_d1_w1_v2/witnesses",
           "output": "experiments/try6/artifacts/try6_0_d1_w1_v2/raw.json"}
    job_path = ARTIFACT / "job.json"
    job_path.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")
    proc = subprocess.run([python_runtime(), str(worker), str(job_path)], cwd=ROOT,
                          capture_output=True, text=True, timeout=2400)
    (ARTIFACT / "stdout.txt").write_text(proc.stdout, encoding="utf-8")
    (ARTIFACT / "stderr.txt").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode:
        (RESULT / "witnesses/infrastructure_failure.json").write_text(json.dumps({
            "returncode": proc.returncode, "stderr": proc.stderr[-5000:], "no_silent_retry": True}, indent=2), encoding="utf-8")
        raise RuntimeError("W1-v2 FreeCAD worker failed: " + proc.stderr[-1300:])
    raw = read(ARTIFACT / "raw.json")
    if len(raw["rows"]) != 9:
        raise RuntimeError("nine-subset raw denominator incomplete")
    print(json.dumps({"fresh_subsets": len(raw["rows"]), "raw_worker_statuses":
                      {x["subset"]: x["status"] for x in raw["rows"]}}))


if __name__ == "__main__":
    main()
