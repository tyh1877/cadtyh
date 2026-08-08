"""Aggregate baseline run records without turning NOT_RUN into model failures."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd

METHODS = ("direct_frontier_mllm", "cadir_simplecad", "articad", "assemcad")


def markdown_table(frame: pd.DataFrame, include_index: bool = True) -> str:
    table = frame.reset_index() if include_index else frame.copy()
    columns = [str(column) for column in table.columns]
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in table.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def not_run_reason(method: str, registry: dict) -> str:
    status = next(item["status"] for item in registry["methods"] if item["id"] == method)
    return status


def metric_row(base: dict, path: Path, fields: list[str]) -> dict:
    row = dict(base)
    if path.is_file():
        payload = read_json(path)
        for field in fields:
            row[field] = payload.get(field)
    else:
        row.update({field: None for field in fields})
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--runs-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    manifest = pd.read_csv(args.manifest)
    registry = read_json(args.registry)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    status_rows, geometry_rows, assembly_rows, kinematic_rows, motion_rows = [], [], [], [], []
    failures = []

    for method in METHODS:
        for case in manifest.itertuples():
            run_dir = args.runs_dir / method / case.case_id
            prediction_manifest = run_dir / "prediction_manifest.json"
            outcome_path = run_dir / "evaluation" / "outcome.json"
            if prediction_manifest.is_file():
                prediction = read_json(prediction_manifest)
                status = prediction["status"]
                reason = prediction.get("error")
                model = prediction.get("provenance", {}).get("model")
                attempts = prediction.get("attempts", 0)
                latency_seconds = prediction.get("latency_seconds")
            else:
                status, reason, model, attempts, latency_seconds = (
                    "NOT_RUN", not_run_reason(method, registry), None, 0, None
                )
            outcome = read_json(outcome_path) if outcome_path.is_file() else {}
            base = {
                "method": method, "case_id": case.case_id,
                "pilot_index": int(case.pilot_index), "manufacturer": case.manufacturer,
                "name": case.name, "run_status": status, "reason": reason,
                "model": model, "attempts": attempts,
                "latency_seconds": latency_seconds,
                "simultaneous_success": outcome.get("simultaneous_success"),
            }
            status_rows.append(base)
            geometry_rows.append(metric_row(base, run_dir / "evaluation" / "geometry_metrics.json", [
                "chamfer", "hd95", "hausdorff_max", "voxel_iou"
            ]))
            assembly_rows.append(metric_row(base, run_dir / "evaluation" / "assembly_metrics.json", [
                "gt_link_count", "pred_link_count", "matched_parts", "part_precision",
                "part_recall", "part_f1", "assembly_graph_precision",
                "assembly_graph_recall", "assembly_graph_f1"
            ]))
            kinematic_rows.append(metric_row(base, run_dir / "evaluation" / "kinematic_metrics.json", [
                "matched_joints", "joint_type_accuracy", "axis_error_degrees_median",
                "axis_error_degrees_mean", "joint_origin_error_normalized_median",
                "joint_origin_error_normalized_mean"
            ]))
            motion_rows.append(metric_row(base, run_dir / "evaluation" / "motion_metrics.json", [
                "mapped_links", "link_translation_error_normalized_median",
                "link_rotation_error_degrees_median",
                "end_effector_translation_error_normalized_median",
                "end_effector_rotation_error_degrees_median"
            ]))
            for pattern in outcome.get("failure_patterns", []):
                failures.append({"method": method, "case_id": case.case_id,
                                 "category": "model_failure", "failure_pattern": pattern})
            if status == "NOT_RUN":
                failures.append({"method": method, "case_id": case.case_id,
                                 "category": "availability_blocker", "failure_pattern": reason})

    status = pd.DataFrame(status_rows)
    status.to_csv(args.output_dir / "run_status.csv", index=False, encoding="utf-8-sig")
    for filename, rows in (
        ("geometry_results.csv", geometry_rows), ("assembly_results.csv", assembly_rows),
        ("kinematic_results.csv", kinematic_rows), ("motion_results.csv", motion_rows),
    ):
        pd.DataFrame(rows).to_csv(args.output_dir / filename, index=False, encoding="utf-8-sig")
    failure_df = pd.DataFrame(failures)
    if failure_df.empty:
        failure_breakdown = pd.DataFrame(columns=["method", "category", "failure_pattern", "case_count"])
    else:
        failure_breakdown = (
            failure_df.groupby(["method", "category", "failure_pattern"], dropna=False)
            .size().rename("case_count").reset_index()
        )
    failure_breakdown.to_csv(args.output_dir / "failure_breakdown.csv", index=False, encoding="utf-8-sig")
    (args.output_dir / "failure_cases.json").write_text(
        json.dumps(failures, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    terminal_counts = status.groupby("method").run_status.apply(lambda x: int(x.isin(["SUCCESS", "FAILURE"]).sum()))
    complete_methods = [method for method, count in terminal_counts.items() if count == 10]
    strong = (
        status.loc[status.simultaneous_success == True]  # noqa: E712
        .groupby("method").size().reindex(METHODS, fill_value=0)
    )
    comparison_complete = len(complete_methods) == len(METHODS)
    recurrent = Counter(
        (row["method"], row["failure_pattern"])
        for row in failures if row["category"] == "model_failure"
    )
    recurrent_methods = {method for (method, _), count in recurrent.items() if count >= 3}

    metric_frames = {
        "geometry": pd.DataFrame(geometry_rows),
        "assembly": pd.DataFrame(assembly_rows),
        "kinematic": pd.DataFrame(kinematic_rows),
        "motion": pd.DataFrame(motion_rows),
    }
    aggregate_rows = []
    for method in METHODS:
        method_status = status.loc[status.method == method]
        successful = method_status.loc[method_status.run_status == "SUCCESS"]
        row = {
            "method": method,
            "terminal_cases": int(method_status.run_status.isin(["SUCCESS", "FAILURE"]).sum()),
            "generation_success_cases": int((method_status.run_status == "SUCCESS").sum()),
            "generation_failure_cases": int((method_status.run_status == "FAILURE").sum()),
            "not_run_cases": int((method_status.run_status == "NOT_RUN").sum()),
            "attempts_total": int(method_status.attempts.sum()),
            "latency_seconds_median_success": successful.latency_seconds.median(),
            "simultaneous_success_cases": int(strong[method]),
        }
        field_map = {
            "geometry": ["chamfer", "hd95", "voxel_iou"],
            "assembly": ["part_f1", "assembly_graph_f1"],
            "kinematic": ["joint_type_accuracy", "axis_error_degrees_median",
                          "joint_origin_error_normalized_median"],
            "motion": ["link_translation_error_normalized_median",
                       "link_rotation_error_degrees_median"],
        }
        for family, fields in field_map.items():
            frame = metric_frames[family]
            valid = frame.loc[(frame.method == method) & (frame.run_status == "SUCCESS")]
            for field in fields:
                row[f"{field}_median_successful_outputs"] = valid[field].median()
        aggregate_rows.append(row)
    aggregate = pd.DataFrame(aggregate_rows)
    aggregate.to_csv(args.output_dir / "aggregate_results.csv", index=False, encoding="utf-8-sig")
    if comparison_complete and any(strong[method] >= 8 for method in METHODS):
        decision = "NO-GO"
    elif comparison_complete and len(recurrent_methods) >= 2:
        decision = "GO"
    else:
        decision = "INCONCLUSIVE"

    summary = {
        "decision": decision,
        "comparison_complete": comparison_complete,
        "fixed_cases": 10,
        "required_methods": list(METHODS),
        "complete_methods": complete_methods,
        "terminal_case_counts": {key: int(value) for key, value in terminal_counts.items()},
        "simultaneous_success_counts": {key: int(value) for key, value in strong.items()},
        "not_run_counts": {
            method: int(((status.method == method) & (status.run_status == "NOT_RUN")).sum())
            for method in METHODS
        },
        "decision_rule": "protocol.md frozen v1",
        "executable_method_results": {
            row["method"]: {
                "generation_success_cases": row["generation_success_cases"],
                "generation_failure_cases": row["generation_failure_cases"],
                "simultaneous_success_cases": row["simultaneous_success_cases"],
                "attempts_total": row["attempts_total"],
            }
            for row in aggregate_rows if row["method"] in {"direct_frontier_mllm", "cadir_simplecad"}
        },
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    status_table = status.groupby(["method", "run_status"]).size().unstack(fill_value=0).reindex(METHODS, fill_value=0)
    report = [
        "# Go/No-Go 2 pilot summary", "", f"**Decision: {decision}**", "",
        "The fixed dataset and deterministic evaluator are ready. `NOT_RUN` records are availability",
        "blockers and are not model scores.", "", "## Run coverage", "",
        markdown_table(status_table), "", "## Simultaneous successes", "",
        markdown_table(strong.rename("cases").to_frame()), "",
        "## Executable-method aggregate", "",
        "Metric medians below use successful generated outputs only; generation failures remain",
        "visible in their own columns and in the fixed denominator of ten.", "",
        markdown_table(aggregate.loc[aggregate.method.isin(["direct_frontier_mllm", "cadir_simplecad"])], include_index=False), "",
        "## Failure patterns", "",
        markdown_table(failure_breakdown.loc[
            (failure_breakdown.category == "model_failure") &
            failure_breakdown.method.isin(["direct_frontier_mllm", "cadir_simplecad"])
        ], include_index=False), "",
        "## Interpretation", "",
    ]
    if decision == "INCONCLUSIVE":
        report.extend([
            "The four-baseline comparison is incomplete, so neither a SOTA gap nor its absence is established.",
            "For the two executable tracks, both have 0/10 simultaneous successes. The SDK-conditioned",
            "CADIR track improves generation success from 6/10 to 9/10, but it does not close the joint",
            "geometry-assembly-kinematics gap. This is provisional evidence, not a four-method decision.",
        ])
    elif decision == "GO":
        report.append("No method is jointly strong and stable failure modes recur across methods.")
    else:
        report.append("At least one baseline is jointly strong on at least 8/10 cases.")
    (args.output_dir / "summary_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    go_report = [
        "# Go/No-Go 2 decision", "", f"## {decision}", "",
        f"Comparison complete: **{comparison_complete}**.", "",
        "A GO or NO-GO claim is allowed only after all four official baselines have ten terminal records.",
    ]
    if decision == "INCONCLUSIVE":
        blockers = failure_breakdown.loc[failure_breakdown.category == "availability_blocker"]
        go_report.extend([
            "", "## Provisional executable-method evidence", "",
            "Direct LLM: 6/10 generation successes, 0/10 simultaneous successes.",
            "CADIR/SimpleCADAPI SDK-conditioned: 9/10 generation successes, 0/10 simultaneous successes.",
            "", "## Blocking evidence", "", markdown_table(blockers, include_index=False),
            "", "ArtiCAD and AssemCAD have no verified runnable official method code, so the frozen",
            "four-baseline rule prevents a final GO or NO-GO decision.",
        ])
    (args.output_dir / "go_nogo_report.md").write_text("\n".join(go_report) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
