"""Frozen deterministic Try-4 Phase-5 geometry, trace-feature and gate evaluator."""
import csv,hashlib,itertools,json
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from trimesh.registration import icp
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';RES=EXP/'results';CACHE=EXP/'evaluation_cache';PROTOCOL=EXP/'protocol/phase5_evaluator_v1.json'
CFG=json.loads(PROTOCOL.read_text(encoding='utf-8'));SEED=CFG['sampling']['seed'];N=CFG['sampling']['surface_points'];NA=CFG['sampling']['alignment_points']
def load(path):
    x=trimesh.load(path,force='scene',process=False);geoms=list(x.geometry.values()) if isinstance(x,trimesh.Scene) else [x];return trimesh.util.concatenate([g for g in geoms if len(g.faces)])
def sample(mesh,n,seed):
    state=np.random.get_state();np.random.seed(seed);p,_=trimesh.sample.sample_surface(mesh,n);np.random.set_state(state);return p
def rotations24():
    out=[]
    for perm in itertools.permutations(range(3)):
      for signs in itertools.product((-1,1),repeat=3):
        r=np.zeros((3,3));r[range(3),perm]=signs
        if np.linalg.det(r)>0.5:out.append(r)
    return out
def rigid_align(gt,pr,seed):
    a=sample(gt,NA,seed);b=sample(pr,NA,seed+1);ca=a.mean(0);cb=b.mean(0);aa=a-ca;bb=b-cb
    _,_,va=np.linalg.svd(np.cov(aa.T));_,_,vb=np.linalg.svd(np.cov(bb.T));best=None
    for q in rotations24():
        r=va.T@q@vb;t=ca-cb@r.T;x=bb@r.T+ca;d=cKDTree(aa).query(x,k=1)[0].mean()+cKDTree(x).query(aa,k=1)[0].mean()
        if best is None or d<best[0]:best=(d,r,t)
    m=np.eye(4);m[:3,:3]=best[1];m[:3,3]=best[2]
    m2,_,_=icp(b,a,initial=m,threshold=1e-7,max_iterations=40,reflection=False,scale=False);return m2
def distances(a,b):
    da=cKDTree(b).query(a,k=1)[0];db=cKDTree(a).query(b,k=1)[0];return da,db
def voxels(mesh,pitch,origin):
    v=mesh.voxelized(pitch).fill();pts=v.points;return {tuple(x) for x in np.rint((pts-origin)/pitch).astype(np.int32)}
def silhouette(ga,pa):
    scores=[]
    for axes in ((0,1),(1,2),(0,2)):
        all_cells=ga|pa;lo=np.min([[x[axes[0]],x[axes[1]]] for x in all_cells],axis=0);hi=np.max([[x[axes[0]]+1,x[axes[1]]+1] for x in all_cells],axis=0);span=np.maximum(hi-lo,1);res=CFG['sampling']['silhouette_grid']
        def raster(cells):
            mask=np.zeros((res,res),dtype=bool)
            for x in cells:
                a=np.array([x[axes[0]],x[axes[1]]],float);b=a+1
                i0=np.floor((a-lo)/span*res).astype(int);i1=np.ceil((b-lo)/span*res).astype(int);i0=np.clip(i0,0,res-1);i1=np.clip(i1,1,res)
                mask[i0[0]:i1[0],i0[1]:i1[1]]=True
            return mask
        g=raster(ga);p=raster(pa);union=np.logical_or(g,p).sum();scores.append(float(np.logical_and(g,p).sum()/union) if union else 1.)
    return scores
def trace_metrics(condition,pid):
    base=EXP/condition/pid/'round_0';data=json.loads((base/'agent_output.json').read_text());log=json.loads((base/'execution_log.json').read_text());ok={x['input_parameters']['feature_ref'] for x in log if x['success'] and not x['fallback_used']};features=data['feature_graph']['features'];realized=[f for f in features if f['status']!='UNIMPLEMENTED_VISIBLE_DETAIL' and f['feature_id'] in ok];critical=[f for f in features if f['critical']];cr=[f for f in realized if f['critical']]
    return len(realized)/len(features),len(realized)/max(1,len({x['input_parameters']['feature_ref'] for x in log if x['success']})),len(cr)/len(critical) if critical else 1.,len(features),len(realized)
def cad_ok(condition,pid):
    v=json.loads((EXP/condition/pid/'round_0/cad_validity.json').read_text());e=v.get('editability',{});return v['status']=='SUCCESS' and v.get('fallback_count')==0 and v.get('reopen',{}).get('status')=='PASS',bool(e.get('edited_valid') and e.get('restored_valid'))
