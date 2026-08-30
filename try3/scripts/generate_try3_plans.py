"""Generate non-GT visual evidence and V1/V2 Fusion blueprints for Try-3."""
from __future__ import annotations
import argparse, base64, csv, hashlib, json, mimetypes, shutil, sys, time, xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path
from typing import Any
from PIL import Image, ImageDraw
import jsonschema

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'go_nogo2/scripts'),str(ROOT/'go_nogo3/scripts')]
from glm_config import load_glm
from robot_blueprint import extract_json, load_schema
from run_prototype import generic_validate

VIEWS=('front','rear','left','right','top','isometric')

def skeleton(path:Path):
 root=ET.parse(path).getroot();links=[n.get('name') for n in root.findall('link')];joints=[]
 for n in root.findall('joint'):
  o=n.find('origin');a=n.find('axis');lim=n.find('limit');xyz=[float(x)*1000 for x in (o.get('xyz','0 0 0').split() if o is not None else ['0','0','0'])];rpy=[float(x) for x in (o.get('rpy','0 0 0').split() if o is not None else ['0','0','0'])];axis=[float(x) for x in (a.get('xyz','0 0 1').split() if a is not None else ['0','0','1'])]
  joints.append({'name':n.get('name'),'parent':n.find('parent').get('link'),'child':n.find('child').get('link'),'type':n.get('type'),'origin_xyz':xyz,'origin_rpy':rpy,'axis':axis,'lower':float(lim.get('lower','0')) if lim is not None else 0.0,'upper':float(lim.get('upper','0')) if lim is not None else 0.0})
 return links,joints

def image_item(path:Path):
 mime=mimetypes.guess_type(path.name)[0] or 'image/png';return {'type':'image_url','image_url':{'url':f'data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}'}}

def content(packet:dict, extra:str, crop:Path|None=None):
 out=[{'type':'text','text':packet['rendered_prompt']+extra}]
 for view in VIEWS:out += [{'type':'text','text':'view='+view},image_item(ROOT/packet['images'][view])]
 if crop: out += [{'type':'text','text':'Non-GT visual-agent crop contact sheet; labels are anonymous URDF IDs.'},image_item(crop)]
 return out

def invoke(client,model,system,content):
 body=[];reason=[];usage=None;rid=None;finish=None
 for chunk in client.chat.completions.create(model=model,messages=[{'role':'system','content':system},{'role':'user','content':content}],temperature=0,top_p=1,max_tokens=32768,stream=True,extra_body={'reasoning_effort':'low'}):
  rid=getattr(chunk,'id',rid);usage=getattr(chunk,'usage',None) or usage
  if not chunk.choices:continue
  d=chunk.choices[0].delta;body.append(getattr(d,'content',None) or '');reason.append(getattr(d,'reasoning_content',None) or '');finish=chunk.choices[0].finish_reason or finish
 u=usage;return ''.join(body),{'input_tokens':int(getattr(u,'prompt_tokens',0)or 0),'output_tokens':int(getattr(u,'completion_tokens',0)or 0),'total_tokens':int(getattr(u,'total_tokens',0)or 0),'finish_reason':finish,'request_id':rid,'reasoning_characters':len(''.join(reason))}

def evidence(raw:str,links:list[str]):
 value=extract_json(raw);by={x.get('link_id'):x for x in value.get('links',[]) if isinstance(x,dict)};out=[]
 for name in links:
  x=by.get(name,{}) ;focus=x.get('focus',{})
  try: cx,cy,w,h=[float(focus.get(k,d)) for k,d in [('cx',.5),('cy',.5),('w',.35),('h',.35)]]
  except:cx,cy,w,h=.5,.5,.35,.35
  out.append({'link_id':name,'focus':{'cx':min(1,max(0,cx)),'cy':min(1,max(0,cy)),'w':min(1,max(.1,w)),'h':min(1,max(.1,h))},'visual_observations':x.get('visual_observations',{}),'confidence':x.get('confidence',{})})
 return {'global_observation':value.get('global_observation',{}),'links':out}

