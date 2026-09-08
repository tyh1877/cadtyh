"""Evaluate exact collisions and attachment paths for a D1 selective round."""
import json,sys
from pathlib import Path
import FreeCAD as App,Part
job=json.loads(Path(sys.argv[-1]).read_text());root=Path(job['root']);here=root/'experiments/try5A';T=here/'try5A_2';r=int(job['round']);line=json.loads((T/f'D1/round_{r}/lineage.json').read_text());poses=json.loads((root/'experiments/try5A_1/collision_cache/collision_poses.json').read_text());links=sorted(line);joints=[x for x in poses['joints'] if x['parent'] in links and x['child'] in links];adj={frozenset((x['parent'],x['child'])) for x in joints};source={};attach=[]
for lid in links:
 p=Path(line[lid]['model_dir']);d=App.openDocument(str(p/'model.FCStd'));ir=json.loads((p/'cad_ir.json').read_text());source[lid]=Part.makeCompound([d.getObject(n).Shape.copy() for n in ir['final_objects']]);man=json.loads((p/'attachment_manifest.json').read_text())
 for m in man:
  o=d.getObject(m['attachment_result_object']);ok=bool(o and not o.Shape.isNull() and o.Shape.isValid() and len(o.Shape.Solids)==1);attach.append({'link_id':lid,'interface_id':m['interface_id'],'physical_path_exists':ok,'solid_count':len(o.Shape.Solids) if o else 0})
 App.closeDocument(d.Name)
def mat(v):
 m=App.Matrix()
 for i in range(4):
  for j in range(4):setattr(m,f'A{i+1}{j+1}',v[i][j])
 return m
def ov(a,b):return not(a.XMax<b.XMin or b.XMax<a.XMin or a.YMax<b.YMin or b.YMax<a.YMin or a.ZMax<b.ZMin or b.ZMax<a.ZMin)
truth={'ADJACENT_UNINTENDED','NONADJACENT_TRUE','MOTION_ADJACENT_UNINTENDED','MOTION_INDUCED_TRUE'};rows=[]
for pose in poses['poses']:
 sh={x:source[x].transformGeometry(mat(pose['world_transforms_mm'][x])) for x in links}
 for i,a in enumerate(links):
  for b in links[i+1:]:
   broad=ov(sh[a].BoundBox,sh[b].BoundBox);ad=frozenset((a,b)) in adj;rec={'pose_id':pose['pose_id'],'pose_kind':pose['kind'],'active_joint':pose['active_joint'],'link_a':a,'link_b':b,'adjacent_urdf':ad,'aabb_overlap':broad,'narrow_status':'BROAD_CLEAR','intersection_volume_mm3':None,'classification':'AABB_CLEAR'}
   if broad:
    try:
     c=sh[a].common(sh[b]);v=0.0 if c.isNull() else float(c.Volume);rec.update(narrow_status='EXACT_OK',intersection_volume_mm3=v);rec['classification']=('MOTION_ADJACENT_UNINTENDED' if ad else 'MOTION_INDUCED_TRUE') if v>1e-6 and pose['kind']=='sweep' else (('ADJACENT_UNINTENDED' if ad else 'NONADJACENT_TRUE') if v>1e-6 else ('EXPECTED_INTERFACE' if ad else 'AABB_FALSE_POSITIVE'))
    except Exception as e:rec.update(narrow_status='NARROW_ERROR',classification='NARROW_ERROR',error=str(e))
   rows.append(rec)
(T/f'D1/round_{r}/collision_rows.json').write_text(json.dumps(rows,indent=2)+'\n');(T/f'D1/round_{r}/attachment_rows.json').write_text(json.dumps(attach,indent=2)+'\n');print(json.dumps({'round':r,'true':sum(x['classification'] in truth for x in rows),'attachment_ok':sum(x['physical_path_exists'] for x in attach),'attachments':len(attach),'errors':sum(x['narrow_status']=='NARROW_ERROR' for x in rows)}))
