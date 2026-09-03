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
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib.collections import PolyCollection
from PIL import Image, ImageDraw, ImageStat
from scipy.spatial.transform import Rotation


ROOT = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parents[1]
FORMAL_EXP = ROOT / "experiments" / "try3_freecad_full_workflow"
TRYSET = FORMAL_EXP / "tryset5_v1.csv"
RUNS = EXP / "runs" / "a1_colored"
ARTIFACTS = EXP / "artifacts" / "a1_colored"
RESULTS = EXP / "results"

sys.path.insert(0, str(ROOT / "go_nogo2" / "scripts"))
from glm_config import load_glm  # noqa: E402

sys.path.insert(0, str(FORMAL_EXP / "scripts"))
from run_visual_agent_v2 import (  # noqa: E402
    clamp_bbox,
    extract_json,
    normalize_joint_region,
    parse_urdf,
    write_csv,
    write_json,
)


VIEWS = {
    "front": (0, 0),
    "rear": (180, 0),
    "left": (90, 0),
    "right": (-90, 0),
    "top": (0, 90),
    "isometric": (45, 25),
}
DEFAULT_VIEWS = ("front", "isometric")
PALETTE = [
    (230, 57, 70),
    (29, 53, 87),
    (69, 123, 157),
    (42, 157, 143),
    (233, 196, 106),
    (244, 162, 97),
    (231, 111, 81),
    (131, 56, 236),
    (255, 0, 110),
    (58, 134, 255),
    (6, 214, 160),
    (255, 209, 102),
    (17, 138, 178),
    (7, 59, 76),
    (239, 71, 111),
    (118, 200, 147),
    (255, 183, 3),
    (33, 158, 188),
    (142, 202, 230),
    (251, 133, 0),
    (80, 81, 79),
]


@dataclass(frozen=True)
class RenderMesh:
    link_id: str
    source_link: str
    mesh: trimesh.Trimesh
    color_rgb: tuple[int, int, int]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def vector(text: str | None, default: list[float]) -> np.ndarray:
    if not text:
        return np.asarray(default, dtype=float)
    values = [float(x) for x in text.split()]
    if len(values) != len(default):
        return np.asarray(default, dtype=float)
    return np.asarray(values, dtype=float)


def origin_transform(node: ET.Element | None) -> np.ndarray:
    matrix = np.eye(4)
    if node is None:
        return matrix
    matrix[:3, :3] = Rotation.from_euler("xyz", vector(node.get("rpy"), [0, 0, 0])).as_matrix()
    matrix[:3, 3] = vector(node.get("xyz"), [0, 0, 0])
    return matrix


def link_transforms(root: ET.Element) -> dict[str, np.ndarray]:
    links = [x.get("name", "") for x in root.findall("link")]
    children: dict[str, list[tuple[str, np.ndarray]]] = defaultdict(list)
    child_names: set[str] = set()
    for joint in root.findall("joint"):
        parent, child = joint.find("parent"), joint.find("child")
        if parent is None or child is None:
            continue
        p, c = parent.get("link", ""), child.get("link", "")
        children[p].append((c, origin_transform(joint.find("origin"))))
        child_names.add(c)
    roots = [x for x in links if x and x not in child_names]
    transforms = {x: np.eye(4) for x in roots}
    queue: deque[str] = deque(roots)
    while queue:
        parent = queue.popleft()
        for child, local in children[parent]:
            transforms[child] = transforms[parent] @ local
            queue.append(child)
    return transforms


def view_rotation(azimuth_deg: float, elevation_deg: float) -> np.ndarray:
    az, elv = np.radians([azimuth_deg, elevation_deg])
    rz = Rotation.from_euler("z", -az).as_matrix()
    rx = Rotation.from_euler("x", elv).as_matrix()
    return rx @ rz


def case_dir(case_id: str) -> Path:
    return ROOT / "go_nogo3" / "data" / "dev15" / case_id


