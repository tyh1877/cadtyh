"""Reject CAD IR whose primitive family contradicts its selected interface family."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';OUT=HERE/'results/try5a3_interface_geometry_semantics.json';rows=[]
for i in range(12):
 lid=f'L{i:02d}';p=HERE/'A2'/lid;ir=json.loads((p/'cad_ir.json').read_text());refs=json.loads((p/'InterfaceRefs.json').read_text())['interfaces'];ops=ir.get('operations',[])
 for ref in refs:
  fid='IF_'+ref['joint_id'];kinds=[x['op_type'] for x in ops if x['feature_ref']==fid];family=ref['interface_family'];side=ref['side']
  if family=='end_tool_interface':ok=not kinds;rule='metadata only; no solid'
  elif family=='rail_slider_interface':ok=bool(kinds) and set(kinds)=={'oriented_box'};rule='rectilinear rail/slider primitives'
  elif family=='planar_mount_interface':ok=bool(kinds) and set(kinds)=={'oriented_box'};rule='planar plate primitive'
  elif family=='fork_pin_interface':ok=(kinds.count('oriented_box')>=2 if side=='parent' else kinds==['cylinder_primitive']);rule='two fork arms on parent; central pin on child'
  elif family in ('coaxial_rotary_interface','nested_rotary_housing'):ok='cylinder_primitive' in kinds;rule='coaxial cylindrical carrier/housing'
  elif family=='flange_interface':ok=kinds==['cylinder_primitive'];rule='circular flange disk'
  else:ok=False;rule='explicit unsupported family failure'
  rows.append({'link_id':lid,'joint_id':ref['joint_id'],'side':side,'interface_family':family,'cad_operation_types':kinds,'required_semantics':rule,'status':'PASS' if ok else 'INTERFACE_GEOMETRY_SEMANTICS_FAIL'})
result={'status':'PASS' if rows and all(x['status']=='PASS' for x in rows) else 'FAIL','interfaces_checked':len(rows),'semantic_match_rate':sum(x['status']=='PASS' for x in rows)/len(rows),'rows':rows};OUT.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2));raise SystemExit(result['status']!='PASS')
