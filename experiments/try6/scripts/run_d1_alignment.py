"""One frozen 5×13 KFDE/exact-mechanics local-pose diagnostic run."""

from __future__ import annotations

import json
import subprocess
import sys
import time

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try6.scripts.run_r1_reliability import save

sys.path.insert(0,str(ROOT/"experiments/try5A/scripts"))
from freecad_runtime import python_runtime

RESULT=HERE/"results/try6_0_d1"
ARTIFACT=HERE/"artifacts/try6_0_d1/alignment"


def main():
    cfg=load(HERE/"protocol/try6_0_d1.json")
    pre=load(RESULT/"pre_run_manifest.json")
    if pre["status"]!="READY_FOR_FROZEN_ALIGNMENT_AND_WITNESS" or pre["protocol_sha256"]!=sha(HERE/"protocol/try6_0_d1.json"):
        raise RuntimeError("D1 protocol not frozen")
    if (RESULT/"alignment/raw_alignment.json").exists():raise FileExistsError("D1 alignment already completed")
    prior_attempt=(RESULT/"alignment/attempt_started.json").exists()
    if prior_attempt:
        failure=RESULT/"alignment/failure.json"
        if not failure.is_file() or (RESULT/"alignment/technical_retry_started.json").exists():
            raise FileExistsError("D1 alignment technical retry unavailable or already attempted")
        save(RESULT/"alignment/technical_retry_started.json",{"reason":"Null mutable F0 BREP cut guard only",
            "first_failure_sha256":sha(failure),"scientific_protocol_unchanged":True,
            "geometry_set_unchanged":True,"exact_mechanics_source_unchanged":True,
            "max_technical_retries":1})
    ARTIFACT.mkdir(parents=True,exist_ok=True)
    job={"protocol":"experiments/try6/protocol/try6_0_d1.json",
        "geometry_set":"experiments/try6/results/try6_0_d1/frozen_inputs/geometry_set.json",
        "output":"experiments/try6/results/try6_0_d1/alignment/raw_alignment.json"}
    save(ARTIFACT/"job.json",job)
    if not prior_attempt:
        save(RESULT/"alignment/attempt_started.json",{"protocol_sha256":pre["protocol_sha256"],
            "geometry_set_sha256":pre["geometry_set_sha256"],"KFDE_construction_sha256":pre["KFDE_construction_sha256"],
            "exact_mechanics_source_sha256":pre["exact_mechanics_source_sha256"],
            "planned_cases":65,"final_96_case_mechanics":False,"GT_access":False})
    tick=time.perf_counter()
    proc=subprocess.run([python_runtime(),str(HERE/"evaluation/freecad_d1_alignment.py"),str(ARTIFACT/"job.json")],
        cwd=ROOT,capture_output=True,text=True,timeout=900)
    (RESULT/"alignment/stdout.txt").write_text(proc.stdout,encoding="utf-8")
    (RESULT/"alignment/stderr.txt").write_text(proc.stderr,encoding="utf-8")
    if proc.returncode:
        save(RESULT/"alignment/failure.json",{"status":"DIAGNOSTIC_INCONCLUSIVE","returncode":proc.returncode,
            "error":(proc.stderr or proc.stdout)[-3000:],"no_retry":True})
        raise RuntimeError("D1 exact alignment diagnostic failed")
    raw=load(RESULT/"alignment/raw_alignment.json")
    if raw["status"]!="PASS" or raw["case_count"]!=65 or raw["GT_accessed"] or raw["final_96_case_mechanics_run"]:
        raise RuntimeError("D1 alignment output invalid")
    save(RESULT/"alignment/runtime.json",{"seconds":time.perf_counter()-tick,"cases":65,
        "GT_evaluations":0,"full_final_mechanics_evaluations":0})
    print(json.dumps({"status":"PASS","cases":65,"seconds":time.perf_counter()-tick,"GT_evaluations":0}))


if __name__=="__main__":main()
