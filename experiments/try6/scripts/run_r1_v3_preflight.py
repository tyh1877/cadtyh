"""One endpoint acceptance test for the frozen closed-set slot transport schema."""

from __future__ import annotations

import base64
import json
import sys
import time
import tomllib
from datetime import datetime, timezone

import httpx
import openai
from jsonschema import Draft202012Validator

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha,audit_functional_authority,validate_registry
from experiments.try6.scripts.r1_v2_projection import project
from experiments.try6.scripts.r1_v3_contract import validate_slot_registry
from experiments.try6.scripts.run_r1_reliability import save

RESULT=HERE/"results/try6_0_r1_v3"
ARTIFACT=HERE/"artifacts/try6_0_r1_v3/preflight"


def frozen_result(path):
    folder=HERE/path;manifest=load(folder/"manifest.json")
    hashes=manifest.get("lightweight_result_sha256",manifest.get("result_file_sha256",{}))
    if not all(sha(folder/p)==expected for p,expected in hashes.items()):
        raise RuntimeError(f"frozen result drift: {path}")
    return {"manifest_sha256":sha(folder/"manifest.json"),"files_checked":len(hashes),"unchanged":True}


def run():
    cfg=load(HERE/"protocol/r1_v3_protocol.json")
    folder=RESULT/"preflight"
    if folder.exists():raise FileExistsError("R1-v3 production preflight already attempted")
    canonical=load(ROOT/cfg["canonical_slot_schema"])
    api=load(RESULT/"schema/api_transport_schema.json")
    projected,removed=project(canonical,load(ROOT/cfg["projection_rules"]))
    if api!=projected:raise RuntimeError("schema projection drift")
    prior={name:frozen_result(path) for name,path in (("c1_v1","results/try6_0_c1"),
        ("r0","results/try6_0_r0"),("r1_v1","results/try6_0_r1"),
        ("r1_v2","results/try6_0_r1_v2"))}
    lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"]!=0:raise RuntimeError("holdout lock violated")
    authority=audit_functional_authority();registry=validate_registry();slots=validate_slot_registry()
    inputs=load(ROOT/cfg["source_input_manifest"])["inputs"]
    engineering=inputs["engineering_text"]
    image=inputs["images"]["isometric"]
    if sha(ROOT/engineering["path"])!=engineering["sha256"] or sha(ROOT/image["path"])!=image["sha256"]:
        raise RuntimeError("preflight raw input drift")
    local=tomllib.loads((ROOT/cfg["model_config"]).read_text(encoding="utf-8"))
    if local["generation"]["model"]!=cfg["requested_model"]:raise RuntimeError("model mismatch")
    prompt=(ROOT/cfg["prompt"]).read_text(encoding="utf-8")
    text=(ROOT/engineering["path"]).read_text(encoding="utf-8")
    data="data:image/png;base64,"+base64.b64encode((ROOT/image["path"]).read_bytes()).decode("ascii")
    messages=[{"role":"system","content":prompt},{"role":"user","content":[
        {"type":"text","text":"Closed-set production-schema compatibility preflight only. L04 engineering description:\n"+text},
        {"type":"text","text":"Evidence view: isometric"},
        {"type":"image_url","image_url":{"url":data}}]}]
    folder.mkdir(parents=True)
    save(folder/"attempt_started.json",{"timestamp_utc":datetime.now(timezone.utc).isoformat(),
        "purpose":"SCHEMA_COMPATIBILITY_ONLY_NOT_RELIABILITY_SAMPLE","attempt_limit":1,"retry_count":0,
        "canonical_schema_sha256":sha(ROOT/cfg["canonical_slot_schema"]),
        "api_schema_sha256":sha(RESULT/"schema/api_transport_schema.json")})
    captured={}
    def on_request(req):captured.update(request_bytes=req.content,request_json=json.loads(req.content))
    def on_response(resp):
        resp.read();captured["http_status"]=resp.status_code
        try:captured["http_json"]=resp.json()
        except Exception:captured["http_text"]=resp.text
    outcome={"schema_version":"robotcad_try6_r1_v3_preflight_report_v1", "preflight_pass":False,
        "api_schema_accepted":False,"raw_transport_valid":False,"reliability_sample":False,
        "retry_count":0,"model_requested":cfg["requested_model"],"prior_results":prior,
        "authority_audit":authority,"parameter_registry_audit":registry,"slot_registry_audit":slots,
        "gt_evaluations":0,"formal_holdout_evaluations":0}
    tick=time.perf_counter()
    try:
        with httpx.Client(timeout=cfg["timeout_seconds"],event_hooks={"request":[on_request],"response":[on_response]}) as transport:
            client=openai.OpenAI(api_key=local["provider"]["api_key"],base_url=local["provider"]["base_url"],
                timeout=cfg["timeout_seconds"],max_retries=0,http_client=transport)
            response=client.chat.completions.create(model=cfg["requested_model"],messages=messages,
                response_format={"type":"json_schema","json_schema":{"name":"try6_r1_v3_slots_preflight","strict":True,"schema":api}},
                temperature=cfg["temperature"],top_p=cfg["top_p"],max_tokens=cfg["max_output_tokens"],seed=cfg["seed"])
        sdk=response.model_dump(mode="json");save(folder/"sdk_response.json",sdk)
        outcome["api_schema_accepted"]=True
        outcome["model_returned"]=sdk.get("model")
        outcome["token_usage"]=sdk.get("usage")
        raw=captured["http_json"]["choices"][0]["message"]["content"]
        if not isinstance(raw,str):raise ValueError("HTTP message content not string")
        (folder/"raw_response.txt").write_text(raw,encoding="utf-8")
        if raw!=sdk["choices"][0]["message"]["content"]:raise ValueError("HTTP/SDK raw mismatch")
        Draft202012Validator(api).validate(json.loads(raw))
        outcome["raw_transport_valid"]=True
        outcome["preflight_pass"]=True
    except Exception as error:outcome["error"]=f"{type(error).__name__}: {error}"
    finally:
        outcome["latency_seconds"]=time.perf_counter()-tick
        outcome["http_status"]=captured.get("http_status")
        if "request_bytes" in captured:
            ARTIFACT.mkdir(parents=True,exist_ok=True)
            exact=ARTIFACT/"request_payload.json";exact.write_bytes(captured["request_bytes"])
            outcome["exact_request_path"]=str(exact.relative_to(ROOT)).replace("\\","/")
            outcome["exact_request_sha256"]=sha(exact)
            sent=captured["request_json"]
            outcome["schema_actually_sent"]=sent["response_format"]["json_schema"]["schema"]==api and sent["response_format"]["json_schema"]["strict"] is True
            save(folder/"request_metadata.json",{"exact_request_path":outcome["exact_request_path"],
                "exact_request_sha256":outcome["exact_request_sha256"],"response_format":sent["response_format"],
                "model":sent["model"],"seed":sent["seed"],"temperature":sent["temperature"],
                "top_p":sent["top_p"],"max_tokens":sent["max_tokens"],
                "prompt_sha256":sha(ROOT/cfg["prompt"]),"image_sha256":image["sha256"],
                "engineering_text_sha256":engineering["sha256"]})
        if "http_json" in captured:save(folder/"http_response.json",captured["http_json"])
        elif "http_text" in captured:(folder/"http_response.txt").write_text(captured["http_text"],encoding="utf-8")
        if not outcome.get("schema_actually_sent",False):outcome["preflight_pass"]=False
        save(folder/"report.json",outcome)
    print(json.dumps({"preflight_pass":outcome["preflight_pass"],"http_status":outcome.get("http_status"),
        "raw_transport_valid":outcome["raw_transport_valid"]}))
    return outcome["preflight_pass"]


if __name__=="__main__":sys.exit(0 if run() else 2)
