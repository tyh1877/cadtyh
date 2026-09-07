"""Export explicit topology/substructure graph artifacts from frozen condition records."""
import json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try4_1B';A=ROOT/'experiments/try4_1A'
for pid in ('R02_P04','R02_P06'):
 src=A/f'topology_graphs/A1/{pid}.json';out=HERE/f'topology_graphs/B0/{pid}.json';out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,out);ref=HERE/f'B0/{pid}/reference.json';ref.parent.mkdir(parents=True,exist_ok=True);ref.write_text(json.dumps({'condition':'B0','part_id':pid,'frozen_artifact':str((A/f'A1/{pid}/round_0').relative_to(ROOT)),'regenerated':False},indent=2)+'\n')
 for cond in ('B1','B2'):
  inst=json.loads((HERE/f'shape_family_schemas/{cond}/{pid}.json').read_text());nodes=[{'node_id':s['substructure_id'],'role':s['semantic_role'],'feature_ref':s['feature_ref']} for s in inst['substructures']];rels=[]
  for s in inst['substructures']:
   rels += [{'source':s['substructure_id'],'relation':'connected_to','target':x} for x in s['connection_relation'] if any(y['substructure_id']==x for y in inst['substructures'])]
   if s['symmetry_relation'] and any(y['substructure_id']==s['symmetry_relation'] for y in inst['substructures']):rels.append({'source':s['substructure_id'],'relation':'symmetric_with','target':s['symmetry_relation']})
  graph={'part_id':pid,'condition':cond,'nodes':nodes,'relations':rels};p=HERE/f'topology_graphs/{cond}/{pid}.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(graph,indent=2)+'\n');q=HERE/f'substructure_graphs/{cond}/{pid}.json';q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps({'part_id':pid,'condition':cond,'family':inst['family'],'substructures':inst['substructures']},indent=2)+'\n')
print('exported')
