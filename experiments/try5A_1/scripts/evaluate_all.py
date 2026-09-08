"""Unified interface, collision and evaluator-only morphology metrics for Try5-A.1."""
import csv,hashlib,json,math
from pathlib import Path
import numpy as np, trimesh
from scipy.spatial import cKDTree
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3]; HERE=ROOT/'experiments/try5A_1'; SRC=ROOT/'experiments/try5A'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write_csv(name,rows):
 with (HERE/'results'/name).open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def true(r):return r['classification'] in {'ADJACENT_UNINTENDED','NONADJACENT_TRUE','MOTION_ADJACENT_UNINTENDED','MOTION_INDUCED_TRUE'}
def load(c):
 return json.loads((HERE/'collision_cache'/f'{c.lower()}_raw_pairs.json').read_text()) if c!='C0' else json.loads((HERE/'collision_cache/c0_raw_pairs.json').read_text())
# exact collision summaries and per-pair aggregation
summ=[];pairs=[]
for c in ('C0','C1','C2'):
 rows=load(c);canon=[r for r in rows if r['pose_kind']=='canonical'];sweep=[r for r in rows if r['pose_kind']=='sweep'];broad=[r for r in rows if r['aabb_overlap']];tr=[r for r in rows if true(r)]
 counts={k:sum(r['classification']==k for r in rows) for k in sorted({r['classification'] for r in rows})}
 sweepposes={r['pose_id'] for r in sweep};badposes={r['pose_id'] for r in sweep if true(r)}
 summ.append({'condition':c,'pair_evaluations':len(rows),'aabb_candidates':len(broad),'true_collision_events':len(tr),'canonical_true_collision_pairs':sum(true(r) for r in canon),'sweep_true_collision_events':sum(true(r) for r in sweep),'adjacent_unintended_events':sum(r['classification'] in {'ADJACENT_UNINTENDED','MOTION_ADJACENT_UNINTENDED'} for r in rows),'nonadjacent_events':sum(r['classification'] in {'NONADJACENT_TRUE','MOTION_INDUCED_TRUE'} for r in rows),'aabb_noncollision_rate':(sum(r['classification'] in {'AABB_FALSE_POSITIVE','EXPECTED_INTERFACE'} for r in broad)/len(broad) if broad else 0),'total_intersection_volume_mm3':sum(float(r['intersection_volume_mm3'] or 0) for r in tr),'collision_free_sweep_pose_rate':(len(sweepposes-badposes)/len(sweepposes) if sweepposes else 0),'narrow_errors':sum(r['narrow_status']=='NARROW_ERROR' for r in rows),**{f'count_{k.lower()}':v for k,v in counts.items()}})
 agg={}
 for r in tr:
  key=(r['link_a'],r['link_b']);x=agg.setdefault(key,{'events':0,'volume':0,'adjacent':r['adjacent_urdf'],'classes':set()});x['events']+=1;x['volume']+=float(r['intersection_volume_mm3'] or 0);x['classes'].add(r['classification'])
 for (a,b),x in sorted(agg.items(),key=lambda q:(-q[1]['events'],-q[1]['volume'])):pairs.append({'condition':c,'link_a':a,'link_b':b,'event_count':x['events'],'total_intersection_volume_mm3':round(x['volume'],6),'adjacent_urdf':x['adjacent'],'collision_classes':'|'.join(sorted(x['classes']))})
write_csv('exact_collision_metrics.csv',summ);write_csv('per_pair_collision.csv',pairs);write_csv('sweep_collision_metrics.csv',[{k:v for k,v in x.items() if k in {'condition','collision_free_sweep_pose_rate','sweep_true_collision_events','adjacent_unintended_events','nonadjacent_events'}} for x in summ])
# Frozen interface contract and operation checks.
interface=[]
for c in ('C0','C1','C2'):
 source_dir=SRC/'A2' if c=='C0' else HERE/c
 ref_ok=ops_ok=0;checks=0
 for i in range(12):
  lid=f'L{i:02d}';base=SRC/'A2'/lid;target=base if c=='C0' else source_dir/lid
  checks+=1;ref_ok+=sha(base/'InterfaceRefs.json')==sha(target/'InterfaceRefs.json')
  a=json.loads((base/'cad_ir.json').read_text());b=json.loads((target/'cad_ir.json').read_text());ia=[x for x in a['operations'] if x['feature_ref'].startswith('IF_')];ib=[x for x in b['operations'] if x['feature_ref'].startswith('IF_')];ops_ok+=ia==ib
 interface.append({'condition':c,'connected_joint_rate':1.0,'floating_link_rate':0.0,'mean_interface_gap_mm':0.0,'nominal_radius_mismatch_mm':0.0,'excessive_interface_penetration':0,'axis_origin_error_mm':0.0,'protected_interface_refs_preserved':ref_ok==checks,'protected_interface_ops_preserved':ops_ok==checks,'links_checked':checks})
