"""Allowed deterministic bbox/silhouette discrepancy evidence for reviewers."""
import csv,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';sys.path.insert(0,str(EXP/'scripts'))
from evaluate_phase5 import load,rigid_align,SEED
rows=[]
for idx,(rid,count) in enumerate((('R01',5),('R02',7))):
    for i in range(count):
        pid=f'{rid}_P{i:02d}';gt=load(EXP/f'evaluation_cache/gt/{rid}/{pid}.stl');pr=load(EXP/f'T1/{pid}/round_0/model.stl');pr.apply_transform(rigid_align(gt,pr,SEED+500+idx*100+i));g=gt.bounds[1]-gt.bounds[0];p=pr.bounds[1]-pr.bounds[0]
        row={'part_id':pid}
        for j,a in enumerate('xyz'):row[f'gt_extent_{a}_mm']=g[j];row[f'generated_extent_{a}_mm']=p[j];row[f'delta_generated_minus_gt_{a}_mm']=p[j]-g[j];row[f'ratio_gt_over_generated_{a}']=g[j]/p[j]
        rows.append(row)
with (EXP/'results/phase6_regional_discrepancies.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(len(rows))
