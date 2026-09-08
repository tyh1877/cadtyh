"""Invoke FreeCAD assembly reopen validation."""
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];p=subprocess.run([r'D:\software\freeCAD\install\bin\python.exe',str(ROOT/'experiments/try5A/scripts/freecad_validate_assemblies.py')],cwd=ROOT,capture_output=True,text=True,timeout=600);print(p.stdout);print(p.stderr);raise SystemExit(p.returncode)
