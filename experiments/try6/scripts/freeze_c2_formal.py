"""Pre-register constrained C2 run only after independent active-KFDE replay gate."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime,timezone

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try6.scripts.run_r1_reliability import save

RESULT=HERE/"results/try6_0_c2"


def main():
    cfg=load(HERE/"protocol/try6_0_c2.json")
    target=RESULT/"formal_solver_freeze.json"
    if target.exists():raise FileExistsError("formal C2 already frozen")
    construction=load(RESULT/"kfde/independent_construction_validation.json")
    activity=load(RESULT/"replay/independent_activity_validation.json")
    parity=load(RESULT/"frozen_c1/parity_audit.json")
    if construction["status"]!="PASS" or activity["activity_decision"]!="KFDE_ACTIVE_FORMAL_C2_ALLOWED" or parity["status"]!="PASS":
        raise RuntimeError("formal C2 start gates not passed")
    if (RESULT/"solver").exists():raise FileExistsError("formal C2 solver already attempted")
    c1=ROOT/cfg["c1_result_root"]
    c1_pre=load(c1/"pre_run_manifest.json")
    if sha(HERE/"scripts/freecad_c1_builder.py")!=c1_pre["method_hashes"]["freecad_builder_source"] or sha(HERE/"scripts/c1_v2_visual_objective.py")!=c1_pre["method_hashes"]["visual_objective_source"]:
        raise RuntimeError("C1 compiler/objective source drift")
    c1_solver=load(c1/"solver/config.json")
    if c1_solver!=parity["optimizer_config"] or c1_solver["max_candidate_evaluations"]!=cfg["c2_max_proposals_if_active"]:
        raise RuntimeError("C1 optimizer/config parity drift")
    lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"]!=0:raise RuntimeError("holdout lock violated")
    head=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    record={"schema_version":"robotcad_try6_c2_formal_solver_freeze_v1",
        "timestamp_utc":datetime.now(timezone.utc).isoformat(),
        "implementation_commit_before_formal_C2":head,"protocol_sha256":sha(HERE/"protocol/try6_0_c2.json"),
        "c1_slot_sha256":sha(c1/"slot/validated_slots.json"),
        "c1_kfdg_sha256":sha(c1/"kfdg/canonical_kfdg.json"),
        "c1_active_parameters_sha256":sha(c1/"kfdg/active_parameters.json"),
        "c1_visual_evidence_sha256":sha(c1/"visual_metric_evidence/visual_metric_evidence.json"),
        "c1_view_registration_sha256":sha(c1/"visual_metric_evidence/view_registration_report.json"),
        "c1_visual_objective_definition_sha256":sha(c1/"solver/objective_definition.json"),
        "c1_optimizer_config_sha256":sha(c1/"solver/config.json"),
        "c1_candidate_history_sha256":sha(c1/"solver/candidate_history.json"),
        "c1_cad_compiler_sha256":sha(HERE/"scripts/freecad_c1_builder.py"),
        "c1_visual_objective_source_sha256":sha(HERE/"scripts/c1_v2_visual_objective.py"),
        "c2_constrained_solver_source_sha256":sha(HERE/"scripts/c2_constrained_metric_solver.py"),
        "kfde_construction_sha256":sha(RESULT/"kfde/construction_report.json"),
        "kfde_keepout_sha256":load(RESULT/"kfde/construction_report.json")["keepout"]["sha256"],
        "allowed_contact_sha256":load(RESULT/"kfde/construction_report.json")["allowed_region"]["sha256"],
        "replay_activity_sha256":sha(RESULT/"replay/independent_activity_validation.json"),
        "proposal_budget":cfg["c2_max_proposals_if_active"],"optimizer_config":c1_solver,
        "no_new_vlm_call":True,"gt_access_before_final_C2_lock":False,
        "formal_holdout_access":False,"manual_intervention":0}
    save(target,record)
    print(json.dumps({"status":"FORMAL_C2_FROZEN","budget":record["proposal_budget"],
        "kfde_replay_rejection_rate":activity["rejection_rate"],"gt_access":False}))


if __name__=="__main__":main()
