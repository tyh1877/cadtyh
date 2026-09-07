"""Orchestrate deterministic GT Macro-Part mesh export using bundled FreeCAD."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';OUT=EXP/'evaluation_cache/gt';RUNTIME=Path(r'D:\software\freeCAD\install\bin\python.exe');HELPER=EXP/'scripts/freecad_export_gt_parts.py'
def main():
    provenance={x['robot_id']:x for x in json.loads((EXP/'robots/source_provenance.json').read_text(encoding='utf-8'))}
    for rid in ('R01','R02'):
        meta=json.loads((EXP/f'robots/semantic_parts/{rid}.json').read_text(encoding='utf-8'));src=ROOT/provenance[rid]['step_path']
        if hashlib.sha256(src.read_bytes()).hexdigest()!=provenance[rid]['step_sha256']:raise RuntimeError(rid+': source STEP hash mismatch')
        folder=OUT/rid;folder.mkdir(parents=True,exist_ok=True);job={'step':str(src),'parts':meta['parts'],'output':str(folder)};jp=folder/'job.json';jp.write_text(json.dumps(job,indent=2)+'\n',encoding='utf-8')
        subprocess.run([str(RUNTIME),str(HELPER),str(jp)],cwd=ROOT,check=True,timeout=600);print(rid,'GT exported')
if __name__=='__main__':main()
