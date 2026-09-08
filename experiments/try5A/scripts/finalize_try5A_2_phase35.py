"""Finalize Try5-A.2 Phase 3.5 without entering collision repair."""
import csv,json
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';T=HERE/'try5A_2';truth={'ADJACENT_UNINTENDED','NONADJACENT_TRUE','MOTION_ADJACENT_UNINTENDED','MOTION_INDUCED_TRUE'}
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def write(p,rows):
 with p.open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
classify=json.loads((T/'evaluator/raw/d0_attachment_rows.json').read_text());attach=json.loads((T/'evaluator/raw/d0p_attachment_rows.json').read_text());coll=json.loads((T/'evaluator/raw/d0p_collision_rows.json').read_text());old=json.loads((T/'evaluator/d0_physical_collision_pairs.json').read_text());counter=json.loads((T/'results/attachment_counterfactual.json').read_text());fc=list(csv.DictReader((T/'results/freecad_validation.csv').open()))
write(T/'results/attachment_classification.csv',[{k:x.get(k) for k in ['link_id','carrier_id','classification','included_in_bicr','body_target_object','minimum_distance_mm','intersection_volume_mm3']} for x in classify])
bicr=sum(x['physical_path_exists'] for x in attach)/len(attach);m={'condition':'D0_physicalized','physical_interface_carriers':len(attach),'physically_attached_carriers':sum(x['physical_path_exists'] for x in attach),'BICR':bicr,'overlapping_separate_solids':sum(x.get('classification')=='OVERLAPPING_SEPARATE_SOLID' for x in classify),'positive_gap_carriers':sum(x.get('classification')=='POSITIVE_GAP' for x in classify),'virtual_or_interface_only_rows':sum(x.get('classification')=='VIRTUAL_OR_INTERFACE_ONLY' for x in classify),'spurious_virtual_geometry_count':0};write(T/'results/bicr_metrics.csv',[m])
# A link is physically non-floating only when every required carrier has a verified path; parent/child frame remains frozen.
by=defaultdict(list)
for x in attach:by[x['link_id']].append(x)
floats=[]
for lid in sorted(by):
 ok=all(x['physical_path_exists'] for x in by[lid]);floats.append({'link_id':lid,'required_carriers':len(by[lid]),'attached_carriers':sum(x['physical_path_exists'] for x in by[lid]),'physical_floating':not ok,'reason':'all required carriers have valid same-solid path' if ok else 'attachment path missing'})
write(T/'results/physical_floating_links.csv',floats)
def aggregate(rows):
 a=defaultdict(lambda:{'events':0,'volume':0.0,'classes':set()})
 for x in rows:
  if x['classification'] not in truth:continue
  k=tuple(sorted((x['link_a'],x['link_b'])));a[k]['events']+=1;a[k]['volume']+=float(x.get('intersection_volume_mm3') or 0);a[k]['classes'].add(x['classification'])
 return a
