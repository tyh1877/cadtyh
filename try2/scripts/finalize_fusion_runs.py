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
   target_run=ROOT/'try2/runs'/target/source_run.name;fx=target_run/'fusion_execution.json'
   if not fx.is_file():continue
   result=json.loads(fx.read_text());bp=json.loads((source_run/'blueprint.json').read_text())
   if result['status']=='SUCCESS':write_urdf(bp,target_run)
   (target_run/'manifest.json').write_text(json.dumps({'case_id':source_run.name,'condition':target,'status':result['status'],'backend':'Fusion API','source_condition':source,'fusion_execution':'fusion_execution.json','prediction_urdf':'urdf/model.urdf' if result['status']=='SUCCESS' else None,'error':result.get('errors',[])},indent=2))
if __name__=='__main__':main()
