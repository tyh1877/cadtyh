"""Compile interface-first A2 with family-specific mechanical CAD semantics."""
import hashlib,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';PLAN=HERE/'blackboard/robot_assembly_plan.json';GRAPH=HERE/'blackboard/joint_interface_graph.json';plan=json.loads(PLAN.read_text());graph=json.loads(GRAPH.read_text());ph=hashlib.sha256(PLAN.read_bytes()).hexdigest();gh=hashlib.sha256(GRAPH.read_bytes()).hexdigest();plans={x['link_id']:x for x in plan['links']};contracts={x['joint_id']:x for x in graph['joints']};FRAME={'origin':[0,0,0],'x_axis':[1,0,0],'y_axis':[0,1,0],'z_axis':[0,0,1]}
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def op(i,t,f,**kw):return {'op_id':f'op_{i:03d}','op_type':t,'target_body':kw.pop('target_body',f'op_{i:03d}'),'dependencies':kw.pop('dependencies',[]),'feature_ref':f,'reference_frame':FRAME,**kw}
def endpoints(center,axis,length_mm):
 half_m=length_mm/2000.0;return ((center-axis*half_m)*1000).tolist(),((center+axis*half_m)*1000).tolist()
def perpendicular(axis):
 ref=np.array([1.,0,0]) if abs(axis[0])<.8 else np.array([0.,1,0]);v=np.cross(axis,ref);return v/np.linalg.norm(v)
def editable(ops):
 for x in ops:
  if x['op_type']=='cylinder_primitive':return {'object_id':x['op_id'],'property':'Radius','baseline_value':x['radius_mm'],'edit_fraction':.05}
  if x['op_type']=='oriented_box':return {'object_id':x['op_id'],'property':'Length','baseline_value':x['width_mm'],'edit_fraction':.05}
 raise RuntimeError('no editable native primitive')
def realize(family,side,j,center,axis,radius,depth,fid,n):
 """Return operations, final objects, next id, realized depth and geometry center."""
 if family=='end_tool_interface':return [],[],n,0.0,center
 if family=='rail_slider_interface':
  if side=='parent':
   lo,hi=j['limits']['lower']*1000,j['limits']['upper']*1000;travel=abs(hi-lo);center=center+axis*((lo+hi)/2000);length=travel+2*depth
  else:length=max(depth*.9,5)
  a,b=endpoints(center,axis,length);item=op(n,'oriented_box',fid,start=a,end=b,width_mm=2.0*radius,depth_mm=1.25*radius,operation_mode='new_body');return [item],[item['op_id']],n+1,length,center
 if family=='planar_mount_interface':
  length=max(depth*.35,2.5);a,b=endpoints(center,axis,length);item=op(n,'oriented_box',fid,start=a,end=b,width_mm=2.0*radius,depth_mm=2.0*radius,operation_mode='new_body');return [item],[item['op_id']],n+1,length,center
 if family=='fork_pin_interface' and side=='parent':
  p=perpendicular(axis);offset=.72*radius/1000;length=max(depth,6);items=[]
  for k,s in enumerate((-1,1)):
   a,b=endpoints(center+p*offset*s,axis,length);items.append(op(n+k,'oriented_box',fid,start=a,end=b,width_mm=.55*radius,depth_mm=1.35*radius,operation_mode='new_body'))
  return items,[x['op_id'] for x in items],n+2,length,center
 if family=='flange_interface':
  length=max(depth*.4,3);item=op(n,'cylinder_primitive',fid,center=(center*1000).tolist(),axis=axis.tolist(),radius_mm=radius*1.2,height_mm=length,operation_mode='new_body');return [item],[item['op_id']],n+1,length,center
 if side=='child':
  length=max(depth*.8,4);item=op(n,'cylinder_primitive',fid,center=(center*1000).tolist(),axis=axis.tolist(),radius_mm=radius,height_mm=length,operation_mode='new_body');return [item],[item['op_id']],n+1,length,center
 length=depth;outer=radius+.75;inner=radius+.30;items=[op(n,'cylinder_primitive',fid,center=(center*1000).tolist(),axis=axis.tolist(),radius_mm=outer,height_mm=length,operation_mode='new_body'),op(n+1,'cylinder_primitive',fid,center=(center*1000).tolist(),axis=axis.tolist(),radius_mm=inner,height_mm=length*1.2,operation_mode='new_body'),op(n+2,'boolean_cut',fid,target_body=f'op_{n:03d}',dependencies=[f'op_{n:03d}',f'op_{n+1:03d}'],tool_bodies=[f'op_{n+1:03d}'])];return items,[f'op_{n+2:03d}'],n+3,length,center
