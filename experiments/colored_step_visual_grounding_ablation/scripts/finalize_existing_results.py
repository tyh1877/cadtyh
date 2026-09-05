"""Offline closeout of historical runs; never calls the model or changes its evaluator.

Recompute recorded metrics, preserve failed cases/components, and export paired
diagnostics. An integrity pass does not mean the frozen scientific gates passed.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

from jsonschema import Draft202012Validator

import run_e1_visual_grounding as e1
import run_e2_component_mep as e2

EXP = Path(__file__).resolve().parents[1]
ROOT = EXP.parents[1]
RESULTS = EXP / "results"


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(name, rows):
    with (RESULTS / name).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def check_metrics(expected, recorded):
    for key, value in expected.items():
        if isinstance(value, (int, float)):
            assert math.isclose(value, float(recorded[key]), abs_tol=1e-10), (key, value, recorded[key])


def main():
    cases = read_csv(EXP / "native_step5_v1.csv")
    sources = {r["slug"]: r for r in read_csv(ROOT / "go_nogo1/sources/step_calibration/trossen/source_manifest.csv")}
    manifests = {}
    provenance = []
    for case in cases:
        cid = case["case_id"]
        manifest = read_json(e1.ARTIFACTS / cid / "component_manifest.json")
        manifests[cid] = manifest
        source = ROOT / case["step_path"]
        assert sha(source) == manifest["source_step_sha256"]
        record = sources[cid.removeprefix("step_")]
        provenance.append({"case_id": cid, "source_path": case["step_path"],
                           "source_sha256": sha(source), "version": "content-addressed; upstream release not recorded",
                           **{k: record[k] for k in ["documentation_url", "download_url", "downloaded_utc", "zip_sha256"]},
                           "regeneration_script": "go_nogo1/scripts/download_trossen_step.py"})
    expected_pairs = {(c["case_id"], cond) for c in cases for cond in e1.CONDITIONS}
    components = []
    aggregate = []
    paired = []
    failures = []
    summaries = {}
    for replicate in ["replicate_01", "replicate_02", "replicate_03"]:
        suffix = "" if replicate == "replicate_01" else "_" + replicate
        rows = read_csv(RESULTS / f"e1_case_condition_summary{suffix}.csv")
        assert len(rows) == 15 and {(r["case_id"], r["condition"]) for r in rows} == expected_pairs
        summaries[replicate] = rows
        for row in rows:
            cid, cond = row["case_id"], row["condition"]
            run = EXP / "runs" / f"e1_{replicate}" / cond / cid
            if row["status"] == "SUCCESS":
                api = read_json(run / "api_manifest.json")
                assert api["model"] == "glm-5.3-flash" and api["actual_image_inputs"] == 6
                details, metrics = e1.evaluate(e1.ARTIFACTS / cid, manifests[cid], read_json(run / "component_grounding_v1.json"))
                check_metrics(metrics, row)
                for key in ["input_tokens", "output_tokens", "total_tokens", "elapsed_seconds"]:
                    assert api[key] == float(row[key])
                e1.contact_sheet(replicate, cid, cond, e1.ARTIFACTS / cid / cond / "renders/isometric.png",
                                 read_json(run / "component_grounding_v1.json"))
            else:
                failure = read_json(run / "failure.json")
                assert failure["error_type"] == row["error_type"]
                failures.append({"stage": "E1", "replicate": replicate, "case_id": cid, "condition": cond,
                                 "status": row["status"], "error_type": row["error_type"],
                                 "usage_status": "unknown; historical zero is not proof of no billing"})
                details = [{"component_id": c["component_id"], "matched_region_id": "", "reported_component_id": "",
                            "identity_correct": 0, "best_view_bbox_iou": 0, "recall_at_0_5": 0,
                            "mean_target_purity": 0, "blank_crop": 1} for c in manifests[cid]["components"]]
            for detail in details:
                components.append({"replicate": replicate, "case_id": cid, "condition": cond,
                                   "status": row["status"], **detail})
        for cond in e1.CONDITIONS:
            selected = [r for r in rows if r["condition"] == cond]
            n = sum(int(r["gt_components"]) for r in selected)
            aggregate.append({"replicate": replicate, "condition": cond, "cases": 5, "components": n,
                              "successes": sum(r["status"] == "SUCCESS" for r in selected),
                              "case_macro_iou": sum(float(r["mean_bbox_iou"]) for r in selected) / 5,
                              "component_micro_iou": sum(float(r["mean_bbox_iou"]) * int(r["gt_components"]) for r in selected) / n,
                              "case_macro_recall": sum(float(r["recall_at_0_5"]) for r in selected) / 5,
                              "case_macro_contamination_proxy": sum(float(r["wrong_link_rate"]) for r in selected) / 5,
                              "recorded_tokens_lower_bound": sum(int(r["total_tokens"]) for r in selected),
                              "recorded_seconds_lower_bound": sum(float(r["elapsed_seconds"]) for r in selected)})
        for case in cases:
            indexed = {r["condition"]: r for r in rows if r["case_id"] == case["case_id"]}
            for cond in e1.CONDITIONS[1:]:
                paired.append({"replicate": replicate, "case_id": case["case_id"], "contrast": cond + "-A0_controlled",
                               "delta_iou": float(indexed[cond]["mean_bbox_iou"]) - float(indexed[e1.CONDITIONS[0]]["mean_bbox_iou"]),
                               "both_successful": all(indexed[c]["status"] == "SUCCESS" for c in [cond, e1.CONDITIONS[0]])})
        print(f"Verified E1 {replicate}: {len(rows)} cases/conditions", flush=True)

    rows = read_csv(RESULTS / "e2_case_condition_summary.csv")
    assert len(rows) == 15 and {(r["case_id"], r["condition"]) for r in rows} == expected_pairs
    validator = Draft202012Validator(read_json(e2.SCHEMA_PATH))
    plans = {}
    for row in rows:
        cid, cond = row["case_id"], row["condition"]
        if row["status"] == "SUCCESS":
            run = e2.RUNS / cond / cid
            plan = read_json(run / "component_mechanical_embodiment_v1.json")
            validator.validate(plan)
            assert (plan["case_id"], plan["condition"]) == (cid, cond)
            scan = read_json(e2.E1_RUNS / cond / cid / "component_grounding_v1.json")
            check_metrics(e2.evaluate(plan, scan), row)
            api = read_json(run / "api_manifest.json")
            assert api["actual_image_inputs"] == 6 and api["model"] == "glm-5.3-flash"
            plans[(cid, cond)] = {p["evidence_region_id"]: p for p in plan["components"]}
        else:
            assert row["status"] == "UPSTREAM_FAILURE"
            assert not (e2.E1_RUNS / cond / cid / "component_grounding_v1.json").exists()
            failures.append({"stage": "E2", "replicate": "replicate_01", "case_id": cid, "condition": cond,
                             "status": row["status"], "error_type": row["error_type"], "usage_status": "not called (upstream failure)"})
    differences = []
    for detail in components:
        if detail["replicate"] != "replicate_01":
            continue
        plan = plans.get((detail["case_id"], detail["condition"]), {}).get(detail["matched_region_id"])
        differences.append({k: detail[k] for k in ["case_id", "condition", "component_id", "matched_region_id"]} | {
            "matched_iou": detail["best_view_bbox_iou"], "plan_available": bool(plan),
            "functional_role": plan["functional_role"] if plan else "",
            "geometry_family": plan["main_envelope"]["geometry_family"] if plan else "",
            "joint_region_count": len(plan["joint_regions"]) if plan else 0,
            "visible_feature_count": len(plan["visible_structural_features"]) if plan else 0})
    write_csv("source_provenance.csv", provenance)
    write_csv("closeout_e1_components.csv", components)
    write_csv("closeout_e1_aggregate.csv", aggregate)
    write_csv("closeout_e1_paired.csv", paired)
    write_csv("closeout_e2_component_plans.csv", differences)
    write_csv("closeout_failures.csv", failures)
    # Hash local evidence without copying raw generations, images, or source CAD into Git.
    inventory = []
    for folder in [EXP / "artifacts/native_step5", EXP / "runs", EXP / "scripts", EXP / "prompts", EXP / "schemas"]:
        for path in sorted(folder.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                inventory.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)})
    write_csv("closeout_evidence_inventory.csv", inventory)
    first = {r["condition"]: r for r in aggregate if r["replicate"] == "replicate_01"}
    a0, a2 = first[e1.CONDITIONS[0]], first[e1.CONDITIONS[2]]
    audit = {"integrity_status": "PASS", "scientific_completion": "INCOMPLETE_PROTOCOL_GATES",
             "native_cases": 5, "leaf_components_per_condition": sum(len(m["components"]) for m in manifests.values()),
             "e1_cells": sum(len(r) for r in summaries.values()),
             "e1_successes": sum(r["status"] == "SUCCESS" for rs in summaries.values() for r in rs),
             "e2_cells": len(rows), "e2_successes": sum(r["status"] == "SUCCESS" for r in rows),
             "full_denominator_component_rows": len(components),
             "replicate_01_case_macro_delta_iou": a2["case_macro_iou"] - a0["case_macro_iou"],
             "replicate_01_relative_contamination_proxy_reduction": 1 - a2["case_macro_contamination_proxy"] / a0["case_macro_contamination_proxy"],
             "replicate_01_e2_failure_inclusive_unsupported_reference_delta":
                 sum(float(r["unsupported_reference_rate"]) for r in rows if r["condition"] == e1.CONDITIONS[2]) / 5
                 - sum(float(r["unsupported_reference_rate"]) for r in rows if r["condition"] == e1.CONDITIONS[0]) / 5,
             "decision": "NO_GO for promotion; preserve repeats as exploratory, not confirmatory",
             "recorded_e1_tokens_lower_bound": sum(r["recorded_tokens_lower_bound"] for r in aggregate),
             "recorded_e2_tokens": sum(int(r["total_tokens"]) for r in rows)}
    (RESULTS / "closeout_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
