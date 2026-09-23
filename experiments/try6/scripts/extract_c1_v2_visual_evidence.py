"""Raw-image-only L04 visible contour/profile evidence and frozen view registration."""

from __future__ import annotations

import hashlib
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try6.scripts.run_r1_reliability import save

RESULT=HERE/"results/try6_0_c1_v2/visual_metric_evidence"
ARTIFACT=HERE/"artifacts/try6_0_c1_v2/visual_metric_evidence"


def color_mask(path):
    rgb=np.asarray(Image.open(path).convert("RGB"),dtype=np.int16)
    raw=(rgb[:,:,0]<85)&(rgb[:,:,1]>110)&(rgb[:,:,2]>85)&(rgb[:,:,1]>rgb[:,:,0]+40)&(rgb[:,:,2]>rgb[:,:,0]+35)
    labels,count=ndimage.label(raw)
    sizes=np.bincount(labels.ravel(),minlength=count+1)
    return (labels>0)&(sizes[labels]>=1000)


def urdf_anchor(path):
    root=ET.parse(path).getroot()
    joint=next(j for j in root.findall("joint") if j.get("name")=="J04")
    xyz=[float(x) for x in joint.find("origin").get("xyz").split()]
    return math.sqrt(sum(x*x for x in xyz))*1000.0


