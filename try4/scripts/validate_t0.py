"""T0 CAD-IR preflight plus post-execution coverage checks."""
import csv,json,math
from pathlib import Path
import jsonschema
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';RESULTS=EXP/'results';OUT=EXP/'T0'

def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def positive(x):return isinstance(x,(int,float)) and math.isfinite(x) and x>0

def check(pid):
    out=OUT/pid/'round_0';errors=[]
    try:data=json.loads((out/'agent_output.json').read_text());jsonschema.validate(data,json.loads((EXP/'schemas/t0_direct_output.schema.json').read_text()))
    except Exception as e:return {'part_id':pid,'status':'PLAN_INCOMPLETE','errors':[f'{type(e).__name__}: {e}']}
    if data['part_id']!=pid:errors.append('part_id mismatch')
    packet=json.loads((EXP/'packets'/pid/'part_input.json').read_text());requirements={r['feature_id']:r for r in packet['expected_features']}
    features=data['feature_graph']['features'];fids=[f['feature_id'] for f in features];ops=data['cad_ir']['operations'];opids=[];objects=set()
    if len(fids)!=len(set(fids)):errors.append('duplicate feature IDs')
    refs=[r for f in features for r in f['requirement_refs']]
    if set(refs)-set(requirements):errors.append('unknown requirement refs')
    if set(requirements)-set(refs):errors.append('requirements not explicitly covered')
    for f in features:
        if set(f['dependencies'])-set(fids):errors.append(f"{f['feature_id']}: unknown feature dependency")
        if not all((EXP/'packets'/pid/e).is_file() for e in f['evidence']):errors.append(f"{f['feature_id']}: missing evidence")
        if f['status']=='PLANNED' and not any(o['feature_ref']==f['feature_id'] for o in ops):errors.append(f"{f['feature_id']}: planned without operation")
    required={'oriented_box':['start','end','width_mm','depth_mm'],'cylinder_primitive':['center','axis','radius_mm','height_mm'],'lofted_prism':['start','end','start_size_mm','end_size_mm'],'boolean_union':['tool_bodies'],'boolean_cut':['tool_bodies'],'fillet':['edge_selectors','radius_mm'],'chamfer':['edge_selectors','distance_mm']}
    for op in ops:
        if op['op_id'] in opids:errors.append('duplicate op ID')
        if set(op['dependencies'])-set(opids):errors.append(f"{op['op_id']}: forward/missing dependency")
        for key in required[op['op_type']]:
            if key not in op:errors.append(f"{op['op_id']}: missing {key}")
        if op['op_type'] in ['oriented_box','cylinder_primitive','lofted_prism']:
            if op['target_body']!=op['op_id']:errors.append(f"{op['op_id']}: primitive target mismatch")
            objects.add(op['op_id'])
        else:
            if op['target_body'] not in objects:errors.append(f"{op['op_id']}: unknown base")
            tools=op.get('tool_bodies',[])
            if set(tools)-objects:errors.append(f"{op['op_id']}: unknown tools")
            objects.add(op['op_id'])
        values=[]
        for k in ['width_mm','depth_mm','radius_mm','height_mm','distance_mm']:
            if op.get(k) is not None:values.append(op[k])
        values += list(op.get('start_size_mm') or [])+list(op.get('end_size_mm') or [])
        if not all(positive(v) for v in values):errors.append(f"{op['op_id']}: nonpositive dimension")
        if op['op_type']=='oriented_box' and op['start']==op['end']:errors.append(f"{op['op_id']}: zero length")
        if op['op_type']=='lofted_prism' and op['start']==op['end']:errors.append(f"{op['op_id']}: zero length")
        if op['op_type']=='cylinder_primitive' and not any(op['axis']):errors.append(f"{op['op_id']}: zero axis")
        opids.append(op['op_id'])
    finals=data['cad_ir']['final_objects'];bfinals=[b['final_object'] for b in data['cad_ir']['bodies']]
    if set(finals)!=set(bfinals) or set(finals)-set(opids):errors.append('final object/body mismatch')
    edit=data['cad_ir']['editable_parameter']
    if edit['object_id'] not in opids:errors.append('editable object missing')
    else:
        source=next(o for o in ops if o['op_id']==edit['object_id'])
        expected=None
        if source['op_type']=='oriented_box':
            expected={'Length':source['width_mm'],'Width':source['depth_mm'],'Height':math.dist(source['start'],source['end'])}.get(edit['property'])
        elif source['op_type']=='cylinder_primitive':
            expected={'Radius':source['radius_mm'],'Height':source['height_mm']}.get(edit['property'])
        if expected is None:errors.append('editable parameter must target a primitive property')
        elif not math.isclose(edit['baseline_value'],expected,rel_tol=1e-6,abs_tol=1e-6):errors.append('editable baseline does not match IR')
    if data['cad_ir']['silent_fallback_allowed'] is not False:errors.append('fallback enabled')
    gate={'part_id':pid,'status':'PASS' if not errors else 'PLAN_INCOMPLETE','schema_valid':not errors,'feature_count':len(features),'planned_features':sum(f['status']=='PLANNED' for f in features),'unimplemented_features':sum(f['status']=='UNIMPLEMENTED' for f in features),'critical_unimplemented':sum(f['status']=='UNIMPLEMENTED' and any(requirements[r]['critical'] for r in f['requirement_refs']) for f in features),'body_count':len(data['cad_ir']['bodies']),'operation_count':len(ops),'errors':errors}
    dump(out/'plan_gate.json',gate);return gate

def main():
    rows=[check(f'R01_P{i:02d}') for i in range(5)]
    with (RESULTS/'t0_plan_gate.csv').open('w',newline='',encoding='utf-8') as f:
        keys=sorted({k for r in rows for k in r});w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows({**r,'errors':json.dumps(r['errors'])} for r in rows)
    print(json.dumps({'parts':5,'plan_passes':sum(r['status']=='PASS' for r in rows),'plan_incomplete':sum(r['status']!='PASS' for r in rows)},indent=2))
    return 0 if all(r['status']=='PASS' for r in rows) else 1
if __name__=='__main__':raise SystemExit(main())
