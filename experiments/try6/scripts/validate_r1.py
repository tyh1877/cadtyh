"""Independent post-run R1 representation validator; never reads GT/holdout cases."""

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

RESULT = HERE / "results/try6_0_r1"


def save(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def pair_agreement(items, transform):
    pairs = [(a,b) for a,b in combinations(range(len(items)),2) if items[a] is not None and items[b] is not None]
    if not pairs: return None
    return sum(transform(items[a]) == transform(items[b]) for a,b in pairs) / len(pairs)


def representation():
    cfg = load(HERE / "protocol/r1_protocol.json")
    pre = load(RESULT / "preflight.json")
    if pre["protocol_sha256"] != sha(HERE / "protocol/r1_protocol.json"):
        raise RuntimeError("frozen protocol drift")
    for key,expected in pre["frozen_hashes"].items():
        if sha(ROOT / cfg[key]) != expected: raise RuntimeError(f"frozen {key} drift")
    schema = load(ROOT / cfg["vfp_schema"])
    calls = []
    proposals = []
    request_hashes = []
    all_evidence_hashes = {i["view"]:i["sha256"] for i in pre["images"]}
    for number in range(1,cfg["independent_calls"]+1):
        name = f"call_{number:02d}"
        folder = RESULT / "reliability" / name
        recorded = load(folder / "call_result.json")
        request_metadata = load(folder / "request_metadata.json") if (folder / "request_metadata.json").exists() else None
        check = {"call_number":number,"attempt_exists":(folder / "attempt_started.json").exists(),
                 "raw_schema_valid":False,"semantic_valid":False,"assembly_success":False,"canonical_kfdg_valid":False,
                 "response_repair_count":0,"duplicate_reference_count":0,"dangling_reference_count":0,
                 "unsupported_feature_count":0,"recorded_status":recorded["status"],"error":None}
        proposal = None
        if request_metadata:
            exact = ROOT / recorded["exact_http_request_path"]
            if sha(exact) != request_metadata["exact_request_sha256"]:
                raise RuntimeError(f"exact request hash mismatch {name}")
            sent = load(exact)
            if sent["response_format"]["json_schema"]["schema"] != schema or sent["response_format"]["json_schema"]["strict"] is not True:
                raise RuntimeError(f"schema not actually sent {name}")
            if (sent["model"],sent["temperature"],sent["top_p"],sent["seed"],sent["max_tokens"]) != (cfg["requested_model"],cfg["temperature"],cfg["top_p"],cfg["seed"],cfg["max_output_tokens"]):
                raise RuntimeError(f"model/budget parity mismatch {name}")
            if sent["messages"][0]["content"] != (ROOT / cfg["prompt"]).read_text(encoding="utf-8"):
                raise RuntimeError(f"exact prompt mismatch {name}")
            pieces = sent["messages"][1]["content"]
            expected_engineering = "Engineering description for L04:\n" + (ROOT / pre["source_files"]["engineering_text"]["path"]).read_text(encoding="utf-8")
            if len(pieces) != 1 + 2*len(pre["images"]) or pieces[0]["text"] != expected_engineering:
                raise RuntimeError(f"engineering text or image count mismatch {name}")
            for index,image in enumerate(pre["images"]):
                if pieces[1+2*index]["text"] != "Evidence view: "+image["view"]:
                    raise RuntimeError(f"view label mismatch {name}: {image['view']}")
                url = pieces[2+2*index]["image_url"]["url"]
                if not url.startswith("data:image/png;base64,") or hashlib.sha256(base64.b64decode(url.split(",",1)[1])).hexdigest() != image["sha256"]:
                    raise RuntimeError(f"image bytes mismatch {name}: {image['view']}")
            if request_metadata["image_hashes"] != all_evidence_hashes:
                raise RuntimeError(f"image evidence parity mismatch {name}")
            request_hashes.append(request_metadata["exact_request_sha256"])
        if (folder / "raw_response.txt").is_file():
            raw = (folder / "raw_response.txt").read_text(encoding="utf-8")
            http = load(folder / "http_response.json")
            sdk = load(folder / "sdk_response.json")
            if raw != http["choices"][0]["message"]["content"] or raw != sdk["choices"][0]["message"]["content"]:
                raise RuntimeError(f"HTTP/SDK raw mismatch {name}")
            try:
                parsed = json.loads(raw)
                if isinstance(parsed,dict) and isinstance(parsed.get("visual_features"),list):
                    for feature in parsed["visual_features"]:
                        if isinstance(feature,dict) and (feature.get("feature_type") not in {"main_housing","pocket","profile_transition"} or any(term in str(feature.get("local_name","")) for term in FORBIDDEN_VISUAL_TERMS)):
                            check["unsupported_feature_count"] += 1
                Draft202012Validator(schema).validate(parsed)
                check["raw_schema_valid"] = True
                proposal = parsed
                checked = validate_vfp(parsed)
                check["semantic_valid"] = True
                if (folder / "validated_vfp.json").is_file() and load(folder / "validated_vfp.json") != parsed:
                    check["response_repair_count"] += 1
                assembled = assemble(checked)
                check["assembly_success"] = True
                existing = RESULT / "canonical_kfdg" / f"{name}_kfdg.json"
                if not existing.is_file() or load(existing) != assembled:
                    raise RuntimeError("stored graph differs from independent deterministic assembly")
                validate_kfdg(assembled,checked)
                check["canonical_kfdg_valid"] = True
                for feature in assembled["geometric_features"]:
                    check["duplicate_reference_count"] += len(feature["parameter_refs"])-len(set(feature["parameter_refs"]))
                    ids = {p["id"] for p in assembled["parameters"]}
                    check["dangling_reference_count"] += sum(ref not in ids for ref in feature["parameter_refs"])
            except Exception as error:
                check["error"] = f"{type(error).__name__}: {error}"
        else:
            check["error"] = recorded.get("error","raw response missing")
        calls.append(check)
        proposals.append(proposal)
    request_parity = len(request_hashes) == cfg["independent_calls"] and len(set(request_hashes)) == 1
    consistency = {"denominator_calls":cfg["independent_calls"],"possible_pair_count":cfg["independent_calls"]*(cfg["independent_calls"]-1)//2,
        "evaluable_pair_count":sum(a is not None and b is not None for a,b in combinations(proposals,2)),
        "feature_type_agreement":pair_agreement(proposals,lambda x:sorted(f["feature_type"] for f in x["visual_features"])),
        "feature_count_agreement":pair_agreement(proposals,lambda x:len(x["visual_features"])),
        "role_agreement":pair_agreement(proposals,lambda x:sorted((f["feature_type"],tuple(sorted(f["parameter_roles"]))) for f in x["visual_features"])),
        "relation_agreement":pair_agreement(proposals,lambda x:sorted((f["feature_type"],canonical(f["relations"])) for f in x["visual_features"])),
        "missing_or_unparseable_proposals":sum(p is None for p in proposals)}
    save(RESULT / "reliability/proposal_consistency.json",consistency)
    denom = cfg["independent_calls"]
    counts = {key:sum(bool(c[key]) for c in calls) for key in ("raw_schema_valid","semantic_valid","assembly_success","canonical_kfdg_valid")}
    totals = {key:sum(c[key] for c in calls) for key in ("response_repair_count","duplicate_reference_count","dangling_reference_count","unsupported_feature_count")}
    gate = (len(calls)==denom and request_parity and all(value==denom for value in counts.values()) and
            all(value==0 for value in totals.values()) and all(c["attempt_exists"] for c in calls))
    summary = {"schema_version":"robotcad_try6_r1_reliability_summary_v1","timestamp_utc":datetime.now(timezone.utc).isoformat(),
        "requested_calls":denom,"attempts_retained":sum(c["attempt_exists"] for c in calls),"exact_request_body_parity":request_parity,
        "request_sha256":request_hashes[0] if request_parity else None,
        "raw_schema_validity_rate":counts["raw_schema_valid"]/denom,"vfp_semantic_validity_rate":counts["semantic_valid"]/denom,
        "graph_assembly_success_rate":counts["assembly_success"]/denom,"canonical_kfdg_validity_rate":counts["canonical_kfdg_valid"]/denom,
        "no_repair_rate":1-totals["response_repair_count"]/denom,
        "counts":counts,"totals":totals,"calls":calls,"representation_gate_pass":gate,
        "gt_evaluations":0,"formal_holdout_evaluations":0}
    save(RESULT / "reliability/reliability_summary.json",summary)
    save(RESULT / "canonical_kfdg/validator_report.json",{"representation_gate_pass":gate,
        "canonical_valid_count":counts["canonical_kfdg_valid"],"duplicate_refs":totals["duplicate_reference_count"],
        "dangling_refs":totals["dangling_reference_count"],"per_call":[{"call_number":c["call_number"],"valid":c["canonical_kfdg_valid"],"error":c["error"]} for c in calls]})
    print(json.dumps({"representation_gate_pass":gate,"counts":counts,"request_parity":request_parity,"totals":totals}))
    return summary


def finalize():
    summary = representation()
    cfg = load(HERE / "protocol/r1_protocol.json")
    pre = load(RESULT / "preflight.json")
    frozen_recheck = {}
    for key,folder in (("c1_v1",HERE / "results/try6_0_c1"),("r0",HERE / "results/try6_0_r0")):
        manifest = load(folder / "manifest.json")
        prior = pre["frozen_prior_results"][key]
        hashes = manifest.get("lightweight_result_sha256",manifest.get("result_file_sha256",{}))
        unchanged = sha(folder / "manifest.json") == prior["manifest_sha256"] and all(sha(folder / name) == expected for name,expected in hashes.items())
        frozen_recheck[key] = {"unchanged":unchanged,"file_count":len(hashes)}
    lock = load(ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    holdout_closed = lock["accessed"] is False and lock["evaluation_count"] == 0
    suite = unittest.defaultTestLoader.loadTestsFromName("experiments.try6.tests.test_r1_contract")
    test_result = unittest.TestResult(); suite.run(test_result)
    local_tests = {"run":test_result.testsRun,"errors":len(test_result.errors),"failures":len(test_result.failures),
                   "pass":test_result.wasSuccessful() and test_result.testsRun >= 23}
    attempts = [load(RESULT / "reliability" / f"call_{i:02d}" / "call_result.json") for i in range(1,cfg["independent_calls"]+1)]
    api_rejections = [a["call_number"] for a in attempts if a.get("http_status") == 400 or "BadRequestError" in a.get("error","")]
    error_texts = [a.get("error","") for a in attempts]
    uniqueitems_rejected = len(api_rejections) == cfg["independent_calls"] and all("uniqueItems" in text for text in error_texts)
    for item in attempts:
        folder = RESULT / "reliability" / f"call_{item['call_number']:02d}"
        if not (folder / "raw_response.txt").exists():
            save(folder / "raw_response_absence.json",{"model_content_present":False,"reason":"API_400_SCHEMA_REJECTED",
                "http_error_artifact":"http_response.json","not_a_model_semantic_validation":True})
    e2e_path = RESULT / "e2e_smoke"
    e2e_not_run = not e2e_path.exists()
    decision = "SEMANTIC_CONTRACT_BLOCKED" if not summary["representation_gate_pass"] else ("SOLVER_INTEGRATION_BLOCKED" if e2e_not_run else "READY_FOR_C1_V2")
    if decision != "SEMANTIC_CONTRACT_BLOCKED":
        raise RuntimeError("this validator run expects the frozen five-attempt representation failure")
    if not all(x["unchanged"] for x in frozen_recheck.values()) or not holdout_closed or not local_tests["pass"]:
        raise RuntimeError("R1 independent freeze/holdout/test validation failed")
    if not uniqueitems_rejected or not e2e_not_run or not summary["exact_request_body_parity"]:
        raise RuntimeError("API rejection classification or stop rule not independently supported")
    failure_accounting = {"schema_version":"robotcad_try6_r1_failure_accounting_v1","requested_http_attempts":5,
        "completed_http_attempts":5,"api_schema_rejections":len(api_rejections),"model_generations":0,
        "raw_vfp_available":0,"semantic_vfp_pass":0,"assembly_pass":0,"canonical_kfdg_pass":0,
        "solver_candidates":0,"gt_evaluations":0,"formal_holdout_evaluations":0,
        "all_attempt_ids":[f"call_{i:02d}" for i in range(1,6)],"excluded_attempt_ids":[]}
    save(RESULT / "failure_accounting.json",failure_accounting)
    claims = [
        {"claim":"five identical API attempts","evidence_type":"computed","artifact":"reliability/reliability_summary.json","field":"exact_request_body_parity","expected":True},
        {"claim":"all attempts rejected by API schema parser","evidence_type":"computed","artifact":"validation.json","field":"api_schema_rejections","expected":5},
        {"claim":"no VFP semantic reliability result","evidence_type":"computed","artifact":"failure_accounting.json","field":"model_generations","expected":0},
        {"claim":"prior results unchanged","evidence_type":"computed","artifact":"validation.json","field":"frozen_prior_results_recheck","expected":"all unchanged"},
        {"claim":"GT and holdout untouched","evidence_type":"computed","artifact":"validation.json","field":"gt_evaluations / holdout_lock","expected":"0 / closed"}
    ]
    save(RESULT / "claim_ledger.json",{"schema_version":"robotcad_try6_r1_claim_ledger_v1","claims":claims})
    validation = {"schema_version":"robotcad_try6_r1_independent_validation_v1","timestamp_utc":datetime.now(timezone.utc).isoformat(),
        "decision":decision,"failure_subtype":"VFP_SCHEMA_API_REJECTED","api_schema_rejections":len(api_rejections),
        "api_error_fingerprint":"uniqueItems array-keyword rejected by endpoint", "representation_gate_pass":False,
        "exact_request_body_parity":summary["exact_request_body_parity"],
        "frozen_prior_results_recheck":frozen_recheck,"holdout_lock":{"accessed":False,"evaluation_count":0,"closed":holdout_closed},
        "gt_evaluations":0,"solver_candidates":0,"e2e_not_run":e2e_not_run,"local_contract_tests":local_tests,
        "response_repair_count":0,"retries":0}
    save(RESULT / "validation.json",validation)
    commit = subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    branch = subprocess.run(["git","branch","--show-current"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    artifact_hashes = {str(p.relative_to(RESULT)).replace("\\","/"):sha(p) for p in RESULT.rglob("*") if p.is_file() and p.name != "manifest.json"}
    manifest = {"schema_version":"robotcad_try6_r1_manifest_v1","decision":decision,"failure_subtype":"VFP_SCHEMA_API_REJECTED",
        "starting_commit":cfg["starting_commit"],"implementation_head_at_validation":commit,"branch":branch,
        "protocol_sha256":pre["protocol_sha256"],"frozen_hashes":pre["frozen_hashes"],
        "source_files":pre["source_files"],"image_hashes":{i["view"]:i["sha256"] for i in pre["images"]},
        "model_requested":cfg["requested_model"],"model_returned":None,"model_generations":0,
        "api_base_url":pre["api_base_url"],"api_key_recorded":False,
        "sdk_version":__import__("openai").__version__,"python_executable":sys.executable,
        "freecad_version":pre["freecad_version"],"frozen_prior_results":frozen_recheck,
        "formal_holdout_accessed":False,"formal_holdout_evaluation_count":0,"gt_evaluation_count":0,
        "result_file_sha256":artifact_hashes}
    save(RESULT / "manifest.json",manifest)
    print(json.dumps({"decision":decision,"failure_subtype":"VFP_SCHEMA_API_REJECTED","api_rejections":len(api_rejections),"local_tests":local_tests["run"]}))
    return validation


if __name__ == "__main__": finalize()
