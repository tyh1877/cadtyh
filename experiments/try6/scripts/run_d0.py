"""Frozen probes + 256 Sobol + 5×12 local violation-only D0 characterization."""

from __future__ import annotations

import csv
import json
import math
import statistics
import subprocess
import sys
import time

import numpy as np
from scipy.stats import qmc,spearmanr

from experiments.try6.scripts.r1_contract import ROOT,HERE,canonical,load,sha
from experiments.try6.scripts.run_r1_reliability import save

sys.path.insert(0,str(ROOT/"experiments/try5A/scripts"))
from freecad_runtime import python_runtime

RESULT=HERE/"results/try6_0_d0"
ARTIFACT=HERE/"artifacts/try6_0_d0/probes"


def run():
    cfg=load(HERE/"protocol/try6_0_d0.json")
    pre=load(RESULT/"pre_run_manifest.json")
    if pre["status"]!="READY_FOR_FROZEN_DIAGNOSTIC" or pre["protocol_sha256"]!=sha(HERE/"protocol/try6_0_d0.json"):
        raise RuntimeError("D0 protocol not frozen")
    if sha(HERE/"scripts/freecad_d0_component_probe.py")!=pre["diagnostic_worker_sha256"]:
        raise RuntimeError("diagnostic worker changed after freeze")
    if sha(ROOT/cfg["active_parameter_source"])!=pre["active_bounds_sha256"] or sha(ROOT/cfg["kfde_construction_source"])!=pre["kfde_construction_sha256"]:
        raise RuntimeError("frozen C1/KFDE source drift")
    if (RESULT/"diagnostic_started.json").exists():raise FileExistsError("D0 already attempted; no rerun")
    lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"]!=0:raise RuntimeError("holdout lock violated")
    domain=load(RESULT/"frozen_inputs/c1_domain.json")
    ids=domain["active_ids"]
    bounds=np.asarray([domain["active_bounds"][pid] for pid in ids],dtype=float)
    initial=domain["initial_theta"]
    winner=domain["c1_winner_theta"]
    base={pid:initial[pid] for pid in initial}
    if len(ids)!=6 or cfg["stage_a"]["sample_count"]!=256 or cfg["stage_b"]["total_proposal_budget"]!=60:
        raise RuntimeError("D0 six-dimensional frozen budget drift")
    ARTIFACT.mkdir(parents=True,exist_ok=True)
    save(RESULT/"diagnostic_started.json",{"timestamp":time.time(),"protocol_sha256":pre["protocol_sha256"],
        "canonical_probe_count":5,"repeat_probe_count":1,"sobol_count":256,"local_count":60,
        "runtime_ceiling_seconds":cfg["maximum_total_runtime_seconds"],
        "VLM_calls":0,"GT_evaluations":0,"final_mechanics_evaluations":0})
    records=[];start=time.perf_counter()
    def candidate(candidate_id,phase,theta,metadata=None):
        if time.perf_counter()-start>=cfg["maximum_total_runtime_seconds"]:
            raise TimeoutError("predeclared D0 total runtime ceiling reached")
        folder=ARTIFACT/candidate_id;folder.mkdir(parents=True,exist_ok=True)
        job={"candidate_id":candidate_id,"theta":theta,
            "d0_protocol":"experiments/try6/protocol/try6_0_d0.json",
            "c2_protocol":"experiments/try6/protocol/try6_0_c2.json",
            "construction_report":cfg["kfde_construction_source"],
            "kfdg_source":cfg["kfdg_source"],
            "output_root":str(folder.relative_to(ROOT)).replace("\\","/")}
        job_path=folder/"job.json";save(job_path,job)
        tick=time.perf_counter()
        try:
            proc=subprocess.run([python_runtime(),str(HERE/"scripts/freecad_d0_component_probe.py"),str(job_path)],
                cwd=ROOT,capture_output=True,text=True,timeout=cfg["candidate_build_timeout_seconds"]+cfg["kfde_check_timeout_seconds"])
            (folder/"stdout.txt").write_text(proc.stdout,encoding="utf-8")
            (folder/"stderr.txt").write_text(proc.stderr,encoding="utf-8")
            if proc.returncode:raise RuntimeError(f"FreeCAD exit {proc.returncode}: {proc.stderr[-1000:]}")
            raw=load(folder/"component_result.json")
            if len(raw["components"])!=13 or raw["candidate_id"]!=candidate_id or raw["theta"]!=theta:
                raise RuntimeError("component vector/identity mismatch")
            record={"candidate_id":candidate_id,"phase":phase,"status":"EVALUATED","theta":theta,
                "cad_build_valid":raw["cad_build_valid"],"connected_solid_count":raw["connected_solid_count"],
                "g_sum_mm3":raw["g_sum_mm3"],"g_max_mm3":raw["g_max_mm3"],
                "strict_feasible":raw["strict_feasible"],"violating_component_count":raw["violating_component_count"],
                "dominant_component":raw["dominant_component"],"dominant_neighbor":raw["dominant_neighbor"],
                "mutable_added_volume_mm3":raw["mutable_added_volume_mm3"],
                "raw_path":str((folder/"component_result.json").relative_to(ROOT)).replace("\\","/"),
                "raw_sha256":sha(folder/"component_result.json"),"metadata":metadata or {},
                "runtime_seconds":time.perf_counter()-tick}
        except Exception as error:
            record={"candidate_id":candidate_id,"phase":phase,"status":"INFRASTRUCTURE_ERROR",
                "theta":theta,"error":f"{type(error).__name__}: {error}","metadata":metadata or {},
                "runtime_seconds":time.perf_counter()-tick}
        records.append(record)
        save(RESULT/"progress.json",{"completed":len(records),
            "canonical":sum(x["phase"]=="canonical" for x in records),
            "sobol":sum(x["phase"]=="sobol" for x in records),
            "local":sum(x["phase"]=="local" for x in records),
            "errors":sum(x["status"]!="EVALUATED" for x in records),
            "strict_feasible":sum(x.get("strict_feasible") is True for x in records),
            "elapsed_seconds":time.perf_counter()-start})
        return record
    probes=[("P0_ALL_LOWER",bounds[:,0]),("P1_ALL_UPPER",bounds[:,1]),
        ("P2_MIDPOINT",(bounds[:,0]+bounds[:,1])/2),
        ("P3_C1_INITIAL",np.asarray([initial[pid] for pid in ids])),
        ("P4_C1_VISUAL_WINNER",np.asarray([winner[pid] for pid in ids]))]
    probe_definitions=[]
    for candidate_id,vector in probes:
        theta=dict(base);theta.update({pid:float(value) for pid,value in zip(ids,vector)})
        probe_definitions.append({"candidate_id":candidate_id,"theta":theta})
        candidate(candidate_id,"canonical",theta)
    save(RESULT/"canonical_probes/probes.json",{"probes":probe_definitions,"P5_exact_F0_equivalent_omitted":True,
        "reason":"frozen F0 coarse FCStd has no exact six-variable current-builder parameter mapping"})
    repeat=candidate("P3_REPEAT_REPRODUCIBILITY","repeat",probe_definitions[3]["theta"])
    original=next(x for x in records if x["candidate_id"]=="P3_C1_INITIAL")
    deterministic=(repeat["status"]==original["status"]=="EVALUATED" and
        abs(repeat["g_sum_mm3"]-original["g_sum_mm3"])<=1e-6 and
        abs(repeat["g_max_mm3"]-original["g_max_mm3"])<=1e-6)
    save(RESULT/"canonical_probes/reproducibility_check.json",{"same_theta":True,"g_sum_match":deterministic,
        "g_max_match":deterministic,"P3_g_sum":original.get("g_sum_mm3"),"repeat_g_sum":repeat.get("g_sum_mm3"),
        "P3_g_max":original.get("g_max_mm3"),"repeat_g_max":repeat.get("g_max_mm3")})
    if not deterministic:raise RuntimeError("same-theta KFDE component evaluation not deterministic")
    points=qmc.Sobol(d=len(ids),scramble=True,seed=cfg["stage_a"]["seed"]).random_base2(m=8)
    for index,point in enumerate(points):
        vector=bounds[:,0]+point*(bounds[:,1]-bounds[:,0])
        theta=dict(base);theta.update({pid:float(value) for pid,value in zip(ids,vector)})
        candidate(f"S{index:03d}","sobol",theta,{"sobol_index":index})
    sobol=[x for x in records if x["phase"]=="sobol" and x["status"]=="EVALUATED"]
    if len(sobol)<cfg["stage_b"]["seed_count"]:
        raise RuntimeError("insufficient valid Stage-A seeds for frozen local search")
    seeds=sorted(sobol,key=lambda x:(x["g_max_mm3"],x["g_sum_mm3"],x["candidate_id"]))[:cfg["stage_b"]["seed_count"]]
    save(RESULT/"feasible_search/local_seed_selection.json",{"selection_rule":"lexicographic g_max then g_sum then candidate_id",
        "seed_ids":[x["candidate_id"] for x in seeds],"seed_metrics":[{"candidate_id":x["candidate_id"],
            "g_max_mm3":x["g_max_mm3"],"g_sum_mm3":x["g_sum_mm3"]} for x in seeds],
        "visual_objective_used":False})
    for seed_index,seed in enumerate(seeds):
        current=seed
        for dim,pid in enumerate(ids):
            pair=[]
            for direction in cfg["stage_b"]["directions_per_coordinate"]:
                theta=dict(current["theta"])
                theta[pid]=float(np.clip(theta[pid]+direction*cfg["stage_b"]["step_fraction_of_parameter_range"]*(bounds[dim,1]-bounds[dim,0]),bounds[dim,0],bounds[dim,1]))
                row=candidate(f"L{seed_index}_{dim}_{'N' if direction<0 else 'P'}","local",theta,
                    {"seed_id":seed["candidate_id"],"coordinate":pid,"direction":direction,
                     "base_id":current["candidate_id"]})
                pair.append(row)
            legal=[x for x in [current,*pair] if x["status"]=="EVALUATED"]
            current=min(legal,key=lambda x:(x["g_max_mm3"],x["g_sum_mm3"],x["candidate_id"]))
    save(RESULT/"all_candidate_records.json",{"requested_canonical":5,"requested_repeat":1,
        "requested_sobol":256,"requested_local":60,"completed":len(records),
        "runtime_seconds":time.perf_counter()-start,"records":records,
        "VLM_calls":0,"GT_evaluations":0,"final_mechanics_evaluations":0,"formal_holdout_accessed":False})
    if len(records)!=322:
        raise RuntimeError(f"D0 sample count incomplete: {len(records)}/322")
    with (RESULT/"canonical_probes/probe_results.csv").open("w",newline="",encoding="utf-8") as handle:
        fields=["candidate_id","status","g_sum_mm3","g_max_mm3","strict_feasible","connected_solid_count",
            "violating_component_count","dominant_component","dominant_neighbor","runtime_seconds",*ids]
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
        for row in records:
            if row["phase"]=="canonical":writer.writerow({**{k:row.get(k) for k in fields},**{pid:row["theta"][pid] for pid in ids}})
    with (RESULT/"feasible_search/sobol_samples.csv").open("w",newline="",encoding="utf-8") as handle:
        fields=["candidate_id",*ids];writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
        for row in records:
            if row["phase"]=="sobol":writer.writerow({"candidate_id":row["candidate_id"],**{pid:row["theta"][pid] for pid in ids}})
    with (RESULT/"feasible_search/violation_results.csv").open("w",newline="",encoding="utf-8") as handle:
        fields=["candidate_id","phase","status","g_sum_mm3","g_max_mm3","strict_feasible","runtime_seconds","error"]
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
        for row in records:writer.writerow({key:row.get(key) for key in fields})
    with (RESULT/"feasible_search/local_search_history.csv").open("w",newline="",encoding="utf-8") as handle:
        fields=["candidate_id","seed_id","coordinate","direction","base_id","g_sum_mm3","g_max_mm3","strict_feasible","status"]
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
        for row in records:
            if row["phase"]=="local":writer.writerow({**{key:row.get(key) for key in fields},**row["metadata"]})
    valid=[x for x in records if x["status"]=="EVALUATED" and x["phase"]!="repeat"]
    best=sorted(valid,key=lambda x:(x["g_max_mm3"],x["g_sum_mm3"],x["candidate_id"]))[:10]
    save(RESULT/"feasible_search/best_candidates.json",{"ranking":"g_max then g_sum only",
        "top_candidates":[{"candidate_id":x["candidate_id"],"phase":x["phase"],"theta":x["theta"],
            "g_max_mm3":x["g_max_mm3"],"g_sum_mm3":x["g_sum_mm3"],"strict_feasible":x["strict_feasible"]} for x in best]})
    print(json.dumps({"status":"D0_DIAGNOSTIC_COMPLETED","canonical":5,"repeat":1,"sobol":256,"local":60,
        "strict_feasible_stage_a":sum(x["strict_feasible"] for x in sobol),
        "strict_feasible_total":sum(x["strict_feasible"] for x in valid),
        "best_g_max_mm3":best[0]["g_max_mm3"],"runtime_seconds":time.perf_counter()-start}))
    return records


if __name__=="__main__":run()
