"""Run D1, D2, G1 and hidden O-GT Try-1 conditions without GT leakage."""
from __future__ import annotations
import argparse, base64, json, mimetypes, shutil, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; sys.path[:0]=[str(ROOT/"go_nogo2/scripts"),str(ROOT/"go_nogo3/scripts"),str(ROOT/"try1/validators")]
from glm_config import load_glm
from robot_blueprint import extract_json
from compile_blueprint import compile_direct
from run_prototype import generic_validate
from validate_rmdg_v1 import validate as validate_rmdg
from evaluate_prediction import evaluate, load_robot, write_json
VIEWS=("front","rear","left","right","top","isometric"); CAPS={"D1":(32768,),"D2":(1024,31744),"G1":(8192,24576),"O_GT":(24576,)}
def content(packet, extra=""):
    out=[{"type":"text","text":packet["rendered_prompt"]+extra}]
    for v in VIEWS:
        p=ROOT/packet["images"][v]; mime=mimetypes.guess_type(p.name)[0] or "image/png"; out += [{"type":"text","text":f"view={v}"},{"type":"image_url","image_url":{"url":f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"}}]
    return out
def call(client, model, prompt, packet, cap, json_mode):
    args={"model":model,"messages":[{"role":"system","content":prompt},{"role":"user","content":content(packet)}],"temperature":0.0,"top_p":1.0,"max_tokens":cap}
    if json_mode:
        args["response_format"]={"type":"json_object"}
        # Reserve the completion budget for schema-constrained JSON rather than
        # letting provider-side reasoning consume it before any JSON is emitted.
        args["extra_body"]={"thinking":{"type":"disabled"}}
    r=client.chat.completions.create(**args); u=r.usage; return r.choices[0].message.content or "", {"input_tokens":int(getattr(u,"prompt_tokens",0)or 0),"output_tokens":int(getattr(u,"completion_tokens",0)or 0),"total_tokens":int(getattr(u,"total_tokens",0)or 0),"request_id":getattr(r,"id",None)}
def main():
 p=argparse.ArgumentParser();p.add_argument("--condition",choices=CAPS,required=True);p.add_argument("--case");p.add_argument("--overwrite",action="store_true");a=p.parse_args(); cfg=load_glm(); packets=sorted((ROOT/"try1/inputs/image_text_v1").glob("*.json")); packets=[x for x in packets if not a.case or x.stem==a.case]
 for path in packets:
  packet=json.loads(path.read_text()); run=ROOT/"try1/runs"/a.condition/path.stem
  if run.exists() and a.overwrite: shutil.rmtree(run)
  if (run/"manifest.json").exists(): print(f"{a.condition} {path.stem}: cached");continue
  run.mkdir(parents=True,exist_ok=True); history=[]; error=None; status="FAILURE"; start=time.perf_counter(); intermediate=None
  try:
   if a.condition=="D1": final_prompt=(ROOT/"try1/prompts/try1/direct_1call.txt").read_text(); raw,u=call(cfg.create_client(),cfg.model,final_prompt+"\n"+__import__("robot_blueprint").blueprint_contract(),packet,CAPS[a.condition][0],True);history.append({"stage":"final","raw":raw,**u})
   else:
    if a.condition=="D2": prompt=(ROOT/"try1/prompts/try1/direct_2call_plan.txt").read_text(); raw,u=call(cfg.create_client(),cfg.model,prompt,packet,CAPS[a.condition][0],False); intermediate={"kind":"generic_plan","text":raw};history.append({"stage":"generic_plan","raw":raw,**u})
    elif a.condition=="G1": prompt=(ROOT/"try1/prompts/try1/rmdg_predict.txt").read_text()+"\nSchema: "+(ROOT/"try1/schemas/rmdg_v1.schema.json").read_text(); raw,u=call(cfg.create_client(),cfg.model,prompt,packet,CAPS[a.condition][0],True); intermediate=extract_json(raw); report=validate_rmdg(intermediate);history.append({"stage":"rmdg","raw":raw,"validation":report,**u});
    else: intermediate=json.loads((ROOT/"try1/hidden_gt_rmdg"/f"{path.stem}.json").read_text()); report=validate_rmdg(intermediate);history.append({"stage":"oracle_rmdg","validation":report})
    if a.condition=="G1" and not report["semantic_valid"]: raise ValueError("predicted RMDG invalid")
    final=(ROOT/"try1/prompts/try1/final_generation.txt").read_text().format(intermediate_plan=json.dumps(intermediate,separators=(",",":")))+"\n"+__import__("robot_blueprint").blueprint_contract(); raw,u=call(cfg.create_client(),cfg.model,final,packet,CAPS[a.condition][-1],True);history.append({"stage":"final","raw":raw,**u})
   bp=generic_validate(extract_json(raw)); (run/"blueprint.json").write_text(json.dumps(bp,indent=2)); compile_direct(bp,run); status="SUCCESS"
  except Exception as e: error=f"{type(e).__name__}: {e}"
  (run/"raw_history.json").write_text(json.dumps(history,indent=2)); total={k:sum(int(x.get(k,0)) for x in history) for k in ("input_tokens","output_tokens","total_tokens")}; manifest={"case_id":path.stem,"condition":a.condition,"status":status,"model":cfg.model,"latency_seconds":time.perf_counter()-start,"api_calls":sum("request_id" in x for x in history),"budget":{"max_output_tokens":32768,"max_total_tokens":100000,**total},"error":error};(run/"manifest.json").write_text(json.dumps(manifest,indent=2));
  if status=="SUCCESS":
   gt,pred=load_robot(ROOT/"go_nogo3/data/dev15"/path.stem/"urdf/model.urdf"),load_robot(run/"urdf/model.urdf"); geo,assembly,kin,motion,outcome=evaluate(gt,pred,20260827);write_json(run/"evaluation.json",{"geometry":geo,"assembly":assembly,"kinematic":kin,"motion":motion,"outcome":outcome})
  print(f"{a.condition} {path.stem}: {status}")
if __name__=="__main__":main()
