"""Run the strict FreeCAD executor for all generated C1/C2 link IRs."""
import csv,json,subprocess,time,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A_1';RUNTIME=Path(r'D:\software\freeCAD\install\bin\python.exe');EXEC=ROOT/'try4/scripts/freecad_t1_executor.py'
def main(condition):
 rows=[]
 for i in range(12):
  lid=f'L{i:02d}';out=HERE/condition/lid;job={'repo_root':str(ROOT),'agent_output':str(out/'agent_output.json'),'output':str(out)};jp=out/'freecad_job.json';jp.write_text(json.dumps(job,indent=2)+'\n');t=time.time();p=subprocess.run([str(RUNTIME),str(EXEC),str(jp)],cwd=ROOT,capture_output=True,text=True,timeout=600);(out/'freecad_stdout.txt').write_text(p.stdout);(out/'freecad_stderr.txt').write_text(p.stderr);r=json.loads((out/'execution_result.json').read_text());rows.append({'condition':condition,'link_id':lid,'status':r['status'],'returncode':p.returncode,'elapsed_seconds':round(time.time()-t,3),'operations':r.get('operations'),'fallbacks':r.get('fallback_count'),'error':r.get('error','')});print(lid,r['status'],flush=True)
 (HERE/'results').mkdir(exist_ok=True)
 with (HERE/f'results/{condition.lower()}_link_execution.csv').open('w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
 raise SystemExit(not all(x['status']=='SUCCESS' for x in rows))
if __name__=='__main__':main(sys.argv[1])
