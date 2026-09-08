"""Evaluator-only whole-robot geometry metrics for D0_physicalized and accepted D1."""
import json,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np,trimesh
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';T=HERE/'try5A_2'
import sys;sys.path.insert(0,str(HERE/'scripts'));from kinematics import rpy
urdf=ROOT/'go_nogo1/sources/urdf_files_dataset/urdf_files/robotics-toolbox/xacro_generated/interbotix_descriptions/urdf/px100.urdf';meshroot=urdf.parent.parent/'meshes/meshes_px100';mapping=json.loads((HERE/'protocol/source_id_mapping.json').read_text())['links'];stable={v:k for k,v in mapping.items()};sk=json.loads((HERE/'blackboard/kinematic_skeleton.json').read_text());world={x['link_id']:np.array(x['world_transform_canonical']) for x in sk['links']};xml=ET.parse(urdf).getroot()
def tf(R,p):m=np.eye(4);m[:3,:3]=R;m[:3,3]=p;return m
g=[]
for lid,name in stable.items():
 node=next(x for x in xml.findall('link') if x.attrib['name']==name);v=node.find('visual')
 if v is None:continue
 path=meshroot/Path(v.find('geometry/mesh').attrib['filename']).name;o=v.find('origin');xyz=np.array([float(x) for x in o.attrib.get('xyz','0 0 0').split()])*1000;rp=np.array([float(x) for x in o.attrib.get('rpy','0 0 0').split()]);m=trimesh.load(path,force='mesh',process=False);m.apply_transform(tf(rpy(rp),xyz));W=world[lid].copy();W[:3,3]*=1000;m.apply_transform(W);g.append(m)
GT=trimesh.util.concatenate(g)
def metric(p,seed):
 m=trimesh.load(p,force='mesh',process=False);np.random.seed(seed);a,_=trimesh.sample.sample_surface(GT,5000);np.random.seed(seed+1);b,_=trimesh.sample.sample_surface(m,5000);da=cKDTree(b).query(a)[0];db=cKDTree(a).query(b)[0];diag=np.linalg.norm(GT.bounds[1]-GT.bounds[0]);pitch=diag/40;origin=np.minimum(GT.bounds[0],m.bounds[0])-pitch
 def vox(q):return {tuple(x) for x in np.rint((q.voxelized(pitch).fill().points-origin)/pitch).astype(int)}
 x,y=vox(GT),vox(m);iou=len(x&y)/max(1,len(x|y));sil=[]
 for axes in ((0,1),(1,2),(0,2)):
  q={(z[axes[0]],z[axes[1]]) for z in x};w={(z[axes[0]],z[axes[1]]) for z in y};sil.append(len(q&w)/max(1,len(q|w)))
 return {'whole_robot_iou':iou,'whole_silhouette_iou':float(np.mean(sil)),'normalized_chamfer':float((da.mean()+db.mean())/2/diag),'normalized_hd95':float(max(np.percentile(da,95),np.percentile(db,95))/diag),'bbox_error_mm':float(np.linalg.norm((m.bounds[1]-m.bounds[0])-(GT.bounds[1]-GT.bounds[0])))}
rows=[]
for c,p in [('D0_physicalized',T/'D0_physicalized/assembly/assembled_robot.stl'),('D1_final',T/'D1/round_3/assembly/assembled_robot.stl')]:rows.append({'condition':c,**metric(p,9100+len(rows))})
import csv
with (T/'results/geometry_metrics.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
print(json.dumps(rows,indent=2))
