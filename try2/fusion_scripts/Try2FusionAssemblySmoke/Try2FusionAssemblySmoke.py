"""Non-destructive world-transform smoke for one Try-2 Fusion D case.

It executes the frozen D blueprint into ``try2/smoke_runs`` rather than
overwriting the formal B/D matrix.  The wrapper is deliberately narrow: it
tests only whether native occurrence placement survives F3D/STEP/STL export.
"""
import importlib.util
import json
import os

ROOT = r"D:\CADtest\papertest"
source = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "Try2FusionBatch", "Try2FusionBatch.py"))
spec = importlib.util.spec_from_file_location("try2_assembly_smoke", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
source_jobs = os.path.join(ROOT, "try2", "fusion_jobs.json")
smoke_jobs = os.path.join(ROOT, "try2", "fusion_assembly_smoke_job.json")
with open(source_jobs, encoding="utf-8") as handle:
    selected = [job for job in json.load(handle)["jobs"]
                if job["case_id"] == "dev_arm-3ce41d3c31" and job["target_condition"] == "D"]
if len(selected) != 1:
    raise RuntimeError("expected exactly one frozen D smoke job")
with open(smoke_jobs, "w", encoding="utf-8") as handle:
    json.dump({"jobs": selected}, handle, indent=2)
module.JOBS = smoke_jobs
module.RUNS = os.path.join(ROOT, "try2", "smoke_runs")
module.BATCH_RESULTS = os.path.join(ROOT, "try2", "smoke_runs", "fusion_batch_results.json")

def run(context):
    module.run(context)
