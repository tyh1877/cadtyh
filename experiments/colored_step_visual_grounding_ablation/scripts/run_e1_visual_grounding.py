"""Run paired A0/A1/A2 VLM component grounding and objective mask evaluation."""

from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import mimetypes
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw
from scipy.optimize import linear_sum_assignment


ROOT = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parents[1]
MANIFEST = EXP / "native_step5_v1.csv"
ARTIFACTS = EXP / "artifacts" / "native_step5"
RESULTS = EXP / "results"
VIEWS = ["front", "rear", "left", "right", "top", "isometric"]
CONDITIONS = ["A0_controlled", "A1_color_only", "A2_color_legend"]

sys.path.insert(0, str(ROOT / "go_nogo2" / "scripts"))
from glm_config import load_glm  # noqa: E402

sys.path.insert(0, str(ROOT / "experiments" / "try3_freecad_full_workflow" / "scripts"))
from run_visual_agent_v2 import clamp_bbox, extract_json  # noqa: E402


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def image_item(path: Path, max_side: int = 1000) -> dict[str, Any]:
    image = Image.open(path).convert("RGB")
    image.thumbnail((max_side, max_side))
    stream = io.BytesIO(); image.save(stream, format="PNG")
    data = base64.b64encode(stream.getvalue()).decode("ascii")
    return {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{data}"}}


def build_prompt(case_id: str, condition: str, component_manifest: dict[str, Any]) -> str:
    payload = {
        "task": "Locate every visibly distinct mechanical component in six matched views of one robot assembly. Return JSON only.",
        "case_id": case_id,
        "condition": condition,
        "expected_component_count": len(component_manifest["components"]),
        "views": VIEWS,
        "required_output": {
            "case_id": case_id,
            "condition": condition,
            "regions": [{
                "region_id": "R00",
                "component_id": "C00 or null when the condition provides no reliable identity cue",
                "visibility": "clear|partial|occluded|unknown",
                "bbox_by_view": {"isometric": [0.5, 0.5, 0.3, 0.3]},
                "mechanical_role_hint": "base|shoulder|upper_arm|forearm|wrist|gripper|finger|other|unknown",
                "candidate_details": [{"view": "isometric", "bbox": [0.5, 0.5, 0.1, 0.1], "hint": "joint_housing|flange|boss|recess|rib|yoke|hole_pattern|curved_transition|cover|other"}],
                "confidence": 0.0,
            }],
        },
        "rules": [
            "Use normalized [cx,cy,w,h] coordinates in [0,1].",
            "Return one region for each visually separable rigid component; do not split surface patches of one component.",
            "Use evidence from all six views and omit bbox entries where the component is not visible.",
            "Do not infer brand or product identity.",
            "Do not generate CAD or hidden internal mechanisms.",
        ],
    }
    if condition == "A1_color_only":
        payload["color_instruction"] = "Different colors indicate different components, but no identity legend is provided. Use color boundaries for localization."
    elif condition == "A2_color_legend":
        payload["color_instruction"] = "Different colors indicate different components. Use the legend for both boundary localization and component_id."
        payload["color_legend"] = [
            {"component_id": item["component_id"], "rgb": item["color_rgb"]}
            for item in component_manifest["components"]
        ]
    else:
        payload["color_instruction"] = "All components are the same neutral gray. Use geometry, seams, and view consistency."
    return json.dumps(payload, ensure_ascii=False)


def call_vlm(case_id: str, condition: str, root: Path, component_manifest: dict[str, Any], timeout: float) -> tuple[dict, dict]:
    cfg = load_glm()
    client = cfg.create_client().with_options(timeout=timeout, max_retries=0)
    content: list[dict[str, Any]] = [{"type": "text", "text": build_prompt(case_id, condition, component_manifest)}]
    for view in VIEWS:
        content.extend([{"type": "text", "text": f"view={view}"}, image_item(root / condition / "renders" / f"{view}.png")])
    started = time.time()
    response = client.chat.completions.create(
        model=cfg.model,
        messages=[{"role": "system", "content": "You are a precise multi-view mechanical component localization module. Return JSON only."}, {"role": "user", "content": content}],
        temperature=0, top_p=1, max_tokens=8192,
        response_format={"type": "json_object"}, extra_body={"reasoning_effort": "low"},
    )
    elapsed = time.time() - started
    raw_text = response.choices[0].message.content or ""
    usage = getattr(response, "usage", None)
    return extract_json(raw_text), {
        "model": cfg.model, "elapsed_seconds": elapsed,
        "input_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
        "actual_image_inputs": len(VIEWS), "raw_text": raw_text,
    }


def normalize(raw: dict, case_id: str, condition: str) -> dict:
    regions = raw.get("regions", [])
    if not isinstance(regions, list):
        raise ValueError("regions must be an array")
    output = []
    for index, item in enumerate(regions):
        if not isinstance(item, dict):
            continue
        boxes = item.get("bbox_by_view", {})
        if not isinstance(boxes, dict):
            boxes = {}
        normalized_boxes = {view: clamp_bbox(box) for view, box in boxes.items() if view in VIEWS and box is not None}
        output.append({
            "region_id": str(item.get("region_id") or f"R{index:02d}"),
            "component_id": str(item["component_id"]) if item.get("component_id") else None,
            "visibility": str(item.get("visibility") or "unknown"),
            "bbox_by_view": normalized_boxes,
            "mechanical_role_hint": str(item.get("mechanical_role_hint") or "unknown"),
            "candidate_details": item.get("candidate_details", []) if isinstance(item.get("candidate_details", []), list) else [],
            "confidence": max(0.0, min(1.0, float(item.get("confidence", 0.0) or 0.0))),
        })
    if not output:
        raise ValueError("no valid regions")
    return {"schema_version": "component_grounding_v1", "case_id": case_id, "condition": condition, "regions": output}


def binary_mask(path: Path) -> np.ndarray:
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)
    return np.any(rgb < 245, axis=2)


