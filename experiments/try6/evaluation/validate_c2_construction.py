"""Independent no-GT KFDE construction/provenance gate before C1 replay."""

from __future__ import annotations

import json
import math
import subprocess
import sys

import numpy as np

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try6.scripts.run_r1_reliability import save
from experiments.try5A.scripts.kinematics import parse,canonical_q,fk

sys.path.insert(0,str(ROOT/"experiments/try5A/scripts"))
from freecad_runtime import python_runtime

RESULT=HERE/"results/try6_0_c2"
ARTIFACT=HERE/"artifacts/try6_0_c2/kfde"


def validate():
    cfg=load(HERE/"protocol/try6_0_c2.json")
    report=load(RESULT/"kfde/construction_report.json")
    if report["status"]!="PASS" or len(report["components"])!=13:
        raise RuntimeError("KFDE component count/status invalid")
    if report["gt_accessed"] or report["final_development_configurations_consumed"] or report["c1_failure_ids_consumed"]:
        raise RuntimeError("forbidden KFDE construction source")
    if sha(ROOT/report["sanitized_urdf_path"])!=report["sanitized_urdf_sha256"]:
        raise RuntimeError("KFDE URDF source hash drift")
    if sha(ROOT/report["keepout"]["path"])!=report["keepout"]["sha256"] or sha(ROOT/report["allowed_region"]["path"])!=report["allowed_region"]["sha256"]:
        raise RuntimeError("KFDE BREP hash mismatch")
    links,joints=parse(ROOT/cfg["sanitized_urdf"])
    by={j["joint_id"]:j for j in joints}
    expected_j03=np.linspace(by["J03"]["limits"]["lower"],by["J03"]["limits"]["upper"],7).tolist()
    if any(abs(a-b)>1e-12 for a,b in zip(report["j03_samples_rad"],expected_j03)) or report["j05_samples_rad"]!=cfg["construction_sweep"]["J05"]["angles_radians"]:
        raise RuntimeError("KFDE sweep differs from URDF/protocol")
    q0=canonical_q(joints)
    for item in report["components"]:
        if sha(ROOT/item["brep_path"])!=item["brep_sha256"] or sha(ROOT/item["source_fcstd"])!=item["source_sha256"]:
            raise RuntimeError("KFDE component/source BREP hash drift")
        q=dict(q0)
        if item["joint_id"] in ("J03","J05"):q[item["joint_id"]]=item["q_rad"]
        _,world,_=fk(links,joints,q)
        expected=(np.linalg.inv(world["L04"])@world[item["link_id"]]).tolist()
        if not np.allclose(expected,item["relative_transform_L04"],atol=1e-12):
            raise RuntimeError("KFDE transformed neighbor not in L04 frame")
    by_link={link:[c for c in report["components"] if c["link_id"]==link] for link in ("L03","L05","L06","L07")}
    if [len(by_link[x]) for x in ("L03","L05","L06","L07")]!=[7,1,4,1]:
        raise RuntimeError("KFDE topology/pose coverage changed")
    if by_link["L03"][0]["brep_sha256"]==by_link["L03"][-1]["brep_sha256"] or by_link["L06"][0]["brep_sha256"]==by_link["L06"][2]["brep_sha256"]:
        raise RuntimeError("KFDE pose changes did not affect geometry")
    job={"construction_report":"experiments/try6/results/try6_0_c2/kfde/construction_report.json",
        "scaffold_fcstd":cfg["frozen_l04_scaffold"],
        "output":"experiments/try6/results/try6_0_c2/kfde/independent_brep_audit.json"}
    save(ARTIFACT/"independent_construction_audit_job.json",job)
    proc=subprocess.run([python_runtime(),str(HERE/"evaluation/freecad_validate_c2_construction.py"),
        str(ARTIFACT/"independent_construction_audit_job.json")],cwd=ROOT,capture_output=True,text=True,timeout=180)
    (RESULT/"kfde/independent_brep_stdout.txt").write_text(proc.stdout,encoding="utf-8")
    (RESULT/"kfde/independent_brep_stderr.txt").write_text(proc.stderr,encoding="utf-8")
    if proc.returncode:raise RuntimeError(f"independent KFDE BREP audit failed: {proc.stderr[-1000:]}")
    brep=load(RESULT/"kfde/independent_brep_audit.json")
    if brep["status"]!="PASS" or brep["valid_component_count"]!=13:
        raise RuntimeError("KFDE BREP artifact invalid")
    if cfg["engineering_clearance_margin_mm"]!=0 or cfg["numerical_forbidden_volume_tolerance_mm3"]!=1e-6:
        raise RuntimeError("KFDE frozen tolerance drift")
    lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"]!=0:raise RuntimeError("holdout lock violated")
    result={"status":"PASS","component_count":13,"neighbor_pose_counts":{"L03":7,"L05":1,"L06":4,"L07":1},
        "pose_sensitive":True,"L04_frame_recomputed":True,"allowed_scaffold_residual_mm3":brep["frozen_scaffold_residual_mm3"],
        "keepout_nonempty":brep["keepout_compound_volume_proxy_mm3"]>0,
        "gt_accessed":False,"final_development_configurations_consumed":False,
        "c1_failure_ids_consumed":False,"formal_holdout_accessed":False,
        "construction_report_sha256":sha(RESULT/"kfde/construction_report.json")}
    save(RESULT/"kfde/independent_construction_validation.json",result)
    print(json.dumps({"status":"PASS","components":13,"pose_sensitive":True,"scaffold_exempt":True}))
    return result


if __name__=="__main__":validate()
