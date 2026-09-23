"""Development-only L04 metric grounding from raw color masks and a URDF anchor."""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.stats import qmc

ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/"experiments/try6"
sys.path.insert(0,str(ROOT/"experiments/try5A/scripts"))
from freecad_runtime import python_runtime  # noqa: E402

PARAMETERS=("housing_width_mm","housing_height_mm","proximal_section_length_mm","transition_length_mm","distal_width_mm","distal_height_mm","recess_length_mm","recess_depth_mm","fillet_radius_mm")


def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def dump(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+"\n",encoding="utf-8")


class Objective:
    def __init__(self,config,registration,parameter_spec,artifact_root,kfdg_path):
        self.config=config;self.registration=registration;self.spec=parameter_spec;self.root=Path(artifact_root);self.kfdg_path=Path(kfdg_path).resolve()
        self.bounds=np.asarray([(item["lower_bound"],item["upper_bound"]) for item in parameter_spec["optimizable"]],dtype=float)
        self.initial=np.asarray([item["value"] for item in parameter_spec["optimizable"]],dtype=float)
        self.prior=self.initial.copy()
        self.views={}
        for view in ("right","top"):
            full=np.asarray(Image.open(HERE/"artifacts/try6_0_c1/observed_masks"/(view+".png")).convert("L"))>127
            bbox=registration["views"][view]["teal_bbox_px"]
            x0=max(0,bbox[0]-25);y0=max(0,bbox[1]-25);x1=min(full.shape[1],bbox[2]+26);y1=min(full.shape[0],bbox[3]+26)
            self.views[view]={"mask":full[y0:y1,x0:x1],"crop":(x0,y0),"shape":(y1-y0,x1-x0)}

    def vector(self,values): return {item["id"]:float(value) for item,value in zip(self.spec["optimizable"],values)}

    def project(self,mesh,view,anchor_mm):
        info=self.views[view];reg=self.registration["registration"][view];vertices=np.asarray(mesh.vertices)
        scale=float(self.registration["views"][view]["teal_bbox_px"][2 if view=="right" else 3]-self.registration["views"][view]["teal_bbox_px"][0 if view=="right" else 1])/anchor_mm
        if view=="right":
            u=-scale*vertices[:,0]+reg["world_x_to_pixel_x"][1]-info["crop"][0]
            v=-scale*vertices[:,2]+reg["world_z_to_pixel_y"][1]-info["crop"][1]
        else:
            u=scale*vertices[:,1]+reg["world_y_to_pixel_x"][1]-info["crop"][0]
            v=scale*vertices[:,0]+reg["world_x_to_pixel_y"][1]-info["crop"][1]
        image=Image.new("L",(info["shape"][1],info["shape"][0]),0);draw=ImageDraw.Draw(image)
        coords=np.column_stack((u,v))
        for face in np.asarray(mesh.faces):
            draw.polygon([tuple(point) for point in coords[face]],fill=255)
        return np.asarray(image)>127

    @staticmethod
    def silhouette(a,b):
        union=np.count_nonzero(a|b)
        return 1-np.count_nonzero(a&b)/union if union else 1.0

    @staticmethod
    def edge(a,b):
        if not a.any() or not b.any(): return 1.0
        ea=a^ndimage.binary_erosion(a); eb=b^ndimage.binary_erosion(b)
        da=ndimage.distance_transform_edt(~ea);db=ndimage.distance_transform_edt(~eb)
        diagonal=math.hypot(*a.shape)
        return float((da[eb].mean()+db[ea].mean())/(2*diagonal))

    @staticmethod
    def landmark(a,b):
        if not a.any() or not b.any(): return 1.0
        ay,ax=np.where(a);by,bx=np.where(b)
        diag=math.hypot(*a.shape)
        return float(sum(abs(x-y) for x,y in zip((ax.min(),ax.max(),ay.min(),ay.max()),(bx.min(),bx.max(),by.min(),by.max())))/(4*diag))

    @staticmethod
    def profile(a,b):
        if not a.any() or not b.any(): return 1.0
        losses=[]
        for fraction in (.25,.5,.75):
            index=int((a.shape[1]-1)*fraction)
            left=np.flatnonzero(a[:,index]);right=np.flatnonzero(b[:,index])
            length_left=(left[-1]-left[0]+1) if len(left) else 0
            length_right=(right[-1]-right[0]+1) if len(right) else 0
            losses.append(abs(length_left-length_right)/max(1,a.shape[0]))
        return float(np.mean(losses))

    def evaluate_mesh(self,mesh,values,anchor_mm):
        observed=[]
        for view in ("right","top"):
            predicted=self.project(mesh,view,anchor_mm);target=self.views[view]["mask"]
            observed.append({"view":view,"silhouette":self.silhouette(predicted,target),"edge":self.edge(predicted,target),"profile":self.profile(predicted,target),"landmark":self.landmark(predicted,target),"predicted_pixels":int(predicted.sum()),"reference_pixels":int(target.sum())})
        silhouette=float(np.mean([item["silhouette"] for item in observed]))
        edge_profile=float(np.mean([(item["edge"]+item["profile"])/2 for item in observed]))
        landmark=float(np.mean([item["landmark"] for item in observed]))
        prior=float(np.mean(((np.asarray(values)-self.prior)/(self.bounds[:,1]-self.bounds[:,0]))**2))
        weights=self.config["objective_weights"]
        total=weights["silhouette"]*silhouette+weights["edge_profile"]*edge_profile+weights["landmark"]*landmark+weights["prior"]*prior
        return {"total":total,"silhouette":silhouette,"edge_profile":edge_profile,"landmark":landmark,"prior":prior,"views":observed}

    def build_and_score(self,index,values,anchor_mm):
        folder=self.root/"candidates"/f"candidate_{index:03d}"
        folder.mkdir(parents=True,exist_ok=True)
        job={"mode":"METRIC_SOLVER_CANDIDATE","parameters":self.vector(values),"anchor_distance_mm":anchor_mm,"kfdg_path":str(self.kfdg_path),"frozen_interface_contracts":str(ROOT/"experiments/try5A/results/try5a5/motion_interface_contracts.json"),"f0_fcstd":str(ROOT/"experiments/try5A/artifacts/try5a5/round3_verified/links/L04/model.FCStd"),"output_root":str(folder)}
        job_path=folder/"build_job.json";dump(job_path,job)
        start=time.perf_counter()
        try:
            result=subprocess.run([python_runtime(),str(HERE/"scripts/freecad_c1_builder.py"),str(job_path)],cwd=ROOT,capture_output=True,text=True,timeout=self.config["candidate_timeout_seconds"])
            stdout,stderr=result.stdout,result.stderr;code=result.returncode
        except subprocess.TimeoutExpired as error:
            stdout,stderr,code="",str(error),124
        (folder/"stdout.txt").write_text(stdout,encoding="utf-8")
        (folder/"stderr.txt").write_text(stderr,encoding="utf-8")
        duration=time.perf_counter()-start
        if code: return {"index":index,"status":"INVALID_CAD","total":10.0,"error":stderr[-1500:],"seconds":duration,"parameters":self.vector(values)}
        mesh=trimesh.load(folder/"final.stl",force="mesh",process=False)
        score=self.evaluate_mesh(mesh,values,anchor_mm)
        return {"index":index,"status":"PASS","seconds":duration,"parameters":self.vector(values),**score,"cad_result_path":str((folder/"build_result.json").relative_to(ROOT)).replace("\\","/")}


