"""Deterministic bounded C1-v2 visual-only optimizer; no GT/mechanics imports."""

from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
import time

import numpy as np
from scipy.stats import qmc

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try6.scripts.r1_v3_contract import validate_kfdg
from experiments.try6.scripts.c1_v2_visual_objective import VisibleObjective
from experiments.try6.scripts.run_r1_reliability import save

sys.path.insert(0,str(ROOT/"experiments/try5A/scripts"))
from freecad_runtime import python_runtime

RESULT=HERE/"results/try6_0_c1_v2/solver"
ARTIFACT=HERE/"artifacts/try6_0_c1_v2/solver"


def solve():
    cfg=load(HERE/"protocol/try6_0_c1_v2.json")
    slot=load(HERE/"results/try6_0_c1_v2/slot/validation.json")
    if slot["status"]!="PASS":raise RuntimeError("fresh slot representation gate not passed")
    evidence=load(HERE/"results/try6_0_c1_v2/visual_metric_evidence/evidence_audit.json")
    if not evidence["registration_gate_pass"] or not evidence["evidence_gate_pass"]:
        raise RuntimeError("visual evidence/registration gate not passed")
    graph_path=HERE/"results/try6_0_c1_v2/kfdg/canonical_kfdg.json"
    graph=load(graph_path);validate_kfdg(graph)
    active=load(HERE/"results/try6_0_c1_v2/kfdg/active_parameters.json")
    ids=active["active_ids"]
    initial=active["initial_theta"]
    bounds=np.asarray([active["active_bounds"][pid] for pid in ids],dtype=float)
    if len(ids)<2 or len(ids)>8 or not np.all(bounds[:,0]<bounds[:,1]):
        raise RuntimeError("active parameter set/bounds invalid")
    if RESULT.exists():raise FileExistsError("formal C1-v2 solver already attempted; no rerun")
    RESULT.mkdir(parents=True);ARTIFACT.mkdir(parents=True,exist_ok=True)
    save(RESULT/"attempt_started.json",{"status":"STARTED_ONE_FORMAL_CANDIDATE",
        "protocol_sha256":sha(HERE/"protocol/try6_0_c1_v2.json"),
        "kfdg_sha256":sha(graph_path),"active_parameter_sha256":sha(HERE/"results/try6_0_c1_v2/kfdg/active_parameters.json"),
        "visual_evidence_sha256":sha(HERE/"results/try6_0_c1_v2/visual_metric_evidence/visual_metric_evidence.json"),
        "gt_access":False,"mechanical_feedback":False,"manual_intervention":0})
    save(RESULT/"config.json",cfg["solver"])
    save(RESULT/"objective_definition.json",{"components":cfg["visual_objective"]["components"],
        "weights":cfg["visual_objective"]["weights"],"normalization":cfg["visual_objective"]["normalization"],
        "selected_views":cfg["view_registration"]["views"],
        "view_registration_sha256":sha(HERE/"results/try6_0_c1_v2/visual_metric_evidence/view_registration_report.json"),
        "visual_evidence_sha256":sha(HERE/"results/try6_0_c1_v2/visual_metric_evidence/visual_metric_evidence.json"),
        "gt_terms":0,"mechanical_terms":0,"candidate_specific_reregistration":False})
    objective=VisibleObjective()
    anchor=objective.anchor
    if abs(anchor-63.0)>1e-9 or abs(graph["metric_anchor"]["distance_mm"]-anchor)>1e-9:
        raise RuntimeError("URDF/KFDG anchor drift")
    start=time.perf_counter();history=[]
    def evaluate(vector):
        index=len(history)
        if index>=cfg["solver"]["max_candidate_evaluations"]:raise RuntimeError("candidate budget exhausted")
        if time.perf_counter()-start>cfg["solver"]["max_runtime_seconds"]:raise TimeoutError("solver runtime budget exhausted")
        vector=np.clip(np.asarray(vector,dtype=float),bounds[:,0],bounds[:,1])
        theta=dict(initial)
        for pid,value in zip(ids,vector):theta[pid]=float(value)
        folder=ARTIFACT/f"candidate_{index:03d}";folder.mkdir(parents=True,exist_ok=True)
        job={"mode":"C1_V2_FORMAL_VISUAL_ONLY_CANDIDATE","parameters":theta,"anchor_distance_mm":anchor,
            "kfdg_path":str(graph_path),
            "frozen_interface_contracts":str(ROOT/"experiments/try5A/results/try5a5/motion_interface_contracts.json"),
            "f0_fcstd":str(ROOT/"experiments/try5A/artifacts/try5a5/round3_verified/links/L04/model.FCStd"),
            "output_root":str(folder)}
        save(folder/"job.json",job)
        tick=time.perf_counter()
        try:
            process=subprocess.run([python_runtime(),str(HERE/"scripts/freecad_c1_builder.py"),str(folder/"job.json")],
                cwd=ROOT,capture_output=True,text=True,timeout=cfg["solver"]["candidate_timeout_seconds"])
            (folder/"stdout.txt").write_text(process.stdout,encoding="utf-8")
            (folder/"stderr.txt").write_text(process.stderr,encoding="utf-8")
            if process.returncode:raise RuntimeError(f"FreeCAD exit {process.returncode}: {process.stderr[-1200:]}")
            built=load(folder/"build_result.json")
            if built["final_solid_count"]!=1 or not built["reopen"]["valid"]:
                raise RuntimeError("CAD invalid/reopen failed")
            score=objective.evaluate(folder/"body_only.stl",folder/"renders")
            row={"candidate_id":f"candidate_{index:03d}","status":"PASS","theta":theta,
                "active_parameters":ids,"total_visual_objective":score["total"],
                "contour_term":score["contour_term"],"landmark_term":None,
                "profile_term":score["profile_term"],"per_view":score["views"],
                "cad_build_success":True,"render_success":True,"final_solid_count":built["final_solid_count"],
                "cad_artifact_path":str((folder/"final.FCStd").relative_to(ROOT)).replace("\\","/"),
                "body_stl_path":str((folder/"body_only.stl").relative_to(ROOT)).replace("\\","/"),
                "runtime_seconds":time.perf_counter()-tick,"rejection_reason":None}
        except Exception as error:
            row={"candidate_id":f"candidate_{index:03d}","status":"INFRASTRUCTURE_INVALID","theta":theta,
                "active_parameters":ids,"total_visual_objective":cfg["solver"]["invalid_candidate_penalty"],
                "contour_term":None,"landmark_term":None,"profile_term":None,"per_view":[],
                "cad_build_success":(folder/"build_result.json").is_file(),"render_success":False,
                "final_solid_count":None,"cad_artifact_path":None,"body_stl_path":None,
                "runtime_seconds":time.perf_counter()-tick,
                "rejection_reason":f"{type(error).__name__}: {error}"}
        save(folder/"candidate_record.json",row)
        history.append(row)
        return row
    baseline=np.asarray([initial[pid] for pid in ids],dtype=float)
    evaluate(baseline)
    sampler=qmc.Sobol(d=len(ids),scramble=True,seed=cfg["solver"]["seed"])
    for point in sampler.random_base2(m=4):
        if len(history)>=cfg["solver"]["max_candidate_evaluations"]:break
        if time.perf_counter()-start>cfg["solver"]["max_runtime_seconds"]:break
        evaluate(bounds[:,0]+point*(bounds[:,1]-bounds[:,0]))
    stale=0
    while len(history)<cfg["solver"]["max_candidate_evaluations"] and time.perf_counter()-start<cfg["solver"]["max_runtime_seconds"]:
        valid=[x for x in history if x["status"]=="PASS"]
        if not valid:break
        best=min(valid,key=lambda x:x["total_visual_objective"])
        next_index=len(history)
        dim=(next_index-17)%len(ids)
        sign=1 if ((next_index-17)//len(ids))%2==0 else -1
        step=0.1*(bounds[dim,1]-bounds[dim,0])*(0.7**stale)
        proposal=np.asarray([best["theta"][pid] for pid in ids],dtype=float)
        proposal[dim]+=sign*step
        prior=best["total_visual_objective"]
        row=evaluate(proposal)
        stale=0 if row["status"]=="PASS" and row["total_visual_objective"]<prior-cfg["solver"]["convergence_tolerance"] else stale+1
        if stale>=cfg["solver"]["max_stale_evaluations"]:break
    valid=[row for row in history if row["status"]=="PASS"]
    if not valid:
        save(RESULT/"solver_failure.json",{"status":"NO_VALID_CAD_CANDIDATE","history_count":len(history),"invalid_count":len(history)})
        raise RuntimeError("no valid CAD candidate")
    best=min(valid,key=lambda row:row["total_visual_objective"])
    save(RESULT/"candidate_history.json",{"requested_max":cfg["solver"]["max_candidate_evaluations"],
        "evaluated":len(history),"valid":len(valid),"invalid":len(history)-len(valid),
        "history":history,"gt_accessed":False,"mechanical_feedback":False})
    with (RESULT/"candidate_history.csv").open("w",newline="",encoding="utf-8") as handle:
        fields=["candidate_id","status","total_visual_objective","contour_term","landmark_term","profile_term","runtime_seconds","cad_build_success","render_success","rejection_reason",*ids]
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
        for row in history:writer.writerow({**{key:row.get(key) for key in fields},**{pid:row["theta"][pid] for pid in ids}})
    with (RESULT/"objective_breakdown.csv").open("w",newline="",encoding="utf-8") as handle:
        fields=["candidate_id","status","total_visual_objective","contour_term","landmark_term","profile_term"]
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows([{key:row.get(key) for key in fields} for row in history])
    selected={"status":"SELECTED_BY_VISUAL_OBJECTIVE_ONLY","selected_candidate_id":best["candidate_id"],
        "theta_star":best["theta"],"active_parameters":ids,"initial_theta":initial,
        "initial_objective":history[0]["total_visual_objective"],"selected_objective":best["total_visual_objective"],
        "visual_objective_improvement":history[0]["total_visual_objective"]-best["total_visual_objective"],
        "actual_candidate_evaluations":len(history),"valid_candidates":len(valid),
        "invalid_candidates":len(history)-len(valid),"solver_runtime_seconds":time.perf_counter()-start,
        "termination":"stale_tolerance" if stale>=cfg["solver"]["max_stale_evaluations"] else "budget_or_runtime",
        "gt_accessed":False,"mechanical_feedback":False}
    save(RESULT/"theta_selected.json",selected)
    print(json.dumps({"status":"SELECTED","candidate":best["candidate_id"],
        "evaluations":len(history),"initial_objective":selected["initial_objective"],
        "selected_objective":selected["selected_objective"],"gt_accessed":False}))
    return selected


if __name__=="__main__":solve()
