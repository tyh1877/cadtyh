"""One-shot GT geometry + diagnostic development mechanics after candidate lock."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime,timezone

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try6.scripts.run_r1_reliability import save

sys.path.insert(0,str(ROOT/"experiments/try5A/scripts"))
from freecad_runtime import python_runtime

RESULT=HERE/"results/try6_0_c1_v2"
ARTIFACT=HERE/"artifacts/try6_0_c1_v2/evaluation"


def run():
    cfg=load(HERE/"protocol/try6_0_c1_v2.json")
    lock_path=RESULT/"evaluation/final_candidate_lock.json"
    lock=load(lock_path)
    if lock["gt_evaluation_count_at_lock"]!=0 or not lock["selection_used_only_visual_objective"]:
        raise RuntimeError("candidate lock did not precede GT")
    if sha(RESULT/"solver/candidate_history.json")!=lock["solver_history_sha256"]:
        raise RuntimeError("solver history changed after lock")
    for item in lock["final_cad_artifacts"].values():
        if sha(ROOT/item["path"])!=item["sha256"]:raise RuntimeError("final CAD artifact changed after lock")
    eval_dir=RESULT/"evaluation"
    marker=eval_dir/"evaluation_started.json"
    if marker.exists():raise FileExistsError("formal final evaluation already attempted; no rerun")
    holdout=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if holdout["accessed"] is not False or holdout["evaluation_count"]!=0:
        raise RuntimeError("formal holdout lock violated")
    development=load(ROOT/cfg["evaluation"]["development_input"])
    if development["contains_formal_holdout_configurations"] is not False or development["configuration_count"]!=96:
        raise RuntimeError("development mechanics input invalid")
    save(marker,{"timestamp_utc":datetime.now(timezone.utc).isoformat(),
        "final_candidate_lock_sha256":sha(lock_path),"gt_first_access_after_lock":True,
        "gt_evaluation_attempt_limit":1,"formal_holdout_access":False})
    ARTIFACT.mkdir(parents=True,exist_ok=True)
    cad=lock["final_cad_artifacts"]
    geometry_job={"gt_urdf":"go_nogo1/sources/urdf_files_dataset/urdf_files/robotics-toolbox/xacro_generated/interbotix_descriptions/urdf/px100.urdf",
        "seed":cfg["model"]["seed"],"candidates":[{"condition":"C1_V2","link_id":"L04",
            "body_stl":cad["body_only.stl"]["path"],"final_stl":cad["final.stl"]["path"]}],
        "output":str(eval_dir/"geometry_raw.json")}
    save(ARTIFACT/"geometry_job.json",geometry_job)
    geometry_tick=time.perf_counter()
    geometry=subprocess.run([sys.executable,str(ROOT/cfg["evaluation"]["geometry_evaluator"]),str(ARTIFACT/"geometry_job.json")],
        cwd=ROOT,capture_output=True,text=True,timeout=400)
    (eval_dir/"geometry_stdout.txt").write_text(geometry.stdout,encoding="utf-8")
    (eval_dir/"geometry_stderr.txt").write_text(geometry.stderr,encoding="utf-8")
    if geometry.returncode:
        save(eval_dir/"evaluation_failure.json",{"stage":"GEOMETRY","returncode":geometry.returncode,
            "error":(geometry.stderr or geometry.stdout)[-2000:],"no_retry":True})
        raise RuntimeError("one-shot GT geometry evaluator failed")
    geometry_seconds=time.perf_counter()-geometry_tick
    candidate_manifest={"schema_version":"robotcad_try6_c1_v2_exact_candidate_v1",
        "frozen_nonpilot_root":"experiments/try5A/artifacts/try5a5/round3_verified/links",
        "interface_contracts":"experiments/try5A/results/try5a5/motion_interface_contracts.json",
        "conditions":{"C1_V2":{"selected_candidate":lock["selected_candidate_id"],
            "pilot_fcstd":{"L04":cad["final.FCStd"]["path"]},
            "mechanical_policy":{"protected_interface_cuts":True,"distal_clearance_cut":True,
                "preserve_frozen_scaffold":True,"auto_attachment_closure":False}}}}
    save(eval_dir/"candidate_manifest.json",candidate_manifest)
    exact_job={"mode":"C1_V2_DEVELOPMENT_DIAGNOSTIC_EXACT_AFTER_THETA_LOCK",
        "candidate_manifest":str(eval_dir/"candidate_manifest.json"),
        "configurations":development["coupled_configurations"],
        "per_joint":{"J03":development["per_joint"]["J03"]},
        "output":str(eval_dir/"mechanical_raw.json")}
    save(ARTIFACT/"mechanical_job.json",exact_job)
    exact_tick=time.perf_counter()
    exact=subprocess.run([python_runtime(),str(ROOT/cfg["evaluation"]["mechanical_evaluator"]),str(ARTIFACT/"mechanical_job.json")],
        cwd=ROOT,capture_output=True,text=True,timeout=1800)
    (eval_dir/"mechanical_stdout.txt").write_text(exact.stdout,encoding="utf-8")
    (eval_dir/"mechanical_stderr.txt").write_text(exact.stderr,encoding="utf-8")
    if exact.returncode:
        save(eval_dir/"evaluation_failure.json",{"stage":"MECHANICS","returncode":exact.returncode,
            "error":(exact.stderr or exact.stdout)[-2000:],"no_retry":True})
        raise RuntimeError("one-shot development exact mechanics evaluator failed")
    exact_seconds=time.perf_counter()-exact_tick
    geometry_raw=load(eval_dir/"geometry_raw.json")
    rows={r["scope"]:r for r in geometry_raw["rows"] if r["condition"]=="C1_V2" and r["link_id"]=="L04"}
    if set(rows)!={"refined_body_only","final_assembled_link"}:
        raise RuntimeError("geometry evaluator did not return both scopes")
    mechanics=load(eval_dir/"mechanical_raw.json")["conditions"]
    if len(mechanics)!=1 or mechanics[0]["condition"]!="C1_V2":
        raise RuntimeError("exact evaluator result mismatch")
    m=mechanics[0]
    final=rows["final_assembled_link"]
    save(eval_dir/"geometry_metrics.json",{"status":"EVALUATED_ONCE_AFTER_LOCK",
        "final":final,"body_only_diagnostic":rows["refined_body_only"],
        "raw_geometry_sha256":sha(eval_dir/"geometry_raw.json"),
        "final_candidate_lock_sha256":sha(lock_path),"gt_evaluation_count":1})
    save(eval_dir/"mechanical_metrics.json",{"status":"DIAGNOSTIC_AFTER_LOCK",
        "bicr":float(lock["connected_solid_count"]==1 and lock["interface_invariant"]),
        "connected_solid_count":lock["connected_solid_count"],
        "j03_jr3":next(item["jr3"] for item in m["per_joint"] if item["joint_id"]=="J03"),
        "gcfr":m["gcfr"],"collision_events":m["collision_events"],
        "intersection_volume_mm3":m["intersection_volume_mm3"],
        "failed_configuration_ids":m["failed_configuration_ids"],
        "configuration_count":m["configuration_count"],
        "mechanical_feedback_to_solver":False,
        "raw_mechanical_sha256":sha(eval_dir/"mechanical_raw.json")})
    save(eval_dir/"evaluation_runtime.json",{"geometry_seconds":geometry_seconds,"exact_mechanics_seconds":exact_seconds,
        "gt_evaluation_count":1,"formal_holdout_evaluation_count":0,"candidate_lock_sha256":sha(lock_path)})
    print(json.dumps({"status":"EVALUATED_ONCE_AFTER_LOCK","final_iou":final["voxel_iou"],
        "bicr":float(lock["connected_solid_count"]==1 and lock["interface_invariant"]),
        "gcfr":m["gcfr"],"holdout_accessed":False}))
    return final


if __name__=="__main__":run()
