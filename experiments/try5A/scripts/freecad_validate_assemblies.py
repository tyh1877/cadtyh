"""Reopen and recompute all three whole-robot FCStd assemblies."""
import json
from pathlib import Path
import FreeCAD as App
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';rows=[]
for c in ('A0','A1','A2'):
 p=HERE/f'assemblies/{c}/assembled_robot.FCStd';doc=App.openDocument(str(p));doc.recompute();links=[o for o in doc.Objects if o.Name.startswith('Link_L')];rows.append({'condition':c,'fcstd_exists':p.is_file(),'reopen':'PASS','recompute':'PASS','link_objects':len(links),'valid_shapes':sum(not o.Shape.isNull() and o.Shape.isValid() for o in links),'step_exists':(p.parent/'assembled_robot.step').is_file(),'stl_exists':(p.parent/'assembled_robot.stl').is_file()});App.closeDocument(doc.Name)
(HERE/'results/assembly_reopen_validation.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows));raise SystemExit(not all(x['link_objects']==12 and x['valid_shapes']==12 and x['step_exists'] and x['stl_exists'] for x in rows))
