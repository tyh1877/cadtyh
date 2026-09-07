"""Create aggregate, shape-family and resource tables for Try-4.1A."""
import json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/'experiments/try4_1A'
g=pd.read_csv(HERE/'results/geometry_metrics.csv')
t=pd.read_csv(HERE/'results/topology_metrics.csv')
metrics=['voxel_iou','normalized_chamfer','normalized_hd95','silhouette_iou_mean','mfr_trace','critical_feature_recall_trace']
gs=g.groupby('condition')[metrics].mean().reset_index()
ts=t.groupby('condition')[['component_region_count_accuracy','branch_fork_accuracy','opening_gap_recall','topology_relation_f1','topology_node_role_f1','realized_node_fraction']].mean().reset_index()
gs.merge(ts,on='condition').to_csv(HERE/'results/condition_summary.csv',index=False)
plans=json.loads((HERE/'planning_inputs.json').read_text())['parts']
manual={'R02_P02':'PASS','R02_P04':'PARTIAL','R02_P05':'PASS','R02_P06':'PARTIAL'}
rows=[{'part_id':p['part_id'],'selected_families':';'.join(p['A2_plan']['families']),'family_count':len(p['A2_plan']['families']),'manual_shape_family_fit':manual[p['part_id']],'assessment_scope':'development diagnostic, not independent judge'} for p in plans]
pd.DataFrame(rows).to_csv(HERE/'results/shape_family_metrics.csv',index=False)
pd.DataFrame([{'condition':'A0','parts':4,'new_agent_planning_outputs':0,'new_freecad_builds':0,'extra_method_stage':'none (frozen T1)'},{'condition':'A1','parts':4,'new_agent_planning_outputs':4,'new_freecad_builds':4,'extra_method_stage':'Mechanical Topology Graph'},{'condition':'A2','parts':4,'new_agent_planning_outputs':4,'new_freecad_builds':4,'extra_method_stage':'Topology Graph + Shape-Family Selection'}]).to_csv(HERE/'results/resource_metrics.csv',index=False)
print(gs.to_json(orient='records'))
