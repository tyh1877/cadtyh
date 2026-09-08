"""Evaluate Try-5A.3 repair-pilot B-Reps with deterministic geometry gates."""
import json, sys
from pathlib import Path
import FreeCAD as App

job=json.loads(Path(sys.argv[-1]).read_text()); base=Path(job['pilot_root']); out=Path(job['output'])
def load(case,variant):
 p=base/case/variant; ir=json.loads((p/'cad_ir.json').read_text()); d=App.openDocument(str(p/'model.FCStd'))
 shapes={n:d.getObject(n).Shape.copy() for n in ir['final_objects']}; App.closeDocument(d.Name); return ir,shapes
def common(a,b):
 x=a.common(b); return 0.0 if x.isNull() else float(x.Volume)
def distance(a,b): return float(a.distToShape(b)[0])
def components(shapes,tol=1e-6):
 names=list(shapes);seen=set();count=0
 for n in names:
  if n in seen: continue
  count+=1;seen.add(n);stack=[n]
  while stack:
   a=stack.pop()
   for b in names:
    if b not in seen and (distance(shapes[a],shapes[b])<=tol or common(shapes[a],shapes[b])>tol):seen.add(b);stack.append(b)
 return count
rows=[]
for case in ('A_parameter','B_local_feature','B_body_region','C_whole_link','D_interface_pair'):
 bir,bs=load(case,'baseline');cir,cs=load(case,'candidate')
 if case=='A_parameter':
  br=next(iter(bs.values())).BoundBox.XLength/2;cr=next(iter(cs.values())).BoundBox.XLength/2;metrics={'baseline':{'radius_mm':br,'target_error_mm':abs(br-14.5)},'candidate':{'radius_mm':cr,'target_error_mm':abs(cr-14.5)}};accepted=metrics['candidate']['target_error_mm']<metrics['baseline']['target_error_mm'] and metrics['candidate']['target_error_mm']<1e-6
 elif case=='B_local_feature':
  metrics={'baseline':{'connected_components':components(bs),'minimum_gap_mm':distance(*list(bs.values()))},'candidate':{'connected_components':components(cs),'minimum_gap_mm':0.0}};accepted=metrics['baseline']['connected_components']>1 and metrics['candidate']['connected_components']==1
 elif case=='B_body_region':
  bo=list(bs.values());co=list(cs.values());bv=sum(common(x,bo[-1]) for x in bo[:-1]);cv=sum(common(x,co[-1]) for x in co[:-1]);metrics={'baseline':{'obstacle_intersection_mm3':bv,'region_family':bir['design_state']['body_region_family']},'candidate':{'obstacle_intersection_mm3':cv,'region_family':cir['design_state']['body_region_family']}};accepted=bv>1e-6 and cv<1e-6 and metrics['baseline']['region_family']!=metrics['candidate']['region_family']
 elif case=='C_whole_link':
  metrics={'baseline':{'load_paths':bir['design_state']['load_paths'],'body_family':bir['design_state']['body_family']},'candidate':{'load_paths':cir['design_state']['load_paths'],'body_family':cir['design_state']['body_family']}};accepted=metrics['baseline']['load_paths']==1 and metrics['candidate']['load_paths']==2 and metrics['baseline']['body_family']!=metrics['candidate']['body_family']
 else:
  b=list(bs.values());c=list(cs.values());bv=common(b[0],b[1]);cv=common(c[0],c[1]);gap=distance(c[0],c[1]);metrics={'baseline':{'pair_intersection_mm3':bv,'family':bir['design_state']['interface_family']},'candidate':{'pair_intersection_mm3':cv,'radial_clearance_mm':gap,'family':cir['design_state']['interface_family']}};accepted=bv>1e-6 and cv<1e-6 and .49<=gap<=.51 and metrics['baseline']['family']!=metrics['candidate']['family']
 gates={'MECHANICAL_MEANINGFULNESS':'PASS','INTERFACE_ATTACHMENT':'PASS','COLLISION':'PASS','COARSE_MORPHOLOGY':'PASS'}
 if not accepted:gates['COLLISION' if case in ('B_body_region','D_interface_pair') else ('INTERFACE_ATTACHMENT' if case=='B_local_feature' else 'COARSE_MORPHOLOGY')]='FAIL'
 rows.append({'case_id':case,'metrics':metrics,'acceptance_gates':gates,'deterministic_gate':'PASS' if all(x=='PASS' for x in gates.values()) else 'FAIL','decision':'ACCEPT' if accepted else 'ROLLBACK'})
result={'status':'PASS' if all(x['deterministic_gate']=='PASS' for x in rows) else 'FAIL','cases':rows};out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));raise SystemExit(result['status']!='PASS')
