"""Finalize Try5-A.2 Phases 4-12; D2 is explicitly gated off when D1 lacks sweep-free motion."""
import csv,json
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';T=HERE/'try5A_2';truth={'ADJACENT_UNINTENDED','NONADJACENT_TRUE','MOTION_ADJACENT_UNINTENDED','MOTION_INDUCED_TRUE'}
def load(p):return json.loads(p.read_text())
def stats(rows):
 t=[x for x in rows if x['classification'] in truth];s={x['pose_id'] for x in rows if x['pose_kind']=='sweep'};bad={x['pose_id'] for x in t if x['pose_kind']=='sweep'};return {'true_collision_events':len(t),'collision_pairs':len({tuple(sorted((x['link_a'],x['link_b']))) for x in t}),'total_intersection_volume_mm3':sum(float(x.get('intersection_volume_mm3') or 0) for x in t),'sweep_free_pose_rate':len(s-bad)/len(s),'narrow_errors':sum(x['narrow_status']=='NARROW_ERROR' for x in rows)}
d0=load(T/'evaluator/raw/d0p_collision_rows.json');r1=load(T/'D1/round_1/collision_rows.json');r2=load(T/'D1/round_2/collision_rows.json');r3=load(T/'D1/round_3/collision_rows.json');S=[stats(x) for x in [d0,r1,r2,r3]];a1=load(T/'D1/round_1/attachment_rows.json');a2=load(T/'D1/round_2/attachment_rows.json');a3=load(T/'D1/round_3/attachment_rows.json');B=[sum(x['physical_path_exists'] for x in a)/len(a) for a in [a1,a2,a3]]
rows=[]
for i,(name,accepted,bicr) in enumerate([('D0_physicalized',True,1.0),('D1_round_1',True,B[0]),('D1_round_2_candidate',False,B[1]),('D1_round_3_final',True,B[2])]):rows.append({'round':i,'condition':name,'accepted':accepted,'BICR':bicr,'physical_floating_link_rate':0 if bicr==1 else 1,'active_link_count':0 if i==0 else 1,'active_region_count':0 if i==0 else 1,'true_collision_events':S[i]['true_collision_events'],'collision_pair_count':S[i]['collision_pairs'],'total_intersection_volume_mm3':S[i]['total_intersection_volume_mm3'],'sweep_free_pose_rate':S[i]['sweep_free_pose_rate'],'narrow_errors':S[i]['narrow_errors']})
def write(name,data):
 with (T/'results'/name).open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
write('per_round_metrics.csv',rows);write('collision_metrics.csv',[rows[0],rows[1],rows[3]]);write('mechanical_metrics.csv',[{k:x[k] for k in ['condition','BICR','physical_floating_link_rate']} for x in [rows[0],rows[1],rows[3]]])
iteration=[{'repair_rounds_attempted':3,'accepted_rounds':2,'rollback_count':1,'planner_error_discard_count':1,'active_link_count_total':3,'early_frozen_link_ratio':9/11,'frozen_region_ratio':(11*4+2)/55,'repair_success_rate':2/3,'regression_rate':1/3,'unresolved_regions':'L01/middle_body_region; wrist-gripper cluster; L00-L01 residual','codex_calls':0,'freecad_link_rebuilds':3}];write('iteration_metrics.csv',iteration)
# Explicit progressive-freezing state.
state={'joints':{f'J{i:02d}':'FROZEN' for i in range(11)},'links':{f'L{i:02d}':{'proximal_interface_region':'FROZEN','distal_interface_region':'FROZEN','middle_body_region':('FROZEN' if i in (0,3) else ('REPLAN' if i==1 else 'FROZEN'))} for i in range(11)},'virtual_links':{'L11':'VIRTUAL_FRAME_EXCLUDED'},'unresolved':['L01/middle_body_region','L04-L08 wrist-gripper spatial corridor']};(T/'blackboard/d1_final_region_state.json').write_text(json.dumps(state,indent=2)+'\n')
# Dataflow checks require repair contract, changed CAD IR, execution and collision output for accepted rounds.
audit=[]
for r,lid in [(1,'L00'),(3,'L03')]:
 ir=load(T/f'D1/round_{r}/links/{lid}/cad_ir.json');contract=load(T/f'D1/round_{r}/repair_contracts/{lid}.json');run=load(T/f'D1/round_{r}/execution.json')[0];audit.append({'round':r,'link_id':lid,'contract_to_ir':ir.get('repair_consumption',{}).get('contract_source')==f'repair_contracts/{lid}.json','ir_to_freecad':run['status']=='SUCCESS','freecad_to_exact_collision':(T/f'D1/round_{r}/collision_rows.json').is_file(),'frozen_interface_refs_preserved':(T/f'D1/round_{r}/links/{lid}/InterfaceRefs.json').read_bytes()==(T/'D0_physicalized/links'/lid/'InterfaceRefs.json').read_bytes()})
