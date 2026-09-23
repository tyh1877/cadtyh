"""Independent post-run R1-v2 transport, semantic, and assembly audit."""

from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

from jsonschema import Draft202012Validator

from experiments.try6.scripts.r1_contract import ROOT, HERE, FORBIDDEN_VISUAL_TERMS, assemble, canonical, load, sha, validate_kfdg, validate_vfp
from experiments.try6.scripts.r1_v2_projection import project

RESULT = HERE / "results/try6_0_r1_v2"


def save(path,obj):
    path = Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")


def prior_audit(name,path):
    folder = HERE / path
    manifest = load(folder/"manifest.json")
    hashes = manifest.get("lightweight_result_sha256",manifest.get("result_file_sha256",{}))
    if not all(sha(folder/item)==digest for item,digest in hashes.items()):
        raise RuntimeError(f"frozen prior result drift: {name}")
    return {"manifest_sha256":sha(folder/"manifest.json"),"files_checked":len(hashes),"unchanged":True}


def pair_agreement(proposals,key):
    pairs = [(a,b) for a,b in combinations(proposals,2) if a is not None and b is not None]
    if not pairs: return None
    return sum(key(a)==key(b) for a,b in pairs)/len(pairs)


def audit():
    cfg = load(HERE/"protocol/r1_v2_protocol.json")
    frozen = load(RESULT/"reliability_freeze.json")
    preflight = load(RESULT/"preflight/compatibility_report.json")
    if preflight["preflight_pass"] is not True: raise RuntimeError("preflight not passed")
    if sha(RESULT/"preflight/compatibility_report.json") != frozen["preflight_report_sha256"]:
        raise RuntimeError("preflight drift")
    if sha(HERE/"protocol/r1_v2_protocol.json") != frozen["protocol_sha256"]:
        raise RuntimeError("protocol drift")
    for name,digest in frozen["frozen_hashes"].items():
        if sha(ROOT/cfg[name]) != digest: raise RuntimeError(f"frozen {name} drift")
    canonical_schema = load(ROOT/cfg["canonical_schema"])
    api_schema = load(RESULT/"schema_projection/api_transport_schema.json")
    projected,removed = project(canonical_schema,load(ROOT/cfg["projection_rules"]))
    if api_schema != projected or sha(RESULT/"schema_projection/api_transport_schema.json") != frozen["api_schema_sha256"]:
        raise RuntimeError("schema projection drift")
    pre_meta = load(RESULT/"preflight/request_metadata.json")
    pre_exact = ROOT/pre_meta["exact_request_path"]
    if sha(pre_exact) != pre_meta["exact_request_sha256"]:
        raise RuntimeError("preflight exact request hash mismatch")
    pre_sent = load(pre_exact)
    if pre_sent["response_format"]["json_schema"]["schema"] != api_schema or pre_sent["response_format"]["json_schema"]["strict"] is not True:
        raise RuntimeError("preflight did not actually send projected schema")
    pre_http = load(RESULT/"preflight/http_response.json")
    pre_sdk = load(RESULT/"preflight/sdk_response.json")
    pre_raw = (RESULT/"preflight/raw_model_response.txt").read_text(encoding="utf-8")
    if preflight["http_status"] != 200 or pre_raw != pre_http["choices"][0]["message"]["content"] or pre_raw != pre_sdk["choices"][0]["message"]["content"]:
        raise RuntimeError("preflight HTTP/SDK/raw mismatch")
    Draft202012Validator(api_schema).validate(json.loads(pre_raw))
    image_hashes = {item["view"]:item["sha256"] for item in frozen["images"]}
    request_hashes = []
    records,proposals = [],[]
    metrics = {name:0 for name in ("duplicate_roles","duplicate_evidence","unsupported_features","invalid_feature_signatures",
        "missing_required_features","dangling_refs","duplicate_refs","ownership_violations","functional_conflicts","response_repairs")}
    for number in range(1,cfg["independent_reliability_calls"]+1):
        name = f"call_{number:02d}"
        folder = RESULT/"reliability"/name
        runner = load(folder/"call_result.json")
        meta = load(folder/"request_metadata.json")
        exact = ROOT/meta["exact_request_path"]
        if sha(exact) != meta["exact_request_sha256"]: raise RuntimeError(f"request hash mismatch {name}")
        sent = load(exact)
        if (sent["model"],sent["temperature"],sent["top_p"],sent["seed"],sent["max_tokens"]) != (cfg["requested_model"],cfg["temperature"],cfg["top_p"],cfg["seed"],cfg["max_output_tokens"]):
            raise RuntimeError(f"model/budget mismatch {name}")
        if sent["response_format"]["json_schema"]["schema"] != api_schema or sent["response_format"]["json_schema"]["strict"] is not True:
            raise RuntimeError(f"API schema not actually sent {name}")
        if sent["messages"][0]["content"] != (ROOT/cfg["prompt"]).read_text(encoding="utf-8"):
            raise RuntimeError(f"prompt mismatch {name}")
        pieces = sent["messages"][1]["content"]
        text = "Engineering description for L04:\n"+(ROOT/frozen["source_files"]["engineering_text"]["path"]).read_text(encoding="utf-8")
        if len(pieces) != 25 or pieces[0]["text"] != text: raise RuntimeError(f"engineering or image count mismatch {name}")
        for index,item in enumerate(frozen["images"]):
            if pieces[1+2*index]["text"] != "Evidence view: "+item["view"]: raise RuntimeError(f"view label mismatch {name}")
            url = pieces[2+2*index]["image_url"]["url"]
            if not url.startswith("data:image/png;base64,") or hashlib.sha256(base64.b64decode(url.split(",",1)[1])).hexdigest()!=item["sha256"]:
                raise RuntimeError(f"image bytes mismatch {name}")
        if meta["image_hashes"] != image_hashes: raise RuntimeError(f"image manifest mismatch {name}")
        request_hashes.append(meta["exact_request_sha256"])
        record = {"call_number":number,"attempt_retained":(folder/"attempt_started.json").exists(),
            "transport_valid":False,"canonical_schema_valid":False,"semantic_valid":False,
            "assembly_success":False,"canonical_kfdg_valid":False,"error":None,
            "model_returned":runner.get("model_returned"),"token_usage":runner.get("token_usage"),
            "latency_seconds":runner.get("latency_seconds")}
        proposal = None
        if (folder/"raw_response.txt").is_file():
            raw = (folder/"raw_response.txt").read_text(encoding="utf-8")
            http = load(folder/"http_response.json")
            sdk = load(folder/"sdk_response.json")
            if raw != http["choices"][0]["message"]["content"] or raw != sdk["choices"][0]["message"]["content"]:
                raise RuntimeError(f"HTTP/SDK raw mismatch {name}")
            try:
                proposal = json.loads(raw)
                if isinstance(proposal,dict) and isinstance(proposal.get("visual_features"),list):
                    classes = [f.get("feature_type") for f in proposal["visual_features"] if isinstance(f,dict)]
                    if set(classes) != {"main_housing","pocket","profile_transition"}:
                        metrics["missing_required_features"] += 1
                    for f in proposal["visual_features"]:
                        if not isinstance(f,dict): continue
                        roles = f.get("parameter_roles",[])
                        evidence = f.get("evidence_views",[])
                        if isinstance(roles,list): metrics["duplicate_roles"] += len(roles)-len(set(roles))
                        if isinstance(evidence,list): metrics["duplicate_evidence"] += len(evidence)-len(set(evidence))
                        if f.get("feature_type") not in {"main_housing","pocket","profile_transition"} or any(term in str(f.get("local_name","")) for term in FORBIDDEN_VISUAL_TERMS):
                            metrics["unsupported_features"] += 1
                        signatures = load(ROOT/cfg["assembler_rules"])["feature_signatures"]
                        if f.get("feature_type") in signatures and set(roles) != set(signatures[f["feature_type"]]["required_roles"]):
                            metrics["invalid_feature_signatures"] += 1
                    if any(key in proposal for key in ("joint_ids","joint_axis","joint_origin","interface_geometry","functional_nodes")):
                        metrics["functional_conflicts"] += 1
                Draft202012Validator(api_schema).validate(proposal)
                record["transport_valid"] = True
                Draft202012Validator(canonical_schema).validate(proposal)
                record["canonical_schema_valid"] = True
                checked = validate_vfp(proposal)
                record["semantic_valid"] = True
                if (folder/"validated_vfp.json").is_file() and load(folder/"validated_vfp.json") != proposal:
                    metrics["response_repairs"] += 1
                graph = assemble(checked)
                record["assembly_success"] = True
                validate_kfdg(graph,checked)
                existing = RESULT/"canonical_kfdg"/f"{name}.json"
                if not existing.is_file() or load(existing) != graph:
                    raise RuntimeError("stored graph differs from independent assembly")
                record["canonical_kfdg_valid"] = True
                ids = {p["id"] for p in graph["parameters"]}
                for feature in graph["geometric_features"]:
                    refs = feature["parameter_refs"]
                    metrics["duplicate_refs"] += len(refs)-len(set(refs))
                    metrics["dangling_refs"] += sum(ref not in ids for ref in refs)
            except Exception as error:
                record["error"] = f"{type(error).__name__}: {error}"
                if "OWNERSHIP" in record["error"]: metrics["ownership_violations"] += 1
                if "FUNCTIONAL" in record["error"]: metrics["functional_conflicts"] += 1
        else:
            record["error"] = runner.get("error","no raw response")
        records.append(record)
        proposals.append(proposal)
    if len(set(request_hashes)) != 1: raise RuntimeError("five exact request bodies differed")
    n = cfg["independent_reliability_calls"]
    counts = {key:sum(bool(r[key]) for r in records) for key in ("transport_valid","canonical_schema_valid","semantic_valid","assembly_success","canonical_kfdg_valid")}
    consistency = {"denominator":n,"pair_count":n*(n-1)//2,
        "feature_class_agreement":pair_agreement(proposals,lambda p:sorted(f["feature_type"] for f in p["visual_features"])),
        "parameter_role_agreement":pair_agreement(proposals,lambda p:sorted((f["feature_type"],tuple(sorted(f["parameter_roles"]))) for f in p["visual_features"])),
        "relation_agreement":pair_agreement(proposals,lambda p:sorted((f["feature_type"],canonical(f["relations"])) for f in p["visual_features"])),
        "confidence_agreement":pair_agreement(proposals,lambda p:sorted((f["feature_type"],f["confidence"]) for f in p["visual_features"])),
        "all_five_transport_valid":counts["transport_valid"]==n,
        "all_five_semantic_valid":counts["semantic_valid"]==n,
        "interpretation":"descriptive raw-proposal consistency; invalid proposals retained; not a paper performance metric"}
    save(RESULT/"reliability/proposal_consistency.json",consistency)
    gate = counts["transport_valid"]==n and counts["semantic_valid"]==n and counts["canonical_kfdg_valid"]==n and all(v==0 for v in metrics.values())
    summary = {"schema_version":"robotcad_try6_r1_v2_reliability_summary_v1","requested_calls":n,
        "attempts_retained":sum(r["attempt_retained"] for r in records),"preflight_excluded":True,
        "exact_request_sha256":request_hashes[0],"exact_request_parity":True,
        "TSR":counts["transport_valid"]/n,"VSR":counts["semantic_valid"]/n,"GAR":counts["canonical_kfdg_valid"]/n,
        "counts":counts,"violation_counts":metrics,"repair_count":metrics["response_repairs"],
        "representation_gate_pass":gate,"per_call":records,
        "gt_evaluations":0,"formal_holdout_evaluations":0}
    save(RESULT/"reliability/reliability_summary.json",summary)
    save(RESULT/"canonical_kfdg/validation_summary.json",{"valid_graphs":counts["canonical_kfdg_valid"],
        "requested":n,"duplicate_refs":metrics["duplicate_refs"],"dangling_refs":metrics["dangling_refs"],
        "ownership_violations":metrics["ownership_violations"],"functional_conflicts":metrics["functional_conflicts"],
        "gate_pass":gate})
    print(json.dumps({"TSR":summary["TSR"],"VSR":summary["VSR"],"GAR":summary["GAR"],
        "representation_gate_pass":gate,"violations":metrics}))
    return summary


