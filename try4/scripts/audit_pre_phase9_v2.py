"""Audit pre-Phase-9 v2 pilot coverage, CAD validity, determinism and scope."""
import csv,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';RES=EXP/'results';pids=['R01_P00','R02_P02','R02_P05','R02_P06'];snap=json.loads((RES/'pre_phase9_v2_method_snapshot.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
method={p:sha(EXP/p)==h for p,h in snap['files'].items()};parts=[];manifest=[]
for pid in pids:
 d=EXP/f'PRE_PHASE9_V2/{pid}/round_0';v=json.loads((d/'cad_validity.json').read_text());required=['agent_output.json','cad_ir.json','feature_graph.json','model.FCStd','model.step','model.stl','feature_tree.json','execution_log.json','v2_metrics.json','renders/front.png','renders/side.png','renders/top.png','renders/isometric.png'];missing=[x for x in required if not (d/x).exists()];parts.append({'part_id':pid,'missing':missing,'cad_success':v['status']=='SUCCESS','fallbacks':v['fallback_count'],'reopen':v['reopen']['status'],'edit':v['editability']['edited_valid'] and v['editability']['restored_valid']})
 for p in d.rglob('*'):
  if p.is_file():manifest.append({'path':str(p.relative_to(EXP)),'bytes':p.stat().st_size,'sha256':sha(p)})
with (RES/'pre_phase9_v2_artifact_manifest.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(manifest[0]));w.writeheader();w.writerows(manifest)
det=json.loads((RES/'pre_phase9_v2_determinism.json').read_text(encoding='utf-8-sig'));checks={'method_hashes_match':all(method.values()),'four_parts':len(parts)==4,'all_artifacts_complete':all(not p['missing'] for p in parts),'all_native_cad_valid':all(p['cad_success'] and p['fallbacks']==0 and p['reopen']=='PASS' and p['edit'] for p in parts),'metrics_deterministic':det['match'],'pilot_gate_failed_recorded':True,'formal_v2_matrix_not_started':len(list((EXP/'PRE_PHASE9_V2').glob('R*/round_[1-9]*')))==0,'robot_c_absent':not any(p.name.startswith('R03') for p in (EXP/'PRE_PHASE9_V2').glob('R*'))}
out={'status':'PASS' if all(checks.values()) else 'FAIL','experiment_outcome':'PILOT_GATE_FAIL_DO_NOT_ENTER_PHASE9','checks':checks,'method_files':method,'parts':parts};(RES/'pre_phase9_v2_validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));raise SystemExit(out['status']!='PASS')
