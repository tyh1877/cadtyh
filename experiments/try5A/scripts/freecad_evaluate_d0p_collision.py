"""Exact collision evaluator for D0_physicalized; virtual frames excluded."""
import json,math,sys
from pathlib import Path
import FreeCAD as App,Part
job=json.loads(Path(sys.argv[-1]).read_text());root=Path(job['root']);here=root/'experiments/try5A';T=here/'try5A_2';poses=json.loads((root/'experiments/try5A_1/collision_cache/collision_poses.json').read_text());types={x['link_id']:x for x in json.loads((T/'virtual_link_filter/link_realization_types.json').read_text())['links']};links=[x for x in poses['links'] if types[x]['solid_generation_allowed']];joints=[x for x in poses['joints'] if x['parent'] in links and x['child'] in links];adj={frozenset((x['parent'],x['child'])) for x in joints};source={}
for lid in links:
 p=T/'D0_physicalized/links'/lid;d=App.openDocument(str(p/'model.FCStd'));ir=json.loads((p/'cad_ir.json').read_text());source[lid]=Part.makeCompound([d.getObject(n).Shape.copy() for n in ir['final_objects']]);App.closeDocument(d.Name)
def mat(v):
 m=App.Matrix()
 for r in range(4):
  for c in range(4):setattr(m,f'A{r+1}{c+1}',v[r][c])
 return m
def ov(a,b):return not(a.XMax<b.XMin or b.XMax<a.XMin or a.YMax<b.YMin or b.YMax<a.YMin or a.ZMax<b.ZMin or b.ZMax<a.ZMin)
rows=[]
for pose in poses['poses']:
 shapes={x:source[x].transformGeometry(mat(pose['world_transforms_mm'][x])) for x in links}
 for i,a in enumerate(links):
  for b in links[i+1:]:
   broad=ov(shapes[a].BoundBox,shapes[b].BoundBox); adjacent=frozenset((a,b)) in adj;rec={'pose_id':pose['pose_id'],'pose_kind':pose['kind'],'active_joint':pose['active_joint'],'link_a':a,'link_b':b,'adjacent_urdf':adjacent,'aabb_overlap':broad,'narrow_status':'BROAD_CLEAR','intersection_volume_mm3':None,'classification':'AABB_CLEAR'}
   if broad:
    try:
     c=shapes[a].common(shapes[b]);v=0.0 if c.isNull() else float(c.Volume);rec.update(narrow_status='EXACT_OK',intersection_volume_mm3=v)
     if v>1e-6:rec['classification']=('MOTION_ADJACENT_UNINTENDED' if adjacent else 'MOTION_INDUCED_TRUE') if pose['kind']=='sweep' else ('ADJACENT_UNINTENDED' if adjacent else 'NONADJACENT_TRUE')
     else:rec['classification']='EXPECTED_INTERFACE' if adjacent else 'AABB_FALSE_POSITIVE'
    except Exception as e:rec.update(narrow_status='NARROW_ERROR',classification='NARROW_ERROR',error=str(e))
   rows.append(rec)
(T/'evaluator/raw/d0p_collision_rows.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps({'pairs':len(rows),'true':sum('TRUE' in x['classification'] or 'UNINTENDED' in x['classification'] for x in rows),'errors':sum(x['narrow_status']=='NARROW_ERROR' for x in rows)}))