def extract():
    cfg=load(HERE/"protocol/try6_0_c1_v2.json")
    inputs=load(ROOT/cfg["source_input_manifest"])["inputs"]
    anchor=urdf_anchor(ROOT/inputs["sanitized_urdf"]["path"])
    if abs(anchor-cfg["view_registration"]["anchor_distance_mm"])>1e-9:
        raise RuntimeError("URDF anchor differs from frozen protocol")
    if sha(ROOT/inputs["sanitized_urdf"]["path"])!=inputs["sanitized_urdf"]["sha256"]:
        raise RuntimeError("sanitized URDF drift")
    views={};scales=[]
    for name in cfg["view_registration"]["views"]:
        source=ROOT/inputs["images"][name]["path"]
        if sha(source)!=inputs["images"][name]["sha256"]:raise RuntimeError(f"raw image drift: {name}")
        mask=color_mask(source)
        if name=="top":mask[:600,:]=False
        yy,xx=np.where(mask)
        if len(xx)<cfg["view_registration"]["minimum_visible_pixels_per_view"]:
            raise RuntimeError(f"insufficient visible pixels: {name}")
        bbox=[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())]
        axis_span=(bbox[2]-bbox[0]) if name=="right" else (bbox[3]-bbox[1])
        scale=axis_span/anchor
        scales.append(scale)
        origin_axis=bbox[2] if name=="right" else bbox[1]
        center_perp=(bbox[1]+bbox[3])/2 if name=="right" else (bbox[0]+bbox[2])/2
        start_mm,end_mm=cfg["visual_evidence"]["roi_axis_mm"]
        endpoints=[origin_axis-scale*x if name=="right" else origin_axis+scale*x for x in (start_mm,end_mm)]
        axis_min=max(0,int(math.floor(min(endpoints))))
        axis_max=min(mask.shape[1 if name=="right" else 0]-1,int(math.ceil(max(endpoints))))
        if name=="right":
            crop=[axis_min,max(0,bbox[1]-20),axis_max+1,min(mask.shape[0],bbox[3]+21)]
        else:
            crop=[max(0,bbox[0]-20),axis_min,min(mask.shape[1],bbox[2]+21),axis_max+1]
        roi=mask[crop[1]:crop[3],crop[0]:crop[2]]
        edge=roi^ndimage.binary_erosion(roi)
        samples=[]
        half=cfg["visual_evidence"]["station_half_window_pixels"]
        for station in cfg["visual_evidence"]["profile_stations_mm"]:
            axis_pixel=origin_axis-scale*station if name=="right" else origin_axis+scale*station
            lo=max(0,int(round(axis_pixel))-half);hi=min(mask.shape[1 if name=="right" else 0],int(round(axis_pixel))+half+1)
            strip=mask[:,lo:hi] if name=="right" else mask[lo:hi,:]
            locations=np.where(strip)[0 if name=="right" else 1]
            if len(locations)<10:raise RuntimeError(f"unobservable profile station: {name}:{station}")
            perp_min,perp_max=int(locations.min()),int(locations.max())
            samples.append({"station_x_mm":station,"axis_pixel":axis_pixel,"perpendicular_min_px":perp_min,
                "perpendicular_max_px":perp_max,"visible_width_px":perp_max-perp_min+1,
                "visible_width_mm":(perp_max-perp_min+1)/scale,"support_pixels":int(len(locations))})
        ARTIFACT.mkdir(parents=True,exist_ok=True)
        image_path=ARTIFACT/f"{name}_raw_teal_visible_mask.png"
        Image.fromarray(mask.astype(np.uint8)*255).save(image_path)
        with Image.open(source) as image:
            meta=image.info.get("Description","")
        views[name]={"source_path":inputs["images"][name]["path"],"source_sha256":inputs["images"][name]["sha256"],
            "image_size_px":[mask.shape[1],mask.shape[0]],"miba_orientation_metadata_present":bool(meta),
            "visible_color_pixels":int(len(xx)),"visible_color_bbox_px":bbox,
            "landmarks_used":{"proximal_endpoint_px":origin_axis,"distal_endpoint_px":bbox[0] if name=="right" else bbox[3],
                "perpendicular_center_px":center_perp,"landmark_role":"visible teal envelope endpoints; approximate, not manually annotated joint centers"},
            "scale_px_per_mm":scale,"roi_crop_xyxy_px":crop,
            "roi_visible_pixels":int(roi.sum()),"roi_edge_pixels":int(edge.sum()),
            "profile_stations":samples,"mask_path":str(image_path.relative_to(ROOT)).replace("\\","/"),
            "mask_sha256":sha(image_path),"mask_semantics":"raw-color-visible L04 region only; not GT or complete L04 silhouette"}
    discordance=abs(scales[0]-scales[1])/(sum(scales)/2)
    registration_pass=discordance<=cfg["view_registration"]["maximum_cross_view_relative_scale_discordance"]
    registration={"schema_version":"robotcad_try6_c1_v2_registration_v1","calibrated":False,
        "method":cfg["view_registration"]["method"],"usable_views":cfg["view_registration"]["views"],
        "unresolved_views":["front","isometric","left","rear"],
        "anchor_distance_mm":anchor,"anchor_source_path":inputs["sanitized_urdf"]["path"],
        "anchor_source_sha256":inputs["sanitized_urdf"]["sha256"],
        "parameters":{name:{"scale_px_per_mm":view["scale_px_per_mm"],**view["landmarks_used"]} for name,view in views.items()},
        "cross_view_relative_scale_discordance":discordance,
        "maximum_allowed_discordance":cfg["view_registration"]["maximum_cross_view_relative_scale_discordance"],
        "endpoint_fit_residual_px":0.0,"endpoint_fit_residual_caveat":"zero by two-endpoint construction; not independent registration accuracy evidence",
        "candidate_specific_reregistration":False,"registration_gate_pass":registration_pass,
        "uncertainty":"No calibrated intrinsics/extrinsics or articulated reference pose; colored visible-envelope endpoints approximate joint landmarks; central ROI avoids occluded interfaces.",
        "gt_used":False}
    evidence={"schema_version":"robotcad_try6_c1_v2_visual_metric_evidence_v1",
        "source":"raw six-view image set; right/top selected; no GT/holdout",
        "selected_views":cfg["view_registration"]["views"],"views":views,
        "measurement_policy":cfg["visual_evidence"],"view_registration_sha256":None,
        "full_link_silhouette_available":False,
        "objective_uses":"visible central-ROI contour distance and profile widths only",
        "evidence_gate_pass":all(v["roi_visible_pixels"]>1000 and v["roi_edge_pixels"]>100 for v in views.values()),
        "gt_used":False}
    save(RESULT/"view_registration_report.json",registration)
    evidence["view_registration_sha256"]=sha(RESULT/"view_registration_report.json")
    save(RESULT/"visual_metric_evidence.json",evidence)
    save(RESULT/"landmarks.json",{name:view["landmarks_used"] for name,view in views.items()})
    save(RESULT/"profile_measurements.json",{name:view["profile_stations"] for name,view in views.items()})
    save(RESULT/"contour_or_edge_evidence.json",{name:{"roi_crop_xyxy_px":view["roi_crop_xyxy_px"],
        "roi_edge_pixels":view["roi_edge_pixels"],"raw_visible_mask_path":view["mask_path"],
        "raw_visible_mask_sha256":view["mask_sha256"]} for name,view in views.items()})
    save(RESULT/"evidence_audit.json",{"registration_gate_pass":registration_pass,
        "evidence_gate_pass":evidence["evidence_gate_pass"],"gt_accessed":False,"formal_holdout_accessed":False,
        "registration_report_sha256":sha(RESULT/"view_registration_report.json"),
        "visual_evidence_sha256":sha(RESULT/"visual_metric_evidence.json")})
    print(json.dumps({"registration_gate_pass":registration_pass,"evidence_gate_pass":evidence["evidence_gate_pass"],
        "cross_view_scale_discordance":discordance,"views":cfg["view_registration"]["views"]}))
    return registration_pass and evidence["evidence_gate_pass"]


if __name__=="__main__":extract()
