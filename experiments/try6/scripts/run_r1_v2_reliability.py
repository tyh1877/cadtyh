"""Five frozen L04 VFP calls; transport and local semantic gates separate."""

from __future__ import annotations

import json
import sys
import time
import tomllib
from datetime import datetime, timezone

import httpx
import openai
from jsonschema import Draft202012Validator

from experiments.try6.scripts.r1_contract import ROOT, HERE, assemble, load, sha, validate_kfdg, validate_vfp
from experiments.try6.scripts.run_r1_reliability import data_url, save

RESULT = HERE / "results/try6_0_r1_v2"
ARTIFACT = HERE / "artifacts/try6_0_r1_v2/reliability"


def run():
    cfg = load(HERE / "protocol/r1_v2_protocol.json")
    frozen = load(RESULT / "reliability_freeze.json")
    if frozen["protocol_sha256"] != sha(HERE / "protocol/r1_v2_protocol.json"):
        raise RuntimeError("protocol drift after freeze")
    for name,digest in frozen["frozen_hashes"].items():
        if sha(ROOT / cfg[name]) != digest: raise RuntimeError(f"frozen {name} drift")
    for item in frozen["source_files"].values():
        if sha(ROOT/item["path"]) != item["sha256"]: raise RuntimeError("source input drift")
    for image in frozen["images"]:
        if sha(ROOT/image["path"]) != image["sha256"]: raise RuntimeError("image drift")
    if sha(RESULT / "schema_projection/api_transport_schema.json") != frozen["api_schema_sha256"]:
        raise RuntimeError("API schema drift")
    if sha(RESULT / "preflight/compatibility_report.json") != frozen["preflight_report_sha256"]:
        raise RuntimeError("preflight result drift")
    if load(RESULT / "preflight/compatibility_report.json")["preflight_pass"] is not True:
        raise RuntimeError("compatibility preflight not passed")
    lock = load(ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"] != 0: raise RuntimeError("holdout lock violated")
    api_schema = load(RESULT / "schema_projection/api_transport_schema.json")
    canonical_schema = load(ROOT / cfg["canonical_schema"])
    Draft202012Validator.check_schema(api_schema)
    Draft202012Validator.check_schema(canonical_schema)
    local = tomllib.loads((ROOT / cfg["model_config"]).read_text(encoding="utf-8"))
    if local["generation"]["model"] != cfg["requested_model"]: raise RuntimeError("model drift")
    prompt = (ROOT / cfg["prompt"]).read_text(encoding="utf-8")
    engineering = (ROOT / frozen["source_files"]["engineering_text"]["path"]).read_text(encoding="utf-8")
    content = [{"type":"text","text":"Engineering description for L04:\n"+engineering}]
    for image in frozen["images"]:
        content.append({"type":"text","text":"Evidence view: "+image["view"]})
        content.append({"type":"image_url","image_url":{"url":data_url(ROOT/image["path"])}})
    messages = [{"role":"system","content":prompt},{"role":"user","content":content}]
    response_format = {"type":"json_schema","json_schema":{"name":"try6_r1_v2_l04_vfp","strict":True,"schema":api_schema}}
    records = []
    for number in range(1,cfg["independent_reliability_calls"]+1):
        name = f"call_{number:02d}"
        folder = RESULT / "reliability" / name
        if folder.exists(): raise FileExistsError(f"{name} already attempted; no rerun")
        folder.mkdir(parents=True)
        save(folder/"attempt_started.json",{"timestamp_utc":datetime.now(timezone.utc).isoformat(),
            "call_number":number,"preflight_not_counted":True,"retry_count":0,"manual_intervention":0,
            "reliability_freeze_sha256":sha(RESULT/"reliability_freeze.json")})
        captured = {}
        def on_request(request):
            captured["request_bytes"] = request.content
            captured["request_json"] = json.loads(request.content)
        def on_response(response):
            response.read(); captured["http_status"] = response.status_code
            try: captured["http_json"] = response.json()
            except Exception: captured["http_text"] = response.text
        record = {"call_number":number,"status":"STARTED","transport_valid":False,"semantic_valid":False,
            "assembly_success":False,"canonical_kfdg_valid":False,"response_repair_count":0,
            "retry_count":0,"manual_intervention":0}
        tick = time.perf_counter()
        try:
            with httpx.Client(timeout=cfg["timeout_seconds"],event_hooks={"request":[on_request],"response":[on_response]}) as transport:
                client = openai.OpenAI(api_key=local["provider"]["api_key"],base_url=local["provider"]["base_url"],
                    timeout=cfg["timeout_seconds"],max_retries=0,http_client=transport)
                response = client.chat.completions.create(model=cfg["requested_model"],messages=messages,
                    response_format=response_format,temperature=cfg["temperature"],top_p=cfg["top_p"],
                    max_tokens=cfg["max_output_tokens"],seed=cfg["seed"])
            sdk = response.model_dump(mode="json")
            save(folder/"sdk_response.json",sdk)
            record.update({"model_returned":sdk.get("model"),"response_id":sdk.get("id"),
                           "system_fingerprint":sdk.get("system_fingerprint"),"token_usage":sdk.get("usage")})
            raw = captured["http_json"]["choices"][0]["message"]["content"]
            if not isinstance(raw,str): raise ValueError("HTTP message content not string")
            (folder/"raw_response.txt").write_text(raw,encoding="utf-8")
            if raw != sdk["choices"][0]["message"]["content"]:
                raise ValueError("SDK/HTTP content mismatch")
            sent = captured["request_json"]["response_format"]["json_schema"]
            if sent["schema"] != api_schema or sent["strict"] is not True:
                raise ValueError("frozen API schema not actually sent")
            parsed = json.loads(raw)
            Draft202012Validator(api_schema).validate(parsed)
            record["transport_valid"] = True
            Draft202012Validator(canonical_schema).validate(parsed)
            checked = validate_vfp(parsed)
            record["semantic_valid"] = True
            save(folder/"validated_vfp.json",checked)
            graph = assemble(checked)
            record["assembly_success"] = True
            validate_kfdg(graph,checked)
            record["canonical_kfdg_valid"] = True
            save(RESULT/"canonical_kfdg"/f"{name}.json",graph)
            record["status"] = "PASS"
        except Exception as error:
            record["status"] = "FAIL"
            record["failure_stage"] = ("API_OR_TRANSPORT" if not record["transport_valid"] else
                                       "LOCAL_SEMANTIC" if not record["semantic_valid"] else
                                       "ASSEMBLY" if not record["assembly_success"] else "KFDG_VALIDATION")
            record["error"] = f"{type(error).__name__}: {error}"
        finally:
            record["latency_seconds"] = time.perf_counter()-tick
            record["http_status"] = captured.get("http_status")
            if "request_bytes" in captured:
                exact = ARTIFACT/name/"request_payload.json"
                exact.parent.mkdir(parents=True,exist_ok=True)
                exact.write_bytes(captured["request_bytes"])
                record["exact_request_path"] = str(exact.relative_to(ROOT)).replace("\\","/")
                record["exact_request_sha256"] = sha(exact)
                sent = captured["request_json"]
                save(folder/"request_metadata.json",{"exact_request_path":record["exact_request_path"],
                    "exact_request_sha256":record["exact_request_sha256"],
                    "model":sent.get("model"),"seed":sent.get("seed"),"temperature":sent.get("temperature"),
                    "top_p":sent.get("top_p"),"max_tokens":sent.get("max_tokens"),
                    "response_format":sent.get("response_format"),
                    "prompt_sha256":sha(ROOT/cfg["prompt"]),
                    "image_hashes":{item["view"]:item["sha256"] for item in frozen["images"]}})
            if "http_json" in captured: save(folder/"http_response.json",captured["http_json"])
            elif "http_text" in captured: (folder/"http_response.txt").write_text(captured["http_text"],encoding="utf-8")
            save(folder/"call_result.json",record)
            records.append(record)
    save(RESULT/"reliability/runner_attempts.json",{"requested":cfg["independent_reliability_calls"],
        "completed":len(records),"preflight_excluded":True,
        "attempt_ids":[f"call_{i:02d}" for i in range(1,len(records)+1)],
        "gt_evaluations":0,"formal_holdout_evaluations":0})
    print(json.dumps({"requested":cfg["independent_reliability_calls"],"completed":len(records),
        "transport_valid":sum(x["transport_valid"] for x in records),
        "semantic_valid":sum(x["semantic_valid"] for x in records),
        "canonical_valid":sum(x["canonical_kfdg_valid"] for x in records)}))


if __name__ == "__main__": run()
