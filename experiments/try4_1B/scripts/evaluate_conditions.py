"""Evaluate B0/B1/B2 with unchanged Try-4 Phase-5 geometry metrics."""
import argparse,csv,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try4_1B';TRY4=ROOT/'try4';sys.path.insert(0,str(TRY4/'scripts'));from evaluate_phase5 import evaluate
ap=argparse.ArgumentParser();ap.add_argument('--conditions',nargs='+',required=True);a=ap.parse_args();rows=[]
for pid in ('R02_P04','R02_P06'):
 idx=10+int(pid[-2:]);gt=TRY4/f'evaluation_cache/gt/R02/{pid}.stl'
 for cond in a.conditions:
  if cond=='B0':pathcond='../experiments/try4_1A/A1';mesh=ROOT/f'experiments/try4_1A/A1/{pid}/round_0/model.stl'
  else:pathcond=f'../experiments/try4_1B/{cond}';mesh=HERE/f'{cond}/{pid}/round_0/model.stl'
  if not mesh.exists():continue
  r=evaluate(pathcond,pid,gt,mesh,idx);r['condition']=cond;rows.append(r);print(cond,pid,r['gate_status'])
out=HERE/'results/geometry_metrics.csv';existing=[]
if out.exists():
 with out.open(encoding='utf-8') as f:existing=list(csv.DictReader(f))
keys={(x['condition'],x['part_id']) for x in rows};rows=[x for x in existing if (x['condition'],x['part_id']) not in keys]+rows;rows.sort(key=lambda x:(x['part_id'],x['condition']))
with out.open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