for lid,lp in plans.items():
 out=HERE/'A2'/lid
 if lp['body_family']=='interface_marker':
  agent={'part_id':lid,'link_id':lid,'condition':'A2','link_realization_type':'virtual_frame','feature_graph':{'features':[]},'cad_ir':{'ir_version':'try5A_A2_virtual_frame_v2','units':'mm','bodies':[],'operations':[],'final_objects':[],'assumptions':['virtual frame: metadata only; no solid generation'],'silent_fallback_allowed':False}};dump(out/'agent_output.json',agent);dump(out/'LinkCoarseSpec.json',{'link_id':lid,'link_realization_type':'virtual_frame','robot_plan_sha256':ph,'joint_interface_graph_sha256':gh});dump(out/'InterfaceRefs.json',{'link_id':lid,'shared_contract_consumed':True,'interfaces':[]});dump(out/'cad_ir.json',agent['cad_ir']);dump(out/'parameter_manifest.json',{'link_id':lid,'virtual_frame':True});continue
 a1=json.loads((HERE/f'A1/{lid}/agent_output.json').read_text());incident=[c for c in contracts.values() if lid in (c['parent_link'],c['child_link'])];ops=[];final=[];features=[];refs=[];n=1
 for c in incident:
  side='parent' if lid==c['parent_link'] else 'child';joint=c['joint_id'];j=c['consumption_trace']['l0_joint_fields'];center=np.array(j['origin_xyz_m'] if side=='parent' else [0,0,0],float);contract_center=center.copy();axis=np.array(j['axis'],float)
  if side=='parent':axis=np.array(j['origin_transform_parent'])[:3,:3]@axis
  radius=c['interface_envelope']['radius_m']*1000;depth=c['interface_envelope']['axial_depth_m']*1000;family=c['interface_family'];fid='IF_'+joint;new_ops,new_final,n,port_depth,geometry_center=realize(family,side,j,center,axis,radius,depth,fid,n);ops.extend(new_ops);final.extend(new_final);source=c.get('interface_candidate_ranking',{});refs.append({'joint_id':joint,'side':side,'center_local_m':contract_center.tolist(),'geometry_center_local_m':geometry_center.tolist(),'axis_local':axis.tolist(),'radius_mm':radius,'depth_mm':port_depth,'interface_family':family,'geometry_semantics':'metadata_only' if family=='end_tool_interface' else family,'complementary_geometry':True,'contract_sha256':hashlib.sha256((HERE/f'interface_graph/contracts/{joint}.json').read_bytes()).hexdigest(),'target_gap_m':c['target_gap_m']});features.append({'feature_id':fid,'status':'PLANNED','critical':True,'feature_type':family+' '+side+' port','mechanical_role':'shared '+family+' '+side+' carrier','source_evidence':source.get('selection_reason','legacy contract'),'source_design_node':'InterfaceContract/'+joint,'why_required':'realize the shared interface at the URDF joint frame','related_interface_or_body':joint,'cad_strategy':'family-specific '+family+' realization','requirement_refs':[source.get('knowledge_source','')]})
 body=[x for x in a1['cad_ir']['operations'] if x['feature_ref']=='BODY']
 for x in body:
  y=json.loads(json.dumps(x));y['op_id']=f'op_{n:03d}';y['target_body']=y['op_id'];ops.append(y);final.append(y['op_id']);n+=1
 body_feature=json.loads(json.dumps(next(x for x in a1['feature_graph']['features'] if x['feature_id']=='BODY')));body_feature.update({'mechanical_role':'main '+lp['role']+' structural load path','source_evidence':'Robot Assembly Plan body family and neighboring interface locations','source_design_node':'LinkCoarseSpec/'+lid,'why_required':'connect declared proximal and distal interface regions','related_interface_or_body':lid,'cad_strategy':'planned '+lp['body_family']+' body primitive(s)','requirement_refs':['blackboard/robot_assembly_plan.json']});features.append(body_feature);ir={'ir_version':'try5A_A2_family_semantics_v2','units':'mm','bodies':[{'body_id':f'B{i:02d}','role':'interface-first link solid','feature_ids':sorted({x['feature_ref'] for x in ops}),'final_object':x} for i,x in enumerate(final)],'operations':ops,'final_objects':final,'editable_parameter':editable(ops),'assumptions':['A2 consumes Robot Plan and family-specific Shared Interface Contracts'],'silent_fallback_allowed':False};spec={k:lp[k] for k in ['link_id','role','coarse_envelope_m','principal_direction','body_family','proximal_region','distal_region']};spec.update({'robot_plan_sha256':ph,'joint_interface_graph_sha256':gh,'consumed_joint_contracts':[x['joint_id'] for x in refs],'modeling_order':['proximal interface','distal interface(s)','planned main body']});agent={'part_id':lid,'link_id':lid,'condition':'A2','feature_graph':{'features':features},'cad_ir':ir};dump(out/'agent_output.json',agent);dump(out/'LinkCoarseSpec.json',spec);dump(out/'InterfaceRefs.json',{'link_id':lid,'shared_contract_consumed':True,'interfaces':refs});dump(out/'cad_ir.json',ir);dump(out/'parameter_manifest.json',{'robot_plan_sha256':ph,'joint_interface_graph_sha256':gh,'contracts':refs})
print(json.dumps({'links':len(plans),'contracts_consumed':sum(len(json.loads((HERE/f'A2/{x}/InterfaceRefs.json').read_text())['interfaces']) for x in plans)}))
