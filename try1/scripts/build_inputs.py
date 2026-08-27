"""Freeze anonymous Image+Text v1 packets and hidden GT-derived RMDG diagnostics."""
from __future__ import annotations
import csv, json, sys
from pathlib import Path
import numpy as np
from scipy.stats import qmc

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "go_nogo2" / "scripts"))
from evaluate_prediction import load_robot
from prototype_feasibility import forward_kinematics
sys.path.insert(0, str(ROOT / "try1" / "validators"))
from validate_image_text_input_v1 import validate

VIEWS = ("front", "rear", "left", "right", "top", "iso")
TEMPLATE = (ROOT / "try1/prompts/image_text_v1/task_prompt_template.txt").read_text(encoding="utf-8").strip()

def anchor_values(robot):
    height = float(np.ptp(robot.combined.vertices[:, 2]) * 1000)
    movable = [j for j in robot.joints if j["type"] in {"revolute", "continuous", "prismatic"}]
    samples = qmc.Sobol(d=max(1, len(movable)), scramble=False, seed=20260827).random_base2(8)
    end = max(robot.links, key=lambda link: robot.depth[link]); maximum = 0.0
    for row in samples:
        values = {}
        for index, joint in enumerate(movable):
            lo, hi = (-np.pi, np.pi) if joint["type"] == "continuous" else (joint["lower"], joint["upper"])
            values[joint["name"]] = float(lo + row[index] * (hi - lo))
        maximum = max(maximum, float(np.linalg.norm(forward_kinematics(robot.links, robot.joints, values)[end][:3, 3])) * 1000)
    return round(height, 1), round(maximum, 1)

def gt_rmdg(robot):
    transforms = forward_kinematics(robot.links, robot.joints, {})
    ids = {name: f"L{i}" for i, name in enumerate(robot.links)}; jids = {j["name"]: f"J{i}" for i, j in enumerate(robot.joints)}
    children = {name: [] for name in robot.links}
    for joint in robot.joints: children[joint["parent"]].append(jids[joint["name"]])
    links=[]
    for name in robot.links:
        mesh=robot.world_meshes.get(name); ext=np.ptp(mesh.vertices, axis=0)*1000 if mesh is not None else np.zeros(3)
        incoming=next((jids[j["name"]] for j in robot.joints if j["child"]==name),None)
        links.append({"link_id":ids[name],"functional_role":"base" if name==robot.root else ("end_effector_interface" if robot.depth[name]==max(robot.depth.values()) else "intermediate_link"),"parent_joint_id":incoming,"child_joint_ids":children[name],"coarse_geometry":{"shape_family":"unknown","estimated_length_mm":float(max(ext)),"estimated_width_mm":float(np.median(ext)),"estimated_height_mm":float(min(ext))},"interfaces":{"proximal":"unknown","distal":"unknown"},"evidence_views":["front","isometric"]})
    joints=[]
    for joint in robot.joints:
        parent_tf=transforms[joint["parent"]]; origin=parent_tf @ joint["origin"]; axis=parent_tf[:3,:3] @ joint["axis"]
        joints.append({"joint_id":jids[joint["name"]],"parent_link_id":ids[joint["parent"]],"child_link_id":ids[joint["child"]],"joint_type":joint["type"] if joint["type"] in {"revolute","continuous","prismatic","fixed"} else "unknown","functional_role":"kinematic_joint","axis_base":[float(x) for x in axis],"origin_base_mm":[float(x*1000) for x in origin[:3,3]],"limit":{"lower_rad":None if joint["type"]=="continuous" else float(joint["lower"]),"upper_rad":None if joint["type"]=="continuous" else float(joint["upper"])},"evidence_views":["front","isometric"]})
    return {"schema_version":"rmdg_v1","robot":{"mechanism_class":"serial_manipulator","base_link_id":ids[robot.root],"end_effector_link_id":ids[max(robot.links,key=lambda x:robot.depth[x])],"units":"mm"},"links":links,"joints":joints}

def main():
    data=ROOT/"go_nogo3/data/dev15"; out=ROOT/"try1/inputs/image_text_v1"; hidden=ROOT/"try1/hidden_gt_rmdg"; out.mkdir(parents=True,exist_ok=True); hidden.mkdir(parents=True,exist_ok=True); rows=[]
    for case in sorted(data.glob("dev_arm-*")):
        robot=load_robot(case/"urdf/model.urdf"); h,r=anchor_values(robot); packet={"protocol_version":"image_text_v1","case_id":case.name,"images":{("isometric" if v=="iso" else v):str((case/"renders"/f"{v}.png").relative_to(ROOT)).replace("\\\\","/") for v in VIEWS},"text_fields":{"semantic_category":"articulated industrial robot arm","overall_height_home_mm":h,"max_reach_mm":r},"rendered_prompt":TEMPLATE.format(overall_height_home_mm=h,max_reach_mm=r),"units":"mm"}; report=validate(packet)
        if not report["semantic_valid"]: raise ValueError(report)
        (out/f"{case.name}.json").write_text(json.dumps(packet,indent=2),encoding="utf-8"); (hidden/f"{case.name}.json").write_text(json.dumps(gt_rmdg(robot),indent=2),encoding="utf-8"); rows.append({"case_id":case.name,"overall_height_home_mm":h,"max_reach_mm":r})
    with (ROOT/"try1/frozen_cases.csv").open("w",newline="",encoding="utf-8") as f: writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader();writer.writerows(rows)
if __name__=="__main__": main()