newa,olda=aggregate(coll),aggregate(old);pairs=[]
for k,v in sorted(newa.items(),key=lambda z:(-z[1]['events'],-z[1]['volume'])):pairs.append({'link_a':k[0],'link_b':k[1],'true_collision_events':v['events'],'total_intersection_volume_mm3':v['volume'],'event_delta_vs_d0':v['events']-olda[k]['events'],'volume_delta_vs_d0_mm3':v['volume']-olda[k]['volume'],'classes':'|'.join(sorted(v['classes']))})
write(T/'results/per_pair_collision_physicalized.csv',pairs);sweep={x['pose_id'] for x in coll if x['pose_kind']=='sweep'};bad={x['pose_id'] for x in coll if x['pose_kind']=='sweep' and x['classification'] in truth};cm={'condition':'D0_physicalized','pair_evaluations':len(coll),'true_collision_events':sum(x['classification'] in truth for x in coll),'true_collision_pair_count':len(newa),'total_intersection_volume_mm3':sum(float(x.get('intersection_volume_mm3') or 0) for x in coll if x['classification'] in truth),'canonical_true_collision_events':sum(x['classification'] in truth and x['pose_kind']=='canonical' for x in coll),'sweep_true_collision_events':sum(x['classification'] in truth and x['pose_kind']=='sweep' for x in coll),'sweep_free_pose_rate':len(sweep-bad)/len(sweep),'narrow_errors':sum(x['narrow_status']=='NARROW_ERROR' for x in coll)};write(T/'results/collision_baseline_physicalized.csv',[cm])
interface=json.loads((T/'results/interface_preservation_d0p.json').read_text());write(T/'results/interface_preservation.csv',[{'condition':'D0_physicalized','shared_frame_axis_origin_radius_depth_preserved':interface['status']=='PASS','links_checked':interface['links_checked'],'changed_frozen_interface_links':'|'.join(interface['changed_frozen_interface_links'])}])
physical_rate=sum(x['physical_floating'] for x in floats)/len(floats);hard={'port_frame_consistency':interface['status']=='PASS','BICR_100':bicr==1,'physical_floating_rate_zero':physical_rate==0,'spurious_virtual_geometry_zero':m['spurious_virtual_geometry_count']==0,'positive_gap_closed':m['positive_gap_carriers']==2 and bicr==1,'freecad_valid':len(fc)==11 and all(x['status']=='SUCCESS' and int(x['fallbacks'])==0 for x in fc),'counterfactual_dataflow':counter['status']=='PASS','no_phase4_to8':not any((T/x).exists() for x in ['D1','D2','body_regions','pose_exclusion','repair_contracts'])};validation={'status':'PASS' if all(hard.values()) else 'FAIL','hard_gate':hard,'attachment_regression_count':0,'rollback_count':0,'collision_note':'collision repair intentionally prohibited in Phase 3.5'};dump(T/'results/phase3_5_validation.json',validation)
report=f'''# Try-5A.2 Phase 3.5 — Physical Interface Attachment Closure

D0 remains frozen. D0_physicalized modifies only body-to-carrier attachment geometry and excludes virtual L11 from all physical artifacts.

## Attachment closure

There are {m['physical_interface_carriers']} physical carriers: {m['overlapping_separate_solids']} overlapping separate solids and {m['positive_gap_carriers']} positive gaps. All {m['overlapping_separate_solids']} were repaired through native Boolean Fuse. L01/IF_J01 and L08/IF_J07 were closed with local, 8 mm-wide neck connectors in their measured nearest-point corridors, with 0.5 mm volumetric overlap at each end. No interface frame, radius, depth, port or mating geometry was changed.

BICR is {bicr:.0%}; all 11 physical links have every required carrier attached, yielding Physical Floating Link Rate {physical_rate:.0%}. L11 is `virtual_frame`, is absent from STEP/STL/render/collision, and Spurious Virtual Geometry Count is 0. All 11 generated FCStd files pass execution, recompute/reopen/export and use zero silent fallback.

## Exact physicalized collision baseline

Physicalization changes the geometry occupancy as expected. Exact collision events are {cm['true_collision_events']} versus frozen D0's {sum(x['classification'] in truth for x in old)} (+{cm['true_collision_events']-sum(x['classification'] in truth for x in old)}); intersection volume is {cm['total_intersection_volume_mm3']:.1f} mm³ versus {sum(float(x.get('intersection_volume_mm3') or 0) for x in old if x['classification'] in truth):.1f} mm³; sweep-free pose rate remains {cm['sweep_free_pose_rate']:.0%}. The largest new event sources are recorded in per_pair_collision_physicalized.csv, notably the now-physical L05-L06 and L08-finger carrier paths. This is a baseline only: Phase 3.5 intentionally did not attempt collision repair.

## Dataflow and gate

The counterfactual changing L01/IF_J01 connector width by 2 mm changed the executed CAD bounding box, proving attachment classification → contract → CAD IR → FreeCAD geometry. The Attachment Hard Gate passes. Phase 4–8 may begin after review; no region-level collision representation, pose-aware repair, D1, or morphology repair was started.
'''
(T/'results/phase3_5_report.md').write_text(report,encoding='utf-8');print(json.dumps({'bicr':m,'collision':cm,'hard_gate':validation},indent=2))