def sanitized_link_ids(row: dict[str, str]) -> list[str]:
    links, _ = parse_urdf(ROOT / row["sanitized_urdf"])
    return links


def source_link_names(gt: dict[str, Any]) -> list[str]:
    links = gt.get("links", [])
    if not isinstance(links, list) or not all(isinstance(x, str) for x in links):
        raise ValueError("kinematic_gt links missing")
    return links


def load_colored_meshes(row: dict[str, str]) -> tuple[list[RenderMesh], dict[str, Any]]:
    cid = row["case_id"]
    cdir = case_dir(cid)
    gt = load_json(cdir / "kinematic_gt.json")
    source_links = source_link_names(gt)
    link_ids = sanitized_link_ids(row)
    if len(source_links) != len(link_ids):
        raise ValueError(f"source/sanitized link count mismatch: {len(source_links)} vs {len(link_ids)}")

    root = ET.parse(cdir / "urdf" / "model.urdf").getroot()
    transforms = link_transforms(root)
    source_to_anon = dict(zip(source_links, link_ids, strict=True))
    output: list[RenderMesh] = []
    manifest_links: list[dict[str, Any]] = []
    for source_index, source_link in enumerate(source_links):
        link_node = next((node for node in root.findall("link") if node.get("name") == source_link), None)
        if link_node is None:
            raise ValueError(f"missing source link in GT URDF: {source_link}")
        anon = source_to_anon[source_link]
        color = PALETTE[source_index % len(PALETTE)]
        loaded_parts: list[trimesh.Trimesh] = []
        for visual in link_node.findall("visual"):
            mesh_node = visual.find("geometry/mesh")
            if mesh_node is None or not mesh_node.get("filename"):
                continue
            mesh_path = (cdir / "urdf" / mesh_node.get("filename", "")).resolve()
            loaded = trimesh.load(mesh_path, force="scene", process=True)
            parts = list(loaded.geometry.values()) if isinstance(loaded, trimesh.Scene) else [loaded]
            scale = vector(mesh_node.get("scale"), [1, 1, 1])
            transform = transforms.get(source_link, np.eye(4)) @ origin_transform(visual.find("origin"))
            for part in parts:
                if not isinstance(part, trimesh.Trimesh) or len(part.faces) == 0:
                    continue
                mesh = part.copy()
                mesh.vertices *= scale
                mesh.apply_transform(transform)
                loaded_parts.append(mesh)
        if not loaded_parts:
            manifest_links.append({"link_id": anon, "source_link": source_link, "color_rgb": list(color), "has_visual_mesh": False})
            continue
        mesh = trimesh.util.concatenate(loaded_parts) if len(loaded_parts) > 1 else loaded_parts[0]
        output.append(RenderMesh(anon, source_link, mesh, color))
        manifest_links.append({"link_id": anon, "source_link": source_link, "color_rgb": list(color), "has_visual_mesh": True})
    if not output:
        raise ValueError("no renderable visual meshes in case")
    manifest = {
        "case_id": cid,
        "input_mode": "A1_colored_full_assembly_oracle",
        "gt_geometry_used": True,
        "gt_segmentation_used": True,
        "formal_try3_input": False,
        "links": manifest_links,
    }
    return output, manifest


