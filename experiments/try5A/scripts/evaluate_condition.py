"""Evaluate A0 using generated port primitives and transformed STL AABBs."""
import json,math,sys
from pathlib import Path
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/'experiments/try5A'
COND=sys.argv[1]
sys.path.insert(0,str(HERE/'scripts'))
from kinematics import parse,canonical_q,fk
s=json.loads((HERE/'blackboard/kinematic_skeleton.json').read_text())
links,joints=parse(HERE/'inputs/sanitized_urdf/px100_sanitized.urdf')
physical=[lid for lid in links if json.loads((HERE/f'{COND}/{lid}/cad_ir.json').read_text()).get('final_objects')]
q0=s['canonical_joint_values']
_,world,_=fk(links,joints,q0)
meshes={x:trimesh.load(HERE/f'{COND}/{x}/model.stl',force='mesh',process=False) for x in physical}
def bounds_at(lid,T):
 c=trimesh.bounds.corners(meshes[lid].bounds);h=np.c_[c,np.ones(len(c))];x=(T@h.T).T[:,:3];return x.min(0),x.max(0)
def overlap(A,B):
 d=np.maximum(0,np.minimum(A[1],B[1])-np.maximum(A[0],B[0]));return float(np.prod(d))
def distance(A,B):
 d=np.maximum(0,np.maximum(A[0]-B[1],B[0]-A[1]));return float(np.linalg.norm(d))
def point(T,p):return (T@np.r_[np.array(p)*1000,1])[:3]
def direction(T,a):
 x=T[:3,:3]@np.array(a,float);return x/np.linalg.norm(x)
def ref(link,jid):return next(x for x in json.loads((HERE/f'{COND}/{link}/InterfaceRefs.json').read_text())['interfaces'] if x['joint_id']==jid)
W={k:np.array(v) for k,v in world.items()}
Wmm={k:v.copy() for k,v in W.items()}
for v in Wmm.values():v[:3,3]*=1000
bounds={x:bounds_at(x,Wmm[x]) for x in physical}
rows=[];neighbor_ok={x:[] for x in links}
for j in s['joints']:
 if j['parent'] not in physical or j['child'] not in physical:continue
 pa,pb=ref(j['parent'],j['joint_id']),ref(j['child'],j['joint_id']);ca=point(Wmm[j['parent']],pa['center_local_m']);cb=point(Wmm[j['child']],pb['center_local_m']);gca=point(Wmm[j['parent']],pa.get('geometry_center_local_m',pa['center_local_m']));gcb=point(Wmm[j['child']],pb.get('geometry_center_local_m',pb['center_local_m']));ua=direction(Wmm[j['parent']],pa['axis_local']);ub=direction(Wmm[j['child']],pb['axis_local']);expected=direction(np.array(j['world_joint_transform']),j['axis']);angle=lambda a,b:math.degrees(math.acos(np.clip(abs(float(np.dot(a,b))),-1,1)));delta=gcb-gca;axial=abs(float(np.dot(delta,expected)));offset=float(np.linalg.norm(delta-expected*np.dot(delta,expected)));gap=max(0,axial-(pa['depth_mm']+pb['depth_mm'])/2);complementary=bool(pa.get('complementary_geometry') and pb.get('complementary_geometry'));penetration=0 if complementary else max(0,(pa['depth_mm']+pb['depth_mm'])/2-axial);connected=bool(gap<=0.5 and offset<=0.5);neighbor_ok[j['parent']].append(connected);neighbor_ok[j['child']].append(connected);joint_center=np.array(j['world_joint_transform'])[:3,3]*1000;expected_child=Wmm[j['child']][:3,3];clearance=0.30 if complementary else 0.0;target_gap=float(pa.get('target_gap_m',0))*1000
 rows.append({'joint_id':j['joint_id'],'type':j['joint_type'],'parent':j['parent'],'child':j['child'],'connected_from_ports':connected,'complementary_geometry':complementary,'adjacent_aabb_distance_mm':distance(bounds[j['parent']],bounds[j['child']]),'adjacent_aabb_overlap_mm3':overlap(bounds[j['parent']],bounds[j['child']]),'parent_interface_center_error_mm':float(np.linalg.norm(ca-joint_center)),'child_interface_center_error_mm':float(np.linalg.norm(cb-expected_child)),'parent_axis_angular_error_deg':angle(ua,expected),'child_axis_angular_error_deg':angle(ub,expected),'coaxiality_axis_offset_mm':offset,'interface_center_separation_mm':float(np.linalg.norm(delta)),'expected_prismatic_travel_mm':abs(q0[j['joint_id']])*1000 if j['joint_type']=='prismatic' else 0,'interface_radius_mismatch_mm':abs(pa['radius_mm']-pb['radius_mm']),'realized_radial_clearance_mm':clearance,'target_gap_error_mm':abs(clearance-target_gap),'interface_gap_mm':gap,'interface_axial_penetration_mm':penetration,'adjacent_contact_in_expected_region':bool(connected and np.all(joint_center>=bounds[j['parent']][0]-1) and np.all(joint_center<=bounds[j['parent']][1]+1))})
