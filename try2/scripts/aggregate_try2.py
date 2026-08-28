from __future__ import annotations
import csv,json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
METRICS=('graph_f1','joint_type','axis','origin','motion','chamfer','voxel_iou')
def num(x):
 try:return float(x)
 except:return None
def main():
 rows=list(csv.DictReader((ROOT/'try2/results/case_results.csv').open()))
 agg=[]
 for c in 'ABCD':
  s=[r for r in rows if r['condition']==c];out={'condition':c,'denominator':len(s),'success':sum(r['status']=='SUCCESS' for r in s)}
  for m in METRICS:
   v=[num(r.get(m)) for r in s];v=[x for x in v if x is not None];out['median_'+m]=statistics.median(v) if v else None;out['mean_'+m]=statistics.mean(v) if v else None
  agg.append(out)
 outdir=ROOT/'try2/results'
 with (outdir/'aggregate_results.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(agg[0]));w.writeheader();w.writerows(agg)
 by={(r['condition'],r['case_id']):r for r in rows};effects=[]
 for name,left,right in [('fusion_no_urdf','A','B'),('fusion_with_urdf','C','D'),('urdf_primitive','A','C'),('urdf_fusion','B','D')]:
  for case in sorted({r['case_id'] for r in rows}):
   a,b=by.get((left,case)),by.get((right,case))
   if a and b and a['status']=='SUCCESS' and b['status']=='SUCCESS':
    for m in METRICS:
     x,y=num(a.get(m)),num(b.get(m))
     if x is not None and y is not None:effects.append({'effect':name,'case_id':case,'metric':m,'right_minus_left':y-x})
 with (outdir/'paired_effects.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=['effect','case_id','metric','right_minus_left']);w.writeheader();w.writerows(effects)
 (outdir/'try2_report.md').write_text('# Try-2 report\n\nDevelopment-only 2x2 experiment.\n\n```json\n'+json.dumps(agg,indent=2)+'\n```\n')
if __name__=='__main__':main()
