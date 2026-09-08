"""Execute all 12 A2 links once."""
import csv,json,subprocess,time
from pathlib import Path
from freecad_runtime import python_runtime
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';RUNTIME=python_runtime();EXEC=ROOT/'try4/scripts/freecad_t1_executor.py';rows=[]
for i in range(12):
 lid=f'L{i:02d}';out=HERE/'A2'/lid;agent=json.loads((out/'agent_output.json').read_text())
 if agent.get('link_realization_type')=='virtual_frame':
  rows.append({'link_id':lid,'status':'SKIPPED_VIRTUAL_FRAME','returncode':0,'elapsed_seconds':0,'operations':0,'fallbacks':0,'error':''});print(lid,'SKIPPED_VIRTUAL_FRAME',flush=True);continue
 job={'repo_root':str(ROOT),'agent_output':str(out/'agent_output.json'),'output':str(out)};jp=out/'freecad_job.json';jp.write_text(json.dumps(job,indent=2)+'\n');start=time.time();p=subprocess.run([str(RUNTIME),str(EXEC),str(jp)],cwd=ROOT,capture_output=True,text=True,timeout=600);(out/'freecad_stdout.txt').write_text(p.stdout);(out/'freecad_stderr.txt').write_text(p.stderr);r=json.loads((out/'execution_result.json').read_text());rows.append({'link_id':lid,'status':r['status'],'returncode':p.returncode,'elapsed_seconds':time.time()-start,'operations':r.get('operations'),'fallbacks':r.get('fallback_count'),'error':r.get('error','')});print(lid,r['status'],flush=True)
with (HERE/'results/a2_link_execution.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
raise SystemExit(not all(x['status'] in {'SUCCESS','SKIPPED_VIRTUAL_FRAME'} for x in rows))
