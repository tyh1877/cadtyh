"""Hard-gate Try-2 before any result may be called complete."""
from __future__ import annotations
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 rows=[]
 for source,target in (('A','B'),('C','D')):
  for run in sorted((ROOT/'try2/runs'/source).glob('dev_arm-*')):
   manifest=run/'manifest.json'
   if manifest.exists() and json.loads(manifest.read_text()).get('status')!='SUCCESS':
    continue
   bp=run/'blueprint.json';fx=ROOT/'try2/runs'/target/run.name/'fusion_execution.json'
   if not bp.exists() or not fx.exists():rows.append({'condition':target,'case_id':run.name,'valid':False,'reason':'MISSING_ARTIFACT'});continue
   plan=json.loads(bp.read_text());r=json.loads(fx.read_text());valid=r['status']=='SUCCESS' and r.get('component_count')==len(plan['links']) and r.get('joint_count')==len(plan['joints'])
   rows.append({'condition':target,'case_id':run.name,'valid':valid,'expected_components':len(plan['links']),'actual_components':r.get('component_count'),'expected_joints':len(plan['joints']),'actual_joints':r.get('joint_count'),'reason':'' if valid else 'EXECUTION_OR_PRESERVATION'})
 out=ROOT/'try2/results';out.mkdir(exist_ok=True)
 with (out/'acceptance_check.csv').open('w',newline='') as h:w=csv.DictWriter(h,fieldnames=sorted({k for r in rows for k in r}));w.writeheader();w.writerows(rows)
 if not all(r['valid'] for r in rows):raise SystemExit('ACCEPTANCE_FAILED')
if __name__=='__main__':main()
