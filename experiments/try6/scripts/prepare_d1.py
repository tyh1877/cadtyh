"""Freeze D1 geometry/pose/exact-semantics/witness policy before diagnostics."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime,timezone

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try6.scripts.run_r1_reliability import save

sys.path.insert(0,str(ROOT/"experiments/try5A/scripts"))
from freecad_runtime import python_runtime

RESULT=HERE/"results/try6_0_d1"
ARTIFACT=HERE/"artifacts/try6_0_d1"


def prior(root):
    manifest=load(root/"manifest.json")
    if not all(sha(root/p)==digest for p,digest in manifest["result_file_sha256"].items()):
        raise RuntimeError(f"prior frozen result drift: {root}")
    return {"manifest_sha256":sha(root/"manifest.json"),"files_checked":len(manifest["result_file_sha256"]),"unchanged":True}


def main():
    cfg=load(HERE/"protocol/try6_0_d1.json")
    if (RESULT/"pre_run_manifest.json").exists():raise FileExistsError("D1 already prepared")
    priors={name:prior(ROOT/cfg[key]) for name,key in (("c1_v2","c1_result_root"),("c2","c2_result_root"),("d0","d0_result_root"))}
    if load(ROOT/cfg["d0_result_root"]/"validation.json")["decision"]!="DOMAIN_KFDE_INCOMPATIBLE":
        raise RuntimeError("frozen D0 decision drift")
    construction=load(ROOT/cfg["kfde_construction"])
    if construction["status"]!="PASS" or len(construction["components"])!=13:
        raise RuntimeError("frozen 13-component KFDE unavailable")
    if cfg["kfde_numerical_epsilon_mm3"]!=construction["numerical_tolerance_mm3"]:
        raise RuntimeError("D1 numerical tolerance differs from KFDE")
    if sha(ROOT/construction["keepout"]["path"])!=construction["keepout"]["sha256"] or sha(ROOT/construction["allowed_region"]["path"])!=construction["allowed_region"]["sha256"]:
        raise RuntimeError("KFDE/allowed BREP drift")
    c1_pre=load(ROOT/cfg["c1_result_root"]/"pre_run_manifest.json")
    if sha(ROOT/cfg["exact_mechanics_source"])!=sha(ROOT/"experiments/try5A/scripts/freecad_motion_realization.py"):
        raise RuntimeError("exact mechanics source drift")
    exact_wrapper=ROOT/"experiments/try5A/evaluation/mechanical/freecad_holdout_evaluator.py"
    if sha(exact_wrapper)!=c1_pre["evaluator_hashes"]["mechanical_evaluator"]:
        raise RuntimeError("exact mechanics evaluator wrapper differs from frozen C1")
    if sha(ROOT/cfg["sanitized_urdf"])!=load(ROOT/cfg["c2_result_root"]/"pre_run_manifest.json")["source_hashes"]["sanitized_urdf"]:
        raise RuntimeError("sanitized URDF drift")
    lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"]!=0:raise RuntimeError("holdout lock violated")
    ARTIFACT.mkdir(parents=True,exist_ok=True)
    job={"protocol":"experiments/try6/protocol/try6_0_d1.json",
        "artifact_root":"experiments/try6/artifacts/try6_0_d1/geometry_set",
        "output":"experiments/try6/results/try6_0_d1/frozen_inputs/geometry_set.json"}
    save(ARTIFACT/"geometry_inspection_job.json",job)
    proc=subprocess.run([python_runtime(),str(HERE/"evaluation/freecad_d1_inspect_geometry.py"),str(ARTIFACT/"geometry_inspection_job.json")],
        cwd=ROOT,capture_output=True,text=True,timeout=180)
    (ARTIFACT/"geometry_inspection_stdout.txt").write_text(proc.stdout,encoding="utf-8")
    (ARTIFACT/"geometry_inspection_stderr.txt").write_text(proc.stderr,encoding="utf-8")
    if proc.returncode:raise RuntimeError(f"D1 geometry-set inspection failed: {proc.stderr[-1200:]}")
    geometry=load(RESULT/"frozen_inputs/geometry_set.json")
    if geometry["status"]!="PASS":raise RuntimeError("D1 frozen geometry set invalid")
    save(RESULT/"protocol.json",cfg)
    save(RESULT/"frozen_inputs/c1_reference.json",{"c1_final_lock_sha256":sha(ROOT/cfg["c1_result_root"]/"evaluation/final_candidate_lock.json"),
        "C1_mutable_source_path":cfg["geometry_set"][0]["path"],
        "slot_state_sha256":sha(ROOT/cfg["c1_result_root"]/"slot/validated_slots.json"),
        "KFDG_sha256":sha(ROOT/cfg["c1_result_root"]/"kfdg/canonical_kfdg.json"),
        "visual_objective_not_used":True})
    save(RESULT/"frozen_inputs/kfde_reference.json",{"construction_report_path":cfg["kfde_construction"],
        "construction_report_sha256":sha(ROOT/cfg["kfde_construction"]),
        "keepout_sha256":construction["keepout"]["sha256"],
        "allowed_contact_sha256":construction["allowed_region"]["sha256"],
        "component_hashes":{x["component_id"]:x["brep_sha256"] for x in construction["components"]},
        "construction_sweep_sha256":sha(ROOT/cfg["c2_result_root"]/"kfde/construction_sweep.json"),
        "epsilon_mm3":construction["numerical_tolerance_mm3"]})
    save(RESULT/"frozen_inputs/parity_audit.json",{"status":"PASS","prior_results":priors,
        "C1_geometry_set_hashes":{x["geometry_id"]:x["source_sha256"] for x in geometry["geometries"]},
        "KFDE_unchanged":True,"URDF_unchanged":True,"exact_mechanics_unchanged":True,
        "VLM_calls":0,"GT_evaluations":0,"visual_objective_calls":0,
        "final_96_case_mechanics_evaluations":0,"formal_holdout_accessed":False})
    save(RESULT/"case_split.json",{"diagnostic_geometries":[x["geometry_id"] for x in geometry["geometries"]],
        "KFDE_components":13,"alignment_case_count":65,
        "final_development_96_case_rows_used":False,"formal_holdout_case_count":32,
        "formal_holdout_ids_not_read":True,"accessed":False,"evaluation_count":0})
    save(RESULT/"holdout_evaluation_log.json",{"events":[],"accessed":False,"evaluation_count":0,"followed_by_tuning":False})
    head=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    freecad=subprocess.run([python_runtime(),"-c","import FreeCAD,json;print(json.dumps(FreeCAD.Version()))"],
        cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    pre={"schema_version":"robotcad_try6_d1_pre_run_v1","status":"READY_FOR_FROZEN_ALIGNMENT_AND_WITNESS",
        "timestamp_utc":datetime.now(timezone.utc).isoformat(),"starting_commit":cfg["starting_commit"],
        "implementation_commit_before_D1":head,"protocol_sha256":sha(HERE/"protocol/try6_0_d1.json"),
        "prior_result_hashes":priors,"geometry_set_sha256":sha(RESULT/"frozen_inputs/geometry_set.json"),
        "KFDE_construction_sha256":sha(ROOT/cfg["kfde_construction"]),
        "KFDE_keepout_sha256":construction["keepout"]["sha256"],
        "allowed_contact_sha256":construction["allowed_region"]["sha256"],
        "exact_mechanics_source_sha256":sha(ROOT/cfg["exact_mechanics_source"]),
        "exact_mechanics_wrapper_sha256":sha(exact_wrapper),
        "URDF_sha256":sha(ROOT/cfg["sanitized_urdf"]),
        "alignment_case_count":65,"witness_subsets":cfg["witness_subsets"],
        "FreeCAD_version":freecad,"python_environment":".venv/Scripts/python.exe",
        "VLM_calls":0,"GT_evaluations":0,"final_mechanics_evaluations":0,
        "formal_holdout_accessed":False}
    save(RESULT/"pre_run_manifest.json",pre)
    print(json.dumps({"status":pre["status"],"geometries":5,"alignment_cases":65,
        "witness_subsets":len(cfg["witness_subsets"]),"GT_evaluations":0}))


if __name__=="__main__":main()
