"""Execute all eight frozen one-shot A1/A2 plans with the Try-4 FreeCAD backend."""
import csv,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try4_1A';TRY4=ROOT/'try4';RUNTIME=Path(r'D:\software\freeCAD\install\bin\python.exe');rows=[]
for cond in ('A1','A2'):
 for pid in ('R02_P02','R02_P04','R02_P05','R02_P06'):
  out=HERE/cond/pid/'round_0';job={'repo_root':str(ROOT),'agent_output':str(out/'agent_output.json'),'output':str(out)};jp=out/'freecad_job.json';jp.write_text(json.dumps(job,indent=2)+'\n');p=subprocess.run([str(RUNTIME),str(TRY4/'scripts/freecad_t1_executor.py'),str(jp)],cwd=ROOT,capture_output=True,text=True,timeout=600);(out/'freecad_stdout.txt').write_text(p.stdout);(out/'freecad_stderr.txt').write_text(p.stderr);r=json.loads((out/'execution_result.json').read_text());rows.append({'condition':cond,'part_id':pid,'status':r['status'],'returncode':p.returncode,'error':r.get('error','')});print(cond,pid,r['status'],flush=True)
with (HERE/'results/execution.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
raise SystemExit(not all(x['status']=='SUCCESS' for x in rows))
