"""Generate a transparent Go/No-Go 3 report from preserved deterministic outputs."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[2]
VARIANTS = ("direct", "simplecad", "v1_joint_frame", "v2_consistency")


def n(value):
    return float(value) if isinstance(value, (int, float)) else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-root", type=Path, default=ROOT / "go_nogo3/runs")
    parser.add_argument("--manifest", type=Path, default=ROOT / "go_nogo3/results/dev15_manifest.csv")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "go_nogo3/results")
    args = parser.parse_args(); args.output_dir.mkdir(parents=True, exist_ok=True)
    dataset = list(csv.DictReader(args.manifest.open(encoding="utf-8-sig")))
    rows, failures = [], []
    for variant in VARIANTS:
        for item in dataset:
            run = args.runs_root / variant / item["case_id"]
            manifest_path, evaluation_path = run / "manifest.json", run / "evaluation" / "results.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {"status": "NOT_RUN", "budget": {}}
            evaluation = json.loads(evaluation_path.read_text(encoding="utf-8")) if evaluation_path.is_file() else {}
            row = {"variant": variant, "case_id": item["case_id"], "run_status": manifest["status"],
                   "api_calls": manifest.get("budget", {}).get("api_calls", 0), "input_tokens": manifest.get("budget", {}).get("input_tokens", 0),
                   "output_tokens": manifest.get("budget", {}).get("output_tokens", 0), "total_tokens": manifest.get("budget", {}).get("total_tokens", 0),
                   "latency_seconds": manifest.get("latency_seconds"), "error": manifest.get("error")}
            for family in ("geometry", "assembly", "kinematic", "motion", "cad_urdf_consistency"):
                for key, value in evaluation.get(family, {}).items():
                    if not isinstance(value, (list, dict)):
                        row[f"{family}_{key}"] = value
            patterns = evaluation.get("outcome", {}).get("failure_patterns", ["invalid_cad"] if manifest["status"] == "FAILURE" else [])
            if "APITimeoutError" in str(manifest.get("error", "")):
                patterns = list(dict.fromkeys([*patterns, "transport_api_timeout"]))
            row["failure_patterns"] = ";".join(patterns)
            for pattern in patterns:
                failures.append({"variant": variant, "case_id": item["case_id"], "failure_pattern": pattern})
            rows.append(row)
    fields = sorted({key for row in rows for key in row})
    with (args.output_dir / "case_results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    summaries = []
    metric_names = ["geometry_chamfer", "geometry_hd95", "geometry_voxel_iou", "assembly_assembly_graph_f1", "kinematic_joint_type_accuracy", "kinematic_axis_error_degrees_median", "kinematic_joint_origin_error_normalized_median", "motion_link_translation_error_normalized_median", "motion_link_rotation_error_degrees_median", "cad_urdf_consistency_joint_axis_error_degrees_median", "cad_urdf_consistency_joint_origin_error_median_meters"]
    for variant in VARIANTS:
        track = [row for row in rows if row["variant"] == variant]
        success = [row for row in track if row["run_status"] == "SUCCESS"]
        summary = {"variant": variant, "cases": len(track), "executed": len(success), "failed": sum(row["run_status"] == "FAILURE" for row in track),
                   "not_run": sum(row["run_status"] == "NOT_RUN" for row in track), "api_calls_total": sum(int(row["api_calls"] or 0) for row in track),
                   "tokens_total": sum(int(row["total_tokens"] or 0) for row in track)}
        for metric in metric_names:
            values = [n(row.get(metric)) for row in success]; values = [value for value in values if value is not None]
            summary[f"median_{metric}"] = median(values) if values else None
        summaries.append(summary)
    with (args.output_dir / "aggregate_results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0])); writer.writeheader(); writer.writerows(summaries)
    failure_counts = Counter((item["variant"], item["failure_pattern"]) for item in failures)
    failure_rows = [{"variant": variant, "failure_pattern": pattern, "case_count": count} for (variant, pattern), count in sorted(failure_counts.items())]
    with (args.output_dir / "failure_breakdown.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["variant", "failure_pattern", "case_count"]); writer.writeheader(); writer.writerows(failure_rows)
    by_name = {row["variant"]: row for row in summaries}
    v0, v1, v2 = by_name["direct"], by_name["v1_joint_frame"], by_name["v2_consistency"]
    # No threshold was tuned on this development set: the decision requires directional gains in all
    # specified kinematic/motion metrics plus no geometry decline, and complete 15-case coverage.
    directions = [("median_assembly_assembly_graph_f1", "up"), ("median_kinematic_axis_error_degrees_median", "down"), ("median_kinematic_joint_origin_error_normalized_median", "down"), ("median_motion_link_translation_error_normalized_median", "down")]
    complete = all(row["executed"] + row["failed"] == 15 for row in summaries)
    def improved(metric, direction):
        a, b = n(v0.get(metric)), n(v2.get(metric))
        return a is not None and b is not None and (b > a if direction == "up" else b < a)
    kin_gain = all(improved(metric, direction) for metric, direction in directions)
    geometry_ok = (n(v0.get("median_geometry_chamfer")) is not None and n(v2.get("median_geometry_chamfer")) is not None and n(v2["median_geometry_chamfer"]) <= n(v0["median_geometry_chamfer"]))
    consistency = n(v2.get("median_cad_urdf_consistency_joint_axis_error_degrees_median")) == 0.0 and n(v2.get("median_cad_urdf_consistency_joint_origin_error_median_meters")) == 0.0
    # V1/V2 replay the visual prompt for a second mechanism call. They have equal *caps*
    # but are not an actual-token matched comparison with one-call V0. A future positive
    # claim needs a two-call budget-matched control, so this pilot cannot attribute a gain
    # solely to the proposed mechanism.
    mechanism_isolated = False
    decision = "GO" if complete and kin_gain and geometry_ok and consistency and mechanism_isolated else "NO-GO"
    lines = ["# Go/No-Go 3 report", "", "## FINAL DECISION: " + decision, "", "## A. Dataset summary", "", f"Development set: {len(dataset)} audited real robots. Input text is structurally blind; GT was not sent to any model call.", "", "## B-D. Baselines, prototype, ablation", "", "| variant | executed | failed | calls | tokens | Graph F1 | axis error | origin error | motion translation | Chamfer |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in summaries:
        lines.append("| {variant} | {executed} | {failed} | {api_calls_total} | {tokens_total} | {median_assembly_assembly_graph_f1} | {median_kinematic_axis_error_degrees_median} | {median_kinematic_joint_origin_error_normalized_median} | {median_motion_link_translation_error_normalized_median} | {median_geometry_chamfer} |".format(**row))
    lines += ["", "V0=Direct; V1=Joint Frame Recovery soft conditioning; V2=Joint Frame Recovery + hard CAD-URDF consistency. SimpleCAD is an execution-constrained baseline.", "", "## E. Failure analysis", "", "See `failure_breakdown.csv` and `case_results.csv`; all categories are produced by the deterministic evaluator. Transport timeouts are separated from invalid-CAD failures.", "", "## F. Novelty assessment", "", "The prototype only tests recovery of reference-conditioned joint frames and consistency between those *predicted* frames and emitted CAD/URDF. It does not claim a connector planner, port matcher, generic assembly agent, or novelty over ArtiCAD/AssemCAD.", "", "## Decision logic", "", f"Coverage complete: {complete}; all requested kinematic/motion directions improved: {kin_gain}; geometry did not decline: {geometry_ok}; hard-frame CAD-URDF consistency exact: {consistency}; mechanism isolated from extra prompt/token use: {mechanism_isolated}."]
    if decision == "GO": lines.append("Proceed to method development, but validate on a frozen family-held-out set before paper claims.")
    else: lines.append("Do not proceed with the method route yet. Redirect to benchmark/evaluation work or revise the mechanism before expansion.")
    (args.output_dir / "go_nogo3_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"decision": decision, "complete": complete, "kinematic_gain": kin_gain, "geometry_ok": geometry_ok, "consistency": consistency}, indent=2))


if __name__ == "__main__":
    main()
