"""Final audit for the combined Phase 6–8 development execution."""
import hashlib,json
from pathlib import Path
import jsonschema,pandas as pd
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';RES=EXP/'results'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
snap=json.loads((RES/'phase78_method_snapshot.json').read_text());method={p:sha(EXP/p)==h for p,h in snap['files'].items()};contract_schema=json.loads((EXP/'schemas/repair_contract.schema.json').read_text());review_schema=json.loads((EXP/'schemas/post_repair_review.schema.json').read_text());contracts=list((EXP/'codex_authored/T2').glob('round_[123]/R*.json'));[jsonschema.validate(json.loads(p.read_text()),contract_schema) for p in contracts];reviews=list((EXP/'T2').glob('R*/round_*/post_review.json'));[jsonschema.validate(json.loads(p.read_text()),review_schema) for p in reviews]
pids=[f'R01_P{i:02d}' for i in range(5)]+[f'R02_P{i:02d}' for i in range(7)];states=[];complete=0
for pid in pids:
 ps=json.loads((EXP/'T2'/pid/'round_3/part_state.json').read_text());states.append(ps)
 for d in (EXP/'T2'/pid).glob('round_*'):
  if (d/'metrics.json').exists() and all((d/x).exists() for x in ['model.FCStd','model.step','model.stl','renders','feature_graph.json','cad_ir.json','feature_tree.json','metrics.json','review_contract.json','repair_log.json','post_review.json','part_state.json']):complete+=1
repair=json.loads((RES/'repair_metrics.json').read_text());phase5=json.loads((RES/'phase5_method_snapshot.json').read_text());checks={'phase78_method_hashes_match':all(method.values()),'phase5_protocol_hash_unchanged':method.get('protocol/phase5_evaluator_v1.json',False),'contracts_36':len(contracts)==36,'post_reviews_32':len(reviews)==32,'complete_built_rounds_32':complete==32,'all_12_final_states':len(states)==12,'all_stop_by_round3':all(s['repair_round']<=3 for s in states),'all_unresolved_after_combined_gate':all(s['state']=='UNRESOLVED' for s in states),'no_r03':not any('R03' in str(p) for p in (EXP/'T2').rglob('*')),'formal_denominator_12':repair['parts']==12,'freeform_cases_2':len(json.loads((RES/'phase8_freeform_ablation.json').read_text()))==2}
out={'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'method_files':method,'contracts':len(contracts),'built_rounds':complete,'final_states':{x:sum(s['state']==x for s in states) for x in ['FROZEN','UNRESOLVED']}};(RES/'phase678_validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));raise SystemExit(out['status']!='PASS')
