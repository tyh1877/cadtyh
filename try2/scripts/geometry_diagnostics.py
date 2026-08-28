"""Per-link and fixed-radius joint-neighborhood geometry diagnostics for Try-2."""
from __future__ import annotations
import csv,sys
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'go_nogo2/scripts'),str(ROOT/'go_nogo1/scripts')]
from evaluate_prediction import deterministic_surface_points,load_robot
from prototype_feasibility import forward_kinematics
def chamfer(a,b):return float((np.mean(cKDTree(b).query(a)[0]**2)+np.mean(cKDTree(a).query(b)[0]**2))/2)
def main():
 out=ROOT/'try2/results';out.mkdir(exist_ok=True);links=[];joints=[]
 for c in 'ABCD':
  for run in sorted((ROOT/'try2/runs'/c).glob('dev_arm-*')):
   if not (run/'urdf/model.urdf').is_file():continue
   gt,pred=load_robot(ROOT/'go_nogo3/data/dev15'/run.name/'urdf/model.urdf'),load_robot(run/'urdf/model.urdf')
   gt_names=gt.links;pred_names=pred.links
   for i,name in enumerate(pred_names):
    if i>=len(gt_names) or name not in pred.world_meshes:continue
    a=deterministic_surface_points(gt.world_meshes[gt_names[i]],500,20260828+i);b=deterministic_surface_points(pred.world_meshes[name],500,20260928+i);links.append({'condition':c,'case_id':run.name,'gt_link':gt_names[i],'pred_link':name,'chamfer_mm2':chamfer(a,b)})
   tf=forward_kinematics(gt.links,gt.joints,{})
   for i,j in enumerate(gt.joints):
    origin=(tf[j['parent']]@j['origin'])[:3,3];r=.10*gt.diagonal
    a=deterministic_surface_points(gt.combined,3000,20261028+i);b=deterministic_surface_points(pred.combined,3000,20261128+i);a=a[np.linalg.norm(a-origin,axis=1)<=r];b=b[np.linalg.norm(b-origin,axis=1)<=r]
    joints.append({'condition':c,'case_id':run.name,'joint_index':i,'radius_m':r,'local_chamfer_mm2':chamfer(a,b) if len(a) and len(b) else None})
 for name,data in [('per_link_geometry.csv',links),('joint_local_geometry.csv',joints)]:
  with (out/name).open('w',newline='') as h:w=csv.DictWriter(h,fieldnames=list(data[0]) if data else ['condition']);w.writeheader();w.writerows(data)
if __name__=='__main__':main()
