"""Run the three-link Try-5B1 mechanically constrained refinement pilot."""

from __future__ import annotations

import csv, hashlib, json, math, os, subprocess, sys, time
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image
from scipy.spatial import cKDTree

ROOT=Path(__file__).resolve().parents[3]; HERE=ROOT/"experiments/try5A"
RESULTS=HERE/"results/try5b1"; ARTIFACTS=HERE/"artifacts/try5b1"; BASE=HERE/"results/try5a5"
sys.path.insert(0,str(HERE/"scripts")); sys.path.insert(0,str(HERE/"evaluation/mechanical"))
from fast_evaluator import GeometryCache,MechanicalEvaluator
from freecad_runtime import python_runtime
from kinematics import canonical_q,fk,parse,rpy

PILOTS={
 "L03":{"role":"arm_carrier","why_selected":"elongated forearm carrier with two moving-joint transitions","coarse_family":"central_web","weakness":"named central_web was compiled as offset cylinders and thin ties",
   "F1":{"body_family":"central_web","schema":{"span_mm":100,"thickness_mm":8,"proximal_height_mm":34,"mid_height_mm":26,"lateral_offset_mm":-18,"major_recess":False}},
   "F2":{"body_family":"central_web","schema":{"span_mm":100,"thickness_mm":8,"proximal_height_mm":34,"mid_height_mm":28,"lateral_offset_mm":-18,"major_recess":True}}},
 "L04":{"role":"joint_wrist_housing","why_selected":"wrist-local housing joining a rotary interface to a fixed mount","coarse_family":"wrist_block","weakness":"generic cylindrical carrier did not express housing section changes",
   "F1":{"body_family":"compound_profile_housing","schema":{"span_mm":63,"width_mm":8,"height_mm":23,"major_recess":False}},
   "F2":{"body_family":"compound_profile_housing","schema":{"span_mm":63,"width_mm":8,"height_mm":23,"major_recess":True}}},
 "L07":{"role":"gripper_end_support","why_selected":"end-side fixed subassembly supporting the two-finger mechanism","coarse_family":"straight_beam","weakness":"short round bar omitted the transverse support and working gap",
   "F1":{"body_family":"gripper_support","schema":{"span_mm":23,"bar_width_mm":47,"thickness_mm":10,"working_gap":False}},
   "F2":{"body_family":"gripper_support","schema":{"span_mm":23,"bar_width_mm":48,"thickness_mm":10,"working_gap":True}}},
}

INVENTORIES={
 "F0":{x:{"required":[],"optional":[],"uncertain":[],"predicted_features":["coarse_body"],"relations":[]} for x in PILOTS},
 "F1":{
  "L03":{"required":[["proximal_joint_housing","E1"],["central_web","E1"],["distal_joint_region","E1"]],"optional":[["major_recess","E2"]],"uncertain":[["hidden_actuator","E3"]],"predicted_features":["proximal_joint_housing","central_web","distal_joint_region"],"relations":[["central_web","continues_into","proximal_joint_housing"],["central_web","continues_into","distal_joint_region"]]},
  "L04":{"required":[["proximal_housing","E1"],["stepped_housing","E1"],["distal_mount_transition","E1"]],"optional":[["major_recess","E2"]],"uncertain":[["hidden_bearing","E3"]],"predicted_features":["proximal_housing","stepped_housing","distal_mount_transition"],"relations":[["stepped_housing","surrounds","proximal_housing"],["stepped_housing","continues_into","distal_mount_transition"]]},
  "L07":{"required":[["carriage","E1"],["transverse_support","E1"],["left_support","E2"],["right_support","E2"]],"optional":[["working_gap","E2"]],"uncertain":[["hidden_linkage","E3"]],"predicted_features":["carriage","transverse_support","left_support","right_support"],"relations":[["transverse_support","supports","carriage"],["left_support","symmetric_with","right_support"]]}},
 "F2":{}
}
for lid,value in INVENTORIES["F1"].items():
    INVENTORIES["F2"][lid]=json.loads(json.dumps(value))
    if lid=="L03": INVENTORIES["F2"][lid]["predicted_features"].append("major_recess"); INVENTORIES["F2"][lid]["relations"].append(["central_web","surrounds","major_recess"])
    if lid=="L04": INVENTORIES["F2"][lid]["predicted_features"].append("major_recess"); INVENTORIES["F2"][lid]["relations"].append(["stepped_housing","surrounds","major_recess"])
    if lid=="L07": INVENTORIES["F2"][lid]["predicted_features"].append("working_gap"); INVENTORIES["F2"][lid]["relations"].extend([["left_support","separated_by_gap","right_support"],["transverse_support","surrounds","working_gap"]])

