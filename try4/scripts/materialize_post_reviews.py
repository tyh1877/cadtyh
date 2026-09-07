"""Write explicit schema-valid post-repair visual/LOD reviews for every built candidate."""
import json
from pathlib import Path
import jsonschema
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';d=json.loads((EXP/'codex_authored/T2/post_review_decisions.json').read_text());schema=json.loads((EXP/'schemas/post_repair_review.schema.json').read_text());n=0
for pid,evidence in d['part_findings'].items():
 for metric in sorted((EXP/'T2'/pid).glob('round_*/metrics.json')):
  rnd=int(metric.parent.name.split('_')[-1]);m=json.loads(metric.read_text());review={'part_id':pid,'round':rnd,'semantic_role_pass':True,'lod_pass':False,'visible_feature_pass':False,'overall_pass':False,'recommended_state':'REPLAN' if m['gate_status']=='PASS' else m['gate_status'],'evidence':evidence,'reviewer':d['reviewer']};jsonschema.validate(review,schema);(metric.parent/'post_review.json').write_text(json.dumps(review,indent=2)+'\n');n+=1
print(n)
