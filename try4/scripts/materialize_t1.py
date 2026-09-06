"""Compile current-agent skill decisions through reusable, ID-agnostic recipes."""
import copy,csv,hashlib,json,math
from datetime import datetime,timezone
from pathlib import Path
import jsonschema
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';SOURCE=EXP/'codex_authored/T1/t1_blueprints.json';OUT=EXP/'T1';RESULTS=EXP/'results'
FRAME={'origin':[0,0,0],'x_axis':[1,0,0],'y_axis':[0,1,0],'z_axis':[0,0,1]}
EMPTY={'start':None,'end':None,'width_mm':None,'depth_mm':None,'center':None,'axis':None,'radius_mm':None,'height_mm':None,'start_size_mm':None,'end_size_mm':None,'tool_bodies':[],'edge_selectors':[],'distance_mm':None,'operation_mode':None}
SKILLS=['skills/visual_grounding/SKILL.md','skills/semantic_mechanical_reasoning/SKILL.md','skills/robot_part_modeling_standard/SKILL.md','skills/mechanical_detail_planning/SKILL.md','skills/freecad_part_modeling/SKILL.md']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def op(i,t,f,**kw):return {'op_id':f'op_{i:03d}','op_type':t,'target_body':kw.pop('target_body',f'op_{i:03d}'),'dependencies':kw.pop('dependencies',[]),'feature_ref':f,**kw}

