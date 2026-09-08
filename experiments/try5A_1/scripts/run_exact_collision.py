"""Invoke FreeCAD exact collision evaluator."""
import json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A_1';p=HERE/'results/collision_job.json';p.write_text(json.dumps({'root':str(ROOT)},indent=2)+'\n');r=subprocess.run([r'D:\software\freeCAD\install\bin\python.exe',str(HERE/'scripts/freecad_exact_collision.py'),str(p)],cwd=ROOT,capture_output=True,text=True,timeout=1200);(HERE/'results/collision_stdout.txt').write_text(r.stdout);(HERE/'results/collision_stderr.txt').write_text(r.stderr);print(r.stdout);print(r.stderr);raise SystemExit(r.returncode)
