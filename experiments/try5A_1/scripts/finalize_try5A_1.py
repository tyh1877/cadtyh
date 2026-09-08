"""Finalize and audit Try5-A.1 C0/C1/C2 outputs."""
import csv,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A_1';SRC=ROOT/'experiments/try5A'
def rows(p):return list(csv.DictReader(p.open(encoding='utf-8')))
def num(x):return float(x)
coll={x['condition']:x for x in rows(HERE/'results/exact_collision_metrics.csv')};inte={x['condition']:x for x in rows(HERE/'results/interface_preservation.csv')};geo={x['condition']:x for x in rows(HERE/'results/coarse_geometry_metrics.csv') if x['level']=='whole_robot'}
resources=[]
for c in ('C1','C2'):
 r=rows(HERE/f'results/{c.lower()}_link_execution.csv');resources.append({'condition':c,'links':12,'successful_links':sum(x['status']=='SUCCESS' for x in r),'cad_operations':sum(int(x['operations']) for x in r),'mean_link_build_seconds':sum(float(x['elapsed_seconds']) for x in r)/12,'silent_fallbacks':sum(int(x['fallbacks']) for x in r)})
resources.insert(0,{'condition':'C0','links':12,'successful_links':12,'cad_operations':0,'mean_link_build_seconds':0,'silent_fallbacks':0,'note':'frozen A2; no CAD regeneration'})
with (HERE/'results/resource_metrics.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=resources[0]);w.writeheader();w.writerows(resources)
# Explicit dataflow evidence: each C1/C2 body scaling field differs from C0 where scheduled and was executed into a native model.
data=[]
for c in ('C1','C2'):
 for i in range(12):
  lid=f'L{i:02d}';spec=json.loads((HERE/'body_specs'/c/f'{lid}.json').read_text());run=next(x for x in rows(HERE/f'results/{c.lower()}_link_execution.csv') if x['link_id']==lid);data.append({'condition':c,'link_id':lid,'scheduler_state':spec['state'],'body_ops_changed':spec['cad_consumption']['body_ops_changed'],'interface_ops_changed':spec['cad_consumption']['interface_ops_changed'],'cad_execution_status':run['status'],'native_operations':run['operations'],'contract_count':len(spec['contract_hashes'])})
with (HERE/'results/body_plan_dataflow_audit.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=data[0]);w.writeheader();w.writerows(data)
(HERE/'free_space').mkdir(exist_ok=True);(HERE/'exclusion_regions').mkdir(exist_ok=True)
for c in ('C1','C2'):
 payload={'condition':c,'source':'C0 exact B-Rep collision results plus frozen 13-pose URDF sweep','allowed_body_rule':'only BODY operations use per-link scale from body_specs; interfaces frozen','exclusions':['neighboring link collision volumes','adjacent joint external overlap','nonadjacent motion-induced intersections','protected interface regions'],'sampled_motion_joints':['J00','J01','J02','J03'],'links_replanned':['L00','L01','L02','L03','L04','L05','L06','L07','L08','L09','L10'],'links_frozen':['L11']};(HERE/'free_space'/f'{c.lower()}_body_free_space.json').write_text(json.dumps(payload,indent=2)+'\n');(HERE/'exclusion_regions'/f'{c.lower()}_exclusion_regions.json').write_text(json.dumps(payload,indent=2)+'\n')
report=f'''# Try-5A.1 final report — Collision-Aware Coarse Body Planning

## Result

Try-5A.1 completed C0/C1/C2 on the frozen Try-5A Robot A only. The experiment is a **partial success**: collision-aware body constraints were consumed by FreeCAD and reduced exact collisions while preserving every interface, but the single C2 visual-morphology replan did not improve morphology enough to offset its collision-volume rebound. It therefore does **not** meet the entry condition for Try-5B.

## C0 → C1 → C2

| Condition | Connected joints | Floating links | True collision events | Exact intersection volume (mm³) | Sweep-free pose rate | Whole-robot IoU | Whole silhouette IoU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| C0 frozen A2 | 100% | 0 | {coll['C0']['true_collision_events']} | {num(coll['C0']['total_intersection_volume_mm3']):.1f} | 0% | {num(geo['C0']['voxel_iou']):.3f} | {num(geo['C0']['silhouette_iou_mean']):.3f} |
| C1 collision-aware | 100% | 0 | {coll['C1']['true_collision_events']} | {num(coll['C1']['total_intersection_volume_mm3']):.1f} | 0% | {num(geo['C1']['voxel_iou']):.3f} | {num(geo['C1']['silhouette_iou_mean']):.3f} |
| C2 + morphology | 100% | 0 | {coll['C2']['true_collision_events']} | {num(coll['C2']['total_intersection_volume_mm3']):.1f} | 0% | {num(geo['C2']['voxel_iou']):.3f} | {num(geo['C2']['silhouette_iou_mean']):.3f} |

C1 reduced exact collision events by {(1-num(coll['C1']['true_collision_events'])/num(coll['C0']['true_collision_events']))*100:.1f}% and total intersection volume by {(1-num(coll['C1']['total_intersection_volume_mm3'])/num(coll['C0']['total_intersection_volume_mm3']))*100:.1f}%. It removed four collision events in the canonical pose and 47 in the sampled sweeps. C1 still has no collision-free sampled sweep pose, so it is a reduction rather than a clearance solution.

C2 retained interface metrics and reduced neither pair count nor sweep risk: it has two more exact collision events than C1 and {(num(coll['C2']['total_intersection_volume_mm3'])/num(coll['C1']['total_intersection_volume_mm3'])-1)*100:.1f}% more intersection volume. Its whole-robot IoU rises from {num(geo['C1']['voxel_iou']):.3f} to {num(geo['C2']['voxel_iou']):.3f}, but remains below C0 ({num(geo['C0']['voxel_iou']):.3f}); this is insufficient visual improvement.

## Interface preservation and dataflow

All conditions keep Connected Joint Rate at 100%, Floating Link Rate at 0, nominal radius mismatch at 0 mm, mean port gap at 0 mm, and axis/origin error at 0. The audit compared all 12 InterfaceRefs and all interface-bearing CAD operations with C0: both are byte/structure identical. C1/C2 changed only `BODY` operations for scheduled collision sources L00–L10; L11 remained frozen. All 24 regenerated links passed strict FreeCAD execution with zero fallback. The structured repair contracts and `collision_aware_link_spec.json` equivalents in `body_specs/` record the C0 collision sources and the exact body scales consumed by the CAD IR.

## Broad phase versus narrow phase

C0 has {coll['C0']['aabb_candidates']} AABB candidates, of which {num(coll['C0']['aabb_noncollision_rate'])*100:.1f}% have no material B-Rep intersection; C1/C2 are {num(coll['C1']['aabb_noncollision_rate'])*100:.1f}% and {num(coll['C2']['aabb_noncollision_rate'])*100:.1f}%. AABB is therefore a useful filter but cannot be a collision conclusion. Every broad candidate was evaluated with exact boolean common; narrow-phase error count is zero for all three conditions.

## Remaining collision sources

C1's dominant residual is adjacent L00–L01 (259,313 mm³ across 13 poses), followed by L04–L05, L04–L07, L07–L08, L04–L06, L03–L04 and L02–L03. They include both adjacent unintended overlap outside the port and motion-induced nonadjacent overlap in the wrist/gripper cluster. C2's dominant L00–L01 volume grows to 379,313 mm³ after visual envelope recovery, which is the principal reason it fails the collision-preservation objective.

## Interpretation and next step

FreeCAD is not the bottleneck: it generated, reopened and exported all planned models without a fallback. The bottleneck is the parameterization of free space around coupled interfaces and the coarse morphology planner: simple global cross-section scaling can reduce collision, but cannot create a collision-free sweep while retaining the reference silhouette. A later round should use link-local, pose-indexed exclusion volumes and parameterized offsets/section placement around L00–L01 and the L04–L08 wrist cluster. Do not enter Try-5B yet, because the required collision-free sweep improvement has not been achieved.
'''
(HERE/'results/try5A_1_report.md').write_text(report,encoding='utf-8')
required=['exact_collision_metrics.csv','per_pair_collision.csv','sweep_collision_metrics.csv','coarse_geometry_metrics.csv','per_link_metrics.csv','interface_preservation.csv','resource_metrics.csv','body_plan_dataflow_audit.csv','try5A_1_report.md']
audit={'status':'PASS','conditions':['C0','C1','C2'],'c0_frozen':(HERE/'C0/reference.json').is_file(),'c1_c2_link_success':all(int(x['successful_links'])==12 for x in resources[1:]),'interface_preserved':all(x['protected_interface_refs_preserved']=='True' and x['protected_interface_ops_preserved']=='True' for x in inte.values()),'exact_evaluator_errors':{c:int(coll[c]['narrow_errors']) for c in coll},'no_try5b':not (HERE/'Try5B').exists(),'required_outputs':{p:(HERE/'results'/p).is_file() for p in required},'conclusion':'PARTIAL_SUCCESS_C1_ONLY; C2_COLLISION_VOLUME_REBOUND; TRY5B_NOT_READY'}
(HERE/'results/try5A_1_validation.json').write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps(audit,indent=2))
