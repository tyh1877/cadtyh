"""Phase 4-6: create D1 region state, pose-indexed localization and round plans."""
import json,sys
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';T=HERE/'try5A_2';truth={'ADJACENT_UNINTENDED','NONADJACENT_TRUE','MOTION_ADJACENT_UNINTENDED','MOTION_INDUCED_TRUE'}
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
types={x['link_id']:x for x in json.loads((T/'virtual_link_filter/link_realization_types.json').read_text())['links']};base=T/'D0_physicalized/links';regions={}
for lid,t in types.items():
 if not t['solid_generation_allowed']:continue
 ir=json.loads((base/lid/'cad_ir.json').read_text());body=[x['op_id'] for x in ir['operations'] if x['feature_ref']=='BODY'];ifs=[x['op_id'] for x in ir['operations'] if x['feature_ref'].startswith('IF_')];regions[lid]={'link_id':lid,'regions':{'proximal_interface_region':{'state':'FROZEN','operations':[x for x in ifs[:1]],'protected':True},'proximal_body_region':{'state':'FROZEN','operations':[],'protected':False},'middle_body_region':{'state':'REPLAN','operations':body,'protected':False},'distal_body_region':{'state':'FROZEN','operations':[],'protected':False},'distal_interface_region':{'state':'FROZEN','operations':ifs[1:],'protected':True}},'attachment_result_operations':[x['attachment_result_object'] for x in json.loads((base/lid/'attachment_manifest.json').read_text())]}
dump(T/'body_regions/d1_region_state_round0.json',regions)
raw=json.loads((T/'evaluator/raw/d0p_collision_rows.json').read_text());group=defaultdict(list)
for x in raw:
 if x['classification'] in truth:group[(x['link_a'],x['link_b'])].append(x)
loc=[]
for (a,b),xs in sorted(group.items(),key=lambda q:-sum(float(x.get('intersection_volume_mm3') or 0) for x in q[1])):
 for lid,other in ((a,b),(b,a)):
  loc.append({'link_id':lid,'region':'middle_body_region','collision_with':other,'critical_poses':[{'pose_id':x['pose_id'],'active_joint':x['active_joint'],'intersection_volume_mm3':x['intersection_volume_mm3']} for x in xs],'avoid_volume_source':'exact generated B-Rep common at critical poses','preferred_escape_direction':'REDUCE_LOCAL_CROSS_SECTION','protected_regions':['proximal_interface_region','distal_interface_region']})
dump(T/'pose_exclusion/d0p_pose_indexed_exclusions.json',loc)
# round 0 is a pure reference; all physical models resolve to D0_physicalized.
lineage={lid:{'model_dir':str((base/lid).resolve()),'cad_ir':str((base/lid/'cad_ir.json').resolve()),'origin':'D0_physicalized'} for lid,t in types.items() if t['solid_generation_allowed']};dump(T/'D1/round_0/lineage.json',lineage);dump(T/'D1/round_0/region_state.json',regions);dump(T/'D1/round_0/metrics.json',{'round':0,'source':'D0_physicalized','true_collision_events':sum(x['classification'] in truth for x in raw),'note':'frozen start; no rebuild'});dump(T/'blackboard/d1_scheduler_state.json',{'rounds_completed':0,'accepted_rounds':[],'rollback_count':0,'history':[]})
print(json.dumps({'physical_links':len(lineage),'pose_indexed_regions':len(loc),'round0_collision_events':sum(x['classification'] in truth for x in raw)}))
