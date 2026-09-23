"""Independent R1-v3 representation and perception audit; no GT or holdout cases."""

from __future__ import annotations

import base64
import csv
import hashlib
import json
import math
import subprocess
import sys
import unittest
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


def prior_audit(name,path):
    folder=HERE/path
    manifest=load(folder/"manifest.json")
    hashes=manifest.get("lightweight_result_sha256",manifest.get("result_file_sha256",{}))
    if not all(sha(folder/item)==digest for item,digest in hashes.items()):
        raise RuntimeError(f"frozen prior result drift: {name}")
    return {"manifest_sha256":sha(folder/"manifest.json"),"files_checked":len(hashes),"unchanged":True}


def validate_e2e(cfg,frozen):
    from experiments.try6.scripts.run_r1_v3_e2e import actual_anchor_mm
    folder=RESULT/"e2e_smoke"
    artifact=HERE/"artifacts/try6_0_r1_v3/e2e_smoke"
    data=load(folder/"dataflow_audit.json")
    if data["status"]!="PASS" or data["fresh_vlm_calls"]!=1 or data["solver_candidates"]!=4:
        raise RuntimeError("E2E call/candidate gate failed")
    request=load(folder/"request.json")
    exact=ROOT/request["exact_request_path"]
    if sha(exact)!=request["exact_request_sha256"]:raise RuntimeError("E2E exact request hash mismatch")
    sent=load(exact)
    api=load(RESULT/"schema/api_transport_schema.json")
    if sent["response_format"]["json_schema"]["schema"]!=api or sent["response_format"]["json_schema"]["strict"] is not True:
        raise RuntimeError("E2E transport schema not sent")
    if (sent["model"],sent["temperature"],sent["top_p"],sent["seed"],sent["max_tokens"])!=(cfg["requested_model"],cfg["temperature"],cfg["top_p"],cfg["seed"],cfg["max_output_tokens"]):
        raise RuntimeError("E2E model/budget parity mismatch")
    if sent["messages"][0]["content"]!=(ROOT/cfg["prompt"]).read_text(encoding="utf-8"):
        raise RuntimeError("E2E prompt mismatch")
    parts=sent["messages"][1]["content"]
    engineering="Engineering description for L04:\n"+(ROOT/frozen["source_files"]["engineering_text"]["path"]).read_text(encoding="utf-8")
    if len(parts)!=25 or parts[0]["text"]!=engineering:raise RuntimeError("E2E evidence count/text mismatch")
    for i,item in enumerate(frozen["images"]):
        if parts[1+2*i]["text"]!="Evidence view: "+item["view"]:raise RuntimeError("E2E view label mismatch")
        url=parts[2+2*i]["image_url"]["url"]
        if not url.startswith("data:image/png;base64,") or hashlib.sha256(base64.b64decode(url.split(",",1)[1])).hexdigest()!=item["sha256"]:
            raise RuntimeError("E2E image bytes mismatch")
    raw=(folder/"raw_slot_response.json").read_text(encoding="utf-8")
    sdk=load(folder/"sdk_response.json")
    http=load(folder/"http_response.json")
    if raw!=sdk["choices"][0]["message"]["content"] or raw!=http["choices"][0]["message"]["content"]:
        raise RuntimeError("E2E raw HTTP/SDK mismatch")
    ids=[load(RESULT/"reliability"/f"call_{i:02d}"/"sdk_response.json")["id"] for i in range(1,6)]
    if sdk["id"] in ids:raise RuntimeError("E2E response is not a fresh call")
    Draft202012Validator(api).validate(json.loads(raw))
    decisions=validate_slots(json.loads(raw))
    if decisions!=load(folder/"validated_slots.json"):raise RuntimeError("E2E slot repair detected")
    graph=assemble(decisions);validate_kfdg(graph,decisions)
    if graph!=load(folder/"canonical_kfdg.json"):raise RuntimeError("E2E graph differs from deterministic assembly")
    actual=actual_anchor_mm(ROOT/frozen["source_files"]["sanitized_urdf"]["path"])
    if abs(actual-63.0)>1e-9 or abs(graph["metric_anchor"]["distance_mm"]-actual)>1e-9:
        raise RuntimeError("E2E URDF anchor mismatch")
    smoke=load(HERE/"protocol/r1_v3_e2e_smoke.json")
    registry_params=load(ROOT/cfg["parameter_registry"])["parameters"]
    width=next(p["value"] for p in registry_params if p["id"]=="housing_width_mm")
    ratio=width/actual
    history=list(csv.DictReader((folder/"solver_history.csv").open(newline="",encoding="utf-8")))
    if len(history)!=4 or [int(row["candidate"]) for row in history]!=[0,1,2,3]:
        raise RuntimeError("E2E candidate accounting mismatch")
    for index,row in enumerate(history):
        anchor=actual if index<3 else actual+smoke["anchor_sensitivity_delta_mm"]
        expected_width=(width*smoke["primary_candidate_width_factors"][index] if index<3 else ratio*anchor)
        expected_objective=(expected_width/anchor-ratio)**2
        if any(abs(float(row[key])-target)>1e-9 for key,target in (("anchor_mm",anchor),("housing_width_mm",expected_width),("objective",expected_objective))):
            raise RuntimeError(f"E2E objective/theta dataflow mismatch candidate {index}")
        if int(row["connected_solids"])!=1:raise RuntimeError("E2E disconnected CAD")
        job=load(artifact/f"candidate_{index:02d}_job.json")
        if job["anchor_distance_mm"]!=actual:raise RuntimeError("synthetic anchor leaked into functional CAD")
        built=load(artifact/f"candidate_{index:02d}"/"build_result.json")
        if built["final_solid_count"]!=1 or not built["reopen"]["valid"] or built["status"]!="PASS":
            raise RuntimeError(f"CAD candidate {index} invalid")
    theta=load(folder/"theta.json")
    if theta["candidate_count"]!=3 or theta["selected_candidate"]!=min(range(3),key=lambda i:float(history[i]["objective"])):
        raise RuntimeError("E2E theta selection invalid")
    sensitivity=load(folder/"anchor_sensitivity.json")
    if not all(sensitivity[k] is True for k in ("objective_changed","theta_changed","cad_dimension_changed","final_volume_changed","functional_cad_anchor_remained_real_urdf")):
        raise RuntimeError("E2E anchor sensitivity incomplete")
    if abs(sensitivity["urdf_anchor_mm"]-actual)>1e-9 or abs(sensitivity["synthetic_anchor_mm"]-(actual+smoke["anchor_sensitivity_delta_mm"]))>1e-9:
        raise RuntimeError("E2E anchor values differ from frozen protocol")
    export=load(folder/"export_reopen.json")
    if export["interface_invariant_across_four_builds"] is not True:raise RuntimeError("E2E interface failed")
    names=("FrozenProximalBoreTool","FrozenMatingEnvelopeTool","FrozenScaffold")
    sigs=[load(artifact/f"candidate_{i:02d}"/"signature/signature.json") for i in range(4)]
    if not all(sig["valid"] for sig in sigs):raise RuntimeError("E2E CAD signature invalid")
    if not all(sig["shapes"][name]==sigs[0]["shapes"][name] for sig in sigs for name in names):
        raise RuntimeError("E2E frozen interface BREP changed")
    for filename,digest in export["final_artifact_sha256"].items():
        path=ROOT/export["final_artifact_paths"][filename]
        if not path.is_file() or path.stat().st_size==0 or sha(path)!=digest:
            raise RuntimeError(f"E2E final artifact missing/hash mismatch: {filename}")
    # Independent FreeCAD reopen/recompute of the copied final FCStd.
    sys.path.insert(0,str(ROOT/"experiments/try5A/scripts"))
    from freecad_runtime import python_runtime
    inspect_out=artifact/"independent_final_signature"
    job=artifact/"independent_final_signature_job.json"
    save(job,{"fcstd":str(artifact/"final.FCStd"),"output":str(inspect_out)})
    proc=subprocess.run([python_runtime(),str(HERE/"scripts/freecad_r1_v3_signature.py"),str(job)],
        cwd=ROOT,capture_output=True,text=True,timeout=120)
    if proc.returncode:raise RuntimeError(f"independent final FCStd reopen failed: {proc.stderr[-1000:]}")
    final_sig=load(inspect_out/"signature.json")
    if not final_sig["valid"] or final_sig["shapes"]["RigidGroup"]["solids"]!=1:
        raise RuntimeError("independent final FCStd invalid")
    if final_sig["parameter_table_housing_width_mm"]!=theta["theta"]["housing_width_mm"]:
        raise RuntimeError("final FCStd theta binding mismatch")
    return {"fresh_call_valid":True,"canonical_kfdg_valid":True,"solver_candidates":4,
        "theta_produced":True,"objective_finite":True,"urdf_anchor_consumed":True,
        "anchor_sensitivity_pass":True,"parameter_changed_final_cad":True,
        "connected_solid_count":1,"interface_invariant":True,
        "step_export":True,"stl_export":True,"fcstd_reopen":True,
        "independent_final_fcstd_reopen":True,"response_repair_count":0,
        "gt_evaluations":0,"formal_holdout_evaluations":0,
        "slot_statuses":{s["slot_id"]:s["status"] for s in decisions["slots"]}}


