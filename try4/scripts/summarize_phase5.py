"""Produce deterministic Phase-5 summaries from the frozen metric table."""
import csv,json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';RES=EXP/'results';d=pd.read_csv(RES/'phase5_metrics.csv')
metrics=['voxel_iou','normalized_chamfer','normalized_hd95','silhouette_iou_mean','mfr_trace','critical_feature_recall_trace']
summary=d.groupby(['robot_id','condition'])[metrics].mean().reset_index();summary.to_csv(RES/'phase5_group_summary.csv',index=False)
p=d[d.robot_id.eq('R01')].pivot(index='part_id',columns='condition',values=metrics);rows=[]
for pid in p.index:
    row={'part_id':pid}
    for m in metrics:row[m+'_t0']=p.loc[pid,(m,'T0')];row[m+'_t1']=p.loc[pid,(m,'T1')];row[m+'_delta_t1_minus_t0']=row[m+'_t1']-row[m+'_t0']
    rows.append(row)
pd.DataFrame(rows).to_csv(RES/'phase5_paired_t0_t1.csv',index=False)
states=[{'part_id':r.part_id,'condition':r.condition,'state':'EVALUATED','gate_status':r.gate_status,'failed_criteria':r.failed_criteria.split(';') if isinstance(r.failed_criteria,str) else [],'repair_executed':False} for r in d.itertuples()]
(RES/'phase5_part_states.json').write_text(json.dumps({'phase':5,'states':states,'next_phase_not_started':True},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'rows':len(d),'groups':len(summary),'paired_parts':len(rows),'pass':int(d.gate_status.eq('PASS').sum()),'local_repair':int(d.gate_status.eq('LOCAL_REPAIR').sum()),'replan':int(d.gate_status.eq('REPLAN').sum())}))
if __name__=='__main__':pass
