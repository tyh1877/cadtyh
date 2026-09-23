"""Non-GT compiler self-test for an UNCERTAIN pocket; not an E2E sample."""

from __future__ import annotations

import json
import subprocess
import sys

from experiments.try6.scripts.r1_contract import ROOT,HERE,load
from experiments.try6.scripts.r1_v3_contract import assemble,validate_kfdg
from experiments.try6.scripts.run_r1_reliability import save

sys.path.insert(0,str(ROOT/"experiments/try5A/scripts"))
from freecad_runtime import python_runtime


def main():
    root=HERE/"artifacts/try6_0_r1_v3/compiler_selftest"
    root.mkdir(parents=True,exist_ok=True)
    protected_signatures=[]
    for label,pocket_status in (("pocket_uncertain","UNCERTAIN"),("pocket_present","PRESENT")):
        fixture=load(HERE/"fixtures/r1_v3_valid_slots.json")
        pocket=next(s for s in fixture["slots"] if s["slot_id"]=="visible_pocket")
        pocket["status"]=pocket_status
        graph=assemble(fixture);validate_kfdg(graph)
        folder=root/label;folder.mkdir(parents=True,exist_ok=True)
        graph_path=folder/"synthetic_kfdg.json";save(graph_path,graph)
        values={p["id"]:p["value"] for p in graph["parameters"]}
        job={"mode":"R1_V3_COMPILER_SELFTEST_NON_GT","parameters":values,"anchor_distance_mm":63.0,
            "kfdg_path":str(graph_path),"frozen_interface_contracts":str(ROOT/"experiments/try5A/results/try5a5/motion_interface_contracts.json"),
            "f0_fcstd":str(ROOT/"experiments/try5A/artifacts/try5a5/round3_verified/links/L04/model.FCStd"),
            "output_root":str(folder/"cad")}
        job_path=folder/"job.json";save(job_path,job)
        result=subprocess.run([python_runtime(),str(HERE/"scripts/freecad_c1_builder.py"),str(job_path)],
            cwd=ROOT,capture_output=True,text=True,timeout=180)
        (folder/"stdout.txt").write_text(result.stdout,encoding="utf-8")
        (folder/"stderr.txt").write_text(result.stderr,encoding="utf-8")
        if result.returncode:raise RuntimeError(result.stderr[-1500:])
        built=load(folder/"cad/build_result.json")
        names={x["name"] for x in built["feature_tree"]}
        if ("VisibleRecessPocket" in names)!=(pocket_status=="PRESENT") or built["final_solid_count"]!=1 or not built["reopen"]["valid"]:
            raise RuntimeError(f"{label} compiler self-test failed")
        sig_job=folder/"signature_job.json";save(sig_job,{"fcstd":str(folder/"cad/final.FCStd"),"output":str(folder/"signature")})
        sig=subprocess.run([python_runtime(),str(HERE/"scripts/freecad_r1_v3_signature.py"),str(sig_job)],
            cwd=ROOT,capture_output=True,text=True,timeout=120)
        if sig.returncode:raise RuntimeError(sig.stderr[-1000:])
        signatures=load(folder/"signature/signature.json")["shapes"]
        protected_signatures.append({name:signatures[name] for name in ("FrozenProximalBoreTool","FrozenMatingEnvelopeTool","FrozenScaffold")})
    if protected_signatures[0]!=protected_signatures[1]:raise RuntimeError("protected interface changed across optional pocket builds")
    print(json.dumps({"status":"PASS","cases":["pocket_uncertain","pocket_present"],"connected_solids":1,"reopen":True,"interface_invariant":True}))


if __name__=="__main__":main()