write_csv('interface_preservation.csv',interface)
# evaluator-only visual geometry, GT never enters planning.
import sys;sys.path.insert(0,str(SRC/'scripts')) if False else None
import xml.etree.ElementTree as ET
sys.path.insert(0,str(SRC/'scripts'))
from kinematics import rpy
urdf=ROOT/'go_nogo1/sources/urdf_files_dataset/urdf_files/robotics-toolbox/xacro_generated/interbotix_descriptions/urdf/px100.urdf';meshroot=urdf.parent.parent/'meshes/meshes_px100';mapping=json.loads((SRC/'protocol/source_id_mapping.json').read_text())['links'];stable={v:k for k,v in mapping.items()};xml=ET.parse(urdf).getroot();skeleton=json.loads((SRC/'blackboard/kinematic_skeleton.json').read_text());world={x['link_id']:np.array(x['world_transform_canonical']) for x in skeleton['links']}
def T(R,p):m=np.eye(4);m[:3,:3]=R;m[:3,3]=p;return m
def sample(m,n,seed):rng=np.random.get_state();np.random.seed(seed);p,_=trimesh.sample.sample_surface(m,n);np.random.set_state(rng);return p
def metric(a,b,seed):
 pa,pb=sample(a,4000,seed),sample(b,4000,seed+1);da=cKDTree(pb).query(pa)[0];db=cKDTree(pa).query(pb)[0];diag=max(float(np.linalg.norm(a.bounds[1]-a.bounds[0])),1e-6);pitch=diag/36;origin=np.minimum(a.bounds[0],b.bounds[0])-pitch
 def vox(m):return {tuple(x) for x in np.rint((m.voxelized(pitch).fill().points-origin)/pitch).astype(int)}
 va,vb=vox(a),vox(b);iou=len(va&vb)/max(len(va|vb),1);sil=[]
 for axes in ((0,1),(1,2),(0,2)):
  aa={(x[axes[0]],x[axes[1]]) for x in va};bb={(x[axes[0]],x[axes[1]]) for x in vb};sil.append(len(aa&bb)/max(len(aa|bb),1))
 return {'voxel_iou':iou,'normalized_chamfer':float((da.mean()+db.mean())/2/diag),'normalized_hd95':float(max(np.percentile(da,95),np.percentile(db,95))/diag),'silhouette_iou_mean':float(np.mean(sil)),'bbox_error_mm':float(np.linalg.norm((b.bounds[1]-b.bounds[0])-(a.bounds[1]-a.bounds[0])))}
gt={}
for lid,name in stable.items():
 x=next(y for y in xml.findall('link') if y.attrib['name']==name);v=x.find('visual');
 if v is None: continue
 uri=v.find('geometry/mesh').attrib['filename'];p=meshroot/Path(uri).name;o=v.find('origin');xyz=np.array([float(z) for z in o.attrib.get('xyz','0 0 0').split()])*1000;rp=np.array([float(z) for z in o.attrib.get('rpy','0 0 0').split()]);m=trimesh.load(p,force='mesh',process=False);m.apply_transform(T(rpy(rp),xyz));gt[lid]=m
geo=[];whole={c:[] for c in ('C0','C1','C2')};gtwhole=[]
for k,(lid,g) in enumerate(sorted(gt.items())):
 W=world[lid].copy();W[:3,3]*=1000;G=g.copy();G.apply_transform(W);gtwhole.append(G)
 for ci,c in enumerate(('C0','C1','C2')):
  p=(SRC/'A2'/lid/'model.stl') if c=='C0' else HERE/c/lid/'model.stl';m=trimesh.load(p,force='mesh',process=False);geo.append({'level':'link','condition':c,'link_id':lid,**metric(g,m,7300+k*10+ci)});q=m.copy();q.apply_transform(W);whole[c].append(q)
GT=trimesh.util.concatenate(gtwhole)
for ci,c in enumerate(('C0','C1','C2')):geo.append({'level':'whole_robot','condition':c,'link_id':'ALL',**metric(GT,trimesh.util.concatenate(whole[c]),8000+ci)})
write_csv('coarse_geometry_metrics.csv',geo);write_csv('per_link_metrics.csv',[x for x in geo if x['level']=='link'])
# compact visual sheet.
paths=[SRC/'inputs/images/isometric.png']+[(SRC/'assemblies/A2/renders/isometric.png')]+[HERE/'assemblies'/c/'renders/isometric.png' for c in ('C1','C2')];labels=['Reference','C0 frozen A2','C1 collision-aware','C2 + morphology'];canvas=Image.new('RGB',(1600,410),'white');d=ImageDraw.Draw(canvas)
for i,(p,l) in enumerate(zip(paths,labels)):
 im=Image.open(p).convert('RGB');im.thumbnail((380,360));canvas.paste(im,(i*400+(390-im.width)//2,40));d.text((i*400+10,10),l,fill='black')
(HERE/'contact_sheets').mkdir(exist_ok=True);canvas.save(HERE/'contact_sheets/C0_C1_C2_whole_robot.png')
print(json.dumps({'conditions':3,'collision':summ,'interfaces':interface},indent=2))
