"""Artifact completeness and contact sheets for Phase 4; no GT metric."""
import csv,hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';OUT=EXP/'T1';RESULTS=EXP/'results'
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def main():
    calls={r['part_id']:r for r in csv.DictReader((RESULTS/'t1_agent_calls.csv').open())};gates={r['part_id']:r for r in csv.DictReader((RESULTS/'t1_plan_gate.csv').open())};execution={r['part_id']:r for r in csv.DictReader((RESULTS/'t1_execution.csv').open())};pids=sorted(calls);rows=[];folder=RESULTS/'t1_contact_sheets';folder.mkdir(parents=True,exist_ok=True);views=['front','side','top','isometric']
    for pid in pids:
        out=OUT/pid/'round_0';cad=json.loads((out/'cad_validity.json').read_text()) if (out/'cad_validity.json').is_file() else {};required=['agent_output.json','visual_evidence.json','mechanical_interpretation.json','feature_graph.json','cad_ir.json','agent_manifest.json','plan_gate.json']
        if execution[pid]['status']=='SUCCESS':required+=['model.FCStd','model.step','model.stl','feature_tree.json','execution_log.json','cad_validity.json','part_state.json']+[f'renders/{v}.png'for v in views]
        missing=[x for x in required if not(out/x).is_file()or(out/x).stat().st_size==0];nonblank=True
        if execution[pid]['status']=='SUCCESS':
            sheet=Image.new('RGB',(800,420),'white');draw=ImageDraw.Draw(sheet)
            for col,v in enumerate(views):
                for row,path in enumerate([EXP/'artifacts'/pid[:3]/'isolated'/pid/(v+'.png'),out/'renders'/(v+'.png')]):
                    im=Image.open(path).convert('RGB');a=np.asarray(im);nonblank &= bool(np.any(a<245));im.thumbnail((190,180));sheet.paste(im,(col*200+(190-im.width)//2,row*200));draw.text((col*200+5,row*200+180),('GT reference 'if row==0 else'T1 generated ')+v,fill='black')
            sheet.save(folder/(pid+'.png'))
        rows.append({'part_id':pid,'agent':calls[pid]['status'],'plan':gates[pid]['status'],'execution':execution[pid]['status'],'missing':missing,'fallbacks':cad.get('fallback_count',''),'reopen':cad.get('reopen',{}).get('status',''),'edit':cad.get('editability',{}).get('edited_valid',''),'restore':cad.get('editability',{}).get('restored_valid',''),'renders_nonblank':nonblank})
    status='PASS'if all(not r['missing']and r['agent']=='SUCCESS'and r['plan']=='PASS'and r['execution']=='SUCCESS'and str(r['fallbacks'])in['0','0.0']and r['reopen']=='PASS'and r['edit']is True and r['restore']is True and r['renders_nonblank']for r in rows)else'PARTIAL_OR_FAILURE'
    gatevals=[json.loads((OUT/p/'round_0/plan_gate.json').read_text())for p in pids];dump(RESULTS/'t1_phase4_validation.json',{'status':status,'condition':'T1_INTERACTIVE','scope':'Phase 4 planning/CAD validity only; no Phase-5 GT metrics or Quality Gate','parts':rows,'features':sum(g['features']for g in gatevals),'critical_features':sum(g['critical_features']for g in gatevals),'unimplemented_features':sum(g['unimplemented_features']for g in gatevals),'bodies':sum(g['bodies']for g in gatevals),'operations':sum(g['operations']for g in gatevals),'t2_transfer_outputs':0})
    artifacts=[]
    for path in sorted(OUT.rglob('*')):
        if path.is_file():artifacts.append({'path':str(path.relative_to(EXP)),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    with(RESULTS/'t1_artifact_manifest.csv').open('w',newline='',encoding='utf-8')as f:w=csv.DictWriter(f,fieldnames=list(artifacts[0]));w.writeheader();w.writerows(artifacts)
    print(json.dumps({'status':status,'parts':len(rows),'agents':sum(r['agent']=='SUCCESS'for r in rows),'plans':sum(r['plan']=='PASS'for r in rows),'builds':sum(r['execution']=='SUCCESS'for r in rows)},indent=2))
if __name__=='__main__':main()
