"""Independent fail-closed audit of C2 formal search with zero feasible designs."""

from __future__ import annotations

import json

import numpy as np
from scipy.stats import qmc

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try6.scripts.run_r1_reliability import save

RESULT=HERE/"results/try6_0_c2"


def validate():
    cfg=load(HERE/"protocol/try6_0_c2.json")
    formal=load(RESULT/"formal_solver_freeze.json")
    history=load(RESULT/"solver/candidate_history.json")
    result=load(RESULT/"solver/solver_result.json")
    gate=load(RESULT/"replay/independent_activity_validation.json")
    c1=ROOT/cfg["c1_result_root"]
    active=load(c1/"kfdg/active_parameters.json")
    config=load(c1/"solver/config.json")
    if gate["activity_decision"]!="KFDE_ACTIVE_FORMAL_C2_ALLOWED":raise RuntimeError("KFDE not active")
    if formal["protocol_sha256"]!=sha(HERE/"protocol/try6_0_c2.json") or formal["c2_constrained_solver_source_sha256"]!=sha(HERE/"scripts/c2_constrained_metric_solver.py"):
        raise RuntimeError("formal C2 implementation/protocol drift")
    if formal["c1_kfdg_sha256"]!=sha(c1/"kfdg/canonical_kfdg.json") or formal["c1_visual_objective_definition_sha256"]!=sha(c1/"solver/objective_definition.json"):
        raise RuntimeError("frozen C1 method parity drift")
    rows=history["history"]
    if result["status"]!="NO_FEASIBLE_CANDIDATE" or len(rows)!=history["actual_proposals"] or len(rows)!=17:
        raise RuntimeError("C2 zero-feasible accounting mismatch")
    if any(row["candidate_id"]!=f"candidate_{i:03d}" for i,row in enumerate(rows)):
        raise RuntimeError("C2 proposal ID/order mismatch")
    if history["cad_builds"]!=17 or history["kfde_evaluations"]!=17 or history["kfde_rejects"]!=17 or history["feasible_candidates"]!=0 or history["visual_renders"]!=0 or history["visual_objective_evaluations"]!=0 or history["infrastructure_failures"]!=0:
        raise RuntimeError("C2 hard pre-render rejection accounting mismatch")
    if history["gt_accessed"] or history["full_mechanics_feedback"] or history["no_new_vlm_call"] is not True:
        raise RuntimeError("forbidden evaluator/VLM feedback in C2 search")
    if (RESULT/"solver/theta_selected.json").exists() or (RESULT/"evaluation/final_candidate_lock.json").exists() or (RESULT/"evaluation/evaluation_started.json").exists():
        raise RuntimeError("final C2 candidate/GT evaluation exists despite no feasible theta")
    ids=active["active_ids"]
    bounds=np.asarray([active["active_bounds"][pid] for pid in ids],dtype=float)
    vectors=[np.asarray([active["initial_theta"][pid] for pid in ids])]
    vectors.extend(bounds[:,0]+point*(bounds[:,1]-bounds[:,0]) for point in qmc.Sobol(d=len(ids),scramble=True,seed=config["seed"]).random_base2(m=4))
    c1_history=load(c1/"solver/candidate_history.json")["history"]
    tolerance=cfg["numerical_forbidden_volume_tolerance_mm3"]
    max_volumes=[]
    for index,(row,vector) in enumerate(zip(rows,vectors)):
        if row["status"]!="KFDE_REJECTED" or not row["cad_build_success"] or not row["kfde_evaluated"] or row["kfde_feasible"] is not False or row["render_success"] or row["visual_objective_evaluated"]:
            raise RuntimeError(f"C2 proposal {index} not properly hard-rejected")
        if row["active_parameters"]!=ids or not np.allclose(vector,[row["theta"][pid] for pid in ids],atol=1e-12,rtol=0):
            raise RuntimeError(f"C2 proposal {index} differs from C1 seed policy")
        if row["theta"]!=c1_history[index]["theta"]:
            raise RuntimeError(f"C2 first 17 proposals differ from frozen C1")
        raw=load(ROOT/row["kfde_check_path"])
        if sha(ROOT/row["kfde_check_path"])!=row["kfde_check_sha256"] or raw["candidate_id"]!=row["candidate_id"]:
            raise RuntimeError(f"KFDE raw check mismatch {index}")
        if raw["maximum_forbidden_intersection_mm3"]!=row["kfde_max_forbidden_intersection_mm3"] or raw["feasible"] is not False or raw["maximum_forbidden_intersection_mm3"]<=tolerance:
            raise RuntimeError(f"C2 proposal {index} rejection not supported by BREP volume")
        if raw["gt_accessed"] or raw["final_mechanics_evaluator_invoked"]:
            raise RuntimeError("GT/full mechanics entered C2 feasibility loop")
        max_volumes.append(raw["maximum_forbidden_intersection_mm3"])
    lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"]!=0:raise RuntimeError("formal holdout lock violated")
    # The frozen decision vocabulary has no exact label for zero feasible theta.
    # Do not misreport geometry preservation, mechanics benefit, or GT metrics.
    audit={"schema_version":"robotcad_try6_c2_no_feasible_audit_v1","status":"PASS",
        "terminal_decision_defined_by_frozen_protocol":False,
        "execution_outcome":"NO_FEASIBLE_CANDIDATE_AFTER_FROZEN_C1_PROPOSAL_SCHEDULE",
        "protocol_gap":"No allowed final C2 label covers an active, auditable KFDE with zero feasible candidates before final CAD/GT/mechanics; KFDE_OVERCONSTRAINED is defined only after improved mechanics and failed geometry preservation.",
        "formal_proposals":17,"valid_cad_builds":17,"kfde_hard_rejects":17,
        "feasible_candidates":0,"visual_renders":0,"visual_objective_evaluations":0,
        "minimum_max_pose_forbidden_intersection_mm3":min(max_volumes),
        "maximum_max_pose_forbidden_intersection_mm3":max(max_volumes),
        "selected_theta_exists":False,"final_candidate_lock_exists":False,
        "gt_evaluations":0,"final_development_mechanics_evaluations":0,
        "formal_holdout_accessed":False,"formal_holdout_evaluation_count":0,
        "no_new_vlm_call":True,"no_tuning_or_retry":True}
    save(RESULT/"audit/independent_no_feasible_validation.json",audit)
    print(json.dumps({"status":"PASS","outcome":audit["execution_outcome"],
        "proposals":17,"kfde_rejects":17,"gt_evaluations":0,
        "terminal_decision_defined":False}))
    return audit


if __name__=="__main__":validate()
