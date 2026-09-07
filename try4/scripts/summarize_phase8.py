"""Summarize accepted T2 states, repair/resource metrics, ablation and contact sheets."""
import csv,hashlib,json
from pathlib import Path
import pandas as pd
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';RES=EXP/'results';base=pd.read_csv(RES/'phase5_metrics.csv');pids=[f'R01_P{i:02d}' for i in range(5)]+[f'R02_P{i:02d}' for i in range(7)];final=[];rounds=[];states=[];manifest=[]
for pid in pids:
 last=1 if json.loads((EXP/f'T2/{pid}/round_1/part_state.json').read_text())['state']=='FROZEN' else 3;ps=json.loads((EXP/f'T2/{pid}/round_{last}/part_state.json').read_text());states.append(ps)
 if '#' in ps['accepted_metrics']:m=base[(base.part_id==pid)&(base.condition=='T1')].iloc[0].to_dict();m['condition']='T2_ACCEPTED';m['accepted_round']=0
 else:m=json.loads((EXP/ps['accepted_metrics']).read_text());m['condition']='T2_ACCEPTED';m['accepted_round']=int(Path(ps['accepted_metrics']).parent.name.split('_')[-1])
 m['final_state']=ps['state'];final.append(m)
 for r in range(1,last+1):
  d=EXP/f'T2/{pid}/round_{r}';st=json.loads((d/'part_state.json').read_text());event=st['repair_history'][-1];row={'part_id':pid,'round':r,**event};
  if (d/'metrics.json').exists():row.update({k:json.loads((d/'metrics.json').read_text())[k] for k in ('voxel_iou','normalized_chamfer','normalized_hd95','gate_status')})
  rounds.append(row)
 for path in (EXP/'T2'/pid).rglob('*'):
  if path.is_file():manifest.append({'path':str(path.relative_to(EXP)),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
pd.DataFrame(final).to_csv(RES/'phase8_final_metrics.csv',index=False);pd.DataFrame(rounds).to_csv(RES/'phase8_round_metrics.csv',index=False);pd.DataFrame(manifest).to_csv(RES/'phase8_artifact_manifest.csv',index=False)
trigger=12;frozen=sum(x['state']=='FROZEN' for x in states);unresolved=12-frozen;events=[e for s in states for e in s['repair_history']];executed=[e for e in events if e['candidate_gate']!='NOT_RUN'];regress=sum(bool(e.get('regression')) for e in executed);replans=len({s['part_id'] for s in states if any(e['contract_status']=='REPLAN' for e in s['repair_history'])});scheduled=len(events);protected=[]
for pid in pids:
 for p in (EXP/'T2'/pid).glob('round_*/repair_log.json'):
  x=json.loads(p.read_text());
  if 'protection' in x:protected.append(all(x['protection'].values()))
repair={'parts':12,'repair_trigger_rate':1.0,'scheduled_contracts':scheduled,'executed_candidates':len(executed),'repair_contract_execution_rate':len(executed)/scheduled,'average_scheduled_rounds':scheduled/12,'early_pass_rate':frozen/12,'repair_success_rate':frozen/12,'replan_part_rate':replans/12,'regression_rate_per_executed_candidate':regress/len(executed),'frozen_feature_preservation_rate':sum(protected)/len(protected),'unresolved_rate':unresolved/12,'codex_calls_saved_vs_three_round_all_parts':36-scheduled,'pass_parts':[s['part_id'] for s in states if s['state']=='FROZEN'],'unresolved_parts':[s['part_id'] for s in states if s['state']=='UNRESOLVED']};(RES/'repair_metrics.json').write_text(json.dumps(repair,indent=2)+'\n');pd.DataFrame([{k:v for k,v in repair.items() if not isinstance(v,list)}]).to_csv(RES/'repair_metrics.csv',index=False);pd.DataFrame([{'condition':'T2_INTERACTIVE_STRUCTURED','parts':12,'review_contract_calls':scheduled,'candidate_builds':len(executed),'external_cli_calls':0,'model_snapshot':'UNAVAILABLE','token_accounting':'UNAVAILABLE','calls_saved':36-scheduled}]).to_csv(RES/'resource_metrics.csv',index=False)
# accepted T1-to-T2 paired deltas
f=pd.DataFrame(final).set_index('part_id');b=base[base.condition=='T1'].set_index('part_id');metrics=['voxel_iou','normalized_chamfer','normalized_hd95','silhouette_iou_mean'];deltas=[]
for pid in pids:
 row={'part_id':pid,'accepted_round':f.loc[pid,'accepted_round'],'final_state':f.loc[pid,'final_state']}
 for k in metrics:row[k+'_t1']=b.loc[pid,k];row[k+'_t2']=f.loc[pid,k];row[k+'_delta']=f.loc[pid,k]-b.loc[pid,k]
 deltas.append(row)
pd.DataFrame(deltas).to_csv(RES/'phase8_t1_t2_paired.csv',index=False)
# lightweight accepted-result contact sheets
folder=RES/'t2_contact_sheets';folder.mkdir(exist_ok=True)
for pid,ps in zip(pids,states):
 paths=[EXP/f'artifacts/{pid[:3]}/isolated/{pid}/isometric.png',EXP/f'T1/{pid}/round_0/renders/isometric.png',(EXP/ps['current_artifact']).parent/'renders/isometric.png'];imgs=[Image.open(p).convert('RGB') for p in paths];canvas=Image.new('RGB',(900,330),'white');draw=ImageDraw.Draw(canvas)
 for i,(im,label) in enumerate(zip(imgs,['GT reference','T1 initial','T2 accepted'])):im.thumbnail((280,280));canvas.paste(im,(i*300+(280-im.width)//2,30));draw.text((i*300+8,8),label,fill='black')
 canvas.save(folder/f'{pid}.png')
print(json.dumps(repair))
