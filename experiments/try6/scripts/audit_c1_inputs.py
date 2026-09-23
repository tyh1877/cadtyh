"""Read-only Try-6 C1 input/camera audit; never opens evaluator GT."""

from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/try6"
RESULTS = HERE / "results/try6_0_c1"
ARTIFACTS = HERE / "artifacts/try6_0_c1"
IMAGES = ROOT / "experiments/try5A/inputs/images"


def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rel(path): return str(Path(path).resolve().relative_to(ROOT)).replace("\\", "/")
def dump(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def color_mask(path):
    array = np.asarray(Image.open(path).convert("RGB"), dtype=np.int16)
    mask = (array[:, :, 0] < 85) & (array[:, :, 1] > 110) & (array[:, :, 2] > 85) & (array[:, :, 1] > array[:, :, 0] + 40) & (array[:, :, 2] > array[:, :, 0] + 35)
    labels, count = ndimage.label(mask)
    sizes = np.bincount(labels.ravel(), minlength=count + 1)
    selected = (labels > 0) & (sizes[labels] >= 1000)
    return selected


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    source = ROOT / "experiments/try5A/results/try5b1_a2a_three_link/paired_main_table.json"
    rows = load(source)["rows"]
    candidates = [row for row in rows if row["link"] == "L04" and row["method"] == "DIRECT_QWEN"]
    if len(candidates) != 1 or candidates[0]["status"] != "EVALUATED": raise RuntimeError("frozen C0 row unavailable")
    holdout = load(ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if holdout["accessed"] is not False or holdout["evaluation_count"] != 0: raise RuntimeError("formal holdout accessed")
    c0 = {"schema_version": "robotcad_try6_c0_frozen_v1", "source": rel(source), "source_sha256": sha(source), "condition": "HISTORICAL_FROZEN_A2A_L04_DIRECT_QWEN", "metrics": candidates[0], "qwen_recalled": False, "formal_holdout_accessed": False}
    dump(RESULTS / "c0_baseline.json", c0)
    input_paths = {"engineering_text": ROOT / "experiments/try5A/inputs/engineering_text/robot_A.md", "sanitized_urdf": ROOT / "experiments/try5A/inputs/sanitized_urdf/px100_sanitized.urdf", "f0_fcstd": ROOT / "experiments/try5A/artifacts/try5a5/round3_verified/links/L04/model.FCStd", "frozen_interface_contracts": ROOT / "experiments/try5A/results/try5a5/motion_interface_contracts.json", "development_configurations": ROOT / "experiments/try5A/protocol/try5b1_a1_development_input.json"}
    input_hashes = {key: {"path": rel(path), "sha256": sha(path)} for key, path in input_paths.items()}
    input_hashes["images"] = {view: {"path": rel(IMAGES / (view + ".png")), "sha256": sha(IMAGES / (view + ".png"))} for view in ("front", "isometric", "left", "right", "top", "rear")}
    dump(RESULTS / "input_hashes.json", {"schema_version": "robotcad_try6_c1_inputs_v1", "inputs": input_hashes, "gt_generator_access": False, "formal_holdout_accessed": False})
    contracts = load(input_paths["frozen_interface_contracts"])
    j03 = next(item for item in contracts if item["joint_id"] == "J03")
    j04 = next(item for item in contracts if item["joint_id"] == "J04")
    anchor = float(np.linalg.norm(np.asarray(j04["origin_xyz_mm"]) - np.zeros(3)))
    if abs(anchor - 63.0) > 1e-9 or j03["axis_child"] != [0.0, 1.0, 0.0]: raise RuntimeError("L04 URDF/interface anchor changed")
    views = {}
    for view in ("front", "isometric", "left", "right", "top", "rear"):
        path = IMAGES / (view + ".png")
        with Image.open(path) as image:
            xml = ET.fromstring(image.info["Description"])
            matrix = {key: float(value) for key, value in xml.find("View/Matrix").attrib.items()}
            image_size = list(image.size)
        mask = color_mask(path)
        if view == "top":
            mask[:600, :] = False  # Exclude small teal regions occluded behind the upper arm.
        yy, xx = np.where(mask)
        bbox = [int(xx.min()), int(yy.min()), int(xx.max()), int(yy.max())] if len(xx) else None
        if view in ("right", "top"):
            target = ARTIFACTS / "observed_masks" / (view + ".png")
            target.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(mask.astype(np.uint8) * 255).save(target)
        views[view] = {"source_sha256": sha(path), "image_size": image_size, "miba_view_matrix": matrix, "visible_teal_pixels": int(len(xx)), "teal_bbox_px": bbox, "occlusion_note": "most L04 material obscured" if view in ("front", "rear") else "visible contour; some joints overlap adjacent links"}
    right = views["right"]["teal_bbox_px"]; top = views["top"]["teal_bbox_px"]
    registration = {"schema_version": "robotcad_try6_c1_view_registration_v1", "available": {"freecad_miba_view_matrices": True, "camera_intrinsics": False, "complete_world_to_pixel_projection": False, "known_link_pose_for_reference_renders": False, "manual_joint_pixel_annotations": False}, "views": views, "selected_solver_views": ["right", "top"], "color_mask_rule": "R<85, G>110, B>85, G>R+40, B>R+35; connected components >=1000 pixels; top y>=600 for visible L04 span", "urdf_metric_anchor": {"joint_pair": ["J03", "J04"], "L04_frame_separation_mm": anchor, "source": rel(input_paths["frozen_interface_contracts"]), "source_sha256": sha(input_paths["frozen_interface_contracts"])}, "registration": {"right": {"world_x_to_pixel_x": [-float(right[2] - right[0]) / anchor, float(right[2])], "world_z_to_pixel_y": [float(right[2] - right[0]) / anchor, float(right[1] + right[3]) / 2]}, "top": {"world_x_to_pixel_y": [float(top[3] - top[1]) / anchor, float(top[1])], "world_y_to_pixel_x": [float(top[3] - top[1]) / anchor, float(top[0] + top[2]) / 2]}}, "nuisance_policy": "fixed scale/translation estimated from colored L04 endpoints and the 63 mm URDF link-frame separation before optimization; no candidate-specific re-registration", "uncertainty": "The visible color endpoints are approximate joint landmarks; camera pixel calibration and articulated reference pose are unavailable. Front/rear and isometric views are excluded from the metric objective.", "gt_used": False}
    dump(RESULTS / "camera_or_view_registration.json", registration)
    print(json.dumps({"status": "PASS", "c0_iou": c0["metrics"]["final_voxel_iou"], "anchor_mm": anchor, "solver_views": registration["selected_solver_views"], "holdout_accessed": False}, indent=2))


if __name__ == "__main__": main()
