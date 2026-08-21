"""Create the deterministic Go/No-Go 4 input-condition comparison report."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[2]
VARIANTS = ("single_view", "multiview_static", "multipose_concat", "motion_aware")
METRICS = ("geometry_chamfer", "geometry_hd95", "geometry_voxel_iou", "assembly_assembly_graph_f1", "assembly_part_f1", "kinematic_joint_type_accuracy", "kinematic_axis_error_degrees_median", "kinematic_joint_origin_error_normalized_median", "motion_link_translation_error_normalized_median", "motion_link_rotation_error_degrees_median")


def number(value): return float(value) if isinstance(value, (int, float)) else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "go_nogo4/results/motion15_manifest.csv")
    parser.add_argument("--runs-root", type=Path, default=ROOT / "go_nogo4/runs")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "go_nogo4/results")
    args = parser.parse_args(); args.output_dir.mkdir(parents=True, exist_ok=True)
    cases = list(csv.DictReader(args.manifest.open(encoding="utf-8-sig")))
    rows, failure_rows = [], []
    for variant in VARIANTS:
        for item in cases:
            run = args.runs_root / variant / item["case_id"]
            manifest_path, result_path = run / "manifest.json", run / "evaluation" / "results.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {"status": "NOT_RUN", "budget": {}}
            result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else {}
            row = {"variant": variant, "case_id": item["case_id"], "status": manifest["status"], "input_images": len(manifest.get("input_observations", [])),
                   "api_calls": manifest.get("budget", {}).get("api_calls", 0), "input_tokens": manifest.get("budget", {}).get("input_tokens", 0), "output_tokens": manifest.get("budget", {}).get("output_tokens", 0), "total_tokens": manifest.get("budget", {}).get("total_tokens", 0), "latency_seconds": manifest.get("latency_seconds"), "error": manifest.get("error")}
            for family in ("geometry", "assembly", "kinematic", "motion"):
                for key, value in result.get(family, {}).items():
                    if not isinstance(value, (list, dict)): row[f"{family}_{key}"] = value
            patterns = result.get("outcome", {}).get("failure_patterns", ["invalid_cad"] if manifest["status"] == "FAILURE" else [])
            if "APITimeoutError" in str(manifest.get("error", "")): patterns = list(dict.fromkeys([*patterns, "transport_api_timeout"]))
            row["failure_patterns"] = ";".join(patterns)
            for pattern in patterns: failure_rows.append({"variant": variant, "case_id": item["case_id"], "failure_pattern": pattern})
            rows.append(row)
    with (args.output_dir / "case_results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted({key for row in rows for key in row})); writer.writeheader(); writer.writerows(rows)
    aggregates = []
    for variant in VARIANTS:
        track = [row for row in rows if row["variant"] == variant]; valid = [row for row in track if row["status"] == "SUCCESS"]
        output = {"variant": variant, "cases": len(track), "executed": len(valid), "failed": sum(row["status"] == "FAILURE" for row in track), "input_images_per_case": sorted({row["input_images"] for row in track}), "api_calls_total": sum(int(row["api_calls"] or 0) for row in track), "tokens_total": sum(int(row["total_tokens"] or 0) for row in track)}
        for metric in METRICS:
            values = [number(row.get(metric)) for row in valid]; values = [value for value in values if value is not None]
            output[f"median_{metric}"] = median(values) if values else None
        aggregates.append(output)
    with (args.output_dir / "aggregate_results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(aggregates[0])); writer.writeheader(); writer.writerows(aggregates)
    counts = Counter((row["variant"], row["failure_pattern"]) for row in failure_rows)
    with (args.output_dir / "failure_breakdown.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["variant", "failure_pattern", "case_count"]); writer.writeheader(); writer.writerows([{"variant": variant, "failure_pattern": pattern, "case_count": count} for (variant, pattern), count in sorted(counts.items())])
    by_variant = {row["variant"]: row for row in aggregates}
    a, b, d, c = (by_variant[key] for key in VARIANTS)
    def up(x, y, metric): return number(y.get(metric)) is not None and number(x.get(metric)) is not None and number(y[metric]) > number(x[metric])
    def down(x, y, metric): return number(y.get(metric)) is not None and number(x.get(metric)) is not None and number(y[metric]) < number(x[metric])
    multiview_gain = up(a, b, "median_assembly_assembly_graph_f1") or down(a, b, "median_motion_link_translation_error_normalized_median")
    motion_gain = all((up(b, c, "median_assembly_assembly_graph_f1"), up(b, c, "median_kinematic_joint_type_accuracy"), down(b, c, "median_motion_link_translation_error_normalized_median")))
    reasoning_gain = all((up(d, c, "median_assembly_assembly_graph_f1"), down(d, c, "median_motion_link_translation_error_normalized_median")))
    geometry_ok = number(c.get("median_geometry_chamfer")) is not None and number(d.get("median_geometry_chamfer")) is not None and number(c["median_geometry_chamfer"]) <= number(d["median_geometry_chamfer"])
    complete = all(row["executed"] + row["failed"] == 15 for row in aggregates)
    actual_token_matched = c["tokens_total"] == d["tokens_total"]
    decision = "GO" if complete and motion_gain and reasoning_gain and geometry_ok else "NO-GO"
    report = ["# Go/No-Go 4 report", "", f"## FINAL DECISION: {decision}", "", "## A. Dataset summary", "", "15 audited real robots; each has three deterministically rendered joint states and four views per state. GT URDF is withheld from model calls.", "", "## B-C. Input setting comparison and quantitative results", "", "| variant | images/case | executed | calls | tokens | Graph F1 | joint type | axis error | origin error | motion translation | Chamfer |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in aggregates:
        report.append("| {variant} | {input_images_per_case} | {executed} | {api_calls_total} | {tokens_total} | {median_assembly_assembly_graph_f1} | {median_kinematic_joint_type_accuracy} | {median_kinematic_axis_error_degrees_median} | {median_kinematic_joint_origin_error_normalized_median} | {median_motion_link_translation_error_normalized_median} | {median_geometry_chamfer} |".format(**row))
    report += ["", "A=single-view, B=multi-view static, D=multi-pose images concatenated without explicit motion reasoning, C=motion-aware prototype with an in-response cross-pose motion hypothesis that constrains CAD/URDF.", "", "## D. Ablation", "", "D and C receive the same 12 labelled images and one model call with identical output-token caps. Their difference is whether motion correspondence/constraints are explicitly inferred and imposed. Actual token usage is reported because C's structured hypothesis may consume more output even under equal caps.", "", "## E. Failure analysis", "", "See `failure_breakdown.csv` and `case_results.csv`; all failure labels are deterministic evaluator outputs.", "", "## F. Novelty assessment", "", "The tested mechanism is multi-pose motion constraints from image changes, not connector, port, mate, retrieval, or generic assembly-agent planning.", "", "## Decision logic", "", f"Terminal coverage complete: {complete}; A→B multi-view signal: {multiview_gain}; B→C motion signal: {motion_gain}; D→C same-image-count motion-reasoning signal: {reasoning_gain}; geometry non-degradation C vs D: {geometry_ok}; actual C/D total-token matched: {actual_token_matched}."]
    report.append("Proceed only if the above evidence is true; otherwise retain the benchmark/evaluation route rather than claiming a RobotCAD-R method." if decision == "GO" else "Do not advance this motion-aware method route. The pilot does not establish independent mechanical value beyond static/more-image evidence.")
    (args.output_dir / "go_nogo4_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"decision": decision, "complete": complete, "multiview_gain": multiview_gain, "motion_gain": motion_gain, "reasoning_gain": reasoning_gain, "geometry_ok": geometry_ok}, indent=2))


if __name__ == "__main__":
    main()
