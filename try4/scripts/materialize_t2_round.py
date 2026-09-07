"""Apply a bounded repair contract to the preceding plan; never consumes GT geometry."""
import argparse,copy,hashlib,json
from pathlib import Path
import jsonschema
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4'
from materialize_t1 import compile_recipe,EMPTY,FRAME
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def sha_obj(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--contract',required=True);args=ap.parse_args();cp=Path(args.contract);c=json.loads(cp.read_text(encoding='utf-8'));schema=json.loads((EXP/'schemas/repair_contract.schema.json').read_text());jsonschema.validate(c,schema)
    pid=c['part_id'];rnd=c['round'];out=EXP/'T2'/pid/f'round_{rnd}'
    if rnd==1:prev=EXP/'T1'/pid/'round_0'
    else:
        state=json.loads((EXP/'T2'/pid/f'round_{rnd-1}/part_state.json').read_text());prev=(EXP/state['current_artifact']).parent
    if out.exists():raise RuntimeError(f'{out} already exists')
    prior=json.loads((prev/'agent_output.json').read_text());blueprints=json.loads((EXP/'codex_authored/T1/t1_blueprints.json').read_text())['parts'];bp=copy.deepcopy(next(x for x in blueprints if x['part_id']==pid)) if not (prev/'repair_blueprint.json').exists() else json.loads((prev/'repair_blueprint.json').read_text())
    changes=[]
    for action in sorted(c['repair_actions'],key=lambda x:x['priority']):
        updates=action['parameters'].get('parameter_updates',{})
        for k,v in updates.items():changes.append({'action':action['action'],'parameter':k,'before':bp['parameters'].get(k),'after':v});bp['parameters'][k]=v
        if action['parameters'].get('recipe'):bp['recipe']['type']=action['parameters']['recipe']
    req_to_fid={r:f['feature_id'] for f in prior['feature_graph']['features'] for r in f['requirement_refs']};fmap={x['key']:req_to_fid[x['requirement_ref']] for x in bp['features']};ops,bodies,finals,edit=compile_recipe(bp['recipe'],bp['parameters'],fmap);ops=[{**EMPTY,**x,'reference_frame':FRAME} for x in ops]
    protected=set(c['protected_features']);before_features={f['feature_id']:sha_obj(f) for f in prior['feature_graph']['features'] if f['feature_id'] in protected};after_features={f['feature_id']:sha_obj(f) for f in prior['feature_graph']['features'] if f['feature_id'] in protected}
    before_ops={x['op_id']:sha_obj(x) for x in prior['cad_ir']['operations'] if x['feature_ref'] in protected};after_ops={x['op_id']:sha_obj(x) for x in ops if x['feature_ref'] in protected and x['op_id'] in before_ops};protection={'feature_nodes_unchanged':before_features==after_features,'protected_operation_ids_preserved':set(before_ops)<=set(after_ops),'protected_operation_subgraphs_unchanged':all(before_ops[k]==after_ops.get(k) for k in before_ops)}
    if protected and not all(protection.values()):raise RuntimeError('protected feature subgraph changed')
    data=copy.deepcopy(prior);data['cad_ir']={**prior['cad_ir'],'bodies':bodies,'operations':ops,'final_objects':finals,'editable_parameter':edit,'assumptions':prior['cad_ir'].get('assumptions',[])+[f'T2 round {rnd} executes only structured contract actions.']};data['repair_round']=rnd;data['repair_contract_sha256']=hashlib.sha256(cp.read_bytes()).hexdigest()
    dump(out/'review_contract.json',c);dump(out/'repair_blueprint.json',bp);dump(out/'agent_output.json',data);dump(out/'feature_graph.json',data['feature_graph']);dump(out/'cad_ir.json',data['cad_ir']);dump(out/'repair_log.json',{'part_id':pid,'round':rnd,'status':'APPLIED','changes':changes,'protection':protection,'gt_geometry_consumed':False,'silent_fallback_allowed':False});print(json.dumps({'part_id':pid,'round':rnd,'changes':len(changes),'protection':protection}))
if __name__=='__main__':main()