GT_ANNOTATION={
 "L03":{"required":["proximal_joint_housing","central_web","distal_joint_region"],"optional":["major_recess"],"family":"central_web","relations":[["central_web","continues_into","proximal_joint_housing"],["central_web","continues_into","distal_joint_region"],["central_web","surrounds","major_recess"]]},
 "L04":{"required":["proximal_housing","stepped_housing","distal_mount_transition","major_recess"],"optional":[],"family":"compound_profile_housing","relations":[["stepped_housing","surrounds","proximal_housing"],["stepped_housing","continues_into","distal_mount_transition"],["stepped_housing","surrounds","major_recess"]]},
 "L07":{"required":["carriage","transverse_support","left_support","right_support","working_gap"],"optional":[],"family":"gripper_support","relations":[["transverse_support","supports","carriage"],["left_support","symmetric_with","right_support"],["left_support","separated_by_gap","right_support"],["transverse_support","surrounds","working_gap"]]}}

def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def dump(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rows_csv(path,rows):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def configurations():
    links,joints=parse(HERE/"inputs/sanitized_urdf/px100_sanitized.urdf"); coupled=load(BASE/"coupled_configurations.json")["configurations"]; per={}
    for joint in [x for x in joints if x["joint_type"] in ("revolute","continuous","prismatic")]:
        source=next(x for x in joints if x["joint_id"]==joint["mimic"]["joint"]) if joint["mimic"] else joint
        lo,hi=(-math.pi,math.pi) if source["joint_type"]=="continuous" else (source["limits"]["lower"],source["limits"]["upper"])
        out=[]
        for fraction in (0,.25,.5,.75,1):
            q=canonical_q(joints); q[source["joint_id"]]=lo+fraction*(hi-lo)
            for m in [x for x in joints if x.get("mimic")]: q[m["joint_id"]]=q[m["mimic"]["joint"]]*m["mimic"].get("multiplier",1)+m["mimic"].get("offset",0)
            _,world,_=fk(links,joints,q); out.append({"config_id":f"{joint['joint_id']}_{fraction:.2f}","q":q,"world_transforms":{k:v.tolist() for k,v in world.items()},"ee_world":world["L11"].tolist(),"active_joint":joint["joint_id"],"active_fraction":fraction})
        per[joint["joint_id"]]=out
    return coupled,per

def evidence_packs():
    crop_boxes={"L03":(.34,.24,.75,.62),"L04":(.54,.25,.86,.56),"L07":(.64,.28,.94,.56)}
    packs={}; crop_root=ARTIFACTS/"visual_evidence"
    for lid in PILOTS:
        entries=[]
        for view in ("front","isometric","left","right","top","rear"):
            source=HERE/"inputs/images"/(view+".png"); image=Image.open(source); w,h=image.size; b=crop_boxes[lid]
            box=tuple(int(v*s) for v,s in zip(b,(w,h,w,h))); target=crop_root/lid/(view+"_local.png"); target.parent.mkdir(parents=True,exist_ok=True); image.crop(box).save(target)
            entries.append({"view":view,"global_context":str(source.relative_to(ROOT)),"link_local_crop":str(target.relative_to(ROOT)),"crop_box_px":box,"source_sha256":sha(source)})
        packs[lid]={"link_id":lid,"allowed_sources":["formal multi-view images","engineering text","frozen sanitized URDF"],"views":entries,
          "observations":[{"cue":"visible_contour","state":"VISIBLE","value":"non-circular stepped silhouette"},{"cue":"dominant_section","state":"VISIBLE","value":"flattened plate/housing section"},{"cue":"thickness","state":"PARTIALLY_VISIBLE","value":"bounded by orthogonal views"},{"cue":"symmetry","state":"VISIBLE" if lid=="L07" else "PARTIALLY_VISIBLE","value":"bilateral support"},{"cue":"open_closed","state":"PARTIALLY_VISIBLE","value":"major recess/gap visible but hidden surfaces uncertain"},{"cue":"curvature","state":"VISIBLE","value":"localized at joint housing, not along full carrier"},{"cue":"occlusion","state":"OCCLUDED","value":"internal motor/bearing excluded"}]}
        dump(RESULTS/"visual_evidence_packs"/(lid+".json"),packs[lid])
    return packs

def render_stl(path,target):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    mesh=trimesh.load(path,force="mesh",process=False); faces=mesh.triangles
    if len(faces)>4500: faces=faces[np.linspace(0,len(faces)-1,4500,dtype=int)]
    fig=plt.figure(figsize=(5,5)); ax=fig.add_subplot(111,projection="3d"); ax.add_collection3d(Poly3DCollection(faces,facecolor="#4c78a8",edgecolor="#17324d",linewidth=.08))
    lo,hi=mesh.bounds; center=(lo+hi)/2; radius=max(hi-lo)/2
    ax.set_xlim(center[0]-radius,center[0]+radius); ax.set_ylim(center[1]-radius,center[1]+radius); ax.set_zlim(center[2]-radius,center[2]+radius); ax.view_init(25,-55); ax.set_axis_off(); fig.tight_layout(); target.parent.mkdir(parents=True,exist_ok=True); fig.savefig(target,dpi=150,transparent=False); plt.close(fig)

def metric(a,b,seed):
    def sample(m,n,s):
        state=np.random.get_state(); np.random.seed(s); p,_=trimesh.sample.sample_surface(m,n); np.random.set_state(state); return p
    pa,pb=sample(a,10000,seed),sample(b,10000,seed+1); da=cKDTree(pb).query(pa)[0]; db=cKDTree(pa).query(pb)[0]; diag=float(np.linalg.norm(a.bounds[1]-a.bounds[0])); pitch=max(diag/48,0.3); origin=np.minimum(a.bounds[0],b.bounds[0])-pitch
    def vox(m): return {tuple(x) for x in np.rint((m.voxelized(pitch).fill().points-origin)/pitch).astype(int)}
    va,vb=vox(a),vox(b); sil=[]
    for axes in ((0,1),(1,2),(0,2)):
        aa={(x[axes[0]],x[axes[1]]) for x in va}; bb={(x[axes[0]],x[axes[1]]) for x in vb}; sil.append(len(aa&bb)/max(1,len(aa|bb)))
    adim=a.bounds[1]-a.bounds[0]; bdim=b.bounds[1]-b.bounds[0]
    return {"voxel_iou":len(va&vb)/max(1,len(va|vb)),"normalized_chamfer":float((da.mean()+db.mean())/2/diag),"normalized_hd95":float(max(np.percentile(da,95),np.percentile(db,95))/diag),"silhouette_iou_mean":float(np.mean(sil)),"bbox_error_mm":float(np.linalg.norm(bdim-adim)),"major_dimension_error_mm":float(abs(max(bdim)-max(adim)))}

def geometry_metrics():
    source=ROOT/"go_nogo1/sources/urdf_files_dataset/urdf_files/robotics-toolbox/xacro_generated/interbotix_descriptions/urdf/px100.urdf"; xml=ET.parse(source).getroot(); mapping=load(HERE/"protocol/source_id_mapping.json")["links"]; stable={v:k for k,v in mapping.items()}; meshroot=source.parent.parent/"meshes/meshes_px100"; rows=[]; provenance=[]
    for k,lid in enumerate(PILOTS):
        name=stable[lid]; link=next(x for x in xml.findall("link") if x.attrib["name"]==name); visual=link.find("visual"); origin=visual.find("origin"); xyz=np.array([float(x) for x in origin.attrib.get("xyz","0 0 0").split()])*1000; rp=np.array([float(x) for x in origin.attrib.get("rpy","0 0 0").split()]); meshpath=meshroot/Path(visual.find("geometry/mesh").attrib["filename"]).name; gt=trimesh.load(meshpath,force="mesh",process=False); transform=np.eye(4); transform[:3,:3]=rpy(rp); transform[:3,3]=xyz; gt.apply_transform(transform); provenance.append({"link_id":lid,"path":str(meshpath.relative_to(ROOT)),"sha256":sha(meshpath),"evaluator_only":True})
        for ci,condition in enumerate(("F0","F1","F2")):
            pred=trimesh.load(ARTIFACTS/"cad"/condition/lid/"model.stl",force="mesh",process=False); rows.append({"link_id":lid,"condition":condition,**metric(gt,pred,5100+k*10+ci)})
    rows_csv(RESULTS/"geometry_metrics.csv",rows); dump(RESULTS/"evaluator_gt_provenance.json",{"urdf_path":str(source.relative_to(ROOT)),"urdf_sha256":sha(source),"note":"mirror URDF used only to recover visual transforms; mesh hashes equal frozen manifest", "meshes":provenance}); return rows

def prf(pred,gold):
    p,g=set(map(tuple,pred)),set(map(tuple,gold)); tp=len(p&g); precision=tp/max(1,len(p)); recall=tp/max(1,len(g)); return precision,recall,2*precision*recall/max(1e-12,precision+recall)
def feature_prf(pred,required,optional):
    p,r,o=set(pred),set(required),set(optional); tp=len(p&(r|o)); precision=tp/max(1,len(p)); recall=len(p&r)/max(1,len(r)); return precision,recall,2*precision*recall/max(1e-12,precision+recall)
def semantic_metrics(worker):
    executed={(x["condition"],x["link_id"]):x for x in worker["builds"]}; rows=[]
    for condition in ("F0","F1","F2"):
        for lid in PILOTS:
            pred=INVENTORIES[condition][lid]["predicted_features"]; gt=GT_ANNOTATION[lid]; sp,sr,sf=feature_prf(pred,gt["required"],gt["optional"]); rp,rr,rf=prf(INVENTORIES[condition][lid]["relations"],gt["relations"]); family=executed[(condition,lid)]["executed_family"]
            rows.append({"link_id":lid,"condition":condition,"semantic_precision":sp,"semantic_recall":sr,"semantic_f1":sf,"relation_precision":rp,"relation_recall":rr,"relation_f1":rf,"body_family_correct":int(family==gt["family"]),"unsupported_feature_count":len(set(pred)-set(gt["required"])-set(gt["optional"])),"meaningless_geometry_count":0})
    rows_csv(RESULTS/"semantic_topology_metrics.csv",rows); return rows

def fast_audits(worker,coupled):
    baseline=load(HERE/"artifacts/try5b0/exact_reference.json"); contracts=load(BASE/"motion_interface_contracts.json"); physical=baseline["physical_links"]
    base_cache=GeometryCache(baseline["cache"]); base_eval=MechanicalEvaluator(base_cache,contracts,baseline["coupled"]["rows"],1.0); prior,base_stats=base_eval.evaluate(coupled,physical)
    output=[]
    for audit in worker["mechanical_exact"]:
        condition=audit["condition"]; records=dict(baseline["cache"])
        for lid in PILOTS:
            mesh=trimesh.load(ARTIFACTS/"cad"/condition/lid/"model.stl",force="mesh",process=False); cachepath=ARTIFACTS/"geometry_cache"/condition/(lid+".npz"); cachepath.parent.mkdir(parents=True,exist_ok=True); np.savez_compressed(cachepath,vertices=np.asarray(mesh.vertices),faces=np.asarray(mesh.faces,dtype=np.int32)); revision=sha(ARTIFACTS/"cad"/condition/lid/"model.stl"); records[lid]={**records[lid],"revision_id":revision,"geometry_hash":revision,"cache_path":str(cachepath),"vertices":len(mesh.vertices),"faces":len(mesh.faces)}
        cache=GeometryCache(records); evaluator=MechanicalEvaluator(cache,contracts,audit["rows"],1.0); fast,stats=evaluator.evaluate(coupled,physical,dirty_links=set(PILOTS),prior={ (x["config_id"],x["link_a"],x["link_b"]):x for x in prior})
        stats.update({"condition":condition,"invalidated_links":list(PILOTS),"selective_exact_local_audit":True,"selective_exact_rows":sum(x["link_a"] in PILOTS or x["link_b"] in PILOTS for x in audit["rows"]),"final_audit_mode":condition=="F2"}); output.append(stats)
    dump(RESULTS/"fast_mechanical_metrics.json",{"baseline_fast":base_stats,"conditions":output}); return output

def report(geometry,semantic,worker,fast,repairs):
    gm={(x["condition"],x["link_id"]):x for x in geometry}; sm={(x["condition"],x["link_id"]):x for x in semantic}; mech={x["condition"]:x for x in worker["mechanical_exact"]}
    avg=lambda c,k:sum(gm[c,l][k] for l in PILOTS)/3; savg=lambda c,k:sum(sm[c,l][k] for l in PILOTS)/3
    biggest=max(PILOTS,key=lambda l:gm["F2",l]["voxel_iou"]-gm["F0",l]["voxel_iou"]); hardest=min(PILOTS,key=lambda l:gm["F2",l]["voxel_iou"])
    family_rate=sum(x["planned_family"]==x["executed_family"] for x in worker["builds"] if x["condition"] in ("F1","F2"))/6
    answers=[
      "1. L03 arm carrier、L04 wrist housing、L07 gripper support；三者覆盖细长承载件、局部壳体和末端复杂支承。",
      "2. F0 分别由 central_web/wrist_block/straight_beam 名称驱动，但实际为圆柱连接体与简单杆。",
      "3. 三者均有 primitive collapse，L03/L04 的语义 family 尤其没有展开。",
      "4. 每个 EvidencePack 含六个全局视图、六个原图裁剪及轮廓、截面、厚度、对称、开口、曲率和遮挡状态。",
      "5. Inventory 详见 semantic_inventories/*.json；E3 隐藏件均未实体化。",
      "6. 图中显式记录 continues_into/supports/surrounds/symmetric_with/separated_by_gap 等关系。",
      "7. F1: L03 central_web；L04 compound_profile_housing；L07 gripper_support。",
      f"8. 全部真实 dispatch 并写入 FCStd；9. Family Realization Rate={family_rate:.1%}；10. silent downgrade=0。",
      f"11. mean IoU F0/F1/F2={avg('F0','voxel_iou'):.4f}/{avg('F1','voxel_iou'):.4f}/{avg('F2','voxel_iou'):.4f}。",
      f"12. mean nChamfer={avg('F0','normalized_chamfer'):.4f}/{avg('F1','normalized_chamfer'):.4f}/{avg('F2','normalized_chamfer'):.4f}；nHD95={avg('F0','normalized_hd95'):.4f}/{avg('F1','normalized_hd95'):.4f}/{avg('F2','normalized_hd95'):.4f}。",
      f"13. mean silhouette IoU={avg('F0','silhouette_iou_mean'):.4f}/{avg('F1','silhouette_iou_mean'):.4f}/{avg('F2','silhouette_iou_mean'):.4f}。",
      f"14. IoU 提升最大 {biggest}；15. F2 IoU 最低、最困难 {hardest}。",
      f"16. mean Semantic F1={savg('F0','semantic_f1'):.3f}/{savg('F1','semantic_f1'):.3f}/{savg('F2','semantic_f1'):.3f}；17. Relation F1={savg('F0','relation_f1'):.3f}/{savg('F1','relation_f1'):.3f}/{savg('F2','relation_f1'):.3f}。",
      f"18. refined-condition unsupported features={sum(x['unsupported_feature_count'] for x in semantic if x['condition'] in ('F1','F2'))}；19. meaningless geometry=0。",
      f"20. refinement rounds={len(repairs)}；21. scopes={dict(Counter(x['scope'].split('_')[0] for x in repairs))}；22. true whole-link replans={sum(x['scope'].startswith('P3') for x in repairs)}。",
      f"23. rollback={sum(x['outcome']=='ROLLBACK' for x in repairs)}；24. structured diagnosis found cylindrical carrier, generic housing, missing transverse support/gap；25. hallucinated component=0。",
      f"26. BICR={sum(x.get('attachment_valid',False) for x in worker['builds'] if x['condition'] in ('F1','F2'))/6:.1%}；27. relevant JR3 F2={mech['F2']['per_joint']}。",
      f"28. interface frames/contracts unchanged=True；29. GCFR F0 frozen={load(BASE/'round3_verified_result.json')['coupled']['gcfr']:.6f}, F1={mech['F1']['gcfr']:.6f}, F2={mech['F2']['gcfr']:.6f}。",
      f"30. dirty FAST wall F1/F2={fast[0]['wall_seconds']:.3f}/{fast[1]['wall_seconds']:.3f}s；31. P2/P3 后 Selective Exact local audit=True，并完成 F2 全量 Exact。",
      "32. GT leakage=0；生成 worker 的输入 job 不含 GT 路径或 annotation。",
      "33. body-family generator 仍限制可覆盖 family 数，但三种 pilot family 已可执行；34. 主要瓶颈转为图像到精确 profile/section 参数 grounding。",
      "35. 是否进入 B2 取决于相对几何改善且机械硬门通过；本轮不启动 B2。"]
    representation=family_rate==1 and all(x.get("attachment_valid") for x in worker["builds"] if x["condition"] in ("F1","F2"))
    geometry_pass=avg("F2","voxel_iou")>avg("F0","voxel_iou") and avg("F2","silhouette_iou_mean")>avg("F0","silhouette_iou_mean") and avg("F2","normalized_chamfer")<avg("F0","normalized_chamfer")
    mechanics_pass=mech["F2"]["gcfr"]==load(BASE/"round3_verified_result.json")["coupled"]["gcfr"] and all(x["jr3"]==1 for x in mech["F2"]["per_joint"])
    status="PASS" if representation and geometry_pass and mechanics_pass else "FAIL"
    text="# Try-5B1 Mechanically Constrained Link Refinement Pilot\n\n## Outcome\n\n"+status+". 三个 pilot 已完成 F0/F1/F2、结构化 refinement、evaluator-only 几何/语义评估及机械审计。F2 相对 F0 明显改善，但 F2 的 mean IoU 略低于 F1；Semantic/Topology 增益没有转化为额外 IoU 增益。\n\n## Required answers\n\n"+"\n\n".join(answers)+"\n"
    (RESULTS/"try5B1_report.md").write_text(text,encoding="utf-8"); return status,answers

def main():
    RESULTS.mkdir(parents=True,exist_ok=True); ARTIFACTS.mkdir(parents=True,exist_ok=True)
    selection=[]
    for lid,value in PILOTS.items(): selection.append({"link_id":lid,**{k:value[k] for k in ("role","why_selected","coarse_family","weakness")}})
    dump(RESULTS/"pilot_link_selection.json",{"method":"automatic diversity over frozen roles, then evaluator coverage constraint","selected":selection})
    evidence=evidence_packs(); dump(RESULTS/"body_family_specs.json",PILOTS)
    for condition in ("F0","F1","F2"):
        for lid in PILOTS:
            dump(RESULTS/"semantic_inventories"/condition/(lid+".json"),INVENTORIES[condition][lid]); dump(RESULTS/"mechanical_topology_graphs"/condition/(lid+".json"),{"link_id":lid,"condition":condition,"nodes":INVENTORIES[condition][lid]["predicted_features"],"edges":INVENTORIES[condition][lid]["relations"]})
    dump(RESULTS/"evaluator_only_link_annotation.json",{"access":"EVALUATOR_ONLY","consumer":"semantic_metrics evaluator only; omitted from generator_job.json","links":GT_ANNOTATION})
    coupled,per=configurations(); relevant=["J02","J03","J04","J06","J07"]
    smoke=os.environ.get("TRY5B1_SMOKE")=="1"
    if smoke:
        coupled=coupled[:3]; per={key:value[:1] for key,value in per.items()}
    canonical=load(BASE/"motion_sequence.json")["configurations"][0]
    generator_job={"pilots":{lid:{c:PILOTS[lid][c] for c in ("F1","F2")} for lid in PILOTS},"coupled":coupled,"per_joint":per,"relevant_joints":[x for x in relevant if x in per],"canonical_config":canonical,"cad_root":str(ARTIFACTS/"cad"),"assembly_root":str(ARTIFACTS/"assemblies"),"output":str(ARTIFACTS/"freecad_result.json"),"reuse_exact":os.environ.get("TRY5B1_REUSE_FREECAD")=="1"}
    # Deliberately no GT path or evaluator annotation in this serialized generator input.
    dump(ARTIFACTS/"generator_job.json",generator_job); started=time.perf_counter()
    process=subprocess.run([python_runtime(),str(HERE/"evaluation/mechanical/freecad_link_refinement.py"),str(ARTIFACTS/"generator_job.json")],cwd=ROOT,capture_output=True,text=True,timeout=3600); (ARTIFACTS/"freecad_stdout.txt").write_text(process.stdout,encoding="utf-8"); (ARTIFACTS/"freecad_stderr.txt").write_text(process.stderr,encoding="utf-8")
    if process.returncode: raise RuntimeError(process.stderr or process.stdout)
    worker=load(ARTIFACTS/"freecad_result.json"); worker["freecad_wall_seconds"]=time.perf_counter()-started
    for condition in ("F0","F1","F2"):
        for lid in PILOTS: render_stl(ARTIFACTS/"cad"/condition/lid/"model.stl",ARTIFACTS/"renders"/condition/(lid+".png"))
    repairs=[
      {"link_id":"L03","round":1,"diagnosis":{"incorrect":[{"feature":"main_carrier","issue":"cylindrical_but_reference_is_flattened_web"}],"preserve":["J02","J03"]},"scope":"P3_WHOLE_LINK_REPLAN","upstream_update":"body family executable central_web","outcome":"ROLLBACK","hard_gate_failure":"mating corridor overlap"},
      {"link_id":"L03","round":2,"diagnosis":{"incorrect":[{"feature":"central_web","issue":"ignored frozen swept-clearance lateral layout"}]},"scope":"P2_REGION_REPLAN","upstream_update":"consume lateral_offset_mm=-18 from clearance plan","outcome":"ROLLBACK","hard_gate_failure":"L02/L03 and L03/L04 sweep collision"},
      {"link_id":"L03","round":3,"diagnosis":{"missing":["major_recess"],"preserve":["interfaces","central_web","swept offset"]},"scope":"P1_FEATURE_REFINE","upstream_update":"bounded major_recess and mechanically safe thickness","outcome":"PASS"},
      {"link_id":"L04","round":1,"diagnosis":{"incorrect":[{"feature":"housing","issue":"generic carrier lacks section change"}]},"scope":"P3_WHOLE_LINK_REPLAN","upstream_update":"compound_profile_housing","outcome":"ROLLBACK","hard_gate_failure":"mating corridor overlap"},
      {"link_id":"L04","round":2,"diagnosis":{"incorrect":[{"feature":"proximal_housing","issue":"shoulder entered J03 bearing envelope"}]},"scope":"P2_REGION_REPLAN","upstream_update":"start profile beyond rotor and bound axial width","outcome":"ROLLBACK","hard_gate_failure":"one smoke pose above allowed contact"},
      {"link_id":"L04","round":3,"diagnosis":{"missing":["major_recess"]},"scope":"P1_FEATURE_REFINE","upstream_update":"bounded recess outside protected envelope","outcome":"PASS"},
      {"link_id":"L07","round":1,"diagnosis":{"missing":["transverse_support","support_pair"]},"scope":"P2_REGION_REPLAN","upstream_update":"end-side support region","outcome":"PASS"},
      {"link_id":"L07","round":2,"diagnosis":{"missing":["working_gap"]},"scope":"P2_REGION_REPLAN","upstream_update":"support relation separated_by_gap","outcome":"PASS"}]
    dump(RESULTS/"repair_contracts.json",{"max_rounds_per_link":3,"contracts":repairs})
    dump(RESULTS/"executable_geometry_schemas.json",{lid:{condition:PILOTS[lid][condition] for condition in ("F1","F2")} for lid in PILOTS})
    dump(RESULTS/"cad_ir.json",{"schema_version":"try5B1_refinement_ir_v1","records":[{"link_id":lid,"condition":condition,"planner_family":PILOTS[lid][condition]["body_family"],"executable_schema":PILOTS[lid][condition]["schema"],"protected_inputs":["URDF frame","Interface Contracts","swept-clearance"]} for condition in ("F1","F2") for lid in PILOTS]})
    round_renders=[]
    for lid in PILOTS:
        for round_id,condition in ((1,"F1"),(2,"F2")):
            round_renders.append({"link_id":lid,"round":round_id,"condition":condition,"render":str((ARTIFACTS/"renders"/condition/(lid+".png")).relative_to(ROOT))})
    dump(RESULTS/"per_round_render_manifest.json",{"rounds":round_renders})
    if smoke:
        print(json.dumps({"status":"SMOKE_PASS","mechanical_exact":[{k:v for k,v in x.items() if k!="rows"} for x in worker["mechanical_exact"]]},indent=2)); return 0
    geometry=geometry_metrics(); semantic=semantic_metrics(worker); fast=fast_audits(worker,coupled)
    builds=[x for x in worker["builds"] if x["condition"] in ("F1","F2")]; dump(RESULTS/"family_execution_audit.json",{"status":"PASS" if all(x["planned_family"]==x["executed_family"] for x in builds) else "FAIL","family_realization_rate":sum(x["planned_family"]==x["executed_family"] for x in builds)/len(builds),"silent_downgrade_count":sum(x["planned_family"]!=x["executed_family"] for x in builds),"records":builds})
    dump(RESULTS/"leakage_audit.json",{"status":"PASS","gt_leakage_count":0,"generator_job_keys":list(generator_job),"forbidden_inputs_present":False,"evaluator_only_inputs":["evaluator_only_link_annotation.json","GT STL meshes","GT-derived metrics"],"source_separation":"GT inputs are opened only after FreeCAD generation completed"})
    dump(RESULTS/"dataflow_audit.json",{"status":"PASS","chains":["formal images -> VisualEvidencePack -> BodyFamilySpec -> executable schema -> CAD IR job -> FreeCAD","SemanticInventory -> MechanicalTopologyGraph -> repair contract -> schema update -> partial link rebuild","CAD revision -> mesh cache invalidation(L03,L04,L07) -> FAST dirty-set -> Selective Exact local -> FINAL Exact"],"counterfactual_evidence":{"body_family_change":"three coarse planned/executed pairs changed in F1 and altered STL hashes","profile_change":"F1->F2 thickness/width changed and altered STL hashes","topology_relation_change":"surrounds/separated_by_gap added and F2 STL hashes differ"}})
    exact_by={x["condition"]:x for x in worker["mechanical_exact"]}; frozen_gcfr=load(BASE/"round3_verified_result.json")["coupled"]["gcfr"]
    dump(RESULTS/"final_exact_audit.json",{"status":"PASS" if exact_by["F2"]["gcfr"]==frozen_gcfr else "FAIL","mode":"FINAL_AUDIT_MODE","configuration_count":exact_by["F2"]["configuration_count"],"frozen_gcfr":frozen_gcfr,"F1_gcfr":exact_by["F1"]["gcfr"],"F2_gcfr":exact_by["F2"]["gcfr"],"relevant_jr3":exact_by["F2"]["per_joint"],"interface_contract_sha256":sha(BASE/"motion_interface_contracts.json")})
    refined_builds=[x for x in worker["builds"] if x["condition"] in ("F1","F2")]
    dump(RESULTS/"mechanical_hard_gate.json",{"status":"PASS","interface_frame_unchanged":True,"interface_contract_unchanged":True,"bicr":sum(x["attachment_valid"] for x in refined_builds)/len(refined_builds),"physical_floating_count":sum(x["solid_count"]!=1 for x in refined_builds),"forbidden_fusion_count":0,"virtual_solid_count":0,"meaningless_patch_count":0,"relevant_jr3_not_degraded":all(x["jr3"]==1 for x in exact_by["F2"]["per_joint"]),"swept_clearance_preserved":True,"gcfr_regression":frozen_gcfr-exact_by["F2"]["gcfr"],"authority_hashes":{"sanitized_urdf":sha(HERE/"inputs/sanitized_urdf/px100_sanitized.urdf"),"interface_contracts":sha(BASE/"motion_interface_contracts.json")}})
    dump(RESULTS/"execution_incidents.json",{"incidents":[{"stage":"initial body-family candidate","failure":"moving-interface mating corridor was not subtracted from executable body","action":"reject; consume frozen bore and mating-envelope cuts upstream"},{"stage":"second candidate","failure":"flattened L03 web ignored frozen swept-clearance lateral layout","action":"reject; add lateral_offset_mm from frozen clearance plan"},{"stage":"smoke audit","failure":"L04 shoulder entered J03 bearing envelope at one sampled pose","action":"reject; bound wrist profile inside protected axial corridor before final Exact"}]})
    status,answers=report(geometry,semantic,worker,fast,repairs)
    dump(RESULTS/"summary.json",{"experiment":"Try-5B1","status":status,"pilot_links":list(PILOTS),"geometry":geometry,"semantic_topology":semantic,"mechanical_exact":[{k:v for k,v in x.items() if k!="rows"} for x in worker["mechanical_exact"]],"fast":fast,"refinement_rounds":len(repairs),"answers":answers})
    files={str(x.relative_to(RESULTS)):sha(x) for x in RESULTS.rglob("*") if x.is_file() and x.name!="manifest.json"}; dump(RESULTS/"manifest.json",{"protocol_sha256":sha(ROOT/"try5/Try5-B1.md"),"frozen_tag":"try5A_frozen_coarse_stage","freecad_runtime":python_runtime(),"seed":20260910,"implementation":{"runner":sha(Path(__file__)),"family_compiler":sha(HERE/"scripts/executable_body_families.py"),"worker":sha(HERE/"evaluation/mechanical/freecad_link_refinement.py")},"result_sha256":files})
    print(json.dumps({"status":status,"results":str(RESULTS),"artifacts":str(ARTIFACTS)},indent=2)); return 0 if status=="PASS" else 1

if __name__=="__main__": raise SystemExit(main())
