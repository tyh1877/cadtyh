"""Two-CAD, no-GT smoke of the frozen raw-image objective and URDF anchor path."""

from __future__ import annotations

import json
import math
import subprocess
import sys
import time

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try6.scripts.r1_v3_contract import assemble,validate_kfdg
from experiments.try6.scripts.c1_v2_visual_objective import VisibleObjective
from experiments.try6.scripts.run_r1_reliability import save

sys.path.insert(0,str(ROOT/"experiments/try5A/scripts"))
from freecad_runtime import python_runtime

RESULT=HERE/"results/try6_0_c1_v2"
ARTIFACT=HERE/"artifacts/try6_0_c1_v2/infrastructure_smoke"


def main():
    evidence=load(RESULT/"visual_metric_evidence/evidence_audit.json")
    if not evidence["registration_gate_pass"] or not evidence["evidence_gate_pass"]:
        raise RuntimeError("visual evidence gate failed")
    graph=assemble(load(HERE/"fixtures/r1_v3_valid_slots.json"));validate_kfdg(graph)
    ARTIFACT.mkdir(parents=True,exist_ok=True)
    graph_path=ARTIFACT/"synthetic_kfdg.json";save(graph_path,graph)
    values={p["id"]:p["value"] for p in graph["parameters"]}
    objective=VisibleObjective();records=[]
    for index,width in enumerate((values["housing_width_mm"],values["housing_width_mm"]+1.0)):
        theta=dict(values);theta["housing_width_mm"]=width
        folder=ARTIFACT/f"candidate_{index}";folder.mkdir(parents=True,exist_ok=True)
        job={"mode":"C1_V2_OBJECTIVE_INFRASTRUCTURE_SMOKE_NON_GT","parameters":theta,
            "anchor_distance_mm":63.0,"kfdg_path":str(graph_path),
            "frozen_interface_contracts":str(ROOT/"experiments/try5A/results/try5a5/motion_interface_contracts.json"),
            "f0_fcstd":str(ROOT/"experiments/try5A/artifacts/try5a5/round3_verified/links/L04/model.FCStd"),
            "output_root":str(folder)}
        job_path=ARTIFACT/f"candidate_{index}_job.json";save(job_path,job)
        tick=time.perf_counter()
        proc=subprocess.run([python_runtime(),str(HERE/"scripts/freecad_c1_builder.py"),str(job_path)],
            cwd=ROOT,capture_output=True,text=True,timeout=120)
        (folder/"stdout.txt").write_text(proc.stdout,encoding="utf-8")
        (folder/"stderr.txt").write_text(proc.stderr,encoding="utf-8")
        if proc.returncode:raise RuntimeError(f"CAD smoke {index} failed: {proc.stderr[-1000:]}")
        score=objective.evaluate(folder/"body_only.stl",folder/"renders")
        built=load(folder/"build_result.json")
        if built["final_solid_count"]!=1 or not built["reopen"]["valid"]:
            raise RuntimeError("smoke CAD invalid")
        records.append({"index":index,"housing_width_mm":width,"objective":score["total"],
            "contour":score["contour_term"],"profile":score["profile_term"],
            "final_volume_mm3":built["final_volume_mm3"],"seconds":time.perf_counter()-tick})
    alternative=VisibleObjective(anchor_override_mm=64.0).evaluate(ARTIFACT/"candidate_0/body_only.stl")
    right=objective.evidence["views"]["right"]["profile_stations"][0]
    target_63=right["visible_width_mm"]
    target_64=right["visible_width_px"]/(objective.evidence["views"]["right"]["scale_px_per_mm"]*63.0/64.0)
    if any(not math.isfinite(r["objective"]) for r in records) or abs(records[0]["objective"]-records[1]["objective"])<1e-9:
        raise RuntimeError("candidate objective did not respond to theta")
    if abs(records[0]["objective"]-alternative["total"])<1e-9 or abs(target_63-target_64)<1e-9:
        raise RuntimeError("URDF anchor not consumed by visible objective")
    report={"schema_version":"robotcad_try6_c1_v2_objective_smoke_v1","status":"PASS",
        "nonformal":True,"candidate_count":2,"candidates":records,
        "anchor_sensitivity":{"actual_urdf_anchor_mm":63.0,"synthetic_anchor_mm":64.0,
            "raw_right_station_width_target_mm_at_63":target_63,
            "raw_right_station_width_target_mm_at_64":target_64,
            "fixed_cad_objective_at_63":records[0]["objective"],
            "fixed_cad_objective_at_64":alternative["total"],
            "metric_relation_changed":True,"objective_changed":True},
        "visual_evidence_sha256":sha(RESULT/"visual_metric_evidence/visual_metric_evidence.json"),
        "gt_evaluations":0,"formal_holdout_evaluations":0}
    save(RESULT/"infrastructure_smoke.json",report)
    print(json.dumps({"status":"PASS","candidate_objectives":[x["objective"] for x in records],
        "anchor64_objective":alternative["total"],"gt_evaluations":0}))


if __name__=="__main__":main()