def render_view(meshes: list[RenderMesh], view: str, output: Path, dpi: int = 160) -> None:
    az, elv = VIEWS[view]
    rotation = view_rotation(az, elv)
    polygons: list[np.ndarray] = []
    depths: list[float] = []
    colors: list[tuple[float, float, float, float]] = []
    light = np.array([0.25, -0.35, 0.9])
    light /= np.linalg.norm(light)
    for item in meshes:
        mesh = item.mesh
        vertices = np.asarray(mesh.vertices) @ rotation.T
        faces = np.asarray(mesh.faces)
        tri = vertices[faces]
        normal = np.asarray(mesh.face_normals) @ rotation.T
        shade = 0.58 + 0.34 * np.clip(normal @ light, -0.25, 1)
        base = np.asarray(item.color_rgb, dtype=float) / 255.0
        polygons.extend(tri[:, :, :2])
        depths.extend(tri[:, :, 2].mean(axis=1))
        colors.extend([tuple(np.clip(base * float(s), 0, 1).tolist() + [1.0]) for s in shade])
    order = np.argsort(depths)
    fig, ax = plt.subplots(figsize=(6, 6), dpi=dpi, facecolor="white")
    collection = PolyCollection(
        [polygons[i] for i in order],
        facecolors=[colors[i] for i in order],
        edgecolors="none",
        rasterized=True,
    )
    ax.add_collection(collection)
    all_vertices = np.vstack([m.mesh.vertices @ rotation.T for m in meshes])
    mins, maxs = all_vertices[:, :2].min(axis=0), all_vertices[:, :2].max(axis=0)
    center = (mins + maxs) / 2
    span = max(float((maxs - mins).max()), 1e-9) * 0.58
    ax.set_xlim(center[0] - span, center[0] + span)
    ax.set_ylim(center[1] - span, center[1] + span)
    ax.set_aspect("equal")
    ax.axis("off")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", pad_inches=0.02, facecolor="white")
    plt.close(fig)


def generate_colored_renders(row: dict[str, str], views: list[str]) -> tuple[dict[str, Path], dict[str, Any]]:
    meshes, manifest = load_colored_meshes(row)
    out_dir = ARTIFACTS / "colored_renders" / row["case_id"]
    if out_dir.exists():
        shutil.rmtree(out_dir)
    images: dict[str, Path] = {}
    for view in views:
        path = out_dir / f"{view}.png"
        render_view(meshes, view, path)
        images[view] = path
    write_json(out_dir / "colored_link_manifest.json", manifest)
    return images, manifest


def image_item(path: Path) -> dict[str, Any]:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}}