def compile_recipe(recipe,p,f):
    """Dispatch only on shared recipe name; never inspect a case or part ID."""
    t=recipe['type'];o=[];b=[]
    if t=='base_pedestal':
        o=[op(1,'oriented_box',f['base'],start=[-p['plate_length']/2,0,0],end=[p['plate_length']/2,0,0],width_mm=p['plate_width'],depth_mm=p['plate_thickness'],operation_mode='new_body'),
           op(2,'lofted_prism',f['pedestal'],start=[0,0,0],end=[0,0,p['pedestal_height']],start_size_mm=p['pedestal_base_size'],end_size_mm=p['pedestal_top_size'],operation_mode='new_body'),
           op(3,'boolean_union',f['pedestal'],target_body='op_001',dependencies=['op_001','op_002'],tool_bodies=['op_002']),
           op(4,'cylinder_primitive',f['top'],center=[0,0,p['pedestal_height']],axis=[0,0,1],radius_mm=p['top_radius'],height_mm=p['top_height'],operation_mode='new_body'),
           op(5,'boolean_union',f['top'],target_body='op_003',dependencies=['op_003','op_004'],tool_bodies=['op_004']),
           op(6,'cylinder_primitive',f['top'],center=[0,0,p['pedestal_height']+p['top_height']/2],axis=[0,0,1],radius_mm=p['recess_radius'],height_mm=p['top_height']*1.5,operation_mode='new_body'),
           op(7,'boolean_cut',f['top'],target_body='op_005',dependencies=['op_005','op_006'],tool_bodies=['op_006'])]
        b=[{'body_id':'B00','role':'mounting pedestal','feature_ids':list(f.values()),'final_object':'op_007'}];final=['op_007'];edit={'object_id':'op_001','property':'Length','baseline_value':p['plate_width'],'edit_fraction':.05}
    elif t=='joint_housing':
        o=[op(1,'oriented_box',f['body'],start=[0,0,0],end=[0,0,p['body_height']],width_mm=p['body_width'],depth_mm=p['body_depth'],operation_mode='new_body'),
           op(2,'oriented_box',f['body'],start=[-p['support_span']/2,0,0],end=[p['support_span']/2,0,0],width_mm=p['support_width'],depth_mm=p['support_depth'],operation_mode='new_body'),
           op(3,'boolean_union',f['body'],target_body='op_001',dependencies=['op_001','op_002'],tool_bodies=['op_002']),
           op(4,'cylinder_primitive',f['pivot'],center=[0,0,p['pivot_z']],axis=[0,1,0],radius_mm=p['pivot_radius'],height_mm=p['pivot_height'],operation_mode='new_body'),
           op(5,'boolean_union',f['pivot'],target_body='op_003',dependencies=['op_003','op_004'],tool_bodies=['op_004'])]
        final_id='op_005'
        if 'inset' in f:
            o += [op(6,'oriented_box',f['inset'],start=[0,0,p['body_height']-p['inset_depth']],end=[0,0,p['body_height']+1],width_mm=p['inset_size'][0],depth_mm=p['inset_size'][1],operation_mode='new_body'),op(7,'boolean_cut',f['inset'],target_body='op_005',dependencies=['op_005','op_006'],tool_bodies=['op_006'])];final_id='op_007'
        b=[{'body_id':'B00','role':'joint housing','feature_ids':list(f.values()),'final_object':final_id}];final=[final_id];edit={'object_id':'op_001','property':'Length','baseline_value':p['body_width'],'edit_fraction':.05}
    elif t=='open_frame':
        y=p['separation']/2;o=[op(1,'oriented_box',f['frame'],start=[0,-y,0],end=[0,-y,p['length']],width_mm=p['plate_thickness'],depth_mm=p['plate_width'],operation_mode='new_body'),op(2,'oriented_box',f['frame'],start=[0,y,0],end=[0,y,p['length']],width_mm=p['plate_thickness'],depth_mm=p['plate_width'],operation_mode='new_body'),op(3,'oriented_box',f['frame'],start=[0,-y-p['plate_thickness'],p['length']],end=[0,y+p['plate_thickness'],p['length']],width_mm=p['carrier_width'],depth_mm=p['carrier_thickness'],operation_mode='new_body'),op(4,'cylinder_primitive',f['pivot'],center=[0,0,p['length']],axis=[0,1,0],radius_mm=p['pivot_radius'],height_mm=p['pivot_height'],operation_mode='new_body'),op(5,'boolean_union',f['pivot'],target_body='op_003',dependencies=['op_003','op_004'],tool_bodies=['op_004'])]
        left,right='op_001','op_002';n=6
        if 'slots' in f:
            for side,base in [(-y,left),(y,right)]:
                cut=f'op_{n:03d}';o.append(op(n,'oriented_box',f['slots'],start=[0,side-p['plate_thickness'],p['slot_z']],end=[0,side+p['plate_thickness'],p['slot_z']],width_mm=p['slot_length'],depth_mm=p['slot_width'],operation_mode='new_body'));n+=1
                result=f'op_{n:03d}';o.append(op(n,'boolean_cut',f['slots'],target_body=base,dependencies=[base,cut],tool_bodies=[cut]));n+=1
                if side<0:left=result
                else:right=result
        if 'fork' in f:
            new=[]
            for side,base in [(-y,left),(y,right)]:
                cut=f'op_{n:03d}';o.append(op(n,'cylinder_primitive',f['fork'],center=[0,side,0],axis=[0,1,0],radius_mm=p['notch_radius'],height_mm=p['plate_thickness']*2,operation_mode='new_body'));n+=1
                result=f'op_{n:03d}';o.append(op(n,'boolean_cut',f['fork'],target_body=base,dependencies=[base,cut],tool_bodies=[cut]));n+=1;new.append(result)
            left,right=new
        b=[{'body_id':'B00','role':'left side plate','feature_ids':[f['frame']]+([f['slots']] if 'slots'in f else [])+([f['fork']] if 'fork'in f else []),'final_object':left},{'body_id':'B01','role':'right side plate','feature_ids':[f['frame']]+([f['slots']] if 'slots'in f else [])+([f['fork']] if 'fork'in f else []),'final_object':right},{'body_id':'B02','role':'cross carrier','feature_ids':[f['frame'],f['pivot']],'final_object':'op_005'}];final=[left,right,'op_005'];edit={'object_id':'op_001','property':'Width','baseline_value':p['plate_width'],'edit_fraction':.05}
    elif t=='dual_support':
        x=p['separation']/2;o=[op(1,'cylinder_primitive',f['base'],center=[0,0,0],axis=[0,0,1],radius_mm=p['disk_radius'],height_mm=p['disk_thickness'],operation_mode='new_body')];final=['op_001'];b=[{'body_id':'B00','role':'mounting disk','feature_ids':[f['base']],'final_object':'op_001'}];n=2
        for side in [-x,x]:
            box=f'op_{n:03d}';o.append(op(n,'oriented_box',f['body'],start=[side,0,p['disk_thickness']],end=[side,0,p['disk_thickness']+p['upright_height']],width_mm=p['upright_width'],depth_mm=p['upright_depth'],operation_mode='new_body'));n+=1
            cyl=f'op_{n:03d}';o.append(op(n,'cylinder_primitive',f['pivot'],center=[side,0,p['disk_thickness']+p['upright_height']],axis=[0,1,0],radius_mm=p['pivot_radius'],height_mm=p['upright_depth']*1.15,operation_mode='new_body'));n+=1
            fuse=f'op_{n:03d}';o.append(op(n,'boolean_union',f['pivot'],target_body=box,dependencies=[box,cyl],tool_bodies=[cyl]));n+=1;final.append(fuse);b.append({'body_id':f'B{len(b):02d}','role':'upright pivot support','feature_ids':[f['body'],f['pivot']],'final_object':fuse})
        edit={'object_id':'op_001','property':'Radius','baseline_value':p['disk_radius'],'edit_fraction':.05}
    elif t=='offset_housing':
        o=[op(1,'lofted_prism',f['body'],start=[0,0,0],end=[p['length'],p['offset'],0],start_size_mm=p['start_size'],end_size_mm=p['end_size'],operation_mode='new_body'),op(2,'cylinder_primitive',f['joint'],center=[0,0,0],axis=[0,1,0],radius_mm=p['joint_radius'],height_mm=p['joint_height'],operation_mode='new_body'),op(3,'boolean_union',f['joint'],target_body='op_001',dependencies=['op_001','op_002'],tool_bodies=['op_002'])];current='op_003';n=4
        if 'channel' in f:
            cut=f'op_{n:03d}';o.append(op(n,'oriented_box',f['channel'],start=[p['length']*.35,-p['channel_depth'],0],end=[p['length']*.7,p['channel_depth'],0],width_mm=p['channel_width'],depth_mm=p['channel_height'],operation_mode='new_body'));n+=1;current=f'op_{n:03d}';o.append(op(n,'boolean_cut',f['channel'],target_body='op_003',dependencies=['op_003',cut],tool_bodies=[cut]));n+=1
        if 'holes' in f:
            for fraction in [.45,.62]:
                cut=f'op_{n:03d}';o.append(op(n,'cylinder_primitive',f['holes'],center=[p['length']*fraction,p['offset']*fraction,0],axis=[0,0,1],radius_mm=p['hole_radius'],height_mm=max(p['start_size'][1],p['end_size'][1])*1.5,operation_mode='new_body'));n+=1;prev=current;current=f'op_{n:03d}';o.append(op(n,'boolean_cut',f['holes'],target_body=prev,dependencies=[prev,cut],tool_bodies=[cut]));n+=1
        b=[{'body_id':'B00','role':'offset link housing','feature_ids':list(f.values()),'final_object':current}];final=[current];edit={'object_id':'op_002','property':'Radius','baseline_value':p['joint_radius'],'edit_fraction':.05}
    elif t=='wrist_carrier':
        y=p['separation']/2;o=[op(1,'oriented_box',f['body'],start=[-p['body_length']/2,0,0],end=[p['body_length']/2,0,0],width_mm=p['body_width'],depth_mm=p['body_depth'],operation_mode='new_body'),op(2,'cylinder_primitive',f['roll'],center=[-p['body_length']/2,0,0],axis=[0,1,0],radius_mm=p['roll_radius'],height_mm=p['roll_height'],operation_mode='new_body'),op(3,'boolean_union',f['roll'],target_body='op_001',dependencies=['op_001','op_002'],tool_bodies=['op_002']),op(4,'lofted_prism',f['fork'],start=[0,-y,0],end=[p['arm_length'],-y,0],start_size_mm=p['arm_start_size'],end_size_mm=p['arm_end_size'],operation_mode='new_body'),op(5,'lofted_prism',f['fork'],start=[0,y,0],end=[p['arm_length'],y,0],start_size_mm=p['arm_start_size'],end_size_mm=p['arm_end_size'],operation_mode='new_body')];left,right='op_004','op_005';n=6
        if 'slot' in f:
            new=[]
            for side,base in [(-y,left),(y,right)]:
                cut=f'op_{n:03d}';o.append(op(n,'oriented_box',f['slot'],start=[p['arm_length']*.35,side-p['body_depth'],0],end=[p['arm_length']*.6,side+p['body_depth'],0],width_mm=p['slot_length'],depth_mm=p['slot_width'],operation_mode='new_body'));n+=1;res=f'op_{n:03d}';o.append(op(n,'boolean_cut',f['slot'],target_body=base,dependencies=[base,cut],tool_bodies=[cut]));n+=1;new.append(res)
            left,right=new
        b=[{'body_id':'B00','role':'central roll carrier','feature_ids':[f['body'],f['roll']],'final_object':'op_003'},{'body_id':'B01','role':'left fork arm','feature_ids':[f['fork']]+([f['slot']] if 'slot'in f else []),'final_object':left},{'body_id':'B02','role':'right fork arm','feature_ids':[f['fork']]+([f['slot']] if 'slot'in f else []),'final_object':right}];final=['op_003',left,right];edit={'object_id':'op_002','property':'Radius','baseline_value':p['roll_radius'],'edit_fraction':.05}
    elif t=='gripper':
        y=p['jaw_separation']/2;o=[op(1,'oriented_box',f['carriage'],start=[-p['carriage_length']/2,0,0],end=[p['carriage_length']/2,0,0],width_mm=p['carriage_width'],depth_mm=p['carriage_depth'],operation_mode='new_body'),op(2,'oriented_box',f['carriage'],start=[0,-p['rail_span']/2,0],end=[0,p['rail_span']/2,0],width_mm=p['rail_width'],depth_mm=p['rail_depth'],operation_mode='new_body'),op(3,'boolean_union',f['carriage'],target_body='op_001',dependencies=['op_001','op_002'],tool_bodies=['op_002']),op(4,'lofted_prism',f['jaws'],start=[0,-y,0],end=[p['jaw_length'],-y,0],start_size_mm=p['jaw_start_size'],end_size_mm=p['jaw_end_size'],operation_mode='new_body'),op(5,'lofted_prism',f['jaws'],start=[0,y,0],end=[p['jaw_length'],y,0],start_size_mm=p['jaw_start_size'],end_size_mm=p['jaw_end_size'],operation_mode='new_body'),op(6,'oriented_box',f['attachment'],start=[-p['attachment_length'],0,0],end=[-p['carriage_length']/2,0,0],width_mm=p['attachment_width'],depth_mm=p['attachment_depth'],operation_mode='new_body'),op(7,'oriented_box',f['attachment'],start=[-p['attachment_length'], -p['attachment_separation']/2,0],end=[-p['carriage_length']/2,-p['attachment_separation']/2,0],width_mm=p['plate_thickness'],depth_mm=p['plate_depth'],operation_mode='new_body'),op(8,'oriented_box',f['attachment'],start=[-p['attachment_length'], p['attachment_separation']/2,0],end=[-p['carriage_length']/2,p['attachment_separation']/2,0],width_mm=p['plate_thickness'],depth_mm=p['plate_depth'],operation_mode='new_body'),op(9,'boolean_union',f['attachment'],target_body='op_006',dependencies=['op_006','op_007','op_008'],tool_bodies=['op_007','op_008'])];bracket='op_009'
        if p.get('attachment_slot'):
            o += [op(10,'oriented_box',f['attachment'],start=[-p['attachment_length']*.72,-p['attachment_depth'],0],end=[-p['attachment_length']*.45,p['attachment_depth'],0],width_mm=p['slot_length'],depth_mm=p['slot_width'],operation_mode='new_body'),op(11,'boolean_cut',f['attachment'],target_body='op_009',dependencies=['op_009','op_010'],tool_bodies=['op_010'])];bracket='op_011'
        b=[{'body_id':'B00','role':'cross carriage','feature_ids':[f['carriage']],'final_object':'op_003'},{'body_id':'B01','role':'left jaw','feature_ids':[f['jaws']],'final_object':'op_004'},{'body_id':'B02','role':'right jaw','feature_ids':[f['jaws']],'final_object':'op_005'},{'body_id':'B03','role':'proximal attachment bracket','feature_ids':[f['attachment']],'final_object':bracket}];final=['op_003','op_004','op_005',bracket];edit={'object_id':'op_001','property':'Length','baseline_value':p['carriage_width'],'edit_fraction':.05}
    else:raise ValueError('unsupported shared recipe: '+t)
    return o,b,final,edit

