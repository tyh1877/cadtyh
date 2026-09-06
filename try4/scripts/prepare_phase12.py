"""Root-.venv orchestration of offline reference preparation only."""
import csv
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
EXP=ROOT/'try4'
SOURCES=ROOT/'go_nogo1/sources/step_calibration/trossen'
SELECTED=[('R01','px100','DEV_A'),('R02','vx300s','DEV_B'),('R03','rx200','TRANSFER')]
RUNTIME=Path(r'D:\software\freeCAD\install\bin\python.exe')

def dump(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')

def main():
    sources={r['slug']:r for r in csv.DictReader((SOURCES/'source_manifest.csv').open(encoding='utf-8-sig'))}
    inventory_only='--inventory' in sys.argv
    for rid,slug,role in SELECTED:
        out=EXP/'artifacts'/rid
        job={'step':sources[slug]['step_files'],'output':str(out),'inventory_only':inventory_only}
        if not inventory_only:job['parts']=json.loads((EXP/'robots/semantic_parts'/f'{rid}.json').read_text())['parts']
        dump(out/'reference_job.json',job)
        p=subprocess.run([str(RUNTIME),str(EXP/'scripts/freecad_reference.py'),str(out/'reference_job.json')],cwd=ROOT,capture_output=True,text=True,timeout=600)
        (out/'renderer_stdout.txt').write_text(p.stdout,encoding='utf-8');(out/'renderer_stderr.txt').write_text(p.stderr,encoding='utf-8')
        if p.returncode:raise RuntimeError(f'{rid}: {p.stderr[-1200:]}')
        print(rid,'inventory ready' if inventory_only else 'rendered',flush=True)

if __name__=='__main__':main()
