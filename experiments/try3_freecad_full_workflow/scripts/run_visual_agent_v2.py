from __future__ import annotations

import argparse
import base64
import csv
import json
import mimetypes
import shutil
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema
from PIL import Image, ImageDraw, ImageStat

from stale_artifact_guard import write_stage_manifest


ROOT = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "go_nogo2" / "scripts"))
from glm_config import load_glm  # noqa: E402

TRYSET = EXP / "tryset5_v1.csv"
RUNS = EXP / "runs" / "visual_agent_v2"
ARTIFACTS = EXP / "artifacts" / "visual_agent_v2"
RESULTS = EXP / "results"
SCAN_SCHEMA = EXP / "schemas" / "visual_scan_plan_v1.schema.json"
PACKET_SCHEMA = EXP / "schemas" / "visual_evidence_packet_v2.schema.json"

ALL_VIEWS = ("front", "rear", "left", "right", "top", "isometric")
DEFAULT_SCAN_VIEWS = ("front", "isometric")


@dataclass(frozen=True)
class JointInfo:
    name: str
    parent: str
    child: str
    joint_type: str
    origin_xyz_mm: list[float]
    axis: list[float]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`").strip()
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            parsed = json.loads(stripped[start : end + 1])
        else:
            raise
    if isinstance(parsed, dict) and isinstance(parsed.get("answer"), dict):
        parsed = parsed["answer"]
    if not isinstance(parsed, dict):
        raise ValueError("VLM response JSON is not an object")
    return parsed


def parse_urdf(path: Path) -> tuple[list[str], list[JointInfo]]:
    root = ET.parse(path).getroot()
    links = [node.get("name", "") for node in root.findall("link") if node.get("name")]
    joints: list[JointInfo] = []
    for node in root.findall("joint"):
        origin = node.find("origin")
        axis = node.find("axis")
        parent = node.find("parent")
        child = node.find("child")
        xyz = [float(x) * 1000.0 for x in (origin.get("xyz", "0 0 0").split() if origin is not None else ["0", "0", "0"])]
        axis_xyz = [float(x) for x in (axis.get("xyz", "0 0 1").split() if axis is not None else ["0", "0", "1"])]
        joints.append(
            JointInfo(
                name=node.get("name", ""),
                parent=parent.get("link", "") if parent is not None else "",
                child=child.get("link", "") if child is not None else "",
                joint_type=node.get("type", ""),
                origin_xyz_mm=xyz,
                axis=axis_xyz,
            )
        )
    return links, joints


def image_item(path: Path) -> dict[str, Any]:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}}


def resized_image(case_id: str, view: str, source: Path, max_side: int) -> Path:
    out = ARTIFACTS / "resized_inputs" / case_id / f"{view}_{max_side}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        rgb = image.convert("RGB")
        rgb.thumbnail((max_side, max_side))
        rgb.save(out)
    return out


def clamp_bbox(value: Any) -> list[float]:
    if not isinstance(value, list) or len(value) != 4:
        return [0.5, 0.5, 0.6, 0.6]
    cx, cy, w, h = [float(x) for x in value]
    return [
        max(0.0, min(1.0, cx)),
        max(0.0, min(1.0, cy)),
        max(0.05, min(1.0, w)),
        max(0.05, min(1.0, h)),
    ]


def normalize_scan_plan(raw: dict[str, Any], case_id: str, links: list[str], views: list[str]) -> dict[str, Any]:
    raw_links = raw.get("links", [])
    if not isinstance(raw_links, list):
        raise ValueError("scan plan missing links array")
    by_link = {str(item.get("link_id")): item for item in raw_links if isinstance(item, dict) and item.get("link_id")}
    normalized_links = []
    for link_id in links:
        item = by_link.get(link_id)
        if not isinstance(item, dict):
            raise ValueError(f"scan plan missing link_id {link_id}")
        bbox_by_view = {}
        raw_bbox = item.get("link_bbox_by_view", {})
        if not isinstance(raw_bbox, dict):
            raw_bbox = {}
        for view in views:
            bbox_by_view[view] = clamp_bbox(raw_bbox.get(view))
        details = []
        for idx, detail in enumerate(item.get("candidate_detail_regions", []) if isinstance(item.get("candidate_detail_regions"), list) else []):
            if not isinstance(detail, dict):
                continue
            source_view = str(detail.get("source_view") or views[0])
            if source_view not in views:
                source_view = views[0]
            hint = str(detail.get("feature_hint") or "unknown")
            if hint not in {
                "joint_housing",
                "flange",
                "boss",
                "recess",
                "rib",
                "yoke",
                "hole_pattern",
                "curved_transition",
                "cover_boundary",
                "shell_opening",
                "other_visible_detail",
                "unknown",
            }:
                hint = "other_visible_detail"
            details.append(
                {
                    "region_id": str(detail.get("region_id") or f"{link_id}_R{idx + 1:02d}"),
                    "source_view": source_view,
                    "bbox": clamp_bbox(detail.get("bbox")),
                    "feature_hint": hint,
                    "reason": str(detail.get("reason") or ""),
                    "confidence": max(0.0, min(1.0, float(detail.get("confidence", 0.0) or 0.0))),
                }
            )
        normalized_links.append(
            {
                "link_id": link_id,
                "visibility": str(item.get("visibility") or "unknown") if str(item.get("visibility") or "unknown") in {"clear", "partial", "occluded", "unknown"} else "unknown",
                "link_bbox_by_view": bbox_by_view,
                "proximal_joint_region": normalize_joint_region(item.get("proximal_joint_region"), views),
                "distal_joint_region": normalize_joint_region(item.get("distal_joint_region"), views),
                "candidate_detail_regions": details[:5],
            }
        )
    return {
        "schema_version": "visual_scan_plan_v1",
        "case_id": case_id,
        "scan_mode": "glm_vlm_case_scan",
        "source_views": views,
        "links": normalized_links,
        "leakage_guard": {
            "uses_gt_mesh": False,
            "uses_gt_segmentation": False,
            "uses_product_identity": False,
        },
    }


def normalize_joint_region(value: Any, views: list[str]) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    source_view = str(value.get("source_view") or views[0])
    if source_view not in views:
        source_view = views[0]
    return {
        "source_view": source_view,
        "bbox": clamp_bbox(value.get("bbox")),
        "joint_id": value.get("joint_id") if isinstance(value.get("joint_id"), str) else None,
        "confidence": max(0.0, min(1.0, float(value.get("confidence", 0.0) or 0.0))),
    }


def build_scan_prompt(case_id: str, links: list[str], joints: list[JointInfo], views: list[str]) -> str:
    expected_link_count = len(links)
    return json.dumps(
        {
            "task": "Locate robot links, joint neighborhoods, and candidate visible detail regions. Return one strict top-level JSON object only.",
            "case_id": case_id,
            "views": views,
            "links": links,
            "expected_link_count": expected_link_count,
            "joints": [
                {
                    "name": j.name,
                    "parent": j.parent,
                    "child": j.child,
                    "type": j.joint_type,
                    "origin_xyz_mm": j.origin_xyz_mm,
                    "axis": j.axis,
                }
                for j in joints
            ],
            "required_output": {
                "links": [
                    {
                        "link_id": "one exact URDF link id",
                        "visibility": "clear|partial|occluded|unknown",
                        "link_bbox_by_view": {views[0]: [0.5, 0.5, 0.4, 0.4]},
                        "proximal_joint_region": {"source_view": views[0], "bbox": [0.5, 0.5, 0.25, 0.25], "joint_id": "or null", "confidence": 0.0},
                        "distal_joint_region": {"source_view": views[0], "bbox": [0.5, 0.5, 0.25, 0.25], "joint_id": "or null", "confidence": 0.0},
                        "candidate_detail_regions": [
                            {
                                "region_id": "L2_R01",
                                "source_view": views[0],
                                "bbox": [0.5, 0.5, 0.2, 0.2],
                                "feature_hint": "joint_housing|flange|boss|recess|rib|yoke|hole_pattern|curved_transition|cover_boundary|shell_opening|other_visible_detail|unknown",
                                "reason": "visible evidence only",
                                "confidence": 0.0,
                            }
                        ],
                    }
                ],
                "leakage_guard": {"uses_gt_mesh": False, "uses_gt_segmentation": False, "uses_product_identity": False},
            },
            "rules": [
                "Use normalized [cx, cy, w, h] image coordinates in [0,1].",
                f"Return every input link exactly once: exactly {expected_link_count} link objects.",
                "Do not omit a URDF link just because it is hard to visually separate.",
                "If individual links cannot be separated, still return each missing link_id with visibility='unknown' or 'occluded', a broad low-confidence bbox, and an explicit reason in candidate_detail_regions if any visible detail exists.",
                "The top-level JSON object must contain keys case_id, views, links, and leakage_guard. Do not wrap it in an answer field.",
                "At most five candidate detail regions per link.",
                "If a link is occluded, give a broad uncertain box and say occluded.",
                "Do not use product identity, GT mesh, STEP/CAD, segmentation, or hidden labels.",
                "Do not generate CAD or mechanical feature graphs.",
            ],
        },
        ensure_ascii=False,
    )


def run_vlm_scan(row: dict[str, str], links: list[str], joints: list[JointInfo], images: dict[str, Path], views: list[str], timeout_seconds: float, image_max_side: int) -> tuple[str, dict[str, Any]]:
    cfg = load_glm()
    client = cfg.create_client().with_options(timeout=timeout_seconds, max_retries=0)
    case_id = row["case_id"]
    content: list[dict[str, Any]] = [{"type": "text", "text": build_scan_prompt(case_id, links, joints, views)}]
    for view in views:
        resized = resized_image(case_id, view, images[view], image_max_side)
        content.extend([{"type": "text", "text": f"view={view}"}, image_item(resized)])
    started = time.time()
    response = client.chat.completions.create(
        model=cfg.model,
        messages=[
            {"role": "system", "content": "You are a visual localization module. Return JSON only."},
            {"role": "user", "content": content},
        ],
        temperature=0,
        top_p=1,
        max_tokens=8192,
        response_format={"type": "json_object"},
        extra_body={"reasoning_effort": "low"},
    )
    elapsed = time.time() - started
    raw_text = response.choices[0].message.content or ""
    usage = getattr(response, "usage", None)
    manifest = {
        "model": cfg.model,
        "mode": "vlm_case_scan",
        "views": views,
        "image_max_side": image_max_side,
        "elapsed_seconds": elapsed,
        "input_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
        "raw_response_chars": len(raw_text),
    }
    return raw_text, manifest


def bbox_to_pixels(bbox: list[float], width: int, height: int, pad: float = 0.08) -> list[int]:
    cx, cy, w, h = bbox
    w = min(1.0, w * (1.0 + pad))
    h = min(1.0, h * (1.0 + pad))
    x0 = max(0, int((cx - w / 2.0) * width))
    y0 = max(0, int((cy - h / 2.0) * height))
    x1 = min(width, int((cx + w / 2.0) * width))
    y1 = min(height, int((cy + h / 2.0) * height))
    return [x0, y0, max(x0 + 1, x1), max(y0 + 1, y1)]


def crop_and_measure(src: Path, dst: Path, bbox: list[float]) -> tuple[list[int], float]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as image:
        rgb = image.convert("RGB")
        px = bbox_to_pixels(bbox, rgb.width, rgb.height)
        crop = rgb.crop(tuple(px))
        crop.save(dst)
        stat = ImageStat.Stat(crop.convert("L"))
        # Proxy for empty crop: mean very high and low variance on white renders.
        empty_score = 1.0 if stat.mean[0] > 248 and stat.stddev[0] < 5 else 0.0
    return px, empty_score


def generate_crops(case_id: str, images: dict[str, Path], scan_plan: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    crop_records: list[dict[str, Any]] = []
    refs_by_link: dict[str, list[str]] = {}
    for link in scan_plan["links"]:
        link_id = link["link_id"]
        refs_by_link[link_id] = []
        for view, bbox in link["link_bbox_by_view"].items():
            crop_id = f"{case_id}_{link_id}_{view}_link"
            path = RUNS / "crops" / case_id / link_id / f"{crop_id}.png"
            px, empty = crop_and_measure(images[view], path, bbox)
            refs_by_link[link_id].append(f"crop:{crop_id}")
            crop_records.append(record_crop(crop_id, case_id, link_id, "link", view, bbox, px, None, path, empty))
        for name, crop_type in (("proximal_joint_region", "proximal_joint"), ("distal_joint_region", "distal_joint")):
            region = link.get(name)
            if isinstance(region, dict):
                view = region["source_view"]
                crop_id = f"{case_id}_{link_id}_{crop_type}"
                path = RUNS / "crops" / case_id / link_id / f"{crop_id}.png"
                px, empty = crop_and_measure(images[view], path, region["bbox"])
                refs_by_link[link_id].append(f"crop:{crop_id}")
                crop_records.append(record_crop(crop_id, case_id, link_id, crop_type, view, region["bbox"], px, None, path, empty))
        for detail in link.get("candidate_detail_regions", []):
            view = detail["source_view"]
            crop_id = f"{case_id}_{link_id}_{detail['region_id']}"
            path = RUNS / "crops" / case_id / link_id / f"{crop_id}.png"
            px, empty = crop_and_measure(images[view], path, detail["bbox"])
            refs_by_link[link_id].append(f"crop:{crop_id}")
            crop_records.append(record_crop(crop_id, case_id, link_id, "feature", view, detail["bbox"], px, detail["feature_hint"], path, empty))
    return crop_records, refs_by_link


def record_crop(crop_id: str, case_id: str, link_id: str, crop_type: str, view: str, bbox: list[float], bbox_px: list[int], feature_hint: str | None, path: Path, empty_score: float) -> dict[str, Any]:
    return {
        "crop_id": crop_id,
        "case_id": case_id,
        "link_id": link_id,
        "crop_type": crop_type,
        "source_view": view,
        "bbox_normalized": bbox,
        "bbox_px": bbox_px,
        "feature_hint": feature_hint,
        "crop_path": str(path),
        "localization_source": "glm-5.3-flash",
        "gt_geometry_used": False,
        "_empty_score": empty_score,
    }


def make_packet(case_id: str, scan_path: Path, scan_plan: dict[str, Any], crop_records: list[dict[str, Any]], refs_by_link: dict[str, list[str]]) -> dict[str, Any]:
    details_by_link: dict[str, list[dict[str, Any]]] = {}
    for crop in crop_records:
        if crop["crop_type"] == "feature":
            details_by_link.setdefault(crop["link_id"], []).append(crop)
    links = []
    for link in scan_plan["links"]:
        link_id = link["link_id"]
        refs = refs_by_link.get(link_id, [])
        feature_obs = [
            {
                "feature_type": str(crop.get("feature_hint") or "unknown"),
                "description": "candidate visible detail localized by VLM scan; crop observer pending",
                "evidence_refs": [f"crop:{crop['crop_id']}"],
                "confidence": 0.0,
            }
            for crop in details_by_link.get(link_id, [])
        ]
        links.append(
            {
                "link_id": link_id,
                "visibility": link["visibility"],
                "visual_observations": {
                    "main_body": {"description": "link-level crop generated; crop observer pending", "evidence_refs": refs[:1], "confidence": 0.0},
                    "proximal_region": {"description": "proximal joint crop generated when localized; crop observer pending", "evidence_refs": [r for r in refs if "proximal" in r], "confidence": 0.0},
                    "distal_region": {"description": "distal joint crop generated when localized; crop observer pending", "evidence_refs": [r for r in refs if "distal" in r], "confidence": 0.0},
                    "visible_features": feature_obs,
                    "surface_hints": [],
                },
                "uncertainty": ["semantic crop observation pending"],
            }
        )
    clean_crops = [{k: v for k, v in crop.items() if not k.startswith("_")} for crop in crop_records]
    return {
        "schema_version": "visual_evidence_packet_v2",
        "case_id": case_id,
        "scan_plan_ref": str(scan_path),
        "links": links,
        "crop_records": clean_crops,
        "leakage_guard": {
            "uses_gt_mesh": False,
            "uses_gt_segmentation": False,
            "uses_product_identity": False,
        },
    }


def make_contact_sheet(case_id: str, crop_records: list[dict[str, Any]]) -> None:
    feature_crops = [c for c in crop_records if c["crop_type"] in {"link", "feature"}]
    tiles = []
    for crop in feature_crops[:80]:
        path = Path(crop["crop_path"])
        if not path.exists():
            continue
        with Image.open(path) as image:
            tile = image.convert("RGB")
            tile.thumbnail((180, 140))
        canvas = Image.new("RGB", (210, 180), "white")
        canvas.paste(tile, ((210 - tile.width) // 2, 8))
        draw = ImageDraw.Draw(canvas)
        draw.text((6, 148), crop["link_id"], fill="black")
        draw.text((6, 162), crop["crop_type"][:18], fill="black")
        tiles.append(canvas)
    if not tiles:
        return
    cols = min(5, len(tiles))
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 210, rows * 180), "white")
    for i, tile in enumerate(tiles):
        sheet.paste(tile, ((i % cols) * 210, (i // cols) * 180))
    out = RESULTS / "visual_agent_v2_contact_sheets" / f"{case_id}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def process_case(row: dict[str, str], views: list[str], timeout_seconds: float, image_max_side: int, scan_schema: dict[str, Any], packet_schema: dict[str, Any]) -> dict[str, Any]:
    case_id = row["case_id"]
    case_run = RUNS / "cases" / case_id
    if case_run.exists():
        shutil.rmtree(case_run)
    case_run.mkdir(parents=True, exist_ok=True)
    image_text_path = ROOT / row["image_text_json"]
    urdf_path = ROOT / row["sanitized_urdf"]
    image_text = load_json(image_text_path)
    images = {view: ROOT / image_text["images"][view] for view in ALL_VIEWS}
    links, joints = parse_urdf(urdf_path)
    try:
        raw_text, api_manifest = run_vlm_scan(row, links, joints, images, views, timeout_seconds, image_max_side)
        write_json(case_run / "api_manifest.json", api_manifest)
        (case_run / "raw_response.txt").write_text(raw_text, encoding="utf-8")
        raw_scan = extract_json(raw_text)
        scan_plan = normalize_scan_plan(raw_scan, case_id, links, views)
        jsonschema.validate(scan_plan, scan_schema)
        scan_path = case_run / "visual_scan_plan_v1.json"
        write_json(scan_path, scan_plan)
        crop_records, refs_by_link = generate_crops(case_id, images, scan_plan)
        packet = make_packet(case_id, scan_path, scan_plan, crop_records, refs_by_link)
        jsonschema.validate(packet, packet_schema)
        write_json(case_run / "visual_evidence_packet_v2.json", packet)
        make_contact_sheet(case_id, crop_records)
        write_stage_manifest(
            case_run / "stage_manifest.json",
            stage="visual_agent_v2_scan_and_crop",
            status="SUCCESS",
            schema_version="visual_scan_plan_v1+visual_evidence_packet_v2",
            producer="run_visual_agent_v2.py",
            input_paths=[image_text_path, urdf_path],
        )
        empty_rate = sum(float(c["_empty_score"]) for c in crop_records) / max(1, len(crop_records))
        return {
            "case_id": case_id,
            "status": "SUCCESS",
            "links": len(links),
            "scan_views": ";".join(views),
            "crop_records": len(crop_records),
            "feature_crops": sum(1 for c in crop_records if c["crop_type"] == "feature"),
            "empty_crop_rate": round(empty_rate, 4),
            "input_tokens": api_manifest["input_tokens"],
            "output_tokens": api_manifest["output_tokens"],
            "total_tokens": api_manifest["total_tokens"],
            "elapsed_seconds": round(api_manifest["elapsed_seconds"], 3),
            "error_type": "",
            "error": "",
        }
    except Exception as exc:
        failure = {
            "stage": "visual_agent_v2_scan_and_crop",
            "status": "FAILURE",
            "case_id": case_id,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        write_json(case_run / "stage_manifest.json", failure)
        return {
            "case_id": case_id,
            "status": "FAILURE",
            "links": 0,
            "scan_views": ";".join(views),
            "crop_records": 0,
            "feature_crops": 0,
            "empty_crop_rate": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "elapsed_seconds": "",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def write_report(rows: list[dict[str, Any]], views: list[str], timeout_seconds: float, image_max_side: int) -> None:
    successes = [r for r in rows if r["status"] == "SUCCESS"]
    total_links = sum(int(r["links"]) for r in rows)
    total_crops = sum(int(r["crop_records"]) for r in rows)
    lines = [
        "# Visual Evidence Agent v2 Feature Zoom Report",
        "",
        "## Scope",
        "",
        "This stage tests VLM-guided visual scan and feature-level crop generation. It does not generate MEP or CAD.",
        "",
        "## Configuration",
        "",
        f"- VLM model: `glm-5.3-flash`.",
        f"- Scan views: `{';'.join(views)}`.",
        f"- Request timeout seconds: `{timeout_seconds}`.",
        f"- Resized image max side: `{image_max_side}`.",
        "- GT geometry used: `false`.",
        "",
        "## Coverage",
        "",
        f"- Cases attempted: `{len(rows)}`.",
        f"- Successful cases: `{len(successes)}`.",
        f"- Links with packets: `{total_links}`.",
        f"- Crop records: `{total_crops}`.",
        f"- Stage status: `{'SUCCESS' if len(successes) == len(rows) else 'FAILURE' if not successes else 'PARTIAL'}`.",
        "",
        "## Case rows",
        "",
        "| case_id | status | links | crops | feature_crops | empty_crop_rate | error |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(f"| {row['case_id']} | {row['status']} | {row['links']} | {row['crop_records']} | {row['feature_crops']} | {row['empty_crop_rate']} | {row['error_type']} |")
    lines.extend(
        [
            "",
            "## Gate decision",
            "",
            "Do not release to MEP unless at least 4/5 cases succeed, links are covered, feature crops are non-empty, and manual spot-check passes.",
        ]
    )
    (RESULTS / "visual_agent_v2_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run VLM-guided Try-3 Visual Evidence Agent v2.")
    parser.add_argument("--case", help="Optional single case smoke run.")
    parser.add_argument("--views", default=",".join(DEFAULT_SCAN_VIEWS), help="Comma-separated views for VLM scan.")
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
    parser.add_argument("--image-max-side", type=int, default=384)
    args = parser.parse_args()

    views = [v.strip() for v in args.views.split(",") if v.strip()]
    for view in views:
        if view not in ALL_VIEWS:
            raise SystemExit(f"unsupported view: {view}")
    scan_schema = load_json(SCAN_SCHEMA)
    packet_schema = load_json(PACKET_SCHEMA)
    rows = list(csv.DictReader(TRYSET.open("r", encoding="utf-8")))
    if args.case:
        rows = [r for r in rows if r["case_id"] == args.case]
        if not rows:
            raise SystemExit(f"case not found in TrySet: {args.case}")

    results = [process_case(row, views, args.timeout_seconds, args.image_max_side, scan_schema, packet_schema) for row in rows]
    write_csv(RESULTS / "visual_agent_v2_case_summary.csv", results)
    write_report(results, views, args.timeout_seconds, args.image_max_side)
    print(json.dumps({"cases": len(results), "successes": sum(1 for r in results if r["status"] == "SUCCESS"), "views": views}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
