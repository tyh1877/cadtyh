"""Frozen right/top raw-visible contour/profile objective; no GT or mechanics."""

from __future__ import annotations

import copy
import math
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image,ImageDraw
from scipy import ndimage

from experiments.try6.scripts.r1_contract import ROOT,HERE,load


def edge(mask):
    return mask ^ ndimage.binary_erosion(mask)


class VisibleObjective:
    def __init__(self, anchor_override_mm=None):
        self.cfg=load(HERE/"protocol/try6_0_c1_v2.json")
        self.evidence=load(HERE/"results/try6_0_c1_v2/visual_metric_evidence/visual_metric_evidence.json")
        registration=load(HERE/"results/try6_0_c1_v2/visual_metric_evidence/view_registration_report.json")
        if registration["registration_gate_pass"] is not True or self.evidence["evidence_gate_pass"] is not True:
            raise RuntimeError("raw-image evidence/registration gate not passed")
        frozen_anchor=registration["anchor_distance_mm"]
        self.anchor=float(anchor_override_mm) if anchor_override_mm is not None else frozen_anchor
        if self.anchor<=0:raise ValueError("metric anchor must be positive")
        self.views={}
        for name,item in self.evidence["views"].items():
            item=copy.deepcopy(item)
            if anchor_override_mm is not None:
                item["scale_px_per_mm"]*=frozen_anchor/self.anchor
                for station in item["profile_stations"]:
                    station["visible_width_mm"]=station["visible_width_px"]/item["scale_px_per_mm"]
                    origin=item["landmarks_used"]["proximal_endpoint_px"]
                    station["axis_pixel"]=origin-item["scale_px_per_mm"]*station["station_x_mm"] if name=="right" else origin+item["scale_px_per_mm"]*station["station_x_mm"]
            raw=np.asarray(Image.open(ROOT/item["mask_path"]).convert("L"))>127
            x0,y0,x1,y1=item["roi_crop_xyxy_px"]
            crop=raw[y0:y1,x0:x1]
            if not crop.any():raise RuntimeError(f"empty raw ROI {name}")
            self.views[name]={"source":item,"raw_roi":crop,"crop":(x0,y0,x1,y1),"raw_edge":edge(crop)}

    def project(self,mesh,name):
        item=self.views[name]["source"]
        x0,y0,x1,y1=self.views[name]["crop"]
        scale=item["scale_px_per_mm"]
        landmarks=item["landmarks_used"]
        verts=np.asarray(mesh.vertices)
        if name=="right":
            u=landmarks["proximal_endpoint_px"]-scale*verts[:,0]-x0
            v=landmarks["perpendicular_center_px"]-scale*verts[:,2]-y0
        else:
            u=landmarks["perpendicular_center_px"]+scale*verts[:,1]-x0
            v=landmarks["proximal_endpoint_px"]+scale*verts[:,0]-y0
        image=Image.new("L",(x1-x0,y1-y0),0)
        draw=ImageDraw.Draw(image)
        xy=np.column_stack((u,v))
        for face in np.asarray(mesh.faces):
            draw.polygon([tuple(pt) for pt in xy[face]],fill=255)
        return np.asarray(image)>127

    def evaluate(self,mesh_path,render_dir=None):
        mesh=trimesh.load(mesh_path,force="mesh",process=False)
        if len(mesh.vertices)==0 or len(mesh.faces)==0:raise RuntimeError("empty CAD mesh")
        records=[]
        for name,view in self.views.items():
            predicted=self.project(mesh,name)
            raw=view["raw_roi"]
            eraw=view["raw_edge"]
            epred=edge(predicted)
            if not epred.any() or not eraw.any():raise RuntimeError(f"empty candidate/raw contour {name}")
            diagonal=math.hypot(*raw.shape)
            distance_raw_to_pred=ndimage.distance_transform_edt(~epred)[eraw].mean()
            distance_pred_to_raw=ndimage.distance_transform_edt(~eraw)[epred].mean()
            contour=float((distance_raw_to_pred+distance_pred_to_raw)/(2*diagonal))
            item=view["source"]
            x0,y0,x1,y1=view["crop"]
            scale=item["scale_px_per_mm"]
            profile_errors=[]
            profile_rows=[]
            for station in item["profile_stations"]:
                axis=station["axis_pixel"]-(x0 if name=="right" else y0)
                half=self.cfg["visual_evidence"]["station_half_window_pixels"]
                lo=max(0,int(round(axis))-half)
                hi=min(predicted.shape[1 if name=="right" else 0],int(round(axis))+half+1)
                strip=predicted[:,lo:hi] if name=="right" else predicted[lo:hi,:]
                locations=np.where(strip)[0 if name=="right" else 1]
                if len(locations)<5:raise RuntimeError(f"candidate misses profile station {name}:{station['station_x_mm']}")
                predicted_width_mm=(int(locations.max())-int(locations.min())+1)/scale
                observed_width_mm=station["visible_width_mm"]
                error=abs(predicted_width_mm-observed_width_mm)/self.anchor
                profile_errors.append(error)
                profile_rows.append({"station_x_mm":station["station_x_mm"],
                    "observed_width_mm":observed_width_mm,"predicted_width_mm":predicted_width_mm,
                    "normalized_abs_error":error})
            profile=float(np.mean(profile_errors))
            if render_dir is not None:
                out=Path(render_dir);out.mkdir(parents=True,exist_ok=True)
                Image.fromarray(predicted.astype(np.uint8)*255).save(out/f"{name}_predicted_visible_roi.png")
            records.append({"view":name,"contour_distance":contour,"profile_width_error":profile,
                "raw_visible_pixels":int(raw.sum()),"predicted_visible_pixels":int(predicted.sum()),
                "profile_stations":profile_rows})
        contour=float(np.mean([r["contour_distance"] for r in records]))
        profile=float(np.mean([r["profile_width_error"] for r in records]))
        weights=self.cfg["visual_objective"]["weights"]
        total=weights["visible_contour_distance"]*contour+weights["visible_profile_width"]*profile
        if not all(math.isfinite(x) for x in (contour,profile,total)):raise RuntimeError("non-finite objective")
        return {"total":total,"contour_term":contour,"profile_term":profile,
            "landmark_term":None,"weights":weights,"views":records,
            "full_link_silhouette_metric":False,"gt_used":False}
