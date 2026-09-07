"""Materialize frozen A0 references and one-shot A1/A2 plans without part dispatch."""
import hashlib,json,sys
from pathlib import Path
import jsonschema
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try4_1A';TRY4=ROOT/'try4';sys.path.insert(0,str(TRY4/'scripts'));from compile_pre_phase9_v2 import compile_recipe,op,profile,extrude,cylinder,union,cut
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stepped(p):
 L,W,D,O=p['length'],p['width'],p['depth'],p['offset'];pts=[[-L/2,-W/2,0],[L*.15,-W/2,0],[L/2,-W*.32+O,0],[L/2,W*.32+O,0],[L*.15,W/2,0],[-L/2,W/2,0],[-L/2,-W/2,0]];ops=[extrude(1,'F00',pts,D),op(2,'oriented_box','F00',start=[-p['step_length']/2,0,D+p['step_height']/2],end=[p['step_length']/2,0,D+p['step_height']/2],width_mm=p['step_width'],depth_mm=p['step_height'],operation_mode='new_body'),union(3,'F00','op_001',['op_002']),cylinder(4,'F03',[-L/2,0,D/2],p['joint_radius'],p['joint_depth']),union(5,'F03','op_003',['op_004']),op(6,'oriented_box','F01',start=[-p['channel_length']/2,-p['channel_width']/2,D*.75],end=[p['channel_length']/2,-p['channel_width']/2,D*.75],width_mm=p['channel_width'],depth_mm=D,operation_mode='new_body'),cut(7,'F01','op_005','op_006')];current='op_007';n=8
 for k in range(p['hole_count']):
  x=-p['hole_spacing']*(p['hole_count']-1)/2+k*p['hole_spacing'];ops.append(cylinder(n,'F02',[x,W*.28,D+p['step_height']/2],p['hole_radius'],D*2));tool=f'op_{n:03d}';n+=1;ops.append(cut(n,'F02',current,tool));current=f'op_{n:03d}';n+=1
 return ops,[current],{'object_id':'op_004','property':'Radius','baseline_value':p['joint_radius'],'edit_fraction':.05}
def main():
 data=json.loads((HERE/'planning_inputs.json').read_text());schema=json.loads((HERE/'schemas/mechanical_topology_graph.schema.json').read_text());manifest=[]
 for part in data['parts']:
  pid=part['part_id'];packet=TRY4/f'packets/{pid}/part_input.json';prior_path=TRY4/f'T1/{pid}/round_0/agent_output.json';prior=json.loads(prior_path.read_text());dump(HERE/f'topology_graphs/TARGET/{pid}.json',part['target_graph']);dump(HERE/f'topology_graphs/A0/{pid}.json',part['A0_graph'])
  manifest.append({'part_id':pid,'packet_sha256':sha(packet),'a0_agent_output_sha256':sha(prior_path),'reference_images':prior.get('visual_evidence',{}),'a0_path':str(prior_path.relative_to(ROOT))})
  for cond in ('A1','A2'):
   graph=part[f'{cond}_graph'];jsonschema.validate(graph,schema);dump(HERE/f'topology_graphs/{cond}/{pid}.json',graph)
   if cond=='A1':ops,final,edit=part['A1_operations'],part['A1_final'],part['A1_edit'];families=[]
   else:
    plan=part['A2_plan'];families=plan['families'];ops,final,edit=stepped(plan['parameters']) if plan['recipe']=='stepped_housing' else compile_recipe(plan['recipe'],plan['parameters']);dump(HERE/f'shape_family_plans/{pid}.json',{'part_id':pid,'condition':'A2','selected_families':families,'selection_evidence':'current-agent visual/topology reasoning before generation','recipe':plan['recipe'],'parameters':plan['parameters']})
   used={x['feature_ref'] for x in ops};expected={f['feature_id'] for f in prior['feature_graph']['features']};assert used==expected,(pid,cond,used,expected)
   out=HERE/cond/pid/'round_0';ir={**prior['cad_ir'],'operations':ops,'final_objects':final,'editable_parameter':edit,'bodies':[{'body_id':f'B{i:02d}','role':f'{cond} final body','feature_ids':sorted(used),'final_object':x} for i,x in enumerate(final)],'assumptions':[f'{cond} one-shot plan; no repair or post-generation correction']};agent={**prior,'condition':cond,'mechanical_topology_graph':graph,'selected_shape_families':families,'cad_ir':ir};dump(out/'agent_output.json',agent);dump(out/'feature_graph.json',agent['feature_graph']);dump(out/'cad_ir.json',ir);dump(out/'mechanical_topology_graph.json',graph)
 dump(HERE/'input_manifest.json',manifest);print(json.dumps({'parts':len(data['parts']),'new_candidates':len(data['parts'])*2}))
if __name__=='__main__':main()
