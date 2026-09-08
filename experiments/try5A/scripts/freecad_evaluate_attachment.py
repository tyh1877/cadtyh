"""Measure carrier-to-nearest-BODY relation for D0 and produce attachment classifications."""
import json,sys
from pathlib import Path
import FreeCAD as App,Part
job=json.loads(Path(sys.argv[-1]).read_text());root=Path(job['root']);here=root/'experiments/try5A';out=here/'try5A_2/evaluator';source=root/'experiments/try5A_1/C1';types={x['link_id']:x for x in json.loads((here/'try5A_2/virtual_link_filter/link_realization_types.json').read_text())['links']};tol=1e-5;rows=[]
for i in range(12):
 lid=f'L{i:02d}';kind=types[lid]['link_realization_type'];doc=App.openDocument(str(source/lid/'model.FCStd'));ir=json.loads((source/lid/'cad_ir.json').read_text());op={x['op_id']:x for x in ir['operations']};body_names=[n for n in ir['final_objects'] if op[n]['feature_ref']=='BODY']
 if kind not in {'physical_body','rigid_subassembly'}:
  rows.append({'link_id':lid,'carrier_id':None,'classification':'VIRTUAL_OR_INTERFACE_ONLY','included_in_bicr':False,'reason':'virtual frame','body_target_object':None});App.closeDocument(doc.Name);continue
 for n in ir['final_objects']:
  if not op[n]['feature_ref'].startswith('IF_'):continue
  jid=op[n]['feature_ref'][3:]
  if jid=='J10' and types['L11']['link_realization_type']=='virtual_frame':
   rows.append({'link_id':lid,'carrier_id':op[n]['feature_ref'],'classification':'VIRTUAL_OR_INTERFACE_ONLY','included_in_bicr':False,'reason':'peer L11 is virtual frame','body_target_object':None});continue
  carrier=doc.getObject(n).Shape;best=None
  for bn in body_names:
   b=doc.getObject(bn).Shape;d,pts,_=b.distToShape(carrier);common=b.common(carrier);vol=0.0 if common.isNull() else float(common.Volume);area=0.0 if common.isNull() else float(common.Area);candidate=(float(d),-vol,bn,vol,area,pts)
   if best is None or candidate[:2]<best[:2]:best=candidate
  d,neg,bn,vol,area,pts=best
  def xyz(v): return [float(v.x),float(v.y),float(v.z)]
  bp=xyz(pts[0][0]) if pts else None;cp=xyz(pts[0][1]) if pts else None
  cls='OVERLAPPING_SEPARATE_SOLID' if vol>tol else ('POSITIVE_GAP' if d>tol else 'OVERLAPPING_SEPARATE_SOLID')
  rows.append({'link_id':lid,'carrier_id':op[n]['feature_ref'],'carrier_object':n,'classification':cls,'included_in_bicr':True,'body_target_object':bn,'minimum_distance_mm':d,'intersection_volume_mm3':vol,'contact_area_mm2':area,'nearest_body_point_mm':bp,'nearest_carrier_point_mm':cp,'reason':'separate final solids; no attachment path'})
 App.closeDocument(doc.Name)
out.mkdir(parents=True,exist_ok=True);(out/'raw').mkdir(exist_ok=True);(out/'raw/d0_attachment_rows.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps({'overlap':sum(x.get('classification')=='OVERLAPPING_SEPARATE_SOLID' for x in rows),'gap':sum(x.get('classification')=='POSITIVE_GAP' for x in rows),'excluded':sum(not x['included_in_bicr'] for x in rows)}))
