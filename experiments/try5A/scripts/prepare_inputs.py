"""Copy image evidence and create mesh-free sanitized URDF for Robot A."""
import hashlib,json,shutil,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';SRC=ROOT/'go_nogo1/sources/urdf_files_dataset/urdf_files/robotics-toolbox/xacro_generated/interbotix_descriptions/urdf/px100.urdf';OUT=HERE/'inputs/sanitized_urdf/px100_sanitized.urdf'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
root=ET.parse(SRC).getroot();links=root.findall('link');joints=root.findall('joint');lm={x.attrib['name']:f'L{i:02d}' for i,x in enumerate(links)};jm={x.attrib['name']:f'J{i:02d}' for i,x in enumerate(joints)};clean=ET.Element('robot',{'name':'R01_sanitized'})
for x in links:ET.SubElement(clean,'link',{'name':lm[x.attrib['name']]})
for x in joints:
 y=ET.SubElement(clean,'joint',{'name':jm[x.attrib['name']],'type':x.attrib['type']})
 for tag in ('origin','axis','limit'):
  z=x.find(tag)
  if z is not None:ET.SubElement(y,tag,dict(z.attrib))
 ET.SubElement(y,'parent',{'link':lm[x.find('parent').attrib['link']]});ET.SubElement(y,'child',{'link':lm[x.find('child').attrib['link']]})
 z=x.find('mimic')
 if z is not None:
  a=dict(z.attrib);a['joint']=jm[a['joint']];ET.SubElement(y,'mimic',a)
OUT.parent.mkdir(parents=True,exist_ok=True);ET.indent(clean);ET.ElementTree(clean).write(OUT,encoding='utf-8',xml_declaration=True)
imgout=HERE/'inputs/images';imgout.mkdir(parents=True,exist_ok=True);images=[]
for p in sorted((ROOT/'try4/artifacts/R01/global').glob('*.png')):q=imgout/p.name;shutil.copy2(p,q);images.append({'path':str(q.relative_to(HERE)),'sha256':sha(q),'bytes':q.stat().st_size})
mapping={'links':lm,'joints':jm};(HERE/'protocol/source_id_mapping.json').write_text(json.dumps(mapping,indent=2)+'\n');manifest={'source_urdf':str(SRC.relative_to(ROOT)),'source_urdf_sha256':sha(SRC),'sanitized_urdf_sha256':sha(OUT),'images':images,'engineering_text_sha256':sha(HERE/'inputs/engineering_text/robot_A.md'),'forbidden_xml_tags_found':{x:len(clean.findall('.//'+x)) for x in ['visual','collision','inertial','mesh','geometry','material','transmission']}};(HERE/'inputs/input_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({'links':len(links),'joints':len(joints),'images':len(images),'forbidden':manifest['forbidden_xml_tags_found']}))
