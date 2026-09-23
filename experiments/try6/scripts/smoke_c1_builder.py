"""One-point infrastructure smoke for the native FreeCAD feature history."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/"experiments/try6"
sys.path.insert(0,str(ROOT/"experiments/try5A/scripts"))
from freecad_runtime import python_runtime  # noqa: E402
from kfdg_contract import build_kfdg,load  # noqa: E402


def main():
    params=json.loads((HERE/"protocol/parameter_bounds.json").read_text(encoding="utf-8"))
    values={item["id"]:item["value"] for item in params["optimizable"]}
    root=HERE/"artifacts/try6_0_c1/smoke/point_0"; root.mkdir(parents=True,exist_ok=True)
    kfdg=build_kfdg(load(HERE/"tests/fixtures/valid_vlm.json"),params)
    kfdg_path=root/"synthetic_kfdg.json";kfdg_path.write_text(json.dumps(kfdg,indent=2)+"\n",encoding="utf-8")
    job={"mode":"INFRASTRUCTURE_SMOKE","parameters":values,"anchor_distance_mm":params["fixed_functional"]["anchor_distance_mm"],"kfdg_path":str(kfdg_path),"frozen_interface_contracts":"experiments/try5A/results/try5a5/motion_interface_contracts.json","f0_fcstd":"experiments/try5A/artifacts/try5a5/round3_verified/links/L04/model.FCStd","output_root":str(root)}
    job["frozen_interface_contracts"]=str(ROOT/job["frozen_interface_contracts"])
    job["f0_fcstd"]=str(ROOT/job["f0_fcstd"])
    job_path=root/"job.json"; job_path.write_text(json.dumps(job,indent=2)+"\n",encoding="utf-8")
    started=time.perf_counter(); result=subprocess.run([python_runtime(),str(HERE/"scripts/freecad_c1_builder.py"),str(job_path)],cwd=ROOT,capture_output=True,text=True,timeout=120)
    (root/"stdout.txt").write_text(result.stdout,encoding="utf-8")
    (root/"stderr.txt").write_text(result.stderr,encoding="utf-8")
    print(json.dumps({"status":"PASS" if result.returncode==0 else "FAIL","seconds":time.perf_counter()-started,"stdout":result.stdout[-500:],"stderr":result.stderr[-1500:]},indent=2))
    return result.returncode


if __name__=="__main__": raise SystemExit(main())
