import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';T=HERE/'try5A_2'
for arg in sys.argv[1:]:
 r=int(arg);p=T/f'D1/round_{r}/assembly_job.json';p.write_text(json.dumps({'root':str(ROOT),'round':r},indent=2)+'\n');x=subprocess.run([r'D:\\software\\freeCAD\\install\\bin\\python.exe',str(HERE/'scripts/freecad_assemble_d1_round.py'),str(p)],cwd=ROOT,capture_output=True,text=True,timeout=600);(T/f'D1/round_{r}/assembly_stdout.txt').write_text(x.stdout);(T/f'D1/round_{r}/assembly_stderr.txt').write_text(x.stderr);print(r,x.returncode)
 if x.returncode: raise SystemExit(x.returncode)
