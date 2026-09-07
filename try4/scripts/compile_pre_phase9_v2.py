"""Compile generic v2 shape-family blueprints; never dispatches on robot or part ID."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';FRAME={'origin':[0,0,0],'x_axis':[1,0,0],'y_axis':[0,1,0],'z_axis':[0,0,1]}
def op(i,t,f,**kw):return {'op_id':f'op_{i:03d}','op_type':t,'target_body':kw.pop('target_body',f'op_{i:03d}'),'dependencies':kw.pop('dependencies',[]),'feature_ref':f,'reference_frame':FRAME,**kw}
def profile(points):return {'profile_type':'polyline','closed':True,'parameters':{'points':points}}
def extrude(i,f,pts,depth):return op(i,'extrude',f,profile=profile(pts),distance_mm=depth,operation_mode='new_body')
def cylinder(i,f,c,r,h):return op(i,'cylinder_primitive',f,center=c,axis=[0,0,1],radius_mm=r,height_mm=h,operation_mode='new_body')
def union(i,f,base,tools):return op(i,'boolean_union',f,target_body=base,dependencies=[base,*tools],tool_bodies=tools)
def cut(i,f,base,tool):return op(i,'boolean_cut',f,target_body=base,dependencies=[base,tool],tool_bodies=[tool])
def octagon(r,z):return [[r*.42,-r,z],[r,-r*.42,z],[r,r*.42,z],[r*.42,r,z],[-r*.42,r,z],[-r,r*.42,z],[-r,-r*.42,z],[-r*.42,-r,z],[r*.42,-r,z]]
def compile_recipe(recipe,p):
 if recipe=='polygonal_pedestal':
  L,W,D,E=p['plate_length'],p['plate_width'],p['plate_depth'],p['rear_extension'];pts=[[-L/2,-W/2,0],[L/2,-W/2,0],[L/2+E,-W*.32,0],[L/2+E,W*.32,0],[L/2,W/2,0],[-L/2,W/2,0],[-L/2,-W/2,0]];ops=[extrude(1,'F01',pts,D),op(2,'loft','F00',profiles=[profile(octagon(p['pedestal_radius'],D)),profile(octagon(p['pedestal_radius']*.68,D+p['pedestal_height']))],solid=True,operation_mode='new_body'),union(3,'F00','op_001',['op_002']),cylinder(4,'F02',[0,0,D+p['pedestal_height']+p['waist_height']/2],p['waist_radius'],p['waist_height']),union(5,'F02','op_003',['op_004']),cylinder(6,'F02',[0,0,D+p['pedestal_height']+p['waist_height']/2],p['recess_radius'],p['waist_height']*1.5),cut(7,'F02','op_005','op_006')];return ops,['op_007'],{'object_id':'op_004','property':'Radius','baseline_value':p['waist_radius'],'edit_fraction':.05}
 if recipe=='single_web_terminal_fork':
  L,H,FL,OH,IH=p['length'],p['web_half_height'],p['fork_length'],p['fork_outer_half_height'],p['fork_inner_half_height'];x0=-L/2;x1=L/2-FL;x2=L/2;pts=[[x0,-H,0],[x1,-H,0],[x1,-OH,0],[x2,-OH,0],[x2,-IH,0],[x1,-IH,0],[x1,IH,0],[x2,IH,0],[x2,OH,0],[x1,OH,0],[x1,H,0],[x0,H,0],[x0,-H,0]];tip_r=(OH-IH)/2;tip_y=(OH+IH)/2;ops=[extrude(1,'F00',pts,p['depth']),cylinder(2,'F02',[x0+p['proximal_length']/2,0,p['depth']/2],p['proximal_radius'],p['depth']),union(3,'F02','op_001',['op_002']),cylinder(4,'F02',[x0+p['proximal_length']/2,0,p['depth']/2],p['pivot_hole_radius'],p['depth']*1.4),cut(5,'F02','op_003','op_004'),cylinder(6,'F01',[x2,-tip_y,p['depth']/2],tip_r,p['depth']),union(7,'F01','op_005',['op_006']),cylinder(8,'F01',[x2,tip_y,p['depth']/2],tip_r,p['depth']),union(9,'F01','op_007',['op_008'])];return ops,['op_009'],{'object_id':'op_002','property':'Radius','baseline_value':p['proximal_radius'],'edit_fraction':.05}
 if recipe=='curved_wrist_fork':
  B,F,OH,IH=p['body_length'],p['fork_length'],p['outer_half_height'],p['inner_half_height'];x0=-B/2;x1=B/2;x2=x1+F;pts=[[x0,-OH,0],[x1,-OH,0],[x2,-OH*.55,0],[x2,-IH,0],[x1,-IH,0],[x1,IH,0],[x2,IH,0],[x2,OH*.55,0],[x1,OH,0],[x0,OH,0],[x0,-OH,0]];ops=[extrude(1,'F00',pts,p['depth']),cylinder(2,'F02',[x0,0,p['depth']/2],p['roll_radius'],p['roll_depth']),union(3,'F02','op_001',['op_002']),op(4,'oriented_box','F01',start=[x1+F*.35,-OH*.75,p['depth']/2],end=[x1+F*.65,-OH*.55,p['depth']/2],width_mm=p['slot_length'],depth_mm=p['slot_height'],operation_mode='new_body'),cut(5,'F01','op_003','op_004')];return ops,['op_005'],{'object_id':'op_002','property':'Radius','baseline_value':p['roll_radius'],'edit_fraction':.05}
 if recipe=='rail_carriage_linkage':
  B,W,D=p['carriage_length'],p['carriage_width'],p['depth'];ops=[op(1,'oriented_box','F01',start=[-B/2,0,D/2],end=[B/2,0,D/2],width_mm=W,depth_mm=D,operation_mode='new_body')];final=['op_001'];n=2
  for y in (-p['rail_span']/2,p['rail_span']/2):ops.append(op(n,'oriented_box','F01',start=[-B/2,y,D/2],end=[B/2+p['jaw_length']*.35,y,D/2],width_mm=p['rail_width'],depth_mm=p['rail_width'],operation_mode='new_body'));final.append(f'op_{n:03d}');n+=1
  for y,s in ((-p['jaw_gap']/2,-1),(p['jaw_gap']/2,1)):
   pts=[[-B/2,y-s*p['jaw_root_height']/2,0],[B/2+p['jaw_length'],y-s*p['jaw_tip_height']/2,0],[B/2+p['jaw_length'],y+s*p['jaw_tip_height']/2,0],[-B/2,y+s*p['jaw_root_height']/2,0],[-B/2,y-s*p['jaw_root_height']/2,0]];ops.append(extrude(n,'F00',pts,D*.65));final.append(f'op_{n:03d}');n+=1
   ops.append(op(n,'oriented_box','F02',start=[-B*.1,0,D*.75],end=[B*.35,y,D*.75],width_mm=p['link_width'],depth_mm=p['link_width'],operation_mode='new_body'));final.append(f'op_{n:03d}');n+=1
   ops.append(cylinder(n,'F02',[B*.35,y,D*.75],p['pivot_radius'],p['link_width']));final.append(f'op_{n:03d}');n+=1
  return ops,final,{'object_id':'op_001','property':'Length','baseline_value':W,'edit_fraction':.05}
 raise ValueError('unsupported v2 recipe '+recipe)
def main():
 src=json.loads((EXP/'codex_authored/PRE_PHASE9_V2/pilot_blueprints.json').read_text());
 for bp in src['parts']:
  pid=bp['part_id'];prior=json.loads((EXP/f'T1/{pid}/round_0/agent_output.json').read_text());ops,final,edit=compile_recipe(bp['recipe'],bp['parameters']);used={o['feature_ref'] for o in ops};assert used=={f['feature_id'] for f in prior['feature_graph']['features']};data={**prior,'condition':'PRE_PHASE9_V2_PILOT','v2_recipe':bp['recipe'],'cad_ir':{**prior['cad_ir'],'operations':ops,'final_objects':final,'editable_parameter':edit,'bodies':[{'body_id':f'B{i:02d}','role':'v2 final body','feature_ids':sorted(used),'final_object':x} for i,x in enumerate(final)],'assumptions':['v2 blueprint estimated from allowed renders and reviewer discrepancies; no GT geometry consumed']}};out=EXP/f'PRE_PHASE9_V2/{pid}/round_0';out.mkdir(parents=True,exist_ok=True);(out/'agent_output.json').write_text(json.dumps(data,indent=2)+'\n');(out/'feature_graph.json').write_text(json.dumps(data['feature_graph'],indent=2)+'\n');(out/'cad_ir.json').write_text(json.dumps(data['cad_ir'],indent=2)+'\n');(out/'blueprint.json').write_text(json.dumps(bp,indent=2)+'\n')
 print(len(src['parts']))
if __name__=='__main__':main()
