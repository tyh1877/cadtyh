"""Read-only provenance/governance preflight before the one formal C1-v2 slot call."""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from datetime import datetime,timezone

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha,audit_functional_authority,validate_registry
from experiments.try6.scripts.r1_v3_contract import validate_slot_registry
from experiments.try6.scripts.run_r1_reliability import save

RESULT=HERE/"results/try6_0_c1_v2"


def prior(name,path):
    folder=HERE/path;manifest=load(folder/"manifest.json")
    hashes=manifest.get("lightweight_result_sha256",manifest.get("result_file_sha256",{}))
    if not all(sha(folder/item)==digest for item,digest in hashes.items()):
        raise RuntimeError(f"frozen prior result drift: {name}")
    return {"manifest_sha256":sha(folder/"manifest.json"),"files_checked":len(hashes),"unchanged":True}


def main():
    cfg_path=HERE/"protocol/try6_0_c1_v2.json"
    cfg=load(cfg_path)
    target=RESULT/"pre_run_manifest.json"
    if target.exists():raise FileExistsError("formal C1-v2 pre-run already frozen")
    priors={name:prior(name,path) for name,path in (("c1_v1","results/try6_0_c1"),
        ("r0","results/try6_0_r0"),("r1_v1","results/try6_0_r1"),
        ("r1_v2","results/try6_0_r1_v2"),("r1_v3","results/try6_0_r1_v3"))}
    readiness=load(ROOT/cfg["r1_v3_readiness"])
    if readiness["decision"]!="READY_FOR_C1_V2":raise RuntimeError("R1-v3 readiness not PASS")
    evidence=load(RESULT/"visual_metric_evidence/evidence_audit.json")
    smoke=load(RESULT/"infrastructure_smoke.json")
    if not evidence["registration_gate_pass"] or not evidence["evidence_gate_pass"] or smoke["status"]!="PASS":
        raise RuntimeError("visual registration/evidence/objective smoke not ready")
    lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"]!=0:raise RuntimeError("holdout lock violated")
    source=load(ROOT/cfg["source_input_manifest"])["inputs"]
    input_hashes={}
    for name,item in source.items():
        if name=="images":
            input_hashes["images"]={view:{"path":v["path"],"sha256":v["sha256"]} for view,v in item.items()}
            for view,v in item.items():
                if sha(ROOT/v["path"])!=v["sha256"]:raise RuntimeError(f"input image drift: {view}")
        else:
            if sha(ROOT/item["path"])!=item["sha256"]:raise RuntimeError(f"input drift: {name}")
            input_hashes[name]=item
    local=tomllib.loads((ROOT/cfg["model_config"]).read_text(encoding="utf-8"))
    if (local["generation"]["model"],local["generation"]["temperature"],local["generation"]["top_p"],local["generation"]["max_retries"]) != (cfg["model"]["identifier"],cfg["model"]["temperature"],cfg["model"]["top_p"],cfg["model"]["sdk_retries"]):
        raise RuntimeError("model config drift")
    functional=audit_functional_authority();registry=validate_registry();slots=validate_slot_registry()
    frozen_keys=("slot_registry","slot_canonical_schema","slot_api_schema","slot_prompt",
        "functional_backbone","parameter_registry","kfdg_schema")
    method_hashes={key:sha(ROOT/cfg[key]) for key in frozen_keys}
    method_hashes["visual_objective_source"]=sha(HERE/"scripts/c1_v2_visual_objective.py")
    method_hashes["metric_solver_source"]=sha(HERE/"scripts/c1_v2_metric_solver.py")
    method_hashes["freecad_builder_source"]=sha(HERE/"scripts/freecad_c1_builder.py")
    evaluator_hashes={key:sha(ROOT/cfg["evaluation"][key]) for key in ("geometry_evaluator","mechanical_evaluator")}
    frozen_a2a=load(HERE/"../try5A/results/try5b1_a2a_three_link/manifest.json")
    if evaluator_hashes["geometry_evaluator"]!=frozen_a2a["geometry_evaluator_sha256"] or evaluator_hashes["mechanical_evaluator"]!=frozen_a2a["exact_evaluator_sha256"]:
        raise RuntimeError("C1-v2 evaluator differs from frozen C0 evaluator version")
    sdk=__import__("openai").__version__
    sys.path.insert(0,str(ROOT/"experiments/try5A/scripts"))
    from freecad_runtime import python_runtime
    freecad=subprocess.run([python_runtime(),"-c","import FreeCAD,json;print(json.dumps(FreeCAD.Version()))"],
        cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    commit=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    save(RESULT/"protocol.json",cfg)
    save(RESULT/"case_split.json",{"development_subjects":["L04"],"development_mechanical_configurations":96,
        "formal_holdout_case_count":32,"formal_holdout_lock_sha256":sha(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json"),
        "formal_holdout_ids_not_read":True,"accessed":False,"evaluation_count":0})
    save(RESULT/"condition_parity.json",{"comparison":"single new C1-v2 vs historical frozen Direct-Qwen C0",
        "c0_not_regenerated":True,"model_controlled_pair":False,
        "c0_source_path":cfg["frozen_c0_source"],"c0_source_sha256":sha(ROOT/cfg["frozen_c0_source"]),
        "no_gt_generator_access":True})
    save(RESULT/"holdout_evaluation_log.json",{"events":[],"followed_by_tuning":False,
        "accessed":False,"evaluation_count":0})
    pre={"schema_version":"robotcad_try6_c1_v2_pre_run_v1","status":"READY_FOR_ONE_FRESH_SLOT_CALL",
        "timestamp_utc":datetime.now(timezone.utc).isoformat(),"starting_commit":cfg["starting_commit"],
        "implementation_commit_before_call":commit,"protocol_sha256":sha(cfg_path),
        "prior_results":priors,"r1_v3_readiness_sha256":sha(ROOT/cfg["r1_v3_readiness"]),
        "input_hashes":input_hashes,"method_hashes":method_hashes,"evaluator_hashes":evaluator_hashes,
        "visual_metric_evidence_sha256":sha(RESULT/"visual_metric_evidence/visual_metric_evidence.json"),
        "view_registration_sha256":sha(RESULT/"visual_metric_evidence/view_registration_report.json"),
        "objective_smoke_sha256":sha(RESULT/"infrastructure_smoke.json"),
        "c0_frozen_source_sha256":sha(ROOT/cfg["frozen_c0_source"]),
        "model_identifier":cfg["model"]["identifier"],"api_base_url":local["provider"]["base_url"],
        "api_key_recorded":False,"sdk_version":sdk,"python_executable":sys.executable,
        "freecad_version":freecad,"functional_authority_audit":functional,
        "parameter_registry_audit":registry,"slot_registry_audit":slots,
        "holdout_lock":{"accessed":False,"evaluation_count":0},
        "gt_evaluations_before_formal_candidate":0,"one_fresh_slot_call_limit":1,
        "solver_budget":cfg["solver"],"primary_iou_gate":cfg["primary_iou_gate"]}
    save(target,pre)
    print(json.dumps({"status":pre["status"],"solver_max_evaluations":cfg["solver"]["max_candidate_evaluations"],
        "registration_gate":True,"evidence_gate":True,"holdout_accessed":False}))


if __name__=="__main__":main()
