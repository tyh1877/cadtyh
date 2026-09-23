"""One frozen diagnostic full/per-neighbor/combined C1 mutable-body relief run."""

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
ARTIFACT=HERE/"artifacts/try6_0_d1/witness"


def main():
    cfg=load(HERE/"protocol/try6_0_d1.json")
    pre=load(RESULT/"pre_run_manifest.json")
    if pre["status"]!="READY_FOR_FROZEN_ALIGNMENT_AND_WITNESS" or pre["protocol_sha256"]!=sha(HERE/"protocol/try6_0_d1.json"):
        raise RuntimeError("D1 witness protocol not frozen")
    if not (RESULT/"alignment/raw_alignment.json").is_file():raise RuntimeError("D1 alignment phase not complete")
    if (RESULT/"witness/witness_summary.json").exists():raise FileExistsError("D1 witness already attempted")
    ARTIFACT.mkdir(parents=True,exist_ok=True)
    job={"protocol":"experiments/try6/protocol/try6_0_d1.json",
        "construction_report":cfg["kfde_construction"],
        "artifact_root":"experiments/try6/artifacts/try6_0_d1/witness",
        "result_root":"experiments/try6/results/try6_0_d1/witness",
        "geometry_set":"experiments/try6/results/try6_0_d1/frozen_inputs/geometry_set.json"}
    save(ARTIFACT/"job.json",job)
    save(RESULT/"witness/attempt_started.json",{"protocol_sha256":pre["protocol_sha256"],
        "C1_geometry_sha256":load(RESULT/"frozen_inputs/geometry_set.json")["geometries"][0]["source_sha256"],
        "KFDE_construction_sha256":pre["KFDE_construction_sha256"],
        "planned_subsets":cfg["witness_subsets"],"diagnostic_only":True,"GT_access":False})
    tick=time.perf_counter()
    proc=subprocess.run([python_runtime(),str(HERE/"evaluation/freecad_d1_witness.py"),str(ARTIFACT/"job.json")],
        cwd=ROOT,capture_output=True,text=True,timeout=600)
    (RESULT/"witness/stdout.txt").write_text(proc.stdout,encoding="utf-8")
    (RESULT/"witness/stderr.txt").write_text(proc.stderr,encoding="utf-8")
    if proc.returncode:
        save(RESULT/"witness/failure.json",{"status":"DIAGNOSTIC_INCONCLUSIVE","returncode":proc.returncode,
            "error":(proc.stderr or proc.stdout)[-3000:],"no_retry":True})
        raise RuntimeError("D1 exact BREP witness failed")
    raw=load(RESULT/"witness/witness_summary.json")
    if raw["status"]!="PASS" or len(raw["subsets"])!=len(cfg["witness_subsets"]) or raw["GT_accessed"] or not raw["frozen_C1_fcstd_unchanged"]:
        raise RuntimeError("D1 witness output invalid")
    save(RESULT/"witness/runtime.json",{"seconds":time.perf_counter()-tick,"subsets":len(raw["subsets"]),
        "GT_evaluations":0,"full_final_mechanics_evaluations":0})
    print(json.dumps({"status":"PASS","subsets":len(raw["subsets"]),
        "full_removed_ratio":next(x["removed_ratio"] for x in raw["subsets"] if x["subset"]=="FULL"),
        "GT_evaluations":0}))


if __name__=="__main__":main()
