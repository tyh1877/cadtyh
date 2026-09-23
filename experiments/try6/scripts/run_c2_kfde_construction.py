"""One-shot no-GT KFDE BREP construction from frozen URDF/neighbor geometry."""

from __future__ import annotations

import json
import subprocess
import sys
import time

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try6.scripts.run_r1_reliability import save

sys.path.insert(0,str(ROOT/"experiments/try5A/scripts"))
from freecad_runtime import python_runtime

RESULT=HERE/"results/try6_0_c2"
ARTIFACT=HERE/"artifacts/try6_0_c2/kfde"


def run():
    cfg=load(HERE/"protocol/try6_0_c2.json")
    pre=load(RESULT/"pre_run_manifest.json")
    if pre["status"]!="READY_FOR_KFDE_CONSTRUCTION" or pre["protocol_sha256"]!=sha(HERE/"protocol/try6_0_c2.json"):
        raise RuntimeError("KFDE protocol not frozen")
    if (RESULT/"kfde/construction_report.json").exists():raise FileExistsError("KFDE construction already attempted")
    job={"mode":"construct","protocol":"experiments/try6/protocol/try6_0_c2.json",
        "artifact_root":"experiments/try6/artifacts/try6_0_c2/kfde",
        "result_root":"experiments/try6/results/try6_0_c2/kfde"}
    ARTIFACT.mkdir(parents=True,exist_ok=True)
    save(ARTIFACT/"construction_job.json",job)
    save(RESULT/"kfde/definition.json",{"schema_version":"robotcad_try6_c2_kfde_definition_v1",
        "neighbor_scope":cfg["neighbor_scope"],"design_frame":cfg["design_frame"],
        "construction_sweep":cfg["construction_sweep"],
        "allowed_contact_policy":cfg["allowed_contact_policy"],
        "primary_metric":cfg["primary_kfde_metric"],
        "hard_feasibility":True,"engineering_margin_mm":cfg["engineering_clearance_margin_mm"],
        "numerical_tolerance_mm3":cfg["numerical_forbidden_volume_tolerance_mm3"],
        "no_gt":True,"no_C1_failure_diagnostic_input":True})
    save(RESULT/"kfde/tolerance_policy.json",{"engineering_margin_mm":0.0,
        "numerical_forbidden_volume_tolerance_mm3":cfg["numerical_forbidden_volume_tolerance_mm3"],
        "existing_frozen_FreeCAD_distance_TOL_mm":1e-6,
        "interface_clearance_mm":0.6,
        "interpretation":"0.6 mm is a frozen joint-interface clearance, not a new general KFDE margin; zero engineering margin plus predeclared minimum BREP volume epsilon.",
        "not_tuned_on_C1_failures":True})
    tick=time.perf_counter()
    proc=subprocess.run([python_runtime(),str(HERE/"scripts/freecad_c2_kfde.py"),str(ARTIFACT/"construction_job.json")],
        cwd=ROOT,capture_output=True,text=True,timeout=600)
    (RESULT/"kfde/construction_stdout.txt").write_text(proc.stdout,encoding="utf-8")
    (RESULT/"kfde/construction_stderr.txt").write_text(proc.stderr,encoding="utf-8")
    if proc.returncode:
        save(RESULT/"kfde/construction_failure.json",{"status":"KFDE_CONSTRUCTION_BLOCKED",
            "returncode":proc.returncode,"error":(proc.stderr or proc.stdout)[-3000:],"no_retry":True})
        raise RuntimeError("KFDE construction failed")
    report=load(RESULT/"kfde/construction_report.json")
    if report["status"]!="PASS" or report["gt_accessed"] or report["final_development_configurations_consumed"] or report["c1_failure_ids_consumed"]:
        raise RuntimeError("KFDE construction integrity failed")
    save(RESULT/"kfde/construction_runtime.json",{"seconds":time.perf_counter()-tick,
        "pose_components":report["design_pose_count"],"gt_evaluations":0,"final_mechanics_evaluations":0})
    print(json.dumps({"status":"PASS","components":report["design_pose_count"],
        "keepout_volume_proxy_mm3":report["keepout"]["compound_volume_proxy_mm3"],"gt_evaluations":0}))
    return report


if __name__=="__main__":run()
