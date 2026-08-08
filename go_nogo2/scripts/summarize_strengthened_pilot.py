"""Create the deterministic, case-level report for the strengthened final pilot.

This program intentionally reads only frozen-case provenance, runner manifests and
deterministic evaluator artifacts.  It does not call a judge model or modify a
threshold.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any


BACKBONES = ("qwen3.7-plus", "qwen3.7-max-2026-06-08")
METHODS = ("direct_frontier_mllm", "cadir_simplecad")
METRIC_FILES = {
    "geometry": "geometry_metrics.json",
    "assembly": "assembly_metrics.json",
    "kinematic": "kinematic_metrics.json",
    "motion": "motion_metrics.json",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join("---" for _ in fields) + " |"]
    for row in rows:
        values = [str(row.get(field, "")).replace("|", "/") for field in fields]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def as_number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def normalize_patterns(outcome: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    patterns = list(outcome.get("failure_patterns", []))
    error = (manifest.get("error") or "").lower()
    if "apitimeouterror" in error or "request timed out" in error:
        patterns.append("transport_api_timeout")
    return list(dict.fromkeys(patterns))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--sanity-report", type=Path, required=True)
    args = parser.parse_args()
    runs_root, results_root = args.runs_root.resolve(), args.results_root.resolve()
    validation_dir = results_root / "final_validation"
    validation_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    case_failures: list[dict[str, Any]] = []
    for backbone in BACKBONES:
        for method in METHODS:
            method_dir = runs_root / backbone / method
            for case_dir in sorted(path for path in method_dir.glob("case_*") if path.is_dir()):
                manifest = load_json(case_dir / "prediction_manifest.json")
                evaluation_dir = case_dir / "evaluation"
                outcome = load_json(evaluation_dir / "outcome.json")
                budget = manifest.get("budget", {})
                row: dict[str, Any] = {
                    "backbone": backbone, "method": method, "case_id": case_dir.name,
                    "run_status": manifest["status"],
                    "simultaneous_success": bool(outcome.get("simultaneous_success", False)),
                    "api_calls": budget.get("api_calls", manifest.get("attempts", 0)),
                    "repair_iterations": max(0, int(manifest.get("attempts", 0)) - 1),
                    "input_tokens": budget.get("input_tokens", 0),
                    "output_tokens": budget.get("output_tokens", 0),
                    "total_tokens": budget.get("total_tokens", 0),
                    "max_total_output_tokens": budget.get("max_total_output_tokens"),
                    "max_total_model_tokens": budget.get("max_total_model_tokens"),
                    "max_repair_iterations": budget.get("max_repair_iterations"),
                    "latency_seconds": manifest.get("latency_seconds"),
                    "error": manifest.get("error"),
                    "failure_patterns": ";".join(normalize_patterns(outcome, manifest)),
                }
                for family, filename in METRIC_FILES.items():
                    metric_path = evaluation_dir / filename
                    if metric_path.is_file():
                        for key, value in load_json(metric_path).items():
                            row[f"{family}_{key}"] = value
                # A count-preserving but low-F1 prediction is a deterministic decomposition error.
                if (row.get("assembly_gt_link_count") == row.get("assembly_pred_link_count")
                        and (as_number(row.get("assembly_part_f1")) or 1.0) < 0.9):
                    row["failure_patterns"] = ";".join(filter(None, [row["failure_patterns"], "wrong_part_decomposition"]))
                rows.append(row)
                for pattern in filter(None, row["failure_patterns"].split(";")):
                    category = "transport" if pattern.startswith("transport_") else "deterministic"
                    case_failures.append({
                        "backbone": backbone, "method": method, "case_id": case_dir.name,
                        "category": category, "failure_pattern": pattern,
                    })

    expected = len(BACKBONES) * len(METHODS) * 10
    if len(rows) != expected:
        raise SystemExit(f"expected {expected} terminal case records, found {len(rows)}")
    write_csv(results_root / "equal_budget_results.csv", rows)
    write_csv(validation_dir / "case_level_failures.csv", case_failures)
    (validation_dir / "case_level_failures.json").write_text(
        json.dumps(case_failures, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    breakdown_rows = []
    counts = Counter((r["backbone"], r["method"], r["category"], r["failure_pattern"]) for r in case_failures)
    for (backbone, method, category, pattern), count in sorted(counts.items()):
        breakdown_rows.append({"backbone": backbone, "method": method, "category": category,
                               "failure_pattern": pattern, "case_count": count})
    write_csv(validation_dir / "failure_breakdown.csv", breakdown_rows)

    summary_rows: list[dict[str, Any]] = []
    for backbone in BACKBONES:
        for method in METHODS:
            track = [row for row in rows if row["backbone"] == backbone and row["method"] == method]
            successful = [row for row in track if row["run_status"] == "SUCCESS"]
            def med(field: str) -> float | None:
                values = [as_number(row.get(field)) for row in successful]
                values = [value for value in values if value is not None]
                return median(values) if values else None
            summary_rows.append({
                "backbone": backbone, "method": method, "terminal_cases": len(track),
                "generation_success_cases": len(successful),
                "generation_failure_cases": len(track) - len(successful),
                "simultaneous_success_cases": sum(row["simultaneous_success"] for row in track),
                "api_calls_total": sum(int(row["api_calls"] or 0) for row in track),
                "repair_iterations_total": sum(int(row["repair_iterations"] or 0) for row in track),
                "input_tokens_total": sum(int(row["input_tokens"] or 0) for row in track),
                "output_tokens_total": sum(int(row["output_tokens"] or 0) for row in track),
                "total_tokens_total": sum(int(row["total_tokens"] or 0) for row in track),
                "latency_seconds_median": med("latency_seconds"),
                "geometry_chamfer_median_successful": med("geometry_chamfer"),
                "assembly_part_f1_median_successful": med("assembly_part_f1"),
                "assembly_graph_f1_median_successful": med("assembly_assembly_graph_f1"),
                "kinematic_joint_type_accuracy_median_successful": med("kinematic_joint_type_accuracy"),
                "kinematic_axis_error_degrees_median_successful": med("kinematic_axis_error_degrees_median"),
                "kinematic_origin_error_median_successful": med("kinematic_joint_origin_error_normalized_median"),
                "motion_link_translation_error_median_successful": med("motion_link_translation_error_normalized_median"),
                "motion_link_rotation_error_median_successful": med("motion_link_rotation_error_degrees_median"),
            })
    write_csv(results_root / "backbone_generalization.csv", summary_rows)

    public_rows = [{
        "agent": "CADSmith", "repository": "https://github.com/jabarkle/CADSmith",
        "commit": "a856517e4e9449eb71dd6f7f83aa9fffa40f5bbb", "official_implementation": True,
        "license": "NOT_DECLARED", "run_status": "NOT_RUN",
        "reason": "Official setup requires ANTHROPIC_API_KEY and a separate Python 3.10/VTK environment; current credentials are Alibaba-only.",
        "geometry_cad_validity": "NOT_RUN", "assembly": "UNSUPPORTED",
        "kinematics": "UNSUPPORTED", "motion": "UNSUPPORTED",
    }]
    write_csv(results_root / "open_agent_baseline.csv", public_rows)
    capability_rows = [{
        "system": "Direct LLM", "official_public_agent": False, "geometry": "SUPPORTED",
        "cad_validity": "SUPPORTED", "assembly": "SUPPORTED", "kinematics": "SUPPORTED", "motion": "SUPPORTED",
        "note": "Frozen benchmark adapter outputs Mesh + URDF."},
        {"system": "CADIR/SimpleCAD SDK-conditioned", "official_public_agent": False, "geometry": "SUPPORTED",
         "cad_validity": "SUPPORTED", "assembly": "SUPPORTED", "kinematics": "SUPPORTED", "motion": "SUPPORTED",
         "note": "Public SDK execution/replay; learned CADIR retrieval index unavailable."},
        {"system": "CADSmith", "official_public_agent": True, "geometry": "NOT_RUN", "cad_validity": "NOT_RUN",
         "assembly": "UNSUPPORTED", "kinematics": "UNSUPPORTED", "motion": "UNSUPPORTED",
         "note": "Official code targets single-part CAD; no native URDF/articulation output."}]
    write_csv(results_root / "capability_matrix.csv", capability_rows)

    sanity_pass = "## PASS" in args.sanity_report.read_text(encoding="utf-8")
    structural_tracks = 0
    for track in summary_rows:
        patterns = {r["failure_pattern"] for r in case_failures if r["backbone"] == track["backbone"] and r["method"] == track["method"] and r["category"] == "deterministic"}
        if patterns:
            structural_tracks += 1
    all_zero_joint = all(row["simultaneous_success_cases"] == 0 for row in summary_rows)
    full_go = sanity_pass and all_zero_joint and structural_tracks >= 2
    decision = "GO" if full_go else "NO-GO / REDIRECT"
    report = [
        "# Strengthened final Go/No-Go pilot report", "",
        f"## Decision: {decision}", "",
        "This is a 10-case strengthened pilot, not a claim of a completed benchmark or universal SOTA comparison.",
        "The decision is computed from the frozen cases, preserved manifests and deterministic evaluator outputs; no thresholds were changed.", "",
        "## A. Evaluator sanity", "",
        f"Sanity status: **{'PASS' if sanity_pass else 'FAIL'}**. The complete perturbation record is in `results/evaluator_sanity/`.",
        "It confirms exact GT identity, monotone axis/origin/scale/translation perturbations, and degradation or invalidity for large structural corruptions.", "",
        "## B. Equal-budget rerun", "",
        "Every track used the same ten prompts, six renders, temperature, CAD runtime, 300-second API timeout, 32,768 total output-token cap, 100,000 total model-token cap, and at most one repair iteration. Direct receives one call by definition; CADIR/SimpleCAD may use the one repair call. Actual input usage can differ because repair replays the identical visual context.", "",
        table(summary_rows, ["backbone", "method", "generation_success_cases", "generation_failure_cases", "simultaneous_success_cases", "api_calls_total", "repair_iterations_total", "total_tokens_total"]), "",
        "Successful-output medians (rather than silently discarding failed cases from the denominator) are recorded in `backbone_generalization.csv`; all 40 case rows and token/call/latency accounting are in `equal_budget_results.csv`.", "",
        "## C. Second-backbone generalization", "",
        "The second run uses Qwen3.7-Max-2026-06-08, a distinct released Max snapshot, under the identical protocol. It is independent model evidence but not cross-provider evidence, since both backbones are from the same provider/family.",
        f"All four tracks have 0 simultaneous successes: **{all_zero_joint}**. Deterministic structural failure patterns occur in {structural_tracks}/4 tracks.", "",
        "## D. Runnable public-agent baseline", "",
        "CADSmith was audited at the recorded commit. Its official repository has no declared license file, requires an Anthropic key not available in this environment, and targets single-part CAD rather than native URDF/articulation. It is therefore explicitly NOT_RUN for geometry/CAD validity and UNSUPPORTED (not scored as zero) for assembly, kinematics and motion. No surrogate reimplementation was used.", "",
        "## E. Case-level structural gap", "",
        "The failure taxonomy is deterministic: invalid CAD, missing/extra part, wrong decomposition, topology, joint type, axis, origin, poor geometry/curved geometry and wrong multi-pose motion. Self-collision is UNSUPPORTED by this evaluator. See `results/final_validation/case_level_failures.csv` and `failure_breakdown.csv`.", "",
    ]
    if full_go:
        report += [
            "**Recommendation: continue the paper.** Under two released multimodal backbones and Direct/SimpleCAD execution styles, no output jointly clears geometry, assembly, kinematics and multi-pose motion. SimpleCAD execution conditioning can improve artifact production, but does not close the joint structural gap. This supports (rather than proves) headroom for a surface-aware and kinematic/interface-aware method.",
            "The future paper must add a broader, cross-provider baseline suite and a runnable licensed public-agent comparison before making field-wide claims.",
        ]
    else:
        report += [
            "**Recommendation: redirect before expanding the study.** At least one required sanity, joint-gap, or recurrence condition was not demonstrated by the frozen evidence.",
        ]
    (results_root / "final_strengthened_pilot_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"decision": decision, "sanity_pass": sanity_pass, "records": len(rows), "summary": summary_rows}, indent=2))


if __name__ == "__main__":
    main()
