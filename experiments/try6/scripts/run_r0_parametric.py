"""R0-B independent three-edit feature-history robustness smoke (no GT)."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from experiments.try6.scripts.kfdg_contract import build_kfdg

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments" / "try6"
sys.path.insert(0, str(ROOT / "experiments" / "try5A" / "scripts"))
from freecad_runtime import python_runtime  # noqa: E402


def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def save(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    transport = load(HERE / "results/try6_0_r0/schema_transport/transport_report.json")
    if not transport["all_pass"]: raise RuntimeError("R0-A gate not passed")
    protocol = load(HERE / "protocol/r0_parametric_protocol.json")
    param_spec = load(HERE / protocol["baseline_parameter_source"])
    values = {item["id"]: item["value"] for item in param_spec["optimizable"]}
    artifacts = HERE / "artifacts/try6_0_r0/parametric_rebuild"
    results = HERE / "results/try6_0_r0/parametric_rebuild"
    artifacts.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)
    graph = build_kfdg(load(HERE / "tests/fixtures/valid_vlm.json"), param_spec)
    graph_path = artifacts / "synthetic_legacy_builder_graph.json"
    save(graph_path, graph)
    job = {"mode": "R0_PARAMETRIC_BASELINE", "parameters": values,
           "anchor_distance_mm": param_spec["fixed_functional"]["anchor_distance_mm"],
           "kfdg_path": str(graph_path),
           "frozen_interface_contracts": str(ROOT / protocol["frozen_interface_contracts"]),
           "f0_fcstd": str(ROOT / protocol["f0_fcstd"]), "output_root": str(artifacts / "baseline")}
    job_path = artifacts / "baseline_job.json"
    save(job_path, job)
    started = time.perf_counter()
    baseline = subprocess.run([python_runtime(), str(HERE / "scripts/freecad_c1_builder.py"), str(job_path)], cwd=ROOT, capture_output=True, text=True, timeout=180)
    (results / "baseline_stdout.txt").write_text(baseline.stdout, encoding="utf-8")
    (results / "baseline_stderr.txt").write_text(baseline.stderr, encoding="utf-8")
    report = {"schema_version": "robotcad_try6_r0_parametric_report_v1", "baseline_exit_code": baseline.returncode,
              "baseline_runtime_seconds": time.perf_counter() - started,
              "baseline_graph_note": "Synthetic existing-builder graph; R0-B isolates FreeCAD feature history. KFDG v1 dataflow is separately gated in end-to-end smoke.",
              "frozen_edit_protocol_sha256": hashlib.sha256((HERE / "protocol/r0_parametric_protocol.json").read_bytes()).hexdigest(),
              "edits": [], "gt_evaluations": 0, "formal_holdout_evaluations": 0}
    if baseline.returncode != 0:
        report["pass"] = False
        report["error"] = "baseline CAD build failed"
        save(results / "rebuild_report.json", report)
        print(json.dumps({"pass": False, "error": report["error"]}))
        return False
    source = artifacts / "baseline/final.FCStd"
    baseline_path = artifacts / "baseline.FCStd"
    shutil.copy2(source, baseline_path)
    baseline_result = load(artifacts / "baseline/build_result.json")
    report["baseline"] = {"path": str(baseline_path.relative_to(ROOT)).replace("\\", "/"),
                          "sha256": hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
                          "builder_result": baseline_result}
    save(results / "baseline_signature.json", report["baseline"])
    for edit in protocol["edits"]:
        output = artifacts / f"edit_{edit['id']}"
        old = values[edit["parameter"]]
        edit_job = {"edit_id": edit["id"], "parameter": edit["parameter"], "old_value_mm": old,
                    "new_value_mm": old * edit["multiplier"], "baseline_fcstd": str(baseline_path), "output": str(output)}
        edit_job_path = artifacts / f"edit_{edit['id']}_job.json"
        save(edit_job_path, edit_job)
        started = time.perf_counter()
        process = subprocess.run([python_runtime(), str(HERE / "scripts/freecad_r0_edit.py"), str(edit_job_path)], cwd=ROOT, capture_output=True, text=True, timeout=180)
        (results / f"edit_{edit['id']}_stdout.txt").write_text(process.stdout, encoding="utf-8")
        (results / f"edit_{edit['id']}_stderr.txt").write_text(process.stderr, encoding="utf-8")
        item = {"id": edit["id"], "parameter": edit["parameter"], "old_value_mm": old,
                "new_value_mm": edit_job["new_value_mm"], "exit_code": process.returncode,
                "runtime_seconds": time.perf_counter() - started}
        if (output / "edit_result.json").is_file():
            item["result"] = load(output / "edit_result.json")
            save(results / f"edit_{edit['id']}_result.json", item["result"])
        else:
            item["error"] = process.stderr[-2000:]
        item["pass"] = process.returncode == 0 and item.get("result", {}).get("pass") is True
        report["edits"].append(item)
        save(results / "rebuild_report.json", report)
    report["pass"] = len(report["edits"]) == 3 and all(item["pass"] for item in report["edits"])
    save(results / "rebuild_report.json", report)
    print(json.dumps({"pass": report["pass"], "edits": [{"id": x["id"], "pass": x["pass"]} for x in report["edits"]]}))
    return report["pass"]


if __name__ == "__main__": sys.exit(0 if main() else 2)
