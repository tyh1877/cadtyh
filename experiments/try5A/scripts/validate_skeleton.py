"""Independent L0 frame/FK smoke checks and deterministic joint samples."""
import json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';sys.path.insert(0,str(HERE/'scripts'));from kinematics import parse,canonical_q,fk,T,rpy
src=HERE/'inputs/sanitized_urdf/px100_sanitized.urdf';saved=json.loads((HERE/'blackboard/kinematic_skeleton.json').read_text());links,joints=parse(src);q0=canonical_q(joints);root,w0,jw=fk(links,joints,q0);errors=[];rot_errors=[];relative_errors=[]
for x in saved['links']:
 m=np.array(x['world_transform_canonical']);rot_errors.append(float(np.max(np.abs(m[:3,:3].T@m[:3,:3]-np.eye(3)))));errors += [x['link_id']+':rotation'] if not np.allclose(m[:3,:3].T@m[:3,:3],np.eye(3),atol=1e-9) or abs(np.linalg.det(m[:3,:3])-1)>1e-9 else [];errors += [x['link_id']+':saved_fk'] if not np.allclose(m,w0[x['link_id']],atol=1e-12) else []
for j in joints:
 relative=np.linalg.inv(w0[j['parent']])@jw[j['joint_id']];expected=T(rpy(np.array(j['origin_rpy_rad'])),np.array(j['origin_xyz_m']));relative_errors.append(float(np.max(np.abs(relative-expected))));errors += [j['joint_id']+':relative'] if not np.allclose(relative,expected,atol=1e-12) else []
samples=[]
for frac in (0,.25,.5,.75,1):
 q={}
 for j in joints:
  lim=j['limits'];q[j['joint_id']]=(lim['lower']+(lim['upper']-lim['lower'])*frac) if 'lower'in lim and 'upper'in lim else 0.0
 for j in joints:
  if j['mimic']:q[j['joint_id']]=q[j['mimic']['joint']]*j['mimic'].get('multiplier',1)+j['mimic'].get('offset',0)
 _,w,_=fk(links,joints,q);samples.append({'fraction':frac,'joint_values':q,'end_frame':w['L11'].tolist(),'all_finite':all(np.isfinite(m).all() for m in w.values())})
out={'status':'PASS' if not errors and all(x['all_finite'] for x in samples) else 'FAIL','errors':errors,'tree_root':root,'link_count':len(links),'joint_count':len(joints),'max_rotation_orthonormal_error':max(rot_errors),'max_parent_joint_relative_error':max(relative_errors),'canonical_end_frame':w0['L11'].tolist(),'sample_count':len(samples),'samples':samples};(HERE/'results').mkdir(exist_ok=True);(HERE/'results/fk_frame_validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'status':out['status'],'errors':errors,'samples':5,'max_rotation_error':max(rot_errors),'max_relative_error':max(relative_errors)}));raise SystemExit(out['status']!='PASS')
