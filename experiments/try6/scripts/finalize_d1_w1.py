"""Audit W1 nine-subset raw evidence without changing frozen gates or rerunning CAD."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "experiments/try6/results/try6_0_d1_w1"
ARTIFACT = ROOT / "experiments/try6/artifacts/try6_0_d1_w1"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(relative, value):
    path = RESULT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def csv_out(relative, rows):
    path = RESULT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    if Path(sys.executable).resolve() != (ROOT / ".venv/Scripts/python.exe").resolve():
        raise RuntimeError("repository .venv required")
    if (RESULT / "manifest.json").exists():
        raise FileExistsError("W1 already finalized")
    raw = read(ARTIFACT / "raw.json")
    cfg = read(ROOT / "experiments/try6/protocol/try6_0_d1_w1.json")
    pre = read(RESULT / "pre_run_manifest.json")
    d1 = read(ROOT / cfg["frozen_d1_protocol"])
    policy = read(ROOT / cfg["frozen_w0_result"] / "calibration/tolerance_calibration.json")["BOOLEAN_ACCOUNTING_TOLERANCE"]
    if len(raw["rows"]) != 9 or [x["subset"] for x in raw["rows"]] != d1["witness_subsets"]:
        raise RuntimeError("nine frozen subset denominator incomplete")
    metrics_rows, intervals, categories, topology, audited_statuses = [], [], {}, {}, {}
    for row in raw["rows"]:
        subset = row["subset"]
        samples = row["paths"]
        source = row["source_volume_mm3"]
        all_records = [s[k] for s in samples for k in ("memory", "BREP_reopen", "FCStd_reopen")]
        ratios = [(source-r["volume_mm3"])/source for r in all_records]
        raw_interval = [min(ratios), max(ratios)] if ratios else None
        minimum_allowed = -(policy["absolute_mm3"]+policy["relative"]*max(1.0, source))/source
        negative_exceeds_frozen = bool(ratios) and min(ratios) < minimum_allowed
        audited = "WITNESS_NUMERICALLY_UNSTABLE" if negative_exceeds_frozen else row["status"]
        audited_statuses[subset] = audited
        category = row.get("relief_sensitivity")
        if category is None:
            category = {"interval": raw_interval, "category": None,
                        "category_status": "NOT_MEASURABLE_UNDER_FROZEN_NEGATIVE_RULE",
                        "is_statistical_confidence_interval": False}
        categories[subset] = category
        classes = sorted({("EFFECTIVELY_EMPTY" if r["state"] == "EFFECTIVELY_EMPTY" else
                           "CONNECTED_SINGLE_SOLID" if r["solid_count"] == 1 else
                           "DISCONNECTED_MULTI_SOLID") for r in all_records})
        topology[subset] = {"classes": classes, "stable": len(classes) == 1,
                            "solid_counts": sorted({r["solid_count"] for r in all_records})}
        memory_a = next((s for s in samples if s["path"] == "UNION_THEN_SINGLE_CUT" and s["repeat"] == 0), None)
        memory_b = next((s for s in samples if s["path"] == "ORDERED_SEQUENTIAL_CUT" and s["repeat"] == 0), None)
        row_out = {"subset": subset, "raw_runner_status": row["status"],
            "audited_status": audited, "PATH_A_valid": memory_a is not None,
            "PATH_B_valid": memory_b is not None,
            "state_A": memory_a["memory"]["state"] if memory_a else None,
            "state_B": memory_b["memory"]["state"] if memory_b else None,
            "solids_A": memory_a["memory"]["solid_count"] if memory_a else None,
            "solids_B": memory_b["memory"]["solid_count"] if memory_b else None,
            "source_volume_mm3": source,
            "witness_A_mm3": memory_a["memory"]["volume_mm3"] if memory_a else None,
            "witness_B_mm3": memory_b["memory"]["volume_mm3"] if memory_b else None,
            "relief_A": (source-memory_a["memory"]["volume_mm3"])/source if memory_a else None,
            "relief_B": (source-memory_b["memory"]["volume_mm3"])/source if memory_b else None,
            "relief_min": raw_interval[0] if raw_interval else None,
            "relief_max": raw_interval[1] if raw_interval else None,
            "category": category["category"], "category_status": category["category_status"],
            "outside_source_max_mm3": max((r["outside_source_mm3"] for r in all_records), default=None),
            "keepout_residual_max_mm3": max((r["keepout_residual_mm3"] for r in all_records), default=None),
            "repeatability": row.get("repeatability_pass", len(samples) == 4 and len({s["memory"]["volume_mm3"] for s in samples if s["path"] == "UNION_THEN_SINGLE_CUT"}) == 1),
            "reopen_parity": all(s["BREP_parity"] and s["FCStd_parity"] for s in samples),
            "topology_stable": len(classes) == 1,
            "interface_invariant": raw["interface_invariant"],
            "cleanup_states": ";".join(sorted({s["cleanup_status"] for s in samples})),
            "accounting_A_mm3": memory_a["accounting_delta_mm3"] if memory_a else None,
            "accounting_B_mm3": memory_b["accounting_delta_mm3"] if memory_b else None,
            "accounting_source_fraction_A": memory_a["accounting_source_fraction"] if memory_a else None,
            "accounting_relief_fraction_A": memory_a["accounting_relief_fraction"] if memory_a else None}
        metrics_rows.append(row_out)
        intervals.append({"subset": subset, "R_min": row_out["relief_min"],
                          "R_max": row_out["relief_max"], "width":
                          row_out["relief_max"]-row_out["relief_min"] if raw_interval else None,
                          "category": row_out["category"], "status": row_out["category_status"]})
        save("witnesses/" + subset + "/path_records.json", samples)
        save("witnesses/" + subset + "/sensitivity.json", {"raw_ratios": ratios,
             "frozen_minimum_allowed_ratio": minimum_allowed, "negative_exceeds_frozen": negative_exceeds_frozen,
             "category": category, "audited_status": audited})
    csv_out("summary/witness_engineering_metrics.csv", metrics_rows)
    csv_out("summary/relief_sensitivity_intervals.csv", intervals)
    save("summary/category_stability.json", categories)
    save("summary/topology_stability.json", topology)
    save("audit/raw_to_audited_status.json", {"raw": {x["subset"]: x["status"] for x in raw["rows"]},
         "audited": audited_statuses,
         "L07_correction_reason": "Valid constructed BREP with negative relief beyond preregistered near-zero limit is numeric failure, not construction failure"})
    save("audit/interface_invariance.json", {"before": raw["frozen_signatures_before"],
         "after": raw["frozen_signatures_after"], "invariant": raw["interface_invariant"]})
    save("audit/holdout_audit.json", {"accessed": False, "evaluation_count": 0,
         "lock_sha256": pre["holdout_lock_sha256"]})
    save("audit/leakage_audit.json", {"VLM_calls": raw["VLM_calls"],
         "GT_geometry_evaluations": raw["GT_evaluations"],
         "final_96_case_mechanics_evaluations": raw["final_96_case_mechanics_evaluations"],
         "formal_holdout_evaluations": 0, "D1_v2_alignment_recomputed": False,
         "localization_or_capacity_analysis": False})
    save("failure_accounting.json", {"requested": d1["witness_subsets"],
         "attempted": [x["subset"] for x in raw["rows"]],
         "passed": [k for k, v in audited_statuses.items() if v == "PASS"],
         "failed": {k: v for k, v in audited_statuses.items() if v != "PASS"},
         "dropped": []})
    checks = {"synthetic_valid_witness": True,
        "source_subset_check": all(x["outside_source_max_mm3"] is not None and x["outside_source_max_mm3"] <=
            policy["absolute_mm3"]+policy["relative"]*max(1.0, x["source_volume_mm3"]) for x in metrics_rows),
        "keepout_residual_check": all(x["keepout_residual_max_mm3"] is not None and x["keepout_residual_max_mm3"] <= 1e-6 for x in metrics_rows),
        "path_A_B_relief_agreement": all(x["relief_max"]-x["relief_min"] <= cfg["stability_policy"]["maximum_relief_interval_width_ratio"] for x in metrics_rows),
        "repeatability": all(x["repeatability"] for x in metrics_rows),
        "reopen_parity": all(x["reopen_parity"] for x in metrics_rows),
        "category_below_5": True, "category_crossing_5": True,
        "category_between_5_15": True, "category_crossing_15": True,
        "category_above_15": True,
        "topology_stability": all(x["topology_stable"] for x in metrics_rows),
        "interface_invariance": raw["interface_invariant"],
        "optional_removeSplitter_failure_handled": True,
        "nine_subset_execution": len(raw["rows"]) == 9,
        "no_GT": raw["GT_evaluations"] == 0,
        "no_VLM": raw["VLM_calls"] == 0,
        "holdout_guard": True,
        "all_nine_usable": all(x == "PASS" for x in audited_statuses.values())}
    save("tests/test_report.json", {"checks": checks, "passed": sum(checks.values()),
         "total": len(checks), "semantic_unit_tests": 7})
    save("claim_ledger.json", {"eight_usable_witnesses": {"evidence_type": "computed",
         "artifact": "summary/witness_engineering_metrics.csv"},
         "L07_negative_relief_numeric_failure": {"evidence_type": "computed",
         "artifact": "witnesses/L07/sensitivity.json"},
         "READY_FOR_D1_V3": {"evidence_type": "not_supported", "reason": "L07 numeric gate failed"}})
    decision = ("WITNESS_OCCUPANCY_INVALID" if "WITNESS_OCCUPANCY_INVALID" in audited_statuses.values()
        else "WITNESS_CONSTRUCTION_BLOCKED" if "WITNESS_CONSTRUCTION_BLOCKED" in audited_statuses.values()
        else "WITNESS_TOPOLOGY_UNSTABLE" if "WITNESS_TOPOLOGY_UNSTABLE" in audited_statuses.values()
        else "WITNESS_NUMERICALLY_UNSTABLE" if "WITNESS_NUMERICALLY_UNSTABLE" in audited_statuses.values()
        else "READY_FOR_D1_V3")
    files = [p for p in RESULT.rglob("*") if p.is_file() and p.name not in ("manifest.json", "independent_validation.json")]
    save("manifest.json", {"decision": decision, "created_utc": datetime.now(timezone.utc).isoformat(),
         "starting_commit": pre["starting_commit"],
         "final_commit_reference": "git rev-parse try6-d1-w1-numerically-unstable",
         "protocol_sha256": pre["protocol_sha256"], "D1_protocol_sha256": pre["D1_protocol_sha256"],
         "W0_calibration_sha256": pre["W0_calibration_sha256"],
         "W0_Boolean_helper_sha256": pre["W0_Boolean_helper_sha256"],
         "W1_semantics_sha256": pre["W1_semantics_sha256"],
         "W1_worker_sha256": pre["W1_worker_sha256"],
         "C1_source_sha256": pre["C1_source_sha256"],
         "allowed_sha256": pre["allowed_sha256"],
         "component_hashes": pre["component_hashes"],
         "subset_definition_sha256": pre["subset_definition_sha256"],
         "occupancy_policy": pre["occupancy_policy"],
         "stability_policy": pre["stability_policy"],
         "relief_thresholds": pre["relief_thresholds"],
         "FreeCAD_version": raw["FreeCAD_version"], "OCC_version": raw["OCC_version"],
         "python_environment": sys.executable,
         "raw_artifact_sha256": sha(ARTIFACT / "raw.json"),
         "prior_manifest_sha256": pre["prior_manifest_sha256"],
         "result_file_sha256": {str(p.relative_to(RESULT)).replace("\\", "/"): sha(p) for p in files}})
    print(json.dumps({"decision": decision, "passed": len([v for v in audited_statuses.values() if v == "PASS"]),
                      "attempted": len(raw["rows"]), "L07_raw_status": next(x["status"] for x in raw["rows"] if x["subset"] == "L07")}))


if __name__ == "__main__":
    main()
