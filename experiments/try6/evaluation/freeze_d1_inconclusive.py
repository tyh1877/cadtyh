"""Freeze independently validated D1 inconclusive diagnostic without semantic claims."""

from __future__ import annotations

import json
import subprocess
import unittest
from datetime import datetime,timezone

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try6.scripts.run_r1_reliability import save

RESULT=HERE/"results/try6_0_d1"


def main():
    validation=load(RESULT/"audit/independent_validation.json")
    if validation["decision"]!="DIAGNOSTIC_INCONCLUSIVE" or not validation["witness_not_run"]:
        raise RuntimeError("D1 independent failure gate not passed")
    if (RESULT/"manifest.json").exists():raise FileExistsError("D1 result already frozen")
    cfg=load(HERE/"protocol/try6_0_d1.json")
    pre=load(RESULT/"pre_run_manifest.json")
    if pre["protocol_sha256"]!=sha(HERE/"protocol/try6_0_d1.json"):
        raise RuntimeError("D1 protocol changed after freeze")
    suites=[unittest.defaultTestLoader.loadTestsFromName(name) for name in
        ("experiments.try6.tests.test_d1_protocol","experiments.try6.tests.test_d1_inconclusive")]
    tests=unittest.TestResult()
    for suite in suites:suite.run(tests)
    if not tests.wasSuccessful() or tests.testsRun<13:raise RuntimeError("D1 tests failed")
    lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"]!=0:raise RuntimeError("holdout lock violated")
    save(RESULT/"experiment_config_snapshot.json",cfg)
    save(RESULT/"condition_parity.json",load(RESULT/"frozen_inputs/parity_audit.json"))
    save(RESULT/"failure_accounting.json",{"schema_version":"robotcad_try6_d1_failure_accounting_v1",
        "planned_alignment_cases":65,"complete_alignment_cases_retained":0,
        "initial_alignment_attempts":1,"technical_retries":1,"additional_retries":0,
        "initial_failure_artifact_commit":validation["first_failure_commit"],
        "technical_retry_failure_sha256":validation["second_failure_sha256"],
        "witness_subsets_planned":len(cfg["witness_subsets"]),"witness_subsets_attempted":0,
        "VLM_calls":0,"GT_geometry_evaluations":0,
        "final_96_case_mechanics_evaluations":0,"formal_holdout_evaluations":0,
        "manual_intervention_count":0,"alignment_rate_evaluable":False})
    save(RESULT/"audit/leakage_audit.json",{"VLM_calls":0,"GT_geometry_evaluations":0,
        "C1_visual_objective_calls":0,"final_96_case_mechanics_evaluations":0,
        "alignment_used_existing_exact_classifier_only":True,
        "formal_holdout_accessed":False,"no_KFDE_or_CAD_design_change":True,
        "audit_limit":"code-path/artifact audit, not OS-level filesystem-read trace"})
    save(RESULT/"audit/holdout_audit.json",{"accessed":False,"evaluation_count":0,
        "lock_sha256":sha(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json"),
        "formal_holdout_case_data_read":False})
    save(RESULT/"validation.json",validation)
    ledger={"schema_version":"robotcad_try6_d1_claim_ledger_v1","claims":[
        {"claim":"C1/C2/D0 prior results unchanged","evidence_type":"computed","artifact":"audit/independent_validation.json","field":"frozen_prior_results","expected":"all unchanged"},
        {"claim":"all five source geometries available","evidence_type":"computed","artifact":"frozen_inputs/geometry_set.json","field":"status / geometries","expected":"PASS / 5"},
        {"claim":"F0 mutable-added BREP zero volume","evidence_type":"computed","artifact":"frozen_inputs/geometry_set.json","field":"G5_F0_COARSE.mutable_volume_mm3","expected":0.0},
        {"claim":"two technical failures retained","evidence_type":"computed","artifact":"audit/independent_validation.json","field":"initial_attempts / recorded_technical_retries","expected":"1 / 1"},
        {"claim":"alignment/witness non-evaluable","evidence_type":"computed","artifact":"audit/independent_validation.json","field":"complete_alignment_tables / witness_not_run","expected":"0 / true"},
        {"claim":"GT/VLM/final mechanics/holdout untouched","evidence_type":"computed","artifact":"failure_accounting.json","field":"GT_geometry_evaluations / VLM_calls / final_96_case_mechanics_evaluations / formal_holdout_evaluations","expected":"0 / 0 / 0 / 0"}
    ]}
    save(RESULT/"claim_ledger.json",ledger)
    head=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    branch=subprocess.run(["git","branch","--show-current"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    source_paths={"geometry_inspection":HERE/"evaluation/freecad_d1_inspect_geometry.py",
        "alignment_worker":HERE/"evaluation/freecad_d1_alignment.py",
        "alignment_runner":HERE/"scripts/run_d1_alignment.py",
        "witness_worker_not_run":HERE/"evaluation/freecad_d1_witness.py",
        "independent_failure_validator":HERE/"evaluation/validate_d1_inconclusive.py",
        "existing_exact_mechanics":ROOT/cfg["exact_mechanics_source"]}
    hashes={str(p.relative_to(RESULT)).replace("\\","/"):sha(p) for p in RESULT.rglob("*") if p.is_file() and p.name!="manifest.json"}
    manifest={"schema_version":"robotcad_try6_d1_manifest_v1","experiment_id":cfg["experiment_id"],
        "decision":"DIAGNOSTIC_INCONCLUSIVE","starting_commit":cfg["starting_commit"],
        "implementation_commit_before_D1":pre["implementation_commit_before_D1"],
        "technical_incident_commit":validation["first_failure_commit"],
        "result_freeze_parent_commit":head,"branch":branch,
        "protocol_sha256":sha(HERE/"protocol/try6_0_d1.json"),
        "prior_results":validation["frozen_prior_results"],
        "five_geometry_source_hashes":{x["geometry_id"]:x["source_sha256"] for x in load(RESULT/"frozen_inputs/geometry_set.json")["geometries"]},
        "KFDE_construction_sha256":pre["KFDE_construction_sha256"],
        "KFDE_keepout_sha256":pre["KFDE_keepout_sha256"],
        "allowed_contact_sha256":pre["allowed_contact_sha256"],
        "KFDE_component_hashes":load(RESULT/"frozen_inputs/kfde_reference.json")["component_hashes"],
        "URDF_sha256":pre["URDF_sha256"],
        "exact_mechanics_source_sha256":pre["exact_mechanics_source_sha256"],
        "exact_mechanics_wrapper_sha256":pre["exact_mechanics_wrapper_sha256"],
        "witness_config_protocol_sha256":pre["protocol_sha256"],
        "source_sha256":{name:sha(path) for name,path in source_paths.items()},
        "FreeCAD_version":pre["FreeCAD_version"],"python_environment":".venv/Scripts/python.exe",
        "VLM_calls":0,"GT_geometry_evaluations":0,
        "final_96_case_mechanics_evaluations":0,"formal_holdout_accessed":False,
        "formal_holdout_evaluation_count":0,"local_test_count":tests.testsRun,
        "result_file_sha256":hashes,"created_utc":datetime.now(timezone.utc).isoformat()}
    save(RESULT/"manifest.json",manifest)
    print(json.dumps({"decision":"DIAGNOSTIC_INCONCLUSIVE","complete_alignment_tables":0,
        "witness_attempts":0,"tests":tests.testsRun,"GT_evaluations":0,"holdout_accessed":False}))


if __name__=="__main__":main()
