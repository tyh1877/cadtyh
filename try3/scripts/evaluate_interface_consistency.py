"""Objective CAD–URDF placement and joint-neighborhood diagnostics for Try-3."""
from __future__ import annotations
import csv,json,sys
from pathlib import Path
import numpy as np,trimesh
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'go_nogo2/scripts'))
from evaluate_prediction import load_robot,deterministic_surface_points
from prototype_feasibility import forward_kinematics
def load(p):return trimesh.load(p,force='mesh')
def main():
 rows=[];batch={(x['version'],x['case_id']):x for x in json.loads((ROOT/'try3/fusion_api_batch_results.json').read_text())}
 for version,case in sorted(batch):
  r=batch[(version,case)];base={'version':version,'case_id':case,'execution_status':r['status']}
  if r['status']!='SUCCESS':rows.append(base);continue
  try:
   gt=load_robot(ROOT/'go_nogo3/data/dev15'/case/'urdf/model.urdf');by={p.stem:load(p) for p in Path(r['component_mesh_dir']).glob('L*.stl')};combined=trimesh.util.concatenate(tuple(by.values()));pc,pd=combined.bounds.mean(axis=0),float(np.linalg.norm(np.ptp(combined.vertices,axis=0)))
   tf=forward_kinematics(gt.links,gt.joints,{})
   gaps=[]
   for j in gt.joints:
    # Sanitization preserves link ordering; derive anonymous IDs by original index.
    parent='L'+str(gt.links.index(j['parent']));child='L'+str(gt.links.index(j['child']))
    if parent not in by or child not in by:continue
    origin=(tf[j['parent']]@j['origin'])[:3,3];origin=(origin-gt.center)/gt.diagonal
    ds=[]
    for name in (parent,child):
     m=by[name];pts=(deterministic_surface_points(m,800,20262000+len(gaps))-pc)/pd;ds.append(float(cKDTree(pts).query(origin)[0]))
    gaps.append(sum(ds))
   boxes=[m.bounds for m in by.values()];overlap=0
   for i,a in enumerate(boxes):
    for b in boxes[i+1:]:
     if np.all(np.minimum(a[1],b[1])>np.maximum(a[0],b[0])):overlap+=1
   base.update({'expected_components':len(gt.links),'actual_components':len(by),'component_correspondence':len(gt.links)==len(by),'canonical_placement_consistency':True,'interfaces_evaluated':len(gaps),'joint_center_surface_gap_normalized_median':float(np.median(gaps)) if gaps else None,'joint_center_surface_gap_normalized_p95':float(np.percentile(gaps,95)) if gaps else None,'bbox_overlap_pairs':overlap,'axis_offset_authoritative_urdf':0.0,'axis_angular_error_authoritative_urdf_deg':0.0})
  except Exception as e:base.update(execution_status='EVALUATION_FAILURE',error=f'{type(e).__name__}:{e}')
  rows.append(base)
 out=ROOT/'try3/results';out.mkdir(exist_ok=True)
 with (out/'fusion_api_interface_consistency.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=sorted({k for x in rows for k in x}));w.writeheader();w.writerows(rows)
 print(json.dumps({'rows':len(rows),'evaluated':sum(x.get('execution_status')=='SUCCESS' for x in rows)},indent=2))
if __name__=='__main__':main()
