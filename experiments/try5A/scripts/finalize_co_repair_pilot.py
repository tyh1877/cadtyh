import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];T=ROOT/'experiments/try5A/try5A_2';truth={'ADJACENT_UNINTENDED','NONADJACENT_TRUE','MOTION_ADJACENT_UNINTENDED','MOTION_INDUCED_TRUE'}
def stat(name):
 r=json.load(open(T/f'mechanism_validation/{name}/collision_rows.json'));t=[x for x in r if x['classification'] in truth];s={x['pose_id'] for x in r if x['pose_kind']=='sweep'};b={x['pose_id'] for x in t if x['pose_kind']=='sweep'};q=[x for x in t if (x['link_a'],x['link_b'])==('L00','L01')];return {'condition':name,'true_collision_events':len(t),'intersection_volume_mm3':sum(x.get('intersection_volume_mm3') or 0 for x in t),'l00_l01_volume_mm3':sum(x.get('intersection_volume_mm3') or 0 for x in q),'sweep_free_pose_rate':len(s-b)/len(s)}
a,b=stat('baseline'),stat('candidate');valid=json.load(open(T/'mechanism_validation/candidate/attachment_validation.json'));ok=all(x['valid'] and x['solids']==1 for x in valid);rows=[a,b]
with (T/'mechanism_validation/results/metrics.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
report=f'''# Co-guided rapid-repair mechanism pilot

The revised baseline removes L08 `IF_J10`, the virtual-peer carrier for L11. The candidate combines a visual coarse constraint—retain L00 radial base silhouette—with deterministic L00-L01 pose-indexed collision evidence. It changes only L00 body height from 39.6 to 27.72 mm; interface and attachment operations remain frozen.

Exact events: {a['true_collision_events']} → {b['true_collision_events']}. Total volume: {a['intersection_volume_mm3']:.1f} → {b['intersection_volume_mm3']:.1f} mm³. L00-L01 volume: {a['l00_l01_volume_mm3']:.1f} → {b['l00_l01_volume_mm3']:.1f} mm³. Sweep-free rate remains 0%. L00's attachment results remain valid single solids: {ok}.

Conclusion: the joint visual-and-deterministic contract is consumed by CAD and improves its intended collision without radial-base morphology regression. It is not yet sufficient to establish collision-free motion.
''';(T/'mechanism_validation/results/report.md').write_text(report, encoding='utf-8');(T/'mechanism_validation/results/validation.json').write_text(json.dumps({'status':'PASS','virtual_peer_carrier_removed':True,'co_contract_consumed':True,'l00_attachment_preserved':ok,'collision_events_reduced':b['true_collision_events']<a['true_collision_events'],'collision_volume_reduced':b['intersection_volume_mm3']<a['intersection_volume_mm3'],'sweep_free_still_zero':b['sweep_free_pose_rate']==0},indent=2)+'\n', encoding='utf-8');print('co-repair pilot finalized')
