from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from common import RESULTS, RUNS, VERSIONS, dump_json, frozen_rows, load_json, read_csv, write_csv, write_text


def failed_operations() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for version in VERSIONS:
        for row in frozen_rows():
            log_path = RUNS / "replay" / version / row["case_id"] / row["link_id"] / "freecad" / "execution_log.json"
            if not log_path.exists():
                continue
            for item in load_json(log_path):
                if not item.get("success"):
                    rows.append(
                        {
                            "version": version,
                            "case_id": row["case_id"],
                            "link_id": row["link_id"],
                            "op_id": item.get("op_id"),
                            "op_type": item.get("requested_operation"),
                            "semantic_feature_type": item.get("input_parameters", {}).get("semantic_feature_type", ""),
                            "failure_code": item.get("failure_code"),
                            "has_preflight": item.get("preflight") is not None,
                            "has_failure_context": item.get("failure_context") is not None,
                            "failure_reason": item.get("failure_reason"),
                        }
                    )
    return rows


def baseline_counts() -> dict[str, dict[str, int]]:
    rows = read_csv(Path("experiments/mfg_to_ir_repair_pilot/results/execution_metrics.csv"))
    out: dict[str, dict[str, int]] = {}
    for version in VERSIONS:
        subset = [r for r in rows if r["version"] == version]
        out[version] = {
            "success_links": sum(r["status"] == "SUCCESS" for r in subset),
            "links_total": len(subset),
        }
    return out


def aggregate() -> dict[str, Any]:
    smoke = read_csv(RESULTS / "operation_smoke.csv")
    replay = read_csv(RESULTS / "replay_metrics.csv")
    failures = failed_operations()
    explicit_failure_codes = all(bool(row["failure_code"]) for row in failures)
    out: dict[str, Any] = {
        "baseline_mfg_to_ir_repair": baseline_counts(),
        "operation_smoke": {
            "total": len(smoke),
            "passed": sum(str(r["passed"]).lower() == "true" for r in smoke),
            "fallback_count": sum(int(r["fallback_count"]) for r in smoke),
        },
        "replay": {},
        "silent_fallback_total": sum(int(r["fallback_count"]) for r in replay),
        "failure_code_counts": dict(Counter(str(r["failure_code"]) for r in failures)),
        "explicit_failure_codes": explicit_failure_codes,
    }
    for version in VERSIONS:
        subset = [r for r in replay if r["version"] == version]
        out["replay"][version] = {
            "links_total": len(subset),
            "success_links": sum(r["status"] == "SUCCESS" for r in subset),
            "ir_incomplete_links": sum(r["status"] == "IR_INCOMPLETE" for r in subset),
            "failure_links": sum(r["status"] == "FAILURE" for r in subset),
            "native_success_count": sum(int(r["native_success_count"]) for r in subset),
            "operation_count": sum(int(r["operation_count"]) for r in subset),
            "fcstd_success": sum(str(r["fcstd_success"]).lower() == "true" for r in subset),
            "step_success": sum(str(r["step_success"]).lower() == "true" for r in subset),
            "stl_success": sum(str(r["stl_success"]).lower() == "true" for r in subset),
        }
    out["acceptance"] = {
        "r1_batch_success_min_3": out["replay"]["R1"]["success_links"] >= 3,
        "r2_batch_success_min_3": out["replay"]["R2"]["success_links"] >= 3,
        "silent_fallback_zero": out["silent_fallback_total"] == 0,
        "explicit_failure_codes": explicit_failure_codes,
        "operation_smoke_all_passed": out["operation_smoke"]["passed"] == out["operation_smoke"]["total"],
    }
    return out


def write_report(agg: dict[str, Any], failures: list[dict[str, Any]]) -> None:
    lines = [
        "# FreeCAD Operation Robustness Pilot Report",
        "",
        "## Scope",
        "",
        "This pilot replays the repaired IR from `mfg_to_ir_repair_pilot`. It does not call an LLM/VLM and does not change MFG semantics.",
        "",
        "## Result summary",
        "",
        "| Version | Previous success | Robust replay success | IR incomplete | Native failures | Exports |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for version in VERSIONS:
        prev = agg["baseline_mfg_to_ir_repair"][version]
        now = agg["replay"][version]
        lines.append(
            f"| {version} | {prev['success_links']}/{prev['links_total']} | {now['success_links']}/{now['links_total']} | {now['ir_incomplete_links']} | {now['failure_links']} | {now['step_success']}/{now['links_total']} STEP |"
        )
    lines.extend(
        [
            "",
            f"Operation smoke: `{agg['operation_smoke']['passed']}/{agg['operation_smoke']['total']}` passed.",
            f"Silent fallback total: `{agg['silent_fallback_total']}`.",
            "",
            "## Failure codes",
            "",
            "```json",
            json.dumps(agg["failure_code_counts"], indent=2, ensure_ascii=False),
            "```",
            "",
            "## Failed operations",
            "",
        ]
    )
    if failures:
        lines.extend(["| Version | Case | Link | Operation | Code | Preflight | Context |", "|---|---|---|---|---|---:|---:|"])
        for row in failures:
            lines.append(f"| {row['version']} | {row['case_id']} | {row['link_id']} | {row['op_type']} | {row['failure_code']} | {row['has_preflight']} | {row['has_failure_context']} |")
    else:
        lines.append("No failed native operations.")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
        ]
    )
    if agg["acceptance"]["r1_batch_success_min_3"] and agg["acceptance"]["r2_batch_success_min_3"]:
        lines.append("The backend robustness target passed for both R1 and R2. Remaining failures, if any, are now explicitly coded rather than opaque native shape errors.")
    else:
        lines.append("The backend robustness target did not fully pass. The report now separates explicit backend failure codes from upstream IR incompleteness, which is sufficient to decide the next repair target.")
    write_text(RESULTS / "freecad_operation_robustness_pilot_report.md", "\n".join(lines) + "\n")


def main() -> None:
    failures = failed_operations()
    fields = ["version", "case_id", "link_id", "op_id", "op_type", "semantic_feature_type", "failure_code", "has_preflight", "has_failure_context", "failure_reason"]
    write_csv(RESULTS / "failed_operations.csv", failures, fields=fields)
    agg = aggregate()
    dump_json(RESULTS / "aggregate_results.json", agg)
    rows = []
    for version in VERSIONS:
        rows.append(
            {
                "version": version,
                "previous_success": agg["baseline_mfg_to_ir_repair"][version]["success_links"],
                "robust_success": agg["replay"][version]["success_links"],
                "ir_incomplete": agg["replay"][version]["ir_incomplete_links"],
                "native_failures": agg["replay"][version]["failure_links"],
            }
        )
    write_csv(RESULTS / "aggregate_results.csv", rows)
    write_report(agg, failures)
    print(json.dumps(agg, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
