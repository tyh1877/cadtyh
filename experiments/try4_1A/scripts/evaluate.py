"""Run identical geometry evaluator plus frozen plan-realization topology metrics."""
import csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try4_1A';TRY4=ROOT/'try4';sys.path.insert(0,str(TRY4/'scripts'));from evaluate_phase5 import evaluate
PIDS=['R02_P02','R02_P04','R02_P05','R02_P06'];geometry=[]
for pid in PIDS:
 idx=10+int(pid[-2:]);gt=TRY4/f'evaluation_cache/gt/R02/{pid}.stl'
 for cond,pathcond,mesh in [('A0','T1',TRY4/f'T1/{pid}/round_0/model.stl'),('A1','../experiments/try4_1A/A1',HERE/f'A1/{pid}/round_0/model.stl'),('A2','../experiments/try4_1A/A2',HERE/f'A2/{pid}/round_0/model.stl')]:
  row=evaluate(pathcond,pid,gt,mesh,idx);row['condition']=cond;geometry.append(row);print(cond,pid,row['gate_status'],flush=True)
with (HERE/'results/geometry_metrics.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(geometry[0]));w.writeheader();w.writerows(geometry)
with (HERE/'results/feature_metrics.csv').open('w',newline='',encoding='utf-8') as f:
 fields=['part_id','condition','mfr_trace','mechanical_feature_precision_trace','critical_feature_recall_trace','cad_valid','editability_pass'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows([{k:r[k] for k in fields} for r in geometry])
