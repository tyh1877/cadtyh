"""Orchestrate D1-T0 technical audit in the repository Python environment."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments/try5A/scripts"))
from freecad_runtime import python_runtime

RESULT = ROOT / "experiments/try6/results/try6_0_d1_t0"
ARTIFACT = ROOT / "experiments/try6/artifacts/try6_0_d1_t0"
PROTOCOL = ROOT / "experiments/try6/protocol/try6_0_d1_t0.json"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(relative, value):
    path = RESULT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    if Path(sys.executable).resolve() != (ROOT / ".venv/Scripts/python.exe").resolve():
        raise RuntimeError("paper audit must use repository .venv")
    if RESULT.exists():
        if sys.argv[1:] != ["--technical-retry"]:
            raise FileExistsError("D1-T0 result already exists; require explicit --technical-retry")
        previous = ARTIFACT / "preliminary_attempt_1_result"
        if previous.exists():
            raise FileExistsError("preliminary attempt already archived; no further rerun")
        ARTIFACT.mkdir(parents=True, exist_ok=True)
        shutil.copytree(RESULT, previous)
    cfg = read(PROTOCOL)
    d1 = read(ROOT / cfg["frozen_d1_protocol"])
    frozen = read(ROOT / cfg["frozen_geometry_set"])
    construction = read(ROOT / cfg["frozen_kfde_construction"])
    if not (cfg["numerical_tolerance_mm3"] == d1["kfde_numerical_epsilon_mm3"] ==
            construction["numerical_tolerance_mm3"]):
        raise RuntimeError("frozen tolerance mismatch")
    lock_path = ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json"
    lock = read(lock_path)
    if lock["accessed"] is not False or lock["evaluation_count"] != 0:
        raise RuntimeError("formal holdout lock violated")
    prior_roots = [ROOT / "experiments/try6/results" / name for name in
                   ("try6_0_c1_v2", "try6_0_c2", "try6_0_d0", "try6_0_d1")]
    before = {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p / "manifest.json") for p in prior_roots}
    for p in prior_roots:
        manifest = read(p / "manifest.json")
        for relative, digest in manifest["result_file_sha256"].items():
            if sha(p / relative) != digest:
                raise RuntimeError("frozen result drift: " + str(p / relative))
    for item in frozen["geometries"]:
        if sha(ROOT / item["source_path"]) != item["source_sha256"]:
            raise RuntimeError("geometry source drift: " + item["geometry_id"])
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                          text=True, check=True).stdout.strip()
    ARTIFACT.mkdir(parents=True, exist_ok=True)
    job = {"d1_protocol": cfg["frozen_d1_protocol"], "frozen_geometry_set": cfg["frozen_geometry_set"],
           "scratch": "experiments/try6/artifacts/try6_0_d1_t0/roundtrip",
           "output": "experiments/try6/artifacts/try6_0_d1_t0/freecad_raw.json"}
    job_path = ARTIFACT / "worker_job.json"
    job_path.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")
    worker = ROOT / "experiments/try6/evaluation/freecad_d1_t0_audit.py"
    proc = subprocess.run([python_runtime(), str(worker), str(job_path)], cwd=ROOT,
                          capture_output=True, text=True, timeout=300)
    (ARTIFACT / "worker_stdout.txt").write_text(proc.stdout, encoding="utf-8")
    (ARTIFACT / "worker_stderr.txt").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode:
        raise RuntimeError("FreeCAD T0 audit failed; see ignored worker stderr: " + proc.stderr[-1200:])
    raw = read(ARTIFACT / "freecad_raw.json")
    save("protocol.json", cfg)
    save("geometry_state/classifier_spec.json", {"states": ["VALID_SINGLE_SOLID", "VALID_MULTI_SOLID",
         "EFFECTIVELY_EMPTY", "NONVOLUMETRIC_ONLY", "INVALID_BREP"],
         "precedence": cfg["state_precedence"], "tolerance_mm3": cfg["numerical_tolerance_mm3"],
         "nonvolumetric_policy": cfg["nonvolumetric_boolean_policy"]})
    save("geometry_state/g1_g5_states.json", raw["geometry_states"])
    save("geometry_state/synthetic_fixture_states.json", raw["synthetic_fixtures"])
    save("boolean_safety/operation_results.json", {"synthetic": raw["synthetic_boolean"],
         "g5": raw["g5_boolean_trace"], "component_rows": raw["empty_intersection_rows"],
         "empty_witness_semantics": raw["empty_witness_semantics"]})
    save("roundtrip/parity_report.json", {"roundtrips": raw["roundtrips"], "cross_paths": raw["cross_paths"]})
    save("provenance/g5_provenance_audit.json", raw["geometry_states"][4])
    save("provenance/full_mutable_separation.json", {"full": raw["geometry_states"][4]["full"],
         "mutable": raw["geometry_states"][4]["mutable"],
         "allowed": raw["geometry_states"][4]["allowed"],
         "scaffold": raw["geometry_states"][4]["scaffold"]})
    save("tests/test_report.json", {"tests": raw["tests"], "count": len(raw["tests"]),
         "passed": sum(t["pass"] for t in raw["tests"]), "all_pass": raw["all_tests_pass"]})
    after = {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p / "manifest.json") for p in prior_roots}
    save("audit/frozen_state_audit.json", {"before": before, "after": after,
         "unchanged": before == after, "source_hashes": {x["geometry_id"]: x["source_sha256"] for x in frozen["geometries"]},
         "allowed_brep_sha256": construction["allowed_region"]["sha256"]})
    save("audit/holdout_audit.json", {"lock_path": str(lock_path.relative_to(ROOT)).replace("\\", "/"),
         "lock_sha256": sha(lock_path), "accessed": lock["accessed"], "evaluation_count": lock["evaluation_count"]})
    save("audit/leakage_audit.json", {"VLM_calls": 0, "GT_geometry_evaluations": 0,
         "final_96_case_mechanics_evaluations": 0, "formal_holdout_evaluations": 0,
         "D1_v2_alignment_rows": 0, "scientific_witness_runs": 0})
    save("audit/no_dummy_geometry_audit.json", {"dummy_geometry_created": False,
         "empty_solid_count": raw["g5_boolean_trace"]["state"]["solid_count"],
         "empty_intersection_rows_retained": len(raw["empty_intersection_rows"])})
    save("manifest.json", {"created_utc": datetime.now(timezone.utc).isoformat(),
         "starting_commit": head, "final_commit_reference": "git rev-parse try6-d1-t0-ready",
         "protocol_sha256": sha(PROTOCOL), "classifier_implementation_sha256": sha(ROOT / "experiments/try6/scripts/volumetric_geometry_state.py"),
         "worker_sha256": sha(worker), "worker_raw_sha256": sha(ARTIFACT / "freecad_raw.json"),
         "frozen_tolerance_policy_sha256": sha(ROOT / "experiments/try6/results/try6_0_c2/kfde/tolerance_policy.json"),
         "freecad_version": raw["freecad_version"], "occ_version": raw["occ_version"],
         "orchestrator_python": sys.executable, "freecad_python": python_runtime(),
         "frozen_manifest_hashes": before, "source_hashes": {x["geometry_id"]: x["source_sha256"] for x in frozen["geometries"]},
         "allowed_brep_sha256": construction["allowed_region"]["sha256"],
         "holdout_lock_sha256": sha(lock_path), "technical_test_count": len(raw["tests"])})
    print(json.dumps({"worker": proc.stdout.strip(), "tests": len(raw["tests"]),
                      "passed": sum(t["pass"] for t in raw["tests"])}))


if __name__ == "__main__":
    main()