def solve(config_path,kfdg_path,output_root):
    config=load(config_path);graph=load(kfdg_path);params=load(HERE/"protocol/parameter_bounds.json")
    root=Path(output_root);root.mkdir(parents=True,exist_ok=True)
    if (root/"solver_started.json").exists(): raise FileExistsError("formal metric solver already started")
    if graph["schema_version"]!="robotcad_kfdg_l04_v1" or graph["metric_anchor"]["distance_mm"]!=63: raise RuntimeError("KFDG/URDF anchor invalid")
    objective=Objective(config,load(HERE/"results/try6_0_c1/camera_or_view_registration.json"),params,root,kfdg_path)
    cues={item["parameter_id"]:item for item in load(HERE/"results/try6_0_c1/vlm_response.json")["parameter_cues"]}
    for index,item in enumerate(params["optimizable"]):
        cue=cues.get(item["id"])
        if cue:
            tentative=cue["ratio_hint"]*63.0
            objective.prior[index]=np.clip(tentative,item["lower_bound"],item["upper_bound"])
    dump(root/"solver_started.json",{"status":"STARTED_NO_BUDGET_CHANGE","config":str(Path(config_path).relative_to(ROOT)).replace("\\","/"),"maximum_evaluations":config["max_solver_evaluations"],"optimizer_seed":config["optimizer_seed"],"gt_accessed":False,"motion_feedback":False})
    history=[];start=time.perf_counter();anchor=graph["metric_anchor"]["distance_mm"]
    def run(values):
        if time.perf_counter()-start>=config["max_runtime_seconds"]: raise TimeoutError("pre-registered solver runtime exhausted")
        values=np.clip(np.asarray(values,dtype=float),objective.bounds[:,0],objective.bounds[:,1])
        record=objective.build_and_score(len(history),values,anchor);history.append(record)
        return record
    run(objective.initial)
    sobol=qmc.Sobol(d=len(PARAMETERS),scramble=True,seed=config["optimizer_seed"])
    for point in sobol.random_base2(m=config["sobol_power"]):
        if len(history)>=config["max_solver_evaluations"]:break
        run(objective.bounds[:,0]+point*(objective.bounds[:,1]-objective.bounds[:,0]))
    rng=np.random.default_rng(config["optimizer_seed"])
    stale=0
    while len(history)<config["max_solver_evaluations"]:
        valid=[record for record in history if record["status"]=="PASS"]
        if not valid:break
        best=min(valid,key=lambda item:item["total"])
        radius=config["local_radius_fraction"]*(objective.bounds[:,1]-objective.bounds[:,0])*(.7**stale)
        proposal=np.asarray([best["parameters"][key] for key in PARAMETERS])+rng.normal(size=len(PARAMETERS))*radius
        result=run(proposal)
        stale=0 if result["status"]=="PASS" and result["total"]<best["total"]-config["convergence_tolerance"] else stale+1
        if stale>=config["max_stale_local_evaluations"]:break
    with (root/"solver_history.csv").open("w",newline="",encoding="utf-8") as handle:
        fields=["index","status","total","silhouette","edge_profile","landmark","prior","seconds",*PARAMETERS,"error"]
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
        for record in history: writer.writerow({**{key:record.get(key) for key in fields},**record["parameters"]})
    with (root/"objective_breakdown.csv").open("w",newline="",encoding="utf-8") as handle:
        fields=["index","status","total","silhouette","edge_profile","landmark","prior"]
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows([{key:record.get(key) for key in fields} for record in history])
    valid=[record for record in history if record["status"]=="PASS"]
    if not valid: raise RuntimeError("all solver CAD candidates invalid")
    best=min(valid,key=lambda item:item["total"])
    output={"status":"PASS","optimizer":"seeded_sobol_then_local_random","optimizer_seed":config["optimizer_seed"],"max_solver_evaluations":config["max_solver_evaluations"],"actual_evaluations":len(history),"valid_candidates":len(valid),"failed_candidates":len(history)-len(valid),"solver_runtime_seconds":time.perf_counter()-start,"initial_objective":history[0]["total"],"best_objective":best["total"],"best_candidate_index":best["index"],"theta_star":best["parameters"],"objective_breakdown":{key:best[key] for key in ("silhouette","edge_profile","landmark","prior")},"termination":"stale_tolerance" if len(history)<config["max_solver_evaluations"] else "budget_exhausted","gt_accessed":False,"motion_feedback":False}
    dump(root/"solver_result.json",output)
    print(json.dumps({"status":"PASS","evaluations":len(history),"best_objective":best["total"],"best_index":best["index"]},indent=2))
    return output


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--config",required=True);parser.add_argument("--kfdg",required=True);parser.add_argument("--output-root",required=True);args=parser.parse_args()
    solve(args.config,args.kfdg,args.output_root)


if __name__=="__main__":main()
