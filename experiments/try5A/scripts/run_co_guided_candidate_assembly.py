import json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];T=ROOT/'experiments/try5A/try5A_2';p=T/'mechanism_validation/candidate/assembly_job.json';p.write_text(json.dumps({'root':str(ROOT)},indent=2)+'\n');x=subprocess.run([r'D:\software\freeCAD\install\bin\python.exe',str(ROOT/'experiments/try5A/scripts/freecad_assemble_co_guided_candidate.py'),str(p)],cwd=ROOT,capture_output=True,text=True,timeout=600);print(x.stdout or x.stderr);raise SystemExit(x.returncode)
