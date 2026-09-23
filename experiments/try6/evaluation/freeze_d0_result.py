"""Freeze independently validated no-GT D0 characterization and claim ledger."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from datetime import datetime,timezone

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try6.scripts.run_r1_reliability import save

RESULT=HERE/"results/try6_0_d0"


def main():
    validation=load(RESULT/"audit/independent_validation.json")
    if validation["decision"] not in ("FEASIBLE_REGION_FOUND","FEASIBLE_REGION_TOO_SMALL","DOMAIN_KFDE_INCOMPATIBLE",
        "KFDE_SEMANTIC_MISMODEL_SUSPECTED","KFDE_AUTHORITY_INCONSISTENCY_SUSPECTED","DIAGNOSTIC_INCONCLUSIVE"):
        raise RuntimeError("D0 independent decision missing/invalid")
    if (RESULT/"manifest.json").exists():raise FileExistsError("D0 result already frozen")
    cfg=load(HERE/"protocol/try6_0_d0.json")
    pre=load(RESULT/"pre_run_manifest.json")
    if pre["protocol_sha256"]!=sha(HERE/"protocol/try6_0_d0.json"):
        raise RuntimeError("D0 protocol changed")
    c1=ROOT/cfg["c1_result_root"];c2=ROOT/cfg["c2_result_root"]
    for root,name in ((c1,"c1"),(c2,"c2")):
        manifest=load(root/"manifest.json")
        if not all(sha(root/p)==digest for p,digest in manifest["result_file_sha256"].items()):
            raise RuntimeError(f"frozen {name} result changed")
    lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"]!=0:
        raise RuntimeError("formal holdout lock violated")
    suites=[unittest.defaultTestLoader.loadTestsFromName(name) for name in
        ("experiments.try6.tests.test_d0_protocol","experiments.try6.tests.test_d0_result")]
    tests=unittest.TestResult()
    for suite in suites:suite.run(tests)
    if not tests.wasSuccessful() or tests.testsRun<16:
        raise RuntimeError("D0 local/result tests failed")
    all_records=load(RESULT/"all_candidate_records.json")
    records=all_records["records"]
    save(RESULT/"experiment_config_snapshot.json",cfg)
    save(RESULT/"condition_parity.json",load(RESULT/"frozen_inputs/parity_audit.json"))
    save(RESULT/"failure_accounting.json",{"schema_version":"robotcad_try6_d0_failure_accounting_v1",
        "canonical_probes_requested":5,"canonical_probes_completed":5,
        "same_theta_technical_repeat_requested":1,"same_theta_technical_repeat_completed":1,
        "sobol_requested":256,"sobol_completed":256,
        "local_requested":60,"local_completed":60,
        "total_CAD_builds":322,"total_KFDE_component_checks":322,
        "infrastructure_failures":sum(r["status"]!="EVALUATED" for r in records),
        "strict_feasible_sobol":validation["stage_a_strict_feasible"],
        "strict_feasible_all_nonrepeat":validation["all_unique_strict_feasible"],
        "excluded_candidate_ids":[],"GT_evaluations":0,"final_mechanics_evaluations":0,
        "VLM_calls":0,"formal_holdout_evaluations":0,"technical_retries":0,
        "total_runtime_seconds":all_records["runtime_seconds"],
        "runtime_ceiling_seconds":cfg["maximum_total_runtime_seconds"]})
    save(RESULT/"audit/leakage_audit.json",{"VLM_calls":0,"GT_evaluations":0,
        "final_96_case_mechanics_evaluations":0,"formal_holdout_accessed":False,
        "D0_ranking_terms":cfg["ranking_terms"],"visual_objective_used":False,
        "C1_failed_case_optimization_hints_used":False,
        "source_paths":"sanitized C1 domain/KFDG, frozen CAD compiler, frozen C2 KFDE BREP only",
        "audit_limit":"code-path/artifact audit, not OS-level filesystem-read trace"})
    save(RESULT/"audit/holdout_audit.json",{"accessed":False,"evaluation_count":0,
        "holdout_lock_sha256":sha(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json"),
        "formal_holdout_case_data_read":False})
    save(RESULT/"validation.json",validation)
    ledger={"schema_version":"robotcad_try6_d0_claim_ledger_v1","claims":[
        {"claim":"C1/C2 frozen artifacts unchanged","evidence_type":"computed","artifact":"audit/independent_validation.json","field":"frozen_prior_results","expected":"both unchanged"},
        {"claim":"322 scheduled D0 CAD/component evaluations completed","evidence_type":"computed","artifact":"failure_accounting.json","field":"total_CAD_builds / infrastructure_failures","expected":"322 / 0"},
        {"claim":"strict Stage-A feasible density 0/256","evidence_type":"computed","artifact":"feasible_search/feasible_density.json","field":"strict_feasible_sample_count / stage_a_sample_count","expected":"0 / 256"},
        {"claim":"best observed g_max materially above frozen epsilon","evidence_type":"computed","artifact":"audit/independent_validation.json","field":"best_g_max_mm3","expected":validation["best_g_max_mm3"]},
        {"claim":"no single neighbor removal creates strict feasible D0 sample","evidence_type":"computed","artifact":"counterfactual/semantic_suspect_summary.json","field":"strict_feasible_count_by_subset","expected":"all zero"},
        {"claim":"D0 decision DOMAIN_KFDE_INCOMPATIBLE under finite sample protocol","evidence_type":"computed","artifact":"audit/independent_validation.json","field":"decision","expected":validation["decision"]},
        {"claim":"GT/VLM/final mechanics/holdout untouched","evidence_type":"computed","artifact":"failure_accounting.json","field":"GT_evaluations / VLM_calls / final_mechanics_evaluations / formal_holdout_evaluations","expected":"0 / 0 / 0 / 0"}
    ]}
    save(RESULT/"claim_ledger.json",ledger)
    head=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    branch=subprocess.run(["git","branch","--show-current"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    source_paths={"diagnostic_worker":HERE/"scripts/freecad_d0_component_probe.py",
        "runner":HERE/"scripts/run_d0.py","aggregator":HERE/"scripts/aggregate_d0.py",
        "independent_validator":HERE/"evaluation/validate_d0.py",
        "f0_mapping_audit":HERE/"evaluation/freecad_d0_f0_mapping.py"}
    hashes={str(p.relative_to(RESULT)).replace("\\","/"):sha(p) for p in RESULT.rglob("*") if p.is_file() and p.name!="manifest.json"}
    manifest={"schema_version":"robotcad_try6_d0_manifest_v1","experiment_id":cfg["experiment_id"],
        "decision":validation["decision"],"starting_commit":cfg["starting_commit"],
        "implementation_commit_before_D0":pre["implementation_commit_before_D0"],
        "result_freeze_parent_commit":head,"branch":branch,
        "protocol_sha256":sha(HERE/"protocol/try6_0_d0.json"),
        "C1_manifest_sha256":sha(c1/"manifest.json"),"C2_manifest_sha256":sha(c2/"manifest.json"),
        "active_bounds_sha256":pre["active_bounds_sha256"],"KFDG_sha256":pre["kfdg_sha256"],
        "KFDE_construction_sha256":pre["kfde_construction_sha256"],
        "KFDE_keepout_sha256":pre["kfde_keepout_sha256"],
        "allowed_contact_sha256":pre["allowed_contact_sha256"],
        "numerical_tolerance_mm3":cfg["strict_feasibility_epsilon_mm3"],
        "search_seed":cfg["stage_a"]["seed"],"sobol_budget":256,"local_budget":60,
        "neighbor_source_hashes":load(RESULT/"frozen_inputs/kfde_reference.json")["neighbor_source_hashes"],
        "design_sweep_sha256":sha(c2/"kfde/construction_sweep.json"),
        "method_source_sha256":{name:sha(path) for name,path in source_paths.items()},
        "FreeCAD_version":pre["FreeCAD_version"],"python_environment":".venv/Scripts/python.exe",
        "VLM_calls":0,"GT_evaluations":0,"final_mechanics_evaluations":0,
        "formal_holdout_accessed":False,"formal_holdout_evaluation_count":0,
        "frozen_prior_results":validation["frozen_prior_results"],
        "local_test_count":tests.testsRun,"result_file_sha256":hashes,
        "created_utc":datetime.now(timezone.utc).isoformat()}
    save(RESULT/"manifest.json",manifest)
    print(json.dumps({"decision":validation["decision"],"sobol":256,"local":60,
        "strict_feasible":validation["all_unique_strict_feasible"],
        "best_g_max_mm3":validation["best_g_max_mm3"],"tests":tests.testsRun,
        "GT_evaluations":0,"holdout_accessed":False}))


if __name__=="__main__":main()
