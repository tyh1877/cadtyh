"""Freeze formal Fusion API jobs from schema-validated RobotCAD SkillCalls."""
from __future__ import annotations
import csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from robotcad.validators.validate_skill_calls import validate
def assert_real_skill_calls(value):
 calls=value['calls'];composites=[x for x in calls if x['skill']=='CreateCompositeLinkGeometry']
 if not composites:raise ValueError('missing CreateCompositeLinkGeometry; stale envelope-only skill calls')
 for item in composites:
  primitives=item['parameters'].get('primitives',[])
  if not primitives:raise ValueError(item['target_component']+' has no explicit primitives')
  if len(primitives)==1 and primitives[0].get('type')=='sphere' and float(primitives[0].get('radius',0))==10:
   raise ValueError(item['target_component']+' uses rejected fallback sphere primitive')
 return value
def main():
 jobs=[]
 for row in csv.DictReader((ROOT/'try3/tryset5_v1.csv').open(encoding='utf-8-sig')):
  for version in ('V1','V2'):
   run=ROOT/'try3/runs'/version/row['case_id'];m=json.loads((run/'manifest.json').read_text())
   if m['status']!='SUCCESS':jobs.append({'case_id':row['case_id'],'version':version,'status':'UPSTREAM_FAILURE','error':m['error']});continue
   try:jobs.append({'case_id':row['case_id'],'version':version,'status':'READY','calls':assert_real_skill_calls(validate(run/'skill_calls.json'))['calls']})
   except Exception as exc:jobs.append({'case_id':row['case_id'],'version':version,'status':'SKILL_PROJECTION_FAILURE','error':f'{type(exc).__name__}: {exc}'})
 out=ROOT/'try3/fusion_api_jobs.json';out.write_text(json.dumps({'backend':'FusionAPIBackend.v1.basic_operations','jobs':jobs},indent=2));print(json.dumps({'jobs':len(jobs),'ready':sum(x['status']=='READY' for x in jobs)},indent=2))
if __name__=='__main__':main()
