"""Replay all 32 frozen C1 candidate FCStd geometries through KFDE only."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import time

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try6.scripts.run_r1_reliability import save

sys.path.insert(0,str(ROOT/"experiments/try5A/scripts"))
from freecad_runtime import python_runtime

RESULT=HERE/"results/try6_0_c2"
ARTIFACT=HERE/"artifacts/try6_0_c2/replay"


def run():
    cfg=load(HERE/"protocol/try6_0_c2.json")
    construction=load(RESULT/"kfde/construction_report.json")
    if construction["status"]!="PASS":raise RuntimeError("construction not passed")
    history=load(ROOT/cfg["c1_result_root"]/"solver/candidate_history.json")
    rows=history["history"]
    if len(rows)!=cfg["c1_replay_candidate_count"] or any(x["candidate_id"]!=f"candidate_{i:03d}" for i,x in enumerate(rows)):
        raise RuntimeError("frozen C1 candidate denominator/order drift")
    if (RESULT/"replay/c1_candidate_replay.csv").exists():raise FileExistsError("C1 replay already attempted")
    ARTIFACT.mkdir(parents=True,exist_ok=True)
    save(RESULT/"replay/replay_started.json",{"requested":32,"source_C1_history_sha256":sha(ROOT/cfg["c1_result_root"]/"solver/candidate_history.json"),
        "construction_report_sha256":sha(RESULT/"kfde/construction_report.json"),
        "candidate_regeneration":False,"gt_access":False,"final_mechanics_access":False})
    records=[];start=time.perf_counter()
    for index,item in enumerate(rows):
        cid=item["candidate_id"]
        if item["status"]!="PASS" or not item["cad_artifact_path"]:raise RuntimeError(f"frozen C1 candidate has no CAD: {cid}")
        job={"mode":"check","protocol":"experiments/try6/protocol/try6_0_c2.json",
            "construction_report":"experiments/try6/results/try6_0_c2/kfde/construction_report.json",
            "candidate_id":cid,"candidate_fcstd":item["cad_artifact_path"],
            "output":f"experiments/try6/artifacts/try6_0_c2/replay/{cid}_check.json"}
        job_path=ARTIFACT/f"{cid}_job.json";save(job_path,job)
        tick=time.perf_counter()
        proc=subprocess.run([python_runtime(),str(HERE/"scripts/freecad_c2_kfde.py"),str(job_path)],
            cwd=ROOT,capture_output=True,text=True,timeout=120)
        (ARTIFACT/f"{cid}_stdout.txt").write_text(proc.stdout,encoding="utf-8")
        (ARTIFACT/f"{cid}_stderr.txt").write_text(proc.stderr,encoding="utf-8")
        if proc.returncode:
            record={"candidate_id":cid,"status":"KFDE_EVALUATION_ERROR","visual_loss_c1":item["total_visual_objective"],
                "theta":item["theta"],"feasible":None,"maximum_forbidden_intersection_mm3":None,
                "violating_components":[],"error":(proc.stderr or proc.stdout)[-1800:],
                "runtime_seconds":time.perf_counter()-tick}
        else:
            kfde=load(ROOT/job["output"])
            record={"candidate_id":cid,"status":"EVALUATED","visual_loss_c1":item["total_visual_objective"],
                "theta":item["theta"],"feasible":kfde["feasible"],
                "maximum_forbidden_intersection_mm3":kfde["maximum_forbidden_intersection_mm3"],
                "mutable_added_volume_mm3":kfde["mutable_added_volume_mm3"],
                "violating_components":kfde["violating_components"],
                "violating_component_count":kfde["violating_component_count"],
                "kfde_raw_path":job["output"],"kfde_raw_sha256":sha(ROOT/job["output"]),
                "runtime_seconds":time.perf_counter()-tick}
        records.append(record)
        save(RESULT/"replay/replay_progress.json",{"completed":len(records),"requested":32,
            "errors":sum(x["status"]!="EVALUATED" for x in records)})
    evaluated=[x for x in records if x["status"]=="EVALUATED"]
    if len(evaluated)!=32:
        save(RESULT/"replay/replay_failure.json",{"status":"KFDE_CONSTRUCTION_BLOCKED",
            "completed":len(records),"evaluation_errors":32-len(evaluated),"records":records})
        raise RuntimeError("KFDE replay incomplete; cannot classify activity")
    with (RESULT/"replay/c1_candidate_replay.csv").open("w",newline="",encoding="utf-8") as handle:
        fields=["candidate_id","visual_loss_c1","feasible","maximum_forbidden_intersection_mm3",
            "mutable_added_volume_mm3","violating_component_count","runtime_seconds","kfde_raw_path"]
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows([{k:r.get(k) for k in fields} for r in records])
    save(RESULT/"replay/c1_candidate_replay.json",{"requested":32,"completed":32,"records":records,
        "candidate_regeneration":False,"gt_access":False,"final_mechanics_access":False})
    rejects=sum(not x["feasible"] for x in records)
    chosen=next(x for x in records if x["candidate_id"]=="candidate_031")
    summary={"schema_version":"robotcad_try6_c2_replay_activity_v1","requested":32,"evaluated":32,
        "feasible_count":32-rejects,"infeasible_count":rejects,"rejection_rate":rejects/32,
        "c1_selected_candidate_id":"candidate_031","c1_selected_feasible":chosen["feasible"],
        "c1_selected_maximum_forbidden_intersection_mm3":chosen["maximum_forbidden_intersection_mm3"],
        "construction_tolerance_mm3":cfg["numerical_forbidden_volume_tolerance_mm3"],
        "replay_runtime_seconds":time.perf_counter()-start,"activity_status":"PENDING_INDEPENDENT_VALIDATION",
        "gt_access":False,"final_mechanics_access":False,"no_candidate_selected_for_C2":True}
    save(RESULT/"replay/activity_summary.json",summary)
    print(json.dumps({"status":"REPLAY_COMPLETE","infeasible":rejects,"rejection_rate":rejects/32,
        "c1_selected_feasible":chosen["feasible"],"gt_access":False}))
    return summary


if __name__=="__main__":run()
