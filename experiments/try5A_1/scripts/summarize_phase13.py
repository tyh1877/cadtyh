"""Summarize frozen C0 broad/narrow collision baseline without replanning bodies."""
import csv,json,collections
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A_1';SRC=ROOT/'experiments/try5A';rows=json.loads((HERE/'collision_cache/c0_raw_pairs.json').read_text());true={'ADJACENT_UNINTENDED','NONADJACENT_TRUE','MOTION_ADJACENT_UNINTENDED','MOTION_INDUCED_TRUE'}
summary=[]
for kind in ('canonical','sweep'):
 x=[r for r in rows if r['pose_kind']==kind];b=[r for r in x if r['aabb_overlap']];t=[r for r in x if r['classification'] in true];summary.append({'scope':kind,'pair_evaluations':len(x),'aabb_candidates':len(b),'true_collision_events':len(t),'narrow_errors':sum(r['narrow_status']=='NARROW_ERROR' for r in x),'aabb_noncollision_rate':sum(r['classification'] in ('AABB_FALSE_POSITIVE','EXPECTED_INTERFACE') for r in b)/len(b),'aabb_false_positive_rate_excluding_expected':sum(r['classification']=='AABB_FALSE_POSITIVE' for r in b)/max(1,sum(not r['adjacent_urdf'] for r in b)),'collision_free_pose_rate':sum(not any(r['classification'] in true for r in x if r['pose_id']==pid) for pid in {r['pose_id'] for r in x})/len({r['pose_id'] for r in x})})
def write(name,data):
 with (HERE/'results'/name).open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
write('exact_collision_metrics.csv',summary)
agg=collections.defaultdict(lambda:{'events':0,'volume':0.0,'canonical':0,'sweep':0,'classification':set()})
for r in rows:
 if r['classification'] in true:
  k=tuple(sorted((r['link_a'],r['link_b'])));a=agg[k];a['events']+=1;a['volume']+=r.get('intersection_volume_mm3') or 0;a[r['pose_kind']]+=1;a['classification'].add(r['classification'])
pairs=[{'link_a':k[0],'link_b':k[1],'true_collision_events':v['events'],'total_intersection_volume_mm3':v['volume'],'canonical_events':v['canonical'],'sweep_events':v['sweep'],'classes':';'.join(sorted(v['classification']))} for k,v in agg.items()];pairs.sort(key=lambda x:(-x['true_collision_events'],-x['total_intersection_volume_mm3']));write('per_pair_collision.csv',pairs)
srcm=json.loads((SRC/'results/a2_common_interface_metrics.json').read_text())['summary'];(HERE/'results/interface_preservation.csv').write_text('condition,connected_joint_rate,floating_link_rate,mean_interface_gap_mm,mean_radius_mismatch_mm,excessive_axial_penetrations\nC0,{},{},{},{},{}\n'.format(srcm['connected_joint_rate'],srcm['floating_link_rate'],srcm['mean_interface_gap_mm'],srcm['mean_radius_mismatch_mm'],srcm['excessive_axial_penetrations']))
paths=[SRC/'inputs/images/isometric.png',SRC/'assemblies/A2/renders/isometric.png'];labels=['Reference','C0 frozen A2'];canvas=Image.new('RGB',(800,390),'white');d=ImageDraw.Draw(canvas)
for i,(p,l) in enumerate(zip(paths,labels)):
 im=Image.open(p).convert('RGB');im.thumbnail((370,340));canvas.paste(im,(i*400+(390-im.width)//2,35));d.text((i*400+10,8),l,fill='black')
(HERE/'contact_sheets').mkdir(exist_ok=True);canvas.save(HERE/'contact_sheets/C0_whole_robot.png')
print(json.dumps({'summary':summary,'true_pairs':len(pairs)}))
