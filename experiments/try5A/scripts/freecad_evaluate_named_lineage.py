"""Exact B-Rep evaluator reusable for a named physical-link lineage."""
import json,sys
from pathlib import Path
import FreeCAD as App,Part
job=json.loads(Path(sys.argv[-1]).read_text());root=Path(job['root']);T=root/'experiments/try5A/try5A_2';line=json.loads(Path(job['lineage']).read_text());out=Path(job['output']);poses=json.loads((root/'experiments/try5A_1/collision_cache/collision_poses.json').read_text());links=sorted(line);adj={frozenset((x['parent'],x['child'])) for x in poses['joints'] if x['parent'] in links and x['child'] in links};src={}
for lid in links:
 p=Path(line[lid]['model_dir']);d=App.openDocument(str(p/'model.FCStd'));ir=json.loads((p/'cad_ir.json').read_text());src[lid]=Part.makeCompound([d.getObject(n).Shape.copy() for n in ir['final_objects']]);App.closeDocument(d.Name)
def mat(v):
 m=App.Matrix()
 for i in range(4):
  for j in range(4):setattr(m,f'A{i+1}{j+1}',v[i][j])
 return m
def ov(a,b):return not(a.XMax<b.XMin or b.XMax<a.XMin or a.YMax<b.YMin or b.YMax<a.YMin or a.ZMax<b.ZMin or b.ZMax<a.ZMin)
rows=[]
for p in poses['poses']:
 sh={x:src[x].transformGeometry(mat(p['world_transforms_mm'][x])) for x in links}
 for i,a in enumerate(links):
  for b in links[i+1:]:
   broad=ov(sh[a].BoundBox,sh[b].BoundBox);ad=frozenset((a,b)) in adj;r={'pose_id':p['pose_id'],'pose_kind':p['kind'],'link_a':a,'link_b':b,'adjacent_urdf':ad,'aabb_overlap':broad,'classification':'AABB_CLEAR','intersection_volume_mm3':None,'narrow_status':'BROAD_CLEAR'}
   if broad:
    c=sh[a].common(sh[b]);v=0 if c.isNull() else float(c.Volume);r.update(narrow_status='EXACT_OK',intersection_volume_mm3=v);r['classification']=('MOTION_ADJACENT_UNINTENDED' if ad else 'MOTION_INDUCED_TRUE') if v>1e-6 and p['kind']=='sweep' else (('ADJACENT_UNINTENDED' if ad else 'NONADJACENT_TRUE') if v>1e-6 else ('EXPECTED_INTERFACE' if ad else 'AABB_FALSE_POSITIVE'))
   rows.append(r)
out.write_text(json.dumps(rows,indent=2)+'\n');print(len(rows))
