"""Freeze formal Fusion API jobs from schema-validated RobotCAD SkillCalls."""
from __future__ import annotations
import csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from robotcad.validators.validate_skill_calls import validate
def main():
 jobs=[]
 for row in csv.DictReader((ROOT/'try3/tryset5_v1.csv').open(encoding='utf-8-sig')):
  for version in ('V1','V2'):
   run=ROOT/'try3/runs'/version/row['case_id'];m=json.loads((run/'manifest.json').read_text())
   if m['status']!='SUCCESS':jobs.append({'case_id':row['case_id'],'version':version,'status':'UPSTREAM_FAILURE','error':m['error']});continue
   jobs.append({'case_id':row['case_id'],'version':version,'status':'READY','calls':validate(run/'skill_calls.json')['calls']})
 out=ROOT/'try3/fusion_api_jobs.json';out.write_text(json.dumps({'backend':'FusionAPIBackend.v1','jobs':jobs},indent=2));print(json.dumps({'jobs':len(jobs),'ready':sum(x['status']=='READY' for x in jobs)},indent=2))
if __name__=='__main__':main()
