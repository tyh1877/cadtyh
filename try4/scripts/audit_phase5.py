"""Audit frozen Phase-5 method, inputs, outputs, determinism, and scope."""
import csv,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';RES=EXP/'results';CACHE=EXP/'evaluation_cache/gt'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
snap=json.loads((RES/'phase5_method_snapshot.json').read_text(encoding='utf-8'));method={p:sha(EXP/p)==h for p,h in snap['files'].items()}
rows=list(csv.DictReader((RES/'phase5_metrics.csv').open(encoding='utf-8')));det=json.loads((RES/'phase5_determinism_audit.json').read_text(encoding='utf-8-sig'))
prov={x['robot_id']:x for x in json.loads((EXP/'robots/source_provenance.json').read_text(encoding='utf-8'))};gt=[]
for rid,count in [('R01',5),('R02',7)]:
    src=ROOT/prov[rid]['step_path'];gt.append({'robot_id':rid,'source_step':prov[rid]['step_path'],'expected_step_sha256':prov[rid]['step_sha256'],'actual_step_sha256':sha(src),'part_meshes':[{'part_id':f'{rid}_P{i:02d}','bytes':(CACHE/rid/f'{rid}_P{i:02d}.stl').stat().st_size,'sha256':sha(CACHE/rid/f'{rid}_P{i:02d}.stl')} for i in range(count)]})
(RES/'phase5_gt_manifest.json').write_text(json.dumps(gt,indent=2)+'\n',encoding='utf-8')
checks={'method_hashes_match':all(method.values()),'metric_rows_17':len(rows)==17,'conditions_correct':sum(r['condition']=='T0' for r in rows)==5 and sum(r['condition']=='T1' for r in rows)==12,'all_determinism_hashes_match':all(x['match'] for x in det),'gt_step_hashes_match':all(x['expected_step_sha256']==x['actual_step_sha256'] for x in gt),'no_pass':all(r['gate_status']!='PASS' for r in rows),'no_t2_directory':not (EXP/'T2').exists(),'no_r03_evaluation':not any(r['robot_id']=='R03' for r in rows)}
out={'status':'PASS' if all(checks.values()) else 'FAIL','scope':'Phase 5 only','checks':checks,'method_files':method,'evaluations':len(rows),'gate_counts':{s:sum(r['gate_status']==s for r in rows) for s in ('PASS','LOCAL_REPAIR','REPLAN')}}
(RES/'phase5_validation.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,indent=2));raise SystemExit(out['status']!='PASS')
