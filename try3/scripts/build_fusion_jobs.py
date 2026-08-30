"""Build frozen V1/V2 Fusion jobs and record V0 provenance."""
from __future__ import annotations
import csv,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def digest(p):
 h=hashlib.sha256();h.update(p.read_bytes());return h.hexdigest()
def main():
 cases=list(csv.DictReader((ROOT/'try3/tryset5_v1.csv').open(encoding='utf-8-sig')));jobs=[];v0=[]
 for item in cases:
  case=item['case_id'];source=ROOT/'try2/runs/D'/case
  m=json.loads((source/'manifest.json').read_text());v0.append({'case_id':case,'source':str(source),'status':m['status'],'blueprint_sha256':digest(source/'blueprint.json') if (source/'blueprint.json').exists() else None,'fusion_f3d':str(source/'model.f3d')})
  for version in ('V1','V2'):
   run=ROOT/'try3/runs'/version/case;manifest=json.loads((run/'manifest.json').read_text())
   if manifest['status']!='SUCCESS':
    jobs.append({'case_id':case,'version':version,'status':'UPSTREAM_FAILURE','error':manifest.get('error')});continue
   job={'case_id':case,'version':version,'status':'READY','blueprint':json.loads((run/'blueprint.json').read_text()),'source_run':str(run)}
   if version=='V2':
    job['mep']=json.loads((run/'mechanical_embodiment_plan.json').read_text());job['interfaces']=json.loads((run/'interface_graph.json').read_text());job['features']=json.loads((run/'feature_graph.json').read_text())
   jobs.append(job)
 out=ROOT/'try3';(out/'results').mkdir(exist_ok=True)
 json.dump({'jobs':jobs},(out/'fusion_jobs.json').open('w'),indent=2)
 with (out/'results'/'v0_provenance.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(v0[0]));w.writeheader();w.writerows(v0)
 print(json.dumps({'jobs':len(jobs),'ready':sum(x['status']=='READY' for x in jobs)},indent=2))
if __name__=='__main__':main()
