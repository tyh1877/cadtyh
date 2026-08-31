"""Evaluate Operation-plan Pilot outputs."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "operation_plan_pilot"
RESULTS = PILOT / "results"

NON_PRIMITIVE = {
    "Loft",
    "Revolve",
    "Sweep",
    "Shell",
    "OffsetFace",
    "BooleanCut",
    "CircularPattern",
    "LinearPattern",
    "Mirror",
}
EXECUTABLE_NOW = {
    "CreateSketchProfile",
    "Extrude",
    "Loft",
    "ApplyFillet",
    "ApplyChamfer",
    "CreateHole",
    "BooleanCut",
    "CircularPattern",
}


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    rows = []
    for case in csv.DictReader((PILOT / "cases.csv").open(encoding="utf-8-sig")):
        run = PILOT / "runs" / case["case_id"] / case["link_id"]
        manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8")) if (run / "manifest.json").exists() else {}
        row = {
            "case_id": case["case_id"],
            "link_id": case["link_id"],
            "role": case["role"],
            "status": manifest.get("status", "MISSING"),
            "operation_count": 0,
            "unique_operation_count": 0,
            "nonprimitive_operation_count": 0,
            "executable_now_count": 0,
            "interface_constraint_count": 0,
            "has_ack": False,
            "error": manifest.get("error"),
        }
        if row["status"] == "SUCCESS":
            plan = json.loads((run / "operation_plan.json").read_text(encoding="utf-8"))
            ops = [op.get("op") for op in plan.get("operations", [])]
            row.update(
                {
                    "operation_count": len(ops),
                    "unique_operation_count": len(set(ops)),
                    "nonprimitive_operation_count": sum(op in NON_PRIMITIVE for op in ops),
                    "executable_now_count": sum(op in EXECUTABLE_NOW for op in ops),
                    "interface_constraint_count": len(plan.get("interface_constraints", [])),
                    "has_ack": "No GT mesh" in plan.get("prohibited_input_ack", ""),
                }
            )
        rows.append(row)

    fields = list(rows[0])
    with (RESULTS / "plan_quality.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    valid = [r for r in rows if r["status"] == "SUCCESS"]
    aggregate = {
        "links_total": len(rows),
        "schema_valid_links": len(valid),
        "links_with_5plus_ops": sum(int(r["operation_count"]) >= 5 for r in valid),
        "links_with_2plus_nonprimitive_ops": sum(int(r["nonprimitive_operation_count"]) >= 2 for r in valid),
        "links_with_interface_constraints": sum(int(r["interface_constraint_count"]) >= 1 for r in valid),
        "links_with_gt_ack": sum(str(r["has_ack"]) == "True" for r in valid),
    }
    aggregate["pass"] = (
        aggregate["schema_valid_links"] >= 5
        and aggregate["links_with_5plus_ops"] >= 4
        and aggregate["links_with_2plus_nonprimitive_ops"] >= 3
        and aggregate["links_with_interface_constraints"] >= 4
        and aggregate["links_with_gt_ack"] >= 5
    )
    (RESULTS / "aggregate.json").write_text(json.dumps(aggregate, indent=2), encoding="utf-8")

    report = [
        "# Operation-plan Pilot Report",
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
        "## Per-link results",
        "",
        "| case | link | status | ops | unique ops | nonprimitive ops | executable now | interface constraints |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        report.append(
            f"| `{r['case_id']}` | `{r['link_id']}` | {r['status']} | {r['operation_count']} | "
            f"{r['unique_operation_count']} | {r['nonprimitive_operation_count']} | "
            f"{r['executable_now_count']} | {r['interface_constraint_count']} |"
        )
    report += [
        "",
        "## Interpretation",
        "",
        "This pilot evaluates upstream CAD operation planning only. Passing means the next Try-3 revision should regenerate operation plans and then extend Fusion execution coverage for the operation subset the model actually uses. It does not by itself prove geometry quality against GT mesh.",
    ]
    (RESULTS / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(aggregate, indent=2))


if __name__ == "__main__":
    main()
