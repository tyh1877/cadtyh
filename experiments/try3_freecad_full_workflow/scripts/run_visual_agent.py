from __future__ import annotations

import csv
import base64
import json
import math
import mimetypes
import shutil
import sys
import statistics
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema
from PIL import Image, ImageChops, ImageDraw

from stale_artifact_guard import write_stage_manifest


ROOT = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "go_nogo2" / "scripts"))
from glm_config import load_glm  # noqa: E402

RUNS = EXP / "runs" / "visual_agent"
ARTIFACTS = EXP / "artifacts" / "visual_agent"
RESULTS = EXP / "results"
SCHEMA = EXP / "schemas" / "visual_evidence_packet_v1.schema.json"
TRYSET = EXP / "tryset5_v1.csv"

VIEWS = ("front", "rear", "left", "right", "top", "isometric")
DISPLAY_VIEW = "isometric"


@dataclass(frozen=True)
class ViewGeometry:
    bbox: tuple[int, int, int, int]
    center: tuple[float, float]
    direction: tuple[float, float]
    projection_min: float
    projection_max: float


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


def extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            return json.loads(stripped[start : end + 1])
        raise


def image_item(path: Path) -> dict[str, Any]:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}}


def resized_image_for_vlm(case_id: str, view: str, source: Path, max_side: int = 384) -> Path:
    out = ARTIFACTS / "resized_inputs" / case_id / f"{view}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        rgb = image.convert("RGB")
        rgb.thumbnail((max_side, max_side))
        rgb.save(out)
    return out


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


def robot_view_geometry(image: Image.Image) -> ViewGeometry:
    rgb = image.convert("RGB")
    # Render backgrounds are near-white. Detect pixels that differ from white
    # without using mesh, segmentation, CAD, or hidden labels.
    diff = ImageChops.difference(rgb, Image.new("RGB", rgb.size, "white")).convert("L")
    mask = diff.point(lambda p: 255 if p > 18 else 0)
    bbox = mask.getbbox()
    if bbox is None:
        bbox = (0, 0, rgb.width, rgb.height)
        center = (rgb.width / 2.0, rgb.height / 2.0)
        direction = (1.0, 0.0)
        return ViewGeometry(bbox, center, direction, -rgb.width / 2.0, rgb.width / 2.0)
    left, top, right, bottom = bbox
    pad_x = int((right - left) * 0.08)
    pad_y = int((bottom - top) * 0.08)
    padded_bbox = (
        max(0, left - pad_x),
        max(0, top - pad_y),
        min(rgb.width, right + pad_x),
        min(rgb.height, bottom + pad_y),
    )
    # Down-sample mask pixels for a deterministic non-GT principal-axis
    # estimate. This improves over naive horizontal slicing for diagonal robot
    # poses while still using only rendered image evidence.
    pixels = []
    step = max(1, int(math.sqrt(rgb.width * rgb.height / 20000)))
    mask_data = mask.load()
    for y in range(top, bottom, step):
        for x in range(left, right, step):
            if mask_data[x, y]:
                pixels.append((float(x), float(y)))
    if len(pixels) < 10:
        cx = (left + right) / 2.0
        cy = (top + bottom) / 2.0
        direction = (1.0, 0.0)
        projections = [left - cx, right - cx]
    else:
        xs = [p[0] for p in pixels]
        ys = [p[1] for p in pixels]
        cx = statistics.fmean(xs)
        cy = statistics.fmean(ys)
        var_x = statistics.fmean((x - cx) ** 2 for x in xs)
        var_y = statistics.fmean((y - cy) ** 2 for y in ys)
        cov_xy = statistics.fmean((x - cx) * (y - cy) for x, y in pixels)
        angle = 0.5 * math.atan2(2.0 * cov_xy, var_x - var_y)
        dx = math.cos(angle)
        dy = math.sin(angle)
        if dx < 0:
            dx, dy = -dx, -dy
        direction = (dx, dy)
        projections = [(x - cx) * dx + (y - cy) * dy for x, y in pixels]
    return ViewGeometry(padded_bbox, (cx, cy), direction, min(projections), max(projections))


