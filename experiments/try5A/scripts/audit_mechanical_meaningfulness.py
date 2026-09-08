"""Audit every non-virtual feature in the current A2 CAD IR provenance graph."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';OUT=HERE/'results/try5a3_full';required=('feature_id','mechanical_role','source_evidence','source_design_node','why_required','related_interface_or_body','cad_strategy')
rows=[]
for i in range(12):
 lid=f'L{i:02d}';agent=json.loads((HERE/f'A2/{lid}/agent_output.json').read_text())
 if agent.get('link_realization_type')=='virtual_frame':continue
 for feature in agent['feature_graph']['features']:
  missing=[key for key in required if not feature.get(key)];rows.append({'link_id':lid,'feature_id':feature['feature_id'],'missing':missing,'status':'PASS' if not missing else 'MECHANICAL_MEANINGFULNESS_FAIL'})
result={'status':'PASS' if all(row['status']=='PASS' for row in rows) else 'FAIL','meaningful_geometry_rate':sum(row['status']=='PASS' for row in rows)/len(rows),'meaningless_patch_count':sum(row['status']!='PASS' for row in rows),'features':rows,'virtual_geometry_count':0}
OUT.mkdir(parents=True,exist_ok=True);(OUT/'k1_mechanical_meaningfulness.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));raise SystemExit(result['status']!='PASS')
