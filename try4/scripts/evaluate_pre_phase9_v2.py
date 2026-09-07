"""Evaluate v2 pilot with frozen Phase-5 metrics plus topology/section/region diagnostics."""
import json,sys
from pathlib import Path
import numpy as np
from scipy.ndimage import label
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';sys.path.insert(0,str(EXP/'scripts'));from evaluate_phase5 import evaluate,load,rigid_align,sample,voxels,SEED,N,CFG
PIDS=['R01_P00','R02_P02','R02_P05','R02_P06'];rows=[]
def region_cd(g,p,axis,lo,hi,diag):
 gs=g[(g[:,axis]>=lo)&(g[:,axis]<=hi)];ps=p[(p[:,axis]>=lo)&(p[:,axis]<=hi)]
 if len(gs)<20 or len(ps)<20:return 1.0
 return float((cKDTree(ps).query(gs)[0].mean()+cKDTree(gs).query(ps)[0].mean())/2/diag)
for j,pid in enumerate(PIDS):
 idx=2*int(pid[-2:]) if pid.startswith('R01') else 10+int(pid[-2:]);gtp=EXP/f'evaluation_cache/gt/{pid[:3]}/{pid}.stl';prp=EXP/f'PRE_PHASE9_V2/{pid}/round_0/model.stl';base=evaluate('PRE_PHASE9_V2',pid,gtp,prp,idx);gt=load(gtp);pr=load(prp);pr.apply_transform(rigid_align(gt,pr,SEED+idx*10));diag=np.linalg.norm(gt.bounds[1]-gt.bounds[0]);g=sample(gt,N,SEED+idx*10+2);p=sample(pr,N,SEED+idx*10+3);axis=int(np.argmax(gt.bounds[1]-gt.bounds[0]));edges=np.linspace(gt.bounds[0,axis],gt.bounds[1,axis],4);regions=[region_cd(g,p,axis,edges[k],edges[k+1],diag) for k in range(3)];pitch=diag/64;origin=np.minimum(gt.bounds[0],pr.bounds[0])-pitch;gv=voxels(gt,pitch,origin);pv=voxels(pr,pitch,origin);allc=gv|pv;amin=min(x[axis] for x in gv);amax=max(x[axis] for x in gv)+1;bins=np.linspace(amin,amax,10);areas=[];components=[]
 for cells in (gv,pv):
  ar=[];co=[]
  other=[x for x in range(3) if x!=axis]
  for k in range(9):
   sl=[x for x in cells if bins[k]<=x[axis]<bins[k+1]];ar.append(len(sl))
   if sl:
    lo=np.min([[x[other[0]],x[other[1]]] for x in sl],0);hi=np.max([[x[other[0]],x[other[1]]] for x in sl],0);mask=np.zeros(hi-lo+1,dtype=bool)
    for x in sl:mask[x[other[0]]-lo[0],x[other[1]]-lo[1]]=1
    co.append(int(label(mask)[1]))
   else:co.append(0)
  areas.append(np.array(ar,float)/max(max(ar),1));components.append(np.array(co,float))
 base.update({'gt_connected_components':len(gt.split(only_watertight=False)),'generated_connected_components':len(pr.split(only_watertight=False)),'section_area_curve_mae':float(np.abs(areas[0]-areas[1]).mean()),'section_component_count_mae':float(np.abs(components[0]-components[1]).mean()),'regional_normalized_chamfer_proximal':regions[0],'regional_normalized_chamfer_body':regions[1],'regional_normalized_chamfer_distal':regions[2],'regional_normalized_chamfer_max':max(regions)});out=EXP/f'PRE_PHASE9_V2/{pid}/round_0/v2_metrics.json';out.write_text(json.dumps(base,indent=2)+'\n');rows.append(base);print(pid,base['gate_status'],round(base['section_area_curve_mae'],3),round(base['regional_normalized_chamfer_max'],3))
(EXP/'results/pre_phase9_v2_pilot_metrics.json').write_text(json.dumps(rows,indent=2)+'\n')