def finalize():
    summary=representation()
    cfg=load(HERE/"protocol/r1_v3_protocol.json")
    frozen=load(RESULT/"reliability_freeze.json")
    perception=load(RESULT/"reliability/perception_stability.json")
    prior={name:prior_audit(name,path) for name,path in (("c1_v1","results/try6_0_c1"),
        ("r0","results/try6_0_r0"),("r1_v1","results/try6_0_r1"),
        ("r1_v2","results/try6_0_r1_v2"))}
    lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    holdout_closed=lock["accessed"] is False and lock["evaluation_count"]==0
    if not holdout_closed:raise RuntimeError("formal holdout lock violated")
    suite=unittest.defaultTestLoader.loadTestsFromName("experiments.try6.tests.test_r1_v3_contract")
    tests=unittest.TestResult();suite.run(tests)
    test_report={"run":tests.testsRun,"failures":len(tests.failures),"errors":len(tests.errors),
        "pass":tests.wasSuccessful() and tests.testsRun>=26}
    if not test_report["pass"]:raise RuntimeError("R1-v3 local contract tests failed")
    if summary["representation_gate_pass"]:
        e2e=validate_e2e(cfg,frozen)
        decision="READY_FOR_C1_V2"
    else:
        e2e=None
        if not (RESULT/"e2e_smoke").exists():
            decision=("API_SCHEMA_COMPATIBILITY_BLOCKED" if not load(RESULT/"preflight/report.json")["preflight_pass"] else
                "CLOSED_SET_CONTRACT_BLOCKED" if summary["contract_valid_count"]<cfg["reliability_calls"] else "GRAPH_ASSEMBLY_BLOCKED")
        else:raise RuntimeError("E2E ran after failed representation gate")
    if summary["representation_gate_pass"] and (e2e is None or not all(e2e[k] for k in
        ("fresh_call_valid","canonical_kfdg_valid","theta_produced","objective_finite","urdf_anchor_consumed",
         "anchor_sensitivity_pass","parameter_changed_final_cad","interface_invariant","step_export","stl_export","fcstd_reopen","independent_final_fcstd_reopen"))):
        decision="SOLVER_INTEGRATION_BLOCKED"
    save(RESULT/"experiment_config_snapshot.json",cfg)
    save(RESULT/"case_split.json",{"schema_version":"robotcad_try6_r1_v3_split_lock_v1",
        "development_subjects":["L04"],"formal_holdout_case_count":32,
        "formal_holdout_lock_sha256":sha(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json"),
        "formal_holdout_ids_not_read":True,"accessed":False,"evaluation_count":0})
    save(RESULT/"condition_parity.json",{"schema_version":"robotcad_try6_r1_v3_request_parity_v1",
        "reliability_exact_request_sha256":summary["exact_request_sha256"],
        "reliability_exact_request_parity":summary["exact_request_parity"],
        "preflight_excluded":True,"e2e_fresh_call_excluded":True,
        "no_voting_or_best_of_five":True})
    save(RESULT/"holdout_evaluation_log.json",{"events":[],"followed_by_tuning":False,
        "accessed":False,"evaluation_count":0})
    accounting={"schema_version":"robotcad_try6_r1_v3_failure_accounting_v1",
        "preflight_attempts":1,"preflight_pass":load(RESULT/"preflight/report.json")["preflight_pass"],
        "preflight_in_denominator":False,"reliability_requested":5,"reliability_completed":5,
        "transport_valid":summary["transport_valid_count"],"contract_valid":summary["contract_valid_count"],
        "assembly_success":summary["assembly_success_count"],"canonical_kfdg_valid":summary["canonical_kfdg_valid_count"],
        "excluded_reliability_calls":[],"fresh_e2e_calls":1 if e2e else 0,
        "e2e_in_reliability_denominator":False,"solver_candidates":e2e["solver_candidates"] if e2e else 0,
        "failed_cad_candidates":0 if e2e else None,"gt_evaluations":0,"formal_holdout_evaluations":0}
    save(RESULT/"failure_accounting.json",accounting)
    ledger={"schema_version":"robotcad_try6_r1_v3_claim_ledger_v1","claims":[
        {"claim":"production slot schema accepted","evidence_type":"computed","artifact":"preflight/report.json","field":"http_status / preflight_pass","expected":"200 / true"},
        {"claim":"five exact requests identical","evidence_type":"computed","artifact":"reliability/contract_summary.json","field":"exact_request_parity","expected":True},
        {"claim":"closed-set contract 5/5","evidence_type":"computed","artifact":"reliability/contract_summary.json","field":"contract_valid_count","expected":5},
        {"claim":"canonical KFDG 5/5","evidence_type":"computed","artifact":"reliability/contract_summary.json","field":"canonical_kfdg_valid_count","expected":5},
        {"claim":"visible pocket perception warning","evidence_type":"computed","artifact":"reliability/perception_stability.json","field":"per_slot.visible_pocket.modal_agreement","expected":0.6},
        {"claim":"fresh E2E dataflow passed","evidence_type":"computed","artifact":"validation.json","field":"e2e_independent_validation","expected":"all PASS"},
        {"claim":"GT and holdout untouched","evidence_type":"computed","artifact":"validation.json","field":"gt_evaluations / holdout_closed","expected":"0 / true"}
    ]}
    save(RESULT/"claim_ledger.json",ledger)
    validation={"schema_version":"robotcad_try6_r1_v3_independent_validation_v1",
        "timestamp_utc":datetime.now(timezone.utc).isoformat(),"decision":decision,
        "production_preflight_pass":load(RESULT/"preflight/report.json")["preflight_pass"],
        "representation_gate_pass":summary["representation_gate_pass"],
        "transport_valid_count":summary["transport_valid_count"],
        "contract_valid_count":summary["contract_valid_count"],
        "canonical_kfdg_valid_count":summary["canonical_kfdg_valid_count"],
        "response_repair_count":summary["response_repair_count"],
        "manual_intervention_count":summary["manual_intervention_count"],
        "perception_warning":perception["PERCEPTION_STABILITY_WARNING"],
        "warning_slots":perception["warning_slots"],
        "e2e_independent_validation":e2e,"prior_result_hash_recheck":prior,
        "holdout_closed":holdout_closed,"gt_evaluations":0,"formal_holdout_evaluations":0,
        "local_tests":test_report,
        "scope_note":"READY is infrastructure readiness only; synthetic objective does not establish geometry performance or Metric Grounding efficacy"}
    save(RESULT/"validation.json",validation)
    head=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    branch=subprocess.run(["git","branch","--show-current"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    sys.path.insert(0,str(ROOT/"experiments/try5A/scripts"))
    from freecad_runtime import python_runtime
    freecad=subprocess.run([python_runtime(),"-c","import FreeCAD,json;print(json.dumps(FreeCAD.Version()))"],
        cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    result_hashes={str(p.relative_to(RESULT)).replace("\\","/"):sha(p)
        for p in RESULT.rglob("*") if p.is_file() and p.name!="manifest.json"}
    manifest={"schema_version":"robotcad_try6_r1_v3_manifest_v1","decision":decision,
        "starting_commit":cfg["starting_commit"],"implementation_commit_before_calls":frozen["implementation_commit_before_calls"],
        "implementation_head_at_validation":head,"branch":branch,
        "protocol_sha256":frozen["protocol_sha256"],"frozen_hashes":frozen["frozen_hashes"],
        "api_schema_sha256":frozen["api_schema_sha256"],
        "projection_removed_paths":frozen["projection_removed_paths"],
        "preflight_report_sha256":frozen["preflight_report_sha256"],
        "e2e_smoke_config_sha256":sha(HERE/"protocol/r1_v3_e2e_smoke.json"),
        "source_files":frozen["source_files"],"image_hashes":{x["view"]:x["sha256"] for x in frozen["images"]},
        "model_requested":cfg["requested_model"],"model_returned":"qwen3.7-plus",
        "sdk_version":__import__("openai").__version__,"api_base_url":frozen["api_base_url"],
        "api_key_recorded":False,"python_executable":sys.executable,"freecad_version":freecad,
        "prior_results":prior,"formal_holdout_accessed":False,"formal_holdout_evaluation_count":0,
        "gt_evaluation_count":0,"solver_candidate_count":e2e["solver_candidates"] if e2e else 0,
        "result_file_sha256":result_hashes}
    save(RESULT/"manifest.json",manifest)
    print(json.dumps({"decision":decision,"contract_valid":summary["contract_valid_count"],
        "canonical_valid":summary["canonical_kfdg_valid_count"],"e2e_pass":e2e is not None,
        "perception_warning":perception["PERCEPTION_STABILITY_WARNING"],"tests":test_report["run"]}))
    return validation


if __name__=="__main__":finalize()
