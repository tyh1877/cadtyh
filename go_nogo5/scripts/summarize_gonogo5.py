"""Aggregate deterministic verification and repair evidence for Go/No-Go 5."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parents[2]


def load(path: Path): return json.loads(path.read_text(encoding="utf-8"))
def num(value): return float(value) if isinstance(value, (int, float)) else None


def engineering(result: dict) -> dict:
    collision = result.get("engineering", {}).get("collision", {})
    workspace = result.get("engineering", {}).get("workspace", {})
    return {"collision_rate_proxy": num(collision.get("collision_rate_proxy")), "minimum_clearance": num(collision.get("minimum_clearance")), "workspace_iou": num(workspace.get("workspace_iou")), "graph_f1": num(result.get("assembly", {}).get("assembly_graph_f1")), "motion_translation": num(result.get("motion", {}).get("link_translation_error_normalized_median")), "chamfer": num(result.get("geometry", {}).get("chamfer"))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=ROOT / "go_nogo4/data/motion15")
    parser.add_argument("--verification-root", type=Path, default=ROOT / "go_nogo5/runs/verification")
    parser.add_argument("--repair-root", type=Path, default=ROOT / "go_nogo5/runs/repair")
    parser.add_argument("--repair-verification-root", type=Path, default=ROOT / "go_nogo5/runs/repair_verification")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "go_nogo5/results")
    args = parser.parse_args(); args.output_dir.mkdir(parents=True, exist_ok=True)
    rows, paired = [], []
    for case in sorted(args.data_root.glob("dev_arm-*")):
        baseline_path = args.verification_root / case.name / "verification.json"
        repair_manifest_path = args.repair_root / case.name / "manifest.json"
        baseline = load(baseline_path); b = engineering(baseline)
        repair_manifest = load(repair_manifest_path) if repair_manifest_path.is_file() else {"status": "NOT_RUN", "budget": {}}
        repair_path = args.repair_verification_root / case.name / "verification.json"
        repaired = load(repair_path) if repair_path.is_file() else None
        r = engineering(repaired) if repaired else {key: None for key in b}
        row = {"case_id": case.name, "baseline_status": baseline["status"], "repair_status": repair_manifest["status"], "repair_tokens": repair_manifest.get("budget", {}).get("total_tokens", 0), **{f"baseline_{key}": value for key, value in b.items()}, **{f"repair_{key}": value for key, value in r.items()}}
        rows.append(row)
        if baseline["status"] == "SUCCESS" and repair_manifest["status"] == "SUCCESS" and repaired:
            paired.append(row)
    with (args.output_dir / "case_results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    baseline_success = [row for row in rows if row["baseline_status"] == "SUCCESS"]
    def aggregate(source, prefix):
        values = {}
        for key in ("collision_rate_proxy", "minimum_clearance", "workspace_iou", "graph_f1", "motion_translation", "chamfer"):
            series = [row[f"{prefix}_{key}"] for row in source if row[f"{prefix}_{key}"] is not None]
            values[f"median_{key}"] = median(series) if series else None
            values[f"mean_{key}"] = mean(series) if series else None
        return values
    base_stats, repair_stats = aggregate(baseline_success, "baseline"), aggregate(paired, "repair")
    paired_base = aggregate(paired, "baseline")
    failure_common = sum((row["baseline_collision_rate_proxy"] or 0) > 0 for row in baseline_success) >= 3 and sum((row["baseline_workspace_iou"] or 0) < 0.1 for row in baseline_success) >= 8
    collision_improved = (repair_stats["mean_collision_rate_proxy"] is not None and paired_base["mean_collision_rate_proxy"] is not None and repair_stats["mean_collision_rate_proxy"] < paired_base["mean_collision_rate_proxy"])
    workspace_improved = (repair_stats["median_workspace_iou"] is not None and paired_base["median_workspace_iou"] is not None and repair_stats["median_workspace_iou"] > paired_base["median_workspace_iou"])
    # Kinematic parameters are intentionally immutable during this local-body repair.
    # Any motion-metric shift can only come from geometric part matching, not a
    # repaired trajectory, so it is not valid evidence of a motion improvement.
    motion_improved = False
    graph_improved = (repair_stats["median_graph_f1"] is not None and paired_base["median_graph_f1"] is not None and repair_stats["median_graph_f1"] > paired_base["median_graph_f1"])
    geometry_ok = (repair_stats["median_chamfer"] is not None and paired_base["median_chamfer"] is not None and repair_stats["median_chamfer"] <= paired_base["median_chamfer"])
    # There is no extra-call matched non-feedback repair control, so a gain cannot be isolated.
    feedback_isolated = False
    improvements = sum((collision_improved, workspace_improved, motion_improved, graph_improved))
    decision = "GO" if failure_common and improvements >= 2 and geometry_ok and feedback_isolated else "NO-GO"
    summary_rows = [{"flow": "one_shot_all", "cases": 15, "executable": len(baseline_success), "repair_success": None, **base_stats}, {"flow": "one_shot_paired_subset", "cases": len(paired), "executable": len(paired), "repair_success": None, **paired_base}, {"flow": "verification_guided_repair_paired", "cases": len(paired), "executable": len(paired), "repair_success": len(paired) / len(baseline_success) if baseline_success else None, **repair_stats}]
    with (args.output_dir / "aggregate_results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0])); writer.writeheader(); writer.writerows(summary_rows)
    report = ["# Go/No-Go 5 report", "", f"## FINAL DECISION: {decision}", "", "## A. Dataset summary", "", "15 audited real robots reused as a development set. The one-shot source is the fixed Go/No-Go 4 static-multiview output; only 14 executable sources enter repair eligibility.", "", "## B. Baseline generation results", "", f"One-shot executable outputs: {len(baseline_success)}/15.", "", "## C. Verification statistics", "", f"Engineering failures common: {failure_common}. Collision uses a deterministic sampled non-adjacent surface-clearance proxy (not exact FCL penetration); GT workspace IoU is evaluation-only.", "", "## D. Repair results", "", f"Paired repair outputs: {len(paired)}/{len(baseline_success)}. Repair froze links, topology, joint type, axis, origin and limits, permitting only local primitive geometry edits. Therefore a motion-score shift is not counted as trajectory repair evidence.", "", "| flow | collision mean | workspace IoU median | Graph F1 median | motion translation median | Chamfer median |", "|---|---:|---:|---:|---:|---:|"]
    for row in summary_rows:
        report.append("| {flow} | {mean_collision_rate_proxy} | {median_workspace_iou} | {median_graph_f1} | {median_motion_translation} | {median_chamfer} |".format(**row))
    report += ["", "## E. Ablation", "", "No-feedback is the frozen one-shot output; mechanical feedback is the bounded local repair. Geometry-only feedback is not claimed because meaningful geometry-error feedback would require hidden GT or an AI judge. The absence of an extra-call matched non-feedback repair control prevents causal attribution of any apparent change to feedback.", "", "## F. Failure analysis", "", "Case-level results are in `case_results.csv`. The structured repair inputs are retained under ignored raw runs as `failure.json`.", "", "## G. Research decision", "", f"Collision improved: {collision_improved}; workspace improved: {workspace_improved}; motion improved: {motion_improved}; graph improved: {graph_improved}; geometry non-degradation: {geometry_ok}; feedback isolated from extra call: {feedback_isolated}."]
    report.append("Do not advance RobotCAD-Agent. Verification exposes common engineering failures, but bounded local repair does not establish two engineering gains or feedback-specific causal value." if decision == "NO-GO" else "Proceed to a bounded RobotCAD-Agent prototype with a pre-registered extra-call control.")
    (args.output_dir / "go_nogo5_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"decision": decision, "failure_common": failure_common, "improvements": improvements, "geometry_ok": geometry_ok, "feedback_isolated": feedback_isolated}, indent=2))


if __name__ == "__main__": main()
