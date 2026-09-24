"""Pre-real-run W0 synthetic calibration and independent frozen-state guard."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "experiments/try6/results/try6_0_d1_w0"
ARTIFACT = ROOT / "experiments/try6/artifacts/try6_0_d1_w0"
PROTOCOL = ROOT / "experiments/try6/protocol/try6_0_d1_w0.json"
sys.path.insert(0, str(ROOT / "experiments/try5A/scripts"))
from freecad_runtime import python_runtime


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(relative, data):
    path = RESULT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    if Path(sys.executable).resolve() != (ROOT / ".venv/Scripts/python.exe").resolve():
        raise RuntimeError("repository .venv required")
    if RESULT.exists():
        raise FileExistsError("W0 calibration already attempted; no silent rerun")
    cfg = read(PROTOCOL)
    d1 = read(ROOT / cfg["frozen_d1_protocol"])
    prior = {}
    for name in ("try6_0_c1_v2", "try6_0_c2", "try6_0_d0", "try6_0_d1", "try6_0_d1_t0", "try6_0_d1_v2"):
        folder = ROOT / "experiments/try6/results" / name
        manifest = read(folder / "manifest.json")
        if "result_file_sha256" in manifest and not all(
                sha(folder / p) == digest for p, digest in manifest["result_file_sha256"].items()):
            raise RuntimeError("frozen result drift: " + name)
        prior[name] = sha(folder / "manifest.json")
    lock_path = ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json"
    lock = read(lock_path)
    if lock["accessed"] is not False or lock["evaluation_count"] != 0:
        raise RuntimeError("formal holdout lock violated")
    construction = read(ROOT / cfg["frozen_kfde_construction"])
    geometry = read(ROOT / cfg["frozen_geometry_set"])
    if len(construction["components"]) != 13 or len(d1["witness_subsets"]) != 9:
        raise RuntimeError("frozen subset/component count drift")
    if sha(ROOT / geometry["geometries"][0]["source_path"]) != geometry["geometries"][0]["source_sha256"]:
        raise RuntimeError("C1 source drift")
    for item in construction["components"]:
        if sha(ROOT / item["brep_path"]) != item["brep_sha256"]:
            raise RuntimeError("KFDE BREP drift")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()
    ARTIFACT.mkdir(parents=True, exist_ok=True)
    job = {"protocol": "experiments/try6/protocol/try6_0_d1_w0.json",
           "scratch": "experiments/try6/artifacts/try6_0_d1_w0/synthetic_brep",
           "output": "experiments/try6/artifacts/try6_0_d1_w0/synthetic_raw.json"}
    job_path = ARTIFACT / "synthetic_job.json"
    job_path.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")
    worker = ROOT / "experiments/try6/evaluation/freecad_d1_w0_calibration.py"
    proc = subprocess.run([python_runtime(), str(worker), str(job_path)], cwd=ROOT,
                          capture_output=True, text=True, timeout=300)
    (ARTIFACT / "synthetic_stdout.txt").write_text(proc.stdout, encoding="utf-8")
    (ARTIFACT / "synthetic_stderr.txt").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode:
        raise RuntimeError("synthetic calibration failed: " + proc.stderr[-1800:])
    raw = read(ARTIFACT / "synthetic_raw.json")
    rows = raw["rows"]
    if len(rows) != 8 * 2 * cfg["calibration_repetitions"] or raw["cleanup_failure_test"] != "FAILURE_CAUGHT":
        raise RuntimeError("synthetic fixture coverage incomplete")
    rule = cfg["accounting_tolerance_rule"]
    maximum_absolute = max(x["max_absolute_error_mm3"] for x in rows)
    maximum_relative = max(x["max_relative_error"] for x in rows)
    absolute = max(rule["absolute_floor_mm3"], rule["calibration_multiplier"] * maximum_absolute)
    relative = max(rule["relative_floor"], rule["calibration_multiplier"] * maximum_relative)
    tolerance_pass = absolute <= rule["absolute_ceiling_mm3"] and relative <= rule["relative_ceiling"]
    parity_pass = all(x["state"] == x["reopen_state"] and x["solid_count"] == x["reopen_solid_count"]
                      and x["bbox_delta_mm"] <= 1e-7 for x in rows)
    repeat_pass = True
    for case in cfg["calibration_cases"]:
        for path in cfg["candidate_paths"]:
            subset = [x for x in rows if x["case"] == case and x["path"] == path]
            repeat_pass &= (max(x["witness_volume_mm3"] for x in subset) -
                            min(x["witness_volume_mm3"] for x in subset) <=
                            absolute + relative * max(1.0, subset[0]["source_volume_mm3"]))
    save("protocol.json", cfg)
    save("calibration/synthetic_cases.json", raw)
    csv_path = RESULT / "calibration/repeated_runs.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    save("calibration/tolerance_calibration.json", {
        "status": "PASS" if tolerance_pass and parity_pass and repeat_pass else "FAIL",
        "BOOLEAN_ACCOUNTING_TOLERANCE": {"absolute_mm3": absolute, "relative": relative,
            "formula": rule["formula"]},
        "max_synthetic_absolute_error_mm3": maximum_absolute,
        "max_synthetic_relative_error": maximum_relative,
        "frozen_before_real_witness": True, "KFDE_feasibility_epsilon_mm3_unchanged": d1["kfde_numerical_epsilon_mm3"],
        "serialization_parity_pass": parity_pass, "repeatability_pass": repeat_pass,
        "calibration_ceilings_pass": tolerance_pass, "real_witness_inputs_not_opened_by_worker": True})
    save("calibration/calibration_report.json", {"cases": cfg["calibration_cases"],
         "repetitions": cfg["calibration_repetitions"], "paths": cfg["candidate_paths"],
         "synthetic_result": "PASS" if tolerance_pass and parity_pass and repeat_pass else "FAIL",
         "cleanup_failure_is_nonfatal": True})
    save("construction_paths/declared_paths.json", {"paths": cfg["candidate_paths"],
         "selection_rule": cfg["canonical_selection_rule"]})
    save("construction_paths/canonical_path_decision.json", {
        "status": "FROZEN" if tolerance_pass and parity_pass and repeat_pass else "BLOCKED",
        "canonical_path": "UNION_THEN_SINGLE_CUT" if tolerance_pass and parity_pass and repeat_pass else None,
        "selected_before_real_witness": True, "based_on_real_relief_magnitude": False})
    save("union/union_method.json", {"method": cfg["union_rule"],
         "component_order": cfg["component_order"], "optional_cleanup_required": False})
    save("audit/frozen_state_audit.json", {"prior_manifest_sha256": prior,
         "C1_mutable_source_sha256": geometry["geometries"][0]["source_sha256"],
         "component_sha256": {x["component_id"]: x["brep_sha256"] for x in construction["components"]},
         "allowed_region_sha256": construction["allowed_region"]["sha256"],
         "subset_definitions": d1["witness_subsets"], "D1_v2_alignment_untouched": True})
    save("audit/holdout_audit.json", {"lock_sha256": sha(lock_path),
         "accessed": lock["accessed"], "evaluation_count": lock["evaluation_count"]})
    save("audit/leakage_audit.json", {"VLM_calls": 0, "GT_geometry_evaluations": 0,
         "final_96_case_mechanics_evaluations": 0, "formal_holdout_evaluations": 0,
         "D1_v2_alignment_recomputed": False})
    save("pre_real_manifest.json", {"created_utc": datetime.now(timezone.utc).isoformat(),
         "starting_commit": head, "protocol_sha256": sha(PROTOCOL),
         "synthetic_raw_sha256": sha(ARTIFACT / "synthetic_raw.json"),
         "frozen_D1_protocol_sha256": sha(ROOT / cfg["frozen_d1_protocol"]),
         "T0_classifier_sha256": sha(ROOT / cfg["frozen_t0_classifier"]),
         "Boolean_helper_sha256": sha(ROOT / "experiments/try6/scripts/witness_boolean.py"),
         "C1_source_sha256": geometry["geometries"][0]["source_sha256"],
         "component_sha256": {x["component_id"]: x["brep_sha256"] for x in construction["components"]},
         "subset_definitions_sha256": hashlib.sha256(json.dumps(d1["witness_subsets"], separators=(",", ":")).encode()).hexdigest(),
         "allowed_region_sha256": construction["allowed_region"]["sha256"],
         "calibration_sha256": sha(RESULT / "calibration/tolerance_calibration.json"),
         "canonical_path_sha256": sha(RESULT / "construction_paths/canonical_path_decision.json"),
         "freecad_version": raw["freecad_version"], "occ_version": raw["occ_version"],
         "python_environment": sys.executable, "freecad_python": python_runtime()})
    print(json.dumps({"calibration": "PASS" if tolerance_pass and parity_pass and repeat_pass else "FAIL",
                      "absolute_mm3": absolute, "relative": relative,
                      "synthetic_rows": len(rows)}))


if __name__ == "__main__":
    main()
