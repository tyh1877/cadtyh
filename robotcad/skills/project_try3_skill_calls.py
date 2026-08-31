"""Project frozen Try-3 plans into backend-agnostic RobotCAD SkillCalls."""
from __future__ import annotations
import argparse,json
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def call(n,skill,target,parameters,agent):return {'call_id':n,'skill':skill,'version':'v1','target_component':target,'parameters':parameters,'calling_agent':agent}
def mat(rpy,xyz):
 r,p,y=rpy;cr,sr=math.cos(r),math.sin(r);cp,sp=math.cos(p),math.sin(p);cy,sy=math.cos(y),math.sin(y)
 return [[cy*cp,cy*sp*sr-sy*cr,cy*sp*cr+sy*sr,xyz[0]/10],[sy*cp,sy*sp*sr+cy*cr,sy*sp*cr-cy*sr,xyz[1]/10],[-sp,cp*sr,cp*cr,xyz[2]/10],[0,0,0,1]]
def mul(a,b):return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
def world_frames(bp):
 links=bp['links'];world={links[0]['name']:[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]};pending=list(bp['joints'])
 while pending:
  rest=[]
  for j in pending:
   if j['parent'] in world:world[j['child']]=mul(world[j['parent']],mat(j['origin_rpy'],j['origin_xyz']))
   else:rest.append(j)
  if len(rest)==len(pending):raise RuntimeError('disconnected URDF skeleton')
  pending=rest
 return world
def envelope(primitives):
 # Retained for feature-only secondary skills. The primary geometry call below
 # carries every explicit primitive into the backend.
 lo=[float('inf')]*3;hi=[float('-inf')]*3
 for p in primitives:
  c=p.get('center',[0,0,0]);kind=p['type']
  if kind=='box':e=[x/2 for x in p['size']]
  elif kind=='sphere':e=[p['radius']]*3
  elif kind=='cylinder':e=[max(p['radius'],p['height']/2)]*3
  else:e=[max(p['bottom_radius'],p['top_radius'],p['height']/2)]*3
  for i in range(3):lo[i]=min(lo[i],c[i]-e[i]);hi[i]=max(hi[i],c[i]+e[i])
 size=[max(2,hi[i]-lo[i]) for i in range(3)]
 return {'length_mm':max(size),'radius_mm':max(2,min(size)/2),'fillet_radius_mm':max(1,min(size)/20),'source_primitive_count':len(primitives)}
def skills_for(primitives,feature_skills):
 return [normalize_skill(x) for x in feature_skills if normalize_skill(x)]

def normalize_skill(skill):
 aliases={
  'CreateRoundedLinkHousing':'ApplyFillet',
  'CreateRotaryJointHousing':'ApplyFillet',
  'CreateLoftedLinkHousing':'ApplyChamfer',
  'CreateFlangeInterface':'CircularPattern',
  'CreateShellHousing':'BooleanCut',
  'CreateJointTransition':'ApplyChamfer',
  'ApplyFilletGroup':'ApplyFillet',
  'circular_flange':'CircularPattern',
  'mounting_tabs':'CircularPattern',
  'rectangular_housing':'ApplyFillet',
  'rectangular_tube':'BooleanCut',
  'parallel_gripper':'BooleanCut',
 }
 return aliases.get(skill,skill if skill in {'ApplyFillet','ApplyChamfer','CreateHole','CircularPattern','BooleanCut'} else None)

def composite_params(primitives):
 return {'primitives':primitives,'source_primitive_count':len(primitives)}

def largest(primitives,kind):
 items=[p for p in primitives if p['type']==kind]
 if not items:return None
 if kind=='box':return max(items,key=lambda p:p['size'][0]*p['size'][1]*p['size'][2])
 if kind=='cylinder':return max(items,key=lambda p:p['radius']*p['radius']*p['height'])
 return items[0]

def derived_operations(primitives,feature_skills,version):
 if version!='V2':return []
 ops=[];box=largest(primitives,'box');cyl=largest(primitives,'cylinder');env=envelope(primitives)
 requested=skills_for(primitives,feature_skills)
 if 'ApplyFillet' in requested or env['radius_mm']>6:ops.append(('ApplyFillet',{'radius_mm':max(0.5,min(2.0,env['fillet_radius_mm']))}))
 if 'ApplyChamfer' in requested or any(p['type']=='cone' for p in primitives):ops.append(('ApplyChamfer',{'distance_mm':max(0.5,min(1.5,env['fillet_radius_mm']))}))
 if cyl:
  if 'CircularPattern' in requested or cyl['radius']>=10:ops.append(('CircularPattern',{'center':cyl.get('center',[0,0,0]),'axis':cyl.get('axis',[0,0,1]),'radius_mm':max(2,cyl['radius']*0.75),'boss_radius_mm':max(0.8,cyl['radius']*0.12),'boss_height_mm':max(1,cyl['height']*0.06),'count':4}))
 if box:
  ops.append(('CreateHole',{'center':box.get('center',[0,0,0]),'axis':[0,0,1],'radius_mm':max(1,min(box['size'])*0.12),'depth_mm':max(2,box['size'][2]*1.2)}))
  if 'BooleanCut' in requested or max(box['size'])/max(1,min(box['size']))>2.0:
   ops.append(('BooleanCut',{'center':box.get('center',[0,0,0]),'axis':[0,0,1],'shape':'rectangle','size_mm':[max(2,box['size'][0]*0.45),max(1,box['size'][1]*0.18),max(2,box['size'][2]*1.2)]}))
 seen=[];unique=[]
 for skill,params in ops:
  key=(skill,json.dumps(params,sort_keys=True))
  if key not in seen:seen.append(key);unique.append((skill,params))
 return unique[:5]
def main():
 a=argparse.ArgumentParser();a.add_argument('--version',choices=('V1','V2'),required=True);a.add_argument('--case',required=True);x=a.parse_args();run=ROOT/'try3/runs'/x.version/x.case
 bp=json.loads((run/'blueprint.json').read_text());features={}
 fp=run/'feature_graph.json'
 if fp.exists():
  for f in json.loads(fp.read_text()).get('features',[]):features.setdefault(f['link_id'],[]).append(f['skill'])
 calls=[];i=0;world=world_frames(bp)
 for link in bp['links']:
  target=link['name'];agent='V1PerLinkPlanner' if x.version=='V1' else 'V2MechanicalArchitect';i+=1;calls.append(call(f'{x.case}-{i:03d}','PlaceComponentFromURDF',target,{'transform_cm':world[target]},'SkillCallProjection'))
  i+=1;calls.append(call(f'{x.case}-{i:03d}','CreateCompositeLinkGeometry',target,composite_params(link['primitives']),agent))
  for skill,params in derived_operations(link['primitives'],features.get(target,[]),x.version):
   i+=1;calls.append(call(f'{x.case}-{i:03d}',skill,target,params,agent))
 for j in bp['joints']:
  i+=1;calls.append(call(f'{x.case}-{i:03d}','CreateSharedJointReference',j['child'],{'joint_id':j['name'],'parent_link':j['parent'],'origin_xyz_mm':j['origin_xyz'],'axis':j['axis']},'SkillCallProjection'))
 out=run/'skill_calls.json';out.write_text(json.dumps({'schema_version':'robotcad.skill_call.v1','calls':calls},indent=2));print(out)
if __name__=='__main__':main()
