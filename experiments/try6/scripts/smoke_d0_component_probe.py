"""Non-sample implementation check: D0 full component vector matches frozen C2 P3."""

from __future__ import annotations

import json
import subprocess
import sys

from experiments.try6.scripts.r1_contract import ROOT,HERE,load
from experiments.try6.scripts.run_r1_reliability import save

sys.path.insert(0,str(ROOT/"experiments/try5A/scripts"))
from freecad_runtime import python_runtime


def main():
    root=HERE/"artifacts/try6_0_d0/technical_smoke"
    root.mkdir(parents=True,exist_ok=True)
    theta=load(HERE/"results/try6_0_c1_v2/kfdg/active_parameters.json")["initial_theta"]
    job={"candidate_id":"TECH_P3_NOT_D0_SAMPLE","theta":theta,
        "d0_protocol":"experiments/try6/protocol/try6_0_d0.json",
        "c2_protocol":"experiments/try6/protocol/try6_0_c2.json",
        "construction_report":"experiments/try6/results/try6_0_c2/kfde/construction_report.json",
        "kfdg_source":"experiments/try6/results/try6_0_c1_v2/kfdg/canonical_kfdg.json",
        "output_root":"experiments/try6/artifacts/try6_0_d0/technical_smoke"}
    save(root/"job.json",job)
    proc=subprocess.run([python_runtime(),str(HERE/"scripts/freecad_d0_component_probe.py"),str(root/"job.json")],
        cwd=ROOT,capture_output=True,text=True,timeout=180)
    (root/"stdout.txt").write_text(proc.stdout,encoding="utf-8")
    (root/"stderr.txt").write_text(proc.stderr,encoding="utf-8")
    if proc.returncode:raise RuntimeError(proc.stderr[-1200:])
    result=load(root/"component_result.json")
    c2=load(HERE/"artifacts/try6_0_c2/replay/candidate_000_check.json")
    if len(result["components"])!=13 or abs(result["g_max_mm3"]-c2["maximum_forbidden_intersection_mm3"])>1e-6 or result["strict_feasible"]!=c2["feasible"]:
        raise RuntimeError("D0 component vector disagrees with frozen C2 checker")
    if abs(result["g_sum_mm3"]-sum(item["intersection_volume_mm3"] for item in result["components"]))>1e-9:
        raise RuntimeError("D0 component sum mismatch")
    print(json.dumps({"status":"PASS","component_count":13,"g_max_matches_frozen_C2":True,
        "non_sample":True,"GT_accessed":False}))


if __name__=="__main__":main()
