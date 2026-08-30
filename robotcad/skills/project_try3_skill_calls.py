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
 if feature_skills:return feature_skills
 kinds=[p['type'] for p in primitives]
 if 'cone' in kinds:return ['CreateLoftedLinkHousing']
 if kinds.count('cylinder')>=2:return ['CreateRotaryJointHousing']
 return ['CreateRoundedLinkHousing']

def composite_params(primitives):
 return {'primitives':primitives,'source_primitive_count':len(primitives)}
def main():
 a=argparse.ArgumentParser();a.add_argument('--version',choices=('V1','V2'),required=True);a.add_argument('--case',required=True);x=a.parse_args();run=ROOT/'try3/runs'/x.version/x.case
 bp=json.loads((run/'blueprint.json').read_text());features={}
 fp=run/'feature_graph.json'
 if fp.exists():
  for f in json.loads(fp.read_text()).get('features',[]):features.setdefault(f['link_id'],[]).append(f['skill'])
 calls=[];i=0;world=world_frames(bp)
 for link in bp['links']:
  target=link['name'];e=envelope(link['primitives']);agent='V1PerLinkPlanner' if x.version=='V1' else 'V2MechanicalArchitect';skills=skills_for(link['primitives'],features.get(target,[]));i+=1;calls.append(call(f'{x.case}-{i:03d}','PlaceComponentFromURDF',target,{'transform_cm':world[target]},'SkillCallProjection'))
  i+=1;calls.append(call(f'{x.case}-{i:03d}','CreateCompositeLinkGeometry',target,composite_params(link['primitives']),agent))
  for skill in skills:
   if skill in {'CreateRoundedLinkHousing','CreateRotaryJointHousing','CreateLoftedLinkHousing'}:
    continue
   i+=1;calls.append(call(f'{x.case}-{i:03d}',skill,target,e,agent))
 for j in bp['joints']:
  i+=1;calls.append(call(f'{x.case}-{i:03d}','CreateSharedJointReference',j['child'],{'joint_id':j['name'],'parent_link':j['parent'],'origin_xyz_mm':j['origin_xyz'],'axis':j['axis']},'SkillCallProjection'))
 out=run/'skill_calls.json';out.write_text(json.dumps({'schema_version':'robotcad.skill_call.v1','calls':calls},indent=2));print(out)
if __name__=='__main__':main()
