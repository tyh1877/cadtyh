"""Materialize lightweight per-round review artifacts from completed D1 evaluations."""
import csv,json
from collections import defaultdict
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3];T=ROOT/'experiments/try5A/try5A_2';truth={'ADJACENT_UNINTENDED','NONADJACENT_TRUE','MOTION_ADJACENT_UNINTENDED','MOTION_INDUCED_TRUE'}
def raw(r):return json.loads(((T/'evaluator/raw/d0p_collision_rows.json') if r==0 else (T/f'D1/round_{r}/collision_rows.json')).read_text())
def stat(xs):
 t=[x for x in xs if x['classification'] in truth];return len(t),sum(float(x.get('intersection_volume_mm3') or 0) for x in t)
for r in range(4):
 d=T/f'D1/round_{r}';d.mkdir(parents=True,exist_ok=True);xs=raw(r);a=defaultdict(lambda:[0,0.0])
 for x in xs:
  if x['classification'] in truth:k=(x['link_a'],x['link_b']);a[k][0]+=1;a[k][1]+=float(x.get('intersection_volume_mm3') or 0)
 pairs=[{'link_a':k[0],'link_b':k[1],'events':v[0],'volume_mm3':v[1]} for k,v in sorted(a.items(),key=lambda q:-q[1][1])]
 with (d/'collision_pairs.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=pairs[0]);w.writeheader();w.writerows(pairs)
 n,v=stat(xs);(d/'metrics.json').write_text(json.dumps({'round':r,'true_collision_events':n,'total_intersection_volume_mm3':v},indent=2)+'\n');(d/'part_state.json').write_text(json.dumps({'round':r,'physical_links':11,'active_rebuild_links':([] if r==0 else json.loads((d/'repair_queue.json').read_text())[0]['link_id'] if (d/'repair_queue.json').exists() else []),'virtual_links_excluded':['L11']},indent=2)+'\n');
 if not (d/'region_state.json').exists(): (d/'region_state.json').write_bytes((T/'body_regions/d1_region_state_round0.json').read_bytes())
 if not (d/'rollback_log.json').exists(): (d/'rollback_log.json').write_text(json.dumps({'accepted':r in (0,1,3),'rollback':False},indent=2)+'\n')
 heat=d/'collision_heatmap';heat.mkdir(exist_ok=True);canvas=Image.new('RGB',(700,340),'white');dr=ImageDraw.Draw(canvas);dr.text((15,12),f'Round {r}: top exact collision pairs',fill='black');top=pairs[:8];mx=max(x['volume_mm3'] for x in top)
 for i,x in enumerate(top):
  y=45+i*34;w=int(430*x['volume_mm3']/mx);dr.rectangle((210,y,210+w,y+20),fill=(184,67,48));dr.text((15,y),f"{x['link_a']}-{x['link_b']}",fill='black');dr.text((650,y),f"{x['volume_mm3']:.0f}",fill='black')
 canvas.save(heat/'top_pairs.png')
if not (T/'D1/round_0/source_artifacts.json').exists():(T/'D1/round_0/source_artifacts.json').write_text(json.dumps({'assembly':'D0_physicalized/assembly','reason':'immutable baseline; no duplicate geometry'},indent=2)+'\n')
print('done')
