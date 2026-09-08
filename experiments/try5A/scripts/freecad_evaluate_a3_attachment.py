"""Strict physical body-to-interface attachment audit for current K1 A2 B-Reps."""
import json,sys
from pathlib import Path
import FreeCAD as App
job=json.loads(Path(sys.argv[-1]).read_text());here=Path(job['root'])/'experiments/try5A';out=Path(job['output']);rows=[];tol=1e-6
for i in range(12):
 lid=f'L{i:02d}';p=here/'A2'/lid;ir=json.loads((p/'cad_ir.json').read_text())
 if not ir.get('final_objects'):continue
 doc=App.openDocument(str(p/'model.FCStd'));ops={x['op_id']:x for x in ir['operations']};bodies=[n for n in ir['final_objects'] if ops[n]['feature_ref']=='BODY'];interfaces=[n for n in ir['final_objects'] if ops[n]['feature_ref'].startswith('IF_')]
 for n in interfaces:
  carrier=doc.getObject(n).Shape;best=None
  for bn in bodies:
   body=doc.getObject(bn).Shape;dist=float(body.distToShape(carrier)[0]);c=body.common(carrier);vol=0.0 if c.isNull() else float(c.Volume);candidate=(dist,-vol,bn,vol)
   if best is None or candidate[:2]<best[:2]:best=candidate
  if best is None:rows.append({'link_id':lid,'interface_id':ops[n]['feature_ref'],'attached':False,'classification':'NO_BODY_FINAL_OBJECT'})
  else:
   dist,_,bn,vol=best;rows.append({'link_id':lid,'interface_id':ops[n]['feature_ref'],'body_object':bn,'carrier_object':n,'minimum_distance_mm':dist,'intersection_volume_mm3':vol,'same_connected_solid':False,'attached':False,'classification':'SEPARATE_FINAL_SOLID' if dist<=tol else 'POSITIVE_GAP'})
 App.closeDocument(doc.Name)
result={'status':'PASS' if rows and all(x['attached'] for x in rows) else 'FAIL','attachment_count':len(rows),'attached_count':sum(x['attached'] for x in rows),'bicr':sum(x['attached'] for x in rows)/len(rows) if rows else 0.0,'rows':rows};out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
