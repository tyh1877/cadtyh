"""Execute exactly one preregistered D1-v2 phase, preserving failures."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "experiments/try6/results/try6_0_d1_v2"
ARTIFACT = ROOT / "experiments/try6/artifacts/try6_0_d1_v2"
sys.path.insert(0, str(ROOT / "experiments/try5A/scripts"))
from freecad_runtime import python_runtime


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(phase):
    if Path(sys.executable).resolve() != (ROOT / ".venv/Scripts/python.exe").resolve():
        raise RuntimeError("repository .venv required")
    if phase not in ("alignment", "witness"):
        raise ValueError("phase must be alignment or witness")
    pre = read(RESULT / "pre_run_manifest.json")
    cfg = read(RESULT / "protocol.json")
    lock = read(ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"] != 0:
        raise RuntimeError("formal holdout lock violated")
    prior_attempt = (RESULT / phase / "attempt_started.json").exists()
    technical_retry = phase == "witness" and sys.argv[2:] == ["--technical-retry"]
    if prior_attempt and not technical_retry:
        raise FileExistsError("phase already attempted; no silent retry")
    if technical_retry:
        marker = read(RESULT / "witness/technical_retry_authorization.json")
        if marker["retry_limit"] != 1 or (RESULT / "witness/technical_retry_started.json").exists():
            raise FileExistsError("technical retry unavailable/already used")
        first_failure = RESULT / "witness/failure.json"
        import hashlib
        if hashlib.sha256(first_failure.read_bytes()).hexdigest() != marker["first_failure_sha256"]:
            raise RuntimeError("first failure artifact drift")
        archive = ARTIFACT / "first_witness_failure"
        archive.mkdir(parents=True, exist_ok=False)
        for name in ("attempt_started.json", "failure.json", "stdout.txt", "stderr.txt"):
            shutil.copy2(RESULT / "witness" / name, archive / name)
        save(RESULT / "witness/technical_retry_started.json", marker)
    if phase == "witness":
        raw = read(RESULT / "alignment/raw_alignment.json")
        if raw["status"] != "PASS" or raw["case_count"] != 65 or len(raw["cases"]) != 65:
            raise RuntimeError("65-row alignment incomplete; witness forbidden")
    if phase == "alignment":
        worker = ROOT / "experiments/try6/evaluation/freecad_d1_v2_alignment.py"
        job = {"science_protocol": "experiments/try6/protocol/try6_0_d1.json",
               "geometry_set": "experiments/try6/results/try6_0_d1_v2/frozen_inputs/geometry_set.json",
               "output": "experiments/try6/results/try6_0_d1_v2/alignment/raw_alignment.json"}
        planned = 65
    else:
        worker = ROOT / "experiments/try6/evaluation/freecad_d1_v2_witness.py"
        job = {"science_protocol": "experiments/try6/protocol/try6_0_d1.json",
               "result_root": "experiments/try6/results/try6_0_d1_v2/witness",
               "artifact_root": "experiments/try6/artifacts/try6_0_d1_v2/witness"}
        planned = len(cfg["witness_subsets"])
    ARTIFACT.mkdir(parents=True, exist_ok=True)
    job_path = ARTIFACT / (phase + "_job.json")
    save(job_path, job)
    folder = RESULT / phase
    if not prior_attempt:
        save(folder / "attempt_started.json", {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
         "starting_commit": pre["starting_commit"], "planned": planned,
         "frozen_D1_protocol_sha256": pre["frozen_D1_protocol_sha256"],
         "T0_classifier_sha256": pre["T0_classifier_sha256"], "GT_accessed": False})
    tick = time.perf_counter()
    try:
        proc = subprocess.run([python_runtime(), str(worker), str(job_path)], cwd=ROOT,
                              capture_output=True, text=True, timeout=1200)
    except subprocess.TimeoutExpired as exc:
        save(folder / "failure.json", {"type": "TIMEOUT", "planned": planned,
             "completed": 0, "detail": str(exc), "no_silent_retry": True})
        raise
    (folder / "stdout.txt").write_text(proc.stdout, encoding="utf-8")
    (folder / "stderr.txt").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode:
        save(folder / "failure.json", {"type": "WORKER_EXCEPTION", "returncode": proc.returncode,
             "planned": planned, "completed": 0, "detail": proc.stderr[-5000:], "no_silent_retry": True})
        raise RuntimeError(phase + " worker failed: " + proc.stderr[-1500:])
    save(folder / "runtime.json", {"seconds": time.perf_counter()-tick,
         "planned": planned, "GT_evaluations": 0, "final_96_case_mechanics_evaluations": 0})
    print(json.dumps({"phase": phase, "planned": planned, "seconds": time.perf_counter()-tick,
                      "worker_stdout": proc.stdout[-500:]}))


if __name__ == "__main__":
    main(sys.argv[1])
