"""Build L0 Kinematic Skeleton from sanitized URDF only."""
import hashlib,json
from pathlib import Path
import numpy as np
from kinematics import parse,canonical_q,fk,T,rpy
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';src=HERE/'inputs/sanitized_urdf/px100_sanitized.urdf';links,joints=parse(src);q=canonical_q(joints);root,world,jw=fk(links,joints,q);by_child={j['child']:j for j in joints}
chains={}
for link in links:
 c=[];x=link
 while x in by_child:c.append(by_child[x]['joint_id']);x=by_child[x]['parent']
 chains[link]=list(reversed(c))
for j in joints:
 axis=np.array(j['axis'],float);j['axis']=(axis/np.linalg.norm(axis)).tolist();j['origin_transform_parent']=T(rpy(np.array(j['origin_rpy_rad'])),np.array(j['origin_xyz_m'])).tolist();j['world_joint_transform']=jw[j['joint_id']].tolist();j['world_axis']=((jw[j['joint_id']][:3,:3]@axis)/np.linalg.norm(axis)).tolist()
out={'schema_version':'try5A_kinematic_skeleton_v1','authority':'sanitized_urdf','source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'units':{'translation':'m','angle':'rad'},'root_link':root,'links':[{'link_id':x,'world_transform_canonical':world[x].tolist(),'fk_chain':chains[x]} for x in links],'joints':joints,'canonical_joint_values':q};(HERE/'blackboard').mkdir(exist_ok=True);(HERE/'blackboard/kinematic_skeleton.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'root':root,'links':len(links),'joints':len(joints),'canonical_q':q}))
