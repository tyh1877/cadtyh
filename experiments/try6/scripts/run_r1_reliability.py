"""Frozen five-call L04 VFP reliability run. Every attempt is retained; no retry."""

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

from experiments.try6.scripts.r1_contract import ROOT, HERE, assemble, canonical, load, sha, validate_kfdg, validate_vfp

RESULT = HERE / "results/try6_0_r1"
ARTIFACT = HERE / "artifacts/try6_0_r1/reliability"


def save(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def data_url(path):
    return "data:image/png;base64," + base64.b64encode(Path(path).read_bytes()).decode("ascii")


def run():
    cfg = load(HERE / "protocol/r1_protocol.json")
    pre = load(RESULT / "preflight.json")
    if pre["protocol_sha256"] != sha(HERE / "protocol/r1_protocol.json"):
        raise RuntimeError("protocol changed after preflight")
    for key,expected in pre["frozen_hashes"].items():
        if sha(ROOT / cfg[key]) != expected: raise RuntimeError(f"frozen {key} changed")
    for image in pre["images"]:
        if sha(ROOT / image["path"]) != image["sha256"]: raise RuntimeError(f"image drift: {image['view']}")
    for item in pre["source_files"].values():
        if sha(ROOT / item["path"]) != item["sha256"]: raise RuntimeError(f"input drift: {item['path']}")
    lock = load(ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"] != 0: raise RuntimeError("holdout lock violated")
    local = tomllib.loads((ROOT / cfg["model_config"]).read_text(encoding="utf-8"))
    if local["generation"]["model"] != cfg["requested_model"]: raise RuntimeError("model drift")
    schema = load(ROOT / cfg["vfp_schema"])
    Draft202012Validator.check_schema(schema)
    prompt = (ROOT / cfg["prompt"]).read_text(encoding="utf-8")
    engineering = (ROOT / pre["source_files"]["engineering_text"]["path"]).read_text(encoding="utf-8")
    user_content = [{"type":"text","text":"Engineering description for L04:\n"+engineering}]
    for image in pre["images"]:
        user_content.append({"type":"text","text":"Evidence view: "+image["view"]})
        user_content.append({"type":"image_url","image_url":{"url":data_url(ROOT / image["path"])}})
    messages = [{"role":"system","content":prompt},{"role":"user","content":user_content}]
    schema_format = {"type":"json_schema","json_schema":{"name":"try6_r1_l04_vfp","strict":True,"schema":schema}}
    records = []
    for call_number in range(1,cfg["independent_calls"]+1):
        name = f"call_{call_number:02d}"
        folder = RESULT / "reliability" / name
        if folder.exists(): raise FileExistsError(f"{name} already attempted; no rerun")
        folder.mkdir(parents=True)
        save(folder / "attempt_started.json",{"timestamp_utc":datetime.now(timezone.utc).isoformat(),"call_number":call_number,
            "max_calls":cfg["independent_calls"],"retry_count":0,"manual_intervention":0,
            "prompt_sha256":pre["frozen_hashes"]["prompt"],"schema_sha256":pre["frozen_hashes"]["vfp_schema"]})
        captured = {}
        def request_hook(request):
            captured["request_bytes"] = request.content
            captured["request_json"] = json.loads(request.content)
        def response_hook(response):
            response.read(); captured["http_status"] = response.status_code
            try: captured["http_json"] = response.json()
            except Exception: captured["http_text"] = response.text
        tick = time.perf_counter()
        outcome = {"call_number":call_number,"status":"STARTED","raw_schema_valid":False,"semantic_valid":False,
                   "assembly_success":False,"canonical_kfdg_valid":False,"response_repaired":False,
                   "retry_count":0,"manual_intervention":0,"unsupported_feature_count":0,"duplicate_reference_count":0,"dangling_reference_count":0}
        try:
            with httpx.Client(timeout=cfg["timeout_seconds"], event_hooks={"request":[request_hook],"response":[response_hook]}) as transport:
                client = openai.OpenAI(api_key=local["provider"]["api_key"],base_url=local["provider"]["base_url"],timeout=cfg["timeout_seconds"],max_retries=0,http_client=transport)
                response = client.chat.completions.create(model=cfg["requested_model"],messages=messages,
                    response_format=schema_format,temperature=cfg["temperature"],top_p=cfg["top_p"],
                    max_tokens=cfg["max_output_tokens"],seed=cfg["seed"])
            sdk = response.model_dump(mode="json")
            save(folder / "sdk_response.json",sdk)
            if "http_json" in captured: save(folder / "http_response.json",captured["http_json"])
            raw_http = captured["http_json"]["choices"][0]["message"]["content"]
            raw_sdk = sdk["choices"][0]["message"]["content"]
            if not isinstance(raw_http,str): raise ValueError("HTTP content not string")
            (folder / "raw_response.txt").write_text(raw_http,encoding="utf-8")
            outcome.update({"model_returned":sdk.get("model"),"response_id":sdk.get("id"),"system_fingerprint":sdk.get("system_fingerprint"),
                            "token_usage":sdk.get("usage"),"http_status":captured.get("http_status")})
            if raw_http != raw_sdk: raise ValueError("SDK modified raw message content")
            if captured["request_json"]["response_format"]["json_schema"]["schema"] != schema or captured["request_json"]["response_format"]["json_schema"]["strict"] is not True:
                raise ValueError("actual HTTP request did not carry frozen strict schema")
            raw_obj = json.loads(raw_http)
            Draft202012Validator(schema).validate(raw_obj)
            outcome["raw_schema_valid"] = True
            vfp = validate_vfp(raw_obj)
            outcome["semantic_valid"] = True
            save(folder / "validated_vfp.json",vfp)
            graph = assemble(vfp)
            outcome["assembly_success"] = True
            save(RESULT / "canonical_kfdg" / f"{name}_kfdg.json",graph)
            validate_kfdg(graph,vfp)
            outcome["canonical_kfdg_valid"] = True
            outcome["status"] = "PASS"
        except Exception as error:
            outcome["status"] = "FAIL"
            outcome["failure_stage"] = ("RAW_SCHEMA" if not outcome["raw_schema_valid"] else "VFP_SEMANTIC" if not outcome["semantic_valid"] else "ASSEMBLY" if not outcome["assembly_success"] else "KFDG_VALIDATION")
            outcome["error"] = f"{type(error).__name__}: {error}"
            if "UNSUPPORTED" in outcome["error"] or "MISSING_OR_EXTRA_VISIBLE_FEATURE" in outcome["error"]:
                outcome["unsupported_feature_count"] = 1
            if "DUPLICATE_REFERENCE" in outcome["error"]: outcome["duplicate_reference_count"] = 1
            if "DANGLING" in outcome["error"]: outcome["dangling_reference_count"] = 1
        finally:
            outcome["latency_seconds"] = time.perf_counter()-tick
            if "request_bytes" in captured:
                exact = ARTIFACT / name / "request_payload.json"
                exact.parent.mkdir(parents=True,exist_ok=True)
                exact.write_bytes(captured["request_bytes"])
                outcome["exact_http_request_path"] = str(exact.relative_to(ROOT)).replace("\\","/")
                outcome["exact_http_request_sha256"] = sha(exact)
                save(folder / "request_metadata.json",{"exact_request_sha256":sha(exact),"response_format":captured["request_json"].get("response_format"),
                    "model":captured["request_json"].get("model"),"seed":captured["request_json"].get("seed"),
                    "image_hashes":{image["view"]:image["sha256"] for image in pre["images"]},
                    "prompt_sha256":sha(ROOT / cfg["prompt"]),"engineering_text_sha256":pre["source_files"]["engineering_text"]["sha256"]})
            if "http_json" in captured and not (folder / "http_response.json").exists(): save(folder / "http_response.json",captured["http_json"])
            save(folder / "call_result.json",outcome)
            records.append(outcome)
    save(RESULT / "reliability/runner_attempts.json",{"requested":cfg["independent_calls"],"completed":len(records),
        "calls":[{"call_number":x["call_number"],"status":x["status"],"failure_stage":x.get("failure_stage")} for x in records],
        "all_attempts_retained":len(records)==cfg["independent_calls"],"gt_evaluations":0,"formal_holdout_evaluations":0})
    print(json.dumps({"requested":cfg["independent_calls"],"completed":len(records),"pass_count":sum(x["status"]=="PASS" for x in records)}))


if __name__ == "__main__": run()
