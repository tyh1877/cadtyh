"""Generate the shared A/B and C/D embodiment plans for Try-2."""
from __future__ import annotations
import argparse, base64, json, mimetypes, shutil, sys, time, xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; sys.path[:0]=[str(ROOT/'go_nogo2/scripts'),str(ROOT/'go_nogo3/scripts')]
from glm_config import load_glm
from robot_blueprint import extract_json, blueprint_contract
from compile_blueprint import compile_direct
from run_prototype import generic_validate

VIEWS=('front','rear','left','right','top','isometric')
def content(packet, extra):
 out=[{'type':'text','text':packet['rendered_prompt']+extra}]
 for view in VIEWS:
  path=ROOT/packet['images'][view]; mime=mimetypes.guess_type(path.name)[0] or 'image/png'
  out += [{'type':'text','text':f'view={view}'},{'type':'image_url','image_url':{'url':f'data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}'}}]
 return out
def invoke(client, model, packet, extra):
 body=[];reason=[];usage=None;finish=None;rid=None
 for chunk in client.chat.completions.create(model=model,messages=[{'role':'system','content':'Return JSON only. '+blueprint_contract()},{'role':'user','content':content(packet,extra)}],temperature=0,top_p=1,max_tokens=32768,stream=True,extra_body={'reasoning_effort':'low'}):
  rid=getattr(chunk,'id',rid);usage=getattr(chunk,'usage',None) or usage
  if not chunk.choices: continue
  d=chunk.choices[0].delta;body.append(getattr(d,'content',None) or '');reason.append(getattr(d,'reasoning_content',None) or '');finish=chunk.choices[0].finish_reason or finish
 u=usage;return ''.join(body),{'input_tokens':int(getattr(u,'prompt_tokens',0)or 0),'output_tokens':int(getattr(u,'completion_tokens',0)or 0),'total_tokens':int(getattr(u,'total_tokens',0)or 0),'finish_reason':finish,'request_id':rid,'reasoning_characters':len(''.join(reason))}
def skeleton(path):
 root=ET.parse(path).getroot(); links=[n.get('name') for n in root.findall('link')]; joints=[]
 for n in root.findall('joint'):
  origin=n.find('origin');axis=n.find('axis');limit=n.find('limit'); xyz=[float(x)*1000 for x in (origin.get('xyz','0 0 0').split() if origin is not None else ['0','0','0'])]; rpy=[float(x) for x in (origin.get('rpy','0 0 0').split() if origin is not None else ['0','0','0'])]; av=[float(x) for x in (axis.get('xyz','0 0 1').split() if axis is not None else ['0','0','1'])]
  joints.append({'name':n.get('name'),'parent':n.find('parent').get('link'),'child':n.find('child').get('link'),'type':n.get('type'),'origin_xyz':xyz,'origin_rpy':rpy,'axis':av,'lower':float(limit.get('lower','0')) if limit is not None else 0.0,'upper':float(limit.get('upper','0')) if limit is not None else 0.0})
 return links,joints
def enforce_known(raw, urdf):
 value=extract_json(raw); links,joints=skeleton(urdf); geom={x.get('name'):x.get('primitives',[]) for x in value.get('links',[]) if isinstance(x,dict)}
 fallback=[{'type':'sphere','center':[0,0,0],'radius':10}]
 return generic_validate({'schema_version':'1.0','units':'mm','links':[{'name':name,'primitives':geom.get(name,fallback)} for name in links],'joints':joints})
def main():
 p=argparse.ArgumentParser();p.add_argument('--condition',choices=('A','C'),required=True);p.add_argument('--case');p.add_argument('--overwrite',action='store_true');a=p.parse_args();cfg=load_glm()
 for pp in sorted((ROOT/'try1/inputs/image_text_v1').glob('*.json')):
  if a.case and pp.stem!=a.case:continue
  run=ROOT/'try2/runs'/a.condition/pp.stem
  if run.exists() and a.overwrite:shutil.rmtree(run)
  if (run/'manifest.json').exists():continue
  run.mkdir(parents=True,exist_ok=True);packet=json.loads(pp.read_text());extra=' Generate an editable primitive CAD assembly and kinematic model from Image+Text only.'
  if a.condition=='C':
   prior=(ROOT/'try2/inputs/sanitized_urdf'/f'{pp.stem}.urdf').read_text();extra+=' The following sanitized kinematic-only URDF is a binding constraint: instantiate every anonymous link and preserve every joint exactly; infer only exterior geometry.\n'+prior
  started=time.perf_counter();raw='';error=None;status='FAILURE';usage={}
  try:
   raw,usage=invoke(cfg.create_client(),cfg.model,packet,extra);bp=enforce_known(raw,ROOT/'try2/inputs/sanitized_urdf'/f'{pp.stem}.urdf') if a.condition=='C' else generic_validate(extract_json(raw));(run/'blueprint.json').write_text(json.dumps(bp,indent=2));compile_direct(bp,run);status='SUCCESS'
  except Exception as exc:error=f'{type(exc).__name__}: {exc}'
  (run/'raw_response.txt').write_text(raw);(run/'manifest.json').write_text(json.dumps({'case_id':pp.stem,'condition':a.condition,'status':status,'model':cfg.model,'api_calls':1,'latency_seconds':time.perf_counter()-started,'budget':usage,'error':error},indent=2));print(a.condition,pp.stem,status,flush=True)
if __name__=='__main__':main()
