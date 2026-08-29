"""Write evaluator-compatible URDF/manifests for successful native Fusion runs."""
from __future__ import annotations
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'go_nogo2/scripts'))
from compile_blueprint import write_urdf
def main():
 for source,target in (('A','B'),('C','D')):
  for source_run in (ROOT/'try2/runs'/source).glob('dev_arm-*'):
   target_run=ROOT/'try2/runs'/target/source_run.name;target_run.mkdir(parents=True,exist_ok=True)
   source_manifest=json.loads((source_run/'manifest.json').read_text()) if (source_run/'manifest.json').is_file() else {}
   fx=target_run/'fusion_execution.json'
   if fx.is_file():
    result=json.loads(fx.read_text());status=result['status'];errors=result.get('errors',[])
    bp=json.loads((source_run/'blueprint.json').read_text())
    if status=='SUCCESS':write_urdf(bp,target_run)
   else:
    # Preserve the frozen 15-case denominator when A/C planning failed.
    status='UPSTREAM_FAILURE';errors=[f'{source} planning status: {source_manifest.get("status","MISSING")}']
   (target_run/'manifest.json').write_text(json.dumps({'case_id':source_run.name,'condition':target,'status':status,'backend':'Fusion API','source_condition':source,'fusion_execution':'fusion_execution.json' if fx.is_file() else None,'prediction_urdf':'urdf/model.urdf' if status=='SUCCESS' else None,'error':errors},indent=2))
if __name__=='__main__':main()
