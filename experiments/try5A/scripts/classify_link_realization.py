"""Classify URDF links before any physical-geometry evaluator consumes them."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; HERE=ROOT/'experiments/try5A'; OUT=HERE/'try5A_2/virtual_link_filter'
plan=json.loads((HERE/'blackboard/robot_assembly_plan.json').read_text())
rows=[]
for link in plan['links']:
 lid=link['link_id']; role=link['role']; family=link['body_family']
 # Frame markers are kinematic metadata, never an independent physical part.
 realization='virtual_frame' if role=='tool_center_frame' or family=='interface_marker' else 'physical_body'
 rows.append({'link_id':lid,'role':role,'body_family':family,'link_realization_type':realization,'solid_generation_allowed':realization in {'physical_body','rigid_subassembly'},'render_allowed':realization in {'physical_body','rigid_subassembly'},'collision_allowed':realization in {'physical_body','rigid_subassembly'},'reason':'tool-center coordinate frame only' if realization=='virtual_frame' else 'URDF moving or structural link'})
OUT.mkdir(parents=True,exist_ok=True);(OUT/'link_realization_types.json').write_text(json.dumps({'schema_version':'try5A_2_link_realization_v1','links':rows},indent=2)+'\n')
print(json.dumps({'physical':[x['link_id'] for x in rows if x['solid_generation_allowed']],'virtual':[x['link_id'] for x in rows if not x['solid_generation_allowed']]}))