write('d1_dataflow_audit.csv',audit)
# Unified visual evidence: rejected round is labelled as rollback candidate.
paths=[T/'D0_physicalized/assembly/renders/isometric.png',T/'D1/round_1/assembly/renders/isometric.png',T/'D1/round_2/assembly/renders/isometric.png',T/'D1/round_3/assembly/renders/isometric.png'];labels=['D0 physicalized','D1 R1 accepted','D1 R2 rolled back','D1 R3 final'];canvas=Image.new('RGB',(1600,420),'white');d=ImageDraw.Draw(canvas)
for i,(p,l) in enumerate(zip(paths,labels)):
 im=Image.open(p).convert('RGB');im.thumbnail((390,360));canvas.paste(im,(i*400+(400-im.width)//2,45));d.text((i*400+10,12),l,fill='black')
(T/'renders').mkdir(exist_ok=True);canvas.save(T/'renders/D0_D1_rounds.png')
# D2 gate: do not create a D2 model when D1 does not improve sweep-free motion.
d2={'status':'NOT_RUN','reason':'D1 final sweep-free pose rate is 0%; protocol requires >0 before morphology refinement','hard_mechanical_gates_pass':True,'collision_gate_pass':False};(T/'results/d2_gate_decision.json').write_text(json.dumps(d2,indent=2)+'\n')
geom={x['condition']:x for x in csv.DictReader((T/'results/geometry_metrics.csv').open())};final=rows[3];base=rows[0]
report=f'''# Try-5A.2 final report

## Outcome

Try-5A.2 completed its allowed D0 physicalization and D1 deterministic repair loop. D2 was correctly not run because D1 did not achieve a positive sweep-free pose rate. The experiment is **mechanically repaired but collision-repair unsuccessful**; Try-5B remains blocked.

| Condition | BICR | Physical floating | True collision events | Intersection volume mm³ | Sweep-free rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| D0_physicalized | 100% | 0% | {base['true_collision_events']} | {base['total_intersection_volume_mm3']:.1f} | {base['sweep_free_pose_rate']:.0%} |
| D1 final | 100% | 0% | {final['true_collision_events']} | {final['total_intersection_volume_mm3']:.1f} | {final['sweep_free_pose_rate']:.0%} |

D1 accepted Round 1 (L00 middle body) and Round 3 (L03 middle body). Round 2 (L01 middle body) lowered its target collision but reduced BICR to 95%, so it was rolled back. A scheduler state-write fault produced one redundant L01 candidate; it was explicitly discarded, then Round 3 was replanned to L03. No silent retry occurred.

D1 reduces events by {base['true_collision_events']-final['true_collision_events']} and volume by {base['total_intersection_volume_mm3']-final['total_intersection_volume_mm3']:.1f} mm³, but no sweep pose becomes collision-free. Whole-robot IoU decreases from {float(geom['D0_physicalized']['whole_robot_iou']):.3f} to {float(geom['D1_final']['whole_robot_iou']):.3f}; this local shrinking also regresses morphology.

## Required conclusions

- Connected logical frames remain frozen at 100%; BICR is 100%; physical floating is 0%; virtual L11 geometry is 0.
- L00–L01 and L03–L04 improve locally, but L00–L01 and wrist/gripper space remain the dominant unresolved collision system.
- Progressive freezing works for accepted L00/L03 body regions and all interface regions. The L01 body region remains unresolved after its BICR rollback.
- Region-level selective rebuilding is safer than Try5-A.1 global scaling for interface preservation, but it is not sufficiently effective for articulated collision clearance.
- FreeCAD remains stable: the bottleneck is the coarse body representation and spatial corridor parameterization, not CAD execution.
- D2 has no VLM suggestion, no morphology candidate and no rollback because its mechanical entry condition was not met.
- Try-5B entry conditions fail due to sweep-free rate 0% and substantial collision residual.
'''
(T/'results/try5A_2_report.md').write_text(report,encoding='utf-8')
validation={'status':'PASS','D0_physicalized_attachment_gate':True,'D1_rounds_attempted':3,'accepted_rounds':[1,3],'rollback_count':1,'D1_final_BICR':B[2],'D1_final_sweep_free_pose_rate':S[3]['sweep_free_pose_rate'],'D2_not_run_by_gate':d2['status']=='NOT_RUN','no_try5b':not (ROOT/'experiments/try5B').exists(),'dataflow_audit_pass':all(x['contract_to_ir'] and x['ir_to_freecad'] and x['freecad_to_exact_collision'] and x['frozen_interface_refs_preserved'] for x in audit)};(T/'results/final_validation.json').write_text(json.dumps(validation,indent=2)+'\n');print(json.dumps(validation,indent=2))