def evaluate(condition,pid,gt_path,pred_path,index):
    gt=load(gt_path);pr=load(pred_path);xf=rigid_align(gt,pr,SEED+index*10);pr.apply_transform(xf);g=sample(gt,N,SEED+index*10+2);p=sample(pr,N,SEED+index*10+3);da,db=distances(g,p);diag=float(np.linalg.norm(gt.bounds[1]-gt.bounds[0]));ch=float((da.mean()+db.mean())/2);hd=float(max(np.percentile(da,95),np.percentile(db,95)));pitch=diag/CFG['sampling']['voxel_resolution_per_gt_bbox_diagonal'];origin=np.minimum(gt.bounds[0],pr.bounds[0])-pitch;gv=voxels(gt,pitch,origin);pv=voxels(pr,pitch,origin);iou=len(gv&pv)/len(gv|pv);sil=silhouette(gv,pv);mfr,prec,crit,nf,nr=trace_metrics(condition,pid);valid,editable=cad_ok(condition,pid);thr=CFG['quality_gate'];criteria={'cad_valid':valid,'editability':editable,'iou':iou>=thr['tau_iou_min'],'normalized_chamfer':ch/diag<=thr['tau_normalized_chamfer_max'],'normalized_hd95':hd/diag<=thr['tau_normalized_hd95_max'],'mfr':mfr>=thr['tau_mfr_min'],'critical_feature_recall':crit>=thr['critical_feature_recall_required']};status='PASS' if all(criteria.values()) else ('REPLAN' if iou<.15 or crit<.5 else 'LOCAL_REPAIR')
    return {'part_id':pid,'robot_id':pid[:3],'condition':condition,'alignment':'rigid_shape_only_no_scale','gt_bbox_diagonal_mm':diag,'voxel_pitch_mm':pitch,'voxel_iou':iou,'chamfer_mm':ch,'normalized_chamfer':ch/diag,'hd95_mm':hd,'normalized_hd95':hd/diag,'bbox_error_x_mm':abs((pr.bounds[1]-pr.bounds[0])[0]-(gt.bounds[1]-gt.bounds[0])[0]),'bbox_error_y_mm':abs((pr.bounds[1]-pr.bounds[0])[1]-(gt.bounds[1]-gt.bounds[0])[1]),'bbox_error_z_mm':abs((pr.bounds[1]-pr.bounds[0])[2]-(gt.bounds[1]-gt.bounds[0])[2]),'centroid_error_mm':float(np.linalg.norm(pr.centroid-gt.centroid)),'silhouette_iou_front':sil[0],'silhouette_iou_side':sil[1],'silhouette_iou_top':sil[2],'silhouette_iou_mean':float(np.mean(sil)),'mfr_trace':mfr,'mechanical_feature_precision_trace':prec,'critical_feature_recall_trace':crit,'feature_requirements':nf,'features_realized_trace':nr,'cad_valid':valid,'editability_pass':editable,'gate_status':status,'failed_criteria':';'.join(k for k,v in criteria.items() if not v)}
def write_csv(path,rows):
    with path.open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
    rows=[];idx=0
    for rid,count in [('R01',5),('R02',7)]:
      for i in range(count):
        pid=f'{rid}_P{i:02d}';conds=['T1']+(['T0'] if rid=='R01' else [])
        for cond in conds:
          rows.append(evaluate(cond,pid,CACHE/f'gt/{rid}/{pid}.stl',EXP/cond/pid/'round_0/model.stl',idx));idx+=1;print(cond,pid,rows[-1]['gate_status'],flush=True)
    write_csv(RES/'phase5_metrics.csv',rows);geom=[{k:v for k,v in r.items() if k not in ('mfr_trace','mechanical_feature_precision_trace','critical_feature_recall_trace','feature_requirements','features_realized_trace')} for r in rows];write_csv(RES/'geometry_metrics.csv',geom);write_csv(RES/'mechanical_feature_metrics.csv',[{k:r[k] for k in ('part_id','robot_id','condition','mfr_trace','mechanical_feature_precision_trace','critical_feature_recall_trace','feature_requirements','features_realized_trace')} for r in rows]);write_csv(RES/'editability_metrics.csv',[{k:r[k] for k in ('part_id','robot_id','condition','cad_valid','editability_pass','gate_status','failed_criteria')} for r in rows]);print(json.dumps({'evaluations':len(rows),'pass':sum(r['gate_status']=='PASS' for r in rows)}))
if __name__=='__main__':main()
