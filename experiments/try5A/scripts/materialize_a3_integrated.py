"""Apply accepted Try-5A.3 R0-R4 design repairs to the current Robot-A CAD IR."""
import copy,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';SRC=HERE/'A2';DST=HERE/'A3_integrated';FRAME={'origin':[0,0,0],'x_axis':[1,0,0],'y_axis':[0,1,0],'z_axis':[0,0,1]}
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def box(i,f,start,end,w,d):return {'op_id':f'op_{i:03d}','op_type':'oriented_box','target_body':f'op_{i:03d}','dependencies':[],'feature_ref':f,'reference_frame':FRAME,'start':start,'end':end,'width_mm':w,'depth_mm':d,'operation_mode':'new_body'}
def loft(i,f,start,end,a,b):return {'op_id':f'op_{i:03d}','op_type':'lofted_prism','target_body':f'op_{i:03d}','dependencies':[],'feature_ref':f,'reference_frame':FRAME,'start':start,'end':end,'start_size_mm':a,'end_size_mm':b,'operation_mode':'new_body'}
def fuse(ir,names,start):
 current=names[0];i=start
 for tool in names[1:]:
  oid=f'op_{i:03d}';ir['operations'].append({'op_id':oid,'op_type':'boolean_union','target_body':current,'dependencies':[current,tool],'feature_ref':'A3_RIGID_LOAD_PATH','reference_frame':FRAME,'tool_bodies':[tool]});current=oid;i+=1
 ir['final_objects']=[current];return current
def next_id(ir):return max(int(x['op_id'].split('_')[-1]) for x in ir['operations'])+1
def replace_body(ir,new_ops):
 old={x['op_id'] for x in ir['operations'] if x['feature_ref']=='BODY'};ir['operations']=[x for x in ir['operations'] if x['op_id'] not in old];ir['final_objects']=[x for x in ir['final_objects'] if x not in old];ir['operations'].extend(new_ops);ir['final_objects'].extend(x['op_id'] for x in new_ops)
repairs={
 'L00':['R4_INTERFACE_PAIR_REPLAN: nested outer housing with 0.5 mm radial clearance'],
 'L01':['R4_INTERFACE_PAIR_REPLAN: nested inner rotor and rebuilt adjacent region'],
 'L03':['R0_PARAMETER_REPAIR: J03 carrier radius','R1_LOCAL_FEATURE_REPAIR: tapered body-to-carrier transitions'],
 'L04':['R2_BODY_REGION_REPLAN: straight wrist block replaced by tapered structural region'],
 'L05':['R3_WHOLE_LINK_REPLAN: straight spacer replaced by dual side plates']}
for idx in range(12):
 lid=f'L{idx:02d}';src=SRC/lid;dst=DST/lid;agent=copy.deepcopy(json.loads((src/'agent_output.json').read_text()));ir=agent['cad_ir'];agent['condition']='A3_integrated';agent['part_id']=lid
 dst.mkdir(parents=True,exist_ok=True)
 for name in ('InterfaceRefs.json','LinkCoarseSpec.json','parameter_manifest.json'):
  if (src/name).is_file():shutil.copyfile(src/name,dst/name)
 if not ir.get('final_objects'):
  dump(dst/'agent_output.json',agent);dump(dst/'cad_ir.json',ir);dump(dst/'repair_manifest.json',{'link_id':lid,'repairs':[],'virtual_frame':True});continue
 ir['ir_version']='try5A3_integrated_robot_v1';ir['assumptions'].append('accepted Try-5A.3 repair scopes integrated into Robot A')
 if lid=='L00':
  cylinders=[x for x in ir['operations'] if x['feature_ref']=='IF_J00' and x['op_type']=='cylinder_primitive'];cylinders[0]['radius_mm']=24.0;cylinders[1]['radius_mm']=22.9;fuse(ir,list(ir['final_objects']),next_id(ir))
 elif lid=='L01':
  body=next(x for x in ir['operations'] if x['feature_ref']=='BODY');fuse(ir,list(ir['final_objects']),next_id(ir));ir['editable_parameter']={'object_id':body['op_id'],'property':'Radius','baseline_value':body['radius_mm'],'edit_fraction':.05}
 elif lid=='L03':
  cylinders=[x for x in ir['operations'] if x['feature_ref']=='IF_J03' and x['op_type']=='cylinder_primitive'];cylinders[0]['radius_mm']=14.5;cylinders[1]['radius_mm']=14.0;i=next_id(ir);replace_body(ir,[loft(i,'BODY_A3_TAPERED_WEB',[0,0,0],[100,0,0],[30,26],[24,20])]);fuse(ir,list(ir['final_objects']),next_id(ir));ir['editable_parameter']={'object_id':cylinders[0]['op_id'],'property':'Radius','baseline_value':14.5,'edit_fraction':.05}
 elif lid=='L04':
  i=next_id(ir);replace_body(ir,[loft(i,'BODY_A3_OFFSET_REGION',[0,0,0],[63,0,0],[42,34],[26,22])]);mount=next(x for x in ir['operations'] if x['feature_ref']=='IF_J04');fuse(ir,list(ir['final_objects']),next_id(ir));ir['editable_parameter']={'object_id':mount['op_id'],'property':'Length','baseline_value':mount['width_mm'],'edit_fraction':.05}
 elif lid=='L05':
  i=next_id(ir);plates=[box(i,'BODY_A3_LEFT_PLATE',[-3,-7,0],[9,-7,0],8,16),box(i+1,'BODY_A3_RIGHT_PLATE',[-3,7,0],[9,7,0],8,16)];replace_body(ir,plates);fuse(ir,list(ir['final_objects']),next_id(ir));ir['editable_parameter']={'object_id':plates[0]['op_id'],'property':'Length','baseline_value':8.0,'edit_fraction':.05}
 ir['bodies']=[{'body_id':'A3_'+lid,'role':'integrated repaired link','feature_ids':repairs.get(lid,[]),'final_object':x} for x in ir['final_objects']];agent['feature_graph']['features'].extend([{'feature_id':f'A3_REPAIR_{i+1}','status':'PLANNED','critical':True,'feature_type':r.split(':')[0],'mechanical_role':r.split(': ',1)[1],'source_evidence':'accepted Try-5A.3 physical pilot','source_design_node':'RepairScope/'+r.split(':')[0],'why_required':'integrate accepted design-level repair into whole robot','related_interface_or_body':lid,'cad_strategy':'regenerate affected link from updated CAD IR','requirement_refs':['Try5-A.3.md']} for i,r in enumerate(repairs.get(lid,[]))]);dump(dst/'agent_output.json',agent);dump(dst/'cad_ir.json',ir);dump(dst/'repair_manifest.json',{'link_id':lid,'repairs':repairs.get(lid,[]),'final_objects':ir['final_objects']})
print(json.dumps({'condition':'A3_integrated','links':12,'physical_links':11,'repaired_links':sorted(repairs)}))
