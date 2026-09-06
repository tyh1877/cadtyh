"""Materialize current-agent geometry decisions; adds no geometry or features."""
import csv,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
import jsonschema
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';SOURCE=EXP/'codex_authored/T0_INTERACTIVE';OUT=EXP/'T0';RESULTS=EXP/'results'
FRAME={'origin':[0,0,0],'x_axis':[1,0,0],'y_axis':[0,1,0],'z_axis':[0,0,1]}
FIELDS={'start':None,'end':None,'width_mm':None,'depth_mm':None,'center':None,'axis':None,'radius_mm':None,'height_mm':None,'start_size_mm':None,'end_size_mm':None,'tool_bodies':[],'edge_selectors':[],'distance_mm':None,'operation_mode':None}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def main():
    schema=json.loads((EXP/'schemas/t0_direct_output.schema.json').read_text());rows=[]
    files=[EXP/'AMENDMENT_T0_INTERACTIVE.md',EXP/'schemas/t0_direct_output.schema.json',Path(__file__),EXP/'scripts/validate_t0.py',EXP/'scripts/freecad_t0_executor.py',EXP/'scripts/run_t0_freecad.py']+sorted(SOURCE.glob('*.json'))
    dump(RESULTS/'t0_interactive_method_snapshot.json',{'created_at':datetime.now(timezone.utc).isoformat(),'condition':'T0_INTERACTIVE','producer':'current_interactive_codex','context_isolation':False,'files':{str(p.relative_to(EXP)):sha(p) for p in files}})
    for i in range(5):
        pid=f'R01_P{i:02d}';source=SOURCE/(pid+'.json');plan=json.loads(source.read_text());assert plan['part_id']==pid
        operations=[]
        for value in plan['operations']:
            op={**FIELDS,**value};op['reference_frame']=FRAME;operations.append(op)
        data={'schema_version':'try4_t0_direct_output_v1','part_id':pid,'feature_graph':{'features':plan['features']},'cad_ir':{'ir_version':'try4_executable_cad_ir_v1','units':'mm','bodies':plan['bodies'],'operations':operations,'final_objects':plan['final_objects'],'editable_parameter':plan['editable_parameter'],'assumptions':plan['assumptions'],'silent_fallback_allowed':False}}
        jsonschema.validate(data,schema)
        out=OUT/pid/'round_0';out.mkdir(parents=True,exist_ok=True)
        if (out/'agent_output.json').exists():raise RuntimeError(f'{pid}: interactive output exists')
        dump(out/'agent_output.json',data)
        manifest={'part_id':pid,'status':'SUCCESS','producer':'current_interactive_codex','execution_mode':'T0_INTERACTIVE','context_isolation':False,'packet_sha256':sha(EXP/'packets'/pid/'part_input.json'),'source_decision_sha256':sha(source),'output_sha256':sha(out/'agent_output.json'),'model_snapshot':'UNAVAILABLE','tokens':'UNAVAILABLE','selection_or_repair':False,'created_at':datetime.now(timezone.utc).isoformat()}
        dump(out/'agent_manifest.json',manifest);rows.append(manifest)
    with (RESULTS/'t0_agent_calls.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps({'condition':'T0_INTERACTIVE','parts':5,'outputs':5,'context_isolation':False}))
if __name__=='__main__':main()
