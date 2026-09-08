"""Evaluator-only URDF visual-mesh comparison for A0/A1/A2 coarse geometry."""
import csv,glob,hashlib,json,math,sys,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np,trimesh
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';sys.path.insert(0,str(HERE/'scripts'));from kinematics import rpy
SRC=ROOT/'go_nogo1/sources/urdf_files_dataset/urdf_files/robotics-toolbox/xacro_generated/interbotix_descriptions/urdf/px100.urdf';mapping=json.loads((HERE/'protocol/source_id_mapping.json').read_text())['links'];stable={v:k for k,v in mapping.items()};s=json.loads((HERE/'blackboard/kinematic_skeleton.json').read_text());world={x['link_id']:np.array(x['world_transform_canonical']) for x in s['links']};meshroot=SRC.parent.parent/'meshes/meshes_px100';xml=ET.parse(SRC).getroot();gt={};provenance=[]
def T(R,p):m=np.eye(4);m[:3,:3]=R;m[:3,3]=p;return m
for lid,name in stable.items():
 x=next(y for y in xml.findall('link') if y.attrib['name']==name);v=x.find('visual')
 if v is None:continue
 uri=v.find('geometry/mesh').attrib['filename'];path=meshroot/Path(uri).name;o=v.find('origin');xyz=np.array([float(z) for z in o.attrib.get('xyz','0 0 0').split()])*1000;rp=np.array([float(z) for z in o.attrib.get('rpy','0 0 0').split()]);m=trimesh.load(path,force='mesh',process=False);m.apply_transform(T(rpy(rp),xyz));gt[lid]=m;provenance.append({'link_id':lid,'source_mesh':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'evaluator_only':True})
def sample(m,n,seed):state=np.random.get_state();np.random.seed(seed);p,_=trimesh.sample.sample_surface(m,n);np.random.set_state(state);return p
def metrics(a,b,seed):
 n=10000;pa=sample(a,n,seed);pb=sample(b,n,seed+1);da=cKDTree(pb).query(pa)[0];db=cKDTree(pa).query(pb)[0];diag=float(np.linalg.norm(a.bounds[1]-a.bounds[0]));pitch=diag/48;origin=np.minimum(a.bounds[0],b.bounds[0])-pitch
 def vox(m):return {tuple(x) for x in np.rint((m.voxelized(pitch).fill().points-origin)/pitch).astype(int)}
 va,vb=vox(a),vox(b);iou=len(va&vb)/len(va|vb);sil=[]
 for axes in ((0,1),(1,2),(0,2)):
  aa={(x[axes[0]],x[axes[1]]) for x in va};bb={(x[axes[0]],x[axes[1]]) for x in vb};sil.append(len(aa&bb)/len(aa|bb))
 return {'voxel_iou':iou,'normalized_chamfer':float((da.mean()+db.mean())/2/diag),'normalized_hd95':float(max(np.percentile(da,95),np.percentile(db,95))/diag),'silhouette_iou_mean':float(np.mean(sil)),'bbox_error_mm':float(np.linalg.norm((b.bounds[1]-b.bounds[0])-(a.bounds[1]-a.bounds[0])))}
rows=[];whole={c:[] for c in ('A0','A1','A2')};gtwhole=[]
for k,(lid,g) in enumerate(sorted(gt.items())):
 G=g.copy();Gw=world[lid].copy();Gw[:3,3]*=1000;G.apply_transform(Gw);gtwhole.append(G)
 for ci,c in enumerate(('A0','A1','A2')):
  m=trimesh.load(HERE/f'{c}/{lid}/model.stl',force='mesh',process=False);rows.append({'level':'link','link_id':lid,'condition':c,**metrics(g,m,5100+k*10+ci)});mw=m.copy();mw.apply_transform(Gw);whole[c].append(mw)
GT=trimesh.util.concatenate(gtwhole)
for ci,c in enumerate(('A0','A1','A2')):rows.append({'level':'whole_robot','link_id':'ALL','condition':c,**metrics(GT,trimesh.util.concatenate(whole[c]),5900+ci)})
with (HERE/'results/coarse_geometry_metrics.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(HERE/'results/evaluator_gt_mesh_manifest.json').write_text(json.dumps({'source_urdf_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'meshes':provenance,'excluded_virtual_links':sorted(set(stable)-set(gt))},indent=2)+'\n');print(json.dumps({'evaluable_links':len(gt),'rows':len(rows)}))

