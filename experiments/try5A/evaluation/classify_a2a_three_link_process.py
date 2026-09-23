"""Classify frozen A2a execution outcomes without rerunning generation."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--result-dir", required=True); args = parser.parse_args()
    root = Path(args.result_dir).resolve()
    marker = root / "process_classification.json"
    if marker.exists(): raise FileExistsError("process classification already recorded")
    records = json.loads((root / "run_records.json").read_text(encoding="utf-8"))["records"]
    table_path = root / "paired_main_table.json"; table = json.loads(table_path.read_text(encoding="utf-8"))
    by = {(row["link"], row["method"]): row for row in records}
    classes = []
    for row in table["rows"]:
        source = by[(row["link"], row["method"])]
        row["cad_build_success"] = source["status"] == "EVALUATED" and source.get("cad_build_success") is True
        schema_failure = source["method"] == "STRUCTURED_QWEN" and source["status"] == "EXECUTION_EXCEPTION" and "STRUCTURED_SCHEMA_VALUE_INVALID" in source.get("error", "")
        direct_failure = source["method"] == "DIRECT_QWEN" and source["status"] in ("DIRECT_CODE_FAILURE", "INVALID_CAD_ATTEMPT")
        classes.append({"link": row["link"], "method": row["method"], "status": source["status"], "cad_build_success": row["cad_build_success"], "structured_schema_failure": schema_failure, "direct_code_failure": direct_failure, "freecad_execution_failure": source["status"] == "FREECAD_BUILD_FAILURE", "evaluator_failure": source["status"] in ("EXACT_EVALUATOR_FAILURE", "GEOMETRY_EVALUATOR_FAILURE"), "invalid_cad_attempts": int(source["status"] == "INVALID_CAD_ATTEMPT"), "error": source.get("error")})
    table_path.write_text(json.dumps(table, indent=2) + "\n", encoding="utf-8")
    with (root / "paired_main_table.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = list(table["rows"][0]); writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(table["rows"])
    payload = {"schema_version": "robotcad_a2a_three_link_process_classification_v1", "runs": classes, "counts": {"attempted": 6, "evaluated": sum(row["status"] == "EVALUATED" for row in classes), "structured_schema_failures": sum(row["structured_schema_failure"] for row in classes), "direct_code_failures": sum(row["direct_code_failure"] for row in classes), "freecad_execution_failures": sum(row["freecad_execution_failure"] for row in classes), "invalid_cad_attempts": sum(row["invalid_cad_attempts"] for row in classes), "manual_interventions": 0, "result_conditioned_retries": 0}, "raw_model_or_cad_artifacts_changed": False, "additional_model_calls": 0}
    marker.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["counts"], indent=2))


if __name__ == "__main__": main()
