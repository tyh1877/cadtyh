import json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';T=HERE/'try5A_2';r=int(sys.argv[1]);queue=json.loads((T/f'D1/round_{r}/repair_queue.json').read_text());rows=[]
for c in queue:
 lid=c['link_id'];out=T/f'D1/round_{r}/links/{lid}';job={'repo_root':str(ROOT),'agent_output':str(out/'agent_output.json'),'output':str(out)};p=out/'job.json';p.write_text(json.dumps(job,indent=2)+'\n');t=time.time();x=subprocess.run([r'D:\software\freeCAD\install\bin\python.exe',str(ROOT/'try4/scripts/freecad_t1_executor.py'),str(p)],cwd=ROOT,capture_output=True,text=True,timeout=600);res=json.loads((out/'execution_result.json').read_text());rows.append({'round':r,'link_id':lid,'status':res['status'],'elapsed_seconds':time.time()-t,'fallbacks':res.get('fallback_count'),'error':res.get('error','')});(out/'stdout.txt').write_text(x.stdout);(out/'stderr.txt').write_text(x.stderr)
(T/f'D1/round_{r}/execution.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows));raise SystemExit(not all(x['status']=='SUCCESS' for x in rows))
