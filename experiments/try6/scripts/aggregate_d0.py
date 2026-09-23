"""Frozen D0 component/feasible-density/counterfactual descriptive aggregation."""

from __future__ import annotations

import csv
import json
import math
import statistics
from collections import Counter,defaultdict

import numpy as np
from scipy.stats import spearmanr

from experiments.try6.scripts.r1_contract import ROOT,HERE,canonical,load,sha
from experiments.try6.scripts.run_r1_reliability import save

RESULT=HERE/"results/try6_0_d0"


def main():
    cfg=load(HERE/"protocol/try6_0_d0.json")
    bundle=load(RESULT/"all_candidate_records.json")
    records=bundle["records"]
    if len(records)!=322 or any(r["status"]!="EVALUATED" for r in records):
        raise RuntimeError("D0 all-case completion gate failed")
    samples=[r for r in records if r["phase"]!="repeat"]
    stage=[r for r in records if r["phase"]=="sobol"]
    local=[r for r in records if r["phase"]=="local"]
    if (len(samples),len(stage),len(local))!=(321,256,60):raise RuntimeError("D0 denominator drift")
    tol=cfg["strict_feasibility_epsilon_mm3"]
    if any(r["strict_feasible"]!=(r["g_max_mm3"]<=tol) for r in samples):
        raise RuntimeError("D0 strict feasibility mismatch")
    components=load(RESULT/"constraint_decomposition/component_registry.json")["components"]
    ids=[c["component_id"] for c in components]
    by_id={c["component_id"]:c for c in components}
    stage_component=defaultdict(list);stage_neighbor_reject=Counter()
    stage_pose_reject=Counter()
    matrix=RESULT/"constraint_decomposition/constraint_contribution_matrix.csv"
    with matrix.open("w",newline="",encoding="utf-8") as handle:
        fields=["candidate_id","phase","theta_json","constraint_component","neighbor","joint_id","pose_q_rad",
            "intersection_volume_mm3","violation_true_false"]
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
        for row in samples:
            raw=load(ROOT/row["raw_path"])
            if sha(ROOT/row["raw_path"])!=row["raw_sha256"] or [x["component_id"] for x in raw["components"]]!=ids:
                raise RuntimeError("D0 raw component vector hash/order mismatch")
            if abs(sum(x["intersection_volume_mm3"] for x in raw["components"])-row["g_sum_mm3"])>1e-6 or max(x["intersection_volume_mm3"] for x in raw["components"])!=row["g_max_mm3"]:
                raise RuntimeError("D0 g_sum/g_max decomposition mismatch")
            violated_neighbors=set()
            for value in raw["components"]:
                cid=value["component_id"]
                writer.writerow({"candidate_id":row["candidate_id"],"phase":row["phase"],
                    "theta_json":canonical(row["theta"]),"constraint_component":cid,
                    "neighbor":value["neighbor_id"],"joint_id":value["joint_id"],"pose_q_rad":value["pose_q_rad"],
                    "intersection_volume_mm3":value["intersection_volume_mm3"],
                    "violation_true_false":value["violation"]})
                if row["phase"]=="sobol":
                    stage_component[cid].append(value["intersection_volume_mm3"])
                    if value["violation"]:
                        stage_pose_reject[cid]+=1
                        violated_neighbors.add(value["neighbor_id"])
            if row["phase"]=="sobol":
                for neighbor in violated_neighbors:stage_neighbor_reject[neighbor]+=1
    component_summary=[]
    for cid in ids:
        vals=stage_component[cid]
        component_summary.append({"component_id":cid,"neighbor_id":by_id[cid]["neighbor_id"],
            "joint_id":by_id[cid]["joint_id"],"pose_q_rad":by_id[cid]["pose_q_rad"],
            "stage_a_violation_count":stage_pose_reject[cid],
            "stage_a_rejection_rate":stage_pose_reject[cid]/256,
            "stage_a_mean_forbidden_mm3":statistics.mean(vals),
            "stage_a_median_forbidden_mm3":statistics.median(vals),
            "stage_a_max_forbidden_mm3":max(vals)})
    summary={"schema_version":"robotcad_try6_d0_constraint_summary_v1","stage_a_denominator":256,
        "all_unique_candidate_denominator":321,
        "per_component":component_summary,
        "per_neighbor":[{"neighbor_id":n,"stage_a_rejected_candidates":stage_neighbor_reject[n],
            "stage_a_rejection_rate":stage_neighbor_reject[n]/256,
            "component_ids":[c["component_id"] for c in components if c["neighbor_id"]==n]} for n in ("L03","L05","L06","L07")],
        "g_sum_definition":"sum of 13 per-pose BREP intersection volumes; overlapping sweep poses can double-count in this descriptive diagnostic",
        "g_max_definition":"maximum single frozen neighbor/pose component exact BREP intersection volume"}
    save(RESULT/"constraint_decomposition/constraint_summary.json",summary)
    feasible=[r for r in stage if r["strict_feasible"]]
    near={str(t):sum(r["g_max_mm3"]<=t for r in stage) for t in cfg["near_feasible_thresholds_mm3"]}
    domain=load(RESULT/"frozen_inputs/c1_domain.json")
    active=domain["active_ids"]
    bounds={pid:domain["active_bounds"][pid] for pid in active}
    distinct={canonical({pid:r["theta"][pid] for pid in active}):r for r in feasible}
    def nearest(ref):
        if not feasible:return None
        return min(({"candidate_id":r["candidate_id"],"normalized_l2_distance":math.sqrt(sum(((r["theta"][pid]-ref[pid])/(bounds[pid][1]-bounds[pid][0]))**2 for pid in active))} for r in feasible),key=lambda x:x["normalized_l2_distance"])
    density={"schema_version":"robotcad_try6_d0_empirical_density_v1","stage_a_sample_count":256,
        "strict_feasible_sample_count":len(feasible),"strict_feasible_distinct_theta_count":len(distinct),
        "empirical_feasible_sample_density":len(feasible)/256,
        "near_feasible_stage_a_counts_by_threshold_mm3":near,
        "strict_epsilon_mm3":tol,"stage_a_minimum_g_max_mm3":min(r["g_max_mm3"] for r in stage),
        "stage_a_minimum_g_sum_mm3":min(r["g_sum_mm3"] for r in stage),
        "feasible_empirical_ranges":{pid:[min(r["theta"][pid] for r in feasible),max(r["theta"][pid] for r in feasible)] for pid in active} if feasible else None,
        "feasible_distance_to_bounds":{pid:[min((r["theta"][pid]-bounds[pid][0])/(bounds[pid][1]-bounds[pid][0]) for r in feasible),
            min((bounds[pid][1]-r["theta"][pid])/(bounds[pid][1]-bounds[pid][0]) for r in feasible)] for pid in active} if feasible else None,
        "nearest_feasible_to_c1_initial":nearest(domain["initial_theta"]),
        "nearest_feasible_to_c1_winner":nearest(domain["c1_winner_theta"]),
        "not_a_continuous_volume_estimate":True}
    save(RESULT/"feasible_search/feasible_density.json",density)
    sensitivity={"schema_version":"robotcad_try6_d0_parameter_sensitivity_v1","stage_a_denominator":256,
        "method":"Spearman rho descriptive only; no causal interpretation",
        "by_parameter":{pid:{"rho_g_sum":float(spearmanr([r["theta"][pid] for r in stage],[r["g_sum_mm3"] for r in stage]).statistic),
            "rho_g_max":float(spearmanr([r["theta"][pid] for r in stage],[r["g_max_mm3"] for r in stage]).statistic)} for pid in active},
        "not_used_by_D0_search":True}
    save(RESULT/"feasible_search/parameter_sensitivity.json",sensitivity)
    counter_rows=[]
    counts={name:0 for name in cfg["counterfactual_subsets"]}
    distinct_by_subset={name:set() for name in cfg["counterfactual_subsets"]}
    for row in samples:
        raw=load(ROOT/row["raw_path"])
        vector=raw["components"]
        for name in cfg["counterfactual_subsets"]:
            drop=None if name=="FULL" else name.removeprefix("MINUS_")
            selected=[x for x in vector if x["neighbor_id"]!=drop]
            if len(selected)!=len(vector)-(sum(x["neighbor_id"]==drop for x in vector) if drop else 0):
                raise RuntimeError("counterfactual removed unintended component")
            g_max=max([x["intersection_volume_mm3"] for x in selected] or [0.0])
            g_sum=sum(x["intersection_volume_mm3"] for x in selected)
            strict=g_max<=tol
            if strict:
                counts[name]+=1
                distinct_by_subset[name].add(canonical({pid:row["theta"][pid] for pid in active}))
            counter_rows.append({"candidate_id":row["candidate_id"],"phase":row["phase"],
                "subset":name,"removed_neighbor":drop or "NONE","remaining_component_count":len(selected),
                "g_max_mm3":g_max,"g_sum_mm3":g_sum,"strict_feasible":strict})
    with (RESULT/"counterfactual/counterfactual_results.csv").open("w",newline="",encoding="utf-8") as handle:
        fields=list(counter_rows[0]);writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows(counter_rows)
    threshold=cfg["counterfactual_semantic_suspect_min_distinct_strict_feasible"]
    suspect=[name for name in cfg["counterfactual_subsets"] if name!="FULL" and len(distinct_by_subset[name])>=threshold and counts["FULL"]==0]
    save(RESULT/"counterfactual/semantic_suspect_summary.json",{"candidate_denominator":321,
        "strict_feasible_count_by_subset":counts,
        "distinct_theta_strict_feasible_by_subset":{name:len(value) for name,value in distinct_by_subset.items()},
        "semantic_suspect_min_distinct_threshold":threshold,
        "SEMANTIC_MISMODEL_SUSPECT_neighbors":[name.removeprefix("MINUS_") for name in suspect],
        "diagnostic_only":True,"no_KFDE_artifact_modified":True})
    contracts=load(ROOT/"experiments/try5A/results/try5a5/motion_interface_contracts.json")
    j04=next(x for x in contracts if x["joint_id"]=="J04")
    j06=next(x for x in contracts if x["joint_id"]=="J06")
    save(RESULT/"authority_audit/fixed_neighbor_audit.json",{"L05_J04_fixed":j04["joint_type"]=="fixed",
        "L07_J06_fixed":j06["joint_type"]=="fixed",
        "J04_allowed_contact_volume_mm3":j04["allowed_contact_volume_mm3"],
        "frozen_allowed_contact_policy":load(ROOT/"experiments/try6/protocol/try6_0_c2.json")["allowed_contact_policy"],
        "L05_stage_a_rejection_rate":stage_neighbor_reject["L05"]/256,
        "L07_stage_a_rejection_rate":stage_neighbor_reject["L07"]/256,
        "allowed_contact_audit_sha256":sha(ROOT/"experiments/try6/results/try6_0_c2/kfde/allowed_contact_audit.json"),
        "interpretation":"J04 is a fixed mount with frozen allowed contact volume 0 mm3; L05 volumetric overlap outside the frozen scaffold/interface allowance is forbidden by current KFDE, but this diagnostic alone cannot prove semantic correctness."})
    save(RESULT/"authority_audit/allowed_contact_audit.json",{"frozen_C2_allowed_region_sha256":load(ROOT/"experiments/try6/results/try6_0_c2/kfde/construction_report.json")["allowed_region"]["sha256"],
        "frozen_scaffold_residual_mm3":load(ROOT/"experiments/try6/results/try6_0_c2/kfde/allowed_contact_audit.json")["frozen_scaffold_residual_after_exemption_mm3"],
        "allowed_mask_unchanged":True,"no_posthoc_adjustment":True})
    print(json.dumps({"samples_stage_a":256,"strict_stage_a":len(feasible),
        "best_g_max_all":min(r["g_max_mm3"] for r in samples),
        "strict_counterfactual":counts,"semantic_suspects":suspect}))
    return {"constraint_summary":summary,"density":density,"counterfactual_counts":counts}


if __name__=="__main__":main()