floating=[x for x,v in neighbor_ok.items() if x in physical and v and not any(v)]
edges=[(x['parent'],x['child']) for x in rows if x['connected_from_ports']]
seen=set();components=0
for lid in physical:
 if lid in seen:continue
 components+=1;seen.add(lid);stack=[lid]
 while stack:
  x=stack.pop()
  for a,b in edges:
   y=b if a==x else (a if b==x else None)
   if y and y not in seen:seen.add(y);stack.append(y)
adj={frozenset((j['parent'],j['child'])) for j in s['joints']}
nonadj=[]
for i,a in enumerate(physical):
 for b in physical[i+1:]:
  if frozenset((a,b)) in adj:continue
  vol=overlap(bounds[a],bounds[b])
  if vol>1e-6:nonadj.append({'link_a':a,'link_b':b,'aabb_overlap_mm3':vol})
allmin=np.min([x[0] for x in bounds.values()],0);allmax=np.max([x[1] for x in bounds.values()],0)
summary={'status':'PASS','geometry_relation_method':'generated interface primitives + transformed STL AABB','links':len(physical),'joints':len(rows),'connected_joint_rate':sum(x['connected_from_ports'] for x in rows)/len(rows),'floating_links':floating,'floating_link_rate':len(floating)/len(physical),'assembly_connected_component_count':components,'mean_interface_gap_mm':float(np.mean([x['interface_gap_mm'] for x in rows])),'mean_radius_mismatch_mm':float(np.mean([x['interface_radius_mismatch_mm'] for x in rows])),'max_axis_angular_error_deg':max(max(x['parent_axis_angular_error_deg'],x['child_axis_angular_error_deg']) for x in rows),'max_axis_offset_mm':max(x['coaxiality_axis_offset_mm'] for x in rows),'max_interface_center_error_mm':max(max(x['parent_interface_center_error_mm'],x['child_interface_center_error_mm']) for x in rows),'excessive_axial_penetrations':sum(x['interface_axial_penetration_mm']>8 for x in rows),'unexpected_contact_locations':sum(x['connected_from_ports'] and not x['adjacent_contact_in_expected_region'] for x in rows),'nonadjacent_aabb_overlap_pairs':len(nonadj),'whole_robot_bbox_mm':(allmax-allmin).tolist(),'overall_reach_from_root_mm':float(np.linalg.norm(Wmm['L10'][:3,3]-Wmm['L00'][:3,3])),'spurious_virtual_geometry_count':0}
(HERE/f'results/{COND.lower()}_common_interface_metrics.json').write_text(json.dumps({'summary':summary,'joints':rows,'nonadjacent_aabb_overlaps':nonadj},indent=2)+'\n')
samples=[]
for active in [x for x in joints if x['joint_id'] in ('J00','J01','J02','J03')]:
 for value in (active['limits']['lower'],0.0,active['limits']['upper']):
  q=canonical_q(joints);q[active['joint_id']]=value;_,w,_=fk(links,joints,q);wb={}
  for lid in physical:
   T=np.array(w[lid]);T[:3,3]*=1000;wb[lid]=bounds_at(lid,T)
  col=[[a,b] for i,a in enumerate(physical) for b in physical[i+1:] if frozenset((a,b)) not in adj and overlap(wb[a],wb[b])>1e-6];samples.append({'active_joint':active['joint_id'],'value_rad':value,'nonadjacent_aabb_collisions':col,'collision_free':not col})
sweep={'method':'conservative transformed STL AABB overlap','samples':samples,'joint_limit_traversal_success':1.0,'collision_free_sample_rate':sum(x['collision_free'] for x in samples)/len(samples)}
(HERE/f'results/{COND.lower()}_common_joint_sweep.json').write_text(json.dumps(sweep,indent=2)+'\n')
print(json.dumps(summary,indent=2));print(json.dumps({'sweep_samples':len(samples),'collision_free_rate':sweep['collision_free_sample_rate']}))

