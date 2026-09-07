"""Execute two Robot-B free-form review decisions as a separate ablation."""
import copy,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';sys.path.insert(0,str(EXP/'scripts'));from materialize_t1 import compile_recipe,EMPTY,FRAME;from evaluate_phase5 import evaluate
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def main():
 dec=json.loads((EXP/'codex_authored/T2_FREEFORM/decisions.json').read_text());blue=json.loads((EXP/'codex_authored/T1/t1_blueprints.json').read_text())['parts'];rows=[]
 for case in dec['cases']:
  pid=case['part_id'];src=EXP/'T1'/pid/'round_0';out=EXP/'T2_FREEFORM'/pid/'round_1';bp=copy.deepcopy(next(x for x in blue if x['part_id']==pid));bp['parameters'].update(case['agent_interpretation_for_execution']);prior=json.loads((src/'agent_output.json').read_text());req={r:f['feature_id'] for f in prior['feature_graph']['features'] for r in f['requirement_refs']};fmap={x['key']:req[x['requirement_ref']] for x in bp['features']};ops,bodies,finals,edit=compile_recipe(bp['recipe'],bp['parameters'],fmap);ops=[{**EMPTY,**x,'reference_frame':FRAME} for x in ops];data=copy.deepcopy(prior);data['cad_ir']={**data['cad_ir'],'operations':ops,'bodies':bodies,'final_objects':finals,'editable_parameter':edit};dump(out/'agent_output.json',data);dump(out/'feature_graph.json',data['feature_graph']);dump(out/'cad_ir.json',data['cad_ir']);(out/'freeform_review.txt').write_text(case['free_form_review']+'\n');dump(out/'freeform_interpretation.json',case['agent_interpretation_for_execution']);job={'repo_root':str(ROOT),'agent_output':str(out/'agent_output.json'),'output':str(out)};jp=out/'freecad_job.json';dump(jp,job);p=subprocess.run([r'D:\software\freeCAD\install\bin\python.exe',str(EXP/'scripts/freecad_t1_executor.py'),str(jp)],cwd=ROOT,capture_output=True,text=True,timeout=600);(out/'freecad_stdout.txt').write_text(p.stdout);(out/'freecad_stderr.txt').write_text(p.stderr)
  if p.returncode:raise RuntimeError(pid+' FreeCAD failure')
  stage=EXP/'T2_EVAL'/pid/'round_0';shutil.rmtree(stage.parent.parent,ignore_errors=True);shutil.copytree(out,stage);idx=10+int(pid[-2:]);m=evaluate('T2_EVAL',pid,EXP/f'evaluation_cache/gt/R02/{pid}.stl',stage/'model.stl',idx);m['condition']='T2_FREEFORM';m['round']=1;dump(out/'metrics.json',m);rows.append(m);shutil.rmtree(EXP/'T2_EVAL',ignore_errors=True);print(pid,m['gate_status'])
 dump(EXP/'results/phase8_freeform_ablation.json',rows)
if __name__=='__main__':main()