def mask_bbox(mask: np.ndarray) -> list[float] | None:
    ys, xs = np.where(mask)
    if not len(xs):
        return None
    h, w = mask.shape
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    return [float((x0 + x1) / 2 / w), float((y0 + y1) / 2 / h), float((x1 - x0) / w), float((y1 - y0) / h)]


def bbox_iou(a: list[float], b: list[float]) -> float:
    def corners(x):
        cx, cy, w, h = x; return cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    ax0, ay0, ax1, ay1 = corners(a); bx0, by0, bx1, by1 = corners(b)
    inter = max(0.0, min(ax1, bx1) - max(ax0, bx0)) * max(0.0, min(ay1, by1) - max(ay0, by0))
    union = max(0.0, (ax1-ax0)*(ay1-ay0)) + max(0.0, (bx1-bx0)*(by1-by0)) - inter
    return inter / union if union else 0.0


def evaluate(case_root: Path, component_manifest: dict, scan: dict) -> tuple[list[dict], dict]:
    component_ids = [item["component_id"] for item in component_manifest["components"]]
    gt_boxes: dict[str, dict[str, list[float]]] = {cid: {} for cid in component_ids}
    masks: dict[tuple[str, str], np.ndarray] = {}
    union_masks: dict[str, np.ndarray] = {}
    for view in VIEWS:
        for cid in component_ids:
            mask = binary_mask(case_root / "evaluator_masks" / view / f"{cid}.png")
            masks[(cid, view)] = mask
            box = mask_bbox(mask)
            if box is not None:
                gt_boxes[cid][view] = box
            union_masks[view] = np.logical_or(union_masks.get(view, np.zeros_like(mask)), mask)
    regions = scan["regions"]
    score = np.zeros((len(component_ids), len(regions)), dtype=float)
    for i, cid in enumerate(component_ids):
        for j, region in enumerate(regions):
            values = [bbox_iou(region["bbox_by_view"][v], gt_boxes[cid][v]) for v in region["bbox_by_view"] if v in gt_boxes[cid]]
            score[i, j] = max(values) if values else 0.0
    matched = {}
    if score.size:
        rr, cc = linear_sum_assignment(-score)
        matched = {int(i): int(j) for i, j in zip(rr, cc)}
    rows = []
    for i, cid in enumerate(component_ids):
        j = matched.get(i)
        region = regions[j] if j is not None else None
        best_iou = float(score[i, j]) if j is not None else 0.0
        purity_values = []
        blank_values = []
        if region:
            for view, box in region["bbox_by_view"].items():
                target = masks[(cid, view)]; union = union_masks[view]
                h, w = target.shape; cx, cy, bw, bh = box
                x0=max(0,int((cx-bw/2)*w)); x1=min(w,int((cx+bw/2)*w)); y0=max(0,int((cy-bh/2)*h)); y1=min(h,int((cy+bh/2)*h))
                area_union = int(union[y0:y1, x0:x1].sum())
                area_target = int(target[y0:y1, x0:x1].sum())
                purity_values.append(area_target / area_union if area_union else 0.0)
                blank_values.append(1.0 if area_union == 0 else 0.0)
        rows.append({
            "component_id": cid, "matched_region_id": region["region_id"] if region else "",
            "reported_component_id": region.get("component_id") if region else "",
            "identity_correct": int(bool(region and region.get("component_id") == cid)),
            "best_view_bbox_iou": best_iou, "recall_at_0_5": int(best_iou >= 0.5),
            "mean_target_purity": float(np.mean(purity_values)) if purity_values else 0.0,
            "blank_crop": float(np.mean(blank_values)) if blank_values else 1.0,
        })
    aggregate = {
        "gt_components": len(component_ids), "predicted_regions": len(regions),
        "mean_bbox_iou": float(np.mean([row["best_view_bbox_iou"] for row in rows])),
        "recall_at_0_5": float(np.mean([row["recall_at_0_5"] for row in rows])),
        "mean_target_purity": float(np.mean([row["mean_target_purity"] for row in rows])),
        "wrong_link_rate": float(1.0 - np.mean([row["mean_target_purity"] for row in rows])),
        "blank_crop_rate": float(np.mean([row["blank_crop"] for row in rows])),
        "identity_accuracy": float(np.mean([row["identity_correct"] for row in rows])),
        "feature_candidates": sum(len(region.get("candidate_details", [])) for region in regions),
    }
    return rows, aggregate


