"""Execute all and only the 12 DEV_A/B T1 plans once."""
import argparse,csv,hashlib,json,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';OUT=EXP/'T1';RESULTS=EXP/'results';RUNTIME=Path(r'D:\software\freeCAD\install\bin\python.exe');HELPER=EXP/'scripts/freecad_t1_executor.py'
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--part');args=parser.parse_args()
    files=[HELPER,EXP/'scripts/freecad_t0_executor.py',Path(__file__),EXP/'scripts/validate_t1.py',EXP/'schemas/t1_skill_output.schema.json']
    snapshot_name='t1_freecad_method_snapshot_replay_01.json'if args.part else't1_freecad_method_snapshot.json';(RESULTS/snapshot_name).write_text(json.dumps({'created_at':datetime.now(timezone.utc).isoformat(),'replay_part':args.part,'files':{str(p.relative_to(EXP)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}},indent=2)+'\n')
    gates={r['part_id']:r for r in csv.DictReader((RESULTS/'t1_plan_gate.csv').open())};rows=[];pids=[f'R01_P{i:02d}'for i in range(5)]+[f'R02_P{i:02d}'for i in range(7)]
    if args.part:pids=[args.part]
    for pid in pids:
        out=OUT/pid/'round_0'
        if gates[pid]['status']!='PASS':rows.append({'part_id':pid,'status':'PLAN_INCOMPLETE','returncode':'','elapsed_seconds':0,'error':gates[pid]['errors']});continue
        job={'repo_root':str(ROOT),'agent_output':str(out/'agent_output.json'),'output':str(out)};path=out/'freecad_job.json';path.write_text(json.dumps(job,indent=2)+'\n');started=time.time();p=subprocess.run([str(RUNTIME),str(HELPER),str(path)],cwd=ROOT,capture_output=True,text=True,timeout=600);elapsed=time.time()-started
        (out/'freecad_stdout.txt').write_text(p.stdout);(out/'freecad_stderr.txt').write_text(p.stderr);result=json.loads((out/'execution_result.json').read_text()) if (out/'execution_result.json').is_file() else {'status':'FAILURE','error':'missing result'}
        rows.append({'part_id':pid,'status':result['status'],'returncode':p.returncode,'elapsed_seconds':elapsed,'error':result.get('error','')});print(pid,result['status'],flush=True)
    path=RESULTS/'t1_execution.csv'
    if args.part and path.exists():
        with path.open(newline='',encoding='utf-8')as f:old=list(csv.DictReader(f))
        rows=[r for r in old if r['part_id']!=args.part]+rows;rows.sort(key=lambda r:r['part_id'])
    with path.open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return 0 if all(r['status']=='SUCCESS' for r in rows) else 1
if __name__=='__main__':raise SystemExit(main())
