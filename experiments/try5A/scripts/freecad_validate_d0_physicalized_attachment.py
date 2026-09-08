"""Validate physical attachment paths and frozen interface preservation in D0_physicalized."""
import json,sys
from pathlib import Path
import FreeCAD as App
job=json.loads(Path(sys.argv[-1]).read_text());root=Path(job['root']);here=root/'experiments/try5A';T=here/'try5A_2';src=root/'experiments/try5A_1/C1';types={x['link_id']:x for x in json.loads((T/'virtual_link_filter/link_realization_types.json').read_text())['links']};rows=[];diffs=[]
for lid,t in types.items():
 if not t['solid_generation_allowed']:continue
 p=T/'D0_physicalized/links'/lid;ir=json.loads((p/'cad_ir.json').read_text());man=json.loads((p/'attachment_manifest.json').read_text());old=json.loads((src/lid/'cad_ir.json').read_text());old_ops=old['operations'];new_prefix=ir['operations'][:len(old_ops)];refs_same=(src/lid/'InterfaceRefs.json').read_bytes()==(p/'InterfaceRefs.json').read_bytes();ops_same=old_ops==new_prefix;d=App.openDocument(str(p/'model.FCStd'))
 for m in man:
  o=d.getObject(m['attachment_result_object']);valid=bool(o and not o.Shape.isNull() and o.Shape.isValid());solids=len(o.Shape.Solids) if valid else 0;attached=valid and solids==1;rows.append({'link_id':lid,'interface_id':m['interface_id'],'repair_action':m['repair_action'],'attachment_result_object':m['attachment_result_object'],'connector_id':m['connector_object'] or '', 'same_connected_solid':attached,'physical_path_exists':attached,'result_solid_count':solids,'result_valid':valid,'interface_refs_preserved':refs_same,'frozen_prefix_ops_preserved':ops_same})
 if not refs_same or not ops_same:diffs.append(lid)
 App.closeDocument(d.Name)
(T/'evaluator/raw/d0p_attachment_rows.json').write_text(json.dumps(rows,indent=2)+'\n');(T/'results/interface_preservation_d0p.json').write_text(json.dumps({'status':'PASS' if not diffs else 'FAIL','links_checked':11,'changed_frozen_interface_links':diffs},indent=2)+'\n');print(json.dumps({'attachments':len(rows),'attached':sum(x['physical_path_exists'] for x in rows),'bad_interface_diffs':diffs}))
