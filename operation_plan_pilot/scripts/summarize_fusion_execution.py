"""Summarize Operation-plan Pilot Fusion execution results."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "operation_plan_pilot"
RESULTS = PILOT / "results"


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    batch_path = PILOT / "fusion_batch_results.json"
    jobs_path = PILOT / "fusion_jobs.json"
    if not batch_path.exists():
        raise FileNotFoundError(batch_path)
    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    jobs = {f"{j['case_id']}::{j['link_id']}": j for j in json.loads(jobs_path.read_text(encoding="utf-8"))["jobs"]}
    rows = []
    feature_counts = {}
    for item in batch:
        key = f"{item['case_id']}::{item['link_id']}"
        job = jobs.get(key, {})
        source_ops = {}
        for call in job.get("calls", []):
            src = call.get("parameters", {}).get("source_op")
            if src:
                source_ops[src] = source_ops.get(src, 0) + 1
        for call in item.get("calls", []):
            ft = call.get("feature_type") or "None"
            feature_counts[ft] = feature_counts.get(ft, 0) + 1
        rows.append(
            {
                "case_id": item["case_id"],
                "link_id": item["link_id"],
                "status": item["status"],
                "executed_calls": len(item.get("calls", [])),
                "component_count": item.get("component_count", 0),
                "has_f3d": bool(item.get("f3d") and Path(item["f3d"]).exists()),
                "has_step": bool(item.get("step") and Path(item["step"]).exists()),
                "has_stl": bool(item.get("stl") and Path(item["stl"]).exists()),
                "source_op_types": ",".join(sorted(source_ops)),
                "error": " | ".join(item.get("errors", [])[:1]),
            }
        )
    fields = list(rows[0])
    with (RESULTS / "fusion_execution_quality.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    aggregate = {
        "links_total": len(rows),
        "fusion_success": sum(r["status"] == "SUCCESS" for r in rows),
        "links_with_5plus_calls": sum(r["status"] == "SUCCESS" and int(r["executed_calls"]) >= 5 for r in rows),
        "links_with_exports": sum(r["status"] == "SUCCESS" and r["has_f3d"] and r["has_step"] and r["has_stl"] for r in rows),
        "feature_counts": dict(sorted(feature_counts.items())),
    }
    aggregate["pass"] = (
        aggregate["fusion_success"] >= 5
        and aggregate["links_with_5plus_calls"] >= 5
        and aggregate["links_with_exports"] >= 5
        and any(k.endswith("LoftFeature") for k in feature_counts)
        and any(k.endswith("FilletFeature") for k in feature_counts)
    )
    (RESULTS / "fusion_execution_aggregate.json").write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    report = [
        "# Operation-plan Fusion Execution Pilot Report",
        "",
        f"Decision: {'PASS' if aggregate['pass'] else 'FAIL'}",
        "",
        "## Aggregate",
        "",
    ]
    for key, value in aggregate.items():
        report.append(f"- {key}: {value}")
    report += [
        "",
        "## Per-link execution",
        "",
        "| case | link | status | calls | exports | source op types |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in rows:
        exports = row["has_f3d"] and row["has_step"] and row["has_stl"]
        report.append(f"| `{row['case_id']}` | `{row['link_id']}` | {row['status']} | {row['executed_calls']} | {exports} | {row['source_op_types']} |")
    report += [
        "",
        "## Limitation",
        "",
        "Compiler v1 lowers not-yet-native source operations such as Revolve, Shell, Sweep, and BooleanUnion into the currently executable Fusion operation subset. The outputs are viewable/editable execution artifacts, not final one-to-one native operation reproductions.",
    ]
    (RESULTS / "fusion_execution_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(aggregate, indent=2))


if __name__ == "__main__":
    main()
