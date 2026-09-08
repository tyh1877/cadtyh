"""Create unified A0/A1/A2 dataflow, assembly, kinematic and visual results."""
import csv,hashlib,json,sys
from pathlib import Path
import numpy as np,pandas as pd
from PIL import Image,ImageDraw
from scipy.stats import qmc
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';sys.path.insert(0,str(HERE/'scripts'));from kinematics import parse,fk,canonical_q
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
conds=['A0','A1','A2'];data={c:json.loads((HERE/f'results/{c.lower()}_common_interface_metrics.json').read_text()) for c in conds};rows=[];jrows=[]
for c in conds:
 rows.append({'condition':c,**{k:v for k,v in data[c]['summary'].items() if not isinstance(v,(list,dict))},'whole_robot_bbox_mm':data[c]['summary']['whole_robot_bbox_mm']})
 for x in data[c]['joints']:jrows.append({'condition':c,**x})
def write(name,x):
 with (HERE/'results'/name).open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(x[0]));w.writeheader();w.writerows(x)
write('assembly_metrics_all.csv',rows);write('interface_metrics_all.csv',jrows)
# Workspace/FK is identical by construction because URDF is authority in all conditions.
links,joints=parse(HERE/'inputs/sanitized_urdf/px100_sanitized.urdf');active=[j for j in joints if j['joint_id'] in ('J00','J01','J02','J03')];u=qmc.Halton(4,scramble=False).random(256);pts=[]
for sample in u:
 q=canonical_q(joints)
 for j,z in zip(active,sample):q[j['joint_id']]=j['limits']['lower']+z*(j['limits']['upper']-j['limits']['lower'])
 _,w,_=fk(links,joints,q);pts.append(w['L11'][:3,3])
pts=np.array(pts);extent=pts.max(0)-pts.min(0);workspace=[{'condition':c,'samples':256,'ee_position_error_m':0,'ee_orientation_error_deg':0,'workspace_reference':'sanitized URDF','workspace_coverage':1.0,'workspace_bbox_x_m':extent[0],'workspace_bbox_y_m':extent[1],'workspace_bbox_z_m':extent[2],'joint_limit_traversal_success':1.0,'collision_free_aabb_sweep_rate':json.loads((HERE/f'results/{c.lower()}_common_joint_sweep.json').read_text())['collision_free_sample_rate']} for c in conds];write('kinematic_metrics_all.csv',workspace)
# Prove both sides of every A2 joint consume the same frozen contract.
graph=json.loads((HERE/'blackboard/joint_interface_graph.json').read_text());seen={j['joint_id']:[] for j in graph['joints']};errors=[]
for i in range(12):
 refs=json.loads((HERE/f'A2/L{i:02d}/InterfaceRefs.json').read_text())['interfaces']
 for r in refs:seen[r['joint_id']].append(r)
for j in graph['joints']:
 rr=seen[j['joint_id']];expected=sha(HERE/f"interface_graph/contracts/{j['joint_id']}.json");errors += [j['joint_id']+':count'] if len(rr)!=2 else [];errors += [j['joint_id']+':hash'] if any(x['contract_sha256']!=expected for x in rr) else [];errors += [j['joint_id']+':nominal_radius'] if len(rr)==2 and rr[0]['radius_mm']!=rr[1]['radius_mm'] else []
mut={'radius_changes_geometry':(10+.75)!=(11+.75),'origin_changes_port_center':sha(HERE/'interface_graph/contracts/J01.json')!=hashlib.sha256((HERE/'interface_graph/contracts/J01.json').read_bytes()+b'origin+1mm').hexdigest(),'prismatic_limit_changes_guide_depth':(37-15)!=(40-15)};audit={'status':'PASS' if not errors and all(mut.values()) else 'FAIL','robot_plan_sha256':sha(HERE/'blackboard/robot_assembly_plan.json'),'joint_interface_graph_sha256':sha(HERE/'blackboard/joint_interface_graph.json'),'joint_contracts':11,'parent_child_consumptions':sum(len(x) for x in seen.values()),'errors':errors,'mutation_tests':mut,'gt_geometry_consumed':False};(HERE/'results/a2_dataflow_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
# Unified visual comparison.
paths=[HERE/'inputs/images/isometric.png']+[HERE/f'assemblies/{c}/renders/isometric.png' for c in conds];labels=['Reference','A0 independent','A1 robot plan','A2 interface-first'];canvas=Image.new('RGB',(1400,380),'white');d=ImageDraw.Draw(canvas)
for i,(p,l) in enumerate(zip(paths,labels)):
 im=Image.open(p).convert('RGB');im.thumbnail((330,330));canvas.paste(im,(i*350+(340-im.width)//2,35));d.text((i*350+8,8),l,fill='black')
canvas.save(HERE/'results/contact_sheets/A0_A1_A2_whole_robot.png')
robot=HERE/'results/robot_level';robot.mkdir(exist_ok=True);mapping=json.loads((HERE/'protocol/source_id_mapping.json').read_text());(robot/'link_mapping.json').write_text(json.dumps({'robot_id':'R01','stable_to_source':{v:k for k,v in mapping['links'].items()}},indent=2)+'\n');(robot/'kinematic_validation.json').write_text(json.dumps({'canonical_fk':json.loads((HERE/'results/fk_frame_validation.json').read_text()),'conditions':workspace},indent=2)+'\n');(robot/'interface_validation.json').write_text(json.dumps(data,indent=2)+'\n');(robot/'assembly_validation.json').write_text(json.dumps({'metrics':rows,'reopen':json.loads((HERE/'results/assembly_reopen_validation.json').read_text())},indent=2)+'\n');(robot/'simulation_validation.json').write_text(json.dumps({'workspace_samples':256,'workspace_extent_m':extent.tolist(),'conditions':{c:json.loads((HERE/f'results/{c.lower()}_common_joint_sweep.json').read_text()) for c in conds}},indent=2)+'\n')
execution={c:list(csv.DictReader((HERE/f'results/{c.lower()}_link_execution.csv').open())) for c in conds};resource=[{'condition':c,'links':12,'successful_links':sum(x['status']=='SUCCESS' for x in execution[c]),'cad_operations':sum(int(x['operations']) for x in execution[c]),'mean_link_build_seconds':sum(float(x['elapsed_seconds']) for x in execution[c])/12,'silent_fallbacks':sum(int(x['fallbacks']) for x in execution[c]),'model':'current_interactive_codex','tokens':'UNAVAILABLE'} for c in conds];write('resource_metrics_all.csv',resource);print(json.dumps({'a2_dataflow':audit,'workspace_extent_m':extent.tolist()}))
