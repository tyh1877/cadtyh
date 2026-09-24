"""Independent, fail-closed validation of incomplete D1-v2 witness outcome."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "experiments/try6/results/try6_0_d1_v2"


def read(relative):
    return json.loads((RESULT / relative).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = read("manifest.json")
    cfg = read("protocol.json")
    pre = read("pre_run_manifest.json")
    raw = read("alignment/raw_alignment.json")
    summary = read("alignment/alignment_summary.json")
    failure = read("failure_accounting.json")
    g5 = read("authority/authority_summary.json")
    empty = read("audit/empty_geometry_semantics.json")
    leakage = read("audit/leakage_audit.json")
    holdout = read("audit/holdout_audit.json")
    checks = {}
    checks["result_file_hashes"] = all(sha(RESULT / p) == digest for p, digest in manifest["result_file_sha256"].items())
    checks["frozen_prior_manifests"] = all(sha(ROOT / p) == digest for p, digest in manifest["prior_manifest_sha256"].items())
    checks["frozen_D1_protocol"] = sha(ROOT / "experiments/try6/protocol/try6_0_d1.json") == pre["frozen_D1_protocol_sha256"]
    checks["T0_classifier"] = sha(ROOT / "experiments/try6/scripts/volumetric_geometry_state.py") == pre["T0_classifier_sha256"]
    checks["exact_mechanics"] = sha(ROOT / cfg["exact_mechanics_source"]) == pre["exact_mechanics_sha256"]
    checks["URDF"] = sha(ROOT / cfg["sanitized_urdf"]) == pre["URDF_sha256"]
    checks["65_rows_unique_complete"] = (raw["status"] == "PASS" and len(raw["cases"]) == 65 and
        len({(x["geometry_id"], x["component_id"]) for x in raw["cases"]}) == 65)
    checks["pose_and_source_mapping"] = all(x["geometry_fcstd_sha256"] == pre["source_hashes"][x["geometry_id"]] and
        x["KFDE_component_brep_sha256"] == pre["component_hashes"][x["component_id"]] and
        x["coordinate_volume_delta_mm3"] <= 1e-6 for x in raw["cases"])
    construction = json.loads((ROOT / cfg["kfde_construction"]).read_text(encoding="utf-8"))
    components = {x["component_id"]: x for x in construction["components"]}
    checks["frozen_pose_ids"] = all(x["neighbor_id"] == components[x["component_id"]]["link_id"] and
        x["joint_id"] == components[x["component_id"]]["joint_id"] and
        x["pose_q_rad"] == components[x["component_id"]]["q_rad"] for x in raw["cases"])
    checks["taxonomy_values"] = all(x["alignment_category"] in (
        "ALIGNED_UNSAFE", "ALIGNED_SAFE", "KFDE_FALSE_POSITIVE_SUSPECT",
        "KFDE_FALSE_NEGATIVE_SUSPECT", "AMBIGUOUS_NUMERICAL") for x in raw["cases"])
    checks["violation_and_taxonomy_consistency"] = all(
        x["kfde_violation"] == (x["kfde_mutable_added_intersection_mm3"] > cfg["kfde_numerical_epsilon_mm3"]) and
        x["exact_unintended_collision"] == (x["exact_taxonomy"] in
            ("ADJACENT_UNINTENDED_COLLISION", "NONADJACENT_COLLISION")) for x in raw["cases"])
    def category(row):
        if row["coordinate_volume_delta_mm3"] > cfg["kfde_numerical_epsilon_mm3"]:
            return "AMBIGUOUS_NUMERICAL"
        if row["kfde_violation"]:
            if row["exact_unintended_collision"]:
                return "ALIGNED_UNSAFE"
            return ("KFDE_FALSE_POSITIVE_SUSPECT" if
                    row["kfde_mutable_added_intersection_mm3"] >= cfg["material_exact_overlap_mm3"]
                    else "AMBIGUOUS_NUMERICAL")
        if row["exact_unintended_collision"]:
            return ("AMBIGUOUS_NUMERICAL" if row["scope_ambiguity"] or
                    row["allowed_region_pair_common_mm3"] > cfg["kfde_numerical_epsilon_mm3"]
                    else "KFDE_FALSE_NEGATIVE_SUSPECT")
        return "ALIGNED_SAFE"
    checks["frozen_category_logic"] = all(category(x) == x["alignment_category"] for x in raw["cases"])
    checks["G5_full_vs_mutable"] = (g5["case_count"] == 13 and
        g5["G5_full_state"] == "VALID_SINGLE_SOLID" and g5["G5_mutable_state"] == "EFFECTIVELY_EMPTY" and
        empty["all_G5_status_empty"] and empty["no_G5_row_dropped"])
    checks["descriptive_counts"] = (sum(summary["counts"].values()) == 65 and
        summary["KFDE_violation_count_nonambiguous"] == 32 and
        summary["aligned_unsafe_count"] == 5 and
        summary["descriptive_unsafe_alignment_rate"] == 5/32)
    checks["witness_failure_retained"] = (failure["witness"]["completed"] == 0 and
        failure["witness"]["failed"] == len(cfg["witness_subsets"]) == 9 and
        (RESULT / "witness/technical_retry_started.json").exists() and
        not (RESULT / "witness/witness_summary.json").exists())
    checks["no_witness_science_promoted"] = read("claim_ledger.json")["final_mechanism_claim"]["evidence_type"] == "incomplete"
    checks["no_forbidden_evaluations"] = all(value == 0 for value in leakage.values()) and not raw["GT_accessed"] and not raw["final_96_case_mechanics_run"]
    lock_path = ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    checks["holdout_untouched"] = (sha(lock_path) == holdout["lock_sha256"] and
        lock["accessed"] is False and lock["evaluation_count"] == 0)
    if not all(checks.values()):
        raise RuntimeError("independent validation failed: " + json.dumps(checks))
    output = {"decision": "DIAGNOSTIC_INCONCLUSIVE", "independent_of_runner": True,
              "checks": checks, "passed": len(checks), "total": len(checks),
              "phase_A_complete": True, "witness_complete": False,
              "scientific_mechanism_verdict_supported": False}
    target = RESULT / "audit/independent_validation.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"decision": output["decision"], "passed": output["passed"],
                      "total": output["total"]}))


if __name__ == "__main__":
    main()
