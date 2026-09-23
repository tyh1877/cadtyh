"""Independent D0 all-case feasibility, counterfactual and frozen-decision audit."""

from __future__ import annotations

import csv
import json
import math
import statistics
import subprocess
import sys
import unittest

import numpy as np
from scipy.stats import qmc,spearmanr

from experiments.try6.scripts.r1_contract import ROOT,HERE,canonical,load,sha
from experiments.try6.scripts.run_r1_reliability import save

RESULT=HERE/"results/try6_0_d0"


def prior(root):
    manifest=load(root/"manifest.json")
    if not all(sha(root/name)==digest for name,digest in manifest["result_file_sha256"].items()):
        raise RuntimeError(f"frozen prior result changed: {root}")
    return {"manifest_sha256":sha(root/"manifest.json"),"files_checked":len(manifest["result_file_sha256"]),"unchanged":True}


def validate():
    cfg=load(HERE/"protocol/try6_0_d0.json")
    pre=load(RESULT/"pre_run_manifest.json")
    if pre["protocol_sha256"]!=sha(HERE/"protocol/try6_0_d0.json"):
        raise RuntimeError("D0 protocol changed after freeze")
    priors={"c1_v2":prior(ROOT/cfg["c1_result_root"]),"c2":prior(ROOT/cfg["c2_result_root"])}
    domain=load(RESULT/"frozen_inputs/c1_domain.json")
    active=load(ROOT/cfg["active_parameter_source"])
    if domain["active_ids"]!=active["active_ids"] or domain["active_bounds"]!=active["active_bounds"] or domain["initial_theta"]!=active["initial_theta"]:
        raise RuntimeError("frozen C1 parameter domain drift")
    if pre["active_bounds_sha256"]!=sha(ROOT/cfg["active_parameter_source"]) or pre["kfdg_sha256"]!=sha(ROOT/cfg["kfdg_source"]) or pre["kfde_construction_sha256"]!=sha(ROOT/cfg["kfde_construction_source"]):
        raise RuntimeError("C1/KFDE hash drift")
    construction=load(ROOT/cfg["kfde_construction_source"])
    if construction["keepout"]["sha256"]!=sha(ROOT/construction["keepout"]["path"]) or construction["allowed_region"]["sha256"]!=sha(ROOT/construction["allowed_region"]["path"]):
        raise RuntimeError("frozen KFDE BREP drift")
    if cfg["strict_feasibility_epsilon_mm3"]!=construction["numerical_tolerance_mm3"]:
        raise RuntimeError("formal epsilon changed")
    all_rows=load(RESULT/"all_candidate_records.json")["records"]
    if len(all_rows)!=322 or any(x["status"]!="EVALUATED" for x in all_rows):
        raise RuntimeError("D0 characterization incomplete/invalid candidate")
    phase_counts={phase:sum(r["phase"]==phase for r in all_rows) for phase in ("canonical","repeat","sobol","local")}
    if phase_counts!={"canonical":5,"repeat":1,"sobol":256,"local":60}:
        raise RuntimeError("D0 frozen phase denominator mismatch")
    if load(RESULT/"all_candidate_records.json")["runtime_seconds"]>cfg["maximum_total_runtime_seconds"]:
        raise RuntimeError("D0 runtime ceiling exceeded")
    ids=domain["active_ids"]
    bounds=np.asarray([domain["active_bounds"][pid] for pid in ids],dtype=float)
    start=domain["initial_theta"]
    winner=domain["c1_winner_theta"]
    canonical_expected=[bounds[:,0],bounds[:,1],(bounds[:,0]+bounds[:,1])/2,
        np.asarray([start[pid] for pid in ids]),np.asarray([winner[pid] for pid in ids])]
    for row,vector in zip([r for r in all_rows if r["phase"]=="canonical"],canonical_expected):
        if not np.allclose([row["theta"][pid] for pid in ids],vector,atol=1e-12,rtol=0):
            raise RuntimeError("canonical probe theta mismatch")
    repeat=load(RESULT/"canonical_probes/reproducibility_check.json")
    if not repeat["g_sum_match"] or not repeat["g_max_match"]:
        raise RuntimeError("same-theta determinism failed")
    sobol=[r for r in all_rows if r["phase"]=="sobol"]
    points=qmc.Sobol(d=6,scramble=True,seed=cfg["stage_a"]["seed"]).random_base2(m=8)
    for index,(row,point) in enumerate(zip(sobol,points)):
        if row["candidate_id"]!=f"S{index:03d}" or not np.allclose([row["theta"][pid] for pid in ids],bounds[:,0]+point*(bounds[:,1]-bounds[:,0]),atol=1e-12,rtol=0):
            raise RuntimeError(f"Stage-A Sobol sample {index} drift")
    seeds=sorted(sobol,key=lambda x:(x["g_max_mm3"],x["g_sum_mm3"],x["candidate_id"]))[:5]
    frozen_seeds=load(RESULT/"feasible_search/local_seed_selection.json")["seed_ids"]
    if [x["candidate_id"] for x in seeds]!=frozen_seeds:
        raise RuntimeError("Stage-B local seeds not lowest frozen violation")
    local=[r for r in all_rows if r["phase"]=="local"]
    for seed_index,seed in enumerate(seeds):
        current=seed
        for dim,pid in enumerate(ids):
            pair=[]
            for direction in (-1,1):
                cid=f"L{seed_index}_{dim}_{'N' if direction<0 else 'P'}"
                row=next(r for r in local if r["candidate_id"]==cid)
                expected=float(np.clip(current["theta"][pid]+direction*cfg["stage_b"]["step_fraction_of_parameter_range"]*(bounds[dim,1]-bounds[dim,0]),bounds[dim,0],bounds[dim,1]))
                if row["metadata"]!={"seed_id":seed["candidate_id"],"coordinate":pid,"direction":direction,"base_id":current["candidate_id"]} or abs(row["theta"][pid]-expected)>1e-12:
                    raise RuntimeError(f"local proposal/base/step mismatch {cid}")
                if any(row["theta"][other]!=current["theta"][other] for other in ids if other!=pid):
                    raise RuntimeError(f"other parameter changed in local proposal {cid}")
                pair.append(row)
            current=min([current,*pair],key=lambda x:(x["g_max_mm3"],x["g_sum_mm3"],x["candidate_id"]))
    samples=[r for r in all_rows if r["phase"]!="repeat"]
    component_ids=[c["component_id"] for c in construction["components"]]
    tol=cfg["strict_feasibility_epsilon_mm3"]
    raw_by_id={}
    for row in all_rows:
        raw=load(ROOT/row["raw_path"])
        if sha(ROOT/row["raw_path"])!=row["raw_sha256"] or raw["candidate_id"]!=row["candidate_id"] or raw["theta"]!=row["theta"]:
            raise RuntimeError("raw D0 candidate identity/hash mismatch")
        if [x["component_id"] for x in raw["components"]]!=component_ids:
            raise RuntimeError("D0 component identity/order mismatch")
        if abs(sum(x["intersection_volume_mm3"] for x in raw["components"])-row["g_sum_mm3"])>1e-6 or max(x["intersection_volume_mm3"] for x in raw["components"])!=row["g_max_mm3"]:
            raise RuntimeError("D0 component sum/max mismatch")
        if raw["strict_feasible"]!=(row["g_max_mm3"]<=tol) or raw["GT_accessed"] or raw["final_mechanics_invoked"] or raw["VLM_calls"]!=0:
            raise RuntimeError("D0 strict feasibility/leakage mismatch")
        if raw["connected_solid_count"]!=1 or not raw["cad_build_valid"]:
            raise RuntimeError("D0 CAD invalid")
        raw_by_id[row["candidate_id"]]=raw
    matrix=list(csv.DictReader((RESULT/"constraint_decomposition/constraint_contribution_matrix.csv").open(newline="",encoding="utf-8")))
    if len(matrix)!=321*13:raise RuntimeError("component contribution matrix incomplete")
    for row in matrix:
        raw=raw_by_id[row["candidate_id"]]
        item=next(x for x in raw["components"] if x["component_id"]==row["constraint_component"])
        if float(row["intersection_volume_mm3"])!=item["intersection_volume_mm3"] or (row["violation_true_false"]=="True")!=item["violation"]:
            raise RuntimeError("component matrix differs from raw BREP result")
    component_summary=load(RESULT/"constraint_decomposition/constraint_summary.json")
    stage_matrix=[row for row in matrix if row["phase"]=="sobol"]
    for item in component_summary["per_component"]:
        values=[float(row["intersection_volume_mm3"]) for row in stage_matrix if row["constraint_component"]==item["component_id"]]
        count=sum(value>tol for value in values)
        if len(values)!=256 or count!=item["stage_a_violation_count"] or abs(statistics.mean(values)-item["stage_a_mean_forbidden_mm3"])>1e-9 or abs(statistics.median(values)-item["stage_a_median_forbidden_mm3"])>1e-9 or max(values)!=item["stage_a_max_forbidden_mm3"]:
            raise RuntimeError("per-pose contribution summary mismatch")
    for item in component_summary["per_neighbor"]:
        violating={row["candidate_id"] for row in stage_matrix if row["neighbor"]==item["neighbor_id"] and float(row["intersection_volume_mm3"])>tol}
        if len(violating)!=item["stage_a_rejected_candidates"]:
            raise RuntimeError("neighbor rejection frequency mismatch")
    counter=list(csv.DictReader((RESULT/"counterfactual/counterfactual_results.csv").open(newline="",encoding="utf-8")))
    if len(counter)!=321*5:raise RuntimeError("counterfactual matrix incomplete")
    counter_counts={name:0 for name in cfg["counterfactual_subsets"]}
    distinct={name:set() for name in cfg["counterfactual_subsets"]}
    samples_by_id={r["candidate_id"]:r for r in samples}
    for row in counter:
        raw=raw_by_id[row["candidate_id"]]
        subset=row["subset"]
        drop=None if subset=="FULL" else subset.removeprefix("MINUS_")
        vals=[x for x in raw["components"] if x["neighbor_id"]!=drop]
        gmax=max([x["intersection_volume_mm3"] for x in vals] or [0.0])
        gsum=sum(x["intersection_volume_mm3"] for x in vals)
        if len(vals)!=int(row["remaining_component_count"]) or abs(gsum-float(row["g_sum_mm3"]))>1e-6 or gmax!=float(row["g_max_mm3"]):
            raise RuntimeError("counterfactual removed/changed wrong components")
        if (row["strict_feasible"]=="True")!=(gmax<=tol):raise RuntimeError("counterfactual feasibility mismatch")
        if gmax<=tol:
            counter_counts[subset]+=1
            distinct[subset].add(canonical({pid:samples_by_id[row["candidate_id"]]["theta"][pid] for pid in ids}))
    suspect=load(RESULT/"counterfactual/semantic_suspect_summary.json")
    if counter_counts!=suspect["strict_feasible_count_by_subset"] or {k:len(v) for k,v in distinct.items()}!=suspect["distinct_theta_strict_feasible_by_subset"]:
        raise RuntimeError("counterfactual summary mismatch")
    stage_feasible=[r for r in sobol if r["strict_feasible"]]
    all_feasible=[r for r in samples if r["strict_feasible"]]
    density=load(RESULT/"feasible_search/feasible_density.json")
    if density["strict_feasible_sample_count"]!=len(stage_feasible) or density["empirical_feasible_sample_density"]!=len(stage_feasible)/256:
        raise RuntimeError("empirical Stage-A density mismatch")
    for threshold in cfg["near_feasible_thresholds_mm3"]:
        if density["near_feasible_stage_a_counts_by_threshold_mm3"][str(threshold)]!=sum(r["g_max_mm3"]<=threshold for r in sobol):
            raise RuntimeError("near-feasible threshold count mismatch")
    sensitivity=load(RESULT/"feasible_search/parameter_sensitivity.json")
    for pid in ids:
        for key,metric in (("rho_g_sum","g_sum_mm3"),("rho_g_max","g_max_mm3")):
            expected=float(spearmanr([r["theta"][pid] for r in sobol],[r[metric] for r in sobol]).statistic)
            if abs(sensitivity["by_parameter"][pid][key]-expected)>1e-12:raise RuntimeError("Spearman sensitivity mismatch")
    f0=load(RESULT/"authority_audit/f0_consistency_audit.json")
    if f0["exact_F0_equivalent_current_theta_mapping_available"]:raise RuntimeError("unexecuted exact P5 mapping exists")
    best=min(samples,key=lambda r:(r["g_max_mm3"],r["g_sum_mm3"],r["candidate_id"]))
    semantic_suspects=[name for name in cfg["counterfactual_subsets"] if name!="FULL" and len(distinct[name])>=cfg["counterfactual_semantic_suspect_min_distinct_strict_feasible"] and not all_feasible]
    if len({canonical({pid:r["theta"][pid] for pid in ids}) for r in stage_feasible})>=cfg["feasible_region_found_min_stage_a_distinct"]:
        decision="FEASIBLE_REGION_FOUND"
    elif all_feasible:
        decision="FEASIBLE_REGION_TOO_SMALL"
    elif semantic_suspects:
        decision="KFDE_SEMANTIC_MISMODEL_SUSPECTED"
    elif best["g_max_mm3"]>=cfg["material_incompatibility_min_best_gmax_mm3"]:
        decision="DOMAIN_KFDE_INCOMPATIBLE"
    else:
        decision="DIAGNOSTIC_INCONCLUSIVE"
    lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"]!=0:raise RuntimeError("holdout lock violated")
    validation={"schema_version":"robotcad_try6_d0_independent_validation_v1",
        "decision":decision,"frozen_prior_results":priors,
        "full_case_count":322,"canonical_probe_count":5,"reproducibility_repeat_count":1,
        "stage_a_sobol_count":256,"stage_b_local_count":60,"infrastructure_errors":0,
        "stage_a_strict_feasible":len(stage_feasible),"all_unique_strict_feasible":len(all_feasible),
        "empirical_stage_a_density":len(stage_feasible)/256,
        "best_candidate_id":best["candidate_id"],"best_g_max_mm3":best["g_max_mm3"],
        "best_g_sum_mm3":best["g_sum_mm3"],"strict_epsilon_mm3":tol,
        "counterfactual_strict_counts":counter_counts,
        "counterfactual_semantic_suspects":semantic_suspects,
        "F0_exact_mapping_available":False,
        "does_not_prove_continuous_domain_empty":True,
        "VLM_calls":0,"GT_evaluations":0,"final_mechanics_evaluations":0,
        "formal_holdout_accessed":False,"formal_holdout_evaluation_count":0,
        "no_KFDE_or_bounds_tuning":True}
    save(RESULT/"audit/independent_validation.json",validation)
    print(json.dumps({"decision":decision,"stage_a_feasible":len(stage_feasible),
        "all_feasible":len(all_feasible),"best_g_max_mm3":best["g_max_mm3"],
        "counterfactual_strict_counts":counter_counts,"GT_evaluations":0}))
    return validation


if __name__=="__main__":validate()
