"""Independent R1-v3 representation and perception audit; no GT or holdout cases."""

from __future__ import annotations

import base64
import hashlib
import json
import math
from collections import Counter
from datetime import datetime,timezone

from jsonschema import Draft202012Validator

from experiments.try6.scripts.r1_contract import ROOT,HERE,canonical,load,sha
from experiments.try6.scripts.r1_v2_projection import project
from experiments.try6.scripts.r1_v3_contract import assemble,registry,validate_kfdg,validate_slots
from experiments.try6.scripts.run_r1_reliability import save

RESULT=HERE/"results/try6_0_r1_v3"


def representation():
    cfg=load(HERE/"protocol/r1_v3_protocol.json")
    frozen=load(RESULT/"reliability_freeze.json")
    pre=load(RESULT/"preflight/report.json")
    if pre["preflight_pass"] is not True or sha(RESULT/"preflight/report.json")!=frozen["preflight_report_sha256"]:
        raise RuntimeError("preflight drift")
    if sha(HERE/"protocol/r1_v3_protocol.json")!=frozen["protocol_sha256"]:
        raise RuntimeError("protocol drift")
    for key,digest in frozen["frozen_hashes"].items():
        if sha(ROOT/cfg[key])!=digest:raise RuntimeError(f"frozen {key} drift")
    canonical_schema=load(ROOT/cfg["canonical_slot_schema"])
    api_schema=load(RESULT/"schema/api_transport_schema.json")
    projected,_=project(canonical_schema,load(ROOT/cfg["projection_rules"]))
    if api_schema!=projected or sha(RESULT/"schema/api_transport_schema.json")!=frozen["api_schema_sha256"]:
        raise RuntimeError("schema projection drift")
    for item in frozen["source_files"].values():
        if sha(ROOT/item["path"])!=item["sha256"]:raise RuntimeError("source input drift")
    for item in frozen["images"]:
        if sha(ROOT/item["path"])!=item["sha256"]:raise RuntimeError("image input drift")
    expected_images={item["view"]:item["sha256"] for item in frozen["images"]}
    records=[];decisions=[];request_hashes=[]
    violations={key:0 for key in ("missing_slots","unknown_slots","duplicate_slot_ids","invalid_status",
        "invalid_evidence","duplicate_evidence","response_repairs","dangling_refs","duplicate_refs",
        "parameter_ownership","functional_authority")}
    for index in range(1,cfg["reliability_calls"]+1):
        name=f"call_{index:02d}";folder=RESULT/"reliability"/name
        runner=load(folder/"call_result.json")
        meta=load(folder/"request_metadata.json")
        exact=ROOT/meta["exact_request_path"]
        if sha(exact)!=meta["exact_request_sha256"]:raise RuntimeError(f"request hash mismatch {name}")
        sent=load(exact)
        if (sent["model"],sent["temperature"],sent["top_p"],sent["seed"],sent["max_tokens"])!=(cfg["requested_model"],cfg["temperature"],cfg["top_p"],cfg["seed"],cfg["max_output_tokens"]):
            raise RuntimeError(f"model/budget mismatch {name}")
        if sent["response_format"]["json_schema"]["schema"]!=api_schema or sent["response_format"]["json_schema"]["strict"] is not True:
            raise RuntimeError(f"API schema not sent {name}")
        if sent["messages"][0]["content"]!=(ROOT/cfg["prompt"]).read_text(encoding="utf-8"):
            raise RuntimeError(f"prompt drift {name}")
        parts=sent["messages"][1]["content"]
        engineering="Engineering description for L04:\n"+(ROOT/frozen["source_files"]["engineering_text"]["path"]).read_text(encoding="utf-8")
        if len(parts)!=25 or parts[0]["text"]!=engineering:raise RuntimeError(f"source evidence mismatch {name}")
        for offset,item in enumerate(frozen["images"]):
            if parts[1+2*offset]["text"]!="Evidence view: "+item["view"]:raise RuntimeError(f"view label mismatch {name}")
            url=parts[2+2*offset]["image_url"]["url"]
            if not url.startswith("data:image/png;base64,") or hashlib.sha256(base64.b64decode(url.split(",",1)[1])).hexdigest()!=item["sha256"]:
                raise RuntimeError(f"image bytes mismatch {name}")
        if meta["image_hashes"]!=expected_images:raise RuntimeError(f"image manifest drift {name}")
        request_hashes.append(meta["exact_request_sha256"])
        record={"call_number":index,"attempt_retained":(folder/"attempt_started.json").exists(),
            "transport_valid":False,"contract_valid":False,"assembly_success":False,"canonical_kfdg_valid":False,
            "status":runner["status"],"token_usage":runner.get("token_usage"),
            "latency_seconds":runner.get("latency_seconds"),"error":None}
        raw_slots=None
        if (folder/"raw_response.txt").is_file():
            raw=(folder/"raw_response.txt").read_text(encoding="utf-8")
            http=load(folder/"http_response.json")
            sdk=load(folder/"sdk_response.json")
            if raw!=http["choices"][0]["message"]["content"] or raw!=sdk["choices"][0]["message"]["content"]:
                raise RuntimeError(f"HTTP/SDK content mismatch {name}")
            try:
                parsed=json.loads(raw)
                if isinstance(parsed,dict) and isinstance(parsed.get("slots"),list):
                    raw_ids=[s.get("slot_id") for s in parsed["slots"] if isinstance(s,dict)]
                    expected={s["slot_id"] for s in registry()["slots"]}
                    violations["missing_slots"]+=len(expected-set(raw_ids))
                    violations["unknown_slots"]+=sum(sid not in expected for sid in raw_ids)
                    violations["duplicate_slot_ids"]+=len(raw_ids)-len(set(raw_ids))
                    for s in parsed["slots"]:
                        if not isinstance(s,dict):continue
                        if s.get("status") not in {"PRESENT","ABSENT","UNCERTAIN"}:violations["invalid_status"]+=1
                        evidence=s.get("evidence_views",[])
                        if isinstance(evidence,list):
                            violations["duplicate_evidence"]+=len(evidence)-len(set(evidence))
                            if s.get("status") in {"PRESENT","UNCERTAIN"} and not evidence:violations["invalid_evidence"]+=1
                Draft202012Validator(api_schema).validate(parsed)
                record["transport_valid"]=True
                Draft202012Validator(canonical_schema).validate(parsed)
                checked=validate_slots(parsed)
                record["contract_valid"]=True
                raw_slots=checked
                if (folder/"validated_slots.json").is_file() and load(folder/"validated_slots.json")!=parsed:
                    violations["response_repairs"]+=1
                graph=assemble(checked)
                record["assembly_success"]=True
                validate_kfdg(graph,checked)
                stored=RESULT/"canonical_kfdg"/f"{name}.json"
                if not stored.is_file() or load(stored)!=graph:raise RuntimeError("stored KFDG differs from independent assembly")
                record["canonical_kfdg_valid"]=True
                ids={p["id"] for p in graph["parameters"]}
                for feature in graph["geometric_features"]:
                    refs=feature["parameter_refs"]
                    violations["duplicate_refs"]+=len(refs)-len(set(refs))
                    violations["dangling_refs"]+=sum(ref not in ids for ref in refs)
            except Exception as error:
                record["error"]=f"{type(error).__name__}: {error}"
                if "OWNERSHIP" in record["error"]:violations["parameter_ownership"]+=1
                if "FUNCTIONAL" in record["error"]:violations["functional_authority"]+=1
        else:record["error"]=runner.get("error","missing raw response")
        records.append(record);decisions.append(raw_slots)
    if len(request_hashes)!=cfg["reliability_calls"] or len(set(request_hashes))!=1:
        raise RuntimeError("exact request body parity failed")
    n=cfg["reliability_calls"]
    counts={key:sum(bool(r[key]) for r in records) for key in ("transport_valid","contract_valid","assembly_success","canonical_kfdg_valid")}
    expected_slots=[s["slot_id"] for s in registry()["slots"]]
    stability={}
    for sid in expected_slots:
        items=[next((s for s in decision["slots"] if s["slot_id"]==sid),None) if decision else None for decision in decisions]
        status_counts=Counter(s["status"] for s in items if s)
        confidence_counts=Counter(s["confidence"] for s in items if s)
        modal,count=(status_counts.most_common(1)[0] if status_counts else (None,0))
        probabilities=[c/n for c in status_counts.values()]
        entropy=-sum(p*math.log2(p) for p in probabilities if p>0)
        stability[sid]={"PRESENT":status_counts["PRESENT"],"ABSENT":status_counts["ABSENT"],
            "UNCERTAIN":status_counts["UNCERTAIN"],"modal_decision":modal,"modal_agreement":count/n,
            "status_entropy_bits":entropy,"confidence_counts":dict(confidence_counts),
            "confidence_modal_agreement":confidence_counts.most_common(1)[0][1]/n if confidence_counts else None,
            "decision_coverage":sum(s is not None for s in items)}
    warning_slots=[sid for sid,item in stability.items() if item["modal_agreement"]<cfg["perception_warning_modal_agreement_below"]]
    perception={"schema_version":"robotcad_try6_r1_v3_perception_stability_v1","denominator":n,
        "per_slot":stability,"average_modal_agreement":sum(x["modal_agreement"] for x in stability.values())/len(stability),
        "warning_threshold":cfg["perception_warning_modal_agreement_below"],
        "PERCEPTION_STABILITY_WARNING":bool(warning_slots),"warning_slots":warning_slots,
        "no_overall_performance_score":True,"no_majority_vote_kfdg":True}
    save(RESULT/"reliability/slot_decision_summary.json",{"denominator":n,"per_slot":stability})
    save(RESULT/"reliability/perception_stability.json",perception)
    gate=counts["transport_valid"]==n and counts["contract_valid"]==n and counts["assembly_success"]==n and counts["canonical_kfdg_valid"]==n and all(v==0 for v in violations.values())
    summary={"schema_version":"robotcad_try6_r1_v3_contract_summary_v1","requested_calls":n,
        "attempts_retained":sum(r["attempt_retained"] for r in records),"preflight_excluded":True,
        "exact_request_sha256":request_hashes[0],"exact_request_parity":True,
        "transport_valid_count":counts["transport_valid"],"contract_valid_count":counts["contract_valid"],
        "assembly_success_count":counts["assembly_success"],"canonical_kfdg_valid_count":counts["canonical_kfdg_valid"],
        "response_repair_count":violations["response_repairs"],"manual_intervention_count":0,
        "violations":violations,"representation_gate_pass":gate,"per_call":records,
        "gt_evaluations":0,"formal_holdout_evaluations":0}
    save(RESULT/"reliability/contract_summary.json",summary)
    save(RESULT/"canonical_kfdg/validation_summary.json",{"requested":n,"valid":counts["canonical_kfdg_valid"],
        "duplicate_refs":violations["duplicate_refs"],"dangling_refs":violations["dangling_refs"],
        "functional_conflicts":violations["functional_authority"],"gate_pass":gate})
    save(RESULT/"representation_audit.json",{"representation_gate_pass":gate,
        "counts":counts,"perception_warning":bool(warning_slots),"warning_slots":warning_slots,
        "independent_validator":True,"timestamp_utc":datetime.now(timezone.utc).isoformat()})
    print(json.dumps({"representation_gate_pass":gate,"counts":counts,
        "perception_warning":bool(warning_slots),"warning_slots":warning_slots}))
    return summary


if __name__=="__main__":representation()
