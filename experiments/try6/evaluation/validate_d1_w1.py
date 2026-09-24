"""Independent nine-subset W1 evidence audit; no FreeCAD rerun."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "experiments/try6/results/try6_0_d1_w1"
ARTIFACT = ROOT / "experiments/try6/artifacts/try6_0_d1_w1"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    manifest = read(RESULT / "manifest.json")
    cfg = read(ROOT / "experiments/try6/protocol/try6_0_d1_w1.json")
    d1 = read(ROOT / cfg["frozen_d1_protocol"])
    raw = read(ARTIFACT / "raw.json")
    pre = read(RESULT / "pre_run_manifest.json")
    calib = read(ROOT / cfg["frozen_w0_result"] / "calibration/tolerance_calibration.json")
    policy = calib["BOOLEAN_ACCOUNTING_TOLERANCE"]
    fail = read(RESULT / "failure_accounting.json")
    categories = read(RESULT / "summary/category_stability.json")
    topology = read(RESULT / "summary/topology_stability.json")
    checks = {}
    checks["result_hashes"] = all(sha(RESULT / p) == digest for p, digest in manifest["result_file_sha256"].items())
    checks["raw_artifact_hash"] = sha(ARTIFACT / "raw.json") == manifest["raw_artifact_sha256"]
    checks["frozen_prior_manifests"] = all(sha(ROOT / "experiments/try6/results" / n / "manifest.json") == h
        for n, h in pre["prior_manifest_sha256"].items())
    d1v2 = ROOT / cfg["frozen_d1_v2_result"]
    checks["frozen_65_rows_unchanged"] = (sha(d1v2 / "alignment/raw_alignment.json") ==
        read(d1v2 / "manifest.json")["result_file_sha256"]["alignment/raw_alignment.json"])
    checks["implementation_hashes"] = (sha(ROOT / "experiments/try6/protocol/try6_0_d1_w1.json") == pre["protocol_sha256"] and
        sha(ROOT / "experiments/try6/evaluation/freecad_d1_w1_real.py") == pre["W1_worker_sha256"] and
        sha(ROOT / "experiments/try6/scripts/w1_semantics.py") == pre["W1_semantics_sha256"])
    checks["frozen_subset_definitions"] = [x["subset"] for x in raw["rows"]] == d1["witness_subsets"] == fail["requested"] and len(raw["rows"]) == 9
    checks["same_source_all_rows"] = len({x["source_volume_mm3"] for x in raw["rows"]}) == 1 and sha(ROOT / read(ROOT / cfg["frozen_geometry_set"])["geometries"][0]["source_path"]) == pre["C1_source_sha256"]
    construction = read(ROOT / cfg["frozen_kfde_construction"])
    checks["frozen_components"] = all(sha(ROOT / x["brep_path"]) == pre["component_hashes"][x["component_id"]] for x in construction["components"])
    checks["frozen_allowed"] = sha(ROOT / construction["allowed_region"]["path"]) == pre["allowed_sha256"]
    checks["both_paths_two_repeats"] = all(len(x["paths"]) == 4 and
        {(s["path"], s["repeat"]) for s in x["paths"]} == {(p, r) for p in cfg["paths"] for r in (0, 1)}
        for x in raw["rows"])
    def records(row):
        return [s[k] for s in row["paths"] for k in ("memory", "BREP_reopen", "FCStd_reopen")]
    checks["source_subset_invariant"] = all(r["outside_source_mm3"] <=
        policy["absolute_mm3"]+policy["relative"]*max(1.0, row["source_volume_mm3"])
        for row in raw["rows"] for r in records(row))
    checks["keepout_residual_invariant"] = all(r["keepout_residual_mm3"] <= d1["kfde_numerical_epsilon_mm3"]
        for row in raw["rows"] for r in records(row))
    checks["reopen_parity"] = all(s["BREP_parity"] and s["FCStd_parity"] for row in raw["rows"] for s in row["paths"])
    checks["topology_parity"] = all(topology[row["subset"]]["stable"] and
        len({(r["state"], r["solid_count"]) for r in records(row)}) == 1 for row in raw["rows"])
    checks["repeatability"] = all(len({s["memory"]["volume_mm3"] for s in row["paths"] if s["path"] == p}) == 1
        for row in raw["rows"] for p in cfg["paths"])
    checks["relief_intervals_recomputed"] = all(
        categories[row["subset"]]["interval"] == [
            min((row["source_volume_mm3"]-r["volume_mm3"])/row["source_volume_mm3"] for r in records(row)),
            max((row["source_volume_mm3"]-r["volume_mm3"])/row["source_volume_mm3"] for r in records(row))]
        for row in raw["rows"])
    checks["frozen_category_boundaries"] = d1["witness_small_removed_ratio_max"] == 0.05 and d1["witness_moderate_removed_ratio_max"] == 0.15
    checks["eight_robust_categories"] = sum(categories[x["subset"]]["category_status"] == "ROBUST" for x in raw["rows"]) == 8
    l07 = next(x for x in raw["rows"] if x["subset"] == "L07")
    l07_sens = read(RESULT / "witnesses/L07/sensitivity.json")
    checks["L07_numeric_failure_not_construction"] = (len(l07["paths"]) == 4 and
        l07_sens["negative_exceeds_frozen"] and
        l07_sens["audited_status"] == "WITNESS_NUMERICALLY_UNSTABLE" and
        l07["status"] == "WITNESS_CONSTRUCTION_BLOCKED")
    checks["failure_accounting"] = len(fail["attempted"]) == 9 and len(fail["passed"]) == 8 and fail["failed"] == {"L07": "WITNESS_NUMERICALLY_UNSTABLE"} and fail["dropped"] == []
    checks["interface_invariance"] = raw["interface_invariant"] and read(RESULT / "audit/interface_invariance.json")["invariant"]
    leakage = read(RESULT / "audit/leakage_audit.json")
    checks["no_forbidden_evaluation"] = all(v == 0 or v is False for v in leakage.values()) and raw["GT_evaluations"] == raw["VLM_calls"] == raw["final_96_case_mechanics_evaluations"] == 0
    lock_path = ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json"
    lock = read(lock_path)
    checks["holdout_untouched"] = sha(lock_path) == pre["holdout_lock_sha256"] and lock["accessed"] is False and lock["evaluation_count"] == 0
    checks["no_readiness_claim"] = manifest["decision"] == "WITNESS_NUMERICALLY_UNSTABLE" and read(RESULT / "claim_ledger.json")["READY_FOR_D1_V3"]["evidence_type"] == "not_supported"
    if not all(checks.values()):
        raise RuntimeError("independent W1 validation failed: " + json.dumps(checks))
    output = {"decision": "WITNESS_NUMERICALLY_UNSTABLE", "checks": checks,
              "passed": len(checks), "total": len(checks), "independent_of_runner": True,
              "subsets_attempted": 9, "subsets_usable": 8, "READY_FOR_D1_V3": False,
              "scientific_relief_conclusion": None}
    target = RESULT / "audit/independent_validation.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"decision": output["decision"], "passed": output["passed"], "total": output["total"]}))


if __name__ == "__main__":
    main()
