"""Run canonical A2 whole-robot assembly."""
import json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';out=HERE/'assemblies/A2';job={'root':str(ROOT),'output':str(out),'skeleton':str(HERE/'blackboard/kinematic_skeleton.json')};p=HERE/'results/a2_assembly_job.json';p.write_text(json.dumps(job,indent=2)+'\n');r=subprocess.run([r'D:\software\freeCAD\install\bin\python.exe',str(HERE/'scripts/freecad_assemble_a2.py'),str(p)],cwd=ROOT,capture_output=True,text=True,timeout=600);(HERE/'results/a2_assembly_stdout.txt').write_text(r.stdout);(HERE/'results/a2_assembly_stderr.txt').write_text(r.stderr);print((out/'assembly_result.json').read_text() if (out/'assembly_result.json').exists() else r.stderr);raise SystemExit(r.returncode)