def finalize():
    summary = audit()
    cfg = load(HERE/"protocol/r1_v2_protocol.json")
    frozen = load(RESULT/"reliability_freeze.json")
    prior = {name:prior_audit(name,path) for name,path in (("c1_v1","results/try6_0_c1"),
        ("r0","results/try6_0_r0"),("r1_v1","results/try6_0_r1"))}
    lock = load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    holdout_closed = lock["accessed"] is False and lock["evaluation_count"] == 0
    if not holdout_closed: raise RuntimeError("formal holdout lock violated")
    suites = [unittest.defaultTestLoader.loadTestsFromName(name) for name in
        ("experiments.try6.tests.test_r1_contract","experiments.try6.tests.test_r1_v2_projection")]
    tests = unittest.TestResult()
    for suite in suites: suite.run(tests)
    test_report = {"run":tests.testsRun,"failures":len(tests.failures),"errors":len(tests.errors),
        "pass":tests.wasSuccessful() and tests.testsRun>=31}
    if not test_report["pass"]: raise RuntimeError("R1-v2 local test gate failed")
    e2e_not_run = not (RESULT/"e2e_smoke").exists()
    if summary["representation_gate_pass"]:
        raise RuntimeError("representation unexpectedly passed; this finalizer requires gated E2E evidence")
    if not e2e_not_run: raise RuntimeError("E2E ran despite failed representation gate")
    decision = ("API_SCHEMA_COMPATIBILITY_BLOCKED" if not load(RESULT/"preflight/compatibility_report.json")["preflight_pass"] else
        "VFP_SEMANTIC_RELIABILITY_BLOCKED" if summary["VSR"]<1 else
        "GRAPH_ASSEMBLY_BLOCKED" if summary["GAR"]<1 else "SOLVER_INTEGRATION_BLOCKED")
    if decision != "VFP_SEMANTIC_RELIABILITY_BLOCKED": raise RuntimeError("unexpected blocked layer")
    save(RESULT/"experiment_config_snapshot.json",cfg)
    save(RESULT/"case_split.json",{"schema_version":"robotcad_try6_r1_v2_split_lock_v1",
        "development_subjects":["L04"],"formal_holdout_case_count":32,
        "formal_holdout_lock_sha256":sha(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json"),
        "formal_holdout_ids_not_read":True,"accessed":False,"evaluation_count":0})
    save(RESULT/"condition_parity.json",{"schema_version":"robotcad_try6_r1_v2_request_parity_v1",
        "declared_identical_inputs":True,"observed_exact_request_body_sha256":summary["exact_request_sha256"],
        "observed_exact_request_parity":summary["exact_request_parity"],"preflight_excluded":True,
        "only_variation":"independent API response/sample stochasticity"})
    save(RESULT/"holdout_evaluation_log.json",{"events":[],"followed_by_tuning":False,"accessed":False,"evaluation_count":0})
    failures = {"schema_version":"robotcad_try6_r1_v2_failure_accounting_v1","preflight_attempts":1,
        "preflight_accepted":1,"preflight_in_denominator":False,"reliability_requested":5,
        "reliability_completed":5,"transport_valid":summary["counts"]["transport_valid"],
        "semantic_valid":summary["counts"]["semantic_valid"],
        "canonical_kfdg_valid":summary["counts"]["canonical_kfdg_valid"],
        "semantic_failed":5-summary["counts"]["semantic_valid"],
        "all_attempt_ids":[f"call_{i:02d}" for i in range(1,6)],"excluded_attempt_ids":[],
        "solver_candidates":0,"cad_builds":0,"gt_evaluations":0,"formal_holdout_evaluations":0}
    save(RESULT/"failure_accounting.json",failures)
    ledger = {"schema_version":"robotcad_try6_r1_v2_claim_ledger_v1","claims":[
        {"claim":"projected schema accepted by API","evidence_type":"computed","artifact":"preflight/compatibility_report.json","field":"http_status / preflight_pass","expected":"200 / true"},
        {"claim":"five exact requests identical","evidence_type":"computed","artifact":"reliability/reliability_summary.json","field":"exact_request_parity","expected":True},
        {"claim":"TSR=5/5","evidence_type":"computed","artifact":"reliability/reliability_summary.json","field":"TSR","expected":1.0},
        {"claim":"VSR=1/5","evidence_type":"computed","artifact":"reliability/reliability_summary.json","field":"VSR","expected":0.2},
        {"claim":"GAR=1/5","evidence_type":"computed","artifact":"reliability/reliability_summary.json","field":"GAR","expected":0.2},
        {"claim":"E2E not reached","evidence_type":"computed","artifact":"validation.json","field":"e2e_not_run","expected":True},
        {"claim":"frozen prior results unchanged","evidence_type":"computed","artifact":"validation.json","field":"prior_result_hash_recheck","expected":"all unchanged"}
    ]}
    save(RESULT/"claim_ledger.json",ledger)
    validation = {"schema_version":"robotcad_try6_r1_v2_independent_validation_v1",
        "timestamp_utc":datetime.now(timezone.utc).isoformat(),"decision":decision,
        "production_preflight_pass":True,"representation_gate_pass":False,
        "TSR":summary["TSR"],"VSR":summary["VSR"],"GAR":summary["GAR"],
        "violations":summary["violation_counts"],"repair_count":summary["repair_count"],
        "exact_request_parity":summary["exact_request_parity"],
        "prior_result_hash_recheck":prior,"holdout_lock_closed":holdout_closed,
        "e2e_not_run":e2e_not_run,"solver_candidates":0,"cad_builds":0,
        "gt_evaluations":0,"formal_holdout_evaluations":0,"local_tests":test_report,
        "semantic_confounds":["joint/mount local-name substring filter may reject visible geometry descriptors",
            "prompt permits omitting visually unsupported pocket while gate requires pocket"]}
    save(RESULT/"validation.json",validation)
    head = subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    branch = subprocess.run(["git","branch","--show-current"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    sys.path.insert(0,str(ROOT/"experiments/try5A/scripts"))
    from freecad_runtime import python_runtime
    freecad = subprocess.run([python_runtime(),"-c","import FreeCAD,json;print(json.dumps(FreeCAD.Version()))"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    hashes = {str(path.relative_to(RESULT)).replace("\\","/"):sha(path) for path in RESULT.rglob("*") if path.is_file() and path.name!="manifest.json"}
    manifest = {"schema_version":"robotcad_try6_r1_v2_manifest_v1","decision":decision,
        "starting_commit":cfg["starting_commit"],"implementation_commit_before_calls":frozen["implementation_commit_before_calls"],
        "implementation_head_at_validation":head,"branch":branch,
        "protocol_sha256":frozen["protocol_sha256"],"frozen_hashes":frozen["frozen_hashes"],
        "api_schema_sha256":frozen["api_schema_sha256"],
        "projection_removed_paths":frozen["projection_removed_paths"],
        "preflight_report_sha256":frozen["preflight_report_sha256"],
        "source_files":frozen["source_files"],"image_hashes":{x["view"]:x["sha256"] for x in frozen["images"]},
        "model_requested":cfg["requested_model"],"model_returned":"qwen3.7-plus",
        "sdk_version":__import__("openai").__version__,"api_base_url":frozen["api_base_url"],
        "api_key_recorded":False,"python_executable":sys.executable,"freecad_version":freecad,
        "prior_results":prior,"formal_holdout_accessed":False,"formal_holdout_evaluation_count":0,
        "gt_evaluation_count":0,"solver_candidate_count":0,"result_file_sha256":hashes}
    save(RESULT/"manifest.json",manifest)
    print(json.dumps({"decision":decision,"TSR":summary["TSR"],"VSR":summary["VSR"],"GAR":summary["GAR"],"tests":test_report["run"]}))
    return validation


if __name__ == "__main__": finalize()
