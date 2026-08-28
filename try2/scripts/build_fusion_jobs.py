"""Create non-secret Fusion build jobs from already generated A/C blueprints."""
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 jobs=[]
 for source,target in (('A','B'),('C','D')):
  for path in sorted((ROOT/'try2/runs'/source).glob('dev_arm-*/blueprint.json')):
   jobs.append({'case_id':path.parent.name,'source_condition':source,'target_condition':target,'blueprint':json.loads(path.read_text())})
 (ROOT/'try2/fusion_jobs.json').write_text(json.dumps({'jobs':jobs},indent=2))
if __name__=='__main__':main()
