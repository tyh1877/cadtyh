"""Freeze all R1-v2 reliability inputs after compatibility preflight passes."""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from experiments.try6.scripts.r1_contract import ROOT, HERE, audit_functional_authority, load, sha, validate_registry
from experiments.try6.scripts.r1_v2_projection import project

RESULT = HERE / "results/try6_0_r1_v2"


def save(path,obj):
    path = Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")


def main():
    cfg = load(HERE / "protocol/r1_v2_protocol.json")
    preflight = load(RESULT / "preflight/compatibility_report.json")
    if preflight["preflight_pass"] is not True or preflight["api_schema_accepted"] is not True or preflight["schema_actually_sent"] is not True:
        raise RuntimeError("production schema compatibility preflight did not pass")
    target = RESULT / "reliability_freeze.json"
    if target.exists(): raise FileExistsError("reliability already frozen")
    canonical = load(ROOT / cfg["canonical_schema"])
    rules = load(ROOT / cfg["projection_rules"])
    api,removed = project(canonical,rules)
    if api != load(RESULT / "schema_projection/api_transport_schema.json"):
        raise RuntimeError("projection changed after preflight")
    images = []
    old = load(ROOT / cfg["source_input_manifest"])["inputs"]
    source_files = {}
    for name in ("engineering_text","sanitized_urdf","f0_fcstd","frozen_interface_contracts"):
        item = old[name]
        if sha(ROOT / item["path"]) != item["sha256"]: raise RuntimeError(f"input drift: {name}")
        source_files[name] = item
    for view,item in old["images"].items():
        if sha(ROOT/item["path"]) != item["sha256"]: raise RuntimeError(f"raw image drift: {view}")
        images.append({"view":view,**item})
    for view in ("front","isometric","left","right","top","rear"):
        path = ROOT / cfg["f0_render_directory"] / f"{view}.png"
        images.append({"view":"f0_"+view,"path":str(path.relative_to(ROOT)).replace("\\","/"),"sha256":sha(path)})
    authority = audit_functional_authority()
    registry = validate_registry()
    lock = load(ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"] != 0: raise RuntimeError("holdout lock violated")
    local = tomllib.loads((ROOT / cfg["model_config"]).read_text(encoding="utf-8"))
    if local["generation"]["model"] != cfg["requested_model"]: raise RuntimeError("model config drift")
    paths = ("canonical_schema","projection_rules","prompt","functional_backbone","parameter_registry","assembler_rules","canonical_kfdg_schema")
    hashes = {name:sha(ROOT / cfg[name]) for name in paths}
    head = subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    output = {"schema_version":"robotcad_try6_r1_v2_reliability_freeze_v1","timestamp_utc":datetime.now(timezone.utc).isoformat(),
        "implementation_commit_before_calls":head,"protocol_sha256":sha(HERE / "protocol/r1_v2_protocol.json"),
        "frozen_hashes":hashes,"api_schema_sha256":sha(RESULT / "schema_projection/api_transport_schema.json"),
        "projection_removed_paths":[item["path"] for item in removed],
        "preflight_report_sha256":sha(RESULT / "preflight/compatibility_report.json"),
        "source_files":source_files,"images":images,"model_requested":cfg["requested_model"],
        "api_base_url":local["provider"]["base_url"],"api_key_recorded":False,
        "temperature":cfg["temperature"],"top_p":cfg["top_p"],"seed":cfg["seed"],
        "max_output_tokens":cfg["max_output_tokens"],"timeout_seconds":cfg["timeout_seconds"],
        "sdk_retries":0,"technical_retries":0,"target_calls":cfg["independent_reliability_calls"],
        "authority_audit":authority,"registry_audit":registry,
        "holdout_lock":{"accessed":False,"evaluation_count":0},"gt_evaluations":0}
    save(target,output)
    print(json.dumps({"status":"RELIABILITY_FROZEN","target_calls":output["target_calls"],"image_count":len(images)}))


if __name__ == "__main__": main()
