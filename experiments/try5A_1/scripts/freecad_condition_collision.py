"""Evaluate exact B-Rep collisions for C1/C2 with C0's frozen pose set."""
import json,math,sys
from pathlib import Path
import FreeCAD as App,Part
job=json.loads(Path(sys.argv[-1]).read_text());root=Path(job['root']);cond=job['condition'];here=root/'experiments/try5A_1';poses=json.loads((here/'collision_cache/collision_poses.json').read_text());links=poses['links'];joints=poses['joints'];adj={frozenset((j['parent'],j['child'])) for j in joints};source={}
for lid in links:
 d=App.openDocument(str(here/cond/lid/'model.FCStd'));ir=json.loads((here/cond/lid/'cad_ir.json').read_text());source[lid]=Part.makeCompound([d.getObject(x).Shape.copy() for x in ir['final_objects']]);App.closeDocument(d.Name)
def matrix(values):
 m=App.Matrix()
 for r in range(4):
  for c in range(4): setattr(m,f'A{r+1}{c+1}',values[r][c])
 return m
def overlap(A,B): return not(A.XMax<B.XMin or B.XMax<A.XMin or A.YMax<B.YMin or B.YMax<A.YMin or A.ZMax<B.ZMin or B.ZMax<A.ZMin)
def gap(A,B):
 d=[max(0,A.XMin-B.XMax,B.XMin-A.XMax),max(0,A.YMin-B.YMax,B.YMin-A.YMax),max(0,A.ZMin-B.ZMax,B.ZMin-A.ZMax)];return math.sqrt(sum(x*x for x in d))
rows=[]
for pose in poses['poses']:
 shapes={lid:source[lid].transformGeometry(matrix(pose['world_transforms_mm'][lid])) for lid in links}
 for i,a in enumerate(links):
  for b in links[i+1:]:
   broad=overlap(shapes[a].BoundBox,shapes[b].BoundBox); adjacent=frozenset((a,b)) in adj
   rec={'condition':cond,'pose_id':pose['pose_id'],'pose_kind':pose['kind'],'active_joint':pose['active_joint'],'link_a':a,'link_b':b,'adjacent_urdf':adjacent,'aabb_overlap':broad,'narrow_status':'NOT_RUN','intersection_volume_mm3':None,'minimum_clearance_mm':None,'classification':None}
   if not broad: rec.update(narrow_status='BROAD_CLEAR',minimum_clearance_mm=gap(shapes[a].BoundBox,shapes[b].BoundBox),classification='AABB_CLEAR')
   else:
    try:
     common=shapes[a].common(shapes[b]);vol=0.0 if common.isNull() else float(common.Volume)
     if not math.isfinite(vol) or vol<0: raise RuntimeError('invalid common volume')
     rec['narrow_status']='EXACT_OK';rec['intersection_volume_mm3']=vol
     if vol>1e-6:
      rec['minimum_clearance_mm']=0.0;rec['classification']=('MOTION_ADJACENT_UNINTENDED' if adjacent else 'MOTION_INDUCED_TRUE') if pose['kind']=='sweep' else ('ADJACENT_UNINTENDED' if adjacent else 'NONADJACENT_TRUE')
     else:
      try: rec['minimum_clearance_mm']=float(shapes[a].distToShape(shapes[b])[0])
      except Exception: pass
      rec['classification']='EXPECTED_INTERFACE' if adjacent else 'AABB_FALSE_POSITIVE'
    except Exception as e: rec.update(narrow_status='NARROW_ERROR',classification='NARROW_ERROR',error=f'{type(e).__name__}: {e}')
   rows.append(rec)
(here/'collision_cache'/f'{cond.lower()}_raw_pairs.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps({'condition':cond,'pairs':len(rows),'broad':sum(x['aabb_overlap'] for x in rows),'true':sum('TRUE' in x['classification'] or 'UNINTENDED' in x['classification'] for x in rows),'errors':sum(x['narrow_status']=='NARROW_ERROR' for x in rows)}))
