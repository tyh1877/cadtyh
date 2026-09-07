"""Execute all 12 A0 links once with the shared FreeCAD backend."""
import csv,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';RUNTIME=Path(r'D:\software\freeCAD\install\bin\python.exe');EXEC=ROOT/'try4/scripts/freecad_t1_executor.py';rows=[]
for i in range(12):
 lid=f'L{i:02d}';out=HERE/'A0'/lid;job={'repo_root':str(ROOT),'agent_output':str(out/'agent_output.json'),'output':str(out)};jp=out/'freecad_job.json';jp.write_text(json.dumps(job,indent=2)+'\n');start=time.time();p=subprocess.run([str(RUNTIME),str(EXEC),str(jp)],cwd=ROOT,capture_output=True,text=True,timeout=600);(out/'freecad_stdout.txt').write_text(p.stdout);(out/'freecad_stderr.txt').write_text(p.stderr);r=json.loads((out/'execution_result.json').read_text());rows.append({'link_id':lid,'status':r['status'],'returncode':p.returncode,'elapsed_seconds':time.time()-start,'operations':r.get('operations'),'fallbacks':r.get('fallback_count'),'error':r.get('error','')});print(lid,r['status'],flush=True)
with (HERE/'results/a0_link_execution.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
raise SystemExit(not all(x['status']=='SUCCESS' for x in rows))
