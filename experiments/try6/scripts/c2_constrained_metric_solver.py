"""C1 seeded bounded visual search with one added hard pre-render KFDE gate."""

from __future__ import annotations

import csv
import json
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

RESULT=HERE/"results/try6_0_c2/solver"
ARTIFACT=HERE/"artifacts/try6_0_c2/solver"


def solve():
    c2=load(HERE/"protocol/try6_0_c2.json")
    gate=load(HERE/"results/try6_0_c2/replay/independent_activity_validation.json")
    if gate["activity_decision"]!="KFDE_ACTIVE_FORMAL_C2_ALLOWED":
        raise RuntimeError("KFDE activity gate not passed")
    formal=load(HERE/"results/try6_0_c2/formal_solver_freeze.json")
    if formal["protocol_sha256"]!=sha(HERE/"protocol/try6_0_c2.json") or formal["c2_constrained_solver_source_sha256"]!=sha(HERE/"scripts/c2_constrained_metric_solver.py"):
        raise RuntimeError("formal C2 implementation/protocol changed after freeze")
    parity=load(HERE/"results/try6_0_c2/frozen_c1/parity_audit.json")
    if parity["status"]!="PASS" or parity["no_new_vlm_call"] is not True:
        raise RuntimeError("C1→C2 parity gate not passed")
    construction=load(HERE/"results/try6_0_c2/kfde/construction_report.json")
    if construction["status"]!="PASS":raise RuntimeError("KFDE construction not passed")
    c1=ROOT/c2["c1_result_root"]
    graph_path=c1/"kfdg/canonical_kfdg.json"
    graph=load(graph_path);validate_kfdg(graph)
    active=load(c1/"kfdg/active_parameters.json")
    ids=active["active_ids"]
    initial=active["initial_theta"]
    bounds=np.asarray([active["active_bounds"][pid] for pid in ids],dtype=float)
    config=load(c1/"solver/config.json")
    if config!=parity["optimizer_config"] or config["max_candidate_evaluations"]!=c2["c2_max_proposals_if_active"]:
        raise RuntimeError("C1 optimizer config not reused exactly")
    # The actual source hash is pinned in C1 pre_run_manifest; no objective code edit is allowed.
    c1_pre=load(c1/"pre_run_manifest.json")
    if sha(HERE/"scripts/c1_v2_visual_objective.py")!=c1_pre["method_hashes"]["visual_objective_source"] or sha(HERE/"scripts/freecad_c1_builder.py")!=c1_pre["method_hashes"]["freecad_builder_source"]:
        raise RuntimeError("C1 visual objective/CAD compiler source drift")
    lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"]!=0:raise RuntimeError("holdout lock violated")
    if RESULT.exists():raise FileExistsError("formal C2 solver already attempted; no rerun")
    RESULT.mkdir(parents=True);ARTIFACT.mkdir(parents=True,exist_ok=True)
    save(RESULT/"attempt_started.json",{"status":"STARTED_ONE_FORMAL_C2_SEARCH",
        "protocol_sha256":sha(HERE/"protocol/try6_0_c2.json"),
        "c1_kfdg_sha256":sha(graph_path),"c1_active_parameters_sha256":sha(c1/"kfdg/active_parameters.json"),
        "c1_objective_sha256":sha(c1/"solver/objective_definition.json"),
        "c1_optimizer_config_sha256":sha(c1/"solver/config.json"),
        "kfde_construction_sha256":sha(HERE/"results/try6_0_c2/kfde/construction_report.json"),
        "gt_access":False,"full_mechanics_feedback":False,"manual_intervention":0})
    save(RESULT/"config.json",config)
    objective=VisibleObjective()
    if abs(objective.anchor-graph["metric_anchor"]["distance_mm"])>1e-9:
        raise RuntimeError("URDF anchor/visual objective drift")
    history=[];start=time.perf_counter()
    def evaluate(vector):
        index=len(history)
        if index>=config["max_candidate_evaluations"]:raise RuntimeError("proposal budget exhausted")
        if time.perf_counter()-start>config["max_runtime_seconds"]:raise TimeoutError("solver runtime budget exhausted")
        vector=np.clip(np.asarray(vector,dtype=float),bounds[:,0],bounds[:,1])
        theta=dict(initial)
        for pid,value in zip(ids,vector):theta[pid]=float(value)
        folder=ARTIFACT/f"candidate_{index:03d}";folder.mkdir(parents=True,exist_ok=True)
        job={"mode":"C2_VISUAL_SEARCH_WITH_HARD_KFDE","parameters":theta,"anchor_distance_mm":objective.anchor,
            "kfdg_path":str(graph_path),
            "frozen_interface_contracts":str(ROOT/"experiments/try5A/results/try5a5/motion_interface_contracts.json"),
            "f0_fcstd":str(ROOT/"experiments/try5A/artifacts/try5a5/round3_verified/links/L04/model.FCStd"),
            "output_root":str(folder)}
        save(folder/"job.json",job)
        tick=time.perf_counter()
        row={"candidate_id":f"candidate_{index:03d}","theta":theta,"active_parameters":ids,
            "status":"STARTED","cad_build_success":False,"kfde_evaluated":False,
            "kfde_feasible":None,"kfde_max_forbidden_intersection_mm3":None,
            "kfde_violating_components":[],"render_success":False,"visual_objective_evaluated":False,
            "total_visual_objective":None,"contour_term":None,"landmark_term":None,"profile_term":None,
            "rejection_reason":None}
        try:
            cad=subprocess.run([python_runtime(),str(HERE/"scripts/freecad_c1_builder.py"),str(folder/"job.json")],
                cwd=ROOT,capture_output=True,text=True,timeout=config["candidate_timeout_seconds"])
            (folder/"cad_stdout.txt").write_text(cad.stdout,encoding="utf-8")
            (folder/"cad_stderr.txt").write_text(cad.stderr,encoding="utf-8")
            if cad.returncode:raise RuntimeError(f"FreeCAD build exit {cad.returncode}: {cad.stderr[-1000:]}")
            built=load(folder/"build_result.json")
            if built["final_solid_count"]!=1 or not built["reopen"]["valid"]:
                raise RuntimeError("CAD invalid/reopen failed")
            row["cad_build_success"]=True
            check_job={"mode":"check","protocol":"experiments/try6/protocol/try6_0_c2.json",
                "construction_report":"experiments/try6/results/try6_0_c2/kfde/construction_report.json",
                "candidate_id":row["candidate_id"],
                "candidate_fcstd":str((folder/"final.FCStd").relative_to(ROOT)).replace("\\","/"),
                "output":str((folder/"kfde_check.json").relative_to(ROOT)).replace("\\","/")}
            save(folder/"kfde_job.json",check_job)
            ktick=time.perf_counter()
            kproc=subprocess.run([python_runtime(),str(HERE/"scripts/freecad_c2_kfde.py"),str(folder/"kfde_job.json")],
                cwd=ROOT,capture_output=True,text=True,timeout=config["candidate_timeout_seconds"])
            row["kfde_runtime_seconds"]=time.perf_counter()-ktick
            (folder/"kfde_stdout.txt").write_text(kproc.stdout,encoding="utf-8")
            (folder/"kfde_stderr.txt").write_text(kproc.stderr,encoding="utf-8")
            if kproc.returncode:raise RuntimeError(f"KFDE check exit {kproc.returncode}: {kproc.stderr[-1000:]}")
            kfde=load(folder/"kfde_check.json")
            row["kfde_evaluated"]=True
            row["kfde_feasible"]=kfde["feasible"]
            row["kfde_max_forbidden_intersection_mm3"]=kfde["maximum_forbidden_intersection_mm3"]
            row["kfde_violating_components"]=kfde["violating_components"]
            row["kfde_check_path"]=check_job["output"]
            row["kfde_check_sha256"]=sha(folder/"kfde_check.json")
            if not kfde["feasible"]:
                row["status"]="KFDE_REJECTED"
                row["rejection_reason"]="hard forbidden intersection exceeds predeclared numerical tolerance"
            else:
                score=objective.evaluate(folder/"body_only.stl",folder/"renders")
                row.update({"status":"FEASIBLE_VISUAL_EVALUATED","render_success":True,
                    "visual_objective_evaluated":True,"total_visual_objective":score["total"],
                    "contour_term":score["contour_term"],"profile_term":score["profile_term"],
                    "per_view":score["views"]})
        except Exception as error:
            row["status"]="INFRASTRUCTURE_INVALID"
            row["rejection_reason"]=f"{type(error).__name__}: {error}"
        row["runtime_seconds"]=time.perf_counter()-tick
        save(folder/"candidate_record.json",row)
        history.append(row)
        save(RESULT/"solver_progress.json",{"proposals":len(history),"max_proposals":config["max_candidate_evaluations"],
            "kfde_rejects":sum(x["status"]=="KFDE_REJECTED" for x in history),
            "feasible":sum(x["status"]=="FEASIBLE_VISUAL_EVALUATED" for x in history),
            "infrastructure_invalid":sum(x["status"]=="INFRASTRUCTURE_INVALID" for x in history)})
        return row
    baseline=np.asarray([initial[pid] for pid in ids],dtype=float)
    evaluate(baseline)
    sampler=qmc.Sobol(d=len(ids),scramble=True,seed=config["seed"])
    for point in sampler.random_base2(m=4):
        if len(history)>=config["max_candidate_evaluations"] or time.perf_counter()-start>config["max_runtime_seconds"]:break
        evaluate(bounds[:,0]+point*(bounds[:,1]-bounds[:,0]))
    stale=0
    while len(history)<config["max_candidate_evaluations"] and time.perf_counter()-start<config["max_runtime_seconds"]:
        feasible=[x for x in history if x["status"]=="FEASIBLE_VISUAL_EVALUATED"]
        if not feasible:break  # Identical C1 fallback when no legal visual candidate exists.
        best=min(feasible,key=lambda x:x["total_visual_objective"])
        next_index=len(history);dim=(next_index-17)%len(ids)
        sign=1 if ((next_index-17)//len(ids))%2==0 else -1
        step=0.1*(bounds[dim,1]-bounds[dim,0])*(0.7**stale)
        proposal=np.asarray([best["theta"][pid] for pid in ids],dtype=float)
        proposal[dim]+=sign*step
        prior=best["total_visual_objective"]
        row=evaluate(proposal)
        stale=0 if row["status"]=="FEASIBLE_VISUAL_EVALUATED" and row["total_visual_objective"]<prior-config["convergence_tolerance"] else stale+1
        if stale>=config["max_stale_evaluations"]:break
    feasible=[x for x in history if x["status"]=="FEASIBLE_VISUAL_EVALUATED"]
    save(RESULT/"candidate_history.json",{"max_proposals":config["max_candidate_evaluations"],
        "actual_proposals":len(history),"cad_builds":sum(x["cad_build_success"] for x in history),
        "kfde_evaluations":sum(x["kfde_evaluated"] for x in history),
        "kfde_rejects":sum(x["status"]=="KFDE_REJECTED" for x in history),
        "feasible_candidates":len(feasible),"visual_renders":sum(x["render_success"] for x in history)*2,
        "visual_objective_evaluations":sum(x["visual_objective_evaluated"] for x in history),
        "infrastructure_failures":sum(x["status"]=="INFRASTRUCTURE_INVALID" for x in history),
        "solver_runtime_seconds":time.perf_counter()-start,"history":history,
        "gt_accessed":False,"full_mechanics_feedback":False,"no_new_vlm_call":True})
    with (RESULT/"candidate_history.csv").open("w",newline="",encoding="utf-8") as handle:
        fields=["candidate_id","status","cad_build_success","kfde_evaluated","kfde_feasible",
            "kfde_max_forbidden_intersection_mm3","render_success","visual_objective_evaluated",
            "total_visual_objective","contour_term","profile_term","runtime_seconds","rejection_reason",*ids]
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
        for row in history:writer.writerow({**{key:row.get(key) for key in fields},**{pid:row["theta"][pid] for pid in ids}})
    with (RESULT/"kfde_violations.csv").open("w",newline="",encoding="utf-8") as handle:
        fields=["candidate_id","component_id","link_id","joint_id","q_rad","forbidden_intersection_mm3"]
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
        for row in history:
            for v in row["kfde_violating_components"]:
                writer.writerow({"candidate_id":row["candidate_id"],**{key:v[key] for key in fields if key!="candidate_id"}})
    with (RESULT/"visual_objective_history.csv").open("w",newline="",encoding="utf-8") as handle:
        fields=["candidate_id","total_visual_objective","contour_term","profile_term"]
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
        for row in feasible:writer.writerow({key:row[key] for key in fields})
    if feasible:
        best=min(feasible,key=lambda row:row["total_visual_objective"])
        selected={"status":"SELECTED_LOWEST_VISUAL_LOSS_AMONG_KFDE_FEASIBLE",
            "selected_candidate_id":best["candidate_id"],"theta_star":best["theta"],
            "selected_visual_objective":best["total_visual_objective"],
            "active_parameters":ids,"actual_proposals":len(history),"feasible_candidates":len(feasible),
            "gt_accessed":False,"mechanical_feedback":False}
        save(RESULT/"theta_selected.json",selected)
        status="FEASIBLE_THETA_SELECTED"
    else:
        status="NO_FEASIBLE_CANDIDATE"
    save(RESULT/"solver_result.json",{"status":status,"actual_proposals":len(history),
        "feasible_candidates":len(feasible),"kfde_rejects":sum(x["status"]=="KFDE_REJECTED" for x in history),
        "visual_objective_evaluations":sum(x["visual_objective_evaluated"] for x in history),
        "termination":"no_feasible_after_frozen_C1_initial_and_Sobol_schedule" if not feasible else
            "stale_tolerance_or_budget","gt_accessed":False,"holdout_accessed":False})
    print(json.dumps({"status":status,"proposals":len(history),"kfde_rejects":sum(x["status"]=="KFDE_REJECTED" for x in history),
        "feasible":len(feasible),"renders":sum(x["render_success"] for x in history)*2,"gt_accessed":False}))
    return status


if __name__=="__main__":solve()
