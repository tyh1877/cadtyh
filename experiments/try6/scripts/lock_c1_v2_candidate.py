"""Build selected visual-theta CAD and freeze candidate before any GT evaluator."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime,timezone

from experiments.try6.scripts.r1_contract import ROOT,HERE,canonical,load,sha
from experiments.try6.scripts.r1_v3_contract import validate_kfdg
from experiments.try6.scripts.run_r1_reliability import save

sys.path.insert(0,str(ROOT/"experiments/try5A/scripts"))
from freecad_runtime import python_runtime

RESULT=HERE/"results/try6_0_c1_v2"
ARTIFACT=HERE/"artifacts/try6_0_c1_v2/cad"


def lock():
    cfg=load(HERE/"protocol/try6_0_c1_v2.json")
    target=RESULT/"evaluation/final_candidate_lock.json"
    if target.exists():raise FileExistsError("final C1-v2 candidate already locked; no rerun")
    selected=load(RESULT/"solver/theta_selected.json")
    if selected["status"]!="SELECTED_BY_VISUAL_OBJECTIVE_ONLY" or selected["gt_accessed"] or selected["mechanical_feedback"]:
        raise RuntimeError("solver selection not visual-only")
    graph_path=RESULT/"kfdg/canonical_kfdg.json"
    graph=load(graph_path);validate_kfdg(graph)
    slot=load(RESULT/"slot/validation.json")
    if slot["status"]!="PASS":raise RuntimeError("slot gate failed")
    audit=load(RESULT/"visual_metric_evidence/evidence_audit.json")
    if not audit["registration_gate_pass"] or not audit["evidence_gate_pass"]:raise RuntimeError("evidence/registration gate failed")
    if ARTIFACT.exists():raise FileExistsError("final CAD build already attempted; no rerun")
    ARTIFACT.mkdir(parents=True)
    theta=selected["theta_star"]
    job={"mode":"C1_V2_ONE_FINAL_VISUAL_SELECTED_CAD","parameters":theta,
        "anchor_distance_mm":graph["metric_anchor"]["distance_mm"],
        "kfdg_path":str(graph_path),
        "frozen_interface_contracts":str(ROOT/"experiments/try5A/results/try5a5/motion_interface_contracts.json"),
        "f0_fcstd":str(ROOT/"experiments/try5A/artifacts/try5a5/round3_verified/links/L04/model.FCStd"),
        "output_root":str(ARTIFACT)}
    job_path=ARTIFACT/"job.json";save(job_path,job)
    started=time.perf_counter()
    proc=subprocess.run([python_runtime(),str(HERE/"scripts/freecad_c1_builder.py"),str(job_path)],
        cwd=ROOT,capture_output=True,text=True,timeout=180)
    (ARTIFACT/"stdout.txt").write_text(proc.stdout,encoding="utf-8")
    (ARTIFACT/"stderr.txt").write_text(proc.stderr,encoding="utf-8")
    if proc.returncode:raise RuntimeError(f"final CAD build failed: {proc.stderr[-1200:]}")
    built=load(ARTIFACT/"build_result.json")
    if built["final_solid_count"]!=1 or not built["reopen"]["valid"] or not all(x["valid"] for x in built["feature_tree"]):
        raise RuntimeError("final CAD solid/recompute/reopen gate failed")
    sig_job=ARTIFACT/"signature_job.json"
    save(sig_job,{"fcstd":str(ARTIFACT/"final.FCStd"),"output":str(ARTIFACT/"signature")})
    sigproc=subprocess.run([python_runtime(),str(HERE/"scripts/freecad_r1_v3_signature.py"),str(sig_job)],
        cwd=ROOT,capture_output=True,text=True,timeout=120)
    (ARTIFACT/"signature_stdout.txt").write_text(sigproc.stdout,encoding="utf-8")
    (ARTIFACT/"signature_stderr.txt").write_text(sigproc.stderr,encoding="utf-8")
    if sigproc.returncode:raise RuntimeError(f"final CAD signature failed: {sigproc.stderr[-1000:]}")
    signature=load(ARTIFACT/"signature/signature.json")
    if not signature["valid"] or abs(signature["parameter_table_housing_width_mm"]-theta["housing_width_mm"])>1e-6:
        raise RuntimeError("final CAD parameter binding invalid")
    reference=load(HERE/"results/try6_0_r1_v3/e2e_smoke/export_reopen.json")["protected_shape_signatures"]["0"]
    protected=("FrozenProximalBoreTool","FrozenMatingEnvelopeTool","FrozenScaffold")
    invariant=all(signature["shapes"][name]==reference[name] for name in protected)
    if not invariant:raise RuntimeError("final CAD frozen interface BREP drift")
    mapping=load(ARTIFACT/"feature_mapping.json")
    active=load(RESULT/"kfdg/active_parameters.json")
    if mapping["parameter_binding"]["values"]!=theta:raise RuntimeError("KFDG/theta/CAD parameter table mismatch")
    if any(pid not in theta for pid in active["active_ids"]):raise RuntimeError("active parameter not bound")
    save(RESULT/"cad/feature_mapping.json",mapping)
    save(RESULT/"cad/parameter_table.json",{"theta_star":theta,"active_parameters":active["active_ids"],
        "frozen_parameters":active["frozen_ids"],"sheet":"ParameterTable",
        "final_cad_path":str((ARTIFACT/"final.FCStd").relative_to(ROOT)).replace("\\","/")})
    save(RESULT/"cad/export_reopen.json",{"status":"PASS","build_runtime_seconds":time.perf_counter()-started,
        "final_solid_count":built["final_solid_count"],"feature_tree":built["feature_tree"],
        "reopen":built["reopen"],"interface_invariant":invariant,
        "protected_shape_signatures":{name:signature["shapes"][name] for name in protected},
        "artifacts":{name:{"path":str((ARTIFACT/name).relative_to(ROOT)).replace("\\","/"),"sha256":sha(ARTIFACT/name)}
            for name in ("final.FCStd","final.step","final.stl","body_only.stl")},
        "gt_accessed":False})
    lock_record={"schema_version":"robotcad_try6_c1_v2_final_candidate_lock_v1",
        "timestamp_utc":datetime.now(timezone.utc).isoformat(),"link_id":"L04",
        "selected_candidate_id":selected["selected_candidate_id"],
        "theta_star":theta,"theta_sha256":hashlib.sha256(canonical(theta).encode("utf-8")).hexdigest(),
        "slot_statuses":slot["slot_statuses"],
        "raw_slot_response_sha256":sha(RESULT/"slot/raw_response.txt"),
        "kfdg_sha256":sha(graph_path),
        "view_registration_sha256":sha(RESULT/"visual_metric_evidence/view_registration_report.json"),
        "visual_evidence_sha256":sha(RESULT/"visual_metric_evidence/visual_metric_evidence.json"),
        "objective_definition_sha256":sha(RESULT/"solver/objective_definition.json"),
        "solver_config_sha256":sha(RESULT/"solver/config.json"),
        "solver_history_sha256":sha(RESULT/"solver/candidate_history.json"),
        "theta_selection_sha256":sha(RESULT/"solver/theta_selected.json"),
        "final_cad_artifacts":load(RESULT/"cad/export_reopen.json")["artifacts"],
        "connected_solid_count":1,"interface_invariant":True,
        "gt_evaluation_count_at_lock":0,"formal_holdout_accessed_at_lock":False,
        "selection_used_only_visual_objective":True}
    save(target,lock_record)
    print(json.dumps({"status":"FINAL_CANDIDATE_LOCKED_BEFORE_GT","candidate":selected["selected_candidate_id"],
        "connected_solids":1,"interface_invariant":True,"gt_evaluations":0}))
    return lock_record


if __name__=="__main__":lock()
