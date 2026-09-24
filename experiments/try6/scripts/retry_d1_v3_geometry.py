"""One logged localization-reporting retry; leaves first D1-v3 failure intact."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "experiments/try6/results/try6_0_d1_v3"
ARTIFACT = ROOT / "experiments/try6/artifacts/try6_0_d1_v3"
sys.path.insert(0, str(ROOT / "experiments/try5A/scripts"))
from freecad_runtime import python_runtime


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if Path(sys.executable).resolve() != (ROOT / ".venv/Scripts/python.exe").resolve():
        raise RuntimeError("repository .venv required")
    marker_path = RESULT / "localization/technical_retry_authorization.json"
    failure_path = RESULT / "localization/infrastructure_failure.json"
    marker = read(marker_path)
    if marker["max_technical_retries"] != 1 or sha(failure_path) != marker["first_failure_sha256"]:
        raise RuntimeError("first failure/technical retry authorization drift")
    if (RESULT / "localization/technical_retry_started.json").exists() or (ARTIFACT / "geometry_raw.json").exists():
        raise FileExistsError("technical retry already used or geometry output exists")
    pre = read(RESULT / "pre_run_manifest.json")
    cfg = read(ROOT / "experiments/try6/protocol/try6_0_d1_v3.json")
    if sha(ROOT / cfg["frozen_alignment"]) != pre["alignment_sha256"]:
        raise RuntimeError("frozen alignment drift")
    lock = read(ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"] != 0:
        raise RuntimeError("formal holdout lock violated")
    archive = ARTIFACT / "first_failure"
    archive.mkdir(parents=True, exist_ok=False)
    shutil.copy2(failure_path, archive / failure_path.name)
    for name in ("geometry_stdout.txt", "geometry_stderr.txt"):
        path = ARTIFACT / name
        if path.exists():
            shutil.copy2(path, archive / name)
    worker = ROOT / "experiments/try6/evaluation/freecad_d1_v3_geometry.py"
    retry_record = {"first_failure_sha256": marker["first_failure_sha256"],
        "technical_change": marker["technical_change"], "new_worker_sha256": sha(worker),
        "original_worker_sha256": pre["geometry_worker_sha256"],
        "scientific_protocol_sha256": pre["protocol_sha256"],
        "scientific_inputs_and_thresholds_unchanged": True}
    target = RESULT / "localization/technical_retry_started.json"
    target.write_text(json.dumps(retry_record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    job_path = ARTIFACT / "geometry_job.json"
    proc = subprocess.run([python_runtime(), str(worker), str(job_path)], cwd=ROOT,
        capture_output=True, text=True, timeout=1200)
    (ARTIFACT / "technical_retry_stdout.txt").write_text(proc.stdout, encoding="utf-8")
    (ARTIFACT / "technical_retry_stderr.txt").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode:
        (RESULT / "localization/technical_retry_failure.json").write_text(json.dumps({
            "returncode": proc.returncode, "stderr": proc.stderr[-5000:], "no_more_retries": True}, indent=2), encoding="utf-8")
        raise RuntimeError("D1-v3 technical retry failed: " + proc.stderr[-1300:])
    raw = read(ARTIFACT / "geometry_raw.json")
    print(json.dumps({"localizations": len(raw["localizations"]),
        "C1_supported_rows": len(raw["C1_supported_rows"]),
        "C1_suspect_rows": len(raw["C1_suspect_rows"]),
        "decomposition": raw["semantic_decomposition"]["status"]}))


if __name__ == "__main__":
    main()
