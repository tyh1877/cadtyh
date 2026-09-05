"""Orchestrate Codex-agent Try-3 FreeCAD execution from the root .venv."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from codex_agent_common import EXP, ROOT, RUNS, RESULTS, load_json, manifest, parse_urdf, tryset_rows, write_csv, write_json


FREECAD_PYTHON = Path(r"D:\software\freeCAD\install\bin\python.exe")
HELPER = Path(__file__).with_name("freecad_codex_case_job.py")


def run_one(row: dict[str, str], version: str, timeout: float) -> dict:
    case_id = row["case_id"]
    urdf_path = ROOT / row["sanitized_urdf"]
    links, joints = parse_urdf(urdf_path)
    assembly_plan_path = RUNS / version / case_id / "assembly_plan.json"
    if not assembly_plan_path.exists():
        return {"case_id": case_id, "version": version, "status": "UPSTREAM_FAILURE", "links_expected": len(links), "links_success": 0, "operation_count": 0, "fallback_count": 0, "component_count": 0, "fcstd": False, "step": False, "stl": False, "elapsed_seconds": 0.0, "error_type": "MISSING_ASSEMBLY_PLAN", "error": str(assembly_plan_path)}
    assembly_plan = load_json(assembly_plan_path)
    transforms = {item["link_id"]: item["world_transform_mm"] for item in assembly_plan["components"]}
    root = RUNS / version / case_id
    job = {
        "repo_root": str(ROOT), "case_id": case_id, "version": version,
        "output_dir": str(root), "result_path": str(root / "freecad_case_result.json"),
        "links": [{"link_id": link, "ir_path": str(root / "links" / link / "executable_cad_ir.json"), "world_transform_mm": transforms[link]} for link in links],
        "joints": [{"joint_id": j.joint_id, "joint_type": j.joint_type, "parent": j.parent, "child": j.child, "origin_xyz_mm": list(j.xyz_mm), "axis": list(j.axis)} for j in joints],
    }
    job_path = root / "freecad_case_job.json"
    write_json(job_path, job)
    try:
        completed = subprocess.run([str(FREECAD_PYTHON), str(HELPER), str(job_path)], cwd=str(ROOT), capture_output=True, text=True, timeout=timeout, check=False)
        (root / "freecad_stdout.txt").write_text(completed.stdout or "", encoding="utf-8")
        (root / "freecad_stderr.txt").write_text(completed.stderr or "", encoding="utf-8")
        result = load_json(root / "freecad_case_result.json") if (root / "freecad_case_result.json").exists() else {"status": "FAILURE", "error_type": "MISSING_RESULT", "error": "helper did not write result", "link_results": [], "assembly": {}, "elapsed_seconds": 0.0}
    except Exception as exc:
        result = {"status": "FAILURE", "error_type": type(exc).__name__, "error": str(exc), "link_results": [], "assembly": {}, "elapsed_seconds": 0.0}
    assembly = result.get("assembly") or {}
    link_results = result.get("link_results") or []
    row_result = {
        "case_id": case_id, "version": version, "status": result["status"],
        "links_expected": len(links), "links_success": sum(item["status"] == "SUCCESS" for item in link_results),
        "operation_count": sum(int(item["operation_count"]) for item in link_results),
        "fallback_count": sum(int(item["fallback_count"]) for item in link_results),
        "component_count": int(assembly.get("component_count", 0)),
        "fcstd": bool(assembly.get("fcstd_exists", False)), "step": bool(assembly.get("step_exists", False)), "stl": bool(assembly.get("stl_exists", False)),
        "elapsed_seconds": float(result.get("elapsed_seconds", 0.0)), "error_type": result.get("error_type", ""), "error": str(result.get("error", ""))[:1000],
    }
    write_json(root / "freecad_stage_manifest.json", manifest("freecad_backend_and_assembly", result["status"], "freecad_case_result_v1", "freecad_codex_case_job.py+robotcad.backends.freecad_api.FreeCADBackend", [job_path, urdf_path, HELPER, ROOT / "robotcad/backends/freecad_api/FreeCADBackend.py"], version=version, case_id=case_id, returncode=getattr(completed, "returncode", -1) if "completed" in locals() else -1))
    return row_result


def summarize(rows: list[dict]) -> None:
    write_csv(RESULTS / "codex_agent_v1_freecad_execution.csv", rows)
    summary = []
    for version in ["V0", "V1", "V2"]:
        selected = [row for row in rows if row["version"] == version]
        if selected:
            summary.append({"version": version, "cases_attempted": len(selected), "cases_success": sum(row["status"] == "SUCCESS" for row in selected), "links_expected": sum(int(row["links_expected"]) for row in selected), "links_success": sum(int(row["links_success"]) for row in selected), "operations": sum(int(row["operation_count"]) for row in selected), "fallbacks": sum(int(row["fallback_count"]) for row in selected), "elapsed_seconds": sum(float(row["elapsed_seconds"]) for row in selected)})
    write_csv(RESULTS / "codex_agent_v1_freecad_execution_summary.csv", summary)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default="dev_arm-ab15a75247,dev_arm-dcc2b0ce1e")
    parser.add_argument("--versions", default="V0,V1,V2")
    parser.add_argument("--timeout", type=float, default=900.0)
    args = parser.parse_args()
    requested = {item.strip() for item in args.cases.split(",") if item.strip()}
    versions = [item.strip() for item in args.versions.split(",") if item.strip()]
    rows = []
    for row in tryset_rows():
        if row["case_id"] not in requested:
            continue
        for version in versions:
            result = run_one(row, version, args.timeout)
            rows.append(result)
            print(json.dumps(result), flush=True)
    existing_path = RESULTS / "codex_agent_v1_freecad_execution.csv"
    if existing_path.exists():
        import csv
        with existing_path.open(encoding="utf-8", newline="") as stream:
            existing = list(csv.DictReader(stream))
        keys = {(row["case_id"], row["version"]) for row in rows}
        rows = [row for row in existing if (row["case_id"], row["version"]) not in keys] + rows
    summarize(rows)
    return 0 if all(row["status"] == "SUCCESS" for row in rows if row["case_id"] in requested and row["version"] in versions) else 1


if __name__ == "__main__":
    raise SystemExit(main())