def crops(packet,evidence,output):
 source=Image.open(ROOT/packet['images']['front']).convert('RGB');tiles=[]
 for item in evidence['links']:
  f=item['focus'];w,h=source.size;left=max(0,int((f['cx']-f['w']/2)*w));top=max(0,int((f['cy']-f['h']/2)*h));right=min(w,int((f['cx']+f['w']/2)*w));bottom=min(h,int((f['cy']+f['h']/2)*h));tile=source.crop((left,top,max(left+1,right),max(top+1,bottom)));tile.thumbnail((180,180));canvas=Image.new('RGB',(190,210),'white');canvas.paste(tile,((190-tile.width)//2,5));ImageDraw.Draw(canvas).text((5,188),item['link_id'],fill='black');tiles.append(canvas)
 cols=5;rows=(len(tiles)+cols-1)//cols;sheet=Image.new('RGB',(cols*190,rows*210),'white')
 for i,tile in enumerate(tiles):sheet.paste(tile,((i%cols)*190,(i//cols)*210))
 output.parent.mkdir(parents=True,exist_ok=True);sheet.save(output);return output

def enforce(raw,links,joints):
 value=extract_json(raw);geom={x.get('name'):normalize_primitives(x.get('primitives',[])) for x in value.get('links',[]) if isinstance(x,dict)};fallback=[{'type':'sphere','center':[0,0,0],'radius':10}]
 return generic_validate({'schema_version':'1.0','units':'mm','links':[{'name':n,'primitives':geom.get(n,fallback)} for n in links],'joints':joints})

def normalize_primitives(items):
 """Canonicalize model-authored base geometry; detail remains in Feature Graph."""
 axis_map={'x':[1,0,0],'-x':[-1,0,0],'y':[0,1,0],'-y':[0,-1,0],'z':[0,0,1],'-z':[0,0,-1]}
 clean=[]
 for item in items:
  if not isinstance(item,dict) or item.get('type') not in {'box','cylinder','sphere','cone'}:continue
  kind=item['type'];out={'type':kind,'center':item.get('center',[0,0,0])}
  if kind=='box':out['size']=item.get('size',[10,10,10])
  elif kind=='sphere':out['radius']=item.get('radius',10)
  elif kind=='cylinder':out.update(radius=item.get('radius',10),height=item.get('height',10),axis=axis_map.get(str(item.get('axis','z')).lower(),item.get('axis',[0,0,1])))
  else:out.update(bottom_radius=item.get('bottom_radius',10),top_radius=item.get('top_radius',0),height=item.get('height',10),axis=axis_map.get(str(item.get('axis','z')).lower(),item.get('axis',[0,0,1])))
  clean.append(out)
 return clean[:8] or [{'type':'sphere','center':[0,0,0],'radius':10}]

def canonicalize_plan(value):
 mep=value.get('mep',{});links=[]
 for item in mep.get('links',[]):
  link_id=item.get('link_id',item.get('id'))
  if not link_id:continue
  role=item.get('functional_role',item.get('name','link'))
  family='rotary_housing' if any(x in str(role).lower() for x in ('base','shoulder','wrist','housing')) else 'elongated_housing'
  links.append({'link_id':link_id,'functional_role':role,'geometry_family':family,'surface_strategy':'rounded_housing','protected_interface_regions':[]})
 interfaces=[]
 raw_interfaces=value.get('interfaces',{})
 iterator=raw_interfaces.items() if isinstance(raw_interfaces,dict) else enumerate(raw_interfaces)
 for key,item in iterator:
  if not isinstance(item,dict):continue
  joint_id=item.get('joint_id',key)
  if isinstance(joint_id,(int,float)): joint_id='J'+str(int(joint_id))
  interfaces.append({'joint_id':joint_id,'parent_link':item.get('parent_link',item.get('parent')),'child_link':item.get('child_link',item.get('child')),'interface_family':'prismatic_guide' if item.get('type')=='prismatic' else ('fixed_mount' if item.get('type')=='fixed' else 'rotary_housing'),'coaxial':item.get('type')!='fixed','clearance_mm':item.get('clearance_mm')})
 skill_map={'circular_flange':'CreateFlangeInterface','mounting_tabs':'CreateFlangeInterface','rectangular_housing':'CreateRoundedLinkHousing','rectangular_tube':'CreateLoftedLinkHousing','parallel_gripper':'CreateShellHousing'}
 features=[]
 for item in value.get('features',[]):
  if not isinstance(item,dict):continue
  link_id=item.get('link_id',item.get('link'));skill=item.get('skill','')
  if not link_id:continue
  features.append({'link_id':link_id,'feature_type':skill,'skill':skill_map.get(skill,skill if skill in skill_map.values() else 'ApplyFilletGroup')})
 return {'mep':{'version':'1','links':links},'interfaces':{'version':'1','interfaces':interfaces},'features':{'version':'1','features':features}}

def validate_plan(value):
 value=canonicalize_plan(value)
 for name in ('mep','interfaces','features'):
  schema=json.loads((ROOT/'try3/schemas'/({'mep':'mechanical_embodiment_plan_v1.schema.json','interfaces':'interface_graph_v1.schema.json','features':'feature_graph_v1.schema.json'}[name])).read_text())
  jsonschema.validate(value[name],schema)
 return value

def main():
 p=argparse.ArgumentParser();p.add_argument('--version',choices=('V1','V2'),required=True);p.add_argument('--case');p.add_argument('--overwrite',action='store_true');a=p.parse_args();cfg=load_glm();client=cfg.create_client()
 selected=[r['case_id'] for r in csv.DictReader((ROOT/'try3/tryset5_v1.csv').open(encoding='utf-8-sig'))]
 for case in selected:
  if a.case and case!=a.case:continue
  run=ROOT/'try3/runs'/a.version/case
  if run.exists() and a.overwrite:shutil.rmtree(run)
  if (run/'manifest.json').exists():continue
  run.mkdir(parents=True);packet=json.loads((ROOT/'try1/inputs/image_text_v1'/f'{case}.json').read_text());links,joints=skeleton(ROOT/'try2/inputs/sanitized_urdf'/f'{case}.urdf');urdf=(ROOT/'try2/inputs/sanitized_urdf'/f'{case}.urdf').read_text();history=[];total={'input_tokens':0,'output_tokens':0,'total_tokens':0};status='FAILURE';error=None
  try:
   sys1='Return JSON only: {"global_observation":{},"links":[{"link_id":"L0","focus":{"cx":0.5,"cy":0.5,"w":0.3,"h":0.3},"visual_observations":{},"confidence":{}}]}. Analyze images only; do not use hidden geometry.'
   raw,u=invoke(client,cfg.model,sys1,content(packet,'\nKnown anonymous kinematic skeleton:\n'+urdf));history.append({'stage':'visual_evidence','response':raw,'usage':u});[total.__setitem__(k,total[k]+u[k]) for k in total];ev=evidence(raw,links);(run/'visual_evidence.json').write_text(json.dumps(ev,indent=2));sheet=crops(packet,ev,run/'crops'/'contact_sheet.png')
   plan_context='\nSanitized URDF:\n'+urdf+'\nVisual evidence:\n'+json.dumps(ev,separators=(',',':'))
   if a.version=='V2':
    sys2='Return JSON only with keys mep, interfaces, features. MEP must use version="1" and anonymous L IDs; interfaces must use J/L IDs from URDF; features must use the listed Try-3 generic skills. Do not invent topology.'
    raw,u=invoke(client,cfg.model,sys2,[{'type':'text','text':plan_context}]);history.append({'stage':'mep_interface_feature_plan','response':raw,'usage':u});[total.__setitem__(k,total[k]+u[k]) for k in total];plan=validate_plan(extract_json(raw));(run/'mechanical_embodiment_plan.json').write_text(json.dumps(plan['mep'],indent=2));(run/'interface_graph.json').write_text(json.dumps(plan['interfaces'],indent=2));(run/'feature_graph.json').write_text(json.dumps(plan['features'],indent=2));plan_context+='\nMEP/Interface/Feature plan:\n'+json.dumps(plan,separators=(',',':'))
   sys3='Return JSON only Robot CAD blueprint. Instantiate every anonymous URDF link exactly once. URDF joints are binding and will be overwritten deterministically, so focus on detailed exterior link primitives: housings, tapered bodies, flanges, recesses and rounded transitions visible in the evidence. Each link may emit at most 8 base primitives and each primitive must contain only its required geometry fields (no primitive_id, notes, geometry wrapper, or extra metadata). Put extra detail into the Feature Graph plan, not the primitive list.'
   raw,u=invoke(client,cfg.model,sys3,content(packet,plan_context,sheet));history.append({'stage':'cad_blueprint','response':raw,'usage':u});[total.__setitem__(k,total[k]+u[k]) for k in total];bp=enforce(raw,links,joints);(run/'blueprint.json').write_text(json.dumps(bp,indent=2));status='SUCCESS'
  except Exception as exc:error=f'{type(exc).__name__}: {exc}'
  (run/'raw_history.json').write_text(json.dumps(history,indent=2));(run/'manifest.json').write_text(json.dumps({'case_id':case,'version':a.version,'status':status,'model':cfg.model,'calls':len(history),'budget':total,'error':error},indent=2));print(a.version,case,status,flush=True)
if __name__=='__main__':main()
