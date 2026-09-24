"""One preregistered frozen-evidence D1-v3 FreeCAD diagnostic run."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "experiments/try6/results/try6_0_d1_v3"
ARTIFACT = ROOT / "experiments/try6/artifacts/try6_0_d1_v3"
PROTOCOL = ROOT / "experiments/try6/protocol/try6_0_d1_v3.json"
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
        raise FileExistsError("D1-v3 result already exists; no silent rerun")
    cfg = read(PROTOCOL)
    d1 = read(ROOT / cfg["frozen_d1_protocol"])
    alignment = read(ROOT / cfg["frozen_alignment"])
    w1_root = ROOT / cfg["frozen_witness_result"]
    w1_validation = read(w1_root / "audit/independent_validation.json")
    if w1_validation["decision"] != "READY_FOR_D1_V3" or len(alignment["cases"]) != 65:
        raise RuntimeError("required frozen alignment/witness readiness missing")
    prior = {}
    for name in ("try6_0_c1_v2", "try6_0_c2", "try6_0_d0", "try6_0_d1", "try6_0_d1_t0",
                 "try6_0_d1_v2", "try6_0_d1_w0", "try6_0_d1_w1", "try6_0_d1_w1_v2"):
        folder = ROOT / "experiments/try6/results" / name
        manifest = read(folder / "manifest.json")
        if "result_file_sha256" in manifest and not all(sha(folder / p) == digest
                for p, digest in manifest["result_file_sha256"].items()):
            raise RuntimeError("frozen result drift: " + name)
        prior[name] = sha(folder / "manifest.json")
    frozen = read(ROOT / cfg["frozen_geometry_set"])
    c1 = frozen["geometries"][0]
    if sha(ROOT / c1["mutable_brep_path"]) != c1["mutable_brep_sha256"]:
        raise RuntimeError("frozen C1 mutable BREP drift")
    construction = read(ROOT / cfg["frozen_kfde_construction"])
    if any(sha(ROOT / x["brep_path"]) != x["brep_sha256"] for x in construction["components"]):
        raise RuntimeError("frozen KFDE component drift")
    lock_path = ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json"
    lock = read(lock_path)
    if lock["accessed"] is not False or lock["evaluation_count"] != 0:
        raise RuntimeError("holdout lock violated")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()
    comp_hashes = {x["component_id"]: x["brep_sha256"] for x in construction["components"]}
    pre = {"starting_commit": head, "created_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": sha(PROTOCOL), "D1_protocol_sha256": sha(ROOT / cfg["frozen_d1_protocol"]),
        "alignment_sha256": sha(ROOT / cfg["frozen_alignment"]),
        "W1_v2_manifest_sha256": sha(w1_root / "manifest.json"),
        "W1_v2_metrics_sha256": sha(w1_root / "summary/engineering_witness_metrics.csv"),
        "C1_mutable_brep_sha256": c1["mutable_brep_sha256"],
        "component_hashes": comp_hashes,
        "W0_exact_union_sha256": sha(ROOT / "experiments/try6/scripts/witness_boolean.py"),
        "geometry_worker_sha256": sha(ROOT / "experiments/try6/evaluation/freecad_d1_v3_geometry.py"),
        "six_theta_source_sha256": sha(ROOT / "experiments/try6/results/try6_0_c1_v2/solver/theta_selected.json"),
        "C1_builder_sha256": sha(ROOT / "experiments/try6/scripts/freecad_c1_builder.py"),
        "prior_manifest_sha256": prior, "holdout_lock_sha256": sha(lock_path),
        "python_environment": sys.executable}
    save("protocol.json", cfg)
    save("experiment_config_snapshot.json", cfg)
    save("pre_run_manifest.json", pre)
    save("case_split.json", {"frozen_alignment_rows": 65, "frozen_witness_subsets": d1["witness_subsets"],
        "formal_holdout_case_count": 32, "formal_holdout_ids_not_read": True,
        "accessed": False, "evaluation_count": 0})
    save("condition_parity.json", {"frozen_alignment_hash": pre["alignment_sha256"],
        "frozen_witness_metrics_hash": pre["W1_v2_metrics_sha256"],
        "no_new_condition_or_candidate": True, "status": "PASS"})
    save("holdout_evaluation_log.json", {"events": [], "accessed": False,
        "evaluation_count": 0, "followed_by_tuning": False})
    save("frozen_evidence/alignment_reference.json", {"path": cfg["frozen_alignment"],
        "sha256": pre["alignment_sha256"], "case_count": 65})
    save("frozen_evidence/witness_reference.json", {"result_root": cfg["frozen_witness_result"],
        "manifest_sha256": pre["W1_v2_manifest_sha256"],
        "metrics_sha256": pre["W1_v2_metrics_sha256"],
        "accepted_path": cfg["frozen_witness_path"]})
    save("frozen_evidence/source_hashes.json", {"C1_mutable_brep_sha256": c1["mutable_brep_sha256"],
        "component_hashes": comp_hashes,
        "allowed_region_sha256": construction["allowed_region"]["sha256"],
        "six_theta_source_sha256": pre["six_theta_source_sha256"],
        "C1_builder_sha256": pre["C1_builder_sha256"]})
    save("frozen_evidence/parity_audit.json", {"prior_manifest_sha256": prior,
        "alignment_frozen": True, "witness_frozen": True,
        "KFDE_and_CAD_unchanged": True, "formal_holdout_untouched": True})
    ARTIFACT.mkdir(parents=True, exist_ok=True)
    job = {"protocol": "experiments/try6/protocol/try6_0_d1_v3.json",
        "pre_run_manifest": "experiments/try6/results/try6_0_d1_v3/pre_run_manifest.json",
        "artifact_root": "experiments/try6/artifacts/try6_0_d1_v3/geometry",
        "output": "experiments/try6/artifacts/try6_0_d1_v3/geometry_raw.json"}
    job_path = ARTIFACT / "geometry_job.json"
    job_path.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")
    worker = ROOT / "experiments/try6/evaluation/freecad_d1_v3_geometry.py"
    proc = subprocess.run([python_runtime(), str(worker), str(job_path)], cwd=ROOT,
        capture_output=True, text=True, timeout=1200)
    (ARTIFACT / "geometry_stdout.txt").write_text(proc.stdout, encoding="utf-8")
    (ARTIFACT / "geometry_stderr.txt").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode:
        save("localization/infrastructure_failure.json", {"returncode": proc.returncode,
            "stderr": proc.stderr[-5000:], "no_silent_retry": True})
        raise RuntimeError("D1-v3 geometry diagnostic failed: " + proc.stderr[-1500:])
    raw = read(ARTIFACT / "geometry_raw.json")
    if len(raw["localizations"]) != 9:
        raise RuntimeError("nine-subset localization incomplete")
    print(json.dumps({"localizations": 9, "C1_supported_rows": len(raw["C1_supported_rows"]),
        "C1_suspect_rows": len(raw["C1_suspect_rows"]),
        "decomposition": raw["semantic_decomposition"]["status"]}))


if __name__ == "__main__":
    main()
