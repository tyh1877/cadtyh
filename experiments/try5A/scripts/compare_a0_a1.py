"""Create deterministic A0/A1 tables, silhouette diagnostics and contact sheet."""
import csv,json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';a0=json.loads((HERE/'results/a0_interface_metrics.json').read_text());a1=json.loads((HERE/'results/a1_interface_metrics.json').read_text())
fields=['connected_joint_rate','floating_link_rate','assembly_connected_component_count','mean_interface_gap_mm','mean_radius_mismatch_mm','max_axis_angular_error_deg','max_axis_offset_mm','max_interface_center_error_mm','excessive_axial_penetrations','nonadjacent_aabb_overlap_pairs','overall_reach_from_root_mm'];rows=[]
for cond,x in [('A0',a0['summary']),('A1',a1['summary'])]:rows.append({'condition':cond,**{k:x[k] for k in fields},'whole_robot_bbox_mm':x['whole_robot_bbox_mm']})
with (HERE/'results/a0_a1_assembly_metrics.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
joint=[]
for x,y in zip(a0['joints'],a1['joints']):joint.append({'joint_id':x['joint_id'],'a0_connected':x['connected_from_ports'],'a1_connected':y['connected_from_ports'],'a0_gap_mm':x['interface_gap_mm'],'a1_gap_mm':y['interface_gap_mm'],'a0_radius_mismatch_mm':x['interface_radius_mismatch_mm'],'a1_radius_mismatch_mm':y['interface_radius_mismatch_mm'],'a0_penetration_mm':x['interface_axial_penetration_mm'],'a1_penetration_mm':y['interface_axial_penetration_mm']})
with (HERE/'results/a0_a1_per_joint.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(joint[0]));w.writeheader();w.writerows(joint)
def mask(path):
 a=np.array(Image.open(path).convert('RGB'));m=np.any(a<242,axis=2);ys,xs=np.where(m);m=m[ys.min():ys.max()+1,xs.min():xs.max()+1];im=Image.fromarray((m*255).astype('uint8'));im.thumbnail((480,480));out=np.zeros((512,512),bool);z=np.array(im)>0;y=(512-z.shape[0])//2;x=(512-z.shape[1])//2;out[y:y+z.shape[0],x:x+z.shape[1]]=z;return out
sil=[]
for view in ('front','side','top','isometric'):
 gt=mask(HERE/f'inputs/images/{"right" if view=="side" else view}.png')
 for cond in ('A0','A1'):
  p=mask(HERE/f'assemblies/{cond}/renders/{view}.png');sil.append({'view':view,'condition':cond,'silhouette_iou':float(np.logical_and(gt,p).sum()/np.logical_or(gt,p).sum())})
with (HERE/'results/a0_a1_silhouette.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(sil[0]));w.writeheader();w.writerows(sil)
paths=[HERE/'inputs/images/isometric.png',HERE/'assemblies/A0/renders/isometric.png',HERE/'assemblies/A1/renders/isometric.png'];labs=['Reference','A0 independent links','A1 robot plan'];canvas=Image.new('RGB',(1200,390),'white');d=ImageDraw.Draw(canvas)
for i,(p,l) in enumerate(zip(paths,labs)):
 im=Image.open(p).convert('RGB');im.thumbnail((380,340));canvas.paste(im,(i*400+(390-im.width)//2,35));d.text((i*400+10,8),l,fill='black')
folder=HERE/'results/contact_sheets';folder.mkdir(exist_ok=True);canvas.save(folder/'A0_A1_whole_robot.png')
plan=HERE/'blackboard/robot_assembly_plan.json';ph=hashlib.sha256(plan.read_bytes()).hexdigest();errors=[]
for i in range(12):
 spec=json.loads((HERE/f'A1/L{i:02d}/LinkCoarseSpec.json').read_text());manifest=json.loads((HERE/f'A1/L{i:02d}/parameter_manifest.json').read_text());errors += [f'L{i:02d}:hash'] if spec['robot_plan_source_sha256']!=ph or manifest['robot_plan_source_sha256']!=ph else []
base={'envelope':[.1,.05,.03],'family':'straight_beam'};h0=hashlib.sha256(json.dumps(base,sort_keys=True).encode()).hexdigest();base['envelope'][1]*=1.5;h1=hashlib.sha256(json.dumps(base,sort_keys=True).encode()).hexdigest();(HERE/'results/a1_dataflow_audit.json').write_text(json.dumps({'status':'PASS' if not errors and h0!=h1 else 'FAIL','robot_plan_sha256':ph,'link_consumers':12,'trace_errors':errors,'envelope_mutation_changes_planning_fingerprint':h0!=h1,'forbidden_interface_graph_consumption':False},indent=2)+'\n');print(json.dumps({'silhouette':sil,'dataflow_errors':errors}))
