from __future__ import annotations

from collections import Counter
from typing import Any

from common import RESULTS, ROBUSTNESS_EXP, dump_json, read_csv, write_csv, write_text


def truthy(value: Any) -> bool:
    return str(value).lower() == "true"


def main() -> None:
    baseline = {}
    baseline_path = ROBUSTNESS_EXP / "results" / "aggregate_results.json"
    if baseline_path.exists():
        import json

        baseline = json.loads(baseline_path.read_text(encoding="utf-8")).get("replay", {})
    ir_rows = read_csv(RESULTS / "ir_repair_metrics.csv")
    modifier_rows = read_csv(RESULTS / "modifier_repair_metrics.csv")
    execution_rows = read_csv(RESULTS / "execution_metrics.csv")
    failure_codes = Counter(row["failure_code"] for row in execution_rows if row["failure_code"])
    repair_status = Counter(row["repair_status"] for row in modifier_rows if row.get("repair_status"))
    replay: dict[str, dict[str, Any]] = {}
    for version in ["R1", "R2"]:
        subset = [r for r in execution_rows if r["version"] == version]
        replay[version] = {
            "links_total": len(subset),
            "success_links": sum(r["status"] == "SUCCESS" for r in subset),
            "ir_incomplete_links": sum(r["status"] == "IR_INCOMPLETE" for r in subset),
            "failure_links": sum(r["status"] not in {"SUCCESS", "IR_INCOMPLETE"} for r in subset),
            "operation_count": sum(int(float(r["operation_count"])) for r in subset),
            "native_success_count": sum(int(float(r["native_success_count"])) for r in subset),
            "fallback_count": sum(int(float(r["fallback_count"])) for r in subset),
            "fcstd_success": sum(truthy(r["fcstd_success"]) for r in subset),
            "step_success": sum(truthy(r["step_success"]) for r in subset),
            "stl_success": sum(truthy(r["stl_success"]) for r in subset),
        }
    aggregate = {
        "baseline_freecad_operation_robustness": baseline,
        "ir_repair": {
            "total": len(ir_rows),
            "success": sum(r["status"] == "SUCCESS" for r in ir_rows),
            "ir_incomplete": sum(r["status"] == "IR_INCOMPLETE" for r in ir_rows),
        },
        "modifier_repair_status_counts": dict(repair_status),
        "execution": replay,
        "silent_fallback_total": sum(v["fallback_count"] for v in replay.values()),
        "failure_code_counts": dict(failure_codes),
        "acceptance": {
            "r1_batch_success_min_3": replay["R1"]["success_links"] >= 3,
            "r2_batch_success_not_below_4": replay["R2"]["success_links"] >= 4,
            "silent_fallback_zero": sum(v["fallback_count"] for v in replay.values()) == 0,
            "all_modifier_failures_have_codes": all(bool(r["failure_code"]) for r in execution_rows if r["status"] not in {"SUCCESS", "IR_INCOMPLETE"}),
        },
    }
    dump_json(RESULTS / "aggregate_results.json", aggregate)
    flat = []
    for version, metrics in replay.items():
        flat.append({"version": version, **metrics})
    write_csv(RESULTS / "aggregate_results.csv", flat)
    lines = [
        "# modifier_parameter_repair_pilot report",
        "",
        "## Controls",
        "",
        "- Inputs: repaired MFG/IR from `mfg_to_ir_repair_pilot`.",
        "- Frozen denominator: R1/R2 × 6 links.",
        "- LLM/VLM calls: none.",
        "- GT mesh/STEP/CAD use: none.",
        "- Backend silent fallback: forbidden; execution logs remain authoritative.",
        "",
        "## Results",
        "",
        f"- IR repair success: {aggregate['ir_repair']['success']}/{aggregate['ir_repair']['total']}",
        f"- Modifier repair status: `{dict(repair_status)}`",
        f"- R1 batch success: {replay['R1']['success_links']}/6",
        f"- R2 batch success: {replay['R2']['success_links']}/6",
        f"- Silent fallback total: {aggregate['silent_fallback_total']}",
        f"- Failure codes: `{dict(failure_codes)}`",
        "",
        "## Interpretation",
        "",
    ]
    if all(aggregate["acceptance"].values()):
        lines.append("The pilot meets the acceptance criteria. The previous R1 fillet failures were caused by non-executable modifier parameters rather than a general FreeCAD backend limitation.")
    else:
        lines.append("The pilot does not fully meet acceptance. Remaining failures should be attributed using explicit failure codes in `execution_metrics.csv`.")
    lines.extend([
        "",
        "Parameter repair is counted explicitly as partial semantic match, not backend fallback. This preserves the distinction between executable CAD repair and silent success inflation.",
        "",
        "## Modifier repair audit",
        "",
        "| version | case | link | op | type | requested mm | resolved mm | safe cap mm | reason |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |",
    ])
    for row in modifier_rows:
        lines.append(
            f"| {row['version']} | {row['case_id']} | {row['link_id']} | {row['op_id']} | {row['op_type']} | "
            f"{row['requested_value_mm']} | {row['resolved_value_mm']} | {row['safe_cap_mm']} | {row['reason']} |"
        )
    write_text(RESULTS / "modifier_parameter_repair_pilot_report.md", "\n".join(lines) + "\n")
    print(aggregate)


if __name__ == "__main__":
    main()
