"""Write B2 final gate and CAD validity tables without changing frozen evaluators."""
import csv,json,pandas as pd
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try4_1B';cfg=json.loads((HERE/'protocol.json').read_text())['shape_structure_gate'];g=pd.read_csv(HERE/'results/geometry_metrics.csv');t=pd.read_csv(HERE/'results/topology_metrics.csv');rows=[];cad=[]
for pid in ('R02_P04','R02_P06'):
 a=g[(g.part_id==pid)&(g.condition=='B2')].iloc[0];b=t[(t.part_id==pid)&(t.condition=='B2')].iloc[0];checks={'substructure_realization':b.substructure_realization_recall>=cfg['substructure_realization_recall_min'],'required_feature_coverage':b.required_feature_coverage>=cfg['required_feature_coverage_min'],'independent_topology':b.topology_relation_f1>=cfg['independent_topology_relation_f1_min'],'iou':a.voxel_iou>=cfg['voxel_iou_min'],'hd95':a.normalized_hd95<=cfg['normalized_hd95_max']};rows.append({'part_id':pid,'condition':'B2','status':'PASS' if all(checks.values()) else 'STRUCTURE_REALIZATION_FAIL','failed_checks':';'.join(k for k,v in checks.items() if not v)})
 for cond,path in [('B0',ROOT/f'experiments/try4_1A/A1/{pid}/round_0'),('B1',HERE/f'B1/{pid}/round_0'),('B2',HERE/f'B2/{pid}/round_0')]:
  v=json.loads((path/'cad_validity.json').read_text());cad.append({'part_id':pid,'condition':cond,'fcstd_valid':v['status']=='SUCCESS','reopen':v['reopen']['status'],'recompute':'PASS','step_export':v['exports']['step'],'stl_export':v['exports']['stl'],'editable':v['editability']['edited_valid'] and v['editability']['restored_valid'],'silent_fallbacks':v['fallback_count']})
for name,data in [('b2_final_gate.csv',rows),('cad_validity.csv',cad)]:
 with (HERE/'results'/name).open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
print(json.dumps(rows))