def build_prompt(case_id: str, links: list[str], joints: list[Any], views: list[str], color_manifest: dict[str, Any]) -> str:
    color_map = [
        {"link_id": item["link_id"], "color_rgb": item["color_rgb"], "has_visual_mesh": item.get("has_visual_mesh", True)}
        for item in color_manifest["links"]
    ]
    return json.dumps(
        {
            "task": "A1 diagnostic oracle: locate robot links and candidate visible details in colored full-assembly renders. Return strict top-level JSON only.",
            "case_id": case_id,
            "input_condition": "GT-derived colored full assembly render. Each URDF link has a unique color. This is diagnostic only, not formal Try-3.",
            "views": views,
            "links": links,
            "expected_link_count": len(links),
            "color_map": color_map,
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
                "case_id": case_id,
                "views": views,
                "links": [
                    {
                        "link_id": "exact URDF link id",
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
                "oracle_input_guard": {"uses_gt_mesh": True, "uses_gt_segmentation": True, "formal_try3_input": False},
            },
            "rules": [
                "Use normalized [cx, cy, w, h] image coordinates in [0,1].",
                f"Return every input link exactly once: exactly {len(links)} link objects.",
                "Use the color_map to distinguish links, but do not infer product identity.",
                "Some URDF links may have has_visual_mesh=false. Return those link_ids with visibility='unknown' or 'occluded' and broad low-confidence boxes; do not invent a colored visible body for them.",
                "At most five candidate detail regions per link.",
                "Do not generate CAD, MFG, or mechanical embodiment plans.",
            ],
        },
        ensure_ascii=False,
    )


def run_vlm(row: dict[str, str], links: list[str], joints: list[Any], images: dict[str, Path], views: list[str], color_manifest: dict[str, Any], timeout_seconds: float) -> tuple[str, dict[str, Any]]:
    cfg = load_glm()
    client = cfg.create_client().with_options(timeout=timeout_seconds, max_retries=0)
    content: list[dict[str, Any]] = [{"type": "text", "text": build_prompt(row["case_id"], links, joints, views, color_manifest)}]
    for view in views:
        content.extend([{"type": "text", "text": f"colored_view={view}"}, image_item(images[view])])
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
    return raw_text, {
        "model": cfg.model,
        "mode": "a1_colored_oracle_scan",
        "views": views,
        "elapsed_seconds": elapsed,
        "input_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
        "raw_response_chars": len(raw_text),
    }


def normalize_scan(raw: dict[str, Any], case_id: str, links: list[str], views: list[str]) -> dict[str, Any]:
    raw_links = raw.get("links", [])
    if not isinstance(raw_links, list):
        raise ValueError("scan plan missing links array")
    by_link = {str(item.get("link_id")): item for item in raw_links if isinstance(item, dict) and item.get("link_id")}
    normalized = []
    allowed_hints = {
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
    }
    for link_id in links:
        item = by_link.get(link_id)
        if not isinstance(item, dict):
            raise ValueError(f"scan plan missing link_id {link_id}")
        bbox_by_view = item.get("link_bbox_by_view", {})
        if not isinstance(bbox_by_view, dict):
            bbox_by_view = {}
        details = []
        raw_details = item.get("candidate_detail_regions", [])
        if not isinstance(raw_details, list):
            raw_details = []
        for idx, detail in enumerate(raw_details[:5]):
            if not isinstance(detail, dict):
                continue
            source_view = str(detail.get("source_view") or views[0])
            if source_view not in views:
                source_view = views[0]
            hint = str(detail.get("feature_hint") or "unknown")
            if hint not in allowed_hints:
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
        normalized.append(
            {
                "link_id": link_id,
                "visibility": str(item.get("visibility") or "unknown") if str(item.get("visibility") or "unknown") in {"clear", "partial", "occluded", "unknown"} else "unknown",
                "link_bbox_by_view": {view: clamp_bbox(bbox_by_view.get(view)) for view in views},
                "proximal_joint_region": normalize_joint_region(item.get("proximal_joint_region"), views),
                "distal_joint_region": normalize_joint_region(item.get("distal_joint_region"), views),
                "candidate_detail_regions": details,
            }
        )
    return {
        "schema_version": "visual_scan_plan_a1_oracle_v1",
        "case_id": case_id,
        "scan_mode": "glm_vlm_colored_oracle_scan",
        "source_views": views,
        "links": normalized,
        "oracle_input_guard": {"uses_gt_mesh": True, "uses_gt_segmentation": True, "formal_try3_input": False},
    }


def bbox_to_pixels(bbox: list[float], width: int, height: int, pad: float = 0.08) -> list[int]:
    cx, cy, w, h = bbox
    w = min(1.0, w * (1.0 + pad))
    h = min(1.0, h * (1.0 + pad))
    x0 = max(0, int((cx - w / 2) * width))
    y0 = max(0, int((cy - h / 2) * height))
    x1 = min(width, int((cx + w / 2) * width))
    y1 = min(height, int((cy + h / 2) * height))
    return [x0, y0, max(x0 + 1, x1), max(y0 + 1, y1)]


def crop_image(src: Path, dst: Path, bbox: list[float]) -> tuple[list[int], float]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as image:
        rgb = image.convert("RGB")
        px = bbox_to_pixels(bbox, rgb.width, rgb.height)
        crop = rgb.crop(tuple(px))
        crop.save(dst)
        stat = ImageStat.Stat(crop.convert("L"))
    return px, 1.0 if stat.mean[0] > 248 and stat.stddev[0] < 5 else 0.0


def generate_crops(case_id: str, images: dict[str, Path], scan: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    for link in scan["links"]:
        link_id = link["link_id"]
        for view, bbox in link["link_bbox_by_view"].items():
            crop_id = f"{case_id}_{link_id}_{view}_link"
            path = RUNS / "crops" / case_id / link_id / f"{crop_id}.png"
            px, empty = crop_image(images[view], path, bbox)
            records.append(crop_record(crop_id, case_id, link_id, "link", view, bbox, px, None, path, empty))
        for key, crop_type in (("proximal_joint_region", "proximal_joint"), ("distal_joint_region", "distal_joint")):
            region = link.get(key)
            if isinstance(region, dict):
                view = region["source_view"]
                crop_id = f"{case_id}_{link_id}_{crop_type}"
                path = RUNS / "crops" / case_id / link_id / f"{crop_id}.png"
                px, empty = crop_image(images[view], path, region["bbox"])
                records.append(crop_record(crop_id, case_id, link_id, crop_type, view, region["bbox"], px, None, path, empty))
        for detail in link.get("candidate_detail_regions", []):
            crop_id = f"{case_id}_{link_id}_{detail['region_id']}"
            view = detail["source_view"]
            path = RUNS / "crops" / case_id / link_id / f"{crop_id}.png"
            px, empty = crop_image(images[view], path, detail["bbox"])
            records.append(crop_record(crop_id, case_id, link_id, "feature", view, detail["bbox"], px, detail["feature_hint"], path, empty))
    return records


def crop_record(crop_id: str, case_id: str, link_id: str, crop_type: str, view: str, bbox: list[float], bbox_px: list[int], feature_hint: str | None, path: Path, empty: float) -> dict[str, Any]:
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
        "localization_source": "glm-5.3-flash on A1 colored oracle render",
        "gt_geometry_used": True,
        "gt_segmentation_used": True,
        "_empty_score": empty,
    }


def make_contact_sheet(case_id: str, crop_records: list[dict[str, Any]]) -> None:
    tiles = []
    for crop in [c for c in crop_records if c["crop_type"] in {"link", "feature"}][:80]:
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
    for idx, tile in enumerate(tiles):
        sheet.paste(tile, ((idx % cols) * 210, (idx // cols) * 180))
    out = RESULTS / "a1_colored_contact_sheets" / f"{case_id}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)


def process_case(row: dict[str, str], views: list[str], timeout_seconds: float) -> dict[str, Any]:
    case_id = row["case_id"]
    case_run = RUNS / "cases" / case_id
    if case_run.exists():
        shutil.rmtree(case_run)
    case_run.mkdir(parents=True, exist_ok=True)
    try:
        images, color_manifest = generate_colored_renders(row, views)
        links, joints = parse_urdf(ROOT / row["sanitized_urdf"])
        raw_text, api_manifest = run_vlm(row, links, joints, images, views, color_manifest, timeout_seconds)
        (case_run / "raw_response.txt").write_text(raw_text, encoding="utf-8")
        write_json(case_run / "api_manifest.json", api_manifest)
        raw = extract_json(raw_text)
        scan = normalize_scan(raw, case_id, links, views)
        write_json(case_run / "visual_scan_plan_a1_oracle_v1.json", scan)
        crop_records = generate_crops(case_id, images, scan)
        packet = {
            "schema_version": "visual_evidence_packet_a1_oracle_v1",
            "case_id": case_id,
            "scan_plan_ref": str(case_run / "visual_scan_plan_a1_oracle_v1.json"),
            "input_mode": "A1_colored_full_assembly_oracle",
            "links": scan["links"],
            "crop_records": [{k: v for k, v in item.items() if not k.startswith("_")} for item in crop_records],
            "oracle_input_guard": {"uses_gt_mesh": True, "uses_gt_segmentation": True, "formal_try3_input": False},
        }
        write_json(case_run / "visual_evidence_packet_a1_oracle_v1.json", packet)
        make_contact_sheet(case_id, crop_records)
        empty_rate = sum(float(c["_empty_score"]) for c in crop_records) / max(1, len(crop_records))
        feature_crops = sum(1 for c in crop_records if c["crop_type"] == "feature")
        return {
            "case_id": case_id,
            "status": "SUCCESS",
            "links": len(links),
            "scan_views": ";".join(views),
            "crop_records": len(crop_records),
            "feature_crops": feature_crops,
            "empty_crop_rate": round(empty_rate, 4),
            "input_tokens": api_manifest["input_tokens"],
            "output_tokens": api_manifest["output_tokens"],
            "total_tokens": api_manifest["total_tokens"],
            "elapsed_seconds": round(api_manifest["elapsed_seconds"], 3),
            "error_type": "",
            "error": "",
        }
    except Exception as exc:
        write_json(case_run / "failure.json", {"case_id": case_id, "error_type": type(exc).__name__, "error": str(exc)})
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


def write_report(rows: list[dict[str, Any]]) -> None:
    a0_path = FORMAL_EXP / "results" / "visual_agent_v2_case_summary.csv"
    a0_rows = list(csv.DictReader(a0_path.open("r", encoding="utf-8"))) if a0_path.exists() else []
    a0_success = sum(1 for r in a0_rows if r.get("status") == "SUCCESS")
    a1_success = sum(1 for r in rows if r.get("status") == "SUCCESS")
    lines = [
        "# Visual Evidence Input Ablation: A1 Colored Link Render",
        "",
        "## Status",
        "",
        f"- A1 attempted cases: `{len(rows)}`.",
        f"- A1 successful cases: `{a1_success}`.",
        "- A1 input is GT-derived colored full-assembly render: `true`.",
        "- Formal Try-3 input: `false`.",
        "",
        "## A0 vs A1 coverage",
        "",
        "| condition | input | cases | successes | links | crops | feature_crops |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    lines.append(
        f"| A0 | original multi-view render | {len(a0_rows)} | {a0_success} | "
        f"{sum(int(r.get('links') or 0) for r in a0_rows)} | "
        f"{sum(int(r.get('crop_records') or 0) for r in a0_rows)} | "
        f"{sum(int(r.get('feature_crops') or 0) for r in a0_rows)} |"
    )
    lines.append(
        f"| A1 | colored full-assembly oracle render | {len(rows)} | {a1_success} | "
        f"{sum(int(r.get('links') or 0) for r in rows)} | "
        f"{sum(int(r.get('crop_records') or 0) for r in rows)} | "
        f"{sum(int(r.get('feature_crops') or 0) for r in rows)} |"
    )
    lines.extend(
        [
            "",
            "## Case rows",
            "",
            "| case_id | status | links | crops | feature_crops | empty_crop_rate | error |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in rows:
        lines.append(f"| {row['case_id']} | {row['status']} | {row['links']} | {row['crop_records']} | {row['feature_crops']} | {row['empty_crop_rate']} | {row['error_type']} |")
    lines.extend(
        [
            "",
            "## Interpretation guard",
            "",
            "A1 uses GT-derived link color information. If A1 improves over A0, the result diagnoses a visual grounding/link disambiguation bottleneck. It is not evidence that the formal method works under the original input contract.",
        ]
    )
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "a1_colored_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run A1 colored-link visual evidence input ablation.")
    parser.add_argument("--case", help="Optional single TrySet case.")
    parser.add_argument("--views", default=",".join(DEFAULT_VIEWS))
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
    args = parser.parse_args()
    views = [v.strip() for v in args.views.split(",") if v.strip()]
    for view in views:
        if view not in VIEWS:
            raise SystemExit(f"unsupported view: {view}")
    rows = list(csv.DictReader(TRYSET.open("r", encoding="utf-8")))
    if args.case:
        rows = [r for r in rows if r["case_id"] == args.case]
        if not rows:
            raise SystemExit(f"case not found: {args.case}")
    results = [process_case(row, views, args.timeout_seconds) for row in rows]
    write_csv(RESULTS / "a1_colored_case_summary.csv", results)
    write_report(results)
    print(json.dumps({"cases": len(results), "successes": sum(1 for r in results if r["status"] == "SUCCESS")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
