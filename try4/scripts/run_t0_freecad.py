"""Root-.venv orchestrator for one-shot T0 FreeCAD execution."""
import csv,json,subprocess,time,hashlib
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';OUT=EXP/'T0';RESULTS=EXP/'results'
RUNTIME=Path(r'D:\software\freeCAD\install\bin\python.exe');HELPER=EXP/'scripts/freecad_t0_executor.py'

def main():
    files=[HELPER,Path(__file__),EXP/'scripts/validate_t0.py',EXP/'schemas/t0_direct_output.schema.json']
    snapshot={'created_at':datetime.now(timezone.utc).isoformat(),'replay_reason':'generic native editable-object lookup repair; CAD IR unchanged','files':{str(p.relative_to(EXP)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    (RESULTS/'t0_freecad_method_snapshot.json').write_text(json.dumps(snapshot,indent=2)+'\n')
    gates={r['part_id']:r for r in csv.DictReader((RESULTS/'t0_plan_gate.csv').open())};rows=[]
    for i in range(5):
        pid=f'R01_P{i:02d}';out=OUT/pid/'round_0';gate=gates[pid]
        if gate['status']!='PASS':rows.append({'part_id':pid,'status':'PLAN_INCOMPLETE','returncode':'','elapsed_seconds':0,'error':gate['errors']});continue
        job={'repo_root':str(ROOT),'agent_output':str(out/'agent_output.json'),'output':str(out)};job_path=out/'freecad_job.json';job_path.write_text(json.dumps(job,indent=2)+'\n')
        started=time.time();p=subprocess.run([str(RUNTIME),str(HELPER),str(job_path)],cwd=ROOT,capture_output=True,text=True,timeout=600);elapsed=time.time()-started
        (out/'freecad_stdout.txt').write_text(p.stdout);(out/'freecad_stderr.txt').write_text(p.stderr)
        result=json.loads((out/'execution_result.json').read_text()) if (out/'execution_result.json').is_file() else {'status':'FAILURE','error':'missing result'}
        rows.append({'part_id':pid,'status':result['status'],'returncode':p.returncode,'elapsed_seconds':elapsed,'error':result.get('error','')});print(pid,result['status'],flush=True)
    with (RESULTS/'t0_execution.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return 0 if all(r['status']=='SUCCESS' for r in rows) else 1
if __name__=='__main__':raise SystemExit(main())
