"""One production-schema API compatibility attempt; never a reliability sample."""

from __future__ import annotations

import base64
import hashlib
import json
import sys
import time
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import httpx
import openai
from jsonschema import Draft202012Validator

from experiments.try6.scripts.r1_contract import ROOT, HERE, audit_functional_authority, load, sha, validate_registry
from experiments.try6.scripts.r1_v2_projection import project

RESULT = HERE / "results/try6_0_r1_v2"
ARTIFACT = HERE / "artifacts/try6_0_r1_v2/preflight"


def save(path,obj):
    path = Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")


def verify_prior(folder):
    manifest = load(folder / "manifest.json")
    hashes = manifest.get("lightweight_result_sha256",manifest.get("result_file_sha256",{}))
    if not all(sha(folder/name)==digest for name,digest in hashes.items()):
        raise RuntimeError(f"prior frozen result drift: {folder.name}")
    return {"manifest_sha256":sha(folder/"manifest.json"),"files_checked":len(hashes),"unchanged":True}


def run():
    cfg = load(HERE / "protocol/r1_v2_protocol.json")
    folder = RESULT / "preflight"
    if folder.exists(): raise FileExistsError("R1-v2 preflight already attempted; no rerun")
    report = load(RESULT / "schema_projection/projection_report.json")
    canonical = load(ROOT / cfg["canonical_schema"])
    rules = load(ROOT / cfg["projection_rules"])
    projected,removed = project(canonical,rules)
    api = load(RESULT / "schema_projection/api_transport_schema.json")
    if api != projected or report["removed"] != removed: raise RuntimeError("projection snapshot drift")
    lock = load(ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"] != 0: raise RuntimeError("holdout lock violated")
    prior = {name:verify_prior(HERE / path) for name,path in (("c1_v1","results/try6_0_c1"),("r0","results/try6_0_r0"),("r1_v1","results/try6_0_r1"))}
    authority = audit_functional_authority()
    registry = validate_registry()
    source = load(ROOT / cfg["source_input_manifest"])["inputs"]
    engineering_item = source["engineering_text"]
    if sha(ROOT / engineering_item["path"]) != engineering_item["sha256"]: raise RuntimeError("engineering input drift")
    image_item = source["images"]["isometric"]
    if sha(ROOT / image_item["path"]) != image_item["sha256"]: raise RuntimeError("image input drift")
    local = tomllib.loads((ROOT / cfg["model_config"]).read_text(encoding="utf-8"))
    if local["generation"]["model"] != cfg["requested_model"]: raise RuntimeError("model config drift")
    prompt = (ROOT / cfg["prompt"]).read_text(encoding="utf-8")
    engineering = (ROOT / engineering_item["path"]).read_text(encoding="utf-8")
    image_b64 = base64.b64encode((ROOT / image_item["path"]).read_bytes()).decode("ascii")
    messages = [{"role":"system","content":prompt},{"role":"user","content":[
        {"type":"text","text":"Production-schema compatibility preflight only. L04 engineering description:\n"+engineering},
        {"type":"text","text":"Evidence view: isometric"},
        {"type":"image_url","image_url":{"url":"data:image/png;base64,"+image_b64}}
    ]}]
    folder.mkdir(parents=True)
    save(folder/"attempt_started.json",{"timestamp_utc":datetime.now(timezone.utc).isoformat(),
        "purpose":"API_SCHEMA_COMPATIBILITY_ONLY_NOT_RELIABILITY_SAMPLE","attempt_limit":1,"retry_count":0,
        "canonical_schema_sha256":sha(ROOT/cfg["canonical_schema"]),
        "api_schema_sha256":sha(RESULT/"schema_projection/api_transport_schema.json")})
    captured = {}
    def on_request(request):
        captured["request_bytes"] = request.content
        captured["request_json"] = json.loads(request.content)
    def on_response(response):
        response.read(); captured["status"] = response.status_code
        try: captured["http_json"] = response.json()
        except Exception: captured["http_text"] = response.text
    started = time.perf_counter()
    outcome = {"schema_version":"robotcad_try6_r1_v2_compatibility_report_v1","purpose":"API_SCHEMA_COMPATIBILITY_ONLY",
        "preflight_pass":False,"api_schema_accepted":False,"retry_count":0,"reliability_sample":False,
        "model_requested":cfg["requested_model"],"api_schema_sha256":sha(RESULT/"schema_projection/api_transport_schema.json"),
        "canonical_schema_sha256":sha(ROOT/cfg["canonical_schema"]),"projection_removed_paths":[x["path"] for x in removed],
        "prior_results":prior,"functional_authority_audit":authority,"registry_audit":registry,
        "gt_evaluations":0,"formal_holdout_evaluations":0}
    try:
        with httpx.Client(timeout=cfg["timeout_seconds"],event_hooks={"request":[on_request],"response":[on_response]}) as transport:
            client = openai.OpenAI(api_key=local["provider"]["api_key"],base_url=local["provider"]["base_url"],
                timeout=cfg["timeout_seconds"],max_retries=0,http_client=transport)
            response = client.chat.completions.create(model=cfg["requested_model"],messages=messages,
                response_format={"type":"json_schema","json_schema":{"name":"try6_r1_v2_l04_vfp_preflight","strict":True,"schema":api}},
                temperature=cfg["temperature"],top_p=cfg["top_p"],max_tokens=cfg["max_output_tokens"],seed=cfg["seed"])
        sdk = response.model_dump(mode="json")
        save(folder/"sdk_response.json",sdk)
        outcome["api_schema_accepted"] = True
        outcome["model_returned"] = sdk.get("model")
        outcome["token_usage"] = sdk.get("usage")
        raw = captured["http_json"]["choices"][0]["message"]["content"]
        if isinstance(raw,str):
            (folder/"raw_model_response.txt").write_text(raw,encoding="utf-8")
            try:
                Draft202012Validator(api).validate(json.loads(raw))
                outcome["raw_transport_valid_diagnostic"] = True
            except Exception as error:
                outcome["raw_transport_valid_diagnostic"] = False
                outcome["raw_diagnostic_error"] = f"{type(error).__name__}: {error}"
        else: outcome["raw_transport_valid_diagnostic"] = False
        outcome["preflight_pass"] = True
    except Exception as error:
        outcome["error"] = f"{type(error).__name__}: {error}"
        outcome["http_status"] = captured.get("status")
        outcome["preflight_pass"] = False
    finally:
        outcome["latency_seconds"] = time.perf_counter()-started
        if "request_bytes" in captured:
            ARTIFACT.mkdir(parents=True,exist_ok=True)
            exact = ARTIFACT/"request_payload.json"; exact.write_bytes(captured["request_bytes"])
            outcome["exact_request_path"] = str(exact.relative_to(ROOT)).replace("\\","/")
            outcome["exact_request_sha256"] = sha(exact)
            sent = captured["request_json"]
            outcome["schema_actually_sent"] = sent["response_format"]["json_schema"]["schema"] == api and sent["response_format"]["json_schema"]["strict"] is True
            save(folder/"request_metadata.json",{"exact_request_path":outcome["exact_request_path"],
                "exact_request_sha256":outcome["exact_request_sha256"],"model":sent.get("model"),
                "response_format":sent.get("response_format"),"prompt_sha256":sha(ROOT/cfg["prompt"]),
                "engineering_text_sha256":engineering_item["sha256"],"image_sha256":image_item["sha256"],
                "seed":sent.get("seed"),"temperature":sent.get("temperature"),"top_p":sent.get("top_p"),
                "max_tokens":sent.get("max_tokens")})
        if "http_json" in captured: save(folder/"http_response.json",captured["http_json"])
        elif "http_text" in captured: (folder/"http_response.txt").write_text(captured["http_text"],encoding="utf-8")
        outcome["http_status"] = captured.get("status")
        if not outcome.get("schema_actually_sent",False): outcome["preflight_pass"] = False
        save(folder/"compatibility_report.json",outcome)
    print(json.dumps({"preflight_pass":outcome["preflight_pass"],"http_status":outcome.get("http_status"),
        "api_schema_accepted":outcome["api_schema_accepted"]}))
    return outcome["preflight_pass"]


if __name__ == "__main__": sys.exit(0 if run() else 2)
