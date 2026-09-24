"""Freeze W1 controls, then run nine witness technical checks exactly once."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "experiments/try6/results/try6_0_d1_w1"
ARTIFACT = ROOT / "experiments/try6/artifacts/try6_0_d1_w1"
PROTOCOL = ROOT / "experiments/try6/protocol/try6_0_d1_w1.json"
sys.path.insert(0, str(ROOT / "experiments/try5A/scripts"))
from freecad_runtime import python_runtime


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(relative, value):
    target = RESULT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    if Path(sys.executable).resolve() != (ROOT / ".venv/Scripts/python.exe").resolve():
        raise RuntimeError("repository .venv required")
    if RESULT.exists():
        raise FileExistsError("W1 already started; no silent rerun")
    cfg = read(PROTOCOL)
    d1 = read(ROOT / cfg["frozen_d1_protocol"])
    construction = read(ROOT / cfg["frozen_kfde_construction"])
    geometry = read(ROOT / cfg["frozen_geometry_set"])
    w0_root = ROOT / cfg["frozen_w0_result"]
    w0_cal = read(w0_root / "calibration/tolerance_calibration.json")
    w0_paths = read(w0_root / "construction_paths/declared_paths.json")
    if w0_cal["status"] != "PASS" or cfg["paths"] != w0_paths["paths"] or len(d1["witness_subsets"]) != 9:
        raise RuntimeError("frozen W0 path/nine-subset drift")
    if cfg["occupancy_policy"]["keepout_intersection_limit_mm3"] != d1["kfde_numerical_epsilon_mm3"]:
        raise RuntimeError("KFDE penetration tolerance drift")
    prior = {}
    for name in ("try6_0_c1_v2", "try6_0_c2", "try6_0_d0", "try6_0_d1", "try6_0_d1_t0", "try6_0_d1_v2", "try6_0_d1_w0"):
        folder = ROOT / "experiments/try6/results" / name
        manifest = read(folder / "manifest.json")
        if "result_file_sha256" in manifest and not all(
                sha(folder / p) == digest for p, digest in manifest["result_file_sha256"].items()):
            raise RuntimeError("frozen result drift: " + name)
        prior[name] = sha(folder / "manifest.json")
    lock_path = ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json"
    lock = read(lock_path)
    if lock["accessed"] is not False or lock["evaluation_count"] != 0:
        raise RuntimeError("holdout lock violated")
    c1 = geometry["geometries"][0]
    if sha(ROOT / c1["source_path"]) != c1["source_sha256"]:
        raise RuntimeError("C1 frozen geometry drift")
    if sha(ROOT / construction["allowed_region"]["path"]) != construction["allowed_region"]["sha256"]:
        raise RuntimeError("allowed BREP drift")
    for item in construction["components"]:
        if sha(ROOT / item["brep_path"]) != item["brep_sha256"]:
            raise RuntimeError("frozen KFDE component drift: " + item["component_id"])
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()
    hashes = {x["component_id"]: x["brep_sha256"] for x in construction["components"]}
    pre = {"created_utc": datetime.now(timezone.utc).isoformat(), "starting_commit": head,
        "protocol_sha256": sha(PROTOCOL), "D1_protocol_sha256": sha(ROOT / cfg["frozen_d1_protocol"]),
        "W0_calibration_sha256": sha(w0_root / "calibration/tolerance_calibration.json"),
        "W0_Boolean_helper_sha256": sha(ROOT / "experiments/try6/scripts/witness_boolean.py"),
        "W1_semantics_sha256": sha(ROOT / "experiments/try6/scripts/w1_semantics.py"),
        "W1_worker_sha256": sha(ROOT / "experiments/try6/evaluation/freecad_d1_w1_real.py"),
        "C1_source_sha256": c1["source_sha256"], "allowed_sha256": construction["allowed_region"]["sha256"],
        "component_hashes": hashes,
        "subset_definition_sha256": hashlib.sha256(json.dumps(d1["witness_subsets"], separators=(",", ":")).encode()).hexdigest(),
        "occupancy_policy": cfg["occupancy_policy"], "stability_policy": cfg["stability_policy"],
        "relief_thresholds": {"small_max": d1["witness_small_removed_ratio_max"],
                             "moderate_max": d1["witness_moderate_removed_ratio_max"]},
        "prior_manifest_sha256": prior, "holdout_lock_sha256": sha(lock_path),
        "python_environment": sys.executable}
    save("protocol.json", cfg)
    save("experiment_config_snapshot.json", cfg)
    save("pre_run_manifest.json", pre)
    save("frozen_inputs/c1_mutable_reference.json", {"source": c1["source_path"], "sha256": c1["source_sha256"],
         "extraction": "FrozenMatingEnvelopeCut minus frozen allowed region"})
    save("frozen_inputs/witness_subsets.json", {"subsets": d1["witness_subsets"],
         "canonical_sha256": pre["subset_definition_sha256"]})
    save("frozen_inputs/kfde_reference.json", {"construction_sha256": sha(ROOT / cfg["frozen_kfde_construction"]),
         "component_hashes": hashes, "allowed_sha256": pre["allowed_sha256"]})
    save("frozen_inputs/parity_audit.json", {"prior_manifest_sha256": prior,
         "C1_source_unchanged": True, "KFDE_unchanged": True, "D1_v2_alignment_unchanged": True,
         "W0_result_unchanged": True, "holdout_untouched": True})
    save("case_split.json", {"frozen_witness_subsets": d1["witness_subsets"], "count": 9,
         "formal_holdout_case_count": 32, "formal_holdout_ids_not_read": True,
         "accessed": False, "evaluation_count": 0})
    save("condition_parity.json", {"PATH_A": cfg["paths"][0], "PATH_B": cfg["paths"][1],
         "shared_source": c1["source_sha256"], "shared_component_hashes": hashes,
         "same_repeat_count": cfg["repeats_per_path"], "status": "PASS"})
    save("holdout_evaluation_log.json", {"events": [], "accessed": False,
         "evaluation_count": 0, "followed_by_tuning": False})
    save("witnesses/attempt_started.json", {"subsets": d1["witness_subsets"],
         "paths": cfg["paths"], "repeats_per_path": cfg["repeats_per_path"],
         "no_GT_VLM_final_mechanics_holdout": True})
    ARTIFACT.mkdir(parents=True, exist_ok=True)
    job = {"protocol": "experiments/try6/protocol/try6_0_d1_w1.json",
           "pre_run_manifest": "experiments/try6/results/try6_0_d1_w1/pre_run_manifest.json",
           "artifact_root": "experiments/try6/artifacts/try6_0_d1_w1/witnesses",
           "output": "experiments/try6/artifacts/try6_0_d1_w1/raw.json"}
    job_path = ARTIFACT / "job.json"
    job_path.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")
    worker = ROOT / "experiments/try6/evaluation/freecad_d1_w1_real.py"
    proc = subprocess.run([python_runtime(), str(worker), str(job_path)], cwd=ROOT,
                          capture_output=True, text=True, timeout=2400)
    (ARTIFACT / "stdout.txt").write_text(proc.stdout, encoding="utf-8")
    (ARTIFACT / "stderr.txt").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode:
        save("witnesses/infrastructure_failure.json", {"returncode": proc.returncode,
             "stderr": proc.stderr[-5000:], "no_silent_retry": True})
        raise RuntimeError("W1 FreeCAD worker failed: " + proc.stderr[-1200:])
    raw = read(ARTIFACT / "raw.json")
    if len(raw["rows"]) != 9:
        raise RuntimeError("nine-subset denominator incomplete")
    print(json.dumps({"subsets": len(raw["rows"]), "statuses": {x["subset"]: x["status"] for x in raw["rows"]}}))


if __name__ == "__main__":
    main()
