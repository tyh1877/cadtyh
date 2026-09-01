from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from common import EXP, RESULTS, RUNS, SOURCE_EXP, VERSIONS, dump_json, frozen_rows, load_json, read_csv, write_csv, write_text


def count_status(rows: list[dict[str, Any]], version: str, status: str) -> int:
    return sum(r["version"] == version and r["status"] == status for r in rows)


def v2_counts() -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    files = {
        "mfg_success": SOURCE_EXP / "results" / "feature_graph_generation.csv",
        "ir_success": SOURCE_EXP / "results" / "ir_translation.csv",
        "exec_success": SOURCE_EXP / "results" / "execution_metrics.csv",
    }
    for version in VERSIONS:
        out[version] = {}
        for name, path in files.items():
            rows = read_csv(path)
            out[version][name] = sum(r["version"] == version and r["status"] == "SUCCESS" for r in rows)
    return out


def repaired_counts() -> dict[str, dict[str, int]]:
    repair = read_csv(RESULTS / "repair_generation.csv")
    ir = read_csv(RESULTS / "ir_translation.csv")
    exe = read_csv(RESULTS / "execution_metrics.csv")
    out: dict[str, dict[str, int]] = {}
    for version in VERSIONS:
        out[version] = {
            "mfg_success": count_status(repair, version, "SUCCESS"),
            "ir_success": count_status(ir, version, "SUCCESS"),
            "exec_success": count_status(exe, version, "SUCCESS"),
            "mfg_total": sum(r["version"] == version for r in repair),
            "ir_total": sum(r["version"] == version for r in ir),
            "exec_total": sum(r["version"] == version for r in exe),
        }
    return out


def failed_ops() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for version in VERSIONS:
        for row in frozen_rows():
            log_path = RUNS / version / row["case_id"] / row["link_id"] / "freecad" / "execution_log.json"
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
                            "failure_reason": item.get("failure_reason"),
                        }
                    )
    return rows


def op_usage() -> dict[str, dict[str, int]]:
    usage: dict[str, Counter[str]] = {v: Counter() for v in VERSIONS}
    for version in VERSIONS:
        for row in frozen_rows():
            ir_path = RUNS / version / row["case_id"] / row["link_id"] / "executable_cad_ir_v1_2.json"
            if not ir_path.exists():
                continue
            for op in load_json(ir_path).get("operations", []):
                usage[version][op.get("op_type", "")] += 1
    return {k: dict(v) for k, v in usage.items()}


def classify_bottlenecks() -> dict[str, int]:
    repair = read_csv(RESULTS / "repair_generation.csv")
    ir = read_csv(RESULTS / "ir_translation.csv")
    exe = read_csv(RESULTS / "execution_metrics.csv")
    counts = Counter()
    for row in repair:
        if row["status"] != "SUCCESS":
            counts["MFG parsing/schema expression"] += 1
    for row in ir:
        if row["status"] != "SUCCESS":
            counts["MFG-to-IR translation / CAD parameter estimation"] += 1
    for row in exe:
        if row["status"] not in {"SUCCESS", "IR_INCOMPLETE"}:
            counts["selector/backend execution"] += 1
    return dict(counts)


def write_report(aggregate: dict[str, Any], failures: list[dict[str, Any]]) -> None:
    lines = [
        "# MFG-to-IR Repair Pilot Report",
        "",
        "## Scope",
        "",
        "This pilot reuses the 6 frozen links from `freecad_robot_link_reconstruction_pilot_v2`. It does not call an LLM/VLM. It only repairs deterministic MFG schema/canonicalization issues and reruns strict MFG→IR→FreeCAD execution.",
        "",
        "## Aggregate result",
        "",
        "| Version | v2 MFG | repaired MFG | v2 IR | repaired IR | v2 exec | repaired exec |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for version in VERSIONS:
        before = aggregate["v2"][version]
        after = aggregate["repaired"][version]
        lines.append(
            f"| {version} | {before['mfg_success']}/6 | {after['mfg_success']}/6 | {before['ir_success']}/6 | {after['ir_success']}/6 | {before['exec_success']}/6 | {after['exec_success']}/6 |"
        )
    lines.extend(
        [
            "",
            f"Silent fallback total: `{aggregate['silent_fallback_total']}`.",
            "",
            "## Operation usage after repair",
            "",
            "```json",
            json.dumps(aggregate["operation_usage"], indent=2, ensure_ascii=False),
            "```",
            "",
            "## Failure accounting",
            "",
        ]
    )
    if failures:
        lines.extend(["| Version | Case | Link | Operation | Feature | Reason |", "|---|---|---|---|---|---|"])
        for item in failures:
            reason = str(item.get("failure_reason", "")).splitlines()[-1][:160]
            lines.append(f"| {item['version']} | {item['case_id']} | {item['link_id']} | {item['op_type']} | {item['semantic_feature_type']} | {reason} |")
    else:
        lines.append("No native operation failures were recorded for executed IR-complete links.")
    lines.extend(
        [
            "",
            "## Bottleneck classification",
            "",
            "```json",
            json.dumps(aggregate["bottlenecks"], indent=2, ensure_ascii=False),
            "```",
            "",
            "## Interpretation",
            "",
        ]
    )
    r2 = aggregate["repaired"]["R2"]
    if r2["ir_success"] < 4:
        lines.append("The repair did not meet the target for R2 IR completeness. The remaining blocker is upstream CAD parameter completeness in the MFG, not the FreeCAD API itself.")
    elif r2["exec_success"] < 3:
        lines.append("The repair improved IR completeness but did not meet the target execution success. The remaining blocker is primarily selector/backend execution or unstable operation parameters.")
    else:
        lines.append("The repair pilot meets the minimum technical target for moving from MFG to executable FreeCAD IR on this frozen set, while still not claiming visually faithful full robot-arm reconstruction.")
    write_text(RESULTS / "mfg_to_ir_repair_pilot_report.md", "\n".join(lines) + "\n")


def main() -> None:
    exe = read_csv(RESULTS / "execution_metrics.csv")
    failures = failed_ops()
    write_csv(RESULTS / "failed_operations.csv", failures, fields=["version", "case_id", "link_id", "op_id", "op_type", "semantic_feature_type", "failure_reason"])
    aggregate = {
        "v2": v2_counts(),
        "repaired": repaired_counts(),
        "silent_fallback_total": sum(int(row["fallback_count"]) for row in exe),
        "operation_usage": op_usage(),
        "bottlenecks": classify_bottlenecks(),
        "acceptance": {},
    }
    aggregate["acceptance"] = {
        "r2_mfg_valid_min_5": aggregate["repaired"]["R2"]["mfg_success"] >= 5,
        "r2_ir_complete_min_4": aggregate["repaired"]["R2"]["ir_success"] >= 4,
        "r2_batch_success_min_3": aggregate["repaired"]["R2"]["exec_success"] >= 3,
        "silent_fallback_zero": aggregate["silent_fallback_total"] == 0,
    }
    dump_json(RESULTS / "aggregate_results.json", aggregate)
    rows = []
    for version in VERSIONS:
        before = aggregate["v2"][version]
        after = aggregate["repaired"][version]
        rows.append(
            {
                "version": version,
                "v2_mfg_success": before["mfg_success"],
                "repaired_mfg_success": after["mfg_success"],
                "v2_ir_success": before["ir_success"],
                "repaired_ir_success": after["ir_success"],
                "v2_exec_success": before["exec_success"],
                "repaired_exec_success": after["exec_success"],
            }
        )
    write_csv(RESULTS / "aggregate_results.csv", rows)
    write_report(aggregate, failures)
    print(json.dumps(aggregate, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