def focus_box(
    image: Image.Image,
    geometry: ViewGeometry,
    *,
    center_ratio: float,
    span_ratio: float,
    mode: str,
) -> tuple[int, int, int, int]:
    left, top, right, bottom = geometry.bbox
    width = max(1, right - left)
    height = max(1, bottom - top)
    crop_w = int(max(100, width * span_ratio))
    crop_h = int(max(100, height * 0.85))
    if mode in {"left", "right"}:
        # Side views often compress the chain horizontally; keep more context.
        crop_w = int(max(crop_w, width * 0.55))
    if mode in {"front", "rear", "isometric", "top"}:
        projection = geometry.projection_min + (geometry.projection_max - geometry.projection_min) * center_ratio
        cx = int(geometry.center[0] + geometry.direction[0] * projection)
        cy = int(geometry.center[1] + geometry.direction[1] * projection)
    else:
        cx = int(left + width * center_ratio)
        cy = int(top + height * 0.52)
    x0 = max(0, cx - crop_w // 2)
    y0 = max(0, cy - crop_h // 2)
    x1 = min(image.width, x0 + crop_w)
    y1 = min(image.height, y0 + crop_h)
    x0 = max(0, x1 - crop_w)
    y0 = max(0, y1 - crop_h)
    return (x0, y0, max(x0 + 1, x1), max(y0 + 1, y1))


def focus_box_from_normalized(image: Image.Image, focus: dict[str, Any]) -> tuple[int, int, int, int]:
    def number(name: str, default: float) -> float:
        try:
            return float(focus.get(name, default))
        except Exception:
            return default

    cx = max(0.0, min(1.0, number("cx", 0.5))) * image.width
    cy = max(0.0, min(1.0, number("cy", 0.5))) * image.height
    cw = max(0.08, min(1.0, number("w", 0.35))) * image.width
    ch = max(0.08, min(1.0, number("h", 0.35))) * image.height
    x0 = max(0, int(cx - cw / 2))
    y0 = max(0, int(cy - ch / 2))
    x1 = min(image.width, int(cx + cw / 2))
    y1 = min(image.height, int(cy + ch / 2))
    return (x0, y0, max(x0 + 1, x1), max(y0 + 1, y1))


def crop_image(src: Path, dst: Path, box: tuple[int, int, int, int]) -> dict[str, Any]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as image:
        image.convert("RGB").crop(box).save(dst)
        width, height = image.size
    return {
        "path": str(dst),
        "bbox_px": list(box),
        "source_size_px": [width, height],
    }


def role_guess(link_id: str, index: int, count: int) -> str:
    if index == 0:
        return "base_or_shoulder"
    if index <= max(1, count // 4):
        return "shoulder_or_upper_arm"
    if index >= count - 2:
        return "wrist_or_tool_side"
    return "arm_link_or_elbow_region"


def observation_template(link_id: str, index: int, count: int, joints: list[JointInfo]) -> dict[str, Any]:
    proximal = [j for j in joints if j.child == link_id]
    distal = [j for j in joints if j.parent == link_id]
    return {
        "observation_source": "deterministic_non_gt_crop_heuristic",
        "functional_role_hint": role_guess(link_id, index, count),
        "main_body": "requires VLM/manual inspection; crop generated for local evidence",
        "proximal_region": "proximal joint crop available" if proximal else "root/no proximal joint in URDF",
        "distal_region": "distal joint crop available" if distal else "terminal/no distal joint in URDF",
        "surface_hints": [],
        "visible_features": [],
        "urdf_context": {
            "proximal_joints": [j.name for j in proximal],
            "distal_joints": [j.name for j in distal],
            "proximal_axes": [j.axis for j in proximal],
            "distal_axes": [j.axis for j in distal],
        },
        "limitations": [
            "Crops are localized by image silhouette and URDF link order, not by GT segmentation.",
            "Mechanical feature labels are intentionally not inferred without VLM/manual inspection.",
        ],
    }


def vlm_focus_and_observations(
    row: dict[str, str],
    links: list[str],
    joints: list[JointInfo],
    images: dict[str, Path],
    timeout_seconds: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    cfg = load_glm()
    client = cfg.create_client().with_options(timeout=timeout_seconds, max_retries=0)
    case_id = row["case_id"]
    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": json.dumps(
                {
                    "task": "Return strict JSON for Try-3 Visual Evidence Agent.",
                    "case_id": case_id,
                    "links": links,
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
                    "output_schema": {
                        "links": [
                            {
                                "link_id": "exact URDF link id",
                                "focus_by_view": {
                                    "front": {"cx": 0.5, "cy": 0.5, "w": 0.35, "h": 0.35},
                                    "isometric": {"cx": 0.5, "cy": 0.5, "w": 0.35, "h": 0.35},
                                },
                                "visual_observations": {
                                    "main_body": "observable exterior shape only",
                                    "proximal_region": "observable joint-side geometry",
                                    "distal_region": "observable joint-side geometry",
                                    "visible_features": [],
                                    "surface_hints": [],
                                },
                                "confidence": {"focus": 0.0, "semantics": 0.0},
                            }
                        ]
                    },
                    "rules": [
                        "Use normalized image coordinates in [0,1].",
                        "Do not use or infer product identity.",
                        "Do not claim hidden internal mechanisms.",
                        "Do not use mesh, STEP, CAD, segmentation, or hidden labels.",
                        "If a link is occluded, provide a broad crop and state uncertainty.",
                    ],
                },
                ensure_ascii=False,
            ),
        }
    ]
    for view in VIEWS:
        resized = resized_image_for_vlm(case_id, view, images[view])
        content.extend([{"type": "text", "text": f"view={view}"}, image_item(resized)])
    response = client.chat.completions.create(
        model=cfg.model,
        messages=[
            {"role": "system", "content": "You are the Visual Evidence Agent. Return JSON only."},
            {"role": "user", "content": content},
        ],
        temperature=0,
        top_p=1,
        max_tokens=min(cfg.max_output_tokens, 4096),
    )
    raw = response.choices[0].message.content or ""
    parsed = extract_json(raw)
    usage = getattr(response, "usage", None)
    manifest = {
        "model": cfg.model,
        "mode": "vlm",
        "timeout_seconds": timeout_seconds,
        "input_images": len(VIEWS),
        "input_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
        "raw_response": raw,
    }
    return parsed, manifest


def normalize_vlm_link_map(value: dict[str, Any], links: list[str]) -> dict[str, dict[str, Any]]:
    raw_links = value.get("links", [])
    if not isinstance(raw_links, list):
        raise ValueError("VLM output missing links array")
    by_link = {str(item.get("link_id")): item for item in raw_links if isinstance(item, dict) and item.get("link_id")}
    missing = [link for link in links if link not in by_link]
    if missing:
        raise ValueError("VLM output missing link ids: " + ",".join(missing))
    return by_link


def build_case_packet(row: dict[str, str], schema: dict[str, Any], *, mode: str, timeout_seconds: float) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    case_id = row["case_id"]
    run_root = RUNS / mode
    case_run = run_root / case_id
    if case_run.exists():
        shutil.rmtree(case_run)
    case_run.mkdir(parents=True, exist_ok=True)

    image_text_path = ROOT / row["image_text_json"]
    urdf_path = ROOT / row["sanitized_urdf"]
    image_text = load_json(image_text_path)
    links, joints = parse_urdf(urdf_path)
    images = {view: ROOT / image_text["images"][view] for view in VIEWS}
    vlm_links: dict[str, dict[str, Any]] = {}
    vlm_manifest: dict[str, Any] = {"mode": mode}
    if mode == "vlm":
        parsed, vlm_manifest = vlm_focus_and_observations(row, links, joints, images, timeout_seconds)
        (case_run / "raw_visual_agent_response.json").write_text(json.dumps(vlm_manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        vlm_links = normalize_vlm_link_map(parsed, links)

    source_images = {view: str(path) for view, path in images.items()}
    geometries: dict[str, ViewGeometry] = {}
    for view, path in images.items():
        with Image.open(path) as image:
            geometries[view] = robot_view_geometry(image)

    packet_links = []
    audit_rows: list[dict[str, Any]] = []
    count = max(1, len(links))
    span_ratio = max(0.32, min(0.62, 3.2 / count))
    for index, link_id in enumerate(links):
        vlm_item = vlm_links.get(link_id, {})
        focus_by_view = vlm_item.get("focus_by_view", {}) if isinstance(vlm_item, dict) else {}
        center = (index + 0.5) / count
        prox_center = max(0.02, index / count)
        dist_center = min(0.98, (index + 1) / count)
        link_dir = case_run / "crops" / link_id

        link_crops = []
        joint_crops_prox = []
        joint_crops_dist = []
        for view in ("front", "isometric"):
            src = images[view]
            with Image.open(src) as image:
                view_focus = focus_by_view.get(view) if isinstance(focus_by_view, dict) else None
                if mode == "vlm" and isinstance(view_focus, dict):
                    link_box = focus_box_from_normalized(image, view_focus)
                    prox_box = focus_box_from_normalized(image, view_focus)
                    dist_box = focus_box_from_normalized(image, view_focus)
                    crop_method = "glm_vlm_normalized_focus_box"
                else:
                    link_box = focus_box(image, geometries[view], center_ratio=center, span_ratio=span_ratio, mode=view)
                    prox_box = focus_box(image, geometries[view], center_ratio=prox_center, span_ratio=span_ratio * 0.75, mode=view)
                    dist_box = focus_box(image, geometries[view], center_ratio=dist_center, span_ratio=span_ratio * 0.75, mode=view)
                    crop_method = "silhouette_bbox_plus_urdf_link_order"
            link_crop_path = link_dir / f"{view}_link_crop.png"
            prox_crop_path = link_dir / f"{view}_proximal_joint_crop.png"
            dist_crop_path = link_dir / f"{view}_distal_joint_crop.png"
            link_meta = crop_image(src, link_crop_path, link_box)
            prox_meta = crop_image(src, prox_crop_path, prox_box)
            dist_meta = crop_image(src, dist_crop_path, dist_box)
            link_crops.append(f"crop:{case_id}:{link_id}:{view}:link:{link_meta['path']}")
            joint_crops_prox.append(f"crop:{case_id}:{link_id}:{view}:proximal:{prox_meta['path']}")
            joint_crops_dist.append(f"crop:{case_id}:{link_id}:{view}:distal:{dist_meta['path']}")
            for kind, meta in (("link", link_meta), ("proximal", prox_meta), ("distal", dist_meta)):
                audit_rows.append(
                    {
                        "case_id": case_id,
                        "link_id": link_id,
                        "view": view,
                        "crop_kind": kind,
                        "crop_path": meta["path"],
                        "bbox_px": json.dumps(meta["bbox_px"]),
                        "localization_method": crop_method,
                        "gt_geometry_used": False,
                    }
                )

        vlm_observations = vlm_item.get("visual_observations") if isinstance(vlm_item, dict) else None
        vlm_confidence = vlm_item.get("confidence") if isinstance(vlm_item, dict) else None
        packet_links.append(
            {
                "link_id": link_id,
                "global_views": [f"global_view:{view}:{source_images[view]}" for view in VIEWS],
                "link_crops": link_crops,
                "proximal_joint_crops": joint_crops_prox,
                "distal_joint_crops": joint_crops_dist,
                "visual_observations": vlm_observations if isinstance(vlm_observations, dict) else observation_template(link_id, index, count, joints),
                "confidence": {
                    "crop_localization": float(vlm_confidence.get("focus", 0.0)) if isinstance(vlm_confidence, dict) and mode == "vlm" else 0.35,
                    "feature_semantics": float(vlm_confidence.get("semantics", 0.0)) if isinstance(vlm_confidence, dict) and mode == "vlm" else 0.0,
                    "reason": "GLM VLM focus and observations" if mode == "vlm" else "non-GT deterministic crop stage; VLM/manual semantic interpretation pending",
                },
                "crop_method": "glm_vlm_normalized_focus_box" if mode == "vlm" else "silhouette_bbox_plus_urdf_link_order",
            }
        )

    packet = {
        "schema_version": "visual_evidence_packet_v1",
        "case_id": case_id,
        "source_images": source_images,
        "links": packet_links,
        "leakage_guard": {
            "uses_gt_mesh": False,
            "uses_gt_segmentation": False,
            "uses_product_identity": False,
        },
    }
    jsonschema.validate(packet, schema)
    (case_run / "visual_evidence_packet_v1.json").write_text(json.dumps(packet, indent=2, ensure_ascii=False), encoding="utf-8")
    write_stage_manifest(
        case_run / "stage_manifest.json",
        stage="visual_agent",
        status="SUCCESS",
        schema_version="visual_evidence_packet_v1",
        producer="run_visual_agent.py",
        input_paths=[image_text_path, urdf_path],
    )
    make_case_contact_sheet(case_id, links, mode=mode)
    return packet, audit_rows, vlm_manifest


def make_case_contact_sheet(case_id: str, links: list[str], *, mode: str) -> None:
    tiles = []
    for link_id in links:
        path = RUNS / mode / case_id / "crops" / link_id / f"{DISPLAY_VIEW}_link_crop.png"
        if not path.exists():
            continue
        with Image.open(path) as image:
            tile = image.convert("RGB")
            tile.thumbnail((210, 160))
        canvas = Image.new("RGB", (230, 200), "white")
        canvas.paste(tile, ((230 - tile.width) // 2, 8))
        draw = ImageDraw.Draw(canvas)
        draw.text((8, 172), link_id, fill="black")
        tiles.append(canvas)
    if not tiles:
        return
    cols = min(5, len(tiles))
    rows = math.ceil(len(tiles) / cols)
    sheet = Image.new("RGB", (cols * 230, rows * 200), "white")
    for i, tile in enumerate(tiles):
        sheet.paste(tile, ((i % cols) * 230, (i // cols) * 200))
    out = RESULTS / "visual_agent_contact_sheets" / mode / f"{case_id}_link_crops.png"
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


def write_report(case_rows: list[dict[str, Any]], audit_rows: list[dict[str, Any]], mode: str) -> None:
    success_cases = sum(1 for row in case_rows if row.get("status") == "SUCCESS")
    total_links = sum(int(row["link_count"]) for row in case_rows)
    stage_status = "SUCCESS" if success_cases == len(case_rows) and total_links > 0 else "FAILURE" if success_cases == 0 else "PARTIAL"
    lines = [
        "# Visual Evidence Agent Stage Report",
        "",
        "## Scope",
        "",
        "This stage generates non-GT global-to-local visual evidence packets for the fixed TrySet-5.",
        f"Generation mode: `{mode}`.",
        "",
        "## Crop localization method",
        "",
        "- Deterministic mode computes a near-white-background silhouette bounding box and divides it by anonymous URDF link order.",
        "- VLM mode asks `glm-5.3-flash` for normalized per-link focus boxes and observable local evidence.",
        "- Generate front/isometric link, proximal-joint, and distal-joint crops for every URDF link.",
        "- Do not use GT mesh, GT segmentation, STEP/CAD, product identity, or hidden part labels.",
        "",
        "## Coverage",
        "",
        f"- Cases: `{len(case_rows)}`.",
        f"- Links: `{total_links}`.",
        f"- Crop records: `{len(audit_rows)}`.",
        f"- Stage status: `{stage_status}` for crop/evidence-packet generation.",
        "",
        "## Known limitations",
        "",
        "- Crops must be manually spot-checked before downstream MEP generation.",
        "- Deterministic crops are broad localization aids, not semantic annotations.",
        "- Side-view occlusion and high-link-count robots may have weak per-link localization.",
        "- Deterministic mode is not sufficient to release packets to MEP unless manual spot check explicitly passes.",
        "",
        "## Manual inspection targets",
        "",
    ]
    for row in case_rows:
        if row.get("contact_sheet"):
            lines.append(f"- `{row['case_id']}` contact sheet: `{row['contact_sheet']}`")
        else:
            lines.append(f"- `{row['case_id']}`: no contact sheet; status `{row.get('status')}`")
    (RESULTS / f"visual_agent_report_{mode}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run Try-3 FreeCAD Visual Evidence Agent.")
    parser.add_argument("--mode", choices=["deterministic", "vlm"], default="deterministic")
    parser.add_argument("--case", help="Optional single case_id smoke run.")
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    args = parser.parse_args()

    RESULTS.mkdir(parents=True, exist_ok=True)
    schema = load_json(SCHEMA)
    rows = list(csv.DictReader(TRYSET.open("r", encoding="utf-8")))
    if args.case:
        rows = [row for row in rows if row["case_id"] == args.case]
        if not rows:
            raise SystemExit(f"case not in TrySet: {args.case}")
    all_audit_rows: list[dict[str, Any]] = []
    case_rows: list[dict[str, Any]] = []
    for row in rows:
        try:
            packet, audit_rows, vlm_manifest = build_case_packet(row, schema, mode=args.mode, timeout_seconds=args.timeout_seconds)
        except Exception as exc:
            case_run = RUNS / args.mode / row["case_id"]
            case_run.mkdir(parents=True, exist_ok=True)
            failure = {
                "case_id": row["case_id"],
                "stage": "visual_agent",
                "mode": args.mode,
                "status": "FAILURE",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            (case_run / "stage_manifest.json").write_text(json.dumps(failure, indent=2, ensure_ascii=False), encoding="utf-8")
            case_rows.append(
                {
                    "case_id": row["case_id"],
                    "status": "FAILURE",
                    "link_count": 0,
                    "crop_records": 0,
                    "packet_path": "",
                    "contact_sheet": "",
                    "gt_geometry_used": False,
                    "semantic_observation_source": "glm-5.3-flash" if args.mode == "vlm" else "pending_vlm_or_manual",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                }
            )
            continue
        all_audit_rows.extend(audit_rows)
        case_rows.append(
            {
                "case_id": row["case_id"],
                "status": "SUCCESS",
                "link_count": len(packet["links"]),
                "crop_records": len(audit_rows),
                "packet_path": str(RUNS / args.mode / row["case_id"] / "visual_evidence_packet_v1.json"),
                "contact_sheet": str(RESULTS / "visual_agent_contact_sheets" / args.mode / f"{row['case_id']}_link_crops.png"),
                "gt_geometry_used": False,
                "semantic_observation_source": "glm-5.3-flash" if args.mode == "vlm" else "pending_vlm_or_manual",
                "input_tokens": vlm_manifest.get("input_tokens", 0),
                "output_tokens": vlm_manifest.get("output_tokens", 0),
                "total_tokens": vlm_manifest.get("total_tokens", 0),
            }
        )
    write_csv(RESULTS / f"visual_agent_case_summary_{args.mode}.csv", case_rows)
    write_csv(RESULTS / f"visual_agent_crop_audit_{args.mode}.csv", all_audit_rows)
    write_report(case_rows, all_audit_rows, args.mode)
    print(json.dumps({"mode": args.mode, "cases": len(case_rows), "links": sum(r["link_count"] for r in case_rows), "crop_records": len(all_audit_rows), "gt_geometry_used": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
