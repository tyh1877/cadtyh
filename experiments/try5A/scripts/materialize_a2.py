"""Compile interface-first A2 from L1 Robot Plan and L2 Shared Interface Contracts."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';PLAN=HERE/'blackboard/robot_assembly_plan.json';GRAPH=HERE/'blackboard/joint_interface_graph.json';plan=json.loads(PLAN.read_text());graph=json.loads(GRAPH.read_text());ph=hashlib.sha256(PLAN.read_bytes()).hexdigest();gh=hashlib.sha256(GRAPH.read_bytes()).hexdigest();plans={x['link_id']:x for x in plan['links']};contracts={x['joint_id']:x for x in graph['joints']};FRAME={'origin':[0,0,0],'x_axis':[1,0,0],'y_axis':[0,1,0],'z_axis':[0,0,1]}
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def op(i,t,f,**kw):return {'op_id':f'op_{i:03d}','op_type':t,'target_body':kw.pop('target_body',f'op_{i:03d}'),'dependencies':kw.pop('dependencies',[]),'feature_ref':f,'reference_frame':FRAME,**kw}
for lid,lp in plans.items():
 a1=json.loads((HERE/f'A1/{lid}/agent_output.json').read_text());incident=[c for c in contracts.values() if lid in (c['parent_link'],c['child_link'])];ops=[];final=[];features=[];refs=[];n=1
 for c in incident:
  side='parent' if lid==c['parent_link'] else 'child';joint=c['joint_id'];j=c['consumption_trace']['l0_joint_fields'];center=np.array(j['origin_xyz_m'] if side=='parent' else [0,0,0],float);contract_center=center.copy();axis=np.array(j['axis'],float)
  if side=='parent':axis=np.array(j['origin_transform_parent'])[:3,:3]@axis
  radius=c['interface_envelope']['radius_m']*1000;depth=c['interface_envelope']['axial_depth_m']*1000;family=c['interface_family'];fid='IF_'+joint
  if side=='parent':
   if family=='linear_slider_interface':lo=j['limits']['lower']*1000;hi=j['limits']['upper']*1000;mid=(lo+hi)/2;center=center+axis*(mid/1000);engagement=abs(hi-lo)+2*depth
   else:engagement=depth
   outer=radius+0.75;inner=radius+0.30;ops += [op(n,'cylinder_primitive',fid,center=(center*1000).tolist(),axis=axis.tolist(),radius_mm=outer,height_mm=engagement,operation_mode='new_body'),op(n+1,'cylinder_primitive',fid,center=(center*1000).tolist(),axis=axis.tolist(),radius_mm=inner,height_mm=engagement*1.2,operation_mode='new_body'),op(n+2,'boolean_cut',fid,target_body=f'op_{n:03d}',dependencies=[f'op_{n:03d}',f'op_{n+1:03d}'],tool_bodies=[f'op_{n+1:03d}'])];final.append(f'op_{n+2:03d}');port_depth=engagement;n+=3
  else:
   port_depth=max(depth*.8,4);ops.append(op(n,'cylinder_primitive',fid,center=[0,0,0],axis=axis.tolist(),radius_mm=radius,height_mm=port_depth,operation_mode='new_body'));final.append(f'op_{n:03d}');n+=1
  refs.append({'joint_id':joint,'side':side,'center_local_m':contract_center.tolist(),'geometry_center_local_m':center.tolist(),'axis_local':axis.tolist(),'radius_mm':radius,'depth_mm':port_depth,'interface_family':family,'complementary_geometry':True,'contract_sha256':hashlib.sha256((HERE/f'interface_graph/contracts/{joint}.json').read_bytes()).hexdigest(),'target_gap_m':c['target_gap_m']});features.append({'feature_id':fid,'status':'PLANNED','critical':True,'feature_type':family+' '+side+' port','requirement_refs':[]})
 body=[x for x in a1['cad_ir']['operations'] if x['feature_ref']=='BODY'];mapping={}
 for x in body:
  y=json.loads(json.dumps(x));old=y['op_id'];y['op_id']=f'op_{n:03d}';y['target_body']=y['op_id'];mapping[old]=y['op_id'];ops.append(y);final.append(y['op_id']);n+=1
 features.append(next(x for x in a1['feature_graph']['features'] if x['feature_id']=='BODY'));edit={'object_id':ops[0]['op_id'],'property':'Radius','baseline_value':ops[0]['radius_mm'],'edit_fraction':.05};ir={'ir_version':'try5A_A2_interface_first_v1','units':'mm','bodies':[{'body_id':f'B{i:02d}','role':'interface-first link solid','feature_ids':sorted({x['feature_ref'] for x in ops}),'final_object':x} for i,x in enumerate(final)],'operations':ops,'final_objects':final,'editable_parameter':edit,'assumptions':['A2 consumes Robot Plan and Shared Joint Interface Contracts'],'silent_fallback_allowed':False};spec={k:lp[k] for k in ['link_id','role','coarse_envelope_m','principal_direction','body_family','proximal_region','distal_region']};spec.update({'robot_plan_sha256':ph,'joint_interface_graph_sha256':gh,'consumed_joint_contracts':[x['joint_id'] for x in refs],'modeling_order':['proximal interface','distal interface(s)','planned main body']});out=HERE/'A2'/lid;agent={'part_id':lid,'link_id':lid,'condition':'A2','feature_graph':{'features':features},'cad_ir':ir};dump(out/'agent_output.json',agent);dump(out/'LinkCoarseSpec.json',spec);dump(out/'InterfaceRefs.json',{'link_id':lid,'shared_contract_consumed':True,'interfaces':refs});dump(out/'cad_ir.json',ir);dump(out/'parameter_manifest.json',{'robot_plan_sha256':ph,'joint_interface_graph_sha256':gh,'contracts':refs})
print(json.dumps({'links':len(plans),'contracts_consumed':sum(len(json.loads((HERE/f'A2/{x}/InterfaceRefs.json').read_text())['interfaces']) for x in plans)}))
