"""One fresh formal C1-v2 slot call; fail closed before solver on any error."""

from __future__ import annotations

import json
import sys
import time
import tomllib
from datetime import datetime,timezone

import httpx
import openai
from jsonschema import Draft202012Validator

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try6.scripts.r1_v3_contract import assemble,validate_kfdg,validate_slots
from experiments.try6.scripts.run_r1_reliability import data_url,save

RESULT=HERE/"results/try6_0_c1_v2"
ARTIFACT=HERE/"artifacts/try6_0_c1_v2/slot"


def run():
    cfg=load(HERE/"protocol/try6_0_c1_v2.json")
    audit=load(RESULT/"visual_metric_evidence/evidence_audit.json")
    if audit["registration_gate_pass"] is not True or audit["evidence_gate_pass"] is not True:
        raise RuntimeError("view/evidence gate not passed")
    if load(ROOT/cfg["r1_v3_readiness"])["decision"]!="READY_FOR_C1_V2":
        raise RuntimeError("R1-v3 readiness not frozen PASS")
    source=load(ROOT/cfg["source_input_manifest"])["inputs"]
    lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"]!=0:raise RuntimeError("holdout lock violated")
    local=tomllib.loads((ROOT/cfg["model_config"]).read_text(encoding="utf-8"))
    if local["generation"]["model"]!=cfg["model"]["identifier"]:raise RuntimeError("model config drift")
    folder=RESULT/"slot"
    if folder.exists():raise FileExistsError("formal C1-v2 slot call already attempted; no rerun")
    folder.mkdir(parents=True)
    save(folder/"attempt_started.json",{"timestamp_utc":datetime.now(timezone.utc).isoformat(),
        "fresh_formal_call":True,"max_calls":1,"technical_retries":0,"manual_intervention":0,
        "protocol_sha256":sha(HERE/"protocol/try6_0_c1_v2.json")})
    prompt=(ROOT/cfg["slot_prompt"]).read_text(encoding="utf-8")
    engineering=(ROOT/source["engineering_text"]["path"]).read_text(encoding="utf-8")
    content=[{"type":"text","text":"Engineering description for L04:\n"+engineering}]
    images=[]
    for view,item in source["images"].items():images.append({"view":view,**item})
    for view in ("front","isometric","left","right","top","rear"):
        path=ROOT/"experiments/try6/artifacts/try6_0_c1/vlm_inputs/renders"/f"{view}.png"
        images.append({"view":"f0_"+view,"path":str(path.relative_to(ROOT)).replace("\\","/"),"sha256":sha(path)})
    for image in images:
        if sha(ROOT/image["path"])!=image["sha256"]:raise RuntimeError("image input drift")
        content.extend([{"type":"text","text":"Evidence view: "+image["view"]},
            {"type":"image_url","image_url":{"url":data_url(ROOT/image["path"])}}])
    messages=[{"role":"system","content":prompt},{"role":"user","content":content}]
    api=load(ROOT/cfg["slot_api_schema"])
    canonical=load(ROOT/cfg["slot_canonical_schema"])
    captured={}
    def on_request(req):captured.update(request_bytes=req.content,request_json=json.loads(req.content))
    def on_response(resp):
        resp.read();captured["http_status"]=resp.status_code
        try:captured["http_json"]=resp.json()
        except Exception:captured["http_text"]=resp.text
    status={"status":"STARTED","fresh_calls":0,"transport_valid":False,"contract_valid":False,
        "kfdg_valid":False,"retry_count":0,"manual_intervention":0,"gt_accessed":False,"formal_holdout_accessed":False}
    tick=time.perf_counter()
    try:
        with httpx.Client(timeout=cfg["model"]["timeout_seconds"],event_hooks={"request":[on_request],"response":[on_response]}) as transport:
            client=openai.OpenAI(api_key=local["provider"]["api_key"],base_url=local["provider"]["base_url"],
                timeout=cfg["model"]["timeout_seconds"],max_retries=0,http_client=transport)
            response=client.chat.completions.create(model=cfg["model"]["identifier"],messages=messages,
                response_format={"type":"json_schema","json_schema":{"name":"try6_c1_v2_l04_slots","strict":True,"schema":api}},
                temperature=cfg["model"]["temperature"],top_p=cfg["model"]["top_p"],
                max_tokens=cfg["model"]["max_output_tokens"],seed=cfg["model"]["seed"])
        sdk=response.model_dump(mode="json");save(folder/"response.json",sdk)
        raw=captured["http_json"]["choices"][0]["message"]["content"]
        if not isinstance(raw,str):raise RuntimeError("HTTP message content not string")
        (folder/"raw_response.txt").write_text(raw,encoding="utf-8")
        status["fresh_calls"]=1
        status["model_returned"]=sdk.get("model")
        status["token_usage"]=sdk.get("usage")
        if raw!=sdk["choices"][0]["message"]["content"]:raise RuntimeError("HTTP/SDK raw mismatch")
        if captured["request_json"]["response_format"]["json_schema"]["schema"]!=api:
            raise RuntimeError("frozen slot API schema not sent")
        parsed=json.loads(raw)
        Draft202012Validator(api).validate(parsed);status["transport_valid"]=True
        Draft202012Validator(canonical).validate(parsed)
        decisions=validate_slots(parsed);status["contract_valid"]=True
        graph=assemble(decisions);validate_kfdg(graph,decisions);status["kfdg_valid"]=True
        save(folder/"validated_slots.json",decisions)
        save(RESULT/"kfdg/canonical_kfdg.json",graph)
        active_ids=[pid for pid in cfg["active_parameter_rule"]["base"]
            if next(p for p in graph["parameters"] if p["id"]==pid)["active"]]
        if next(s for s in decisions["slots"] if s["slot_id"]=="visible_pocket")["status"]=="PRESENT":
            active_ids += [pid for pid in cfg["active_parameter_rule"]["if_visible_pocket_present_add"]
                if next(p for p in graph["parameters"] if p["id"]==pid)["active"]]
        if len(active_ids)<2:raise RuntimeError("insufficient observable active parameters")
        frozen_ids=[p["id"] for p in graph["parameters"] if p["id"] not in active_ids]
        save(RESULT/"kfdg/active_parameters.json",{"active_ids":active_ids,"frozen_ids":frozen_ids,
            "active_bounds":{p["id"]:[p["lower_bound"],p["upper_bound"]] for p in graph["parameters"] if p["id"] in active_ids},
            "initial_theta":{p["id"]:p["value"] for p in graph["parameters"]},
            "rule_source":"protocol/try6_0_c1_v2.json:active_parameter_rule",
            "slot_statuses":{x["slot_id"]:x["status"] for x in decisions["slots"]}})
        status["status"]="PASS"
        status["slot_statuses"]={x["slot_id"]:x["status"] for x in decisions["slots"]}
        status["active_parameters"]=active_ids
    except Exception as error:
        status["status"]="REPRESENTATION_FAILURE"
        status["error"]=f"{type(error).__name__}: {error}"
    finally:
        status["latency_seconds"]=time.perf_counter()-tick
        status["http_status"]=captured.get("http_status")
        if "request_bytes" in captured:
            ARTIFACT.mkdir(parents=True,exist_ok=True)
            exact=ARTIFACT/"request_payload.json";exact.write_bytes(captured["request_bytes"])
            save(folder/"request.json",{"exact_request_path":str(exact.relative_to(ROOT)).replace("\\","/"),
                "exact_request_sha256":sha(exact),"response_format":captured["request_json"].get("response_format"),
                "prompt_sha256":sha(ROOT/cfg["slot_prompt"]),"image_hashes":{x["view"]:x["sha256"] for x in images},
                "engineering_text_sha256":source["engineering_text"]["sha256"]})
        if "http_json" in captured:save(folder/"http_response.json",captured["http_json"])
        elif "http_text" in captured:(folder/"http_response.txt").write_text(captured["http_text"],encoding="utf-8")
        save(folder/"validation.json",status)
    print(json.dumps({"status":status["status"],"slot_statuses":status.get("slot_statuses"),
        "active_parameters":status.get("active_parameters"),"error":status.get("error")}))
    return status["status"]=="PASS"


if __name__=="__main__":sys.exit(0 if run() else 2)
