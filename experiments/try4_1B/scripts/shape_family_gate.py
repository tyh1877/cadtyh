"""Pre-build Shape-Family Gate independent of GT/evaluator annotations."""
import argparse,csv,json
from pathlib import Path
import jsonschema
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try4_1B';ap=argparse.ArgumentParser();ap.add_argument('--condition',choices=['B1','B2'],required=True);a=ap.parse_args();schema=json.loads((HERE/'schemas/executable_shape_family_v1.schema.json').read_text());rows=[]
for p in sorted((HERE/f'shape_family_schemas/{a.condition}').glob('*.json')):
 errors=[]
 try:inst=json.loads(p.read_text());jsonschema.validate(inst,schema)
 except Exception as e:errors.append(type(e).__name__);inst={}
 if inst:
  ids={s['substructure_id'] for s in inst['substructures']};errors += ['required_substructure_missing'] if not set(inst['required_substructures'])<=ids else [];errors += ['open_space_rule_missing'] if not inst['open_space_rules'] else [];errors += ['symmetry_rule_missing'] if not inst['symmetry_rules'] else [];errors += ['nonpositive_bbox'] if any(min(s['approximate_bbox'])<=0 for s in inst['substructures']) else []
 rows.append({'condition':a.condition,'part_id':inst.get('part_id',p.stem),'status':'PASS' if not errors else 'SHAPE_FAMILY_FAIL','errors':';'.join(errors)})
out=HERE/f'results/{a.condition.lower()}_shape_family_gate.csv';out.parent.mkdir(exist_ok=True);f=out.open('w',newline='',encoding='utf-8');w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows);f.close();print(json.dumps(rows));raise SystemExit(any(r['status']!='PASS' for r in rows))
