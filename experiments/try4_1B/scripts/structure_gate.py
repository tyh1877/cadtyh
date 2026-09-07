"""Apply frozen B1 structure/shape gate and emit B2 trigger decisions."""
import csv,json,pandas as pd
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try4_1B';cfg=json.loads((HERE/'protocol.json').read_text())['shape_structure_gate'];g=pd.read_csv(HERE/'results/geometry_metrics.csv');t=pd.read_csv(HERE/'results/topology_metrics.csv');shape=pd.read_csv(HERE/'results/b1_shape_family_gate.csv');rows=[]
for pid in ('R02_P04','R02_P06'):
 a=g[(g.part_id==pid)&(g.condition=='B1')].iloc[0];b=t[(t.part_id==pid)&(t.condition=='B1')].iloc[0];checks={'shape_family':shape[shape.part_id==pid].iloc[0].status=='PASS','substructure_realization':b.substructure_realization_recall>=cfg['substructure_realization_recall_min'],'required_feature_coverage':b.required_feature_coverage>=cfg['required_feature_coverage_min'],'independent_topology':b.topology_relation_f1>=cfg['independent_topology_relation_f1_min'],'iou':a.voxel_iou>=cfg['voxel_iou_min'],'hd95':a.normalized_hd95<=cfg['normalized_hd95_max']};rows.append({'part_id':pid,'status':'PASS' if all(checks.values()) else 'STRUCTURE_REALIZATION_FAIL','trigger_b2':not all(checks.values()),'failed_checks':';'.join(k for k,v in checks.items() if not v)})
with (HERE/'results/b1_structure_gate.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(json.dumps(rows))
