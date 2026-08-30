"""Project frozen Try-3 plans into backend-agnostic RobotCAD SkillCalls."""
from __future__ import annotations
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def call(n,skill,target,parameters,agent):return {'call_id':n,'skill':skill,'version':'v1','target_component':target,'parameters':parameters,'calling_agent':agent}
def envelope(primitives):
 # Deterministic plan-to-skill projection; never examines GT. Conservative
 # dimensions are read only from the planner's primitive parameters.
 p=primitives[0] if primitives else {'type':'sphere','radius':10,'center':[0,0,0]}
 if p['type']=='box':return {'length_mm':max(p['size']),'radius_mm':max(2,min(p['size'])/2),'fillet_radius_mm':1.5}
 if p['type'] in ('cylinder','sphere'):return {'length_mm':p.get('height',2*p.get('radius',10)),'radius_mm':p.get('radius',10),'fillet_radius_mm':1.5}
 return {'length_mm':p.get('height',20),'radius_mm':max(p.get('bottom_radius',10),p.get('top_radius',10)),'fillet_radius_mm':1.5}
def main():
 a=argparse.ArgumentParser();a.add_argument('--version',choices=('V1','V2'),required=True);a.add_argument('--case',required=True);x=a.parse_args();run=ROOT/'try3/runs'/x.version/x.case
 bp=json.loads((run/'blueprint.json').read_text());features={}
 fp=run/'feature_graph.json'
 if fp.exists():
  for f in json.loads(fp.read_text()).get('features',[]):features.setdefault(f['link_id'],[]).append(f['skill'])
 calls=[];i=0
 for link in bp['links']:
  target=link['name'];e=envelope(link['primitives']);agent='V1PerLinkPlanner' if x.version=='V1' else 'V2MechanicalArchitect';skills=features.get(target,[]) or ['CreateRoundedLinkHousing']
  for skill in skills:
   i+=1;calls.append(call(f'{x.case}-{i:03d}',skill,target,e,agent))
 for j in bp['joints']:
  i+=1;calls.append(call(f'{x.case}-{i:03d}','CreateSharedJointReference',j['child'],{'joint_id':j['name'],'parent_link':j['parent'],'origin_xyz_mm':j['origin_xyz'],'axis':j['axis']},'SkillCallProjection'))
 out=run/'skill_calls.json';out.write_text(json.dumps({'schema_version':'robotcad.skill_call.v1','calls':calls},indent=2));print(out)
if __name__=='__main__':main()
