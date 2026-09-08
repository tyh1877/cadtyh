import json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];T=ROOT/'experiments/try5A/try5A_2';out=T/'mechanism_validation/candidate/L00';p=out/'job.json';p.write_text(json.dumps({'repo_root':str(ROOT),'agent_output':str(out/'agent_output.json'),'output':str(out)},indent=2)+'\n');x=subprocess.run([r'D:\software\freeCAD\install\bin\python.exe',str(ROOT/'try4/scripts/freecad_t1_executor.py'),str(p)],cwd=ROOT,capture_output=True,text=True,timeout=600);print(x.stdout or x.stderr);raise SystemExit(x.returncode)
