"""Artifact-level Phase 3 audit and diagnostic contact sheets (no GT metrics)."""
import csv,json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';OUT=EXP/'T0';RESULTS=EXP/'results'

def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def main():
    calls={r['part_id']:r for r in csv.DictReader((RESULTS/'t0_agent_calls.csv').open())};gates={r['part_id']:r for r in csv.DictReader((RESULTS/'t0_plan_gate.csv').open())};execution={r['part_id']:r for r in csv.DictReader((RESULTS/'t0_execution.csv').open())}
    rows=[];views=['front','side','top','isometric'];folder=RESULTS/'t0_contact_sheets';folder.mkdir(parents=True,exist_ok=True)
    for i in range(5):
        pid=f'R01_P{i:02d}';out=OUT/pid/'round_0';required=['agent_output.json','agent_manifest.json','plan_gate.json']
        if execution[pid]['status']=='SUCCESS':required += ['model.FCStd','model.step','model.stl','feature_graph.json','cad_ir.json','feature_tree.json','execution_log.json','cad_validity.json','part_state.json']+[f'renders/{v}.png' for v in views]
        missing=[x for x in required if not (out/x).is_file() or (out/x).stat().st_size==0]
        cad=json.loads((out/'cad_validity.json').read_text()) if (out/'cad_validity.json').is_file() else {}
        render_ok=True
        for v in views:
            if not (out/'renders'/(v+'.png')).is_file():continue
            a=np.asarray(Image.open(out/'renders'/(v+'.png')).convert('RGB'));render_ok &= bool(np.any(a<245))
        rows.append({'part_id':pid,'agent_status':calls[pid]['status'],'plan_status':gates[pid]['status'],'execution_status':execution[pid]['status'],'missing_artifacts':missing,'fallbacks':cad.get('fallback_count',''),'reopen':cad.get('reopen',{}).get('status',''),'edit_valid':cad.get('editability',{}).get('edited_valid',''),'restore_valid':cad.get('editability',{}).get('restored_valid',''),'renders_nonblank':render_ok})
        if execution[pid]['status']=='SUCCESS':
            sheet=Image.new('RGB',(800,420),'white');draw=ImageDraw.Draw(sheet)
            for col,v in enumerate(views):
                for row,path in enumerate([EXP/'artifacts/R01/isolated'/pid/(v+'.png'),out/'renders'/(v+'.png')]):
                    im=Image.open(path).convert('RGB');im.thumbnail((190,180));sheet.paste(im,(col*200+(190-im.width)//2,row*200));draw.text((col*200+5,row*200+180),('GT reference ' if row==0 else 'T0 generated ')+v,fill='black')
            sheet.save(folder/(pid+'.png'))
    status='PASS' if all(not r['missing_artifacts'] and r['agent_status']=='SUCCESS' and r['plan_status']=='PASS' and r['execution_status']=='SUCCESS' and str(r['fallbacks']) in ['0',"0.0"] and r['reopen']=='PASS' and r['edit_valid'] is True and r['restore_valid'] is True and r['renders_nonblank'] for r in rows) else 'PARTIAL_OR_FAILURE'
    gates=[json.loads((OUT/f'R01_P{i:02d}/round_0/plan_gate.json').read_text()) for i in range(5)]
    dump(RESULTS/'t0_phase3_validation.json',{'status':status,'condition':'T0_INTERACTIVE','context_isolation':False,'scope':'Phase 3 CAD validity/artifact completeness only; no GT geometry or quality score','parts':rows,
         'planned_features':sum(g['planned_features'] for g in gates),'unimplemented_features':sum(g['unimplemented_features'] for g in gates),'critical_unimplemented':sum(g['critical_unimplemented'] for g in gates),'bodies':sum(g['body_count'] for g in gates),'operations':sum(g['operation_count'] for g in gates),
         'quality_gate_status':'NOT_RUN_UNTIL_PHASE5','transfer_outputs':0,'t1_t2_outputs':0})
    artifacts=[]
    for path in sorted(OUT.rglob('*')):
        if path.is_file():artifacts.append({'path':str(path.relative_to(EXP)),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    with (RESULTS/'t0_artifact_manifest.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(artifacts[0]));w.writeheader();w.writerows(artifacts)
    print(json.dumps({'status':status,'parts':len(rows),'agents':sum(r['agent_status']=='SUCCESS' for r in rows),'plans':sum(r['plan_status']=='PASS' for r in rows),'builds':sum(r['execution_status']=='SUCCESS' for r in rows)},indent=2))
if __name__=='__main__':main()
