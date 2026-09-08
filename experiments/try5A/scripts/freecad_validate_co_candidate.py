import json,sys
from pathlib import Path
import FreeCAD as App
job=json.loads(Path(sys.argv[-1]).read_text());p=Path(job['model']);d=App.openDocument(str(p/'model.FCStd'));m=json.loads((p/'attachment_manifest.json').read_text());rows=[]
for x in m:
 o=d.getObject(x['attachment_result_object']);rows.append({'interface':x['interface_id'],'valid':bool(o and o.Shape.isValid() and not o.Shape.isNull()),'solids':len(o.Shape.Solids) if o else 0})
App.closeDocument(d.Name);Path(job['out']).write_text(json.dumps(rows,indent=2)+'\n');print(rows)
