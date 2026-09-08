"""Create a selective D1 candidate from previous exact collision evidence."""
import copy,json,sys
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';T=HERE/'try5A_2';truth={'ADJACENT_UNINTENDED','NONADJACENT_TRUE','MOTION_ADJACENT_UNINTENDED','MOTION_INDUCED_TRUE'};round_no=int(sys.argv[1]);prev=round_no-1
if prev==0:
 raw=json.loads((T/'evaluator/raw/d0p_collision_rows.json').read_text())
 oldline=json.loads((T/'D1/round_0/lineage.json').read_text())
else:
 accepted=T/f'D1/round_{prev}/accepted_collision_rows.json'
 raw=json.loads((accepted if accepted.exists() else T/f'D1/round_{prev}/collision_rows.json').read_text())
 line_path=T/f'D1/round_{prev}/accepted_lineage.json'
 oldline=json.loads((line_path if line_path.exists() else T/f'D1/round_{prev}/lineage.json').read_text());hist=json.loads((T/'blackboard/d1_scheduler_state.json').read_text());agg=defaultdict(lambda:{'rows':[],'volume':0.0})
for x in raw:
 if x['classification'] in truth:
  k=(x['link_a'],x['link_b']);agg[k]['rows'].append(x);agg[k]['volume']+=float(x.get('intersection_volume_mm3') or 0)
# Rank by exact volume; favor an endpoint not yet repaired, otherwise retry the highest unresolved source.
rank=sorted(agg.items(),key=lambda q:-q[1]['volume']);seen=[x['link_id'] for x in hist['history']];pair,data=next(((p,d) for p,d in rank if p[0] not in seen or p[1] not in seen),rank[0]);target=pair[0] if pair[0] not in seen else pair[1];src=Path(oldline[target]['model_dir']);ir=json.loads((src/'cad_ir.json').read_text());body=[x for x in ir['operations'] if x['feature_ref']=='BODY'];op=body[0];before=copy.deepcopy(op)
# This changes one declared body region only; interfaces and attachment operations remain byte-identical.
if op['op_type']=='cylinder_primitive':
 op['radius_mm']*=0.70;op['height_mm']*=0.90;params={'radius_mm':'*0.70','height_mm':'*0.90'}
elif op['op_type']=='oriented_box':
 op['width_mm']*=0.65;op['depth_mm']*=0.65;params={'width_mm':'*0.65','depth_mm':'*0.65'}
elif op['op_type']=='lofted_prism':
 op['start_size_mm']=[v*.65 for v in op['start_size_mm']];op['end_size_mm']=[v*.65 for v in op['end_size_mm']];params={'section_sizes':'*0.65'}
else:raise RuntimeError(op['op_type'])
out=T/f'D1/round_{round_no}/links/{target}';out.mkdir(parents=True,exist_ok=True);ir['ir_version']=f'try5A_2_d1_round_{round_no}_local_region_v1';ir['repair_consumption']={'contract_source':f'repair_contracts/{target}.json','target_region':'middle_body_region','before':before,'after':op,'parameters':params};(out/'cad_ir.json').write_text(json.dumps(ir,indent=2)+'\n');(out/'agent_output.json').write_text(json.dumps({'part_id':target,'link_id':target,'condition':f'D1_round_{round_no}','cad_ir':ir},indent=2)+'\n');(out/'InterfaceRefs.json').write_bytes((src/'InterfaceRefs.json').read_bytes());(out/'attachment_manifest.json').write_bytes((src/'attachment_manifest.json').read_bytes())
contract={'repair_id':f'D1_R{round_no}_{target}_middle','round':round_no,'link_id':target,'region':'middle_body_region','failure_type':'LOCAL_COLLISION_FAIL','collision_pair':list(pair),'collision_with':pair[1] if target==pair[0] else pair[0],'critical_poses':[{'pose_id':x['pose_id'],'active_joint':x['active_joint'],'intersection_volume_mm3':x['intersection_volume_mm3']} for x in data['rows']],'current_intersection_volume_mm3':data['volume'],'repair_action':'LOCAL_SECTION_SHRINK','parameter_targets':params,'protected':['proximal_interface_region','distal_interface_region','frozen InterfaceRefs'],'must_preserve':['body-interface connectivity','link centerline continuity'],'cad_ir_target_operation':before['op_id']};(T/f'D1/round_{round_no}/repair_contracts/{target}.json').parent.mkdir(parents=True,exist_ok=True);(T/f'D1/round_{round_no}/repair_contracts/{target}.json').write_text(json.dumps(contract,indent=2)+'\n')
lineage=copy.deepcopy(oldline);lineage[target]={'model_dir':str(out.resolve()),'cad_ir':str((out/'cad_ir.json').resolve()),'origin':f'D1_round_{round_no}'};(T/f'D1/round_{round_no}/lineage.json').write_text(json.dumps(lineage,indent=2)+'\n');(T/f'D1/round_{round_no}/repair_queue.json').write_text(json.dumps([contract],indent=2)+'\n');print(json.dumps({'round':round_no,'target':target,'pair':pair,'volume':data['volume'],'params':params}))
