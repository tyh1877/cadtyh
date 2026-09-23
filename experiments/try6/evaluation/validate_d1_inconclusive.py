"""Independent D1 fail-closed audit after the single recorded technical retry."""

from __future__ import annotations

import hashlib
import json
import subprocess

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try6.scripts.run_r1_reliability import save

RESULT=HERE/"results/try6_0_d1"
FIRST_FAILURE_COMMIT="3a33ca3"
FIRST_FAILURE_REPO_PATH="experiments/try6/results/try6_0_d1/alignment/failure.json"


def prior(root):
    manifest=load(root/"manifest.json")
    if not all(sha(root/path)==digest for path,digest in manifest["result_file_sha256"].items()):
        raise RuntimeError(f"frozen prior result drift: {root}")
    return {"manifest_sha256":sha(root/"manifest.json"),"files_checked":len(manifest["result_file_sha256"]),"unchanged":True}


def validate():
    cfg=load(HERE/"protocol/try6_0_d1.json")
    pre=load(RESULT/"pre_run_manifest.json")
    if pre["status"]!="READY_FOR_FROZEN_ALIGNMENT_AND_WITNESS" or pre["protocol_sha256"]!=sha(HERE/"protocol/try6_0_d1.json"):
        raise RuntimeError("D1 protocol drift")
    priors={name:prior(ROOT/cfg[key]) for name,key in (("c1_v2","c1_result_root"),("c2","c2_result_root"),("d0","d0_result_root"))}
    geometry=load(RESULT/"frozen_inputs/geometry_set.json")
    if geometry["status"]!="PASS" or len(geometry["geometries"])!=5:
        raise RuntimeError("frozen geometry set invalid")
    if any(sha(ROOT/item["source_path"])!=item["source_sha256"] for item in geometry["geometries"]):
        raise RuntimeError("D1 geometry source changed")
    construction=load(ROOT/cfg["kfde_construction"])
    if sha(ROOT/construction["keepout"]["path"])!=construction["keepout"]["sha256"] or sha(ROOT/construction["allowed_region"]["path"])!=construction["allowed_region"]["sha256"]:
        raise RuntimeError("D1 KFDE artifact drift")
    if sha(ROOT/cfg["exact_mechanics_source"])!=pre["exact_mechanics_source_sha256"]:
        raise RuntimeError("exact mechanics classifier modified")
    marker=load(RESULT/"alignment/technical_retry_started.json")
    if marker["max_technical_retries"]!=1 or marker["scientific_protocol_unchanged"] is not True:
        raise RuntimeError("technical retry scope exceeded")
    blob=subprocess.run(["git","show",f"{FIRST_FAILURE_COMMIT}:{FIRST_FAILURE_REPO_PATH}"],
        cwd=ROOT,capture_output=True,check=True).stdout
    # Git normalizes tracked JSON to LF while the Windows working artifact
    # retained CRLF when the retry marker recorded its SHA-256.
    if hashlib.sha256(blob.replace(b"\n",b"\r\n")).hexdigest()!=marker["first_failure_sha256"]:
        raise RuntimeError("first D1 failure artifact not preserved")
    first=json.loads(blob.decode("utf-8"))
    second=load(RESULT/"alignment/failure.json")
    if first["status"]!="DIAGNOSTIC_INCONCLUSIVE" or second["status"]!="DIAGNOSTIC_INCONCLUSIVE":
        raise RuntimeError("technical failures not retained")
    if "ValueError: Null shape" not in first["error"] or "ValueError: Null shape" not in second["error"]:
        raise RuntimeError("technical failure mechanism drift")
    if (RESULT/"alignment/raw_alignment.json").exists() or (RESULT/"witness/witness_summary.json").exists():
        raise RuntimeError("partial D1 diagnostics were incorrectly promoted")
    lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"]!=0:
        raise RuntimeError("formal holdout lock violated")
    result={"schema_version":"robotcad_try6_d1_independent_inconclusive_v1",
        "decision":"DIAGNOSTIC_INCONCLUSIVE","reason":"G5 actual F0 mutable scope yields non-cuttable zero-volume BREP; two frozen-protocol alignment attempts failed before a 65-case table could be written",
        "planned_geometry_pose_cases":65,"complete_alignment_tables":0,
        "initial_attempts":1,"recorded_technical_retries":1,"further_retries":0,
        "first_failure_commit":FIRST_FAILURE_COMMIT,"first_failure_sha256":marker["first_failure_sha256"],
        "second_failure_sha256":sha(RESULT/"alignment/failure.json"),
        "witness_not_run":True,"alignment_rate_not_evaluable":True,
        "KFDE_semantics_not_classified":True,"relief_capacity_not_classified":True,
        "frozen_prior_results":priors,"geometry_set_unchanged":True,"KFDE_unchanged":True,
        "exact_classifier_unchanged":True,"VLM_calls":0,"GT_geometry_evaluations":0,
        "final_96_case_mechanics_evaluations":0,"formal_holdout_accessed":False,
        "formal_holdout_evaluation_count":0}
    save(RESULT/"audit/independent_validation.json",result)
    print(json.dumps({"decision":result["decision"],"complete_alignment_tables":0,
        "technical_attempts":2,"witness_not_run":True,"GT_evaluations":0}))
    return result


if __name__=="__main__":validate()
