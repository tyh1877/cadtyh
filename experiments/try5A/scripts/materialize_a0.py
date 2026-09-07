"""Compile independent A0 links from sanitized URDF local context; no L1/L2 access."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';sys.path.insert(0,str(HERE/'scripts'));from kinematics import parse
FRAME={'origin':[0,0,0],'x_axis':[1,0,0],'y_axis':[0,1,0],'z_axis':[0,0,1]}
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def op(i,t,f,**kw):return {'op_id':f'op_{i:03d}','op_type':t,'target_body':kw.pop('target_body',f'op_{i:03d}'),'dependencies':kw.pop('dependencies',[]),'feature_ref':f,'reference_frame':FRAME,**kw}
src=HERE/'inputs/sanitized_urdf/px100_sanitized.urdf';links,joints=parse(src);dec=json.loads((HERE/'codex_authored/A0/independent_link_decisions.json').read_text());by={x['link_id']:x for x in dec['parts']};rows=[]
for lid in links:
 d=by[lid];parent=next((j for j in joints if j['child']==lid),None);children=[j for j in joints if j['parent']==lid];ops=[];final=[];features=[];n=1;env=d['envelope_mm']
 # Interface geometry is independently sized by this link's own decision.
 incident=([parent] if parent else [])+children
 for j in incident:
  center=[0,0,0] if parent and j['joint_id']==parent['joint_id'] else [v*1000 for v in j['origin_xyz_m']];axis=j['axis'];q=d['ports'][j['joint_id']];fid='IF_'+j['joint_id'];ops.append(op(n,'cylinder_primitive',fid,center=center,axis=axis,radius_mm=q['radius_mm'],height_mm=q['depth_mm'],operation_mode='new_body'));final.append(f'op_{n:03d}');n+=1;features.append({'feature_id':fid,'status':'PLANNED','critical':True,'feature_type':'independent interface','requirement_refs':[]})
 endpoints=[[v*1000 for v in j['origin_xyz_m']] for j in children];end=max(endpoints,key=lambda x:sum(v*v for v in x),default=[max(env[0],10),0,0]);start=[0,0,0]
 if sum((end[i]-start[i])**2 for i in range(3))<1e-6:end=[max(env[0],10),0,0]
 fid='BODY';
 if d['body_family'] in ('base_housing','rotary_housing','interface_marker'):ops.append(op(n,'cylinder_primitive',fid,center=[0,0,env[2]/2],axis=[0,0,1],radius_mm=max(env[0],env[1])/2,height_mm=env[2],operation_mode='new_body'))
 else:ops.append(op(n,'oriented_box',fid,start=start,end=end,width_mm=max(env[1],4),depth_mm=max(env[2],4),operation_mode='new_body'))
 final.append(f'op_{n:03d}');edit={'object_id':f'op_{n:03d}','property':'Radius' if d['body_family'] in ('base_housing','rotary_housing','interface_marker') else 'Length','baseline_value':max(env[0],env[1])/2 if d['body_family'] in ('base_housing','rotary_housing','interface_marker') else max(env[1],4),'edit_fraction':.05};features.append({'feature_id':fid,'status':'PLANNED','critical':True,'feature_type':'independent coarse body','requirement_refs':[]})
 ir={'ir_version':'try5A_A0_cad_ir_v1','units':'mm','bodies':[{'body_id':f'B{i:02d}','role':'independent link solid','feature_ids':[features[min(i,len(features)-1)]['feature_id']],'final_object':x} for i,x in enumerate(final)],'operations':ops,'final_objects':final,'editable_parameter':edit,'assumptions':['A0 independent link: no Robot Plan or Shared Interface Contract consumed'],'silent_fallback_allowed':False};spec={'link_id':lid,'role':d['role'],'body_family':d['body_family'],'coarse_dimensions_mm':env,'local_parent_joint':parent,'local_child_joints':children,'structural_path':'local parent interface -> independent body -> local child interface(s)','input_scope':['images','engineering_text','sanitized_urdf','local_link_context']};refs={'link_id':lid,'independent_design':True,'interfaces':[{'joint_id':j['joint_id'],'side':'proximal' if parent and j['joint_id']==parent['joint_id'] else 'distal','center_local_m':[0,0,0] if parent and j['joint_id']==parent['joint_id'] else j['origin_xyz_m'],'axis_local':j['axis'],**d['ports'][j['joint_id']]} for j in incident]};out=HERE/f'A0/{lid}';agent={'part_id':lid,'link_id':lid,'condition':'A0','feature_graph':{'features':features},'cad_ir':ir};dump(out/'agent_output.json',agent);dump(out/'LinkCoarseSpec.json',spec);dump(out/'InterfaceRefs.json',refs);dump(out/'cad_ir.json',ir);dump(out/'parameter_manifest.json',{'link_id':lid,'decision_source_sha256':hashlib.sha256((HERE/'codex_authored/A0/independent_link_decisions.json').read_bytes()).hexdigest(),'parameters':d});rows.append(lid)
print(json.dumps({'links':len(rows)}))