def contact_sheet(replicate: str, case_id: str, condition: str, image_path: Path, scan: dict) -> None:
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    w, h = image.size
    for region in scan["regions"]:
        box = region["bbox_by_view"].get("isometric")
        if not box: continue
        cx, cy, bw, bh = box
        rect = [(cx-bw/2)*w, (cy-bh/2)*h, (cx+bw/2)*w, (cy+bh/2)*h]
        draw.rectangle(rect, outline=(255,0,255), width=3)
        draw.text((rect[0]+3, rect[1]+3), region.get("component_id") or region["region_id"], fill=(255,0,255))
    path = RESULTS / "e1_contact_sheets" / replicate / condition / f"{case_id}.png"
    path.parent.mkdir(parents=True, exist_ok=True); image.save(path)


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--case"); parser.add_argument("--condition", choices=CONDITIONS); parser.add_argument("--timeout", type=float, default=180.0); parser.add_argument("--replicate", default="replicate_01"); args=parser.parse_args()
    run_base = EXP / "runs" / f"e1_{args.replicate}"
    manifest_rows = list(csv.DictReader(MANIFEST.open("r", encoding="utf-8")))
    if args.case: manifest_rows = [row for row in manifest_rows if row["case_id"] == args.case]
    conditions = [args.condition] if args.condition else CONDITIONS
    summary=[]; detail=[]
    for row in manifest_rows:
        case_root=ARTIFACTS/row["case_id"]; component_manifest=json.loads((case_root/"component_manifest.json").read_text(encoding="utf-8"))
        for condition in conditions:
            run_root=run_base/condition/row["case_id"]; run_root.mkdir(parents=True,exist_ok=True)
            try:
                raw, api=call_vlm(row["case_id"],condition,case_root,component_manifest,args.timeout)
                (run_root/"raw_response.txt").write_text(api.pop("raw_text"),encoding="utf-8")
                scan=normalize(raw,row["case_id"],condition); write_json(run_root/"component_grounding_v1.json",scan); write_json(run_root/"api_manifest.json",api)
                component_rows,agg=evaluate(case_root,component_manifest,scan)
                for item in component_rows: detail.append({"case_id":row["case_id"],"condition":condition,**item})
                summary.append({"case_id":row["case_id"],"condition":condition,"status":"SUCCESS",**agg,"input_tokens":api["input_tokens"],"output_tokens":api["output_tokens"],"total_tokens":api["total_tokens"],"elapsed_seconds":api["elapsed_seconds"],"error_type":"","error":""})
                contact_sheet(args.replicate,row["case_id"],condition,case_root/condition/"renders"/"isometric.png",scan)
            except Exception as exc:
                write_json(run_root/"failure.json",{"error_type":type(exc).__name__,"error":str(exc)})
                summary.append({"case_id":row["case_id"],"condition":condition,"status":"FAILURE","gt_components":len(component_manifest["components"]),"predicted_regions":0,"mean_bbox_iou":0,"recall_at_0_5":0,"mean_target_purity":0,"wrong_link_rate":1,"blank_crop_rate":1,"identity_accuracy":0,"feature_candidates":0,"input_tokens":0,"output_tokens":0,"total_tokens":0,"elapsed_seconds":0,"error_type":type(exc).__name__,"error":str(exc)[:500]})
    RESULTS.mkdir(parents=True,exist_ok=True)
    suffix = "" if args.replicate == "replicate_01" else f"_{args.replicate}"
    for path,rows in ((RESULTS/f"e1_case_condition_summary{suffix}.csv",summary),(RESULTS/f"e1_component_metrics{suffix}.csv",detail)):
        if rows:
            with path.open("w",encoding="utf-8",newline="") as handle:
                writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps({"rows":len(summary),"successes":sum(r["status"]=="SUCCESS" for r in summary)},indent=2))
    return 0 if all(r["status"]=="SUCCESS" for r in summary) else 1


if __name__ == "__main__":
    raise SystemExit(main())
