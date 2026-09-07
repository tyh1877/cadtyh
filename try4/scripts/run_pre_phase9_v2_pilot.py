"""Execute the four v2 pilot blueprints in native FreeCAD."""
import csv,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';RUNTIME=Path(r'D:\software\freeCAD\install\bin\python.exe');rows=[]
for pid in ['R01_P00','R02_P02','R02_P05','R02_P06']:
 out=EXP/f'PRE_PHASE9_V2/{pid}/round_0';job={'repo_root':str(ROOT),'agent_output':str(out/'agent_output.json'),'output':str(out)};jp=out/'freecad_job.json';jp.write_text(json.dumps(job,indent=2)+'\n');p=subprocess.run([str(RUNTIME),str(EXP/'scripts/freecad_t1_executor.py'),str(jp)],cwd=ROOT,capture_output=True,text=True,timeout=600);(out/'freecad_stdout.txt').write_text(p.stdout);(out/'freecad_stderr.txt').write_text(p.stderr);result=json.loads((out/'execution_result.json').read_text());rows.append({'part_id':pid,'status':result['status'],'returncode':p.returncode,'error':result.get('error','')});print(pid,result['status'])
with (EXP/'results/pre_phase9_v2_pilot_execution.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
raise SystemExit(not all(r['status']=='SUCCESS' for r in rows))
