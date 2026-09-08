"""Create canonical and single-joint limit sweep poses from frozen sanitized URDF."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];SRC=ROOT/'experiments/try5A';HERE=ROOT/'experiments/try5A_1';sys.path.insert(0,str(SRC/'scripts'));from kinematics import parse,canonical_q,fk
links,joints=parse(SRC/'inputs/sanitized_urdf/px100_sanitized.urdf');poses=[]
def add(name,q,kind,active=None):
 _,w,_=fk(links,joints,q);poses.append({'pose_id':name,'kind':kind,'active_joint':active,'joint_values':q,'world_transforms_mm':{k:(lambda m:(m.__setitem__((slice(0,3),3),m[:3,3]*1000) or m))(v.copy()).tolist() for k,v in w.items()}})
q0=canonical_q(joints);add('canonical',q0,'canonical')
for j in [x for x in joints if x['joint_id'] in ('J00','J01','J02','J03')]:
 for label,val in [('lower',j['limits']['lower']),('zero',0.0),('upper',j['limits']['upper'])]:q=canonical_q(joints);q[j['joint_id']]=val;add(f"{j['joint_id']}_{label}",q,'sweep',j['joint_id'])
(HERE/'collision_cache').mkdir(exist_ok=True);(HERE/'collision_cache/collision_poses.json').write_text(json.dumps({'links':links,'joints':joints,'poses':poses},indent=2)+'\n');print(json.dumps({'poses':len(poses)}))
