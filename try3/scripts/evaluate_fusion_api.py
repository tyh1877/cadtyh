"""Deterministic geometry diagnostics for Try-3 FusionAPIBackend artifacts."""
from __future__ import annotations
import csv,json,sys
from pathlib import Path
import numpy as np,trimesh
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'go_nogo2/scripts'))
from evaluate_prediction import deterministic_surface_points,load_robot,point_metrics,voxel_iou
from prototype_feasibility import forward_kinematics

def mesh(path):
 x=trimesh.load(path,force='mesh');return x if isinstance(x,trimesh.Trimesh) else trimesh.util.concatenate(tuple(x.geometry.values()))
def norm(m,center,diagonal):
 x=m.copy();x.vertices=(x.vertices-center)/diagonal;return x
def main():
 out=ROOT/'try3/results';out.mkdir(exist_ok=True);cases=[];links=[];local=[]
 batch={ (x['version'],x['case_id']):x for x in json.loads((ROOT/'try3/fusion_api_batch_results.json').read_text())}
 for version in ('V1','V2'):
  for case in [r['case_id'] for r in csv.DictReader((ROOT/'try3/tryset5_v1.csv').open(encoding='utf-8-sig'))]:
   record=batch[(version,case)];row={'version':version,'case_id':case,'execution_status':record['status']}
   if record['status']!='SUCCESS':cases.append(row);continue
   try:
    gt=load_robot(ROOT/'go_nogo3/data/dev15'/case/'urdf/model.urdf');pred_files=sorted(Path(record['component_mesh_dir']).glob('L*.stl'));pred_by={p.stem:mesh(p) for p in pred_files};combined=trimesh.util.concatenate(tuple(pred_by.values()))
    pm=norm(combined,combined.bounds.mean(axis=0),float(np.linalg.norm(np.ptp(combined.vertices,axis=0))));gm=norm(gt.combined,gt.center,gt.diagonal)
    gp=deterministic_surface_points(gm,3000,20260830);pp=deterministic_surface_points(pm,3000,20260831)
    matrix,_,_=trimesh.registration.icp(pp,gp,max_iterations=50,reflection=False,scale=False);pm.apply_transform(matrix);pp=deterministic_surface_points(pm,3000,20260831)
    row.update(point_metrics(gp,pp));row['voxel_iou']=voxel_iou(gm,pm);row['component_meshes']=len(pred_by);row['expected_links']=len(gt.links);row['canonical_component_correspondence']=len(pred_by)==len(gt.links)
    # Sanitization preserves link order while deliberately renaming links L0…;
    # use this pre-registered bijection rather than original GT display names.
    for i,name in enumerate(gt.links):
     pred_name='L'+str(i)
     if pred_name not in pred_by or name not in gt.world_meshes:continue
     a=norm(gt.world_meshes[name],gt.center,gt.diagonal);b=norm(pred_by[pred_name],combined.bounds.mean(axis=0),float(np.linalg.norm(np.ptp(combined.vertices,axis=0))));b.apply_transform(matrix);aa=deterministic_surface_points(a,600,20260900+i);bb=deterministic_surface_points(b,600,20261000+i);m=point_metrics(aa,bb);links.append({'version':version,'case_id':case,'link_id':pred_name,**m,'voxel_iou':voxel_iou(a,b)})
    tf=forward_kinematics(gt.links,gt.joints,{})
    for i,j in enumerate(gt.joints):
     origin=(tf[j['parent']]@j['origin'])[:3,3];origin=(origin-gt.center)/gt.diagonal;r=.10
     aa=gp[np.linalg.norm(gp-origin,axis=1)<=r];bb=pp[np.linalg.norm(pp-origin,axis=1)<=r]
     local.append({'version':version,'case_id':case,'joint_id':j['name'],'sampled_gt':len(aa),'sampled_pred':len(bb),'local_chamfer':point_metrics(aa,bb)['chamfer'] if len(aa) and len(bb) else None})
   except Exception as e:row.update(execution_status='EVALUATION_FAILURE',error=f'{type(e).__name__}: {e}')
   cases.append(row)
 for name,data in [('fusion_api_case_geometry.csv',cases),('fusion_api_per_link_geometry.csv',links),('fusion_api_joint_local_geometry.csv',local)]:
  keys=sorted({k for x in data for k in x}) if data else ['status']
  with (out/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(data)
 print(json.dumps({'cases':len(cases),'evaluated':sum(x.get('execution_status')=='SUCCESS' for x in cases),'per_link':len(links),'joint_local':len(local)},indent=2))
if __name__=='__main__':main()
