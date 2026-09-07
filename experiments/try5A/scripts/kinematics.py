"""Deterministic sanitized-URDF parser and FK utilities."""
import math,xml.etree.ElementTree as ET
import numpy as np
def vec(s,default='0 0 0'):return np.array([float(x) for x in (s or default).split()])
def rpy(r):
 a,b,c=r;Rx=np.array([[1,0,0],[0,math.cos(a),-math.sin(a)],[0,math.sin(a),math.cos(a)]]);Ry=np.array([[math.cos(b),0,math.sin(b)],[0,1,0],[-math.sin(b),0,math.cos(b)]]);Rz=np.array([[math.cos(c),-math.sin(c),0],[math.sin(c),math.cos(c),0],[0,0,1]]);return Rz@Ry@Rx
def T(R=None,p=None):m=np.eye(4);m[:3,:3]=np.eye(3) if R is None else R;m[:3,3]=np.zeros(3) if p is None else p;return m
def axis_angle(a,q):
 a=a/np.linalg.norm(a);K=np.array([[0,-a[2],a[1]],[a[2],0,-a[0]],[-a[1],a[0],0]]);return np.eye(3)+math.sin(q)*K+(1-math.cos(q))*(K@K)
def parse(path):
 root=ET.parse(path).getroot();links=[x.attrib['name'] for x in root.findall('link')];joints=[]
 for x in root.findall('joint'):
  o=x.find('origin');a=x.find('axis');l=x.find('limit');m=x.find('mimic');joints.append({'joint_id':x.attrib['name'],'joint_type':x.attrib['type'],'parent':x.find('parent').attrib['link'],'child':x.find('child').attrib['link'],'origin_xyz_m':vec(o.attrib.get('xyz') if o is not None else None).tolist(),'origin_rpy_rad':vec(o.attrib.get('rpy') if o is not None else None).tolist(),'axis':vec(a.attrib.get('xyz') if a is not None else '1 0 0').tolist(),'limits':({k:float(l.attrib[k]) for k in ('lower','upper') if k in l.attrib} if l is not None else {}),'mimic':({k:(float(m.attrib[k]) if k in ('multiplier','offset') else m.attrib[k]) for k in m.attrib} if m is not None else None)})
 return links,joints
def canonical_q(joints):
 q={}
 for j in joints:
  lim=j['limits'];q[j['joint_id']]=(lim.get('lower',0)+lim.get('upper',0))/2 if j['joint_type']=='prismatic' and not (lim.get('lower',0)<=0<=lim.get('upper',0)) else 0.0
 for j in joints:
  if j['mimic']:q[j['joint_id']]=q[j['mimic']['joint']]*j['mimic'].get('multiplier',1.0)+j['mimic'].get('offset',0.0)
 return q
def fk(links,joints,q):
 children={j['child'] for j in joints};root=next(x for x in links if x not in children);world={root:np.eye(4)};joint_world={};pending=joints[:]
 while pending:
  progress=False
  for j in pending[:]:
   if j['parent'] not in world:continue
   O=T(rpy(np.array(j['origin_rpy_rad'])),np.array(j['origin_xyz_m']));J=world[j['parent']]@O;joint_world[j['joint_id']]=J;axis=np.array(j['axis'],float);typ=j['joint_type'];M=T(axis_angle(axis,q[j['joint_id']])) if typ in ('revolute','continuous') else (T(p=axis/np.linalg.norm(axis)*q[j['joint_id']]) if typ=='prismatic' else np.eye(4));world[j['child']]=J@M;pending.remove(j);progress=True
  if not progress:raise ValueError('URDF graph disconnected or cyclic')
 return root,world,joint_world