def main():
    source=json.loads(SOURCE.read_text());t0=json.loads((EXP/'schemas/t0_direct_output.schema.json').read_text());outer=json.loads((EXP/'schemas/t1_skill_output.schema.json').read_text());rows=[]
    inner_defs=copy.deepcopy(t0['$defs']);inner_defs['feature']['properties']['requirement_refs']['items']['pattern']='^R0[12]_P[0-9]{2}_E[0-9]{2}$'
    parts=source['parts'];assert len(parts)==12 and len({p['part_id'] for p in parts})==12
    method_files=[EXP/'AMENDMENT_T1_INTERACTIVE.md',SOURCE,Path(__file__),EXP/'schemas/t1_skill_output.schema.json',EXP/'schemas/t0_direct_output.schema.json',EXP/'scripts/validate_t1.py',EXP/'scripts/freecad_t0_executor.py',EXP/'scripts/freecad_t1_executor.py',EXP/'scripts/run_t1_freecad.py']+[EXP/p for p in SKILLS]
    dump(RESULTS/'t1_method_snapshot.json',{'created_at':datetime.now(timezone.utc).isoformat(),'condition':'T1_INTERACTIVE','context_isolation':False,'recipe_dispatch_input':'agent-authored recipe and dimensions only; compiler has no part/case dispatch','files':{str(p.relative_to(EXP)):sha(p) for p in method_files}})
    for plan in parts:
        pid=plan['part_id'];packet_path=EXP/'packets'/pid/'part_input.json';packet=json.loads(packet_path.read_text());requirements={r['feature_id']:r for r in packet['expected_features']}
        assert set(requirements)=={x['requirement_ref'] for x in plan['features']}
        features=[];observations=[];fmap={}
        for i,d in enumerate(plan['features']):
            req=requirements[d['requirement_ref']];fid=f'F{i:02d}';fmap[d['key']]=fid
            observations.append({'requirement_ref':req['feature_id'],'region':req['region'],'shape':d['observed_shape'],'views':req['evidence_views'],'confidence':d['confidence'],'uncertainty':d['uncertainty']})
            features.append({'feature_id':fid,'requirement_refs':[req['feature_id']],'feature_type':req['requirement'],'role':d['role'],'evidence':req['evidence_views'],'reference_region':req['region'],'estimated_dimensions_mm':d['dimensions'],'shape_family':d['shape_family'],'intended_cad_strategy':d['strategy'],'dependencies':[],'critical':req['critical'],'confidence':d['confidence'],'status':d['status']})
        operations,bodies,finals,edit=compile_recipe(plan['recipe'],plan['parameters'],fmap)
        normalized=[{**EMPTY,**value,'reference_frame':FRAME} for value in operations]
        cad={'ir_version':'try4_executable_cad_ir_v1','units':'mm','bodies':bodies,'operations':normalized,'final_objects':finals,'editable_parameter':edit,'assumptions':plan['assumptions'],'silent_fallback_allowed':False}
        visual={'target_color_consumed':True,'observed_regions':observations};mechanical={**plan['mechanical'],'semantic_label_consumed':packet['semantic_label']}
        data={'schema_version':'try4_t1_skill_output_v1','part_id':pid,'visual_evidence':visual,'mechanical_interpretation':mechanical,'feature_graph':{'features':features},'cad_ir':cad,'skill_trace':SKILLS}
        jsonschema.validate(data,outer)
        for name,values in [('feature',features),('body',bodies),('operation',normalized)]:
            validator={'$schema':t0['$schema'],'$ref':f'#/$defs/{name}','$defs':inner_defs}
            for value in values:jsonschema.validate(value,validator)
        jsonschema.validate(edit,{'$schema':t0['$schema'],'$ref':'#/$defs/editable_parameter','$defs':inner_defs})
        out=OUT/pid/'round_0';out.mkdir(parents=True,exist_ok=True)
        if (out/'agent_output.json').exists():raise RuntimeError(pid+': output exists')
        dump(out/'agent_output.json',data);dump(out/'visual_evidence.json',visual);dump(out/'mechanical_interpretation.json',mechanical);dump(out/'feature_graph.json',data['feature_graph']);dump(out/'cad_ir.json',cad)
        manifest={'part_id':pid,'status':'SUCCESS','producer':'current_interactive_codex','condition':'T1_INTERACTIVE','context_isolation':False,'packet_sha256':sha(packet_path),'blueprint_sha256':sha(SOURCE),'output_sha256':sha(out/'agent_output.json'),'skills':{p:sha(EXP/p) for p in SKILLS},'model_snapshot':'UNAVAILABLE','tokens':'UNAVAILABLE','repair_round':0,'created_at':datetime.now(timezone.utc).isoformat()};dump(out/'agent_manifest.json',manifest);rows.append(manifest)
    with (RESULTS/'t1_agent_calls.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps({'parts':12,'outputs':12,'skills':5,'condition':'T1_INTERACTIVE'}))
if __name__=='__main__':main()
