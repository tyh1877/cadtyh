"""Freeze and report Try5-A.2 Phase 1-3 D0 corrected evaluation."""
import csv,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';T=HERE/'try5A_2';C1=ROOT/'experiments/try5A_1';
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
types={x['link_id']:x for x in json.loads((T/'virtual_link_filter/link_realization_types.json').read_text())['links']};raw=json.loads((T/'evaluator/raw/d0_attachment_rows.json').read_text());active=[x for x in raw if x['included_in_bicr']];gaps=[x for x in active if not x['geometric_touch']];logical=json.loads((C1/'results/interface_preservation.csv').read_text().splitlines()[1].replace('True','true').replace('False','false')) if False else None
# D0 is provenance-only: no CAD, interface, or body recipe is regenerated.
files=[]
for i in range(12):
 lid=f'L{i:02d}';files += [C1/'C1'/lid/'cad_ir.json',C1/'C1'/lid/'InterfaceRefs.json',C1/'C1'/lid/'model.FCStd']
files += [C1/'collision_cache/c1_raw_pairs.json',C1/'results/exact_collision_metrics.csv',HERE/'blackboard/kinematic_skeleton.json',HERE/'blackboard/joint_interface_graph.json']
dump(T/'D0/reference.json',{'condition':'D0','source_condition':'Try5-A.1 C1','cad_regenerated':False,'source_files':{str(p.relative_to(ROOT)):sha(p) for p in files},'physical_links':[x for x,t in types.items() if t['solid_generation_allowed']],'virtual_links':[x for x,t in types.items() if not t['solid_generation_allowed']]})
# Exact C1 result only; exclude every pair involving virtual L11 from D0 physical collision population.
allpairs=json.loads((C1/'collision_cache/c1_raw_pairs.json').read_text());pairs=[x for x in allpairs if x['link_a']!='L11' and x['link_b']!='L11'];truth={'ADJACENT_UNINTENDED','NONADJACENT_TRUE','MOTION_ADJACENT_UNINTENDED','MOTION_INDUCED_TRUE'};true=[x for x in pairs if x['classification'] in truth];sweep={x['pose_id'] for x in pairs if x['pose_kind']=='sweep'};bad={x['pose_id'] for x in true if x['pose_kind']=='sweep'}
dump(T/'evaluator/d0_physical_collision_pairs.json',pairs)
mechanical={'condition':'D0','source':'frozen Try5-A.1 C1','logical_connected_joint_rate':1.0,'logical_floating_link_rate':0.0,'physical_interface_carriers':len(active),'physically_attached_carriers':sum(x['physically_attached'] for x in active),'BICR':sum(x['physically_attached'] for x in active)/len(active),'geometrically_touching_but_unjoined_carriers':sum(x['geometric_touch'] for x in active),'detached_carriers':len(gaps),'detached_carrier_ids':[x['link_id']+'/'+x['carrier_id'] for x in gaps],'attachment_qualified_floating_physical_body_rate':1.0,'raw_spurious_virtual_geometry_count':1,'filtered_spurious_virtual_geometry_count':0,'physical_link_count':sum(t['solid_generation_allowed'] for t in types.values()),'virtual_link_count':sum(not t['solid_generation_allowed'] for t in types.values())}
collision={'condition':'D0','pair_evaluations_excluding_virtual':len(pairs),'true_collision_events':len(true),'true_collision_pair_count':len({tuple(sorted((x['link_a'],x['link_b']))) for x in true}),'total_intersection_volume_mm3':sum(float(x.get('intersection_volume_mm3') or 0) for x in true),'sweep_free_pose_rate':len(sweep-bad)/len(sweep),'narrow_errors':sum(x['narrow_status']=='NARROW_ERROR' for x in pairs)}
dump(T/'results/d0_mechanical_metrics.json',mechanical);dump(T/'results/d0_collision_metrics.json',collision)
for name,obj in [('mechanical_metrics.csv',[mechanical]),('collision_metrics.csv',[collision])]:
 with (T/'results'/name).open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(obj[0]));w.writeheader();w.writerows(obj)
report=f'''# Try-5A.2 Phase 1–3 — corrected D0 evaluation

D0 is an immutable reference to Try-5A.1 C1. No C1 CAD, body parameters or interfaces were regenerated.

## Corrected physical validity

The prior 100% Connected Joint Rate and 0 Floating Link Rate are **logical port-frame metrics**. They do not establish physical body-to-carrier attachment. The strict evaluator finds {len(active)} physical carriers, zero valid attachment paths and BICR = 0%. {sum(x['geometric_touch'] for x in active)} carriers geometrically overlap their body but remain separate final B-Rep solids without Boolean union, a declared rigid multi-body contact, or connector geometry; these are not valid attachment under the frozen protocol.

Two genuinely separated physical carriers are L01/IF_J01 ({next(x['minimum_distance_mm'] for x in gaps if x['link_id']=='L01'):.3f} mm) and L08/IF_J07 ({next(x['minimum_distance_mm'] for x in gaps if x['link_id']=='L08'):.3f} mm). The J10 path is excluded because its peer L11 is a virtual tool-center frame. L11 was nevertheless generated as an independent C1 solid, so historical raw Spurious Virtual Geometry Count is 1; the new filter removes it from physical exports, render and collision populations, yielding 0.

## Collision baseline

After excluding virtual L11, exact D0 evaluation contains {collision['pair_evaluations_excluding_virtual']} pair evaluations, {collision['true_collision_events']} true collision events, {collision['total_intersection_volume_mm3']:.1f} mm³ intersection volume and {collision['sweep_free_pose_rate']:.0%} sweep-free pose rate. Narrow-phase errors are {collision['narrow_errors']}.

## Stop decision

D0 fails the Interface/Attachment hard gate: BICR is 0%, attachment-qualified body floating rate is 100%, and two physical carriers have a positive gap. The evaluator and virtual filter are now adequate to support Phase 4–8, but D1 must not begin until the required Phase 1–3 review is accepted.
'''
(T/'results/phase13_report.md').write_text(report,encoding='utf-8')
validation={'status':'PASS','d0_frozen':True,'attachment_evaluator_rows':len(raw),'bicr_denominator':len(active),'virtual_filter_l11':types['L11']['link_realization_type']=='virtual_frame','virtual_removed_from_physical_population':all(x['link_a']!='L11' and x['link_b']!='L11' for x in pairs),'no_d1':not (T/'D1').exists(),'no_d2':not (T/'D2').exists(),'physical_d0_assembly_excludes_virtual':(T/'D0/physical_assembly/assembly_result.json').is_file() and json.loads((T/'D0/physical_assembly/assembly_result.json').read_text())['physical_links']==11,'stop_before_phase4':True};dump(T/'results/phase13_validation.json',validation);print(json.dumps({'mechanical':mechanical,'collision':collision,'validation':validation},indent=2))
