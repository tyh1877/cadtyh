"""Fusion executor for operation_plan_pilot/fusion_jobs.json."""
from __future__ import annotations

import importlib
import json
import os
import sys
import time
import traceback

ROOT = r"D:\CADtest\papertest"
JOBS = os.path.join(ROOT, "operation_plan_pilot", "fusion_jobs.json")
OUT = os.path.join(ROOT, "operation_plan_pilot", "fusion_batch_results.json")


def run(context):
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import FusionAPIBackend as backend_module

    importlib.reload(backend_module)
    FusionAPIBackend, make_design = backend_module.FusionAPIBackend, backend_module.make_design
    results = []
    app = None
    for job in json.load(open(JOBS, encoding="utf-8"))["jobs"]:
        record = {
            "case_id": job["case_id"],
            "link_id": job["link_id"],
            "target_component": job["target_component"],
            "status": "FAILURE",
            "calls": [],
            "errors": [],
        }
        results.append(record)
        start = time.time()
        if job["status"] != "READY":
            record["errors"].append(job.get("error", job["status"]))
            continue
        try:
            app, design, root = make_design()
            backend = FusionAPIBackend(design, root, record)
            components = {}
            for call in job["calls"]:
                backend.execute(call, components)
            base = os.path.join(ROOT, "operation_plan_pilot", "runs", job["case_id"], job["link_id"], "fusion_model")
            os.makedirs(os.path.dirname(base), exist_ok=True)
            backend.export(base, components)
            record.update(
                {
                    "status": "SUCCESS",
                    "rebuild_success": True,
                    "component_count": len(components),
                    "f3d": base + ".f3d",
                    "step": base + ".step",
                    "stl": base + ".stl",
                }
            )
        except Exception:
            record["errors"].append(traceback.format_exc())
        record["elapsed_seconds"] = time.time() - start
    json.dump(results, open(OUT, "w", encoding="utf-8"), indent=2)
    try:
        if app:
            app.userInterface.messageBox("Operation-plan Pilot Fusion batch complete")
    except Exception:
        pass
