"""One fresh slot call and four-candidate synthetic, non-GT anchor→CAD smoke."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import subprocess
import sys
import time
import tomllib
import xml.etree.ElementTree as ET
from datetime import datetime,timezone

import httpx
import openai
from jsonschema import Draft202012Validator

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try6.scripts.r1_v3_contract import assemble,validate_kfdg,validate_slots
from experiments.try6.scripts.run_r1_reliability import data_url,save

RESULT=HERE/"results/try6_0_r1_v3/e2e_smoke"
ARTIFACT=HERE/"artifacts/try6_0_r1_v3/e2e_smoke"
sys.path.insert(0,str(ROOT/"experiments/try5A/scripts"))
from freecad_runtime import python_runtime


def actual_anchor_mm(path):
    root=ET.parse(path).getroot()
    joint=next(j for j in root.findall("joint") if j.get("name")=="J04")
    xyz=[float(v) for v in joint.find("origin").get("xyz").split()]
    return math.sqrt(sum(v*v for v in xyz))*1000.0


def invoke_builder(index,theta,graph_path,anchor):
    folder=ARTIFACT/f"candidate_{index:02d}";folder.mkdir(parents=True,exist_ok=True)
    job={"mode":"R1_V3_SYNTHETIC_NON_GT_E2E","parameters":theta,"anchor_distance_mm":anchor,
        "kfdg_path":str(graph_path),
        "frozen_interface_contracts":str(ROOT/"experiments/try5A/results/try5a5/motion_interface_contracts.json"),
        "f0_fcstd":str(ROOT/"experiments/try5A/artifacts/try5a5/round3_verified/links/L04/model.FCStd"),
        "output_root":str(folder)}
    job_path=ARTIFACT/f"candidate_{index:02d}_job.json";save(job_path,job)
    tick=time.perf_counter()
    result=subprocess.run([python_runtime(),str(HERE/"scripts/freecad_c1_builder.py"),str(job_path)],
        cwd=ROOT,capture_output=True,text=True,timeout=180)
    (RESULT/f"candidate_{index:02d}_stdout.txt").write_text(result.stdout,encoding="utf-8")
    (RESULT/f"candidate_{index:02d}_stderr.txt").write_text(result.stderr,encoding="utf-8")
    if result.returncode:raise RuntimeError(f"candidate {index} CAD failed: {result.stderr[-1200:]}")
    built=load(folder/"build_result.json")
    if built["final_solid_count"]!=1 or not built["reopen"]["valid"]:
        raise RuntimeError(f"candidate {index} solid/reopen invalid")
    signature_job=ARTIFACT/f"candidate_{index:02d}_signature_job.json"
    signature_root=folder/"signature"
    save(signature_job,{"fcstd":str(folder/"final.FCStd"),"output":str(signature_root)})
    signature_run=subprocess.run([python_runtime(),str(HERE/"scripts/freecad_r1_v3_signature.py"),str(signature_job)],
        cwd=ROOT,capture_output=True,text=True,timeout=120)
    (RESULT/f"candidate_{index:02d}_signature_stdout.txt").write_text(signature_run.stdout,encoding="utf-8")
    (RESULT/f"candidate_{index:02d}_signature_stderr.txt").write_text(signature_run.stderr,encoding="utf-8")
    if signature_run.returncode:raise RuntimeError(f"candidate {index} signature failed: {signature_run.stderr[-1000:]}")
    signature=load(signature_root/"signature.json")
    if not signature["valid"]:raise RuntimeError(f"candidate {index} signature invalid")
    return folder,built,signature,time.perf_counter()-tick


def run():
    cfg=load(HERE/"protocol/r1_v3_protocol.json")
    smoke=load(HERE/"protocol/r1_v3_e2e_smoke.json")
    gate=load(HERE/"results/try6_0_r1_v3/representation_audit.json")
    frozen=load(HERE/"results/try6_0_r1_v3/reliability_freeze.json")
    if gate["representation_gate_pass"] is not True:raise RuntimeError("representation gate not independently passed")
    if RESULT.exists():raise FileExistsError("E2E fresh call already attempted; no rerun")
    lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"]!=0:raise RuntimeError("holdout lock violated")
    for key,digest in frozen["frozen_hashes"].items():
        if sha(ROOT/cfg[key])!=digest:raise RuntimeError(f"frozen {key} drift")
    if smoke["fresh_vlm_calls"]!=1 or smoke["total_cad_candidate_budget"]!=4:
        raise RuntimeError("smoke budget drift")
    RESULT.mkdir(parents=True);ARTIFACT.mkdir(parents=True,exist_ok=True)
    save(RESULT/"attempt_started.json",{"timestamp_utc":datetime.now(timezone.utc).isoformat(),
        "fresh_call":True,"not_in_reliability_denominator":True,"retry_count":0,
        "smoke_config_sha256":sha(HERE/"protocol/r1_v3_e2e_smoke.json")})
    status={"status":"STARTED","fresh_vlm_calls":0,"solver_candidates":0,"gt_evaluations":0,
        "formal_holdout_evaluations":0,"response_repair_count":0,"manual_intervention":0}
    try:
        local=tomllib.loads((ROOT/cfg["model_config"]).read_text(encoding="utf-8"))
        api_schema=load(HERE/"results/try6_0_r1_v3/schema/api_transport_schema.json")
        canonical_schema=load(ROOT/cfg["canonical_slot_schema"])
        prompt=(ROOT/cfg["prompt"]).read_text(encoding="utf-8")
        engineering=(ROOT/frozen["source_files"]["engineering_text"]["path"]).read_text(encoding="utf-8")
        content=[{"type":"text","text":"Engineering description for L04:\n"+engineering}]
        for image in frozen["images"]:
            if sha(ROOT/image["path"])!=image["sha256"]:raise RuntimeError("image drift")
            content.extend([{"type":"text","text":"Evidence view: "+image["view"]},
                {"type":"image_url","image_url":{"url":data_url(ROOT/image["path"])}}])
        messages=[{"role":"system","content":prompt},{"role":"user","content":content}]
        captured={}
        def on_request(req):captured.update(request_bytes=req.content,request_json=json.loads(req.content))
        def on_response(resp):
            resp.read();captured["http_status"]=resp.status_code
            try:captured["http_json"]=resp.json()
            except Exception:captured["http_text"]=resp.text
        tick=time.perf_counter()
        try:
            with httpx.Client(timeout=cfg["timeout_seconds"],event_hooks={"request":[on_request],"response":[on_response]}) as transport:
                client=openai.OpenAI(api_key=local["provider"]["api_key"],base_url=local["provider"]["base_url"],
                    timeout=cfg["timeout_seconds"],max_retries=0,http_client=transport)
                response=client.chat.completions.create(model=cfg["requested_model"],messages=messages,
                    response_format={"type":"json_schema","json_schema":{"name":"try6_r1_v3_l04_slots_e2e","strict":True,"schema":api_schema}},
                    temperature=cfg["temperature"],top_p=cfg["top_p"],max_tokens=cfg["max_output_tokens"],seed=cfg["seed"])
            sdk=response.model_dump(mode="json");save(RESULT/"sdk_response.json",sdk)
            raw=captured["http_json"]["choices"][0]["message"]["content"]
            if not isinstance(raw,str):raise RuntimeError("non-string raw slot content")
            (RESULT/"raw_slot_response.json").write_text(raw,encoding="utf-8")
            status["fresh_vlm_calls"]=1
            if raw!=sdk["choices"][0]["message"]["content"]:raise RuntimeError("HTTP/SDK content mismatch")
            if captured["request_json"]["response_format"]["json_schema"]["schema"]!=api_schema:raise RuntimeError("API schema not sent")
            parsed=json.loads(raw)
            Draft202012Validator(api_schema).validate(parsed)
            Draft202012Validator(canonical_schema).validate(parsed)
            decisions=validate_slots(parsed)
            graph=assemble(decisions);validate_kfdg(graph,decisions)
            save(RESULT/"validated_slots.json",decisions)
            graph_path=RESULT/"canonical_kfdg.json";save(graph_path,graph)
            status["model_returned"]=sdk.get("model")
            status["token_usage"]=sdk.get("usage")
        finally:
            status["vlm_latency_seconds"]=time.perf_counter()-tick
            if "request_bytes" in captured:
                exact=ARTIFACT/"request_payload.json";exact.write_bytes(captured["request_bytes"])
                save(RESULT/"request.json",{"exact_request_path":str(exact.relative_to(ROOT)).replace("\\","/"),
                    "exact_request_sha256":sha(exact),"response_format":captured["request_json"].get("response_format"),
                    "prompt_sha256":sha(ROOT/cfg["prompt"]),"image_hashes":{x["view"]:x["sha256"] for x in frozen["images"]},
                    "fresh_not_reliability_sample":True})
            if "http_json" in captured:save(RESULT/"http_response.json",captured["http_json"])
        urdf=ROOT/frozen["source_files"]["sanitized_urdf"]["path"]
        anchor=actual_anchor_mm(urdf)
        if abs(anchor-63.0)>1e-9 or abs(graph["metric_anchor"]["distance_mm"]-anchor)>1e-9:
            raise RuntimeError("URDF/graph anchor mismatch")
        registry_params=load(ROOT/cfg["parameter_registry"])["parameters"]
        values={p["id"]:p["value"] for p in registry_params}
        base_width=values["housing_width_mm"]
        target_ratio=base_width/anchor
        factors=smoke["primary_candidate_width_factors"]
        if len(factors)!=smoke["primary_candidate_count"]:raise RuntimeError("candidate budget drift")
        history=[];signatures={}
        for i,factor in enumerate(factors):
            theta=dict(values);theta["housing_width_mm"]=base_width*factor
            score=(theta["housing_width_mm"]/anchor-target_ratio)**2
            if not math.isfinite(score):raise RuntimeError("non-finite objective")
            folder,built,signature,seconds=invoke_builder(i,theta,graph_path,anchor)
            status["solver_candidates"]+=1
            signatures[str(i)]=signature
            history.append({"candidate":i,"anchor_mm":anchor,"housing_width_mm":theta["housing_width_mm"],
                "objective":score,"final_volume_mm3":built["final_volume_mm3"],
                "connected_solids":built["final_solid_count"],"cad_seconds":seconds})
        best=min(history,key=lambda row:row["objective"])
        theta=dict(values);theta["housing_width_mm"]=best["housing_width_mm"]
        save(RESULT/"theta.json",{"theta":theta,"selected_candidate":best["candidate"],
            "objective":best["objective"],"candidate_count":len(history),"synthetic_target_ratio":target_ratio})
        mutated_anchor=anchor+smoke["anchor_sensitivity_delta_mm"]
        sensitivity_theta=dict(values);sensitivity_theta["housing_width_mm"]=target_ratio*mutated_anchor
        fixed_theta_objective_mutated=(theta["housing_width_mm"]/mutated_anchor-target_ratio)**2
        sensitivity_objective=(sensitivity_theta["housing_width_mm"]/mutated_anchor-target_ratio)**2
        folder,built,sig,seconds=invoke_builder(3,sensitivity_theta,graph_path,anchor)
        status["solver_candidates"]+=1
        signatures["3"]=sig
        history.append({"candidate":3,"anchor_mm":mutated_anchor,"housing_width_mm":sensitivity_theta["housing_width_mm"],
            "objective":sensitivity_objective,"final_volume_mm3":built["final_volume_mm3"],
            "connected_solids":built["final_solid_count"],"cad_seconds":seconds})
        protected=("FrozenProximalBoreTool","FrozenMatingEnvelopeTool","FrozenScaffold")
        interface_invariant=all(sig["shapes"][name]==signatures["0"]["shapes"][name]
            for sig in signatures.values() for name in protected)
        selected_sig=signatures[str(best["candidate"])]
        housing_before=selected_sig["shapes"]["MainHousingPad"]["bbox_mm"]
        housing_after=sig["shapes"]["MainHousingPad"]["bbox_mm"]
        final_volume_changed=abs(history[best["candidate"]]["final_volume_mm3"]-built["final_volume_mm3"])>1e-6
        dimension_changed=housing_before!=housing_after and sig["parameter_table_housing_width_mm"]!=selected_sig["parameter_table_housing_width_mm"]
        objective_changed=abs(fixed_theta_objective_mutated-best["objective"])>1e-12
        theta_changed=abs(sensitivity_theta["housing_width_mm"]-theta["housing_width_mm"])>1e-6
        if not all((interface_invariant,dimension_changed,final_volume_changed,objective_changed,theta_changed)):
            raise RuntimeError("anchor sensitivity or interface invariance failed")
        with (RESULT/"solver_history.csv").open("w",newline="",encoding="utf-8") as handle:
            writer=csv.DictWriter(handle,fieldnames=list(history[0]));writer.writeheader();writer.writerows(history)
        save(RESULT/"parameter_table.json",{"source":"frozen R1 Parameter Registry plus synthetic housing_width theta",
            "selected_theta":theta,"mutated_theta":sensitivity_theta,"frozen_functional_anchor_mm":anchor})
        save(RESULT/"anchor_sensitivity.json",{"urdf_anchor_mm":anchor,"synthetic_anchor_mm":mutated_anchor,
            "ratio_target":target_ratio,"normalized_relation_at_real_anchor":theta["housing_width_mm"]/anchor,
            "fixed_theta_relation_at_synthetic_anchor":theta["housing_width_mm"]/mutated_anchor,
            "selected_objective":best["objective"],"fixed_theta_objective_at_synthetic_anchor":fixed_theta_objective_mutated,
            "mutated_theta_objective":sensitivity_objective,
            "selected_housing_width_mm":theta["housing_width_mm"],"mutated_housing_width_mm":sensitivity_theta["housing_width_mm"],
            "selected_pad_bbox_mm":housing_before,"mutated_pad_bbox_mm":housing_after,
            "selected_final_volume_mm3":history[best["candidate"]]["final_volume_mm3"],
            "mutated_final_volume_mm3":built["final_volume_mm3"],
            "objective_changed":objective_changed,"theta_changed":theta_changed,
            "cad_dimension_changed":dimension_changed,"final_volume_changed":final_volume_changed,
            "functional_cad_anchor_remained_real_urdf":True})
        selected_folder=ARTIFACT/f"candidate_{best['candidate']:02d}"
        for name in ("final.FCStd","final.step","final.stl"):
            shutil.copy2(selected_folder/name,ARTIFACT/name)
        save(RESULT/"export_reopen.json",{"selected_candidate":best["candidate"],
            "selected_build":load(selected_folder/"build_result.json"),
            "interface_invariant_across_four_builds":interface_invariant,
            "protected_shape_signatures":{key:{name:value["shapes"][name] for name in protected} for key,value in signatures.items()},
            "final_artifact_sha256":{name:sha(ARTIFACT/name) for name in ("final.FCStd","final.step","final.stl")},
            "final_artifact_paths":{name:str((ARTIFACT/name).relative_to(ROOT)).replace("\\","/") for name in ("final.FCStd","final.step","final.stl")}})
        status.update({"status":"PASS","raw_slot_valid":True,"canonical_kfdg_valid":True,
            "objective_finite":all(math.isfinite(row["objective"]) for row in history),
            "theta_produced":True,"urdf_anchor_consumed":True,"anchor_sensitivity_pass":True,
            "cad_build_success":True,"connected_solid_count":1,"interface_invariant":True,
            "step_export_success":True,"stl_export_success":True,"fcstd_reopen_success":True})
    except Exception as error:
        status["status"]="FAIL"
        status["error"]=f"{type(error).__name__}: {error}"
    save(RESULT/"dataflow_audit.json",status)
    print(json.dumps({"status":status["status"],"fresh_vlm_calls":status["fresh_vlm_calls"],
        "solver_candidates":status["solver_candidates"],"error":status.get("error")}))
    return status["status"]=="PASS"


if __name__=="__main__":sys.exit(0 if run() else 2)
