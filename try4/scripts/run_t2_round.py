"""Materialize, execute and frozen-evaluate one T2 repair round."""
import argparse,json,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';RUNTIME=Path(r'D:\software\freeCAD\install\bin\python.exe')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--contract',required=True);args=ap.parse_args();c=json.loads(Path(args.contract).read_text());pid=c['part_id'];rnd=c['round'];out=EXP/'T2'/pid/f'round_{rnd}'
    subprocess.run([sys.executable,'-X','utf8',str(EXP/'scripts/materialize_t2_round.py'),'--contract',args.contract],cwd=ROOT,check=True)
    job={'repo_root':str(ROOT),'agent_output':str(out/'agent_output.json'),'output':str(out)};jp=out/'freecad_job.json';jp.write_text(json.dumps(job,indent=2)+'\n');p=subprocess.run([str(RUNTIME),str(EXP/'scripts/freecad_t1_executor.py'),str(jp)],cwd=ROOT,capture_output=True,text=True,timeout=600);(out/'freecad_stdout.txt').write_text(p.stdout);(out/'freecad_stderr.txt').write_text(p.stderr)
    result=json.loads((out/'execution_result.json').read_text());
    if result['status']!='SUCCESS':raise RuntimeError(result.get('error','T2 execution failed'))
    stage=EXP/'T2_EVAL'/pid/'round_0';shutil.rmtree(stage.parent.parent,ignore_errors=True);stage.mkdir(parents=True);[shutil.copy2(x,stage/x.name) for x in out.iterdir() if x.is_file()];
    if (out/'renders').exists():shutil.copytree(out/'renders',stage/'renders')
    sys.path.insert(0,str(EXP/'scripts'));from evaluate_phase5 import evaluate
    baseline_index=2*int(pid[-2:]) if pid.startswith('R01') else 10+int(pid[-2:]);row=evaluate('T2_EVAL',pid,EXP/f'evaluation_cache/gt/{pid[:3]}/{pid}.stl',stage/'model.stl',baseline_index);row['condition']='T2';row['round']=rnd;(out/'metrics.json').write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8');shutil.rmtree(EXP/'T2_EVAL',ignore_errors=True);print(json.dumps({'part_id':pid,'round':rnd,'gate_status':row['gate_status'],'voxel_iou':row['voxel_iou'],'normalized_chamfer':row['normalized_chamfer'],'normalized_hd95':row['normalized_hd95']}))
if __name__=='__main__':main()
