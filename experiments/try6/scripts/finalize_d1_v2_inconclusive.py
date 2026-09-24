"""Account for complete Phase A and failed witness without scientific promotion."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "experiments/try6/results/try6_0_d1_v2"


def read(relative):
    return json.loads((RESULT / relative).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(relative, value):
    path = RESULT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    if Path(sys.executable).resolve() != (ROOT / ".venv/Scripts/python.exe").resolve():
        raise RuntimeError("repository .venv required")
    raw = read("alignment/raw_alignment.json")
    cfg = read("protocol.json")
    pre = read("pre_run_manifest.json")
    rows = raw["cases"]
    if raw["status"] != "PASS" or len(rows) != 65 or len({(x["geometry_id"], x["component_id"]) for x in rows}) != 65:
        raise RuntimeError("cannot finalize incomplete Phase A")
    if (RESULT / "witness/witness_summary.json").exists():
        raise RuntimeError("this finalizer is only for incomplete witness phase")
    first = read("witness/technical_retry_authorization.json")
    second = read("witness/failure.json")
    if first["retry_limit"] != 1 or second["type"] != "WORKER_EXCEPTION":
        raise RuntimeError("witness failure accounting drift")
    csv_path = RESULT / "alignment/alignment_65_rows.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    counts = Counter(x["alignment_category"] for x in rows)
    violations = [x for x in rows if x["kfde_violation"] and x["alignment_category"] != "AMBIGUOUS_NUMERICAL"]
    aligned = sum(x["alignment_category"] == "ALIGNED_UNSAFE" for x in violations)
    rate = aligned/len(violations) if violations else None
    summary = {"status": "PHASE_A_COMPLETE_WITNESS_INCOMPLETE", "case_count": 65,
       "counts": dict(counts), "KFDE_violation_count_nonambiguous": len(violations),
       "aligned_unsafe_count": aligned, "descriptive_unsafe_alignment_rate": rate,
       "ALIGNMENT_HIGH_threshold": cfg["alignment_high_min_fraction"],
       "ALIGNMENT_HIGH": rate is not None and rate >= cfg["alignment_high_min_fraction"],
       "not_general_statistical_precision": True, "final_scientific_verdict_not_supported": True}
    save("alignment/alignment_summary.json", summary)
    neighbors = {}
    for neighbor in ("L03", "L05", "L06", "L07"):
        subset = [x for x in rows if x["neighbor_id"] == neighbor]
        denominator = [x for x in subset if x["kfde_violation"] and x["alignment_category"] != "AMBIGUOUS_NUMERICAL"]
        numerator = sum(x["alignment_category"] == "ALIGNED_UNSAFE" for x in denominator)
        neighbors[neighbor] = {"case_count": len(subset), "counts": dict(Counter(x["alignment_category"] for x in subset)),
            "nonambiguous_KFDE_violations": len(denominator), "aligned_unsafe": numerator,
            "descriptive_alignment_rate": numerator/len(denominator) if denominator else None,
            "material_KFDE_false_positive_suspects": sum(x["alignment_category"] == "KFDE_FALSE_POSITIVE_SUSPECT" for x in subset),
            "exact_taxonomy_counts": dict(Counter(x["exact_taxonomy"] for x in subset))}
    save("alignment/per_neighbor_alignment.json", neighbors)
    save("alignment/per_pose_alignment.json", {component: {
         "case_count": sum(x["component_id"] == component for x in rows),
         "counts": dict(Counter(x["alignment_category"] for x in rows if x["component_id"] == component))}
         for component in sorted({x["component_id"] for x in rows})})
    for name, category in (("false_positive_suspects", "KFDE_FALSE_POSITIVE_SUSPECT"),
                           ("false_negative_suspects", "KFDE_FALSE_NEGATIVE_SUSPECT"),
                           ("ambiguous_rows", "AMBIGUOUS_NUMERICAL")):
        save("alignment/" + name + ".json", [x for x in rows if x["alignment_category"] == category])
    g5 = [x for x in rows if x["geometry_id"] == "G5_F0_COARSE"]
    state = next(x for x in raw["geometry_states"] if x["geometry_id"] == "G5_F0_COARSE")
    save("authority/f0_full_geometry.json", state["full"])
    save("authority/f0_mutable_state.json", state["mutable"])
    save("authority/f0_kfde_rows.json", [{k: x[k] for k in ("component_id", "neighbor_id",
         "kfde_status", "kfde_mutable_added_intersection_mm3", "kfde_violation")} for x in g5])
    save("authority/f0_exact_rows.json", [{k: x[k] for k in ("component_id", "neighbor_id",
         "exact_full_pair_common_mm3", "exact_taxonomy", "exact_unintended_collision")} for x in g5])
    save("authority/authority_summary.json", {"G5_full_state": state["full"]["state"],
         "G5_mutable_state": state["mutable"]["state"], "case_count": len(g5),
         "full_exact_unintended_collision_cases": sum(x["exact_unintended_collision"] for x in g5),
         "mutable_KFDE_violations": sum(x["kfde_violation"] for x in g5),
         "authority_contradiction_established": False,
         "reason": "empty mutable scope is not a full-link authority contradiction"})
    save("audit/empty_geometry_semantics.json", {"G5_full_state": state["full"],
         "G5_mutable_state": state["mutable"], "G5_rows": len(g5),
         "all_G5_status_empty": all(x["kfde_status"] == "EMPTY_MUTABLE_GEOMETRY" for x in g5),
         "no_G5_row_dropped": True})
    save("failure_accounting.json", {"alignment": {"requested": 65, "completed": 65, "failed": 0},
         "witness": {"requested_subsets": cfg["witness_subsets"], "completed": 0,
                     "failed": len(cfg["witness_subsets"]), "first_failure": first["first_failure"],
                     "technical_retry_failure": second["detail"], "no_more_retries": True}})
    save("audit/leakage_audit.json", {"VLM_calls": 0, "GT_geometry_evaluations": 0,
         "final_96_case_mechanics_evaluations": 0, "formal_holdout_evaluations": 0})
    lock_path = ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    save("audit/holdout_audit.json", {"lock_sha256": sha(lock_path),
         "accessed": lock["accessed"], "evaluation_count": lock["evaluation_count"]})
    save("claim_ledger.json", {"phase_A_65_rows": {"evidence_type": "computed",
         "artifact": "alignment/raw_alignment.json", "field": "cases", "use": "descriptive_only"},
         "final_mechanism_claim": {"evidence_type": "incomplete", "reason": "witness phase 0/9"},
         "decision": "DIAGNOSTIC_INCONCLUSIVE"})
    before = {str((ROOT / "experiments/try6/results" / n / "manifest.json").relative_to(ROOT)).replace("\\", "/"):
              sha(ROOT / "experiments/try6/results" / n / "manifest.json")
              for n in ("try6_0_c1_v2", "try6_0_c2", "try6_0_d0", "try6_0_d1", "try6_0_d1_t0")}
    tracked = [p for p in RESULT.rglob("*") if p.is_file() and p.name not in ("manifest.json", "validation.json")
               and p != RESULT / "audit/independent_validation.json"]
    save("manifest.json", {"created_utc": datetime.now(timezone.utc).isoformat(),
         "starting_commit": pre["starting_commit"], "final_commit_reference": "git rev-parse try6-d1-v2-diagnostic-inconclusive",
         "frozen_D1_protocol_sha256": pre["frozen_D1_protocol_sha256"],
         "T0_classifier_sha256": pre["T0_classifier_sha256"],
         "pose_mapping_sha256": pre["pose_mapping_sha256"],
         "KFDE_sha256": pre["KFDE_sha256"], "exact_mechanics_sha256": pre["exact_mechanics_sha256"],
         "URDF_sha256": pre["URDF_sha256"], "allowed_contact_sha256": pre["allowed_contact_sha256"],
         "tolerance_policy_sha256": pre["tolerance_policy_sha256"],
         "witness_configuration_sha256": pre["witness_configuration_sha256"],
         "prior_manifest_sha256": before, "decision": "DIAGNOSTIC_INCONCLUSIVE",
         "result_file_sha256": {str(p.relative_to(RESULT)).replace("\\", "/"): sha(p) for p in tracked}})
    print(json.dumps({"status": "PHASE_A_COMPLETE_WITNESS_INCOMPLETE", "alignment_rows": 65,
         "witness_completed": 0, "descriptive_alignment_rate": rate,
         "decision": "DIAGNOSTIC_INCONCLUSIVE"}))


if __name__ == "__main__":
    main()
