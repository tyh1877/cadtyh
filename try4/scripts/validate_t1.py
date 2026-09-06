"""Phase-4 T1 semantic/feature/IR Plan Gate; no geometry evaluation."""
import copy,csv,json,math
from pathlib import Path
import jsonschema
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';OUT=EXP/'T1';RESULTS=EXP/'results'
SKILLS=['skills/visual_grounding/SKILL.md','skills/semantic_mechanical_reasoning/SKILL.md','skills/robot_part_modeling_standard/SKILL.md','skills/mechanical_detail_planning/SKILL.md','skills/freecad_part_modeling/SKILL.md']
def positive(x):return isinstance(x,(int,float)) and math.isfinite(x) and x>0
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def main():
    outer=json.loads((EXP/'schemas/t1_skill_output.schema.json').read_text());t0=json.loads((EXP/'schemas/t0_direct_output.schema.json').read_text());rows=[];inner_defs=copy.deepcopy(t0['$defs']);inner_defs['feature']['properties']['requirement_refs']['items']['pattern']='^R0[12]_P[0-9]{2}_E[0-9]{2}$'
    pids=[f'R01_P{i:02d}' for i in range(5)]+[f'R02_P{i:02d}' for i in range(7)]
    for pid in pids:
        out=OUT/pid/'round_0';errors=[]
        try:data=json.loads((out/'agent_output.json').read_text());jsonschema.validate(data,outer)
        except Exception as e:rows.append({'part_id':pid,'status':'PLAN_INCOMPLETE','errors':f'{type(e).__name__}: {e}'});continue
        packet=json.loads((EXP/'packets'/pid/'part_input.json').read_text());requirements={r['feature_id']:r for r in packet['expected_features']};features=data['feature_graph']['features'];cad=data['cad_ir'];ops=cad['operations']
        if data['part_id']!=pid:errors.append('part ID mismatch')
        if data['mechanical_interpretation']['semantic_label_consumed']!=packet['semantic_label']:errors.append('semantic label not consumed exactly')
        if data['skill_trace']!=SKILLS:errors.append('skill trace mismatch')
        observed=[r['requirement_ref'] for r in data['visual_evidence']['observed_regions']];covered=[x for f in features for x in f['requirement_refs']]
        if sorted(observed)!=sorted(requirements):errors.append('visual evidence coverage mismatch')
        if sorted(covered)!=sorted(requirements):errors.append('feature requirement coverage mismatch')
        fids=[f['feature_id'] for f in features]
        if len(fids)!=len(set(fids)):errors.append('duplicate features')
        critical_unimplemented=sum(f['status']=='UNIMPLEMENTED' and any(requirements[r]['critical'] for r in f['requirement_refs']) for f in features)
        if critical_unimplemented:errors.append('critical feature unimplemented')
        for f in features:
            jsonschema.validate(f,{'$schema':t0['$schema'],'$ref':'#/$defs/feature','$defs':inner_defs})
            if f['status']=='PLANNED' and not any(o['feature_ref']==f['feature_id'] for o in ops):errors.append(f['feature_id']+': no operation')
            if not all((EXP/'packets'/pid/e).is_file() for e in f['evidence']):errors.append(f['feature_id']+': missing evidence')
        opids=[];objects=set();required={'oriented_box':['start','end','width_mm','depth_mm'],'cylinder_primitive':['center','axis','radius_mm','height_mm'],'lofted_prism':['start','end','start_size_mm','end_size_mm'],'boolean_union':['tool_bodies'],'boolean_cut':['tool_bodies'],'fillet':['edge_selectors','radius_mm'],'chamfer':['edge_selectors','distance_mm']}
        for o in ops:
            jsonschema.validate(o,{'$schema':t0['$schema'],'$ref':'#/$defs/operation','$defs':inner_defs})
            if o['op_id'] in opids:errors.append('duplicate op')
            if set(o['dependencies'])-set(opids):errors.append(o['op_id']+': forward dependency')
            if any(o.get(k) is None or o.get(k)==[] for k in required[o['op_type']]):errors.append(o['op_id']+': applicable parameter missing')
            if o['op_type'] in ['oriented_box','cylinder_primitive','lofted_prism']:
                if o['target_body']!=o['op_id']:errors.append(o['op_id']+': primitive target mismatch')
            elif o['target_body'] not in objects:errors.append(o['op_id']+': unknown base')
            if set(o.get('tool_bodies',[]))-objects:errors.append(o['op_id']+': unknown tool')
            values=[o[k] for k in ['width_mm','depth_mm','radius_mm','height_mm','distance_mm'] if o.get(k) is not None]+list(o.get('start_size_mm')or[])+list(o.get('end_size_mm')or[])
            if not all(positive(v) for v in values):errors.append(o['op_id']+': nonpositive dimension')
            objects.add(o['op_id']);opids.append(o['op_id'])
        finals=cad['final_objects'];bfinals=[b['final_object'] for b in cad['bodies']]
        for b in cad['bodies']:jsonschema.validate(b,{'$schema':t0['$schema'],'$ref':'#/$defs/body','$defs':inner_defs})
        if set(finals)!=set(bfinals) or set(finals)-set(opids):errors.append('body/final mismatch')
        edit=cad['editable_parameter'];jsonschema.validate(edit,{'$schema':t0['$schema'],'$ref':'#/$defs/editable_parameter','$defs':inner_defs})
        source=next((o for o in ops if o['op_id']==edit['object_id']),None);expected=None
        if source and source['op_type']=='oriented_box':expected={'Length':source['width_mm'],'Width':source['depth_mm'],'Height':math.dist(source['start'],source['end'])}.get(edit['property'])
        if source and source['op_type']=='cylinder_primitive':expected={'Radius':source['radius_mm'],'Height':source['height_mm']}.get(edit['property'])
        if expected is None or not math.isclose(expected,edit['baseline_value'],rel_tol=1e-6):errors.append('editable parameter mismatch')
        result={'part_id':pid,'status':'PASS' if not errors else 'PLAN_INCOMPLETE','features':len(features),'critical_features':sum(f['critical'] for f in features),'unimplemented_features':sum(f['status']=='UNIMPLEMENTED' for f in features),'critical_unimplemented':critical_unimplemented,'bodies':len(cad['bodies']),'operations':len(ops),'errors':errors};dump(out/'plan_gate.json',result);rows.append(result)
    with (RESULTS/'t1_plan_gate.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows({**r,'errors':json.dumps(r['errors'])} for r in rows)
    print(json.dumps({'parts':12,'passes':sum(r['status']=='PASS' for r in rows),'incomplete':sum(r['status']!='PASS' for r in rows)},indent=2))
    return 0 if all(r['status']=='PASS' for r in rows) else 1
if __name__=='__main__':raise SystemExit(main())
