"""Post-preflight freeze of the five-call closed-set reliability protocol."""

from __future__ import annotations

import json
import subprocess
import tomllib
from datetime import datetime,timezone

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha,audit_functional_authority,validate_registry
from experiments.try6.scripts.r1_v2_projection import project
from experiments.try6.scripts.r1_v3_contract import validate_slot_registry
from experiments.try6.scripts.run_r1_reliability import save

RESULT=HERE/"results/try6_0_r1_v3"


def main():
    cfg=load(HERE/"protocol/r1_v3_protocol.json")
    pre=load(RESULT/"preflight/report.json")
    if pre["preflight_pass"] is not True or pre["http_status"]!=200 or pre["raw_transport_valid"] is not True:
        raise RuntimeError("production preflight not passed")
    target=RESULT/"reliability_freeze.json"
    if target.exists():raise FileExistsError("R1-v3 reliability already frozen")
    canonical=load(ROOT/cfg["canonical_slot_schema"])
    api,removed=project(canonical,load(ROOT/cfg["projection_rules"]))
    if api!=load(RESULT/"schema/api_transport_schema.json"):raise RuntimeError("schema projection drift")
    inputs=load(ROOT/cfg["source_input_manifest"])["inputs"]
    source_files={}
    for key in ("engineering_text","sanitized_urdf","f0_fcstd","frozen_interface_contracts"):
        item=inputs[key]
        if sha(ROOT/item["path"])!=item["sha256"]:raise RuntimeError(f"input drift: {key}")
        source_files[key]=item
    images=[]
    for view,item in inputs["images"].items():
        if sha(ROOT/item["path"])!=item["sha256"]:raise RuntimeError(f"image drift: {view}")
        images.append({"view":view,**item})
    for view in ("front","isometric","left","right","top","rear"):
        path=ROOT/cfg["f0_render_directory"]/f"{view}.png"
        images.append({"view":"f0_"+view,"path":str(path.relative_to(ROOT)).replace("\\","/"),"sha256":sha(path)})
    lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"]!=0:raise RuntimeError("holdout lock violated")
    local=tomllib.loads((ROOT/cfg["model_config"]).read_text(encoding="utf-8"))
    if local["generation"]["model"]!=cfg["requested_model"]:raise RuntimeError("model drift")
    keys=("slot_registry","canonical_slot_schema","projection_rules","canonical_kfdg_schema","prompt","functional_backbone","parameter_registry")
    hashes={key:sha(ROOT/cfg[key]) for key in keys}
    head=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    frozen={"schema_version":"robotcad_try6_r1_v3_reliability_freeze_v1",
        "timestamp_utc":datetime.now(timezone.utc).isoformat(),"implementation_commit_before_calls":head,
        "protocol_sha256":sha(HERE/"protocol/r1_v3_protocol.json"),"frozen_hashes":hashes,
        "api_schema_sha256":sha(RESULT/"schema/api_transport_schema.json"),
        "projection_removed_paths":[x["path"] for x in removed],
        "preflight_report_sha256":sha(RESULT/"preflight/report.json"),
        "source_files":source_files,"images":images,
        "model_requested":cfg["requested_model"],"api_base_url":local["provider"]["base_url"],
        "api_key_recorded":False,"temperature":cfg["temperature"],"top_p":cfg["top_p"],
        "seed":cfg["seed"],"max_output_tokens":cfg["max_output_tokens"],
        "timeout_seconds":cfg["timeout_seconds"],"sdk_retries":0,"technical_retries":0,
        "target_calls":cfg["reliability_calls"],
        "authority_audit":audit_functional_authority(),"parameter_registry_audit":validate_registry(),
        "slot_registry_audit":validate_slot_registry(),
        "holdout_lock":{"accessed":False,"evaluation_count":0},"gt_evaluations":0}
    save(target,frozen)
    print(json.dumps({"status":"RELIABILITY_FROZEN","target_calls":frozen["target_calls"],"image_count":len(images)}))


if __name__=="__main__":main()
