"""Execute FreeCAD collision evaluator for one condition."""
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A_1';c=sys.argv[1];job={'root':str(ROOT),'condition':c};p=HERE/'results'/f'{c.lower()}_collision_job.json';p.write_text(json.dumps(job,indent=2)+'\n');r=subprocess.run([r'D:\software\freeCAD\install\bin\python.exe',str(HERE/'scripts/freecad_condition_collision.py'),str(p)],cwd=ROOT,capture_output=True,text=True,timeout=600);(HERE/'results'/f'{c.lower()}_collision_stdout.txt').write_text(r.stdout);(HERE/'results'/f'{c.lower()}_collision_stderr.txt').write_text(r.stderr);print(r.stdout or r.stderr);raise SystemExit(r.returncode)
