"""Deterministic blackboard transition, stagnation and regression protection."""
import argparse,json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';CFG=json.loads((EXP/'protocol/phase78_repair_protocol_v1.json').read_text());base=pd.read_csv(EXP/'results/phase5_metrics.csv')
def failed(m):return set(m.get('failed_criteria','').split(';'))-set([''])
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--part',required=True);ap.add_argument('--round',type=int,required=True);args=ap.parse_args();pid=args.part;r=args.round;out=EXP/'T2'/pid/f'round_{r}';cur=json.loads((out/'metrics.json').read_text());contract=json.loads((out/'review_contract.json').read_text());repair=json.loads((out/'repair_log.json').read_text());post=json.loads((out/'post_review.json').read_text()) if (out/'post_review.json').exists() else {'overall_pass':False,'recommended_state':'REPLAN' if cur['gate_status']=='PASS' else cur['gate_status'],'evidence':['post-review not yet available']}
 if r==1:prev=base[(base.part_id==pid)&(base.condition=='T1')].iloc[0].to_dict();history=[];prev_artifact=f'T1/{pid}/round_0/model.FCStd'
 else:
  ps=json.loads((EXP/'T2'/pid/f'round_{r-1}/part_state.json').read_text());prev=ps['previous_metrics'] if '#' in ps['accepted_metrics'] else json.loads((EXP/ps['accepted_metrics']).read_text());history=ps['repair_history'];prev_artifact=ps['current_artifact']
 newfail=failed(cur)-failed(prev);reg=CFG['regression'];regression=bool(newfail or cur['voxel_iou']<prev['voxel_iou']-reg['iou_drop'] or cur['normalized_chamfer']>prev['normalized_chamfer']+reg['normalized_chamfer_increase'] or cur['normalized_hd95']>prev['normalized_hd95']+reg['normalized_hd95_increase'] or not all(repair['protection'].values()))
 st=CFG['stagnation'];improved=bool(cur['voxel_iou']>=prev['voxel_iou']+st['iou_min_gain'] or cur['normalized_chamfer']<=prev['normalized_chamfer']-st['normalized_chamfer_min_reduction'] or cur['normalized_hd95']<=prev['normalized_hd95']-st['normalized_hd95_min_reduction'])
 accepted=not regression;state='FROZEN' if accepted and cur['gate_status']=='PASS' and post['overall_pass'] else (post['recommended_state'] if cur['gate_status']=='PASS' else cur['gate_status'])
 if regression:state=contract['status'];accepted_metrics=(f'results/phase5_metrics.csv#{pid},T1' if r==1 else json.loads((EXP/'T2'/pid/f'round_{r-1}/part_state.json').read_text())['accepted_metrics']);current=prev_artifact
 else:accepted_metrics=str((out/'metrics.json').relative_to(EXP));current=str((out/'model.FCStd').relative_to(EXP))
 if accepted and state!='FROZEN' and not improved:state='REPLAN' if contract['status']=='LOCAL_REPAIR' else 'UNRESOLVED'
 if r>=CFG['max_repair_rounds'] and state!='FROZEN':state='UNRESOLVED'
 fs={f['feature_id']:('PASS_FROZEN' if f['feature_id'] in contract['protected_features'] else ('FAIL_REPLAN' if state in ('REPLAN','UNRESOLVED') else 'FAIL_REPAIR')) for f in json.loads((out/'feature_graph.json').read_text())['features']}
 event={'round':r,'contract_status':contract['status'],'candidate_gate':cur['gate_status'],'post_review_pass':post['overall_pass'],'accepted':accepted,'regression':regression,'new_failed_gates':sorted(newfail),'improved':improved,'resulting_state':state}
 result={'part_id':pid,'state':state,'repair_round':r,'quality_gates':{'failed':sorted(failed(cur if accepted else prev))},'feature_states':fs,'current_artifact':current,'accepted_metrics':accepted_metrics,'previous_metrics':prev,'repair_history':history+[event]};(out/'part_state.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(event));
if __name__=='__main__':main()
