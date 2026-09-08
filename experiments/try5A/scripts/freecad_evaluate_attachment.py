"""Strict B-Rep body-to-interface-carrier attachment evaluator for frozen D0=C1."""
import json, sys
from pathlib import Path
import FreeCAD as App, Part
job=json.loads(Path(sys.argv[-1]).read_text());root=Path(job['root']);here=root/'experiments/try5A';out=here/'try5A_2/evaluator';source=root/'experiments/try5A_1/C1';types={x['link_id']:x for x in json.loads((here/'try5A_2/virtual_link_filter/link_realization_types.json').read_text())['links']};tol=1e-5;rows=[]
def compound(doc, names): return Part.makeCompound([doc.getObject(n).Shape.copy() for n in names if doc.getObject(n) and not doc.getObject(n).Shape.isNull()])
for i in range(12):
 lid=f'L{i:02d}';kind=types[lid]['link_realization_type'];doc=App.openDocument(str(source/lid/'model.FCStd'));ir=json.loads((source/lid/'cad_ir.json').read_text());op={x['op_id']:x for x in ir['operations']};body_names=[n for n in ir['final_objects'] if op[n]['feature_ref']=='BODY']; body=compound(doc,body_names)
 if kind not in {'physical_body','rigid_subassembly'}:
  rows.append({'link_id':lid,'carrier_id':None,'realization_type':kind,'included_in_bicr':False,'body_final_objects':body_names,'carrier_final_objects':[],'minimum_distance_mm':None,'intersection_volume_mm3':None,'contact_area_mm2':None,'same_solid':False,'rigid_multibody_declared':False,'connector_geometry_declared':False,'geometric_touch':False,'physically_attached':False,'connectivity_path':'VIRTUAL_EXCLUDED'});App.closeDocument(doc.Name);continue
 for n in ir['final_objects']:
  if not op[n]['feature_ref'].startswith('IF_'): continue
  jid=op[n]['feature_ref'][3:]
  # A carrier exclusively serving a virtual-frame child is metadata, not a physical carrier.
  peer={'J10':'L11'}.get(jid)
  if peer and types[peer]['link_realization_type']=='virtual_frame':
   rows.append({'link_id':lid,'carrier_id':op[n]['feature_ref'],'realization_type':kind,'included_in_bicr':False,'body_final_objects':body_names,'carrier_final_objects':[n],'minimum_distance_mm':None,'intersection_volume_mm3':None,'contact_area_mm2':None,'same_solid':False,'rigid_multibody_declared':False,'connector_geometry_declared':False,'geometric_touch':False,'physically_attached':False,'connectivity_path':'VIRTUAL_PEER_EXCLUDED'});continue
  carrier=compound(doc,[n]);dist=float(body.distToShape(carrier)[0]);common=body.common(carrier);vol=0.0 if common.isNull() else float(common.Volume);area=0.0 if common.isNull() else float(common.Area)
  # A separate overlapping solid is not a Boolean union and is not an allowed rigid connection.
  touch=dist<=tol or vol>tol
  rows.append({'link_id':lid,'carrier_id':op[n]['feature_ref'],'realization_type':kind,'included_in_bicr':True,'body_final_objects':body_names,'carrier_final_objects':[n],'minimum_distance_mm':dist,'intersection_volume_mm3':vol,'contact_area_mm2':area,'same_solid':False,'rigid_multibody_declared':False,'connector_geometry_declared':False,'geometric_touch':touch,'physically_attached':False,'connectivity_path':'NONE: separate final solids; no union, declared rigid contact, or connector'})
 App.closeDocument(doc.Name)
out.mkdir(parents=True,exist_ok=True);(out/'raw').mkdir(exist_ok=True);(out/'raw/d0_attachment_rows.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps({'carriers':sum(x['included_in_bicr'] for x in rows),'attached':sum(x['physically_attached'] for x in rows),'virtual_rows':sum(not x['included_in_bicr'] for x in rows)}))
